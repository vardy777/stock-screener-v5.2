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

## Phase 1B-2A Evidence Sufficiency Review — 2026-09-08

Starting HEAD: `55b7483897adc52d5d4a2cdddd156338a61833b2`.

### Final resolution of the two semantic cases

1. Event `f61a553ca2ec93dc00f9c0658e9fa9691edc8cf17ede02f412a048f3f03f84fc`, `300029.SZ`, session `20250102`: DataHub `stock-st` reports `type=ST`; BaoStock reports `tradestatus=1,isST=1`. The divergence was the interpretation of `ordinary` as a non-ST value even though it is only the frozen sampling-stratum label. Disposition: `MAPPING_ERROR_FIXED_MATCH`, not a mismatch. Evidence: recovery diagnostic `e860cfcbbb228c46c937e3adde5ae4360381e6dab9282878516593178cf0659d` and independent evidence `bb406f3768c8f568dc582307897ffc76c00727deb592105c87cee0e45e9f7a2d`.
2. Event `300114-to-302132-v1`, `302132.SZ`, session `20250214`: BaoStock retrospectively labels the record `302132`, while the SZSE-hosted implementation notice states that old code `300114` applies through T-1 and new code `302132` begins on `2025-02-17`. BaoStock's value is unsuitable for PIT identity mapping; the official effective chain matches the frozen transition boundary. Disposition: `MAPPING_ERROR_FIXED_MATCH`, not a provider mismatch. Official evidence: `https://disc.static.szse.cn/disc/disk03/finalpage/2025-02-15/cedb693a-f5ee-4463-9682-ea33d406b569.PDF`.

The ledger builder now regression-tests that a stratum label cannot overwrite explicit provider and independent values.

### Final 29-entry coverage ledger

Review artifact `afb939daf6f13d1d91a2de0513b59fabeaa71cd3430b58c9f97602873971976c` contains all 29 entries individually, including event ID, identity, session, attempted source/method, independent evidence ID, security-master evidence ID, delisting date, unavailable reason, systematic coverage class, research impact, and content hash.

All 29 are the same applicability defect: the frozen ordinary stratum selected later-delisted identities at fixed session `2025-01-02`; every identity had delisted between `2003-09-22` and `2024-06-26`. BaoStock exact-security/exact-session lookup therefore correctly returned no row. No applicable exchange daily trading-status record should exist after delisting. This is not a value mismatch, but these cases cannot validate active ordinary-status equivalence.

```text
61 FROZEN ENTRIES / 56 UNIQUE EVENTS
MATCH = 32
MISMATCH = 0
UNRESOLVED = 0
INDEPENDENT_EVIDENCE_UNAVAILABLE = 29
LEDGER = c37fbce55f6f6ceaf8dc89bbeca762b63869fa97c3a8bd5067fdedc8803344cd
```

### Evidence Sufficiency Policy decision

The old frozen contract requires complete independent resolution and is not satisfied. It was not modified. A prospective `Evidence Sufficiency Policy Proposal V1` was written at `docs/superpowers/specs/2026-09-08-phase-1b2a-evidence-sufficiency-policy-proposal.md`; status is `PROPOSED — NOT ADOPTED`.

The proposal does not use a matched percentage. It requires a newly preregistered deterministic inventory with explicit provider values, valid tradable identity/session pairs, separate high-risk semantic strata, official identity/listing/delisting anchors, independent daily observations, zero unexplained mismatches, and pre-observation applicability rules. It preserves the old ledger and requires ChatGPT acceptance before any replacement contract is used.

### PIT coverage matrix

