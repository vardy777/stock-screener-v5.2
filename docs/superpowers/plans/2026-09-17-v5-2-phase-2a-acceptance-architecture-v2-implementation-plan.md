# V5.2 Phase 2A Acceptance Architecture V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the frozen Phase 2A Acceptance Architecture V2 as three evidence layers, without changing the frozen label engine, Phase 1 truth, or Phase 2A label semantics.

**Architecture:** Layer A verifies production label calculations only on constructible five-domain real bundles. Layer B proves unsafe or incomplete evidence is rejected before engine invocation. Layer C verifies rare pure-calculation geometry with explicitly synthetic deterministic fixtures. Six immutable artifacts and a pure fail-closed resolver keep these layers separate and machine-verifiable.

**Tech Stack:** Python 3.11+, frozen V5.2 dataclass/content-hash conventions, pytest, existing Phase 1 immutable artifacts, existing Phase 2A contracts and reference engine.

**Frozen specification:** `docs/superpowers/specs/2026-09-17-v5-2-phase-2a-acceptance-architecture-v2-design.md` at `f92f0a564c802ddc28dc71153be44d409b6858ee`.

**Authorized provenance correction:** `CORRECTION TYPE = PROVENANCE_TYPO_CORRECTION`; `INCORRECT PLAN VALUE = 0ee799f9cfe30c29d43672245fccfc136338e930924f012469624026443c97247`; `AUTHORITATIVE VALUE = 0ee799a175a5e6832b9ca79d88ff9a0b9583ff92e204849274f96a031c397247`; `AUTHORITY = Checkpoint 7 immutable comparison ledger and V5_2_PHASE_2A_ACCEPTANCE.md`; `ARCHITECTURE CHANGED = NO`; `IMPLEMENTATION SEMANTICS CHANGED = NO`; `ACCEPTANCE CRITERIA CHANGED = NO`.

## Global Constraints

- Work only on `phase2a-implementation`; never update `main`, open a PR, merge, rebase, or squash.
- Checkpoint 11 implements acceptance infrastructure only. It must not fresh-run final V2 acceptance or emit a production `Phase2AAcceptanceV2` artifact.
- Do not modify `DomainLineageV1`, `LabelInputBundleV1`, `AnchorKnowledgeBoundary`, `LabelReferencePrice`, `LabelState`, `ReferenceLabelEngine`, Phase 1 artifacts, frozen sample semantics, or the 22-slot V1 history.
- No provider/network calls, artifact regeneration, current/latest database lookup, synthetic market facts, or synthetic Phase 1 lineage.
- Every new artifact is immutable, canonically serialized, content-hashed, versioned, and verified before consumption.
- Every resolver/evaluator fails closed for missing, duplicate, mismatched, revoked, superseded, tampered, or unpinned inputs.
- Layer A, B, and C counts remain separate. There is no combined `total_samples` acceptance metric.
- Commit after every task only when its RED-to-GREEN evidence is recorded. Stop immediately on a frozen-contract contradiction.

## Current Rejection-Contract Inventory

This inventory is implementation input, not a redesign opportunity. Task 1 must encode these exact current boundaries before other work begins.

