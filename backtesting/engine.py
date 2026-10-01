"""The shared backtest engine. One engine for every signal.

Run the example on sample data from the repo root:

    python -m backtesting.engine

To use real prices downloaded from Alpaca (see backtesting/alpaca_data.py):

    python -m backtesting.engine --data raw

That runs every signal in signals.ACTIVE_SIGNALS and writes, per signal:
    backtesting/results/<signal_name>/stats.json
    backtesting/results/<signal_name>/equity_curve.png

Timing rule (no lookahead): a signal dated day t is only known at the end of
day t, so we enter at the close of the FIRST trading day after t and exit
hold_days trading days later. Example: the report on Wednesday 2019-05-22 fires,
we buy at the close on Thursday 2019-05-23 and, with hold_days=5, sell at the
close on 2019-05-30.

Do not copy this file to make a private version. If the engine needs a
change, open a PR so every signal gets the fix.
"""

import argparse
import json
import sys

import matplotlib

matplotlib.use("Agg")  # draw to files, no window needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from backtesting import config

TRADING_DAYS_PER_YEAR = 252


def load_data(source: str = "sample") -> dict:
    """Load every CSV in data/sample/ or data/raw/ as a date-indexed DataFrame.

    Each file becomes one entry named after the file, so data/raw/prices.csv
    becomes data["prices"]. Every CSV must have a "date" column.
    Example: load_data("raw") after running backtesting/alpaca_data.py gives
    {"prices": DataFrame with columns XOM, XLE}.
    """
    folder = {"sample": config.SAMPLE_DATA_DIR, "raw": config.RAW_DATA_DIR}[source]
    files = sorted(folder.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files in {folder}. For raw data run: python -m backtesting.alpaca_data")
    return {f.stem: pd.read_csv(f, parse_dates=["date"], index_col="date") for f in files}


def load_sample_data() -> dict:
    """Load the synthetic CSVs in data/sample/: {"prices": ..., "inventory": ...}."""
    return load_data("sample")


def signal_params(signal_fn) -> dict:
    """Read INSTRUMENT, DIRECTION, HOLD_DAYS from the signal's module and check them.

    Catches a signal copied from signals/_template.py with the placeholders left in.
    Example: {"ticker": "XOM", "direction": "long", "hold_days": 5}.
    """
    module = sys.modules[signal_fn.__module__]
    name = signal_fn.__module__
    ticker = getattr(module, "INSTRUMENT", None)
    direction = getattr(module, "DIRECTION", None)
    hold_days = getattr(module, "HOLD_DAYS", None)
    if not isinstance(ticker, str) or not ticker or ticker == "TODO":
        raise ValueError(f"{name}: INSTRUMENT must be a ticker from the handoff sheet, got {ticker!r}")
    if direction not in ("long", "short"):
        raise ValueError(f"{name}: DIRECTION must be 'long' or 'short', got {direction!r}")
    if not isinstance(hold_days, int) or hold_days < 1:
        raise ValueError(f"{name}: HOLD_DAYS must be a whole number of trading days >= 1, got {hold_days!r}")
    return {"ticker": ticker, "direction": direction, "hold_days": hold_days}


def _fires_from_signal(signal: pd.Series) -> pd.Series:
    """Turn a signal into True/False fires.

    bool signals fire where True. Score (float) signals fire where score > 0.
    Example: a score of 2.5 fires, 0.0 or -1.0 does not.
    """
    if not isinstance(signal, pd.Series) or not isinstance(signal.index, pd.DatetimeIndex):
        raise TypeError("compute_signal must return a pandas Series indexed by date")
    if signal.dtype == bool:
        fires = signal
    elif pd.api.types.is_float_dtype(signal):
        fires = signal.fillna(0.0) > 0
    else:
        raise TypeError(f"signal values must be bool or float, got {signal.dtype}")
    return fires.sort_index()


def _max_drawdown(equity: pd.Series) -> float:
    """Worst peak-to-trough drop. Example: 1.20 falling to 0.90 is -0.25."""
    if equity.empty:
        return 0.0
    return float((equity / equity.cummax() - 1).min())


def _sharpe(daily_returns: pd.Series) -> float:
    """Annualized Sharpe ratio (risk-free rate taken as 0)."""
    std = daily_returns.std()
    if daily_returns.empty or not std or np.isnan(std):
        return 0.0
    return float(daily_returns.mean() / std * np.sqrt(TRADING_DAYS_PER_YEAR))


def _period_stats(
    daily: pd.Series, bench_px: pd.Series, bench_daily: pd.Series, trades: pd.DataFrame, n_fires: int
) -> dict:
    """Stats for one slice of time (full, in-sample, or out-of-sample)."""
    equity = (1 + daily).cumprod()
    total_return = float(equity.iloc[-1] - 1) if len(equity) else 0.0
    bench_return = float(bench_px.iloc[-1] / bench_px.iloc[0] - 1) if len(bench_px) else 0.0
    n_trades = len(trades)
    return {
        "n_fires": int(n_fires),
        "n_trades": n_trades,
        "win_rate": float((trades["net_return"] > 0).mean()) if n_trades else 0.0,
        "avg_trade_return": float(trades["net_return"].mean()) if n_trades else 0.0,
        "avg_excess_vs_benchmark": float(trades["excess_return"].mean()) if n_trades else 0.0,
        "total_return": total_return,
        "benchmark_return": bench_return,
        "sharpe": _sharpe(daily),
        "benchmark_sharpe": _sharpe(bench_daily),  # benchmark buy and hold over the same dates
        "max_drawdown": _max_drawdown(equity),
    }


def run_backtest(
    signal_fn,
    data: dict,
    ticker: str,
    hold_days: int,
    benchmark: str = config.BENCHMARK,
    cost_bps: float = config.COST_BPS,
    out_of_sample_start: str = config.OUT_OF_SAMPLE_START,
    direction: str = "long",
) -> dict:
    """Backtest one signal. Works for any signal that follows the signals/ contract.

    Returns a dict with:
        "stats":  numbers for the report (see stats.json for the full list)
        "equity": DataFrame with columns strategy and benchmark, both starting at 1.0
        "trades": DataFrame with one row per trade taken

    If the signal fires again while we are still holding (before the exit day), that fire is
    counted in n_fires but no second trade is opened (n_trades stays the same).

    How the signal is compared with the benchmark depends on what it trades
    (stats["comparison"]):

    "per_trade" (ticker != benchmark): each trade's net return is compared with the
        benchmark's move over the same holding window. Beating the benchmark means
        avg_excess_vs_benchmark > 0 both in-sample and out-of-sample.
        Example: long XOM for 5 days nets +1.8% while XLE moves +0.5%, so that
        trade's excess is +1.3%.

    "timing" (ticker == benchmark): per-trade excess is meaningless here, because
        every trade's excess is exactly minus the round-trip cost (-0.10% at 5 bps).
        The signal is judged on the whole period instead: beating the benchmark
        means a higher Sharpe than benchmark buy and hold over the same dates,
        both in-sample and out-of-sample.
        Example: an XLE trend signal with in-sample Sharpe 0.62 vs XLE 0.48 and
        out-of-sample Sharpe 0.71 vs XLE 0.55 beats the benchmark.

    In both modes the verdict also needs n_fires >= MIN_FIRES, and a Sharpe above
    SUSPICIOUS_SHARPE gives REVIEW instead of PASS.
    """
    if direction not in ("long", "short"):
        raise ValueError("direction must be 'long' or 'short'")
    if hold_days < 1:
        raise ValueError("hold_days must be at least 1")
    sign = 1 if direction == "long" else -1
    cost = cost_bps / 10_000
    comparison = "timing" if ticker == benchmark else "per_trade"

    prices = data["prices"].sort_index()
    px = prices[ticker]
    bench_px = prices[benchmark]
    dates = prices.index
    fires = _fires_from_signal(signal_fn(data))
    fire_dates = fires[fires].index
    fire_dates = fire_dates[(fire_dates >= dates[0]) & (fire_dates <= dates[-1])]

    daily = pd.Series(0.0, index=dates)
    stock_ret = px.pct_change().fillna(0.0)
    trades = []
    last_exit = -1
    for fire_date in fire_dates:
        entry_i = dates.searchsorted(fire_date, side="right")  # strictly AFTER the fire date
        exit_i = entry_i + hold_days
        if entry_i < last_exit or exit_i >= len(dates):
            continue  # still holding the last trade, or not enough data left to finish it
        gross = sign * (px.iloc[exit_i] / px.iloc[entry_i] - 1)
        bench_move = bench_px.iloc[exit_i] / bench_px.iloc[entry_i] - 1
        net = gross - 2 * cost
        trades.append(
            {
                "fire_date": fire_date,
                "entry_date": dates[entry_i],
                "exit_date": dates[exit_i],
                "entry_price": float(px.iloc[entry_i]),
                "exit_price": float(px.iloc[exit_i]),
                "gross_return": float(gross),
                "net_return": float(net),
                # Long: stock minus XLE. Short: how much the stock fell more than XLE.
                "excess_return": float(net - sign * bench_move),
            }
        )
        daily.iloc[entry_i + 1 : exit_i + 1] += sign * stock_ret.iloc[entry_i + 1 : exit_i + 1]
        daily.iloc[entry_i] -= cost
        daily.iloc[exit_i] -= cost
        last_exit = exit_i

    trades = pd.DataFrame(
        trades,
        columns=["fire_date", "entry_date", "exit_date", "entry_price", "exit_price",
                 "gross_return", "net_return", "excess_return"],
    )

    oos = pd.Timestamp(out_of_sample_start)
    is_mask = dates < oos
    trade_is = trades["fire_date"] < oos if len(trades) else pd.Series(dtype=bool)
    bench_daily = bench_px.pct_change().fillna(0.0)
    full = _period_stats(daily, bench_px, bench_daily, trades, len(fire_dates))
    in_sample = _period_stats(daily[is_mask], bench_px[is_mask], bench_daily[is_mask],
                              trades[trade_is], (fire_dates < oos).sum())
    out_sample = _period_stats(daily[~is_mask], bench_px[~is_mask], bench_daily[~is_mask],
                               trades[~trade_is], (fire_dates >= oos).sum())

    passes_min_fires = full["n_fires"] >= config.MIN_FIRES
    suspicious = full["sharpe"] > config.SUSPICIOUS_SHARPE
    if comparison == "timing":
        beats_bench = (in_sample["sharpe"] > in_sample["benchmark_sharpe"]
                       and out_sample["sharpe"] > out_sample["benchmark_sharpe"])
    else:
        beats_bench = in_sample["avg_excess_vs_benchmark"] > 0 and out_sample["avg_excess_vs_benchmark"] > 0
    if not passes_min_fires or not beats_bench:
        verdict = "REJECT"
    elif suspicious:
        verdict = "REVIEW"  # too good to be true: hunt for a bug before anyone trades it
    else:
        verdict = "PASS"

    stats = {
        "signal": getattr(signal_fn, "__module__", "unknown").split(".")[-1],
        "ticker": ticker,
        "benchmark": benchmark,
        "comparison": comparison,
        "direction": direction,
        "hold_days": hold_days,
        "cost_bps": cost_bps,
        "test_start": str(dates[0].date()),
        "test_end": str(dates[-1].date()),
        "out_of_sample_start": str(oos.date()),
        **full,
        "excess_return": full["total_return"] - full["benchmark_return"],
        "in_sample": in_sample,
        "out_of_sample": out_sample,
        "min_fires": config.MIN_FIRES,
        "passes_min_fires": bool(passes_min_fires),
        "suspicious": bool(suspicious),
        "verdict": verdict,
    }
    equity = pd.DataFrame({"strategy": (1 + daily).cumprod(), "benchmark": bench_px / bench_px.iloc[0]})
    return {"stats": stats, "equity": equity, "trades": trades}


def save_results(signal_name: str, result: dict) -> None:
    """Write stats.json and equity_curve.png to backtesting/results/<signal_name>/."""
    out_dir = config.RESULTS_DIR / signal_name
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "stats.json", "w") as f:
        json.dump(result["stats"], f, indent=2)

    stats = result["stats"]
    equity = result["equity"]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(equity.index, equity["strategy"], label=f"{signal_name} ({stats['ticker']})")
    ax.plot(equity.index, equity["benchmark"], label=f"{stats['benchmark']} buy and hold")
    ax.axvline(pd.Timestamp(stats["out_of_sample_start"]), color="gray", linestyle="--", label="out-of-sample starts")
    ax.set_title(f"{signal_name}: growth of $1 (verdict: {stats['verdict']})")
    ax.set_ylabel("value of $1")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "equity_curve.png", dpi=100)
    plt.close(fig)