```text
listing             = PENDING; planned/approved listing is not actual first tradable session; frozen evidence has no actual-listing case
delisting           = PARTIAL; five unique effective boundaries observed, announcement knowledge incomplete
ST enter            = SAFE_WITH_RULE; ten daily states observable by D close
ST exit             = SAFE_WITH_RULE; D state observable by close, interval-end date remains next-session-safe until observed
suspension          = SAFE_WITH_RULE; ten full-day states independently observable by D close
resumption          = SAFE_WITH_RULE; actual D trading observable by close; no D-1 forecast without notice
identity transition = SAFE_WITH_RULE; official chain prevents overlap and retrospective code backfill
ordinary status     = PENDING; 29 post-delisting samples do not test active ordinary status
```

The existing 30 knowledge-time observations remain valid sample-level evidence. They do not establish semantic-level completeness or full historical coverage. Bundle `d4e050e28ff6b6b85b5fecc3a126d53068d15c90813bca98a12943f61591c152` remains `complete=false`, `pit_evidence_published=false`; therefore `pit_evidence=None` and PIT=PENDING remain correct.

### Final decision

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
```

This is exit result B. No PIT PASS artifact, approved facts, or DatasetManifest was created. STOP pending review of the proposed prospective policy.

### Verification commands and exact results

```text
.\.venv\Scripts\python.exe scripts\recover_phase_1b2a_status_evidence.py
events=11; requests=22; rows=61; diagnostic_id=e860cfcbbb228c46c937e3adde5ae4360381e6dab9282878516593178cf0659d; cross_source_eligible=false

.\.venv\Scripts\python.exe scripts\acquire_baostock_status_audit.py
unique_events=56; MATCH=25; MISMATCH=0; UNRESOLVED=2; INDEPENDENT_EVIDENCE_UNAVAILABLE=29; evidence_id=bb406f3768c8f568dc582307897ffc76c00727deb592105c87cee0e45e9f7a2d

.\.venv\Scripts\python.exe scripts\audit_phase_1b2a_official_samples.py
entries=61; unique_events=56; MATCH=32; INDEPENDENT_EVIDENCE_UNAVAILABLE=29; systematic_defect=false; ledger_id=c37fbce55f6f6ceaf8dc89bbeca762b63869fa97c3a8bd5067fdedc8803344cd

.\.venv\Scripts\python.exe scripts\review_phase_1b2a_evidence_sufficiency.py
coverage_entries=29; semantic_resolutions=2; old_contract_satisfied=false; decision=PENDING; review_id=afb939daf6f13d1d91a2de0513b59fabeaa71cd3430b58c9f97602873971976c

.\.venv\Scripts\python.exe scripts\build_phase_1b2a_knowledge_time.py
observation_count=30; usable_at_D_cutoff=30; complete=false; pit_evidence_published=false; bundle_id=d4e050e28ff6b6b85b5fecc3a126d53068d15c90813bca98a12943f61591c152

.\.venv\Scripts\python.exe scripts\evaluate_phase_1b2a_gates.py
structural_status=PASS; pit_status=PENDING; cross_source_status=PENDING; survivorship_status=PASS; exception_budget_status=PASS; systematic_defect_status=PASS; decision=PENDING; publication_allowed=false

.\.venv\Scripts\python.exe scripts\publish_phase_1b2a_status.py
decision=PENDING; approval_id=05ab1c98a352f49e6e36e92a42503895ca536a8659a3aec62fe36d7543de3632; published_manifest_count=0; published_fact_count=0

.\.venv\Scripts\python.exe -m pytest <focused evidence-sufficiency tests> -q
16 passed in 0.05s

.\.venv\Scripts\python.exe -m pytest -q
295 passed in 9.06s

.\.venv\Scripts\python.exe scripts\verify_standalone.py
PASS forbidden imports: 0
PASS forbidden active paths/dependencies: 0
PASS prohibited repository inventory: 0
PASS phase 1a architecture boundary violations: 0

.\.venv\Scripts\python.exe scripts\clean_room_acceptance.py
clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; build=true; wheel_install=true; wheel_smoke=true; zero_dependency_acceptance=true
clean-room test_output: 295 passed in 106.39s (0:01:46)

