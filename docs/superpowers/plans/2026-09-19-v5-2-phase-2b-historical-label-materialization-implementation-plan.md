# Phase 2B Historical Label Materialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build deterministic, immutable, partitioned Phase 2B outcome-label storage and a gated small-window pilot without authorizing a broad historical run.

**Architecture:** Reuse the frozen Phase 2A assembler and reference engine for every calculation. Store its exact `LabelResultV1` in content-addressed anchor-month partition generations; publish only immutable manifests that pin exact partitions and lineage. New anchors and frozen per-value maturity endpoints select the minimal regeneration workset.

**Tech Stack:** Python 3.11 standard library, frozen `v5_2` contracts, pytest, canonical JSON/JSONL, existing standalone and clean-room scripts.

**Spec:**
- `docs/superpowers/specs/2026-09-19-v5-2-phase-2b-historical-label-materialization-design.md`
- `docs/reports/V5_2_PHASE_2B_MATURATION_CONTRACT_AUDIT.md`

## Frozen authorities

```text
Phase 2A final acceptance = 75df8940cfa5f31757fc9b105be172e60581ead32ff0494fb4c84a2baac43cf7
Phase 2B frozen design HEAD = 6f9e998699b43277d6fa2400797d0c96240fa9e0
Historical provenance = exact approved Phase 1 five-domain lineage; no synthetic snapshot
Contemporaneous provenance = real ResearchDataSnapshotV1 plus exact lineage
Provider/network requests = 0 for implementation and pilot
```

Do not modify Phase 1 lineage semantics, `LabelContractV1`, `LabelState`,
`LabelValueV1`, `LabelResultV1`, `AnchorKnowledgeBoundary`,
`LabelReferencePrice`, `ReferenceLabelEngine`, or the Phase 2A assembler.
No new row-level state exists. A row merely envelopes the exact seven frozen
label values. No research consumer may use a latest pointer or directory scan
as truth. A collision whose existing bytes differ fails closed.

## Review focus

- A row with H1 available and H3/H5 pending must preserve its seven field states; Task 1 owns this regression.
- A barrier decisive at H1 must remain pending until H5; Task 8 owns this regression.
- A calendar or lineage fault must prevent partition and manifest publication; Tasks 4 and 10 own these regressions.
- A partition replacement must preserve old bytes and replace only through manifest supersession; Tasks 3 and 9 own this regression.
- An unsupported CA, delisting, identity, or missing-bar path must remain exact `NOT_LABEL_SAFE`, not an empty/zero label; Tasks 6 and 10 own these regressions.

## Target file map

```text
src/v5_2/labels/dataset_contracts.py       immutable rows, partitions, manifests, coverage ledgers
src/v5_2/labels/partition_store.py         canonical JSONL/JSON create-or-identical persistence
src/v5_2/labels/anchor_enumerator.py       deterministic approved historical anchor enumeration
src/v5_2/labels/materializer.py            five-domain assembly -> engine -> LabelRowV1 streaming
src/v5_2/labels/incremental.py             new/matured/revocation workset selection and generations
src/v5_2/labels/phase2b_gates.py           eighteen typed executable gate predicates
scripts/run_phase2b_small_window_pilot.py  preregistered pilot runner; not a broad-run runner
tests/labels/test_dataset_contracts.py
tests/labels/test_partition_store.py
tests/labels/test_anchor_enumerator.py
tests/labels/test_label_materializer.py
tests/labels/test_incremental_maturation.py
tests/labels/test_phase2b_gates.py
tests/labels/test_phase2b_firewall.py
tests/labels/test_phase2b_pilot.py
```

Artifacts live under ignored data paths, planned as:

```text
data/phase_2b/labels/historical/YYYY-MM/<partition-id>.jsonl
data/phase_2b/partitions/<partition-id>.json
data/phase_2b/manifests/<manifest-id>.json
data/phase_2b/ledgers/<ledger-id>.json
```

The path is an implementation convention, not a research-truth lookup API.

---

### Task 1: Immutable dataset contracts and canonical identities

**Files:** Create `src/v5_2/labels/dataset_contracts.py`; create `tests/labels/test_dataset_contracts.py`.

