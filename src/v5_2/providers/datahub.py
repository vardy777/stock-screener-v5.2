from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from types import MappingProxyType
from typing import Any

from v5_2.providers.contracts import ProviderRequestV1
from v5_2.providers.credentials import Credential
from v5_2.providers.tushare import ProviderContractError, ProviderPageV1
from v5_2.providers.retry import TransientProviderError


DATAHUB_ENDPOINTS = MappingProxyType(
    {
        "trade_calendar": "trade-cal",
        "security_master": "stock-basic",
        "daily_bar": "daily",
        "corporate_action": "dividend",
        "risk_warning_history": "namechange",
        "suspension_history": "suspend-d",
        "risk_warning_daily": "stock-st",
        "risk_warning_events": "st",
        "financial_income": "income",
        "financial_balance_sheet": "balancesheet",
        "financial_cash_flow": "cashflow",
    }
)

Transport = Callable[[str, str, dict[str, object]], dict[str, object]]


class DataHubClient:
    """Credential-safe adapter for the DataHub Tushare-compatible API."""

    def __init__(self, *, transport: Transport) -> None:
        self._transport = transport

    def fetch_page(
        self,
        request: ProviderRequestV1,
        credential: Credential,
        *,
        page_identity: Mapping[str, int],
    ) -> ProviderPageV1:
        expected_endpoint = DATAHUB_ENDPOINTS.get(request.dataset_kind)
        if expected_endpoint is None or request.endpoint != expected_endpoint:
            raise ProviderContractError("endpoint is not allowlisted for dataset kind")
        offset = page_identity.get("offset")
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise ProviderContractError("page offset must be a non-negative integer")
        parameters = dict(request.parameters)
        parameters.update(limit=request.page_size, offset=offset)
        try:
            response = self._transport(
                request.endpoint, credential.reveal_for_transport(), parameters
            )
        except TransientProviderError:
            raise
        except Exception:
            raise ProviderContractError("provider transport failed") from None
        if credential.is_exposed_in(response):
            raise ProviderContractError("provider response failed credential safety check")
        if response.get("code") != 0:
            raise ProviderContractError("provider rejected request")
        data = response.get("data")
        if not isinstance(data, Mapping):
            raise ProviderContractError("provider returned invalid data")
        fields = data.get("fields")
        items = data.get("items")
        has_more = data.get("has_more")
        total_count = data.get("count")
        if (
            not isinstance(fields, list)
            or not fields
            or not all(isinstance(field, str) and field for field in fields)
            or len(set(fields)) != len(fields)
            or not isinstance(items, list)
            or not isinstance(has_more, bool)
            or isinstance(total_count, bool)
            or not isinstance(total_count, int)
            or total_count < 0
        ):
            raise ProviderContractError("provider returned invalid page metadata")
        rows: list[Mapping[str, Any]] = []
        for item in items:
            if (
                not isinstance(item, Sequence)
                or isinstance(item, (str, bytes, bytearray))
                or len(item) != len(fields)
            ):
                raise ProviderContractError("provider returned invalid row width")
            rows.append(MappingProxyType(dict(zip(fields, item, strict=True))))
        return ProviderPageV1(
            request_id=request.request_id,
            page_identity=MappingProxyType(dict(page_identity)),
            response_code=0,
            response_status="ok",
            rows=tuple(rows),
            has_more=has_more,
            total_count=total_count,
        )
