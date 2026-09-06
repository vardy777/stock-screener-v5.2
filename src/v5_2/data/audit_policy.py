from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any

from v5_2.data.identity import canonical_json, content_hash


class AuditPolicyError(ValueError):
    """A real-source audit policy is incomplete or mutable."""


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(value[key]) for key in sorted(value)})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    canonical_json(value)
    return value


@dataclass(frozen=True, slots=True)
class RealSourceAuditPolicyV1:
    policy_id: str
    policy_version: str
    dataset_kind: str
    required_coverage: Mapping[str, Any]
    sample_selection_rule: Mapping[str, Any]
    missing_row_policy: Mapping[str, Any]
    duplicate_policy: Mapping[str, Any]
    cross_source_rule: Mapping[str, Any]
    pit_rule: Mapping[str, Any]
    revision_rule: Mapping[str, Any]
    approval_thresholds: Mapping[str, Any]
    created_at: datetime
    content_hash: str

    @classmethod
    def create(
        cls,
        *,
        policy_version: str,
        dataset_kind: str,
        required_coverage: Mapping[str, Any],
        sample_selection_rule: Mapping[str, Any],
        missing_row_policy: Mapping[str, Any],
        duplicate_policy: Mapping[str, Any],
        cross_source_rule: Mapping[str, Any],
        pit_rule: Mapping[str, Any],
        revision_rule: Mapping[str, Any],
        approval_thresholds: Mapping[str, Any],
        created_at: datetime,
    ) -> RealSourceAuditPolicyV1:
        if not policy_version or not dataset_kind:
            raise AuditPolicyError("policy version and dataset kind are required")
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise AuditPolicyError("created_at must be timezone-aware")
        sections = {
            "required_coverage": _freeze(required_coverage),
            "sample_selection_rule": _freeze(sample_selection_rule),
            "missing_row_policy": _freeze(missing_row_policy),
            "duplicate_policy": _freeze(duplicate_policy),
            "cross_source_rule": _freeze(cross_source_rule),
            "pit_rule": _freeze(pit_rule),
            "revision_rule": _freeze(revision_rule),
            "approval_thresholds": _freeze(approval_thresholds),
        }
        if any(not section for section in sections.values()):
            raise AuditPolicyError("every audit policy section must be explicit")
        body = {
            "schema_version": "RealSourceAuditPolicyV1",
            "policy_version": policy_version,
            "dataset_kind": dataset_kind,
            **sections,
            "created_at": created_at,
        }
        digest = content_hash(body)
        return cls(
            policy_id=digest,
            content_hash=digest,
            policy_version=policy_version,
            dataset_kind=dataset_kind,
            created_at=created_at,
            **sections,
        )
