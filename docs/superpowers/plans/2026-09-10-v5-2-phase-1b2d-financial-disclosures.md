# V5.2 Phase 1B-2D Financial Disclosures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a scoped, immutable and revision-aware PIT financial-disclosure fact source.

**Architecture:** Reuse the provider/raw/checkpoint and approval/manifest boundaries. Add only financial contracts, normalization/availability, revision-aware querying, bounded evidence scripts and gate-driven publication.

**Tech Stack:** Python 3.12, dataclasses, Decimal, zoneinfo, pytest, existing V5.2 provider framework.

**Spec:** `docs/superpowers/specs/2026-09-10-v5-2-phase-1b2d-financial-disclosures-design.md`

## Global Constraints

- Target history starts 2010-01-04; catch-up stops at approved upstream boundaries.
- No credential material in source, artifacts, logs or URLs.
- No derived factors, TTM, ranking, labels, ML, backtest or scheduler.
- Unsupported and ambiguous scope is machine-visible and fail closed.

---

### Task 1: Financial fact, availability and revision repository

**Files:** Create `src/v5_2/data/financial_disclosure_facts.py`, `src/v5_2/data/real_audits/financial_disclosure_availability.py`, `src/v5_2/data/financial_disclosure_repository.py`; test in `tests/data/test_financial_disclosures.py`.

**Interfaces:** Produce `FinancialDisclosureFactV1.create`, `FinancialDisclosureAvailabilityPolicyV1`, and `FinancialDisclosureRepository.query(security, metric, period_end, cutoff)`.

- [ ] Write tests proving bitemporal separation, date-only next-session safety, stock/flow semantics, deterministic identity, supersession, pre-revision queries, and fail-closed missing/tampered/quarantined behavior.
- [ ] Run the focused test and observe missing-module failures.
- [ ] Implement the smallest immutable contracts and repository.
- [ ] Run focused tests green.

### Task 2: Provider capability and acquisition contracts

**Files:** Modify `src/v5_2/providers/datahub.py`; create `src/v5_2/data/real_audits/financial_disclosure_entry.py` and `scripts/probe_phase_1b2d_financial_disclosures.py`; test in `tests/real_audits/test_financial_disclosure_entry.py`.

**Interfaces:** Produce a deterministic endpoint probe ledger and request inventory pinned to upstream universe/approval IDs.

- [ ] Write failing allowlist and deterministic-inventory tests.
- [ ] Probe all six candidate endpoints with bounded real requests and immutable raw/receipt evidence.
- [ ] Add only successful endpoints to the allowlist and freeze supported/unsupported scope.
- [ ] Run focused tests green.

### Task 3: Normalization, sample freeze and evidence gates

**Files:** Create `src/v5_2/data/real_audits/financial_disclosure_normalization.py`, `src/v5_2/data/real_audits/financial_disclosure_validation.py`, and bounded freeze/audit scripts; add focused tests.

**Interfaces:** Produce normalized staging facts, explicit quarantines, frozen sample inventory, cross-source ledger, revision audit and gate artifact.

- [ ] Write failing tests for units, report types, cumulative/point-in-time values, conflicting versions, unavailable evidence and gate fail-closed behavior.
- [ ] Implement minimal normalization and gates from actual supported schemas.
- [ ] Freeze samples before official lookup and perform bounded official comparison.
- [ ] Run focused tests green.

### Task 4: Historical acquisition, publication and acceptance

**Files:** Create bounded acquisition/materialization/publish scripts; modify `src/v5_2/data/manifests.py` only if financial lineage cannot be represented; update `docs/reports/V5_2_PHASE_1B2_ACCEPTANCE.md`.

**Interfaces:** Produce immutable raw acquisition, coverage matrix, optional scoped SourceApprovalArtifact, approved fact bundle and DatasetManifest.

- [ ] Acquire the full approved-universe scope only for endpoints proven safe; checkpoint/resume all requests.
- [ ] Materialize facts and classify every missing/unsupported/conflicting input.
- [ ] Publish only if every correctness-critical gate passes; otherwise publish zero.
- [ ] Run focused/full pytest, standalone, build, clean-room/wheel smoke, zero-dependency, credential scan and `git diff --check`.
- [ ] Record exact results, commit, push main, verify local/remote equality and clean worktree, then stop.
