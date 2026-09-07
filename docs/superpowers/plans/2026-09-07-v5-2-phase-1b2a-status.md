# V5.2 Phase 1B-2A Daily Security Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, validate, acquire, and independently approve PIT-safe historical daily security status facts, reconcile all 6,489 frozen absent daily bars, and prove survivorship safety.

**Architecture:** Store immutable effective/knowledge-time status intervals for listing, risk warning, suspension, and identity, then deterministically project them into daily status. Formal universe resolution fails closed; diagnostic resolution is explicitly non-research. DataHub is the primary provider, official SSE/SZSE evidence is authoritative, and BaoStock is an independent daily-value cross-check only.

**Tech Stack:** Python 3.12, frozen dataclasses/enums, Decimal/date/datetime, existing V5.2 provider/raw/evidence/approval/manifest framework, pytest 8, DataHub Tushare-compatible API, SSE/SZSE official evidence, optional BaoStock 0.9.3.

**Spec:** `docs/superpowers/specs/2026-09-07-v5-2-phase-1b2a-status-design.md`

## Global Constraints

- Phase 1B-1 artifacts are immutable; corrections use revocation/supersession/replacement only.
- Scope is Phase 1B-2A only; no 1B-2B/C/D, features, labels, ranking, ML, backtest, or alpha work.
- Provider responses never enter research directly; only approved immutable facts through a pinned manifest may be queried.
- Missing, ambiguous, conflicting, overlapping, or not-yet-available formal status fails closed.
- All behavior changes follow RED/GREEN TDD and all credentials remain transport-only.

---

### Task 1: Freeze Status Interval and Daily Projection Contracts

**Files:**
- Create: `src/v5_2/data/security_status_facts.py`
- Test: `tests/data/test_security_status_facts.py`

**Interfaces:**
- Produces: `StatusKind`, `SecurityStatusIntervalFactV1.create(...)`, `DailySecurityStatusFactV1.create(...)`, `verify()`.
- Consumes: `content_hash` and timezone-aware datetime contracts.

- [ ] Write failing tests proving deterministic hashes, effective/knowledge separation, 300114/302132 identities, D-close invisibility before `available_at`, and tamper detection.
- [ ] Run `python -m pytest tests/data/test_security_status_facts.py -q`; expect import failure.
- [ ] Implement minimal frozen dataclasses with explicit canonical identities and append-only `supersedes_fact_id`.
- [ ] Re-run the focused test; expect PASS.
- [ ] Commit contract and tests.

### Task 2: Implement Interval Validation and PIT Projection

**Files:**
- Create: `src/v5_2/data/security_status_repository.py`
- Test: `tests/data/test_security_status_repository.py`

**Interfaces:**
- Produces: `StatusResolutionError`, `SecurityStatusRepository.project(security_identity, session, as_of)`, `tradable_universe(session, as_of)`, and `diagnose_tradable_universe(session, as_of)`.
- Consumes: Task 1 interval and daily fact contracts.

- [ ] Write failing tests for missing, ambiguous, conflicting, overlapping, adjacent, ST entry/exit, suspension/resumption, listing/delisting, not-yet-available events, and identity transition boundaries.
- [ ] Verify failures are caused by missing repository behavior.
- [ ] Implement dimension-specific interval indexing, deterministic resolution, typed fail-closed errors, and non-research diagnostics with exact counts/reasons.
- [ ] Add a boundary test proving diagnostic output cannot satisfy the formal research repository interface.
- [ ] Run focused tests and commit.

### Task 3: Freeze Dataset Requests, Provider Schemas, and Credentials Boundary

**Files:**
- Modify: `src/v5_2/providers/datahub.py`
- Create: `src/v5_2/data/phase_1b2a_requests.py`
- Create: `src/v5_2/data/real_audits/status_entry.py`
- Test: `tests/providers/test_datahub_status_adapter.py`
- Test: `tests/real_audits/test_status_entry.py`

**Interfaces:**
- Produces: allowlisted `namechange` and `suspend-d` dataset endpoints, `StatusRequestInventoryV1`, and canonical executable request mapping.
- Consumes: frozen Phase 1B-1 security universe/approvals and `ProviderRequestV1`.

