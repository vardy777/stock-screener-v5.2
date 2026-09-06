# V5.2 Phase 1B-1 Upstream Evidence Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the frozen SZSE calendar and security-master official-sample evidence gaps without changing any sample, policy, threshold, or historical artifact.

**Architecture:** A new composite calendar boundary joins immutable BaoStock SSE evidence with new SZSE official full-month calendar observations by exact sample ID. A separate security governance boundary materializes the frozen official sample inventory, preserves effective-dated identities, enforces quarantine/coverage intersection, and computes the combined upstream gate.

**Tech Stack:** Python 3.11+, standard library dataclasses and urllib, pytest, immutable canonical JSON artifacts.

**Spec:** User-approved Phase 1B-1 upstream evidence closure instruction attached on 2026-09-06.

## Global Constraints

- Preserve inventory `0242b7d10a358d81f5c1b40a42920ef75c55b1e42f6d1e6ea3a77d85b5e11cd0` and all 256 sample IDs.
- Do not alter V1/V2 policy thresholds, replace BaoStock evidence, or resample.
- Do not investigate T600018 identity; only enforce its effective-interval coverage gate.
- Do not acquire daily bars or enter Phase 1B-2, feature, label, ranking, ML, or backtest work.
- Every new artifact is content-addressed and old artifacts remain reproducible.
- Real credentials remain confined to ignored `.env` and never enter output or artifacts.

---

### Task 1: Composite independent calendar evidence

**Files:** Modify `src/v5_2/data/real_audits/tier3_calendar.py`; create `tests/real_audits/test_composite_calendar.py`; create `scripts/acquire_szse_calendar_audit.py`.

**Interfaces:** Produce `CompleteSessionDomainV1`, `CompositeIndependentCalendarEvidenceV1`, and exact-ID merge/adoption functions.

- [ ] Write failing tests for independence, exact 128 unresolved SZSE IDs, immutable BaoStock input, duplicate/conflicting IDs, unavailable states, complete-domain absence rules, and frozen V2 adoption.
- [ ] Run focused tests and confirm failures are caused by missing interfaces.
- [ ] Implement the smallest immutable merge and full-domain validation boundary.
- [ ] Run focused tests and acquire only the 128 frozen SZSE observations from the official full-month calendar endpoint.
- [ ] Persist new source, comparison, composite, and conditional adoption artifacts without rewriting old evidence.

### Task 2: Frozen security-master sample and coverage gate

**Files:** Create `src/v5_2/data/real_audits/security_master_governance.py`; create `tests/real_audits/test_security_master_governance.py`; create `scripts/resolve_security_master_official_sample.py`.

**Interfaces:** Produce `SecurityMasterOfficialSampleInventoryV1`, official comparison evidence, `QuarantineCoverageRuleV1`, coverage-limited approval rules, and `CombinedUpstreamGateV1`.

- [ ] Write failing tests for deterministic exact inventory, replacement rejection, identity preservation, interval intersection, pre-2010 fail-closed behavior, pinned approval rules, and approval revocation re-locking.
- [ ] Run focused tests and confirm expected missing-interface failures.
- [ ] Implement deterministic frozen selection and machine-verifiable coverage admission.
- [ ] Materialize the exact sample inventory and resolve only samples supported by SSE/SZSE official evidence.
- [ ] Re-evaluate security master without changing the 302132 identity graph or T600018 identity evidence.

### Task 3: Exit evaluation and acceptance

**Files:** Modify `docs/reports/V5_2_PHASE_1B1_ACCEPTANCE.md` and the minimum existing evaluation script needed to consume new artifacts.

**Interfaces:** Produce deterministic current calendar/master decisions and a daily-bar gate that is open only when both pinned approvals are currently valid.

- [ ] Run calendar coverage, continuity, PIT/session, pagination, revision, replay, cross-source, equivalence, and approval evaluation.
- [ ] Run master coverage, delisting, normalization, identity, official sample, survivorship, quarantine-overlap, equivalence, and approval evaluation.
- [ ] If both approvals pass, create only deterministic daily-bar universe/request inventory contracts; never acquire daily bars.
- [ ] Run focused tests, full suite, standalone verifier, clean-room acceptance/wheel smoke, credential/sentinel scan, and `git diff --check`.
- [ ] Append exact commands/results and final gate matrix, commit, push main, verify local/remote HEAD equality and clean worktree, then stop.
