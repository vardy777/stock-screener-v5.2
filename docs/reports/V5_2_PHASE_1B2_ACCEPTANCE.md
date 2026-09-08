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

## Phase 1B-2A Evidence Recovery + Gate Integration — 2026-09-08

Starting GitHub HEAD: `600fe3fb238c4f587241ac5f26b130c1ced0c3b0`.

### Code repair

`status_validation.py` now has an artifact-driven V2 gate evaluator. It verifies PIT evidence identity/scope, the complete cross-source disposition ledger, interval-aware historical reconciliation plus immutable supplement, exception-budget status, systematic-defect status, revocations, and content integrity. Approval/publication requires every gate to pass. Missing evidence and unresolved/unavailable dispositions produce `PENDING`; confirmed invalid evidence, mismatch, systematic defects, tampering, revocation, source mismatch, or structural failure produce `REJECTED`. The legacy structural validator no longer hard-codes PIT to `FAIL`.

Focused TDD explicitly covers a complete PASS path; missing PIT evidence; unavailable official evidence; mismatch; systematic defect; unresolved historical identity; revoked ledger; tampered ledger; and wrong source-version PIT evidence. Old incomplete artifacts remain non-approving.

### Evidence recovery

- DataHub endpoint probes confirmed `stock-st`, `stock_st`, and `st` return code 0. Only the canonical dataset-scoped `stock-st` and `st` routes were allowlisted.
- `stock-st` fields: `ts_code,name,trade_date,type,type_name`; `st` fields: `ts_code,name,pub_date,imp_date,st_type,st_reason,st_explain`.
- Evidence-only acquisition for the ten frozen ST-transition events issued 20 immutable requests and stored 54 rows. Diagnostic `218a44544afb60355f1e9eb3f1b35949cbfd3484f86473fcb5cbc6b104f5e2de`. These endpoints are the same provider boundary and therefore are not independent cross-source evidence.
- A representative official path was proven for frozen event `002699.SZ / 2022-06-06`: a SZSE-hosted issuer record states that other-risk-warning status took effect from that session's open. The exact event is `MATCH`; the source is `https://disc.static.szse.cn/disc/disk03/finalpage/2022-10-11/8e84e52b-9e8e-4b8c-a6ff-3f59c13144f6.PDF`.
- Frozen inventory remains 61 entries / 56 unique events. Ledger `1d58ed16ba552404273b427a3d45ce1b20eff89c777a2fb8730164a497e00a6e`: `MATCH=1`, `MISMATCH=0`, `UNRESOLVED=60`, `OFFICIAL_REFERENCE_UNAVAILABLE=0`. Missing retrieval is now correctly represented as `UNRESOLVED`, not falsely asserted unavailable.

### Historical-universe recovery

The exact 542-key inventory is unchanged. Existing dispositions were retained, then 248 `.BJ` identities were resolved as outside the frozen SSE/SZSE A-share scope using their immutable raw status observations; `X19363.SH` was resolved as a non-canonical legacy code. Each resolution records its observed effective interval, payload evidence IDs, and research-scope impact.

```text
TOTAL = 542
NON_TARGET = 539
LEGACY_CODE = 1
TARGET_A_SHARE_REQUIRED = 1 (600747.SH)
UNRESOLVED = 1 (002525.SZ)
SUPPLEMENT = 1 (600747.SH)
```

Reconciliation `03247cdb2b68956172d05c011f96a5f463116f5e4de007b8f88a7ff1b7cc8b16`; supplement `d67d886299be85bb5585c9103140ef327fe13b78161903f7e5120646a8ee9e8f`. `002525.SZ` returned no row from the provider security-master query and could not be authoritatively classified in this iteration, so survivorship remains `PENDING`.

### Actual integrated decision

```text
STRUCTURAL = PASS
PIT = PENDING
CROSS_SOURCE = PENDING
SURVIVORSHIP = PENDING
EXCEPTION_BUDGET = PASS
SYSTEMATIC_DEFECT = PASS

SOURCE APPROVAL = PENDING
APPROVAL_ID = 05ab1c98a352f49e6e36e92a42503895ca536a8659a3aec62fe36d7543de3632
PUBLICATION_ALLOWED = false
APPROVED STATUS FACTS = 0
DATASET MANIFEST = 0
PHASE 1B-2A = FAIL CLOSED / PENDING EVIDENCE
```

The `PENDING` result reflects insufficient proof, not a confirmed provider error. The previous `REJECTED` artifact remains immutable historical evidence; no old artifact was edited.

### Commands and exact results

