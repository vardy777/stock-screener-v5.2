# Phase 2B Checkpoint 18 — Five-Domain Real-Month Interim Record

Checkpoint 18 remains **FAIL / OPEN**. This record covers the source-pinned
production five-domain path and one bounded month, not Gate Evidence V2,
18-gate acceptance, pilot authorization, or broad materialization.

## Exact production source path

The offline `HistoricalFiveDomainProducerV1` pins the approved Calendar,
portable Security Master, Historical Daily Bar authority, portable Status
authority, and scoped Corporate Action facts plus quarantine audit. It
produces `AnchorDispositionV1`, `HistoricalAnchorLineageV1`, five-domain
`LabelInputBundleV1`, and frozen `ReferenceLabelEngine` results. Financial is
not a sixth domain. The original IPO seasoning authority is called, not
reimplemented. A cross-transition identity window and missing bar without
proved full-day suspension are security/session scoped exclusions. No source
is manufactured from a Phase 2A slot fixture or provider request.

## Real 2010-01 result

Command:

```powershell
$env:V52_REAL_MONTH_INTEGRATION='1'
.venv\Scripts\python.exe -m pytest tests/labels/test_historical_month_integration.py -q -s
```

Result after adding immutable scoped ledger: `2 passed in 1172.05s`.
The test independently recomputed the entire month twice into the same
create-or-identical output directory and asserted equal integration objects.

| Measure | Actual |
| --- | ---: |
| Effective anchors | 34,271 |
| Materialized label rows | 26,899 |
| Excluded before label | 6,950 |
| Scoped excluded anchors | 422 |
| Scoped excluded securities | 27 |
| Scoped reason | `UNEXPLAINED_MISSING_BAR`: 422 |

The accounting identity is `34,271 = 26,899 + 6,950 + 422`.

- Partition ID: `3c194baf309486c16dd8f7f9e1916f4a1a4af49c9b108bcc06ce693eee615ba9`
- Coverage hash: `b6108848b3cd469f37f1baaa43e4c3b5aa5f253663d47ac9e32e9fc8022b7e3c`
- Scoped exclusion ledger ID: `a1092d6465b32c7141a9befb290938adecca2f08b8fb646389becf941f9c656e`
- Integration ID: `df54c5a80093115d469ec0257127ecd59c304f7c6d440ad2dc8bd4b85d641f67`

The ledger physically contains every excluded security/session, domain,
reason, and evidence IDs. Twenty-six securities have 16 affected anchors
each; one has six. This finite set is quarantined, not interpreted as zero
bar or proved suspension. Further gate-level audit must establish that the
pattern does not reflect a shared source-coverage defect.

The first successful full-month run, before the ledger writer was added,
produced the same 26,899-row partition and coverage hash and passed twice
(`1 passed in 1184.47s`). The final ledger-aware run above supersedes that
interim measurement; it does not mutate the earlier partition.

## Verification and outstanding gates

- Focused Calendar/CA/producer suite before shared-cache extension:
  `13 passed, 1 skipped in 61.96s`; skip was the explicitly gated real month.
- Shared Status derivation cache tests: RED (two independent resolver calls),
  then `2 passed, 8 deselected in 0.10s`. Cache key includes exact identity,
  session, and 16:30 cutoff; both producer and assembler consume the same
  immutable derivation.
- Scoped ledger test: RED import, then `1 passed, 1 deselected in 0.11s`;
  exact read, tamper rejection, and create-or-identical collision tested.
- Final focused Calendar/CA/producer/month suite with real-month switch off:
  `16 passed, 1 skipped in 61.79s`.
- `git diff --check`: no errors before staging this report.
- DataHub/Tushare/market-data provider requests: **0**.
- Checkpoint 19 pilot: **not run**.

Formal Gate Evidence V2, semantic mutation suite, candidate census,
Task 12 preregistration, full post-change tests, and clean-room acceptance
are still pending. Status/CA/Calendar extension source artifacts used by
this run currently reside in ignored local `data/` paths and are not yet
portable from the feature branch. Therefore this report makes **no**
remote clean-room or Checkpoint 18 PASS claim.
