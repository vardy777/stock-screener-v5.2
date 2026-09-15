# V5.2 Phase 2A Targeted Daily Bar Backfill Closure

Status: `PENDING` (fail closed)

## Frozen scope and acquisition

- Starting HEAD: `f04ce2d36aa12cdfa1de4b86d1df8498385200da`
- Frozen Phase 2A inventory: `81bd6df1955b9e18831779bd7274947f7da6dca50d5554f94cf7d85da31ac1c9`
- Evidence gap audit: `796990a6be6dc53133124cf33c0cdcb8def2aafff9d8041afab6a3cea9a3dd4e`
- Backfill inventory: `70c7d78674a9584704f3e8f4306584cc479d61e529d482f5abfe314cfd7f3494`
- Acquisition artifact: `d224200921b90e4e748e18bd801647a3e3b56d37b3c14638a2114ffbdcd59c7a`
- Frozen slots: 10
- Unique securities: 10
- Unique required bar sessions: 57
- Provider requests: 10
- Raw rows returned: 43

The inventory was frozen before acquisition. No sample, horizon, or label semantic was changed after observing the provider response.

## Returned coverage

| slot | identity | returned required rows | still absent required sessions |
|---:|---|---:|---|
| 6 | 000333.SZ | 6 | none |
| 7 | 600276.SH | 6 | none |
| 8 | 600658.SH | 5 | none (2010-05-19 was excluded before acquisition by an exact approved suspension fact) |
| 9 | 002166.SZ | 3 | 2019-04-12, 2019-04-16 |
| 10 | 600155.SH | 0 | 2015-11-16, 2015-11-18, 2015-11-19, 2015-11-20, 2015-11-23 |
| 11 | 300131.SZ | 5 | 2014-09-11 |
| 12 | 688053.SH | 6 | none |
| 13 | 688247.SH | 6 | none |
| 14 | 002118.SZ | 0 | 2023-08-03, 2023-08-04, 2023-08-07, 2023-08-08, 2023-08-09, 2023-08-10 |
| 17 | 000651.SZ | 6 | none |

No absent row was synthesized. Existing sparse status facts are not treated as proof for unobserved sessions unless their exact effective semantics establish the absence.

## Phase 1 correctness blocker

Formal publication cannot proceed because the final approved Daily Bar lineage is internally incompatible at the availability boundary:

```text
Daily Bar approval ID =
fc26bf140708a72957f687757665508ee439cb079b9bdaff86686109b7683ea5

approval.source_version_identity =
de95192812d99f1c7f4e4363b8160a1b8728d76f503aa7edbf5c851a719527bb

pinned availability evidence ID =
6877256040eb6abbea3e6c4434485aaa212f23eba7f675f9d088ce7e05850bcb

availability_evidence.source_version_identity =
ea88e3bcf5ecbae599567d1f22756f1333b9ff134c2face0895e60fcadc05986
```

`DailyBarAvailabilityPolicyV1` requires exact source-version equality and therefore correctly fails closed. Reusing the approval version, using the evidence version, or assigning `NEXT_SESSION_SAFE` directly would bypass a frozen integrity check. This is a real Phase 1 Daily Bar approval/evidence wiring defect, so this run stops before fact publication as required.

Consequences:

- approved backfill facts: 0
- quarantine: 43 raw rows retained outside research-visible facts pending lineage repair
- supplemental DatasetManifest: not created
- Evidence Assembler: not implemented
- five-slot pilot: not run
- Phase 2A: `PENDING`
- ready for Phase 2B: `NO`

## Verification completed before the mandatory stop

```text
C:\Users\lisha\stock-screener-v5.2\.venv\Scripts\python.exe -m pytest tests/labels/test_bar_backfill_inventory.py tests/labels/test_bar_backfill_publication.py -q
9 passed in 0.11s
```

The focused tests cover deterministic frozen scope, request construction, OHLC/session/identity rejection, duplicate rejection, x100 volume, x1000 amount, immutable payload lineage, and next-session-safe fact construction. Full-suite, clean-room, build, and Phase 2A gates were intentionally not run because the frozen instruction requires an immediate stop when a Phase 1 Daily Bar correctness defect is exposed.
