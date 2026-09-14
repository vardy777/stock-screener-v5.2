# V5.2 Phase 1C Manual Refresh Acceptance

Status: `PASS`

Acceptance ran through the real production entrypoint after the frozen wall-clock
boundary on `2026-09-14` in `Asia/Shanghai`. The service selected the actual
trading session `2026-09-14`, completed every dataset in dependency order, and
published an immutable research snapshot only after all six readiness gates passed.

## Final operational result

```text
TARGET SESSION = 2026-09-14
Calendar = READY
Security Master = READY
Daily Bar = READY / CONTEMPORANEOUS_OBSERVED
Security Status = READY / CONTEMPORANEOUS_OBSERVED
Corporate Action = SCOPED_READY
Financial Disclosure = SCOPED_READY / OBSERVED_FACTS_ONLY / PANEL_COMPLETENESS_PARTIAL
DATA FRESHNESS = CURRENT
RESEARCH READY = true
REFRESH STATUS = SUCCESS
SNAPSHOT ID = 9c5d3f3caddd359a79d7829dcdf87c254a3786fec639fe858d4a05a88168b1ee
PREVIOUS SNAPSHOT = 7565b1f9ad648bcb665eb07d18cb0c9e6008c5fd3d27e4dc13a603e576a29f4a
```

The initial final run exposed and fail-closed on three runtime correctness
defects: superseding lineage lookup used only frozen baseline directories,
same-day publication incorrectly required a future calendar session, and the
financial publisher treated the first sorted evidence ID as endpoint-capability
evidence. Regression tests were written first. The repaired runtime resolves
immutable superseding artifacts before frozen baselines, permits same-day
contemporaneous facts without inventing a future session, and resolves the
financial capability artifact by exact schema, identity and content hash.

## Published lineage

```text
CALENDAR APPROVAL = 79bd31239826ae8f65f5361dfe59f8e29700e6d7dcfcef7a5e328431a186abd7
CALENDAR MANIFEST = 7ac79537a8c65bc5f132fefbeb24ef4794b16fc1329439c5d5ca8f69ebea3b5c

MASTER APPROVAL = 36e7b4804f1b7a0a8147f4e91717281b29708f71a0d28ccc39ae7df7d4660586
MASTER MANIFEST = cdb635fd60969a55e7ac7020ebdef2653d674b696c052384b5c12329f4d5de2b
MASTER SECURITY-SCOPED EXCLUSIONS = 302132.SZ, 688801.SH, T600018.SH

DAILY BAR FACT BUNDLE = 366dba32addcf23f8f18d35ffb714ed537c1aa010947e5210357f7636aee90da
DAILY BAR FACTS = 5204
DAILY BAR APPROVAL = f057dc89adaa60e94b4b0763fc2a7902b8b33f845d9ca4c7f06deb78a7379274
DAILY BAR MANIFEST = 2fa12e2cfdcb35db45266c86631822b015111e33c10c4aa484889c30d1365ddf
DAILY BAR SECURITY-SCOPED EXCLUSIONS = 12

STATUS FACT BUNDLE = 534cff76c6eb8db5a9ce439b5859e1389297bbe1705855eb66768c26fd479307
STATUS FACTS = 5216
STATUS ST = 200
STATUS FULL-DAY SUSPENDED = 12
STATUS TRADABLE = 5008
STATUS APPROVAL = 4ee86e82630fa4dc4469a3411df35187e7d840e4592e2421fecd22ed5568bba7
STATUS MANIFEST = 9d1c65a20c3db2669091feecdab936eececb99b16bd20c751adcec815007e1ca

CA APPROVAL = 3b270014413e8e9c0415b3f196523291f791e4a4306a244b6165767e4ec87f76
CA MANIFEST = cab24bc52982c14c96f0b13ff4ecdd6abbf273dbd74f75e1a3b104374680aaff

FINANCIAL APPROVAL = 4ae1d83b494146c399a236d05fc3e01314dfb2aa86f050d0aa4dbc5af561bf22
FINANCIAL MANIFEST = 8359223cce60065ef795e0a51f03e7f88b18cec4bb93c85bd4e03c94aab89d0f
```

The scoped domains retain explicit capability boundaries. Corporate Action
publishes only its frozen supported action types. Financial Disclosure retains
`OBSERVED_FACTS_ONLY`; unsupported market-wide completeness remains machine
visible and missing disclosures remain `UNKNOWN`, never zero.

## Deterministic replay

The immediate second production-entrypoint run returned:

```text
REFRESH STATUS = NO_OP
RESEARCH READY = true
SNAPSHOT ID = 9c5d3f3caddd359a79d7829dcdf87c254a3786fec639fe858d4a05a88168b1ee
Phase 1C files before/after = 150 / 150
Phase 1C changed files = 0
raw files before/after = 18 / 18
raw changed files = 0
```

Thus the same target neither redownloaded provider data nor created duplicate
receipts, facts, approvals, manifests, state artifacts or snapshots.

## Verification record

```text
COMMAND: .venv\Scripts\python.exe -m pytest tests/refresh -q
RESULT: PASS; 87 passed in 1.05s

COMMAND: .venv\Scripts\python.exe -m pytest -q
RESULT: PASS; 534 passed in 615.98s

COMMAND: .venv\Scripts\python.exe scripts\verify_standalone.py
RESULT: PASS; forbidden imports=0; forbidden paths/dependencies=0;
        prohibited repository inventory=0; architecture violations=0

COMMAND: .venv\Scripts\python.exe scripts\clean_room_acceptance.py
RESULT: PASS; build=true; clean-room dependencies/install/tests=true;
        wheel install/smoke=true; zero dependency=true; archive findings=0;
        486 passed, 48 skipped in 2.31s

COMMAND: actual local credential sentinel scan across tracked/candidate files
         and data/phase_1c, excluding ignored .env
RESULT: PASS; findings=0; one configured sentinel loaded; .env ignored and untracked

COMMAND: git diff --check
RESULT: PASS; exit 0 (line-ending warnings only)
```

The 48 clean-room skips are repository-local immutable-artifact integration
tests. The ignored `data/` directory is deliberately absent from source and
wheel clean rooms; pure contracts, failure boundaries, integrity and replay
tests still execute there.

## Exit decision

```text
PHASE 1C MANUAL REFRESH = PASS
REAL WALL-CLOCK ACCEPTANCE = PASS
DETERMINISTIC REPLAY = PASS
RESEARCH SNAPSHOT PUBLICATION = PASS
ZERO PROJECT DEPENDENCY = PASS
READY TO REQUEST PHASE 2 REVIEW = YES
PHASE 2 STARTED = NO
```

This acceptance does not authorize or start Phase 2.
