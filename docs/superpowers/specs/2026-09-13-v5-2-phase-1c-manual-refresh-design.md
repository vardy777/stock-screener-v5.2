# V5.2 Phase 1C Manual Incremental Refresh Design

**Status:** DESIGN / ARCHITECTURE FREEZE  
**Repository baseline:** `822025a7cd60cd6a149dcf20cd21896e8fd42416`  
**Phase boundary:** Phase 1B is closed; Phase 2 remains not started and
`research_locked=true`.

## 1. Current Architecture Audit

V5.2 already owns the correctness primitives required by Phase 1C. Phase 1C
must compose them rather than replace them.

| Capability | Existing implementation | Reuse decision |
|---|---|---|
| Deterministic provider request | `ProviderRequestV1` in `providers/contracts.py` | Reuse unchanged |
| Credential boundary | `providers/credentials.py`, `integrations/datahub_http.py` | Reuse unchanged; refresh core receives acquisition ports, never secrets |
| Pagination, retry, rate limit | `data/acquisition.py`, `providers/retry.py`, `providers/rate_limit.py` | Reuse unchanged |
| Checkpoint/resume | `CheckpointV1`, `CheckpointStore` | Reuse unchanged |
| Raw payload and acquisition observation | `RawPayloadArtifactV1`, `AcquisitionReceiptV1`, `RawArtifactStore` | Reuse unchanged |
| Deterministic normalization | dataset-specific normalization policies | Reuse per dataset |
| Historical availability | `DailyBarAvailabilityPolicyV1`, `StatusAvailabilityPolicyV2`, Corporate Action and Financial policies | Freeze existing rules |
| Evidence and source approval | `EvidenceArtifactV1`, `EvidenceValidityPolicy`, `SourceApprovalArtifactV1`, immutable revocation/supersession | Reuse unchanged |
| Dataset publication | fact bundles plus `DatasetManifestV1` | Reuse unchanged |
| Historical lineage | `HistoricalDatasetCompositionV1` | Reuse for composed base plus extensions |
| Research readiness semantics | `Phase1BCoverageMatrixV1`, `HistoricalResearchSessionV1` | Extract/reuse narrow checks; do not rerun Phase 1B Exit |
| PIT repositories | status, Corporate Action and Financial repositories | Reuse for target-session queries |

Current scripts prove working flows, but are phase-specific and contain frozen
dates or artifact IDs. They are evidence that adapters can be extracted, not a
daily CLI contract:

- Calendar and Security Master: `acquire_phase_1b1_2026_extension.py` and
  `finalize_phase_1b1_2026_extension.py` implement bounded extensions,
  supersession and effective-dated universe changes.
- Daily Bar: `acquire_phase_1b_exit_daily_bar_2026.py` and
  `finalize_phase_1b_exit_daily_bar_panel.py` implement session-based requests,
  resume, normalization, conservative availability, approval and manifest.
- Security Status: `acquire_phase_1b_exit_status_2026.py` and
  `finalize_phase_1b_exit_status_panel.py` implement bounded event acquisition,
  lifecycle-aware resolution, approval and manifest.
- Corporate Action: `build_corporate_action_inventory()` and
  `acquire_corporate_action_requests()` are parameterized acquisition building
  blocks. The current full-history script is not a daily incremental entrypoint.
- Financial Disclosure: `build_financial_disclosure_inventory()`, bounded retry
  rounds and the acquisition/finalization scripts provide per-symbol/endpoint
  primitives. The current script is historical-range oriented.

There is no shared target-session resolver, approved-boundary reader, gap
planner, refresh service, refresh readiness artifact, snapshot, or thin CLI.
No current script is suitable as the future frontend's single backend call.

## 2. Product Requirement

One backend service must answer one manual request: determine the latest
completed research session, acquire only missing scope, validate and publish
immutable dataset updates, evaluate target-session readiness, and return a
machine-readable result. The CLI, future REST wrapper and future scheduler must
all call this service. None may own acquisition or readiness logic.

