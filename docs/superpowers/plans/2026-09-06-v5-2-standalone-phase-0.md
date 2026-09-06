# V5.2 Standalone Phase 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, verify, and publish a self-contained V5.2 Python repository that has no source, path, package, data, or runtime dependency on any earlier project.

**Architecture:** Use a `src/v5_2` package with V5.2-owned foundation modules and repository-local tests/resources. Copy only characterized low-level algorithms; do not copy old namespaces or product runtime. Enforce independence with AST, path, inventory, clean-install, build, and wheel-smoke gates.

**Tech Stack:** Python 3.11+, setuptools, pytest, build, standard-library dataclasses/zoneinfo/hashlib/json/pathlib/msvcrt.

**Spec:** `docs/superpowers/specs/2026-09-04-v5-2-standalone-repository-design.md`

## Global Constraints

- Do not modify, switch, commit, push, delete, schedule, notify, or run `C:\Users\lisha\stock-screener`.
- Do not import `g1`, `v2`, `v4`, `v5`, `v5_1`, or `shared_core`.
- Do not use submodules, editable/local-path dependencies, the old repository on `PYTHONPATH`, or runtime reads outside the new repository.
- Keep `research_locked=true` and `broker_orders_enabled=false`.
- Do not implement historical datasets, features, labels, ranking, ML, realtime scanning, notifications, scheduling, or trading.
- Every code unit starts with a failing targeted test and ends with a passing targeted test.

---

### Task 1: Standalone project, governance, and corrected documentation

**Files:** Create `.gitignore`, `AGENTS.md`, `README.md`, `pyproject.toml`, `requirements.lock`, `src/v5_2/__init__.py`, required package `__init__.py` files, corrected `docs/*.md`, and migration inventory files. Test `tests/governance/test_standalone.py`.

**Interfaces:** Produces installable package `v5_2`, constants `__version__`, `RESEARCH_LOCKED`, `BROKER_ORDERS_ENABLED`, and repository-root governance checks.

- [ ] Write tests proving package metadata and hard gates.
- [ ] Run `python -m pytest tests/governance/test_standalone.py -v` and observe import/config failure.
- [ ] Create the minimal project/package/docs and make the test pass.
- [ ] Initialize independent Git repository on `main` only after inventory is correct.

### Task 2: V5.2-owned foundations

**Files:** Create `src/v5_2/foundations/{core,calendar_contract,calendar,immutable_facts,order_quantity}.py`, a repository-local calendar fixture, and tests under `tests/foundations/`.

**Interfaces:** `ContractViolation`; strict validators; `TradingCalendar.is_open/shift`; `validate_calendar_records`; `canonical_json/content_id/ImmutableFactStore`; `board/minimum_buy/valid_buy/valid_sell/floor_quantity`.

- [ ] Write failing calendar, immutable-fact, and quantity tests covering all requested cases.
- [ ] Run each targeted test and confirm missing-module failure.
- [ ] Implement the minimum V5.2-native modules without old imports or paths.
- [ ] Run targeted foundation tests and confirm pass.

### Task 3: Enforce zero-project-dependency gates

**Files:** Complete `tests/governance/test_standalone.py` and create `scripts/verify_standalone.py`.

**Interfaces:** Static verifier returns nonzero and findings for forbidden AST imports, active old paths, forbidden root entries, unsafe dependency declarations, secrets/runtime data, or retired scheduler/notification assets.

- [ ] Add failing fixture-based tests proving exact-module matching (`v5` forbidden, `v5_2` allowed).
- [ ] Implement repository scan with documentation-only provenance exemptions.
- [ ] Run governance tests and the verifier from the new root with a sanitized `PYTHONPATH`.
- [ ] Run the complete local suite and record the exact count.

### Task 4: Clean-room build, report, and GitHub publication

**Files:** Create `scripts/clean_room_acceptance.py` and `docs/reports/V5_2_STANDALONE_PHASE_0_ACCEPTANCE.md`; generated `dist/` remains ignored.

**Interfaces:** Acceptance script builds wheel/sdist, creates temporary venvs, installs the wheel, smoke-imports `v5_2`, copies only tracked source into a separate root, runs all tests, scans archives, and emits machine-readable results used by the report.

- [ ] Run local full tests and static verifier immediately before acceptance.
- [ ] Build sdist/wheel and inspect archive contents for prohibited names and secrets.
- [ ] Run clean-room install, import, tests, and wheel smoke with old `PYTHONPATH` removed.
- [ ] Write the acceptance report using observed versions, hashes, counts, and outcomes.
- [ ] Commit only approved V5.2 files; ensure `git status` is clean.
- [ ] Run `gh auth status`; if `vardy777/stock-screener-v5.2` does not exist, create it private and push `main`. If it exists, audit and stop rather than overwrite.
- [ ] Verify local HEAD equals remote `refs/heads/main` and re-check that the old repository branch, HEAD, tree, and porcelain status equal the recorded baseline.

## Stop Conditions

- Any old repository mutation: stop, report, and do not publish.
- Any forbidden dependency/path/inventory finding: `ZERO PROJECT DEPENDENCY = FAIL`.
- Any install/build/test/clean-room failure: fix only in the new repository; otherwise stop with `READY FOR HISTORICAL PIT DATA PHASE = NO`.
- GitHub name collision or authentication failure: keep verified local repository and report the exact blocker; never force-push.
- After verified GitHub publication, stop before historical PIT data work.