| Semantic category | Current implementation path and boundary | Exact current code/type/message | Existing behavior test | V2 harness/adapter | Production behavior change |
|---|---|---|---|---|---|
| `UNEXPLAINED_MISSING_BAR` | `src/v5_2/data/label_evidence_assembler.py`, `Phase2AEvidenceAssemblerV1.assemble` | `EvidenceAssemblyError("UNEXPLAINED_MISSING_BAR:<date>")` or `...:ANCHOR` | `test_evidence_assembler.py::test_missing_bar_without_suspension_fails_but_proven_suspension_passes` | Real approved-boundary Layer B wrapper; structural engine-zero proof | NO |
| `UNSUPPORTED_CA` | `src/v5_2/labels/calculation.py`, `build_economic_wealth_path` | `UnsafeLabelInput(LabelReasonCode.UNSUPPORTED_CORPORATE_ACTION)` | `test_wealth_path.py::test_unsupported_action_fails_closed` | Minimal acceptance-only pre-engine adapter using the same supported-action predicate/reason and real machine-visible unsupported interval | NO to production; YES to acceptance harness only |
| `REVOKED_APPROVAL` | assembler `_validate_governance` / injected seam | `EvidenceAssemblyError("REVOKED_APPROVAL")` | parametrized `test_evidence_assembler.py::test_integrity_and_role_faults_fail_closed[REVOKED_APPROVAL]` | Deterministic governance fixture pinned to real schema | NO |
| `TAMPERED_ARTIFACT` / hash mismatch | assembler `_bars` hash verification / injected seam | `EvidenceAssemblyError("TAMPERED_ARTIFACT")`; there is no separate public `HASH_MISMATCH` code | parametrized `test_evidence_assembler.py::test_integrity_and_role_faults_fail_closed[TAMPERED_ARTIFACT]` | Deterministic integrity fixture; retain existing taxonomy | NO |
| `MISSING_REQUIRED_DOMAIN` | assembler `forbidden_domain` validation | `EvidenceAssemblyError("MISSING_DOMAIN:<domain>")` | parametrized `test_evidence_assembler.py::test_each_missing_domain_fails_closed` | Deterministic five-domain omission fixture | NO |
| `AMBIGUOUS_IDENTITY` | assembler membership validation / injected seam | `EvidenceAssemblyError("IDENTITY_AMBIGUITY")` | parametrized `test_evidence_assembler.py::test_integrity_and_role_faults_fail_closed[IDENTITY_AMBIGUITY]` | Real ambiguity evidence when available, otherwise deterministic contract fixture; never silently resolve | NO |
| `MALFORMED_CALENDAR` | assembler `_load_calendar`, anchor/window validation | `MALFORMED_CALENDAR:<exchange>`, `...:ANCHOR_ABSENT`, or `...:WINDOW_INCOMPLETE` | parametrized `test_evidence_assembler.py::test_integrity_and_role_faults_fail_closed[MALFORMED_CALENDAR]` | Deterministic malformed-calendar fixture with one pinned exact variant | NO |
| `INVALID_LINEAGE` | `src/v5_2/labels/contracts.py`, `LabelInputBundleV1.create` | `ValueError("invalid domain lineage")` | `test_contracts.py::test_domain_lineage_is_role_specific_and_deterministic`; Task 1 adds exact constructor-message characterization | Constructor-rejection fixture; never mutate an approved bundle | NO |
| `ROLE_SWAP` | assembler injected seam; constructor also enforces ordered five domains | `EvidenceAssemblyError("ROLE_SWAP")` at chosen boundary | parametrized `test_evidence_assembler.py::test_integrity_and_role_faults_fail_closed[ROLE_SWAP]` | Deterministic role-swap fixture pinned to assembler boundary | NO |
| `DUPLICATE_DOMAIN` | assembler injected seam; constructor also enforces ordered five domains | `EvidenceAssemblyError("DUPLICATE_DOMAIN")` at chosen boundary | parametrized `test_evidence_assembler.py::test_integrity_and_role_faults_fail_closed[DUPLICATE_DOMAIN]` | Deterministic duplicate-domain fixture pinned to assembler boundary | NO |

`UNSUPPORTED_CA_BOUNDARY_GAP = NO`, subject to one mandatory implementation proof: the acceptance-only adapter must combine real machine-visible Phase 1 unsupported scope/interval evidence with a deterministic contract fixture and must reject before the engine. It may not approve unsupported facts, modify Phase 1 scope, or alter production calculation semantics. If that proof cannot be implemented without changing frozen semantics, Task 5 stops with `UNSUPPORTED_CA_BOUNDARY_GAP` and no later task runs.

## Frozen Artifact Families

Only these six top-level V2 artifact families may be added:

1. `Phase2AAcceptanceArchitectureAmendmentV2`
2. `RealReferenceCoverageLedgerV2`
3. `FailClosedBoundaryLedgerV2`
4. `CalculationEdgeFixtureLedgerV2`
5. `GateArtifactConsumptionMapV2`
6. `Phase2AAcceptanceV2`

Supporting code is limited to necessary enums/classification, canonical hashing, the boundary harness, independent edge calculator, firewall validation, and pure resolver. Do not add a registry, orchestration framework, policy family, scheduler, provider, or new sample inventory.

## Planned File Layout

Runtime modules:

- `src/v5_2/labels/acceptance_v2_contracts.py`
- `src/v5_2/labels/acceptance_v2_layer_a.py`
- `src/v5_2/labels/acceptance_v2_boundaries.py`
- `src/v5_2/labels/acceptance_v2_layer_c.py`
- `src/v5_2/labels/independent_edge_reference.py`
- `src/v5_2/labels/acceptance_v2_resolver.py`

