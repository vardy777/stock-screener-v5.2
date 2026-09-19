# V5.2 Phase 2A Acceptance V2.1 Attempt 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct the two Checkpoint 11 acceptance-infrastructure defects by recording truthful Layer B provenance and executing all 16 frozen Phase 2A gate semantics, while preserving Phase 1, label semantics, and every Attempt 1 artifact.

**Architecture:** Extend the existing six V2 artifact families with narrowly scoped V2.1 versions and one immutable Attempt 1-to-2 supersession artifact. Build missing-bar coverage from an exactly pinned real bundle plus a content-addressed one-bar transform, exercise unsupported Corporate Action safety through `CorporateActionRepository.query`, and resolve the frozen 16 gates through explicit Python predicates rather than layer booleans or a generic expression language.

**Tech Stack:** Python 3.12, frozen dataclasses, canonical SHA-256 identities via `v5_2.data.identity.content_hash`, pytest, AST isolation checks, immutable JSON artifacts, PowerShell verification on Windows.

**Spec:** `docs/superpowers/specs/2026-09-19-v5-2-phase-2a-acceptance-architecture-v2-1-design.md`

## Global Constraints

- Original V2 design authority: `f92f0a564c802ddc28dc71153be44d409b6858ee`.
- Original V2 plan authority: `4db0f4ecb9e61853190f755d1bee164d9f84fe9a` plus provenance correction `390149882f3265b778b736a16380c13d9a64652a`.
- V2.1 amendment identity: `d4a7941e2583eb84dd1bf501fb9183d5346f3813f383704b691c3798fb8ac25b`; design HEAD: `a66825e25d40a46eceae18a50f1f2535ab9ee975`.
- V2.1 overrides V2 only for evidence classification, unsupported-CA boundary execution, and executable 16-gate evaluation.
- Checkpoint 8 missing-bar unavailability evidence: `947a8cd54a0a9a9bf91a8a4b45e7b502c272fb8dff374eab19b99615fca98f48`.
- Attempt 1 artifacts are immutable historical FAIL evidence: amendment `31d262c3a54ebb15b9161a1a2b36e9bdd999a61c92aeb2d87a64ddedcf9e4365`, Layer A `685a441408b4621df177dec7d5a54375b6b15874c49520b8c6b788ef9f8372b8`, Layer B `ad915a5abb2fcf071929089cf85c7924c6c2254ccf8b870b32c613d96ba62505`, Layer C `455fca83088ee0c40f30461c04e8fd5e04f40d47bdc8e94c4d70d0c986ad4ef6`, gate map `9b9ec9d4039194dcf2281b2aadcbf380fcd5da98acc79d2e5ff20eca90e6c264`, and fixture inventory `97e610d410a58001963791e6992cac4a1eb469e4f347afde4e0a72aeeea6e934`. Attempt 2 writes new IDs and records reason `INFRASTRUCTURE_ACCEPTANCE_CORRECTNESS_DEFECT`.
- Do not change `ReferenceLabelEngine`, label arithmetic, frozen label contracts, Phase 1 facts/approvals/manifests, Phase 1 supported CA scope, or `Phase2AEvidenceAssemblerV1` runtime semantics.
- Do not overwrite or silently reinterpret Attempt 1 JSON. Do not modify the V1 inventory, Checkpoint 7/8 artifacts, original V2 design, or original V2 plan.
- Provider requests: `0`. Data network calls: `0`.
- This plan ends after Attempt 2 infrastructure verification. It must not create the authoritative final `Phase2AAcceptanceV2_1` artifact, mark Phase 2A PASS, update `origin/main`, or begin Phase 2B.
- Frozen checkpoint boundary: `FINAL ACCEPTANCE RUN PLANNED IN THIS CHECKPOINT = NO`; `PHASE2B = NOT AUTHORIZED`.

## Planned File Layout

- Modify `src/v5_2/labels/acceptance_v2_contracts.py`: add V2.1 provenance, ledger, gate-map, and supersession schemas without changing V2 schema behavior.
- Modify `src/v5_2/labels/acceptance_v2_boundaries.py`: add truthful missing-bar and real unsupported-CA V2.1 builders; retain Attempt 1 helpers only for historical replay.
- Modify `src/v5_2/labels/acceptance_v2_layer_a.py`: build V2.1 Layer A with an explicit mandatory-role index.
- Modify `src/v5_2/labels/acceptance_v2_layer_c.py`: verify V2.1 compatibility with the exact four frozen fixtures.
- Create `src/v5_2/labels/acceptance_v2_1_predicates.py`: one explicit evaluator per frozen gate name and a fixed dispatch table.
- Create `src/v5_2/labels/acceptance_v2_1_resolver.py`: pure orchestration over the 16 predicate results; no I/O and no final artifact materialization.
- Create `scripts/build_phase2a_acceptance_v2_1_attempt2_infrastructure.py`: offline materializer for new Attempt 2 artifacts only.
- Create `tests/labels/test_acceptance_v2_1_contracts.py`, `test_acceptance_v2_1_boundaries.py`, `test_acceptance_v2_1_gate_predicates.py`, `test_acceptance_v2_1_firewall.py`, `test_acceptance_v2_1_resolver.py`, and `test_acceptance_v2_1_infrastructure.py`.
- Create `docs/reports/V5_2_PHASE_2A_V2_1_ATTEMPT_2_INFRASTRUCTURE.md` only in Task 13 after verification.
- Create new JSON files under `data/phase_2a/v2_1_attempt2/`; never write under `data/phase_2a/v2_infrastructure/`.

