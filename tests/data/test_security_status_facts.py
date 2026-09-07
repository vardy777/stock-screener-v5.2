from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

from v5_2.data.security_status_facts import (
    DailySecurityStatusFactV1,
    SecurityStatusIntervalFactV1,
    StatusFactError,
    StatusKind,
)


UTC = timezone.utc


def test_interval_keeps_effective_and_knowledge_time_separate() -> None:
    fact = SecurityStatusIntervalFactV1.create(
        security_identity="000001.SZ", status_kind=StatusKind.RISK_WARNING,
        status_value="ST", effective_from=date(2025, 1, 2), effective_to=date(2025, 1, 31),
        published_at=datetime(2025, 1, 1, 9, tzinfo=UTC),
        available_at=datetime(2025, 1, 1, 10, tzinfo=UTC),
        availability_basis="VERIFIED_TIMESTAMP", source_fact_id="official-1",
        source_name="szse", policy_version="status-v1",
    )
    assert fact.effective_from == date(2025, 1, 2)
    assert fact.available_at == datetime(2025, 1, 1, 10, tzinfo=UTC)
    assert fact.verify()


def test_interval_rejects_invalid_time_and_range() -> None:
    common = dict(
        security_identity="000001.SZ", status_kind=StatusKind.SUSPENSION,
        status_value="SUSPENDED", effective_from=date(2025, 1, 3),
        effective_to=date(2025, 1, 2), published_at=None,
        available_at=datetime(2025, 1, 2, tzinfo=UTC), availability_basis="DATE_ONLY_NEXT_SESSION",
        source_fact_id="provider-1", source_name="datahubco_tushare_proxy", policy_version="status-v1",
    )
    with pytest.raises(StatusFactError, match="interval"):
        SecurityStatusIntervalFactV1.create(**common)
    common["effective_to"] = None
    common["available_at"] = datetime(2025, 1, 2)
    with pytest.raises(StatusFactError, match="timezone"):
        SecurityStatusIntervalFactV1.create(**common)


def test_daily_projection_hashes_effective_identity_and_detects_tamper() -> None:
    fact = DailySecurityStatusFactV1.create(
        security_identity="300114.SZ", session=date(2025, 2, 14),
        is_listed=True, is_delisted=False, is_risk_warning=False, is_suspended=False,
        risk_warning_excluded=True, effective_from=date(2010, 8, 27), effective_to=date(2025, 2, 16),
        available_at=datetime(2025, 2, 14, 7, tzinfo=UTC),
        source_fact_ids=("listing", "risk", "suspension", "identity"),
        source_name="v5.2-status-projection", policy_version="daily-status-v1",
    )
    assert fact.is_eligible is True
    assert fact.is_tradable is True
    assert fact.verify()
    assert not replace(fact, security_identity="302132.SZ").verify()


def test_daily_projection_derives_ineligible_and_nontradable() -> None:
    fact = DailySecurityStatusFactV1.create(
        security_identity="000001.SZ", session=date(2025, 1, 2),
        is_listed=True, is_delisted=False, is_risk_warning=True, is_suspended=False,
        risk_warning_excluded=True, effective_from=date(1991, 4, 3), effective_to=None,
        available_at=datetime(2025, 1, 2, 7, tzinfo=UTC),
        source_fact_ids=("a", "b", "c", "d"), source_name="projection", policy_version="daily-status-v1",
    )
    assert fact.is_eligible is True
    assert fact.is_tradable is False
