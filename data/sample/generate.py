"""Generate the synthetic sample data in data/sample/.

Run from the repo root:
    python data/sample/generate.py

Writes prices.csv, inventory.csv, wti.csv and vix.csv for business days START to END.
The seed is fixed, so every run writes identical files. Each series draws from its
own seeded stream, so moving END later appends rows and leaves earlier rows unchanged.
Example: with END = "2026-06-30" the 2019-01-02 to 2023-12-29 rows are the same as
with END = "2023-12-29".

Synthetic, not market data. Design:
- XLE: normal daily log returns, mean 0.02%, sd 1.5%.
- XOM: 1.08 x the XLE return plus its own noise (sd 0.9%), plus +0.3% a day on the
  5 trading days after an inventory report whose surprise (actual - consensus) is
  <= -2.0 mbbl. That drift is what the oil_inventory_surprise example detects.
- inventory: Wednesday reports. Consensus ~ N(-0.6, 2.3) mbbl, actual = consensus + N(0, 2.2).
- WTI: daily log returns with sd 2.5% and correlation 0.5 with XLE.
- VIX: mean-reverting around 18 (in logs), plus the scheduled spikes in VIX_SPIKES,
  the only times it goes above 30.
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
START = "2019-01-02"
END = "2023-12-29"
OUT_DIR = Path(__file__).resolve().parent

XLE_START, XOM_START, WTI_START = 56.12, 61.71, 46.54
XLE_MEAN, XLE_SD = 0.0002, 0.015
XOM_BETA, XOM_NOISE_SD = 1.08, 0.009
DRAW_THRESHOLD_MBBL = -2.0  # same threshold as signals/oil_inventory_surprise.py
DRIFT_PER_DAY, DRIFT_DAYS = 0.003, 5
CONSENSUS_MEAN, CONSENSUS_SD, SURPRISE_SD = -0.6, 2.3, 2.2
WTI_SD, WTI_CORR_WITH_XLE = 0.025, 0.5
VIX_LEVEL, VIX_PERSISTENCE, VIX_NOISE_SD = 18.0, 0.9, 0.06  # calm regime stays roughly 13 to 24
SPIKE_PERSISTENCE = 0.95  # a spike to 45 is back under 30 after about 11 trading days
VIX_SPIKES = {"2020-03-16": 60.0, "2022-03-07": 36.0, "2024-08-05": 38.0, "2025-04-07": 45.0}


def stream(n: int) -> np.random.Generator:
    """Seeded random stream number n, independent of every other stream."""
    return np.random.default_rng([SEED, n])


def round_to(values: np.ndarray, decimals: int) -> np.ndarray:
    """Round so the floats equal what the CSV reader will parse back."""
    return np.array([float(f"{v:.{decimals}f}") for v in values])


def make_inventory(start: str, end: str) -> pd.DataFrame:
    dates = pd.date_range(start, end, freq="W-WED", name="date")
    consensus = stream(2).normal(CONSENSUS_MEAN, CONSENSUS_SD, len(dates))
    actual = consensus + stream(3).normal(0.0, SURPRISE_SD, len(dates))
    return pd.DataFrame(
        {"actual_change_mbbl": round_to(actual, 1), "expected_change_mbbl": round_to(consensus, 1)},
        index=dates,
    )


def make_prices(dates: pd.DatetimeIndex, inventory: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """XLE and XOM closes. Also returns XLE's standardized shocks, which WTI reuses."""
    n = len(dates)
    xle_shock = stream(0).standard_normal(n)
    xle_ret = XLE_MEAN + XLE_SD * xle_shock
    xom_ret = XOM_BETA * xle_ret + stream(1).normal(0.0, XOM_NOISE_SD, n)

    surprise = inventory["actual_change_mbbl"] - inventory["expected_change_mbbl"]
    for report_date in surprise[surprise <= DRAW_THRESHOLD_MBBL].index:
        first = dates.searchsorted(report_date, side="right")  # trading day after the report
        xom_ret[first : first + DRIFT_DAYS] += DRIFT_PER_DAY

    xle_ret[0] = xom_ret[0] = 0.0  # day one is the starting price
    prices = pd.DataFrame(
        {
            "XOM": round_to(XOM_START * np.exp(np.cumsum(xom_ret)), 2),
            "XLE": round_to(XLE_START * np.exp(np.cumsum(xle_ret)), 2),
        },
        index=dates,
    )
    return prices, xle_shock


def make_wti(dates: pd.DatetimeIndex, xle_shock: np.ndarray) -> pd.DataFrame:
    own = stream(4).standard_normal(len(dates))
    shock = WTI_CORR_WITH_XLE * xle_shock + np.sqrt(1 - WTI_CORR_WITH_XLE**2) * own
    log_ret = WTI_SD * shock
    log_ret[0] = 0.0
    return pd.DataFrame({"wti": round_to(WTI_START * np.exp(np.cumsum(log_ret)), 2)}, index=dates)


def make_vix(dates: pd.DatetimeIndex) -> pd.DataFrame:
    n = len(dates)
    noise = stream(5).normal(0.0, VIX_NOISE_SD, n)
    jumps = np.zeros(n)
    for day, peak in VIX_SPIKES.items():
        if dates[0] <= pd.Timestamp(day) <= dates[-1]:
            jumps[dates.get_loc(pd.Timestamp(day))] = np.log(peak / VIX_LEVEL)

    calm, spike = np.zeros(n), np.zeros(n)
    for t in range(1, n):
        calm[t] = VIX_PERSISTENCE * calm[t - 1] + noise[t]
        spike[t] = SPIKE_PERSISTENCE * spike[t - 1] + jumps[t]
    return pd.DataFrame({"vix": round_to(VIX_LEVEL * np.exp(calm + spike), 2)}, index=dates)


def main() -> None:
    dates = pd.bdate_range(START, END, name="date")
    inventory = make_inventory(START, END)
    prices, xle_shock = make_prices(dates, inventory)
    tables = {
        "prices": prices,
        "inventory": inventory,
        "wti": make_wti(dates, xle_shock),
        "vix": make_vix(dates),
    }
    for name, table in tables.items():
        table.to_csv(OUT_DIR / f"{name}.csv", date_format="%Y-%m-%d")
        print(f"Wrote {OUT_DIR / name}.csv: {len(table)} rows, {table.index[0].date()} to {table.index[-1].date()}")


if __name__ == "__main__":
    main()
