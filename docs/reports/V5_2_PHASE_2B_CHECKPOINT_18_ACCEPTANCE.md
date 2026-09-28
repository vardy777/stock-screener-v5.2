# V5.2 Phase 2B Checkpoint 18 — final local acceptance

## Formal persistence addendum — 2026-09-28

The earlier `cc8e07b3...` value below was a **printed content hash**, not a
persisted immutable Gate V2 evaluation. Its 18/18 engineering result remains
historical test evidence, but it was not sufficient for formal freeze. The
authorized persistence correction was committed alone as
`0c7a89848417b9ca8ca7f6f855748e93c448d493` (tree
`1b37760efa8e43a7c1eda688c9547f28a370ce8f`), with no Gate V2 predicate,
contract, evaluator, Phase 1, Phase 2A, or label-semantic changes.

On that clean code commit, the verified 44-object private CAS inventory
`a559e02eb8726289bb19c80daa37f78c8041e58bf6884d6c92c382da91ab6536`
at `C:\Users\lisha\.v5_2\private-cas` had zero missing, size-mismatched, or
hash-mismatched objects. New clean-room receipt
`360d085723ebdf47e5bede214213195e916a496454fd9ca16562c73031419c08`
bound that exact commit; its nine commands exited 0. One bounded formal
`evaluate_phase2b_gates_v2_exact()` rerun independently returned 18/18 PASS,
all failure codes null, and `verify() = true`. The same process immediately
wrote the result by immutable create-or-identical semantics to ignored private
evidence storage:

`data/phase_2b_checkpoint18_real_month/gate_evidence/gate-evaluation-2ee052fd40beccee86f62d4b5fe29eb8710e2548ac8ee5c5e418d0a39646be66.json`

A separate Python process exact-read the file and confirmed 18/18 PASS and
`all_pass = true`. The new authoritative Gate evaluation ID is
`2ee052fd40beccee86f62d4b5fe29eb8710e2548ac8ee5c5e418d0a39646be66`;
the old printed hash was not used as authority. Exact readers also reverified
candidate census `1a1f2465a2d60e84f61874feccf6538c1c1daec3f69369600255d78379285a8d`
and Task 12 preregistration
`5a5d9aa9f72a00e63a5712cf6f6f0bed23823119641a563ff68ea141e808dccc`.

The public-safe capsule is
`governance/phase2b/checkpoint18-acceptance-c2ff1d3ff8ffffd49279af39b7bb539a251f226e82923b85bf9234470a53f310.json`.
It embeds the 18 results read from the persisted artifact and reconstructs
the exact Gate evaluation hash. It records `pilot_executed = false`,
`checkpoint19_started = false`, `phase3_started = false`, acknowledged prior
public exposure, and current Git-ref corpus-byte hygiene. No private corpus
payload or derived month rows were committed. The capsule carrier commit is
subsequent governance-only work; it does not redefine the evaluated code
commit. Checkpoint 19 remains unexecuted pending independent GitHub review.

Final capsule-era verification: focused evaluation/capsule tests **21 passed**;
fresh full `python -m pytest -q` **1068 passed, 8 skipped in 2220.28s**;
`scripts/verify_standalone.py` five boundaries PASS; exact persisted evaluation,
census, preregistration, and capsule readbacks PASS in separate Python
processes; `git diff --check` PASS; new-file credential-pattern scan found
zero hits. The evaluated-code clean-room receipt above is the fresh
standalone/build/wheel/private-CAS replay evidence; a second full formal
rerun for this governance-only carrier is neither claimed nor required.

`CHECKPOINT 18 = PASS / FROZEN` for the evaluated **code commit**
`116988942b085930027b7c07cfb53018197b050e`. This report is a subsequent
documentation-only commit; it does not claim that changing the report text
reruns the code evaluation. Checkpoint 19 pilot and Phase 3 remain blocked
pending independent GitHub review. Pilot executed: **NO**. Provider requests
and market-data network acquisition: **0**.

## Exact private corpus and clean-room