**Interfaces:** `LabelRowV1.create(result: LabelResultV1, bundle: LabelInputBundleV1, materialization_version: str) -> LabelRowV1`; `LabelPartitionV1.create(...)`; `LabelDatasetManifestV1.create(...)`; `CoverageAccountingV1.create(...)`.

- [ ] Write failing tests that construct a real mixed-state result and assert the row stores all seven `LabelValueV1` hashes in frozen `CORE_LABELS` order, has no `row_state`, and rejects an invalid nested result hash.
- [ ] Run `python -m pytest tests/labels/test_dataset_contracts.py -q`; expect import failure for `dataset_contracts`.
- [ ] Implement frozen dataclasses using existing `content_hash`; serialize Decimal fixed-point, `null`, dates, aware timestamps, lineage order, and snapshot IDs exactly as the design specifies.
- [ ] Add tests: same nested semantics yield the same row ID; one value/lineage/order change yields a different ID or validation error; duplicate row key is rejected by `LabelPartitionV1`.
- [ ] Run the focused test file; expect PASS. Commit `feat: add immutable Phase 2B dataset contracts`.

### Task 2: Canonical partition persistence

**Files:** Create `src/v5_2/labels/partition_store.py`; create `tests/labels/test_partition_store.py`.

**Interfaces:** `write_partition(root: Path, partition: LabelPartitionV1, rows: Iterable[LabelRowV1]) -> Path`; `write_manifest(root: Path, manifest: LabelDatasetManifestV1) -> Path`; `read_partition_exact(path: Path, expected_id: str) -> LabelPartitionV1`.

- [ ] Write failing tests for ordered `(anchor_session, canonical_security_identity)` JSONL bytes, two identical writes, collision with changed bytes, and tampered partition/manifest bytes.
- [ ] Run `python -m pytest tests/labels/test_partition_store.py -q`; expect import failure.
- [ ] Implement streaming canonical JSONL followed by a content-addressed metadata artifact. Existing destination is accepted only when bytes exactly match; otherwise raise `ImmutableArtifactCollision`.
- [ ] Add tests proving write order is not repaired by sorting at read time and an exact expected ID is required.
- [ ] Run focused tests; expect PASS. Commit `feat: add immutable Phase 2B partition store`.

### Task 3: Manifest generations and supersession

**Files:** Modify `dataset_contracts.py`; modify `partition_store.py`; extend `test_dataset_contracts.py` and `test_partition_store.py`.

**Interfaces:** `LabelDatasetManifestV1.create(previous_manifest_id, active_partition_ids, partition_supersession, phase2a_acceptance_id, lineage_ids, coverage) -> LabelDatasetManifestV1`.

- [ ] Write failing tests where an old manifest/partition is byte-identical after H1 maturation, a new manifest pins the replacement partition, and a manifest cannot reference an unverified/duplicate/superseded active partition.
- [ ] Run the two focused test files; expect missing supersession validation.
- [ ] Implement explicit `previous_manifest_id` and old->new partition map validation; never resolve a latest manifest internally.
- [ ] Add a negative test for a count-preserving swap of one partition ID with unrelated bytes; it must fail lineage integrity.
- [ ] Run focused tests; expect PASS. Commit `feat: add Phase 2B manifest supersession`.

### Task 4: Deterministic historical anchor enumeration

**Files:** Create `src/v5_2/labels/anchor_enumerator.py`; create `tests/labels/test_anchor_enumerator.py`.

**Interfaces:** `enumerate_historical_anchors(lineage: HistoricalAnchorLineageV1, start: date, end: date) -> Iterator[AnchorDispositionV1]`; dispositions are `EFFECTIVE`, `ELIGIBLE`, or `EXCLUDED_BEFORE_LABEL` with exact reason.

- [ ] Write failing tests for listing day, fifth IPO-seasoning session, first eligible session, delisting boundary, suspended session, identity transition, and malformed calendar/approval revocation.
- [ ] Run `python -m pytest tests/labels/test_anchor_enumerator.py -q`; expect import failure.
- [ ] Implement a streaming resolver that consumes only exact approved calendar/master/status/eligibility lineages; it must not manufacture label candidates for excluded anchors.
- [ ] Add deterministic ordering and tampered lineage tests.
- [ ] Run focused tests; expect PASS. Commit `feat: add deterministic Phase 2B anchor enumeration`.