The operation reports `CURRENT`, `STALE`, `INCOMPLETE`, or `FAILED`. It never
silently substitutes an older snapshot for the requested target. A valid older
snapshot remains discoverable as `latest_successful_snapshot_id`, while today's
research remains blocked.

## 3. Target Session Resolution

The resolver accepts a timezone-aware `now` and a pinned approved calendar.
`today` is the Asia/Shanghai civil date. It must not query a provider. Before
resolution, the orchestrator performs one special bootstrap check: if approved
calendar coverage ends before today, the Calendar adapter alone acquires and
approves the missing civil-date tail through today. Target resolution uses only
the resulting approved calendar; it never guesses whether an uncovered date is
open.

1. Verify the calendar approval and manifest are intact, not revoked, and cover
   enough dates to resolve the latest completed open session.
2. If today is closed, `target_session` is the greatest approved open session
   before today.
3. If today is open and `now` is at or after the frozen D-close research cutoff
   of 16:30 Asia/Shanghai, `target_session=today`. This establishes the session
   being requested; individual datasets may still be unavailable and keep the
   refresh non-ready.
4. If today is open but not yet completed, use the preceding approved open
   session. Phase 1C's recommended operating time is 20:00 Asia/Shanghai, but
   20:00 is not a PIT cutoff or scheduler setting.
5. If the bounded Calendar bootstrap or validation cannot establish the answer,
   fail closed with `target_session=null`; never infer weekends or holidays
   algorithmically.

The five distinct values are retained in the result:

- `today`: current Shanghai civil date.
- `target_session`: latest completed open session the request is trying to make
  research-ready.
- `latest_completed_session`: resolved calendar fact; normally equal to target.
- `latest_approved_session`: cross-dataset base boundary after validation, not a
  single dataset's maximum date.
- `latest_successful_snapshot_id`: prior ready snapshot reference, unchanged on
  failure.

## 4. Gap Detection

Gap detection is manifest- and calendar-driven. Users do not supply normal
daily `start_date` or `end_date` values.

For session-indexed base datasets, compute:

```text
required_open_sessions = approved_calendar.open_sessions(
    after=dataset.latest_approved_session,
    through=target_session,
)
missing_scope = required_open_sessions - manifest-backed completed scope
```

The implementation must inspect explicit completed scope, not assume every day
between `coverage_start` and `coverage_end` is complete. Closed dates are never
requests. A coverage hole before the latest boundary is included in catch-up.

Event datasets use a dataset-specific watermark and query scope rather than an
invented expectation that every session has a row. `0 new rows` is accepted only
when the request completed, the raw response and receipt exist, validation
passed, and the adapter emits a `VALID_NO_CHANGE` observation for the exact
queried scope. Absence of a request or an ambiguous response is not no-change.

## 5. Dataset-by-Dataset Incremental Strategy

### Trading Calendar

- Existing incremental acquisition: yes, as a bounded extension pattern.
- Approved boundary: verified latest calendar manifest/composition coverage.
- Missing scope: civil-date tail needed to resolve through today, plus any
  explicit hole; never synthesize open/closed state.
- Acquisition: deterministic calendar request for the missing date interval.
- No-change: invalid if the requested interval has no day records; closed days
  are valid facts, not zero rows.
- Publication: immutable extension facts, evidence, superseding approval,
  extension manifest, then updated historical composition.
- Revision: different payload for the same request/page is revision evidence and
  requires revalidation; it never overwrites prior raw data.
- Ready: calendar deterministically resolves every day required through target
  and the target/preceding open-session relationship.

### Security Master / Effective Universe

- Existing incremental acquisition: yes, as a bounded effective-universe
  extension pattern.
- Approved boundary: verified composed master manifest and effective lifecycle
  coverage, not today's membership snapshot.
- Missing scope: refresh the provider master observation when calendar advances;
  derive additions, delistings and identity transitions against the pinned prior
  universe.
