# V5.2 Phase 2A Acceptance Architecture V2.1 Design Amendment

## Status and authority

This document is a narrow corrective amendment to the frozen Phase 2A
Acceptance Architecture V2. It does not edit or reinterpret the historical V2
design in place.

```text
V2 = HISTORICAL FROZEN ARCHITECTURE ATTEMPT
V2.1 = CORRECTIVE DESIGN AMENDMENT

AMENDMENT REASON =
ACCEPTANCE_EVIDENCE_CLASSIFICATION_AND_GATE_EVALUATION_CORRECTION

PHASE 1 CORRECTION = NO
LABEL ENGINE CORRECTION = NO
RUNTIME IMPLEMENTATION AUTHORIZED BY THIS DOCUMENT = NO
```

Pinned authorities:

- Original V2 design commit:
  `f92f0a564c802ddc28dc71153be44d409b6858ee`.
- Original V2 implementation plan commit:
  `4db0f4ecb9e61853190f755d1bee164d9f84fe9a`.
- Authorized plan provenance correction:
  `390149882f3265b778b736a16380c13d9a64652a`.
- Checkpoint 8 replacement discovery:
  `947a8cd54a0a9a9bf91a8a4b45e7b502c272fb8dff374eab19b99615fca98f48`.
- Checkpoint 11 Attempt 1 amendment artifact:
  `31d262c3a54ebb15b9161a1a2b36e9bdd999a61c92aeb2d87a64ddedcf9e4365`.
- Attempt 1 Layer A ledger:
  `685a441408b4621df177dec7d5a54375b6b15874c49520b8c6b788ef9f8372b8`.
- Attempt 1 Layer B ledger:
  `ad915a5abb2fcf071929089cf85c7924c6c2254ccf8b870b32c613d96ba62505`.
- Attempt 1 Layer C ledger:
  `455fca83088ee0c40f30461c04e8fd5e04f40d47bdc8e94c4d70d0c986ad4ef6`.
- Attempt 1 gate map:
  `9b9ec9d4039194dcf2281b2aadcbf380fcd5da98acc79d2e5ff20eca90e6c264`.
- Attempt 1 fixture inventory:
  `97e610d410a58001963791e6992cac4a1eb469e4f347afde4e0a72aeeea6e934`.
- Checkpoint 11R conclusion at frozen feature HEAD
  `c10694d533a783cd8df5b61c8cf53fe6c346c971`: no naturally occurring
  approved-boundary `UNEXPLAINED_MISSING_BAR` condition exists in the current
  immutable Phase 1 evidence.

The Checkpoint 11 Attempt 1 status is permanently:

```text
FAIL / SUPERSEDED FOR ACCEPTANCE INFRASTRUCTURE CORRECTION
```

Its artifacts remain immutable and must never be relabeled PASS.

## Corrected missing-bar evidence contract

V2.1 supersedes only the V2 requirement that
`UNEXPLAINED_MISSING_BAR` must be a naturally observed
`REAL_APPROVED_BOUNDARY_CONDITION`.

The mandatory semantic is now:

```text
FAIL-CLOSED CONTRACT CONDITION
```

The evidence hierarchy is deterministic:

1. Use a naturally occurring immutable `REAL_APPROVED_BOUNDARY_CONDITION` when
   one exists.
2. Otherwise use `VERIFIED_REAL_BASE + DETERMINISTIC_CONTRACT_FIXTURE`.

Checkpoint 8 proves that option 1 is unavailable in the current repository.
Attempt 2 must therefore use option 2 and record at least:

```text
semantic_category = UNEXPLAINED_MISSING_BAR
base_evidence_class = REAL_MARKET_EVIDENCE
boundary_exercise_class = DETERMINISTIC_CONTRACT_FIXTURE
real_condition_observed = NO
real_condition_availability = REAL_REFERENCE_SAMPLE_UNAVAILABLE
unavailability_evidence_id = 947a8cd54a0a9a9bf91a8a4b45e7b502c272fb8dff374eab19b99615fca98f48
expected_rejection_boundary = Phase2AEvidenceAssemblerV1.assemble
expected_rejection_code = UNEXPLAINED_MISSING_BAR
engine_invocation_required = 0
```

The exact real base bundle and all five domain lineage identities must be
pinned. The `REMOVE_FUTURE_BAR` transform and its output must each have a
deterministic content identity. The transform may remove only the required
future bar selected by the frozen contract; it may not mutate Calendar,
Master/Identity, Status, Corporate Action, the anchor bar, or unrelated future
bars.

The assembler must reject before `ReferenceLabelEngine` is invoked. No
`LabelResultV1` may be created.

## Synthetic and fixture firewall

The following identities are permanently distinct:

```text
DETERMINISTIC_CONTRACT_FIXTURE != REAL_APPROVED_BOUNDARY_CONDITION
DETERMINISTIC_CONTRACT_FIXTURE != REAL_MARKET_EVIDENCE
VERIFIED_REAL_BASE + DETERMINISTIC_CONTRACT_FIXTURE
  != REAL_OBSERVED_FAILURE_CONDITION
```

The missing-bar case may satisfy fail-closed contract coverage. It must not
increment `real_reference_cases`, `real_observed_boundary_cases`, or
`real_market_failure_cases`. No aggregate sample count may conceal this
classification.