credential scan using actual local DATAHUB_API_KEY as sentinel
CREDENTIAL_SCAN_FINDINGS=0

git diff --check
PASS (no output)
```

## Phase 1B-2A Prospective Evidence Contract & PIT Closure — 2026-09-08

Starting HEAD: `0209829732f87ee8414f4adf40f7a9d3a3e05874`.

The old 61-entry contract remains immutable and unchanged: `MATCH=32`, `MISMATCH=0`, `UNRESOLVED=0`, `INDEPENDENT_EVIDENCE_UNAVAILABLE=29`. It was not reused as a passing result.

Prospective Evidence Contract V1 was adopted and its sample inventory was committed before independent acquisition:

```text
contract_id = ec83de3e51d5b13e021ff57a7c1a96dedc33c8df74ba7b1f03fcb8450d09efab
inventory_id = 721523af643819654985676d675aee2cc24c9d7031a0e13d4af64efe6a894f87
sample_count = 71
ACTIVE_ORDINARY_STATUS = 10
ACTUAL_FIRST_TRADABLE_SESSION = 10
DELISTING_BOUNDARY = 10
ST_ENTER = 10
ST_EXIT = 10
FULL_DAY_SUSPENSION = 10
RESUMPTION = 10
IDENTITY_TRANSITION = 1
pre-acquisition freeze commit = 7947ea2
```

The bounded independent run produced ledger `59cc248619400a9155ade3c79c036078d7c614f68f872e82762b36805d667682`: `MATCH=64`, `MISMATCH=4`, `INDEPENDENT_EVIDENCE_UNAVAILABLE=3`.

The four mismatches are confirmed prospective inventory construction defects, not source-unavailability cases. `002147.SZ/20200429`, `300446.SZ/20210428`, `002220.SZ/20200602`, and `002420.SZ/20200723` were asserted as ST exits, but the provider's next effective name remained an `ST` or `*ST` name and BaoStock independently reported `isST=1`. The selector had incorrectly treated every risk-warning interval end as an exit. The selector now requires an explicit risk-warning-name to non-risk-warning-name transition, with regression coverage for `ST -> *ST` and `*ST -> ST`. The frozen V1 inventory and observed results were not replaced, resampled, or retroactively altered.

The three unavailable delisting-boundary observations were not promoted to MATCH. Bounded official review found exact exchange-hosted support for `300630.SZ/20250522` and `600200.SH/20251231`, while `000851.SZ/20251111` did not obtain a sufficiently exact independent anchor within the time box. Because the four confirmed semantic defects already fail the contract, no open-ended retrieval or outcome-driven replacement sampling was performed.

PIT coverage remains incomplete. `StatusAvailabilityPolicyV2` was not changed, no `StatusPITKnowledgeTimeEvidenceV1` PASS artifact was created, and the historical 16:30 Asia/Shanghai cutoff remains frozen. The future 20:00 acquisition / 22:00 reporting product requirement remains recorded only; no scheduler was started.

The formal runtime path now consumes the prospective inventory and evidence ledger, an on-disk revocation registry, the immutable universe reconciliation, and actual exception artifacts:

```text
evidence builder -> gate evaluator -> source approval -> publisher boundary
STRUCTURAL = PASS
PIT = PENDING
CROSS_SOURCE = FAIL
SURVIVORSHIP = PASS
EXCEPTION_BUDGET = PASS
SYSTEMATIC_DEFECT = PASS
SOURCE_APPROVAL = REJECTED
PUBLICATION_ALLOWED = false
APPROVED_FACTS = 0
DATASET_MANIFEST = 0
approval_id = 8b5d39956ff8d5b523ad5641d4fa481e4e45e639af30460dfefb2e9731283aa3
equivalence_id = 4ada9d6e30779bd15f98c39140c3551372269fdf982a0caeae161e237c0997d8
```

This is a fail-closed terminal result for prospective contract V1. No 1B-2B or downstream research work was started.

### Verification commands and exact results

```text
.\.venv\Scripts\python.exe scripts\acquire_phase_1b2a_prospective_evidence.py
total=71; MATCH=64; MISMATCH=4; INDEPENDENT_EVIDENCE_UNAVAILABLE=3; ledger_id=59cc248619400a9155ade3c79c036078d7c614f68f872e82762b36805d667682

