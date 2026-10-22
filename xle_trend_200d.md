# Signal Handoff: xle_trend_200d

**Signal name:** xle_trend_200d

**Hypothesis:** Sector prices trend. When XLE is above its 200-day moving average, it has tended to keep rising and to fall less sharply. Holding XLE only in uptrends should match buy-and-hold returns with smaller drawdowns. Source: Faber, "A Quantitative Approach to Tactical Asset Allocation" (2007).

**Data source:** XLE daily split- and dividend-adjusted closes from Alpaca (`python -m backtesting.alpaca_data`), column `XLE` in `data["prices"]`. Offline: `data/sample/prices.csv` (synthetic).

**Condition + threshold:** sma_200 = 200-trading-day simple moving average of XLE close, including day t. Fire on day t when close_t > sma_200_t. The first 199 days have no average and are False.
Example: close 92.10, 200-day average 88.40, so True.

**Instrument:** XLE

**Direction:** long

**Hold period (trading days):** 21 (about one month, matching the paper's monthly rebalance). While a trade is open, further fires are counted but no new trade starts.

**Output type (bool / score):** bool

**Notes for engineering:**
- Trades the benchmark itself, so it is judged in timing mode (strategy Sharpe vs XLE buy-and-hold Sharpe), per REPO_FIXES.md Fix 1. Merge Fix 1 before backtesting this.
- Expect high correlation with xle_tsmom_12m. Backtesting reports the correlation, and nobody drops either signal for it in phase 1.
- Walkthrough signal (issue #1). Its PR is the reference for every later signal.

**Analyst:** SWE team (established signal, no new research)

**Sign-off, quant researcher (name, date):**

**Sign-off, quant director (name, date):**

**Date submitted:** 2026-10-01
