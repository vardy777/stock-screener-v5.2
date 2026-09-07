# V5.2 Phase 1B-2A Evidence Closure Design

## Scope and immutable inputs

This repair consumes the frozen Phase 1B-2A request inventory, 116 raw payloads, 61-entry sample inventory, and 6,489-key missing-bar inventory. It does not reacquire them, rewrite Phase 1B-1 artifacts, or enter Phase 1B-2B. Corrections are new content-addressed artifacts.

The frozen sample inventory contains 61 entries but 56 unique event IDs because five listing/delisting cases are duplicated. Both counts are reported; no sample is silently replaced.

## Consistency and publication boundary

The publisher reads `UNEXPLAINED` from the pinned classification artifact. Equivalence limitations, approval findings, and acceptance output are derived from the same value. No unexplained count is hard-coded.

## Exception governance

Before inspecting final dispositions, freeze `StatusExceptionBudgetV2` at:

- absolute unexplained limit: 250 (approximately 0.01% of 2,487,799 applicable symbol-sessions);
- ratio limit: 0.0001;
- per-security total limit: 20;
- per-security consecutive-session limit: 10;
- exchange concentration limit: 0.75;
- calendar-month concentration limit: 25;
- unknown effective-interval limit: 0;
- any systematic-pattern flag fails the budget.

These thresholds permit sparse idiosyncratic operational gaps but reject concentrated provider, exchange, temporal, or identity failures. Passing records become explicit, content-addressed `LOCAL_EXCEPTION` quarantine records and remain research-excluded.

## Historical universe reconciliation

`HistoricalUniverseReconciliationV1` classifies all 542 observed-outside-universe identities using historical security-master rows, target A-share normalization, research coverage intersection, and the frozen identity graph. Output categories are `TARGET_A_SHARE_REQUIRED`, `NON_TARGET`, `OUTSIDE_RESEARCH_COVERAGE`, `IDENTITY_ALIAS`, `EFFECTIVE_IDENTITY_ALREADY_PRESENT`, `LEGACY_CODE`, `LOCAL_EXCEPTION`, and `UNRESOLVED`.

Required target identities produce `HistoricalUniverseSupplementV1`, pinning original universe ID, effective intervals, official evidence IDs, reason, and content hash. It never mutates the original universe. Only supplement identities may trigger narrowly scoped bar/status acquisition and immutable approval supersession.

## Official sample ledger

Every one of the 61 frozen entries produces an `OfficialStatusSampleObservationV1` with entry index, event ID, security, session, provider observation, official observation, semantic mapping, disposition (`MATCH`, `MISMATCH`, `UNRESOLVED`, or `OFFICIAL_REFERENCE_UNAVAILABLE`), official URL, retrieval timestamp, and content hash. An unavailable page is never a match. Completeness and mismatch-systematicity are separate gates.

## Status availability

The V5.2 status research cutoff is 16:30 Asia/Shanghai, after official close plus a conservative 90-minute buffer. `StatusAvailabilityPolicyV2` supports:

- `PUBLICATION_TIMESTAMP_BASED`: exact verified timestamp, usable only when at or before cutoff;
- `MARKET_OBSERVABLE_BY_CLOSE`: daily full-day suspension and the security name/risk-warning state observable during session D, available at D 16:30;
- `CONSERVATIVE_AFTER_CLOSE`: verified same-date official publication without exact time, available at D 16:30;
- `NEXT_SESSION_SAFE`: ambiguous date-only event, available at the next approved session's 16:30 cutoff.

Listing/delisting effective dates alone never establish knowledge time. Acquisition timestamps never become historical availability.

## Re-evaluation and approval

The exact 6,489 keys are reclassified. Confirmed full-day suspensions remain `SUSPENDED`; budget-passing unresolved cases become explicit `LOCAL_EXCEPTION`; unquarantined cases remain `UNEXPLAINED`. Approval may be `APPROVED_WITH_RULES` only when acquisition, structure, PIT policy, reconciled/supplemented survivorship, sufficient official evidence, exception budget, and systematic-defect gates all pass. Otherwise it remains `PENDING` or `REJECTED`, with zero approved facts and no manifest.

## Verification and exit

All changes use RED/GREEN TDD. The acceptance report appends exact commands, counts, artifact IDs, approval outcome, full-suite, standalone, clean-room, credential scan, Git push equality, and clean-worktree evidence. Even if 1B-2A passes, Phase 1B-2 overall and Historical PIT Data remain FAIL and the label engine remains locked.
