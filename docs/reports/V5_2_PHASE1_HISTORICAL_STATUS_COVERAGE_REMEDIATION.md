# V5.2 Phase 1 Historical Status Coverage Remediation Acceptance

## Outcome

```text
PHASE1 HISTORICAL STATUS COVERAGE REMEDIATION = PASS / FROZEN
SOURCE COVERAGE CHANGED = NO
SEMANTICS CHANGED = NO
PROVIDER REQUESTS = 0
NETWORK ACQUISITION = 0
TASK 5 = BLOCKED PENDING INDEPENDENT GITHUB REVIEW
```

This checkpoint adds a portable, immutable representation of the already-approved
historical daily-security-status truth. It does not create provider `ACTIVE` facts,
change `StatusAvailabilityPolicyV2`, acquire new observations, or extend coverage.
Ordinary status remains a derivation from positive lifecycle evidence and the exact
closed-world risk-warning and suspension authorities.

## Frozen inputs

```text
coverage_start = 2010-01-04
coverage_end = 2026-09-10
parent_panel_id = cd062ced913e865984d536bc85305f9c6e720e26cee111527aac120fd66fe707
parent_manifest_id = d96fc4f26c459dc000ca8059a8364a8236e906305be83d2d72adc01d9e11ffb0
parent_approval_id = ac1c23dae38c32228bfc6639714976e6a01063b230ae3397ee45d9ac1d8afa07
pit_evidence_id = aabfbcd3e8d4d03ff400c52a12ff005638b259bf0185e802d96372b4015f3f8f
lifecycle_hash = bb96052035488424dcc7aaa9d577c9ca990fe6669df8bf4e466f0e3c8171d2a5
risk_warning_hash = fb81454d499f645283e2c2ede0be3422486546e2a70180926a84a93c24cc199d
suspension_hash = 87e2a971a17660a632d058f95135ebb6d984d40534a956e052df17a19076c38d
raw_payload_hashes = 118 / 118 exact
receipt_hashes = 163 / 163 exact
```

The exact reconstruction used the retained repository-local ignored staging tree.
Missing, extra, duplicate, modified, wrong-source, or out-of-repository inputs fail
closed; no network or provider fallback exists.

## Published immutable outputs

```text
derivation_authority_id = d6f7f5517428891db66da60565baaea5828d7adcaf29c820d5fa746ddf29e59b
coverage_ledger_id = b214cc728c867c7b5bdbef5e6b37cea25afa67650522d5aee800cd95f56237cb
derived_approval_id = 9353de33e62405830a7dbef13e53836a969fb569f9e7d5370a67d5df9078fa95
derived_manifest_id = 0c86954cffaae2ca09ff1efcd4b32d990a9cf3d2b82d520a64172a1875d457a8
composition_id = e4110ec6185731d9a2d80e151d79f82006e07e779c10a90a4b4c2e228a35e139
replay_evidence_id = 235f86dd7269768382c67620cd723d27347c7f99e386488efc9b93665a517baf
```

The portable loader exact-pins and validates the authority, approval, manifest,
composition and replay evidence. It rejects revoked parent or derived approvals,
tampered identities, incomplete shard inventories, governance lineage mismatches,
unknown identities and requests outside the frozen coverage boundary.

## Coverage accounting

```text
covered_identities = 5,551
covered_exchange_sessions = 4,055
lifecycle_intervals = 5,551
risk_warning_intervals = 1,677
suspension_observations = 468,188
full_day_suspension_observations = 440,473
partial_session_observations = 2,644
resumption_observations = 25,071
delisting_boundaries = 333
ordinary_derivation_identity_coverage = 5,551
out_of_scope_sessions = 0
unresolved_identities = 0
unresolved_sessions = 0
coverage_gaps = 0
quarantine_count = 0
```

Partial-session and resumption observations are retained as applicable lineage for
their event session. Only a `FULL_DAY_SUSPENSION` component can set
`full_day_suspended=true`.

## Deterministic replay

Two independent materializations from the same frozen inputs produced the same six
governance IDs above. Relative-path and byte-hash comparison covered 46 files:

```text
LEFT = 46
RIGHT = 46
DIFF = 0
```

Canonical gzip uses a fixed timestamp. Wall-clock acquisition or operational time
does not enter research identity.

## Verification record

```text
COMMAND: $env:V5_2_STATUS_STAGING_ROOT=(Resolve-Path data/s).Path;
         python -m pytest tests/data/test_historical_status_authority.py
         tests/real_audits/test_historical_status_remediation.py
         tests/data/test_historical_status_repository.py
         tests/data/test_phase_1b_exit.py
         tests/real_audits/test_phase_1b_exit_runtime.py -q
RESULT: 37 passed in 60.60s

COMMAND: python -m pytest tests/labels -q
RESULT: 258 passed in 274.07s

COMMAND: python -m pytest tests/labels/test_dataset_contracts.py
         tests/labels/test_partition_store.py tests/labels/test_anchor_enumerator.py
         tests/labels/test_partial_maturation.py -q
RESULT: 37 passed in 0.19s

COMMAND: python -m pytest -q
RESULT: 840 passed, 1 skipped in 840.14s
NOTE: the skip is the explicit-staging reconstruction test already passed above.

COMMAND: python scripts/verify_standalone.py
RESULT: PASS; forbidden imports=0, forbidden paths/dependencies=0,
        prohibited repository inventory=0, Phase1A boundary violations=0

COMMAND: python scripts/clean_room_acceptance.py
RESULT: PASS; 668 passed, 173 skipped; build/install/tests/wheel smoke/
        zero-dependency all true

COMMAND: python -m build
RESULT: Successfully built sdist and wheel

COMMAND: known-secret tracked-file scan
RESULT: 0 files; credential contract tests: 8 passed

COMMAND: git diff --check
RESULT: PASS (line-ending warnings only; no whitespace errors)
```

## Gate result

```text
SOURCE DATA RECONSTRUCTION = EXACT
PORTABLE DERIVATION AUTHORITY = PASS
ORDINARY CLOSED-WORLD LINEAGE = PASS
ST LINEAGE = PASS
SUSPENSION LINEAGE = PASS
AVAILABLE_AT LINEAGE = PASS
APPROVAL/MANIFEST LINEAGE = PASS
REVOCATION VALIDATION = PASS
COVERAGE ACCOUNTING = PASS
DETERMINISTIC REPLAY = PASS
POST-COVERAGE FAIL-CLOSED = PASS
PHASE1 SEMANTIC CHANGE = NO
PHASE2A SEMANTIC CHANGE = NO
```

Phase2B Task 5 and any pilot remain unexecuted. Resume requires independent GitHub
review of this feature-branch checkpoint.
