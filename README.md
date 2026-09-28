# Stock Screener V5.2

Standalone after-close A-share Alpha Research and Swing Candidate Engine.
V5.2 will reconstruct a point-in-time eligible universe, calculate causal
features, rank the market and evaluate Watchlist 50 / Top 20 / Top 10 / Top 5
over future 1-5 trading sessions.

## Current phase

Phase 0 is PASS / FROZEN. Phase 1 is PASS under explicit fail-closed,
scoped-gap governance; it is not a claim of 100% historical data coverage.
Daily Bar missing symbol-sessions remain fail-closed. Security Master
membership is 5,551: 5,549 resolved and two scoped parent-member quarantines.
Phase 2A Label Engine and Phase 2B historical label infrastructure through
Checkpoint 18 are PASS / FROZEN. The exact Task 12 preregistered four-candidate
Checkpoint 19 pilot has run and passed its frozen engineering predicates; its
independent GitHub review is pending. This small pilot is not an Alpha study.
Phase 3 features and ranking have not started. Alpha existence and
profitability are **not proven**.

The machine-readable current state is in `governance/project-state.json`.
Checkpoint 18's public hash-only acceptance capsule is
`c2ff1d3ff8ffffd49279af39b7bb539a251f226e82923b85bf9234470a53f310`.
The feature branch holds this authority; `main` remains unchanged and stale.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test,build]"
.\.venv\Scripts\python.exe -m pytest
```

Editable installation is for this repository only. Local-path or old-project
dependencies are prohibited. The package must also pass a non-editable wheel
installation in clean-room acceptance.

## Manual data refresh

Phase 1C exposes one backend entrypoint for CLI and future API/frontend callers:

```powershell
.\.venv\Scripts\python.exe scripts\refresh_data.py
```

`CURRENT` means a valid immutable snapshot is ready for the resolved latest
completed trading session. `STALE` means the last valid snapshot predates that
target, `INCOMPLETE` means some required dataset did not become ready, and
`FAILED` means target resolution or refresh execution failed. On failure, use
the reported dataset reasons and retry; the last successful snapshot remains
unchanged and is never presented as current.

## Hard safety boundary

`research_locked=true`; broker orders are disabled. V5.2 does not provide live
trading, automatic orders, full-market realtime scanning, notifications or
scheduler registration. AlphaScore is a future deterministic research score,
not an上涨概率 or profitability claim.
