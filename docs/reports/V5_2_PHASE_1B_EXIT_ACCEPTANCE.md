# V5.2 Phase 1B Historical PIT Exit Acceptance

Starting HEAD: `aeddb63de444a318f61a0418dee961b891bba644`.

## Architecture Audit

The six existing domains remain authoritative; the Exit layer will only compose
and validate their artifacts.

| Dataset | Fact / policy / repository boundary | Current approval / manifest | Coverage and frozen limitation |
|---|---|---|---|
| Trading Calendar | `TradingCalendar`; approved calendar records; no replacement repository | `4a900c7e...a601` / `9653175f...8385` | approval 2010-01-01..2026-09-11; extension manifest 2026-01-01..2026-09-11 |
| Security Master / Universe | effective-dated identity/universe artifacts; historical-universe composition | `828e0e72...345c` / `3c53b5a9...c940` | approval 2010-01-01..2026-09-10; current extension manifest is 2026-only and pins effective universe `016d9b64...975f` |
| Daily Bar | `DailyBarFactV1`; `DailyBarAvailabilityPolicyV1`; fact shards | `7daf8a38...4724` / `9f38b28b...51e4` | only 2024-01-01..2025-12-31; historical `NEXT_SESSION_SAFE` availability |
| Security Status | interval/daily status facts; `StatusAvailabilityPolicyV2`; `SecurityStatusRepository` | `60d31609...39edc` / `57b4d385...65e3d` | manifest publishes the frozen 71-case acceptance fact scope, not a full historical status panel |
| Corporate Actions | `CorporateActionFactV1`; `CorporateActionAvailabilityPolicyV1`; `CorporateActionRepository` | `5e53080f...e974` / `5086896d...be2c` | supported: cash dividend and bonus share; rights issue, stock split, share conversion unsupported and fail closed |
| Financial Disclosures | `FinancialDisclosureFactV1`; `FinancialDisclosureAvailabilityPolicyV1`; `FinancialDisclosureRepository` | `58afcda2...0498` / `0b5e7228...06f` | `OBSERVED_FACTS_ONLY`; historical panel completeness PARTIAL; absent facts are `NOT_RESEARCH_SAFE` |

All six manifests must pin their exact approvals and pass content-integrity,
scope, revocation, and evidence-lineage checks before a research session can be
valid. The audit already exposes two likely whole-Exit blockers that must be
measured rather than hidden: daily bars have no EARLY/MIDDLE/2026 coverage, and
the published security-status manifest contains only the 71-case acceptance
scope rather than a research-wide historical status materialization.

## Thin Exit Design

The frozen design is recorded in
`docs/superpowers/specs/2026-09-13-v5-2-phase-1b-exit-design.md`. No unified fact
store, repository, registry, scheduler, feature, label, ranking, ML, or backtest
component is introduced.

## Frozen Exit Artifacts

- Coverage matrix: `512cefe376c57342afb8d3261c623f823625ae2300fbe1473b58e25ed10828c7`
- Exit acceptance: `090f3ec93fed17d23707f0a859e14d768cae7cfb02c70defc814b52df06b1f58`
- EARLY / 2012-06-29: `bfd09d04cedec1232c2ad16a8de4f4730029af279e0f15d3d2ce7f61fb5848bd`
- MIDDLE / 2018-06-29: `b223802c15de6901459bd07b8bb7f1216a75746277658af76542bf9ad22ce1b3`
- RECENT / 2025-06-30: `222594638c5e82f44ac25adf76c76dbfc596dae38573863fa2318e383ed14256`
- 2026 / 2026-06-30: `1c07e67549a33a4d651b64f75c780f1ab7770b96a2a7ae7c963159ec273f3e0b`

Every cutoff is 16:30 Asia/Shanghai and was checked against frozen approved
open-session inputs. Each result pins all six exact approval IDs, manifest IDs,
and the coverage-matrix hash. Replaying the evaluator produced the same IDs.

## Dry-run Results

| Window | Session | Result | Session-fatal reason |
|---|---:|---|---|
| EARLY | 2012-06-29 | INVALID | `OUTSIDE_APPROVED_COVERAGE` |
| MIDDLE | 2018-06-29 | INVALID | `OUTSIDE_APPROVED_COVERAGE` |
| RECENT | 2025-06-30 | INVALID | `OUTSIDE_APPROVED_COVERAGE` |
| 2026 | 2026-06-30 | INVALID | `OUTSIDE_APPROVED_COVERAGE` |

