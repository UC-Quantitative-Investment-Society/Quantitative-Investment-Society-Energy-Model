"""Run from repo root: python -m pytest tests/test_mainline_squeeze.py -q."""
import pandas as pd
import pytest
from signals.mainline_squeeze import compute_signal


def table(months, pcts, dates=None):
    if dates is None:
        dates = [(pd.Period(m, freq='M').start_time - pd.Timedelta(days=10)).strftime('%Y-%m-%d') for m in months]
    return {'apportionment': pd.DataFrame({'delivery_month': months,
        'heavy_apportionment_pct': pcts}, index=pd.to_datetime(dates))}


def test_november_2026_trigger_and_first_month_not_triggered():
    fired = compute_signal(table(['2026-10', '2026-11'], [4, 16],
                                 ['2026-09-20', '2026-10-21']))
    assert fired.tolist() == [False, True]
    assert fired.index[-1] == pd.Timestamp('2026-10-21')
    assert fired.dtype == bool


def test_exact_thresholds_fire():
    assert compute_signal(table(['2026-01', '2026-02'], [5, 10])).tolist() == [False, True]


def test_jump_without_level_fails():
    assert compute_signal(table(['2026-01', '2026-02'], [1, 8])).tolist() == [False, False]


def test_level_without_jump_fails():
    assert compute_signal(table(['2026-01', '2026-02'], [11, 14])).tolist() == [False, False]


def test_missing_previous_month_is_not_substituted():
    assert compute_signal(table(['2026-01', '2026-03'], [1, 16])).tolist() == [False, False]


def test_nonchronological_inputs_are_sorted_by_announcement():
    out = compute_signal(table(['2026-11', '2026-10'], [16, 4],
                               ['2026-10-21', '2026-09-20']))
    assert out.index.is_monotonic_increasing
    assert out.tolist() == [False, True]


@pytest.mark.parametrize('months,pcts,dates', [
    (['2026-10', '2026-10'], [4, 16], ['2026-09-20', '2026-09-21']),
    (['2026-10', '2026-11'], [4, 16], ['2026-09-20', '2026-09-20']),
    (['2026-10'], [-1], ['2026-09-20']),
    (['2026-10'], [101], ['2026-09-20']),
    (['2026-10'], [None], ['2026-09-20']),
    (['2026-11'], [16], ['2026-11-01']),
])
def test_invalid_data_rejected(months, pcts, dates):
    with pytest.raises(ValueError):
        compute_signal(table(months, pcts, dates))


def test_missing_column_rejected():
    with pytest.raises(ValueError, match='missing columns'):
        compute_signal({'apportionment': pd.DataFrame({'delivery_month': ['2026-11']})})
