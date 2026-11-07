"""Manufacturing Thermal Activity Index (MTAI).

Hypothesis: IF satellite imagery reveals an unexpectedly large, 
repeatable rise in cloud-free, weather-adjusted surface temperature 
over thermally exposed activity zones at the GE Vernova Greenville site, 
THEN future turbine manufacturing/testing throughput and, potentially, 
GEV equipment earnings expectations may be higher than anticipated, 
BECAUSE additional manufacturing and full-load testing may leave a 
detectable industrial thermal footprint before quarterly results are 
announced. If this information is not priced in, positive subsequent 
GEV excess stock returns may follow.

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
WINDOW = 24 
RELEASE_DAYS = 16



def compute_signal(data: dict) -> pd.Series:
    """True when the facility - comparisons' roof 
        temperatures spread is more than <THRESHOLD> 
        std devs above its trailing <WINDOW>-scene mean.

    Output type: <bool>
    """
    mtai = data["mtai"]
   # Averaging out all three components of our comparison (heat_gap)
    comps = mtai[["comp1", "comp2", "comp3"]]
    avg = comps.mean(axis=1)
    heat_gap = mtai["facility"] - avg

   # Calculating the last valid heat gaps' avg
    last_gaps = heat_gap.shift(1).rolling(WINDOW, min_periods=24)
    last_gaps_avg = last_gaps.mean()

   # Calculating heat surprise with above
    heat_surprise = heat_gap - last_gaps_avg

   # Calculating for the trigger
    last_gaps_std = last_gaps.std()

    fires = (heat_surprise > THRESHOLD * last_gaps_std).astype(int)
    fires.index = fires.index + pd.Timedelta(days=RELEASE_DAYS)

    fires.name = "mtai_heat_surprise"
    return fires.astype(bool)