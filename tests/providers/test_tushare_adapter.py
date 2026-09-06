from __future__ import annotations

import pytest

from v5_2.providers.contracts import ProviderRequestV1
from v5_2.providers.credentials import load_tushare_credential
from v5_2.providers.tushare import ProviderContractError, TushareClient


def request(endpoint: str = "daily") -> ProviderRequestV1:
    return ProviderRequestV1.create(
        source_name="tushare_pro",
        dataset_kind="daily_bar",
        endpoint=endpoint,
        parameters={"trade_date": "20200102"},
        requested_fields=("ts_code", "trade_date", "close"),
        page_size=100,
        request_policy_version="request-v1",
    )


def test_allowlisted_endpoint_uses_injected_transport_and_sanitizes_page() -> None:
    observed: dict[str, object] = {}

    def transport(endpoint: str, token: str, parameters: dict[str, object]) -> dict[str, object]:
        observed.update(endpoint=endpoint, token=token, parameters=parameters)
        return {"code": 0, "message": "ok", "rows": [{"ts_code": "000001.SZ"}]}

    client = TushareClient(transport=transport, endpoint_registry={"daily_bar": "daily"})
    credential = load_tushare_credential(env={"TUSHARE_TOKEN": "sentinel"})
    page = client.fetch_page(request(), credential, page_identity={"offset": 0})

    assert observed == {
        "endpoint": "daily",
        "token": "sentinel",
        "parameters": {"trade_date": "20200102", "limit": 100, "offset": 0},
    }
    assert page.request_id == request().request_id
    assert page.rows == ({"ts_code": "000001.SZ"},)
    assert "sentinel" not in repr(page)


def test_arbitrary_or_mismatched_endpoint_is_rejected_before_transport() -> None:
    client = TushareClient(
        transport=lambda *_: pytest.fail("transport must not run"),
        endpoint_registry={"daily_bar": "daily"},
    )
    credential = load_tushare_credential(env={"TUSHARE_TOKEN": "sentinel"})
    with pytest.raises(ProviderContractError, match="allowlisted"):
        client.fetch_page(request("moneyflow"), credential, page_identity={"offset": 0})


def test_provider_error_does_not_expose_credential() -> None:
    client = TushareClient(
        transport=lambda *_: {"code": -1, "message": "denied sentinel", "rows": []},
        endpoint_registry={"daily_bar": "daily"},
    )
    credential = load_tushare_credential(env={"TUSHARE_TOKEN": "sentinel"})
    with pytest.raises(ProviderContractError) as caught:
        client.fetch_page(request(), credential, page_identity={"offset": 0})
    assert "sentinel" not in str(caught.value)
