from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from v5_2.data.identity import content_hash


class CorporateActionFactError(ValueError):
    """A corporate-action fact is incomplete or internally inconsistent."""


class ActionType(StrEnum):
    CASH_DIVIDEND = "CASH_DIVIDEND"
    BONUS_SHARE = "BONUS_SHARE"
    RIGHTS_ISSUE = "RIGHTS_ISSUE"
    STOCK_SPLIT = "STOCK_SPLIT"
    SHARE_CONVERSION = "SHARE_CONVERSION"


class KnowledgeClass(StrEnum):
    KNOWN_IN_ADVANCE = "KNOWN_IN_ADVANCE"
    ECONOMIC_EFFECT_ONLY = "ECONOMIC_EFFECT_ONLY"
    RETROSPECTIVE_ONLY = "RETROSPECTIVE_ONLY"


@dataclass(frozen=True, slots=True)
class CorporateActionFactV1:
    fact_id: str
    security_identity: str
    action_type: ActionType
    knowledge_class: KnowledgeClass
    published_at: datetime | None
    available_at: datetime
    ex_date: date | None
    effective_date: date | None
    cash_per_share: Decimal | None
    share_ratio: Decimal | None
    source_fact_id: str
    source_version_identity: str
    revision_marker: str
    supersedes_source_fact_id: str | None
    is_cancelled: bool
    content_hash: str

    @classmethod
    def create(cls, **values) -> CorporateActionFactV1:
        values["action_type"] = ActionType(values["action_type"])
        values["knowledge_class"] = KnowledgeClass(values["knowledge_class"])
        for field in ("available_at", "published_at"):
            value = values[field]
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise CorporateActionFactError(f"{field} must include timezone")
        if values["ex_date"] is None and values["effective_date"] is None:
            raise CorporateActionFactError("an economic date is required")
        for field in ("cash_per_share", "share_ratio"):
            value = values[field]
            if value is not None and value < 0:
                raise CorporateActionFactError("economic values must be non-negative")
        if values["action_type"] is ActionType.CASH_DIVIDEND and values["cash_per_share"] is None:
            raise CorporateActionFactError("cash_per_share is required for cash dividend")
        if values["action_type"] in {
            ActionType.BONUS_SHARE,
            ActionType.STOCK_SPLIT,
            ActionType.SHARE_CONVERSION,
        } and values["share_ratio"] is None:
            raise CorporateActionFactError("share_ratio is required for share action")
        for field in (
            "security_identity",
            "source_fact_id",
            "source_version_identity",
            "revision_marker",
        ):
            if not str(values[field]).strip():
                raise CorporateActionFactError(f"{field} must not be empty")
        body = cls._identity_body(values)
        digest = content_hash(body)
        return cls(fact_id=digest, content_hash=digest, **values)

    @staticmethod
    def _identity_body(values) -> dict[str, object]:
        canonical = dict(values)
        for field in ("cash_per_share", "share_ratio"):
            value = canonical[field]
            canonical[field] = format(value, "f") if value is not None else None
        return {"schema_version": "CorporateActionFactV1", **canonical}

    def verify(self) -> bool:
        fields = (
            "security_identity", "action_type", "knowledge_class", "published_at",
            "available_at", "ex_date", "effective_date", "cash_per_share",
            "share_ratio", "source_fact_id", "source_version_identity",
            "revision_marker", "supersedes_source_fact_id", "is_cancelled",
        )
        body = self._identity_body({field: getattr(self, field) for field in fields})
        return self.fact_id == self.content_hash == content_hash(body)
