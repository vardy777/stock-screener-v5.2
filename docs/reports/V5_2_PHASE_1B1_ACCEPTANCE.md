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

## Final superseding acceptance — TLS and exception-governance closure

This is the chronologically latest and authoritative result. It supersedes every earlier pending/rejected matrix in this append-only report; detailed IDs, rationale, and the complete command record are in “TLS revalidation and exceptional-security governance — superseding result” above.

```text
SZSE OFFICIAL TLS REVALIDATION = PASS

CALENDAR COMPOSITE:
TOTAL = 256
MATCH = 256
MISMATCH = 0
UNRESOLVED = 0
PROVIDER_ERROR = 0

TRADE CALENDAR APPROVAL = APPROVED_WITH_RULES

SECURITY MASTER EXCEPTION POLICY = PASS
EXCEPTION BUDGET = PASS
SYSTEMATIC DEFECT AUDIT = PASS

SECURITY MASTER EXCEPTIONS = 4
SECURITY MASTER QUARANTINED = 1

SECURITY MASTER APPROVAL = APPROVED_WITH_RULES

DAILY BAR ENTRY UNLOCKED = YES
DAILY BAR ACQUISITION = NOT STARTED

PHASE 1B-1 = FAIL
READY FOR PHASE 1B-2 = NO
HISTORICAL PIT DATA = FAIL
READY FOR LABEL ENGINE = NO
```

```text
FOCUSED TESTS = 33 passed in 0.11s
FULL SUITE = 219 passed in 1.11s
STANDALONE VERIFIER = PASS
CLEAN-ROOM TESTS = 219 passed in 1.57s
BUILD / WHEEL INSTALL / WHEEL SMOKE = PASS
CREDENTIAL / SENTINEL FINDINGS = 0
.env = IGNORED AND UNTRACKED
GIT DIFF CHECK = PASS
```

## Daily-bar completion — final superseding acceptance (2026-09-07)

This section supersedes every earlier daily-bar `NOT STARTED`, `PENDING`, Phase 1B-1 `FAIL`, and readiness statement in this report. It does not supersede the frozen trade-calendar or security-master approvals.

### Frozen entry and real acquisition

```text
TRADE CALENDAR APPROVAL ID = 1581b4d367dba1256247ddd13e09b53d0f95b5b1deeb40af9e6ed4a36606353b
SECURITY MASTER APPROVAL ID = f208c17accba6b669359f476b2fdf3a1bc9ec6856e7fa1831ccdd1c42b80d8cf
DAILY BAR UNIVERSE ID = 2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01
DAILY BAR REQUEST INVENTORY ID = 9b1d034f00ab0d637bc56ab120ffcf725f226f21c09d27c3b85e36a4f644a6ce
EXECUTABLE PLAN ID = 93f30b87c86721ea9632a0e566c0a6c8acf1fe12796889d84765c6b48915f1b3
PRICE BASIS = UNADJUSTED_RAW

EXPECTED REQUESTS = 5,548
COMPLETED REQUESTS = 5,548
PAGES = 5,548
RAW ROWS = 13,138,865
RAW ACQUISITION PROCESS EXIT = 0
```

All requests used canonical `ProviderRequestV1` identities mapped bijectively from the frozen logical inventory. Every request has one terminal page; schema, finite numeric values, OHLC inequalities, non-negative volume/amount, approved-session membership, request identity and effective security identity passed the full-row scan. The known provider-current `302132.SZ` history is normalized through the approved effective identity graph to `300114.SZ` before 2025-02-17.

### Research-scope coverage and rules

```text
COVERAGE = 2024-01-01 -> 2025-12-31
REQUESTED SYMBOLS = 5,548
EFFECTIVE IDENTITIES = 5,549
REQUESTED SESSIONS = 485
APPLICABLE SYMBOL-SESSIONS = 2,487,799
OBSERVED FACTS = 2,481,310
MISSING SYMBOL-SESSIONS = 6,489
COVERAGE RATIO = 99.73916703077701%
SYMBOLS WITH FACTS = 5,261
```

The 6,489 absent bars are not interpreted as suspension, delisting, or zero-volume facts. Approval is therefore rule-scoped to observed bars only. Security-status semantics remain Phase 1B-2 work. No absent combination is materialized as a `DailyBarFactV1`.

### Units, cross-source and adjustment audit