### Task 5: Historical five-domain bundle materializer

**Files:** Create `src/v5_2/labels/materializer.py`; create `tests/labels/test_label_materializer.py`.

**Interfaces:** `materialize_anchor(root: Path, anchor: AnchorDispositionV1, lineage: HistoricalAnchorLineageV1, version: str) -> LabelRowV1 | ExcludedAnchorV1`.

- [ ] Write failing tests asserting an eligible historical anchor calls `Phase2AEvidenceAssemblerV1` then `ReferenceLabelEngine`, pins `ProvenancePath.HISTORICAL`, and has null snapshot IDs.
- [ ] Run `python -m pytest tests/labels/test_label_materializer.py -q`; expect import failure.
- [ ] Implement the exact flow `anchor -> assembler -> LabelInputBundleV1 -> ReferenceLabelEngine -> LabelResultV1 -> LabelRowV1`; do not duplicate formula code or reject outcome facts solely because `available_at > anchor cutoff`.
- [ ] Add regression tests for exact five domains, revocation/tamper rejection, and no provider/network import/call.
- [ ] Run focused tests plus `tests/labels/test_reference_engine.py`; expect PASS. Commit `feat: add historical label row materializer`.

### Task 6: Coverage accounting and scoped unsafe preservation

**Files:** Modify `dataset_contracts.py`; extend `test_label_materializer.py`; create `tests/labels/test_phase2b_coverage.py`.

**Interfaces:** `CoverageAccountingV1.from_dispositions(dispositions, rows) -> CoverageAccountingV1`.

- [ ] Write failing tests for effective/eligible/excluded/materialized counts, per-label three-state counts, exact reason-code counts, unsupported CA, delisting, identity unresolved, status unresolved, expected-bar-missing, and barrier ambiguity.
- [ ] Run `python -m pytest tests/labels/test_phase2b_coverage.py -q`; expect missing coverage builder.
- [ ] Implement counter-only aggregation from immutable row/disposition values. A count cannot change a label state or turn unknown coverage into no event.
- [ ] Add a count-preserving mutation that swaps an unsafe reason; semantic validation must fail.
- [ ] Run focused tests; expect PASS. Commit `feat: add Phase 2B coverage accounting`.

### Task 7: Month-streaming partition materializer

**Files:** Modify `materializer.py`; extend `test_label_materializer.py`; extend `test_partition_store.py`.

**Interfaces:** `materialize_month(root, month: YearMonthV1, lineage, version) -> MaterializedPartitionV1`.

- [ ] Write failing tests that feed a multi-anchor month generator and assert ordered streaming, one month plus five-session look-ahead only, exact partition hash, and no partial partition on a systemic fault.
- [ ] Run focused materializer/store tests; expect `materialize_month` missing.
- [ ] Implement generator-based assembly and atomic create-or-identical publication after all rows pass structural validation.
- [ ] Add instrumentation fields `rows`, `canonical_bytes`, `elapsed_seconds`, and `peak_rss_bytes` to a non-research operational ledger; do not set performance thresholds.
- [ ] Run focused tests; expect PASS. Commit `feat: add month-streaming Phase 2B materializer`.

### Task 8: Incremental selector and frozen field-level maturation

**Files:** Create `src/v5_2/labels/incremental.py`; create `tests/labels/test_incremental_maturation.py`.

**Interfaces:** `select_incremental_workset(predecessor: LabelDatasetManifestV1, latest_completed_session: date, governance_changes: tuple[GovernanceChangeV1, ...]) -> IncrementalMaturationLedgerV1`.

- [ ] Write failing tests: H1 selects only `return_1d`; H3 selects `return_3d`; H5 selects return_5d/MFE/MAE/both barriers; decisive barrier at H1 does not select it early; same pinned inputs yield identical workset ID.
- [ ] Run `python -m pytest tests/labels/test_incremental_maturation.py -q`; expect import failure.
- [ ] Implement selector inputs solely from predecessor manifest, persisted `LabelValueV1` horizon endpoints, approved completed session, and explicit lineage supersession/revocation IDs. Do not read wall clock time.
- [ ] Add tests for NEW_ANCHORS, revocation work, duplicate work keys, and `NOT_LABEL_SAFE` permanent cases that are not auto-retried.
- [ ] Run focused tests; expect PASS. Commit `feat: add deterministic Phase 2B incremental selector`.

