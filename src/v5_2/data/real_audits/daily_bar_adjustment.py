from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from v5_2.data.identity import content_hash


@dataclass(frozen=True, slots=True)
class UnadjustedRawEvidenceV1:
    evidence_id: str
    sample_count: int
    tolerance: Decimal
    maximum_difference: Decimal
    passed: bool
    evidence_ids: tuple[str, ...]
    content_hash: str


def audit_unadjusted_raw(samples, *, tolerance, evidence_ids):
    differences = tuple(abs(provider - reference) for provider, reference in samples)
    maximum = max(differences, default=Decimal("Infinity"))
    values = {"sample_count": len(differences), "tolerance": tolerance, "maximum_difference": maximum,
              "passed": bool(differences) and maximum <= tolerance, "evidence_ids": tuple(sorted(set(evidence_ids)))}
    identity = {**values, "tolerance": str(tolerance), "maximum_difference": str(maximum)}
    digest = content_hash({"schema_version": "UnadjustedRawEvidenceV1", **identity})
    return UnadjustedRawEvidenceV1(evidence_id=digest, content_hash=digest, **values)
