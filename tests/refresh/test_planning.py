from datetime import date, datetime, timedelta, timezone

from v5_2.refresh.planning import ApprovedCalendarView, detect_session_gaps, resolve_target_session


SH = timezone(timedelta(hours=8))
SESSIONS = (date(2026, 9, 10), date(2026, 9, 11), date(2026, 9, 14), date(2026, 9, 15))


def calendar(through=date(2026, 9, 15)):
    return ApprovedCalendarView("m" * 64, date(2026, 9, 1), through, SESSIONS)


def test_open_day_after_cutoff_targets_today_without_asserting_readiness():
    result = resolve_target_session(datetime(2026, 9, 14, 17, 0, tzinfo=SH), calendar())
    assert result.target_session == date(2026, 9, 14)
    assert result.is_trading_day is True
    assert not hasattr(result, "research_ready")


def test_before_cutoff_and_closed_day_target_previous_open_session():
    before = resolve_target_session(datetime(2026, 9, 14, 16, 29, tzinfo=SH), calendar())
    weekend = resolve_target_session(datetime(2026, 9, 13, 20, 0, tzinfo=SH), calendar())
    assert before.target_session == date(2026, 9, 11)
    assert weekend.target_session == date(2026, 9, 11)
    assert weekend.is_trading_day is False


def test_uncovered_today_fails_closed():
    result = resolve_target_session(datetime(2026, 9, 16, 20, 0, tzinfo=SH), calendar())
    assert result.target_session is None
    assert result.reason == "CALENDAR_DOES_NOT_COVER_TODAY"


def test_gap_detection_finds_middle_gap_and_all_catch_up_sessions():
    middle = detect_session_gaps(SESSIONS, (date(2026, 9, 10), date(2026, 9, 11), date(2026, 9, 15)), date(2026, 9, 15))
    catch_up = detect_session_gaps(SESSIONS, (date(2026, 9, 10),), date(2026, 9, 15))
    assert middle.missing_sessions == (date(2026, 9, 14),)
    assert catch_up.missing_sessions == (date(2026, 9, 11), date(2026, 9, 14), date(2026, 9, 15))
    assert date(2026, 9, 13) not in catch_up.missing_sessions
