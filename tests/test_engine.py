"""The shared engine must avoid lookahead, apply costs, and count fires."""

import numpy as np
import pandas as pd
import pytest

from backtesting.engine import _clip_to_test_window, load_sample_data, run_backtest, signal_params

DATES = pd.bdate_range("2024-01-01", periods=10)
# Day 2 is the signal day. The stock jumps +10% ON that day (100 -> 110).
# A correct engine enters the day after (day 3, at 110), so it must NOT earn that jump.
# From day 3 to day 5 the stock rises 110 -> 121, a +10% move.
STOCK = [100, 100, 110, 110, 115, 121, 121, 121, 121, 121]
BENCH = [50] * 10


def make_data():
    prices = pd.DataFrame({"TEST": STOCK, "XLE": BENCH}, index=DATES, dtype=float)
    return {"prices": prices}


def fires_on_day_2(data):
    """Output type: bool."""
    return pd.Series(DATES == DATES[2], index=DATES)


def run(cost_bps=0.0, signal_fn=fires_on_day_2):
    return run_backtest(signal_fn, make_data(), ticker="TEST", hold_days=2, benchmark="XLE",
                        cost_bps=cost_bps, out_of_sample_start="2030-01-01")


def test_enters_after_signal_date():
    trade = run()["trades"].iloc[0]
    assert trade["fire_date"] == DATES[2]
    assert trade["entry_date"] == DATES[3], "entry must be the first trading day AFTER the fire"
    assert trade["exit_date"] == DATES[5]
    assert trade["gross_return"] == pytest.approx(0.10), "should not capture the signal-day jump"


def test_costs_are_applied_on_entry_and_exit():
    no_cost = run(cost_bps=0)["trades"].iloc[0]["net_return"]
    with_cost = run(cost_bps=10)["trades"].iloc[0]["net_return"]
    assert with_cost == pytest.approx(no_cost - 2 * 0.0010)


def test_reports_n_fires():
    def fires_three_times(data):
        """Output type: bool."""
        return pd.Series([d in (DATES[0], DATES[1], DATES[6]) for d in DATES], index=DATES)

    stats = run(signal_fn=fires_three_times)["stats"]
    assert stats["n_fires"] == 3
    # Fire on day 1 lands while the day-0 trade is still open, so only 2 trades are taken.
    assert stats["n_trades"] == 2


def test_score_signal_fires_when_positive():
    def score(data):
        """Output type: score (float)."""
        return pd.Series([2.5 if d == DATES[2] else 0.0 for d in DATES], index=DATES)

    assert run(signal_fn=score)["stats"]["n_fires"] == 1


def test_template_placeholders_are_refused():
    from signals import _template

    with pytest.raises(ValueError, match="INSTRUMENT"):
        signal_params(_template.compute_signal)


# Comparison modes. A signal that trades the benchmark itself is judged on Sharpe
# vs benchmark buy and hold ("timing"), never on per-trade excess, which would be
# exactly minus the round-trip cost on every trade.

XLE_DATES = pd.bdate_range("2020-01-01", periods=300)


def make_xle_only_data():
    rng = np.random.default_rng(0)
    xle = 50 * np.exp(np.cumsum(rng.normal(0.0003, 0.015, len(XLE_DATES))))
    return {"prices": pd.DataFrame({"XLE": xle}, index=XLE_DATES)}


def run_on_xle(signal_fn):
    return run_backtest(signal_fn, make_xle_only_data(), ticker="XLE", hold_days=1, benchmark="XLE",
                        cost_bps=5, out_of_sample_start=str(XLE_DATES[200].date()))


def test_signal_trading_the_benchmark_uses_timing():
    def fires_on_mondays(data):
        """Output type: bool."""
        return pd.Series(XLE_DATES.dayofweek == 0, index=XLE_DATES)

    assert run_on_xle(fires_on_mondays)["stats"]["comparison"] == "timing"


def test_always_long_benchmark_is_not_pass():
    # Fires every day, so the strategy is XLE buy and hold minus costs and cannot beat it.
    def fires_every_day(data):
        """Output type: bool."""
        return pd.Series(True, index=XLE_DATES)

    stats = run_on_xle(fires_every_day)["stats"]
    assert stats["n_fires"] >= stats["min_fires"]
    assert stats["in_sample"]["sharpe"] < stats["in_sample"]["benchmark_sharpe"]
    assert stats["out_of_sample"]["sharpe"] < stats["out_of_sample"]["benchmark_sharpe"]
    assert stats["verdict"] == "REJECT"


def test_oil_example_still_per_trade_and_passes():
    from signals import oil_inventory_surprise as oil

    data = _clip_to_test_window(load_sample_data())
    stats = run_backtest(oil.compute_signal, data, ticker=oil.INSTRUMENT, hold_days=oil.HOLD_DAYS,
                         direction=oil.DIRECTION)["stats"]
    assert stats["comparison"] == "per_trade"
    assert stats["verdict"] == "PASS"
