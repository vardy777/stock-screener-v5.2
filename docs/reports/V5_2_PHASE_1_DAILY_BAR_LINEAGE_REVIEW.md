# V5.2 Phase 1 Daily Bar Source-Version Lineage Review

Status: `PHASE 1B HISTORICAL DAILY BAR CORRECTNESS TEMPORARILY REOPENED`

Audit baseline: `6b0c9fc6ef1dda3023c414a7b78f6c72a5c0b2aa`

## Identity tracing

### Identity A

```text
de95192812d99f1c7f4e4363b8160a1b8728d76f503aa7edbf5c851a719527bb
```

- Artifact role: Historical PIT Exit Daily Bar source-version identity.
- Dataset/provider/endpoint: `daily_bar` / `datahubco_tushare_proxy` / `daily`.
- Construction: `content_hash(tuple(sorted(set(raw_payload_hashes))))`.
- Inputs: 5,884 immutable raw payload hashes: the 5,548 Phase 1B-2B inputs plus 336 Phase 1B Exit 2026 extension inputs.
- Coverage represented: `2010-01-04 .. 2026-09-10`.
- Content represented: 14,010,422 observed rows, 5,483 securities.
- Source-version contract implementation: unversioned raw-payload-set hash constructed in `scripts/finalize_phase_1b_exit_daily_bar_panel.py`.
- Normalization/unit inputs: `53fd452337be9368e37fb01aeb8a38082db0a470a5ab94ea0cad06b8653c2cc4` / `e7a744be0f572b6bfe7ad909829f366e0bc75c16a795edb46e561d70effaf093` are panel metadata, not inputs to Identity A.
- Availability input: not part of Identity A. The panel separately pins availability evidence `687725...` and a next-session overlay hash.
- Schema input: tuple hashing via the repository canonical content-hash implementation; no explicit source-version schema/version tag.
- Created by/at: `scripts/finalize_phase_1b_exit_daily_bar_panel.py`; fixed `NOW=2026-09-13T12:00:00+08:00`.
- First introducing commit: `822025a7cd60cd6a149dcf20cd21896e8fd42416` (`feat: close Phase 1B historical PIT exit`).
- Direct downstream references: seven Historical Exit EvidenceArtifactV1 files and approval `fc26bf...`; the approval is pinned by manifest `76c4fe...`, Phase 1B exit sessions/matrix/acceptance, refresh runtime, and Phase 1C.

Identity A means: **the exact expanded Historical Exit raw payload content set**. It does not, by construction, identify provider behavior or availability semantics.

### Identity B

```text
ea88e3bcf5ecbae599567d1f22756f1333b9ff134c2face0895e60fcadc05986
```

- Artifact role: Phase 1B-2B Daily Bar availability-probe source-version identity.
- Dataset/provider/endpoint: `daily_bar` / `datahubco_tushare_proxy` / `daily`, with `trade-cal` supporting the next-safe boundary.
- Construction: `content_hash(tuple(previous_manifest.raw_payload_hashes))` during publication; the probe script stores the resulting value as `SOURCE_VERSION_ID`.
- Inputs: 5,548 Phase 1B-1/1B-2B raw payload hashes.
- Coverage represented by the predecessor manifest: `2024-01-01 .. 2025-12-31`, 2,481,310 facts, 5,261 securities.
- Availability evidence: 12 immutable observations over six frozen securities for session 2026-09-09, plus 13 receipt IDs; policy `daily-bar-availability-v1`; historical rule `NEXT_SESSION_SAFE@16:30 Asia/Shanghai`.
- Normalization/schema inputs: not included in Identity B. Probe observation and evidence schema versions are hashed into their own artifact IDs, not the source-version identity.
- Created by/at: `scripts/probe_daily_bar_availability.py`; probe times `2026-09-10T00:14:46.869951Z .. 2026-09-10T00:14:51.865167Z`.
- First introducing commit: `88164aaed725276213603523ed316db4a4a41993` (`Close Phase 1B-2B daily bar availability`).
- Direct downstream references: availability artifact `687725...`, seven Phase 1B-2B evidence artifacts, approval `7daf8a...`, its manifest/revocation/equivalence, and Historical Exit artifacts that reuse availability ID `687725...`.

Identity B means: **the exact predecessor 5,548-payload content set to which the bounded availability evidence was bound**. It also does not independently identify provider behavior semantics.

## Why they differ

