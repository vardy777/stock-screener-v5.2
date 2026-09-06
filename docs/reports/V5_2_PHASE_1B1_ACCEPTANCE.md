# V5.2 Phase 1B-1 Exit Acceptance

Date: 2026-09-06

This report records an honest fail-closed exit. DataHub is assessed by functional research equivalence, not by brand or official-provider status. No global provider approval is issued.

## Frozen source identity

```text
SOURCE = datahubco_tushare_proxy
TRANSPORT = PLAINTEXT_HTTP
TRANSPORT RISK ACKNOWLEDGED = YES
```

The API key is sent in the `X-API-Key` header only. It is absent from URLs, tracked files, raw artifacts, receipts, checkpoints, evidence, approvals, manifests, exceptions and test output.

## Real observations

- `trade_calendar`: 11,688 rows, SSE and SZSE, 2010-01-01 through 2025-12-31, continuous date coverage, explicit open/closed state and previous-session semantics passed. A 2025 official holiday-boundary set produced 78 matches, zero mismatches and zero unresolved observations. The deterministic official sample is not yet complete for 2010-2024.
- `security_master`: 5,549 SSE/SZSE rows comprising 5,215 listed and 334 historically delisted securities. All delisted rows had a delisting date. Native `market` requires a declared board mapping; security type and A-share membership require explicit deterministic derivation. Deterministic official identity verification is incomplete.
- `daily_bar`: not acquired. The frozen daily universe may only be constructed after security-master approval, which remains pending.
- Replay: calendar and master logical pages were reacquired with stable payload identities and distinct acquisition receipts. A real transient failure also exposed and drove a tested retry-classification fix.
- Pagination: explicit `has_more`, offset advancement, terminal pages, repeated-page rejection and non-zero count consistency are enforced. Provider `count=0` is treated as unavailable rather than as a trusted total.

Official references used for the partial calendar check:

- SSE annual closure notices: https://www.sse.com.cn/disclosure/dealinstruc/closed/list/
- SSE 2025 schedule: https://big5.sse.com.cn/site/cht/www.sse.com.cn/disclosure/announcement/general/c/c_20241223_10767108.shtml
- SZSE 2025 notices: https://www.szse.cn/disclosure/notice/general/index_8.html

## Content-addressed decisions

```text
trade_calendar equivalence evidence = e6e9ff566d1727ed3314020fb55abaeb9b2a1ee4cd80609bd7bc6f09d33689ef
trade_calendar approval = 1871363413c0f58c8a92a1f9ecd23598ec452c28ef783e1d424ef1c09e4c3ad3 (PENDING)

security_master equivalence evidence = 805d0a535f4cb506c7c6d8d2dd6b176ff8be66c560175183ab6ad10b9d50be56
security_master approval = aabcc8f9eb76ae78585193c5e4ceac7946c01ee714fa8c4a1cf38cf53175b98d (PENDING)

daily_bar equivalence evidence = 9f039a78a302037d6bd099d4319d39ff749327e3ebcd6bc644a19cd034464dba
daily_bar approval = 28f03b707058d8f7483592ebd0718049d3b3b2b9c83b24628477f27db1a682b3 (PENDING)
```

The runtime evidence is stored under ignored `data/phase_1b1/governance`. Because no dataset is approving, no approved facts or DatasetManifest were published.

## Exit matrix

```text
SOURCE = datahubco_tushare_proxy
TRANSPORT = PLAINTEXT_HTTP
TRANSPORT RISK ACKNOWLEDGED = YES

REAL PROVIDER ACCESS = PASS
CREDENTIAL LEAK SCAN = PASS

TRADE CALENDAR FUNCTIONAL EQUIVALENCE = FAIL
TRADE CALENDAR APPROVAL = PENDING

SECURITY MASTER FUNCTIONAL EQUIVALENCE = FAIL
SECURITY MASTER APPROVAL = PENDING

DAILY BAR FUNCTIONAL EQUIVALENCE = FAIL
DAILY BAR APPROVAL = PENDING

COVERAGE AUDIT = FAIL
PIT AUDIT = FAIL
REVISION AUDIT = FAIL
PAGINATION AUDIT = FAIL
CROSS-SOURCE VERIFICATION = FAIL
DETERMINISTIC REAL-DATA REPLAY = FAIL
SOURCE APPROVAL DERIVATION = PASS
APPROVED FACT PUBLICATION = FAIL
DATASET MANIFEST = FAIL
PHASE 1A REGRESSION = PASS
CLEAN-ROOM = PASS

PHASE 1B-1 = FAIL
READY FOR PHASE 1B-2 = NO

HISTORICAL PIT DATA = FAIL
READY FOR LABEL ENGINE = NO
```

