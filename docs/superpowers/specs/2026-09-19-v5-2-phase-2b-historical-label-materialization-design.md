# V5.2 Phase 2B Historical Label Materialization Design

## Purpose and frozen authority

Phase 2B safely applies the accepted Phase 2A outcome semantics to the
historical A-share anchor universe and publishes an immutable, partitioned
outcome-label dataset for later training and evaluation.

```text
Phase 2A final acceptance ID =
75df8940cfa5f31757fc9b105be172e60581ead32ff0494fb4c84a2baac43cf7
Phase 2A = PASS / CLOSED
Phase 2B implementation = NOT AUTHORIZED
```

The following are frozen inputs, not redesign targets: `LabelContractV1`,
`ReferenceLabelEngine`, `LabelState`, `LabelReasonCode`, `LabelValueV1`,
`LabelResultV1`, `AnchorKnowledgeBoundary`, `LabelReferencePrice`, the exact
five-domain `LabelInputBundleV1`, and the Phase 1 approval/manifest/revocation
contracts. `IPO_SEASONING_SESSIONS = 5` and the existing eligibility rules
also remain authoritative.

Phase 2B does not change Phase 1 or Phase 2A, create a historical
`ResearchDataSnapshot`, access a provider, implement a feature, or authorize
Phase 3, ranking, backtesting, ML, candidates, UI, scheduler, brokerage, or
realtime scanning.

## Outcome truth versus feature knowledge

An anchor is `(canonical_security_identity, exchange-open anchor session D)`.
Phase 2A eligibility is knowledge available at D's research cutoff. A Phase 2B
label is outcome truth observed after D. It may legitimately consume approved
future bars, status, corporate-action, and delisting facts whose `available_at`
is after D's cutoff. This is not feature leakage.

```text
feature knowledge / eligibility = facts available at D cutoff
label outcome truth             = approved outcome facts needed for D+1..D+5
```

Outcome inputs must still be approved, immutable, exact-lineage-bound, and
accepted by the frozen engine. Historical work uses
`ProvenancePath.HISTORICAL` with approved Phase 1 lineage and no snapshot IDs.
Contemporaneous work uses `ProvenancePath.CONTEMPORANEOUS` and pins real anchor
and outcome `ResearchDataSnapshotV1` IDs. Neither path fabricates a snapshot.

## Materialization unit decision

| Candidate | Benefit | Limitation |
| --- | --- | --- |
| Per security | scoped repair is simple | excessive artifact/manifest fan-out |
| Per anchor session | smallest retry unit | too many published artifacts |
| Per calendar month | chronological, auditable, bounded | one late change regenerates a month |
| Hybrid workset + month | fine-grained selection and bounded storage | needs a strict workset rule |

**Decision: monthly anchor-session partitions with an anchor-session workset.**
The published partition key is the anchor session's `(year, month)`. The
incremental selector produces exact anchor keys; every affected key causes a
new immutable generation of its anchor-month partition. A horizon crossing a
month boundary remains in its anchor month. This preserves a stable row
identity, limits rebuild blast radius, and produces roughly one historical
partition per open calendar month rather than one per security or session.

## LabelRowV1

`LabelRowV1` is an immutable envelope for one exact `LabelResultV1`; it never
recomputes a label. Its `row_id` is the canonical hash of all fields below:

```text
schema_version = LabelRowV1
canonical_security_identity, anchor_session
label_contract_version, materialization_version, provenance_path
anchor_boundary_hash, anchor_reference_price_hash | null
input_bundle_hash, calculation_result_hash
five ordered DomainLineageV1 hashes
anchor_snapshot_id | null, outcome_snapshot_id | null
seven ordered LabelValueV1 hashes and values
ordered barrier evidence hashes
```

The seven values use frozen `CORE_LABELS` order. Decimals use frozen contract
quantization and fixed-point ASCII (never exponent notation); booleans are JSON
booleans; unavailable values are JSON `null`; reason codes are exact enum
strings; dates are ISO dates; aware timestamps normalize to ISO UTC text.