.\.venv\Scripts\python.exe scripts\evaluate_phase_1b2a_gates.py
structural_status=PASS; pit_status=PENDING; cross_source_status=FAIL; survivorship_status=PASS; exception_budget_status=PASS; systematic_defect_status=PASS; decision=REJECTED; publication_allowed=false

.\.venv\Scripts\python.exe scripts\publish_phase_1b2a_status.py
decision=REJECTED; approval_id=8b5d39956ff8d5b523ad5641d4fa481e4e45e639af30460dfefb2e9731283aa3; equivalence=NOT_EQUIVALENT; published_manifest_count=0; published_fact_count=0

.\.venv\Scripts\python.exe -m pytest tests/real_audits/test_status_prospective_sampling.py tests/real_audits/test_status_gate_integration.py tests/real_audits/test_status_official_samples.py -q
11 passed in 0.05s

.\.venv\Scripts\python.exe -m pytest -q
298 passed in 10.64s

.\.venv\Scripts\python.exe scripts\verify_standalone.py
PASS forbidden imports: 0
PASS forbidden active paths/dependencies: 0
PASS prohibited repository inventory: 0
PASS phase 1a architecture boundary violations: 0

.\.venv\Scripts\python.exe scripts\clean_room_acceptance.py
clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; build=true; wheel_install=true; wheel_smoke=true; zero_dependency_acceptance=true
clean-room test_output: 298 passed in 108.39s (0:01:48)

credential scan using actual local DATAHUB_API_KEY and TUSHARE_TOKEN values as sentinels
CREDENTIAL_SCAN_FINDINGS=0

