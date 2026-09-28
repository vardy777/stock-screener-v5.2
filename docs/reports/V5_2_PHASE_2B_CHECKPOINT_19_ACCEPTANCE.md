# V5.2 Checkpoint 19 — exact Task 12 preregistered pilot

Checkpoint 19 is **PASS / FROZEN locally, pending independent GitHub review**.
This is a four-candidate label-plumbing and determinism acceptance, not an
Alpha or profitability study. Phase 3, ranking, AlphaScore, broad research,
and production candidate generation were not started.

## Frozen authority

| Authority | Exact ID |
|---|---|
| Checkpoint 18 public acceptance | `c2ff1d3ff8ffffd49279af39b7bb539a251f226e82923b85bf9234470a53f310` |
| Persisted formal Gate V2 evaluation | `2ee052fd40beccee86f62d4b5fe29eb8710e2548ac8ee5c5e418d0a39646be66` — 18/18 PASS |
| Candidate census | `1a1f2465a2d60e84f61874feccf6538c1c1daec3f69369600255d78379285a8d` — 34,271 source-ordered candidates |
| Task 12 preregistration | `5a5d9aa9f72a00e63a5712cf6f6f0bed23823119641a563ff68ea141e808dccc` |
| Private, immutable pilot result | `f9bd6d10ba10532717a63f5f8b584f71e34db4d651fc96f98445c352c618d4dd` |
| Public, outcome-free acceptance | `1dcf67f90a4fb997123b0c4d17473d0e44e3353800e46fbebb58f87381f9c444` |

The pilot window was exactly `2010-01-04 .. 2010-01-29`. The frozen selection
rule was `FIRST_SOURCE_ORDERED_CANDIDATE_PER_STRATUM_V1`; the four selected IDs
below came from the exact private preregistration, not from a caller or label
outcome. Five absent strata remained `ABSENT_BY_PREREGISTRATION`:
`SUPPORTED_BONUS_SHARE`, `UNSUPPORTED_CA`, `DELISTING_BOUNDARY`,
`IDENTITY_TRANSITION`, and `PENDING_MATURATION`. No substitution occurred.

| Slot | Candidate ID | Anchor | State | Reason | Case ID |
|---|---|---|---|---|---|
| 1 | `443ffe4cb83036f1748cf584c3b1f915a86daed7995fb6b67a4b7db016aab7f7` | 2010-01-08 | LABEL_AVAILABLE | — | `94c5cd61fe4d709aafd8e505701ee6e823787bf9b519f41e78536282ba84a014` |
| 2 | `7f01a8a52ad98e61917fd582a2c7c59d4e861b9e71139bbd0d32917c43e51994` | 2010-01-04 | EXCLUDED_BEFORE_LABEL | IPO_SEASONING | `a38eec92a8d0d349a05e31135af6efe39d5da83d564397f5f45846f05dabfc8d` |
| 3 | `b5bfb5faf06abbc6c6c446891eb6667d3d7dcccf16d557eb1ac6af21618b888c` | 2010-01-08 | LABEL_AVAILABLE | — | `ff4b8f544867f120f708640ecece1f37ee96cc89ca080da39474abc58b428b29` |
| 4 | `70e76ff1db527bcb5415fed647a6e09d4eb5939c05fdba019da379d89d043cae` | 2010-01-08 | NOT_LABEL_SAFE | ANCHOR_BAR_MISSING | `2d4c811baee0cba6ef1bbfacda4d120b7bed1fcf60847c1f0a9d4f0610602e29` |

Slots 1, 3 and 4 each produced a verified, exactly ordered five-domain
`LabelInputBundleV1`, seven label fields, a production result, and an
independent reference result. Their field values, states, reasons, barriers,
decisive sessions and lineage matched exactly. Slot 2 was correctly excluded
before bundle construction by the frozen IPO-seasoning rule: it pins the
five-domain source authority, but it has **no synthetic five-domain bundle or
numeric label**. All four case IDs replayed identically on a second load of
the frozen producer.

The private result stores label values and exact consumed lineage in
Git-ignored `data/phase_2b_checkpoint19/pilot_results/`; its exact reader
survived a separate Python process and rejected mutated candidate order. The
public capsule carries only hashes, states, reasons and authority metadata;
it has no label values, numeric return fields or local absolute paths.

## Frozen acceptance predicates and safety

`NO_PROVIDER_REQUESTS`, `EXACT_FIVE_DOMAIN_LINEAGE`, `18_GATES_PASS`,
`DETERMINISTIC_REPLAY`, and `ZERO_MISMATCH` all evaluated PASS. The real pilot
focused test ran with socket connection attempts blocked and passed; provider
requests and market-data network calls were **0**. Exact census, contract,
Gate V2 evaluation, and Checkpoint 18 capsule were read before pilot labels.
The selected candidate order, month, authorities and absent strata were not
altered. `ALPHA CONCLUSION = NOT EVALUATED` and `PHASE3 STARTED = NO`.

The repository state sync was separately committed as `9922c20`, with README
and a public-safe `governance/project-state.json`. The post-pilot state file
SHA-256 is `7dc28ba3423d2caa5b78169c74bdb4b92dbfa6312a0103c70b6b8a0064c0e168`.
The pilot code, tests, public capsule, and final state update were committed as
`4876947` after the real opt-in pilot and exact readbacks passed.
`origin/main` was not merged or rewritten.

## Verification

The opt-in focused command
`V52_CHECKPOINT19_PILOT=1 V5_2_PRIVATE_CAS_ROOT=<verified private CAS> python -m pytest -q tests/labels/test_phase2b_checkpoint19_pilot.py tests/labels/test_phase2b_checkpoint19_acceptance.py`
returned **3 passed in 281.21s**. Standalone verification reported five
PASS boundaries. The clean-room run, without private `data/`, reported
**819 passed, 260 skipped in 7.37s** inside its copy; dependency install,
project install, build, wheel install, wheel smoke, zero-dependency acceptance,
and archive hygiene all passed. Exact 44-object private corpus bytes remained
unreachable from current Git refs. New-file credential-pattern hits: **0**.
Fresh full `python -m pytest -q` on the pilot implementation commit returned
**1069 passed, 10 skipped in 1781.19s** (exit 0). The two opt-in Checkpoint 19
tests were among the ordinary-suite skips and are covered by the explicit
private-CAS run above. `git diff --check` and exact public capsule readback
were also PASS. No PR, merge, or main-branch update was performed.
