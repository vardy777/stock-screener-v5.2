# V5.2 Phase 2A Acceptance Architecture V2 Design Amendment

Date: 2026-09-17  
Status: DESIGN FROZEN FOR INDEPENDENT REVIEW  
Implementation status: NOT AUTHORIZED  
Branch baseline: `phase2a-implementation@7f89ee734ffd8d72d977fd352129e0c8acd9a134`

## Problem Statement

Acceptance Architecture V1 coupled every required semantic to one successful,
approved `LabelInputBundleV1`. That is invalid for evidence conditions whose
correct behavior is rejection before a bundle exists. In particular,
`FUTURE_BAR_MISSING` requires an exchange-open outcome session with no approved
bar, no suspension, no delisting explanation, and valid identity, while the
approved Phase 1 assembler must reject that condition as
`UNEXPLAINED_MISSING_BAR` before engine invocation.

The V1 architecture also treated rare calculation geometry as if every edge
case needed a preselected real-market sample. This conflated three distinct
questions: whether valid real inputs are calculated correctly, whether invalid
evidence is rejected at the correct boundary, and whether pure calculation
functions handle exact mathematical edge cases.

V2 separates those responsibilities without changing label semantics, Phase 1
data, provider data, or any historical conclusion.

## Evidence From Checkpoints 7 and 8

The following immutable evidence remains authoritative:

- V1 inventory: `81bd6df1955b9e18831779bd7274947f7da6dca50d5554f94cf7d85da31ac1c9`.
- Checkpoint 7 FAIL acceptance: `84d61057ecf5f527dcb5067fe0ea2b6103edf0f66388535e8ceeffd3ef10c3c8`.
- Checkpoint 8 applicability audit: `236039b2286afaff54017317ceeedc08b8e4c40a5a94a676256167c85d96f4d4`.
- Checkpoint 8 discovery STOP: `947a8cd54a0a9a9bf91a8a4b45e7b502c272fb8dff374eab19b99615fca98f48`.

Checkpoint 7 established 22 constructed bundles, 22 production calculations,
22 independent calculations, 22 field-level matches, and zero mismatches. It
also established that V1 slots 16, 17, 20, 21, and 22 did not truthfully match
their registered strata. Checkpoint 8 established that slot 16 cannot be
repaired by selecting another successful approved bundle.

Checkpoint 7 remains FAIL under V1. V2 never retrospectively changes it.

## Why V1 Cannot Be Repaired By Sample Replacement

V1 assumes that every acceptance case has this shape:

```text
approved evidence -> successful five-domain bundle -> engine -> LabelResult
```

Some mandatory safety cases have this correct shape instead:

```text
invalid or incomplete evidence -> assembler/contract rejection -> no bundle
                                                      -> engine invocation = 0
```

Replacing slot 16 cannot reconcile those shapes. Allowing the invalid evidence
through would weaken Phase 1 correctness. Inventing a synthetic bar or a false
suspension would corrupt evidence. Describing an assembler rejection as an
engine `EXPECTED_BAR_MISSING` result would fabricate a `LabelResult` that never
existed. The architecture, not the data or engine, must therefore be superseded.

## Architecture Decision

Phase 2A Acceptance Architecture V2 has four coordinated scopes:

```text
Layer A: Real Bundle Reference Acceptance
Layer B: Fail-Closed Boundary Acceptance
Layer C: Calculation Edge-Case Acceptance
Cross-layer: provenance, replay, classification, and final gate resolution
```

There is no fixed total-sample gate. Each layer declares an explicit mandatory
semantic coverage set. The original 16 gate names remain unchanged and consume
the layer artifacts through a versioned gate-to-artifact map.

## Layer A Contract — Real Bundle Reference Acceptance

Layer A answers: given legal, real, point-in-time-safe Phase 1 evidence, does the
reference engine calculate the frozen labels correctly?

Every Layer A case requires:

1. `evidence_class = REAL_MARKET_EVIDENCE`;
2. a successfully constructed `LabelInputBundleV1`;
3. exact, immutable Calendar, Master/Identity, Daily Bar, Status, and Corporate
   Action lineage;