git diff --check
PASS (line-ending notices only; no whitespace errors)
```

## Phase 1B-2A Prospective Evidence Contract V2 — 2026-09-09

Starting HEAD: `f30ef5fe23c212bcfebc537d7608e2adfb3bdd19`.

### Immutable contract history

```text
Contract V1 = FAIL (permanent)
failure_reason = frozen ST_EXIT sample construction defect
V1 result = MATCH 64 / MISMATCH 4 / UNAVAILABLE 3
```

V1 artifacts and failure were not deleted, overwritten, superseded as PASS, or used to choose V2 outcomes.

P0 found one additional selector edge case before the V2 freeze: substring matching would treat a non-prefix name such as `BEST` as risk-warning. The selector now recognizes only the Chinese-market risk-warning prefixes and regression-tests `ST -> *ST = NOT EXIT`, `*ST -> ST = NOT EXIT`, `ST -> ordinary = EXIT`, `*ST -> ordinary = EXIT`, and non-prefix `ST` substrings as not risk-warning.

```text
Contract V2 ID = 3a9efd2f1047d9ad0432a72202bf1b8e7f926d153c339106475c37a694b20917
Inventory V2 ID = cef91ec0a055f01ac2f0f82ec8e15ce75f4e000acd2123a70685fb25d1df3c9c
freeze commit = 53578aa7e50d151eb292472bfed2fd532fdb4748
sample count = 71
ACTIVE_ORDINARY_STATUS = 10
ACTUAL_FIRST_TRADABLE_SESSION = 10
DELISTING_BOUNDARY = 10
ST_ENTER = 10
ST_EXIT = 10
FULL_DAY_SUSPENSION = 10
RESUMPTION = 10
IDENTITY_TRANSITION = 1
```

The V2 contract and inventory were committed before the first independent V2 retrieval. Every frozen sample pins identity, session, semantic, provider value, semantic assertion, effective interval, provider evidence IDs, and candidate hash.

### Bounded independent validation

The first mechanical pass exposed an evaluator correctness issue: it counted BaoStock daily status alone as MATCH for listing and delisting strata even though the frozen contract requires both an official anchor and independent daily evidence. That provisional 71/71 count was not accepted or used by a gate.

The evaluator was corrected fail-closed on the same immutable inventory. A bounded follow-up retrieved the exact `601028.SH` delisting date from issuer announcement 2025-044 hosted by CNINFO and pinned the retrieved PDF SHA-256. No security was replaced or reselected.

Final immutable evidence ledger:

```text
ledger_id = 0f6772947b821a5819614c652d08544ac8bc14b789b796eb0f4338f71c79e473
MATCH = 52
MISMATCH = 0
INDEPENDENT_EVIDENCE_UNAVAILABLE = 19
decision = PENDING EVIDENCE
```

The 19 unavailable entries are exactly 10 actual-first-tradable-session samples and 9 delisting-boundary samples that still lack the official anchor required by the preregistered contract. BaoStock observations remain independent daily evidence but cannot substitute for an SSE/SZSE/issuer official anchor. Unavailable entries were not converted to MATCH. The bounded pass ended without open-ended archaeology.

### PIT and formal runtime result

V2 did not satisfy the cross-source contract, so P3/P4 PIT Final Closure was not entered. `StatusAvailabilityPolicyV2` and the historical 16:30 Asia/Shanghai cutoff were unchanged. No PIT PASS artifact was created; `pit_evidence=None` remains required.

The runtime path now pins exact V2 inventory and ledger IDs, exact universe/audit/exception/source-version inputs, and an on-disk content-addressed revocation registry. It no longer selects those formal inputs by modification time or uses a placeholder source identity.

```text
STRUCTURAL = PASS
PIT = PENDING
CROSS_SOURCE = PENDING
SURVIVORSHIP = PASS
EXCEPTION_BUDGET = PASS
SYSTEMATIC_DEFECT = PASS
SOURCE_APPROVAL = PENDING
PUBLICATION_ALLOWED = false
APPROVED_FACTS = 0
DATASET_MANIFEST = 0
PHASE 1B-2A = FAIL CLOSED / PENDING EVIDENCE
```

No V3 contract, PIT PASS artifact, approved status fact, DatasetManifest, scheduler, 1B-2B work, or downstream research work was created.

### Verification commands and exact results

```text
.\.venv\Scripts\python.exe scripts\freeze_phase_1b2a_prospective_inventory.py
contract_id=3a9efd2f1047d9ad0432a72202bf1b8e7f926d153c339106475c37a694b20917; inventory_id=cef91ec0a055f01ac2f0f82ec8e15ce75f4e000acd2123a70685fb25d1df3c9c; sample_count=71

.\.venv\Scripts\python.exe scripts\acquire_phase_1b2a_prospective_evidence.py
total=71; MATCH=52; MISMATCH=0; INDEPENDENT_EVIDENCE_UNAVAILABLE=19; ledger_id=0f6772947b821a5819614c652d08544ac8bc14b789b796eb0f4338f71c79e473

.\.venv\Scripts\python.exe scripts\evaluate_phase_1b2a_gates.py
structural_status=PASS; pit_status=PENDING; cross_source_status=PENDING; survivorship_status=PASS; exception_budget_status=PASS; systematic_defect_status=PASS; decision=PENDING; publication_allowed=false

.\.venv\Scripts\python.exe scripts\publish_phase_1b2a_status.py
decision=PENDING; approval_id=05ab1c98a352f49e6e36e92a42503895ca536a8659a3aec62fe36d7543de3632; equivalence=INSUFFICIENT_EVIDENCE; published_manifest_count=0; published_fact_count=0

.\.venv\Scripts\python.exe -m pytest <focused V2 tests> -q
21 passed in 0.09s

.\.venv\Scripts\python.exe -m pytest -q
309 passed in 9.68s

