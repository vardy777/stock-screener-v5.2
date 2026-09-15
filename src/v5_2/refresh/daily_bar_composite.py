from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Mapping, Sequence

from v5_2.data.identity import content_hash


class CompositeLineageError(RuntimeError):
    """Phase 1C Daily Bar composition is incomplete or inconsistent."""


_ROLE_RULES = {
    "HISTORICAL_BASELINE": ("HISTORICAL_RECONSTRUCTED", "NEXT_SESSION_SAFE"),
    "HISTORICAL_CATCH_UP": ("HISTORICAL_RECONSTRUCTED", "NEXT_SESSION_SAFE"),
    "CONTEMPORANEOUS_OBSERVED": ("CONTEMPORANEOUS_OBSERVED", "CONTEMPORANEOUS_OBSERVED"),
}


def _verify(value: Mapping[str, object], identifier: str) -> bool:
    inferred = {"dataset_id": "DatasetManifestV1", "approval_id": "SourceApprovalArtifactV1",
                "evidence_id": ("HistoricalExitDailyBarAvailabilityEvidenceV2" if "cutoff" in value
                                else "Phase1CDailyBarAvailabilityEvidenceV1"),
                "binding_id": "DailyBarSourceBindingV1"}
    schema = value.get("schema_version", inferred[identifier])
    body = {key: item for key, item in value.items() if key not in {identifier, "content_hash", "manifest_hash"}}
    digest = content_hash({"schema_version": schema, **{key: item for key, item in body.items() if key != "schema_version"}})
    expected = value.get(identifier)
    return expected == digest and value.get("content_hash", expected) == expected and value.get("manifest_hash", expected) == expected


@dataclass(frozen=True, slots=True)
class Phase1CDailyBarComponentV1:
    role: str
    provenance_mode: str
    availability_mode: str
    manifest_id: str
    approval_id: str
    availability_evidence_id: str
    binding_id: str
    source_semantic_identity: str
    source_content_set_identity: str
    coverage_start: str
    coverage_end: str
    row_count: int
    member_artifact_ids: tuple[str, ...]
    membership_digest: str
    component_hash: str

    def __post_init__(self) -> None:
        if self.role not in _ROLE_RULES:
            raise CompositeLineageError("unknown component role")
        if (self.provenance_mode, self.availability_mode) != _ROLE_RULES[self.role]:
            raise CompositeLineageError("component provenance or availability mode mismatch")

    @classmethod
    def create(
        cls, *, role: str, provenance_mode: str, availability_mode: str,
        manifest: Mapping[str, object], approval: Mapping[str, object],
        availability: Mapping[str, object], binding: Mapping[str, object],
        revoked_artifact_ids: Sequence[str],
    ) -> Phase1CDailyBarComponentV1:
        if not _verify(manifest, "dataset_id") or not _verify(approval, "approval_id"):
            raise CompositeLineageError("manifest or approval integrity invalid")
        if not _verify(availability, "evidence_id") or not _verify(binding, "binding_id"):
            raise CompositeLineageError("availability or binding integrity invalid")
        approval_id = str(approval["approval_id"])
        if approval_id in set(revoked_artifact_ids):
            raise CompositeLineageError("component approval is revoked")
        if approval.get("decision") not in {"APPROVED", "APPROVED_WITH_RULES"}:
            raise CompositeLineageError("component is not independently approved")
        availability_id = str(availability["evidence_id"])
        binding_id = str(binding["binding_id"])
        semantic = str(binding["source_semantic_identity"])
        content = str(binding["source_content_set_identity"])
        recorded_mode = availability.get("availability_mode")
        effective_mode_matches = recorded_mode == availability_mode or (
            availability_mode == "NEXT_SESSION_SAFE"
            and recorded_mode == "HISTORICAL_RECONSTRUCTED"
            and str(availability.get("cutoff", "")).startswith("NEXT_SESSION_SAFE@")
        )
        rules = approval.get("rule_set", {})
        approval_pins_availability = availability_id in tuple(approval.get("evidence_ids", ())) or (
            isinstance(rules, Mapping) and rules.get("availability_evidence_id") == availability_id)
        if not (
            manifest.get("dataset_kind") == approval.get("dataset_kind") == "daily_bar"
            and manifest.get("approval_id") == approval_id
            and manifest.get("availability_evidence_id") == availability_id
            and approval.get("source_version_identity") == content
            and availability.get("binding_id", availability.get("source_binding_id")) == binding_id
            and availability.get("source_semantic_identity") == semantic
            and availability.get("source_content_set_identity") == content
            and effective_mode_matches
            and manifest.get("source_content_set_identity", content) == content
            and approval_pins_availability
        ):
            raise CompositeLineageError("component manifest approval availability chain mismatch")
        members = tuple(str(item) for item in manifest.get("fact_content_hashes", ()))
        row_count = int(manifest.get("row_count", -1))
        if not members or row_count < 1:
            raise CompositeLineageError("component membership is empty")
        body = {
            "schema_version": "Phase1CDailyBarComponentV1", "role": role,
            "provenance_mode": provenance_mode, "availability_mode": availability_mode,
            "manifest_id": str(manifest["dataset_id"]), "approval_id": approval_id,
            "availability_evidence_id": availability_id, "binding_id": binding_id,
            "source_semantic_identity": semantic, "source_content_set_identity": content,
            "coverage_start": str(manifest["coverage_start"]), "coverage_end": str(manifest["coverage_end"]),
            "row_count": row_count, "member_artifact_ids": members,
            "membership_digest": content_hash(members),
        }
        return cls(component_hash=content_hash(body), **{key: value for key, value in body.items() if key != "schema_version"})

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Phase1CDailyBarCompositeManifestV1:
    historical_baseline: Phase1CDailyBarComponentV1
    historical_catch_up: Phase1CDailyBarComponentV1
    contemporaneous_observed: Phase1CDailyBarComponentV1
    aggregate_row_count: int
    aggregate_membership_digest: str
    unclassified_count: int
    duplicate_membership_count: int
    composite_manifest_id: str
    content_hash: str

    @classmethod
    def create(
        cls, *, historical_baseline: Phase1CDailyBarComponentV1,
        historical_catch_up: Phase1CDailyBarComponentV1,
        contemporaneous_observed: Phase1CDailyBarComponentV1,
    ) -> Phase1CDailyBarCompositeManifestV1:
        components = (historical_baseline, historical_catch_up, contemporaneous_observed)
        expected = tuple(_ROLE_RULES)
        if tuple(item.role for item in components) != expected:
            raise CompositeLineageError("composite requires exactly three typed roles")
        memberships = [set(item.member_artifact_ids) for item in components]
        duplicates = sum(len(memberships[left] & memberships[right]) for left, right in ((0, 1), (0, 2), (1, 2)))
        if duplicates:
            raise CompositeLineageError("component membership is not pairwise disjoint")
        row_count = sum(item.row_count for item in components)
        membership_digest = content_hash(tuple((item.role, item.membership_digest, item.row_count) for item in components))
        body = {
            "schema_version": "Phase1CDailyBarCompositeManifestV1",
            "contract_version": "phase-1c-daily-bar-composite-v1",
            "dataset_kind": "daily_bar",
            "historical_baseline": historical_baseline.as_dict(),
            "historical_catch_up": historical_catch_up.as_dict(),
            "contemporaneous_observed": contemporaneous_observed.as_dict(),
            "aggregate_row_count": row_count,
            "aggregate_membership_digest": membership_digest,
            "unclassified_count": 0,
            "duplicate_membership_count": duplicates,
        }
        digest = content_hash(body)
        return cls(historical_baseline, historical_catch_up, contemporaneous_observed,
                   row_count, membership_digest, 0, duplicates, digest, digest)

    @property
    def component_roles(self) -> tuple[str, str, str]:
        return tuple(item.role for item in (
            self.historical_baseline, self.historical_catch_up,
            self.contemporaneous_observed))  # type: ignore[return-value]

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": "Phase1CDailyBarCompositeManifestV1",
            "contract_version": "phase-1c-daily-bar-composite-v1",
            "dataset_kind": "daily_bar",
            "historical_baseline": self.historical_baseline.as_dict(),
            "historical_catch_up": self.historical_catch_up.as_dict(),
            "contemporaneous_observed": self.contemporaneous_observed.as_dict(),
            "aggregate_row_count": self.aggregate_row_count,
            "aggregate_membership_digest": self.aggregate_membership_digest,
            "unclassified_count": self.unclassified_count,
            "duplicate_membership_count": self.duplicate_membership_count,
            "composite_manifest_id": self.composite_manifest_id,
            "content_hash": self.content_hash,
        }


