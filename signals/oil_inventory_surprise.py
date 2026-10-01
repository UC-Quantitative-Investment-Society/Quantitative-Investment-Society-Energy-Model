"""Oil inventory surprise signal.

Handoff sheet: docs/signal_handoff_template.md (filled-in example at the bottom).

Hypothesis: when the weekly crude inventory report shows a draw at least
2 million barrels bigger than expected, supply is tighter than the market
thought, so energy stocks drift up over the next week.

Output type: bool (True on report dates where the signal fires).

Example: expected change -1.0M barrels, actual change -3.5M barrels.
Surprise = actual - expected = -3.5 - (-1.0) = -2.5, which is <= -2.0, so True.
"""

import pandas as pd

# Parameters come from the analyst handoff sheet. Do NOT change them here.
# A different value means a new signal version with a new handoff sheet.
INSTRUMENT = "XOM"
DIRECTION = "long"
HOLD_DAYS = 5
THRESHOLD_MBBL = -2.0  # fire when (actual - expected) <= this, in millions of barrels


def compute_signal(data: dict) -> pd.Series:
    """Return True on each report date where the draw beat expectations by 2M+ barrels.

    Output type: bool.

    data["inventory"] is a DataFrame indexed by report date with columns
    actual_change_mbbl and expected_change_mbbl.
    """
    inv = data["inventory"]
    surprise = inv["actual_change_mbbl"] - inv["expected_change_mbbl"]
    fires = surprise <= THRESHOLD_MBBL
    fires.name = "oil_inventory_surprise"
    return fires.astype(bool)
