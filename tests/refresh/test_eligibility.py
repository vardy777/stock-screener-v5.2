from datetime import date

import pytest

from v5_2.refresh.eligibility import (
    IPO_SEASONING_SESSIONS, UniverseCoverageV1, evaluate_ipo_eligibility,
)


OPEN = tuple(date(2026, 9, day) for day in (11, 14, 15, 16, 17, 18, 21))


def evaluate(session, **overrides):
    values = dict(symbol="688801.SH", list_date=date(2026, 9, 11),
                  as_of_session=session, approved_open_sessions=OPEN,
                  official_identity_verified=True, bar_coverage_valid=True,
                  status_resolved=True)
    values.update(overrides)
    return evaluate_ipo_eligibility(**values)


def test_listing_day_is_known_but_not_counted_in_five_session_seasoning():
    result = evaluate(date(2026, 9, 11))
    assert IPO_SEASONING_SESSIONS == 5
    assert result.known_security and not result.research_eligible
    assert result.completed_post_listing_sessions == 0
    assert result.exclusion_reason == "IPO_SEASONING"


@pytest.mark.parametrize("day,count", [(14, 1), (15, 2), (16, 3), (17, 4)])
def test_first_four_post_listing_sessions_remain_excluded(day, count):
    result = evaluate(date(2026, 9, day))
    assert result.completed_post_listing_sessions == count
    assert not result.research_eligible


def test_fifth_post_listing_session_is_first_eligible_completed_cutoff():
    result = evaluate(date(2026, 9, 18))
    assert result.eligible_after_session == date(2026, 9, 18)
    assert result.research_eligible


def test_weekend_and_holiday_absence_never_counts_as_seasoning():
    sparse = (date(2026, 9, 11), date(2026, 9, 14), date(2026, 9, 18),
              date(2026, 9, 21), date(2026, 9, 22), date(2026, 9, 23))
    result = evaluate(date(2026, 9, 22), approved_open_sessions=sparse)
    assert result.completed_post_listing_sessions == 4
    assert not result.research_eligible


@pytest.mark.parametrize("field,reason", [
    ("official_identity_verified", "IDENTITY_NOT_VERIFIED"),
    ("bar_coverage_valid", "BAR_COVERAGE_INCOMPLETE"),
    ("status_resolved", "STATUS_UNRESOLVED"),
])
def test_mature_ipo_still_fails_closed_on_onboarding_evidence(field, reason):
    result = evaluate(date(2026, 9, 18), **{field: False})
    assert not result.research_eligible
    assert result.exclusion_reason == reason


def test_multiple_ipos_and_historical_live_calls_use_the_same_pure_rule():
    first = evaluate(date(2026, 9, 18))
    second = evaluate_ipo_eligibility(
        symbol="X.SH", list_date=date(2026, 9, 10), as_of_session=date(2026, 9, 18),
        approved_open_sessions=OPEN, official_identity_verified=True,
        bar_coverage_valid=True, status_resolved=True)
    assert first.research_eligible and second.research_eligible
    assert evaluate(date(2026, 9, 18)) == first


def test_one_security_scoped_exclusion_is_visible_without_becoming_systemic():
    excluded = evaluate(date(2026, 9, 11))
    eligible = evaluate_ipo_eligibility(
        symbol="600000.SH", list_date=date(1999, 11, 10),
        as_of_session=date(2026, 9, 11), approved_open_sessions=tuple(
            date(1999, 11, day) for day in (10, 11, 12, 15, 16, 17)
        ) + OPEN,
        official_identity_verified=True, bar_coverage_valid=True, status_resolved=True)
    coverage = UniverseCoverageV1.create((excluded, eligible))
    assert coverage.excluded_security_count == 1
    assert coverage.research_eligible_count == 1
    assert coverage.exclusion_reason_counts == (("IPO_SEASONING", 1),)
    assert coverage.systematic_defect is False


def test_duplicate_identity_is_a_systemic_coverage_input_error():
    result = evaluate(date(2026, 9, 11))
    with pytest.raises(ValueError, match="duplicate identity"):
        UniverseCoverageV1.create((result, result))