The two identities use the same hashing convention but different content sets. Identity B's 5,548 hashes are a strict subset of Identity A's 5,884 hashes; Historical Exit added 336 hashes. The difference is deterministic and expected for different dataset snapshots. No evidence establishes that the added payloads changed provider field, unit, normalization, or availability behavior.

The defect occurs because Historical Exit:

1. created Identity A for the expanded content set;
2. created seven generic PASS evidence artifacts bound to Identity A;
3. reused availability artifact `687725...`, which remains immutably bound to Identity B;
4. created approval `fc26bf...` and manifest `76c4fe...` without enforcing equality between the approval source version and the pinned availability evidence source version.

Root-cause class: `B. LEGACY_APPROVAL_WIRING_DEFECT`.

There is also a source-version contract modelling weakness: a raw content-set hash is being used as though it were a provider semantic/version identity. Scope expansion therefore changes the identity even when semantics are unchanged. That weakness explains why rebinding is necessary, but it does not make the incompatible evidence pair valid.

## Historical panel blast radius

Machine checks establish:

- panel ID/hash is immutable and its manifest uses the same 5,884 raw payload hashes;
- `content_hash(tuple(manifest.raw_payload_hashes)) == Identity A`;
- panel and manifest both pin availability evidence `687725...`;
- that availability artifact verifies against Identity B, not Identity A;
- `DailyBarAvailabilityPolicyV1` rejects the pair with `source version mismatch`.

```text
PUBLISHED_PANEL_AFFECTED = YES (formal PIT/source lineage)
AFFECTED_FACT_COUNT = 14,010,422
AFFECTED_SHARD_COUNT = 1 formal published panel artifact
AFFECTED_RAW_PAYLOAD_SHARD_COUNT = 5,884
AFFECTED_SESSION_RANGE = 2010-01-04 .. 2026-09-10
AFFECTED_SECURITY_COUNT = 5,483
```

This finding does not prove that OHLC values, x100 volume, or x1000 amount are wrong. It proves that all rows in the currently published panel lack an internally compatible approval-to-availability lineage, so none can be declared unaffected under the frozen contract.

Artifact `70ee31d3...` is not the availability-policy evidence. It is `DailyBarFrozenSessionAvailabilityV1`, a four-session symbol-presence sample bound to panel `a618046...`. The actual policy evidence pinned by the panel and manifest is `687725...`.

## Phase 1C blast radius

Phase 1C correctly records new increment facts as `CONTEMPORANEOUS_OBSERVED`; historical and contemporaneous modes are not assumed equal. However, its approval/manifest chain is not internally closed:

- approval `f057dc...` creates another content-set identity, `4c218b94...`, from predecessor Identity A plus incremental payload hashes;
- it inherits the Historical Exit evidence IDs bound to Identity A and also inserts coverage/fact IDs that are not typed source-version evidence;
- manifest `2fa12e...` still pins availability artifact `687725...`, bound to Identity B;
- no typed contemporaneous availability evidence artifact is pinned to `4c218b94...`.

```text
PHASE 1C CONTEMPORANEOUS LINEAGE = FAIL
PHASE 1C AFFECTED = YES (formal approval/manifest lineage)
PHASE 1C MANIFEST ROWS AFFECTED = 14,020,830
PHASE 1C INCREMENT ROWS REQUIRING REBINDING = 10,408
PHASE 1C FACT CONTENT HASHES = 3
PHASE 1C COVERAGE = 2010-01-04 .. 2026-09-14
```

The contemporaneous observation timestamps may remain valid inputs to corrected evidence, but the current approval cannot establish that result.

## Decision

```text
BACKFILL_ONLY_DEFECT = NO
PHASE 1B REOPEN REQUIRED = YES
RESEARCH_LOCKED = true
IMMUTABLE ARTIFACTS MODIFIED IN PLACE = NO
SUPERSESSION REQUIRED = YES
FIX IMPLEMENTED = NO
43 RAW ROWS REUSED = NO (retained and quarantined)
PROVIDER REDOWNLOAD = NO
PHASE 1 DAILY BAR LINEAGE = FAIL
PHASE 2A = BLOCKED
READY FOR PHASE 2B = NO
```

The next step is a minimal immutable remediation: construct correctly scoped/rebound availability evidence, replacement Historical Exit approval and manifest, and the required revocation/supersession artifacts; then separately repair the Phase 1C chain using its contemporaneous observations. No 14M-row reacquisition is justified by this audit.
