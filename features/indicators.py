import pandas as pd
import ta

def _to_series(x) -> pd.Series:
    """
    Ensure we pass a 1-D pandas Series to ta indicators.
    Sometimes df["Close"] can be a 2-D (N, 1) object depending on data source/version.
    """
    # If it's a DataFrame with one column, squeeze to Series
    if hasattr(x, "ndim") and x.ndim == 2:
        return x.squeeze("columns")
    return x

def add_indicators(df):
    close = _to_series(df["Close"])

    df["rsi"] = ta.momentum.RSIIndicator(close=close).rsi()
    df["macd"] = ta.trend.MACD(close=close).macd()
    df["sma_50"] = close.rolling(50).mean()
    df["sma_200"] = close.rolling(200).mean()

    df.dropna(inplace=True)
    return df
