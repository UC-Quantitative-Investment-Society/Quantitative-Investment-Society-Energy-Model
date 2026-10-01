# Role: Signal Integration (6)

Implement each signed handoff sheet as a signal module, exactly to spec. No
discretion over parameters.

## 1. What you own

- `signals/<name>.py` : one module per signal
- `signals/_template.py` : starting point for every new signal
- `signals/__init__.py` : the `ACTIVE_SIGNALS` registry, read by the engine and the tests
- `tests/test_signals.py` : the signal contract

## 2. What you receive, and from whom

From **quant research**: a handoff sheet (`docs/signal_handoff_template.md`)
with name, hypothesis, data source, condition + threshold, instrument,
direction, hold period, and output type, signed by both the quant researcher
and the quant director. No sign-offs, no implementation.

## 3. What you hand off, and to whom

To **Backtesting**: a merged PR where

- `signals/<name>.py` exports `compute_signal(data) -> pd.Series` with a `DatetimeIndex`
- module constants `INSTRUMENT`, `DIRECTION`, `HOLD_DAYS` match the sheet
  (the engine and `pytest` reject the template placeholders `"TODO"` and `0`)
- the signal is registered in `ACTIVE_SIGNALS`
- `pytest` is green

## 4. Step-by-step: one new signal

1. Read the full sheet; confirm both sign-offs.
2. Resolve any ambiguity with the analyst in writing (e.g. units of the threshold).
3. `git checkout -b signals/add-<name>`
4. `cp signals/_template.py signals/<name>.py`
5. Set `INSTRUMENT`, `DIRECTION`, `HOLD_DAYS`, and the threshold constant from the sheet.
6. Implement `compute_signal(data)`. `data` is a dict of date-indexed DataFrames
   (`data["prices"]`, `data["inventory"]`, ...). Each value at date t may use only information available at t.
7. Docstring must state `Output type: bool` or `Output type: score (float)`.
8. Register in `signals/__init__.py`.
9. `pytest`.
10. Open a PR with the sheet in the description. One signal per PR.

### Output type

| Type | Values | Use when | Example |
|------|--------|----------|---------|
| bool | `True` / `False` | binary condition | surprise <= -2.0 mbbl |
| score | float | research wants magnitude retained | `(-surprise).where(surprise <= -2.0, 0.0)` |

The engine treats score > 0 as a fire, so the threshold lives inside the function.

### Trade signals and filters

Each module sets `ROLE`. A module without it is a trade signal.

| `ROLE` | What it does | Needs `INSTRUMENT`, `DIRECTION`, `HOLD_DAYS` | Output | Example |
|--------|--------------|----------------------------------------------|--------|---------|
| `"trade"` | backtested and traded on its own | yes | bool or score | XLE closes above its 200-day average |
| `"filter"` | switches trade signals on and off; never traded alone | no | bool, True = OK to trade | VIX below 30 |

`python -m backtesting.engine` skips filters and prints, for example,
`vix_filter: filter, not traded alone`. Register a filter in `ACTIVE_SIGNALS`
like any other module so `tests/test_signals.py` checks it returns bool.

A filter only has an effect once a trade signal applies it, as its handoff
sheet specifies. The trade signal imports the filter and combines the two:

```python
from signals import vix_filter

def compute_signal(data: dict) -> pd.Series:
    """... Output type: bool."""
    xle_trend_fires = ...  # this signal's own bool Series, built from its handoff sheet
    ok_to_trade = vix_filter.compute_signal(data).reindex(xle_trend_fires.index, fill_value=False)
    return (xle_trend_fires & ok_to_trade).astype(bool)
```

`fill_value=False`: a date with no filter value is a date we do not trade.
Applying a filter changes the trade signal's spec, so it needs a new handoff
sheet and a new version (`xle_trend_v2`), not an edit to the existing module.

## 5. Worked example: oil inventory surprise

Spec: fire when actual minus consensus <= -2.0 mbbl; XOM, long, 5 days, bool.

Sample rows from `data["inventory"]`:

| date | actual_change_mbbl | expected_change_mbbl | surprise | fires |
|------|--------------------|----------------------|----------|-------|
| 2019-01-09 | +0.4 | -3.0 | +3.4 | no |
| 2019-01-16 | -1.1 | +2.5 | -3.6 | yes |
| 2019-01-30 | +3.8 | +5.6 | -1.8 | no (not <= -2.0) |

`signals/oil_inventory_surprise.py`:

```python
INSTRUMENT = "XOM"
DIRECTION = "long"
HOLD_DAYS = 5
THRESHOLD_MBBL = -2.0  # fire when (actual - expected) <= this, in millions of barrels

def compute_signal(data: dict) -> pd.Series:
    """Return True on each report date where the draw beat expectations by 2M+ barrels.

    Output type: bool.
    """
    inv = data["inventory"]
    surprise = inv["actual_change_mbbl"] - inv["expected_change_mbbl"]
    fires = surprise <= THRESHOLD_MBBL
    fires.name = "oil_inventory_surprise"
    return fires.astype(bool)
```

Sign convention: a larger-than-expected draw is more negative, so the test is `<= -2.0`.

Registration:

```python
from signals import oil_inventory_surprise

ACTIVE_SIGNALS = {
    "oil_inventory_surprise": oil_inventory_surprise.compute_signal,
}
```

Sanity check:

```bash
python -c "from backtesting.engine import load_sample_data; from signals import ACTIVE_SIGNALS; \
s = ACTIVE_SIGNALS['oil_inventory_surprise'](load_sample_data()); print(s.sum())"
# 79
```

## 6. Definition of done

- [ ] Both sign-offs on the sheet
- [ ] `signals/<name>.py` started from `_template.py`
- [ ] `INSTRUMENT`, `DIRECTION`, `HOLD_DAYS`, threshold match the sheet exactly
- [ ] `compute_signal(data)` returns a Series with a `DatetimeIndex`
- [ ] Values all bool or all float, matching the sheet
- [ ] Docstring states the output type
- [ ] Registered in `ACTIVE_SIGNALS`
- [ ] `pytest` green
- [ ] PR contains only this signal, links the sheet, 1 approval

## 7. Common mistakes

**Tuning parameters.** Changing -2.0 to -1.5 because the backtest improves is
overfitting. Parameters change only through a new sheet and a `_v2` signal.

**Lookahead.** `inv["actual_change_mbbl"].shift(-1)` uses next week's report.
`surprise / surprise.std()` normalizes with full-sample statistics. Use
`.shift(1)` or trailing windows (`surprise.rolling(52).std()`).

**Wrong index.** `fires.reset_index(drop=True)` returns a RangeIndex; the
engine cannot align it to prices and `tests/test_signals.py` fails.

**Wrong dtype.** Intermediate steps can produce `object` dtype, which the engine
rejects. End with `.astype(bool)` or `.astype(float)`.

**Not registered.** A module missing from `ACTIVE_SIGNALS` never runs.
