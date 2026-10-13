# Role: Execution & Risk (3)

Paper trade approved signals on Alpaca within hard position and loss limits,
and monitor live performance against the backtest. **Paper only.**

## 1. What you own

- `execution/risk.py` :
  - `MAX_POSITION_PCT = 0.05` : per-position cap as a fraction of equity
  - `MAX_DAILY_LOSS_PCT = 0.02` : intraday drawdown at which new positions are halted
  - `size_order()`, `check_daily_loss_halt()`
- `execution/orders.py` : alpaca-py wrapper (`PAPER_BASE_URL`, `get_client()`, `submit_market_order()`)
- `tests/test_risk.py`, `tests/test_orders.py`
- `.env.example` : credential template; real keys only in your git-ignored `.env`

## 2. What you receive, and from whom

- **Backtesting**: a `PASS` verdict, posted as the engine summary line in the
  signal's PR. Full `stats.json` is reproducible with `python -m backtesting.engine` on `main`.
- **Signal Integration**: `INSTRUMENT`, `DIRECTION`, `HOLD_DAYS` in the signal
  module (e.g. `signals/oil_inventory_surprise.py`: XOM, long, 5).

## 3. What you hand off, and to whom

- **Front-End & Reporting**: the paper trade record (date, ticker, qty, entry,
  exit) for live vs backtest reporting. Not built yet; Alpaca paper order
  history is the record of truth for now.
- **Quant director**: escalation when live performance drifts from the backtest.

## 4. Step-by-step: one new signal

1. Confirm the verdict is `PASS`. Never trade `REJECT` or `REVIEW`.
2. Confirm `ALPACA_BASE_URL=https://paper-api.alpaca.markets` (enforced by `orders.py`).
3. After each data release, check for a fire. Fire on day t means entry on
   day t+1, matching the backtest. No live runner or live inventory feed exists
   yet; this check is manual.
4. Size: `shares = size_order(equity, price)`.
5. Enter: `submit_market_order(ticker, shares, "buy", start_of_day_equity, current_equity)`.
   Paper endpoint and daily loss halt are checked before submission.
6. Exit after `HOLD_DAYS` with `"sell"` and `closing=True`. Exits bypass the halt
   so positions can always be closed.
7. Reconcile fills in Alpaca order history against backtest expectations.

### Limits

| Limit | Value | Effect | On $1,000,000 |
|-------|-------|--------|---------------|
| `MAX_POSITION_PCT` | 0.05 | caps notional per position | $50,000 |
| `MAX_DAILY_LOSS_PCT` | 0.02 | blocks new positions; exits allowed | halt at $980,000 |

### Drift monitoring

Review every 10 live trades against the backtest. Example: backtest 65.8% win
rate and +1.42% average trade; live 2 of 10 winners and -1.5% average. Suspend
the signal and escalate to Backtesting and the quant director. Typical causes:
data latency vs backtest assumptions, slippage above the 5 bps cost assumption,
regime change.

## 5. Worked example: oil inventory surprise

$1,000,000 paper account, verdict `PASS`. Wednesday report fires; Thursday XOM at $61.45.

```python
from execution.risk import size_order, check_daily_loss_halt
from execution.orders import submit_market_order

shares = size_order(1_000_000, 61.45)       # $50,000 cap / 61.45 -> 813 shares (~$49,959)
check_daily_loss_halt(1_000_000, 998_500)   # -0.15% -> False
submit_market_order("XOM", shares, "buy", start_of_day_equity=1_000_000, current_equity=998_500)
```

Cap enforcement:

```python
size_order(1_000_000, 100.0, target_dollars=80_000)   # 500 shares, not 800
```

Halt at -2.1%:

```python
check_daily_loss_halt(1_000_000, 979_000)                   # True
submit_market_order("CVX", 300, "buy", 1_000_000, 979_000)  # RuntimeError: Daily loss limit hit
```

Exit after 5 trading days:

```python
submit_market_order("XOM", 813, "sell", start_of_day_equity=1_000_000,
                    current_equity=1_004_000, closing=True)
```

## 6. Definition of done

- [ ] Verdict is `PASS`
- [ ] Paper endpoint confirmed; keys only in local `.env`
- [ ] All orders sized via `size_order()`
- [ ] All orders submitted via `submit_market_order()`; no direct Alpaca calls
- [ ] Entry the trading day after the fire; exit after `HOLD_DAYS`
- [ ] Exits sent with `closing=True`
- [ ] Fills reconciled in Alpaca order history; drift reviewed every 10 trades
- [ ] `pytest` green

## 7. Common mistakes

**Trading REVIEW.** A REVIEW verdict means the result is likely a bug. Wait for Backtesting.

**Endpoint changes.** Any change to `PAPER_BASE_URL` or bypass of `_require_paper()` is rejected in review.

**Committed keys.** `TradingClient("PK123...", "abc...")` in source. Keys stay in
`.env`. If a key is ever pushed, rotate it in Alpaca immediately.

**Same-day entry.** Entering on the report date diverges from the backtest's
next-day entry and invalidates live vs backtest comparison.

**Resetting the halt.** Restarting with `start_of_day_equity=979_000` defeats
the limit. Always use equity at the open.
