# V5.2 Phase 1B-2A Daily Security Status Design Specification

## Status and scope

This specification implements only Phase 1B-2A: historical listing/delisting, risk-warning (ST), suspension/resumption, effective identity, historical tradability, classification of the 6,489 Phase 1B-1 absent bars, and survivorship acceptance. Phase 1B-1 artifacts are immutable inputs. Phase 1B-2B, corporate actions, financial disclosures, features, labels, ranking, ML, backtesting, and alpha research are excluded.

## Chosen architecture

Status is stored as compact immutable interval facts and projected deterministically into a daily status fact. Four independent dimensions are composed:

1. `LISTING`: listed interval and terminal delisting boundary.
2. `RISK_WARNING`: ST/risk-warning intervals.
3. `SUSPENSION`: suspension intervals and resumption boundaries.
4. `IDENTITY`: effective-dated security identity intervals, including the approved `300114.SZ -> 302132.SZ` transition.

Each interval stores effective time separately from publication/knowledge time. The daily projector evaluates both `session` and `as_of`; an effective event is invisible until `available_at`. The formal universe resolver requires exactly one non-conflicting answer for every required dimension and fails closed on missing, ambiguous, conflicting, overlapping, or not-yet-available status. A separate diagnostic resolver may skip identities but must return complete reasoned counts and may never feed research.

## Contracts

### `SecurityStatusIntervalFactV1`

- `security_identity`
- `status_kind`: `LISTING`, `RISK_WARNING`, `SUSPENSION`, or `IDENTITY`
- `status_value`
- `effective_from`
- `effective_to` (inclusive or null)
- `published_at` (nullable only when the source supplies no publication time)
- `available_at`
- `availability_basis`
- `source_fact_id`
- `source_name`
- `policy_version`
- `content_hash`

Intervals are append-only. Corrections create a new interval fact with `supersedes_fact_id`; old facts remain addressable. Adjacent equal-value intervals may coexist but are normalized deterministically. Overlap between incompatible values in the same dimension is a conflict and fails closed.

### `DailySecurityStatusFactV1`

- `security_identity`
- `session`
- `is_listed`
- `is_delisted`
- `is_risk_warning`
- `is_suspended`
- `is_eligible`
- `is_tradable`
- `effective_from`
- `effective_to`
- `available_at`
- `source_fact_ids`
- `source_name`
- `policy_version`
- `content_hash`

`is_eligible` requires a listed effective identity and no dataset-specific exclusion. `is_tradable` requires eligibility, no effective delisting, no risk-rule exclusion, and no suspension. The policy records whether risk-warning securities are excluded; this is not inferred by callers.

## Provider and source boundary

Primary ingestion remains `datahubco_tushare_proxy`, independently scoped to `daily_security_status`. The initial endpoint contracts are:

- `stock-basic` only as immutable Phase 1B-1 listing/delisting lineage; it is not reacquired or rewritten.
- `namechange` for dated name/risk-warning history.
- `suspend-d` for dated suspension/resumption observations.

Endpoint availability and response schemas are probed without changing the allowlist. Unsupported, incomplete, or semantically ambiguous endpoints leave the affected evidence `PENDING`; they are not emulated from daily-bar absence. SSE/SZSE official records are authoritative deterministic samples for listing/delisting and selected transition events. BaoStock `tradestatus`/`isST` is used only where it supplies an independent daily cross-check; it cannot establish publication time by itself.

Credentials remain transport-only and are prohibited from IDs, artifacts, logs, exceptions, tests, manifests, and reports.

## PIT availability policy

The following rules are fail closed:

- A verified timestamped official announcement uses its timestamp plus the versioned source-processing lag.
- A date-only announcement is unavailable at same-date D-close and becomes available at the next approved session cutoff.
- A provider effective date is never automatically mapped to `available_at`.
- A backfill acquisition timestamp is lineage only and never historical availability.
- A daily provider status without publication evidence may support effective-state cross-checking but cannot alone make the fact visible to PIT research.

The policy is versioned per status kind. No single global age or timing rule applies to listing, ST, suspension, and delisting.

## Acquisition and normalization

All provider requests use canonical `ProviderRequestV1`, pagination, immutable raw payloads, acquisition receipts, bounded retry, shared rate limiting, checkpoints, resume, content hashes, and deterministic normalization. Logical request inventories are frozen before result inspection. Real responses never flow directly to research.

