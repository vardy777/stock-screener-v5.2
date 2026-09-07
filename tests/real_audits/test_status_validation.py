from v5_2.data.real_audits.status_validation import validate_status_observations


def test_validation_separates_value_coverage_from_pit_sufficiency() -> None:
    result = validate_status_observations(
        namechange_rows=({"ts_code": "000001.SZ", "ann_date": "20240102", "start_date": "20240103"},),
        suspension_rows=({"ts_code": "000001.SZ", "trade_date": "20240103", "suspend_type": "S"},),
        universe_symbols=("000001.SZ",), coverage_start="20240101", coverage_end="20241231",
        later_delisted_symbols=(), official_sample_matches=(),
    )
    assert result.structural_status == "PASS"
    assert result.pit_status == "PENDING"
    assert result.decision == "INSUFFICIENT_EVIDENCE"


def test_survivorship_requires_later_delisted_observation() -> None:
    result = validate_status_observations(
        namechange_rows=(), suspension_rows=(), universe_symbols=("000001.SZ",),
        coverage_start="20240101", coverage_end="20241231",
        later_delisted_symbols=("000002.SZ",), official_sample_matches=(),
    )
    assert result.survivorship_status == "FAIL"


def test_systematic_cross_source_mismatch_fails_closed() -> None:
    matches = tuple(False for _ in range(10))
    result = validate_status_observations(
        namechange_rows=(), suspension_rows=(), universe_symbols=("000001.SZ",),
        coverage_start="20240101", coverage_end="20241231",
        later_delisted_symbols=(), official_sample_matches=matches,
    )
    assert result.cross_source_status == "FAIL"
    assert result.decision == "REJECTED"
