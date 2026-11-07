"""Enbridge Mainline Squeeze signal (provisional research specification).

Bullish when the announced *next-month* heavy-crude apportionment is at least
10% and increases by at least 5 percentage points from the preceding month's
announced apportionment.

Input: data['apportionment'], indexed by the date the market first learned the
announcement (NOT the month being rationed). Required columns:
    delivery_month: values parseable as calendar months, e.g. '2026-11'
    heavy_apportionment_pct: percentages on the 0-to-100 scale, e.g. 16.0

Only information available at an announcement timestamp is used. The output is
a boolean series indexed by the actual announcement dates.

Specification source: Enbridge_Deck_with_Signal.pptx, slides 8–9.
"""

import pandas as pd

ROLE = "trade"
INSTRUMENT = "ENB"  # Confirm exchange / pricing convention with backtest owner.
DIRECTION = "long"
HOLD_DAYS = 60  # Provisional test horizon; deck also proposes 30–90 days.
BENCHMARK = "TRP"  # Evaluate ENB excess return vs TRP outside compute_signal.
JUMP_THRESHOLD_PP = 5.0
MIN_APPORTIONMENT_PCT = 10.0


def compute_signal(data: dict) -> pd.Series:
    """Fire on announcements of >=5pp monthly jump AND >=10% level."""
    table = data["apportionment"]
    required = {"delivery_month", "heavy_apportionment_pct"}
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"apportionment missing columns: {sorted(missing)}")

    inv = table.copy()
    inv.index = pd.to_datetime(inv.index)
    if inv.index.has_duplicates:
        raise ValueError("Each announcement date must appear only once")
    inv = inv.sort_index()
    inv["delivery_month"] = pd.PeriodIndex(inv["delivery_month"], freq="M")
    if inv["delivery_month"].duplicated().any():
        raise ValueError("Only one published value per delivery month is supported")
    values = pd.to_numeric(inv["heavy_apportionment_pct"], errors="raise")
    if ((values < 0) | (values > 100)).any():
        raise ValueError("heavy_apportionment_pct must be between 0 and 100")
    if values.isna().any():
        raise ValueError("Missing apportionment values must be resolved before trading")
    inv["apportionment"] = values
    # The announcement must predate the delivery month; otherwise the index
    # cannot be used as an observable trade-decision timestamp.
    if (inv.index.to_period("M") >= inv["delivery_month"]).any():
        raise ValueError("Announcement date must precede its delivery month")

    # Match consecutive *delivery months*, not just adjacent available rows:
    # a missing month must NOT be treated as the previous month.
    by_month = inv.set_index("delivery_month")["apportionment"]
    previous = by_month.reindex(inv["delivery_month"] - 1).to_numpy()
    jump_pp = inv["apportionment"].to_numpy() - previous
    fires = (jump_pp >= JUMP_THRESHOLD_PP) & (
        inv["apportionment"].to_numpy() >= MIN_APPORTIONMENT_PCT
    )
    return pd.Series(fires, index=inv.index, name="mainline_squeeze", dtype=bool)
