# Phase 2B Checkpoint 18 — Gate V2 progress (not acceptance)

`CHECKPOINT 18 = FAIL / OPEN`. `CHECKPOINT 19 PILOT = NOT AUTHORIZED / NOT RUN`.
This report records a bounded infrastructure increment, not a Gate V2 PASS.
The legacy Gate V1 module remains unchanged and fail-closed.

## Frozen source and private-corpus boundary

- Starting feature HEAD: `5fe232d3b7360d643c83fd88d8e9ddf59ceb9f56`.
- Private corpus manifest: `0489978b34834817ee0e33dbd46d4e90b86a14e9827f89ba5b93433797c2ddd6`.
- Private CAS: 44 objects; inventory hash `a559e02eb8726289bb19c80daa37f78c8041e58bf6884d6c92c382da91ab6536`.
- No private source payload, derived month partition, or gate evidence bytes are staged for the public branch. `data/` is ignored.
- Provider requests: 0. No pilot was executed.

## Source-derived gate work

The new evaluator reads exact content-addressed evidence and independently
rederives it from physical partitions and pinned Phase 1/2A authority. Missing
or mismatched evidence remains FAIL. The currently implemented paths are:

- Gate V2 contract ID: `6a0eb73c468c44b96cded8781503bbf1e8304fc6f94d81e544675f144eba609c`.
- Interim evaluator ID: `77eb5c4f897189c81322c39ff6bc487716052f773c1b72f6d6e49d858751540c` (not a final frozen evaluator version).

1. Contract pinning: Phase 2A acceptance, maturation remediation, dataset/producer/engine code identities, private CAS inventory and five approved authorities.
2. Historical coverage: exact source candidate census, materialized membership and scoped ledger.
3. State, return, excursion, and barrier semantics: separate field groups, each compared to the independent calculator across all physical rows.
4. Pending maturation: frozen real Slot 4 H0/H1/H3/H5 boundary, including withheld early barrier outcome.
5. NOT_LABEL_SAFE preservation: physical row/reason mapping, not merely aggregate counts.
6. Partition and five-domain lineage: exact physical readback, independent membership/generation and source reconstruction.
7. Manifest integrity: canonical bytes, exact active physical partition set, month/generation/lineage relationship, and predecessor supersession continuity. The formal evaluator currently accepts only the one independently censused month; additional months cannot be silently added.

The earlier 2010-01 source-pinned evaluator run found **11/18 PASS** for the
physical 26,899-row partition. Its local ignored exact manifest ID is
`74c68c19e73d33491152cd5ffd429c5fd332f1331f8a97ece86e133f25bc2107`.
This was not final Checkpoint 18 acceptance. At that earlier point seven gates
were FAIL: corporate action, suspension, delisting, identity, deterministic
replay, incremental idempotency, and clean-room standalone. Later results are
recorded below; this historical count is not the current gate count.

## Subsequent scoped Gate V2 implementation (still not final)

The later 2010-01 opt-in evaluator run reached **15/18 PASS** (`1 passed in
1564.41s`), with dedicated source-pinned CA, suspension, identity, and
delisting evidence. Unsupported CA negatives are explicitly marked synthetic
contract fixtures, not historical market facts. The real delisting boundary
remains source-quarantined; the frozen Phase 2A delisting fixture only proves
the calculation boundary. No frozen Phase 1 or Phase 2A semantics changed.

An actual Phase 2B incremental selector defect was also found: pending H0
results carry no `horizon_end_session`, so the old selector selected no mature
work. The corrected selector consumes an explicit approved session schedule,
reuses the frozen pure horizon resolver, and rejects missing/conflicting
schedules. The real Slot 4 selector/materializer retry evidence passes a
focused evaluator test; `12 passed, 1 deselected in 4.52s` for incremental
and replay-envelope regression. The full real-month evaluator has **not yet**
been rerun with this artifact; 16/18 is therefore not a formal measured claim.