The aggregate gates remain FAIL wherever daily-bar work is correctly blocked or cross-source evidence is incomplete. This does not mean the DataHub source has been rejected; it means the evidence threshold for approval has not yet been met.

## Final re-validation — supersedes earlier generated identities

This section records the final close attempt at repository HEAD after freezing `SecurityMasterNormalizationPolicyV1`. It supersedes the generated IDs earlier in this report; the historical FAIL narrative above is retained deliberately.

```text
security_master normalization policy = a3d64de6826ce8ad57ca64d3225860770c41e0c25a76900777e50966e7653932
security_master input rows = 5549
security_master deterministically normalized rows = 5546
security_master unsupported rows = 3

trade_calendar equivalence evidence = 578ff31e85d21f1864c5a01c0f4bf084749e0f565efdf73cfd6c9d2d550ebbb2
trade_calendar approval = 97f37b1b5983ee14728de550b9b649a7a86a0e550570b71c969d44b26279dc23 (PENDING)

security_master equivalence evidence = a4d724784e340c29f6e522768fbb762796b93ba2837d353ccaad3891600fe7f9
security_master approval = 9fc23825b06e65892d2b0b8970598d94c0efb7f2e6205b8e97b9b88e5fcd2649 (PENDING)

daily_bar equivalence evidence = 5767a07de72e79f223e1a26bf81aea597d44074018dd59770e3e17697697125c
daily_bar approval = 678c9c4df38d53620aab61f233cdadcdfa2283e29fed5dda625a45b7800a8d5a (PENDING)

equivalence replay summary SHA-256 = 5A78BFE24151A85CDDF270066CE506C1C53063107DEC7694A13D20919BE6A8A3
repeated finalization hash match = True
```

The three unsupported master rows have unknown or missing provider `market` values. The normalization policy fails closed; it does not default them to a main board or A-share. Official deterministic verification for all required calendar years and master identities remains incomplete. Therefore daily-bar acquisition remains prohibited by the upstream approval gate.

## Complete verification command record

Every command below was executed from the repository root. Exit code was zero unless explicitly described otherwise.

```text
COMMAND:
.\.venv\Scripts\python.exe -m pytest tests/data/test_dataset_equivalence.py tests/data/test_pagination.py tests/data/test_source_approval.py tests/data/test_manifests.py tests/real_audits/test_security_master_normalization.py -q
RESULT:
36 passed in 0.11s

COMMAND:
.\.venv\Scripts\python.exe -m pytest -q
RESULT:
175 passed in 0.63s

COMMAND:
.\.venv\Scripts\python.exe scripts/verify_standalone.py
RESULT:
PASS forbidden imports: 0
PASS forbidden active paths/dependencies: 0
PASS prohibited repository inventory: 0
PASS phase 1a architecture boundary violations: 0

COMMAND:
.\.venv\Scripts\python.exe scripts/clean_room_acceptance.py
RESULT:
clean-room dependencies/install/tests = true
wheel install/smoke = true
zero dependency acceptance = true
clean-room test output = 175 passed in 0.99s

COMMAND:
.\.venv\Scripts\python.exe scripts/phase_1b1_finalize.py (executed twice)
RESULT:
trade_calendar rows=11688, equivalence=INSUFFICIENT_EVIDENCE, approval=PENDING
security_master rows=5549, equivalence=INSUFFICIENT_EVIDENCE, approval=PENDING
daily_bar rows=0, equivalence=INSUFFICIENT_EVIDENCE, approval=PENDING
summary hashes from both runs matched exactly

COMMAND:
actual credential and sentinel scan over tracked/runtime artifact areas
RESULT:
PASS actual credential confined to ignored .env
PASS credential/sentinel artifact findings: 0

COMMAND:
git diff --check
RESULT:
exit 0; no whitespace errors
```

Final full-suite and environmental command timings may vary across runs. The exit commit records the last fresh results below before push.

## Upstream blocker re-evaluation — final status at this revision

This is the latest section and supersedes the prior re-validation status while preserving it as historical evidence.

### Trade-calendar unresolved inventory

```text
inventory schema = TradeCalendarUnresolvedSampleInventoryV1
inventory id = 0242b7d10a358d81f5c1b40a42920ef75c55b1e42f6d1e6ea3a77d85b5e11cd0
total frozen samples = 256
verified = 5
unresolved = 251
mismatch = 0

SSE: verified=3, unresolved=125
SZSE: verified=2, unresolved=126

spring_festival_boundary: verified=0, unresolved=64
national_day_boundary: verified=3, unresolved=61
weekend_makeup_boundary: verified=2, unresolved=62
cross_year_boundary: verified=0, unresolved=64

2010-2024: 16 unresolved per year
2025: 5 verified, 11 unresolved
```

