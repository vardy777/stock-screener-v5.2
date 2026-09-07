# V5.2 Phase 1B-2 Acceptance Report

## Phase 1B-2A — Daily Security Status / Historical Status

Acceptance date: 2026-09-07 (Asia/Shanghai)

Frozen starting HEAD: `55f104574235195348e3aa7cd3853cf47cf77707`

Implementation candidate HEAD before this report: `5826c523416b35ebc7c2e30e8e85873a01083b63`

Scope remained limited to Phase 1B-2A. Phase 1B-1 artifacts were not modified. Phase 1B-2B, corporate actions, financial disclosures, features, labels, ranking, ML, backtests, and alpha research were not started.

### Outcome

Phase 1B-2A is **FAIL CLOSED**. Real acquisition and deterministic replay succeeded, and all 6,489 frozen missing daily-bar keys were classified. The dataset was not approved because same-date D-close knowledge cannot be established from date-only provider fields, the frozen official cross-source sample has not been verified, and the survivorship audit exposed a historical delisted-security coverage gap. No approved status facts or DatasetManifest were published.

### Real acquisition and immutable identity

- Provider: `datahubco_tushare_proxy`
- Request inventory: `7977d147eeb4c3361570421d9a02e4808421fa70854ad8cec91227d6e82f1666`
- Coverage: 2010-01-04 through 2025-12-31
- Requests: 32/32 completed
- Raw payload artifacts: 116
- Rows: 473,424
  - `namechange`: 7,687
  - `suspend-d`: 465,737
- Checkpoints: 32
- Acquisition receipts after replay: 119
- Frozen sample inventory: `7ca99bfecd2731d5442ea62eb496afe3cff9b01a7ba32c1434a461c1a931a9c0` (61 cases)
- Replay evidence: `649f082492e47bf6a8fbfe8921276ed31b706a8a8276b84fbd7396a778cc62b7`
- Replay: first/middle/last requests all retained identical payload hashes and each produced a new receipt.

The official Tushare-compatible `suspend_d` contract defines `S` as a daily suspension observation covering each suspended date, not as a single interval-start event. The normalizer was corrected under TDD to compress consecutive daily `S` observations; `R` is treated as a resumption observation. Date-only observations remain unavailable to same-date D-close by default.

### PIT, cross-source, and survivorship findings

- Structural row/date validation: PASS; invalid rows = 0.
- PIT availability: FAIL. `ann_date` and `trade_date` do not contain verified publication timestamps. Acquisition time was not used as historical `available_at`.
- Official SSE/SZSE sample verification: not completed; 0/61 frozen cases verified.
- Cross-source: FAIL CLOSED.
- Survivorship: FAIL. The frozen universe does not contain every later-delisted A-share identity present in the historical security-master source; `600747.SH` is a concrete uncovered historical identity. Current membership was never used to backfill historical membership.
- Observed status symbols: 5,971; symbols outside the frozen daily-bar universe: 542.
- Status audit evidence: `23fb236fd6d1fdf7e0691c3bf3bfb8db3cf5524f13bcddb510bd21fbc52e03b7`.

### Frozen 6,489 missing-bar classification

The classification is diagnostic only and pins `research_eligible=false`; it does not turn unapproved provider observations into research facts.

```text
TOTAL MISSING = 6,489

SUSPENDED = 6,400
NOT_YET_LISTED = 0
DELISTED = 0
IDENTITY_NOT_APPLICABLE = 0
OTHER_LEGITIMATE = 0
LOCAL_EXCEPTION = 0
UNEXPLAINED = 89
```

- Classification artifact: `23a660b27dc476a582401780603d3e7458b823951b5d54c55ef40ef71c9f127d`
- The 89 unexplained keys span 2024 (52) and 2025 (37), SZ (48) and SH (41). One identity, `688766.SH`, accounts for eight consecutive keys; the remaining identities account for one each.
- Because no real-data exception budget was frozen before observing these results, they were not retrospectively fitted into a passing budget. Exception budget and systematic-defect gates therefore fail closed.

### Approval and publication

- Dataset kind: `daily_security_status`
- Equivalence decision: `INSUFFICIENT_EVIDENCE`
- Equivalence evidence: `638c1560840085b58ccd0454120de008721faaeed76af4727ba7f69848ac22c0`
- SourceApproval decision: `REJECTED`
- SourceApproval artifact: `b6d8202e3df6494e75971d5e64ea66ae1f5423b84157429ce8cbfb7a71b0fcbc`
- Approved status facts: 0
- Status DatasetManifest: 0

The manifest constructor was regression-tested to reject a `REJECTED` approval. The publisher independently confirmed `published_manifest_count=0` and `published_fact_count=0`.

### Validation commands and exact results

