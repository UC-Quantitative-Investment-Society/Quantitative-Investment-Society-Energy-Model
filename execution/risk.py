"""Risk limits for paper trading. Every order goes through these checks.

Example with a $1,000,000 portfolio:
    MAX_POSITION_PCT = 0.05  -> no single position bigger than $50,000
    MAX_DAILY_LOSS_PCT = 0.02 -> stop trading for the day once down $20,000
"""

import math

MAX_POSITION_PCT = 0.05
MAX_DAILY_LOSS_PCT = 0.02


def size_order(portfolio_value: float, price: float, target_dollars: float | None = None) -> int:
    """Return how many whole shares to buy, never more than MAX_POSITION_PCT of the portfolio.

    If target_dollars is None we use the full cap.
    Example: size_order(1_000_000, 100.0) -> 500 shares ($50,000).
    Example: size_order(1_000_000, 100.0, target_dollars=80_000) -> still 500 (capped).
    Example: size_order(1_000_000, 100.0, target_dollars=20_000) -> 200.
    """
    if portfolio_value <= 0 or price <= 0:
        raise ValueError("portfolio_value and price must be positive")
    cap_dollars = portfolio_value * MAX_POSITION_PCT
    dollars = cap_dollars if target_dollars is None else min(target_dollars, cap_dollars)
    return max(0, math.floor(dollars / price))


def check_daily_loss_halt(start_of_day_equity: float, current_equity: float) -> bool:
    """Return True if today's loss has reached MAX_DAILY_LOSS_PCT, meaning: stop trading today.

    Example: start 1,000,000, now 981,000 (down 1.9%) -> False, keep trading.
    Example: start 1,000,000, now 980,000 (down 2.0%) -> True, halt.
    """
    if start_of_day_equity <= 0:
        raise ValueError("start_of_day_equity must be positive")
    loss_pct = (start_of_day_equity - current_equity) / start_of_day_equity
    return loss_pct >= MAX_DAILY_LOSS_PCT - 1e-12  # tiny tolerance for float rounding