```text
.\.venv\Scripts\python.exe scripts\recover_phase_1b2a_status_evidence.py
events=10; requests=20; rows=54; diagnostic_id=218a44544afb60355f1e9eb3f1b35949cbfd3484f86473fcb5cbc6b104f5e2de; cross_source_eligible=false

.\.venv\Scripts\python.exe scripts\reconcile_phase_1b2a_universe.py
total=542; NON_TARGET=539; LEGACY_CODE=1; TARGET_A_SHARE_REQUIRED=1; UNRESOLVED=1; supplement_count=1

.\.venv\Scripts\python.exe scripts\audit_phase_1b2a_official_samples.py
entries=61; unique_events=56; MATCH=1; UNRESOLVED=60; systematic_defect=false; ledger_id=1d58ed16ba552404273b427a3d45ce1b20eff89c777a2fb8730164a497e00a6e

.\.venv\Scripts\python.exe scripts\evaluate_phase_1b2a_gates.py
structural_status=PASS; pit_status=PENDING; cross_source_status=PENDING; survivorship_status=PENDING; exception_budget_status=PASS; systematic_defect_status=PASS; decision=PENDING; publication_allowed=false

.\.venv\Scripts\python.exe scripts\publish_phase_1b2a_status.py
decision=PENDING; approval_id=05ab1c98a352f49e6e36e92a42503895ca536a8659a3aec62fe36d7543de3632; equivalence=INSUFFICIENT_EVIDENCE; published_manifest_count=0; published_fact_count=0

.\.venv\Scripts\python.exe -m pytest <focused gate/evidence/provider tests> -q
39 passed in 0.11s

.\.venv\Scripts\python.exe -m pytest -q
289 passed in 9.37s

.\.venv\Scripts\python.exe scripts\verify_standalone.py
PASS forbidden imports: 0
PASS forbidden active paths/dependencies: 0
PASS prohibited repository inventory: 0
PASS phase 1a architecture boundary violations: 0

git diff --check
PASS (no output)

.\.venv\Scripts\python.exe scripts\clean_room_acceptance.py
clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; build=true; wheel_install=true; wheel_smoke=true; zero_dependency_acceptance=true
clean-room test_output: 289 passed in 110.78s (0:01:50)

credential scan using the actual local DATAHUB_API_KEY as a sentinel across repository runtime areas
CREDENTIAL_SCAN_FINDINGS=0
```

Remaining blockers are concrete: 60 frozen sample entries still lack exact independent evidence; `002525.SZ` remains unresolved; and no complete artifact proves each semantic's knowledge time relative to the 16:30 cutoff. Phase 1B-2B and all prohibited downstream work remain untouched.

## Phase 1B-2A Final Closure — 2026-09-08

Starting GitHub HEAD: `8ec00395a9cd3d282df772f5e9613a41fbde3a72`.

No frozen acquisition, 89-record exception audit, exception budget, 61-entry inventory, 600747.SH supplement, or approved daily-bar request was repeated.

### Historical universe

`NeverConfirmedTradableExclusionV1` now applies only when an identity has no approved daily bar, no verified trading session, and no reliable proof of actual historical tradability. It preserves source-record IDs, absence-of-trading evidence, reason, research impact, and content hash. Any positive trading proof makes construction fail.

`002525.SZ` is explicitly retained and classified `NEVER_CONFIRMED_TRADABLE`, with `research_eligible=false` and `survivorship_blocking=false`. Planned listing/code allocation is regression-tested as not equivalent to an actual first tradable session. The existing 600747.SH supplement is unchanged.

```text
TOTAL = 542
NON_TARGET = 539
NEVER_CONFIRMED_TRADABLE = 1
LEGACY_CODE = 1
TARGET_A_SHARE_REQUIRED = 1
UNRESOLVED = 0
SUPPLEMENT = 1
SURVIVORSHIP = PASS
```

Reconciliation artifact: `a5ab86ff4fc0fbc84e3d5f06dbcb1bf51a123dd2e900246404b795d5e1149613`.

### Frozen 61-case independent evidence

A deterministic BaoStock exact-security/exact-session retrieval was executed for all 56 unique events. The evidence artifact records provider identity, retrieval method, semantic suitability, independence rationale, rows, per-event disposition, and content hashes.

Independent evidence artifact: `b4b7cc0ed61ce18751675612f4cf7f8f667b44025f50c915a1211c8988a8015a`.

```text
61 ENTRIES / 56 UNIQUE EVENTS
MATCH = 30
MISMATCH = 0
UNRESOLVED = 2
INDEPENDENT_EVIDENCE_UNAVAILABLE = 29
LEDGER = c60ad6a427a67e8c335bc9914e04e3369e11f645a4f7487c756201407b76da66
CROSS_SOURCE = PENDING
```

