from dataclasses import replace

from v5_2.data.real_audits.corporate_action_probe import (
    CorporateActionEndpointProbeV1,
    evaluate_probe_response,
)


def test_successful_dividend_schema_is_semantically_usable():
    probe = evaluate_probe_response(
        endpoint="dividend",
        response={
            "code": 0,
            "data": {
                "fields": ["ts_code", "ann_date", "div_proc", "cash_div_tax", "stk_div", "ex_date"],
                "items": [["600000.SH", "20240603", "实施", "0.3", "0", "20240610"]],
                "has_more": False,
                "count": 1,
            },
        },
        requested_scope="20240101..20241231",
    )
    assert probe.usable
    assert probe.capabilities == ("BONUS_SHARE", "CASH_DIVIDEND")
    assert probe.verify()


def test_adj_factor_is_audit_only_even_when_endpoint_works():
    probe = evaluate_probe_response(
        endpoint="adj_factor",
        response={"code": 0, "data": {"fields": ["ts_code", "trade_date", "adj_factor"], "items": [], "has_more": False, "count": 0}},
        requested_scope="20240101..20241231",
    )
    assert not probe.usable
    assert probe.disposition == "AUDIT_ONLY"


def test_failure_is_sanitized_and_not_allowlist_evidence():
    probe = evaluate_probe_response(
        endpoint="rights_issue",
        response={"code": 401, "message": "denied secret-value"},
        requested_scope="20240101..20241231",
    )
    assert not probe.usable
    assert probe.detail == "provider rejected candidate endpoint"
    assert "secret-value" not in repr(probe)


def test_probe_hash_excludes_observation_time_but_detects_tamper():
    first = CorporateActionEndpointProbeV1.create(
        endpoint="dividend", requested_scope="2024", fields=("ts_code", "ann_date"),
        row_count=1, has_more=False, disposition="SUPPORTED", capabilities=("CASH_DIVIDEND",),
        detail="verified schema", observed_at="2026-09-10T10:00:00+00:00",
    )
    second = CorporateActionEndpointProbeV1.create(
        endpoint="dividend", requested_scope="2024", fields=("ts_code", "ann_date"),
        row_count=1, has_more=False, disposition="SUPPORTED", capabilities=("CASH_DIVIDEND",),
        detail="verified schema", observed_at="2026-09-10T11:00:00+00:00",
    )
    assert first.probe_id == second.probe_id
    assert not replace(first, row_count=2).verify()