.\.venv\Scripts\python.exe scripts\verify_standalone.py
PASS forbidden imports: 0
PASS forbidden active paths/dependencies: 0
PASS prohibited repository inventory: 0
PASS phase 1a architecture boundary violations: 0

.\.venv\Scripts\python.exe scripts\clean_room_acceptance.py
clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; build=true; wheel_install=true; wheel_smoke=true; zero_dependency_acceptance=true
clean-room test_output: 309 passed in 107.05s (0:01:47)

credential scan using local DATAHUB_API_KEY and TUSHARE_TOKEN values as sentinels
CREDENTIAL_SCAN_FINDINGS=0

git diff --check
PASS (line-ending notices only; no whitespace errors)
```

## Phase 1B-2A Official Anchor Closure — 2026-09-09

Starting HEAD: `0bf7c87ddc51c88c8958fa7e35d51c609037ff11`.

V1 remains permanently failed. The frozen V2 contract, inventory, candidate hashes,
71 samples, strata, and threshold were not changed or reinterpreted:

```text
V2 contract_id = 3a9efd2f1047d9ad0432a72202bf1b8e7f926d153c339106475c37a694b20917
V2 inventory_id = cef91ec0a055f01ac2f0f82ec8e15ce75f4e000acd2123a70685fb25d1df3c9c
V2 freeze_commit = 53578aa7e50d151eb292472bfed2fd532fdb4748
V2 original ledger_id = 0f6772947b821a5819614c652d08544ac8bc14b789b796eb0f4338f71c79e473
```

The content-addressed `OfficialAnchorGapInventoryV1` is
`5466d1c98a2c2dbae5219ebd3e62512c3d33d96ef12f07f4771c3d46440cb4b9`.
It binds exactly 19 existing frozen candidates: 10 `ACTUAL_FIRST_TRADABLE_SESSION`
and 9 `DELISTING_BOUNDARY`. No sample was replaced or added.

The bounded SSE/SZSE/exchange-hosted/CNINFO retrieval produced official-anchor
supplement `806fb76ff4a4afe94c4e4c6382121d3685b04cee9487959c8bec8781d2caf733`:

```text
recovered MATCH = 18
OFFICIAL_MISMATCH = 0
OFFICIAL_ANCHOR_UNAVAILABLE = 1
```

Every recovered entry pins its candidate hash, identity, session, semantic, source
URL, document title, publication date, retrieved-content SHA-256, and evidence ID.
The complete per-entry evidence and hashes are in the immutable supplement artifact.
The sole remaining blocker is:

```text
identity = 688053.SH
session = 20220708
semantic = ACTUAL_FIRST_TRADABLE_SESSION
resolution = OFFICIAL_ANCHOR_UNAVAILABLE
evidence_id = 6df8af5f3c8a8e9105c08d849fdd150e7449fca625d094a408709d31cecf338b
reason = exact listing announcement was discoverable in third-party mirrors, but
         the bounded run did not recover an exchange/CNINFO-hosted immutable copy
```

Third-party mirror content was not promoted to an official anchor. The final V2
ledger is `d5c80b3e38a4d459dba53eab37cccecfecffad3bbdea95511140c71be7315e99`:

```text
TOTAL = 71
MATCH = 70
MISMATCH = 0
INDEPENDENT_EVIDENCE_UNAVAILABLE = 1
CROSS_SOURCE = PENDING
```

Because the frozen contract requires 71/71 MATCH, PIT Final Closure was not entered.
No `StatusPITKnowledgeTimeEvidenceV1` PASS artifact was created. The existing
`StatusAvailabilityPolicyV2` and historical 16:30 Asia/Shanghai cutoff were not
changed. The real gate remains fail-closed:

```text
STRUCTURAL = PASS
PIT = PENDING
CROSS_SOURCE = PENDING
SURVIVORSHIP = PASS
EXCEPTION_BUDGET = PASS
SYSTEMATIC_DEFECT = PASS
SOURCE_APPROVAL = PENDING
PUBLICATION_ALLOWED = false
APPROVED_FACTS = 0
DATASET_MANIFEST = 0
```

No V3, resampling, threshold change, scheduler, 1B-2B work, or downstream research
work was created.

### Verification commands and exact results

```text
.\.venv\Scripts\python.exe scripts\freeze_phase_1b2a_official_anchor_gaps.py
gap_inventory_id=5466d1c98a2c2dbae5219ebd3e62512c3d33d96ef12f07f4771c3d46440cb4b9; total=19; ACTUAL_FIRST_TRADABLE_SESSION=10; DELISTING_BOUNDARY=9

