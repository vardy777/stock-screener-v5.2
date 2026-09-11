# V5.2 Phase 1B-2D Financial Disclosures Design

## Scope

Phase 1B-2D adds only immutable, point-in-time financial-disclosure facts. It reuses the Phase 1A provider, raw-artifact, approval, manifest and fail-closed patterns. It does not implement derived factors, TTM, growth, ranking, labels, ML, backtests, a scheduler, or Phase 1B exit.

## Provider-first boundary

Probe `income`, `balancesheet`, `cashflow`, `fina_indicator`, `forecast`, and `express` without assuming support. Only successful endpoints may enter the allowlist. The candidate approval scope is the three primary statements; provider-derived indicators and forward-looking/express disclosures remain machine-visible as unsupported unless independently validated in their own semantics.

## Facts and time

`FinancialDisclosureFactV1` identifies a security, statement, metric, reporting period, report type, publication/version marker and value. It separately records `period_end`, `published_at`, and `available_at`. Date-only historical publication uses the next approved trading session at 16:30 Asia/Shanghai. Acquisition timestamps never reconstruct historical availability.

Income and cash-flow values are `PERIOD_CUMULATIVE`; balance-sheet values are `POINT_IN_TIME`. Unit, currency and scaling are explicit and never inferred from magnitude. Report type is carried from a validated provider/report contract, not guessed solely from the month.

## Revisions and querying

Equivalent duplicates collapse deterministically. Conflicting versions require an explicit later publication/version marker and supersession link; otherwise they are quarantined. The repository returns only the latest version visible at the requested cutoff. Missing approval, manifest, coverage, identity, metric, version lineage, or quarantine safety raises `NOT_RESEARCH_SAFE`.

## Evidence and publication

A deterministic inventory pins the approved historical universe and upstream approvals. Samples are frozen before official comparison across exchange, period, era, statement and metric strata. Gates separately report structural, PIT, cross-source, revision, value/unit semantics, historical/catch-up coverage, survivorship, rolling readiness, exception budget and systematic defect. Only every correctness-critical gate passing can produce scoped approval, approved facts and a DatasetManifest.

## Failure behavior

Unsupported endpoints and metrics remain visible. Missing rows are classified, never converted to zero or silently dropped. If the provider exposes only final restated values without recoverable version history, revision remains PENDING and publication remains disabled for the affected scope.
