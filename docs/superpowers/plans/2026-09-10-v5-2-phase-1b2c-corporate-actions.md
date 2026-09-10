# V5.2 Phase 1B-2C Corporate Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a credential-safe, PIT-correct, scoped corporate-action dataset that truthfully exposes validated coverage and fails closed outside it.

**Architecture:** Extend the existing immutable provider, evidence, approval, and manifest path with small corporate-action-specific contracts. Probe candidate provider endpoints before allowlisting them, normalize only verified fields, resolve revisions at an explicit cutoff, and publish only the action-type/interval subset that passes every applicable gate.

**Tech Stack:** Python 3.11+, standard library, immutable dataclasses, pytest 8, existing V5.2 content-addressed artifacts.

**Spec:** `docs/superpowers/specs/2026-09-10-v5-2-phase-1b2c-corporate-actions-design.md`

## Global Constraints

- Historical target is exactly `2010-01-04 .. 2025-12-31`; catch-up is `2026-01-01 .. latest available approved session`.
- Approval and coverage are expressed as `action_type x interval`; target scope never implies validated or materialized coverage.
- Supported candidates are `CASH_DIVIDEND` and `BONUS_SHARE`; `RIGHTS_ISSUE`, `STOCK_SPLIT`, and `SHARE_CONVERSION` remain unsupported or pending unless real evidence proves them.
- Unsupported or uncovered security-periods raise `NOT_RESEARCH_SAFE`; missing data never means no event.
- Historical date-only publication uses next approved session 16:30 Asia/Shanghai; acquisition time never backfills availability.
- Daily bars remain `UNADJUSTED_RAW`; vendor final adjusted series and `adj_factor` are not PIT truth.
- No scheduler, disclosure, feature, label, ranking, ML, backtest, or Phase 1B-2D work.
- Credentials remain transport-only and never enter artifacts, logs, exceptions, tests, manifests, reports, or commits.

---

### Task 1: Immutable fact and PIT availability contracts

**Files:**
- Create: `src/v5_2/data/corporate_action_facts.py`
- Create: `src/v5_2/data/real_audits/corporate_action_availability.py`
- Create: `tests/data/test_corporate_action_facts.py`
- Create: `tests/real_audits/test_corporate_action_availability.py`

**Interfaces:**
- Produces: `ActionType`, `KnowledgeClass`, `CorporateActionFactV1.create(...)`, `CorporateActionAvailabilityPolicyV1.available_at(...)`.
- Consumes: `content_hash` and an injected ordered approved-session calendar.

- [ ] **Step 1: Write failing fact tests** for timezone enforcement, deterministic hashes, separate cash/share values, supersession, cancellation, and tamper detection.
- [ ] **Step 2: Run** `python -m pytest tests/data/test_corporate_action_facts.py -q` and confirm missing-module failure.
- [ ] **Step 3: Implement the minimal immutable dataclass** with enum validation, non-negative values, at least one effective date, cancellation marker, and `verify()`.
- [ ] **Step 4: Write failing availability tests** proving timestamped publication, date-only next-session 16:30, effective-only non-advance knowledge, production observation lineage requirements, and backfill acquisition-time non-leakage.
- [ ] **Step 5: Implement the small policy object** returning an explicit availability result and raising on missing next session or incomplete observation lineage.
- [ ] **Step 6: Run both focused test files** and require PASS.
- [ ] **Step 7: Commit** `feat: add corporate action fact and PIT policy`.

### Task 2: Bounded provider probe and allowlist decision

**Files:**
- Create: `src/v5_2/data/real_audits/corporate_action_probe.py`
- Create: `scripts/probe_phase_1b2c_corporate_actions.py`
- Create: `tests/real_audits/test_corporate_action_probe.py`
- Modify: `src/v5_2/providers/datahub.py`
- Modify: `tests/providers/test_datahub_adapter.py`
- Create: `data/phase_1b2c/governance/provider_probe.json`

**Interfaces:**
- Produces: `CorporateActionEndpointProbeV1`, verified endpoint capabilities, immutable raw/receipt IDs, and only evidence-backed `DATAHUB_ENDPOINTS` entries.
- Consumes: `ProviderRequestV1`, `RawArtifactStore`, acquisition controls, and `DATAHUB_API_KEY` through the existing credential boundary.

- [ ] **Step 1: Write failing tests** that reject an endpoint without successful schema evidence, redact transport errors, hash stable semantic probe results independently of observation time, and classify unsupported candidates without allowlisting them.
- [ ] **Step 2: Implement the bounded candidate probe** for `dividend`, `rights`/`rights_issue`, `adj_factor`, and share-structure candidates, with no credential-bearing output.
- [ ] **Step 3: Run the real bounded probe once** across representative early/mid/recent/2026 queries; persist raw payloads and receipts only for successful responses.
- [ ] **Step 4: Inspect actual returned fields and pagination** and add only successful semantically usable endpoints to `DATAHUB_ENDPOINTS`; keep `adj_factor` audit-only.
- [ ] **Step 5: Add adapter contract tests** using fixture transports matching the verified schema.
- [ ] **Step 6: Run** `python -m pytest tests/real_audits/test_corporate_action_probe.py tests/providers/test_datahub_adapter.py -q` and require PASS.
- [ ] **Step 7: Commit** `feat: audit corporate action provider capabilities`.

