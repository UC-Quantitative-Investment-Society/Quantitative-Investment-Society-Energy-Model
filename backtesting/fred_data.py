"""Download daily WTI crude and VIX closes from FRED into data/raw/.

FRED's CSV endpoint is public: no API key or account needed.

Run from the repo root:
    python -m backtesting.fred_data                                       # WTI + VIX, config test window
    python -m backtesting.fred_data --series VIXCLS --start 2018-01-01 --end 2024-12-31

Each series is written to its own file, in the same layout as data/sample/:
    DCOILWTICO -> data/raw/wti.csv  (columns date, wti)
    VIXCLS     -> data/raw/vix.csv  (columns date, vix)

so a signal reads data["wti"]["wti"] or data["vix"]["vix"] on both sample and raw data.
Then backtest on the real data:
    python -m backtesting.engine --data raw

FRED leaves the value missing on days with no close (exchange holidays), for example
2019-01-21 in VIXCLS. Those rows are dropped and counted.

WTI settled at -36.98 on 2020-04-20. The row is kept because it is the real print,
so a signal that takes logs or ratios of WTI must handle a non-positive price.
"""

import argparse
import io
import urllib.request

import pandas as pd

from backtesting import config

# FRED series id -> name of the file in data/raw/ and of its value column.
SERIES = {"DCOILWTICO": "wti", "VIXCLS": "vix"}
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"


def parse_fred_csv(text: str, column: str, start: str | None = None, end: str | None = None) -> tuple[pd.DataFrame, int]:
    """Turn FRED's CSV text into a date-indexed frame with one float column.

    FRED returns
        observation_date,VIXCLS
        2019-01-18,17.80
        2019-01-21,.
        2019-01-22,20.80
    and parse_fred_csv(text, "vix") returns (frame, 1), where frame is
        date        vix
        2019-01-18  17.80
        2019-01-22  20.80
    and 1 is the number of missing rows dropped. FRED writes a missing value as "."
    in older files and as an empty field today; both count as missing.

    start and end (inclusive, YYYY-MM-DD) clip the dates before counting, so the
    count only covers the window that is kept.
    """
    raw = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    dates = pd.to_datetime(raw.iloc[:, 0])
    values = raw.iloc[:, 1].str.strip()

    in_window = pd.Series(True, index=raw.index)
    if start is not None:
        in_window &= dates >= pd.Timestamp(start)
    if end is not None:
        in_window &= dates <= pd.Timestamp(end)
    missing = values.isin([".", ""])
    keep = in_window & ~missing

    frame = pd.DataFrame(
        {column: values[keep].astype(float).to_numpy()},
        index=pd.DatetimeIndex(dates[keep], name="date"),
    )
    return frame.sort_index(), int((in_window & missing).sum())


def fetch_csv(series_id: str) -> str:
    """Download the full history of one FRED series as CSV text."""
    request = urllib.request.Request(
        FRED_CSV_URL.format(series_id=series_id), headers={"User-Agent": "qis-energy-model"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def download_series(series_id: str, start: str, end: str) -> tuple[pd.DataFrame, int]:
    """Download one series between start and end (inclusive).

    Returns the frame and the number of missing days dropped in that window.
    Example: download_series("VIXCLS", "2019-01-01", "2019-12-31") gives a frame
    with one "vix" column, 252 rows, and 9 dropped holidays.
    """
    frame, dropped = parse_fred_csv(fetch_csv(series_id), SERIES[series_id], start, end)
    if frame.empty:
        raise RuntimeError(f"FRED returned no {series_id} values between {start} and {end}")
    return frame, dropped


def main() -> None:
    parser = argparse.ArgumentParser(description="Download daily series from FRED into data/raw/")
    parser.add_argument("--series", nargs="+", default=list(SERIES), choices=list(SERIES),
                        help="FRED series ids, for example: VIXCLS")
    parser.add_argument("--start", default=config.TEST_START, help="first date, YYYY-MM-DD")
    parser.add_argument("--end", default=config.TEST_END, help="last date, YYYY-MM-DD")
    args = parser.parse_args()

    config.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for series_id in args.series:
        frame, dropped = download_series(series_id, args.start, args.end)
        if dropped:
            print(f"{series_id}: dropping {dropped} days with no value (holidays)")
        out = config.RAW_DATA_DIR / f"{SERIES[series_id]}.csv"
        frame.to_csv(out, date_format="%Y-%m-%d")
        print(f"Wrote {len(frame)} days of {series_id} "
              f"({frame.index[0].date()} to {frame.index[-1].date()}) to {out}")


if __name__ == "__main__":
    main()
