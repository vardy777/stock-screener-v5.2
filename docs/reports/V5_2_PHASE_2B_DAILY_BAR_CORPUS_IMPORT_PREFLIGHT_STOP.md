# V5.2 Daily Bar historical corpus import — pre-copy STOP

## Decision

`SOURCE CORPUS IMPORT = STOPPED / NO COPY PERFORMED`.

The one-time import authorization requires a complete, immutable row-level
inventory derived from the currently frozen Daily Bar composite before any
source bytes are copied. That inventory cannot be derived from the existing
approved **fact** artifacts. This is the exact hard-stop condition in the
authorization; it is not an authorization to reconstruct facts from raw data.

The source checkout was inspected read-only as the named one-time import
source. Its operational Git HEAD was
`b0181feeb1a854a8dccbb459fa98e1948cf47474` on `main`. This Git commit is
not used as a market-data identity. The isolated worktree baseline was
`2d5e4b92acfbfcb417c0096b2024ffe6c9e9a9b0`.

## Frozen lineage and source-corpus findings

| Component | Frozen identity and coverage | Row-level fact inventory found |
|---|---|---|
| Current Phase 1C `HISTORICAL_BASELINE` | composite `0053aa0c80a5561dd8557156555bfdb47c841901477a737a0a0a2f5807918744`; manifest `cb79850fac1c28e7b1e8bd9991d65c26f61add832b2f5ed67c40c586a13fd8c6`; 14,010,422 rows | `member_artifact_ids` and manifest `fact_content_hashes` contain only aggregate panel `a618046c952a9bb863a1ec93fcc4d79c24cfca69542fdbb1c6581c1fde75a31d`, not row-level OHLC shards. |
| Phase 1B-1 fact sets | two manifests, each 2,481,310 rows / 5,260 shards, 2024-01-01 through 2025-12-31 | 10,520 physical shards in two old `daily-bar-d-close-v1` sets; these are overlapping versions, not 4,962,620 distinct historical observations. |
| Phase 1B-2B availability-remediated facts | manifest `9f38b28b3b2a4f93a16fe80144a1b894fdbabc1afea0e9dbe58009d3bce051e4`; 2,481,310 rows / 5,260 shards, 2024-01-01 through 2025-12-31 | 5,260 physical shards; this does not account for the 14,010,422-row baseline. |
| 2026 historical extension | 336 immutable raw Daily Bar payload files | No `facts/daily_bar` directory for this component. |
| Phase 2A targeted supplement | one small approved bar-facts bundle | Not a general 2010–2026 corpus. |

The historical panel finalization code reads 5,548 Phase 1B-1 and 336
2026-extension raw payloads, counts their rows, and publishes the aggregate
panel plus a `NEXT_SESSION_SAFE` availability overlay. It does **not** publish
a 14,010,422-row content-addressed normalized Daily Bar fact-shard inventory.
The baseline manifest pins 5,884 raw payload hashes, three normalization/
overlay hashes, and only the one aggregate panel as `fact_content_hashes`.
Raw payloads are source evidence, but their presence alone is not approved
per-row research truth. Producing a new normalized row-level corpus from them
would be materialization, not the authorized physical import of existing
approved fact shards.

Accordingly, no `DailyBarHistoricalCorpusImportPlanV1` with complete expected
row-level membership can be truthfully signed. The 5,260 corrected shards must
not be treated as the entire historical baseline, and the aggregate panel
must not be read as OHLC rows.

## Import-result fields

```text
SOURCE CORPUS IMPORT = STOPPED
SOURCE CHECKOUT ROLE = READ-ONLY PREFLIGHT; NOT A RUNTIME SOURCE
REQUIRED CORPUS COMPONENTS = HISTORICAL_BASELINE ROW-LEVEL FACTS NOT FULLY IDENTIFIED
REQUIRED ARTIFACT COUNT = NOT DERIVABLE FROM APPROVED FACT INVENTORY
EXPECTED INVENTORY HASH = NOT CREATED
SOURCE INVENTORY HASH = NOT CREATED
DESTINATION INVENTORY HASH = NOT CREATED
EXPECTED LOGICAL FACT/ROW COVERAGE = 14,010,422 HISTORICAL BASELINE ROWS
PHASE1B-2B FACT COUNT = 2,481,310
HISTORICAL BASELINE ROW COUNT = 14,010,422
MISSING ARTIFACTS = NOT COMPUTABLE WITHOUT COMPLETE EXPECTED INVENTORY
EXTRA ARTIFACTS = NOT COMPUTABLE WITHOUT COMPLETE EXPECTED INVENTORY
DUPLICATE ARTIFACTS = NOT COMPUTABLE WITHOUT COMPLETE EXPECTED INVENTORY
HASH MISMATCHES = NOT TESTED; NO COPY ATTEMPTED
OLD D@15:00 LINEAGE USED AS RESEARCH TRUTH = NO
NEXT_SESSION_SAFE LINEAGE PRESERVED = YES / UNCHANGED
DESTINATION IS PHYSICAL COPY = NO / NO COPY ATTEMPTED
JUNCTIONS USED FOR IMPORT = NO
SYMLINKS USED FOR IMPORT = NO
HARDLINKS USED FOR IMPORT = NO
MAIN CHECKOUT RUNTIME DEPENDENCY = NOT PROVEN; PRODUCTION READER NOT IMPLEMENTED
IMPORT LEDGER ID = NONE
PROVIDER REQUESTS = 0
NETWORK ACQUISITION = 0
CHECKPOINT 18 = FAIL / OPEN
CHECKPOINT 19 PILOT = NOT STARTED
```

No source or destination artifact was created, modified, deleted, linked, or
copied. Existing worktree junctions remain unchanged but were not traversed
as a research runtime path. No full test suite was run because this was a
read-only pre-copy inventory audit, not an implementation.

## Required decision before resumption

The copy-only authorization is insufficient for the missing 2010–2026
row-level normalized facts. A separate reviewed remediation would have to
define how the frozen approved raw payloads, normalizer, and availability
overlay yield immutable per-row facts and exact membership without changing
Phase 1 semantics or treating acquisition time/D@15:00 as historical
availability. Until that artifact exists and is independently accepted,
there is no complete import inventory and Checkpoint 18 cannot proceed.
