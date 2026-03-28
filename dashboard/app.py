# dashboard/app.py

import sys
import os
import html
import math
from datetime import datetime

import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None

# Project root (stock_ai)
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(ROOT)

from run_scan import scan_tickers
from features.projection import project_cash_in_days


# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="Stock AI", layout="wide")


# -----------------------------
# Disclaimer gate
# -----------------------------
if "agreed" not in st.session_state:
    st.session_state.agreed = False

if not st.session_state.agreed:
    st.title("⚠️ Important Disclaimer")
    st.markdown(
        """
This tool is provided for **educational and informational purposes only**.

It does **NOT** constitute financial, investment, or trading advice.

The analysis and signals shown by this software may be inaccurate, incomplete, delayed, or unsuitable for your personal situation.

By continuing to use this software, you acknowledge and agree that:

- You are solely responsible for any decisions you make
- You will not rely on this tool as a substitute for professional financial advice
- The creator cannot be held liable for any losses, damages, or consequences resulting from your use of this tool

**Use entirely at your own risk.**
"""
    )

    if st.button("I Understand & Accept Risk", type="primary"):
        st.session_state.agreed = True
        st.rerun()

    st.stop()


# -----------------------------
# Global UI styling
# -----------------------------
st.markdown(
    """
    <style>
      .stApp {
        background:
          radial-gradient(1200px 600px at 15% 10%, rgba(56,189,248,0.10), transparent 60%),
          radial-gradient(1000px 500px at 85% 15%, rgba(34,197,94,0.10), transparent 55%),
          radial-gradient(900px 500px at 55% 95%, rgba(245,158,11,0.10), transparent 55%),
          linear-gradient(180deg, rgba(2,6,23,1) 0%, rgba(3,7,18,1) 45%, rgba(0,0,0,1) 100%);
      }

      [data-testid="stMetric"] {
        background: rgba(255,255,255,0.045);
        border: 1px solid rgba(255,255,255,0.08);
        padding: 12px 12px;
        border-radius: 16px;
      }

      hr {
        margin: 20px 0 !important;
        border-color: rgba(255,255,255,0.10) !important;
      }

      .podium-wrap{
        display:flex;
        justify-content:center;
        align-items:flex-end;
        gap:18px;
        margin-top:14px;
        margin-bottom:10px;
      }
      .podium-card{
        width: 280px;
        border-radius: 18px;
        padding: 14px 14px 12px 14px;
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.10);
        box-shadow: 0 10px 28px rgba(0,0,0,0.35);
      }
      .podium-card.winner{
        width: 330px;
        box-shadow: 0 14px 40px rgba(0,0,0,0.45), 0 0 0 1px rgba(255,255,255,0.18);
        outline: 1px solid rgba(255,255,255,0.12);
        position: relative;
      }
      .podium-card.winner:before{
        content:"";
        position:absolute;
        inset:-2px;
        border-radius: 20px;
        background: radial-gradient(600px 180px at 50% 0%, rgba(250,204,21,0.22), transparent 60%);
        pointer-events:none;
        z-index:0;
      }
      .podium-inner{ position: relative; z-index: 1; }

      .podium-rank{
        font-weight: 950;
        font-size: 30px;
        opacity: 0.95;
        margin-bottom: 6px;
        display:flex;
        align-items:center;
        gap:10px;
      }
      .podium-rank .rank-pill{
        font-size: 12px;
        font-weight: 900;
        padding: 4px 10px;
        border-radius: 999px;
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.10);
        opacity: 0.95;
      }

      .podium-ticker{
        font-size: 44px;
        font-weight: 980;
        margin: 0;
        line-height: 1.0;
        letter-spacing: 0.8px;
      }

      .podium-prob{
        margin-top: 10px;
        font-size: 13px;
        opacity: 0.92;
      }

      .badge{
        display:inline-block;
        padding:7px 14px;
        border-radius:999px;
        color:white;
        font-weight:950;
        font-size:14px;
        letter-spacing:0.6px;
      }

      .hero-box{
        background: rgba(255,255,255,0.045);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px;
        padding: 14px 16px;
        margin: 8px 0 12px 0;
      }

      .note-box{
        background: rgba(255,255,255,0.035);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 12px 14px;
        margin-top: 8px;
      }

      .small-kicker{
        opacity:0.8;
        font-size:0.85rem;
        margin-bottom:6px;
      }

      .h1{height: 265px;}
      .h2{height: 210px;}
      .h3{height: 190px;}
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Helpers
# -----------------------------
def pick_first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def clean_action_label(val) -> str:
    if val is None:
        return "N/A"

    s = str(val).strip().upper()

    if "DON'T" in s or "DONT" in s:
        return "BEARISH"
    if "WAIT" in s:
        return "NEUTRAL"
    if "BUY" in s:
        return "BULLISH"
    if "BULLISH" in s:
        return "BULLISH"
    if "BEARISH" in s:
        return "BEARISH"
    if "NEUTRAL" in s:
        return "NEUTRAL"
    return "N/A"


def display_action_text(action_clean: str) -> str:
    return action_clean


def badge_colors(action_clean: str) -> tuple[str, str]:
    a = str(action_clean).upper()
    if a == "BULLISH":
        return ("#16a34a", "white")
    if a == "NEUTRAL":
        return ("#f59e0b", "white")
    if a == "BEARISH":
        return ("#dc2626", "white")
    return ("#6b7280", "white")


def prob_emoji(prob) -> str:
    try:
        p = float(prob)
    except Exception:
        return "⚪"
    if p >= 0.65:
        return "🟢"
    if p >= 0.50:
        return "🟠"
    return "🔴"


def safe_prob(x) -> str:
    try:
        return f"{float(x):.2f}"
    except Exception:
        return str(x)


def html_safe_text(s: str) -> str:
    return html.escape(str(s), quote=True)


def compute_daily_returns(close_series: pd.Series) -> pd.Series:
    s = pd.to_numeric(close_series, errors="coerce").dropna()
    if len(s) < 3:
        return pd.Series(dtype=float)
    return s.pct_change().dropna()


def risk_label_from_vol(ann_vol: float) -> tuple[str, float]:
    if math.isnan(ann_vol):
        return ("N/A", 0.0)
    score = max(0.0, min(1.0, (ann_vol - 0.10) / (0.60 - 0.10)))
    if ann_vol < 0.20:
        return ("LOW", score)
    if ann_vol < 0.35:
        return ("MEDIUM", score)
    return ("HIGH", score)


def confidence_from_prob(prob: float, threshold: float) -> tuple[str, float]:
    if prob is None or math.isnan(prob):
        return ("N/A", 0.0)
    dist = abs(prob - threshold)
    score = max(0.0, min(1.0, dist / 0.20))
    if dist >= 0.12:
        return ("HIGH", score)
    if dist >= 0.06:
        return ("MEDIUM", score)
    return ("LOW", score)


def latest_price_for_ticker(ticker: str, outputs_dir: str) -> float | None:
    pth = os.path.join(outputs_dir, f"{ticker}_signals.csv")
    if not os.path.exists(pth):
        return None
    d = pd.read_csv(pth)
    cc = pick_first_existing_column(d, ["Close", "close"])
    if cc is None or len(d) == 0:
        return None
    try:
        return float(d.iloc[-1][cc])
    except Exception:
        return None


def portfolio_value(paper: dict, outputs_dir: str) -> tuple[float, pd.DataFrame]:
    rows = []
    total_value = float(paper.get("cash", 0.0))

    for t, pos in paper.get("positions", {}).items():
        if isinstance(pos, dict):
            shares = float(pos.get("shares", 0.0))
            avg_price = float(pos.get("avg_price", 0.0))
        else:
            shares = float(pos)
            avg_price = float("nan")

        price = latest_price_for_ticker(t, outputs_dir)
        mkt = (price * shares) if (price is not None) else float("nan")
        unrealized = (mkt - (shares * avg_price)) if (price is not None and not math.isnan(avg_price)) else float("nan")

        if price is not None:
            total_value += mkt

        rows.append(
            {
                "Ticker": t,
                "Shares": shares,
                "Avg Price": avg_price,
                "Price": price,
                "Market Value": mkt,
                "Unrealized P/L": unrealized,
            }
        )

    return total_value, pd.DataFrame(rows)


def record_equity_point(paper: dict, outputs_dir: str):
    total, _ = portfolio_value(paper, outputs_dir)
    paper.setdefault("equity_curve", [])
    paper["equity_curve"].append(
        {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cash": float(paper.get("cash", 0.0)),
            "equity": float(total),
        }
    )


def compute_drawdown(equity_series: pd.Series) -> float:
    if equity_series is None or len(equity_series) < 2:
        return 0.0
    s = pd.to_numeric(equity_series, errors="coerce").dropna()
    if len(s) < 2:
        return 0.0
    running_max = s.cummax()
    dd = (s / running_max) - 1.0
    return float(dd.min())


def trophy_for_rank(rank: str) -> str:
    if rank == "1":
        return "🏆"
    if rank == "2":
        return "🥈"
    if rank == "3":
        return "🥉"
    return ""


def compute_streaks(closed_trade_returns: pd.Series) -> tuple[int, int]:
    best_win_streak = 0
    best_loss_streak = 0
    cur_win = 0
    cur_loss = 0

    for r in closed_trade_returns.dropna():
        if r > 0:
            cur_win += 1
            cur_loss = 0
        elif r < 0:
            cur_loss += 1
            cur_win = 0
        else:
            cur_win = 0
            cur_loss = 0

        best_win_streak = max(best_win_streak, cur_win)
        best_loss_streak = max(best_loss_streak, cur_loss)

    return best_win_streak, best_loss_streak


def fmt_money(x) -> str:
    try:
        return f"£{float(x):,.2f}"
    except Exception:
        return "N/A"


def fmt_num(x) -> str:
    try:
        return f"{float(x):,.2f}"
    except Exception:
        return "N/A"


def fmt_big_num(x) -> str:
    try:
        x = float(x)
    except Exception:
        return "N/A"
    abs_x = abs(x)
    if abs_x >= 1_000_000_000_000:
        return f"{x / 1_000_000_000_000:.2f}T"
    if abs_x >= 1_000_000_000:
        return f"{x / 1_000_000_000:.2f}B"
    if abs_x >= 1_000_000:
        return f"{x / 1_000_000:.2f}M"
    return f"{x:,.0f}"


def classify_trend(pct: float | None) -> str:
    if pct is None or pd.isna(pct):
        return "N/A"
    if pct >= 10:
        return "Strong Uptrend"
    if pct >= 3:
        return "Uptrend"
    if pct > -3:
        return "Sideways"
    if pct > -10:
        return "Downtrend"
    return "Strong Downtrend"


def make_signal_explanation(action_clean: str, prob_val, threshold_val: float, ann_vol: float | None) -> str:
    parts = []

    if action_clean == "BULLISH":
        parts.append("Signal is bullish because the model probability is above the active threshold.")
    elif action_clean == "BEARISH":
        parts.append("Signal is bearish because the latest output is below the threshold or explicitly negative.")
    elif action_clean == "NEUTRAL":
        parts.append("Signal is neutral because the setup is not strong enough to justify a clear bullish call.")
    else:
        parts.append("Signal explanation is limited because the action label could not be read cleanly.")

    if prob_val is not None:
        dist = abs(float(prob_val) - float(threshold_val))
        if dist >= 0.12:
            parts.append("Confidence looks relatively strong because the probability sits comfortably away from the threshold.")
        elif dist >= 0.06:
            parts.append("Confidence looks moderate because the probability is somewhat clear of the threshold.")
        else:
            parts.append("Confidence looks softer because the probability is close to the threshold.")

    if ann_vol is not None and not math.isnan(ann_vol):
        if ann_vol < 0.20:
            parts.append("Historical volatility looks fairly calm, so the setup appears lower risk.")
        elif ann_vol < 0.35:
            parts.append("Historical volatility is moderate, so the setup has a balanced risk profile.")
        else:
            parts.append("Historical volatility is elevated, so price swings may be larger than usual.")

    return " ".join(parts)


def make_portfolio_summary(paper: dict, total_value: float, holdings_df: pd.DataFrame) -> str:
    num_positions = 0 if holdings_df.empty else len(holdings_df)
    invested_value = 0.0
    if not holdings_df.empty and "Market Value" in holdings_df.columns:
        invested_value = pd.to_numeric(holdings_df["Market Value"], errors="coerce").fillna(0).sum()

    cash = float(paper.get("cash", 0.0))
    utilisation = (invested_value / total_value * 100.0) if total_value > 0 else 0.0

    if num_positions == 0:
        return "You are currently fully in cash with no open paper positions."
    return (
        f"You currently hold {num_positions} position(s), with {utilisation:.1f}% of the paper account invested "
        f"and {fmt_money(cash)} remaining in cash."
    )


def make_backtest_summary(stats: dict) -> str:
    lines = []

    strat = stats.get("return_pct")
    bh = stats.get("buy_hold_return_pct")
    dd = stats.get("max_drawdown_pct")
    wr = stats.get("win_rate")
    tim = stats.get("time_in_market_pct")
    pf = stats.get("profit_factor")

    if strat is not None and bh is not None:
        diff = strat - bh
        if diff > 0:
            lines.append(f"The strategy outperformed buy-and-hold by {diff:.2f}% over the tested period.")
        elif diff < 0:
            lines.append(f"The strategy underperformed buy-and-hold by {abs(diff):.2f}% over the tested period.")
        else:
            lines.append("The strategy performed roughly in line with buy-and-hold over the tested period.")

    if wr is not None:
        if wr >= 60:
            lines.append(f"Trade quality looked strong, with a win rate of {wr:.2f}%.")
        elif wr >= 45:
            lines.append(f"Trade quality looked mixed, with a win rate of {wr:.2f}%.")
        else:
            lines.append(f"Trade quality looked weaker, with a win rate of {wr:.2f}%.")

    if dd is not None:
        if abs(dd) < 10:
            lines.append(f"Drawdown stayed relatively contained at {dd:.2f}%.")
        elif abs(dd) < 20:
            lines.append(f"Drawdown was noticeable at {dd:.2f}%, but still manageable.")
        else:
            lines.append(f"Drawdown was heavy at {dd:.2f}%, so risk was meaningful.")

    if tim is not None:
        lines.append(f"The system was in the market {tim:.2f}% of the time.")

    if pf is not None:
        lines.append(f"Profit factor came in at {pf:.2f}, which helps show trade efficiency.")

    return " ".join(lines)


# -----------------------------
# Scan history + sector helpers
# -----------------------------
SECTOR_MAP = {
    "AAPL": "Technology",
    "MSFT": "Technology",
    "GOOGL": "Technology",
    "AMZN": "Consumer",
    "NVDA": "Technology",
    "META": "Technology",
    "TSLA": "Consumer",
    "AMD": "Technology",
    "NFLX": "Communication",
    "INTC": "Technology",
    "AVGO": "Technology",
    "ORCL": "Technology",
    "CRM": "Technology",
    "ADBE": "Technology",
    "QCOM": "Technology",
    "TXN": "Technology",
    "CSCO": "Technology",
    "IBM": "Technology",
    "NOW": "Technology",
    "SNOW": "Technology",
    "UBER": "Technology",
    "ABNB": "Consumer",
    "SHOP": "Technology",
    "PYPL": "Financials",
    "SQ": "Financials",
    "JPM": "Financials",
    "BAC": "Financials",
    "GS": "Financials",
    "MS": "Financials",
    "V": "Financials",
    "MA": "Financials",
    "AXP": "Financials",
    "COST": "Consumer",
    "WMT": "Consumer",
    "HD": "Consumer",
    "LOW": "Consumer",
    "NKE": "Consumer",
    "DIS": "Communication",
    "PEP": "Consumer",
    "KO": "Consumer",
    "JNJ": "Healthcare",
    "PFE": "Healthcare",
    "UNH": "Healthcare",
    "LLY": "Healthcare",
    "MRK": "Healthcare",
    "XOM": "Energy",
    "CVX": "Energy",
    "CAT": "Industrials",
    "DE": "Industrials",
}


def sector_for_ticker(ticker: str) -> str:
    return SECTOR_MAP.get(str(ticker).upper(), "Other")


def compute_watchlist_health(summary_df: pd.DataFrame, prob_col_name: str) -> tuple[float, str]:
    if summary_df.empty:
        return 0.0, "No data available."

    bullish = float((summary_df["_action_clean"] == "BULLISH").mean())
    avg_prob_local = float(pd.to_numeric(summary_df[prob_col_name], errors="coerce").fillna(0).mean())
    confidence_score = max(0.0, min(1.0, (avg_prob_local - 0.45) / 0.25))
    score = (bullish * 0.55 + confidence_score * 0.45) * 100.0

    if score >= 75:
        label = "Strong watchlist tone"
    elif score >= 55:
        label = "Moderately constructive"
    elif score >= 40:
        label = "Mixed watchlist tone"
    else:
        label = "Weak watchlist tone"

    return round(score, 1), label


def append_scan_history(summary_df: pd.DataFrame, ticker_col_name: str, prob_col_name: str, action_col_name: str, history_path: str):
    scan_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hist_df = summary_df.copy()
    hist_df = hist_df[[ticker_col_name, prob_col_name, action_col_name, "_action_clean"]].copy()
    hist_df.columns = ["Ticker", "Probability", "ActionRaw", "Signal"]
    hist_df["Scan Time"] = scan_time
    hist_df["Sector"] = hist_df["Ticker"].apply(sector_for_ticker)

    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    write_header = not os.path.exists(history_path)
    hist_df.to_csv(history_path, mode="a", header=write_header, index=False)


def load_scan_history(history_path: str) -> pd.DataFrame:
    if not os.path.exists(history_path):
        return pd.DataFrame()
    try:
        df = pd.read_csv(history_path)
        if "Scan Time" in df.columns:
            df["Scan Time"] = pd.to_datetime(df["Scan Time"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


def latest_previous_snapshot(history_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if history_df.empty or "Scan Time" not in history_df.columns:
        return pd.DataFrame(), pd.DataFrame()

    valid_times = history_df["Scan Time"].dropna().sort_values().unique()
    if len(valid_times) == 0:
        return pd.DataFrame(), pd.DataFrame()

    latest_time = valid_times[-1]
    current = history_df[history_df["Scan Time"] == latest_time].copy()

    previous = pd.DataFrame()
    if len(valid_times) >= 2:
        prev_time = valid_times[-2]
        previous = history_df[history_df["Scan Time"] == prev_time].copy()

    return current, previous


def build_signal_change_table(current_df: pd.DataFrame, previous_df: pd.DataFrame) -> pd.DataFrame:
    if current_df.empty:
        return pd.DataFrame()

    cur = current_df[["Ticker", "Probability", "Signal"]].copy()
    cur.columns = ["Ticker", "Current Prob", "Current Signal"]

    if previous_df.empty:
        cur["Previous Prob"] = None
        cur["Previous Signal"] = None
        cur["Signal Change"] = "NEW"
        cur["Prob Change"] = None
        return cur

    prev = previous_df[["Ticker", "Probability", "Signal"]].copy()
    prev.columns = ["Ticker", "Previous Prob", "Previous Signal"]

    merged = cur.merge(prev, on="Ticker", how="left")

    def change_label(row):
        prev_sig = row.get("Previous Signal")
        cur_sig = row.get("Current Signal")
        if pd.isna(prev_sig):
            return "NEW"
        if str(prev_sig) == str(cur_sig):
            return "UNCHANGED"
        return f"{prev_sig} → {cur_sig}"

    merged["Signal Change"] = merged.apply(change_label, axis=1)
    merged["Prob Change"] = pd.to_numeric(merged["Current Prob"], errors="coerce") - pd.to_numeric(merged["Previous Prob"], errors="coerce")
    return merged


def compute_consistency_table(history_df: pd.DataFrame) -> pd.DataFrame:
    if history_df.empty or "Ticker" not in history_df.columns:
        return pd.DataFrame()

    hist = history_df.copy()
    hist["Is Bullish"] = hist["Signal"].astype(str).eq("BULLISH").astype(int)

    grouped = hist.groupby("Ticker").agg(
        Scans=("Ticker", "count"),
        Bullish_Count=("Is Bullish", "sum"),
        Avg_Prob=("Probability", "mean"),
    ).reset_index()

    grouped["Bullish %"] = grouped["Bullish_Count"] / grouped["Scans"] * 100.0
    grouped = grouped.sort_values(["Bullish %", "Avg_Prob"], ascending=[False, False]).reset_index(drop=True)
    return grouped


# -----------------------------
# Backtest
# -----------------------------
def run_backtest_advanced(
    signals_df: pd.DataFrame,
    close_col: str,
    action_col: str,
    start_cash: float = 1000.0,
    mode: str = "Aggressive (100%)",
    fee_per_trade: float = 0.0,
    slippage_pct: float = 0.0,
    prob_col: str | None = None,
    min_prob_to_enter: float | None = None,
) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    df = signals_df.copy()
    df[close_col] = pd.to_numeric(df[close_col], errors="coerce")
    df = df.dropna(subset=[close_col]).reset_index(drop=True)

    if prob_col is not None and prob_col in df.columns:
        df[prob_col] = pd.to_numeric(df[prob_col], errors="coerce")

    if df.empty:
        return pd.DataFrame(), {"error": "No usable rows to backtest."}, pd.DataFrame()

    cash = float(start_cash)
    shares = 0.0
    avg_entry_price = None
    trades = 0
    closed_trades = 0
    wins = 0
    total_fees = 0.0
    entry_step = None

    if "Conservative" in mode:
        invest_fraction = 0.50
    else:
        invest_fraction = 1.00

    hold_neutral = "Hold on Neutral" in mode

    equity_rows = []
    trade_rows = []

    for i in range(len(df)):
        market_price = float(df.loc[i, close_col])
        action_clean = clean_action_label(df.loc[i, action_col])

        prob_val = None
        if prob_col is not None and prob_col in df.columns:
            try:
                prob_val = float(df.loc[i, prob_col])
            except Exception:
                prob_val = None

        entered = False
        exited = False

        allow_entry = True
        if min_prob_to_enter is not None and prob_val is not None:
            allow_entry = prob_val >= float(min_prob_to_enter)

        buy_price = market_price * (1.0 + slippage_pct / 100.0)
        sell_price = market_price * (1.0 - slippage_pct / 100.0)

        if action_clean == "BULLISH" and allow_entry:
            if cash > fee_per_trade:
                invest_amount = cash * invest_fraction
                invest_amount = min(invest_amount, cash - fee_per_trade)

                if invest_amount > 0 and buy_price > 0:
                    new_shares = invest_amount / buy_price

                    if shares > 0 and avg_entry_price is not None:
                        total_cost_basis = (shares * avg_entry_price) + (new_shares * buy_price)
                        shares += new_shares
                        avg_entry_price = total_cost_basis / shares
                    else:
                        shares = new_shares
                        avg_entry_price = buy_price
                        entry_step = i

                    cash -= invest_amount
                    cash -= fee_per_trade
                    total_fees += fee_per_trade
                    trades += 1
                    entered = True

                    trade_rows.append(
                        {
                            "Step": i,
                            "Type": "ENTER",
                            "Price": buy_price,
                            "Market Price": market_price,
                            "Shares": new_shares,
                            "Cash After": cash,
                            "Fee": fee_per_trade,
                            "Prob": prob_val,
                        }
                    )

        elif action_clean == "BEARISH":
            if shares > 0:
                sell_shares = shares
                sell_value = sell_shares * sell_price
                cash += sell_value
                cash -= fee_per_trade
                total_fees += fee_per_trade
                shares = 0.0
                trades += 1
                exited = True

                pnl = None
                pnl_pct = None
                duration = None
                if avg_entry_price is not None:
                    pnl = (sell_price - avg_entry_price) * sell_shares - fee_per_trade
                    pnl_pct = ((sell_price / avg_entry_price) - 1.0) * 100.0
                    closed_trades += 1
                    if pnl > 0:
                        wins += 1
                    if entry_step is not None:
                        duration = i - entry_step

                trade_rows.append(
                    {
                        "Step": i,
                        "Type": "EXIT",
                        "Price": sell_price,
                        "Market Price": market_price,
                        "Shares": sell_shares,
                        "Cash After": cash,
                        "Fee": fee_per_trade,
                        "PnL": pnl,
                        "PnL %": pnl_pct,
                        "Duration": duration,
                        "Prob": prob_val,
                    }
                )

                avg_entry_price = None
                entry_step = None

        elif action_clean == "NEUTRAL":
            if (not hold_neutral) and shares > 0:
                sell_shares = shares
                sell_value = sell_shares * sell_price
                cash += sell_value
                cash -= fee_per_trade
                total_fees += fee_per_trade
                shares = 0.0
                trades += 1
                exited = True

                pnl = None
                pnl_pct = None
                duration = None
                if avg_entry_price is not None:
                    pnl = (sell_price - avg_entry_price) * sell_shares - fee_per_trade
                    pnl_pct = ((sell_price / avg_entry_price) - 1.0) * 100.0
                    closed_trades += 1
                    if pnl > 0:
                        wins += 1
                    if entry_step is not None:
                        duration = i - entry_step

                trade_rows.append(
                    {
                        "Step": i,
                        "Type": "EXIT_NEUTRAL",
                        "Price": sell_price,
                        "Market Price": market_price,
                        "Shares": sell_shares,
                        "Cash After": cash,
                        "Fee": fee_per_trade,
                        "PnL": pnl,
                        "PnL %": pnl_pct,
                        "Duration": duration,
                        "Prob": prob_val,
                    }
                )

                avg_entry_price = None
                entry_step = None

        equity = cash + shares * market_price

        equity_rows.append(
            {
                "i": i,
                "price": market_price,
                "signal": action_clean,
                "prob": prob_val,
                "cash": cash,
                "shares": shares,
                "equity": equity,
                "entered": entered,
                "exited": exited,
                "in_market": 1 if shares > 0 else 0,
            }
        )

    eq = pd.DataFrame(equity_rows)
    trade_log = pd.DataFrame(trade_rows)

    if eq.empty:
        return pd.DataFrame(), {"error": "Backtest failed."}, pd.DataFrame()

    eq["running_peak"] = eq["equity"].cummax()
    eq["drawdown"] = (eq["equity"] / eq["running_peak"]) - 1.0
    eq["daily_return"] = eq["equity"].pct_change().fillna(0.0)

    start_val = float(start_cash)
    end_val = float(eq["equity"].iloc[-1])
    ret = (end_val / start_val - 1.0) if start_val > 0 else 0.0
    max_dd = float(eq["drawdown"].min()) * 100.0

    first_price = float(df.iloc[0][close_col])
    last_price = float(df.iloc[-1][close_col])
    buy_hold_end = (start_cash / first_price) * last_price if first_price > 0 else start_cash
    buy_hold_return_pct = ((buy_hold_end / start_cash) - 1.0) * 100.0 if start_cash > 0 else 0.0

    best_trade_pct = None
    worst_trade_pct = None
    avg_trade_pct = None
    avg_win_pct = None
    avg_loss_pct = None
    profit_factor = None
    expectancy_pct = None
    best_win_streak = 0
    worst_loss_streak = 0
    median_trade_pct = None
    longest_trade = None

    if not trade_log.empty and "PnL %" in trade_log.columns:
        closed = trade_log.dropna(subset=["PnL %"]).copy()
        if not closed.empty:
            best_trade_pct = float(closed["PnL %"].max())
            worst_trade_pct = float(closed["PnL %"].min())
            avg_trade_pct = float(closed["PnL %"].mean())
            median_trade_pct = float(closed["PnL %"].median())

            wins_only = closed[closed["PnL %"] > 0]["PnL %"]
            losses_only = closed[closed["PnL %"] < 0]["PnL %"]

            if not wins_only.empty:
                avg_win_pct = float(wins_only.mean())
            if not losses_only.empty:
                avg_loss_pct = float(losses_only.mean())

            gross_profit = closed.loc[closed["PnL"] > 0, "PnL"].sum() if "PnL" in closed.columns else 0.0
            gross_loss = abs(closed.loc[closed["PnL"] < 0, "PnL"].sum()) if "PnL" in closed.columns else 0.0
            if gross_loss > 0:
                profit_factor = float(gross_profit / gross_loss)

            win_rate_for_expectancy = (len(wins_only) / len(closed)) if len(closed) > 0 else 0.0
            if avg_win_pct is not None and avg_loss_pct is not None:
                expectancy_pct = (win_rate_for_expectancy * avg_win_pct) + ((1 - win_rate_for_expectancy) * avg_loss_pct)

            best_win_streak, worst_loss_streak = compute_streaks(closed["PnL %"])

            if "Duration" in closed.columns and closed["Duration"].notna().any():
                longest_trade = int(pd.to_numeric(closed["Duration"], errors="coerce").dropna().max())

    win_rate = (wins / closed_trades * 100.0) if closed_trades > 0 else 0.0

    sharpe = None
    if len(eq["daily_return"]) > 2 and eq["daily_return"].std() > 0:
        sharpe = float((eq["daily_return"].mean() / eq["daily_return"].std()) * math.sqrt(252))

    time_in_market_pct = float((eq["in_market"] > 0).mean() * 100.0) if len(eq) > 0 else 0.0
    current_state = "Currently holding simulated position" if float(eq["shares"].iloc[-1]) > 0 else "Currently in cash"

    stats = {
        "start": start_val,
        "end": end_val,
        "return_pct": ret * 100.0,
        "trades": trades,
        "closed_trades": closed_trades,
        "win_rate": win_rate,
        "max_drawdown_pct": max_dd,
        "buy_hold_end": buy_hold_end,
        "buy_hold_return_pct": buy_hold_return_pct,
        "best_trade_pct": best_trade_pct,
        "worst_trade_pct": worst_trade_pct,
        "avg_trade_pct": avg_trade_pct,
        "median_trade_pct": median_trade_pct,
        "avg_win_pct": avg_win_pct,
        "avg_loss_pct": avg_loss_pct,
        "profit_factor": profit_factor,
        "expectancy_pct": expectancy_pct,
        "sharpe": sharpe,
        "time_in_market_pct": time_in_market_pct,
        "best_win_streak": best_win_streak,
        "worst_loss_streak": worst_loss_streak,
        "fees_paid": total_fees,
        "current_state": current_state,
        "longest_trade": longest_trade,
    }

    return eq, stats, trade_log


# -----------------------------
# Optional market data helpers
# -----------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def yf_history_for_ticker(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    if yf is None:
        return pd.DataFrame()
    try:
        hist = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
        if hist is None or hist.empty:
            return pd.DataFrame()
        return hist.reset_index()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=1800, show_spinner=False)
def yf_info_for_ticker(ticker: str) -> dict:
    if yf is None:
        return {}
    try:
        info = yf.Ticker(ticker).info
        return info if isinstance(info, dict) else {}
    except Exception:
        return {}


@st.cache_data(ttl=1800, show_spinner=False)
def yf_news_for_ticker(ticker: str) -> list:
    if yf is None:
        return []
    try:
        news = yf.Ticker(ticker).news
        return news if isinstance(news, list) else []
    except Exception:
        return []


@st.cache_data(ttl=1800, show_spinner=False)
def market_snapshot(tickers: tuple[str, ...]) -> pd.DataFrame:
    rows = []
    if yf is None:
        return pd.DataFrame()

    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period="6mo", interval="1d", auto_adjust=False)
            if hist is None or hist.empty or "Close" not in hist.columns:
                continue

            close = pd.to_numeric(hist["Close"], errors="coerce").dropna()
            if len(close) < 2:
                continue

            latest = float(close.iloc[-1])
            prev = float(close.iloc[-2]) if len(close) >= 2 else latest
            chg_1d = ((latest / prev) - 1.0) * 100.0 if prev > 0 else None

            chg_1m = None
            chg_3m = None
            chg_6m = None

            if len(close) >= 21:
                chg_1m = ((latest / float(close.iloc[-21])) - 1.0) * 100.0
            if len(close) >= 63:
                chg_3m = ((latest / float(close.iloc[-63])) - 1.0) * 100.0
            if len(close) >= 126:
                chg_6m = ((latest / float(close.iloc[-126])) - 1.0) * 100.0

            ma20 = float(close.tail(20).mean()) if len(close) >= 20 else None
            ma50 = float(close.tail(50).mean()) if len(close) >= 50 else None

            if ma20 is not None and ma50 is not None:
                if latest > ma20 > ma50:
                    trend = "Uptrend"
                elif latest < ma20 < ma50:
                    trend = "Downtrend"
                else:
                    trend = "Mixed"
            else:
                trend = classify_trend(chg_3m if chg_3m is not None else chg_1m)

            rows.append(
                {
                    "Ticker": t,
                    "Sector": sector_for_ticker(t),
                    "Price": latest,
                    "1D %": chg_1d,
                    "1M %": chg_1m,
                    "3M %": chg_3m,
                    "6M %": chg_6m,
                    "Trend": trend,
                }
            )
        except Exception:
            continue

    return pd.DataFrame(rows)


# -----------------------------
# Paths
# -----------------------------
OUTPUTS_DIR = os.path.join(ROOT, "outputs")
SUMMARY_PATH = os.path.join(OUTPUTS_DIR, "summary.csv")
SCAN_HISTORY_PATH = os.path.join(OUTPUTS_DIR, "scan_history.csv")


# -----------------------------
# Header
# -----------------------------
st.title("Stock AI — One-Click Analysis Tool")
st.warning(
    "This tool provides AI-generated market analysis for educational purposes only. "
    "It does NOT constitute financial advice. Always conduct your own research before making decisions."
)


# -----------------------------
# Sidebar scan controls
# -----------------------------
with st.sidebar:
    st.header("Scan Settings")
    tickers_text = st.text_area(
        "Tickers (comma separated)",
        value="AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, AMD, NFLX, INTC, AVGO, ORCL, CRM, ADBE, QCOM, TXN, CSCO, IBM, NOW, SNOW, UBER, ABNB, SHOP, PYPL, SQ, JPM, BAC, GS, MS, V, MA, AXP, COST, WMT, HD, LOW, NKE, DIS, PEP, KO, JNJ, PFE, UNH, LLY, MRK, XOM, CVX, CAT, DE",
    )
    threshold = st.slider("Bullish threshold (probability)", 0.50, 0.80, 0.55, 0.01)
    run_button = st.button("Run Scan", type="primary")

tickers = [t.strip().upper() for t in tickers_text.split(",") if t.strip()]
ticker_options = sorted(set(tickers))

if "activity_feed" not in st.session_state:
    st.session_state.activity_feed = []

if run_button:
    with st.spinner("Running scan… this may take a minute"):
        _ = scan_tickers(tickers, threshold=threshold)
    st.success("Scan complete")
    st.session_state.activity_feed.insert(
        0, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} — Scan completed for {len(tickers)} ticker(s)."
    )


# -----------------------------
# Load summary
# -----------------------------
if not os.path.exists(SUMMARY_PATH):
    st.info("No results found yet. Click **Run Scan** to generate results.")
    st.stop()

summary = pd.read_csv(SUMMARY_PATH)
if summary.empty:
    st.info("Summary is empty. Click **Run Scan** or try fewer tickers.")
    st.stop()

ticker_col = pick_first_existing_column(summary, ["Ticker", "ticker"])
prob_col = pick_first_existing_column(summary, ["Prob Up (5d)", "prob", "Prob", "probability"])
action_col = pick_first_existing_column(summary, ["Action", "Latest Signal", "signal", "action"])

if ticker_col is None:
    st.error("No ticker column found in outputs/summary.csv.")
    st.stop()
if prob_col is None:
    st.error("No probability column found in outputs/summary.csv.")
    st.stop()
if action_col is None:
    st.error("No Action/Signal column found in outputs/summary.csv. Re-run scan to regenerate outputs.")
    st.stop()

tmp = summary.copy()
tmp[prob_col] = pd.to_numeric(tmp[prob_col], errors="coerce")
tmp[action_col] = tmp[action_col].astype(str).str.strip()
tmp["_action_clean"] = tmp[action_col].apply(clean_action_label)
tmp["_prob_color"] = tmp[prob_col].apply(prob_emoji)
tmp["Sector"] = tmp[ticker_col].apply(sector_for_ticker)

if ticker_col in tmp.columns:
    ticker_options = sorted(tmp[ticker_col].dropna().astype(str).unique().tolist())

last_modified = datetime.fromtimestamp(os.path.getmtime(SUMMARY_PATH))
bullish_count = int((tmp["_action_clean"] == "BULLISH").sum())
neutral_count = int((tmp["_action_clean"] == "NEUTRAL").sum())
bearish_count = int((tmp["_action_clean"] == "BEARISH").sum())
avg_prob = float(pd.to_numeric(tmp[prob_col], errors="coerce").dropna().mean()) if not tmp.empty else float("nan")
watchlist_health_score, watchlist_health_label = compute_watchlist_health(tmp, prob_col)

if "last_history_append_mtime" not in st.session_state:
    st.session_state.last_history_append_mtime = None

summary_mtime = os.path.getmtime(SUMMARY_PATH)
if st.session_state.last_history_append_mtime != summary_mtime:
    append_scan_history(tmp, ticker_col, prob_col, action_col, SCAN_HISTORY_PATH)
    st.session_state.last_history_append_mtime = summary_mtime

history_df = load_scan_history(SCAN_HISTORY_PATH)
current_hist, previous_hist = latest_previous_snapshot(history_df)
signal_change_df = build_signal_change_table(current_hist, previous_hist)
consistency_df = compute_consistency_table(history_df)

st.markdown(
    f"""
    <div class="hero-box">
      <div style="font-size:1.02rem; font-weight:800; margin-bottom:6px;">
        Today's scan found <span style="color:#4ade80;">{bullish_count} bullish</span>,
        <span style="color:#f59e0b;">{neutral_count} neutral</span>,
        and <span style="color:#f87171;">{bearish_count} bearish</span> setups
        across <b>{len(tmp)}</b> tracked names.
      </div>
      <div style="opacity:0.88; font-size:0.92rem;">
        Last scan update: {last_modified.strftime("%Y-%m-%d %H:%M:%S")}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

s1, s2, s3, s4, s5, s6 = st.columns(6)
s1.metric("Tickers Scanned", len(tmp))
s2.metric("Bullish", bullish_count)
s3.metric("Neutral", neutral_count)
s4.metric("Bearish", bearish_count)
s5.metric("Avg Probability", f"{avg_prob:.2f}" if not math.isnan(avg_prob) else "N/A")
s6.metric("Watchlist Health", f"{watchlist_health_score:.1f}/100")

st.caption(f"Watchlist read: {watchlist_health_label}")


# -----------------------------
# Tabs
# -----------------------------
tab_dash, tab_backtest, tab_info = st.tabs(["📌 Dashboard", "📊 Backtest", "📰 Stock Info & News"])


# =============================
# DASHBOARD TAB
# =============================
with tab_dash:
    st.subheader("Top 3 Opportunities Today")

    bullish_df = tmp[tmp["_action_clean"] == "BULLISH"].copy()
    if bullish_df.empty:
        st.info("No strong bullish setups today. Showing the top 3 highest-probability names instead.")
        display_df = tmp.sort_values(prob_col, ascending=False).head(3).reset_index(drop=True)
    else:
        display_df = bullish_df.sort_values(prob_col, ascending=False).head(3).reset_index(drop=True)

    display_df = display_df.head(3).reset_index(drop=True)

    def build_card(rank: str, ticker: str, action_clean: str, prob_txt: str, height_class: str) -> str:
        bg, fg = badge_colors(action_clean)
        ticker_html = html_safe_text(ticker)
        action_html = html_safe_text(display_action_text(action_clean))
        prob_html = html_safe_text(prob_txt)
        emoji_html = html_safe_text(prob_emoji(prob_txt))
        trophy_html = html_safe_text(trophy_for_rank(rank))

        winner = rank == "1"
        winner_class = "winner" if winner else ""

        return (
            f"<div class='podium-card {height_class} {winner_class}'>"
            f"  <div class='podium-inner'>"
            f"    <div class='podium-rank'>#{rank} {trophy_html}<span class='rank-pill'>{emoji_html} PROB</span></div>"
            f"    <p class='podium-ticker'>{ticker_html}</p>"
            f"    <div style='margin-top:12px;'>"
            f"      <span class='badge' style='background:{bg}; color:{fg};'>{action_html}</span>"
            f"    </div>"
            f"    <div class='podium-prob'>Probability Score (5d): <b>{prob_html}</b></div>"
            f"  </div>"
            f"</div>"
        )

    entries = []
    if len(display_df) >= 1:
        r = display_df.iloc[0]
        entries.append(("1", str(r[ticker_col]), str(r["_action_clean"]), safe_prob(r[prob_col]), "h1"))
    if len(display_df) >= 2:
        r = display_df.iloc[1]
        entries.append(("2", str(r[ticker_col]), str(r["_action_clean"]), safe_prob(r[prob_col]), "h2"))
    if len(display_df) >= 3:
        r = display_df.iloc[2]
        entries.append(("3", str(r[ticker_col]), str(r["_action_clean"]), safe_prob(r[prob_col]), "h3"))

    lookup = {e[0]: e for e in entries}
    visual = [lookup.get("2"), lookup.get("1"), lookup.get("3")]
    visual = [v for v in visual if v is not None]

    if len(visual) == 0:
        st.info("No rows to display.")
    else:
        cards_html = "".join([build_card(*v) for v in visual])
        st.markdown(f"<div class='podium-wrap'>{cards_html}</div>", unsafe_allow_html=True)

    st.divider()

    st.subheader("Signal Change Tracker")
    if signal_change_df.empty:
        st.caption("Scan history needs at least one saved snapshot before signal changes can be compared.")
    else:
        movers_up = signal_change_df.sort_values("Prob Change", ascending=False).head(5)
        movers_down = signal_change_df.sort_values("Prob Change", ascending=True).head(5)

        ch1, ch2 = st.columns(2)
        with ch1:
            st.write("Biggest Probability Improvements")
            st.dataframe(movers_up[["Ticker", "Previous Signal", "Current Signal", "Prob Change", "Signal Change"]], use_container_width=True, hide_index=True)
        with ch2:
            st.write("Biggest Probability Drops")
            st.dataframe(movers_down[["Ticker", "Previous Signal", "Current Signal", "Prob Change", "Signal Change"]], use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("Sector Grouping")
    sector_summary = (
        tmp.groupby("Sector")
        .agg(
            Count=(ticker_col, "count"),
            Avg_Prob=(prob_col, "mean"),
            Bullish=("_action_clean", lambda s: int((s == "BULLISH").sum())),
            Neutral=("_action_clean", lambda s: int((s == "NEUTRAL").sum())),
            Bearish=("_action_clean", lambda s: int((s == "BEARISH").sum())),
        )
        .reset_index()
        .sort_values("Avg_Prob", ascending=False)
    )

    st.dataframe(sector_summary, use_container_width=True, hide_index=True)

    if not sector_summary.empty:
        best_sector = sector_summary.iloc[0]
        worst_sector = sector_summary.iloc[-1]
        st.caption(
            f"Strongest sector right now: {best_sector['Sector']} (avg prob {best_sector['Avg_Prob']:.2f}). "
            f"Weakest sector: {worst_sector['Sector']} (avg prob {worst_sector['Avg_Prob']:.2f})."
        )

    st.divider()

    st.subheader("💷 Cash Projection (Next 5 Trading Days)")

    selected_proj = st.selectbox(
        "Pick a ticker to project",
        ticker_options,
        key="proj_ticker",
    )

    proj_path = os.path.join(OUTPUTS_DIR, f"{selected_proj}_signals.csv")
    if not os.path.exists(proj_path):
        st.error(f"Missing file: {proj_path}. Click **Run Scan** to generate it.")
    else:
        proj_df = pd.read_csv(proj_path)
        proj_close_col = pick_first_existing_column(proj_df, ["Close", "close"])

        cash_amount = st.number_input("Enter cash amount (£)", min_value=0.0, step=100.0, value=1000.0)
        lookback = st.slider("Lookback days (for avg daily return)", 5, 60, 20, 1)

        if st.button("Calculate 5-Day Projection"):
            if proj_close_col is None:
                st.error("This ticker file has no Close column, so projection can't be calculated.")
            else:
                result = project_cash_in_days(
                    price_df=proj_df,
                    close_col=proj_close_col,
                    cash_amount=cash_amount,
                    days=5,
                    lookback=lookback,
                )
                if result is None:
                    st.error("Not enough usable Close data to calculate projection.")
                else:
                    st.success(f"Projected Value in 5 days: £{result['projected_value']}")
                    st.write(f"Profit / Loss: £{result['profit']}")
                    st.write(f"Return: {result['percent_return']}%")
                    st.caption(
                        f"Based on avg daily return: {result['avg_daily_return']}% "
                        f"(lookback={result['lookback_used']} days)"
                    )

    st.divider()

    st.subheader("🧾 Paper Trading (Simple)")
    st.caption(
        "Practice mode: you deposit pretend money, then enter or exit tickers using the latest close price. "
        "This does not place real trades."
    )

    if "paper" not in st.session_state:
        st.session_state.paper = {
            "cash": 0.0,
            "initial_cash": 0.0,
            "realized_pl": 0.0,
            "positions": {},
            "trades": [],
            "equity_curve": [],
        }

    paper = st.session_state.paper

    st.write("What you're doing here:")
    st.markdown(
        """
- You **start with cash**.
- When you press **Enter**, your cash turns into **shares** of the ticker.
- When you press **Exit**, shares turn back into **cash**.
- Your **Total Value** = cash + (shares × latest price).
"""
    )

    cA, cB, cC = st.columns([1.1, 1.1, 2.0])

    with cA:
        deposit = st.number_input("Starting cash (£)", min_value=0.0, step=100.0, value=1000.0, key="deposit_amt")
        if st.button("Start / Reset"):
            paper["cash"] = float(deposit)
            paper["initial_cash"] = float(deposit)
            paper["realized_pl"] = 0.0
            paper["positions"] = {}
            paper["trades"] = []
            paper["equity_curve"] = []
            record_equity_point(paper, OUTPUTS_DIR)
            st.success("Paper account started/reset.")
            st.session_state.activity_feed.insert(
                0, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} — Paper account reset to {fmt_money(deposit)}."
            )

    with cB:
        trade_ticker = st.selectbox("Ticker", ticker_options, key="trade_ticker")
        trade_price = latest_price_for_ticker(trade_ticker, OUTPUTS_DIR)
        st.write("Latest price:", f"£{trade_price:.2f}" if trade_price is not None else "N/A")

    with cC:
        trade_cash = st.number_input("Amount (£)", min_value=0.0, step=50.0, value=250.0, key="trade_cash")
        enter_col, exit_col, mtm_col = st.columns([1, 1, 1.2])

        def record_trade(side: str, ticker: str, price: float, shares: float, amount: float, realized_pl=None):
            paper["trades"].append(
                {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "side": side,
                    "ticker": ticker,
                    "price": float(price),
                    "shares": float(shares),
                    "amount": float(amount),
                    "realized_pl": realized_pl,
                }
            )

        with enter_col:
            if st.button("Enter", type="primary"):
                if trade_price is None or trade_price <= 0:
                    st.error("No valid price available for this ticker.")
                elif trade_cash <= 0:
                    st.error("Amount must be > 0.")
                elif float(paper["cash"]) < float(trade_cash):
                    st.error("Not enough cash.")
                else:
                    shares = float(trade_cash) / float(trade_price)

                    old_pos = paper["positions"].get(trade_ticker, {"shares": 0.0, "avg_price": 0.0})
                    old_shares = float(old_pos.get("shares", 0.0))
                    old_avg = float(old_pos.get("avg_price", 0.0))

                    new_total_shares = old_shares + shares
                    new_avg = ((old_shares * old_avg) + float(trade_cash)) / new_total_shares if new_total_shares > 0 else 0.0

                    paper["cash"] = float(paper["cash"]) - float(trade_cash)
                    paper["positions"][trade_ticker] = {
                        "shares": float(new_total_shares),
                        "avg_price": float(new_avg),
                    }

                    record_trade("ENTER", trade_ticker, float(trade_price), float(shares), float(trade_cash))
                    record_equity_point(paper, OUTPUTS_DIR)
                    st.success(f"Entered {shares:.6f} shares of {trade_ticker}.")
                    st.session_state.activity_feed.insert(
                        0,
                        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} — Entered {trade_ticker} for {fmt_money(trade_cash)}.",
                    )

        with exit_col:
            if st.button("Exit"):
                if trade_price is None or trade_price <= 0:
                    st.error("No valid price available for this ticker.")
                elif trade_cash <= 0:
                    st.error("Amount must be > 0.")
                else:
                    pos = paper["positions"].get(trade_ticker)
                    if not pos:
                        st.error("You don't hold this ticker.")
                    else:
                        held = float(pos.get("shares", 0.0))
                        avg_price = float(pos.get("avg_price", 0.0))

                        if held <= 0:
                            st.error("You don't hold this ticker.")
                        else:
                            shares_to_sell = float(trade_cash) / float(trade_price)
                            if shares_to_sell > held:
                                shares_to_sell = held
                                trade_cash_effective = shares_to_sell * float(trade_price)
                            else:
                                trade_cash_effective = float(trade_cash)

                            realized_pl = (float(trade_price) - avg_price) * shares_to_sell

                            remaining = held - shares_to_sell
                            if remaining <= 1e-12:
                                paper["positions"].pop(trade_ticker, None)
                            else:
                                paper["positions"][trade_ticker] = {
                                    "shares": float(remaining),
                                    "avg_price": float(avg_price),
                                }

                            paper["cash"] = float(paper["cash"]) + float(trade_cash_effective)
                            paper["realized_pl"] = float(paper.get("realized_pl", 0.0)) + float(realized_pl)

                            record_trade(
                                "EXIT",
                                trade_ticker,
                                float(trade_price),
                                float(shares_to_sell),
                                float(trade_cash_effective),
                                realized_pl=float(realized_pl),
                            )
                            record_equity_point(paper, OUTPUTS_DIR)
                            st.success(f"Exited {shares_to_sell:.6f} shares of {trade_ticker}.")
                            st.session_state.activity_feed.insert(
                                0,
                                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} — Exited {trade_ticker}, realized P/L {fmt_money(realized_pl)}.",
                            )

        with mtm_col:
            if st.button("Mark-to-Market"):
                record_equity_point(paper, OUTPUTS_DIR)
                st.info("Recorded a new equity point (no trade).")
                st.session_state.activity_feed.insert(
                    0, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} — Paper portfolio marked to market."
                )

    total, holdings_df = portfolio_value(paper, OUTPUTS_DIR)
    pl = float(total) - float(paper.get("initial_cash", 0.0))
    ret_pct = (pl / float(paper["initial_cash"]) * 100.0) if float(paper.get("initial_cash", 0.0)) > 0 else 0.0

    eq_df = pd.DataFrame(paper.get("equity_curve", []))
    max_dd = 0.0
    if not eq_df.empty and "equity" in eq_df.columns:
        max_dd = compute_drawdown(eq_df["equity"]) * 100.0

    unrealized_total = 0.0
    if not holdings_df.empty and "Unrealized P/L" in holdings_df.columns:
        unrealized_total = pd.to_numeric(holdings_df["Unrealized P/L"], errors="coerce").fillna(0).sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Cash", f"£{float(paper['cash']):.2f}")
    m2.metric("Total Value", f"£{float(total):.2f}")
    m3.metric("P/L", f"£{pl:.2f}", delta=f"{ret_pct:.2f}%")
    m4.metric("Realized P/L", f"£{float(paper.get('realized_pl', 0.0)):.2f}")

    p1, p2 = st.columns(2)
    p1.metric("Unrealized P/L", f"£{float(unrealized_total):.2f}")
    p2.caption(make_portfolio_summary(paper, float(total), holdings_df))

    st.caption(f"Max Drawdown (so far): {max_dd:.2f}%")

    if not eq_df.empty:
        st.write("Equity Curve")
        eq_plot = eq_df.copy()
        eq_plot["equity"] = pd.to_numeric(eq_plot["equity"], errors="coerce")
        eq_plot["cash"] = pd.to_numeric(eq_plot["cash"], errors="coerce")
        eq_plot = eq_plot.dropna(subset=["equity", "cash"])
        if len(eq_plot) >= 2:
            plot_cols = ["equity", "cash"]
            if "time" in eq_plot.columns:
                eq_plot["time"] = pd.to_datetime(eq_plot["time"], errors="coerce")
                eq_plot = eq_plot.dropna(subset=["time"]).set_index("time")
            st.line_chart(eq_plot[plot_cols])
        else:
            st.caption("Add more points (Mark-to-Market) to see the curve.")

    if not holdings_df.empty:
        st.write("Holdings")
        for c in ["Avg Price", "Price", "Market Value", "Unrealized P/L"]:
            if c in holdings_df.columns:
                holdings_df[c] = pd.to_numeric(holdings_df[c], errors="coerce")
        st.dataframe(holdings_df, use_container_width=True, hide_index=True)

        alloc_df = holdings_df.copy()
        alloc_df["Market Value"] = pd.to_numeric(alloc_df["Market Value"], errors="coerce").fillna(0)
        alloc_df = alloc_df[alloc_df["Market Value"] > 0]
        if not alloc_df.empty:
            st.write("Portfolio Allocation")
            alloc_chart = alloc_df[["Ticker", "Market Value"]].set_index("Ticker")
            st.bar_chart(alloc_chart)

        st.download_button(
            "Download Holdings CSV",
            data=holdings_df.to_csv(index=False),
            file_name="paper_holdings.csv",
            mime="text/csv",
        )
    else:
        st.caption("Start your paper portfolio by entering your first ticker.")

    if paper.get("trades"):
        st.write("Recent Trades")
        trades_df = pd.DataFrame(paper["trades"]).tail(25)
        st.dataframe(trades_df, use_container_width=True, hide_index=True)
        st.download_button(
            "Download Paper Trade History CSV",
            data=pd.DataFrame(paper["trades"]).to_csv(index=False),
            file_name="paper_trades.csv",
            mime="text/csv",
        )

    st.divider()

    st.subheader("Recent Activity Feed")
    if st.session_state.activity_feed:
        for item in st.session_state.activity_feed[:12]:
            st.caption(item)
    else:
        st.caption("No recent activity yet.")

    st.divider()

    st.subheader("Full Scan Results")

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1.2, 1.1, 1.1, 1.8])

    with filter_col1:
        signal_filter = st.selectbox("Signal filter", ["All", "BULLISH", "NEUTRAL", "BEARISH"], key="res_signal")
    with filter_col2:
        top_n = st.selectbox("Show rows", [10, 25, 50, 100, "All"], index=1, key="res_topn")
    with filter_col3:
        min_prob_filter = st.slider("Min prob", 0.00, 1.00, 0.00, 0.01, key="res_min_prob")
    with filter_col4:
        search_text = st.text_input("Search ticker", value="", key="res_search")

    display_results = tmp.copy()
    display_results["Prob Color"] = display_results["_prob_color"]
    display_results["Signal"] = display_results["_action_clean"]
    display_results = display_results.sort_values(prob_col, ascending=False)

    if signal_filter != "All":
        display_results = display_results[display_results["Signal"] == signal_filter]

    display_results = display_results[pd.to_numeric(display_results[prob_col], errors="coerce").fillna(-1) >= min_prob_filter]

    if search_text.strip():
        display_results = display_results[
            display_results[ticker_col].astype(str).str.contains(search_text.strip(), case=False, na=False)
        ]

    if top_n != "All":
        display_results = display_results.head(int(top_n))

    keep_cols = []
    for c in [ticker_col, action_col, prob_col, "Sector"]:
        if c in display_results.columns:
            keep_cols.append(c)

    final_cols = keep_cols + ["Prob Color", "Signal"]
    for maybe in ["Latest Close", "Rows (test)"]:
        if maybe in display_results.columns and maybe not in final_cols:
            final_cols.append(maybe)

    if display_results.empty:
        st.info("No results match the current filters.")
    else:
        st.dataframe(display_results[final_cols], use_container_width=True, hide_index=True)

    st.download_button(
        "Download Summary CSV",
        data=display_results.to_csv(index=False),
        file_name="summary_results.csv",
        mime="text/csv",
    )

    st.divider()

    st.subheader("Bullish Consistency Leaderboard")
    if consistency_df.empty:
        st.caption("Run a few scans over time to build leaderboard consistency.")
    else:
        st.dataframe(consistency_df.head(15), use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("Detailed Ticker View")

    selected = st.selectbox(
        "Select a ticker",
        ticker_options,
        key="details_ticker",
    )

    path = os.path.join(OUTPUTS_DIR, f"{selected}_signals.csv")
    if not os.path.exists(path):
        st.error(f"Missing file: {path}. Click **Run Scan** to generate results.")
    else:
        df = pd.read_csv(path)

        detail_action_col = pick_first_existing_column(df, ["action", "signal", "Action"])
        detail_prob_col = pick_first_existing_column(df, ["prob", "Prob Up (5d)", "probability", "Prob"])
        close_col = pick_first_existing_column(df, ["Close", "close"])
        date_col = pick_first_existing_column(df, ["Date", "date", "Datetime", "datetime", "timestamp"])

        col1, col2 = st.columns([2, 1])

        ann_vol = None
        prob_val = None

        with col1:
            if close_col is not None:
                chart_df = df.copy()
                if date_col is not None:
                    chart_df[date_col] = pd.to_datetime(chart_df[date_col], errors="coerce")
                    chart_df = chart_df.dropna(subset=[date_col]).set_index(date_col)
                    st.line_chart(chart_df[close_col])

                    rets = compute_daily_returns(chart_df[close_col])
                    if len(rets) > 5:
                        rolling_vol = rets.rolling(20).std() * math.sqrt(252)
                        rolling_vol = rolling_vol.dropna()
                        if not rolling_vol.empty:
                            st.write("Rolling Volatility (20-day)")
                            st.line_chart(rolling_vol)
                else:
                    st.line_chart(df[close_col])
            else:
                st.warning("No Close column found in ticker CSV.")

        with col2:
            if len(df) == 0:
                st.warning("No rows in ticker CSV.")
            else:
                last = df.iloc[-1]

                action_clean = clean_action_label(last[detail_action_col]) if detail_action_col is not None else "N/A"

                if detail_prob_col is not None:
                    try:
                        prob_val = float(last[detail_prob_col])
                    except Exception:
                        prob_val = None

                latest_close = None
                if close_col is not None:
                    try:
                        latest_close = float(last[close_col])
                    except Exception:
                        latest_close = None

                st.metric("Market Signal", action_clean)
                if prob_val is not None:
                    st.metric("Probability Score (5d)", f"{prob_val:.2f} {prob_emoji(prob_val)}")
                else:
                    st.metric("Probability Score (5d)", "N/A")

                if latest_close is not None:
                    st.metric("Latest Close", f"{latest_close:.2f}")
                else:
                    st.metric("Latest Close", "N/A")

                st.metric("Sector", sector_for_ticker(selected))

                st.write("Risk (volatility)")
                if close_col is not None:
                    rets = compute_daily_returns(df[close_col])
                    if len(rets) > 5:
                        daily_vol = float(rets.std())
                        ann_vol = daily_vol * math.sqrt(252)
                        r_label, r_score = risk_label_from_vol(ann_vol)
                        st.progress(r_score)
                        st.caption(f"{r_label} — est. annual vol: {ann_vol:.2f}")
                    else:
                        st.caption("N/A — not enough data")
                else:
                    st.caption("N/A — no Close column")

                st.write("Confidence (vs threshold)")
                if prob_val is not None:
                    c_label, c_score = confidence_from_prob(prob_val, float(threshold))
                    st.progress(c_score)
                    st.caption(f"{c_label} — distance from threshold: {abs(prob_val - float(threshold)):.2f}")
                else:
                    st.caption("N/A — missing probability")

        if len(df) > 0:
            action_clean = clean_action_label(df.iloc[-1][detail_action_col]) if detail_action_col is not None else "N/A"
            explanation = make_signal_explanation(action_clean, prob_val, float(threshold), ann_vol)
            st.markdown(f"<div class='note-box'><b>Why this signal?</b><br>{html_safe_text(explanation)}</div>", unsafe_allow_html=True)

        st.write("Recent rows")
        st.dataframe(df.tail(25), use_container_width=True, hide_index=True)
        st.download_button(
            "Download Ticker Detail CSV",
            data=df.to_csv(index=False),
            file_name=f"{selected}_signals.csv",
            mime="text/csv",
        )


# =============================
# BACKTEST TAB
# =============================
with tab_backtest:
    st.subheader("📊 Backtest")

    st.caption(
        "This replays your historical signals and simulates a simple rules-based strategy. "
        "It’s for learning and testing only."
    )

    bt_ticker = st.selectbox("Pick a ticker to backtest", ticker_options, key="bt_ticker")
    start_cash = st.number_input("Starting cash (£)", min_value=0.0, step=100.0, value=1000.0, key="bt_cash")
    mode = st.selectbox(
        "Strategy mode",
        ["Aggressive (100%)", "Conservative (50%)", "Hold on Neutral"],
        key="bt_mode",
        help="Aggressive invests 100% of available cash. Conservative invests 50%. Hold on Neutral keeps positions open through neutral signals.",
    )

    bt_path = os.path.join(OUTPUTS_DIR, f"{bt_ticker}_signals.csv")
    if not os.path.exists(bt_path):
        st.error(f"Missing file: {bt_path}. Run Scan to generate it.")
    else:
        bt_df = pd.read_csv(bt_path)

        bt_close_col = pick_first_existing_column(bt_df, ["Close", "close"])
        bt_action_col = pick_first_existing_column(bt_df, ["action", "signal", "Action"])
        bt_prob_col = pick_first_existing_column(bt_df, ["prob", "Prob Up (5d)", "probability", "Prob"])
        bt_date_col = pick_first_existing_column(bt_df, ["Date", "date", "Datetime", "datetime", "timestamp"])

        if bt_close_col is None:
            st.error("Backtest needs a Close column in the ticker signals CSV.")
        elif bt_action_col is None:
            st.error("Backtest needs an action or signal column in the ticker signals CSV.")
        else:
            st.markdown("### Backtest Controls")

            c1, c2, c3 = st.columns(3)
            with c1:
                fee_per_trade = st.number_input("Fee per trade (£)", min_value=0.0, step=0.5, value=0.0, key="bt_fee")
            with c2:
                slippage_pct = st.slider("Slippage (%)", 0.0, 2.0, 0.0, 0.05, key="bt_slip")
            with c3:
                use_prob_filter = st.checkbox("Use min probability filter", value=False, key="bt_use_prob_filter")

            min_prob_to_enter = None
            if use_prob_filter:
                min_prob_to_enter = st.slider("Minimum probability to enter", 0.50, 0.95, 0.60, 0.01, key="bt_min_prob")

            bt_run_df = bt_df.copy()

            if bt_date_col is not None:
                bt_run_df[bt_date_col] = pd.to_datetime(bt_run_df[bt_date_col], errors="coerce")
                bt_run_df = bt_run_df.dropna(subset=[bt_date_col]).sort_values(bt_date_col).reset_index(drop=True)

                if not bt_run_df.empty:
                    min_dt = bt_run_df[bt_date_col].min().date()
                    max_dt = bt_run_df[bt_date_col].max().date()

                    date_range = st.slider(
                        "Backtest date range",
                        min_value=min_dt,
                        max_value=max_dt,
                        value=(min_dt, max_dt),
                        key="bt_date_range",
                    )

                    bt_run_df = bt_run_df[
                        (bt_run_df[bt_date_col].dt.date >= date_range[0])
                        & (bt_run_df[bt_date_col].dt.date <= date_range[1])
                    ].reset_index(drop=True)

            run_bt = st.button("Run Backtest", type="primary")

            if run_bt:
                eq, stats, trade_log = run_backtest_advanced(
                    signals_df=bt_run_df,
                    close_col=bt_close_col,
                    action_col=bt_action_col,
                    start_cash=float(start_cash),
                    mode=str(mode),
                    fee_per_trade=float(fee_per_trade),
                    slippage_pct=float(slippage_pct),
                    prob_col=bt_prob_col,
                    min_prob_to_enter=min_prob_to_enter,
                )

                st.session_state["bt_eq"] = eq
                st.session_state["bt_stats"] = stats
                st.session_state["bt_trade_log"] = trade_log
                st.session_state["bt_plot_df"] = bt_run_df
                st.session_state["bt_plot_date_col"] = bt_date_col
                st.session_state["bt_plot_close_col"] = bt_close_col
                st.session_state.activity_feed.insert(
                    0, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} — Backtest run for {bt_ticker}."
                )

            eq = st.session_state.get("bt_eq")
            stats = st.session_state.get("bt_stats")
            trade_log = st.session_state.get("bt_trade_log")
            bt_plot_df = st.session_state.get("bt_plot_df")
            bt_plot_date_col_saved = st.session_state.get("bt_plot_date_col")
            bt_plot_close_col_saved = st.session_state.get("bt_plot_close_col")

            if eq is not None and stats is not None and not ("error" in stats):
                st.markdown(
                    f"<div class='note-box'><b>Performance Summary</b><br>{html_safe_text(make_backtest_summary(stats))}</div>",
                    unsafe_allow_html=True,
                )

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Start", f"£{stats['start']:.2f}")
                c2.metric("End", f"£{stats['end']:.2f}")
                c3.metric("Return", f"{stats['return_pct']:.2f}%")
                c4.metric("Trades", int(stats["trades"]))

                c5, c6, c7, c8 = st.columns(4)
                c5.metric("Closed Trades", int(stats["closed_trades"]))
                c6.metric("Win Rate", f"{stats['win_rate']:.2f}%")
                c7.metric("Max Drawdown", f"{stats['max_drawdown_pct']:.2f}%")
                c8.metric("Buy & Hold", f"£{stats['buy_hold_end']:.2f}")

                c9, c10, c11, c12 = st.columns(4)
                best_trade = stats["best_trade_pct"]
                worst_trade = stats["worst_trade_pct"]
                avg_trade = stats["avg_trade_pct"]
                sharpe = stats["sharpe"]

                c9.metric("Best Trade", f"{best_trade:.2f}%" if best_trade is not None else "N/A")
                c10.metric("Worst Trade", f"{worst_trade:.2f}%" if worst_trade is not None else "N/A")
                c11.metric("Avg Trade", f"{avg_trade:.2f}%" if avg_trade is not None else "N/A")
                c12.metric("Sharpe", f"{sharpe:.2f}" if sharpe is not None else "N/A")

                c13, c14, c15, c16 = st.columns(4)
                c13.metric("Profit Factor", f"{stats['profit_factor']:.2f}" if stats["profit_factor"] is not None else "N/A")
                c14.metric("Expectancy", f"{stats['expectancy_pct']:.2f}%" if stats["expectancy_pct"] is not None else "N/A")
                c15.metric("Time in Market", f"{stats['time_in_market_pct']:.2f}%")
                c16.metric("Fees Paid", f"£{stats['fees_paid']:.2f}")

                c17, c18, c19, c20 = st.columns(4)
                c17.metric("Avg Win", f"{stats['avg_win_pct']:.2f}%" if stats["avg_win_pct"] is not None else "N/A")
                c18.metric("Avg Loss", f"{stats['avg_loss_pct']:.2f}%" if stats["avg_loss_pct"] is not None else "N/A")
                c19.metric("Best Win Streak", int(stats["best_win_streak"]))
                c20.metric("Worst Loss Streak", int(stats["worst_loss_streak"]))

                c21, c22, c23, c24 = st.columns(4)
                c21.metric("Median Trade", f"{stats['median_trade_pct']:.2f}%" if stats["median_trade_pct"] is not None else "N/A")
                c22.metric("Longest Trade", str(stats["longest_trade"]) if stats["longest_trade"] is not None else "N/A")
                c23.metric("Current Strategy State", stats["current_state"])
                c24.metric("vs Buy & Hold", f"{(stats['return_pct'] - stats['buy_hold_return_pct']):.2f}%")

                st.divider()

                st.subheader("Equity Curve")
                st.line_chart(eq[["equity"]])

                st.subheader("Drawdown Curve")
                st.line_chart(eq[["drawdown"]])

                st.subheader("Strategy vs Buy & Hold")
                comparison_df = eq.copy()
                comparison_df["strategy_growth"] = comparison_df["equity"] / float(stats["start"])
                if bt_plot_df is not None and bt_plot_close_col_saved in bt_plot_df.columns and len(bt_plot_df) == len(comparison_df):
                    base_price = float(pd.to_numeric(bt_plot_df[bt_plot_close_col_saved], errors="coerce").dropna().iloc[0])
                    comparison_df["buy_hold_growth"] = pd.to_numeric(bt_plot_df[bt_plot_close_col_saved], errors="coerce") / base_price
                    st.line_chart(comparison_df[["strategy_growth", "buy_hold_growth"]])

                st.subheader("Price + Entry / Exit Activity")
                if bt_plot_df is not None and bt_plot_close_col_saved in bt_plot_df.columns:
                    price_debug = bt_plot_df.copy().reset_index(drop=True)
                    price_debug["ENTER"] = None
                    price_debug["EXIT"] = None

                    if trade_log is not None and not trade_log.empty and "Step" in trade_log.columns:
                        for _, row in trade_log.iterrows():
                            step = int(row["Step"])
                            if 0 <= step < len(price_debug):
                                if str(row["Type"]).startswith("ENTER"):
                                    price_debug.loc[step, "ENTER"] = price_debug.loc[step, bt_plot_close_col_saved]
                                if str(row["Type"]).startswith("EXIT"):
                                    price_debug.loc[step, "EXIT"] = price_debug.loc[step, bt_plot_close_col_saved]

                    cols_to_plot = [bt_plot_close_col_saved]
                    if price_debug["ENTER"].notna().any():
                        cols_to_plot.append("ENTER")
                    if price_debug["EXIT"].notna().any():
                        cols_to_plot.append("EXIT")

                    if bt_plot_date_col_saved is not None and bt_plot_date_col_saved in price_debug.columns:
                        price_debug[bt_plot_date_col_saved] = pd.to_datetime(price_debug[bt_plot_date_col_saved], errors="coerce")
                        price_debug = price_debug.dropna(subset=[bt_plot_date_col_saved]).set_index(bt_plot_date_col_saved)

                    st.line_chart(price_debug[cols_to_plot])

                st.divider()

                st.subheader("Trade Log")
                if trade_log is not None and not trade_log.empty:
                    st.dataframe(trade_log, use_container_width=True, hide_index=True)
                    st.download_button(
                        "Download Trade Log CSV",
                        data=trade_log.to_csv(index=False),
                        file_name=f"{bt_ticker}_trade_log.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("This strategy stayed inactive under the current settings.")

                st.divider()

                st.subheader("Backtest Rows (debug)")
                st.dataframe(eq.tail(25), use_container_width=True, hide_index=True)
                st.download_button(
                    "Download Backtest Rows CSV",
                    data=eq.to_csv(index=False),
                    file_name=f"{bt_ticker}_backtest_rows.csv",
                    mime="text/csv",
                )

            elif stats is not None and "error" in stats:
                st.error(stats.get("error", "Backtest failed."))


# =============================
# STOCK INFO / NEWS TAB
# =============================
with tab_info:
    st.subheader("📰 Stock Info & News")
    st.caption("A quick research tab for company details, trend snapshots, and recent headlines.")

    if yf is None:
        st.warning("Install yfinance to enable this tab: `pip install yfinance`")
    else:
        universe = tuple(tickers if tickers else ticker_options)

        st.markdown("### Market Snapshot")
        snapshot_df = market_snapshot(universe)

        if snapshot_df.empty:
            st.info("No market snapshot data could be loaded right now.")
        else:
            up_1d = int((pd.to_numeric(snapshot_df["1D %"], errors="coerce") > 0).sum())
            down_1d = int((pd.to_numeric(snapshot_df["1D %"], errors="coerce") < 0).sum())
            avg_1m = float(pd.to_numeric(snapshot_df["1M %"], errors="coerce").dropna().mean()) if not snapshot_df.empty else float("nan")
            uptrend_count = int(snapshot_df["Trend"].astype(str).str.contains("Uptrend", case=False, na=False).sum())

            g1, g2, g3, g4 = st.columns(4)
            g1.metric("Names Up Today", up_1d)
            g2.metric("Names Down Today", down_1d)
            g3.metric("Avg 1M Return", f"{avg_1m:.2f}%" if not math.isnan(avg_1m) else "N/A")
            g4.metric("Uptrend Count", uptrend_count)

            st.write("Top Movers Today")
            top_movers = snapshot_df.sort_values("1D %", ascending=False).head(10).reset_index(drop=True)
            st.dataframe(top_movers, use_container_width=True, hide_index=True)

            c_left, c_right = st.columns(2)
            with c_left:
                st.write("Strongest 3-Month Trends")
                strong_3m = snapshot_df.sort_values("3M %", ascending=False).head(10).reset_index(drop=True)
                st.dataframe(strong_3m, use_container_width=True, hide_index=True)
            with c_right:
                st.write("Weakest 3-Month Trends")
                weak_3m = snapshot_df.sort_values("3M %", ascending=True).head(10).reset_index(drop=True)
                st.dataframe(weak_3m, use_container_width=True, hide_index=True)

            st.write("Sector Trend Snapshot")
            sector_trend_df = (
                snapshot_df.groupby("Sector")
                .agg(
                    Count=("Ticker", "count"),
                    Avg_1D=("1D %", "mean"),
                    Avg_1M=("1M %", "mean"),
                    Avg_3M=("3M %", "mean"),
                )
                .reset_index()
                .sort_values("Avg_3M", ascending=False)
            )
            st.dataframe(sector_trend_df, use_container_width=True, hide_index=True)

            st.download_button(
                "Download Market Snapshot CSV",
                data=snapshot_df.to_csv(index=False),
                file_name="market_snapshot.csv",
                mime="text/csv",
            )

        st.divider()

        st.markdown("### Company Research")
        info_ticker = st.selectbox("Pick a ticker for company info", list(universe), key="info_ticker")
        info = yf_info_for_ticker(info_ticker)
        hist = yf_history_for_ticker(info_ticker, period="1y", interval="1d")
        news_items = yf_news_for_ticker(info_ticker)

        left, right = st.columns([2, 1])

        with left:
            if hist.empty or "Close" not in hist.columns:
                st.warning("No historical data available for this ticker right now.")
            else:
                hist["Date"] = pd.to_datetime(hist.iloc[:, 0], errors="coerce")
                hist["Close"] = pd.to_numeric(hist["Close"], errors="coerce")
                hist = hist.dropna(subset=["Date", "Close"]).sort_values("Date").reset_index(drop=True)

                hist["MA20"] = hist["Close"].rolling(20).mean()
                hist["MA50"] = hist["Close"].rolling(50).mean()

                chart_df = hist[["Date", "Close", "MA20", "MA50"]].dropna(how="all")
                chart_df = chart_df.set_index("Date")
                st.line_chart(chart_df)

                if len(hist) >= 2:
                    latest = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2])
                    perf_1d = ((latest / prev) - 1.0) * 100.0 if prev > 0 else None
                else:
                    latest = None
                    perf_1d = None

                perf_1m = None
                perf_3m = None
                perf_6m = None

                if len(hist) >= 21:
                    perf_1m = ((float(hist["Close"].iloc[-1]) / float(hist["Close"].iloc[-21])) - 1.0) * 100.0
                if len(hist) >= 63:
                    perf_3m = ((float(hist["Close"].iloc[-1]) / float(hist["Close"].iloc[-63])) - 1.0) * 100.0
                if len(hist) >= 126:
                    perf_6m = ((float(hist["Close"].iloc[-1]) / float(hist["Close"].iloc[-126])) - 1.0) * 100.0

                rc = compute_daily_returns(hist["Close"])
                ann_vol = float(rc.std() * math.sqrt(252)) if len(rc) > 5 else None

                trend_text = classify_trend(perf_3m if perf_3m is not None else perf_1m)

                st.markdown(
                    f"<div class='note-box'><b>Trend Read:</b><br>"
                    f"{info_ticker} currently looks like a <b>{html_safe_text(trend_text)}</b>. "
                    f"1M return: <b>{'N/A' if perf_1m is None else f'{perf_1m:.2f}%'} </b>, "
                    f"3M return: <b>{'N/A' if perf_3m is None else f'{perf_3m:.2f}%'} </b>, "
                    f"6M return: <b>{'N/A' if perf_6m is None else f'{perf_6m:.2f}%'} </b>. "
                    f"{'Volatility looks elevated.' if ann_vol is not None and ann_vol >= 0.35 else 'Volatility looks moderate or calmer.' if ann_vol is not None else 'Volatility read is limited due to thin data.'}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        with right:
            long_name = info.get("longName") or info.get("shortName") or info_ticker
            sector = info.get("sector") or sector_for_ticker(info_ticker)
            industry = info.get("industry")
            market_cap = info.get("marketCap")
            pe = info.get("trailingPE")
            forward_pe = info.get("forwardPE")
            beta = info.get("beta")
            high_52 = info.get("fiftyTwoWeekHigh")
            low_52 = info.get("fiftyTwoWeekLow")
            dividend_yield = info.get("dividendYield")

            st.metric("Company", long_name)
            st.metric("Sector", sector if sector else "N/A")
            st.metric("Industry", industry if industry else "N/A")
            st.metric("Market Cap", fmt_big_num(market_cap))
            st.metric("Trailing P/E", fmt_num(pe))
            st.metric("Forward P/E", fmt_num(forward_pe))
            st.metric("Beta", fmt_num(beta))
            st.metric("52W High", fmt_num(high_52))
            st.metric("52W Low", fmt_num(low_52))
            st.metric("Dividend Yield", f"{float(dividend_yield) * 100:.2f}%" if dividend_yield is not None else "N/A")

        summary_text = info.get("longBusinessSummary")
        if summary_text:
            st.write("Company Overview")
            st.write(summary_text)

        st.divider()

        st.markdown("### Recent Headlines")
        if not news_items:
            st.info("No recent ticker news could be loaded right now.")
        else:
            for item in news_items[:10]:
                title = item.get("title") or "Untitled"
                publisher = item.get("publisher") or "Unknown source"
                link = item.get("link")
                summary = item.get("summary") or item.get("snippet") or ""

                with st.expander(title):
                    st.write(f"Source: {publisher}")
                    if summary:
                        st.write(summary)
                    if link:
                        st.markdown(f"[Open article]({link})")

        st.divider()

        st.markdown("### Global Watchlist News Feed")
        news_feed_tickers = list(universe)[:8]
        news_rows = []
        for t in news_feed_tickers:
            for item in yf_news_for_ticker(t)[:2]:
                news_rows.append(
                    {
                        "Ticker": t,
                        "Title": item.get("title"),
                        "Source": item.get("publisher"),
                        "Link": item.get("link"),
                    }
                )

        if news_rows:
            news_df = pd.DataFrame(news_rows).drop_duplicates(subset=["Ticker", "Title"]).reset_index(drop=True)
            st.dataframe(news_df[["Ticker", "Title", "Source"]], use_container_width=True, hide_index=True)
            st.download_button(
                "Download News Feed CSV",
                data=news_df.to_csv(index=False),
                file_name="watchlist_news.csv",
                mime="text/csv",
            )
        else:
            st.info("No watchlist news could be loaded right now.")
