# V5.2 Phase 1B Historical Daily Bar Lineage Remediation

Status: PASS

- Baseline: 13c40f0732b6a2e9f72f28c9fc97adcc5e346d49
- Source semantic identity: 4f3875e94fe5ff8bf1341dea8ee769b209c301b24204bbc8af65a476e106b1b9
- Source content-set identity: de95192812d99f1c7f4e4363b8160a1b8728d76f503aa7edbf5c851a719527bb
- Source binding: cd5d2cce173f38a896167399740f0f0f1b550bdf5e37b5bdaaa10a689861b771
- Historical availability evidence V2: c52bcc200d4201dae909ee00a95b6a314b8648502cdb9b9ccadd3a6ab8522082
- Replacement approval: 31d91fd99630e3b63b585ae598e7728fe1922454c3dbee276d0ffe9e7b24d79f
- Replacement manifest: 118744559f5869bcbe75b402870524a18ec6f42e813764568bec6c7f070bf5ad
- Old approval revocation: 27aed2a0a75d7e932720586d31b4cd27e3c06bb73f07303522bb1014e7eb0565
- Historical Exit re-acceptance: 288ad596d6c7802666b509a30d490459900605f96f75547315a3912b75cb08db

The remediation reuses the exact 5,884 immutable raw payload hashes and the existing 14,010,422-row panel. The replacement manifest retains the original fact content hashes and business-value lineage. No provider request or fact rematerialization occurred.

The old approval, manifest, availability evidence, and panel remain byte-identical and auditable. The replacement approval supersedes the old approval; an immutable revocation with reason LEGACY_APPROVAL_SOURCE_CONTENT_SET_MISMATCH prevents current resolution of the old approval.

## Verification

Focused Historical lineage and PIT Exit tests: 25 passed in 3.78s.

Historical PIT Exit gate results:

- STRUCTURAL = PASS
- CUTOFF_CONTRACT = PASS
- FAILURE_BOUNDARY = PASS
- CROSS_DATASET_TEMPORAL_CONSISTENCY = PASS
- TEMPORAL_JOIN_SAFETY = PASS
- REVISION_TIME_TRAVEL = PASS
- MANIFEST_LINEAGE = PASS
- COVERAGE_MATRIX = PASS
- OBSERVED_FACTS_BOUNDARY = PASS
- SCOPED_DATASET_ENFORCEMENT = PASS
- SURVIVORSHIP = PASS
- BASE_ELIGIBILITY = PASS
- ROLLING_READINESS = PASS
- CHAOS = PASS
- DETERMINISTIC_REPLAY = PASS
- RESEARCH_INPUT_DRY_RUN = PASS
- PHASE_1B_EXIT = PASS

The remediation script replayed without artifact collision. The frozen panel SHA-256 remained unchanged. Phase 1C remediation has not started.
