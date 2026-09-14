from datetime import date

import pytest

from v5_2.labels.calculation import IncompleteCalendarCoverage, resolve_label_horizons


def d(value: str) -> date:
    return date.fromisoformat(value)


def test_horizons_use_strict_exchange_sessions_across_weekend_and_holiday():
    sessions = tuple(map(d, ("2024-01-05", "2024-01-08", "2024-01-10", "2024-01-11", "2024-01-12", "2024-01-15")))
    result = resolve_label_horizons(d("2024-01-05"), sessions, d("2024-01-15"))
    assert (result.h1, result.h3, result.h5) == (d("2024-01-08"), d("2024-01-11"), d("2024-01-15"))
    assert result.window_5d == sessions[1:]


def test_uncompleted_horizon_is_pending_not_missing():
    sessions = tuple(map(d, ("2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08", "2024-01-09")))
    result = resolve_label_horizons(d("2024-01-02"), sessions, d("2024-01-04"))
    assert result.completed == (True, False, False)


@pytest.mark.parametrize("sessions, message", [
    (("2024-01-02", "2024-01-03", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"), "DUPLICATE"),
    (("2024-01-02", "2024-01-04", "2024-01-03", "2024-01-05", "2024-01-08", "2024-01-09"), "NON_MONOTONIC"),
    (("2024-01-01", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08", "2024-01-09"), "ANCHOR"),
    (("2024-01-02", "2024-01-03", "2024-01-04"), "INSUFFICIENT"),
])
def test_structurally_invalid_calendar_fails_closed(sessions, message):
    with pytest.raises(IncompleteCalendarCoverage, match=message):
        resolve_label_horizons(d("2024-01-02"), tuple(map(d, sessions)), d("2024-01-09"))