### Task 9: Immutable maturation generations

**Files:** Modify `incremental.py`; modify `materializer.py`; extend `test_incremental_maturation.py`.

- [ ] Write failing tests for H1, H3, and H5 transitions, unchanged row IDs outside the workset, old partition/manifest byte preservation, and new partition/manifest supersession IDs.
- [ ] Run focused incremental tests; expect no generation materializer.
- [ ] Implement `materialize_incremental_generation(...)` by rebuilding affected complete anchor months only and publishing a new exact manifest.
- [ ] Add collision, retry-idempotency, and predecessor-manifest tamper tests.
- [ ] Run focused tests; expect PASS. Commit `feat: add immutable Phase 2B maturation generations`.

### Task 10: Eighteen executable acceptance predicates

**Files:** Create `src/v5_2/labels/phase2b_gates.py`; create `tests/labels/test_phase2b_gates.py`.

- [ ] Write one positive and one semantic negative test for each frozen gate: `CONTRACT_PINNING`, `HISTORICAL_COVERAGE_ACCOUNTING`, `STATE_SEMANTICS`, `RETURN_SEMANTICS`, `MFE_MAE_SEMANTICS`, `BARRIER_SEMANTICS`, `CORPORATE_ACTION_SAFETY`, `SUSPENSION_SAFETY`, `DELISTING_SAFETY`, `IDENTITY_SAFETY`, `PENDING_MATURATION`, `NOT_LABEL_SAFE_PRESERVATION`, `PARTITION_INTEGRITY`, `MANIFEST_INTEGRITY`, `LINEAGE_INTEGRITY`, `DETERMINISTIC_REPLAY`, `INCREMENTAL_IDEMPOTENCY`, and `CLEAN_ROOM_STANDALONE`.
- [ ] Run `python -m pytest tests/labels/test_phase2b_gates.py -q`; expect import failure.
- [ ] Implement `evaluate_phase2b_gates(inputs: Phase2BGateInputsV1) -> Phase2BGateEvaluationV1` with exact artifact IDs, explicit predicate evidence, and fail-closed statuses.
- [ ] Add count-preserving negative mutations for row reason, lineage ID, partition ID, manifest ID, and barrier/H5 scheduling; each must fail its relevant predicate.
- [ ] Run focused tests; expect PASS. Commit `feat: add Phase 2B executable gates`.

### Task 11: Feature/label firewall and static isolation

**Files:** Create `tests/labels/test_phase2b_firewall.py`; modify `scripts/verify_standalone.py` only if the tests demonstrate a missing scan.

- [ ] Write failing AST/import tests that ensure dataset/materialization code does not import providers, and future feature namespaces cannot import label rows, label values, future outcome bundles, outcome snapshots, or label reason codes as feature inputs.
- [ ] Run `python -m pytest tests/labels/test_phase2b_firewall.py -q`; expect absent firewall checks.
- [ ] Implement the smallest static check required by the failing test; do not create a Phase 3 module.
- [ ] Run firewall plus standalone verifier; expect PASS. Commit `test: enforce Phase 2B feature label firewall`.

### Task 12: Preregistered small-window pilot contract

**Files:** Create `src/v5_2/labels/pilot_phase2b.py`; create `tests/labels/test_phase2b_pilot.py`; create `docs/reports/V5_2_PHASE_2B_PILOT_PREREGISTRATION.md`.

- [ ] Write failing tests for deterministic selection from a declared bounded date interval and required strata: normal, dividend, bonus share, suspension, identity transition, delisting, pending tail, and `NOT_LABEL_SAFE` where present. Absent strata must be declared rather than replaced after results.
- [ ] Run focused pilot tests; expect missing preregistration contract.
- [ ] Implement `Phase2BPilotContractV1.create(...)` and a deterministic selector that records source manifest/lineage IDs before materialization.
- [ ] Add tests proving candidate reordering, post-result selection changes, and missing required pin fail closed.
- [ ] Run focused tests; expect PASS. Commit `feat: preregister Phase 2B small-window pilot`.

