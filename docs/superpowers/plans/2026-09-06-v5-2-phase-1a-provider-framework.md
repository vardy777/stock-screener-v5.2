# V5.2 Phase 1A Provider Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the credential-safe, deterministic provider and dataset-kind source-approval framework required for a later real-source audit, without acquiring or approving real data.

**Architecture:** Immutable canonical-hash contracts separate logical requests, provider payloads, acquisition receipts, evidence, approvals, revocations and manifests. Injected transports/clocks make acquisition behavior replayable; publication resolves one pinned dataset-kind approval at an explicit historical time and fails closed on every ambiguity.

**Tech Stack:** Python 3.11+, standard-library dataclasses/protocols/hashlib/json/pathlib/datetime, pytest 8, setuptools.

**Spec:** `docs/superpowers/specs/2026-09-06-v5-2-source-approval-provider-framework-design.md`

## Global Constraints

- Do not use a real Tushare token or make a real network request.
- Do not implement features, labels, ranking, strategy logic or trading.
- Do not create an `APPROVED` or `APPROVED_WITH_RULES` artifact for a real dataset.
- Only `TUSHARE_TOKEN` may be read, from the process environment or an explicitly supplied repository-local untracked `.env`.
- Credentials never enter IDs, values, logs, exceptions, files, fixtures, pytest output or debug dumps.
- Request, payload, receipt, evidence, approval, revocation and manifest IDs use versioned canonical content hashing.
- Research code cannot import providers, credentials, raw cache, staging or acquisition pipeline modules.
- Each production change follows RED, observed expected failure, minimal GREEN, full regression, then commit.

---

### Task 1: Canonical identity and deterministic provider request

**Files:** Create `src/v5_2/providers/__init__.py`, `src/v5_2/providers/contracts.py`, `src/v5_2/data/__init__.py`, `src/v5_2/data/identity.py`; Test `tests/providers/test_request_identity.py`.

**Interfaces:** Produces `canonical_json(value) -> bytes`, `content_hash(value) -> str`, and frozen `ProviderRequestV1.create(source_name, dataset_kind, endpoint, parameters, requested_fields, page_size, request_policy_version)` with derived `request_id`.

- [ ] Write tests proving reordered mappings/fields normalize identically, execution time cannot be supplied, and any logical field change changes `request_id`.
- [ ] Run `python -m pytest tests/providers/test_request_identity.py -v`; expect import failure for `v5_2.providers.contracts`.
- [ ] Implement recursive JSON canonicalization, reject non-finite/unsupported values, sort/deduplicate requested fields, validate positive page size and derive SHA-256 from exactly the seven frozen request fields.
- [ ] Run the focused test and `python -m pytest -q`; expect PASS.
- [ ] Commit with `git commit -m "feat: add deterministic provider request identity"`.

### Task 2: Credential boundary and Tushare transport adapter

**Files:** Create `src/v5_2/providers/credentials.py`, `src/v5_2/providers/tushare.py`; Test `tests/providers/test_credentials.py`, `tests/providers/test_tushare_adapter.py`; Modify `.gitignore`, `.env.example`.

**Interfaces:** Produces redacted `Credential`, `load_tushare_credential(env, env_file, repository_root)`, `ProviderPageV1`, `HistoricalProviderClient` protocol, and `TushareClient(transport, endpoint_registry).fetch_page(request, credential)`.

- [ ] Write tests using sentinel `SENTINEL_TUSHARE_SECRET` to prove redacted `str`/`repr`/errors/files, repository-local `.env` enforcement, empty/missing token rejection, endpoint allowlisting and injected transport use.
- [ ] Run both focused files; expect missing-module failures.
- [ ] Implement the opaque credential handle, strict dotenv parser, sanitized provider errors and injected callable transport; never implement HTTP.
- [ ] Run focused and full tests, then scan `git grep -n "SENTINEL_TUSHARE_SECRET" -- ':!tests/**'`; expect no matches.
- [ ] Commit with `git commit -m "feat: enforce provider credential boundary"`.