.\.venv\Scripts\python.exe scripts\acquire_phase_1b2a_official_anchors.py
supplement_id=806fb76ff4a4afe94c4e4c6382121d3685b04cee9487959c8bec8781d2caf733; MATCH=18; OFFICIAL_MISMATCH=0; OFFICIAL_ANCHOR_UNAVAILABLE=1

.\.venv\Scripts\python.exe scripts\reevaluate_phase_1b2a_official_anchors.py
total=71; MATCH=70; MISMATCH=0; INDEPENDENT_EVIDENCE_UNAVAILABLE=1; CROSS_SOURCE=PENDING; ledger_id=d5c80b3e38a4d459dba53eab37cccecfecffad3bbdea95511140c71be7315e99

.\.venv\Scripts\python.exe scripts\evaluate_phase_1b2a_gates.py
STRUCTURAL=PASS; PIT=PENDING; CROSS_SOURCE=PENDING; SURVIVORSHIP=PASS; EXCEPTION_BUDGET=PASS; SYSTEMATIC_DEFECT=PASS; decision=PENDING; publication_allowed=false

.\.venv\Scripts\python.exe scripts\publish_phase_1b2a_status.py
decision=PENDING; approved facts=0; DatasetManifest=0

.\.venv\Scripts\python.exe -m pytest tests/real_audits/test_official_anchor_gaps.py tests/real_audits/test_status_cross_source.py tests/real_audits/test_status_gate_integration.py tests/real_audits/test_status_approval.py -q
14 passed in 0.06s

.\.venv\Scripts\python.exe -m pytest -q
313 passed in 10.82s

.\.venv\Scripts\python.exe scripts\verify_standalone.py
PASS forbidden imports: 0
PASS forbidden active paths/dependencies: 0
PASS prohibited repository inventory: 0
PASS phase 1a architecture boundary violations: 0

.\.venv\Scripts\python.exe -m build
Successfully built stock_screener_v5_2-5.2.0.tar.gz and stock_screener_v5_2-5.2.0-py3-none-any.whl

.\.venv\Scripts\python.exe scripts\clean_room_acceptance.py
clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; build=true; wheel_install=true; wheel_smoke=true; old_pythonpath_removed=true; zero_dependency_acceptance=true
clean-room test_output: 313 passed in 110.44s (0:01:50)

credential scan using local DATAHUB_API_KEY and TUSHARE_TOKEN values as sentinels
CREDENTIAL_SCAN_FINDINGS=0; ENV_TRACKED=NO; .env ignored by .gitignore:9

