# Sample data (synthetic)

Randomly generated with a fixed seed so the pipeline runs offline and
reproducibly. Not market data. Do not draw conclusions from results on it.

The series embed a small post-draw drift in XOM so the example signal has
something to detect. Real markets will not be this clean.

## prices.csv

Daily closes, business days 2019-01-02 to 2023-12-29.

| column | description | example |
|--------|-------------|---------|
| date | trading day | 2019-01-03 |
| XOM | synthetic close | 62.01 |
| XLE | synthetic close (benchmark) | 55.97 |

## inventory.csv

Weekly crude inventory reports (Wednesdays), millions of barrels.

| column | description | example |
|--------|-------------|---------|
| date | release date | 2019-01-09 |
| actual_change_mbbl | reported week-over-week change | -2.6 |
| expected_change_mbbl | consensus estimate | -3.1 |

Real data goes in `data/raw/` (git-ignored). Prices can be pulled with
`python -m backtesting.alpaca_data`. Real inventory data is not wired in yet.