### Task 13: Checkpoint 19 only — pilot runner and evidence report

**Authorization prerequisite:** independent review must have accepted Checkpoint 18 and explicitly opened Checkpoint 19.

**Files:** Create `scripts/run_phase2b_small_window_pilot.py`; modify `pilot_phase2b.py`; extend `test_phase2b_pilot.py`; create `docs/reports/V5_2_PHASE_2B_SMALL_WINDOW_PILOT.md` only when the runner has produced real output.

- [ ] Write failing tests for offline pilot execution: rows, partition generations, manifest, coverage ledger, gate evaluation, deterministic second run, and collision behavior.
- [ ] Run focused pilot tests; expect missing runner.
- [ ] Implement a runner that accepts only an explicit preregistration ID and exact source manifest IDs, writes content-addressed pilot artifacts, and records scale measurements. It must reject a broad interval.
- [ ] Run the preregistered small-window pilot once and replay it once. Record observed rows/month, bytes/month, peak RSS, seconds/month, throughput, all 18 gate results, and exact scoped exclusions.
- [ ] Run focused tests; commit `feat: run preregistered Phase 2B pilot`.

**Hard stop:** Stop here for independent review. The pilot does not authorize broad historical materialization.

### Task 14: Checkpoint 19 only — verification and stop report

**Authorization prerequisite:** Task 13's preregistered pilot completed inside an explicitly opened Checkpoint 19.

**Files:** Create `docs/reports/V5_2_PHASE_2B_CHECKPOINT_19.md` after actual verification output exists.

- [ ] Run focused Phase 2B tests, Phase 2A labels regression, Phase 0-1C regression, full pytest, standalone, clean-room, build/wheel smoke, zero-dependency scan, credential scan, deterministic replay, tamper/revocation, partition/manifest collision, incremental idempotency, count-preserving mutation tests, and `git diff --check`.
- [ ] Record exact commands, output counts, pilot artifact IDs, 18-gate statuses, provider/network request count, diff scope, remote feature head, unchanged `origin/main`, and worktree status.
- [ ] Commit `docs: record Phase 2B Checkpoint 19 pilot acceptance` and push only `phase2a-implementation`.

**Hard stop:** `CHECKPOINT 19 = PILOT READY FOR INDEPENDENT REVIEW` or a concrete fail-closed blocker. Do not run 2010-to-current materialization and do not create Phase 2B final acceptance.

## Checkpoint structure

```text
Checkpoint 18 = Tasks 1-12 core infrastructure and pilot preregistration; stop before a pilot run
Checkpoint 19 = preregistered small-window pilot; stop for independent review
Checkpoint 20 = broad historical month-streaming materialization; separately authorized
Checkpoint 21 = final Phase 2B broad acceptance; separately authorized
```

### Reserved Checkpoint 20 scope — not authorized by this plan

After separate authorization, resume from a manifest-independent operational
checkpoint containing only the exact lineage IDs, ordered completed month keys,
and byte-identical completed partition IDs. It is not a research manifest and
cannot be consumed by research. Stream `2010-01-04` through the latest
label-mature anchor month in chronological anchor-month order, run the exact
Task 7 materializer, and retain each complete partition generation
create-or-identical. On restart, verify every recorded completed partition ID
and resume at the first unrecorded month; any mismatch fails the run closed.

The broad run must produce a provisional coverage ledger containing rows/month,
bytes/month, peak RSS, seconds/month, assembler/engine/write throughput,
per-label state counts, reason counts, scoped quarantines, and systemic defect
count. It must not publish an active `LabelDatasetManifestV1` until the entire
requested interval has passed the future Checkpoint 21 gate evaluation.

### Reserved Checkpoint 21 scope — not authorized by this plan

Reload exact completed partitions and all pinned input artifacts, verify their
canonical bytes, independently recompute every one of the eighteen gate
predicates, replay a preregistered partition sample, run tamper/revocation and
count-preserving semantic mutations, then create a final content-addressed
acceptance artifact. Any failed gate leaves broad publication closed and does
not overwrite prior immutable artifacts.

## Completion boundary for this plan

This plan itself authorizes no code, data artifact, provider request, pilot,
broad run, or final acceptance. It is complete only after independent review.