## Review Focus

- A content-valid missing-bar case with `real_condition_observed=True` must fail provenance validation even if its assembler rejection is correct; Task 1 and Task 10 test this.
- A real unsupported scope plus `ACCEPTANCE_ONLY_CA_PREFLIGHT` must not satisfy `CORPORATE ACTION SAFETY`; Task 4 and Task 9 test this.
- Count-preserving loss of a required Layer A role must fail only the affected semantic gates rather than pass from `20` cases; Task 6 and Task 9 test this.
- A serialized zero invocation count must not substitute for structurally unreachable engine control flow; Task 3, Task 4, and Task 11 use raising/counting spies.
- Engine-zero proof means `pre-engine rejection -> engine structurally unreachable`; persisted counters are corroborating evidence only.
- Replaying the materializer against an occupied Attempt 1 path or a conflicting Attempt 2 filename must fail without overwriting bytes; Task 2 and Task 12 test this.

---

### Task 1: Add the V2.1 Provenance Contracts

**Files:**
- Modify: `src/v5_2/labels/acceptance_v2_contracts.py`
- Create: `tests/labels/test_acceptance_v2_1_contracts.py`

**Interfaces:**
- Consumes: existing `EvidenceClass`, `_digest`, `_ids`, and immutable Attempt 1 schema classes.
- Produces: `BoundaryEvidenceProvenanceV2_1`, `BoundaryExecutionV2_1`, `FailClosedBoundaryLedgerV2_1`, and `Phase2AAcceptanceArchitectureAmendmentV2_1`.

- [ ] **Step 1: Write failing schema tests**

Add tests that construct the four distinct evidence forms and reject mixed classification:

```python
def test_missing_bar_requires_real_base_plus_non_real_fixture():
    value = BoundaryEvidenceProvenanceV2_1.create(
        base_evidence_class="REAL_MARKET_EVIDENCE",
        boundary_exercise_class="DETERMINISTIC_CONTRACT_FIXTURE",
        real_condition_observed=False,
        real_condition_availability="REAL_REFERENCE_SAMPLE_UNAVAILABLE",
        unavailability_evidence_id=CHECKPOINT8_DISCOVERY_ID,
    )
    assert value.verify()


def test_fixture_cannot_claim_real_observed_condition():
    with pytest.raises(ValueError, match="fixture cannot be real observed"):
        BoundaryEvidenceProvenanceV2_1.create(
            base_evidence_class="REAL_MARKET_EVIDENCE",
            boundary_exercise_class="DETERMINISTIC_CONTRACT_FIXTURE",
            real_condition_observed=True,
            real_condition_availability="OBSERVED",
            unavailability_evidence_id=None,
        )
```

Also prove `REAL_UNSUPPORTED_MARKET_EVENT` requires `real_condition_observed=True`, pure Layer C fixtures cannot enter Layer B, and the V2.1 amendment pins all five authorities from Global Constraints.

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_contracts.py -q
```

Expected: collection/import failure because the V2.1 classes do not exist.

- [ ] **Step 3: Implement the minimal frozen schemas**

Add explicit enums or validated string fields for exactly:

```python
base_evidence_class
boundary_exercise_class
real_condition_observed
real_condition_availability
unavailability_evidence_id
```

`BoundaryExecutionV2_1` must additionally pin `transform_id`, `transformed_evidence_id`, `removed_session`, `rejection_boundary`, exact expected/observed rejection, assembler invocation count, engine invocation count, and input artifact IDs. Keep `BoundaryExecutionV2` unchanged.

- [ ] **Step 4: Run GREEN and legacy contract regression**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_contracts.py tests/labels/test_acceptance_v2_contracts.py tests/labels/test_acceptance_v2_amendment.py -q
```

Expected: all selected tests pass; V2 artifact identities remain unchanged.

- [ ] **Step 5: Commit**

```powershell
git add src/v5_2/labels/acceptance_v2_contracts.py tests/labels/test_acceptance_v2_1_contracts.py
git commit -m "feat: add Phase 2A V2.1 provenance contracts"
```

**STOP condition:** any V2 class must be mutated in a way that changes an Attempt 1 content identity.

### Task 2: Freeze Attempt 1-to-2 Supersession

**Files:**
- Modify: `src/v5_2/labels/acceptance_v2_contracts.py`
- Modify: `tests/labels/test_acceptance_v2_1_contracts.py`