```text
.\.venv\Scripts\python.exe scripts\phase_1b2a_acquire.py probe
SOURCE=datahubco_tushare_proxy STATUS=PASS REASON=ALLOWLISTED_PROBE_SUCCEEDED TRANSPORT=PLAINTEXT_HTTP
ENDPOINT_PROBE=risk_warning_history STATUS=PASS ROWS=497 TOTAL=0
ENDPOINT_PROBE=suspension_history STATUS=PASS ROWS=5000 TOTAL=0

.\.venv\Scripts\python.exe scripts\phase_1b2a_acquire.py acquire --resume
STATUS_ACQUISITION=PASS COMPLETED_REQUESTS=32 PAGES=116 ROWS=473424 PAYLOAD_HASHES=116

.\.venv\Scripts\python.exe scripts\replay_phase_1b2a_status.py
same_payload_different_receipt_pass=true; observations=3; each new_receipt_count=1

.\.venv\Scripts\python.exe scripts\audit_phase_1b2a_status.py
structural_status=PASS; pit_status=FAIL; cross_source_status=PENDING; survivorship_status=FAIL
namechange_row_count=7687; suspension_row_count=465737; invalid_row_count=0

.\.venv\Scripts\python.exe scripts\classify_phase_1b1_missing_bars.py
total=6489; SUSPENDED=6400; UNEXPLAINED=89; all other categories=0; research_eligible=false

.\.venv\Scripts\python.exe scripts\publish_phase_1b2a_status.py
decision=REJECTED; equivalence=INSUFFICIENT_EVIDENCE; published_manifest_count=0; published_fact_count=0

.\.venv\Scripts\python.exe -m pytest <12 focused Phase 1B-2A test files> -q
33 passed in 0.12s

.\.venv\Scripts\python.exe -m pytest -q
272 passed in 9.08s

.\.venv\Scripts\python.exe scripts\verify_standalone.py
PASS forbidden imports: 0
PASS forbidden active paths/dependencies: 0
PASS prohibited repository inventory: 0
PASS phase 1a architecture boundary violations: 0

.\.venv\Scripts\python.exe scripts\clean_room_acceptance.py
clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true
build=true; wheel_install=true; wheel_smoke=true; zero_dependency_acceptance=true
archives=stock_screener_v5_2-5.2.0-py3-none-any.whl, stock_screener_v5_2-5.2.0.tar.gz
clean-room test_output: 272 passed in 106.84s (0:01:46)

.\.venv\Scripts\python.exe -m pytest tests\governance\test_phase_1a_boundaries.py tests\governance\test_clean_room_acceptance.py tests\governance\test_standalone.py -q
17 passed in 8.65s

candidate credential scan across data/logs/artifacts/build/dist
CANDIDATE_CREDENTIAL_SCAN_FINDINGS=0

git diff --check
PASS (no output)
```

### Phase 1B-2A exit matrix

```text
DAILY SECURITY STATUS REAL ACQUISITION = PASS
STATUS PIT SEMANTICS = FAIL
LISTING HISTORY = FAIL
DELISTING HISTORY = FAIL
ST / RISK WARNING HISTORY = FAIL
SUSPENSION / RESUMPTION HISTORY = FAIL
6,489 MISSING BAR CLASSIFICATION = PASS
UNEXPLAINED MISSING BAR COUNT = 89
SURVIVORSHIP AUDIT = FAIL
CROSS SOURCE = FAIL
EXCEPTION BUDGET = FAIL
SYSTEMATIC DEFECT AUDIT = FAIL
DAILY SECURITY STATUS APPROVAL = REJECTED
APPROVED STATUS FACTS = 0
DATASET MANIFEST = FAIL
PHASE 1B-2A = FAIL

PHASE 1B-2 overall = FAIL
HISTORICAL PIT DATA = FAIL
READY FOR LABEL ENGINE = NO
```

STOP: Phase 1B-2B was not started. The next corrective iteration must close the official 61-case verification, repair the historical survivorship universe gap through immutable supersession/replacement, freeze a real exception budget before reevaluation, and resolve the 89 unexplained keys. It must not proceed to later phases while this gate remains failed.

## Phase 1B-2A evidence-closure iteration — 2026-09-08

This iteration closed the consistency and local-exception governance work without reacquiring the frozen 32 requests, 116 pages, or 473,424 rows. It did not enter Phase 1B-2B.

### Evidence results