### Task 3: Frozen inventory, deterministic normalization, and incremental acquisition

**Files:**
- Create: `src/v5_2/data/real_audits/corporate_action_entry.py`
- Create: `src/v5_2/data/real_audits/corporate_action_normalization.py`
- Create: `src/v5_2/data/real_audits/corporate_action_acquisition.py`
- Create: `tests/real_audits/test_corporate_action_entry.py`
- Create: `tests/real_audits/test_corporate_action_normalization.py`
- Create: `tests/real_audits/test_corporate_action_acquisition.py`

**Interfaces:**
- Produces: `CorporateActionRequestInventoryV1`, `build_corporate_action_inventory(...)`, `normalize_corporate_action_rows(...)`, and `acquire_corporate_actions(...)`.
- Consumes: verified endpoint capabilities, target/baseline/rolling dates, active approvals, raw store, pagination, checkpoint/resume, retry, and rate limiting.

- [ ] **Step 1: Write failing inventory tests** for canonical request IDs, baseline/catch-up separation, exact upstream approval pins, and immutable incremental continuation.
- [ ] **Step 2: Implement the smallest inventory builder** using only confirmed endpoints and requested fields.
- [ ] **Step 3: Write failing normalization tests** for provider values, units, date fields, action classification, revision/cancellation links, malformed rows, and unknown types.
- [ ] **Step 4: Implement pure deterministic normalization** from verified row schema into candidate `CorporateActionFactV1` values without assigning availability from acquisition time.
- [ ] **Step 5: Write and implement acquisition tests** for pagination, checkpoint/resume, idempotent replay, revision observation, and overlap constraints.
- [ ] **Step 6: Run the three focused files** and require PASS.
- [ ] **Step 7: Commit** `feat: add corporate action acquisition boundary`.

### Task 4: Scoped evidence, frozen samples, and independent validation

**Files:**
- Create: `src/v5_2/data/real_audits/corporate_action_evidence.py`
- Create: `src/v5_2/data/real_audits/corporate_action_sampling.py`
- Create: `scripts/freeze_phase_1b2c_inventory.py`
- Create: `scripts/audit_phase_1b2c_corporate_actions.py`
- Create: `tests/real_audits/test_corporate_action_evidence.py`
- Create: `tests/real_audits/test_corporate_action_sampling.py`
- Create: `data/phase_1b2c/governance/sample_inventory.json`

**Interfaces:**
- Produces: `CorporateActionPITEvidenceV1`, `CorporateActionSampleInventoryV1`, cross-source dispositions, coverage maps, gaps, exceptions, quarantines, and deterministic IDs.
- Consumes: normalized candidates, raw/receipt/source-version lineage, SSE/SZSE/CNINFO evidence, and policy IDs.

- [ ] **Step 1: Write failing evidence tests** for exact target/baseline/rolling dates, per-type validated/materialized intervals, gaps, unsupported intervals, content tamper, zero unexplained mismatches, and scoped `complete` semantics.
- [ ] **Step 2: Implement the immutable evidence artifact** with canonical interval validation and fail-closed completeness rules.
- [ ] **Step 3: Write failing sampling tests** for pre-result deterministic selection across action semantics, exchanges, early/mid/recent/2026 periods, multi-event cases, and revisions when candidates exist.
- [ ] **Step 4: Freeze the sample inventory before comparison** and persist its ID.
- [ ] **Step 5: Perform bounded independent validation** against SSE/SZSE/CNINFO; save URL/source, raw value, semantic mapping, evidence ID, hash, and disposition without treating DataHub internal comparisons as independent.
- [ ] **Step 6: Build the actual evidence artifact** and leave unavailable/mismatching types or intervals pending/failed without changing the inventory.
- [ ] **Step 7: Run the focused tests and audit replay** and require deterministic results.
- [ ] **Step 8: Commit** `feat: add scoped corporate action evidence`.

### Task 5: Revision resolver, fail-closed repository, and causal adjustment inputs

**Files:**
- Create: `src/v5_2/data/corporate_action_repository.py`
- Create: `src/v5_2/data/real_audits/corporate_action_adjustment.py`
- Create: `tests/data/test_corporate_action_repository.py`
- Create: `tests/real_audits/test_corporate_action_adjustment.py`