**Interfaces:**
- Consumes: all six exact Attempt 1 IDs and the V2.1 amendment identity.
- Produces: `AttemptInfrastructureSupersessionV2_1.create(attempt1_ids, attempt2_ids, reason)`.

- [ ] **Step 1: Write failing supersession tests**

```python
def test_supersession_pins_six_old_and_six_new_ids():
    item = AttemptInfrastructureSupersessionV2_1.create(
        attempt1_ids=ATTEMPT1_IDS,
        attempt2_ids=tuple(chr(103 + i) * 64 for i in range(6)),
        reason="INFRASTRUCTURE_ACCEPTANCE_CORRECTNESS_DEFECT",
    )
    assert item.verify()
    assert set(item.attempt1_ids) == set(ATTEMPT1_IDS)


def test_supersession_rejects_overlap_or_wrong_reason():
    with pytest.raises(ValueError):
        AttemptInfrastructureSupersessionV2_1.create(
            attempt1_ids=ATTEMPT1_IDS,
            attempt2_ids=ATTEMPT1_IDS,
            reason="replacement",
        )
```

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_contracts.py -q
```

Expected: missing supersession type or failing validation.

- [ ] **Step 3: Implement immutable supersession validation**

Require exact six unique old IDs, exact six unique new IDs, disjoint sets, exact reason, V2.1 amendment ID, and a content-addressed `supersession_id`. Do not add mutable status fields and do not load “latest” artifacts.

- [ ] **Step 4: Run GREEN**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_contracts.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/v5_2/labels/acceptance_v2_contracts.py tests/labels/test_acceptance_v2_1_contracts.py
git commit -m "feat: freeze Phase 2A Attempt 2 supersession"
```

**STOP condition:** implementation needs to rewrite, delete, rename, or regenerate an Attempt 1 artifact.

### Task 3: Build the Truthful Missing-Bar Fixture

**Files:**
- Modify: `src/v5_2/labels/acceptance_v2_boundaries.py`
- Create: `tests/labels/test_acceptance_v2_1_boundaries.py`

**Interfaces:**
- Consumes: `Phase2AEvidenceAssemblerV1.assemble`, frozen inventory slot 1 as the real base, and Checkpoint 8 discovery ID.
- Produces: `build_missing_bar_boundary_case_v2_1(repository_root) -> BoundaryExecutionV2_1`.

- [ ] **Step 1: Write RED tests for exact pinning and mutation isolation**

The test must assemble the base once, identify the first required future session, run the transform, and assert:

```python
assert result.provenance.base_evidence_class == "REAL_MARKET_EVIDENCE"
assert result.provenance.boundary_exercise_class == "DETERMINISTIC_CONTRACT_FIXTURE"
assert result.provenance.real_condition_observed is False
assert result.provenance.unavailability_evidence_id == CHECKPOINT8_DISCOVERY_ID
assert result.rejection_boundary == "Phase2AEvidenceAssemblerV1.assemble"
assert result.observed_rejection_code.startswith("UNEXPLAINED_MISSING_BAR:")
assert result.engine_invocation_count == engine.calls == 0
assert len(result.real_base_lineage_ids) == 5
assert result.transform_id == content_hash(expected_transform_body)
```

Add negative tests that mutate the anchor bar, Calendar, Master/Identity, Status, Corporate Action, or a second future bar; each must raise `ValueError("REMOVE_FUTURE_BAR transform scope violation")`.

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_boundaries.py -k missing_bar -q
```

Expected: missing builder/schema fields.

- [ ] **Step 3: Implement the minimum content-addressed transform**

Represent the transform body exactly as:

```python
{
    "schema_version": "RemoveFutureBarTransformV2_1",
    "base_bundle_id": base_bundle.bundle_id,
    "five_domain_lineage_ids": base_bundle.lineage_ids,
    "removed_required_future_session": removed.isoformat(),
    "operation": "REMOVE_FUTURE_BAR",
}
```

Hash both this body and a canonical transformed-evidence descriptor. Invoke the existing assembler fault path and capture the real exception; do not duplicate assembler missing-bar logic in the builder. Use a raising/counting engine spy passed through the test harness so execution after rejection is structurally impossible.

The resulting ledger must record `FAIL-CLOSED CONTRACT COVERAGE = YES` and `REAL OBSERVED FAILURE COUNT = 0`.

- [ ] **Step 4: Run GREEN and assembler regression**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_boundaries.py -k missing_bar tests/labels/test_evidence_assembler.py -q
```

Expected: PASS, including existing assembler semantics.

- [ ] **Step 5: Commit**

```powershell
git add src/v5_2/labels/acceptance_v2_boundaries.py tests/labels/test_acceptance_v2_1_boundaries.py
git commit -m "feat: classify Phase 2A missing-bar fixture truthfully"
```

**STOP condition:** the transform cannot be expressed without changing `Phase2AEvidenceAssemblerV1`, or it changes anything except the selected required future bar.

### Task 4: Exercise the Real Unsupported-CA Repository Boundary

**Files:**
- Modify: `src/v5_2/labels/acceptance_v2_boundaries.py`
- Modify: `tests/labels/test_acceptance_v2_1_boundaries.py`