**Maturation decision: field-level.** The reference engine already makes H1
available while H3/H5 and their dependent fields can remain `LABEL_PENDING`.
Phase 2B stores those exact seven values. It creates no competing row-state
machine and may not lower a partially mature row to all-pending. Consumers may
call a row fully available only when every value is `LABEL_AVAILABLE`; any
`NOT_LABEL_SAFE` value remains unsafe. Reporting summaries are derived counts,
not new semantics.

Validation rejects duplicate `(identity, anchor_session, label_contract_version,
provenance_path)` keys in a generation, mismatched bundle/result hashes,
noncanonical ordering, or invalid nested hashes.

## Pending, unsafe, and immutable supersession

`LABEL_PENDING` is a valid immutable observation. When a later approved
completed session matures a horizon, Phase 2B builds a new exact bundle,
evaluates the unchanged reference engine, writes a new row in a new generation
of the anchor-month partition, and publishes a superseding manifest. It never
mutates the old row, partition, or manifest.

The deterministic incremental selector has two worksets:

```text
NEW_ANCHORS = newly eligible anchors for an approved completed session
MATURED_PENDING_ANCHORS = prior rows with a pending LabelValueV1 whose frozen
                          horizon endpoint is now <= latest approved completed
                          exchange session
```

Anchors affected by an explicit approval/lineage supersession or revocation are
also selected. A revocation causes a scoped replacement or typed quarantine;
it cannot silently retain unsafe research truth.

`NOT_LABEL_SAFE` is not pending, missing, or zero return. The row preserves its
exact `LabelReasonCode`, affected values, bundle hash, and barrier evidence.
Only new immutable evidence or a valid governance supersession may cause a
recalculation. Permanent semantic unsafety (for example, delisting inside the
horizon, unsupported corporate action, or barrier ambiguity) cannot be
auto-retried into availability. Missing data cannot be converted to no action,
a carried price, or a synthetic bar.

## LabelPartitionV1 and LabelDatasetManifestV1

`LabelPartitionV1` is a content-addressed immutable anchor-month generation:

```text
schema_version, partition_key, generation_id
label_contract_version, materialization_version, provenance_path_scope
input_lineage_set_id, ordered row_ids, row_count
per-label state counters, reason-code counters
supersedes_partition_id | null, partition_id
```

`input_lineage_set_id` canonically hashes the exact ordered five-domain
approval/manifest identities. It is never a latest pointer. The initial
implementation should keep historical and contemporaneous provenance in
separate partition generations, making replay and audit unambiguous.

`LabelDatasetManifestV1` is content-addressed and pins:

```text
schema_version, scope [2010-01-04, latest mature anchor]
label_contract_version, materialization_version
Phase2A final acceptance ID, ordered active partition IDs
partition supersession map, exact Phase1 approval/manifest/revocation IDs
coverage accounting, broad-acceptance artifact IDs
previous_manifest_id | null, manifest_id
```

Research code receives an exact manifest ID. A human-facing `current` pointer
may aid navigation only; directory scans, mutable CSV replacement, and latest
artifact lookup can never determine research truth.

## Historical coverage, scale, and execution

The baseline interval is `2010-01-04` through the latest label-mature anchor
session. It does not imply that every security-session has a usable label.
Before evaluation, approved calendar, dated canonical identity, listing
interval, five-session IPO seasoning, delisting, daily status, and Phase 1
fail-closed exclusions determine anchor eligibility.

Every manifest reports:

```text
effective anchors, eligible anchors, excluded-before-label, materialized rows
per-label LABEL_AVAILABLE / LABEL_PENDING / NOT_LABEL_SAFE counts
reason-code counts, partition count, duplicate-key count (must be zero)
quarantined scoped defects, unresolved scoped defects, systemic defects
historical and contemporaneous provenance-path counts
```

The existing Phase 1 daily-bar composite has 14,020,830 rows. This defines the
scale class, not an expected label count. Around sixteen years of history means
roughly 192 anchor-months; actual per-month row count and artifact size must be
measured before implementation. The execution model streams one ordered month
and its five-session look-ahead at a time, emitting rows in
`(anchor_session, canonical_security_identity)` order. It must never load the
full 2010-to-current panel as Python objects.

