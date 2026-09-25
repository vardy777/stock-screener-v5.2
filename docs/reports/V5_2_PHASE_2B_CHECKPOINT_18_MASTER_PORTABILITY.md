# Checkpoint 18 — historical Security Master portability (interim)

This is a **component record, not Checkpoint 18 acceptance**. The five-domain
production producer, real month, independent Gate Evidence V2, census, and
Task 12 preregistration remain open. No pilot was executed.

## Frozen parents and physical import

- Parent complete Security Master manifest:
  `025982975b942c416945d9580f2a8272d667f7676e9f6fa213429e3da2ee382b`.
- Parent input / approved membership / non-target exclusion: `5898 / 5551 / 347`.
- Old historical bundle `968ae9660ae02f4a1e16a8eb6510a62368e44defc7f99f7ed56714364c722386`
  remains byte-identical. Its mixed provenance field is corrected by a **new
  typed bridge**, not an in-place edit.
- Physical, byte-hashed source import: 46 files, corpus inventory
  `a534f3969943efa206d0085e5fcbf810eb70c54970610cf2e3b53c46c81ac66e`.
  It contains 16 exact Master raw pages, 16 receipts, parent governance,
  two immutable revocations, the frozen 6275 graph and approval, and the
  historical-universe supplement. No provider request was made.
- `6275f4df087e40a11eb12b4ece0e569865814002d4da301342c2279af98acda0`
  remains the effective identity graph with graph-scoped approval
  `a14be1c8443902fd3c28fd9ec43243710d124ba5c498cf760c9fe4396f11189f`.
  `d67d886299be85bb5585c9103140ef327fe13b78161903f7e5120646a8ee9e8f`
  remains a `HistoricalUniverseSupplementV1`, never a graph.
- The supplement's `600747.SH` is outside the 5,551 parent membership and
  has no independent raw official proof in this import. It is retained as
  typed provenance and **scoped quarantined** for research; its historical
  dates were not rewritten.

## Derived representation

- Typing bridge: `23c288b2c3ebe256de1d138c5799328f842fa535f3302af1282e3f1ceb2fca14`.
- Authority: `33f28a549e94be8317dce5216414eb7b4c3c403fda4e2a160fc7d26e431831c5`.
- Derived approval: `c515bd582600fed01a64c062901ede713dafadb931e5fa7de15f053d52c4bfc1`.
- Manifest: `d570228256b4e693e8ccce7ed5c18196065bcec9ef3dae749048052f3a28304c`.
- Coverage ledger: `ae78946d78fcf107de18d78abe7a8f92df4c042a7cdc7223143b39a20b157945`.
- Two-run replay: `e517e9815009509590ac3bfc3b7f9e2535e432b468090fb29d23840f7fb9f99a`.
- Membership `5551 = 5549 resolved + 2 scoped quarantines`.
  The quarantines are `689009.SH` and `T600018.SH`; neither has a fabricated
  effective interval. `600747.SH` is a separate supplement-scope quarantine,
  not a third subtraction from parent membership.
- The formal reader requires exact governance IDs, rechecks the physical
  source inventory and revocations, and compares all 5,549 interval facts
  with a fresh deterministic derivation. A missing/tampered parent or replay
  fails closed.

## Frozen Phase 1B session comparison

| Session | Old universe | Portable resolved | Explicit difference |
|---|---:|---:|---|
| 2012-06-29 | 2421 | 2421 | none |
| 2018-06-29 | 3529 | 3529 | none |
| 2025-06-30 | 5152 | 5151 | `689009.SH` quarantined |
| 2026-06-30 | 5205 | 5204 | `689009.SH` quarantined |

The later two are **not** reported as exact equality. The parent member is
retained and its affected research sessions are excluded until provenance is
resolved. This is a finite identity-scoped gap, not a change to the historical
universe census.

## Verification scope

Focused tests cover source-byte tamper, missing raw page, revocation import,
typed provenance, interval derivation, exact reader, replay tamper, and the
four regression sessions. Full-suite/clean-room and Checkpoint 18 end-to-end
acceptance are separately required and are not claimed by this record.

`DATAHUB REQUESTS = 0`; `TUSHARE REQUESTS = 0`; `MARKET-DATA PROVIDER REQUESTS = 0`.
