from __future__ import annotations

import ast
from pathlib import Path
import ssl
from urllib.error import URLError

import pytest

from datetime import datetime, timezone

from v5_2.integrations.official_https import OfficialEvidenceTransportTrustV1, VerifiedHttpsTransportV1


class _Response:
    def __init__(self, url: str, payload: bytes = b"ok") -> None:
        self._url = url
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def geturl(self) -> str:
        return self._url

    def read(self) -> bytes:
        return self._payload


class _Opener:
    def __init__(self, outcome) -> None:
        self.outcome = outcome

    def open(self, request, timeout):
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def test_verified_https_accepts_only_https_with_verified_final_url() -> None:
    transport = VerifiedHttpsTransportV1(opener=_Opener(_Response("https://www.szse.cn/api")))
    assert transport.get("https://www.szse.cn/api") == b"ok"
    assert transport.trust_metadata == {
        "tls_certificate_verified": True,
        "hostname_verified": True,
        "http_downgrade_forbidden": True,
    }
    with pytest.raises(ValueError, match="HTTPS"):
        transport.get("http://www.szse.cn/api")


def test_certificate_and_hostname_failures_propagate_fail_closed() -> None:
    failure = URLError(ssl.SSLCertVerificationError("hostname mismatch"))
    transport = VerifiedHttpsTransportV1(opener=_Opener(failure))
    with pytest.raises(URLError):
        transport.get("https://www.szse.cn/api")


def test_https_to_http_redirect_is_rejected() -> None:
    transport = VerifiedHttpsTransportV1(opener=_Opener(_Response("http://www.szse.cn/api")))
    with pytest.raises(RuntimeError, match="downgrade"):
        transport.get("https://www.szse.cn/api")


def test_official_acquisition_code_contains_no_tls_bypass() -> None:
    root = Path(__file__).resolve().parents[2]
    targets = (
        root / "src/v5_2/integrations/official_https.py",
        root / "scripts/acquire_szse_calendar_audit.py",
        root / "scripts/resolve_security_master_official_sample.py",
    )
    forbidden = ("CERT_NONE", "check_hostname", "_create_unverified_context", "verify=False")
    for path in targets:
        source = path.read_text(encoding="utf-8")
        ast.parse(source)
        assert not any(token in source for token in forbidden), path


def test_insecure_evidence_cannot_support_final_approval() -> None:
    old = OfficialEvidenceTransportTrustV1.create(
        evidence_ids=("old-source", "old-composite", "old-approval"),
        tls_certificate_verified=False, hostname_verified=False,
        assessed_at=datetime(2026, 9, 6, tzinfo=timezone.utc), policy_version="official-evidence-trust-v1",
    )
    assert old.evidence_trust == "INVALID_FOR_FINAL_APPROVAL"
    with pytest.raises(ValueError, match="insecure"):
        old.require_final_approval()
