from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any

from v5_2.data.identity import canonical_json, content_hash


class DatasetEquivalenceDecision(str, Enum):
    EQUIVALENT = "EQUIVALENT"
    EQUIVALENT_WITH_RULES = "EQUIVALENT_WITH_RULES"
    NOT_EQUIVALENT = "NOT_EQUIVALENT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(value[key]) for key in sorted(value)})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    canonical_json(value)
    return value


@dataclass(frozen=True, slots=True)
class DatasetEquivalenceEvidenceV1:
    evidence_id: str
    source_name: str
    dataset_kind: str
    reference_contract: str
    tested_endpoints: tuple[str, ...]
    tested_fields: tuple[str, ...]
    coverage_tested: Mapping[str, Any]
    sample_rule: Mapping[str, Any]
    field_mapping: Mapping[str, Any]
    semantic_findings: tuple[str, ...]
    missing_fields: tuple[str, ...]
    extra_fields: tuple[str, ...]
    value_comparison_summary: Mapping[str, Any]
    pit_findings: tuple[str, ...]
    revision_findings: tuple[str, ...]
    pagination_findings: tuple[str, ...]
    cross_source_findings: tuple[str, ...]
    limitations: tuple[str, ...]
    decision: DatasetEquivalenceDecision
    verified_at: datetime
    input_artifact_ids: tuple[str, ...]
    policy_version: str
    content_hash: str

    @classmethod
    def create(cls, **values: Any) -> DatasetEquivalenceEvidenceV1:
        if values.get("source_name") != "datahubco_tushare_proxy":
            raise ValueError("source identity must remain datahubco_tushare_proxy")
        if values["verified_at"].tzinfo is None or values["verified_at"].utcoffset() is None:
            raise ValueError("verified_at must be timezone-aware")
        required = ("dataset_kind", "reference_contract", "tested_endpoints", "tested_fields", "coverage_tested", "sample_rule", "field_mapping", "value_comparison_summary", "input_artifact_ids", "policy_version")
        if any(not values.get(name) for name in required):
            raise ValueError("required equivalence evidence section is empty")
        sequence_fields = (
            "tested_endpoints", "tested_fields", "semantic_findings", "missing_fields",
            "extra_fields", "pit_findings", "revision_findings", "pagination_findings",
            "cross_source_findings", "limitations", "input_artifact_ids",
        )
        canonical = dict(values)
        for name in sequence_fields:
            canonical[name] = tuple(sorted(set(values[name])))
        for name in ("coverage_tested", "sample_rule", "field_mapping", "value_comparison_summary"):
            canonical[name] = _freeze(values[name])
        body = {"schema_version": "DatasetEquivalenceEvidenceV1", **canonical}
        digest = content_hash(body)
        return cls(evidence_id=digest, content_hash=digest, **canonical)