Infrastructure materialization and report:

- `scripts/build_phase2a_acceptance_v2_infrastructure.py`
- `docs/reports/V5_2_PHASE_2A_V2_INFRASTRUCTURE_ACCEPTANCE.md`

Tests:

- `tests/labels/test_acceptance_v2_rejection_inventory.py`
- `tests/labels/test_acceptance_v2_contracts.py`
- `tests/labels/test_acceptance_v2_amendment.py`
- `tests/labels/test_acceptance_v2_layer_a.py`
- `tests/labels/test_acceptance_v2_boundaries.py`
- `tests/labels/test_acceptance_v2_layer_b.py`
- `tests/labels/test_acceptance_v2_layer_c.py`
- `tests/labels/test_independent_edge_reference.py`
- `tests/labels/test_acceptance_v2_firewall.py`
- `tests/labels/test_acceptance_v2_gate_map.py`
- `tests/labels/test_acceptance_v2_resolver.py`
- `tests/labels/test_acceptance_v2_infrastructure.py`

## Task 1: Freeze the Existing Rejection Contract

**Files**

- Create: `tests/labels/test_acceptance_v2_rejection_inventory.py`
- Modify: `docs/reports/V5_2_PHASE_2A_V2_INFRASTRUCTURE_ACCEPTANCE.md`
- Read only: existing assembler, calculation, contracts, and their tests

**Interface:** A literal test table of the ten categories above, their enforcement point, exact exception type/reason, and engine eligibility.

- [ ] Write RED characterization tests that assert exact exception types/messages for all ten categories. For unsupported CA, assert the existing calculation boundary only; do not yet claim pre-engine rejection.
- [ ] Run:

```powershell
python -m pytest tests/labels/test_acceptance_v2_rejection_inventory.py -q
```

Expected RED: the new inventory/report hooks do not exist; any drift in exact current reasons is exposed.

- [ ] Add only test helpers/report inventory needed to characterize current behavior. Strengthen generic existing exception assertions where necessary; do not modify runtime semantics.
- [ ] Re-run the focused test; expected GREEN with ten exact, named categories.
- [ ] Commit:

```powershell
git add tests/labels/test_acceptance_v2_rejection_inventory.py docs/reports/V5_2_PHASE_2A_V2_INFRASTRUCTURE_ACCEPTANCE.md
git commit -m "test: freeze Phase 2A V2 rejection contracts"
```

**STOP:** Any current boundary differs materially from the table, or unsupported CA cannot be tied to the frozen Phase 1 unsupported scope.

## Task 2: Implement the Six V2 Artifact Schemas

**Files**

- Create: `src/v5_2/labels/acceptance_v2_contracts.py`
- Create: `tests/labels/test_acceptance_v2_contracts.py`

**Interfaces:** Frozen dataclasses for the six artifact families plus:

```python
class EvidenceClass(str, Enum):
    REAL_MARKET_EVIDENCE = "REAL_MARKET_EVIDENCE"
    REAL_APPROVED_BOUNDARY_CONDITION = "REAL_APPROVED_BOUNDARY_CONDITION"
    REAL_MACHINE_VISIBLE_UNSUPPORTED_CONDITION = "REAL_MACHINE_VISIBLE_UNSUPPORTED_CONDITION"
    DETERMINISTIC_CONTRACT_FIXTURE = "DETERMINISTIC_CONTRACT_FIXTURE"
    SYNTHETIC_CONTRACT_FIXTURE = "SYNTHETIC_CONTRACT_FIXTURE"
```

- [ ] Write RED tests for canonical field ordering, schema version, content hash, round-trip verification, duplicate IDs, mutation/tamper rejection, and invalid evidence-class/layer combinations.
- [ ] Run `python -m pytest tests/labels/test_acceptance_v2_contracts.py -q`; expected RED on missing module.
- [ ] Implement minimal frozen dataclasses using repository canonical serialization/hash conventions. Constructors validate all invariants and recompute hashes; no mutable defaults or ambient lookup.
- [ ] Re-run focused tests; expected GREEN.
- [ ] Commit: `git commit -m "feat: add Phase 2A V2 acceptance artifacts"`.

**STOP:** A schema would require changing a frozen Phase 2A or Phase 1 contract.

## Task 3: Encode the V1-to-V2 Amendment and Literal 22-Slot Migration

**Files**

