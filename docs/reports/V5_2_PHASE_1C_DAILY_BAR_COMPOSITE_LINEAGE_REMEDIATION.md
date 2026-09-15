# V5.2 Phase 1C Daily Bar Composite Lineage Remediation

Status: `CHECKPOINT 2 CONTRACT REMEDIATION PASS / AWAITING INDEPENDENT REVIEW`

The first remote Checkpoint 2 commit, `e3ccdcbc6d5439ca44b6ecd33e7242438f4d7cbe`, was not accepted because its V1 source semantic identity included availability policy while its contemporaneous binding claimed `NEXT_SESSION_SAFE`. Those immutable artifacts remain unchanged and are no longer current.

## Semantic contract decision

`availability_policy_version` is not part of Daily Bar source semantic identity under `daily-bar-semantic-contract-v2`. Provider, endpoint, requested fields, normalization, identity, price and unit semantics remain semantic inputs. Availability policy remains an auditable `DailyBarSourceBindingV1` field and therefore still changes `binding_id`.

- Source semantic identity shared by all three components: `032e396c8587dc1dc0a5d934db60bcf684a37f21ac8d614fa09a79035888ca48`
- Historical baseline binding: `176dba27d4cb6943e2434f1608668dc5bc756fa2e1357e18098927873032f3e8`; policy `daily-bar-availability-v1:NEXT_SESSION_SAFE`
- Historical catch-up binding: `0b02049ec5de47dca8c862174e7c872eb7d63578f9362bd961c616ce472938fa`; policy `daily-bar-availability-v1:NEXT_SESSION_SAFE`
- Contemporaneous binding: `c3872b18b86f06f4188fc65090a7224ac53220a433abce2f3dad460126beb187`; policy `daily-bar-availability-v1:CONTEMPORANEOUS_OBSERVED`

V1 binding verification remains backward compatible. Component construction fails closed when binding policy and availability evidence disagree.

## Immutable three-component replacement

- Composite manifest: `0053aa0c80a5561dd8557156555bfdb47c841901477a737a0a0a2f5807918744`
- Historical baseline: 14,010,422 rows; manifest `cb79850fac1c28e7b1e8bd9991d65c26f61add832b2f5ed67c40c586a13fd8c6`; approval `eaa2c254b85077ae8f988c393b133ba90f5443025d2cfdbe10523229f8f753f4`; availability `2bb3877daa164b5c09b617c9a44168d1a8035fae6e247ef4cb023d313070448e`
- Historical catch-up: 5,204 rows on 2026-09-11; manifest `12d4124dad67314ed9d03ba66410e7015e986a77383789c182b941b0e7e0e443`; approval `e108798a79fdafc9591f1e3f81cb033fbe127299e478ebaa2f00beca253ef1d5`; availability `7e63d79275508281d360edc5a88d3627dde13f31b88c8d0640523a91d7159709`
- Contemporaneous observed: 5,204 rows on 2026-09-14; manifest `557083bb56b239bfe9f9a4c20591ff89288c5913961c65a803b6ffd7d5649e46`; approval `8eb44524d114bb0a5487119e0d5db5a7c795bf0073a5d6465ecd1aa0839c6296`; availability `7da60a677b4eeb9279ace08baad2ec7b49ccba7ef12ee817ec0bf2d85f5dcafa`
- Aggregate: 14,020,830 rows; unclassified 0; duplicate membership 0
- Composite approval: none

The expected membership comes independently from immutable Phase 1C manifest `2fa12e2cfdcb35db45266c86631822b015111e33c10c4aa484889c30d1365ddf` and its three pinned `fact_content_hashes`.

```text
expected_membership_digest  = f102209d421fa1d1103f634e976a4828f91c39145de8b0cc740388c991fee4df
composite_membership_digest = f102209d421fa1d1103f634e976a4828f91c39145de8b0cc740388c991fee4df
union_complete              = true
unclassified                = 0
duplicate_membership        = 0
```

## Replacement and revocation

- Composite replacement: `4f6601e8728f63d897c48e48e3f7c6bb5b2df3955f00f8e95ae658c412091c44`
- Historical baseline approval revocation: `20c9df97b6f1396e39536f9b93e666cd2567d9dec21b574309985587350c9423`
- Historical catch-up approval revocation: `5b71472a22b18177ec703b0cdd00a0efa27bf7e584a52b4995b3cca1234504b6`
- Contemporaneous approval revocation: `ac2145c8110e6f6b936491c74898abe968bb0b41df6d7bf2a05dd5e3428bc4a9`
- Replacement mixed-approval revocation: `e9926de3b00468cae864ec6fd8c740b931144f5c168bd4404ca97b6fb563409e`
- Replacement governance supersession: `d8157998ff018864b18d468fc532b1cd6376454d7014dec821327c69cb9bd84a`
- Global acceptance: `7e0d0eba6bc49a96187f67590c454ba586e9397fccc5f727233206de058298a8`

Old Checkpoint 2 artifacts are byte-identical. No provider request or fact rematerialization occurred. Business values, Historical and Catch-Up `available_at`, and Contemporaneous `observed_at` are unchanged.

## Gate results

```text
HISTORICAL_COMPONENT       = PASS
EXACT_THREE_ROLES          = PASS
ROW_COMPOSITION            = PASS
PAIRWISE_DISJOINT          = PASS
UNION_COMPLETENESS         = PASS
UNCLASSIFIED               = PASS
AVAILABILITY               = PASS
SOURCE_SEMANTIC_CONTRACT   = PASS
NO_AGGREGATE_APPROVAL      = PASS
OLD_GOVERNANCE_REVOKED     = PASS
CURRENT_RESOLUTION         = PASS

PHASE 1B DAILY BAR LINEAGE = PASS
PHASE 1C DAILY BAR LINEAGE = PASS
PHASE 1 GLOBAL LINEAGE     = PASS
```

## Commands and results

```text
python -m pytest -q tests/data/test_daily_bar_source_binding.py tests/refresh/test_daily_bar_composite_lineage.py tests/data/test_historical_lineage_composition.py tests/data/test_historical_remediation.py tests/real_audits/test_phase_1b_exit_runtime.py tests/refresh
47 passed in 3.78s

python -m pytest -q
636 passed in 93.44s

python scripts/verify_standalone.py
four standalone and zero-project-dependency boundaries PASS

python scripts/clean_room_acceptance.py
build=true; clean_room_dependencies=true; clean_room_install=true; clean_room_tests=true; wheel_install=true; wheel_smoke=true; zero_dependency_acceptance=true; 580 passed, 56 skipped in 2.85s

python -m pytest tests/governance/test_phase_1a_boundaries.py::test_sentinel_scan_detects_secret_split_across_stream_chunks tests/governance/test_phase_1a_boundaries.py::test_current_runtime_areas_have_no_sentinel_leak -q
2 passed in 67.97s

actual configured credential scan across git tracked/candidate files
configured sentinels=1; findings=0; .env ignored=true; .env tracked=false

remediation and global acceptance replay twice
same composite ID and acceptance ID; old artifacts byte-identical; provider requests=0

git diff --check
PASS
```

Phase 2A remains blocked pending independent review. The 43-row backfill was not resumed. Phase 2B was not started. `origin/main` was not updated.
