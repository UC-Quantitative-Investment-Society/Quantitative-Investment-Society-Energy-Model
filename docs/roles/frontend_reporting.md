# Role: Front-End & Reporting (2)

Own the Streamlit dashboard. It presents engine output and never computes metrics.

## 1. What you own

- `dashboard/app.py`
- Presentation: ordering, labels, charts

## 2. What you receive, and from whom

From **Backtesting**, per signal in `backtesting/results/<signal_name>/`:

- `stats.json` : all metrics and the verdict
- `equity_curve.png` : strategy vs XLE

Results folders are git-ignored; generate them locally with `python -m backtesting.engine` on `main`.

From **Execution & Risk** (not built yet): paper trade records for live vs backtest reporting.

## 3. What you hand off, and to whom

To the **quant director** and the team: `streamlit run dashboard/app.py`,
showing every signal's verdict and results.

## 4. Step-by-step: one new signal

1. Pull `main`; run `python -m backtesting.engine`.
2. `streamlit run dashboard/app.py`.
3. The signal appears automatically: `load_results()` globs `backtesting/results/*/stats.json`.
4. Spot-check 2 or 3 values against `stats.json`.
5. New presentation requirements (e.g. a `hold_days` column) go in `app.py` via PR, reading only from `stats.json`.

### Display only

`app.py` must not import `backtesting.engine` or recompute any metric. A second
Sharpe implementation that shows 1.15 against the engine's 1.02 leaves two
answers. Fix the engine and rerun instead.

### Layout

Top of page: the summary table, one row per signal, verdict first.

| signal | verdict | comparison | ticker | n_fires | win rate | vs XLE | Sharpe | max drawdown | out-of-sample vs XLE |

Below: one panel per signal.

## 5. Worked example: oil inventory surprise

`stats.json` (rounded):

```json
{"signal": "oil_inventory_surprise", "ticker": "XOM", "comparison": "per_trade", "verdict": "PASS",
 "n_fires": 79, "win_rate": 0.658, "avg_excess_vs_benchmark": 0.0128,
 "total_return": 1.823, "excess_return": 2.535, "sharpe": 1.02, "benchmark_sharpe": -0.55,
 "max_drawdown": -0.159, ...}
```

Ratios are stored as decimals (0.658 = 65.8%).

Summary row:

| oil_inventory_surprise | PASS | per_trade | XOM | 79 | 66% | +1.28% per trade | 1.02 | -16% | +1.47% per trade |

Panel (expander `oil_inventory_surprise: PASS`):

- metrics: Fires 79, Win rate 66%, Total return 182% (+253% vs XLE), Sharpe 1.02, Max drawdown -16%
- context: "Trades XOM long for 5 days, 5 bps cost per side, tested 2019-01-02 to 2026-06-30, data: sample."
- comparison: "Comparison: per trade. Each trade's net return vs XLE over the same holding window, in both periods."
- in-sample / out-of-sample table: 65 vs 14 fires, 1.00 vs 1.13 Sharpe
- `equity_curve.png` with the out-of-sample start marked at 2025-01-01
- warning only if `"suspicious": true`

```python
cols[0].metric("Fires", s["n_fires"], help=f"Minimum is {s['min_fires']}")
```

The page caption flags that `data: sample` results are synthetic.

## 6. Definition of done

- [ ] `streamlit run dashboard/app.py` starts cleanly
- [ ] New signal has a summary row and a panel
- [ ] Every displayed value comes from `stats.json` (spot-check 3)
- [ ] Verdict visible above the fold
- [ ] Equity curve renders
- [ ] Empty `backtesting/results/` shows a message, not a crash
- [ ] 1 approval on the PR

## 7. Common mistakes

**Recomputing metrics.** `returns.mean() / returns.std()` in `app.py` omits
annualization and shows 0.06 instead of 1.02. Use `s["sharpe"]`.

**Hard-coded paths.** `open("backtesting/results/oil_inventory_surprise/stats.json")`
hides every other signal. Iterate like `load_results()`.

**Verdict below the chart.** A rising curve read before the verdict invites a wrong conclusion.

**Ratio formatting.** Render 0.658 with `f"{x:.0%}"` (66%), not as `0.658%`.

**Missing artifacts.** A folder can have `stats.json` before the PNG exists.
Check `png.exists()` before `st.image`.
