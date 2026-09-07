from datetime import date, datetime, timedelta, timezone

import pytest

from v5_2.data.real_audits.status_availability import (
    StatusAvailabilityError, StatusAvailabilityPolicyV1, StatusAvailabilityPolicyV2,
)


SESSIONS = (date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 6))


def test_date_only_event_is_unavailable_at_same_date_close() -> None:
    policy = StatusAvailabilityPolicyV1.date_only_next_session()
    result = policy.derive(event_date=date(2025, 1, 2), published_at=None, approved_sessions=SESSIONS)
    assert result.isoformat() == "2025-01-03T15:00:00+08:00"


def test_verified_timestamp_is_preserved_and_acquisition_time_is_ignored() -> None:
    policy = StatusAvailabilityPolicyV1.verified_timestamp()
    published = datetime(2025, 1, 2, 8, 30, tzinfo=timezone.utc)
    assert policy.derive(event_date=date(2025, 1, 3), published_at=published, approved_sessions=SESSIONS,
                         acquired_at=datetime(2026, 1, 1, tzinfo=timezone.utc)) == published


def test_date_only_event_after_calendar_coverage_fails_closed() -> None:
    with pytest.raises(StatusAvailabilityError, match="next session"):
        StatusAvailabilityPolicyV1.date_only_next_session().derive(
            event_date=date(2025, 1, 6), published_at=None, approved_sessions=SESSIONS,
        )


def test_after_close_policy_uses_conservative_1630_cutoff_and_ignores_acquisition() -> None:
    policy = StatusAvailabilityPolicyV2.conservative_after_close("FULL_DAY_SUSPENSION")
    actual = policy.derive(event_date=date(2025, 1, 2), published_at=None, approved_sessions=SESSIONS,
                           acquired_at=datetime(2026, 9, 7, tzinfo=timezone.utc))
    assert actual.isoformat() == "2025-01-02T16:30:00+08:00"


def test_v2_supports_all_four_bases() -> None:
    published = datetime(2025, 1, 2, 8, 15, tzinfo=timezone(timedelta(hours=8)))
    assert StatusAvailabilityPolicyV2.publication_timestamp("DELISTING_ANNOUNCEMENT").derive(
        event_date=SESSIONS[0], published_at=published, approved_sessions=SESSIONS) == published
    assert StatusAvailabilityPolicyV2.market_observable_by_close("RISK_WARNING_STATE").derive(
        event_date=SESSIONS[0], published_at=None, approved_sessions=SESSIONS).hour == 16
    assert StatusAvailabilityPolicyV2.next_session_safe("DATE_ONLY_STATUS").derive(
        event_date=SESSIONS[0], published_at=None, approved_sessions=SESSIONS).date() == SESSIONS[1]
