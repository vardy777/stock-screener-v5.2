# Stock Screener V5.2

Standalone after-close A-share Alpha Research and Swing Candidate Engine.
V5.2 will reconstruct a point-in-time eligible universe, calculate causal
features, rank the market and evaluate Watchlist 50 / Top 20 / Top 10 / Top 5
over future 1-5 trading sessions.

## Current phase

Standalone Phase 0 provides only the independent package, governance gates and
foundation primitives. It does not yet contain historical datasets, features,
labels, ranking or a strategy, and there is no evidence that alpha exists.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test,build]"
.\.venv\Scripts\python.exe -m pytest
```

Editable installation is for this repository only. Local-path or old-project
dependencies are prohibited. The package must also pass a non-editable wheel
installation in clean-room acceptance.

## Hard safety boundary

`research_locked=true`; broker orders are disabled. V5.2 does not provide live
trading, automatic orders, full-market realtime scanning, notifications or
scheduler registration. AlphaScore is a future deterministic research score,
not an上涨概率 or profitability claim.