Normalization rejects missing required fields, malformed dates, unknown codes, invalid interval ordering, incompatible duplicate events, and non-canonical risk-warning interpretation. Risk warning is derived from versioned name/event rules, not an unversioned substring check. Suspension and resumption observations form explicit intervals; an unmatched start or end is quarantined or fails the dataset according to the frozen exception policy.

## Formal and diagnostic APIs

`tradable_universe(session, as_of)` returns a deterministic tuple of effective identities only when all required status dimensions resolve uniquely. It raises a typed fail-closed error containing no credential or payload data otherwise.

`diagnose_tradable_universe(session, as_of)` returns:

- `included_symbols`
- `skipped_symbols`
- per-symbol `reason`
- `coverage_ratio`
- `missing_count`
- `ambiguous_count`
- `conflict_count`

The diagnostic result carries `research_eligible = false` and cannot be accepted by the research repository boundary.

## Phase 1B-1 absent-bar reconciliation

The exact immutable Phase 1B-1 daily-bar manifest and status dataset manifest are inputs. Every one of the 6,489 keys is classified exactly once as:

- `SUSPENDED`
- `NOT_YET_LISTED`
- `DELISTED`
- `IDENTITY_NOT_APPLICABLE`
- `OTHER_LEGITIMATE_NO_BAR`
- `LOCAL_EXCEPTION`
- `UNEXPLAINED`

Classification precedence is frozen in that order except that contradictions produce `UNEXPLAINED`, never a convenient legitimate class. Counts must reconcile to 6,489. Missing-bar keys are never used to create status facts.

## Survivorship and cross-source acceptance

The sample inventory is frozen before source comparison and contains at least 60 cases: 30 ordinary sessions, 10 ST transition cases, 10 suspension/resumption cases, and 10 listing/delisting boundaries. It additionally pins later-delisted securities and the identity transition boundary. Sampling is canonical-hash based within each stratum and cannot be changed after observing results.

The survivorship audit proves that later-delisted securities are included during their valid historical intervals and excluded only when the dated facts make them ineligible. Current membership is forbidden as a historical filter.

Cross-source comparison evaluates effective status values and timing semantics separately. Value agreement cannot compensate for unknown historical availability.

## Exception governance

`StatusExceptionalRecordV1`, `StatusExceptionBudgetV1`, and `StatusExceptionPatternAuditV1` are immutable and status-specific. Isolated historical ambiguity, unavailable announcements, merger/code transitions, and legacy anomalies may be quarantined with exact fields, dates, evidence, and scope. Exchange-wide, year-wide, provider-wide, field-wide, or clustered failures escalate to `SYSTEMATIC_DATASET_DEFECT`. Systematic ST-history or suspension-history absence cannot be packaged as local exceptions.

## Approval and publication

`daily_security_status` receives its own `DatasetEquivalenceEvidenceV1`, seven-type evidence bundle, `SourceApprovalArtifactV1`, immutable approved interval/daily facts, and `DatasetManifestV1`. No provider-wide approval exists. Facts and manifest are published only for `APPROVED` or `APPROVED_WITH_RULES`. The manifest pins upstream Phase 1B-1 approval/manifest IDs, request inventory, raw payloads, receipts, normalization and availability policies, exception set, cross-source evidence, coverage, counts, and fact shard hashes.

If any required historical availability, systematic-coverage, survivorship, cross-source, replay, or revision gate fails, approval remains `PENDING` or becomes `REJECTED`, facts are not published, Phase 1B-2A fails, and the report records the exact blocker.

## Verification and exit

Tests cover missing/ambiguous/conflicting status, overlap/adjacency, all transition boundaries, later-delisted membership, current-membership backfill prevention, PIT visibility, local/systematic exceptions, approval revocation, manifest tamper, and deterministic replay. Exit also requires the full suite, standalone verifier, clean-room install/test/build/smoke, credential/sentinel scan, and `git diff --check`.

The acceptance record is `docs/reports/V5_2_PHASE_1B2_ACCEPTANCE.md`. Phase 1B-2A stops after commit, push, remote-HEAD equality, and clean-worktree verification. Even on PASS, overall Phase 1B-2 and Historical PIT Data remain FAIL and Label Engine readiness remains NO.