The 29 unavailable cases are frozen ordinary-stratum securities for which the independent source has no exact-session coverage. The two unresolved cases have a record but insufficient semantic mapping (ordinary status and identity transition). They were not rewritten as MATCH and no threshold was changed.

### PIT knowledge time

`StatusKnowledgeTimeObservationV1` records effective session, independent observation/source/reference/document hash, real publication fields when available, availability basis, derived `available_at`, 16:30 cutoff, D-cutoff usability, semantic mapping version, input IDs, and content hash. Regression tests enforce date-only next-session safety and `planned listing != actual tradable listing`.

Thirty independently matched entries produced knowledge-time observations, all usable at the D cutoff through `MARKET_OBSERVABLE_BY_CLOSE`. Bundle `2edb43de6b3c795173b7d740a1e2665ff7371e0c04fc489a4f4425568a1963ad` is explicitly `complete=false` and `pit_evidence_published=false`. Missing resumption and other acceptance-scope proof means `pit_evidence=None` remains correct.

### Final gate and publication

```text
PIT KNOWLEDGE TIME = PENDING
CROSS SOURCE = PENDING
SURVIVORSHIP = PASS
EXCEPTION BUDGET = PASS
SYSTEMATIC DEFECT = PASS

SOURCE APPROVAL = PENDING
PUBLICATION_ALLOWED = false
APPROVED STATUS FACTS = 0
DATASET MANIFEST = 0
PHASE 1B-2A = FAIL CLOSED / PENDING EVIDENCE

PHASE 1B-2 overall = FAIL
HISTORICAL PIT DATA = FAIL
READY FOR LABEL ENGINE = NO
```

### Commands and exact results

```text
.\.venv\Scripts\python.exe scripts\reconcile_phase_1b2a_universe.py
total=542; NON_TARGET=539; NEVER_CONFIRMED_TRADABLE=1; LEGACY_CODE=1; TARGET_A_SHARE_REQUIRED=1; UNRESOLVED=0; supplement_count=1

.\.venv\Scripts\python.exe scripts\acquire_baostock_status_audit.py
unique_events=56; MATCH=25; MISMATCH=0; UNRESOLVED=2; INDEPENDENT_EVIDENCE_UNAVAILABLE=29; evidence_id=b4b7cc0ed61ce18751675612f4cf7f8f667b44025f50c915a1211c8988a8015a

.\.venv\Scripts\python.exe scripts\audit_phase_1b2a_official_samples.py
entries=61; unique_events=56; MATCH=30; MISMATCH=0; UNRESOLVED=2; INDEPENDENT_EVIDENCE_UNAVAILABLE=29; ledger_id=c60ad6a427a67e8c335bc9914e04e3369e11f645a4f7487c756201407b76da66

.\.venv\Scripts\python.exe scripts\build_phase_1b2a_knowledge_time.py
observation_count=30; usable_at_D_cutoff=30; complete=false; pit_evidence_published=false; bundle_id=2edb43de6b3c795173b7d740a1e2665ff7371e0c04fc489a4f4425568a1963ad

.\.venv\Scripts\python.exe scripts\evaluate_phase_1b2a_gates.py
structural_status=PASS; pit_status=PENDING; cross_source_status=PENDING; survivorship_status=PASS; exception_budget_status=PASS; systematic_defect_status=PASS; decision=PENDING; publication_allowed=false

.\.venv\Scripts\python.exe scripts\publish_phase_1b2a_status.py
decision=PENDING; approval_id=05ab1c98a352f49e6e36e92a42503895ca536a8659a3aec62fe36d7543de3632; published_manifest_count=0; published_fact_count=0

.\.venv\Scripts\python.exe -m pytest <focused final-closure tests> -q
19 passed in 0.06s

.\.venv\Scripts\python.exe -m pytest -q
294 passed in 105.89s (0:01:45)

.\.venv\Scripts\python.exe scripts\verify_standalone.py
PASS forbidden imports: 0
PASS forbidden active paths/dependencies: 0
PASS prohibited repository inventory: 0
PASS phase 1a architecture boundary violations: 0

git diff --check
PASS (no output)

.\.venv\Scripts\python.exe scripts\clean_room_acceptance.py
clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; build=true; wheel_install=true; wheel_smoke=true; zero_dependency_acceptance=true
clean-room test_output: 294 passed in 111.13s (0:01:51)

credential scan using the actual local DATAHUB_API_KEY as a sentinel across repository runtime areas
CREDENTIAL_SCAN_FINDINGS=0
```

STOP: the remaining evidence gap is bounded to 29 independently unavailable entries, two semantic-mapping-unresolved entries, and incomplete acceptance-scope PIT proof. No later phase was started.
