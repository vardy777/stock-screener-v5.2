# V5.2 Phase 1 Historical Status Coverage Remediation Implementation Plan

> **Execution:** inline on `phase2a-implementation`; TDD for every behavior
> change. Stop after publishing and verifying the remediation. Do not resume
> Phase 2B Task 5.

**Spec:**
`docs/superpowers/specs/2026-09-23-v5-2-phase1-historical-status-coverage-remediation-design.md`

**Goal:** Turn the already approved Phase 1 historical status interval/event
truth into a portable, exact-lineage authority that resolves any covered
identity/session without network access, mutable/latest lookup, sibling-checkout
runtime access, or synthetic provider `ACTIVE` facts.

**Architecture:** Build deterministic, content-addressed normalized shards from
the exact 118 payloads and 163 receipts in a temporary repository-local staging
root. Store canonical rows as deterministic gzip (`mtime=0`) grouped by
component kind, with a content-addressed authority descriptor that pins shard
byte hashes, source-row hashes, the closed-world inventory, parent governance,
coverage and policy. A read-only resolver verifies all pins, indexes the shards,
and produces a content-addressed derivation result for one identity/session.
Ordinary status is a derivation over positive lifecycle evidence plus negative
closed-world ST/suspension authority; it is never a provider observation.

**Global constraints:** No network/provider calls. No frozen artifact mutation.
No status, identity, Phase 2A or Phase 2B semantic change. Coverage ends at
2026-09-10. Runtime/research must use only committed portable artifacts. Build
staging must resolve inside the repository and is never referenced by published
artifacts. No wall-clock value enters an artifact identity.

## File map

- `src/v5_2/data/historical_status_authority.py` — immutable contracts,
  deterministic shard encoding/verification, exact-input preflight, resolver,
  derivation result and coverage/replay/composition contracts.
- `scripts/remediate_historical_status_coverage.py` — offline-only publisher;
  consumes explicit repository-local staging root and exact frozen parents.
- `tests/data/test_historical_status_authority.py` — contract/resolver TDD,
  PIT semantics, tamper/revocation and boundary tests.
- `tests/real_audits/test_historical_status_remediation.py` — exact real-input
  reconstruction, coverage accounting, replay and artifact-chain tests.
- `data/phase_1_status_lineage_remediation/authority/` — portable compressed
  normalized shards.
- `data/phase_1_status_lineage_remediation/governance/` — authority descriptor,
  coverage ledger, replay evidence, approval, manifest and composition artifact.
- `docs/reports/V5_2_PHASE1_HISTORICAL_STATUS_COVERAGE_REMEDIATION.md` — commands,
  artifact IDs, counts, gates and STOP state.

## Task 1: Freeze portable contracts and deterministic shard encoding

**Files:** create `src/v5_2/data/historical_status_authority.py`; create
`tests/data/test_historical_status_authority.py`.

1. Write RED tests for deterministic gzip bytes, create-or-identical storage,
   shard hash verification, wrong bytes, wrong component kind and duplicate
   source-row identity.
2. Define focused immutable contracts:
   `HistoricalStatusComponentV1`, `HistoricalStatusShardV1`,
   `HistoricalStatusAuthorityV1`, `HistoricalStatusDerivationV1`,
   `HistoricalStatusCoverageLedgerV1`, `HistoricalStatusReplayEvidenceV1`, and
   `HistoricalStatusCompositionV1`.
3. Canonical shard rows must include canonical security identity, effective/event
   fields, source-row hash and availability inputs. Use canonical JSON and gzip
   with fixed compression settings and `mtime=0`; the filename is the compressed
   byte SHA-256. Store schema/content identities separately from storage-byte
   identity.
4. Authority verification must exact-pin parent panel/manifest/approval/PIT
   evidence, source version, coverage, raw/receipt inventory hashes and every
   shard descriptor.
5. Run `pytest tests/data/test_historical_status_authority.py -q` and commit.

## Task 2: Implement exact frozen-input preflight and normalization

**Files:** extend contract module and tests; create
`tests/real_audits/test_historical_status_remediation.py`.

1. Write RED tests for exact set equality (not subset) of 118 raw hashes and 163
   receipt hashes; missing, extra, duplicate, wrong-source, hash mismatch,
   revoked parent, wrong panel/manifest/approval and wrong source version.
2. Implement an offline preflight loader. It must resolve its staging root under
   repository root and reject symlinks/path escape. Read payloads/receipts through
   their existing immutable contracts, not raw `json.loads` trust.
3. Reconstruct and assert the frozen hashes exactly:

   ```text
   lifecycle = bb96052035488424dcc7aaa9d577c9ca990fe6669df8bf4e466f0e3c8171d2a5
   ST        = fb81454d499f645283e2c2ede0be3422486546e2a70180926a84a93c24cc199d
   suspension= 87e2a971a17660a632d058f95135ebb6d984d40534a956e052df17a19076c38d
   panel     = cd062ced913e865984d536bc85305f9c6e720e26cee111527aac120fd66fe707
   ```

4. Normalize lifecycle, ST intervals, full-day suspensions, partial-session
   observations and resumptions without altering the frozen selection rules.
   Every normalized component pins its provider-row content hash.
5. Run focused real-input fixtures and commit. No published artifacts yet.

## Task 3: Implement PIT-safe arbitrary-session resolver