- Acquisition: deterministic master request; retain full observation because a
  provider may revise lifecycle fields.
- No-change: valid only after a successful complete observation whose normalized
  lifecycle delta is empty.
- Publication: immutable delta/supplement facts, superseding approval and
  manifest, then composition. Never backfill current membership into history.
- Revision: quarantine conflicts until identity/effective interval validation
  passes.
- Ready: every target-session identity is deterministically classified as target,
  non-target or quarantined; unresolved identities block affected scope.

### Daily Bar

- Existing incremental acquisition: yes, with session-based deterministic
  inventories and checkpoint/resume; the current entrypoint is date-frozen.
- Approved boundary: manifest-backed completed session scope plus explicit
  missing-bar dispositions.
- Missing scope: missing open sessions crossed with the effective universe for
  each session; do not request BJ/non-target identities.
- Acquisition: session/identity requests using existing acquisition controls.
- No-change: a target identity/session needs an existing valid classification;
  zero rows alone is not success.
- Publication: normalize, enforce units/structure, apply availability, classify
  missing bars, issue evidence/approval/manifest supersession, and compose with
  prior immutable facts.
- Revision: compare same request/page payload identity; a changed bar is a
  revision requiring validation and supersession.
- Ready: each effective identity at target is either a visible valid bar or an
  approved explicit fail-closed disposition. Unclassified gaps block that
  security and may block full-market readiness according to the frozen rule.

### Security Status

- Existing incremental acquisition: partial. Event acquisition, checkpointing,
  lifecycle resolution and publication exist, but the script is year-range
  frozen rather than driven by target and prior watermark.
- Approved boundary: status manifest coverage plus event/lifecycle observation
  scope and frozen PIT policy.
- Missing scope: event query tail through target, with enough overlap to detect
  provider revision of open-ended intervals; overlap is policy-defined, not a
  hidden rewrite of the approved boundary.
- Acquisition: existing name-change/risk-warning and suspension endpoints.
- No-change: valid only for a completed exact event query with an immutable empty
  payload observation.
- Publication: new event facts or valid-no-change evidence, status panel
  composition, superseding approval and manifest.
- Revision: reconcile provider revision while preserving old event facts and
  knowledge times; changed historical semantics fail closed pending validation.
- Ready: every target-universe identity resolves to an as-of status without
  look-ahead or unresolved event conflict.

### Corporate Action

- Existing incremental acquisition: acquisition primitives yes; daily
  target-driven publication no.
- Approved boundary: manifest pins supported action types, actual coverage
  intervals and gaps. Unsupported types remain machine-visible.
- Missing scope: query supported action types from the prior observation
  watermark through target, with a bounded revision overlap.
- Acquisition: reuse segmented corporate-action inventory and acquisition.
- No-change: completed query plus validated empty response yields
  `VALID_NO_CHANGE`; it never means unsupported types had no events.
- Publication: publish supported typed facts and scoped manifest supersession.
- Revision: preserve source revisions and re-evaluate ex-date/publication-time
  semantics.
- Ready: supported types must be safe for the target. A security-period affected
  by unsupported/pending type is explicit `NOT_RESEARCH_SAFE`; absence of a new
  supported event is not globally fatal.

### Financial Disclosure

- Existing incremental acquisition: parameterized per-symbol/endpoint primitives
  and bounded retries yes; daily target-driven delta publication no.
- Approved boundary: observed-facts manifest, supported metrics and exact query
  watermark, not a claim that every issuer has every metric.
- Missing scope: query announcement/update tail for supported endpoints through
  target with bounded overlap for revisions.
- Acquisition: reuse current endpoint inventories, raw store, checkpoints and
  bounded retry rounds.
- No-change: completed endpoint scope with validated empty response is
  `VALID_NO_CHANGE`; missing endpoint coverage is not.
- Publication: append immutable observations/revisions, superseding approval and
  manifest with honest metric/issuer coverage.