**Interfaces:**
- Consumes: the exact approval, manifest, materialization audit, candidate bundle, and quarantine IDs frozen in the spec; `CorporateActionRepository.query`.
- Produces: `build_unsupported_ca_boundary_case_v2_1(repository_root) -> BoundaryExecutionV2_1`.

- [ ] **Step 1: Write RED tests that revalidate every pin from disk**

Use these exact values:

```python
APPROVAL_ID = "5e53080fd85dba5328cda9ed44c5dc5959e5bea965d8f5df12e07201deb8e974"
MANIFEST_ID = "5086896d0066baa928fe44c3469b2c1362feb2068db04acb7336b38c13bdbe2c"
AUDIT_ID = "8cf46a3dbaf6170cd64a1f2514f47ea87609200886fb2d8eebf60f888b11d28d"
CANDIDATE_ID = "e36c885b4ad5a666a829bc56eba0ba455cb26c1fae2cd321748d14908c67d16d"
QUARANTINE_ID = "000c9bb50f41b1ad603bb4367f1bf7eb5c6506557d323c2356baa00a12a3f7c6"
```

Assert the event is exactly `002029.SZ`, `2012-05-08`, and `UNSUPPORTED_SHARE_CONVERSION`; the repository raises exact `NOT_RESEARCH_SAFE: unsupported action type`; engine calls remain zero; the event is not returned as a fact or added to a bundle.