```text
CROSS-SOURCE EVIDENCE ID = 32d3b74551fc962cecb61a11839bdc177f1f3492fa1d11f8fba2fc9c15c7dd87
REFERENCE = BaoStock adjustflag=3 (unadjusted)
FROZEN STRATA = normal, high volatility, limit-like, IPO boundary,
                delisting boundary, holiday-adjacent before/after,
                identity-transition boundary
PRICE TOLERANCE = 0.0001
ALL OHLC DIFFERENCES = 0.0000
VOLUME CONVERSION = provider vol * 100 = shares
ALL VOLUME DIFFERENCES = 0 shares
AMOUNT CONVERSION = provider amount * 1000 = yuan
MAXIMUM AMOUNT DIFFERENCE = 0.47 yuan
FROZEN AMOUNT TOLERANCE = 1 yuan
ZERO-VOLUME OBSERVATION = NOT OBSERVED IN PROVIDER RAW

ADJUSTMENT SAMPLE = 000001.SZ / 2010-01-04
PROVIDER CLOSE = 23.71
REFERENCE UNADJUSTED CLOSE = 23.7100
REFERENCE FORWARD-ADJUSTED CLOSE = 6.1242455800
UNADJUSTED RAW VALIDATION = PASS
```

### Replay, approval and immutable facts

The real replay selected the first, middle and last frozen logical requests. All three later acquisitions reproduced the exact prior payload hash and produced a new receipt. The changed-payload revision branch remains covered by the provider identity contract test.

```text
REAL REPLAY EVIDENCE ID = f2dc6b315eef600dc83baa74224d8149f2c1ea83bc6ebed7586dd3c4cb8c19cf
REPLAY SAMPLE = 3/3 SAME PAYLOAD HASH
NEW RECEIPTS = 3/3

SUPERSEDED DAILY BAR APPROVAL = 50777e6ca46c0149885f0218291a0ce539f36cbfc1ef71e6e56a9f8131a12eee
SUPERSEDED APPROVAL DISPOSITION = IMMUTABLY REVOKED AFTER EFFECTIVE-IDENTITY COVERAGE ACCOUNTING CORRECTION
CURRENT DAILY BAR APPROVAL = APPROVED_WITH_RULES
CURRENT DAILY BAR APPROVAL ID = 1ead49dfaefdfb8e4e75c9d94170d440abe77986e3388a6e96e6805537c1173c
DAILY BAR FACTS = 2,481,310
FACT SHARDS = 5,260
FACT EFFECTIVE IDENTITIES = 5,261
PINNED DAILY-BAR RECEIPTS = 5,551
DATASET MANIFEST ID = 1ad71807083aba6222fa6ab27aedf47c0ac2e2ba65a56ad1ce5ae5956db43ead
```

Each fact pins its raw payload hash and deterministically applies `UNADJUSTED_RAW`, verified unit factors, effective identity, and `available_at = D 15:00 Asia/Shanghai`. Historical acquisition time is not used as historical availability. The manifest pins the exact daily approval, both upstream approvals, request inventory, raw and receipt hashes, normalization/unit/exception policies, empty exception-set hash, cross-source evidence, coverage and fact-shard hashes.

### Complete validation command record

