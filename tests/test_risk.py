"""Position cap and daily-loss halt."""

import pytest

from execution.risk import MAX_DAILY_LOSS_PCT, MAX_POSITION_PCT, check_daily_loss_halt, size_order


def test_default_size_is_the_cap():
    # $1,000,000 portfolio, 5% cap -> $50,000 -> 500 shares at $100
    assert MAX_POSITION_PCT == 0.05
    assert size_order(1_000_000, 100.0) == 500


def test_size_order_caps_large_requests():
    assert size_order(1_000_000, 100.0, target_dollars=80_000) == 500


def test_size_order_allows_small_requests():
    assert size_order(1_000_000, 100.0, target_dollars=20_000) == 200


def test_size_order_rounds_down_to_whole_shares():
    assert size_order(1_000_000, 333.0) == 150  # 50,000 / 333 = 150.15


def test_no_halt_below_limit():
    assert MAX_DAILY_LOSS_PCT == 0.02
    assert check_daily_loss_halt(1_000_000, 981_000) is False  # down 1.9%


def test_halt_at_limit():
    assert check_daily_loss_halt(1_000_000, 980_000) is True  # down exactly 2.0%


def test_halt_beyond_limit():
    assert check_daily_loss_halt(1_000_000, 950_000) is True  # down 5%


def test_bad_inputs_raise():
    with pytest.raises(ValueError):
        size_order(0, 100.0)
