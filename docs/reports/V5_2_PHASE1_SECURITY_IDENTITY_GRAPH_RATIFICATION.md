# V5.2 Phase 1 Security Master: 6275 graph official-evidence ratification

## Scope and decision

This checkpoint ratifies only the existing `EffectiveDatedSecurityIdentityV1` graph
`6275f4df087e40a11eb12b4ece0e569865814002d4da301342c2279af98acda0`.
The old Security Master approvals did **not** adequately pin this child graph. This
new approval is graph-scoped, made on 2026-09-25; it is not a retroactive
interpretation of the old dataset approvals. Historical effective dates are not
the verification date.

The graph body was physically copied from the named V5.2 main checkout. Its
file SHA-256 is `ee07e6cf21b3ce07613f6b3936110a591678817085b34c84ca5c044429303eac`;
source and portable copies were byte-identical, and re-evaluating the graph
contract produced the unchanged graph ID above. Its original evidence IDs
`szse-listing-2010-300114` and `szse-code-change-2025-302132` remain unchanged.
Those historical labels are not being presented as newly recovered source bytes.

## Official source bytes and factual proof

| Dimension | Official source | Raw SHA-256 | Evidence artifact ID | Finding |
| --- | --- | --- | --- | --- |
| Original listing | [SZSE 2010 listing news](https://www.szse.cn/aboutus/trends/news/t20100827_518017.html), dated 2010-08-27 | `e0357fb6ddc81f4ae93f0423f7f668ebb8ba53e3ffd80baed73341baa4381f20` | `94ed51b460193c837d81ab6e916276accf15fdf4846c89b4d72621251a02c630` | 中航电测 / 300114 / 2010-08-27 / ChiNext |
| Code implementation | [SZSE-hosted issuer implementation notice](https://disc.static.szse.cn/download/disc/disk03/finalpage/2025-02-15/cedb693a-f5ee-4463-9682-ea33d406b569.PDF), board dated 2025-02-14 | `dd68049c48df826848f361fd9e7b23dd20b6805144a2e5bc36e54db638611488` | `16a3644f36adc46af76e1e016b049bc5fc60502979b8399cf4a317eb87090398` | 300114 → 302132 effective 2025-02-17; listed legal entity continues without substantive change |

These are content-addressed raw bytes in `data/phase_1b1_identity_graph_ratification/official`.
The exact raw-document path is marked `-text` in `.gitattributes` so Git's
Windows line-ending conversion cannot change the downloaded HTML bytes on
another checkout; staged and working-file Git blob IDs were checked equal.
The implementation notice was visually checked on page 1 and machine-extracted
from its four pages. The evaluator re-reads official bytes, validates their hashes
and allowlisted HTTPS source identities, parses the factual claims, and compares
them with the unchanged graph. It derives the predecessor interval end
`2025-02-16` mechanically as the day before the documented transition; no
new boundary convention was introduced.

The [ratification evidence](../../data/phase_1b1_identity_graph_ratification/governance/identity-graph-ratification-e6f2a0ab1bbfc6df9d3e52f2ba4d13b661a8407ad056bd0729571cf62aa4fe92.json)
has ID `e6f2a0ab1bbfc6df9d3e52f2ba4d13b661a8407ad056bd0729571cf62aa4fe92`.
The graph-scoped approval has ID
`a14be1c8443902fd3c28fd9ec43243710d124ba5c498cf760c9fe4396f11189f`
and scope `EXISTING_GRAPH_RATIFICATION`; it does not approve the entire
`security_master` dataset.

## Network and immutable boundary

Direct official-document request attempts: **4** (3 HTTP 200, 1 transport EOF).
The first PowerShell request to the 2010 SZSE page failed with an unexpected
EOF; `curl` then retrieved that same page. A 2025-02-07 preliminary reminder PDF
was retrieved during bounded validation, but not used for approval and its local
probe copy was removed after the stronger 2025-02-14 implementation notice was
verified. No search-engine text was used as evidence. DataHub, Tushare, and
other market-data provider requests: **0**.

The old historical bundle `968ae9660ae02f4a1e16a8eb6510a62368e44defc7f99f7ed56714364c722386`
and old approvals `f208c17a…`, `828e0e72…` were not modified. The separate
`d67d8862…` item remains a `HistoricalUniverseSupplementV1`, **not** an
identity graph; its old provenance typing defect remains open for the next
authorized checkpoint. No typed Master lineage, interval materialization,
five-domain producer, real month, or pilot was executed.

## Verification

| Command | Result |
| --- | --- |
| `.\.venv\Scripts\python.exe -m pytest tests/real_audits/test_identity_graph_ratification.py -q` | 15 passed |
| `.\.venv\Scripts\python.exe -m pytest tests/governance/test_phase_1a_boundaries.py tests/real_audits/test_identity_graph_ratification.py -q` | 23 passed |
| bundled audit Python `scripts/ratify_6275_identity_graph.py` (three replay runs after generation) | Same four content IDs; create-or-identical |
| `.\.venv\Scripts\python.exe scripts/verify_standalone.py` | PASS; forbidden imports/paths and architecture boundaries 0 |
| `.\.venv\Scripts\python.exe -m build --no-isolation` | PASS after offline-cache install of missing local `setuptools`; wheel and sdist built |
| Offline wheel install and import smoke in a disposable virtual environment | PASS; package import, ratification module import, and `RESEARCH_LOCKED` assertion |
| `.\.venv\Scripts\python.exe -m pytest -q` | 925 passed, 1 skipped in 465.43s; skip requires an explicit offline status staging root |
| Changed-file credential scan | 0 hits for API-key/token patterns |
| `git diff --cached --check` | PASS; official raw HTML is exempted from whitespace normalization only, preserving its SHA-256 |

The first post-change full-suite attempt exposed the Phase 1A AST rule against
importing `urllib.parse` in a data-audit module. The module now uses strict
official-URL syntax and an exact host allowlist; the focused governance suite
passed after that correction. No network client was added to the data module.
The offline replay requires optional `pdfplumber` in its audit runtime to
re-parse the saved official PDF bytes. The project's ordinary virtual
environment does not include that optional dependency; executing the replay
there fails explicitly rather than treating PDF claims as pre-approved.

Checkpoint 18 remains `FAIL / OPEN`. Master typing remediation awaits
independent review of this graph-only ratification.
