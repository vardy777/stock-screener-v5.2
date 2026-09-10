from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from v5_2.data.identity import content_hash


DIVIDEND_REQUIRED_FIELDS = {"ts_code", "ann_date", "div_proc", "ex_date"}


@dataclass(frozen=True, slots=True)
class CorporateActionEndpointProbeV1:
    probe_id: str
    endpoint: str
    requested_scope: str
    fields: tuple[str, ...]
    row_count: int
    has_more: bool
    disposition: str
    capabilities: tuple[str, ...]
    detail: str
    observed_at: str
    content_hash: str

    @classmethod
    def create(cls, **values) -> CorporateActionEndpointProbeV1:
        values["fields"] = tuple(values["fields"])
        values["capabilities"] = tuple(sorted(set(values["capabilities"])))
        body = {
            "schema_version": "CorporateActionEndpointProbeV1",
            **{key: value for key, value in values.items() if key != "observed_at"},
        }
        digest = content_hash(body)
        return cls(probe_id=digest, content_hash=digest, **values)

    @property
    def usable(self) -> bool:
        return self.disposition == "SUPPORTED"

    def verify(self) -> bool:
        body = {
            "schema_version": "CorporateActionEndpointProbeV1",
            "endpoint": self.endpoint,
            "requested_scope": self.requested_scope,
            "fields": self.fields,
            "row_count": self.row_count,
            "has_more": self.has_more,
            "disposition": self.disposition,
            "capabilities": self.capabilities,
            "detail": self.detail,
        }
        return self.probe_id == self.content_hash == content_hash(body)


def evaluate_probe_response(
    *, endpoint: str, response: Mapping[str, object], requested_scope: str,
    observed_at: str = "observation-time-not-part-of-semantic-identity",
) -> CorporateActionEndpointProbeV1:
    data = response.get("data")
    if response.get("code") != 0 or not isinstance(data, Mapping):
        return CorporateActionEndpointProbeV1.create(
            endpoint=endpoint, requested_scope=requested_scope, fields=(), row_count=0,
            has_more=False, disposition="UNSUPPORTED", capabilities=(),
            detail="provider rejected candidate endpoint", observed_at=observed_at,
        )
    fields_value, items = data.get("fields"), data.get("items")
    fields = tuple(fields_value) if isinstance(fields_value, Sequence) and not isinstance(fields_value, str) else ()
    rows = items if isinstance(items, Sequence) and not isinstance(items, (str, bytes)) else ()
    has_more = data.get("has_more") is True
    if endpoint == "adj_factor":
        disposition, capabilities, detail = "AUDIT_ONLY", (), "adjustment factor is non-authoritative audit evidence"
    elif endpoint == "dividend" and DIVIDEND_REQUIRED_FIELDS <= set(fields):
        disposition, capabilities, detail = "SUPPORTED", ("CASH_DIVIDEND", "BONUS_SHARE"), "verified dividend schema"
    else:
        disposition, capabilities, detail = "UNSUPPORTED", (), "candidate schema is not semantically sufficient"
    return CorporateActionEndpointProbeV1.create(
        endpoint=endpoint, requested_scope=requested_scope, fields=fields,
        row_count=len(rows), has_more=has_more, disposition=disposition,
        capabilities=capabilities, detail=detail, observed_at=observed_at,
    )