The inventory is generated from the frozen hash-selection seed and records every exact provider observation and official-resolution status. The earlier 78/78 boundary comparison remains valid historical evidence, but only five observations overlap the exact frozen sample inventory. It therefore cannot resolve the other 251 samples.

### Security-master exception disposition

```text
evidence schema = SecurityMasterNormalizationExceptionEvidenceV1
evidence id = b3e050a611fa0772473341eedb1ba97fcddc33cf204db27c3cc82126e46e48c6
normalization policy id = d7a7eedfb3dbcbc18382d5d2b4423b2362858b1c48feea7472fea4e7861b5b7d

input = 5549
NORMALIZED_ELIGIBLE = 5546
EXCLUDED_NON_TARGET = 1
REJECTED_UNRESOLVED = 2
```

The excluded record is an SSE-listed CDR, supported by the SSE listing announcement. The two unresolved records represent a legacy absorbed-company identity and a current code combined with older historical listing identity. Neither can be converted into a permanent A-share identity rule without effective-dated official evidence. Raw records, classification, reasons and official source identities are retained in the ignored immutable evidence chain.

### Latest decisions

```text
TRADE CALENDAR UNRESOLVED SAMPLES = 251
TRADE CALENDAR FUNCTIONAL EQUIVALENCE = FAIL
TRADE CALENDAR APPROVAL = PENDING

SECURITY MASTER INPUT ROWS = 5549
SECURITY MASTER NORMALIZED ELIGIBLE = 5546
SECURITY MASTER EXCLUDED NON-TARGET = 1
SECURITY MASTER UNRESOLVED = 2
SECURITY MASTER FUNCTIONAL EQUIVALENCE = FAIL
SECURITY MASTER APPROVAL = PENDING

DAILY BAR ENTRY UNLOCKED = NO
DAILY BAR ACQUISITION = NOT STARTED

PHASE 1B-1 = FAIL
READY FOR PHASE 1B-2 = NO
HISTORICAL PIT DATA = FAIL
READY FOR LABEL ENGINE = NO
```

### Latest content-addressed approval evaluation

```text
trade_calendar equivalence = 578ff31e85d21f1864c5a01c0f4bf084749e0f565efdf73cfd6c9d2d550ebbb2
trade_calendar approval = 97f37b1b5983ee14728de550b9b649a7a86a0e550570b71c969d44b26279dc23 (PENDING)

security_master equivalence = 6b1fd47c72f067fbcfc1427458fad935c176322509d3ecab3c0d48d5b3c7b997
security_master approval = d2d8fbdf4c57e2d981fd144a0879fd848939512ce9e2725edfe8d340d89e10b5 (PENDING)

daily_bar equivalence = 5767a07de72e79f223e1a26bf81aea597d44074018dd59770e3e17697697125c
daily_bar approval = 678c9c4df38d53620aab61f233cdadcdfa2283e29fed5dda625a45b7800a8d5a (PENDING)
```

### Final verification commands and results

```text
COMMAND: .\.venv\Scripts\python.exe -m pytest tests/real_audits/test_blocker_evidence.py tests/real_audits/test_security_master_normalization.py -q
RESULT: 15 passed in 0.16s

COMMAND: .\.venv\Scripts\python.exe scripts/resolve_phase_1b1_blockers.py
RESULT: calendar total=256 verified=5 unresolved=251 mismatch=0; master input=5549 eligible=5546 excluded=1 unresolved=2

COMMAND: .\.venv\Scripts\python.exe -m pytest -q
RESULT: 180 passed in 0.77s
```

```text
COMMAND: .\.venv\Scripts\python.exe scripts/verify_standalone.py
RESULT: forbidden imports=0; forbidden active paths/dependencies=0; prohibited repository inventory=0; phase 1a architecture boundary violations=0

COMMAND: .\.venv\Scripts\python.exe scripts/clean_room_acceptance.py
RESULT: build=true; clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; wheel_install=true; wheel_smoke=true; zero_dependency_acceptance=true; clean-room test output="180 passed in 1.02s"

COMMAND: actual credential and sentinel scan over tracked/runtime artifact areas
RESULT: actual credential confined to ignored .env; credential/sentinel artifact findings=0

COMMAND: git diff --check
RESULT: exit 0; no whitespace errors
```

## Approval-policy adequacy review — Outcome C

This is the latest re-evaluation and supersedes only the current status fields above. All V1 artifacts and earlier PENDING decisions remain immutable and reproducible.

```text
ApprovalPolicyAdequacyReviewV1 = 85f38a57975b56eac4352571f35f20712865a9b326d515b6bea006b22bafa449
CrossSourceEvidencePolicyV2 = 4112a50ce8f06b1b9f685bb19804488888c8d641f6465dc9e152dd505ad889b6
CrossSourceEvidencePolicyV2 status = DESIGNED_NOT_ADOPTED
decision = RETAIN_V1_PENDING
```

