# V5.2 Phase 2B Historical Evidence Assembler Bridge Design

## Purpose and boundary

`Phase2AEvidenceAssemblerV1` remains frozen. It is an acceptance-fixture
assembler whose `LabelAcceptanceSlotV1` input, frozen-audit lookup, and
slot-specific transition/delisting logic establish semantics for 22 cases;
it is not an arbitrary-anchor repository. Phase 2B therefore requires a
separate, production-only `HistoricalLabelEvidenceAssemblerV1`.

The new class may assemble evidence, but it must not implement label formulas,
IPO seasoning, status semantics, or a second label engine. It produces one
historical `LabelInputBundleV1`; the frozen `ReferenceLabelEngine` remains the
only label calculator.

## Inputs and exact algorithm

Input is an `AnchorDispositionV1` that is already `ELIGIBLE`, an exact
`HistoricalAnchorLineageV1`, and an explicit `latest_completed_session`.
The resolver must pin approval, manifest, and revocation artifacts before it
reads facts. It must never use a current pointer, directory scan, latest
approval, provider, network, or synthetic historical snapshot.

For one anchor it deterministically:

1. Validates calendar/master/status/CA approvals and manifests plus revocation
   registry, then resolves the exchange-open D,H1,H2,H3,H4,H5 sessions.
2. Resolves the effective canonical identity chain at each session from pinned
   master identity facts; an absent or ambiguous chain fails closed.
3. Looks up the D reference bar and each future bar through immutable
   daily-bar component indexes, retaining the exact component, fact, composite,
   approval, and manifest IDs used.
4. Looks up explicit daily status observations, delisting/identity-transition
   facts, and CA facts in `(D,H5]` through bounded interval indexes.
5. Emits exactly five ordered `DomainLineageV1` values: trade_calendar,
   security_master, daily_bar, daily_security_status, corporate_action. No
   financial lineage or snapshot IDs is permitted for `HISTORICAL` provenance.
6. Creates a hash-valid `LabelInputBundleV1` and calls the frozen engine.

Indexes are built once per pinned lineage/month and keyed by
`(exchange, session)`, `(canonical_identity, session)`, and
`(canonical_identity, effective_date)`. Month streaming permits only the
anchor month plus five-session look-ahead in memory; it must not scan all Phase
1 artifacts for every anchor.

## Reusable Phase 1 authorities

| Domain | Existing authority | Direct use | Required bridge adapter |
|---|---|---:|---|
| Calendar | approved calendar facts and manifests; `resolve_label_horizons` | partial | exact pinned open-session reader |
| Identity/master | complete master fact bundles; effective identity artifacts | partial | effective interval/transition index |
| IPO eligibility | `refresh.eligibility.evaluate_ipo_eligibility`, `IPO_SEASONING_SESSIONS=5` | yes | none; only consume via `AnchorDispositionV1` |
| Daily bars | `DailyBarFactV1`; Phase 1C composite validators | partial | component-aware fact index |
| Status/suspension | `SecurityStatusRepository`, `DailySecurityStatusFactV1` | partial | exact historical fact/status interval index |
| Delisting | status/master effective facts | partial | delisting boundary resolver |
| Corporate actions | `CorporateActionFactV1`, CA manifest/approval | partial | `(D,H5]` interval index and coverage proof |
| Governance | `SourceApprovalResolver`, immutable approval/revocation artifacts | yes | pinned-artifact loader only |

No existing production arbitrary-anchor five-domain repository is available;
the listed adapters are read-only index/lookup adapters over pinned immutable
Phase 1 facts, not replacement repositories or new policy engines.

## Missing-bar decision table

| Condition for an expected identity/session | Result |
|---|---|
| Verified approved bar | include it and pin its fact ID |
| No bar + explicit verified full-day suspension | include status-only carry path |
| No bar + verified delisting effective boundary | preserve frozen delisting safety path |
| No bar + verified canonical transition and successor bar | resolve only through pinned identity-chain evidence |
| No bar + none of the above | assembly rejects with the frozen missing-bar boundary |
| Missing status | assembly rejects; never default ACTIVE |
| Missing/ambiguous identity | assembly rejects; never assume unchanged |
| Missing CA coverage | assembly rejects/quarantines; never infer no event |

Unsupported `RIGHTS_ISSUE`, `STOCK_SPLIT`, and `SHARE_CONVERSION` events in
`(D,H5]` are retained in the CA lineage and passed to the frozen unsupported-CA
rejection boundary. Supported `CASH_DIVIDEND` and `BONUS_SHARE` facts are
ordered by effective date, action type, and fact ID.

## Failure taxonomy

`SYSTEMIC_INTEGRITY_FAILURE` aborts a month before partition publication:
tampered/noncanonical calendar, missing/revoked approval, manifest mismatch,
or index integrity failure. `SCOPED_SECURITY_EXCLUSION` arises only from the
already-resolved anchor eligibility authority. `NOT_LABEL_SAFE` is a valid
engine result after a complete admissible bundle (for example delisting,
unsupported CA, or proven suspension anchor). `LABEL_PENDING` is allowed only
when the frozen contract can represent the completed evidence window safely.

## Phase 2A equivalence regression plan

For every legal Phase 2A Layer-A case that can be resolved from the same
Phase 1 truth, build both bundles. Compare canonical identity, anchor, five
ordered domain lineage identities, reference/future facts, statuses, CA facts,
delisting, and provenance-relevant fields. Legitimate acceptance-only evidence
IDs are documented separately. Both bundles must then produce identical frozen
`ReferenceLabelEngine` values and barrier evidence.

## Partial-window gate

The production assembler cannot be implemented until the frozen contract can
represent a hash-valid H1/H3 bundle that contains only presently available
outcome evidence while yielding field-level pending values for later horizons.
Checkpoint 18A audit found this is currently unverified and conflicting; see
the companion report. No Phase 1 or Phase 2A semantic modification is proposed
by this design.
