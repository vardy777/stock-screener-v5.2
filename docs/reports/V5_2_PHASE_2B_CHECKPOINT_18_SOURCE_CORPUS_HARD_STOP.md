# Checkpoint 18 Closure — source-corpus hard stop

Baseline: `0ab89fc9ab9062505a06df6ae1e2ab0b966d28e2` on
`phase2a-implementation`. This report does not change the prior Checkpoint 18
hard-stop report or the accepted V1 gate fuse.

## Blocking observation

The exact approved Daily Bar governance artifacts are present in this
worktree, but the fact corpus needed to turn an arbitrary historical month
into `HistoricalEvidenceWindowV1` is not present within its source boundary.

- The Phase 1B-2B corrected Daily Bar manifest
  `9f38b28b3b2a4f93a16fe80144a1b894fdbabc1afea0e9dbe58009d3bce051e4`
  pins 2,481,310 facts and 5,260 content hashes. The current worktree has
  no `data/phase_1b2b/facts` directory; the first pinned shard
  `0003d9ffc66d6040def6125290813b88b9cae11e9f56987e202003052fdbe7d7`
  is absent here.
- The current Phase 1C historical-baseline manifest
  `cb79850fac1c28e7b1e8bd9991d65c26f61add832b2f5ed67c40c586a13fd8c6`
  records 14,010,422 rows but its `fact_content_hashes` identify a single
  aggregate panel, `a618046c952a9bb863a1ec93fcc4d79c24cfca69542fdbb1c6581c1fde75a31d`.
  That panel is a 396,350-byte summary, not per-session OHLC facts.
- `data/phase_1b1` and `data/phase_1b1_2026_extension` in this worktree are
  junctions to the separate main checkout, not self-contained artifact
  directories. The repository's `AGENTS.md` forbids reading a sibling checkout
  as a runtime fact source. The visible Phase 1B-1 shards also contain the old
  `daily-bar-d-close-v1` availability policy, so their mere presence could not
  establish the current approved `NEXT_SESSION_SAFE` lineage.
- The checked-in Phase 2A targeted bar backfill is a small specific supplement,
  not a replacement for the missing general historical corpus.

The exact-pinned five-domain production reader and source-pinned real-month
integration cannot be honestly completed from this worktree. Using the
junction target, treating the aggregate panel as row facts, or treating raw
payload presence as approved truth would violate the frozen boundary.

## Verification performed

Read-only checks: `git status --short --branch`, `git rev-parse HEAD`,
`Test-Path data/phase_1b2b/facts`, exact manifest `fact_content_hashes`
inspection, `git ls-files` of fact paths, junction-target inspection, and
aggregate panel schema/size inspection. No provider request or data-network
acquisition was made. No Phase 1, Phase 2A, or Phase 2B production code was
changed in this attempt. Full tests and formal 18-gate acceptance were not run
because implementation has not begun.

## Required resolution

Provide an in-worktree, immutable, checksum-verifiable copy of the approved
historical Daily Bar fact corpus and its exact membership mapping, or explicitly
authorize a one-time import from the named V5.2 main checkout into this
isolated worktree. The import must be verified against the frozen manifests
and must not become a runtime dependency on the other checkout. After that,
resume the frozen order: five-domain producer, real month, formal Gate V2,
mutations, census, preregistration, Checkpoint 18 acceptance. Pilot remains
blocked.

Status: `CHECKPOINT 18 = FAIL / OPEN`; `CHECKPOINT 19 = NOT STARTED`.