- Create: `tests/labels/test_acceptance_v2_amendment.py`
- Modify: `src/v5_2/labels/acceptance_v2_contracts.py`

**Interface:** `Phase2AAcceptanceArchitectureAmendmentV2.create(...)` pins the V1 design/plan/Checkpoint 7/8/9 IDs, the V2 design commit, and a literal ordered 22-slot migration tuple.

- [ ] Write RED tests proving slots 1-15 and 18-22 map to Layer A, slot 16 maps to Layer B `UNEXPLAINED_MISSING_BAR`, slot 17 maps to Layer B `UNSUPPORTED_CA`, and slot 22 additionally maps to Layer C only for its rare pure geometry. Assert no deletion, renumbering, or reinterpretation of V1 history.
- [ ] Run the amendment test; expected RED because creation/migration verification is absent.
- [ ] Implement the immutable amendment with exact provenance IDs and reject any non-literal, incomplete, duplicated, or reordered mapping.
- [ ] Re-run; expected GREEN.
- [ ] Commit: `git commit -m "feat: encode Phase 2A V2 amendment provenance"`.

**STOP:** The frozen 22-slot identity cannot be preserved exactly.

## Task 4: Build Layer A Real Reference Coverage

**Files**

- Create: `src/v5_2/labels/acceptance_v2_layer_a.py`
- Create: `tests/labels/test_acceptance_v2_layer_a.py`

**Interfaces:**

```python
def build_real_reference_coverage_ledger(
    amendment: Phase2AAcceptanceArchitectureAmendmentV2,
    checkpoint7_comparison_ledger: object,
    bundles: tuple[LabelInputBundleV1, ...],
) -> RealReferenceCoverageLedgerV2: ...
```

Safe reuse is limited to immutable Checkpoint 7 inputs and results whose IDs and hashes still verify: the 20 retained constructed bundles, their production results, independent results, field-level comparisons, and exact five-domain lineage. V2 must fresh-materialize the classification/migration records and `RealReferenceCoverageLedgerV2` wrapper because those artifacts did not exist under V1. It must not recompute market facts, rewrite the Checkpoint 7 comparison ledger, or infer V2 PASS merely because a V1 artifact exists. Slots whose registered strata were untruthful remain recorded in amendment provenance; the retained Layer A case description uses actual observed behavior only.

- [ ] Write RED tests requiring exactly the 20 retained real slots, `REAL_MARKET_EVIDENCE`, exact five-domain lineage, comparison ledger ID `0ee799a175a5e6832b9ca79d88ff9a0b9583ff92e204849274f96a031c397247`, truthful barrier roles, and zero mismatch. Reject slots 16/17, synthetic evidence, incomplete lineage, revoked/superseded inputs, or a mismatch.
- [ ] Run `python -m pytest tests/labels/test_acceptance_v2_layer_a.py -q`; expected RED.
- [ ] Implement a pure builder that consumes already verified Checkpoint 7 artifacts; it does not rerun acquisition or silently manufacture missing barrier coverage.
- [ ] Re-run; expected GREEN.
- [ ] Commit: `git commit -m "feat: build Phase 2A V2 real reference ledger"`.

**STOP:** A retained slot is not backed by exact approved five-domain lineage or the Checkpoint 7 comparison.

## Task 5: Implement the Minimal Pre-Engine Boundary Harness

**Files**

- Create: `src/v5_2/labels/acceptance_v2_boundaries.py`
- Create: `tests/labels/test_acceptance_v2_boundaries.py`

**Interfaces:**

```python
def execute_boundary_case(case: BoundaryCaseV2) -> BoundaryExecutionV2: ...
```

`BoundaryExecutionV2` records evidence class, exact rejection layer/reason, assembler invocation count, engine invocation count, and verified input IDs.

- [ ] Write RED tests proving a rejected case structurally cannot call `ReferenceLabelEngine`; use a raising/counting engine spy rather than trusting a reported integer.
- [ ] Add RED tests for unsupported CA using real machine-visible Phase 1 unsupported type/interval evidence plus a deterministic action fixture. Expected reason is exactly `UNSUPPORTED_CORPORATE_ACTION`, and engine count is zero.
- [ ] Run `python -m pytest tests/labels/test_acceptance_v2_boundaries.py -q`; expected RED.
- [ ] Implement only a boundary adapter. It reuses the exact frozen supported-action predicate/reason, preflights the unsupported action, prevents assembler/engine continuation after rejection, and never publishes the fixture as a market fact.
- [ ] Re-run; expected GREEN and structural engine-zero proof.
- [ ] Commit: `git commit -m "feat: add Phase 2A fail-closed boundary harness"`.