```text
COMMAND: .\.venv\Scripts\python.exe scripts\phase_1b1_audit.py daily_bar --resume --workers 64
RESULT: exit 0; requests=5,548/5,548; pages=5,548; rows=13,138,865

COMMAND: .\.venv\Scripts\python.exe scripts\evaluate_daily_bar.py
RESULT: exit 0; full-row structural findings only rows=13,138,865; audit id=c090d1762828db2b713a9c7e70ab076a2a37efc4a9a5f111bf7fdb61de9a0939

COMMAND: .\.venv\Scripts\python.exe scripts\audit_daily_bar_reference.py
RESULT: exit 0; cross-source PASS; unit PASS; UNADJUSTED_RAW PASS; evidence id=32d3b74551fc962cecb61a11839bdc177f1f3492fa1d11f8fba2fc9c15c7dd87

COMMAND: .\.venv\Scripts\python.exe scripts\replay_daily_bar_sample.py
RESULT: exit 0; first/middle/last payload hashes stable; distinct receipts created; evidence id=f2dc6b315eef600dc83baa74224d8149f2c1ea83bc6ebed7586dd3c4cb8c19cf

COMMAND: .\.venv\Scripts\python.exe scripts\publish_daily_bar_facts.py
RESULT: exit 0; approval=APPROVED_WITH_RULES; facts=2,481,310; symbols=5,261; shards=5,260; manifest=PASS

COMMAND: .\.venv\Scripts\python.exe -m pytest tests/data/test_manifests.py -q
RESULT: 8 passed in 0.03s

COMMAND: .\.venv\Scripts\python.exe -m pytest tests/data/test_daily_bar_facts.py tests/data/test_manifests.py tests/real_audits/test_daily_bar_audit_contracts.py tests/real_audits/test_daily_bar_entry.py -q
RESULT: 25 passed in 0.06s

COMMAND: .\.venv\Scripts\python.exe -m pytest -q
RESULT: initial final run 239 passed in 43.27s; post-package-metadata final rerun 239 passed in 9.74s

COMMAND: .\.venv\Scripts\python.exe -m compileall -q src scripts
RESULT: exit 0

COMMAND: .\.venv\Scripts\python.exe scripts\verify_standalone.py
RESULT: exit 0; forbidden imports=0; forbidden active paths/dependencies=0; prohibited repository inventory=0; phase 1a boundary violations=0

COMMAND: .\.venv\Scripts\python.exe -m build
RESULT: exit 0; sdist and wheel built successfully

COMMAND: .\.venv\Scripts\python.exe scripts\clean_room_acceptance.py
RESULT: exit 0; build=true; clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; old_pythonpath_removed=true; wheel_install=true; wheel_smoke=true; zero_dependency_acceptance=true; archive findings=0; clean-room tests="239 passed in 102.68s"

COMMAND: actual credential scan over every tracked and untracked non-ignored repository candidate; git ls-files .env; git check-ignore -v .env
RESULT: repository-candidate credential findings=0; .env tracked=NO; .env ignored by .gitignore:9

COMMAND: git diff --check
RESULT: exit 0; no whitespace errors (Git emitted LF-to-CRLF working-copy warnings only)
```

### Final Phase 1B-1 gate

```text
DAILY BAR REAL ACQUISITION = PASS

RAW COVERAGE = PASS
PAGINATION = PASS
SCHEMA = PASS
OHLC STRUCTURE = PASS
SESSION ALIGNMENT = PASS
SECURITY IDENTITY ALIGNMENT = PASS

VOLUME UNIT = PASS
AMOUNT UNIT = PASS

UNADJUSTED RAW VALIDATION = PASS

CROSS SOURCE = PASS
REPLAY = PASS
REVISION = PASS

EXCEPTION BUDGET = PASS
SYSTEMATIC DEFECT AUDIT = PASS

DAILY BAR APPROVAL = APPROVED_WITH_RULES
APPROVED FACTS PUBLICATION = PASS
DATASET MANIFEST = PASS

PHASE 1B-1 = PASS
READY FOR PHASE 1B-2 = YES

HISTORICAL PIT DATA = FAIL
READY FOR LABEL ENGINE = NO
```

The project must stop at this gate. Phase 1B-2, features, labels, ranking, ML, backtesting and alpha claims remain unauthorized.

## TLS revalidation and exceptional-security governance — superseding result

This section supersedes the prior upstream result while preserving every prior artifact. The original SZSE source, composite, V2 adoption, and approval remain immutable, but are now covered by transport-trust artifact `2e5a273b0d2a68268fba93a79403402038306eaa9f4bd5daadfed2eae66c2937` with `TLS_VERIFICATION=DISABLED` and `EVIDENCE_TRUST=INVALID_FOR_FINAL_APPROVAL`. Approval `08933ef18a3532078ade97f6f5f574216e68f04225a95d7c7838bed5ad9b840d` is immutably revoked by `9591e05cc5fae5a059a6183f791f20ca4261ba8fb9b50619439fe1aef625037b`; it is not inherited by the secure evaluation.

### Secure exact-sample calendar replay

