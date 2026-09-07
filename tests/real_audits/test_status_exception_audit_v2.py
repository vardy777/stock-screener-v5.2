from v5_2.data.real_audits.status_exceptions import StatusExceptionBudgetV2


def test_sparse_cross_market_exceptions_pass_prefrozen_budget() -> None:
    budget = StatusExceptionBudgetV2.default()
    records = tuple(
        {"security_identity": f"{index:06d}.{'SH' if index % 2 else 'SZ'}",
         "session": f"{2024 + (index % 24) // 12}-{index % 12 + 1:02d}-02",
         "exchange": "SH" if index % 2 else "SZ", "month": f"{2024 + (index % 24) // 12}-{index % 12 + 1:02d}", "board": "MAIN",
         "effective_interval_known": True}
        for index in range(89)
    )
    result = budget.evaluate_records(records, applicable_symbol_sessions=2_487_799)
    assert result.passed is True
    assert result.systematic_pattern is False


def test_consecutive_identity_cluster_over_limit_fails() -> None:
    budget = StatusExceptionBudgetV2.default()
    records = tuple(
        {"security_identity": "688766.SH", "session": f"202501{day:02d}", "exchange": "SH",
         "month": "2025-01", "board": "STAR", "effective_interval_known": True}
        for day in range(1, 12)
    )
    result = budget.evaluate_records(records, applicable_symbol_sessions=2_487_799)
    assert result.passed is False
    assert "per_security_consecutive_limit" in result.reasons


def test_unknown_interval_and_month_concentration_fail() -> None:
    budget = StatusExceptionBudgetV2.default()
    records = tuple(
        {"security_identity": f"600{index:03d}.SH", "session": f"202402{index % 28 + 1:02d}",
         "exchange": "SH", "month": "2024-02", "board": "SH_MAIN",
         "effective_interval_known": index != 0}
        for index in range(26)
    )
    result = budget.evaluate_records(records, applicable_symbol_sessions=2_487_799)
    assert result.passed is False
    assert "month_concentration_limit" in result.reasons
    assert "unknown_effective_interval_limit" in result.reasons
