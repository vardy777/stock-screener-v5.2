from datetime import date, datetime, timezone

import pytest

from v5_2.data.security_status_facts import SecurityStatusIntervalFactV1, StatusKind
from v5_2.data.security_status_repository import SecurityStatusRepository, StatusResolutionError


UTC = timezone.utc
SESSION = date(2025, 1, 3)
AS_OF = datetime(2025, 1, 3, 8, tzinfo=UTC)


def interval(kind, value, *, start=date(2025, 1, 1), end=None, available=datetime(2025, 1, 1, tzinfo=UTC), source=None):
    return SecurityStatusIntervalFactV1.create(
        security_identity="000001.SZ", status_kind=kind, status_value=value,
        effective_from=start, effective_to=end, published_at=available,
        available_at=available, availability_basis="VERIFIED_TIMESTAMP",
        source_fact_id=source or f"{kind}-{value}-{start}", source_name="test", policy_version="status-v1",
    )


def complete(*extra):
    return (
        interval(StatusKind.LISTING, "LISTED"),
        interval(StatusKind.RISK_WARNING, "CLEAR"),
        interval(StatusKind.SUSPENSION, "TRADING"),
        interval(StatusKind.IDENTITY, "000001.SZ"),
        *extra,
    )


def test_formal_projection_fails_closed_when_dimension_is_missing() -> None:
    repository = SecurityStatusRepository(complete()[:-1], identities=("000001.SZ",))
    with pytest.raises(StatusResolutionError, match="missing"):
        repository.project("000001.SZ", SESSION, AS_OF)


def test_formal_projection_fails_closed_on_overlap_or_conflict() -> None:
    repository = SecurityStatusRepository(
        complete(interval(StatusKind.SUSPENSION, "SUSPENDED", start=date(2025, 1, 2))),
        identities=("000001.SZ",),
    )
    with pytest.raises(StatusResolutionError, match="conflicting"):
        repository.project("000001.SZ", SESSION, AS_OF)


def test_adjacent_intervals_resolve_without_overlap() -> None:
    facts = [fact for fact in complete() if fact.status_kind is not StatusKind.SUSPENSION]
    facts.extend((
        interval(StatusKind.SUSPENSION, "SUSPENDED", end=date(2025, 1, 2)),
        interval(StatusKind.SUSPENSION, "TRADING", start=date(2025, 1, 3)),
    ))
    projected = SecurityStatusRepository(facts, identities=("000001.SZ",)).project("000001.SZ", SESSION, AS_OF)
    assert projected.is_suspended is False
    assert projected.is_tradable is True


def test_not_yet_available_status_fails_closed() -> None:
    facts = [fact for fact in complete() if fact.status_kind is not StatusKind.RISK_WARNING]
    facts.append(interval(StatusKind.RISK_WARNING, "ST", available=datetime(2025, 1, 4, tzinfo=UTC)))
    with pytest.raises(StatusResolutionError, match="not_available"):
        SecurityStatusRepository(facts, identities=("000001.SZ",)).project("000001.SZ", SESSION, AS_OF)


def test_diagnostic_reports_skipped_reasons_and_is_not_research_eligible() -> None:
    repository = SecurityStatusRepository(complete()[:-1], identities=("000001.SZ",))
    result = repository.diagnose_tradable_universe(SESSION, AS_OF)
    assert result.included_symbols == ()
    assert result.skipped_symbols == ("000001.SZ",)
    assert result.missing_count == 1
    assert result.coverage_ratio == 0
    assert result.research_eligible is False


def test_tradable_universe_returns_deterministic_effective_identities() -> None:
    repository = SecurityStatusRepository(complete(), identities=("000001.SZ",))
    assert repository.tradable_universe(SESSION, AS_OF) == ("000001.SZ",)