4. a production result;
5. an independently implemented result;
6. field-level immutable comparison evidence, including states, reasons,
   numeric values, barrier categorical outcomes, decisive sessions, and lineage;
7. deterministic replay.

Mandatory Layer A coverage is semantic, not numeric:

- positive and negative ordinary returns;
- volatile paths and real limit-like paths;
- cash dividend and bonus-share wealth arithmetic;
- proven full-day suspension carry and resumption behavior;
- fully explained anchor suspension producing engine-level `NOT_LABEL_SAFE`;
- delisting horizon producing engine-level `NOT_LABEL_SAFE`;
- canonical identity transition;
- latest-session `LABEL_PENDING`;
- real `UPPER_FIRST`, `LOWER_FIRST`, and `NEITHER` outcomes when present;
- real same-session ambiguity when present and fully proven;
- IPO/seasoning boundaries represented by complete legal bundles.

Assembler rejection cases, incomplete domains, revoked approvals, tampered
evidence, unexplained bar absence, and unsupported corporate-action conditions
cannot satisfy Layer A.

## Layer B Contract — Fail-Closed Boundary Acceptance

Layer B answers: does invalid, incomplete, revoked, tampered, role-invalid, or
unsupported evidence fail at its frozen boundary without invoking the engine?

Each immutable Layer B case records:

```text
case_id
semantic_category
evidence_class
evidence_condition
input_evidence_ids
rejection_boundary
expected_rejection_code
observed_rejection_code
engine_invocation_count
provenance
deterministic_result_hash
```

For assembler-level rejection, `engine_invocation_count` must equal zero. The
evidence harness proves this by separating assembly and engine orchestration:
an assembler rejection yields no bundle and therefore no callable engine input.
It must not call or mock an engine and infer a zero count afterward.

Mandatory Layer B coverage is:

| Semantic category | Frozen rejection boundary/code | Evidence classification |
|---|---|---|
| unexplained future bar missing | assembler / `UNEXPLAINED_MISSING_BAR` | real approved-boundary condition |
| unsupported corporate action | CA coverage/assembler boundary / existing unsupported or quarantine code determined by implemented contract | real machine-visible scope evidence plus deterministic boundary fixture only if required to exercise the contract |
| revoked approval | assembler governance validation / `REVOKED_APPROVAL` | deterministic contract fixture pinned to real schema |
| tampered artifact or hash mismatch | integrity validation / `TAMPERED_ARTIFACT` | deterministic contract fixture |
| missing required domain | bundle/assembler validation / `MISSING_DOMAIN:<domain>` | deterministic contract fixture |
| ambiguous identity | identity validation / `IDENTITY_AMBIGUITY` | deterministic contract fixture or real ambiguity evidence |
| malformed calendar | calendar validation / existing `MALFORMED_CALENDAR` code | deterministic contract fixture |
| invalid lineage | lineage integrity validation / existing frozen lineage code | deterministic contract fixture |
| role swap | domain-role validation / `ROLE_SWAP` | deterministic contract fixture |
| duplicate domain | exact five-domain validation / `DUPLICATE_DOMAIN` | deterministic contract fixture |

Implementation must first inventory the exact currently implemented error codes.
Where this table describes a category rather than an existing exact code, the
implementation plan must bind it to the current contract; it may not create a
synonymous taxonomy merely for V2.

### Slot 16 normative rule

`EXPECTED_BAR_MISSING` is the semantic coverage category. The observed boundary
result is assembler rejection `UNEXPLAINED_MISSING_BAR`. No `LabelResultV1`
exists and `engine_invocation_count = 0`. Reports must expose all three fields
separately: semantic category, rejection code, and absent engine result.

### Unsupported corporate-action normative rule

`RIGHTS_ISSUE`, `STOCK_SPLIT`, and `SHARE_CONVERSION` remain unsupported. V2
does not promote them to approved `CorporateActionFactV1` calculation inputs.
The boundary must use the existing machine-visible unsupported/quarantine
contract. The implementation design must stop if the present contract cannot
produce deterministic rejection evidence without changing Phase 1 semantics.

## Layer C Contract — Calculation Edge-Case Acceptance

Layer C answers: do the frozen pure calculations handle exact edge geometry?

Layer C may use deterministic fixtures only when every case declares:

```text
evidence_class = SYNTHETIC_CONTRACT_FIXTURE
```

Mandatory Layer C coverage includes exact fixtures for:

- `UPPER_FIRST`;
- `LOWER_FIRST`;
- `NEITHER`;
- same-session upper-and-lower ambiguity after prior sessions with no decisive
  hit, yielding `NOT_LABEL_SAFE / BARRIER_PATH_AMBIGUOUS`.

Fixtures may share frozen input contracts and enums. The independent calculator
must not import or call `ReferenceLabelEngine`, production calculation
functions, production barrier helpers, or production wealth-path helpers.
Production and independent outputs produce immutable field-level comparison
evidence.

Real Layer A and synthetic Layer C coverage may coexist. They are counted and
reported separately and never substitute provenance identity.

## Cross-Layer Contract

Cross-layer acceptance requires:

- exact immutable artifact IDs and content verification;
- explicit architecture/amendment version pinning;
- deterministic replay of all ledgers and gate resolution;
- complete mandatory coverage per layer;
- no missing, duplicate, or conflicting coverage ownership;
- the synthetic provenance firewall;
- preservation of all V1 and negative historical artifacts;
- all original 16 gates resolved PASS from the frozen consumption map.

Any missing, stale, tampered, revoked, misclassified, or conflicting artifact
fails closed. A new V2 acceptance cannot mutate the meaning of a prior V1
artifact.

## Engine-Level vs Assembler-Level Failure Semantics

Two failure families are normative:

```text
A. Legal bundle reaches ReferenceLabelEngine; label path is unsafe
   -> LabelResultV1 exists
   -> LabelState.NOT_LABEL_SAFE plus frozen LabelReasonCode

B. Evidence cannot form a legal bundle
   -> assembler/contract exception artifact exists
   -> no LabelInputBundleV1
   -> no LabelResultV1
   -> engine_invocation_count = 0
```

Delisting in horizon and fully explained anchor suspension can be family A.
Unexplained missing bars, missing domains, revoked approvals, tampering, role
swap, and malformed calendar are family B. Reports cannot translate family B
into `NOT_LABEL_SAFE` or an engine reason.

## V1 22-Slot Migration Map

The migration preserves every old row and records its truthful V2 role.

| Old slot | V1 registered stratum | Checkpoint 7 actual behavior | V2 layer / coverage role | Real case retained | Replacement required | Migration reason |
|---:|---|---|---|---|---|---|
| 1 | normal positive return | positive real return path | A / positive ordinary path | yes | no | truthful legal bundle |
| 2 | normal negative return | negative path; real lower-first barriers | A / negative path and lower-first evidence | yes | no | truthful legal bundle |
| 3 | high volatility | high-volatility positive path | A / volatility | yes | no | truthful legal bundle |
| 4 | limit-up-like path | real upper-first limit-like path | A / limit-like and upper-first | yes | no | truthful legal bundle |
| 5 | limit-down-like path | real lower-first limit-like path | A / limit-like and lower-first | yes | no | truthful legal bundle |
| 6 | cash dividend | supported cash-dividend wealth path | A / supported CA calculation | yes | no | truthful legal bundle |
| 7 | bonus share | supported bonus-share wealth path | A / supported CA calculation | yes | no | truthful legal bundle |
| 8 | D+1 full-day suspension | suspension carry then trading | A / suspension carry | yes | no | truthful legal bundle |
| 9 | multi-day suspension | fully evidenced anchor bar absent | A / engine-level anchor unsafe | yes | no | legal bundle, truthful unsafe result |
| 10 | suspension through H5 | fully evidenced anchor bar absent | A / engine-level anchor unsafe | yes | no | legal bundle, truthful unsafe result |
| 11 | resumption before H5 | anchor full-day suspended; no legal D close | A / engine-level anchor unsafe | yes | no | legal bundle, truthful unsafe result |
| 12 | first IPO-eligible boundary | legal IPO-boundary bundle; real same-session 3/-2 ambiguity | A / IPO boundary and real ambiguity | yes | no | retain all truthful behaviors; C separately tests exact geometry |
| 13 | inside IPO seasoning | legal seasoning-boundary bundle | A / IPO seasoning | yes | no | truthful legal bundle |
| 14 | delisting boundary | `DELISTING_IN_HORIZON` | A / engine-level delisting unsafe | yes | no | truthful legal bundle |
| 15 | identity transition | canonical transition resolves and calculates | A / identity transition | yes | no | truthful legal bundle |
| 16 | expected future bar missing | all required bars present | B / unexplained-missing semantic category; old sample is negative applicability evidence only | no as stratum example | Layer B case required | successful bundle cannot prove assembler rejection |
| 17 | unsupported corporate action | no unsupported action in window | B / unsupported-CA semantic category; old sample is negative applicability evidence only | no as stratum example | Layer B case required | old sample does not contain the condition |
| 18 | latest-session pending | all labels `LABEL_PENDING` | A / pending | yes | no | truthful legal bundle |
| 19 | upper barrier first | real upper-first | A / upper-first; C exact upper fixture supplementary | yes | no | truthful real coverage |
| 20 | lower barrier first | actual upper-first for both contracts | A / truthful upper-first; registered lower role remapped | yes under actual behavior | no: lower real coverage exists in other A cases; C exact lower fixture mandatory | never relabel actual result |
| 21 | neither barrier | 3/-2 lower-first and 5/-3 neither | A / contract-specific lower and neither; C exact neither fixture supplementary | yes under contract-specific behavior | no | avoid collapsing two barrier contracts into one label |
| 22 | same-session ambiguity | actual lower-first | A / truthful lower-first; registered ambiguity role remapped | yes under actual behavior | no: slot 12 supplies real ambiguity; C exact ambiguity fixture mandatory | never relabel actual result |

