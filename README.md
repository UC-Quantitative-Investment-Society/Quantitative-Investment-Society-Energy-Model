# QIS Energy Quant Model

Energy-sector systematic trading model for the Quantitative Investment Society.
Signals are researched by the quant team, implemented and validated by
engineering, paper traded on Alpaca, and reported through a Streamlit dashboard.

> **Sample data is synthetic.** `data/sample/` is randomly generated so the
> project runs offline. Results on it validate the pipeline, not any strategy.
> See `data/sample/README.md`.
>
> **Paper trading only.** `execution/orders.py` refuses to run unless
> `ALPACA_BASE_URL` is Alpaca's paper endpoint.

## Pipeline

```
 Quant research                       (outside this repo)
   signal spec on the handoff sheet (docs/signal_handoff_template.md),
   signed off by the quant researcher and quant director
        |
        v
 [1] Signal Integration (6)           signals/<name>.py, signals/__init__.py
   implement compute_signal(data) exactly per spec
        |
        v
 [2] Backtesting (6)                  backtesting/engine.py, backtesting/config.py
   run the shared engine, write backtesting/results/<name>/
        |
        v  (PASS only)
 [3] Execution & Risk (3)             execution/risk.py, execution/orders.py
   size, risk-check, and paper trade on Alpaca
        |
        v
 [4] Front-End & Reporting (2)        dashboard/app.py
   report stats and equity curves vs XLE
```

End-to-end walkthrough: `docs/pipeline_overview.md`. Role guides: `docs/roles/`.

## Layout

| Folder         | Contents                                                           | Owner                 |
| -------------- | ------------------------------------------------------------------ | --------------------- |
| `signals/`     | one module per signal, `ACTIVE_SIGNALS` registry, `_template.py`   | Signal Integration    |
| `backtesting/` | shared engine, testing standards, Alpaca price downloader, results | Backtesting           |
| `execution/`   | position sizing, daily loss halt, paper-only Alpaca order wrapper  | Execution & Risk      |
| `dashboard/`   | Streamlit dashboard                                                | Front-End & Reporting |
| `data/sample/` | synthetic prices and inventory                                     | read only             |
| `docs/`        | pipeline overview, handoff template, role guides                   | all                   |
| `tests/`       | pytest suite                                                       | all                   |

## Setup and run

Python 3.11. Run from the repo root.

```bash
python3.11 -m venv .venv            # or: uv venv --python 3.11 .venv
source .venv/bin/activate
pip install -r requirements.txt

pytest                              # all tests should pass
python -m backtesting.engine        # writes backtesting/results/<signal>/{stats.json,equity_curve.png}
streamlit run dashboard/app.py
```

### Alpaca credentials

```bash
cp .env.example .env                # fill in PAPER keys
set -a; source .env; set +a
```

`.env` is git-ignored. Never commit keys.

### Historical prices from Alpaca

```bash
python -m backtesting.alpaca_data                                   # XOM, XLE over the config test window
python -m backtesting.alpaca_data --tickers XOM CVX XLE --start 2018-01-01
python -m backtesting.engine --data raw                             # backtest on data/raw/
```

Writes split- and dividend-adjusted daily closes to `data/raw/prices.csv` in the
same layout as the sample file. In `--data raw` mode, signals that need a table
not present in `data/raw/` (e.g. `inventory`) are skipped. Real and synthetic
data are never mixed.

## Results are not committed

`backtesting/results/*/` is git-ignored. Results are reproducible: run
`python -m backtesting.engine` on `main`. Backtesting records each verdict by
posting the engine's summary line in the signal's PR.

## Not built yet

| Gap                        | Current state                                                                                                                                                         | Owner                  |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| Real inventory data        | Synthetic only. EIA provides actuals; consensus (expected change) requires a paid source. Source to be chosen by research before the oil signal can run on real data. | Backtesting + research |
| Live signal runner         | None. Execution & Risk checks fires manually.                                                                                                                         | Execution & Risk       |
| Trade log                  | Alpaca paper order history is the record of truth.                                                                                                                    | Execution & Risk       |
| Live vs backtest reporting | Dashboard shows backtest results only.                                                                                                                                | Front-End & Reporting  |
| Branch protection          | Must be enabled in GitHub settings to enforce `CONTRIBUTING.md`.                                                                                                      | Repo admin             |

## Contributing

See `CONTRIBUTING.md`.