**Interfaces:**
- Produces: `CorporateActionRepository.query(...)`, `NotResearchSafeError`, and `CausalCorporateActionAdjustmentPolicyV1.effects_for_bar(...)`.
- Consumes: facts, evidence, exact approval/manifest pins, revocations, requested security-period/type, and research cutoff.

- [ ] **Step 1: Write failing repository tests** for latest then-known revision, cancellation, future-revision invisibility, unsupported type, coverage gap, quarantine, unavailable fact, revoked approval, and tampered lineage.
- [ ] **Step 2: Implement deterministic revision-chain resolution** and the typed `NOT_RESEARCH_SAFE` boundary; valid covered no-event results are allowed only after coverage proof.
- [ ] **Step 3: Write failing adjustment tests** proving raw bars are unchanged, effects require economic effectiveness and cutoff availability, cash and share effects stay distinct, final adjusted histories are rejected, and missing unsupported events fail closed.
- [ ] **Step 4: Implement the minimal causal effect projection** without labels, returns, or backtesting.
- [ ] **Step 5: Run both focused test files** and require PASS.
- [ ] **Step 6: Commit** `feat: enforce causal corporate action queries`.

### Task 6: Gate, approval, manifest, and publisher integration

**Files:**
- Create: `src/v5_2/data/real_audits/corporate_action_validation.py`
- Create: `scripts/evaluate_phase_1b2c_gates.py`
- Create: `scripts/publish_phase_1b2c_corporate_actions.py`
- Create: `tests/real_audits/test_corporate_action_gate_integration.py`
- Create: `tests/real_audits/test_corporate_action_approval.py`
- Modify: `src/v5_2/data/manifests.py`
- Modify: `tests/data/test_manifests.py`

**Interfaces:**
- Produces: `CorporateActionGateResultV1`, scoped `SourceApprovalArtifactV1`, approved facts, and `DatasetManifestV1` with corporate-action coverage lineage.
- Consumes: verified `CorporateActionPITEvidenceV1`, frozen inventory, source versions, raw/receipt/fact hashes, revocation registry, and existing approval validity machinery.

- [ ] **Step 1: Write failing gate tests** for every required emitted gate and exact PENDING/REJECTED distinction, including missing/tampered/revoked/mismatched evidence.
- [ ] **Step 2: Implement artifact-driven gate evaluation** with no hard-coded pass counts or publisher-side policy reinterpretation.
- [ ] **Step 3: Write failing approval/manifest tests** proving supported/unsupported action types, per-type intervals, gaps, latest approved session, evidence ID, and exact approval pins are preserved.
- [ ] **Step 4: Extend `DatasetManifestV1` minimally** with optional corporate-action scope fields validated only when `dataset_kind == "corporate_action"`.
- [ ] **Step 5: Implement publisher wiring** that consumes a verified PASS gate and approving artifact and otherwise publishes zero facts/no manifest.
- [ ] **Step 6: Run focused integration tests** and verify both a scoped approval path and all fail-closed paths.
- [ ] **Step 7: Commit** `feat: integrate corporate action approval gates`.

### Task 7: Real catch-up, replay, and acceptance record

**Files:**
- Create: `scripts/replay_phase_1b2c_corporate_actions.py`
- Modify: `docs/reports/V5_2_PHASE_1B2_ACCEPTANCE.md`
- Create/Modify: `data/phase_1b2c/**` immutable artifacts generated by approved scripts.

**Interfaces:**
- Produces: actual gate output, approval/facts/manifest only if warranted, deterministic replay result, and exact acceptance evidence.
- Consumes: tasks 1-6 and live provider credentials only through environment-backed transport.

- [ ] **Step 1: Acquire the bounded historical/catch-up scope** supported by the verified endpoint, without claiming unmaterialized 2010-2025 coverage.
- [ ] **Step 2: Run the evaluator and publisher**; preserve PENDING and zero publication if any required scoped gate is incomplete.
- [ ] **Step 3: Replay from pinned raw artifacts without network** and assert identical normalized facts, evidence, gate, approval, and manifest IDs.
- [ ] **Step 4: Run focused corporate-action tests** and record exact command/output.
- [ ] **Step 5: Run full verification:** `python -m pytest -q`, `python scripts/verify_standalone.py`, `python -m build`, `python scripts/clean_room_acceptance.py`, wheel install/smoke, credential/sentinel scan, and `git diff --check`.
- [ ] **Step 6: Update the acceptance report** with endpoint evidence, coverage by type/interval, gaps, 2026 catch-up status, every gate, fact count, manifest ID, command outputs, and blockers.
- [ ] **Step 7: Commit** `docs: record phase 1b2c acceptance`.
- [ ] **Step 8: Push `main`**, verify `git rev-parse HEAD` equals `git rev-parse origin/main`, verify `git status --short` is empty, then stop without Phase 1B-2D.
