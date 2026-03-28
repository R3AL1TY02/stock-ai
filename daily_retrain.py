# daily_retrain.py
from __future__ import annotations

import os
from datetime import datetime

from run_scan import scan_tickers

# Change these tickers to whatever you want scanned daily
TICKERS = [ "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "LMT", "XOM", "JPM", "JNJ", "CAT"]

# BUY threshold (same idea as your dashboard slider)
THRESHOLD = 0.60


def main() -> None:
    os.makedirs("outputs", exist_ok=True)

    summary = scan_tickers(TICKERS, threshold=THRESHOLD)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("outputs/last_run.txt", "w", encoding="utf-8") as f:
        f.write(f"Last daily retrain: {now}\n")
        f.write(f"Tickers: {', '.join(TICKERS)}\n")
        f.write(f"Threshold: {THRESHOLD}\n")

    print("Daily retrain complete.")
    print(summary)


if __name__ == "__main__":
    main()
