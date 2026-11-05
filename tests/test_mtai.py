import pandas as pd
from backtesting import config
from backtesting.mtai_data import POLYGONS, COMPS, MIN_COMPS, parse_mtai_csv
import pytest

def check_mtai(df):
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.index.is_monotonic_increasing and df.index.is_unique
    assert list(df.columns) == POLYGONS
    assert df["facility"].notna().all()
    assert (df[COMPS].notna().sum(axis=1) >= MIN_COMPS).all()
    assert not ((df < -40) | (df > 80)).any().any(), "temps out of plausible range"

def test_sample_mtai():
    path = config.RAW_DATA_DIR.parent / "sample" / "mtai.csv"
    check_mtai(pd.read_csv(path, index_col="date", parse_dates=True))

def test_parse_docstring_example():
    text = """system:index,date,name,temp_c,valid,CLOUD_COVER
1_LC08_018036_20180102_0..0,2018-01-02,facility,6.41,0.74,12.3
1_LC08_018036_20180102_0..1,2018-01-02,comp1,2.80,0.44,12.3
1_LC08_018036_20180102_0..3,2018-01-02,comp3,4.55,1.00,12.3
1_LC08_018036_20180118_0..0,2018-01-18,facility,9.12,0.91,4.0
1_LC08_018036_20180118_0..1,2018-01-18,comp1,5.30,0.88,4.0
1_LC08_018036_20180118_0..2,2018-01-18,comp2,5.95,0.97,4.0
1_LC08_018036_20180118_0..3,2018-01-18,comp3,4.71,0.63,4.0
1_LC08_018036_20180203_0..0,2018-02-03,facility,-3.20,0.95,63.0
"""
    frame, counts = parse_mtai_csv(text)
    assert list(frame.index.strftime("%Y-%m-%d")) == ["2018-01-18"]
    assert counts == {"cloudy_scenes": 1, "low_valid_readings": 1, "dropped_dates": 2}
    check_mtai(frame)

def test_raw_mtai():
    path = config.RAW_DATA_DIR / "mtai.csv"
    if not path.exists():
        pytest.skip("no raw MTAI data; run python -m backtesting.mtai_data")
    check_mtai(pd.read_csv(path, index_col="date", parse_dates=True))