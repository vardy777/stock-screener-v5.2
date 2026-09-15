# V5.2 Phase 1C Daily Bar Composite Lineage Remediation

Status: `CHECKPOINT 2 IMPLEMENTED LOCALLY`

## Immutable composition

- Contract: `Phase1CDailyBarCompositeManifestV1`
- Contract version: `phase-1c-daily-bar-composite-v1`
- Composite manifest: `72eab2642f7143c27536107fed41ea537cd8984ac54d9090486708e182f5d80a`
- Historical baseline: 14,010,422 rows, `HISTORICAL_RECONSTRUCTED`, `NEXT_SESSION_SAFE`
- Historical catch-up: 5,204 rows on 2026-09-11, `HISTORICAL_RECONSTRUCTED`, `NEXT_SESSION_SAFE`
- Contemporaneous observed: 5,204 rows on 2026-09-14, `CONTEMPORANEOUS_OBSERVED`
- Aggregate: 14,020,830 rows; unclassified 0; duplicate membership 0
- Composite approval: none

The baseline directly pins manifest `118744559f5869bcbe75b402870524a18ec6f42e813764568bec6c7f070bf5ad`, approval `31d91fd99630e3b63b585ae598e7728fe1922454c3dbee276d0ffe9e7b24d79f`, and availability evidence `c52bcc200d4201dae909ee00a95b6a314b8648502cdb9b9ccadd3a6ab8522082`.

The catch-up component pins manifest `f7466f9364c0610e4ab37bf70acd290526022187cb66303f785eaf1ca67ce993`, approval `4026913c2f107864849219ecf3d63f6a47d7b31d61b5d030dfecacb58ddd9164`, availability evidence `23634f98b56edc10d95dca0aa631d0f7b7087f3963f9ba4dafa6d97c5d7e7e17`, and content identity `ce5c402cd869541db8f69c136e2d4ba0d2793ba42a245cab1c8aacda72f6e238`.

The contemporaneous component pins manifest `20ddfa8c41d6e8ee259d8930428f00316d3d653f7af016f32fccdb0636627b38`, approval `c0d8955966d66c9727f37213d8933b7bb9e46fffbc6538581e055c5a1d449e0e`, availability evidence `c77cdc172c472908a781a9148f1f20fca458379d21b33fdc12ea71c72cd631a5`, and content identity `5ebf5d7df068aaf74e72c24d31d6c403ab8b47be131e5675edef6716f4a95b2f`.

All three components use semantic identity `4f3875e94fe5ff8bf1341dea8ee769b209c301b24204bbc8af65a476e106b1b9` because their provider, endpoint, schema, normalization, price, unit, and identity semantics are identical. Availability remains component evidence, not source semantic identity.

## Supersession

- Old mixed approval revocation: `c0a79b0c225e1b1d527e75e3355fbfd664281de62806d0261b4099db1a277981`
- Governance supersession: `d7220ef333d97e0a533021284d76342e03221501b5313302999c92de71e710d9`
- Reason: `MIXED_SOURCE_CONTENT_LINEAGE_REBIND`
- Old approval and manifest remain immutable and are not current.

## Acceptance evidence

- Global acceptance: `ed07ae34ebefb7e5560b5c8800aace27ad79aaa87c4573461ed24a216eed2d02`
- Phase 1B Historical Daily Bar lineage: PASS
- Phase 1C Daily Bar lineage: PASS
- Phase 1 Daily Bar global lineage: PASS
- Provider requests: 0
- Business values changed: no
- Historical/catch-up available_at changed: no
- Contemporaneous observed_at changed: no

## Commands and results

```text
python -m pytest tests/refresh/test_daily_bar_composite_lineage.py tests/refresh/test_runtime.py tests/refresh/test_service.py tests/refresh/test_contracts.py -q
38 passed in 0.25s

python -m pytest -q tests/refresh/test_daily_bar_composite_lineage.py tests/data/test_daily_bar_source_binding.py tests/real_audits/test_phase_1b_exit_runtime.py tests/data/test_historical_lineage_composition.py tests/data/test_historical_remediation.py tests/refresh
44 passed in 3.74s

python -m pytest -q
633 passed in 91.13s

python scripts/verify_standalone.py
four standalone and zero-project-dependency boundaries PASS

python scripts/clean_room_acceptance.py
build=true; clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; wheel_install=true; wheel_smoke=true; zero_dependency_acceptance=true; 577 passed, 56 skipped

python -m pytest tests/governance/test_phase_1a_boundaries.py::test_current_runtime_areas_have_no_sentinel_leak -q
1 passed in 65.12s

remediation and global acceptance replay
same composite ID and acceptance ID; old artifacts byte-identical; provider requests=0

known credential scan
PASS

git diff --check
PASS
```

Phase 2A remains blocked pending independent review. The 43-row backfill was not resumed. Phase 2B was not started, and `origin/main` was not updated.