### Task 3: Payload artifacts, receipts and revision identity

**Files:** Create `src/v5_2/data/raw_artifacts.py`; Test `tests/data/test_raw_artifacts.py`.

**Interfaces:** Produces frozen `RawPayloadArtifactV1.create(request_id, page_identity, provider_payload, semantic_metadata)`, `AcquisitionReceiptV1.create(payload_hash, acquired_at, attempt_metadata, transport_metadata)`, `RawArtifactStore.put_payload/put_receipt`, and `observe_revision(previous, current)`.

- [ ] Write tests for identical reacquisition, acquisition-time-only receipt change, changed-payload revision, immutable-path collision, round-trip hash verification and token-field rejection.
- [ ] Run focused tests; expect import failure.
- [ ] Implement payload hash without acquisition fields, receipt hash with acquisition fields, atomic create-only JSON persistence under `raw/<source>/<kind>/<request>/<page>/<payload_hash>.json`, and fail-closed read verification.
- [ ] Run focused/full tests and verify no generated raw cache is tracked.
- [ ] Commit with `git commit -m "feat: separate payload and acquisition identity"`.

### Task 4: Pagination, retry, rate limiting and checkpoint/resume

**Files:** Create `src/v5_2/providers/retry.py`, `src/v5_2/providers/rate_limit.py`, `src/v5_2/data/checkpoints.py`, `src/v5_2/data/acquisition.py`; Test `tests/providers/test_acquisition_controls.py`, `tests/data/test_checkpoints.py`.

**Interfaces:** Produces `RetryPolicyV1.run(operation, sleeper)`, `RateLimiter.acquire(clock, sleeper)`, immutable `CheckpointV1.create(...)`, `CheckpointStore`, and `acquire_pages(request, client, credential, store, checkpoint_store, retry_policy, limiter)`.

- [ ] Write deterministic-clock tests for bounded exponential delays and error classification, plus pagination termination, repeated/non-advancing page rejection, resume continuity, request mismatch and checkpoint tamper rejection.
- [ ] Run focused tests; expect missing-module failures.
- [ ] Implement only injected-clock/sleeper controls and injected client acquisition; persist every payload/receipt before advancing a content-hashed checkpoint.
- [ ] Run focused/full tests; assert no socket/HTTP library is imported by acquisition modules.
- [ ] Commit with `git commit -m "feat: add deterministic resumable acquisition"`.

### Task 5: Deterministic normalization and PIT availability policy

**Files:** Create `src/v5_2/data/normalization.py`, `src/v5_2/data/availability.py`; Test `tests/data/test_normalization.py`, `tests/data/test_availability.py`.

**Interfaces:** Produces `NormalizerRegistry.register/normalize`, `AvailabilityPolicyV1`, and `derive_available_at(policy, source_fields, exchange_calendar)`.

- [ ] Write tests for row-order independence, duplicate/missing/unregistered/coercion failures, forbidden I/O dependencies, and date-only announcement eligibility no earlier than next verified session close.
- [ ] Run focused tests; expect missing-module failures.
- [ ] Implement pure registry dispatch and conservative availability derivation; reject unverified provider time fields and unknown calendar mappings.
- [ ] Run focused/full tests.
- [ ] Commit with `git commit -m "feat: add deterministic normalization and PIT policy"`.

### Task 6: Evidence validity and fail-closed source approval

**Files:** Create `src/v5_2/data/evidence.py`, `src/v5_2/data/source_approval.py`; Test `tests/data/test_evidence_validity.py`, `tests/data/test_source_approval.py`.

**Interfaces:** Produces `EvidenceArtifactV1`, typed `EvidenceValidityRuleV1`, `EvidenceValidityPolicyV1.evaluate(evidence, resolution_as_of, source_version_identity)`, `SourceApprovalArtifactV1.evaluate(...)`, `SourceApprovalRevocationArtifactV1.create(...)`, and immutable repositories.

