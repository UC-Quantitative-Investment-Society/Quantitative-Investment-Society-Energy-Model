"""Shared testing standards, owned by engineering and identical for every signal.

Changes require Backtesting lead approval and a rerun of every active signal.
"""

from pathlib import Path

# Benchmark for every signal.
BENCHMARK = "XLE"

# Full test window (inclusive). Data outside this window is ignored.
TEST_START = "2019-01-01"
TEST_END = "2023-12-31"

# Out-of-sample holdout starts here (inclusive). Not used during signal research.
OUT_OF_SAMPLE_START = "2022-07-01"

# Cost per side in basis points (charged on entry and on exit).
COST_BPS = 5

# Minimum fires in the test window for a signal to be eligible for PASS.
MIN_FIRES = 30

# Full-sample Sharpe above this triggers a REVIEW verdict (presumed bug until cleared).
SUSPICIOUS_SHARPE = 3.0

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "backtesting" / "results"
SAMPLE_DATA_DIR = REPO_ROOT / "data" / "sample"  # synthetic, always available offline
RAW_DATA_DIR = REPO_ROOT / "data" / "raw"  # real data you download (git-ignored)
