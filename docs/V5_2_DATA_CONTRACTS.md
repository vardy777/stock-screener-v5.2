# V5.2 Data Contracts

All future facts will be immutable, content-addressed and source-lined. Times
must be timezone-aware. `known_at` or `available_at` must not exceed a research
run's `as_of`. Revisions append rather than overwrite.

Planned contracts are SecurityMasterFact, DailySecurityStatusFact,
DailyBarFact, CorporateActionFact, FinancialDisclosureFact, DatasetManifest,
ResearchRunManifest, FeatureSnapshot, LabelSet, RankingFact, WatchlistFact and
EvaluationReport.

Phase 0 implements only the generic canonical serialization, content identity
and immutable atomic store used by those future contracts. It does not claim
that historical coverage, corporate actions or DailyBar correctness pass.