Counts under the migration design:

```text
old rows retained as truthful Layer A real cases = 20 (all except 16 and 17)
old registered roles migrated to Layer B = 16, 17
old registered edge roles with Layer C obligations = 20, 21, 22
multi-layer semantic coverage = 12, 19, 20, 21, 22
```

Layer C fixtures are new acceptance evidence families, not replacements inserted
into the V1 inventory.

## Original 16-Gate Artifact Consumption Map

`GateArtifactConsumptionMapV2` is immutable and pins the following ownership.

| Gate | Primary layer | Required artifacts/coverage | PASS condition | FAIL condition | Cross-layer prerequisites |
|---|---|---|---|---|---|
| LABEL CONTRACT | A | frozen contract identity; seven canonical labels; exact five domains | contract and every A bundle verify | drift, missing label/domain, tamper | amendment pin, provenance |
| CAUSAL ISOLATION | B | offline boundary harness and AST isolation evidence | no provider/current/network access; rejected cases never reach engine | forbidden dependency or invocation | replay, synthetic firewall |
| TRADING SESSION SEMANTICS | A | real calendar/horizon cases | H1/H3/H5 derive from pinned ordered exchange sessions | sorting/repair/drift/mismatch | provenance |
| RETURN SEMANTICS | A | real positive/negative/CA/suspension paths and comparisons | all mandatory numeric comparisons match | missing coverage or mismatch | replay |
| MFE/MAE SEMANTICS | A | real volatile/trading/suspension paths | all extrema comparisons match | missing coverage or mismatch | replay |
| BARRIER SEMANTICS | C | C exact four-edge ledger plus truthful A real outcomes | all C cases and independent comparisons pass; A evidence not mislabelled | missing edge, mismatch, synthetic-as-real | Layer A supplementary evidence, firewall, replay |
| CORPORATE ACTION SAFETY | B | A cash/bonus calculations; B unsupported-CA rejection | both supported calculation and unsupported rejection coverage pass | either half missing/unsafe/mismatched | required Layer A supported-CA evidence, provenance, firewall |
| SUSPENSION SAFETY | A | real carry/resumption and anchor-suspension cases | carry and engine-level unsafe behavior match independent evidence | synthetic bar/carry or mismatch | provenance |
| DELISTING SAFETY | A | real delisting horizon case | frozen unsafe state/reason match | fabricated return/carry or mismatch | provenance |
| IDENTITY SAFETY | A+B | A real transition; B ambiguity/role/lineage rejection | transition resolves; invalid identity/lineage rejects before engine | ambiguity silently resolves or rejection missing | provenance |
| MISSING DATA FAIL-CLOSED | B | unexplained bar, missing domain, malformed calendar, hash/tamper cases | exact boundary codes; no bundle/result; engine count zero | engine called, code mismatch, or case missing | replay |
| LABEL_PENDING | A | real latest-session incomplete horizon | exact pending state/reason match | future completion fabricated or mismatch | provenance |
| NOT_LABEL_SAFE | A | legal-bundle unsafe cases only | required engine-level unsafe states/reasons match | assembler failures counted as label states or A cases missing | provenance |
| REFERENCE SAMPLES | A | explicit mandatory real-reference semantic set | every required A semantic has valid real evidence and comparison | missing real coverage or invalid provenance | synthetic firewall |
| INDEPENDENT VERIFICATION | A+C | independent implementations and immutable comparison ledgers | all required A and C comparisons match and independence checks pass | import/call violation, mismatch, incomplete ledger | replay, firewall |
| DETERMINISTIC REPLAY | Cross-layer | amendment, A/B/C ledgers, map, resolver, final acceptance | identical inputs yield identical artifacts and decision | any identity/output drift | all provenance valid |

