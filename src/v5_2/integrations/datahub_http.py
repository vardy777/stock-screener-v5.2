from __future__ import annotations

from collections.abc import Callable, Mapping
import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from v5_2.providers.datahub import DATAHUB_ENDPOINTS


BASE_URL = "http://datahubco.com/app-api/openapi/v1/tushare"


class TransportError(RuntimeError):
    """Sanitized external transport failure."""


class DataHubHttpTransport:
    """The single allowlisted DataHub HTTP boundary.

    The provider currently exposes this verified route over plaintext HTTP. That
    transport fact must be represented in audit evidence and approval rules.
    """

    def __init__(
        self,
        *,
        opener: Callable[..., Any] = urlopen,
        timeout_seconds: float = 30.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._opener = opener
        self._timeout_seconds = timeout_seconds

    def __repr__(self) -> str:
        return f"DataHubHttpTransport(timeout_seconds={self._timeout_seconds!r})"

    def __call__(
        self, endpoint: str, api_key: str, parameters: dict[str, object]
    ) -> dict[str, object]:
        if endpoint not in DATAHUB_ENDPOINTS.values():
            raise TransportError("endpoint is not allowlisted")
        query = urlencode(parameters, doseq=True)
        url = f"{BASE_URL}/{endpoint}"
        if query:
            url = f"{url}?{query}"
        request = Request(url, headers={"X-API-Key": api_key, "Accept": "application/json"})
        try:
            with self._opener(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read())
        except json.JSONDecodeError:
            raise TransportError("provider returned invalid JSON") from None
        except Exception:
            raise TransportError("provider HTTP request failed") from None
        if not isinstance(payload, Mapping):
            raise TransportError("provider returned invalid JSON object")
        return dict(payload)