- The equivalence unexplained count is now derived from the immutable classification artifact; the hard-coded 88/89 inconsistency is removed and regression-tested.
- Predeclared `StatusExceptionBudgetV2` passed for all 89 records: ratio `0.00003577459433016895657567190919`, maximum per security 8, maximum consecutive 8, maximum exchange share `0.5393258426966292134831460674`, maximum per month 16, unknown effective intervals 0, systematic pattern false. All 89 records are content-addressed, quarantined, and research-excluded.
- Exact 6,489-key immutable supersession: `SUSPENDED=6400`, `LOCAL_EXCEPTION=89`, `UNEXPLAINED=0`; classification `34612813c3bfdeb233bf41b66796a9ca9e89751062523ca7be30fc4c76f56420`; keys preserved=true; research_eligible=false.
- Historical universe reconciliation: total 542; `NON_TARGET=291`, `TARGET_A_SHARE_REQUIRED=1` (`600747.SH`), `UNRESOLVED=250`. Supplement count 1; reconciliation `9496756d9691c8dc7b61b1876e4424c2a992cf6b86aebbd230ec06496b1f7c8d`; supplement `d67d886299be85bb5585c9103140ef327fe13b78161903f7e5120646a8ee9e8f`. The 250 unresolved identities keep survivorship fail-closed.
- Frozen official inventory was preserved exactly: 61 entries / 56 unique events. Ledger `f9a8e6b6962d6db7d242bc32305a91f9ac3dfb745e6102b6dcdf6a3d1a4c2f8f`: MATCH=0, MISMATCH=0, UNRESOLVED=0, OFFICIAL_REFERENCE_UNAVAILABLE=61. No unavailable reference was promoted to MATCH; cross-source remains FAIL.
- `StatusAvailabilityPolicyV2` fixes the V5.2 research cutoff at 16:30 Asia/Shanghai and machine-represents publication timestamp, market-observable-by-close, conservative-after-close, and next-session-safe bases. Acquisition time is ignored. Because exact official event evidence and semantic mapping remain incomplete, PIT semantics remain FAIL for dataset approval.
- Publisher decision remains `REJECTED`; approval `f46ab5bd8ec4bdfbc425b533e57065cb9203b797a05d64b5b612872235a6115e`; approved facts 0; DatasetManifest count 0.

### Validation commands and exact results

```text
.\.venv\Scripts\python.exe scripts\reconcile_phase_1b2a_universe.py
total=542; NON_TARGET=291; TARGET_A_SHARE_REQUIRED=1; UNRESOLVED=250; supplement_count=1; supplement_identity=600747.SH

.\.venv\Scripts\python.exe scripts\audit_phase_1b2a_official_samples.py
entries=61; unique_events=56; OFFICIAL_REFERENCE_UNAVAILABLE=61; systematic_defect=false

.\.venv\Scripts\python.exe scripts\reclassify_phase_1b2a_missing_bars.py
total=6489; SUSPENDED=6400; LOCAL_EXCEPTION=89; UNEXPLAINED=0; preserved_keys=true; research_eligible=false

.\.venv\Scripts\python.exe scripts\publish_phase_1b2a_status.py
decision=REJECTED; equivalence=INSUFFICIENT_EVIDENCE; published_manifest_count=0; published_fact_count=0

.\.venv\Scripts\python.exe -m pytest -q
282 passed in 75.06s (0:01:15)

.\.venv\Scripts\python.exe scripts\verify_standalone.py
PASS forbidden imports: 0
PASS forbidden active paths/dependencies: 0
PASS prohibited repository inventory: 0
PASS phase 1a architecture boundary violations: 0

.\.venv\Scripts\python.exe scripts\clean_room_acceptance.py
clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; build=true; wheel_install=true; wheel_smoke=true; zero_dependency_acceptance=true
clean-room test_output: 282 passed in 109.81s (0:01:49)

git diff --check
PASS (no output)
```

### Exit matrix

```text
REAL ACQUISITION = PASS
STATUS AVAILABILITY POLICY = PASS
PIT SEMANTICS = FAIL

OFFICIAL 61-CASE SAMPLE:
MATCH = 0
MISMATCH = 0
UNRESOLVED = 0
OFFICIAL_REFERENCE_UNAVAILABLE = 61

HISTORICAL UNIVERSE RECONCILIATION = FAIL
HISTORICAL UNIVERSE SUPPLEMENT = 1

6,489 MISSING BARS:
SUSPENDED = 6,400
LOCAL_EXCEPTION = 89
UNEXPLAINED = 0

EXCEPTION BUDGET = PASS
SYSTEMATIC DEFECT AUDIT = PASS
SURVIVORSHIP AUDIT = FAIL
CROSS SOURCE = FAIL

DAILY SECURITY STATUS APPROVAL = REJECTED
APPROVED STATUS FACTS = 0
DATASET MANIFEST = FAIL
PHASE 1B-2A = FAIL

PHASE 1B-2 overall = FAIL
HISTORICAL PIT DATA = FAIL
READY FOR LABEL ENGINE = NO
```

STOP: no later phase was started. Remaining blockers are the 250 unresolved historical-universe identities, exact official evidence for the frozen 61 entries, and semantic application of that evidence to PIT availability.