All 16 names are mapped exactly once as decision owners. Gates may consume
supplementary evidence from another layer, but the map defines one primary
owner and all dependencies. There is no seventeenth gate.

## Synthetic Provenance Firewall

Any artifact with `evidence_class = SYNTHETIC_CONTRACT_FIXTURE` is prohibited
from contributing to:

- `REAL_REFERENCE_SAMPLE`;
- `REAL_MARKET_EVIDENCE`;
- `PHASE1_APPROVED_FACT_COVERAGE`;
- `REAL_BUNDLE`;
- real-market case counts or coverage claims.

The gate resolver validates classification before aggregating counts. A
synthetic ID in a Layer A ledger, a real-reference count, or a Phase 1 lineage
field fails the relevant gate. Reports output separate counts:

```text
REAL_REFERENCE_CASES
REAL_FAIL_CLOSED_EVIDENCE_CASES
SYNTHETIC_CONTRACT_FIXTURES
```

No combined `TOTAL SAMPLES` value may stand in for these counts.

## Immutable Evidence Families

V2 defines, but this checkpoint does not implement, these minimal families:

1. `Phase2AAcceptanceArchitectureAmendmentV2` — immutable supersession and
   definitions;
2. `RealReferenceCoverageLedgerV2` — Layer A cases and comparisons;
3. `FailClosedBoundaryLedgerV2` — Layer B conditions, exact rejection evidence,
   and engine invocation counts;
4. `CalculationEdgeFixtureLedgerV2` — Layer C fixture identity, production and
   independent results, and comparisons;
5. `GateArtifactConsumptionMapV2` — exact gate ownership and evidence contract;
6. `Phase2AAcceptanceV2` — new final decision pinned to all preceding IDs.

No generic registry, workflow engine, DAG, or new data platform is introduced.

## Immutable Supersession Model

The amendment schema is:

```text
amendment_version
superseded_architecture
new_architecture
reason = REFERENCE_ACCEPTANCE_ARCHITECTURE_CONTRACT_CONFLICT
triggering_acceptance_id
triggering_applicability_audit_id
triggering_discovery_id
layer_a_definition
layer_b_definition
layer_c_definition
cross_layer_definition
old_slot_migration_map
gate_artifact_map
label_engine_semantics_changed = false
phase1_data_changed = false
provider_data_changed = false
content_hash
```

V1 artifacts are not edited, deleted, revoked, or reinterpreted. The V2
amendment supersedes only the future acceptance architecture. Historical
resolution by architecture version remains deterministic.

## V2 Acceptance Invariants

`Phase2AAcceptanceV2` may report PASS only when:

```text
Layer A mandatory real coverage is complete
Layer A independent comparisons all PASS

Layer B mandatory rejection coverage is complete
Layer B exact rejection codes all PASS
Layer B assembler-level engine invocation counts all equal zero

Layer C mandatory edge coverage is complete
Layer C independent comparisons all PASS
Layer C evidence classification all equals SYNTHETIC_CONTRACT_FIXTURE

cross-layer deterministic replay PASS
cross-layer immutable provenance PASS
cross-layer synthetic firewall PASS

all original 16 gates PASS
```