The result is intentionally fail closed. The current calendar and master
manifests publish the 2026 extension, not a manifest-pinned 2010-2025 base;
daily bars publish only 2024-2025; and security status publishes 71 acceptance
facts rather than a complete historical eligibility panel. Consequently the
Exit layer cannot lawfully construct base eligibility at all four points.
Optional Corporate Actions and Financial Disclosure limitations remain
security-scoped and do not independently invalidate a session.

## Chaos and Boundary Evidence

Chaos evidence ID:
`0b486a0876ed219dc919f0a10bda4466a3bbb680404b8be647877ddbc54688bd`.

- tampered manifest: fail closed
- wrong approval/manifest pin: fail closed
- valid immutable revocation: consumed; tampered revocation: fail closed
- naive or wrong-day cutoff: fail closed
- optional-data absence: security-scoped, not session-fatal
- unsupported Corporate Action type: explicit `NOT_RESEARCH_SAFE`
- unsupported/missing Financial metric: explicit `NOT_RESEARCH_SAFE`

## Gate Results

```text
STRUCTURAL = PASS
CUTOFF CONTRACT = PASS
FAILURE BOUNDARY = PASS
CROSS-DATASET TEMPORAL CONSISTENCY = FAIL
TEMPORAL JOIN SAFETY = PASS
REVISION TIME TRAVEL = PASS
MANIFEST LINEAGE = FAIL
COVERAGE MATRIX = PASS
OBSERVED FACTS BOUNDARY = PASS
SCOPED DATASET ENFORCEMENT = PASS
SURVIVORSHIP = FAIL
BASE ELIGIBILITY = FAIL
ROLLING READINESS = FAIL
CHAOS = PASS
DETERMINISTIC REPLAY = PASS
RESEARCH INPUT DRY RUN = FAIL

PHASE 1B HISTORICAL PIT EXIT = FAIL
READY FOR PHASE 2 = NO
RESEARCH_LOCKED = true
```

`MANIFEST LINEAGE = FAIL` means the complete historical base lineage needed by
the Exit contract is absent; the six individually selected artifacts themselves
all passed content-hash, approval pin, decision, scope and revocation checks.

## Verification Record

```text
COMMAND: .\.venv\Scripts\python.exe -m pytest -q tests/data/test_phase_1b_exit.py tests/real_audits/test_phase_1b_exit_runtime.py
RESULT: 14 passed in 1.17s

COMMAND: .\.venv\Scripts\python.exe -m pytest -q
RESULT: 433 passed in 48.98s

COMMAND: .\.venv\Scripts\python.exe scripts/verify_standalone.py
RESULT: forbidden imports=0; forbidden active paths/dependencies=0; prohibited repository inventory=0; Phase 1A architecture violations=0

COMMAND: .\.venv\Scripts\python.exe scripts/clean_room_acceptance.py
RESULT: build=true; clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; wheel_install=true; wheel_smoke=true; old_pythonpath_removed=true; zero_dependency_acceptance=true; archive findings=0; 428 passed, 5 skipped in 1.85s

COMMAND: actual DATAHUB_API_KEY/TUSHARE_TOKEN plus sentinel scan across git ls-files -co --exclude-standard
RESULT: actual credential findings=0; .env tracked=false; .env ignored by .gitignore:9

COMMAND: git diff --check
RESULT: exit 0
```

The five clean-room skips are precisely the repository-local artifact integration
tests: ignored `data/` is deliberately excluded from a source/wheel clean room.
The pure contract, failure-boundary, tamper, revocation and replay tests still
execute there. The first clean-room run exposed this environment assumption
(`5 failed, 428 passed`); the corrected recorded run passed.

## Remaining Blockers and Stop

1. Publish a complete manifest-pinned calendar and effective-dated security
   universe lineage for the historical base interval, not only a 2026 extension.
2. Materialize and approve daily bars outside 2024-2025 for every intended
   historical/rolling Exit session.
3. Materialize a research-wide PIT security-status panel. The existing 71 facts
   remain valid acceptance evidence but cannot substitute for panel coverage.
4. Re-run these same four frozen dry runs without changing their dates or
   weakening the contract.

No Phase 2, feature, label, ranking, ML, backtest, scheduler, new provider, or new
dataset work was started. Work stops at the failed Phase 1B Exit gate.
