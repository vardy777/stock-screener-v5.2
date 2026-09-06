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
