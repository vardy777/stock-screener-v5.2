from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from v5_2.providers.contracts import ProviderRequestV1
from v5_2.providers.credentials import Credential


class ProviderContractError(RuntimeError):
    """A sanitized provider or adapter contract failure."""


@dataclass(frozen=True, slots=True)
class ProviderPageV1:
    request_id: str
    page_identity: Mapping[str, Any]
    response_code: int
    response_status: str
    rows: tuple[Mapping[str, Any], ...]


Transport = Callable[[str, str, dict[str, object]], dict[str, object]]


class TushareClient:
    def __init__(self, *, transport: Transport, endpoint_registry: Mapping[str, str]) -> None:
        self._transport = transport
        self._endpoint_registry = MappingProxyType(dict(endpoint_registry))

    def fetch_page(
        self,
        request: ProviderRequestV1,
        credential: Credential,
        *,
        page_identity: Mapping[str, int],
    ) -> ProviderPageV1:
        expected_endpoint = self._endpoint_registry.get(request.dataset_kind)
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
        except Exception:
            raise ProviderContractError("provider transport failed") from None
        if response.get("code") != 0:
            raise ProviderContractError("provider rejected request")
        rows = response.get("rows")
        if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
            raise ProviderContractError("provider returned invalid rows")
        return ProviderPageV1(
            request_id=request.request_id,
            page_identity=MappingProxyType(dict(page_identity)),
            response_code=0,
            response_status="ok",
            rows=tuple(MappingProxyType(dict(row)) for row in rows),
        )
