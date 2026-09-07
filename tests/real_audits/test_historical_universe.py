from v5_2.data.real_audits.historical_universe import reconcile_historical_universe


def test_reconciliation_classifies_target_non_target_outside_and_alias() -> None:
    result = reconcile_historical_universe(
        observed_symbols=("600747.SH", "832317.BJ", "600001.SH", "302132.SZ"),
        original_symbols=("300114.SZ",),
        master_rows={
            "600747.SH": {"exchange": "SSE", "symbol": "600747", "market": "主板", "list_status": "D", "list_date": "19960916", "delist_date": "20191212", "ts_code": "600747.SH"},
            "832317.BJ": {"exchange": "BSE", "symbol": "832317", "market": "北交所", "list_status": "D", "list_date": "20200727", "delist_date": "20220426", "ts_code": "832317.BJ"},
            "600001.SH": {"exchange": "SSE", "symbol": "600001", "market": "主板", "list_status": "D", "list_date": "19900101", "delist_date": "20090101", "ts_code": "600001.SH"},
            "302132.SZ": {"exchange": "SZSE", "symbol": "302132", "market": "主板", "list_status": "L", "list_date": "20250217", "delist_date": None, "ts_code": "302132.SZ"},
        },
        aliases={"302132.SZ": "300114.SZ"}, coverage_start="20100104", coverage_end="20251231",
        original_universe_id="u", official_evidence={"600747.SH": ("sse-600747",)},
    )
    assert dict(result.counts) == {"IDENTITY_ALIAS": 1, "NON_TARGET": 1,
                                   "OUTSIDE_RESEARCH_COVERAGE": 1, "TARGET_A_SHARE_REQUIRED": 1}
    assert result.supplement.identities[0].security_identity == "600747.SH"
    assert result.supplement.original_universe_id == "u"
    assert result.supplement.content_hash
