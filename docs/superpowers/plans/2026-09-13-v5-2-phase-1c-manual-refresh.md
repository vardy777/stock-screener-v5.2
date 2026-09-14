# V5.2 Phase 1C Manual Incremental Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a thin, deterministic manual incremental refresh service that publishes a research-ready immutable snapshot only after target-session dataset readiness passes.

**Architecture:** A fixed six-adapter orchestrator resolves calendar coverage and target session, calculates manifest-backed gaps, delegates dataset semantics to existing Phase 1 functions, evaluates a thin readiness artifact, and atomically publishes a content-addressed snapshot. CLI and future transports call the same service.

**Tech Stack:** Python 3.12, frozen dataclasses, canonical JSON/SHA-256, pytest, existing V5.2 provider/acquisition/approval/manifest contracts.

**Spec:** `docs/superpowers/specs/2026-09-13-v5-2-phase-1c-manual-refresh-design.md`

## Global Constraints

- `research_locked=true`; no Phase 2, feature, label, ranking, ML, backtest, frontend, REST API or scheduler implementation.
- No provider call from research-facing packages or snapshot/readiness evaluation.
- Preserve `HISTORICAL_RECONSTRUCTED = NEXT_SESSION_SAFE at next approved session 16:30 Asia/Shanghai`.
- Contemporaneous `available_at` cannot predate actual observation/validation.
- Reuse existing request, raw, receipt, checkpoint, evidence, approval, manifest and repository contracts.
- All production behavior is introduced by RED/GREEN TDD.

---

### Task 1: Immutable refresh contracts and snapshot store

**Files:**
- Create: `src/v5_2/refresh/__init__.py`
- Create: `src/v5_2/refresh/contracts.py`
- Test: `tests/refresh/test_contracts.py`

**Interfaces:**
- Produces: `FreshnessStatus`, `RefreshStatus`, `DatasetRefreshResultV1`, `RefreshResultV1`, `ResearchDataSnapshotV1.create(...)`, `SnapshotStore.publish_ready(...)`, `SnapshotStore.latest_successful()`.

- [ ] Write tests for deterministic canonical identity, serializable result, invalid references, non-ready publication rejection, atomic pointer preservation and identical snapshot reuse.
- [ ] Run the focused tests and verify failure because the refresh contracts do not exist.
- [ ] Implement frozen contracts and a content-addressed store using temp-file plus `os.replace` for the pointer.
- [ ] Run focused tests and verify PASS.

### Task 2: Target resolution and gap planning

**Files:**
- Create: `src/v5_2/refresh/planning.py`
- Test: `tests/refresh/test_planning.py`

**Interfaces:**
- Produces: `ApprovedCalendarView`, `TargetSessionResolutionV1`, `resolve_target_session(now, calendar)`, `IncrementalGapPlanV1`, `detect_session_gaps(...)`.

- [ ] Write literal tests for after/before 16:30, closed day, uncovered calendar fail-closed, middle gap, multi-day catch-up and no weekend session.
- [ ] Run focused tests and verify expected missing-interface failures.
- [ ] Implement pure deterministic planning with explicit approved session sets.
- [ ] Run focused tests and verify PASS.

### Task 3: Thin dataset adapter contract and provenance

**Files:**
- Create: `src/v5_2/refresh/adapters.py`
- Test: `tests/refresh/test_adapters.py`

**Interfaces:**
- Produces: `AvailabilityMode`, `IncrementalPlanV1`, `DatasetStateV1`, `DatasetRefreshAdapter` protocol, `ThinDatasetAdapter`, and six named adapter constructors.

- [ ] Write tests proving exact missing scope, valid-no-change requires terminal evidence, ambiguous zero rows fail closed, historical versus observed availability, revision supersession metadata, status target watermark and scoped optional results.
- [ ] Verify RED.
- [ ] Implement one fixed thin adapter shape using injected existing-pipeline callables; no dynamic registry or DAG.
- [ ] Verify GREEN.

### Task 4: Cross-dataset refresh readiness

**Files:**
- Create: `src/v5_2/refresh/readiness.py`
- Test: `tests/refresh/test_readiness.py`

**Interfaces:**
- Produces: `RefreshReadinessArtifactV1.evaluate(target_session, dataset_results, evaluated_at)`.

- [ ] Write tests for every required base domain, manifest/approval/PIT/identity/coverage failure, scoped Corporate Action/Financial exclusions and all-ready PASS.
- [ ] Verify RED.
- [ ] Implement minimal fail-closed evaluation and canonical artifact identity.
- [ ] Verify GREEN.

### Task 5: Fixed-order refresh service and crash safety

**Files:**
- Create: `src/v5_2/refresh/service.py`
- Test: `tests/refresh/test_service.py`

**Interfaces:**
- Produces: `RefreshService(calendar_adapter, remaining_adapters, snapshot_store, clock).refresh() -> RefreshResultV1`.

- [ ] Write integration-style tests for already-current no-op, one-day refresh, multi-session catch-up, Calendar/Master success then Bar failure, Bar success then Status failure, after-16:30 provider incomplete, previous snapshot preservation and idempotent rerun.
- [ ] Verify RED.
- [ ] Implement calendar bootstrap, fixed order, dataset failure capture, readiness evaluation and final atomic snapshot commit.
- [ ] Verify GREEN.

### Task 6: Thin CLI and stable frontend-ready serialization

**Files:**
- Create: `scripts/refresh_data.py`
- Modify: `README.md`
- Test: `tests/refresh/test_cli.py`

**Interfaces:**
- Consumes: a single `RefreshService.refresh()` result.
- Produces: stable JSON/text output and exit code 0 only for `CURRENT` ready or successful no-op/refresh.

- [ ] Write subprocess/entry-function tests proving output fields, failure reasons, last snapshot, no credential output and no planning logic in CLI.
- [ ] Verify RED.
- [ ] Implement dependency construction seam and serialization only; document manual invocation and four freshness states.
- [ ] Verify GREEN.

### Task 7: Acceptance artifact and full verification

**Files:**
- Create: `scripts/evaluate_phase_1c_refresh.py`
- Create: `docs/reports/V5_2_PHASE_1C_REFRESH_ACCEPTANCE.md`
- Test: `tests/refresh/test_acceptance.py`

**Interfaces:**
- Produces: content-addressed `Phase1CRefreshAcceptanceV1` with the fifteen frozen gates and exact verification record.

- [ ] Write tests proving all-gate PASS, any-gate fail closed and deterministic replay.
- [ ] Verify RED, implement the minimal acceptance artifact/evaluator, then verify GREEN.
- [ ] Run focused refresh tests and full pytest.
- [ ] Run standalone, clean-room, build/wheel smoke, zero-dependency, actual credential sentinel scan, deterministic replay and `git diff --check`.
- [ ] Record exact commands, counts, snapshot IDs, acceptance ID and gate results in the report.
- [ ] Commit, push `main`, verify local HEAD equals `origin/main`, verify worktree clean, and STOP without starting Phase 2.
