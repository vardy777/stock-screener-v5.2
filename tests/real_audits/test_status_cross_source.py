import pytest

from v5_2.data.real_audits.status_cross_source import resolve_cross_source


@pytest.mark.parametrize("semantic", ("ACTUAL_FIRST_TRADABLE_SESSION", "DELISTING_BOUNDARY"))
def test_listing_and_delisting_require_both_daily_and_official_evidence(semantic) -> None:
    assert resolve_cross_source(semantic, daily_matches=True, official_anchor_matches=False) == "INDEPENDENT_EVIDENCE_UNAVAILABLE"
    assert resolve_cross_source(semantic, daily_matches=True, official_anchor_matches=True) == "MATCH"


def test_observable_daily_semantic_does_not_require_official_anchor() -> None:
    assert resolve_cross_source("ST_EXIT", daily_matches=True, official_anchor_matches=False) == "MATCH"
    assert resolve_cross_source("ST_EXIT", daily_matches=False, official_anchor_matches=False) == "MISMATCH"