| Item | Measured result |
|---|---|
| Private CAS physical root | `C:\Users\lisha\.v5_2\private-cas` |
| Manifest ID | `0489978b34834817ee0e33dbd46d4e90b86a14e9827f89ba5b93433797c2ddd6` |
| Objects / missing / hash mismatches / size mismatches | 44 / 0 / 0 / 0 |
| Inventory hash | `a559e02eb8726289bb19c80daa37f78c8041e58bf6884d6c92c382da91ab6536` |
| Fresh private-CAS clean-room receipt | `085b5508e1a8514d1aa0f78ac771cf0ae5718bf4c1114e1d7f84cce7d11ba49a` |
| Receipt repository commit | `116988942b085930027b7c07cfb53018197b050e` |
| Reproduced effective / materialized / pre-label / scoped | 34,271 / 26,899 / 6,950 / 422 |
| Reproduced partition | `3c194baf309486c16dd8f7f9e1916f4a1a4af49c9b108bcc06ce693eee615ba9` |
| Coverage / scoped ledger | `b6108848b3cd469f37f1baaa43e4c3b5aa5f253663d47ac9e32e9fc8022b7e3c` / `a1092d6465b32c7141a9befb290938adecca2f08b8fb646389becf941f9c656e` |
| Integration / row-comparison ledger | `df54c5a80093115d469ec0257127ecd59c304f7c6d440ad2dc8bd4b85d641f67` / `c3b16aa0f7618e702e5bcab8b977b1919a75f72c5d65795576a1eeb74dd0bca8` |

The one-time CAS import used only 44 local byte-size/SHA-256 verified
sources, then reread all content-addressed objects. No source checkout,
junction, import staging, provider, or network endpoint is a runtime fallback.
The final clean-room cloned the exact feature commit to a fresh short path,
installed a fresh environment, staged only the external CAS, replayed exact
source evidence, ran standalone and ordinary clean-room checks, and built and
smoke-tested the wheel. All nine recorded clean-room commands exited 0.
Private payloads and derived month artifacts remain in Git-ignored `data/`
or the external CAS; they were not committed for public redistribution.

An earlier full clean-room attempt failed at `ORDINARY_CLEAN_ROOM` with exit 1
and emitted no underlying subprocess diagnostics. It was **not** used as
approval evidence. A fixed-HEAD diagnostic clone then passed ordinary
clean-room without CAS, with the CAS variable set, and after exact staging
of all 44 objects. The complete clean-room subsequently passed and produced
the receipt above; the formal evaluator independently reran it and accepted
the exact receipt. The first failure's specific transient cause remains
unproven; no gate was bypassed or manually flipped.

## Formal Gate V2

`Phase2BGateEvaluationV2` content hash:
`cc8e07b3d3970f8b95c17c4bc4762341bc36b61f7429e1f72cea3b2bacfc8d62`.
`verify() = true`, `all_pass = true`, process exit 0, **18/18 PASS**.
The evaluator read exact artifact IDs and independently rederived source,
semantic, replay, incremental and clean-room evidence. No gate had a failure
code.

| Gate | Result |
|---|---|
| CONTRACT_PINNING | PASS |
| HISTORICAL_COVERAGE_ACCOUNTING | PASS |
| STATE_SEMANTICS | PASS |
| RETURN_SEMANTICS | PASS |
| MFE_MAE_SEMANTICS | PASS |
| BARRIER_SEMANTICS | PASS |
| CORPORATE_ACTION_SAFETY | PASS |
| SUSPENSION_SAFETY | PASS |
| DELISTING_SAFETY | PASS |
| IDENTITY_SAFETY | PASS |
| PENDING_MATURATION | PASS |
| NOT_LABEL_SAFE_PRESERVATION | PASS |
| PARTITION_INTEGRITY | PASS |
| MANIFEST_INTEGRITY | PASS |
| LINEAGE_INTEGRITY | PASS |
| DETERMINISTIC_REPLAY | PASS |
| INCREMENTAL_IDEMPOTENCY | PASS |
| CLEAN_ROOM_STANDALONE | PASS |

The exact input IDs include partition
`3c194baf309486c16dd8f7f9e1916f4a1a4af49c9b108bcc06ce693eee615ba9`,
manifest `74c68c19e73d33491152cd5ffd429c5fd332f1331f8a97ece86e133f25bc2107`,
replay `349b09b145cd7f7877d0989b0c72d8a4f0cd621391fc032663a1d9221eef726b`,
incremental `040cce92879b2ce8fb6457760db6fada6bc4f66c5cbd82b3cf43e41acec1e49d`,
and the fresh clean-room receipt above. Gate V1 was not used to approve V2.