```text
SZSE OFFICIAL TLS REVALIDATION = PASS
TLS CERTIFICATE VERIFIED = true
HOSTNAME VERIFIED = true
HTTPS TO HTTP DOWNGRADE = FORBIDDEN
SECURE SOURCE ID = b23194c57ee1004105413da7d9a09a141d5cffed3d8797739d4522ac25e2ff24
EXACT PRIOR SZSE SAMPLE IDS = 128 / 128
SECURE COMPOSITE ID = 19e54246af0355173a961cc9d91f6842e4094e2732bc650eab47c25734d5bece
SECURE V2 ADOPTION ID = 0275632a8fb4d6e2de5990b68168f1da2d6244190dbc1e628e8693e82e6d13e6

CALENDAR COMPOSITE:
TOTAL = 256
MATCH = 256
MISMATCH = 0
UNRESOLVED = 0
PROVIDER_ERROR = 0

TRADE CALENDAR APPROVAL = APPROVED_WITH_RULES
TRADE CALENDAR APPROVAL ID = 1581b4d367dba1256247ddd13e09b53d0f95b5b1deeb40af9e6ed4a36606353b
```

### Exceptional-security re-evaluation

The exception budget was frozen independently of the observed four records: absolute ceiling 10, ratio ceiling 0.1%, explicit field-scoped coverage/session impact ceiling 0.1%, no unknown intervals, and no systematic semantic cluster. Three historical SZSE board observations are resolved by their 1993/1996/1997 listing dates and the official SZSE market chronology (main board existed from 1990; SME board began in 2004; ChiNext began in 2009). `600747.SH` remains an active field-scoped quarantine because SSE official sources disagree on the exact `delisting_date` semantic. Research requiring that field receives explicit `UniverseExclusionEvidenceV1`; no board or date is defaulted and no exclusion is silent.

```text
SECURITY MASTER EXCEPTION POLICY = PASS
EXCEPTION POLICY ID = d4d6cff9b8a51405eaeffb0ff9dca2189c589aac825ccb2d9cfd9db4e39fb2a2
EXCEPTION BUDGET = PASS
EXCEPTION BUDGET ID = 4bdbccfcf03cb7584860a54d5c3fdf2356045bbd6710fb4949dde80741b1350c
EXCEPTION SET HASH = a241e5adc5b66691c37c14ab5ef0c7456d8d46be6868ccf0b6cbeee6586a086f
SYSTEMATIC DEFECT AUDIT = PASS
PATTERN AUDIT ID = 592582f0378a14181e86a1e0f88b55bc5d1942b155f8e0c305286c6d4df38c64

SECURITY MASTER EXCEPTIONS = 4
SECURITY MASTER QUARANTINED = 1
RESOLVED EXCEPTIONS = 3
ACTIVE FIELD-SCOPED QUARANTINE = 600747.SH / delisting_date

SECURITY MASTER APPROVAL = APPROVED_WITH_RULES
SECURITY MASTER APPROVAL ID = f208c17accba6b669359f476b2fdf3a1bc9ec6856e7fa1831ccdd1c42b80d8cf
```

### Combined gate and daily-bar planning artifacts

```text
COMBINED UPSTREAM GATE = a155e05358bb863bc5788e8c4f93e397ad4f6ee8430dc4a36b03f596df094e13
DAILY BAR ENTRY UNLOCKED = YES
DETERMINISTIC DAILY BAR UNIVERSE = 2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01
DAILY BAR REQUEST INVENTORY = 9b1d034f00ab0d637bc56ab120ffcf725f226f21c09d27c3b85e36a4f644a6ce
ADJUSTMENT = UNADJUSTED_RAW
VOLUME UNIT AUDIT = REQUIRED_BEFORE_APPROVAL
AMOUNT UNIT AUDIT = REQUIRED_BEFORE_APPROVAL
DAILY BAR ACQUISITION = NOT STARTED

PHASE 1B-1 = FAIL
READY FOR PHASE 1B-2 = NO
HISTORICAL PIT DATA = FAIL
READY FOR LABEL ENGINE = NO
```

### Complete verification record for this superseding result

