"""Download real daily prices from Alpaca's market data API into data/raw/prices.csv.

Alpaca's market data API is free and read-only, and uses the same keys as the
paper trading account.

Setup (once): copy .env.example to .env, fill in your paper keys, then export them:
    set -a; source .env; set +a

Run from the repo root:
    python -m backtesting.alpaca_data                          # XOM + XLE, config test window
    python -m backtesting.alpaca_data --tickers XOM CVX XLE --start 2018-01-01 --end 2024-12-31

Then backtest on the real prices:
    python -m backtesting.engine --data raw

The file has the same layout as data/sample/prices.csv (a date column, then one
closing-price column per ticker), so signals and the engine work unchanged.

Prices are split- and dividend-adjusted (Adjustment.ALL).
"""

import argparse
import os

import pandas as pd

from backtesting import config

DEFAULT_TICKERS = ["XOM", config.BENCHMARK]


def bars_to_wide(bars: pd.DataFrame) -> pd.DataFrame:
    """Turn Alpaca's bar table into one row per date and one close column per ticker.

    Alpaca returns one row per (symbol, timestamp), for example
        ("XOM", 2019-01-02 05:00 UTC) close 69.69
        ("XLE", 2019-01-02 05:00 UTC) close 58.10
    and we return
        date        XOM    XLE
        2019-01-02  69.69  58.10

    Timestamps are UTC, so convert to New York time before taking the date,
    otherwise a bar can land on the wrong trading day.
    """
    closes = bars["close"].unstack(level="symbol")
    timestamps = pd.DatetimeIndex(closes.index)
    if timestamps.tz is not None:
        timestamps = timestamps.tz_convert("America/New_York").tz_localize(None)
    closes.index = timestamps.normalize()
    closes.index.name = "date"
    closes.columns.name = None
    return closes.sort_index()


def download_prices(tickers: list[str], start: str, end: str, feed: str = "sip") -> pd.DataFrame:
    """Download adjusted daily closing prices for tickers between start and end (inclusive).

    feed: "sip" is the full US market (all exchanges combined); on the free plan
    it works for any data older than 15 minutes, which is fine for backtests.
    "iex" uses one exchange only; try it if your account rejects "sip".
    """
    key = os.environ.get("ALPACA_API_KEY")
    secret = os.environ.get("ALPACA_SECRET_KEY")
    if not key or not secret:
        raise RuntimeError(
            "ALPACA_API_KEY and ALPACA_SECRET_KEY are not set. Copy .env.example to .env, "
            "fill in your paper keys, then run: set -a; source .env; set +a"
        )

    from alpaca.data.enums import Adjustment, DataFeed
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    client = StockHistoricalDataClient(key, secret)
    request = StockBarsRequest(
        symbol_or_symbols=tickers,
        timeframe=TimeFrame.Day,
        start=pd.Timestamp(start),
        end=pd.Timestamp(end) + pd.Timedelta(days=1),  # make the end date inclusive
        adjustment=Adjustment.ALL,
        feed=DataFeed(feed),
    )
    bars = client.get_stock_bars(request).df
    if bars.empty:
        raise RuntimeError(f"Alpaca returned no bars for {tickers} between {start} and {end}")

    prices = bars_to_wide(bars)
    missing = [t for t in tickers if t not in prices.columns]
    if missing:
        raise RuntimeError(f"No data returned for {missing}. Check the ticker spelling.")
    return prices[tickers]


def main() -> None:
    parser = argparse.ArgumentParser(description="Download daily prices from Alpaca into data/raw/prices.csv")
    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS, help="for example: XOM CVX XLE")
    parser.add_argument("--start", default=config.TEST_START, help="first date, YYYY-MM-DD")
    parser.add_argument("--end", default=config.TEST_END, help="last date, YYYY-MM-DD")
    parser.add_argument("--feed", default="sip", choices=["sip", "iex"])
    args = parser.parse_args()

    prices = download_prices(args.tickers, args.start, args.end, args.feed)

    # A day where any ticker has no price cannot be backtested, so drop it and say so.
    gaps = prices[prices.isna().any(axis=1)]
    if not gaps.empty:
        print(f"Dropping {len(gaps)} days with a missing price, for example {gaps.index[0].date()}")
        prices = prices.dropna()

    config.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = config.RAW_DATA_DIR / "prices.csv"
    prices.to_csv(out, date_format="%Y-%m-%d")
    print(f"Wrote {len(prices)} days x {len(prices.columns)} tickers "
          f"({prices.index[0].date()} to {prices.index[-1].date()}) to {out}")


if __name__ == "__main__":
    main()
