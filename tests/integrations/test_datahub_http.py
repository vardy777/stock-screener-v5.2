from __future__ import annotations

import json
from urllib.error import HTTPError

import pytest

from v5_2.integrations.datahub_http import DataHubHttpTransport, TransportError


class Response:
    status = 200

    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


def test_transport_builds_allowlisted_request_without_key_in_url() -> None:
    observed = {}

    def opener(req, *, timeout):
        observed.update(url=req.full_url, headers=dict(req.header_items()), timeout=timeout)
        return Response({"code": 0, "data": {}})

    transport = DataHubHttpTransport(opener=opener, timeout_seconds=15)
    result = transport("daily", "sentinel", {"limit": 3, "ts_code": "000001.SZ"})

    assert result == {"code": 0, "data": {}}
    assert observed["url"].startswith(
        "http://datahubco.com/app-api/openapi/v1/tushare/daily?"
    )
    assert "limit=3" in observed["url"]
    assert "ts_code=000001.SZ" in observed["url"]
    assert "sentinel" not in observed["url"]
    assert observed["headers"]["X-api-key"] == "sentinel"
    assert observed["timeout"] == 15
    assert "sentinel" not in repr(transport)


@pytest.mark.parametrize("endpoint", ["../admin", "https://evil.invalid", "unknown"])
def test_transport_rejects_non_phase_1b1_endpoint(endpoint: str) -> None:
    transport = DataHubHttpTransport(opener=lambda *_args, **_kwargs: pytest.fail("must not run"))
    with pytest.raises(TransportError, match="allowlisted"):
        transport(endpoint, "sentinel", {})


def test_http_and_decode_failures_are_sanitized() -> None:
    def failed(*_args, **_kwargs):
        raise HTTPError("http://example.invalid?key=sentinel", 401, "sentinel", {}, None)

    with pytest.raises(TransportError) as caught:
        DataHubHttpTransport(opener=failed)("daily", "sentinel", {})
    assert "sentinel" not in str(caught.value)

    with pytest.raises(TransportError, match="invalid JSON"):
        DataHubHttpTransport(opener=lambda *_args, **_kwargs: ResponsePayload(b"bad"))(
            "daily", "sentinel", {}
        )


class ResponsePayload(Response):
    def __init__(self, payload: bytes) -> None:
        self._bytes = payload

    def read(self) -> bytes:
        return self._bytes