- Revision: retain both versions and their publication/availability times.
- Ready: optional scoped readiness is evaluated per security/metric. Missing
  optional facts do not block base research, but consumers requiring them receive
  explicit `NOT_RESEARCH_SAFE`.

## 6. Thin Refresh Architecture

Option A is selected: a thin coordinator over existing dataset adapters.

```text
CLI / future API / future scheduler
              |
              v
        RefreshService.refresh(now)
              |
      Calendar horizon bootstrap
              |
      TargetSessionResolver
              |
      ApprovedStateReader
              |
          RefreshPlanner
              |
  Calendar -> Master -> Daily Bar -> Status
              |
       CA -> Financial scoped adapters
              |
       RefreshReadinessEvaluator
              |
       ResearchDataSnapshotV1
```

`RefreshService` owns ordering and failure containment only. Dataset adapters
own dataset semantics and call existing acquisition/normalization/publication
code. The service never normalizes rows, invents availability, approves evidence
or edits manifests. The evaluator consumes verified artifacts; it does not call
providers. The CLI is an argument-free normal daily command with optional
test-only/investigation clock injection, and serializes one response contract.

No generic DAG engine, job database, plugin registry, worker or state machine is
introduced. A fixed tuple of six adapters is sufficient.

## 7. Historical vs Contemporaneous Availability

Every published increment carries a machine-readable mode:

- `HISTORICAL_RECONSTRUCTED`: retain the frozen `NEXT_SESSION_SAFE` rule;
  `available_at` is the next approved trading session at 16:30 Asia/Shanghai.
- `CONTEMPORANEOUS_OBSERVED`: an acquisition receipt proves the real
  `observed_at`; facts can become visible only after the required validation and
  approval conditions. `available_at` may not predate the observation or other
  applicable semantic knowledge time.

The mode is decided by a narrow existing-policy adapter from evidence, not by
the user's wall-clock preference. A 20:04 observation cannot become 15:00. A
2026 same-day observation cannot prove 2015 same-day availability. Mixed-mode
snapshots summarize mode per dataset and pin all supporting manifests.

## 8. ResearchDataSnapshotV1

The snapshot stores references, not facts. Minimum immutable fields:

```text
snapshot_id
target_session
created_at
latest_approved_session
calendar_manifest_id
security_master_manifest_id
daily_bar_manifest_id
security_status_manifest_id
corporate_action_manifest_id
financial_disclosure_manifest_id
availability_mode_summary
dataset_readiness
freshness_status
research_ready
latest_successful_snapshot_id
content_hash
```

`dataset_readiness` records, per dataset, verified approval ID, manifest ID,
coverage/watermark, readiness (`READY`, `SCOPED_READY`, `NOT_READY`), reason codes
and optional affected security scope. `availability_mode_summary` maps each
dataset to the modes actually present.

`snapshot_id` is the content hash of the complete canonical snapshot body except
the two identity fields. Repeated refresh with identical target and manifest
references returns the already stored snapshot; it does not create a new
`created_at` or new identity. The snapshot store is a small content-addressed
artifact store, not a database or fact store.

## 9. RefreshReadiness Contract

`research_ready=true` exactly when all conditions hold:

1. The target session is resolved from a valid pinned calendar.
2. Calendar, Security Master, Daily Bar and Security Status each have an intact,
   non-revoked approval/manifest lineage that is research-safe for target.
3. Their cross-dataset identities, target session, coverage and PIT visibility
   agree.
4. No base dataset has missing, tampered, revoked, conflicting or unresolved
   evidence affecting target full-market research.
5. Corporate Action and Financial Disclosure satisfy their frozen scoped rules:
   supported scope may be `SCOPED_READY`; affected unsupported security-periods
   are explicit exclusions, never inferred safe.
6. The proposed snapshot passes its own content-hash and pin validation.

`freshness_status=CURRENT` only when the resulting snapshot is ready for the
resolved target. `STALE` means intact approved state ends before target and no
refresh attempt has yet closed it. `INCOMPLETE` means an attempted or inspected
target has one or more dataset gaps. `FAILED` means execution/validation failed;
it never implies that prior approved artifacts were damaged.

