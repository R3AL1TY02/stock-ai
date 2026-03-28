import yfinance as yf
import pandas as pd

def fetch_data(ticker, period="5y"):
    df = yf.download(ticker, period=period)
    df.dropna(inplace=True)
    return df