The deterministic replay gate now has a two-fresh-output implementation and
tamper-resistant evidence envelope. Opt-in real-month verification passed:
`1 passed in 2981.09s`; both fresh runs yielded partition
`3c194baf309486c16dd8f7f9e1916f4a1a4af49c9b108bcc06ce693eee615ba9`
and independent row-comparison ledger
`c3b16aa0f7618e702e5bcab8b977b1919a75f72c5d65795576a1eeb74dd0bca8`.
Exact replay evidence ID:
`349b09b145cd7f7877d0989b0c72d8a4f0cd621391fc032663a1d9221eef726b`.
The formal evaluator additionally requires this evidence to bind the currently
evaluated partition, candidate census, coverage, scoped ledger and comparison
ledger. The formal real-month evaluator rerun passed:
`1 passed, 12 deselected in 5254.69s` with
`V52_REAL_MONTH_GATES=1` and `-k
real_month_partition_and_lineage_gates_require_source_pins`. It asserts
**17/18 source-pinned gates PASS** and `CLEAN_ROOM_STANDALONE = FAIL`.
The clean-room evidence producer and formal rederivation hook exist, but
missing explicit external private CAS prevents a formal Gate 18 PASS.
Checkpoint 18 is still FAIL / OPEN.

## TDD negatives already exercised

- Rehashed numeric values fail only the relevant return or excursion group.
- Rehashed barrier outcome fails the barrier group.
- Rehashed lineage swap fails lineage rather than being disguised as a numeric mismatch.
- `AVAILABLE` with no numeric value fails state semantics, even after all hashes are rebuilt.
- Unknown rehashed label state raises a fail-closed error instead of crashing the gate evaluator.
- A mixed unsafe row with one missing reason is rejected even if other unsafe values have valid reasons.
- Count-preserving NOT_LABEL_SAFE reason swaps change exact evidence identity.
- A valid but different active partition with a rehashed manifest fails the independent expected-set check.
- A missing supersession for a removed predecessor partition fails; noncanonical manifest bytes fail.
- Wrong or missing exact evidence IDs remain FAIL.

## Verification boundary

- Latest Gate V2 focused suite: `27 passed, 2 skipped in 525.88s`; skips are opt-in real-month tests.
- Latest opt-in real-month formal evaluator: `1 passed in 1168.66s`, asserting 11 precise PASS results and seven fail-closed missing-evidence results. This run includes physical manifest verification.
- Previous real-month evaluator revision: `1 passed in 1171.78s`; it checked 26,899 rows, but predates the later state/manifest refinements and is **not** final Gate V2 acceptance.
- Manifest/unsafe focused regression: `5 passed in 0.18s` and `3 passed in 0.21s` respectively.
- New state-combination and unknown-state regression tests individually passed after RED failures.
- `scripts/verify_standalone.py`: five checks PASS, zero violations.
- Latest ordinary clean-room run: `788 passed, 257 skipped in 8.01s`, build,
  wheel install/smoke and zero-project-dependency acceptance true; archive
  findings empty. Its skipped private-CAS tests are **not** formal Gate 18
  evidence.
- `python -m compileall` on changed evaluator modules: PASS.
- `git diff --cached --check`: PASS.

The complete mutation suite, full pytest, clean-room, build/wheel,
public-ref hygiene, candidate census, Task 12
preregistration and final immutable Checkpoint 18 acceptance are **not yet
complete**. Do not infer a Gate V2 PASS or open Checkpoint 19 from this report.

Current machine limitation: `V5_2_PRIVATE_CAS_ROOT` is unset and the
previously documented `%LOCALAPPDATA%/V5_2/private-cas` is not present in this
environment. The formal clean-room producer therefore fails before clone,
as required; focused fail-closed tests: `3 passed in 0.17s`. Ordinary
clean-room acceptance above is not a substitute for this missing private-CAS
evidence. No runtime fallback to the main checkout or sibling worktree was
introduced.

Local full pytest baseline (launched before the last three clean-room
fail-closed cases were added): `1038 passed, 7 skipped in 3534.67s`, exit 0.
The last clean-room focused cases separately passed `3 passed in 0.17s`.
This does not constitute one final full-suite run against the exact final
worktree. Tracked credential-pattern scan found zero matching files; the only
tracked `.env*` file is `.env.example` with an empty `TUSHARE_TOKEN=` value.

The fresh-checkout runner was narrowed to a single-branch, depth-1 `file://`
Git transport after a diagnostic full-history local clone proved needlessly
expensive. `git ls-remote` on that exact file URL resolved the frozen feature
HEAD. The interrupted diagnostic clone remains only in the machine's Temp
directory because recursive cleanup was rejected by the command policy; it
is not a provider source, repository artifact, or pushed content. This is not
formal private-CAS clean-room evidence.