```text
COMMAND: .\.venv\Scripts\python.exe scripts\acquire_szse_calendar_audit.py
RESULT: secure default/system CA acquisition succeeded; exact_szse_unresolved=128; total=256; match=256; mismatch=0; unresolved=0; provider_error=0; V2=ADOPTED

COMMAND: .\.venv\Scripts\python.exe scripts\evaluate_phase_1b1_upstream.py (executed twice)
RESULT: byte-identical console result and identical content IDs; trade_calendar=APPROVED_WITH_RULES; security_master=APPROVED_WITH_RULES; exceptions=4; quarantined=1; exception_budget=PASS; systematic_defect=PASS; daily_bar unlocked=YES; acquisition=NOT_STARTED

COMMAND: .\.venv\Scripts\python.exe -m pytest tests\real_audits\test_verified_https.py tests\real_audits\test_exception_governance.py tests\real_audits\test_daily_bar_inventory.py tests\real_audits\test_composite_calendar.py tests\real_audits\test_security_master_governance.py tests\data\test_source_approval.py -q
RESULT: 33 passed in 0.11s

COMMAND: .\.venv\Scripts\python.exe -m pytest -q
RESULT: 219 passed in 1.09s

COMMAND: .\.venv\Scripts\python.exe scripts\verify_standalone.py
RESULT: forbidden imports=0; forbidden active paths/dependencies=0; prohibited repository inventory=0; phase 1a architecture boundary violations=0

COMMAND: .\.venv\Scripts\python.exe scripts\clean_room_acceptance.py
RESULT: build=true; clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; wheel_install=true; wheel_smoke=true; zero_dependency_acceptance=true; archive_findings=0; clean-room test output="219 passed in 1.62s"

COMMAND: actual credential and sentinel scan over tracked/runtime artifact areas; git check-ignore .env; git tracked-file check for .env
RESULT: credential/sentinel findings=0; .env ignored; .env tracked=NO

COMMAND: git diff --check
RESULT: exit 0; no whitespace errors
```

## Current acceptance result

The final, superseding result is the Tier 3 and identity-lineage re-evaluation in this report: calendar and security master remain PENDING; V2 remains DESIGNED_NOT_ADOPTED; daily-bar entry remains locked; Phase 1B-1 remains FAIL.

The current verification record is: focused tests 34 passed in 0.20s; full suite 193 passed in 0.99s; standalone boundary checks all passed; clean-room build/install/test/wheel/smoke passed with 193 passed in 1.24s; credential/sentinel findings 0; .env is ignored and untracked; git diff --check exited 0.

## Final superseding status — Tier 3 and identity lineage

The current decision is the Tier 3/identity-lineage result recorded above, not the retained historical two-quarantine snapshot.

```text
TIER 3 SOURCE INDEPENDENCE = PASS
CALENDAR TIER 3 SAMPLE = MATCH 128 / MISMATCH 0 / UNRESOLVED 128 / PROVIDER_ERROR 0
CROSS SOURCE POLICY V2 = DESIGNED_NOT_ADOPTED
TRADE CALENDAR APPROVAL = PENDING

302132 HISTORICAL IDENTITY = RESOLVED
SECURITY MASTER QUARANTINED IDENTITIES = 1
SECURITY MASTER APPROVAL = PENDING

DAILY BAR ENTRY UNLOCKED = NO
DAILY BAR ACQUISITION = NOT STARTED
PHASE 1B-1 = FAIL
READY FOR PHASE 1B-2 = NO
HISTORICAL PIT DATA = FAIL
READY FOR LABEL ENGINE = NO
```

### Final repository verification

```text
COMMAND: .\.venv\Scripts\python.exe -m pytest -q
RESULT: 193 passed in 0.99s

COMMAND: .\.venv\Scripts\python.exe scripts\verify_standalone.py
RESULT: forbidden imports=0; forbidden active paths/dependencies=0; prohibited repository inventory=0; phase 1a architecture boundary violations=0

COMMAND: .\.venv\Scripts\python.exe scripts\clean_room_acceptance.py
RESULT: build=true; clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; wheel_install=true; wheel_smoke=true; zero_dependency_acceptance=true; clean-room test output="193 passed in 1.24s"

COMMAND: actual credential plus sentinel scan over runtime artifact areas; git check-ignore .env; git tracked-file check for .env
RESULT: credential/sentinel findings=0; .env ignored; .env tracked=NO

COMMAND: .\.venv\Scripts\python.exe -m py_compile scripts\acquire_szse_calendar_audit.py scripts\resolve_security_master_official_sample.py scripts\evaluate_phase_1b1_upstream.py src\v5_2\data\real_audits\tier3_calendar.py src\v5_2\data\real_audits\security_master_governance.py
RESULT: exit 0; all new Python modules compile

COMMAND: git diff --check
RESULT: exit 0; no whitespace errors
```

## Tier 3 independent calendar evidence and identity-lineage re-evaluation

This section is the latest Phase 1B-1 evaluation. It preserves all earlier V1 artifacts and decisions. BaoStock was used only as an independent audit source through the local ignored virtual environment; it was not added as a project or runtime dependency.

### Independent trade-calendar comparison

