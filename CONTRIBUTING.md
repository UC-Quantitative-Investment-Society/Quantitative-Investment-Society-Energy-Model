# Contributing

## Rules

1. **No direct pushes to `main`.** All changes go through a pull request.
2. **At least 1 approving review** before merge. No self-approval.
3. **One signal per PR.** A PR adding `crack_spread.py` must not touch `oil_inventory_surprise.py`.
4. **Code owner approval.** `.github/CODEOWNERS` auto-requests the role lead for
   every path a PR touches (e.g. `backtesting/` requests the Backtesting lead).
   A PR spanning two roles needs both leads. `execution/orders.py`,
   `execution/risk.py`, and `.env.example` also require the repo owner.

## Branches

Branch from the latest `main` as `<team>/<short-description>`:

| Team | Example |
|------|---------|
| Signal Integration | `signals/add-crack-spread` |
| Backtesting | `backtesting/fix-sharpe-annualization` |
| Execution & Risk | `execution/lower-daily-loss-limit` |
| Front-End & Reporting | `dashboard/add-drawdown-chart` |

```bash
git checkout main && git pull
git checkout -b signals/add-crack-spread
git add signals/crack_spread.py signals/__init__.py
git commit -m "Add crack spread signal (handoff signed 2026-10-01)"
git push -u origin signals/add-crack-spread
```

## PR requirements

- Title states the change, e.g. "Add crack spread signal v1".
- Description links the signed handoff sheet (signals) or states the rationale (everything else).
- `pytest` green locally; paste the summary line.
- No secrets. Keys live only in your git-ignored `.env`.

## Review checklist

- Signals: every parameter matches the handoff sheet exactly.
- Backtesting: changes land in the shared `backtesting/engine.py`, never a private copy.
- Execution: nothing points anywhere but the Alpaca paper endpoint.
- Dashboard: reads result files only; no recomputation.

## Changing testing standards

`backtesting/config.py` applies to every signal. Changes require Backtesting
lead approval and a rerun of every active signal in the same PR.
