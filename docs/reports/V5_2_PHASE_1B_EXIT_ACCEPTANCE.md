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

# Remediation Run — 2026-09-13

The original failed acceptance above is retained unchanged. This section records
the bounded remediation from repository baseline
`f0f4564890a9dcb87a6abe33f99d3622f918b264`.

## Correctness Repairs and Immutable Lineage

- The original dry-run label/hash table had MIDDLE, RECENT and 2026 attached to
  the wrong immutable artifacts. The corrected source mapping is: EARLY
  `bfd09d04cedec1232c2ad16a8de4f4730029af279e0f15d3d2ce7f61fb5848bd`;
  MIDDLE `222594638c5e82f44ac25adf76c76dbfc596dae38573863fa2318e383ed14256`;
  RECENT `1c07e67549a33a4d651b64f75c780f1ab7770b96a2a7ae7c963159ec273f3e0b`;
  2026 `b223802c15de6901459bd07b8bb7f1216a75746277658af76542bf9ad22ce1b3`.
- Complete calendar lineage: base facts
  `d64a2ef0823e9a55a33d3b8111337fb71fcb43ce778235694ebfadfed1396dcc`,
  base manifest `64f1de5d11563a4d236875bb04c986c072973bf9e1b7402d6c3c2b343776f54f`,
  composition `48146ed89be306a30a43ffd91de6db2e77763b32b011847fd619fd7fb0e50f1d`,
  complete manifest `5f5ba7d0594f5f1e2d40ad43b54a93a303a7d25af8e1104e6c633463076e6486`.
- Complete effective-dated security-master lineage: base facts
  `968ae9660ae02f4a1e16a8eb6510a62368e44defc7f99f7ed56714364c722386`,
  complete facts `2675dc691521dbcfecc3ac48c8ef3af1e3fb69a9230afb6835c9a3a0ad86e69a`,
  base manifest `f56fc49dcc8ac07e640f2c0339fc40d3b72986b17cbbc19a7508e1c6622d7e60`,
  composition `68893814f156e16547afbdac82fa1bb8e94e82756a256495c07b4be9736f30e9`,
  complete manifest `025982975b942c416945d9580f2a8272d667f7676e9f6fa213429e3da2ee382b`.
- Daily-bar 2026 acquisition used 168 terminal requests and 924,023 raw rows;
  the final immutable research panel contains 14,010,422 rows across
  2010-01-04..2026-09-10. Panel
  `a618046c952a9bb863a1ec93fcc4d79c24cfca69542fdbb1c6581c1fde75a31d`,
  inventory `87154d81d85d946fc03b4156010494dc7ef0bffb4ff1d56fc56ea4cea2b15cef`,
  availability `70ee31d3e126d12baf6d08a4b780d8051d3477762521f1fe34780319c9ccadbd`,
  approval `fc26bf140708a72957f687757665508ee439cb079b9bdaff86686109b7683ea5`,
  manifest `76c4fe58d0714405d0a6a826bf9b814237d812f88f69b63986a0e0317f924b4b`.
  The prior D 15:00 lineage is excluded; research availability is
  `NEXT_SESSION_SAFE` at 16:30 Asia/Shanghai. The 423,182 absent effective
  symbol-sessions remain explicit unclassified fail-closed gaps, never zero bars.
- Research-wide status materialization contains 475,416 PIT rows, with zero
  unresolved identities and zero unresolved sessions. Panel
  `cd062ced913e865984d536bc85305f9c6e720e26cee111527aac120fd66fe707`,
  resolution `3ae79a145d7d0252aea1d5e35fb6b737fba568603cc5e2a9a499e22fdf68fd44`,
  approval `ac1c23dae38c32228bfc6639714976e6a01063b230ae3397ee45d9ac1d8afa07`,
  manifest `d96fc4f26c459dc000ca8059a8364a8236e906305be83d2d72adc01d9e11ffb0`.
  The existing 71/71 cross-source result remains independent equivalence
  evidence rather than being substituted for panel coverage.
- Financial-disclosure partial coverage remains security-scoped and fail closed;
  it is not promoted to complete historical coverage.

## Remediated Dry Runs