This is a thin `RefreshReadinessArtifactV1`, not a new approval framework. It
records evaluated target, dataset results, reason codes, evaluated artifact IDs
and a content hash.

## 10. Partial Failure / Fail Closed

Raw payloads and receipts from successful acquisition steps remain immutable
even when a later dataset fails. A failed dataset cannot produce a new approved
manifest, and any dependency downstream of it is skipped with an explicit
reason. No ready snapshot is published unless all base readiness conditions
pass.

The snapshot pointer update is the only final commit point: first write and
verify the immutable snapshot, then atomically update a small
`latest-successful-snapshot` pointer. Failure before that point leaves the prior
pointer unchanged. The response may display the prior snapshot and its true
target session, but cannot relabel it as current.

## 11. Idempotency / Revision

Refresh planning is deterministic for pinned approved state, calendar and
target. Existing request IDs, checkpoint compatibility, raw payload identity and
immutable stores provide acquisition idempotency. Publication must look up exact
content identities and return existing facts/approval/manifest when inputs are
unchanged.

The second click for the same target and provider facts returns `CURRENT` with
`NO_OP` and the same snapshot ID. A changed provider payload for the same logical
page is a revision observation. It triggers dataset validation and immutable
supersession; old raw data, evidence, approval, manifest and snapshot remain
reproducible.

## 12. Catch-up

Catch-up uses the same planner and adapters as a one-session refresh. It orders
all missing open sessions ascending and can group requests only where the
dataset's existing deterministic inventory permits it. Calendar closes the
resolution range first; Master establishes each session's effective universe;
Daily Bar and Status then fill the base scope; optional event domains follow.

Checkpoint/resume may continue an interrupted request. Readiness is evaluated
for the final target only after all planned base gaps have terminal,
content-verified outcomes. A weekend invocation performs no weekend acquisition;
it catches up earlier missing open sessions or returns `CURRENT/NO_OP`.

## 13. Frontend Future Contract

The future frontend calls a thin API wrapper around the same
`RefreshService.refresh()` method used by CLI. The service returns:

```json
{
  "today": "2026-09-14",
  "is_trading_day": true,
  "target_session": "2026-09-14",
  "latest_completed_session": "2026-09-14",
  "latest_approved_session_before_refresh": "2026-09-11",
  "missing_sessions": ["2026-09-14"],
  "refresh_status": "SUCCESS",
  "data_freshness": "CURRENT",
  "latest_approved_session": "2026-09-14",
  "dataset_readiness": {},
  "research_ready": true,
  "snapshot_id": "...",
  "latest_successful_snapshot_id": "..."
}
```

The API adds transport concerns only. It does not calculate gaps or readiness.
The current phase implements neither API nor frontend.

## 14. Phase 2 Snapshot Consumption

All future Label, Feature, Ranking and research-run contracts must require
`snapshot_id` (or the exact immutable snapshot artifact) and validate its hash,
target session and readiness. They must resolve repositories through its pinned
manifest IDs. Interfaces named `load_latest`, implicit provider calls and
ambient current-manifest discovery are forbidden in research packages.

This requirement is frozen here but implemented only in Phase 2.

## 15. Testing Strategy

Phase 1C implementation must use RED/GREEN TDD and deterministic injected clocks
and acquisition ports. Required groups:

- Target resolution: trading evening, trading day before completion, weekend,
  holiday, calendar coverage failure and timezone edge.
- Gap planning: no gap, single gap, non-contiguous catch-up, closed dates,
  effective universe changes and earlier hidden hole.
- Per-dataset adapters: exact request scope, valid no-change, ambiguous zero rows,
  revision, supersession, revoked/tampered inputs and unsupported scoped facts.
- Availability: reconstructed next-session safety, contemporaneous observation
  lower bound, no historical extrapolation and mixed-mode summary.
