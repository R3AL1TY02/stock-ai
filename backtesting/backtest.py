import numpy as np

def backtest_signals(df, initial_cash=10_000.0):
    """
    Simple backtest:
    - BUY => invest all cash at close
    - HOLD => do nothing
    - Always stays invested once bought (basic, no SELL yet)
    Returns performance stats.
    """
    cash = float(initial_cash)
    shares = 0.0

    equity_curve = []

    for i in range(len(df)):
        price = float(df["Close"].iloc[i])
        signal = df["signal"].iloc[i]

        if signal == "BUY" and cash > 0:
            shares = cash / price
            cash = 0.0

        equity = cash + shares * price
        equity_curve.append(equity)

    equity_curve = np.array(equity_curve, dtype=float)

    total_return = (equity_curve[-1] / initial_cash) - 1.0
    peak = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve / peak) - 1.0
    max_drawdown = float(drawdown.min())

    return {
        "final_equity": float(equity_curve[-1]),
        "total_return": float(total_return),
        "max_drawdown": float(max_drawdown),
        "equity_curve": equity_curve,
    }
