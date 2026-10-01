# Role: Backtesting (6)

Determine, under one fixed set of standards, whether each signal produces
excess return over XLE after costs, robust out-of-sample. Own the engine and
the standards.

## 1. What you own

- `backtesting/engine.py` : the shared engine (`run_backtest`, `save_results`, `load_data`, `signal_params`)
- `backtesting/config.py` : testing standards, identical for every signal:
  - `BENCHMARK = "XLE"`
  - `TEST_START`, `TEST_END` : 2019-01-01 to 2023-12-31
  - `OUT_OF_SAMPLE_START = "2022-07-01"`
  - `COST_BPS = 5` (per side)
  - `MIN_FIRES = 30`
  - `SUSPICIOUS_SHARPE = 3.0`
- `backtesting/alpaca_data.py` : adjusted daily closes from Alpaca into
  `data/raw/prices.csv`; use with `python -m backtesting.engine --data raw`.
  Signals needing tables absent from `data/raw/` are skipped.
- `backtesting/fred_data.py` : daily WTI (`DCOILWTICO`) and VIX (`VIXCLS`) from
  FRED into `data/raw/wti.csv` and `data/raw/vix.csv`. No key needed.
- `data/sample/generate.py` : the seeded generator for every synthetic file in `data/sample/`
- `backtesting/results/<signal_name>/` : `stats.json`, `equity_curve.png` (git-ignored)
- `tests/test_engine.py`, `tests/test_alpaca_data.py`, `tests/test_fred_data.py`

## 2. What you receive, and from whom

From **Signal Integration**: a signal merged to `main`, registered in
`ACTIVE_SIGNALS`, with `INSTRUMENT`, `DIRECTION`, `HOLD_DAYS` set per the sheet.

## 3. What you hand off, and to whom

- **Execution & Risk**: the verdict (`PASS`, `REJECT`, `REVIEW`). Only `PASS` is traded.
- **Front-End & Reporting**: `backtesting/results/<signal_name>/`. Git-ignored,
  so handed off as a reproducible run: `python -m backtesting.engine` on `main`.
- **Research**: a written summary, e.g. "oil_inventory_surprise: PASS, 45 fires,
  +1.28% excess vs XLE per trade, holds out-of-sample."

## 4. Step-by-step: one new signal

1. Pull `main`; confirm the signal is in `ACTIVE_SIGNALS`.
2. `python -m backtesting.engine` from the repo root. Never run a private copy of the engine; fixes go in via PR.
3. Review `stats.json` and `equity_curve.png`.
4. Confirm the verdict logic:
   - `n_fires < MIN_FIRES`: **REJECT**
   - does not beat XLE both in-sample and out-of-sample, under the signal's comparison mode (below): **REJECT**
   - Sharpe > `SUSPICIOUS_SHARPE`: **REVIEW** (bug hunt before anything else)
   - otherwise: **PASS**
5. Post the engine's summary line and your written summary in the signal's PR. That comment is the record of the verdict.

### Comparison modes

The engine picks the mode from the signal's `INSTRUMENT` and records it in `stats["comparison"]`.

| Mode | When | Beats XLE means | Example |
|------|------|-----------------|---------|
| `per_trade` | `INSTRUMENT != "XLE"` | `avg_excess_vs_benchmark > 0` in both periods | Long XOM for 5 days nets +1.8% while XLE moves +0.5%: that trade's excess is +1.3%. |
| `timing` | `INSTRUMENT == "XLE"` | strategy Sharpe > XLE buy-and-hold Sharpe over the same dates, in both periods | XLE trend signal: in-sample 0.62 vs 0.48, out-of-sample 0.71 vs 0.55. Beats XLE. |

Why `timing` exists: when the signal trades XLE itself, each trade's excess is
the XLE move minus the same XLE move minus costs, so it is exactly -0.10% (two
sides at 5 bps) on every trade and `per_trade` would reject every such signal.

The summary line shows the figures the verdict used. Timing example:

```
xle_trend: verdict=REJECT comparison=timing n_fires=820 n_trades=410 win_rate=51.2% sharpe=0.31 is_sharpe=0.28 vs XLE 0.35 oos_sharpe=0.40 vs XLE 0.52
```

(Illustrative numbers.) `MIN_FIRES` and the `SUSPICIOUS_SHARPE` REVIEW check are the same in both modes.

### Reported metrics

| Field | Definition | Example |
|-------|------------|---------|
| `n_fires` | signal dates in the test window | 45 |
| `n_trades` | trades taken (fires during an open trade are not re-entered) | 44 |
| `win_rate` | share of trades with positive net return | 0.568 |
| `total_return` / `benchmark_return` | strategy vs XLE buy-and-hold over the window | +78.5% / -56.7% |
| `comparison` | `per_trade` or `timing` (see Comparison modes) | `per_trade` |
| `avg_excess_vs_benchmark` | mean per-trade net return minus XLE over the same holding window | +1.28% |
| `sharpe` | annualized, daily returns, rf = 0 | 0.95 |
| `benchmark_sharpe` | XLE buy and hold over the same dates, same method | -0.55 |
| `max_drawdown` | peak to trough on the strategy equity curve | -15.1% |
| `in_sample`, `out_of_sample` | the same stats split at `OUT_OF_SAMPLE_START` | |

### Execution assumptions

Signal on date t; entry at the close of the first trading day after t; exit at
the close `hold_days` trading days later; `COST_BPS` charged on entry and exit.
`tests/test_engine.py` asserts no lookahead using a price jump on the signal date.

