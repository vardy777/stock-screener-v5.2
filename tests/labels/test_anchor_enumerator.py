from dataclasses import replace
from datetime import date

import pytest

from v5_2.labels.anchor_enumerator import (
    AnchorDispositionKind,
    HistoricalAnchorLineageV1,
    IdentityIntervalV1,
    StatusObservationV1,
    enumerate_historical_anchors,
)


IDS = tuple((format(index, "x") * 64)[:64] for index in range(1, 7))
SESSIONS = tuple(date(2024, 1, day) for day in (2, 3, 4, 5, 8, 9, 10, 11, 12))


def lineage(*, intervals=None, statuses=None, revoked=()):
    intervals = intervals or (IdentityIntervalV1("000001.SZ", "000001.SZ", "SZSE", SESSIONS[0], None),)
    statuses = statuses or tuple(StatusObservationV1("000001.SZ", day, False) for day in SESSIONS)
    return HistoricalAnchorLineageV1.create(
        calendar_approval_id=IDS[0], calendar_manifest_id=IDS[1],
        master_approval_id=IDS[2], master_manifest_id=IDS[3],
        status_approval_id=IDS[4], status_manifest_id=IDS[5],
        open_sessions=SESSIONS, identity_intervals=intervals,
        status_observations=statuses, revoked_approval_ids=revoked,
    )


def resolved(value):
    return tuple(enumerate_historical_anchors(value, SESSIONS[0], SESSIONS[-1]))


def test_listing_and_first_four_post_listing_sessions_are_effective_but_excluded():
    rows = resolved(lineage())
    assert all(item.effective for item in rows[:5])
    assert [item.disposition for item in rows[:5]] == [AnchorDispositionKind.EXCLUDED_BEFORE_LABEL] * 5
    assert all(item.reason == "IPO_SEASONING" for item in rows[:5])
    assert rows[5].disposition is AnchorDispositionKind.ELIGIBLE


def test_full_day_suspension_remains_effective_and_eligible_not_non_listed():
    statuses = tuple(StatusObservationV1("000001.SZ", day, day == SESSIONS[6]) for day in SESSIONS)
    item = resolved(lineage(statuses=statuses))[6]
    assert item.disposition is AnchorDispositionKind.ELIGIBLE
    assert item.full_day_suspended is True


def test_delisting_boundary_and_identity_transition_follow_pinned_intervals():
    intervals = (
        IdentityIntervalV1("000001.SZ", "000001.SZ", "SZSE", SESSIONS[0], SESSIONS[5]),
        IdentityIntervalV1("000001.SZ", "300001.SZ", "SZSE", SESSIONS[6], None),
    )
    rows = resolved(lineage(intervals=intervals))
    assert rows[5].canonical_security_identity == "000001.SZ"
    assert rows[6].canonical_security_identity == "300001.SZ"
    assert all(item.effective for item in rows)


def test_delisted_identity_has_no_anchor_after_its_pinned_effective_interval():
    rows = resolved(lineage(intervals=(
        IdentityIntervalV1("000001.SZ", "000001.SZ", "SZSE", SESSIONS[0], SESSIONS[5]),
    )))
    assert [item.anchor_session for item in rows] == list(SESSIONS[:6])


def test_overlapping_identity_intervals_fail_closed_instead_of_duplicate_candidates():
    value = lineage(intervals=(
        IdentityIntervalV1("000001.SZ", "000001.SZ", "SZSE", SESSIONS[0], None),
        IdentityIntervalV1("000001.SZ", "000001.SZ", "SZSE", SESSIONS[4], None),
    ))
    with pytest.raises(ValueError, match="lineage"):
        resolved(value)


@pytest.mark.parametrize("mutation", ("calendar", "master", "revoked"))
def test_tampered_or_revoked_pinned_lineage_fails_closed(mutation):
    value = lineage(revoked=(IDS[4],) if mutation == "revoked" else ())
    if mutation == "calendar":
        value = replace(value, open_sessions=tuple(reversed(value.open_sessions)))
    if mutation == "master":
        value = replace(value, master_manifest_id="f" * 64)
    with pytest.raises(ValueError, match="lineage"):
        resolved(value)


def test_same_pinned_inputs_have_same_ordered_dispositions_and_missing_status_fails_closed():
    first = resolved(lineage())
    second = resolved(lineage())
    assert first == second
    incomplete = lineage(statuses=tuple(StatusObservationV1("000001.SZ", day, False) for day in SESSIONS[:-1]))
    assert resolved(incomplete)[-1].reason == "STATUS_UNRESOLVED"
