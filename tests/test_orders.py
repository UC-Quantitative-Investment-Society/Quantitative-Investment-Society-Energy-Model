"""Safety checks in execution/orders.py. None of these reach Alpaca."""

import pytest

from execution import orders


@pytest.fixture
def paper_env(monkeypatch):
    monkeypatch.setenv("ALPACA_BASE_URL", orders.PAPER_BASE_URL)


def test_refuses_non_paper_endpoint(monkeypatch):
    monkeypatch.setenv("ALPACA_BASE_URL", "https://example.com")
    with pytest.raises(RuntimeError, match="paper trading only"):
        orders.submit_market_order("XOM", 100, "buy", 1_000_000, 1_000_000)


def test_rejects_unknown_side(paper_env):
    with pytest.raises(ValueError, match="side"):
        orders.submit_market_order("XOM", 100, "Buy", 1_000_000, 1_000_000)


def test_halt_blocks_new_positions(paper_env):
    with pytest.raises(RuntimeError, match="Daily loss limit"):
        orders.submit_market_order("XOM", 100, "buy", 1_000_000, 979_000)


def test_halt_allows_closing(paper_env, monkeypatch):
    sent = []

    class FakeClient:
        def submit_order(self, order):
            sent.append(order)

    monkeypatch.setattr(orders, "get_client", lambda: FakeClient())
    orders.submit_market_order("XOM", 100, "sell", 1_000_000, 979_000, closing=True)
    assert len(sent) == 1 and sent[0].symbol == "XOM"