The absence of a naturally observed unexplained missing bar is not a Phase 1
defect. Phase 1 is expected to reject unexplained missing data. Requiring that
failure to exist inside approved immutable evidence would make Phase 2A
acceptance circular. V2.1 instead proves the counterfactual: if an otherwise
valid real evidence path loses a required unexplained future bar, the assembler
rejects it before the Label Engine.

## Unsupported corporate-action provenance audit

The audit found three distinct facts; none may be inferred from another.

### A. Real machine-visible unsupported scope

The immutable Corporate Action approval and manifest declare
`RIGHTS_ISSUE`, `SHARE_CONVERSION`, and `STOCK_SPLIT` unsupported over
`2010-01-04 .. 2026-09-09`:

- approval ID:
  `5e53080fd85dba5328cda9ed44c5dc5959e5bea965d8f5df12e07201deb8e974`;
- manifest ID:
  `5086896d0066baa928fe44c3469b2c1362feb2068db04acb7336b38c13bdbe2c`.

### B. Real immutable unsupported market events

The current content-addressed materialization audit
`8cf46a3dbaf6170cd64a1f2514f47ea87609200886fb2d8eebf60f888b11d28d`
contains 7,894 `UNSUPPORTED_SHARE_CONVERSION` quarantines. Its pinned candidate
bundle is
`e36c885b4ad5a666a829bc56eba0ba455cb26c1fae2cd321748d14908c67d16d`.

The deterministic Attempt 2 exemplar is the existing immutable quarantine:

```text
security_identity = 002029.SZ
effective_date = 2012-05-08
reason = UNSUPPORTED_SHARE_CONVERSION
quarantine_id = 000c9bb50f41b1ad603bb4367f1bf7eb5c6506557d323c2356baa00a12a3f7c6
```

This event remains quarantined. It is not an approved Phase 1 fact and cannot
be inserted into an approved `LabelInputBundleV1`.

### C. Production/governance rejection contract

An authoritative machine-enforced rejection boundary exists independently of
the acceptance harness:

```text
CorporateActionRepository.query
  -> NotResearchSafeError("NOT_RESEARCH_SAFE: unsupported action type")
```

The repository validates approval and manifest lineage, action type, coverage,
quarantined security-periods, and fact integrity before returning facts. The
existing production label calculation also rejects any unsupported action that
reaches its economic-wealth path, but that guard is defense in depth; Attempt 2
must not inject a quarantined event into an approved bundle merely to reach it.

Checkpoint 11 instead used `ACCEPTANCE_ONLY_CA_PREFLIGHT` with a deterministic
`RIGHTS_ISSUE` fixture. That harness accurately checked scope metadata but did
not exercise `CorporateActionRepository.query`; it is therefore not sufficient
as the authoritative unsupported-CA boundary.

Attempt 2 must classify and exercise the unsupported-CA case as:

```text
base_evidence_class = REAL_MACHINE_VISIBLE_UNSUPPORTED_SCOPE
boundary_exercise_class = REAL_UNSUPPORTED_MARKET_EVENT
real_condition_observed = YES
real_event_type = SHARE_CONVERSION
expected_rejection_boundary = CorporateActionRepository.query
expected_rejection_code = NOT_RESEARCH_SAFE: unsupported action type
engine_invocation_required = 0
publishes_market_fact = false
```

It must pin the manifest, approval, materialization audit, candidate bundle,
and quarantine ID above. It must execute the real repository boundary, not
serialize an acceptance-only rejection. `RIGHTS_ISSUE`, `STOCK_SPLIT`, and
`SHARE_CONVERSION` remain unsupported; no Phase 1 semantics or supported scope
changes.

## Executable 16-gate rule

P0-1 remains unchanged. `GateConsumptionV2.predicate` is an executable,
deterministic semantic assertion, not descriptive metadata. Every one of the
original 16 gate names must evaluate its literal required semantics against
the pinned artifacts.

```text
same artifact counts
+ missing required semantic coverage
= relevant gate FAIL
```

A layer-level boolean, count, or aggregate status cannot pass an individual
gate. V2.1 adds no gate and renames no gate.

## Attempt 2 design boundary

This amendment authorizes no implementation. A separately reviewed plan is
required before Attempt 2 may change the V2 resolver, Layer B case builder,
gate predicates, ledgers, or fixture inventory.

Attempt 2 must create new immutable artifacts and supersede Attempt 1 for
acceptance-infrastructure purposes. It must not mutate Attempt 1 artifacts,
Checkpoint 7/8 artifacts, the V1 inventory, the original V2 design, or the V2
implementation plan and its correction.

The amendment does not authorize final Phase 2A acceptance, Phase 2B, network
acquisition, provider requests, Phase 1 changes, assembler runtime-semantic
changes, or Label Engine changes.

## Design self-review

```text
PLACEHOLDERS = NONE
MISSING-BAR PROVENANCE = EXPLICIT AND NON-REAL
UNSUPPORTED-CA SCOPE = REAL AND PINNED
UNSUPPORTED-CA EVENT = REAL, IMMUTABLE, AND QUARANTINED
UNSUPPORTED-CA PRODUCTION CONTRACT = PRESENT AND PINNED BY SYMBOLIC BOUNDARY
ACCEPTANCE-ONLY PREFLIGHT SUFFICIENT = NO
16-GATE EXECUTABLE SEMANTICS = EXPLICIT
ATTEMPT 1 IMMUTABILITY = EXPLICIT
PHASE 1 / LABEL ENGINE CHANGE = NONE
IMPLEMENTATION AUTHORIZATION = NONE
```
