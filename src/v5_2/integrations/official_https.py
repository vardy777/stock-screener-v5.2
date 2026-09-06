from __future__ import annotations

from types import MappingProxyType
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from v5_2.data.identity import content_hash


@dataclass(frozen=True, slots=True)
class OfficialEvidenceTransportTrustV1:
    trust_id: str
    evidence_ids: tuple[str, ...]
    tls_certificate_verified: bool
    hostname_verified: bool
    evidence_trust: str
    assessed_at: datetime
    policy_version: str
    content_hash: str

    @classmethod
    def create(cls, *, evidence_ids, tls_certificate_verified, hostname_verified, assessed_at, policy_version):
        trust = "VALID_FOR_FINAL_APPROVAL" if tls_certificate_verified and hostname_verified else "INVALID_FOR_FINAL_APPROVAL"
        values = {"evidence_ids": tuple(sorted(set(evidence_ids))), "tls_certificate_verified": tls_certificate_verified,
                  "hostname_verified": hostname_verified, "evidence_trust": trust,
                  "assessed_at": assessed_at, "policy_version": policy_version}
        digest = content_hash({"schema_version": "OfficialEvidenceTransportTrustV1", **values})
        return cls(trust_id=digest, content_hash=digest, **values)

    def require_final_approval(self) -> None:
        if self.evidence_trust != "VALID_FOR_FINAL_APPROVAL":
            raise ValueError("insecure official evidence cannot support final approval")


class _HttpsOnlyRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).scheme.lower() != "https":
            raise RuntimeError("HTTPS downgrade redirect rejected")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class VerifiedHttpsTransportV1:
    """HTTPS-only transport using Python/system default CA and hostname checks."""

    def __init__(self, *, opener=None) -> None:
        self._opener = opener or build_opener(ProxyHandler({}), _HttpsOnlyRedirectHandler())
        self.trust_metadata = MappingProxyType({
            "tls_certificate_verified": True,
            "hostname_verified": True,
            "http_downgrade_forbidden": True,
        })

    def get(self, url: str, *, headers=None, timeout: float = 30) -> bytes:
        if urlparse(url).scheme.lower() != "https":
            raise ValueError("verified transport requires HTTPS")
        request = Request(url, headers=dict(headers or {}))
        with self._opener.open(request, timeout=timeout) as response:
            final_url = response.geturl()
            if urlparse(final_url).scheme.lower() != "https":
                raise RuntimeError("HTTPS downgrade redirect rejected")
            return response.read()