git diff --check
PASS (line-ending notice only; no whitespace errors)
```

## Phase 1B-2A 688053 SSE document semantic verification — 2026-09-09

Starting HEAD: `bd278e01af2bb7093b6c63048661fd4014287fb7`.

V1 remains permanently failed. V2 contract
`3a9efd2f1047d9ad0432a72202bf1b8e7f926d153c339106475c37a694b20917`
and inventory
`cef91ec0a055f01ac2f0f82ec8e15ce75f4e000acd2123a70685fb25d1df3c9c`
remain unchanged.

The user-specified SSE-hosted PDF was downloaded and content-addressed:

```text
URL = https://star.sse.com.cn/disclosure/listedinfo/announcement/c/new/2023-04-10/688053_20230410_KLOY.pdf
bytes = 566996
document SHA-256 = 2b5cd22ab948ab5c284f9cf378b1f3312f0c34d795cae61976f8d68f70314a66
document title = 关于使用部分超募资金永久性补充流动资金的公告
publication date = 20230410
```

The document is an SSE-hosted issuer disclosure, but its text does not state that
688053.SH listed or first traded on 2022-07-08. It states that the capital verification
report was issued on 2022-07-05 and refers readers to a separate listing announcement
published on 2022-07-07. A reference to another document is not semantic proof of the
effective listing session asserted by the frozen sample.

The immutable fail-closed evidence is:

```text
recovery artifact_id = 72880e4a21ec34b6bc3ba208b67ed7a0cd234f39fce1ab6c8c6fea4dc96a5707
receipt_id = 46e04bb1ff9a933fdd25e5c6044f048ff7c1362017fbebda6ff837633b88dc91
text_verification_id = 897180ed2e4e83c7313e51ffe88ba7ec3c41357f0062295aba49cf703eb14f02
resolution = OFFICIAL_ANCHOR_UNAVAILABLE
reason = document text does not state the asserted effective session
```

A regression test now requires both the security identity and asserted effective
session to be present in verified document text. A URL, downloaded bytes, later
reference, or caller-supplied assertion alone cannot satisfy this semantic check.

Because the specified document failed content validation, the explicit P2 stop branch
was taken. No final ledger replacement or PIT work was performed:

```text
V1 = FAIL permanently
V2 TOTAL = 71
V2 MATCH = 70
V2 MISMATCH = 0
V2 UNAVAILABLE = 1
CROSS_SOURCE = PENDING
PIT = PENDING
SURVIVORSHIP = PASS
EXCEPTION_BUDGET = PASS
SYSTEMATIC_DEFECT = PASS
SOURCE_APPROVAL = PENDING
PUBLICATION_ALLOWED = false
APPROVED_FACTS = 0
DATASET_MANIFEST = 0
```

The 2023 follow-up announcement was not used as contemporaneous 2022-07-08 PIT
knowledge-time evidence. No V3, threshold change, resampling, 1B-2B, or downstream
research work was started.

### Verification commands and exact results

```text
.\.venv\Scripts\python.exe scripts\verify_phase_1b2a_688053_anchor.py
artifact_id=72880e4a21ec34b6bc3ba208b67ed7a0cd234f39fce1ab6c8c6fea4dc96a5707; document_sha256=2b5cd22ab948ab5c284f9cf378b1f3312f0c34d795cae61976f8d68f70314a66; text_verification_id=897180ed2e4e83c7313e51ffe88ba7ec3c41357f0062295aba49cf703eb14f02; resolution=OFFICIAL_ANCHOR_UNAVAILABLE

.\.venv\Scripts\python.exe -m pytest tests/real_audits/test_official_anchor_gaps.py tests/real_audits/test_status_cross_source.py tests/real_audits/test_status_gate_integration.py tests/real_audits/test_status_approval.py -q
15 passed in 0.06s

.\.venv\Scripts\python.exe -m pytest -q
314 passed in 9.62s

.\.venv\Scripts\python.exe scripts\verify_standalone.py
PASS forbidden imports: 0
PASS forbidden active paths/dependencies: 0
PASS prohibited repository inventory: 0
PASS phase 1a architecture boundary violations: 0

.\.venv\Scripts\python.exe -m build
Successfully built stock_screener_v5_2-5.2.0.tar.gz and stock_screener_v5_2-5.2.0-py3-none-any.whl

.\.venv\Scripts\python.exe scripts\clean_room_acceptance.py
clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; build=true; wheel_install=true; wheel_smoke=true; old_pythonpath_removed=true; zero_dependency_acceptance=true
clean-room test_output: 314 passed in 107.01s (0:01:47)
```
