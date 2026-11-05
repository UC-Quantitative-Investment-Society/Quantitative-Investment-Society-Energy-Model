"""Turn the Earth Engine MTAI export into data/raw/mtai.csv.

The satellite extraction runs in Earth Engine and exports one row per Landsat
scene per roof polygon:
    system:index, date, name, temp_c, valid, CLOUD_COVER, .geo
where name is facility, comp1, comp2 or comp3, temp_c is the mean surface
temperature in Celsius and valid is the fraction of the polygon's pixels that
survived the pixel mask. This script only cleans the Earth Engine export, no
contact occuring.

Run from the repo root:
    python -m backtesting.mtai_data    # data/exports/mtai_raw.csv, config test window
    python -m backtesting.mtai_data --export <path-to>/mtai_raw.csv --start 2018-01-01

Output, in the same layout as data/sample/mtai.csv:
    data/raw/mtai.csv  (columns date, facility, comp1, comp2, comp3; degrees C)
so a signal reads data["mtai"]["facility"] on both sample and raw data.
Then backtest on the real data:
    python -m backtesting.engine --data raw

Scenes with CLOUD_COVER above 20 percent are dropped whole, because cloud tops
read far colder than a roof and show up as large negative spikes in the signal.
Readings that kept less than half their pixels after masking are dropped too.
A date needs the facility and at least 2 of the 3 comps to be kept. Each filter's
removals are counted and printed.

Older exports name the cloud column cloud_cover; it is read as CLOUD_COVER.
"""

import argparse
import io
from pathlib import Path

import pandas as pd

from backtesting import config

# Roof polygons in the export: the GE Vernova Greenville facility and three comparison roofs.
POLYGONS = ["facility", "comp1", "comp2", "comp3"]
COMPS = POLYGONS[1:]
DEFAULT_EXPORT = config.RAW_DATA_DIR.parent / "exports" / "mtai_raw.csv"

MAX_CLOUD_COVER = 20.0  # scene-level Landsat CLOUD_COVER, percent
MIN_VALID = 0.5         # minimum fraction of a polygon's pixels left after masking
MIN_COMPS = 2           # comps a date needs to keep it

# Landsat scene id inside system:index, e.g. "1_LC08_018036_20180102_000...".
SCENE_ID_PATTERN = r"(LC0[89]_\d{6}_\d{8})"