| Label | Session | New artifact | Universe | Eligible | Blocked | Result |
|---|---|---|---:|---:|---:|---|
| EARLY | 2012-06-29 | `19c0153b6e4467b44e97b6a27930874e1fbd5927a76aa11869bb233a2b1ae146` | 2,421 | 2,205 | 216 | PASS |
| MIDDLE | 2018-06-29 | `17da053120bb163d5241aced0ea238540867c440b44796f8f5aafc0f8959eeac` | 3,529 | 3,256 | 273 | PASS |
| RECENT | 2025-06-30 | `71b6f37f119c3bc1c7663aeef80664090350b2b5d1846eadcce6270cf49d3119` | 5,152 | 4,972 | 180 | PASS |
| 2026 | 2026-06-30 | `52b64bedbc05071a1f379a9bad080b7c775617eecabb1bef2558780c5f803353` | 5,205 | 4,978 | 227 | PASS |

The evaluator output is content-addressed as coverage matrix
`f75ea8d4c91b8a9a4fc9074f2bb0caa74c8bb939801e1fa7af8c66c7433d2adf`,
deterministic replay `588e647dc57effe81b01a0d9dc315374bb2a455b990fad98af0a1e795c155ce4`,
and acceptance
`ab471057c9504b64171524259562dc9429bb8179c27a06213ef7a9d452a1207c`.

## Remediated Gate Results

```text
STRUCTURAL = PASS
CUTOFF CONTRACT = PASS
FAILURE BOUNDARY = PASS
CROSS-DATASET TEMPORAL CONSISTENCY = PASS
TEMPORAL JOIN SAFETY = PASS
REVISION TIME TRAVEL = PASS
MANIFEST LINEAGE = PASS
COVERAGE MATRIX = PASS
OBSERVED FACTS BOUNDARY = PASS
SCOPED DATASET ENFORCEMENT = PASS
SURVIVORSHIP = PASS
BASE ELIGIBILITY = PASS
ROLLING READINESS = PASS
CHAOS = PASS
DETERMINISTIC REPLAY = PASS
RESEARCH INPUT DRY RUN = PASS

PHASE 1B HISTORICAL PIT EXIT = PASS
READY FOR PHASE 2 = YES
RESEARCH_LOCKED = true
```

`READY FOR PHASE 2 = YES` means the Phase 1B historical PIT exit contract is
satisfied. It does not unlock research or authorize Phase 2 work in this run.

## Remediation Verification Record

```text
COMMAND: .\.venv\Scripts\python.exe -m pytest -q tests/data/test_historical_lineage_composition.py tests/data/test_historical_remediation.py tests/data/test_historical_status_repository.py tests/data/test_phase_1b_exit.py tests/real_audits/test_phase_1b_exit_runtime.py
RESULT: 27 passed in 3.60s

COMMAND: .\.venv\Scripts\python.exe -m pytest tests/governance/test_phase_1a_boundaries.py::test_sentinel_scan_detects_secret_split_across_stream_chunks tests/governance/test_phase_1a_boundaries.py::test_current_runtime_areas_have_no_sentinel_leak -q
RESULT: 2 passed in 70.35s

COMMAND: .\.venv\Scripts\python.exe -m pytest -q
RESULT: 447 passed in 84.57s

COMMAND: .\.venv\Scripts\python.exe scripts\verify_standalone.py
RESULT: forbidden imports=0; forbidden active paths/dependencies=0; prohibited repository inventory=0; Phase 1A architecture violations=0

COMMAND: .\.venv\Scripts\python.exe -m build
RESULT: exit 0; sdist and wheel built successfully

COMMAND: .\.venv\Scripts\python.exe scripts\clean_room_acceptance.py
RESULT: build=true; clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; wheel_install=true; wheel_smoke=true; old_pythonpath_removed=true; zero_dependency_acceptance=true; archive findings=0; 440 passed, 7 skipped in 1.88s

COMMAND: .\.venv\Scripts\python.exe scripts\evaluate_phase_1b_exit.py --help
RESULT: acceptance=ab471057c9504b64171524259562dc9429bb8179c27a06213ef7a9d452a1207c; all 17 gates PASS; all four frozen sessions valid

COMMAND: actual local DATAHUB_API_KEY sentinel scan across data/logs/artifacts/build/dist; git ls-files .env; git check-ignore -v .env
RESULT: credential sentinel count=1; credential findings=0; .env tracked=false; .env ignored by .gitignore:9

COMMAND: git diff --check
RESULT: exit 0 (line-ending conversion warnings only)
```

The seven clean-room skips are repository-local immutable artifact integration
tests because ignored `data/` is deliberately absent from the source/wheel clean
room. Pure lineage, policy, fail-closed, tamper and replay tests execute there.

No Phase 2, feature, label, ranking, ML, backtest, scheduler, new provider or new
dataset work was started. This run stops after commit/push at the Phase 1B Exit.