Any missing, PENDING, FAIL, conflicting, revoked, stale, or tampered prerequisite
produces `PHASE 2A = FAIL / OPEN` and `READY FOR PHASE 2B = NO`.

## Failure Semantics

- Layer A calculation mismatch: FAIL; do not repair by changing independent
  expectations or sample identities after outcomes.
- Layer B rejection-code mismatch or nonzero engine count: FAIL; preserve exact
  observed evidence.
- Layer C mismatch: FAIL; fixture cannot be replaced based on outcome.
- Missing mandatory coverage: FAIL/OPEN, never assumed safe.
- Synthetic-as-real classification: FAIL and quarantine the affected acceptance.
- Artifact integrity or supersession failure: FAIL CLOSED.

## No Retrospective PASS

After any future V2 PASS, reports must state:

```text
Checkpoint 7 = FAIL under Acceptance Architecture V1
Acceptance Architecture V1 = SUPERSEDED due contract conflict
Phase 2A final status = determined by a new Acceptance V2 artifact
```

`Checkpoint 7 now PASS` is prohibited.

## Non-Goals

This amendment does not:

- change `ReferenceLabelEngine`, calculation, return, MFE/MAE, barrier,
  suspension, delisting, corporate-action, label-state, or anchor semantics;
- change Phase 1 facts, approvals, manifests, or providers;
- create Inventory V2 or rewrite the V1 inventory;
- create runtime V2 artifact classes or ledgers;
- create synthetic fixtures;
- run a new final acceptance;
- authorize Phase 2B.

## Implementation Boundaries

The implementation checkpoint may add only the six V2 evidence families,
classification/firewall enforcement, boundary execution evidence, frozen edge
fixtures, and the mapped evaluator. Existing engine and Phase 1 behavior remain
read-only unless an independently demonstrated correctness defect triggers a
separate STOP and review.

Layer B must bind every category to current error codes before implementation.
If unsupported CA cannot be exercised without changing Phase 1 scope, the
implementation stops and reports that boundary gap; it must not promote the
action type or fabricate a normal approved fact.

## Migration and Rollout

1. Independent review and freeze this design amendment.
2. Create a separate implementation plan.
3. Implement A/B/C evidence infrastructure and migration mapping only; run its
   focused acceptance tests, then STOP for independent review.
4. In a later checkpoint, fresh-run Layer A, B, and C evidence and resolve all
   16 gates into a new `Phase2AAcceptanceV2`.
5. Only an independently reviewed V2 PASS may make `READY FOR PHASE 2B = YES`.

Implementation and final acceptance are deliberately separate checkpoints so
evaluator correctness cannot be conflated with label correctness.

## Verification Plan

Design validation requires:

- all 22 V1 slots appear exactly once in the migration map;
- all 16 frozen gate names appear exactly once as primary owners;
- no unresolved placeholders or ambiguous ownership;
- Slot 16 explicitly records `UNEXPLAINED_MISSING_BAR`, absent engine result,
  and zero engine invocations;
- unsupported CA scope and boundary rule are explicit;
- engine-level unsafe and assembler-level rejection are distinct;
- the synthetic provenance firewall and separate counts are explicit;
- V1 artifacts and Checkpoint 7 FAIL remain immutable;
- runtime source, tests, Phase 1 data, and V2 artifacts remain unchanged;
- provider and network requests remain zero;
- Git diff contains design documentation only.

## Design Self-Review Result

```text
unresolved placeholders = 0
unfinished implementation placeholders = 0
old slots mapped = 22/22
frozen gates mapped = 16/16
unmapped gates = 0
ambiguous primary gate ownership = 0
Layer B engine_invocation_count invariant = explicit
Slot 16 exact rejection semantics = explicit
unsupported CA boundary = explicit and implementation-gated
synthetic firewall = explicit
V1 immutability = explicit
Checkpoint 7 FAIL immutability = explicit
Phase 2B blocked = explicit
```

Phase 2A remains FAIL/OPEN. Phase 2B remains blocked.
