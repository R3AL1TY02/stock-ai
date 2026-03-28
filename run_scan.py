# run_scan.py
from __future__ import annotations

import os
from typing import List, Dict, Any

import pandas as pd

from ingestion.fetch_data import fetch_data
from features.indicators import add_indicators
from models.ml_model import train_model
from strategies.strategy import generate_signal

FEATURE_COLS = ["rsi", "macd", "sma_50", "sma_200"]

# Absolute paths (ALWAYS write to stock_ai/outputs)
ROOT_DIR = os.path.dirname(__file__)
OUTPUTS_DIR = os.path.join(ROOT_DIR, "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)


def _action_rank(a: str) -> int:
    """
    Sort order for actions (best at top).
    BUY first, then WAIT, then DON'T BUY.
    """
    a = str(a).strip().upper()
    if a.startswith("BUY"):
        return 0
    if a.startswith("WAIT"):
        return 1
    return 2  # DON'T BUY / anything else


def _ensure_date_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Make sure we have a usable Date column so we can tell if data is up-to-date.
    If df index is datetime-like and 'Date' doesn't exist, we create it.
    """
    if df is None or df.empty:
        return df

    if "Date" in df.columns:
        return df

    # If the index is datetime-like, store it
    try:
        idx = df.index
        if hasattr(idx, "dtype") and "datetime" in str(idx.dtype).lower():
            out = df.copy()
            out["Date"] = pd.to_datetime(idx)
            return out
    except Exception:
        pass

    return df


def _last_date_str_from_df(df: pd.DataFrame) -> str:
    """
    Returns last date as YYYY-MM-DD if possible, else "".
    """
    if df is None or df.empty:
        return ""

    if "Date" not in df.columns:
        return ""

    try:
        return str(pd.to_datetime(df["Date"].iloc[-1]).date())
    except Exception:
        return ""


def scan_tickers(tickers: List[str], threshold: float = 0.55) -> pd.DataFrame:
    """
    Runs the full pipeline for each ticker and returns a summary table.
    Also writes per-ticker CSVs into stock_ai/outputs/.

    SPEEDUP #1:
      - Fetch fresh data each run.
      - If an existing outputs/{TICKER}_signals.csv is already at the same latest Date
        as the freshly fetched data -> skip retraining + reuse existing signals.
      - Otherwise regenerate and overwrite the file.
    """

    rows: List[Dict[str, Any]] = []

    for ticker in tickers:
        ticker = str(ticker).strip().upper()
        if not ticker:
            continue

        signals_path = os.path.join(OUTPUTS_DIR, f"{ticker}_signals.csv")

        # 1) Fetch fresh data (this is what makes it accurate for "now")
        df = fetch_data(ticker, period="5y")
        df = add_indicators(df)

        # Ensure Date column exists (for freshness checks + saving)
        df = _ensure_date_column(df)

        # Need enough data for indicators + train/test split
        if df is None or len(df) < 300:
            continue

        fetched_last_date = _last_date_str_from_df(df)

        # 2) If we already have signals, and they match latest fetched date -> reuse
        if os.path.exists(signals_path) and fetched_last_date:
            try:
                existing = pd.read_csv(signals_path)
                # For older files that didn't have Date, this will be ""
                existing_last_date = _last_date_str_from_df(existing)

                if existing_last_date and (existing_last_date == fetched_last_date):
                    last = existing.iloc[-1]
                    rows.append(
                        {
                            "Ticker": ticker,
                            "Action": str(last.get("action", "")).strip(),
                            "Prob Up (5d)": float(last.get("prob", float("nan"))),
                            "Latest Close": float(last.get("Close", float("nan"))),
                            "Rows (test)": int(len(existing)),
                        }
                    )
                    continue
            except Exception:
                # If the file is unreadable, fall back to regeneration
                pass

        # 3) Full pipeline (regenerate)
        split = int(len(df) * 0.8)
        train_df = df.iloc[:split].copy()
        test_df = df.iloc[split:].copy()

        model = train_model(train_df)

        actions: List[str] = []
        probs: List[float] = []

        for i in range(len(test_df)):
            feat_row = test_df.iloc[i][FEATURE_COLS]
            action, prob = generate_signal(model, feat_row, threshold=threshold)
            actions.append(str(action).strip())
            probs.append(float(prob))

        # Save per-ticker signals for drill-down
        test_df["action"] = actions
        test_df["prob"] = probs

        # Make sure Date is present in saved signals too (so freshness check works next time)
        test_df = _ensure_date_column(test_df)

        test_df.to_csv(signals_path, index=False)

        last = test_df.iloc[-1]

        rows.append(
            {
                "Ticker": ticker,
                "Action": str(last.get("action", "")).strip(),
                "Prob Up (5d)": float(last.get("prob", float("nan"))),
                "Latest Close": float(last.get("Close", float("nan"))),
                "Rows (test)": int(len(test_df)),
            }
        )

    out = pd.DataFrame(rows)

    summary_path = os.path.join(OUTPUTS_DIR, "summary.csv")

    if out.empty:
        out.to_csv(summary_path, index=False)
        return out

    # Clean types
    out["Action"] = out["Action"].astype(str).str.strip()
    out["Prob Up (5d)"] = pd.to_numeric(out["Prob Up (5d)"], errors="coerce")
    out["Latest Close"] = pd.to_numeric(out["Latest Close"], errors="coerce")

    # Sort: best action first, then highest probability
    out["_rank"] = out["Action"].map(_action_rank).fillna(99).astype(int)
    out = (
        out.sort_values(["_rank", "Prob Up (5d)"], ascending=[True, False])
        .drop(columns=["_rank"])
        .reset_index(drop=True)
    )

    # Save summary for dashboard (ALWAYS to stock_ai/outputs/summary.csv)
    out.to_csv(summary_path, index=False)
    return out
