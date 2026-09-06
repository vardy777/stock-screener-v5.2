from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any

from v5_2.data.identity import content_hash
from v5_2.data.real_audits.policy_adequacy import CrossSourceEvidencePolicyV2, EvidenceResolution


@dataclass(frozen=True, slots=True)
class IndependentSourceIdentityV1:
    source_id: str
    source_name: str
    provider_identity: str
    dataset_kind: str
    endpoint_identity: str
    source_independence_rationale: str
    coverage_capability: Mapping[str, Any]
    schema_identity: tuple[str, ...]
    retrieved_at: datetime
    policy_version: str
    content_hash: str

    @classmethod
    def create(cls, **values):
        identity = f"{values['source_name']} {values['provider_identity']} {values['endpoint_identity']}".lower()
        rationale = values["source_independence_rationale"].lower()
        if "datahub" in identity or "same upstream" in rationale:
            raise ValueError("Tier 3 independent source is not established")
        values["coverage_capability"] = MappingProxyType(dict(sorted(values["coverage_capability"].items())))
        values["schema_identity"] = tuple(values["schema_identity"])
        body = {"schema_version": "IndependentSourceIdentityV1", **values}
        digest = content_hash(body)
        return cls(source_id=digest, content_hash=digest, **values)


@dataclass(frozen=True, slots=True)
class IndependentCalendarSampleRequestV1:
    request_id: str
    sample_id: str
    exchange: str
    calendar_date: str
    sample_stratum: str
    datahub_observation: int
    independent_source_id: str

    @classmethod
    def from_frozen(cls, samples: Sequence[Any], source: IndependentSourceIdentityV1):
        result = []
        for item in samples:
            get = item.get if isinstance(item, Mapping) else lambda name: getattr(item, name)
            body = {
                "sample_id": get("sample_id"), "exchange": get("exchange"),
                "calendar_date": get("calendar_date"), "sample_stratum": get("sample_stratum"),
                "datahub_observation": get("provider_is_open"), "independent_source_id": source.source_id,
            }
            result.append(cls(request_id=content_hash({"schema_version": "IndependentCalendarSampleRequestV1", **body}), **body))
        return tuple(sorted(result, key=lambda value: value.sample_id))


@dataclass(frozen=True, slots=True)
class IndependentCalendarComparisonEvidenceV1:
    evidence_id: str
    records: tuple[Mapping[str, Any], ...]
    total: int
    match_count: int
    mismatch_count: int
    unresolved_count: int
    provider_error_count: int
    source_id: str
    content_hash: str


def compare_independent_calendar(requests: Sequence[IndependentCalendarSampleRequestV1], observations: Mapping[str, int], source: IndependentSourceIdentityV1, *, official_anchors: Mapping[str, int]):
    supported = set(source.coverage_capability.get("exchanges", ()))
    records = []
    counts = {status: 0 for status in EvidenceResolution}
    for request in requests:
        independent = observations.get(request.calendar_date) if request.exchange in supported else None
        if independent not in (0, 1):
            resolution = EvidenceResolution.UNRESOLVED_EVIDENCE
        elif independent == request.datahub_observation:
            resolution = EvidenceResolution.MATCH
        else:
            resolution = EvidenceResolution.MISMATCH
        counts[resolution] += 1
        records.append(MappingProxyType({
            "sample_id": request.sample_id, "exchange": request.exchange,
            "calendar_date": request.calendar_date, "datahub_value": request.datahub_observation,
            "independent_value": independent, "official_anchor_value": official_anchors.get(request.sample_id),
            "resolution": resolution,
        }))
    body = {"schema_version": "IndependentCalendarComparisonEvidenceV1", "records": tuple(records), "total": len(records), "match_count": counts[EvidenceResolution.MATCH], "mismatch_count": counts[EvidenceResolution.MISMATCH], "unresolved_count": counts[EvidenceResolution.UNRESOLVED_EVIDENCE], "provider_error_count": counts[EvidenceResolution.PROVIDER_ERROR], "source_id": source.source_id}
    digest = content_hash(body)
    return IndependentCalendarComparisonEvidenceV1(evidence_id=digest, content_hash=digest, **{k: v for k, v in body.items() if k != "schema_version"})


@dataclass(frozen=True, slots=True)
class CrossSourceEvidencePolicyAdoptionArtifactV1:
    adoption_id: str
    v1_policy_id: str
    v2_policy_id: str
    independent_source_identity: str
    sample_evidence_id: str
    official_anchor_evidence_ids: tuple[str, ...]
    adopted_at: datetime
    methodological_reason: str
    content_hash: str

    @classmethod
    def create(cls, *, v1_policy_id: str, v2_policy: CrossSourceEvidencePolicyV2, independent_source: IndependentSourceIdentityV1, sample_evidence_id: str, total: int, matches: int, mismatches: int, unresolved: int, provider_errors: int, official_anchor_evidence_ids: Sequence[str], adopted_at: datetime, methodological_reason: str):
        if total != 256 or matches != 256 or mismatches or unresolved or provider_errors:
            raise ValueError("V2 adoption requires complete matching evidence")
        if v2_policy.evaluate(official_anchor_count=len(official_anchor_evidence_ids), independent_sample_count=total, unexplained_mismatch_count=mismatches) != "EQUIVALENT_WITH_RULES":
            raise ValueError("V2 policy thresholds are not satisfied")
        body = {"schema_version": "CrossSourceEvidencePolicyAdoptionArtifactV1", "v1_policy_id": v1_policy_id, "v2_policy_id": v2_policy.policy_id, "independent_source_identity": independent_source.source_id, "sample_evidence_id": sample_evidence_id, "official_anchor_evidence_ids": tuple(sorted(set(official_anchor_evidence_ids))), "adopted_at": adopted_at, "methodological_reason": methodological_reason}
        digest = content_hash(body)
        return cls(adoption_id=digest, content_hash=digest, **{k: v for k, v in body.items() if k != "schema_version"})
