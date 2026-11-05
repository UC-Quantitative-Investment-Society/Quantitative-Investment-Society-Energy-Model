"""Manufacturing Thermal Activity Index (MTAI).

Hypothesis: IF satellite imagery reveals an unexpectedly large, repeatable rise in cloud-free, weather-adjusted surface temperature over thermally exposed activity zones at the GE Vernova Greenville site, THEN future turbine manufacturing/testing throughput and, potentially, GEV equipment earnings expectations may be higher than anticipated, BECAUSE additional manufacturing and full-load testing may leave a detectable industrial thermal footprint before quarterly results are announced. If this information is not priced in, positive subsequent GEV excess stock returns may follow.

Output type: <bool>
  bool  -> True on dates the condition is met, False otherwise.


After the file works, register it in signals/__init__.py (ACTIVE_SIGNALS).
"""

import pandas as pd

ROLE = "trade"
INSTRUMENT = "GEV"
DIRECTION = "long"
HOLD_DAYS = 60
THRESHOLD = 1.0  # pilot value
SCENES = 2 # pilot value


def compute_signal(data: dict) -> pd.Series:
    """TODO: describe the condition in one sentence.

    Output type: <bool>
    """
    raise NotImplementedError("Fill this in from the handoff sheet")