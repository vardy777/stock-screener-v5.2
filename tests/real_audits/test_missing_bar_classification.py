from v5_2.data.real_audits.missing_bar_classification import classify_missing_bar_keys


def test_classification_is_total_exclusive_and_uses_frozen_precedence() -> None:
    missing = (("A", "20250102"), ("B", "20250102"), ("C", "20250102"))
    result = classify_missing_bar_keys(
        missing,
        full_day_suspensions={missing[0]}, partial_suspensions={missing[1]},
        resume_observations={missing[1]}, local_exception_keys=set(),
    )
    assert result.total == 3
    assert dict(result.counts) == {
        "DELISTED": 0, "IDENTITY_NOT_APPLICABLE": 0, "LOCAL_EXCEPTION": 0,
        "NOT_YET_LISTED": 0, "OTHER_LEGITIMATE": 0, "SUSPENDED": 1,
        "UNEXPLAINED": 2,
    }
    assert len({item.key for item in result.items}) == 3


def test_input_total_is_pinned_when_required() -> None:
    try:
        classify_missing_bar_keys((), full_day_suspensions=set(), partial_suspensions=set(),
                                  resume_observations=set(), local_exception_keys=set(), expected_total=6489)
    except ValueError as error:
        assert "6489" in str(error)
    else:
        raise AssertionError("expected pinned total failure")
