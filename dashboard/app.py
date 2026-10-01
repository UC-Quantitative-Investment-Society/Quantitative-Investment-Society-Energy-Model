"""Minimal results dashboard.

Run from the repo root:
    streamlit run dashboard/app.py

This page only READS files from backtesting/results/<signal_name>/.
It never recomputes anything. If a number looks wrong, fix the engine or the
signal and re-run `python -m backtesting.engine`, never patch it here.
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

RESULTS_DIR = Path(__file__).resolve().parent.parent / "backtesting" / "results"


def load_results() -> dict:
    """Return {signal_name: stats_dict} for every results folder with a stats.json."""
    results = {}
    for stats_file in sorted(RESULTS_DIR.glob("*/stats.json")):
        with open(stats_file) as f:
            results[stats_file.parent.name] = json.load(f)
    return results


st.set_page_config(page_title="QIS Energy Signals", layout="wide")
st.title("QIS Energy Signals: backtest results")
st.caption("Data source per signal: sample = synthetic, raw = Alpaca historical prices. Paper trading only.")

results = load_results()
if not results:
    st.info("No results yet. Run `python -m backtesting.engine` from the repo root, then refresh.")
    st.stop()

# 1. What the director needs first: one row per signal with the verdict.
st.header("Summary")
summary = pd.DataFrame(
    [
        {
            "signal": name,
            "verdict": s["verdict"],
            "ticker": s["ticker"],
            "n_fires": s["n_fires"],
            "win rate": f"{s['win_rate']:.0%}",
            f"avg excess vs {s['benchmark']} per trade": f"{s['avg_excess_vs_benchmark']:.2%}",
            "Sharpe": round(s["sharpe"], 2),
            "max drawdown": f"{s['max_drawdown']:.0%}",
            "out-of-sample avg excess": f"{s['out_of_sample']['avg_excess_vs_benchmark']:.2%}",
        }
        for name, s in results.items()
    ]
)
st.dataframe(summary, hide_index=True, width="stretch")

# 2. One panel per signal. New signals appear here automatically once their
#    results folder exists.
st.header("Signals")
for name, s in results.items():
    with st.expander(f"{name}: {s['verdict']}", expanded=True):
        cols = st.columns(5)
        cols[0].metric("Fires", s["n_fires"], help=f"Minimum is {s['min_fires']}")
        cols[1].metric("Win rate", f"{s['win_rate']:.0%}")
        cols[2].metric("Total return", f"{s['total_return']:.0%}", f"{s['excess_return']:+.0%} vs {s['benchmark']}")
        cols[3].metric("Sharpe", f"{s['sharpe']:.2f}")
        cols[4].metric("Max drawdown", f"{s['max_drawdown']:.0%}")
        st.write(
            f"Trades {s['ticker']} {s['direction']} for {s['hold_days']} days, "
            f"{s['cost_bps']} bps cost per side, tested {s['test_start']} to {s['test_end']}, "
            f"data: {s.get('data_source', 'sample')}."
        )
        split = pd.DataFrame(
            {"in-sample": s["in_sample"], "out-of-sample": s["out_of_sample"]}
        ).T[["n_fires", "n_trades", "win_rate", "avg_excess_vs_benchmark", "sharpe"]]
        st.dataframe(split.round(3), width="stretch")
        png = RESULTS_DIR / name / "equity_curve.png"
        if png.exists():
            st.image(str(png), caption=f"Growth of $1: {name} vs {s['benchmark']}")
        if s["suspicious"]:
            st.warning("Sharpe above the suspicious limit: treat as a bug until proven otherwise.")