def parse_mtai_csv(
    text: str,
    start: str | None = None,
    end: str | None = None,
    max_cloud: float | None = MAX_CLOUD_COVER,
    min_valid: float = MIN_VALID,
    min_comps: int = MIN_COMPS,
) -> tuple[pd.DataFrame, dict]:
    """Turn the Earth Engine export text into a date-indexed frame of temperatures.

    The export has one row per scene per polygon:
        system:index,date,name,temp_c,valid,CLOUD_COVER
        1_LC08_018036_20180102_0..0,2018-01-02,facility,6.41,0.74,12.3
        1_LC08_018036_20180102_0..1,2018-01-02,comp1,2.80,0.44,12.3
        1_LC08_018036_20180102_0..3,2018-01-02,comp3,4.55,1.00,12.3
        1_LC08_018036_20180118_0..0,2018-01-18,facility,9.12,0.91,4.0
        1_LC08_018036_20180118_0..1,2018-01-18,comp1,5.30,0.88,4.0
        1_LC08_018036_20180118_0..2,2018-01-18,comp2,5.95,0.97,4.0
        1_LC08_018036_20180118_0..3,2018-01-18,comp3,4.71,0.63,4.0
        1_LC08_018036_20180203_0..0,2018-02-03,facility,-3.20,0.95,63.0
    and parse_mtai_csv(text) returns (frame, counts), where frame is
        date        facility  comp1  comp2  comp3
        2018-01-18  9.12      5.30   5.95   4.71
    and counts is
        {"cloudy_scenes": 1, "low_valid_readings": 1, "dropped_dates": 2}
    2018-02-03 is a cloudy scene. On 2018-01-02 comp1 fails min_valid and comp2
    was never imaged, which leaves 1 comp.

    start and end (inclusive, YYYY-MM-DD) clip the dates before counting, so the
    counts only cover the window that is kept.
    max_cloud=None skips the cloud filter, for exports made without CLOUD_COVER.
    """
    raw = pd.read_csv(io.StringIO(text))
    raw.columns = [c.strip() for c in raw.columns]
    raw = raw.rename(columns={"cloud_cover": "CLOUD_COVER"})
    needed = ["system:index", "date", "name", "temp_c", "valid"]
    if max_cloud is not None:
        needed.append("CLOUD_COVER")
    missing_cols = [c for c in needed if c not in raw.columns]
    if missing_cols:
        hint = (" Add the scene's CLOUD_COVER property to each feature in the Earth Engine export,"
                " or pass --no-cloud-filter.") if "CLOUD_COVER" in missing_cols else ""
        raise ValueError(f"MTAI export is missing columns {missing_cols}.{hint}")

    unknown = set(raw["name"]) - set(POLYGONS)
    if unknown:
        raise ValueError(f"MTAI export has unexpected polygon names {sorted(unknown)}, expected {POLYGONS}")

    raw["date"] = pd.to_datetime(raw["date"])
    raw["scene"] = raw["system:index"].str.extract(SCENE_ID_PATTERN, expand=False)
    if start is not None:
        raw = raw[raw["date"] >= pd.Timestamp(start)]
    if end is not None:
        raw = raw[raw["date"] <= pd.Timestamp(end)]
    all_dates = raw["date"].unique()

    cloudy_scenes = 0
    if max_cloud is not None:
        cloudy = raw["CLOUD_COVER"] > max_cloud
        cloudy_scenes = raw.loc[cloudy, "scene"].nunique()
        raw = raw[~cloudy]

    low_valid = raw["valid"] < min_valid
    low_valid_readings = int(low_valid.sum())
    raw = raw[~low_valid]

    if raw.duplicated(["date", "name"]).any():
        raise ValueError("MTAI export has two readings for the same date and polygon")
    wide = raw.pivot(index="date", columns="name", values="temp_c").reindex(columns=POLYGONS)
    keep = wide["facility"].notna() & (wide[COMPS].notna().sum(axis=1) >= min_comps)
    frame = wide[keep].astype(float)
    frame.index.name = "date"
    frame.columns.name = None

    counts = {
        "cloudy_scenes": int(cloudy_scenes),
        "low_valid_readings": low_valid_readings,
        "dropped_dates": int(len(all_dates) - len(frame)),
    }
    return frame.sort_index(), counts


def load_export(path: str | Path, start: str, end: str, max_cloud: float | None) -> tuple[pd.DataFrame, dict]:
    """Read and clean one Earth Engine export file between start and end (inclusive).

    Returns the frame and the counts from parse_mtai_csv for that window.
    Example: load_export("data/exports/mtai_raw.csv", "2018-01-01", "2018-12-31", 20.0)
    gives a frame with columns facility, comp1, comp2, comp3 and one row per
    clear Landsat date in 2018.
    """
    with open(path, encoding="utf-8") as f:
        frame, counts = parse_mtai_csv(f.read(), start, end, max_cloud=max_cloud)
    if frame.empty:
        raise RuntimeError(f"No usable MTAI dates in {path} between {start} and {end}")
    return frame, counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean the Earth Engine MTAI export into data/raw/mtai.csv")
    parser.add_argument("--export", default=str(DEFAULT_EXPORT), help="path to the Earth Engine CSV export")
    parser.add_argument("--start", default=config.TEST_START, help="first date, YYYY-MM-DD")
    parser.add_argument("--end", default=config.TEST_END, help="last date, YYYY-MM-DD")
    parser.add_argument("--max-cloud", type=float, default=MAX_CLOUD_COVER,
                        help="drop scenes with CLOUD_COVER above this percent")
    parser.add_argument("--no-cloud-filter", action="store_true",
                        help="skip the cloud filter (only for exports without CLOUD_COVER)")
    args = parser.parse_args()

    max_cloud = None if args.no_cloud_filter else args.max_cloud
    if max_cloud is None:
        print("WARNING: cloud filter off. Cloudy scenes cause large negative spikes in the signal.")
    frame, counts = load_export(args.export, args.start, args.end, max_cloud)
    if any(counts.values()):
        print(f"Dropped {counts['cloudy_scenes']} cloudy scenes, {counts['low_valid_readings']} readings "
              f"below valid={MIN_VALID}, and {counts['dropped_dates']} dates in total")

    config.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = config.RAW_DATA_DIR / "mtai.csv"
    frame.to_csv(out, date_format="%Y-%m-%d", float_format="%.3f")
    print(f"Wrote {len(frame)} dates of MTAI "
          f"({frame.index[0].date()} to {frame.index[-1].date()}) to {out}")


if __name__ == "__main__":
    main()