## Mutation, census and Task 12

- Mutation ledger: `V5_2_PHASE_2B_CHECKPOINT_18_MUTATION_LEDGER.md`, file
  SHA-256 `677bb62bc5317a7e660e6b729cf7ace07c0db491272f868f7782af5eba43dd1a`;
  all 9 required targeted negative tests passed in 291.35s. The ledger
  distinguishes each expected/observed target rejection from unrelated gates
  that were not evaluated on the mutated input. Unmutated formal gates passed
  independently above.
- Source-pinned 2010-01 candidate census ID:
  `1a1f2465a2d60e84f61874feccf6538c1c1daec3f69369600255d78379285a8d`.
  It contains 34,271 effective candidates and pins source candidate-set hash
  `76ed7e266c91e0dcef1326555b3c1fae08d47e0530c4a97f7fd381292f655770`.
- Task 12 pilot preregistration ID:
  `5a5d9aa9f72a00e63a5712cf6f6f0bed23823119641a563ff68ea141e808dccc`.
  The exact private contract selected four distinct source-ordered candidates
  across anchor sessions 2010-01-04 and 2010-01-08. Present selected paths
  include an ordinary control, pre-label exclusion, full-day suspension /
  source NOT_LABEL_SAFE boundary, and supported cash dividend. The five
  unavailable strata are explicitly `ABSENT`, not resampled using outcomes.
  Exact canonical readers accepted the census and preregistration. No pilot
  calculation or result was produced.

## Final verification commands and outcomes

All commands below ran from the isolated `phase2a-implementation` worktree
against the evaluated code commit, using the project Python environment
unless a fresh environment is stated.

| Command / check | Actual outcome |
|---|---|
| `python -m pytest -q` | 1047 passed, 8 skipped in 2297.45s; exit 0. Opt-in real-month tests were separately run, not counted as ordinary suite PASS. |
| Nine explicit mutation test targets in the mutation ledger | 9 passed in 291.35s; exit 0. |
| `scripts/verify_standalone.py` | Five boundaries PASS, zero violations; exit 0. |
| `scripts/clean_room_acceptance.py` | 797 passed, 258 skipped in its clean copy; dependencies/install/build/wheel-install/wheel-smoke/zero-dependency all true, archive findings empty; exit 0. |
| `derive_cleanroom_evidence_exact()` with explicit `V5_2_PRIVATE_CAS_ROOT` | Fresh clone, fresh env, 44 CAS objects, private replay, standalone, ordinary clean-room, build/wheel: all nine commands exit 0; receipt ID above. |
| `evaluate_phase2b_gates_v2_exact()` with all exact IDs including new receipt | Verified content hash above; 18/18 PASS; exit 0. |
| Real source census and preregistration opt-in test | 1 passed, 4 deselected in 600.43s; source set and immutable read-back matched. |
| Exact persisted census/prereg reader check | 34,271 candidates, four selected, five absent strata; both `verify()` true; exit 0. |
| Tracked known-credential scan | Both previously disclosed credential strings absent from `HEAD`; `.env`, `.env.local`, `credentials.txt`, `secrets.txt` ignored. No token printed or committed. |
| `git diff --check` and `git status --porcelain` before this report | Exit 0, empty worktree. |
| `git ls-files data/phase_2b_checkpoint18_real_month` | 0 tracked private-month files. |

The final Git push and clean-worktree/remote-HEAD equality checks are recorded
in the task handoff after this report-only commit. `origin/main` must remain
at `4254bb73a3eef054c7d998c43fd36521fe93db66`.

The old diagnostic Temp directory and the new short-path diagnostic clone
are non-authoritative local residuals. They are not research input, provider
sources, CAS objects, Git artifacts, or Checkpoint 18 blockers. No safety
policy was weakened to remove them.

**STOP:** Do not execute Checkpoint 19 pilot, broad runs, Phase 3, PR, merge,
or an update to `origin/main` before independent GitHub acceptance.