**STOP:** If unsupported CA pre-engine rejection requires modifying Phase 1 approval scope, approved facts, the label engine, or calculation semantics, record `UNSUPPORTED_CA_BOUNDARY_GAP` and stop Checkpoint 11.

## Task 6: Build the Layer B Fail-Closed Ledger

**Files**

- Create: `tests/labels/test_acceptance_v2_layer_b.py`
- Modify: `src/v5_2/labels/acceptance_v2_boundaries.py`

**Interface:** A literal, ordered ten-case builder returning `FailClosedBoundaryLedgerV2`; no discovery or registry.

The planned evidence classification is literal:

| Layer B case | Evidence class |
|---|---|
| unexplained future bar missing | `REAL_APPROVED_BOUNDARY_CONDITION` |
| unsupported corporate action | `REAL_MACHINE_VISIBLE_UNSUPPORTED_CONDITION` plus a separately identified `DETERMINISTIC_CONTRACT_FIXTURE` only to exercise the frozen boundary |
| revoked approval | `DETERMINISTIC_CONTRACT_FIXTURE` pinned to the real approval schema |
| tampered artifact/hash mismatch | `DETERMINISTIC_CONTRACT_FIXTURE` |
| missing required domain | `DETERMINISTIC_CONTRACT_FIXTURE` |
| ambiguous identity | `REAL_APPROVED_BOUNDARY_CONDITION` when the pinned ambiguity evidence exists; otherwise `DETERMINISTIC_CONTRACT_FIXTURE`, never a fabricated market identity |
| malformed calendar | `DETERMINISTIC_CONTRACT_FIXTURE` |
| invalid lineage | `DETERMINISTIC_CONTRACT_FIXTURE` |
| role swap | `DETERMINISTIC_CONTRACT_FIXTURE` |
| duplicate domain | `DETERMINISTIC_CONTRACT_FIXTURE` |

- [ ] Write RED tests requiring exactly: unexplained missing bar, unsupported CA, revoked approval, tampered artifact, missing required domain, ambiguous identity, malformed calendar, invalid lineage, role swap, duplicate domain.
- [ ] Require appropriate evidence classes, exact rejection reasons, verified source IDs, and `engine_invocation_count == 0` for every entry. A missing, duplicate, extra, or engine-called entry fails.
- [ ] Run the Layer B tests; expected RED.
- [ ] Implement the literal builder using Task 5 harness and existing injected seams. If assembler unexpectedly constructs a supposedly rejected case, mark the infrastructure run failed and do not call the engine.
- [ ] Re-run; expected GREEN.
- [ ] Commit: `git commit -m "feat: build Phase 2A V2 fail-closed ledger"`.

**STOP:** Any category can reach the engine or relies only on a self-reported zero count.

## Task 7: Freeze the Four Layer C Calculation Fixtures

**Files**

- Create: `src/v5_2/labels/acceptance_v2_layer_c.py`
- Create: `tests/labels/test_acceptance_v2_layer_c.py`

**Interface:** Literal fixture constructors for `UPPER_FIRST`, `LOWER_FIRST`, `NEITHER`, and `SAME_SESSION_BARRIER_AMBIGUITY`.

- [ ] Write RED tests requiring exactly four immutable fixtures, pre-calculation frozen IDs/hashes, `SYNTHETIC_CONTRACT_FIXTURE`, explicit prices/sessions/actions, and no Phase 1 lineage claim.
- [ ] Run the Layer C test; expected RED.
- [ ] Implement deterministic literal fixtures and `CalculationEdgeFixtureLedgerV2` construction. No random data, market symbol impersonation, or reuse in Layer A.
- [ ] Re-run; expected GREEN.
- [ ] Commit: `git commit -m "feat: freeze Phase 2A calculation edge fixtures"`.

**STOP:** Any fixture identity depends on a computed production result or claims real-market evidence.

## Task 8: Add the Independent Layer C Calculator and Comparison

**Files**

- Create: `src/v5_2/labels/independent_edge_reference.py`
- Create: `tests/labels/test_independent_edge_reference.py`
- Modify: `src/v5_2/labels/acceptance_v2_layer_c.py`

**Interface:**

