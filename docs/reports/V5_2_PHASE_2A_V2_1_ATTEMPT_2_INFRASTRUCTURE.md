# V5.2 Phase 2A V2.1 Attempt 2 Infrastructure

Date: 2026-09-19 Asia/Shanghai

## Scope and decision

```text
ATTEMPT 2 INFRASTRUCTURE = PASS / AWAITING INDEPENDENT REVIEW
FINAL V2.1 ACCEPTANCE = NOT RUN
PHASE 2A = FAIL / OPEN
READY FOR PHASE 2B = NO
PHASE 2B STARTED = NO
PROVIDER REQUESTS = 0
DATA NETWORK CALLS = 0
```

This checkpoint implemented and verified acceptance infrastructure only. It did
not create `Phase2AAcceptanceV2_1`, modify the Label Engine, change
`Phase2AEvidenceAssemblerV1` runtime semantics, modify Phase 1, run final Phase
2A acceptance, or start Phase 2B.

## Frozen authority

- Implementation plan: `d9cfcf4822bd0d617e1e599e35fde0b939de03cd`
- V2.1 amendment design HEAD: `a66825e25d40a46eceae18a50f1f2535ab9ee975`
- V2.1 design amendment ID: `d4a7941e2583eb84dd1bf501fb9183d5346f3813f383704b691c3798fb8ac25b`
- Checkpoint 7 comparison ledger: `0ee799a175a5e6832b9ca79d88ff9a0b9583ff92e204849274f96a031c397247`
- Attempt 1 artifacts remain immutable and are superseded for infrastructure
  acceptance with reason `INFRASTRUCTURE_ACCEPTANCE_CORRECTNESS_DEFECT`.

## Attempt 2 immutable artifacts

| Family | ID |
|---|---|
| V2.1 amendment | `fadd791ac0562cf218a6e52954c36eff05244d6b69e7a70cb38814b256fb98d5` |
| Layer A real-reference coverage | `da6356776020f8d32737184bbd7759e3ecdee49ce8dc67784fe4dda3d9840ec4` |
| Layer B fail-closed boundaries | `161f59093ac9e9949de007bf08989e1220b8a2177991a604ad48cee2c70428a4` |
| Layer C calculation edges | `5d4cfa298891ad0cf1f2e997429d7e2f505a97f63e66acc9e8a9970ad1c16f4f` |
| Gate consumption map | `fe268e2d080580485715bb69eefc4c6ebc144b959c404ff0f50692be12d685bb` |
| Infrastructure evaluation | `edf35f614c2631b352b47c5680354b86e517a23f7ae620fa0d285a3ec90f407c` |
| Attempt 1-to-2 supersession | `37279c7e92bd33891c833eb95dae1cfc4d104388acc03f01d0ee810f216b390c` |

The six Attempt 2 family IDs are unique and disjoint from the six exact Attempt
1 IDs. Two consecutive materializer runs produced identical filenames, IDs,
and bytes. Collision tests prove different bytes are rejected without overwrite.

## Missing-bar boundary provenance

```text
semantic category = UNEXPLAINED_MISSING_BAR
real base bundle = 20fb25a67c620390cd15cba87aec7a4d45eae00b7f1973cd554d6c919fdc339b
five-domain lineage =
  1e4edaa967b8da27118c9353820a8a03d51625c38da2317a01d0ae9d50eb87ae
  b8e7cad556dfa0d201a369d60f0dadadaf84a3ae4583fb7880870b03c531648c
  371e0d5fab4efca359563465d738c119246f12dc9f98875d738de75ff18b2cb0
  95c2827164c436df9bc564c6871e7edc3dd21cab8a4b81c26661616d97b27dc1
  5a236dc1ce49dbcc0b495f656a0624df8fc5e0abb085957f28b88dd64c21dca1
removed required future session = 2024-01-25
transform ID = ff346ff9bfac0a886370f6c20b18aaf73cde8ad8c69fa1f7519c24cc4d0d22cf
transformed evidence ID = 85d67e37a998332003d41f1b071d6ce60b404648bcf45a56a4d77b283bc3d955
Checkpoint 8 unavailability evidence = 947a8cd54a0a9a9bf91a8a4b45e7b502c272fb8dff374eab19b99615fca98f48
observed rejection = UNEXPLAINED_MISSING_BAR:2024-01-25
assembler invocations = 1
engine invocations = 0
real condition observed = false
```