### Historical baseline

1. Pin one Phase 1 lineage set, the accepted Phase 2A contract, an anchor scope,
   and a materialization version.
2. Stream open anchor sessions month by month and resolve eligibility at each
   anchor cutoff.
3. Count ineligible anchors as `excluded-before-label`, never as fake pending.
4. Assemble the exact historical five-domain bundle, evaluate the frozen engine,
   validate row hashes, and write an immutable month partition.
5. Publish a manifest only after every selected partition passes validation.

### Incremental run

1. Pin a predecessor manifest and exact latest approved completed session.
2. Derive the two worksets from persisted row values and horizon endpoints, not
   wall-clock time.
3. Include explicit lineage supersession/revocation work.
4. Group by anchor month and rebuild only complete affected partition generations.
5. Verify unaffected rows retain IDs; write a new manifest with explicit
   supersession. Same inputs must yield the same worksets, bytes, IDs, and
   manifest ID; a rerun may not write differing bytes.

## Failure model

Scoped defects remain machine-visible:

```text
individual identity/status/bar/CA defect
  -> exact NOT_LABEL_SAFE reason, explicit quarantine, or excluded-before-label
```

Systemic integrity defects fail the attempted publication closed:

```text
calendar corruption/non-monotonic sessions
missing, revoked, or tampered approval/manifest
partition hash mismatch or noncanonical ordering
contract-version mismatch, duplicate row identity
row/partition/manifest lineage-set mismatch
nondeterministic replay or unexplained systemic coverage gap
```

No partial manifest is published after a systemic defect. Existing immutable
manifests remain interpretable and cannot be overwritten by a failed attempt.

## Broad historical acceptance gates

Phase 2B must define executable, artifact-driven predicates for eighteen gates:

```text
1 CONTRACT_PINNING                 10 IDENTITY_SAFETY
2 HISTORICAL_COVERAGE_ACCOUNTING   11 PENDING_MATURATION
3 STATE_SEMANTICS                  12 NOT_LABEL_SAFE_PRESERVATION
4 RETURN_SEMANTICS                 13 PARTITION_INTEGRITY
5 MFE_MAE_SEMANTICS                14 MANIFEST_INTEGRITY
6 BARRIER_SEMANTICS                15 LINEAGE_INTEGRITY
7 CORPORATE_ACTION_SAFETY          16 DETERMINISTIC_REPLAY
8 SUSPENSION_SAFETY                17 INCREMENTAL_IDEMPOTENCY
9 DELISTING_SAFETY                 18 CLEAN_ROOM_STANDALONE
```

The later implementation plan must state each predicate's exact input
artifacts, invariant or expected count, failure code, and test fixture. Counts
alone never establish correctness.

## Phase 3 feature/label firewall

Phase 3 may pin `LabelDatasetManifestV1` for training, evaluation, or research
analysis. Feature computation may use only anchor identity, anchor session, and
feature-side PIT inputs authorized at the anchor cutoff. It must not import
label partitions, values, future outcome facts, future fields from an input
bundle, outcome snapshots, or reason codes as feature or ranking-time inputs.

The later join is allowed only after the feature dataset and label dataset each
pin their own immutable manifest. This firewall must be enforced by imports,
runtime contracts, and tests in Phase 3; Phase 2B does not implement Phase 3.

## Rollout boundary

Once separately authorized, work should proceed from partition/manifest tests,
to a small historical window, to deterministic supersession tests, to a
preregistered broad historical run and its acceptance gates. This document is
not an implementation plan and authorizes none of those steps.

```text
CHECKPOINT 16 DESIGN = PASS / READY FOR INDEPENDENT REVIEW
PHASE 1 CHANGE = NO
PHASE 2A CHANGE = NO
PHASE 2B IMPLEMENTATION AUTHORIZED = NO
```

No frozen Phase 1 lineage or Phase 2A semantic change is required.
