# Phase 2B Checkpoint 18 — Gate V2 progress (not acceptance)

`CHECKPOINT 18 = FAIL / OPEN`. `CHECKPOINT 19 PILOT = NOT AUTHORIZED / NOT RUN`.
This report records a bounded infrastructure increment, not a Gate V2 PASS.
The legacy Gate V1 module remains unchanged and fail-closed.

## Frozen source and private-corpus boundary

- Starting feature HEAD: `5fe232d3b7360d643c83fd88d8e9ddf59ceb9f56`.
- Private corpus manifest: `0489978b34834817ee0e33dbd46d4e90b86a14e9827f89ba5b93433797c2ddd6`.
- Private CAS: 44 objects; inventory hash `a559e02eb8726289bb19c80daa37f78c8041e58bf6884d6c92c382da91ab6536`.
- No private source payload, derived month partition, or gate evidence bytes are staged for the public branch. `data/` is ignored.
- Provider requests: 0. No pilot was executed.

## Source-derived gate work

The new evaluator reads exact content-addressed evidence and independently
rederives it from physical partitions and pinned Phase 1/2A authority. Missing
or mismatched evidence remains FAIL. The currently implemented paths are:

- Gate V2 contract ID: `6a0eb73c468c44b96cded8781503bbf1e8304fc6f94d81e544675f144eba609c`.
- Interim evaluator ID: `77eb5c4f897189c81322c39ff6bc487716052f773c1b72f6d6e49d858751540c` (not a final frozen evaluator version).

1. Contract pinning: Phase 2A acceptance, maturation remediation, dataset/producer/engine code identities, private CAS inventory and five approved authorities.
2. Historical coverage: exact source candidate census, materialized membership and scoped ledger.
3. State, return, excursion, and barrier semantics: separate field groups, each compared to the independent calculator across all physical rows.
4. Pending maturation: frozen real Slot 4 H0/H1/H3/H5 boundary, including withheld early barrier outcome.
5. NOT_LABEL_SAFE preservation: physical row/reason mapping, not merely aggregate counts.
6. Partition and five-domain lineage: exact physical readback, independent membership/generation and source reconstruction.
7. Manifest integrity: canonical bytes, exact active physical partition set, month/generation/lineage relationship, and predecessor supersession continuity. The formal evaluator currently accepts only the one independently censused month; additional months cannot be silently added.

The latest 2010-01 source-pinned evaluator run found **11/18 PASS** for the
physical 26,899-row partition. Its local ignored exact manifest ID is
`74c68c19e73d33491152cd5ffd429c5fd332f1331f8a97ece86e133f25bc2107`.
This is not final Checkpoint 18 acceptance. The remaining seven gates stay
FAIL: corporate action, suspension, delisting, identity, deterministic replay,
incremental idempotency, and clean-room standalone.

## TDD negatives already exercised

- Rehashed numeric values fail only the relevant return or excursion group.
- Rehashed barrier outcome fails the barrier group.
- Rehashed lineage swap fails lineage rather than being disguised as a numeric mismatch.
- `AVAILABLE` with no numeric value fails state semantics, even after all hashes are rebuilt.
- Unknown rehashed label state raises a fail-closed error instead of crashing the gate evaluator.
- A mixed unsafe row with one missing reason is rejected even if other unsafe values have valid reasons.
- Count-preserving NOT_LABEL_SAFE reason swaps change exact evidence identity.
- A valid but different active partition with a rehashed manifest fails the independent expected-set check.
- A missing supersession for a removed predecessor partition fails; noncanonical manifest bytes fail.
- Wrong or missing exact evidence IDs remain FAIL.

## Verification boundary

- Latest Gate V2 focused suite: `27 passed, 2 skipped in 525.88s`; skips are opt-in real-month tests.
- Latest opt-in real-month formal evaluator: `1 passed in 1168.66s`, asserting 11 precise PASS results and seven fail-closed missing-evidence results. This run includes physical manifest verification.
- Previous real-month evaluator revision: `1 passed in 1171.78s`; it checked 26,899 rows, but predates the later state/manifest refinements and is **not** final Gate V2 acceptance.
- Manifest/unsafe focused regression: `5 passed in 0.18s` and `3 passed in 0.21s` respectively.
- New state-combination and unknown-state regression tests individually passed after RED failures.
- `scripts/verify_standalone.py`: five checks PASS, zero violations.
- `python -m compileall` on changed evaluator modules: PASS.
- `git diff --cached --check`: PASS.

The complete mutation suite, full pytest, clean-room, build/wheel,
public-ref hygiene, candidate census, Task 12
preregistration and final immutable Checkpoint 18 acceptance are **not yet
complete**. Do not infer a Gate V2 PASS or open Checkpoint 19 from this report.
