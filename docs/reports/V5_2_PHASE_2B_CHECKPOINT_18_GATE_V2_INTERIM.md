# Phase 2B Checkpoint 18 — Gate Evidence V2 Interim

`CHECKPOINT 18 = FAIL / OPEN`. This is an independent, source-pinned row
comparison ledger, **not** the final 18-gate evaluator or acceptance.

## Trust boundary

The formal `derive_partition_comparisons_exact(...)` entrypoint reloads the
exact approved five-domain sources and the physical content-addressed
partition. It reads every row from canonical JSONL, verifies the physical
partition SHA-256, row membership/order, all seven nested value identities,
and each row identity. It then rebuilds each bundle from Phase 1 sources and
uses the frozen `independent_reference` calculator, which does not call the
production label engine or calculation helpers. The comparator checks states,
reasons, numeric values, barrier outcome/decisive session, and exact lineage.
Caller-supplied equal hashes are not an acceptance input. The old 18-gate V1
evaluator remains permanently fail-closed.

## Actual 2010-01 evidence

The real month partition was replayed from exact Phase 1 sources into the
local ignored `data/phase_2b_checkpoint18_real_month` directory. This was
not a provider acquisition and did not execute a Checkpoint 19 pilot. Its
partition, coverage, scoped ledger, and integration IDs exactly equalled the
earlier twice-computed results in
`V5_2_PHASE_2B_CHECKPOINT_18_REAL_MONTH.md`.

The formal row-comparison run used partition ID:

```text
3c194baf309486c16dd8f7f9e1916f4a1a4af49c9b108bcc06ce693eee615ba9
```

Result:

```text
CHECKED ROWS = 26899
INDEPENDENT MISMATCH ROWS = 0
ROW COMPARISON LEDGER ID =
c3b16aa0f7618e702e5bcab8b977b1919a75f72c5d65795576a1eeb74dd0bca8
EXACT PHYSICAL READBACK = PASS
```

Before the formal full run, a 100-row diagnostic (explicitly not acceptance)
found 0 mismatches. The full result above did not use the diagnostic subset
as a threshold or substitute. The comparison ledger is content-addressed in
the ignored local `gate_evidence` directory. It is not claimed to exist on
GitHub, because the approved source artifacts used for replay are not yet
authorized for redistribution to the public repository.

## TDD and negative controls

- Exact physical row read test began RED due to missing API, then
  `tests/labels/test_partition_store.py` was GREEN (`5 passed`).
- Gate V2 comparison module began RED due to missing API; focused row/source
  and physical-read tests finished `11 passed in 106.35s`.
- A deliberately forged return value was used to rebuild internally valid
  LabelValue, LabelResult, LabelRow, Partition and metadata identities.
  Source-pinned independent comparison still reported a mismatch.
- A rehashed barrier outcome mutation was independently rejected.
- Exact comparison-ledger read rejects tampering; create-or-identical rejects
  a collision. No caller `expected_hash == observed_hash` can make a gate PASS.
- `scripts/verify_standalone.py`: five checks PASS, zero violations.
- `git diff --check`: no whitespace errors.
- Provider requests: **0**.

The formal 18-gate evaluator, remaining semantic mutation classes, exact
candidate census, Task 12 preregistration, post-change full/clean-room
verification, and license/redistribution decision remain outstanding.
Therefore this report does not set `READY FOR CHECKPOINT 19 = YES`.