- [ ] Write parameterized stale/non-stale tests for all five evidence classes and tests proving missing/failed/conflicting/tampered evidence cannot yield an approving decision.
- [ ] Run focused tests; expect missing-module failures.
- [ ] Implement type-specific versioned rules, canonical evidence bundles and an evaluator that accepts no boolean approval override; keep all fixture decisions synthetic.
- [ ] Run focused/full tests.
- [ ] Commit with `git commit -m "feat: enforce evidence-backed source approvals"`.

### Task 7: Deterministic approval resolution, revocation and manifests

**Files:** Create `src/v5_2/data/manifests.py`; Modify `src/v5_2/data/source_approval.py`; Test `tests/data/test_approval_resolution.py`, `tests/data/test_manifests.py`.

**Interfaces:** Produces `ApprovalResolver.resolve(source_name, dataset_kind, requested_coverage, resolution_as_of) -> approval_id` and `DatasetManifestV1.create(..., approval_id, approval_resolution_as_of, ...)`.

- [ ] Write tests for explicit supersession, effective-time revocation, as-of resolution, ambiguous resolution failure, dataset-kind isolation, coverage containment and old-manifest reproducibility after later artifacts arrive.
- [ ] Run focused tests; expect missing interface failures.
- [ ] Implement deterministic graph resolution without creation-order tie-breaking; manifests pin and verify the exact immutable approval and reject all non-approving/PIT-failing inputs.
- [ ] Run focused/full tests.
- [ ] Commit with `git commit -m "feat: pin immutable approvals in dataset manifests"`.

### Task 8: Governance boundary and credential leak scanning

**Files:** Create `tests/governance/test_phase_1a_boundaries.py`; Modify `scripts/verify_standalone.py`, `scripts/clean_room_acceptance.py` only if tests demonstrate a missing scan.

**Interfaces:** Adds AST import-direction enforcement and repository/output scans; no runtime API.

- [ ] Write tests proving research-facing packages cannot import `v5_2.providers`, credentials, raw artifacts, checkpoints or acquisition, and proving tracked secret/cache patterns and real-network calls fail the verifier.
- [ ] Run focused tests; verify RED against the current verifier.
- [ ] Minimally extend the verifier and clean-room scan to enforce the demonstrated gaps.
- [ ] Run focused/full tests and both verification scripts.
- [ ] Commit with `git commit -m "test: enforce phase 1a governance boundaries"`.

### Task 9: Acceptance report and final clean-room gate

**Files:** Create `docs/reports/V5_2_PHASE_1A_ACCEPTANCE.md`; Modify `README.md` only for stable local commands.

**Interfaces:** Records exact commit, commands, counts and frozen readiness states; does not grant a source approval.

- [ ] Run `python -m pytest -q`, `python scripts/verify_standalone.py`, `python scripts/clean_room_acceptance.py`, `git diff --check`, tracked-file secret/network scans and `git status --short`.
- [ ] Record only observed evidence for `PROVIDER FRAMEWORK`, `SOURCE APPROVAL FRAMEWORK`, `CREDENTIAL SAFETY`, `IMMUTABLE RAW / REVISION IDENTITY`, `DETERMINISTIC REPLAY`, `GOVERNANCE BOUNDARY` and `CLEAN-ROOM`.
- [ ] Freeze `HISTORICAL PIT DATA = FAIL`, `REAL DATASET APPROVALS = NONE`, and `READY FOR LABEL ENGINE = NO`; write `READY FOR REAL SOURCE AUDIT = YES` only if every Phase 1A gate passed in the same acceptance run.
- [ ] Re-run the full acceptance commands after documentation changes.
- [ ] Commit with `git commit -m "docs: record phase 1a acceptance"` and push only after the working tree is clean and the commit is locally verified.
