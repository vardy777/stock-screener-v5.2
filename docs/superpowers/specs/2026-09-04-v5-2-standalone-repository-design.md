# V5.2 Standalone Repository Design

## Decision

Create a new repository named `vardy777/stock-screener-v5.2`. The existing
`vardy777/stock-screener-v5-1` repository, its branches, tags, releases and
artifacts remain unchanged. V5.2 receives a new Git history and does not use a
Git submodule, editable install, relative filesystem reference, runtime import,
test import, data path or documentation dependency on G1, V2, V4, V5 or V5.1.

## Product boundary

V5.2 is the after-close full-market A-share Alpha Research and Swing Candidate
Engine approved in the V5.2 product specification. Its Phase 1 objective is to
prove data correctness, research correctness and whether reproducible 1-5 day
cross-sectional alpha exists. Realtime full-market scanning, broker trading,
automatic ordering, ML-first development and production capital remain out of
scope.

## Repository contents

```text
stock-screener-v5.2/
  .gitignore
  AGENTS.md
  README.md
  pyproject.toml
  requirements.lock
  docs/
    V5_2_PRODUCT_SPEC.md
    V5_2_ARCHITECTURE.md
    V5_2_DATA_CONTRACTS.md
    V5_2_RESEARCH_PROTOCOL.md
    V5_2_MIGRATION_PLAN.md
    V5_1_PRODUCT_RETIREMENT.md
    V5_1_REUSE_INVENTORY.{json,md}
    superpowers/specs/
    superpowers/plans/
  src/v5_2/
    foundations/
    facts/
    data/
    universe/
    features/
    labels/
    ranking/
    strategies/
    evaluation/
    portfolio/
    execution/
    dashboard/
  tests/
    foundations/
    facts/
    data/
    universe/
    features/
    labels/
    ranking/
    evaluation/
    governance/
```

The repository contains no `.hermes`, `g1`, `v2`, `v4`, `v5`, `v5_1`, old RC
ZIP, historical runtime fact, notification credential, scheduler definition or
legacy entrypoint.

## Copy and ownership rule

Useful code is copied only after classification and becomes V5.2-owned code
under `src/v5_2`. No source file retains imports from the old namespaces.
Copied code receives:

1. a V5.2 module name and version-neutral public interface;
2. characterization tests establishing which behavior was retained;
3. removal of realtime product assumptions and old data paths;
4. explicit provenance in migration documentation, without a runtime link;
5. V5.2-native error types, schemas, configuration and storage roots.

The minimum copied foundation comprises strict validation/timezone helpers,
TradingCalendar and its validator, canonical content hashing, atomic immutable
fact persistence, A-share lot rules, and only the paper-ledger primitives that
remain useful for a deferred execution phase. Security Master and daily
tradability logic are adapted into V5.2-native fact contracts. Realtime quote
sources, MorningPool, CloseScan and V5.1 orchestration are not copied.

## Dependency independence

The package must install from its own `pyproject.toml` in an empty environment.
All resources needed by tests and normal operation live in the repository or
are acquired through declared V5.2 adapters. No path may escape the repository
root. Tests reject:

- imports whose top-level name is `g1`, `v2`, `v4`, `v5` or `v5_1`;
- references to the old repository path or `.hermes`;
- dependency declarations using local paths, Git URLs to the old repository,
  editable installs or namespace packages outside `v5_2`;
- packaged files matching retired project names, RC archives, secrets, runtime
  data or Windows task-registration scripts.

## Data and research isolation

V5.2 owns its schemas, storage root and manifest identity. Imported historical
datasets are inputs with content hashes and source lineage, never live reads of
old project folders. The ranking process cannot import label/evaluation future
windows. Optional candidate-only D+1 confirmation consumes a persisted
WatchlistFact and cannot scan the market.

## Verification gates

Before GitHub publication:

1. repository inventory contains only approved V5.2 paths;
2. forbidden-name/import/path scan passes;
3. package builds and installs in a newly created clean virtual environment;
4. every test passes from the standalone checkout with the old repository
   unavailable on `PYTHONPATH`;
5. a clean-room copy outside the old repository reproduces test results;
6. `git status` is clean and no secret or generated runtime artifact is tracked;
7. the GitHub remote is the new `stock-screener-v5.2` repository.

Passing these gates proves repository independence and engineering
reproducibility. It does not prove historical data coverage, alpha, production
readiness or authorization for trading.

## GitHub publication

Initialize a new repository with default branch `main`, one focused initial
commit, and remote `https://github.com/vardy777/stock-screener-v5.2.git`.
Create the GitHub repository as private unless the user explicitly requests
public visibility. Never delete or rewrite anything in the old repository.

## Failure and rollback

If dependency isolation, clean installation or tests fail, do not publish a
completion claim. Keep the new local repository for repair. If GitHub creation
fails because the name exists or authentication is unavailable, report the
exact blocker without changing the old remote. Because the old repository is
untouched, rollback consists only of abandoning the unpublished new repository;
no historical restoration is required.