### Gate analysis

- Coverage and continuity prevent silent truncation and missing historical sessions; they directly protect data correctness.
- Explicit session state and previous-session consistency prevent weekday inference and incorrect event alignment; they directly protect PIT/session semantics.
- Delisted-security coverage and effective-dated identity prevent current-membership survivorship contamination; they directly protect historical-universe correctness.
- Replay, revision and pagination gates prevent mutable provider responses, repeated pages and transport observations from silently changing research facts.
- Cross-source comparison detects provider semantic/value errors. `MISMATCH`, `UNRESOLVED_EVIDENCE`, `PROVIDER_ERROR`, and `OFFICIAL_REFERENCE_UNAVAILABLE` are now distinct machine states. Unresolved evidence is not counted as a mismatch.
- V1's requirement for official resolution of every frozen sample is stricter than necessary for functional equivalence and can be blocked by archive availability rather than provider quality. However, replacing it now would be result-driven: no Tier 3 independent deterministic sample exists yet.
- V2 therefore defines four honest tiers: structured official records, official notices, independent trusted data, and internal invariant/replay evidence. Tier 3/4 never impersonate official truth. Its predeclared gate requires official anchors, 256 independent samples, and zero unexplained mismatches.

V2 could support `EQUIVALENT_WITH_RULES` at lower operational cost while remaining strict because independent observations test the entire frozen sample inventory and official records anchor semantics. It is not adopted in this revision because the required independent sample has not been acquired. No threshold was tuned against the current provider result.

### Security quarantine and survivorship impact

Two `QuarantinedSecurityIdentityV1` artifacts were generated. Formal universe filtering excludes them, explicit requests fail closed, and their raw/evidence lineage is retained. The manifest contract now pins input, eligible, excluded and quarantined counts, quarantine hashes, normalization policy and approval-policy identity.

- `T600018.SH`: possible interval 2000-07-19 through 2006-10-20. Quarantine creates a bounded false exclusion, but the interval predates the acquired calendar, so affected trading-session count cannot be computed from approved inputs.
- `302132.SZ`: possible start 2010-08-27; the code-reassignment effective date and predecessor lineage are unresolved. Impact is unbounded false exclusion or cross-identity historical corruption.

Quarantine reliably prevents contamination, but approving only the remaining identities would still permit survivorship bias through false exclusion. Because one impact interval is unbounded, quarantine is not sufficient for security-master approval under the current historical-universe contract.

### Decision gate

```text
APPROVAL POLICY ADEQUACY REVIEW = PASS

TRADE CALENDAR POLICY V1 = RETAINED
TRADE CALENDAR APPROVAL = PENDING

SECURITY MASTER POLICY V1 = RETAINED
SECURITY MASTER APPROVAL = PENDING
SECURITY MASTER QUARANTINED IDENTITIES = 2

DAILY BAR ENTRY UNLOCKED = NO
DAILY BAR ACQUISITION = NOT STARTED

PHASE 1B-1 = FAIL
READY FOR PHASE 1B-2 = NO
HISTORICAL PIT DATA = FAIL
READY FOR LABEL ENGINE = NO
```

### Verification record for adequacy review

```text
COMMAND: .\.venv\Scripts\python.exe scripts/review_phase_1b1_policy.py (executed twice)
RESULT: identical review/policy IDs on both runs; RETAIN_V1_PENDING; quarantined=2; daily_bar unlocked=NO

COMMAND: .\.venv\Scripts\python.exe -m pytest tests/real_audits/test_policy_adequacy.py tests/real_audits/test_blocker_evidence.py tests/real_audits/test_security_master_normalization.py tests/data/test_manifests.py -q
RESULT: 27 passed in 0.18s

COMMAND: .\.venv\Scripts\python.exe -m pytest -q
RESULT: 186 passed in 0.82s
```

```text
COMMAND: .\.venv\Scripts\python.exe scripts/verify_standalone.py
RESULT: forbidden imports=0; forbidden active paths/dependencies=0; prohibited repository inventory=0; phase 1a architecture boundary violations=0

COMMAND: .\.venv\Scripts\python.exe scripts/clean_room_acceptance.py
RESULT: build=true; clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; wheel_install=true; wheel_smoke=true; zero_dependency_acceptance=true; clean-room test output="186 passed in 1.13s"

COMMAND: actual credential and sentinel scan over tracked/runtime artifact areas
RESULT: actual credential confined to ignored .env; credential/sentinel artifact findings=0

COMMAND: git diff --check
RESULT: exit 0; no whitespace errors
```
