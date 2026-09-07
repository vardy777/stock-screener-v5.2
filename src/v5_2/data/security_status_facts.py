from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from v5_2.data.identity import content_hash


class StatusFactError(ValueError):
    """A status fact cannot be represented without ambiguity."""


class StatusKind(StrEnum):
    LISTING = "LISTING"
    RISK_WARNING = "RISK_WARNING"
    SUSPENSION = "SUSPENSION"
    IDENTITY = "IDENTITY"


@dataclass(frozen=True, slots=True)
class SecurityStatusIntervalFactV1:
    fact_id: str
    security_identity: str
    status_kind: StatusKind
    status_value: str
    effective_from: date
    effective_to: date | None
    published_at: datetime | None
    available_at: datetime
    availability_basis: str
    source_fact_id: str
    source_name: str
    policy_version: str
    supersedes_fact_id: str | None
    content_hash: str

    @classmethod
    def create(cls, *, supersedes_fact_id: str | None = None, **values):
        values["status_kind"] = StatusKind(values["status_kind"])
        if values["effective_to"] is not None and values["effective_to"] < values["effective_from"]:
            raise StatusFactError("status interval is reversed")
        for field in ("available_at", "published_at"):
            value = values[field]
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise StatusFactError(f"{field} must include timezone")
        for field in ("security_identity", "status_value", "availability_basis", "source_fact_id", "source_name", "policy_version"):
            if not str(values[field]).strip():
                raise StatusFactError(f"{field} must not be empty")
        body = {"schema_version": "SecurityStatusIntervalFactV1", **values,
                "supersedes_fact_id": supersedes_fact_id}
        digest = content_hash(body)
        return cls(fact_id=digest, content_hash=digest, supersedes_fact_id=supersedes_fact_id, **values)

    def verify(self) -> bool:
        fields = ("security_identity", "status_kind", "status_value", "effective_from", "effective_to",
                  "published_at", "available_at", "availability_basis", "source_fact_id", "source_name",
                  "policy_version", "supersedes_fact_id")
        body = {"schema_version": "SecurityStatusIntervalFactV1",
                **{field: getattr(self, field) for field in fields}}
        return self.fact_id == self.content_hash == content_hash(body)


@dataclass(frozen=True, slots=True)
class DailySecurityStatusFactV1:
    fact_id: str
    security_identity: str
    session: date
    is_listed: bool
    is_delisted: bool
    is_risk_warning: bool
    is_suspended: bool
    is_eligible: bool
    is_tradable: bool
    effective_from: date
    effective_to: date | None
    available_at: datetime
    source_fact_ids: tuple[str, ...]
    source_name: str
    policy_version: str
    content_hash: str

    @classmethod
    def create(cls, *, risk_warning_excluded: bool, **values):
        available_at = values["available_at"]
        if available_at.tzinfo is None or available_at.utcoffset() is None:
            raise StatusFactError("available_at must include timezone")
        sources = tuple(sorted(set(values["source_fact_ids"])))
        if not sources:
            raise StatusFactError("daily status requires source facts")
        is_eligible = values["is_listed"] and not values["is_delisted"]
        is_tradable = is_eligible and not values["is_suspended"] and not (
            risk_warning_excluded and values["is_risk_warning"]
        )
        values["source_fact_ids"] = sources
        body = {"schema_version": "DailySecurityStatusFactV1", **values,
                "is_eligible": is_eligible, "is_tradable": is_tradable}
        digest = content_hash(body)
        return cls(fact_id=digest, content_hash=digest, is_eligible=is_eligible,
                   is_tradable=is_tradable, **values)

    def verify(self) -> bool:
        fields = ("security_identity", "session", "is_listed", "is_delisted", "is_risk_warning",
                  "is_suspended", "is_eligible", "is_tradable", "effective_from", "effective_to",
                  "available_at", "source_fact_ids", "source_name", "policy_version")
        body = {"schema_version": "DailySecurityStatusFactV1",
                **{field: getattr(self, field) for field in fields}}
        return self.fact_id == self.content_hash == content_hash(body)
