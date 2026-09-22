# V5.2 Phase 2B Historical Assembler Contract Audit

## Checkpoint 18A result

```text
PHASE2A ASSEMBLER PURPOSE = frozen 22-slot acceptance fixture
PHASE2A ASSEMBLER MODIFIED = NO
PHASE2B HISTORICAL ASSEMBLER REQUIRED = YES
PROPOSED CLASS = HistoricalLabelEvidenceAssemblerV1
PHASE1 SEMANTIC CHANGE REQUIRED = NO
PHASE2A SEMANTIC CHANGE REQUIRED = NOT PROPOSED
```

The exact root cause is confirmed in
`src/v5_2/data/label_evidence_assembler.py`: `assemble()` accepts
`LabelAcceptanceSlotV1`, indexes `self._entries[slot.slot]`, consumes
acceptance audit candidate paths, and has slot/security-specific transition
and delisting branches. It cannot be made arbitrary-anchor capable without
changing frozen Phase 2A acceptance infrastructure.

## Reusable authority decision

The production bridge can reuse immutable Phase 1 calendar/master/bar/status/
CA facts, daily-bar composite governance, `SecurityStatusRepository`,
`SourceApprovalResolver`, and the frozen
`refresh.eligibility.evaluate_ipo_eligibility` authority. It needs only
read-only, exact-pinned interval/index adapters described in the bridge design.
It must not duplicate IPO eligibility or label formulas.

```text
ARBITRARY ANCHOR SUPPORT = requires new Phase2B read-only assembler
FIVE DOMAIN LINEAGE SUPPORT = design defined; implementation blocked
MISSING BAR POLICY = explicit suspension/delisting/transition proof or reject
STATUS UNKNOWN POLICY = reject; no default ACTIVE
UNSUPPORTED CA POLICY = frozen NOT_LABEL_SAFE boundary
IDENTITY TRANSITION SOURCE = pinned effective master identity chain
DELISTING SOURCE = pinned master/status effective facts
HISTORICAL PATH = exact Phase1 lineage, HISTORICAL, null snapshots
CONTEMPORANEOUS PATH = separate future scope; real snapshots required
```

## Partial-window evidence-sufficiency probe

The probe used the existing reference-engine test fixture, rebuilt a
content-hash-valid historical bundle with:

```text
latest_completed_session = H1
future_bars = [H1 only]
future_statuses = [H1 only]
```

The frozen `ReferenceLabelEngine` output was all seven values:

```text
NOT_LABEL_SAFE / STATUS_UNRESOLVED
```

It did not return the required field-level state:

```text
return_1d = LABEL_AVAILABLE
return_3d and H5 fields = LABEL_PENDING
```

The cause is direct: after horizons are resolved, `validate_label_window()`
iterates the full H1..H5 window before per-value maturity handling and rejects
missing H2 status. The previous 16R evidence used full H5 evidence and only
changed `latest_completed_session`; it does not establish real partial-evidence
support.

```text
PARTIAL H1 BUNDLE SUPPORT = NOT VERIFIED / CONTRACT CONFLICT
PARTIAL H3 BUNDLE SUPPORT = NOT VERIFIED / CONTRACT CONFLICT
PARTIAL H5 BUNDLE SUPPORT = COMPLETE-WINDOW PATH ONLY
```

## Required stop

The bridge design is complete, but the frozen partial-window behavior blocks
Task 5 implementation. Correct arbitrary-anchor assembly must not omit future
facts and then call an engine that interprets the omission as unsafe. No
assembler implementation, Task 5–12 work, pilot, broad run, or final Phase 2B
acceptance is authorized by this report.

```text
TASK 5 IMPLEMENTATION READY = NO
CHECKPOINT 18 RESUME READY = NO
PILOT = BLOCKED
BROAD RUN = BLOCKED
```
