from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping

from v5_2.data.identity import content_hash


class DailyBarLineageError(RuntimeError):
    """Daily Bar governance artifacts do not form one compatible lineage."""


@dataclass(frozen=True, slots=True)
class DailyBarSourceBindingV1:
    source_name: str
    dataset_kind: str
    endpoint: str
    payload_hashes: tuple[str, ...]
    source_semantic_contract_version: str
    requested_fields: tuple[str, ...]
    normalizer_version: str
    identity_policy_version: str
    unit_policy_id: str
    availability_policy_version: str
    source_semantic_identity: str
    source_content_set_identity: str
    binding_id: str
    content_hash: str

    @classmethod
    def create(cls, **values) -> DailyBarSourceBindingV1:
        payloads = tuple(sorted(set(values.pop("payload_hashes"))))
        fields = tuple(sorted(set(values.pop("requested_fields"))))
        semantic_values = dict(values)
        if semantic_values["source_semantic_contract_version"] == "daily-bar-semantic-contract-v2":
            semantic_values.pop("availability_policy_version")
        semantic = {"schema_version": "DailyBarSourceSemanticIdentityV1", **semantic_values,
                    "requested_fields": fields}
        semantic_id = content_hash(semantic)
        content_set_id = content_hash(payloads)
        body = {"schema_version": "DailyBarSourceBindingV1", **values,
                "payload_hashes": payloads, "requested_fields": fields,
                "source_semantic_identity": semantic_id,
                "source_content_set_identity": content_set_id}
        digest = content_hash(body)
        body.pop("schema_version")
        return cls(**body, binding_id=digest, content_hash=digest)

    def verify(self) -> bool:
        rebuilt = type(self).create(**{name: getattr(self, name) for name in (
            "source_name", "dataset_kind", "endpoint", "payload_hashes",
            "source_semantic_contract_version", "requested_fields", "normalizer_version",
            "identity_policy_version", "unit_policy_id", "availability_policy_version",
        )})
        return rebuilt == self


@dataclass(frozen=True, slots=True)
class HistoricalExitDailyBarAvailabilityEvidenceV2:
    source_binding_id: str
    source_semantic_identity: str
    source_content_set_identity: str
    coverage_start: date
    coverage_end: date
    availability_mode: str
    cutoff: str
    approved_calendar_lineage_id: str
    parent_evidence_ids: tuple[str, ...]
    evidence_id: str
    content_hash: str

    @classmethod
    def create(cls, *, binding: DailyBarSourceBindingV1, **values):
        if not binding.verify():
            raise DailyBarLineageError("source binding integrity failed")
        parents = tuple(sorted(set(values.pop("parent_evidence_ids"))))
        body = {"schema_version": "HistoricalExitDailyBarAvailabilityEvidenceV2",
                "source_binding_id": binding.binding_id,
                "source_semantic_identity": binding.source_semantic_identity,
                "source_content_set_identity": binding.source_content_set_identity,
                **values, "parent_evidence_ids": parents}
        digest = content_hash(body)
        body.pop("schema_version")
        return cls(**body, evidence_id=digest, content_hash=digest)

    def verify(self, binding: DailyBarSourceBindingV1) -> bool:
        if not binding.verify():
            return False
        body = {"schema_version": type(self).__name__, **{name: getattr(self, name) for name in (
            "source_binding_id", "source_semantic_identity", "source_content_set_identity",
            "coverage_start", "coverage_end", "availability_mode", "cutoff",
            "approved_calendar_lineage_id", "parent_evidence_ids",
        )}}
        return (
            self.evidence_id == self.content_hash == content_hash(body)
            and self.source_binding_id == binding.binding_id
            and self.source_semantic_identity == binding.source_semantic_identity
            and self.source_content_set_identity == binding.source_content_set_identity
        )


def validate_daily_bar_lineage(*, binding: DailyBarSourceBindingV1,
                               availability: HistoricalExitDailyBarAvailabilityEvidenceV2,
                               approval: Mapping[str, object], manifest: Mapping[str, object],
                               revoked_approval_ids=()) -> None:
    if not availability.verify(binding):
        raise DailyBarLineageError("availability binding mismatch")
    if approval.get("approval_id") in set(revoked_approval_ids):
        raise DailyBarLineageError("approval is not current")
    if approval.get("source_version_identity") != binding.source_content_set_identity:
        raise DailyBarLineageError("approval content set mismatch")
    rules = approval.get("rule_set")
    if not isinstance(rules, Mapping) or (
        rules.get("source_semantic_identity") != binding.source_semantic_identity
        or rules.get("source_content_set_identity") != binding.source_content_set_identity
        or rules.get("availability_evidence_id") != availability.evidence_id
    ):
        raise DailyBarLineageError("approval source binding mismatch")
    if (manifest.get("approval_id") != approval.get("approval_id")
            or manifest.get("approval_content_hash") != approval.get("content_hash")):
        raise DailyBarLineageError("manifest approval mismatch")
    if manifest.get("availability_evidence_id") != availability.evidence_id:
        raise DailyBarLineageError("manifest availability mismatch")
    hashes = tuple(sorted(set(manifest.get("raw_payload_hashes", ()))))
    if content_hash(hashes) != binding.source_content_set_identity:
        raise DailyBarLineageError("manifest content set mismatch")
