# V5.2 Phase 1B-1 Daily Bar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Acquire, audit, normalize, approve, and publish immutable V5.2-owned daily-bar facts for the frozen universe without entering Phase 1B-2 or research logic.

**Architecture:** Preserve the frozen universe/inventory as immutable logical intent and add a one-to-one executable `ProviderRequestV1` mapping. Acquisition remains behind the existing credential-safe DataHub adapter and immutable raw/checkpoint stores. Pure audit modules independently evaluate normalization, units, structure, calendars, identities, completeness, exceptions, replay/revision, cross-source evidence, and adjustment contamination before an approval-gated fact/manifest publisher runs.

**Tech Stack:** Python 3.12, dataclasses, pytest, existing V5.2 provider/acquisition/raw/evidence/approval contracts, DataHub Tushare-compatible `daily` endpoint.

**Spec:** User-frozen Phase 1B-1 daily-bar instruction received 2026-09-06; this plan is its repository execution record.

## Global Constraints

- Freeze universe `2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01` and logical request inventory `9b1d034f00ab0d637bc56ab120ffcf725f226f21c09d27c3b85e36a4f644a6ce`; never resample from observed results.
- Pin trade-calendar approval `1581b4d367dba1256247ddd13e09b53d0f95b5b1deeb40af9e6ed4a36606353b` and security-master approval `f208c17accba6b669359f476b2fdf3a1bc9ec6856e7fa1831ccdd1c42b80d8cf`.
- Source is `datahubco_tushare_proxy`, endpoint is `daily`, and price basis is exactly `UNADJUSTED_RAW`.
- Tokens remain only in environment variables or ignored `.env`; no credential may enter code, tests, logs, exceptions, artifacts, manifests, or output.
- Local exceptions are explicit and bounded; systematic unit, adjustment, pagination, schema, missingness, or identity defects reject the dataset.
- No Phase 1B-2, status, corporate-action ingestion, financial disclosure, feature, label, ranking, ML, backtest, or alpha work.

---

### Task 1: Freeze and validate entry artifacts

**Files:**
- Create: `src/v5_2/data/real_audits/daily_bar_entry.py`
- Test: `tests/real_audits/test_daily_bar_entry.py`

**Interfaces:**
- Consumes: pinned JSON universe/inventory plus explicit approval/revocation sets.
- Produces: `DailyBarAcquisitionPlanV1` and `require_daily_bar_entry(...)`.

- [ ] Write failing tests proving artifact hash tampering, changed order/sample, adjustment other than `UNADJUSTED_RAW`, missing/revoked upstream approval, and non-bijective logical/provider request mappings fail closed.
- [ ] Run `pytest tests/real_audits/test_daily_bar_entry.py -q` and confirm missing-interface failures.
- [ ] Implement immutable loading and one canonical `ProviderRequestV1` per frozen symbol with `start_date=20100104`, `end_date=20251231`, exact requested fields, page size 5000, and a one-to-one mapping to the frozen logical IDs.
- [ ] Re-run the focused test and confirm pass.

### Task 2: Implement pure normalization and structural audit

**Files:**
- Create: `src/v5_2/data/real_audits/daily_bar_normalization.py`
- Create: `src/v5_2/data/real_audits/daily_bar_validation.py`
- Test: `tests/real_audits/test_daily_bar_normalization.py`
- Test: `tests/real_audits/test_daily_bar_validation.py`

**Interfaces:**
- Consumes: raw provider rows, verified unit policy, approved sessions and effective identity intervals.
- Produces: `DailyBarNormalizationPolicyV1`, normalized rows, and deterministic audit summaries.

- [ ] Write failing tests for exact field mapping; malformed/NaN/infinite/nonpositive prices; OHLC invariant failure; negative volume/amount; weekend/non-session bars; unknown identity; and the 300114/302132 transition boundary.
- [ ] Run both focused test files and verify expected missing-interface failures.
- [ ] Implement Decimal-based parsing and immutable normalized records without acquisition timestamps or implicit unit conversion.
- [ ] Implement session and effective-identity validators; zero volume remains a valid observation rather than inferred suspension.
- [ ] Re-run focused tests and confirm pass.

### Task 3: Implement unit and adjustment evidence

**Files:**
- Create: `src/v5_2/data/real_audits/daily_bar_units.py`
- Create: `src/v5_2/data/real_audits/daily_bar_adjustment.py`
- Test: `tests/real_audits/test_daily_bar_units.py`
- Test: `tests/real_audits/test_daily_bar_adjustment.py`

**Interfaces:**
- Produces: `DailyBarUnitEvidenceV1`, `DailyBarUnitPolicyV1`, and `UnadjustedRawEvidenceV1`.

- [ ] Write failing tests for constant volume/amount factors, mixed factors, zero denominators, price mismatch tolerance fixed at `0.0001`, and adjusted-price contamination.
- [ ] Run tests and observe missing-interface failures.
- [ ] Implement exact rational-factor evaluation; factors are frozen only from deterministic reference samples and inconsistent factors are dataset-level failures.
- [ ] Implement corporate-action discontinuity comparison as audit-only evidence; it does not create a corporate-action dataset.
- [ ] Re-run focused tests.

