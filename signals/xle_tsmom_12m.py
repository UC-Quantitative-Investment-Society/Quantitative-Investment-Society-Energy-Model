"""XLE 12-month time-series momentum.

Hypothesis: an asset's own past 12-month return predicts its next month's
return (Moskowitz, Ooi and Pedersen 2012). Long-only version: hold XLE when
it is up over the past year, otherwise stay out.

Output type: bool. True on day t when close_t / close_(t-252) - 1 > 0.
The first 252 days have no lookback and are False.
Example: close 92.10 today, 80.00 a year ago -> +15.1% -> True.
"""

import pandas as pd

INSTRUMENT = "XLE"
DIRECTION = "long"
HOLD_DAYS = 21
LOOKBACK = 252  # trading days, about 12 months


def compute_signal(data: dict) -> pd.Series:
    """True when XLE's 12-month return is positive. Output type: bool."""
    px = data["prices"]["XLE"]
    ret_12m = px / px.shift(LOOKBACK) - 1
    return (ret_12m > 0).fillna(False)