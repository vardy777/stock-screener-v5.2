from datetime import date

import pytest

from v5_2.data.real_audits.upstream_extension import (
    EffectiveDatedUniverseV1,
    IncrementalCalendarExtensionV1,
    UpstreamExtensionError,
)


def calendar_rows(end="20260106"):
    states = {
        "20260101": 0, "20260102": 0, "20260103": 0,
        "20260104": 0, "20260105": 1, "20260106": 1,
    }
    return tuple(
        {"exchange": exchange, "cal_date": day, "is_open": state}
        for exchange in ("SSE", "SZSE")
        for day, state in states.items() if day <= end
    )


def test_calendar_extension_is_complete_content_addressed_and_supersedes():
    item = IncrementalCalendarExtensionV1.create(
        previous_approval_id="old-calendar", coverage_start=date(2026, 1, 1),
        coverage_end=date(2026, 1, 6), rows=calendar_rows(),
        official_anchor_ids=("official-sse", "official-szse"),
    )
    assert item.supersedes_approval_id == "old-calendar"
    assert item.is_open(date(2026, 1, 5))
    assert item.next_open_session(date(2026, 1, 2)) == date(2026, 1, 5)
    assert item.content_hash == item.extension_id


def test_calendar_extension_fails_closed_without_any_date_or_exchange():
    with pytest.raises(UpstreamExtensionError, match="continuous"):
        IncrementalCalendarExtensionV1.create(
            previous_approval_id="old", coverage_start=date(2026, 1, 1),
            coverage_end=date(2026, 1, 6), rows=calendar_rows()[:-1],
            official_anchor_ids=("sse", "szse"),
        )


def test_calendar_never_inferrs_weekdays_or_out_of_coverage():
    item = IncrementalCalendarExtensionV1.create(
        previous_approval_id="old", coverage_start=date(2026, 1, 1),
        coverage_end=date(2026, 1, 6), rows=calendar_rows(),
        official_anchor_ids=("sse", "szse"),
    )
    with pytest.raises(UpstreamExtensionError, match="unavailable"):
        item.is_open(date(2026, 1, 7))


def test_effective_universe_adds_listing_and_removes_after_delisting():
    universe = EffectiveDatedUniverseV1.create(
        previous_approval_id="old-master", previous_universe_id="old-universe",
        baseline_symbols=("600000.SH", "600001.SH"),
        changes=(
            {"security_identity": "688999.SH", "listing_date": "20260105", "delisting_date": None},
            {"security_identity": "600001.SH", "listing_date": "19990101", "delisting_date": "20260106"},
        ), coverage_end=date(2026, 1, 7), evidence_ids=("official-master",),
    )
    assert "688999.SH" not in universe.approved_universe_as_of_session(date(2026, 1, 4))
    assert "688999.SH" in universe.approved_universe_as_of_session(date(2026, 1, 5))
    assert "600001.SH" in universe.approved_universe_as_of_session(date(2026, 1, 6))
    assert "600001.SH" not in universe.approved_universe_as_of_session(date(2026, 1, 7))


@pytest.mark.parametrize("change", [
    {"security_identity": "", "listing_date": "20260105", "delisting_date": None},
    {"security_identity": "688999.SH", "listing_date": None, "delisting_date": None},
    {"security_identity": "688999.SH", "listing_date": "20260105", "delisting_date": "20260104"},
])
def test_ambiguous_or_conflicting_identity_change_fails_closed(change):
    with pytest.raises(UpstreamExtensionError):
        EffectiveDatedUniverseV1.create(
            previous_approval_id="old", previous_universe_id="u",
            baseline_symbols=("600000.SH",), changes=(change,),
            coverage_end=date(2026, 1, 7), evidence_ids=("e",),
        )


def test_identity_transition_requires_explicit_linkage():
    with pytest.raises(UpstreamExtensionError, match="transition"):
        EffectiveDatedUniverseV1.create(
            previous_approval_id="old", previous_universe_id="u",
            baseline_symbols=("600000.SH",), changes=({
                "security_identity": "600999.SH", "listing_date": "20260105",
                "delisting_date": None, "prior_identity": "600000.SH",
            },), coverage_end=date(2026, 1, 7), evidence_ids=("e",),
        )