### Task 4: Implement daily-bar exception governance and completeness

**Files:**
- Create: `src/v5_2/data/real_audits/daily_bar_exceptions.py`
- Create: `src/v5_2/data/real_audits/daily_bar_completeness.py`
- Test: `tests/real_audits/test_daily_bar_exceptions.py`
- Test: `tests/real_audits/test_daily_bar_completeness.py`

**Interfaces:**
- Produces: `DailyBarExceptionalRecordV1`, `DailyBarExceptionBudgetV1`, `DailyBarExceptionPatternAuditV1`, and applicability-aware coverage evidence.

- [ ] Write failing tests for immutable local quarantine, budget overflow, systematic field/exchange clusters, isolated missing bars, and IPO/pre-listing or post-delisting not-applicable sessions.
- [ ] Run focused tests and observe expected failures.
- [ ] Implement a predeclared absolute/ratio/session-impact budget and systematic-signature detector; forbidden systematic categories can never be downgraded to local exceptions.
- [ ] Implement requested/supplied/applicable/missing symbol-session accounting.
- [ ] Re-run focused tests.

### Task 5: Extend real acquisition with deterministic progress/resume

**Files:**
- Modify: `scripts/phase_1b1_audit.py`
- Modify: `src/v5_2/data/acquisition.py`
- Test: `tests/data/test_pagination.py`
- Test: `tests/real_audits/test_daily_bar_entry.py`

**Interfaces:**
- Consumes: `DailyBarAcquisitionPlanV1`.
- Produces: immutable raw payloads/receipts/checkpoints and an acquisition summary.

- [ ] Add failing tests for repeated/missing pages, inconsistent counts, corrupt checkpoints, resume of terminal requests without network, and upstream revocation during restart.
- [ ] Run focused tests and verify failures.
- [ ] Add completed-request resume semantics that verify referenced raw hashes and do not append duplicate semantic payloads; later acquisition creates distinct receipts only when a request is intentionally replayed.
- [ ] Add `daily_bar` CLI support, progress counters, and sanitized failure output.
- [ ] Re-run focused tests.

### Task 6: Acquire and replay frozen daily bars

**Files:**
- Runtime only: ignored `data/phase_1b1/raw`, `receipts`, `checkpoints`, and `governance`.

- [ ] Run preflight without printing credentials.
- [ ] Run `python scripts/phase_1b1_audit.py daily_bar --resume`; preserve checkpoints and continue until all 5,548 logical requests complete or a fail-closed blocker occurs.
- [ ] Report expected/completed requests, pages, rows, symbols, and session range.
- [ ] Reacquire the frozen deterministic replay subset and confirm identical payload hashes with distinct receipts; retain any changed payload as revision evidence.

### Task 7: Cross-source, unit, adjustment, and final audit

**Files:**
- Create: `scripts/audit_daily_bar.py`
- Test: `tests/real_audits/test_daily_bar_final_gate.py`

**Interfaces:**
- Produces: content-addressed audit artifacts and a single daily-bar decision.

- [ ] Write failing final-gate tests requiring every structural, unit, adjustment, cross-source, replay, revision, exception, and upstream gate.
- [ ] Freeze deterministic event strata before looking at reference results.
- [ ] Obtain reference observations only from independent/official sources, store source identity and trust metadata, and evaluate exact tolerance/factors.
- [ ] Run the audit twice and require identical semantic IDs.

### Task 8: Publish approved facts and manifest only after approval

**Files:**
- Create: `src/v5_2/facts/daily_bar.py`
- Modify: `src/v5_2/data/manifests.py`
- Create: `scripts/publish_daily_bar.py`
- Test: `tests/facts/test_daily_bar.py`
- Test: `tests/data/test_manifests.py`

**Interfaces:**
- Produces: immutable `DailyBarFact` files and `DatasetManifestV1` pinning every required upstream/raw/receipt/policy/evidence/coverage/count identity.

- [ ] Write failing tests for publication before approval, manifest tamper, missing hashes, revoked upstream approvals, and historical acquisition time leaking into `available_at`.
- [ ] Implement gated deterministic fact publication and exact manifest validation.
- [ ] Re-run focused tests and deterministic replay.

### Task 9: Acceptance, report, commit, and stop

**Files:**
- Modify: `docs/reports/V5_2_PHASE_1B1_ACCEPTANCE.md`

- [ ] Run focused tests, full suite, standalone verifier, clean-room acceptance, wheel smoke, credential/sentinel scan, and `git diff --check`.
- [ ] Append the complete command outputs and required daily-bar/Phase matrix to the existing report.
- [ ] Commit and push `main`; verify local HEAD equals `origin/main` and worktree is clean.
- [ ] Stop without starting Phase 1B-2 or research engines.