- [ ] Write failing adapter tests for endpoint allowlisting, pagination schema, credential redaction, and malformed rows.
- [ ] Write failing inventory tests proving ordered universe/session/input hashes are frozen before results and revoked upstream approvals fail closed.
- [ ] Implement the minimal adapters and inventory builder without network calls.
- [ ] Run focused tests and commit.

### Task 4: Normalize Listing, Risk-Warning, Suspension, and Identity Events

**Files:**
- Create: `src/v5_2/data/real_audits/status_normalization.py`
- Create: `src/v5_2/data/real_audits/status_availability.py`
- Test: `tests/real_audits/test_status_normalization.py`
- Test: `tests/real_audits/test_status_availability.py`

**Interfaces:**
- Produces: `StatusNormalizationPolicyV1`, dimension-specific event-to-interval normalization, and versioned availability policies.
- Consumes: Task 1 fact contracts and approved calendar/identity artifacts.

- [ ] Write failing tests for exact fields, invalid dates, reversed intervals, unmatched suspension/resumption, versioned ST-name semantics, timestamped announcements, date-only next-session availability, and prohibition of acquisition-time backfill.
- [ ] Implement pure deterministic normalization; network/filesystem/credentials imports are forbidden.
- [ ] Run focused tests plus AST governance test and commit.

### Task 5: Add Status Exception and Systematic-Pattern Governance

**Files:**
- Create: `src/v5_2/data/real_audits/status_exceptions.py`
- Test: `tests/real_audits/test_status_exceptions.py`

**Interfaces:**
- Produces: `StatusExceptionalRecordV1`, `StatusExceptionBudgetV1`, `StatusExceptionPatternAuditV1`.
- Consumes: normalized failures with exchange/year/field/provider dimensions.

- [ ] Write failing tests for isolated quarantine, exact field/date scope, budget overflow, exchange-wide clustering, year-wide gaps, systematic ST absence, and systematic suspension absence.
- [ ] Implement immutable records, frozen thresholds, count reconciliation, and deterministic escalation.
- [ ] Run focused tests and commit.

### Task 6: Build Frozen Survivorship and Cross-Source Sample Inventories

**Files:**
- Create: `src/v5_2/data/real_audits/status_sampling.py`
- Test: `tests/real_audits/test_status_sampling.py`

**Interfaces:**
- Produces: `StatusSampleInventoryV1` with 30 ordinary, 10 ST-transition, 10 suspension-transition, and 10 listing/delisting cases plus pinned identity transition evidence.
- Consumes: only frozen Phase 1B-1 artifacts and canonical hash ordering.

- [ ] Write failing tests for exact stratum counts, later-delisted inclusion, no current-membership filter, deterministic ordering, content hash, and zero acquisition side effects.
- [ ] Implement canonical-hash sampling and immutable inventory serialization.
- [ ] Run tests, materialize the inventory before real response inspection, and commit code plus non-sensitive inventory metadata.

### Task 7: Perform Real DataHub Acquisition with Resume and Replay

**Files:**
- Create: `scripts/phase_1b2a_acquire.py`
- Modify: `src/v5_2/data/acquisition.py` only if a failing status-specific pagination test exposes a generic defect.
- Test: `tests/real_audits/test_status_acquisition.py`

**Interfaces:**
- Produces: immutable raw `namechange`/`suspend-d` artifacts, receipts, checkpoints, and real replay evidence.
- Consumes: Task 3 request inventory and existing shared limiter/retry/raw store.

- [ ] Write failing tests for repeated/missing pages, count inconsistency, checkpoint corruption, deterministic resume, same-payload/new-receipt replay, and changed-payload revision.
- [ ] Implement a credential-safe acquisition CLI with preflight, bounded workers, shared rate limiter, and progress counts.
- [ ] Run focused offline tests.
- [ ] Probe each endpoint schema; if unsupported or semantically incomplete, record immutable blocker evidence and do not emulate data.
- [ ] Acquire the complete frozen inventory, replay deterministic first/middle/last requests, and record exact request/page/row/receipt totals.

