# V5.2 Public Corpus Exposure — Targeted Feature History Remediation

## Scope and decision

The public `phase2a-implementation` history contained 38 exact Status objects
listed in `Phase2BPrivateCorpusManifestV1`
`0489978b34834817ee0e33dbd46d4e90b86a14e9827f89ba5b93433797c2ddd6`.
They total 52,219,846 bytes. This is a **recorded historical public exposure**;
rewriting active refs does not prove erasure from GitHub caches or external clones.
The repository remained public. No whole-repository visibility change, `main`
rewrite, PR, merge, tag, release, provider request, or Checkpoint 19 pilot was
performed.

The affected public feature HEAD was
`cecba5018582ee4daaf403244324c3f29b70ee67`. The 38 bytes-identical Git
blobs first entered that feature history in `da0113fee4a6ddb707e54d1e38aa260573fbcf14`
(34 objects) and `f57622d14d83dbe094e3312c91b96fb5bad097a6` (4 objects).
An exact private incident ledger outside this repository records each SHA-256,
byte size, path, introducing commit, and all feature commits containing the
object. A verified private Git bundle preserves the pre-remediation local
work and incident evidence. The private taint-inventory file SHA-256 is
`0f0fc67f0346fc5a70911d7056a203fc3b96a102ae2f10355a924653c01439fc`;
the private incident-record file SHA-256 is
`c7a694bd7bb743bc953f20f8a0b4b6bb3e8b8e96df3e78f38be86de72477da32`.

## Containment and rewrite

The remote feature ref was temporarily deleted after the private backup and
taint inventory were complete. `git-filter-repo` 2.47.0 removed only the 38
exact paths from a disposable single-feature clone. The rewritten HEAD tree
had 1,086 files versus 1,124 before: exactly the 38 tainted files disappeared,
and every retained file had the same Git blob ID. The three unpushed private-CAS
development commits survived the rewrite. The previously untracked resolver
and tests were restored from verified private copies and committed separately.

The first sanitized remote feature HEAD is
`fa2005027b7b191343e475cd27562eca953d0fe7`. GitHub's branch API and
recursive tree API confirmed two branches, no truncated tree, no affected
path/blob in the feature HEAD, and unchanged `main`:
`4254bb73a3eef054c7d998c43fd36521fe93db66`. The rewritten local
feature history and all current local refs have zero reachable tainted blobs;
the remote feature points to that exact content-addressed HEAD. The old local
branch was removed after the private bundle was verified, preventing an
ordinary future push from restoring the exposed history.

The new Git-index guard checks staged blob contents, not merely worktree
bytes. The current-ref guard inspects every reachable Git object by exact
SHA-256 and byte size; a clean current tree with a tainted other branch fails.
The real public manifest is pinned by the checkout hygiene test. The existing
`/data/` ignore rule remains in force.

## Private CAS and clean-room evidence

Only after the active public refs were sanitized, the 44 exact manifest
objects were copied into a physical private staging area outside Git and
verified by byte size and SHA-256. Two Calendar source paths in the original
worktree resolved through a Windows junction, so direct import correctly
failed closed; the physically copied, rehashed source set was used instead.
The private CAS contains 44 verified objects, 83,290,934 bytes, with inventory
hash `a559e02eb8726289bb19c80daa37f78c8041e58bf6884d6c92c382da91ab6536`.
No corpus bytes were added to Git.

A fresh checkout of the sanitized branch started without the ignored Status
source directory. Missing CAS failed with `PRIVATE_CORPUS_UNAVAILABLE` before
staging. The explicit private CAS then staged and reverified all 44 objects.
A fresh Python 3.11 environment installed the project and reproduced the
approved `2010-01` month from exact five-domain sources:

| Measure | Replayed |
| --- | ---: |
| Effective anchors | 34,271 |
| Materialized rows | 26,899 |
| Excluded before label | 6,950 |
| Scoped excluded | 422 |

Partition ID: `3c194baf309486c16dd8f7f9e1916f4a1a4af49c9b108bcc06ce693eee615ba9`.
Coverage hash: `b6108848b3cd469f37f1baaa43e4c3b5aa5f253663d47ac9e32e9fc8022b7e3c`.
Scoped ledger ID: `a1092d6465b32c7141a9befb290938adecca2f08b8fb646389becf941f9c656e`.
Integration ID: `df54c5a80093115d469ec0257127ecd59c304f7c6d440ad2dc8bd4b85d641f67`.
The explicit, committed private-CAS clean-room test repeated the full
calculation against the same remote feature content in `599.97s` and passed
all four counts and all four pinned IDs (`1 passed`). No source was read from
the original checkout at runtime.
An independent source-pinned Master/Calendar census in the same fresh checkout
recomputed the 34,271 candidate anchors and their 26,899 / 6,950 / 422
dispositions; evidence ID
`834534a947d79b10a16404ae35430aafb63b36e0ac467d46b97a57117959ef75`
matched the prior immutable result.
The source-pinned independent calculator reread the physical partition and
recomputed all 26,899 rows: mismatches `0`, comparison ledger ID
`c3b16aa0f7618e702e5bcab8b977b1919a75f72c5d65795576a1eeb74dd0bca8`.

The repository's ordinary `clean_room_acceptance.py` returned `782 passed,
218 skipped`; build, wheel install/smoke, archive scan, and zero-project-
dependency checks all passed. The initial run had one test-scoping failure:
a Git-ref hygiene test ran inside a wheel-only directory without `.git`.
The test now skips only in non-Git installations; the actual checkout ref
audit remains mandatory and was run separately.

The first source-installed full suite after the history rewrite returned
`993 passed, 4 skipped, 1 failed, 2 errors in 985.51s`. The three non-passes
shared one cause: two real-audit tests still loaded the now-incomplete old
Git-tracked Status portable directory. They were retargeted to the exact
private-CAS `data/replay_status_authority` role, with a file-level availability
check; no production semantics changed. The 8 retained governance files under
the two roots were byte-identical. Focused regression after correction:
`3 passed, 1 skipped in 90.46s`, where the skip requires an explicit offline
status staging root. Final `python -m pytest -q` rerun returned
`996 passed, 4 skipped in 628.54s`. The four skips were explicit local-data
entrypoints: private-corpus manifest, real-month integration, private-CAS
clean-room, and offline Status staging. The gated private-CAS clean-room was
run separately and passed; its generic skip is not counted as that result.

## Residual risk and next gate

A private, hash-only GitHub Support request draft identifies the old affected
range and all 38 paths/object identities. It has **not been submitted**.
The old `cecba5018582ee4daaf403244324c3f29b70ee67` commit remained
readable through GitHub's commit API after the ref rewrite. GitHub cache,
dangling-object, or external-clone erasure is not claimed.
Historical public exposure remains `YES / REMEDIATED_FROM_ACTIVE_REFS`.

`CHECKPOINT 18 = FAIL / OPEN` pending final Gate V2 predicates, mutation
coverage, candidate census, Task 12 preregistration, full verification, and
independent review. `CHECKPOINT 19 PILOT = NOT RUN`.