Add tamper tests for every ID/value and a test proving a serialized `ACCEPTANCE_ONLY_CA_PREFLIGHT` result cannot satisfy the builder.

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_boundaries.py -k unsupported_ca -q
```

Expected: old helper returns acceptance-only preflight and the new builder is absent.

- [ ] **Step 3: Implement exact artifact verification and real query**

Verify the approval and manifest content identities with their native schemas, verify the materialization audit content hash, verify `candidate_bundle_id`, locate the exact quarantine, and instantiate `CorporateActionRepository` from the verified approved manifest scope. Call:

```python
repository.query(
    "002029.SZ",
    date(2012, 5, 8),
    date(2012, 5, 8),
    ActionType.SHARE_CONVERSION,
    datetime(2012, 5, 8, 16, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
)
```

Capture only the exact production exception. Record base class `REAL_MACHINE_VISIBLE_UNSUPPORTED_SCOPE`, exercise class `REAL_UNSUPPORTED_MARKET_EVENT`, observed `YES`, repository boundary, and zero engine invocations.

- [ ] **Step 4: Run GREEN and production repository regression**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_boundaries.py -k unsupported_ca tests/data/test_corporate_action_repository.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/v5_2/labels/acceptance_v2_boundaries.py tests/labels/test_acceptance_v2_1_boundaries.py
git commit -m "feat: bind unsupported CA acceptance to repository safety"
```

**STOP condition:** any pinned ID/event fails verification, the exception text differs, or a replacement event would be required.

### Task 5: Build the V2.1 Layer B Ledger

**Files:**
- Modify: `src/v5_2/labels/acceptance_v2_boundaries.py`
- Modify: `tests/labels/test_acceptance_v2_1_boundaries.py`
- Modify: `tests/labels/test_acceptance_v2_layer_b.py`

**Interfaces:**
- Consumes: Tasks 1, 3, and 4 plus the eight unchanged deterministic rejection builders.
- Produces: `build_fail_closed_boundary_ledger_v2_1(repository_root, amendment) -> FailClosedBoundaryLedgerV2_1`.

- [ ] **Step 1: Write RED ledger tests**

Require the same ten categories in frozen order, but assert exact V2.1 provenance for missing bar and unsupported CA. Assert the old `ad915a5…` ledger remains byte-identical and cannot be passed as V2.1.

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_boundaries.py tests/labels/test_acceptance_v2_layer_b.py -q
```

Expected: V2.1 ledger builder absent or wrong provenance.

- [ ] **Step 3: Implement the V2.1 ledger builder**

Reuse the existing eight deterministic assembler/contract cases only after converting them into V2.1 executions with explicit provenance. Do not call `build_unsupported_ca_boundary_case` or treat `ACCEPTANCE_ONLY_CA_PREFLIGHT` as authoritative.

- [ ] **Step 4: Run GREEN**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_boundaries.py tests/labels/test_acceptance_v2_layer_b.py tests/labels/test_acceptance_v2_boundaries.py -q
```

Expected: both V2 historical tests and V2.1 tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/v5_2/labels/acceptance_v2_boundaries.py tests/labels/test_acceptance_v2_1_boundaries.py tests/labels/test_acceptance_v2_layer_b.py
git commit -m "feat: build truthful Phase 2A V2.1 boundary ledger"
```

**STOP condition:** V2.1 needs to reinterpret the Attempt 1 Layer B bytes.

### Task 6: Validate Mandatory Layer A Semantic Coverage

**Files:**
- Modify: `src/v5_2/labels/acceptance_v2_layer_a.py`
- Create: `tests/labels/test_acceptance_v2_1_layer_a.py`

**Interfaces:**
- Consumes: exact Checkpoint 7 ledger `0ee799a175a5e6832b9ca79d88ff9a0b9583ff92e204849274f96a031c397247` and the 20 verified V2 real cases.
- Produces: `RealReferenceCoverageLedgerV2_1` with `semantic_role_index` and `validate_mandatory_real_roles_v2_1`.

- [ ] **Step 1: Write RED tests for truthful roles**

Freeze mandatory role sets for returns, excursions, supported CA, suspension/resumption, delisting, identity, pending, legal-bundle unsafe, trading-session boundaries, and real barrier paths. Add count-preserving mutations that replace `SUSPENSION_THROUGH_H5`, `LATEST-SESSION_LABEL_PENDING`, and `NORMAL_NEGATIVE_RETURN` with duplicate harmless roles while retaining 20 cases; validation must fail.

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_layer_a.py -q
```

Expected: missing V2.1 role validator.

- [ ] **Step 3: Implement a fixed semantic-role index**

Build the index from verified cases and exact actual behaviors only. Reject false V1 registered strata for slots 16, 17, 20, 21, and 22. Do not recalculate any label field; reuse exact field-level MATCH comparisons after content verification.

- [ ] **Step 4: Run GREEN and Layer A regression**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_layer_a.py tests/labels/test_acceptance_v2_layer_a.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/v5_2/labels/acceptance_v2_layer_a.py tests/labels/test_acceptance_v2_1_layer_a.py
git commit -m "feat: enforce Phase 2A real semantic coverage"
```

**STOP condition:** satisfying a mandatory role requires changing a frozen label result or inventing a new real case.

### Task 7: Preserve Layer C and Expose Exact Semantic Coverage

**Files:**
- Modify: `src/v5_2/labels/acceptance_v2_layer_c.py`
- Create: `tests/labels/test_acceptance_v2_1_layer_c.py`

**Interfaces:**
- Consumes: exact four V2 fixtures and independent comparisons.
- Produces: `validate_edge_semantics_v2_1(ledger) -> bool` and a V2.1 content-addressed ledger referencing unchanged fixture identities.

- [ ] **Step 1: Write RED compatibility and mutation tests**

Assert exact names/classes/IDs and field-level MATCH. Preserve four fixtures: `UPPER_FIRST`, `LOWER_FIRST`, `NEITHER`, and `SAME_SESSION_BARRIER_AMBIGUITY`. Mutate the ambiguity semantic to `UPPER_FIRST` without changing fixture count and assert failure.

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_layer_c.py -q
```

Expected: V2.1 semantic validator absent.

- [ ] **Step 3: Implement exact fixed validation**

Validate fixture content identity, `SYNTHETIC_CONTRACT_FIXTURE`, independent/production equality for all five fields, exact semantic set, and AST/import independence. Do not count any fixture as real evidence.

- [ ] **Step 4: Run GREEN and independent-calculator regression**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_layer_c.py tests/labels/test_acceptance_v2_layer_c.py tests/labels/test_independent_edge_reference.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/v5_2/labels/acceptance_v2_layer_c.py tests/labels/test_acceptance_v2_1_layer_c.py
git commit -m "feat: pin Phase 2A V2.1 edge semantics"
```

**STOP condition:** a fixture identity or frozen calculation result must change.

### Task 8: Implement the 16 Literal Gate Predicates

**Files:**
- Create: `src/v5_2/labels/acceptance_v2_1_predicates.py`
- Create: `tests/labels/test_acceptance_v2_1_gate_predicates.py`
- Modify: `src/v5_2/labels/acceptance_v2_contracts.py`

**Interfaces:**
- Consumes: verified V2.1 amendment, Layer A/B/C ledgers, supersession, and gate map.
- Produces: `GatePredicateIdV2_1`, `GateEvidenceV2_1`, `evaluate_gate_v2_1(gate, evidence) -> GateEvaluationV2_1`, and the exact `GATE_PREDICATES_V2_1` dispatch.

- [ ] **Step 1: Write one RED test per exact gate name**

Pin the 16 names from `ACCEPTANCE_GATES`. Each test must remove or corrupt the gate-specific semantic while leaving unrelated layer verification true. The expected predicate mapping is:

```text
LABEL CONTRACT -> frozen contract identity + exactly five domain identities
CAUSAL ISOLATION -> every required pre-engine case rejects and engine is unreachable
TRADING SESSION SEMANTICS -> IPO/session/boundary real roles and calendar lineage
RETURN SEMANTICS -> positive, negative, volatility, and limit-path field MATCH
MFE/MAE SEMANTICS -> all required real excursion fields MATCH
BARRIER SEMANTICS -> truthful real paths plus four exact C comparisons
CORPORATE ACTION SAFETY -> real cash/bonus MATCH plus real repository unsupported rejection
SUSPENSION SAFETY -> D+1, multi-day, through-H5, and resumption roles
DELISTING SAFETY -> delisting legal-bundle unsafe semantic
IDENTITY SAFETY -> identity transition plus ambiguity rejection
MISSING DATA FAIL-CLOSED -> truthful missing-bar fixture, assembler rejection, engine zero
LABEL_PENDING -> real latest-session pending semantic
NOT_LABEL_SAFE -> engine-level anchor-suspension and delisting unsafe results, not assembler failure
REFERENCE SAMPLES -> complete mandatory Layer A semantic set
INDEPENDENT VERIFICATION -> required A and C field-level MATCH
DETERMINISTIC REPLAY -> all identities verify, supersession pins exact inputs, replay bytes match
```

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_gate_predicates.py -q
```

Expected: predicate module missing.

- [ ] **Step 3: Implement explicit functions, not a DSL**

Create 16 named functions such as `_label_contract`, `_causal_isolation`, and `_deterministic_replay`; dispatch through a constant mapping keyed by the exact gate string. `GateConsumptionV2_1` stores a `predicate_id` that must match the dispatch entry. It may contain a human-readable description, but evaluation must call the function.

- [ ] **Step 4: Run GREEN and exact-name regression**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_gate_predicates.py tests/labels/test_acceptance_v2_gate_map.py -q
```

Expected: 16/16 predicate tests pass and no gate alias is accepted.

- [ ] **Step 5: Commit**

```powershell
git add src/v5_2/labels/acceptance_v2_1_predicates.py src/v5_2/labels/acceptance_v2_contracts.py tests/labels/test_acceptance_v2_1_gate_predicates.py
git commit -m "feat: execute all Phase 2A V2.1 gate semantics"
```

**STOP condition:** implementation requires a generic predicate-expression DSL or changes a frozen gate meaning.

### Task 9: Prove Count-Preserving Semantic Failures

**Files:**
- Modify: `tests/labels/test_acceptance_v2_1_gate_predicates.py`

**Interfaces:**
- Consumes: Task 8 predicate dispatch and verified fixture factories.
- Produces: mandatory mutation regression suite proving counts cannot substitute for semantics.

- [ ] **Step 1: Add all required count-preserving RED mutations**

Create immutable replacements that retain `20` A cases, `10` B cases, or `4` C fixtures while respectively removing suspension, pending, return semantics, truthful missing-bar provenance, repository-backed unsupported CA, or ambiguity semantics. Also replace a gate-map `predicate_id` while retaining 16 entries.

- [ ] **Step 2: Run RED against the first implementation**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_gate_predicates.py -k count_preserving -q
```

Expected: at least one mutation incorrectly passes before tightening the relevant predicate; if all already fail, preserve the tests and record that the initial Task 8 implementation covered them.

- [ ] **Step 3: Tighten only the affected literal predicates**

Do not add global `layer_ok` shortcuts. Each failure must be produced by the gate that owns the missing semantic.

- [ ] **Step 4: Run GREEN**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_gate_predicates.py -q
```

Expected: every count-preserving mutation fails its relevant gate while the valid evidence passes.

- [ ] **Step 5: Commit**

```powershell
git add src/v5_2/labels/acceptance_v2_1_predicates.py tests/labels/test_acceptance_v2_1_gate_predicates.py
git commit -m "test: enforce count-independent Phase 2A gate semantics"
```

**STOP condition:** a mutation can only be detected by changing artifact counts or using one aggregate layer boolean.

### Task 10: Enforce the V2.1 Provenance Firewall

**Files:**
- Create: `tests/labels/test_acceptance_v2_1_firewall.py`
- Modify: `src/v5_2/labels/acceptance_v2_contracts.py`

**Interfaces:**
- Consumes: V2.1 provenance and all three ledgers.
- Produces: schema-level rejection of every forbidden evidence-class promotion.

- [ ] **Step 1: Write RED tests for the five forbidden promotions**

Test exactly:

```text
missing-bar deterministic fixture -> real observed count
real base + deterministic mutation -> REAL_APPROVED_BOUNDARY_CONDITION
pure C fixture -> real market count
unsupported real event -> synthetic classification
acceptance-only preflight -> authoritative unsupported production coverage
```

Also assert no `total_samples` aggregate exists.

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_firewall.py -q
```

Expected: invalid promotions are accepted before validation is tightened.

- [ ] **Step 3: Implement minimal constructor/verify checks**

Keep checks in the owning V2.1 dataclasses. Do not introduce a provenance registry or generic policy framework.

- [ ] **Step 4: Run GREEN plus V2 firewall regression**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_firewall.py tests/labels/test_acceptance_v2_firewall.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/v5_2/labels/acceptance_v2_contracts.py tests/labels/test_acceptance_v2_1_firewall.py
git commit -m "feat: enforce Phase 2A V2.1 provenance firewall"
```

**STOP condition:** correctness depends on an unversioned global policy or inferred evidence class.

### Task 11: Add the Pure V2.1 Infrastructure Resolver

**Files:**
- Create: `src/v5_2/labels/acceptance_v2_1_resolver.py`
- Create: `tests/labels/test_acceptance_v2_1_resolver.py`

**Interfaces:**
- Consumes: exact V2.1 amendment, supersession, A/B/C ledgers, gate map, and fixed predicate dispatch.
- Produces: `resolve_phase2a_acceptance_v2_1_infrastructure(...) -> Phase2AInfrastructureEvaluationV2_1` only; it must not create final acceptance.

- [ ] **Step 1: Write RED resolver tests**

Assert deterministic equality on identical inputs, 16/16 PASS for valid controlled fixtures, affected-gate FAIL for every mutation from Task 9, all gates FAIL on integrity or supersession mismatch, and no final `Phase2AAcceptanceV2_1` object/file.

Add AST tests forbidding filesystem, clock, environment, provider, and network imports/calls. Use raising engine spies in the boundary builders; do not trust serialized zero counts alone.

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_resolver.py -q
```

Expected: resolver absent.

- [ ] **Step 3: Implement pure orchestration**

Verify all content identities and exact cross-artifact IDs, then call `evaluate_gate_v2_1` for each entry in `ACCEPTANCE_GATES` order. Return infrastructure evaluation fields including gate results and `final_acceptance_created=False`; do not set `ready_for_phase_2b=True` in this checkpoint type.

- [ ] **Step 4: Run GREEN**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_resolver.py tests/labels/test_acceptance_v2_1_gate_predicates.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/v5_2/labels/acceptance_v2_1_resolver.py tests/labels/test_acceptance_v2_1_resolver.py
git commit -m "feat: add pure Phase 2A V2.1 infrastructure resolver"
```

**STOP condition:** the resolver needs ambient I/O, invokes the Label Engine itself, or creates authoritative final Phase 2A acceptance.

### Task 12: Materialize Attempt 2 Infrastructure Immutably

**Files:**
- Create: `scripts/build_phase2a_acceptance_v2_1_attempt2_infrastructure.py`
- Create: `tests/labels/test_acceptance_v2_1_infrastructure.py`
- Create at runtime: `data/phase_2a/v2_1_attempt2/*.json`

**Interfaces:**
- Consumes: all Task 1-11 builders and exact frozen disk artifacts.
- Produces: six new V2.1 family artifacts plus one supersession artifact, all content-addressed and byte-replayable.

- [ ] **Step 1: Write RED materializer tests**

Run materialization twice into different temporary directories and compare filenames and bytes. Require exactly seven JSON files, all new IDs, exact Attempt 1 linkage, and absence of final acceptance. Assert collision with different bytes raises and existing Attempt 1 files remain byte-identical.

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_infrastructure.py -q
```

Expected: materializer absent.

- [ ] **Step 3: Implement the offline materializer**

Load only exact paths/IDs. Revalidate the unsupported event during every run. Write canonical bytes with create-or-identical behavior. Call the pure infrastructure resolver only for controlled infrastructure evidence; report `FINAL V2.1 ACCEPTANCE = NOT RUN`, `PHASE 2A = FAIL / OPEN`, and `READY FOR PHASE 2B = NO`.

- [ ] **Step 4: Run GREEN, materialize once, and replay**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_infrastructure.py -q
python scripts/build_phase2a_acceptance_v2_1_attempt2_infrastructure.py
python scripts/build_phase2a_acceptance_v2_1_attempt2_infrastructure.py
git diff --exit-code -- data/phase_2a/v2_1_attempt2
```

Expected: tests pass; the second run is byte-identical; the last command is clean after staging the first generated artifacts for comparison.

- [ ] **Step 5: Commit**

```powershell
git add scripts/build_phase2a_acceptance_v2_1_attempt2_infrastructure.py tests/labels/test_acceptance_v2_1_infrastructure.py data/phase_2a/v2_1_attempt2
git commit -m "feat: materialize Phase 2A V2.1 Attempt 2 infrastructure"
```

**STOP condition:** any pin fails, any provider/network access occurs, output collides with Attempt 1, or the script would create final acceptance.

### Task 13: Verify, Report, Push Feature Branch, and Stop

**Files:**
- Create: `docs/reports/V5_2_PHASE_2A_V2_1_ATTEMPT_2_INFRASTRUCTURE.md`
- Do not modify: runtime semantics, Phase 1 artifacts, Attempt 1 artifacts, `origin/main`.

**Interfaces:**
- Consumes: committed Attempt 2 infrastructure and all verification outputs.
- Produces: a factual infrastructure report and a pushed `phase2a-implementation` feature HEAD.

- [ ] **Step 1: Run focused V2.1 tests**

```powershell
python -m pytest tests/labels/test_acceptance_v2_1_contracts.py tests/labels/test_acceptance_v2_1_boundaries.py tests/labels/test_acceptance_v2_1_layer_a.py tests/labels/test_acceptance_v2_1_layer_c.py tests/labels/test_acceptance_v2_1_gate_predicates.py tests/labels/test_acceptance_v2_1_firewall.py tests/labels/test_acceptance_v2_1_resolver.py tests/labels/test_acceptance_v2_1_infrastructure.py -q
```

Expected: PASS with exact test count recorded.

- [ ] **Step 2: Run Phase 2A and Phase 0-1C regressions**

```powershell
python -m pytest tests/labels -q
python -m pytest tests/data tests/refresh tests/providers -q
python -m pytest -q
```

Expected: all suites pass; record exact pass/skip counts and elapsed time.

- [ ] **Step 3: Run packaging, isolation, and clean-room gates**

```powershell
python scripts/verify_standalone.py
python scripts/clean_room_acceptance.py
python -m build
```

Install the produced wheel into a new temporary virtual environment and import the V2.1 contracts, predicates, and resolver. Record standalone, build, wheel smoke, zero-dependency, and clean-room outputs verbatim.

- [ ] **Step 4: Run security, AST, replay, tamper, and diff gates**

Run the repository credential sentinel, the V2.1 AST/import tests, deterministic materializer replay, tamper/revocation tests, count-preserving mutation suite, and:

```powershell
git diff --check
git diff --name-only a66825e25d40a46eceae18a50f1f2535ab9ee975 -- data/phase_2a/v2_infrastructure
```

Expected: no credential findings, no forbidden imports, replay byte equality, all negative tests pass, diff check clean, and no Attempt 1 artifact path changed.

- [ ] **Step 5: Write the infrastructure report**

The report must record all commands/results, seven new artifact IDs, supersession ID/reason, exact missing-bar base/lineage/transform IDs, exact unsupported-CA pins and repository exception, 16/16 predicate results under controlled infrastructure evaluation, count-preserving mutation results, engine-spy call counts, and:

```text
ATTEMPT 2 INFRASTRUCTURE = PASS / AWAITING INDEPENDENT REVIEW
FINAL V2.1 ACCEPTANCE = NOT RUN
PHASE 2A = FAIL / OPEN
READY FOR PHASE 2B = NO
PHASE 2B STARTED = NO
PROVIDER REQUESTS = 0
DATA NETWORK CALLS = 0
```

- [ ] **Step 6: Commit report and push only the feature branch**

```powershell
git add docs/reports/V5_2_PHASE_2A_V2_1_ATTEMPT_2_INFRASTRUCTURE.md
git commit -m "docs: record Phase 2A V2.1 Attempt 2 infrastructure"
git push origin phase2a-implementation
git fetch origin phase2a-implementation main
```

Verify local HEAD equals `origin/phase2a-implementation`, `origin/main` remains unchanged, and the worktree is clean. Do not create a PR or merge.

**STOP condition:** any verification fails, any prohibited path changed, final acceptance was created, or remote main moved due to this checkpoint.

## Dependency Order and TDD Boundary

```text
Task 1 provenance schemas
  -> Task 2 immutable supersession
  -> Task 3 missing-bar fixture
  -> Task 4 unsupported-CA repository boundary
  -> Task 5 Layer B V2.1 ledger
  -> Task 6 Layer A semantic roles
  -> Task 7 Layer C compatibility
  -> Task 8 literal 16-gate predicates
  -> Task 9 count-preserving mutation proof
  -> Task 10 provenance firewall
  -> Task 11 pure infrastructure resolver
  -> Task 12 immutable Attempt 2 materializer
  -> Task 13 verification/report/push/STOP
```

Each task uses RED, observed RED, minimal GREEN, focused verification, and its own commit. A failure matching any Global Constraint or task STOP condition stops execution before the next task.

## Hard STOP Conditions

Stop implementation immediately if any of the following occurs:

- the pinned unsupported-CA event, approval, manifest, audit, candidate bundle, or quarantine cannot be verified;
- `CorporateActionRepository.query` no longer rejects with `NOT_RESEARCH_SAFE: unsupported action type`;
- `REMOVE_FUTURE_BAR` mutates anything beyond the selected required future bar;
- correctness requires a Phase 1 semantic change, Label Engine semantic change, or Evidence Assembler runtime-semantic change;
- executable evaluation requires changing any frozen gate name or meaning;
- an Attempt 1 artifact would need overwrite, deletion, regeneration, or retrospective PASS;
- another provenance contradiction appears;
- a provider request or data network call would be required.

## Definition of Done for Attempt 2 Infrastructure Implementation

- Thirteen tasks committed in order with task-local RED/GREEN evidence.
- New V2.1 artifacts have new content identities and exact Attempt 1 supersession linkage.
- Missing bar is explicitly real base plus deterministic fixture and contributes zero real-observed failures.
- Unsupported CA is the pinned real quarantine and is rejected by the production repository contract before engine orchestration.
- All 16 gate predicates execute their literal semantics and pass count-preserving negative tests.
- Engine-zero safety is structurally demonstrated with raising/counting spies.
- Attempt 1 bytes and Phase 1/Label Engine behavior are unchanged.
- All verification gates pass and are recorded with exact counts.
- Final Phase 2A acceptance is not run, Phase 2B remains blocked, only the feature branch is pushed, and the worktree is clean.