```text
frozen sample inventory = 0242b7d10a358d81f5c1b40a42920ef75c55b1e42f6d1e6ea3a77d85b5e11cd0
Tier 3 source identity = 51361caa8e8c23285d8c756d12cb7c45c6e7939a240b7db3dcd90b7cfe49713d
Tier 3 source = BaoStock 0.9.3 / query_trade_dates
source independence = PASS
sample IDs reused exactly = 256 / 256

MATCH = 128
MISMATCH = 0
UNRESOLVED = 128
PROVIDER_ERROR = 0
```

BaoStock supplied independent SSE calendar observations. Its source contract was not extended to SZSE without evidence, so all 128 SZSE observations remain `UNRESOLVED`, not matches and not mismatches. Consequently, the frozen V2 completeness threshold is not met.

```text
CROSS SOURCE POLICY V2 = DESIGNED_NOT_ADOPTED
TRADE CALENDAR APPROVAL = PENDING
```

### 302132.SZ effective-dated identity lineage

Official SZSE evidence resolves the historical identity into this immutable graph:

```text
300114.SZ = 2010-08-27 through 2025-02-16
transition = SECURITY_CODE_CHANGE
302132.SZ = 2025-02-17 through open-ended
effective identity graph = 6275f4df087e40a11eb12b4ece0e569865814002d4da301342c2279af98acda0
```

The remaining `T600018.SH` quarantine is bounded to 2000-07-19 through 2006-10-20 and has an empty intersection with research coverage beginning in 2010. This removes that quarantine as a coverage-overlap blocker, but it does not satisfy the still-incomplete frozen official deterministic identity sample gate.

```text
security-master re-evaluation = a58cc58eb70c754f00fc9f3b06e3894794550b4eb89f739460a889412065022b
input rows = 5549
eligible input rows = 5547
normalized effective-dated facts = 5548
excluded non-target = 1
quarantined identities = 1
quarantine coverage overlap = 0
SECURITY MASTER APPROVAL = PENDING
```

### Current frozen decision

```text
TIER 3 INDEPENDENT SOURCE = BaoStock 0.9.3 / query_trade_dates
TIER 3 SOURCE INDEPENDENCE = PASS
CALENDAR TIER 3 SAMPLE MATCH = 128
CALENDAR TIER 3 SAMPLE MISMATCH = 0
CALENDAR TIER 3 SAMPLE UNRESOLVED = 128
CALENDAR TIER 3 SAMPLE PROVIDER_ERROR = 0
CROSS SOURCE POLICY V2 = DESIGNED_NOT_ADOPTED
TRADE CALENDAR APPROVAL = PENDING

302132 HISTORICAL IDENTITY = RESOLVED
SECURITY MASTER QUARANTINED IDENTITIES = 1
SECURITY MASTER APPROVAL = PENDING

DAILY BAR ENTRY UNLOCKED = NO
DAILY BAR ACQUISITION = NOT STARTED

PHASE 1B-1 = FAIL
READY FOR PHASE 1B-2 = NO
HISTORICAL PIT DATA = FAIL
READY FOR LABEL ENGINE = NO
```

### Verification record for this re-evaluation

```text
COMMAND: .\.venv\Scripts\python.exe scripts\acquire_baostock_calendar_audit.py
RESULT: independence=PASS; exact frozen inventory reused; total=256; match=128; mismatch=0; unresolved=128; provider_error=0

COMMAND: .\.venv\Scripts\python.exe scripts\review_phase_1b1_policy.py (executed twice)
RESULT: identical graph/re-evaluation IDs on both runs; input=5549; eligible_input=5547; normalized_facts=5548; excluded=1; quarantined=1; approval=PENDING; daily_bar unlocked=NO

COMMAND: .\.venv\Scripts\python.exe -m pytest tests\real_audits\test_tier3_calendar.py tests\real_audits\test_identity_lineage.py tests\real_audits\test_policy_adequacy.py tests\real_audits\test_blocker_evidence.py tests\real_audits\test_security_master_normalization.py tests\data\test_manifests.py -q
RESULT: 34 passed in 0.20s

COMMAND: .\.venv\Scripts\python.exe -m pytest -q
RESULT: 193 passed in 0.99s
```

## Historical approval-policy adequacy review — Outcome C

This is the earlier pre-Tier-3 re-evaluation retained for immutable audit history. Its two-quarantine snapshot is superseded by the later Tier 3 and identity-lineage re-evaluation above; all V1 artifacts and PENDING decisions remain immutable and reproducible.

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