- Readiness: each base dataset failing independently; scoped optional exclusion;
  cross-dataset mismatch; no ready snapshot on partial failure.
- Idempotency: double click returns identical snapshot and creates no duplicate
  fact, approval or manifest; provider revision creates immutable supersession.
- Catch-up and restart: ordered gaps, checkpoint resume and prior successful
  snapshot preserved.
- Governance: research cannot import provider/raw/staging/credential modules;
  no real credential in fixtures, logs, exceptions or artifacts.
- Acceptance: focused/full pytest, standalone, clean-room, build/wheel smoke,
  credential sentinel scan, deterministic replay and `git diff --check`.

Real provider acceptance must be bounded to genuinely missing post-baseline
scope. Historical 2010-2026 data is not reacquired.

## 16. Security / Credential Boundary

Only dataset acquisition adapters may receive the opaque credential and injected
provider client. `RefreshService`, planner, readiness evaluator, snapshot, CLI
response, logs and exceptions must never contain or stringify it. Secrets remain
in environment variables or ignored `.env`. Raw artifacts continue rejecting
secret-shaped keys. HTTP debugging, manifests, receipts and test output cannot
contain credential material. Existing sentinel and governance scans remain
release gates.

## 17. Explicit Non-Goals

This phase does not implement Phase 2, labels, features, ranking, ML, backtests,
TopN, watchlists, frontend, dashboard, REST API, scheduler, Windows Task, daemon,
worker, broker integration, orders or realtime feeds. It does not change the
historical 16:30 cutoff, rerun the full Phase 1B Exit daily, build a generic data
platform, or unlock research.

## 18. Alternative Options and Trade-offs

### Option A — Thin Refresh Orchestrator (recommended)

Adds only target/gap planning, six narrow adapters, readiness, snapshot and CLI.
It reuses the verified Phase 1 boundaries, minimizes new state and gives future
frontend/API/scheduler callers one correct service. Its fixed dependency order is
intentional and sufficient.

### Option B — Generic Data Orchestration Platform

A DAG engine, generic jobs, plugin registries and persisted workflow state could
support many future pipelines. It also duplicates checkpoint/state concepts,
increases recovery and governance surface, and solves requirements V5.2 does not
currently have. It is rejected as YAGNI.

### Option C — Each Phase 2 Module Refreshes Its Own Data

This has the fewest central components initially, but creates hidden provider
calls, different notions of latest data, PIT drift and irreproducible runs. It
also prevents one frontend refresh status. It is rejected on correctness grounds.

## 19. Recommended Implementation Scope

Minimum new production components:

1. `src/v5_2/refresh/contracts.py` — refresh result, dataset readiness,
   availability mode and `ResearchDataSnapshotV1` immutable contracts.
2. `src/v5_2/refresh/planning.py` — target-session resolution and deterministic
   gap plans from approved artifacts.
3. `src/v5_2/refresh/adapters.py` — one small protocol and six concrete adapters
   that delegate to existing dataset functions; no generic registry.
4. `src/v5_2/refresh/readiness.py` — thin target-session readiness evaluation
   using verified approval/manifest/repository facts.
5. `src/v5_2/refresh/service.py` — fixed dependency ordering, failure containment,
   idempotent snapshot publication and latest-successful pointer update.
6. `scripts/refresh_data.py` — thin CLI serialization of the service response.

Expected tests mirror those files under `tests/refresh/`, plus minimal governance
tests proving the research/provider boundary and snapshot pin requirement. Phase
1 dataset modules should change only where a failing adapter test proves a narrow
incremental seam is missing. Existing phase acceptance scripts remain immutable
historical evidence and are not repurposed as the daily orchestrator.

Implementation should be split into reviewable TDD increments: contracts and
snapshot identity; target/gap planning; Calendar/Master adapters; Daily
Bar/Status adapters; scoped Corporate Action/Financial adapters; readiness and
service atomicity; CLI and acceptance. No task may begin Phase 2 behavior.
