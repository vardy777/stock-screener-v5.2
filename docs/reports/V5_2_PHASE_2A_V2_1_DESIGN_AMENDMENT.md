# V5.2 Phase 2A V2.1 Design Amendment

```text
HEAD (DESIGN AUTHORITY) = 6abea63ad05c2f2ed7eeacc5abf40c067b133c1b

V2.1 DESIGN AMENDMENT ID = d4a7941e2583eb84dd1bf501fb9183d5346f3813f383704b691c3798fb8ac25b

ORIGINAL V2 DESIGN PRESERVED = YES
ATTEMPT 1 ARTIFACTS IMMUTABLE = YES

MISSING BAR REAL CONDITION AVAILABLE = NO
MISSING BAR BASE EVIDENCE CLASS = REAL_MARKET_EVIDENCE
MISSING BAR EXERCISE CLASS = DETERMINISTIC_CONTRACT_FIXTURE
MISSING BAR UNAVAILABILITY EVIDENCE ID = 947a8cd54a0a9a9bf91a8a4b45e7b502c272fb8dff374eab19b99615fca98f48

MISSING BAR COUNTS AS REAL OBSERVED CONDITION = NO
MISSING BAR FAIL-CLOSED CONTRACT COVERAGE = YES

UNSUPPORTED CA REAL SCOPE EXISTS = YES
UNSUPPORTED CA REAL SCOPE EVIDENCE IDs =
  5e53080fd85dba5328cda9ed44c5dc5959e5bea965d8f5df12e07201deb8e974
  5086896d0066baa928fe44c3469b2c1362feb2068db04acb7336b38c13bdbe2c

UNSUPPORTED CA REAL EVENT EXISTS = YES
UNSUPPORTED CA REAL EVENT EVIDENCE IDs =
  8cf46a3dbaf6170cd64a1f2514f47ea87609200886fb2d8eebf60f888b11d28d
  e36c885b4ad5a666a829bc56eba0ba455cb26c1fae2cd321748d14908c67d16d
  000c9bb50f41b1ad603bb4367f1bf7eb5c6506557d323c2356baa00a12a3f7c6

UNSUPPORTED CA ACTUAL PRODUCTION/GOVERNANCE REJECTION CONTRACT = PRESENT
UNSUPPORTED CA REJECTION BOUNDARY =
  CorporateActionRepository.query ->
  NotResearchSafeError("NOT_RESEARCH_SAFE: unsupported action type")
UNSUPPORTED CA ACCEPTANCE-ONLY HARNESS VALID = NO

UNSUPPORTED CA BASE EVIDENCE CLASS = REAL_MACHINE_VISIBLE_UNSUPPORTED_SCOPE
UNSUPPORTED CA EXERCISE CLASS = REAL_UNSUPPORTED_MARKET_EVENT
UNSUPPORTED CA COUNTS AS REAL OBSERVED EVENT = YES

16-GATE EXECUTABLE PREDICATE REQUIREMENT = FROZEN
LAYER BOOLEAN ALONE MAY PASS GATE = NO

PHASE1 CHANGED = NO
LABEL ENGINE CHANGED = NO
PROVIDER REQUESTS = 0
DATA NETWORK CALLS = 0

V2.1 DESIGN STATUS = PASS / READY FOR INDEPENDENT REVIEW
V2.1 IMPLEMENTATION AUTHORIZED = NO

PHASE 2A = FAIL / OPEN
READY FOR PHASE 2B = NO
PHASE 2B STARTED = NO

REMOTE FEATURE HEAD AT DESIGN COMMIT = 6abea63ad05c2f2ed7eeacc5abf40c067b133c1b
ORIGIN/MAIN = 4254bb73a3eef054c7d998c43fd36521fe93db66
WORKTREE AT COMPLETION = CLEAN
```

## Amendment scope

The immutable amendment is
[`2026-09-19-v5-2-phase-2a-acceptance-architecture-v2-1-design.md`](../superpowers/specs/2026-09-19-v5-2-phase-2a-acceptance-architecture-v2-1-design.md).
Its byte-level SHA-256 is the V2.1 Design Amendment ID above. It pins the
original V2 design, the plan and authorized provenance correction, the
Checkpoint 8 discovery, and all six Checkpoint 11 Attempt 1 artifact IDs.

The amendment reason is exactly:

