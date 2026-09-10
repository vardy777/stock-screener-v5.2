# V5.2 Phase 1B-2C Corporate Actions Design Specification

## Status and scope

This specification implements only Phase 1B-2C corporate-action facts, point-in-time availability, scoped approval, causal adjustment inputs, 2026 catch-up, and append-ready coverage tracking. It does not implement a scheduler, financial disclosures, features, labels, ranking, ML, backtesting, or Phase 1B-2D.

The formal historical research target is `2010-01-04 .. 2025-12-31`. Current catch-up is `2026-01-01 .. latest available approved session`. Future production appends each approved trading day. These are distinct dimensions:

- `target_history_start = 2010-01-04`
- `baseline_validation_end = 2025-12-31`
- `rolling_coverage_end = latest approved session`

Neither the approval nor manifest may imply that a target interval is materialized or validated when it is not.

## Chosen architecture

Use the existing provider request/raw artifact/receipt, source approval, and dataset manifest framework. Add one compact corporate-action fact, one availability policy, one evidence artifact, a fail-closed repository, and the minimum gate/publisher wiring. Provider endpoints enter the allowlist only after a bounded real probe confirms endpoint identity, fields, pagination, coverage, revision signals, and semantic suitability.

Approval is scoped by `action_type x interval`. `CASH_DIVIDEND` and `BONUS_SHARE` may receive `APPROVED_WITH_RULES` independently of `RIGHTS_ISSUE`, `STOCK_SPLIT`, and `SHARE_CONVERSION`. Unsupported or unvalidated types and intervals remain machine-visible and make affected security-period queries `NOT_RESEARCH_SAFE`; absence is never interpreted as zero events.

## Fact contract

`CorporateActionFactV1` is immutable and append-only:

- `security_identity`
- `action_type`
- `knowledge_class`: `KNOWN_IN_ADVANCE`, `ECONOMIC_EFFECT_ONLY`, or `RETROSPECTIVE_ONLY`
- `published_at`
- `available_at`
- `ex_date` / `effective_date`
- `cash_per_share`
- `share_ratio`
- `source_fact_id`
- `source_version_identity`
- `revision_marker`
- `supersedes_source_fact_id`
- `content_hash`

Only fields required by a verified endpoint may extend this contract; `record_date`, `pay_date`, `rights_price`, and `rights_ratio` are not added speculatively. Corrections and cancellations are new source-fact versions. A cancelled action remains in announcement history but produces no economic effect. A cutoff query resolves the latest non-cancelled version that was available at that cutoff.

## Provider audit and ingestion

The bounded audit probes DataHub Tushare-compatible candidate endpoints for dividend, rights/rights issue, adjustment factor, and share structure data. A candidate must return a real successful response with a validated schema before it is added to `DATAHUB_ENDPOINTS`. The audit persists credential-free raw payload artifacts, acquisition receipts, content hashes, endpoint/source version identity, pagination observations, available historical coverage, publication/effective fields, and revision markers.

`adj_factor` is audit evidence only. It is never a corporate-action fact and never becomes point-in-time research truth. The ingestion boundary remains provider -> immutable raw artifact -> deterministic normalization -> evidence/approval -> immutable facts -> manifest -> repository.

## PIT availability

`CorporateActionAvailabilityPolicyV1` only converts already validated availability inputs into `available_at`; it does not probe providers, decide approval, or construct manifests.

- A verified timestamped publication uses that timestamp plus the frozen processing rule.
- A historical date-only publication becomes available at the next approved session at 16:30 Asia/Shanghai.
- An event with only an ex/effective date is not `KNOWN_IN_ADVANCE`; it remains `ECONOMIC_EFFECT_ONLY` or `RETROSPECTIVE_ONLY` according to verified semantics.
- A future production observation may use its verified observation time only when `requested_at`, `observed_at`, `payload_hash`, receipt, and source version identity are pinned.
- Backfill acquisition time never becomes historical `available_at`, including the 2026 catch-up.

Publication/knowledge time and economic effect time are independent. Future observations cannot retroactively improve historical visibility.

## Causal adjustment semantics

Daily bars remain immutable `UNADJUSTED_RAW`. `CausalCorporateActionAdjustmentPolicyV1` deterministically derives adjustment inputs from an unadjusted bar and the latest valid corporate-action version that is both economically effective and available at the research cutoff. It does not implement labels or a complete return engine.

