import pandas as pd

def project_cash_in_days(
    price_df: pd.DataFrame,
    close_col: str,
    cash_amount: float,
    days: int = 5,
    lookback: int = 20
):
    """
    Uses average daily return from the last `lookback` rows of Close to project forward `days`.
    Returns dict or None if not enough data.
    """
    if price_df is None or len(price_df) < (lookback + 1):
        return None

    if close_col is None or close_col not in price_df.columns:
        return None

    df = price_df.copy()

    df[close_col] = pd.to_numeric(df[close_col], errors="coerce")
    df = df.dropna(subset=[close_col])

    if len(df) < (lookback + 1):
        return None

    df["daily_return"] = df[close_col].pct_change()
    recent = df["daily_return"].dropna().tail(lookback)

    if recent.empty:
        return None

    avg_daily_return = recent.mean()

    projected_value = cash_amount * ((1 + avg_daily_return) ** days)
    profit = projected_value - cash_amount
    percent_return = (profit / cash_amount) * 100

    return {
        "projected_value": round(projected_value, 2),
        "profit": round(profit, 2),
        "percent_return": round(percent_return, 2),
        "avg_daily_return": round(avg_daily_return * 100, 3),
        "lookback_used": int(lookback),
        "days": int(days),
    }
