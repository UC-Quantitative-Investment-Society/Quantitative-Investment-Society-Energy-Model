"""Thin wrapper around alpaca-py for PAPER trading only.

Setup: copy .env.example to .env and fill in your paper keys, then export them,
for example `set -a; source .env; set +a` in your shell.

Every function here refuses to run unless ALPACA_BASE_URL is exactly the paper
endpoint below. There is deliberately no way to switch this to real money.

Example:
    from execution.orders import submit_market_order
    submit_market_order("XOM", 500, "buy", start_of_day_equity=1_000_000, current_equity=995_000)
    # five trading days later, close it (allowed even if the daily loss halt is on):
    submit_market_order("XOM", 500, "sell", start_of_day_equity=1_000_000, current_equity=975_000, closing=True)
"""

import os

from execution.risk import check_daily_loss_halt

PAPER_BASE_URL = "https://paper-api.alpaca.markets"


def _require_paper() -> None:
    """Raise unless the environment points at Alpaca's paper endpoint."""
    url = os.environ.get("ALPACA_BASE_URL", "").rstrip("/")
    if url != PAPER_BASE_URL:
        raise RuntimeError(
            f"Refusing to trade: ALPACA_BASE_URL is {url!r}, expected {PAPER_BASE_URL!r}. "
            "This project is paper trading only."
        )


def get_client():
    """Build an Alpaca TradingClient locked to paper trading."""
    _require_paper()
    from alpaca.trading.client import TradingClient  # imported here so tests do not need keys

    key = os.environ.get("ALPACA_API_KEY")
    secret = os.environ.get("ALPACA_SECRET_KEY")
    if not key or not secret:
        raise RuntimeError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set (see .env.example)")
    return TradingClient(key, secret, paper=True)


def submit_market_order(
    symbol: str,
    qty: int,
    side: str,
    start_of_day_equity: float,
    current_equity: float,
    closing: bool = False,
):
    """Send a day market order to the paper account, after the paper and daily-loss checks.

    side is "buy" or "sell". Size qty with execution.risk.size_order first.
    closing=True means this order exits an existing position. The daily loss halt
    blocks new positions only, so exits are always allowed.
    """
    _require_paper()
    if side not in ("buy", "sell"):
        raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")
    if qty <= 0:
        raise ValueError("qty must be a positive number of shares")
    if not closing and check_daily_loss_halt(start_of_day_equity, current_equity):
        raise RuntimeError("Daily loss limit hit: no new positions until tomorrow (closing=True exits are allowed)")
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import MarketOrderRequest

    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
    )
    return get_client().submit_order(order)
