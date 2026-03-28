import pandas as pd

from ingestion.fetch_data import fetch_data
from features.indicators import add_indicators
from models.ml_model import train_model
from strategies.strategy import generate_signal
from backtesting.backtest import backtest_signals

tickers = ["AAPL", "MSFT", "GOOGL"]

for ticker in tickers:
    df = fetch_data(ticker)
    df = add_indicators(df)

    # Train on first 80% of history, test signals on last 20%
    split = int(len(df) * 0.8)
    train_df = df.iloc[:split].copy()
    test_df = df.iloc[split:].copy()

    model = train_model(train_df)

    signals = []
    probs = []

    feature_cols = ["rsi", "macd", "sma_50", "sma_200"]

    for i in range(len(test_df)):
        row = test_df.iloc[i][feature_cols]
        signal, prob = generate_signal(model, row, threshold=0.6)
        signals.append(signal)
        probs.append(prob)

    test_df["signal"] = signals
    test_df["prob"] = probs
    test_df.to_csv(f"outputs/{ticker}_signals.csv", index=False)


    stats = backtest_signals(test_df, initial_cash=10_000.0)

    print("\n", "=" * 60)
    print(ticker)
    print(f"Final equity: £{stats['final_equity']:.2f}")
    print(f"Total return: {stats['total_return']*100:.2f}%")
    print(f"Max drawdown: {stats['max_drawdown']*100:.2f}%")
    print("Last signal:", test_df['signal'].iloc[-1], f"prob={test_df['prob'].iloc[-1]:.2f}")