## Current final acceptance result

The superseding result is the Tier 3 and identity-lineage re-evaluation recorded above: calendar and security master remain PENDING; V2 remains DESIGNED_NOT_ADOPTED; daily-bar entry remains locked; Phase 1B-1 remains FAIL.

Current verification: focused tests 34 passed in 0.20s; full suite 193 passed in 0.99s; standalone boundary checks passed; clean-room build/install/test/wheel/smoke passed with 193 passed in 1.24s; credential/sentinel findings 0; .env ignored and untracked; git diff --check exited 0.

## Upstream evidence-gap closure — final re-evaluation

This is the current superseding Phase 1B-1 result. Every earlier V1, BaoStock, pending approval, quarantine, and identity-lineage artifact remains immutable and reproducible.

### Second independent calendar source

```text
SECOND TIER 3 SOURCE = Shenzhen Stock Exchange official full-month calendar endpoint
SECOND SOURCE ID = d5aa4a77620899d1e22ca0506a98797fa9f886e6512bd676d8ef5b9f7c03b5cb
SECOND TIER 3 INDEPENDENCE = PASS
EXACT PRIOR UNRESOLVED SZSE SAMPLE IDS = 128 / 128
OLD BAOSTOCK EVIDENCE = 0d7de5ea50303f43d9c09ecb49fcc9a7d45077c398830af26c0e73f6305aa733 (PRESERVED)
COMPOSITE EVIDENCE = e5e42c14be97aa1bc8d4365f729dfa7d24bebf618141bfdf77f356c3072668d6

CALENDAR COMPOSITE SAMPLE:
TOTAL = 256
MATCH = 256
MISMATCH = 0
UNRESOLVED = 0
PROVIDER_ERROR = 0

CROSS SOURCE POLICY V2 = ADOPTED
V2 ADOPTION ARTIFACT = eaf31f1f1b96c2d2ec491b2f3149ad0d5bda0761defe9170c7e93937bd861c5c
TRADE CALENDAR APPROVAL = APPROVED_WITH_RULES
TRADE CALENDAR APPROVAL ID = 08933ef18a3532078ade97f6f5f574216e68f04225a95d7c7838bed5ad9b840d
```

The second source is a direct exchange-operated endpoint, not DataHub, not a DataHub wrapper, and not derived from the DataHub payload. Each requested month explicitly returned every calendar date and `jybz` open/closed state. No absence or weekday inference was used. The composite joins the immutable BaoStock SSE projection and the new SZSE observations by exact frozen `sample_id` and pins the original BaoStock evidence ID.

### Frozen security-master official sample

```text
SECURITY MASTER OFFICIAL SAMPLE ID = 63acd57d97c01cbdf66dd7a8315a6b515fc0bf3a43ec7052602658db32f0a015
TOTAL = 32
VERIFIED = 28
MISMATCH = 1
UNRESOLVED = 3

SECURITY MASTER DISCREPANCY ID = 7f198ffb8d6440e507873c3fad6f782992afa5a1cd4c678739eca1e9db2b2b56
MISMATCH = 600747.SH delisting_date
DATAHUB VALUE = 2019-12-12
SSE OFFICIAL STRUCTURED VALUE = 2019-12-13
DISPOSITION = FAIL_CLOSED

UNRESOLVED = 000535.SZ, 000606.SZ, 000760.SZ
UNRESOLVED FIELD = board
REASON = SZSE official terminated-company table does not supply board

SECURITY MASTER QUARANTINED IDENTITIES = 1
QUARANTINE COVERAGE OVERLAP = 0
QUARANTINE COVERAGE RULE = 9f79f73bc079f38451c02cc1b906fda3419e4e9fab57d32ee4a6620330ae5883
SECURITY MASTER APPROVAL = REJECTED
SECURITY MASTER APPROVAL ID = c0506bee3879f06028a6f24025993a87cc1be8825ff76f4f6041c1818a96e74b
```

The `302132.SZ` effective-dated graph remains unchanged. The remaining `T600018.SH` interval has zero overlap with the requested 2010+ coverage, but the coverage rule deterministically rejects every pre-2010 request and every request intersecting the quarantine interval. It cannot override the official-sample mismatch or unresolved fields.

### Combined upstream exit gate

