# V5.2 Phase 1B Historical PIT Exit Remediation Implementation Plan

> Execute on the explicitly authorized `main` branch from
> `f0f4564890a9dcb87a6abe33f99d3622f918b264`. Preserve every prior immutable
> artifact and keep `research_locked=true` unless every unchanged Exit gate passes.

**Goal:** Repair only the four measured Phase 1B Exit blockers by reusing existing
contracts and data, then rerun the unchanged four frozen historical sessions.

**Architecture:** Retain the six existing dataset domains and the thin Exit
evaluator. Add only content-addressed composition artifacts where the current
manifest schema cannot express base plus extension. Reuse the current acquisition,
normalization, availability, approval, repository and manifest code paths.

**Constraints:** No Phase 2 work, no gate relaxation, no new provider framework,
no daily snapshot explosion for status, no rework of approved Corporate Actions or
Financial Disclosures, and no historical acquisition timestamp used as availability.

## Task 1: Correct frozen dry-run evidence references

**Files:** `tests/real_audits/test_phase_1b_exit_runtime.py`,
`scripts/evaluate_phase_1b_exit.py`, prior Exit report, new immutable corrected
acceptance artifact.

1. Write a failing test that validates label, session, cutoff, hash and filename as
   one tuple for all four old artifacts.
2. Add a content-addressed reference-correction artifact without changing old files.
3. Correct the report mapping and pin the correction from the remediation evidence.
4. Run the focused Exit tests.

## Task 2: Compose complete Calendar historical lineage

**Files:** focused remediation tests, existing calendar artifacts, minimal
composition/closure code under `src/v5_2/data/`, remediation script, governance
artifacts.

1. Audit existing base facts, official/cross-source evidence, approvals and 2026
   extension; record whether any source acquisition is actually missing.
2. Write failing tests for deterministic composition, no overlap conflict, no gap,
   source hashes, and all four frozen dates.
3. Materialize the minimum base fact bundle/manifest and immutable composition.
4. Verify holiday boundaries and reject weekday inference.

## Task 3: Compose complete effective-dated Security Master lineage

1. Audit the existing identity graph, historical-universe reconciliation and 2026
   universe extension.
2. Write failing tests for base/extension continuity, immutable lineage and
   historically listed-then-delisted membership.
3. Publish the minimum base manifest plus deterministic composition/current manifest.
4. Verify all four frozen universes without substituting today's snapshot.

## Task 4: Extend Daily Bar materialization

1. Audit the existing full-history raw/fact cache before any network use.
2. Freeze deterministic inventories only for truly missing `2010-2023` and 2026
   segments, using the effective identity graph.
3. Write failing tests for coverage accounting, missing-bar neutrality,
   `NEXT_SESSION_SAFE`, delisted/transition identities and idempotent replay.
4. Reuse the existing pipeline to acquire only missing requests with resume; if
   credentials/provider coverage blocks completion, preserve exact PENDING evidence.
5. Validate, approve and manifest only the actually materialized interval.

## Task 5: Materialize the research-wide Status interval/event panel

1. Audit existing `namechange`, suspension and lifecycle raw/evidence coverage.
2. Freeze an acquisition inventory for missing status semantics and identities.
3. Write failing tests for all eight frozen semantics, conservative availability,
   interval resolution, security-scoped ambiguity and session-fatal systematic holes.
4. Reuse existing status contracts/repository; acquire only missing source records.
5. Produce a resolver-oriented coverage audit, approval, fact bundle and manifest;
   retain the old 71-case facts unchanged.

## Task 6: Re-evaluate unchanged Exit gates

1. Generate a new matrix only from verified artifacts.
2. Run EARLY/MIDDLE/RECENT/2026 twice with unchanged cutoff contracts.
3. Re-run temporal, survivorship, base eligibility, chaos and replay gates.
4. Append (do not replace) the remediation run and every artifact ID/command result
   to `docs/reports/V5_2_PHASE_1B_EXIT_ACCEPTANCE.md`.
5. Run focused/full pytest, standalone, clean-room, build/wheel smoke, zero-project
   dependency, actual credential/sentinel scan and `git diff --check`.
6. Commit, push `main`, verify local HEAD equals `origin/main` and worktree clean,
   then STOP regardless of PASS or FAIL.
