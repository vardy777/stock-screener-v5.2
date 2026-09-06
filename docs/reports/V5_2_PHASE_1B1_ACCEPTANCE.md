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