```text
ACCEPTANCE_EVIDENCE_CLASSIFICATION_AND_GATE_EVALUATION_CORRECTION
```

Checkpoint 11 Attempt 1 remains permanently:

```text
FAIL / SUPERSEDED FOR ACCEPTANCE INFRASTRUCTURE CORRECTION
```

No existing V2 document, plan, Checkpoint 7/8 artifact, V1 inventory, or
Attempt 1 artifact was edited.

## Missing-bar ruling

The current immutable Phase 1 evidence contains no naturally occurring
approved-boundary `UNEXPLAINED_MISSING_BAR` condition. This absence was already
established by Checkpoint 8 discovery
`947a8cd54a0a9a9bf91a8a4b45e7b502c272fb8dff374eab19b99615fca98f48`;
no new search or acquisition was performed.

V2.1 therefore requires an exactly pinned real five-domain base plus a
content-addressed `REMOVE_FUTURE_BAR` deterministic contract fixture. The
expected outcome is assembler rejection with `UNEXPLAINED_MISSING_BAR` and zero
Label Engine invocations. It covers the fail-closed contract but contributes
zero real-observed-condition counts.

This does not weaken Phase 1. Approved evidence should exclude unexplained
missing data; demanding that the defect exist naturally inside approved
evidence would be circular.

## Unsupported Corporate Action audit

### Scope evidence

The current approved Corporate Action manifest
`5086896d0066baa928fe44c3469b2c1362feb2068db04acb7336b38c13bdbe2c`
pins approval
`5e53080fd85dba5328cda9ed44c5dc5959e5bea965d8f5df12e07201deb8e974`,
supports only `CASH_DIVIDEND` and `BONUS_SHARE`, and marks `RIGHTS_ISSUE`,
`SHARE_CONVERSION`, and `STOCK_SPLIT` unsupported over the approved interval.

### Event evidence

The current content-addressed materialization audit
`8cf46a3dbaf6170cd64a1f2514f47ea87609200886fb2d8eebf60f888b11d28d`
contains 7,894 immutable `UNSUPPORTED_SHARE_CONVERSION` quarantines. The V2.1
design pins one existing event for deterministic boundary execution:

```text
security = 002029.SZ
effective_date = 2012-05-08
quarantine_id = 000c9bb50f41b1ad603bb4367f1bf7eb5c6506557d323c2356baa00a12a3f7c6
```

This event remains quarantined and is not promoted to an approved Phase 1
market fact.

### Rejection contract

The unsupported contract is not acceptance-only. The production/governance
repository rejects unsupported action types through
`CorporateActionRepository.query` with
`NOT_RESEARCH_SAFE: unsupported action type`. Existing repository tests also
cover this behavior.

Checkpoint 11's `ACCEPTANCE_ONLY_CA_PREFLIGHT` verified real scope metadata but
did not invoke this boundary. It is not valid as the sole acceptance harness.
Attempt 2 must execute the real repository rejection using the pinned real
unsupported event and must keep engine invocation at zero.

## Gate ruling

The original 16 names remain exact. Each gate must execute its literal semantic
predicate against pinned artifacts. Layer booleans, artifact counts, and
aggregate success cannot substitute for semantic consumption. The required
regression remains:

```text
same artifact counts + missing required semantic coverage = relevant gate FAIL
```

## Verification performed

```text
DESIGN PLACEHOLDER / AMBIGUITY SELF-REVIEW = PASS
V2 DESIGN BYTE PRESERVATION = PASS
V2 PLAN BYTE PRESERVATION = PASS
ATTEMPT 1 ARTIFACT BYTE PRESERVATION = PASS
CORPORATE ACTION MANIFEST CONTENT ID = VERIFIED
CURRENT MATERIALIZATION AUDIT CONTENT ID = VERIFIED
UNSUPPORTED SHARE CONVERSION COUNT = 7,894
PRODUCTION REJECTION CONTRACT = VERIFIED IN SOURCE AND TEST
git diff --check = PASS
```

No runtime tests, final V2/V2.1 acceptance, provider requests, or network calls
were required or authorized for this design-only checkpoint.

## Stop boundary

Checkpoint 12 stops after this amendment, provenance audit, and report. It does
not authorize Attempt 2 implementation, final Phase 2A acceptance, Phase 2B,
or changes to Phase 1, `ReferenceLabelEngine`, label calculations, assembler
runtime semantics, or the existing V2 resolver and ledgers.
