from v5_2.data.historical_remediation import (
    build_daily_bar_segment_inventory,
    build_next_session_availability_map,
    canonicalize_rows,
    classify_daily_bar_identity,
)


def test_daily_bar_segment_inventory_is_deterministic_and_session_based():
    first = build_daily_bar_segment_inventory(sessions=("20260105", "20260106"),
        upstream_approval_ids=("calendar", "master"))
    second = build_daily_bar_segment_inventory(sessions=("20260106", "20260105"),
        upstream_approval_ids=("calendar", "master"))
    assert first == second and first.verify()
    assert len(first.requests) == 2
    assert all(item.parameters["trade_date"].startswith("2026") for item in first.requests)
    assert all("ts_code" not in item.parameters for item in first.requests)


def test_daily_bar_segment_inventory_rejects_duplicate_or_non_2026_session():
    import pytest
    with pytest.raises(ValueError, match="unique"):
        build_daily_bar_segment_inventory(sessions=("20260105", "20260105"),
            upstream_approval_ids=("calendar", "master"))
    with pytest.raises(ValueError, match="2026"):
        build_daily_bar_segment_inventory(sessions=("20251231",),
            upstream_approval_ids=("calendar", "master"))


def test_canonicalize_rows_orders_nullable_provider_values_by_content_identity():
    rows = ({"name": None, "code": "B"}, {"name": "ST X", "code": "A"})
    assert canonicalize_rows(rows) == canonicalize_rows(tuple(reversed(rows)))


def test_next_session_overlay_requires_a_later_approved_session():
    assert build_next_session_availability_map(
        research_sessions=("20260105",), approved_sessions=("20260105", "20260106")) == (
            ("20260105", "20260106", "2026-01-06T16:30:00+08:00"),)
    import pytest
    with pytest.raises(ValueError, match="next approved"):
        build_next_session_availability_map(
            research_sessions=("20260105",), approved_sessions=("20260105",))


def test_market_wide_daily_response_explicitly_excludes_non_target_bj_only():
    target = {"000001.SZ"}
    assert classify_daily_bar_identity("000001.SZ", target) == "TARGET"
    assert classify_daily_bar_identity("920000.BJ", target) == "EXCLUDED_NON_TARGET"
    assert classify_daily_bar_identity("999999.SH", target) == "UNRESOLVED_TARGET_IDENTITY"