```python
def calculate_independent_edge_result(fixture: CalculationEdgeFixtureV2) -> EdgeResultV2: ...
def compare_edge_results(independent: EdgeResultV2, production: EdgeResultV2) -> EdgeComparisonV2: ...
```

- [ ] Write RED tests for all four outcomes and mutation tests on decisive session, outcome, return, MFE, and MAE. Add an AST/import test forbidding imports/calls to `ReferenceLabelEngine`, production calculation functions, or Layer C production helpers from the independent module.
- [ ] Run focused tests; expected RED.
- [ ] Implement the smallest independent arithmetic/state walk from fixture primitives. Production results are computed separately and compared field-by-field.
- [ ] Re-run; expected GREEN with four matches and mutation detection.
- [ ] Commit: `git commit -m "feat: add independent Phase 2A edge calculator"`.

**STOP:** Independence requires calling or copying a production helper rather than independently expressing the frozen math.

## Task 9: Enforce the Synthetic Evidence Firewall

**Files**

- Create: `tests/labels/test_acceptance_v2_firewall.py`
- Modify: `src/v5_2/labels/acceptance_v2_contracts.py`

**Interface:** Artifact constructors expose separate counters only:

```text
real_reference_cases
real_fail_closed_evidence_cases
synthetic_contract_fixtures
```

- [ ] Write RED tests proving synthetic evidence cannot enter Layer A, increment a real count, or claim Phase 1 lineage; real evidence mislabeled synthetic is rejected or produces an explicit classification mismatch. Assert no `total_samples` field/property exists.
- [ ] Run the firewall tests; expected RED.
- [ ] Implement constructor-level classification invariants and cross-ledger disjointness checks; do not add a runtime registry.
- [ ] Re-run; expected GREEN.
- [ ] Commit: `git commit -m "feat: enforce Phase 2A synthetic evidence firewall"`.

**STOP:** Any aggregate count can make synthetic coverage satisfy a real-evidence gate.

## Task 10: Encode the Literal 16-Gate Consumption Map

**Files**

- Create: `tests/labels/test_acceptance_v2_gate_map.py`
- Modify: `src/v5_2/labels/acceptance_v2_contracts.py`

**Interface:** `GateArtifactConsumptionMapV2` contains exactly the 16 original frozen gate names and explicit primary/supporting artifact IDs for each.

The implementation must encode this literal consumption contract. In every row, missing required artifacts or hash/provenance tampering is an immediate FAIL; no resolver may substitute a latest artifact.

| Frozen gate | Input artifacts and coverage predicate | Resolver / PASS rule | Explicit FAIL rule |
|---|---|---|---|
| `LABEL CONTRACT` | Amendment plus Layer A exact frozen contract, seven canonical labels, and five-domain bundles | Contract verifier; every pin and A bundle verifies | Drift, missing label/domain, wrong version, missing artifact, tamper |
| `CAUSAL ISOLATION` | Layer B harness evidence plus AST/import evidence | Isolation predicate; no provider/current/network access and rejected cases never reach engine | Forbidden dependency, engine invocation, missing isolation evidence, tamper |
| `TRADING SESSION SEMANTICS` | Layer A real calendar/horizon cases | A coverage resolver; H1/H3/H5 match pinned ordered exchange sessions | Sort/repair/drift, missing coverage, mismatch, tamper |
| `RETURN SEMANTICS` | Layer A real positive, negative, CA, and suspension paths | All mandatory return comparisons match | Missing semantic coverage or field mismatch |
| `MFE/MAE SEMANTICS` | Layer A volatile/trading/suspension paths | All extrema comparisons match | Missing coverage or MFE/MAE mismatch |
| `BARRIER SEMANTICS` | Layer C four-edge ledger plus truthful Layer A real outcomes | All four synthetic edge comparisons pass and A outcomes retain real classification | Missing edge, comparison mismatch, or synthetic-as-real |
| `CORPORATE ACTION SAFETY` | Layer A cash/bonus cases plus Layer B unsupported-CA rejection | Both supported calculation and unsupported pre-engine rejection coverage pass | Either half missing, unsafe, mismatched, or engine invoked for unsupported CA |
| `SUSPENSION SAFETY` | Layer A real carry/resumption and anchor-suspension cases | Carry and engine-level unsafe behavior match independent evidence | Synthetic bar/carry, missing case, mismatch, tamper |
| `DELISTING SAFETY` | Layer A real delisting-horizon case | Frozen unsafe state/reason matches | Fabricated return/carry, missing case, mismatch |
| `IDENTITY SAFETY` | Layer A real transition plus Layer B ambiguity/role/lineage rejections | Transition resolves and all invalid identity/lineage cases reject pre-engine | Ambiguity silently resolves, rejection absent, wrong role accepted |
| `MISSING DATA FAIL-CLOSED` | Layer B unexplained bar, missing domain, malformed calendar, and tamper cases | Exact rejection codes, no bundle/result, structural engine-zero proof | Engine called, code mismatch, case absent, fixture misclassified |
| `LABEL_PENDING` | Layer A real incomplete latest horizon | Exact pending state/reason matches independent result | Future completion fabricated, missing case, mismatch |
| `NOT_LABEL_SAFE` | Layer A legal-bundle unsafe cases only | Required engine-level unsafe states/reasons match | Assembler rejection counted as label state, case missing, mismatch |
| `REFERENCE SAMPLES` | Layer A explicit mandatory real semantic set | Every required Layer A semantic has valid real evidence and comparison | Missing real coverage, invalid provenance, synthetic fixture credited |
| `INDEPENDENT VERIFICATION` | Layer A and Layer C independent implementations and comparison ledgers | All required comparisons match and import-independence checks pass | Import/call violation, mismatch, incomplete ledger |
| `DETERMINISTIC REPLAY` | Amendment, all three ledgers, gate map, resolver test output | Identical pinned inputs yield byte-identical artifacts and decision | Any identity/output drift, missing pin, invalid provenance |

