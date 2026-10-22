"""xle_trend_200d.

Hypothesis: Sector prices trend. When XLE is above its 200-day moving average,
it has tended to keep rising and to fall less sharply, so holding XLE only in
uptrends should match buy-and-hold returns with smaller drawdowns.
Source: Faber, "A Quantitative Approach to Tactical Asset Allocation" (2007).

Output type: bool. True on dates when XLE closes above its 200-day simple
moving average, False otherwise (including the first 199 days).

After the file works, register it in signals/__init__.py (ACTIVE_SIGNALS).
"""

import pandas as pd

INSTRUMENT = "XLE"
DIRECTION = "long"
HOLD_DAYS = 21  # about one month, matching the paper's monthly rebalance
THRESHOLD = 0.0  # fire when close - sma_200 > 0 (the sheet has no extra margin)

SMA_WINDOW = 200  # trading days, including day t


def compute_signal(data: dict) -> pd.Series:
    """True on day t when XLE close_t is above its 200-day simple moving average.

    Output type: bool.

    The average includes day t. The first 199 days have no average (NaN), and a
    comparison with NaN is False, so they come out False as the sheet requires.
    Overlapping fires during an open trade are handled by the engine, not here.
    """
    close = data["prices"]["XLE"]
    sma_200 = close.rolling(window=SMA_WINDOW, min_periods=SMA_WINDOW.mean())
    return ((close - sma_200) > THRESHOLD).astype(bool)