"""The Alpaca downloader's reshaping and the raw-data loader. No internet or keys needed."""

import pandas as pd
import pytest

from backtesting import alpaca_data, config, engine


def fake_alpaca_bars():
    # Same shape Alpaca returns: one row per (symbol, timestamp), timestamps in UTC.
    # 05:00 UTC is midnight in New York in winter.
    index = pd.MultiIndex.from_tuples(
        [
            ("XLE", pd.Timestamp("2019-01-02 05:00", tz="UTC")),
            ("XLE", pd.Timestamp("2019-01-03 05:00", tz="UTC")),
            ("XOM", pd.Timestamp("2019-01-02 05:00", tz="UTC")),
            ("XOM", pd.Timestamp("2019-01-03 05:00", tz="UTC")),
        ],
        names=["symbol", "timestamp"],
    )
    return pd.DataFrame({"open": 1.0, "close": [58.1, 57.2, 69.7, 68.1]}, index=index)


def test_bars_become_one_column_per_ticker():
    wide = alpaca_data.bars_to_wide(fake_alpaca_bars())
    assert list(wide.index) == [pd.Timestamp("2019-01-02"), pd.Timestamp("2019-01-03")]
    assert wide.loc["2019-01-02", "XOM"] == 69.7
    assert wide.loc["2019-01-03", "XLE"] == 57.2
    assert wide.index.tz is None, "dates must be plain New York dates, not UTC timestamps"


def test_download_without_keys_gives_clear_error(monkeypatch):
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ALPACA_API_KEY"):
        alpaca_data.download_prices(["XOM", "XLE"], "2019-01-01", "2019-12-31")


def test_raw_loader_reads_downloaded_prices(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RAW_DATA_DIR", tmp_path)
    alpaca_data.bars_to_wide(fake_alpaca_bars()).to_csv(tmp_path / "prices.csv", date_format="%Y-%m-%d")
    data = engine.load_data("raw")
    assert set(data) == {"prices"}
    assert list(data["prices"].columns) == ["XLE", "XOM"]
    assert isinstance(data["prices"].index, pd.DatetimeIndex)


def test_raw_loader_explains_empty_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RAW_DATA_DIR", tmp_path)
    with pytest.raises(FileNotFoundError, match="alpaca_data"):
        engine.load_data("raw")
