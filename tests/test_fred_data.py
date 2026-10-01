"""The FRED parser and the WTI / VIX sample data. No internet needed."""

import pandas as pd

from backtesting import engine, fred_data

# Same layout FRED returns. 2019-01-21 uses the old "." marker, 2019-01-23 the current empty field.
FRED_CSV = """observation_date,VIXCLS
2019-01-18,17.80
2019-01-21,.
2019-01-22,20.80
2019-01-23,
2019-01-24,18.89
"""


def test_parse_drops_missing_days_and_names_the_column():
    frame, dropped = fred_data.parse_fred_csv(FRED_CSV, "vix")
    assert dropped == 2
    assert list(frame.columns) == ["vix"]
    assert isinstance(frame.index, pd.DatetimeIndex) and frame.index.name == "date"
    assert list(frame.index) == [pd.Timestamp("2019-01-18"), pd.Timestamp("2019-01-22"), pd.Timestamp("2019-01-24")]
    assert frame.loc["2019-01-22", "vix"] == 20.80


def test_parse_counts_missing_days_inside_the_window_only():
    frame, dropped = fred_data.parse_fred_csv(FRED_CSV, "vix", start="2019-01-22", end="2019-01-24")
    assert dropped == 1  # 2019-01-23; 2019-01-21 is outside the window
    assert len(frame) == 2


def test_sample_data_has_wti_and_vix():
    data = engine.load_data("sample")
    assert list(data["wti"].columns) == ["wti"]
    assert list(data["vix"].columns) == ["vix"]
    # Same trading days as the prices, so a signal can combine them without gaps.
    assert data["wti"].index.equals(data["prices"].index)
    assert data["vix"].index.equals(data["prices"].index)
