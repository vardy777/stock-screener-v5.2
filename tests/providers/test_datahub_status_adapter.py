from v5_2.providers.contracts import ProviderRequestV1
from v5_2.providers.credentials import load_datahub_credential
from v5_2.providers.datahub import DATAHUB_ENDPOINTS, DataHubClient


def test_status_endpoints_are_independently_allowlisted_and_normalized() -> None:
    assert DATAHUB_ENDPOINTS["risk_warning_history"] == "namechange"
    assert DATAHUB_ENDPOINTS["suspension_history"] == "suspend-d"
    request = ProviderRequestV1.create(
        source_name="datahubco_tushare_proxy", dataset_kind="suspension_history",
        endpoint="suspend-d", parameters={"start_date": "20250101", "end_date": "20251231"},
        requested_fields=("ts_code", "trade_date", "suspend_type"), page_size=100,
        request_policy_version="phase-1b2a-status-v1",
    )
    client = DataHubClient(transport=lambda *_: {
        "code": 0, "data": {"fields": ["ts_code", "trade_date", "suspend_type"],
                            "items": [["000001.SZ", "20250102", "S"]],
                            "has_more": False, "count": 1},
    })
    page = client.fetch_page(request, load_datahub_credential(env={"DATAHUB_API_KEY": "sentinel"}), page_identity={"offset": 0})
    assert page.rows == ({"ts_code": "000001.SZ", "trade_date": "20250102", "suspend_type": "S"},)

