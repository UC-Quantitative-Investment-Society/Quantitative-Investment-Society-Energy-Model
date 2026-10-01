# Pipeline Overview

Every signal passes through the same five stages in order. No stage is skipped.

## Stages

| Stage | Owner | Input | Output | Files |
|-------|-------|-------|--------|-------|
| 0. Spec | Quant research | research | signed handoff sheet | `docs/signal_handoff_template.md` (in the PR) |
| 1. Implement | Signal Integration (5) | signed sheet | `compute_signal()`, registered in `ACTIVE_SIGNALS` | `signals/<name>.py`, `signals/__init__.py` |
| 2. Validate | Backtesting (5) | registered signal | `stats.json`, `equity_curve.png`, verdict | `backtesting/engine.py`, `backtesting/config.py`, `backtesting/results/<name>/` |
| 3. Trade | Execution & Risk (3) | PASS verdict | paper orders on Alpaca | `execution/risk.py`, `execution/orders.py` |
| 4. Report | Front-End & Reporting (3) | result files | dashboard panel | `dashboard/app.py` |

## Ownership of parameters

- **Research** sets the signal spec: condition, threshold, instrument, direction, hold period.
- **Engineering** sets the testing standards in `backtesting/config.py`, identical for every signal:
  - benchmark: XLE
  - test window: 2019-01-01 to 2023-12-31
  - out-of-sample from 2022-07-01
  - costs: 5 bps per side
  - minimum fires: 30
  - suspicious Sharpe threshold: 3.0

Separating the two prevents parameter tuning against the backtest.

## Stage gates

- 0 to 1: both sign-offs recorded on the sheet.
- 1 to 2: signal merged to `main`, registered in `ACTIVE_SIGNALS`, `pytest` green.
- 2 to 3: verdict is `PASS` and the engine's summary line is posted in the
  signal's PR. REJECT and REVIEW are never traded. Results folders are
  git-ignored and reproducible with `python -m backtesting.engine` on `main`.
- 3 to 4: the dashboard renders whatever is in `backtesting/results/`; it never computes.

## Worked example: `oil_inventory_surprise`

### Stage 0: spec

From the example sheet in `docs/signal_handoff_template.md`: fire when
actual minus consensus crude change <= -2.0 mbbl; long XOM; hold 5 trading
days; bool output. Signed 2026-09-22 (researcher) and 2026-09-23 (director).

### Stage 1: implementation

Branch `signals/add-oil-inventory-surprise`; `signals/_template.py` copied to
`signals/oil_inventory_surprise.py`:

```python
INSTRUMENT = "XOM"
DIRECTION = "long"
HOLD_DAYS = 5
THRESHOLD_MBBL = -2.0

def compute_signal(data):
    """... Output type: bool."""
    inv = data["inventory"]
    surprise = inv["actual_change_mbbl"] - inv["expected_change_mbbl"]
    return (surprise <= THRESHOLD_MBBL).astype(bool)
```

Registered in `signals/__init__.py`:

```python
ACTIVE_SIGNALS = {"oil_inventory_surprise": oil_inventory_surprise.compute_signal}
```

`tests/test_signals.py` enforces the contract (date-indexed Series, bool or
float, documented output type, valid handoff constants). One approval, merged.

### Stage 2: validation

```bash
python -m backtesting.engine
```

The engine reads `INSTRUMENT`, `DIRECTION`, `HOLD_DAYS` from the module and the
standards from `backtesting/config.py`, then calls `run_backtest()`.

Execution timing (no lookahead): signal on date t, entry at the close of the
first trading day after t, exit `hold_days` later. Sample trade:

- 2019-05-22 (Wed): actual -4.8, consensus -1.0, surprise -3.8. Fires.
- Entry 2019-05-23 close at $45.04.
- Exit 2019-05-30 close at $44.82. Net of costs: -0.59%.

Full-sample results (`backtesting/results/oil_inventory_surprise/stats.json`):

| Metric | Value |
|--------|-------|
| n_fires | 45 (min 30) |
| n_trades | 44 |
| win rate | 56.8% |
| avg excess vs XLE per trade | +1.28% |
| Sharpe | 0.95 |
| max drawdown | -15.1% |
| out-of-sample (from 2022-07-01) | 14 fires, 61.5% win rate, +1.44% per trade |
| verdict | PASS |

Plus `equity_curve.png` (strategy vs XLE). Backtesting reviews per
`docs/roles/backtesting.md` and posts the summary line in the PR.

Synthetic data; these numbers validate the pipeline only.

### Stage 3: paper trading

No live runner exists yet (see `README.md`), so fires are checked manually.
On a fire, with a $1,000,000 paper account:

```python
size_order(1_000_000, 45.04)   # 5% cap = $50,000 -> 1110 shares
submit_market_order("XOM", 1110, "buy", start_of_day_equity=1_000_000, current_equity=998_500)
```

`orders.py` enforces the paper endpoint and the 2% daily loss halt before
sending. Exit after 5 trading days with `closing=True` (exits bypass the halt).

### Stage 4: reporting

`dashboard/app.py` discovers `backtesting/results/oil_inventory_surprise/stats.json`
automatically: a summary row (`oil_inventory_surprise | PASS | XOM | 45 | ...`)
and a panel with metrics, the in-sample / out-of-sample split, and the equity
curve. No dashboard change is needed to add a signal.