The map stores exact artifact IDs supplied at construction. Coverage predicates are named literal predicates implemented beside the pure resolver, not arbitrary strings or dynamically loaded callbacks. Every row uses the common fail-closed missing/tamper verifier before its gate-specific resolver.

- [ ] Write RED tests comparing an exact ordered 16-name tuple, rejecting a 17th gate, omissions, aliases, or duplicate names. Map calculation/real-reference gates primarily to Layer A, rejection/governance boundaries to Layer B, rare geometry to Layer C, and corporate-action acceptance to both Layer A supported paths and Layer B unsupported boundary proof.
- [ ] Run focused test; expected RED.
- [ ] Implement the literal map and validate every referenced artifact hash/classification.
- [ ] Re-run; expected GREEN.
- [ ] Commit: `git commit -m "feat: map Phase 2A gates to V2 artifacts"`.

**STOP:** A gate is renamed, weakened, inferred dynamically, or satisfied by the wrong evidence class.

## Task 11: Implement the Pure Fail-Closed V2 Resolver

**Files**

- Create: `src/v5_2/labels/acceptance_v2_resolver.py`
- Create: `tests/labels/test_acceptance_v2_resolver.py`

**Interface:**

```python
def resolve_phase2a_acceptance_v2(
    *,
    amendment: Phase2AAcceptanceArchitectureAmendmentV2,
    real_reference: RealReferenceCoverageLedgerV2,
    fail_closed: FailClosedBoundaryLedgerV2,
    edge_fixtures: CalculationEdgeFixtureLedgerV2,
    gate_map: GateArtifactConsumptionMapV2,
) -> Phase2AAcceptanceV2: ...
```

- [ ] Write RED tests for deterministic PASS construction from explicit verified in-memory artifacts and fail-closed results for missing, tampered, mismatched provenance, wrong evidence class, incomplete gate map, Layer B engine invocation, Layer C mismatch, or Layer A mismatch.
- [ ] Add source/AST tests forbidding paths, network/provider access, environment reads, current/latest database lookup, global artifact discovery, and wall-clock identity fields.
- [ ] Run focused test; expected RED.
- [ ] Implement a pure resolver that consumes only its arguments, verifies every hash/provenance edge, and produces a deterministic artifact. Do not call it with production artifacts in Checkpoint 11.
- [ ] Re-run; expected GREEN using test fixtures only.
- [ ] Commit: `git commit -m "feat: add pure Phase 2A V2 acceptance resolver"`.

**STOP:** Resolver output depends on ambient state or Checkpoint 11 would fresh-run final acceptance.

## Task 12: Materialize Checkpoint 11 Infrastructure Only

**Files**

- Create: `scripts/build_phase2a_acceptance_v2_infrastructure.py`
- Create: `tests/labels/test_acceptance_v2_infrastructure.py`
- Modify: `docs/reports/V5_2_PHASE_2A_V2_INFRASTRUCTURE_ACCEPTANCE.md`

