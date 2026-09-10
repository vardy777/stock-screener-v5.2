from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from v5_2.data.corporate_action_facts import ActionType
from v5_2.data.identity import content_hash


class CorporateActionEvidenceError(RuntimeError):
    """Scoped corporate-action evidence is incomplete or inconsistent."""


CoverageInterval = tuple[ActionType, date, date]


@dataclass(frozen=True, slots=True)
class CorporateActionPITEvidenceV1:
    evidence_id: str
    target_history_start: date
    baseline_validation_end: date
    rolling_coverage_end: date
    source_name: str
    source_version_identity: str
    supported_action_types: tuple[ActionType, ...]
    unsupported_action_types: tuple[ActionType, ...]
    validated_coverage_by_action_type: tuple[CoverageInterval, ...]
    materialized_coverage_by_action_type: tuple[CoverageInterval, ...]
    coverage_gaps: tuple[tuple[date, date, str], ...]
    unsupported_intervals: tuple[CoverageInterval, ...]
    cross_source_evidence_ids: tuple[str, ...]
    exception_ids: tuple[str, ...]
    quarantine_ids: tuple[str, ...]
    publication_rule: str
    economic_effect_rule: str
    revision_rule: str
    cancellation_rule: str
    complete: bool
    content_hash: str

    @classmethod
    def create(cls, **values) -> CorporateActionPITEvidenceV1:
        for field in ("supported_action_types", "unsupported_action_types"):
            values[field] = tuple(sorted({ActionType(value) for value in values[field]}))
        for field in ("validated_coverage_by_action_type", "materialized_coverage_by_action_type", "unsupported_intervals"):
            values[field] = tuple(sorted((ActionType(kind), start, end) for kind, start, end in values[field]))
            if any(end < start for _, start, end in values[field]):
                raise CorporateActionEvidenceError("coverage interval is reversed")
        for field in ("cross_source_evidence_ids", "exception_ids", "quarantine_ids"):
            values[field] = tuple(sorted(set(values[field])))
        values["coverage_gaps"] = tuple(sorted(values["coverage_gaps"]))
        if not (values["target_history_start"] <= values["baseline_validation_end"] < values["rolling_coverage_end"]):
            raise CorporateActionEvidenceError("coverage dates are inconsistent")
        supported, unsupported = set(values["supported_action_types"]), set(values["unsupported_action_types"])
        if not supported or supported & unsupported:
            raise CorporateActionEvidenceError("action type scopes are invalid")
        if values["complete"]:
            validated = {row[0] for row in values["validated_coverage_by_action_type"]}
            materialized = {row[0] for row in values["materialized_coverage_by_action_type"]}
            unsupported_visible = {row[0] for row in values["unsupported_intervals"]}
            if not values["cross_source_evidence_ids"] or not supported <= validated & materialized:
                raise CorporateActionEvidenceError("complete scoped evidence lacks validation")
            if not unsupported <= unsupported_visible:
                raise CorporateActionEvidenceError("unsupported scope is not machine visible")
        body = {"schema_version": "CorporateActionPITEvidenceV1", **values}
        digest = content_hash(body)
        return cls(evidence_id=digest, content_hash=digest, **values)

    def verify(self) -> bool:
        fields = tuple(field for field in self.__dataclass_fields__ if field not in {"evidence_id", "content_hash"})
        body = {"schema_version": "CorporateActionPITEvidenceV1", **{field: getattr(self, field) for field in fields}}
        return self.evidence_id == self.content_hash == content_hash(body)