```text
COMBINED UPSTREAM GATE = c8949f0a94b2a2bacd060ab6cacc43f5ce212fe98190d4f44b273646b89f369f
DAILY BAR ENTRY UNLOCKED = NO
DAILY BAR ACQUISITION = NOT STARTED

PHASE 1B-1 = FAIL
READY FOR PHASE 1B-2 = NO
HISTORICAL PIT DATA = FAIL
READY FOR LABEL ENGINE = NO
```

### Evidence acquisition and deterministic evaluation commands

```text
COMMAND: .\.venv\Scripts\python.exe scripts\acquire_szse_calendar_audit.py (executed twice after checkpoint/resume)
RESULT: identical source/composite/adoption IDs; exact_szse_unresolved=128; total=256; match=256; mismatch=0; unresolved=0; provider_error=0; V2=ADOPTED

COMMAND: .\.venv\Scripts\python.exe scripts\resolve_security_master_official_sample.py (executed twice)
RESULT: identical inventory/discrepancy IDs; total=32; verified=28; mismatch=1; unresolved=3; discrepancy disposition=FAIL_CLOSED

COMMAND: .\.venv\Scripts\python.exe scripts\evaluate_phase_1b1_upstream.py (executed twice)
RESULT: identical approval/gate IDs; trade_calendar=APPROVED_WITH_RULES; security_master=REJECTED; quarantine overlap=0; daily_bar unlocked=NO; acquisition=NOT_STARTED

COMMAND: .\.venv\Scripts\python.exe -m pytest tests\real_audits\test_composite_calendar.py tests\real_audits\test_security_master_governance.py tests\real_audits\test_tier3_calendar.py tests\real_audits\test_identity_lineage.py tests\real_audits\test_policy_adequacy.py tests\real_audits\test_blocker_evidence.py tests\real_audits\test_security_master_normalization.py tests\real_audits\test_dataset_validators.py tests\data\test_manifests.py tests\data\test_source_approval.py -q
RESULT: 60 passed in 0.26s

COMMAND: .\.venv\Scripts\python.exe -m pytest -q
RESULT: 206 passed in 1.02s
```

```text
COMMAND: .\.venv\Scripts\python.exe scripts\verify_standalone.py
RESULT: forbidden imports=0; forbidden active paths/dependencies=0; prohibited repository inventory=0; phase 1a architecture boundary violations=0

COMMAND: .\.venv\Scripts\python.exe scripts\clean_room_acceptance.py
RESULT: build=true; clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; wheel_install=true; wheel_smoke=true; zero_dependency_acceptance=true; clean-room test output="206 passed in 1.32s"

COMMAND: actual credential plus sentinel scan over runtime artifact areas; git check-ignore .env; git tracked-file check for .env
RESULT: credential/sentinel findings=0; .env ignored; .env tracked=NO

COMMAND: git diff --check
RESULT: exit 0; no whitespace errors
```

## Final superseding matrix (latest append)

The TLS revalidation and exception-governance result is authoritative over all preceding historical sections.

```text
SZSE OFFICIAL TLS REVALIDATION = PASS
CALENDAR COMPOSITE: TOTAL=256 MATCH=256 MISMATCH=0 UNRESOLVED=0 PROVIDER_ERROR=0
TRADE CALENDAR APPROVAL = APPROVED_WITH_RULES
SECURITY MASTER EXCEPTION POLICY = PASS
EXCEPTION BUDGET = PASS
SYSTEMATIC DEFECT AUDIT = PASS
SECURITY MASTER EXCEPTIONS = 4
SECURITY MASTER QUARANTINED = 1
SECURITY MASTER APPROVAL = APPROVED_WITH_RULES
DAILY BAR ENTRY UNLOCKED = YES
DAILY BAR ACQUISITION = NOT STARTED
PHASE 1B-1 = FAIL
READY FOR PHASE 1B-2 = NO
HISTORICAL PIT DATA = FAIL
READY FOR LABEL ENGINE = NO
```

```text
FOCUSED TESTS = 33 passed in 0.11s
FULL SUITE = 219 passed in 1.05s
STANDALONE VERIFIER = PASS
CLEAN-ROOM TESTS = 219 passed in 1.54s
BUILD / WHEEL INSTALL / WHEEL SMOKE = PASS
CREDENTIAL / SENTINEL FINDINGS = 0
.env = IGNORED AND UNTRACKED
GIT DIFF CHECK = PASS
```
