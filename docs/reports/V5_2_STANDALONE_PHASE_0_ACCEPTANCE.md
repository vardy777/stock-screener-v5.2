# V5.2 Standalone Phase 0 Acceptance

Acceptance date: 2026-09-06  
Tested source commit: `dc96e48005939561b2b93920c2f54a278a782ae8`  
Python: `3.12.4`

## Results

| Gate | Result | Evidence |
|---|---|---|
| Standalone package | PASS | `src/v5_2`, own `pyproject.toml`, no external runtime dependencies |
| Package install | PASS | non-editable `pip install .` completed |
| Full local tests | PASS | `20 passed in 0.16s` |
| Forbidden imports | PASS | 0 imports from `g1`, `v2`, `v4`, `v5`, `v5_1`, `shared_core` |
| Forbidden active paths/dependencies | PASS | 0 old/local/editable/Git dependency findings |
| Repository inventory | PASS | 0 prohibited root or runtime asset findings |
| Clean-room dependencies | PASS | pinned tool requirements installed in new temporary venv |
| Clean-room package install | PASS | package installed from isolated source copy |
| Clean-room tests | PASS | `20 passed in 0.14s` |
| Wheel build | PASS | `stock_screener_v5_2-5.2.0-py3-none-any.whl` |
| Source distribution build | PASS | `stock_screener_v5_2-5.2.0.tar.gz` |
| Archive scan | PASS | both archives contained 0 prohibited members |
| Wheel install and smoke | PASS | fresh venv printed version `5.2.0`; safety gates true/false as required |
| Old PYTHONPATH removed | PASS | clean-room environment contained no `PYTHONPATH` |

## Scope

Copied and V5.2-owned behavior is limited to strict validation/timezone,
TradingCalendar and calendar validation, canonical content hashing, immutable
atomic fact persistence and A-share quantity rules. No earlier namespace or
source path remains in the installed package.

Realtime providers, MorningPool, CloseScan, execution choreography,
notifications, schedulers, dashboards, production runtime, RC archives and
runtime facts were excluded.

## Verdict

```text
ZERO PROJECT DEPENDENCY = PASS
READY FOR HISTORICAL PIT DATA PHASE = YES
```

This verdict covers repository/package independence only. Historical PIT data,
survivorship safety, DailyBar/corporate-action correctness, feature/label
determinism, alpha and production readiness remain unproven and out of scope.