**Interface:** Offline script materializes only the amendment, Layer A ledger, Layer B ledger, Layer C fixture ledger, gate map, and fixture inventory. It explicitly excludes final `Phase2AAcceptanceV2` production output.

- [ ] Write RED tests for exact output set, deterministic double-run byte identity, zero provider/network calls, no final acceptance artifact, no Phase 2B output, and fixed status fields.
- [ ] Required report state:

```text
CHECKPOINT 11 = INFRASTRUCTURE IMPLEMENTED / AWAITING REVIEW
FINAL V2 ACCEPTANCE = NOT RUN
PHASE 2A = FAIL / OPEN
READY FOR PHASE 2B = NO
PHASE 2B STARTED = NO
```

- [ ] Run focused tests; expected RED.
- [ ] Implement the bounded offline materializer and report. Pin all input IDs and emit content hashes; do not invoke final resolver in production mode.
- [ ] Run twice into isolated temporary output roots and byte-compare; expected GREEN.
- [ ] Commit: `git commit -m "feat: materialize Phase 2A V2 acceptance infrastructure"`.

**STOP:** The script attempts final acceptance, changes Phase 1/frozen runtime artifacts, or emits any readiness claim.

## Task 13: Verify, Report, Push Feature Branch, and Stop

**Files**

- Modify: `docs/reports/V5_2_PHASE_2A_V2_INFRASTRUCTURE_ACCEPTANCE.md`

- [ ] Record every exact command, exit code, test count, artifact ID/hash, Layer A/B/C counts, engine-zero structural proof, firewall result, gate-map result, and deterministic replay hash.
- [ ] Run focused V2 tests:

```powershell
python -m pytest tests/labels/test_acceptance_v2_*.py tests/labels/test_independent_edge_reference.py -q
```

- [ ] Run existing Phase 2A label tests, Phase 1 Status/Daily Bar lineage regressions, Phase 0-1C regression, and full pytest using the repository's documented commands.
- [ ] Run clean-room install/test, standalone, build/wheel install-smoke, zero-project-dependency, credential scan, AST/independence checks, and `git diff --check`.
- [ ] Run infrastructure materialization twice and verify byte-identical artifacts.
- [ ] Prove frozen runtime/data evidence was not modified by comparing against the Checkpoint 10 base commit.
- [ ] Update the report with truthful PASS/FAIL evidence while retaining:

```text
FINAL V2 ACCEPTANCE = NOT RUN
PHASE 2A = FAIL / OPEN
READY FOR PHASE 2B = NO
PHASE 2B STARTED = NO
```

- [ ] Commit verification evidence: `git commit -m "docs: record Phase 2A V2 infrastructure acceptance"`.
- [ ] Push only `phase2a-implementation`, confirm local HEAD equals remote feature HEAD, confirm `origin/main` is unchanged, and confirm clean worktree.
- [ ] STOP. Do not run final V2 acceptance, resume Phase 2B, create a PR, or merge.

## Dependency Order and Checkpoint 11 Boundary

The task order is strict:

```text
1 rejection inventory
→ 2 schemas
→ 3 amendment/migration
→ 4 Layer A
→ 5 boundary harness
→ 6 Layer B
→ 7 Layer C fixtures
→ 8 independent calculator
→ 9 synthetic firewall
→ 10 gate map
→ 11 pure resolver
→ 12 infrastructure materialization
→ 13 verification/push/STOP
```

Checkpoint 11 may prove that the infrastructure *could* compute final acceptance from a complete verified artifact set in unit tests. It must not execute that resolution against the production acceptance set or claim Phase 2A PASS. Independent review of Checkpoint 11 is required before a separately authorized final V2 acceptance run.

## Definition of Done for This Implementation Plan

- All six artifact families are specified and no seventh top-level family is introduced.
- The literal V1-to-V2 migration retains all 22 historical slot identities.
- Layer A uses only constructible real five-domain bundles.
- Layer B proves ten rejections before engine invocation, including unsupported CA through the minimal acceptance-only adapter.
- Layer C uses exactly four explicitly synthetic, pre-frozen calculation fixtures and an independent calculator.
- The synthetic firewall prevents cross-layer credit or aggregate-count inflation.
- The exact original 16 gates are mapped to explicit artifact consumers.
- The resolver is pure, deterministic, explicit-input-only, and fail closed.
- Checkpoint 11 ends with final V2 acceptance not run, Phase 2A open, and Phase 2B blocked.