def _clip_to_test_window(data: dict) -> dict:
    return {name: df.loc[config.TEST_START : config.TEST_END] for name, df in data.items()}


def main() -> None:
    from signals import ACTIVE_SIGNALS

    parser = argparse.ArgumentParser(description="Backtest every signal in ACTIVE_SIGNALS")
    parser.add_argument("--data", choices=["sample", "raw"], default="sample",
                        help="sample = synthetic data/sample/, raw = real data in data/raw/")
    args = parser.parse_args()

    data = _clip_to_test_window(load_data(args.data))
    for name, signal_fn in ACTIVE_SIGNALS.items():
        params = signal_params(signal_fn)  # INSTRUMENT, DIRECTION, HOLD_DAYS from the handoff sheet
        try:
            result = run_backtest(
                signal_fn,
                data,
                ticker=params["ticker"],
                hold_days=params["hold_days"],
                benchmark=config.BENCHMARK,
                cost_bps=config.COST_BPS,
                out_of_sample_start=config.OUT_OF_SAMPLE_START,
                direction=params["direction"],
            )
        except KeyError as missing:
            if args.data != "raw":
                raise  # sample data has every table, so this is a bug in the signal
            # Example: data/raw/ has prices.csv from Alpaca but no inventory.csv yet.
            print(f"{name}: SKIPPED, needs {missing} which is not in data/raw/")
            continue
        result["stats"]["data_source"] = args.data
        save_results(name, result)
        s = result["stats"]
        if s["comparison"] == "timing":
            vs_bench = (
                f"is_sharpe={s['in_sample']['sharpe']:.2f} vs {s['benchmark']} {s['in_sample']['benchmark_sharpe']:.2f} "
                f"oos_sharpe={s['out_of_sample']['sharpe']:.2f} vs {s['benchmark']} "
                f"{s['out_of_sample']['benchmark_sharpe']:.2f}"
            )
        else:
            vs_bench = (
                f"avg_excess_vs_{s['benchmark']}={s['avg_excess_vs_benchmark']:.2%} "
                f"oos_avg_excess={s['out_of_sample']['avg_excess_vs_benchmark']:.2%}"
            )
        print(
            f"{name}: verdict={s['verdict']} comparison={s['comparison']} n_fires={s['n_fires']} "
            f"n_trades={s['n_trades']} win_rate={s['win_rate']:.1%} sharpe={s['sharpe']:.2f} {vs_bench}"
        )
        print(f"  wrote {config.RESULTS_DIR / name}/stats.json and equity_curve.png")


if __name__ == "__main__":
    main()
