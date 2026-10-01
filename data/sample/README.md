# Sample data (synthetic)

Randomly generated with a fixed seed so the pipeline runs offline and
reproducibly. Not market data. Do not draw conclusions from results on it.

The series embed a small post-draw drift in XOM so the example signal has
something to detect. Real markets will not be this clean.

All four files come from `generate.py` (seed 42). To rebuild them:

```bash
python data/sample/generate.py
```

Never edit the CSVs by hand. Change `generate.py` and rerun it, so the data
stays reproducible. The docstring in `generate.py` lists the design.

## prices.csv

Daily closes, business days 2019-01-02 to 2023-12-29.

| column | description | example |
|--------|-------------|---------|
| date | trading day | 2019-01-03 |
| XOM | synthetic close | 61.45 |
| XLE | synthetic close (benchmark) | 55.26 |

## inventory.csv

Weekly crude inventory reports (Wednesdays), millions of barrels.

| column | description | example |
|--------|-------------|---------|
| date | release date | 2019-01-09 |
| actual_change_mbbl | reported week-over-week change | 0.4 |
| expected_change_mbbl | consensus estimate | -3.0 |

## wti.csv

Daily WTI crude close, same dates as `prices.csv`. Correlation with XLE daily
returns is about 0.5. Real equivalent: FRED `DCOILWTICO`.

| column | description | example |
|--------|-------------|---------|
| date | trading day | 2019-01-03 |
| wti | synthetic close, $/bbl | 45.72 |

Read it in a signal as `data["wti"]["wti"]`.

## vix.csv

Daily VIX close, same dates as `prices.csv`. Mean-reverts around 18 and goes
above 30 only in scheduled spikes, for example 60.04 on 2020-03-16, back under
30 on 2020-04-13. Real equivalent: FRED `VIXCLS`.

| column | description | example |
|--------|-------------|---------|
| date | trading day | 2019-01-03 |
| vix | synthetic close | 21.86 |

Read it in a signal as `data["vix"]["vix"]`.

## Real data

Real data goes in `data/raw/` (git-ignored), in the same layout:

- prices: `python -m backtesting.alpaca_data`
- WTI and VIX: `python -m backtesting.fred_data`

Real inventory data is not wired in yet.