A final vendor-provided forward-adjusted series is forbidden as PIT truth. Price adjustment and total shareholder return remain separate concepts: cash distributions and share-ratio events retain sufficient distinct fields for later consumers to calculate either measure explicitly.

## Coverage and repository boundary

The evidence, approval, and manifest record all of:

- `validated_coverage_by_action_type`
- `materialized_coverage_by_action_type`
- `coverage_gaps`
- `unsupported_intervals`
- `latest_approved_session`

The formal repository query checks requested action type, validated and materialized interval coverage, quarantine/exclusion status, PIT cutoff, revision lineage, exact source approval, and manifest integrity. Failure of any check raises a typed `NOT_RESEARCH_SAFE` error; it never returns an empty event set as a substitute for unknown coverage.

Incremental ingestion accepts a last approved coverage position and appends new immutable observations. Overlap is allowed only for idempotent replay or explicit revision discovery; it cannot rewrite older raw artifacts or facts.

## Evidence and gates

`CorporateActionPITEvidenceV1` is a single immutable scoped artifact containing:

- target/baseline/rolling dates
- source name and source version identity
- supported and unsupported action types
- validated and materialized coverage by action type, gaps, and unsupported intervals
- historical publication fallback and future observed-time rules
- economic-effect rules
- revision/cancellation results
- cross-source evidence IDs
- exceptions and quarantines
- `content_hash` and `complete`

`complete=true` means the explicitly supported subset is research-safe within its stated validated/materialized intervals. It does not mean all action types or the full target history are covered.

Samples are frozen before results. The bounded inventory covers cash dividends, bonus shares, multi-event securities, and revisions when available; SSE and SZSE; early, middle, recent, and 2026 catch-up periods; and STAR/ChiNext when valid candidates exist. Independent evidence comes from SSE, SZSE, or CNINFO and is used for validation, not bulk ingestion. A real mismatch fails closed; unavailable evidence stays pending.

The evaluator emits:

```text
CORPORATE ACTION STRUCTURAL = PASS / FAIL
CORPORATE ACTION PIT = PASS / PENDING / FAIL
CORPORATE ACTION CROSS_SOURCE = PASS / PENDING / FAIL
CORPORATE ACTION REVISION = PASS / PENDING / FAIL
ADJUSTMENT SEMANTICS = PASS / PENDING / FAIL
ROLLING COVERAGE MODEL = PASS / FAIL
2026 CATCH-UP = PASS / PARTIAL / PENDING / FAIL
PRODUCTION INCREMENTAL READINESS = PASS / PENDING / FAIL
EXCEPTION BUDGET = PASS / FAIL
SYSTEMATIC DEFECT = PASS / FAIL
SOURCE APPROVAL = APPROVED_WITH_RULES / PENDING / REJECTED
PUBLICATION_ALLOWED = true / false
APPROVED_FACTS = N
DATASET_MANIFEST = id / none
```

Publication requires all applicable correctness gates to pass and a valid scoped approval artifact. The publisher consumes verified gate and approval artifacts; it does not independently reinterpret evidence.

## Approval and manifest

An `APPROVED_WITH_RULES` artifact pins supported and unsupported action types, validated/materialized intervals, coverage gaps, quarantine rules, evidence identity, provider/source versions, and the exact policy versions. Missing early history may remain partial or pending. A large systematic gap for a claimed supported type prevents approval of that type; small explicit exceptions may be quarantined when the frozen exception budget permits.

The dataset manifest pins the same scoped coverage facts plus exact approval, evidence, raw payload, receipt, normalized fact, revision, exception, and policy hashes. `latest_approved_session` advances only after the incremental batch passes the same gates.

## Verification and exit

TDD covers immutable facts, date-only and observed-time availability, acquisition-time non-leakage, revision/cancellation resolution, scoped coverage, unsupported-type quarantine, `NOT_RESEARCH_SAFE`, causal adjustment boundaries, tamper/revocation/missing evidence, exact approval/manifest pins, incremental replay, and publisher fail-closed behavior.

Exit requires focused and full tests, clean-room test/build, standalone verification, wheel install/smoke, zero-project-dependency verification, credential scan, and `git diff --check`. Update `docs/reports/V5_2_PHASE_1B2_ACCEPTANCE.md` with exact commands and results, commit, push `main`, verify local HEAD equals `origin/main`, verify a clean worktree, and stop without entering Phase 1B-2D.