This is real-base plus deterministic counterfactual coverage. It is not counted
as an observed real-market missing-bar event.

## Unsupported Corporate Action boundary

```text
event = 002029.SZ / 2012-05-08 / UNSUPPORTED_SHARE_CONVERSION
approval = 5e53080fd85dba5328cda9ed44c5dc5959e5bea965d8f5df12e07201deb8e974
manifest = 5086896d0066baa928fe44c3469b2c1362feb2068db04acb7336b38c13bdbe2c
materialization audit = 8cf46a3dbaf6170cd64a1f2514f47ea87609200886fb2d8eebf60f888b11d28d
candidate bundle = e36c885b4ad5a666a829bc56eba0ba455cb26c1fae2cd321748d14908c67d16d
quarantine = 000c9bb50f41b1ad603bb4367f1bf7eb5c6506557d323c2356baa00a12a3f7c6
production boundary = CorporateActionRepository.query
exact exception = NOT_RESEARCH_SAFE: unsupported action type
engine invocations = 0
```

The real repository boundary is exercised. An acceptance-only CA preflight
cannot satisfy this coverage.

## Gate and negative-evidence results

- Controlled infrastructure evaluation: all original 16 gate names returned
  `PASS` through their fixed executable predicates.
- The evaluation artifact fixes `final_acceptance_created=false` and
  `ready_for_phase_2b=false`; these 16 results are not final Phase 2A approval.
- Seven count-preserving mutations were rejected by their owning gates while
  retaining 20 Layer A cases, 10 Layer B cases, 4 Layer C fixtures, or 16 map
  entries as applicable.
- Missing required semantics covered suspension-through-H5, LABEL_PENDING,
  negative return, truthful missing-bar provenance, repository-backed
  unsupported CA, same-session ambiguity, and predicate-ID integrity.
- Tampered amendment/A/B/C/map or supersession mismatch produces 16/16 FAIL.
- Raising engine spies remained unreachable for both missing-bar and unsupported
  CA builders; serialized zero counters were not the sole proof.

## Verification record

```text
.venv\Scripts\python.exe -m pytest <eight focused V2.1 files> -q
75 passed in 120.34s

.venv\Scripts\python.exe -m pytest tests/labels -q
216 passed in 197.16s

.venv\Scripts\python.exe -m pytest tests/data tests/refresh tests/providers -q
299 passed in 1.60s

.venv\Scripts\python.exe -m pytest -q
781 passed in 300.29s

.venv\Scripts\python.exe scripts/verify_standalone.py
four standalone / zero-project-dependency checks PASS

.venv\Scripts\python.exe scripts/clean_room_acceptance.py
build/install/tests/wheel/smoke/zero-dependency = true
616 passed, 165 skipped in 3.64s
archive findings = none

.venv\Scripts\python.exe -m build
first invocation: FAIL because the local ignored .venv lacked the build module
remediation: uv pip install --offline --python .venv\Scripts\python.exe build
fresh invocation: PASS; sdist and wheel built

fresh temporary-venv wheel install/import smoke
PASS; V2.1 contracts, 16 predicate dispatch entries, and resolver imported

credential scan across git tracked/candidate files
configured sentinels = 0; findings = 0; .env tracked = false; .env ignored = true

credential chunk-boundary + runtime sentinel tests and AST/import checks
4 passed in 68.90s

deterministic replay + tamper/revocation + firewall + count-preserving suite
59 passed in 67.31s

git diff --check
PASS

git diff --name-only a66825e... -- data/phase_2a/v2_infrastructure
no output; Attempt 1 path unchanged

prohibited Phase 1 / Label Engine / assembler runtime diff
none

final V2.1 acceptance artifact files
0
```

No provider client or data-network acquisition path was invoked during this
checkpoint. Build dependency installation used the local package cache in
offline mode.
