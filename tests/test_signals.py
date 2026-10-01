"""Every registered signal must follow the signals/ contract."""

import pandas as pd
import pytest

from backtesting.engine import load_sample_data, signal_params, signal_role
from signals import ACTIVE_SIGNALS


@pytest.fixture(scope="module")
def data():
    return load_sample_data()


@pytest.mark.parametrize("name", sorted(ACTIVE_SIGNALS))
def test_signal_returns_date_indexed_series(name, data):
    result = ACTIVE_SIGNALS[name](data)
    assert isinstance(result, pd.Series), f"{name} must return a pandas Series"
    assert isinstance(result.index, pd.DatetimeIndex), f"{name} must be indexed by date"
    assert len(result) > 0


@pytest.mark.parametrize("name", sorted(ACTIVE_SIGNALS))
def test_signal_values_are_bool_or_float(name, data):
    result = ACTIVE_SIGNALS[name](data)
    assert result.dtype == bool or pd.api.types.is_float_dtype(result), (
        f"{name} returned {result.dtype}; must be bool or float"
    )


@pytest.mark.parametrize("name", sorted(ACTIVE_SIGNALS))
def test_signal_docstring_states_output_type(name):
    doc = ACTIVE_SIGNALS[name].__doc__ or ""
    assert "Output type:" in doc, f"{name}.compute_signal docstring must say 'Output type: bool' or 'score'"


@pytest.mark.parametrize("name", sorted(ACTIVE_SIGNALS))
def test_signal_has_handoff_parameters(name, data):
    signal_fn = ACTIVE_SIGNALS[name]
    if signal_role(signal_fn) == "filter":
        # A filter is never traded alone, so it has no INSTRUMENT, DIRECTION or HOLD_DAYS.
        # It must say True (OK to trade) or False on every date.
        assert signal_fn(data).dtype == bool, f"{name} is a filter and must return bool"
    else:
        # INSTRUMENT, DIRECTION, HOLD_DAYS must be filled in (not template placeholders)
        params = signal_params(signal_fn)
        assert params["hold_days"] >= 1
