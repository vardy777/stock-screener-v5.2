# V5.2 Phase 2B Private CAS Portability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replay the approved 2010-01 label month in a fresh checkout using only public hash metadata and externally supplied, verified private bytes.

**Architecture:** A strict public manifest identifies the exact untracked source files used by existing five-domain loaders. A narrow CAS stores physical exact bytes outside Git and stages verified copies into a fresh checkout; existing semantic loaders remain unchanged.

**Tech Stack:** Python 3.11 standard library, pytest, Git, Windows PowerShell.

**Spec:** `docs/superpowers/specs/2026-09-26-v5-2-phase-2b-private-cas-portability-design.md`

## Global Constraints

- No public corpus bytes, Git LFS, or Release assets.
- No provider, market-data, or web acquisition.
- No fallback to main checkout, sibling worktree, latest artifact, or link.
- No Phase 1 authority or Phase 2A semantic changes; legacy Gate V1 stays fail-closed.
- Feature branch only; `origin/main` unchanged; no Checkpoint 19 pilot.

## Review Focus

- A same-size but different-byte object must fail SHA-256 validation.
- A manifest path containing `..`, a drive, or a duplicate role must fail before staging.
- A CAS object with a symlink, junction, or hardlink must fail.
- A missing `V5_2_PRIVATE_CAS_ROOT` must never pass clean-room acceptance.
- A private object accidentally tracked by Git must fail the public hygiene guard.

---

### Task 1: CAS object boundary

**Files:** Create `src/v5_2/data/private_cas.py`; create `tests/data/test_private_cas.py`.

**Interfaces:** `put_exact(root: Path, payload: bytes) -> str`; `read_exact(root: Path, sha256: str, byte_size: int) -> bytes`; `resolve_cas_root(environ: Mapping[str,str]) -> Path`.

- [ ] Write tests for exact path, create-or-identical, missing/tampered bytes, wrong size, and linked object rejection.
- [ ] Run focused tests; verify RED from missing module.
- [ ] Implement exclusive physical writes and verified reads with no network or path fallback.
- [ ] Run focused tests; verify GREEN; commit.

### Task 2: Public exact inventory

**Files:** Create `src/v5_2/data/private_corpus_manifest.py`; create `tests/data/test_private_corpus_manifest.py`; create one content-addressed public manifest under `governance/phase2b/`.

**Interfaces:** `PrivateCorpusEntryV1`; `Phase2BPrivateCorpusManifestV1`; `derive_required_private_paths(source_root: Path) -> tuple[...,...]`; `build_manifest_exact(source_root: Path) -> Phase2BPrivateCorpusManifestV1`; exact manifest write/read.

- [ ] Write tests for canonical ordering, duplicate roles, traversal/absolute paths, tampering, missing source, and exact approved file inventory.
- [ ] Run focused tests; verify RED.
- [ ] Implement from approved authority pins only; exclude tracked and unrelated local files.
- [ ] Run focused tests; verify GREEN; generate and commit only metadata.

### Task 3: Private population, resolver, and Git hygiene

**Files:** Extend `private_corpus_manifest.py`; create `tests/data/test_private_corpus_resolver.py`; update `.gitignore` only if needed.

**Interfaces:** `populate_private_cas(manifest, source_root, cas_root) -> ...`; `stage_verified_private_corpus(manifest, cas_root, checkout_root) -> ...`; `assert_private_objects_untracked(manifest, checkout_root) -> ...`.

- [ ] Write tests for exact set, byte verification, incomplete CAS, corrupt CAS, link/path escape, physical stage copy, no fallback, and accidental Git tracking.
- [ ] Run focused tests; verify RED.
- [ ] Implement and populate the private CAS from already-approved local source bytes only.
- [ ] Run focused tests and hygiene guard; verify GREEN; commit.

### Task 4: Fresh-checkout replay and Checkpoint 18 handoff

**Files:** Create `tests/labels/test_phase2b_private_cas_cleanroom.py`; update `docs/reports/V5_2_PHASE_2B_CHECKPOINT_18_GATE_V2_INTERIM.md`.

**Interfaces:** Fresh local clone/checkout, exact manifest, explicit CAS root, existing five-domain producer and Gate V2 evidence.

- [ ] Write a RED integration test proving absent CAS fails, and a gated real test for exact 2010-01 IDs.
- [ ] Stage only verified private objects into a fresh checkout; install a fresh environment; run real month, coverage, and independent row comparison.
- [ ] Verify exact identities and 34,271/26,899/6,950/422; report full commands and IDs.
- [ ] Run focused/full/standalone/build/credential/diff checks; commit and push only the feature branch.

After Task 4, continue the separately frozen Gate V2, mutation, census, and
Task 12 work. This plan alone never declares Checkpoint 18 PASS.
