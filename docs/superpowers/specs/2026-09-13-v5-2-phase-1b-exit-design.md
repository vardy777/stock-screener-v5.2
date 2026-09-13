# V5.2 Phase 1B Historical PIT Exit Design

## Scope

Phase 1B Exit is a thin, read-only composition and acceptance layer. Existing
facts, availability policies, repositories, approvals, evidence, and manifests
remain authoritative. The Exit layer does not store facts or reinterpret PIT.

## Components

- `HistoricalResearchCutoffContractV1` binds one approved open session to one
  timezone-aware Asia/Shanghai cutoff and the exact calendar approval.
- `Phase1BCoverageMatrixV1` derives coverage and supported/unsupported scope
  from the six pinned approvals and manifests.
- `HistoricalResearchSessionV1` distinguishes fatal lineage/base-dataset
  failures from security-scoped optional-data unsafety and emits deterministic
  reason codes and lineage hashes.
- `Phase1BExitAcceptanceV1` content-addresses the repository head, cutoff,
  coverage, dry runs, chaos/replay evidence, gates, limitations, and all six
  approval/manifest IDs.

## Failure boundary

Invalid cutoff, calendar/universe lineage, manifest/approval integrity,
revocation, or unavailable required base-dataset coverage makes the session
invalid. Missing or unsupported optional corporate-action/financial input keeps
the session valid and blocks only the affected security requirement.

## Frozen scope

Base research requires calendar, effective universe identity, daily bar, and
security status. Corporate actions and financial metrics are opt-in. Financial
publication remains `OBSERVED_FACTS_ONLY` with partial panel completeness.
Corporate actions support only `CASH_DIVIDEND` and `BONUS_SHARE`; unsupported
types remain machine-visible and fail closed.

## Acceptance consequence

The Exit evaluator may return FAIL even though all component phases were closed.
In particular, the four historical dry runs must use actual pinned coverage; it
must not manufacture early, middle, recent, or 2026 base-market availability.