def resolve_phase1c_daily_bar_composite(remediation_root: Path) -> str:
    pointer = remediation_root / "daily_bar-current-composite-id.txt"
    if not pointer.is_file():
        raise CompositeLineageError("current composite pointer is missing")
    identifier = pointer.read_text(encoding="ascii").strip()
    path = remediation_root / "governance" / f"phase1c-daily-bar-composite-{identifier}.json"
    if not path.is_file():
        raise CompositeLineageError("current composite artifact is missing")
    value = json.loads(path.read_text(encoding="utf-8"))
    body = {key: item for key, item in value.items() if key not in {"composite_manifest_id", "content_hash"}}
    if (value.get("schema_version") != "Phase1CDailyBarCompositeManifestV1"
            or "approval_id" in value
            or value.get("composite_manifest_id") != identifier
            or value.get("content_hash") != identifier
            or content_hash(body) != identifier):
        raise CompositeLineageError("current composite artifact integrity invalid")
    for field in ("historical_baseline", "historical_catch_up", "contemporaneous_observed"):
        embedded = value[field]
        component_hash = embedded["component_hash"]
        matches = tuple((remediation_root / "governance").glob(f"*-component-{component_hash}.json"))
        if len(matches) != 1:
            raise CompositeLineageError("typed component artifact is missing or ambiguous")
        component = json.loads(matches[0].read_text(encoding="utf-8"))
        component_body = {key: item for key, item in component.items()
                          if key not in {"schema_version", "component_hash"}}
        if (component.get("schema_version") != "Phase1CDailyBarComponentV1"
                or content_hash({"schema_version": "Phase1CDailyBarComponentV1", **component_body}) != component_hash
                or component_body != {key: item for key, item in embedded.items() if key != "component_hash"}):
            raise CompositeLineageError("typed component artifact integrity invalid")
    return identifier
