# V5.2 Phase 1B-1 Minimal Real Source Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Audit and, only where immutable evidence passes frozen policy, publish independently approved Tushare trade-calendar, security-master and raw daily-bar facts.

**Architecture:** Three content-addressed audit policies are frozen before acquisition. Real DataHub Tushare-compatible responses pass through the Phase 1A credential, raw, receipt, normalization, evidence, approval and manifest boundaries; official SSE/SZSE observations provide deterministic cross-source evidence and no provider receives global approval.

**Tech Stack:** Python 3.11+, pytest, standard library, isolated injected HTTP transport, DataHub Tushare-compatible API, immutable JSON artifacts.

**Spec:** User-approved Phase 1B-1 instruction attached on 2026-09-06 and `docs/superpowers/specs/2026-09-06-v5-2-source-approval-provider-framework-design.md`.

## Global Constraints

- Only `trade_calendar`, `security_master` and unadjusted `daily_bar` are in scope.
- No Phase 1B-2 datasets, feature, label, ranking, ML, backtest, research run or alpha claim.
- Audit policy is committed before any real evidence is generated and cannot be loosened after observing results.
- Real credentials come only from `DATAHUB_API_KEY` or repository-local untracked `.env` and never appear in output or artifacts.
- The verified DataHub route is plaintext HTTP; evidence must record this and approval cannot conceal or mislabel the transport.
- Missing local credential stops all real-network work with `REAL SOURCE AUDIT BLOCKED = MISSING_LOCAL_DATAHUB_API_KEY`.
- Every dataset decision is independent and derived by the Phase 1A evaluator.
- `HISTORICAL PIT DATA = FAIL` and `READY FOR LABEL ENGINE = NO` remain frozen.

---

### Task 1: Freeze RealSourceAuditPolicyV1

**Files:** Create `src/v5_2/data/audit_policy.py`, `src/v5_2/data/phase_1b1_policies.py`; Test `tests/data/test_real_source_audit_policy.py`.

**Interfaces:** Produce immutable `RealSourceAuditPolicyV1.create(...)` and `phase_1b1_policies() -> Mapping[str, RealSourceAuditPolicyV1]` with exactly one policy per allowed dataset kind.

- [ ] Write failing tests for content identity, deep immutability, exact independent policy inventory, explicit coverage, deterministic sampling, missing/duplicate/cross-source/PIT/revision rules and fixed thresholds.
- [ ] Run focused tests and observe missing interfaces.
- [ ] Implement canonical content hashing and the three frozen policy definitions without provider access.
- [ ] Run focused/full/static tests and commit `feat: freeze phase 1b1 real source audit policies`.

### Task 2: Credential and real-access preflight

**Files:** Create `src/v5_2/data/real_source_preflight.py`, `scripts/phase_1b1_audit.py`; Test `tests/data/test_real_source_preflight.py`.

**Interfaces:** Produce a non-secret `RealSourcePreflightResult` and an audit CLI that reports only present/missing credential state.

- [ ] Write failing tests proving environment/local `.env` discovery, missing-token blocking, repository-bound path enforcement and output redaction.
- [ ] Implement preflight using the Phase 1A credential loader; do not make a network call during preflight.
- [ ] If credential is missing, stop Tasks 3-7 and report the exact mandated blocker.
- [ ] If credential exists, run a sanitized allowlisted DataHub probe and commit `feat: add phase 1b1 credential preflight`.

### Task 3: Trade-calendar real audit

**Files:** Create `src/v5_2/data/real_audits/trade_calendar.py`; Test `tests/real_audits/test_trade_calendar.py`; Generate only ignored immutable runtime artifacts plus a tracked redacted audit summary.

- [ ] Test coverage, explicit open/closed state, holiday/weekend/regime samples, revision/replay and official cross-source mismatches as fail-closed behavior.
- [ ] Acquire real `trade_cal` pages, store raw payloads/receipts/checkpoints, normalize without weekday inference and generate evidence.
- [ ] Resolve an independent decision, publish only if approving, create a pinned manifest, replay, scan secrets and commit the redacted summary.

### Task 4: Security-master real audit

**Files:** Create `src/v5_2/data/real_audits/security_master.py`; Test `tests/real_audits/test_security_master.py`; Generate ignored artifacts and a tracked redacted summary.

- [ ] Test listed/recent IPO/old IPO/delisted/board/exchange sampling and incomplete delisting coverage as fail closed or machine-limited approval.
- [ ] Acquire all required listing statuses, validate fields and identities, cross-check deterministic official samples, derive the independent decision and publish only within approval rules.
- [ ] Replay, scan secrets and commit the redacted summary.

### Task 5: Raw daily-bar real audit

**Files:** Create `src/v5_2/data/real_audits/daily_bar.py`; Test `tests/real_audits/test_daily_bar.py`; Generate ignored artifacts and a tracked redacted summary.

- [ ] Test OHLC invariants, values, duplicates, gaps, ordering, pagination and deterministic boundary samples including IPO/delisting/holiday adjacency.
- [ ] Acquire only unadjusted `daily` observations; reject any future-adjusted series, cross-check deterministic official samples and record tolerances/mismatches.
- [ ] Derive the independent decision, publish only when permitted, create the pinned manifest, replay, scan secrets and commit the redacted summary.

### Task 6: Adversarial and exit acceptance

**Files:** Create `tests/real_audits/test_adversarial_acceptance.py`, `docs/reports/V5_2_PHASE_1B1_ACCEPTANCE.md`.

- [ ] Prove fail-closed behavior for missing/duplicate pages, revisions, changed requests, checkpoint tamper, revocation, coverage mismatch, stale/cross-source evidence, manifest tamper, secret fields and partial pagination.
- [ ] Run Phase 1A regression, static isolation, sentinel scan, deterministic real-data replay and clean-room build/wheel smoke.
- [ ] Record the exact required exit matrix; keep `HISTORICAL PIT DATA = FAIL` and advance `READY FOR PHASE 1B-2` only if every Phase 1B-1 gate passes.
- [ ] Commit, push `main`, verify remote/local equality and stop.