### Versioning

Any parameter change (threshold, hold, instrument) is a new signal
(`oil_inventory_surprise_v2`) with its own sheet, module, and results folder.
Never overwrite a prior version's results; the number of variants tried must stay auditable.

## 5. Worked example: oil inventory surprise

```bash
python -m backtesting.engine
# oil_inventory_surprise: verdict=PASS n_fires=45 n_trades=44 win_rate=56.8% sharpe=0.95
#   avg_excess_vs_XLE=1.28% oos_avg_excess=1.44%
```

Equivalent call:

```python
run_backtest(oil_inventory_surprise.compute_signal, data, ticker="XOM", hold_days=5,
             benchmark="XLE", cost_bps=5, out_of_sample_start="2022-07-01", direction="long")
```

| | Full | In-sample | Out-of-sample |
|--|------|-----------|---------------|
| n_fires | 45 | 31 | 14 |
| n_trades | 44 | 31 | 13 |
| win rate | 56.8% | 54.8% | 61.5% |
| avg excess vs XLE per trade | +1.28% | +1.21% | +1.44% |
| Sharpe | 0.95 | 0.90 | 1.06 |

45 fires vs 44 trades: the 2023-12-27 fire has fewer than 5 trading days of data remaining.

Verdict: **PASS**. Sufficient fires, positive excess in both periods, plausible Sharpe. (Synthetic data.)

### Reference readings

**Clear pass** (above): 45 fires, +1.28% excess per trade, +1.44% out-of-sample, Sharpe 0.95.

**Noise** (illustrative): 60 fires, 50.0% win rate, excess +0.02% in-sample and
-0.10% out-of-sample, Sharpe 0.05. No edge, and it fails out-of-sample. REJECT.

**Insufficient sample** (illustrative): 12 fires, 75% win rate, +3.1% excess,
Sharpe 2.1. Below `MIN_FIRES`. REJECT; ask research whether a longer history exists.

## 6. Definition of done

- [ ] Engine run on latest `main`; no private engine copies
- [ ] `stats.json` and `equity_curve.png` reviewed
- [ ] n_fires, win rate, total return vs XLE, Sharpe, max drawdown, out-of-sample reported
- [ ] `n_fires >= MIN_FIRES` confirmed
- [ ] Sharpe > 3 investigated and findings documented
- [ ] Equity curve checked for discontinuities
- [ ] Summary line and written summary posted in the PR

## 7. Common mistakes

**Private engine copies.** Re-running with costs at 0 in a notebook produces
results that are not comparable to any other signal.

**Accepting implausible Sharpe.** Sharpe 4.2 with an 80% win rate on an energy
event signal is almost always lookahead (`.shift(-1)`), misaligned dates, or
missing costs. Treat as a bug until disproven.

**Contaminating out-of-sample.** Adjusting the hold period after seeing weak
out-of-sample results consumes the holdout. Record it as `_v2` and disclose it.

**Overwriting versions.** Writing v2 into `oil_inventory_surprise/` destroys v1's record.

**Per-signal standards changes.** Moving `OUT_OF_SAMPLE_START` to suit one
signal changes the standard for all. Requires lead approval and a full rerun.

## Engine backlog

The current engine is a scaffold. Until the P0 items land, a `PASS` overstates
confidence and must not be read as deployment-ready. Each item is one PR to
the shared engine with tests in `tests/test_engine.py`; any change to verdict
logic or standards requires a rerun of every active signal.

| Pri | Item | Current behavior | Target | Done when |
|-----|------|------------------|--------|-----------|
| P0 | Significance test | `PASS` needs only mean excess > 0 in both periods (`run_backtest` verdict block) | t-stat or bootstrap p-value on per-trade excess; threshold in `config.py` | Verdict uses the test; stat and p-value in `stats.json` and on the dashboard |
| P0 | Sizing consistent with execution | 100% of capital compounded per trade | Position sized per `execution/risk.py` (`MAX_POSITION_PCT`) on a portfolio equity curve | Backtest P&L and drawdown are in the same units as live paper P&L |
| P1 | Multiple-testing control | Variants (`_vN`) judged independently | Variant count tracked per signal family; deflated Sharpe or equivalent haircut | `stats.json` reports variant count and adjusted Sharpe |
| P1 | Cost and fill model | Flat `COST_BPS` per side, fill at the close, no borrow cost | Slippage model, fill assumption configurable, borrow cost on shorts | Cost assumptions documented in `config.py`; sensitivity to costs reported |
| P1 | Real data layer | Synthetic inventory; Alpaca prices only | Point-in-time inventory and consensus indexed by release timestamp, including holiday shifts | Oil signal runs on `--data raw` with no synthetic inputs |
| P2 | Exposure-adjusted metrics | Sharpe over all days, including flat days | Add time-in-market and Sharpe on invested days alongside the current figure | Both reported in `stats.json` |
| P2 | Per-period breakdown | Single in-sample / out-of-sample split | Per-year (or regime) stats | Per-year table in `stats.json` and on the dashboard |
| P2 | Parameter sensitivity | None | Report results at neighboring parameter values (e.g. threshold -1.8 / -2.2), for disclosure only, never for selection | Sensitivity table in results; excluded from the verdict |
| P2 | Live vs backtest attribution | None | Compare paper fills with backtest trades, with Execution & Risk | Drift report per signal every 10 live trades |
