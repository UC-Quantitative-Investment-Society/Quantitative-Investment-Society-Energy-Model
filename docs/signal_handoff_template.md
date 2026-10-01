# Signal Handoff Sheet

One sheet per signal. Engineering does not start implementation until both
sign-offs (quant researcher and quant director) are recorded. The
implementation follows the sheet exactly; any parameter change requires a new
sheet and a new version (`_v2`, `_v3`).

**Ownership:**

- **Research owns the signal spec**: condition, threshold, instrument, direction, hold period.
- **Engineering owns the testing standards**: benchmark, test window,
  out-of-sample split, costs, minimum fires. These are fixed across signals in
  `backtesting/config.py` and are not negotiable per signal.

## Field spec

| Field | Requirement | Example |
|-------|-------------|---------|
| Signal name | snake_case module name; version suffix for revisions | `oil_inventory_surprise` |
| Hypothesis | the economic rationale, one or two sentences | Supply shock not priced in at release |
| Data source | provider, series, release schedule | EIA weekly petroleum status report, Wednesdays |
| Condition + threshold | exact rule with units | actual minus consensus <= -2.0 mbbl |
| Instrument | ticker | `XOM` |
| Direction | long or short | long |
| Hold period | trading days after entry | 5 |
| Output type | `bool` (fires / does not) or `score` (float; > 0 fires) | bool |

## Blank template

Paste into the signal's PR description and attach the signed copy.

---

**Signal name:**

**Hypothesis:**

**Data source:**

**Condition + threshold:**

**Instrument:**

**Direction:**

**Hold period (trading days):**

**Output type (bool / score):**

**Analyst:**

**Sign-off, quant researcher (name, date):**

**Sign-off, quant director (name, date):**

**Date submitted:**

---

## Example

---

**Signal name:** oil_inventory_surprise

**Hypothesis:** A crude draw at least 2M bbl larger than consensus indicates
tighter supply than priced. Integrated producers drift higher over the
following week as the market reprices.

**Data source:** Weekly crude inventory change (actual) and pre-release
consensus (expected). Released Wednesdays. Offline sample:
`data/sample/inventory.csv` (synthetic).

**Condition + threshold:** surprise = actual_change_mbbl - expected_change_mbbl;
fire when surprise <= -2.0 mbbl.

**Instrument:** XOM

**Direction:** long

**Hold period (trading days):** 5

**Output type (bool / score):** bool

**Analyst:** A. Analyst

**Sign-off, quant researcher (name, date):** R. Researcher, 2026-09-22

**Sign-off, quant director (name, date):** D. Director, 2026-09-23

**Date submitted:** 2026-09-21

---