**Files:** extend contract module and focused tests.

1. Write RED tests for ordinary, ST enter/exit, full-day suspension, partial
   suspension, resumption, listing boundary, delisting boundary, unknown identity,
   pre-coverage/post-coverage and naive cutoff.
2. Implement a resolver that loads only verified portable shards and exact frozen
   parent governance. It must not read raw staging or select latest artifacts.
3. Preserve availability exactly:
   - full-day suspension/resumption and proven ordinary market observation use
     frozen `MARKET_OBSERVABLE_BY_CLOSE` at 16:30 Asia/Shanghai;
   - cutoff-unproven date-only ST changes use the next approved session at 16:30;
   - acquisition time is ignored;
   - a state whose supporting evidence is not yet available is not applied.
4. For ordinary state, include lifecycle component identity, ST authority/shard
   IDs, suspension closed-world inventory/request ID, coverage and policy IDs in
   the derivation body. Do not create an `ACTIVE` source component.
5. Derivation identity must change for any semantic input change and remain byte
   identical for the same inputs. Run focused tests and commit.

## Task 4: Materialize the portable authority and coverage ledger

**Files:** create publisher script, real-audit tests and output directories.

1. Write RED integration tests that invoke the publisher twice into separate temp
   directories and compare every output byte.
2. Copy only the exact retained local raw/receipt files into an ignored,
   repository-local staging directory. This is an operational preparation step,
   not a committed source dependency. Verify set equality before normalization.
3. Publish deterministic shards plus authority descriptor. Recommended shard
   partition is component kind plus identity-prefix bucket so arbitrary lookup is
   bounded and deterministic; do not partition by nondeterministic row count.
4. Publish a coverage ledger reconciling:
   - 5,551 identities and 4,055 approved sessions;
   - 5,551 lifecycle intervals;
   - 1,677 ST intervals;
   - 468,188 suspension observations split into 443,117 S and 25,071 R;
   - 2,644 partial-session S observations;
   - 333 delisting boundaries;
   - ordinary derivation coverage, zero unresolved identity/session, zero gaps,
     zero quarantine and explicit out-of-scope boundary.
5. Any count/hash mismatch stops without publishing governance. Run integration
   tests and commit portable authority artifacts with code.

## Task 5: Publish derived governance without claiming new source coverage

**Files:** publisher, governance tests and generated governance artifacts.

1. Write RED tests for exact parent pins, current revocation validity, derived
   source identity, approval scope, manifest fact/shard hashes and immutable
   predecessor preservation.
2. Create fresh evidence artifacts for representation integrity, deterministic
   replay, coverage accounting, PIT derivation and license/use inheritance. Their
   input IDs must include the frozen parent approval/manifest/panel and authority.
3. Create a `SourceApprovalArtifactV1` for source
   `v5_2_historical_status_derivation`, dataset kind `daily_security_status`,
   coverage 2010-01-04 through 2026-09-10. Its rule set explicitly says
   `representation_of_parent_source_truth`, not new provider observations.
4. Create a `DatasetManifestV1` pinning authority/shard hashes, the new approval,
   exact coverage/counts and parent lineage. Use a new composition artifact rather
   than mutating or pretending to supersede the provider approval. Composition
   declares the new derived representation authoritative for lineage packaging
   while preserving all predecessor meaning.
5. Create replay evidence from two isolated materializations; operational run
   timestamps stay outside canonical bodies. Run governance tests and commit.

## Task 6: Prove exact lineage, failures and regressions

**Files:** tests and remediation report.

1. Add real arbitrary-session proof cases for ordinary, ST, suspension,
   resumption, listing and delisting. Each must resolve approval ID, manifest ID,
   derivation ID, source/evidence IDs, `available_at`, content hash and valid parent
   revocation state.
2. Complete negative tests for missing/extra/wrong raw or receipt, tampered
   lifecycle/ST/suspension component, wrong source version/parent artifacts,
   revoked parent, post-coverage request, ST backdating, partial-to-full promotion
   and ordinary result without closed-world inventory.
3. Run focused remediation, historical status and governance tests.
4. Run Phase 0–1C and Phase 2A/Phase 2B Tasks 1–4 regression commands already
   frozen in repository reports; record exact commands/counts. Do not execute Task
   5 or any pilot.
5. Run full pytest, clean-room, standalone, build/wheel/install/smoke, zero-project
   dependency, credential scan and `git diff --check`.
6. Write
   `docs/reports/V5_2_PHASE1_HISTORICAL_STATUS_COVERAGE_REMEDIATION.md` with every
   command result and artifact ID. Commit, push only `phase2a-implementation`,
   verify local HEAD equals remote feature HEAD, `origin/main` unchanged and tracked
   worktree clean. STOP for independent review.

## Review focus

- No runtime or research path reads the staging directory or sibling checkout.
- Absence becomes ordinary only through exact closed-world lineage.
- No date-only ST event is visible at same-day cutoff without frozen proof.
- Partial-session suspension never becomes full-day.
- Parent approval is validated against an exact revocation set.
- New approval describes a derived representation, not new provider acquisition.
- Compressed artifact bytes and all IDs are deterministic across isolated runs.
- Coverage and counts reconcile without unexplained remainder.
- No Phase 2B Task 5 code, pilot or final acceptance runs.

