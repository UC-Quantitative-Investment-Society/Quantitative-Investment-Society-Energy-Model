"""<Signal name goes here>.

Copy this file to signals/<your_signal_name>.py to start a new signal.
Build it strictly from the signed handoff sheet (docs/signal_handoff_template.md).

Hypothesis: <copy the one-sentence "why it should work" from the handoff sheet>

Output type: <bool OR score (float)>. Pick exactly one and delete the other.
  bool  -> True on dates the condition is met, False otherwise.
           Example: "draw at least 2M barrels bigger than expected".
  score -> a float per date. The backtest engine treats score > 0 as a fire,
           so put the analyst's threshold inside this function.
           Example: surprise size in barrels, 0.0 when below the threshold.

After the file works, register it in signals/__init__.py (ACTIVE_SIGNALS).
"""

import pandas as pd

# Copy these straight from the handoff sheet. Never tune them yourself.
# The engine refuses to run while the placeholders below are left in.
INSTRUMENT = "TODO"  # ticker to trade, for example "XOM"
DIRECTION = "long"  # "long" or "short"
HOLD_DAYS = 0  # trading days to hold after entry, for example 5
THRESHOLD = 0.0  # the number from the handoff condition


def compute_signal(data: dict) -> pd.Series:
    """TODO: describe the condition in one sentence.

    Output type: <bool OR score (float)>.

    data is a dict of DataFrames indexed by date, for example
    data["prices"] and data["inventory"].
    """
    raise NotImplementedError("Fill this in from the handoff sheet")
