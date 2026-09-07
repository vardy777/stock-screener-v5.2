# V5.2 Phase 1B-2A Evidence Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close or precisely re-state the remaining Phase 1B-2A evidence and governance blockers without reacquiring frozen primary data.

**Architecture:** Add deterministic audit artifacts around the existing frozen inputs, then re-evaluate publication from pinned evidence. Historical corrections are supplements/supersessions, never mutations.

**Tech Stack:** Python 3.12, frozen dataclasses, content-addressed JSON, pytest 8, existing V5.2 approval/manifest framework.

**Spec:** `docs/superpowers/specs/2026-09-07-v5-2-phase-1b2a-evidence-closure-design.md`

## Global Constraints

- Keep Phase 1B-1 immutable and do not reacquire the existing 32 status requests.
- Preserve the exact 6,489 missing keys and all 61 frozen sample entries.
- No Phase 1B-2B, corporate action, financial disclosure, feature, label, ranking, ML, backtest, or alpha work.
- Every new behavior follows RED/GREEN TDD; every unresolved item fails closed or is explicitly quarantined.

---

### Task 1: Fix unexplained-count lineage

**Files:** Modify `scripts/publish_phase_1b2a_status.py`; test `tests/real_audits/test_status_approval.py`.

**Interfaces:** Produce `build_status_equivalence(classification, audit, replay)` whose limitations derive the unexplained count from the classification artifact.

- [ ] Write a failing test with a non-89 literal and assert the generated limitation uses that value.
- [ ] Run the test and confirm failure from the missing builder.
- [ ] Extract the pure builder and remove the hard-coded count.
- [ ] Run focused tests and commit.

### Task 2: Freeze and enforce multidimensional exception governance

**Files:** Modify `src/v5_2/data/real_audits/status_exceptions.py`; create `tests/real_audits/test_status_exception_audit_v2.py`; create `scripts/audit_phase_1b2a_exceptions.py`.

**Interfaces:** Produce `StatusExceptionBudgetV2`, multidimensional pattern audit, and explicit quarantine artifacts.

- [ ] Write failing literal-fixture tests for every frozen threshold and failure dimension.
- [ ] Verify RED, implement minimal immutable contracts, and verify GREEN.
- [ ] Run the real 89-key audit and materialize deterministic records before changing classifications.
- [ ] Commit code and tests.

### Task 3: Reconcile historical identities and create supplements

**Files:** Create `src/v5_2/data/real_audits/historical_universe.py`; create `tests/real_audits/test_historical_universe.py`; create `scripts/reconcile_phase_1b2a_universe.py`.

**Interfaces:** Produce `HistoricalUniverseReconciliationV1` and `HistoricalUniverseSupplementV1` with exact category totals and pinned original universe ID.

- [ ] Write failing tests for all categories, effective intervals, 600747.SH, aliases, and deterministic hashes.
- [ ] Verify RED, implement classification/supplement contracts, and verify GREEN.
- [ ] Reconcile exactly 542 identities; create a supplement only for required targets with available evidence.
- [ ] Commit code and tests.

### Task 4: Implement after-close status availability policy

**Files:** Modify `src/v5_2/data/real_audits/status_availability.py`; modify `src/v5_2/data/real_audits/status_normalization.py`; test `tests/real_audits/test_status_availability.py`.

**Interfaces:** Produce four availability bases and a versioned 16:30 Asia/Shanghai research cutoff.

- [ ] Write failing tests for timestamp, market-observable, conservative-after-close, next-session-safe, and acquisition-time prohibition.
- [ ] Verify RED, implement the policy, and verify GREEN.
- [ ] Update normalization callers only where semantic evidence supports the basis.
- [ ] Commit code and tests.

### Task 5: Build the immutable 61-entry official evidence ledger

**Files:** Create `src/v5_2/data/real_audits/status_official_samples.py`; create `tests/real_audits/test_status_official_samples.py`; create `scripts/audit_phase_1b2a_official_samples.py`.

**Interfaces:** Produce one content-addressed observation per frozen entry plus completeness/systematic-mismatch summary.

- [ ] Write failing tests proving unavailable is not match, duplicate entry IDs remain distinct by index, and systematic mismatch escalates.
- [ ] Verify RED, implement contracts, and verify GREEN.
- [ ] Retrieve SSE/SZSE sources for all 61 entries without resampling and record exact dispositions/URLs.
- [ ] Commit code and tests.

### Task 6: Re-evaluate the frozen missing keys and approval

**Files:** Modify `src/v5_2/data/real_audits/missing_bar_classification.py`; modify `scripts/classify_phase_1b1_missing_bars.py`; modify `scripts/publish_phase_1b2a_status.py`; test corresponding focused suites.

**Interfaces:** Consume the exception audit, universe reconciliation/supplement, availability policy, and official ledger; produce revised classification, approval, optional facts, and optional manifest.

- [ ] Write failing tests that quarantine only explicitly approved exception IDs and preserve all 6,489 keys.
- [ ] Verify RED, implement the minimal re-evaluator, and verify GREEN.
- [ ] Run real reclassification and approval; publish facts/manifest only if every gate passes.
- [ ] Commit code and tests.

### Task 7: Append acceptance evidence and exit

**Files:** Modify `docs/reports/V5_2_PHASE_1B2_ACCEPTANCE.md`.

**Interfaces:** Produce the required final matrix, command outputs, counts, artifact IDs, and Git evidence.

- [ ] Run focused tests, full pytest, standalone, clean-room, wheel smoke, secret scan, and `git diff --check`.
- [ ] Append exact results without altering the earlier acceptance record.
- [ ] Commit, push main, verify local HEAD equals origin/main and worktree is clean.
- [ ] Stop before Phase 1B-2B.