### Task 8: Validate PIT Semantics, Official Samples, and Survivorship

**Files:**
- Create: `scripts/audit_phase_1b2a_status.py`
- Create: `src/v5_2/data/real_audits/status_validation.py`
- Test: `tests/real_audits/test_status_validation.py`

**Interfaces:**
- Produces: full structural/PIT audit, official sample evidence, BaoStock comparison where suitable, and survivorship evidence.
- Consumes: Tasks 4–7 artifacts.

- [ ] Write failing tests for effective-versus-available timing, later-delisted historical inclusion, current-membership backfill detection, transition comparisons, and systematic mismatch escalation.
- [ ] Implement validators and evidence builders.
- [ ] Run the full raw/event audit, then the frozen 60+ sample cross-source audit.
- [ ] Record value agreement and historical availability sufficiency separately; unknown publication timing cannot pass PIT semantics.

### Task 9: Reconcile the Frozen 6,489 Missing Daily Bars

**Files:**
- Create: `src/v5_2/data/real_audits/missing_bar_classification.py`
- Create: `scripts/classify_phase_1b1_missing_bars.py`
- Test: `tests/real_audits/test_missing_bar_classification.py`

**Interfaces:**
- Produces: `MissingBarClassificationArtifactV1` with exactly one category per frozen missing key and exact aggregate counts.
- Consumes: Phase 1B-1 daily facts/manifest and validated status repository only.

- [ ] Write failing precedence tests for suspension, listing, delisting, identity, legitimate absence, local exception, contradictions, and unexplained cases.
- [ ] Write a reconciliation test requiring total count exactly 6,489 and forbidding missing-key-derived status facts.
- [ ] Implement deterministic streaming classification and systematic-pattern analysis.
- [ ] Run real reconciliation; fail closed if input manifest IDs or total differ.

### Task 10: Independently Approve and Publish Status Facts

**Files:**
- Modify: `src/v5_2/data/manifests.py`
- Create: `scripts/publish_phase_1b2a_status.py`
- Test: `tests/data/test_status_manifest.py`
- Test: `tests/real_audits/test_status_approval.py`

**Interfaces:**
- Produces: independent `daily_security_status` equivalence evidence, evidence bundle, approval, approved immutable facts, and manifest.
- Consumes: all prior PASS artifacts; no provider-wide approval.

- [ ] Write failing tests requiring all upstream IDs, status request inventory, raw/receipt hashes, normalization/availability policies, exception set, cross-source/survivorship/missing-classification evidence, and fact shards.
- [ ] Write failing tests for source approval revocation, manifest tamper, old-manifest reproducibility, and publication prohibition on PENDING/REJECTED.
- [ ] Implement minimal daily-security-status manifest extensions and fail-closed publisher.
- [ ] If every gate passes, publish approved interval/daily facts and manifest; otherwise publish only blocker/approval evidence with no approved facts.
- [ ] Run focused tests and deterministic publisher replay.

### Task 11: Phase 1B-2A Acceptance and Repository Exit

**Files:**
- Create: `docs/reports/V5_2_PHASE_1B2_ACCEPTANCE.md`
- Modify: no Phase 1B-1 artifact or acceptance report.

**Interfaces:**
- Produces: exact 1B-2A gate matrix, command output, test totals, hashes, Git commit, and remote verification.
- Consumes: Tasks 1–10 evidence.

- [ ] Record every real acquisition, audit, replay, cross-source, classification, approval, fact, and manifest result with exact counts and IDs.
- [ ] Run all focused status tests and record totals.
- [ ] Run `python -m pytest -q`, `python scripts/verify_standalone.py`, `python scripts/clean_room_acceptance.py`, build/wheel smoke, candidate credential/sentinel scan, and `git diff --check`.
- [ ] Output the complete required 1B-2A matrix. Even on PASS, preserve `PHASE 1B-2 overall = FAIL`, `HISTORICAL PIT DATA = FAIL`, and `READY FOR LABEL ENGINE = NO`.
- [ ] Commit, push `main`, verify local HEAD equals `origin/main`, verify the worktree is clean, and stop before Phase 1B-2B.
