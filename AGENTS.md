# V5.2 Project Instructions

This repository is the only runtime and source boundary for V5.2. It must not
import or read any earlier project, sibling checkout, local-path dependency,
submodule, runtime fact root or environment-provided source tree.

## Hard gates

- Zero imports from `g1`, `v2`, `v4`, `v5`, `v5_1` or `shared_core`.
- Every research input is point-in-time safe; future data is forbidden.
- Historical universes include later-delisted securities and dated ST,
  suspension and listing state. Current membership cannot backfill history.
- Random train/test split is forbidden; use preregistered walk-forward ranges.
- `research_locked=true`; broker/live trading and automatic orders are forbidden.
- A deterministic score is not a probability or evidence of effectiveness.
- Do not develop complex strategy work before P0 data correctness passes.
- Do not claim alpha until locked out-of-sample evidence passes.

All behavior changes use test-first development. A phase passes only with fresh
full-suite, static independence and clean-room evidence.
