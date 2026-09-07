from __future__ import annotations

import pytest

from v5_2.providers.contracts import HistoricalProviderClient, ProviderRequestV1
from v5_2.providers.credentials import load_datahub_credential
from v5_2.providers.datahub import DATAHUB_ENDPOINTS, DataHubClient
from v5_2.providers.tushare import ProviderContractError
from v5_2.providers.retry import TransientProviderError


def request(dataset_kind: str = "daily_bar", endpoint: str = "daily") -> ProviderRequestV1:
    return ProviderRequestV1.create(
        source_name="datahubco_tushare_proxy",
        dataset_kind=dataset_kind,
        endpoint=endpoint,
        parameters={"trade_date": "20250102"},
        requested_fields=("ts_code", "trade_date", "close"),
        page_size=2,
        request_policy_version="datahub-request-v1",
    )


def credential():
    return load_datahub_credential(env={"DATAHUB_API_KEY": "sentinel"})


def test_datahub_endpoint_registry_is_dataset_scoped() -> None:
    assert DATAHUB_ENDPOINTS == {
        "trade_calendar": "trade-cal",
        "security_master": "stock-basic",
        "daily_bar": "daily",
        "risk_warning_history": "namechange",
        "suspension_history": "suspend-d",
    }


def test_fields_and_items_are_deterministically_mapped_to_rows() -> None:
    observed: dict[str, object] = {}

    def transport(endpoint: str, api_key: str, parameters: dict[str, object]):
        observed.update(endpoint=endpoint, api_key=api_key, parameters=parameters)
        return {
            "code": 0,
            "data": {
                "fields": ["ts_code", "trade_date", "close"],
                "items": [["000001.SZ", "20250102", 10.5]],
                "has_more": False,
                "count": 1,
            },
        }

    page = DataHubClient(transport=transport).fetch_page(
        request(), credential(), page_identity={"offset": 0}
    )

    assert observed == {
        "endpoint": "daily",
        "api_key": "sentinel",
        "parameters": {"trade_date": "20250102", "limit": 2, "offset": 0},
    }
    assert page.rows == ({"ts_code": "000001.SZ", "trade_date": "20250102", "close": 10.5},)
    assert page.has_more is False
    assert page.total_count == 1
    assert "sentinel" not in repr(page)
    assert isinstance(DataHubClient(transport=transport), HistoricalProviderClient)


@pytest.mark.parametrize(
    ("dataset_kind", "endpoint"),
    [("daily_bar", "stock-basic"), ("corporate_action", "daily")],
)
def test_non_allowlisted_dataset_endpoint_pair_fails_before_transport(
    dataset_kind: str, endpoint: str
) -> None:
    client = DataHubClient(transport=lambda *_: pytest.fail("must not run"))
    with pytest.raises(ProviderContractError, match="allowlisted"):
        client.fetch_page(request(dataset_kind, endpoint), credential(), page_identity={"offset": 0})


@pytest.mark.parametrize(
    "response",
    [
        {"code": 0, "data": {"fields": ["a", "b"], "items": [[1]], "has_more": False, "count": 1}},
        {"code": 0, "data": {"fields": ["a"], "items": "bad", "has_more": False, "count": 1}},
        {"code": 0, "data": {"fields": ["a"], "items": [[1]], "has_more": "no", "count": 1}},
        {"code": 0, "data": {"fields": ["a"], "items": [[1]], "has_more": False, "count": -1}},
    ],
)
def test_malformed_provider_shape_fails_closed(response: dict[str, object]) -> None:
    client = DataHubClient(transport=lambda *_: response)
    with pytest.raises(ProviderContractError, match="invalid"):
        client.fetch_page(request(), credential(), page_identity={"offset": 0})


def test_provider_error_and_credential_echo_are_sanitized() -> None:
    for response in (
        {"code": 1, "msg": "denied sentinel"},
        {"code": 0, "data": {"fields": ["a"], "items": [["sentinel"]], "has_more": False, "count": 1}},
    ):
        client = DataHubClient(transport=lambda *_, response=response: response)
        with pytest.raises(ProviderContractError) as caught:
            client.fetch_page(request(), credential(), page_identity={"offset": 0})
        assert "sentinel" not in str(caught.value)


def test_sanitized_transient_transport_failure_remains_retryable() -> None:
    def transport(*_):
        raise TransientProviderError("temporary")

    with pytest.raises(TransientProviderError, match="temporary"):
        DataHubClient(transport=transport).fetch_page(
            request(), credential(), page_identity={"offset": 0}
        )
