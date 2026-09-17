# V5.2 Phase 2A Checkpoint 6 — Evidence Assembler and 5-slot Pilot

Checkpoint 6 implements the repository-facing, offline deterministic evidence assembler and stops after the authorized five-slot pilot. It does not run the full 22-slot independent calculation, does not close the 16 Phase 2A gates, and does not start Phase 2B.

## Result

```text
EVIDENCE ASSEMBLER IMPLEMENTED = YES
ASSEMBLER VERSION = phase2a-evidence-assembler-v1
EVIDENCE GAP AUDIT ID = 4249d9908e714ab2339f6873079b39c98fbfff75fa83f13261971da62471be0b
ASSEMBLER_LOOKUP_DEFECT = 0
REAL_PHASE1_EVIDENCE_ABSENT = 0
OTHER GAP = 0
22 BUNDLES CONSTRUCTIBLE = 22
22 EVIDENCE_UNAVAILABLE = 0

5-SLOT PILOT INVENTORY = frozen inventory 81bd6df1955b9e18831779bd7274947f7da6dca50d5554f94cf7d85da31ac1c9
PILOT SLOT IDS = 1, 6, 8, 11, 18
PILOT ID = 79ac7f9f9e34ca6b823e85df6bf2a54faa75c24f66c552af5af76f421ae9896c
PILOT BUNDLES CREATED = 5
PILOT ENGINE RESULTS = 5
PILOT INDEPENDENT RESULTS = 5
PILOT MATCH = 5
PILOT MISMATCH = 0
PILOT LABEL_AVAILABLE = 3 slots
PILOT LABEL_PENDING = 1 slot
PILOT NOT_LABEL_SAFE = 1 slot
PROVIDER REQUESTS = 0

PHASE 1 STATUS LINEAGE = PASS
PHASE 1 DAILY BAR GLOBAL LINEAGE = PASS
PHASE 2A = PENDING
16 GATES = NOT RUN
READY FOR PHASE 2B = NO
PHASE 2B STARTED = NO
```

## Evidence plumbing

The assembler consumes exactly five domain roles in frozen order:

1. `trade_calendar`
2. `security_master`
3. `daily_bar`
4. `daily_security_status`
5. `corporate_action`

Historical bundles leave snapshot IDs empty and pin the approved immutable Phase 1 lineage. Financial data is neither loaded nor represented. Calendar order is checked without sorting or deduplication. Exact current Daily Bar composite identity, targeted backfill governance, Status supplement manifest, and scoped Corporate Action approval/manifest are pinned. Revoked pinned approvals, malformed calendars, tampered facts, missing unexplained bars, invalid identities, and role/domain defects fail closed.

The small `LabelInputBundleV1.reference_price` typing correction permits the already-frozen `ANCHOR_BAR_MISSING` state to be represented without inventing a price. This completes an existing frozen state transition; it does not change price or label semantics.

## Required boundary cases

- `300131.SZ / 2014-09-11`: real full-day suspension evidence is assembled across all five domains; no anchor price is synthesized. Production and independent calculation both return `NOT_LABEL_SAFE / ANCHOR_BAR_MISSING` for all seven labels.
- `002118.SZ / 2023-08-03`: bundle pins the final-trading/suspension lineage and `delisting_session=2023-08-04`. The engine returns `NOT_LABEL_SAFE / DELISTING_IN_HORIZON`; it does not produce -100%, zero, or perpetual carry.
- Pilot slot 6 (`000333.SZ / 2021-06-01`): consumes a real `CASH_DIVIDEND` fact and matches the independent economic-wealth calculation.
- Pilot slot 8: a proven full-day suspended exchange-open session carries economic wealth without creating a synthetic bar or intraday path.
- Pilot slot 18: future horizons are not complete, so all labels remain `LABEL_PENDING` without requiring unavailable future observations.

## Verification

```text
COMMAND: python -m pytest tests/labels -q
RESULT: 100 passed in 36.46s

COMMAND: python -m pytest tests/labels/test_status_closure.py tests/refresh/test_daily_bar_composite_lineage.py tests/governance/test_standalone.py tests/governance/test_clean_room_acceptance.py -q
RESULT: 35 passed in 49.23s

COMMAND: python -m pytest -q
RESULT: 665 passed in 123.61s

COMMAND: python scripts/verify_standalone.py
RESULT: forbidden imports=0; forbidden active paths/dependencies=0; prohibited repository inventory=0; Phase 1A architecture violations=0

COMMAND: python scripts/clean_room_acceptance.py
RESULT: build=true; clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; wheel_install=true; wheel_smoke=true; old_pythonpath_removed=true; zero_dependency_acceptance=true; 580 passed, 85 skipped in 2.71s

COMMAND: python -m pytest tests/providers/test_credentials.py tests/data/test_deterministic_replay.py -q
RESULT: 9 passed in 0.05s

COMMAND: run Phase 2A pilot twice and compare complete console result
RESULT: byte-identical; PILOT_ID identical; DETERMINISTIC_REPLAY=true

COMMAND: git diff --check
RESULT: PASS
```

The first clean-room attempt failed because Windows clean-room Python had no external IANA `tzdata`. The assembler was corrected to use the project-wide fixed UTC+08:00 research timezone without adding a dependency. The recorded clean-room result above is the successful rerun.

## Stop boundary

Checkpoint 6 stops after the five-slot pilot. Full 22-slot independent verification, final 16-gate closure, Phase 2B, feature work, ranking, ML, and backtesting remain prohibited pending independent review.
