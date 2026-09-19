# Phase 2A V2.1 Final Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Materialize one deterministic, authoritative Phase 2A V2.1 final-acceptance artifact from freshly revalidated, exactly pinned Attempt 2 infrastructure.

**Architecture:** A small final-acceptance module reloads each immutable Attempt 2 JSON at its exact ID, verifies canonical identity and cross-artifact links, rebuilds the typed inputs from the same pinned evidence, and independently executes all 16 literal predicates. A separate script writes only the new final artifact with create-or-identical semantics.

**Tech Stack:** Python 3.11+, frozen dataclasses, canonical SHA-256 identity, pytest, immutable JSON.

**Spec:** `docs/superpowers/specs/2026-09-19-v5-2-phase-2a-acceptance-architecture-v2-1-design.md` plus the Checkpoint 15 user authorization.

## Global Constraints

- Pin design `a66825e25d40a46eceae18a50f1f2535ab9ee975`, amendment `d4a7941e2583eb84dd1bf501fb9183d5346f3813f383704b691c3798fb8ac25b`, plan `d9cfcf4822bd0d617e1e599e35fde0b939de03cd`, and infrastructure head `6e436f5da10fc9d2ba5825897f209f018e35d5bf` exactly.
- Read only the seven exact Attempt 2 artifact IDs authorized by Checkpoint 15; no latest lookup or fallback.
- No Phase 1, Label Engine, `Phase2AEvidenceAssemblerV1` runtime, gate semantics, provider, or network changes.
- A single fresh verification failure stops the acceptance; do not repair in this checkpoint.
- Final output is content-addressed and deterministic, with no identity-bearing wall-clock timestamp.
- Do not start Phase 2B, create a PR, merge, or update `origin/main`.

## Review Focus

- A valid infrastructure evaluation artifact alone must never be transformed into final PASS without fresh exact-pinned reload and predicate execution.
- A content-valid artifact under a wrong filename or wrong exact ID must fail before gate evaluation.
- Missing-bar must remain deterministic counterfactual evidence and contribute zero real observed failures.
- Unsupported CA must re-exercise `CorporateActionRepository.query`, not accept preflight output.
- A collision with differing final-artifact bytes must fail without overwriting the existing file.

### Task 1: Add Final Acceptance Contract and Fresh Verifier

**Files:**
- Create: `src/v5_2/labels/acceptance_v2_1_final.py`
- Create: `tests/labels/test_acceptance_v2_1_final.py`

**Interfaces:**
- Produces `Phase2AAcceptanceV2_1`, `verify_frozen_infrastructure_v2_1(repository_root)`, and `run_final_acceptance_v2_1(repository_root)`.

- [ ] Write tests that prove all six exact IDs plus supersession produce 16/16 final PASS, that changing any expected artifact ID fails closed, and that two fresh runs produce the same acceptance ID.
- [ ] Run the new test and observe its import failure.
- [ ] Implement the smallest frozen contract and verifier: reload canonical exact files, check their IDs/lineage, rebuild typed evidence from pinned immutable sources, independently call the 16 predicates, and only construct PASS when every predicate passes.
- [ ] Run the new test and existing V2.1 resolver/predicate tests.
- [ ] Commit the contract/verifier.

### Task 2: Add Immutable Final-Acceptance Materializer

**Files:**
- Create: `scripts/build_phase2a_v2_1_final_acceptance.py`
- Modify: `tests/labels/test_acceptance_v2_1_final.py`

**Interfaces:**
- Produces `materialize_final_acceptance_v2_1(repository_root, output_root)` and a single `final-phase2a-acceptance-v2-1-<id>.json` file.

- [ ] Write tests for two-directory byte-identical materialization, occupied-path idempotence, and different-byte collision failure.
- [ ] Run them and observe the missing materializer failure.
- [ ] Implement create-or-identical output only after calling the fresh verifier; do not write into Attempt 1 or Attempt 2 infrastructure directories.
- [ ] Run final tests plus the existing materializer and V2.1 firewall tests.
- [ ] Commit the materializer and one new final artifact.

### Task 3: Verify, Report, Push Feature Branch, and Stop

**Files:**
- Create: `docs/reports/V5_2_PHASE_2A_V2_1_FINAL_ACCEPTANCE.md`

- [ ] Run final focused tests, all V2.1 focused tests, labels, Phase 0–1C regression, full pytest, standalone, clean-room, build, wheel smoke, credential scan, AST/import checks, replay, tamper/revocation, count-preserving tests, and `git diff --check`.
- [ ] Confirm Attempt 1, Attempt 2 infrastructure, Phase 1, and Label Engine paths have zero diff from infrastructure head.
- [ ] Record exact command evidence, gate results, critical boundary values, final artifact ID, and Phase 2B boundary in the report.
- [ ] Commit the report, push only `phase2a-implementation`, verify feature-head equality, unchanged `origin/main`, clean worktree, and stop.

## Self-review

- Fresh reload, exact identity, cross-lineage, each literal gate, deterministic output, collision handling, and required boundary revalidation each have an owning task.
- No task introduces a new gate, policy, registry, provider request, or Phase 2B activity.
- No placeholders, latest lookup, or synthetic evidence promotion are authorized.
