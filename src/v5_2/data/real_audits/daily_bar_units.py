from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from v5_2.data.identity import content_hash


@dataclass(frozen=True, slots=True)
class DailyBarUnitEvidenceV1:
    evidence_id: str
    field: str
    sample_count: int
    conversion_factor: Decimal | None
    factors: tuple[Decimal, ...]
    passed: bool
    policy_version: str
    content_hash: str


def audit_unit(field, samples, *, policy_version):
    factors = []
    for provider, reference in samples:
        if provider <= 0:
            continue
        factors.append(reference / provider)
    unique = tuple(sorted(set(factors)))
    passed = bool(factors) and len(unique) == 1 and unique[0] > 0
    values = {"field": field, "sample_count": len(factors), "conversion_factor": unique[0] if passed else None,
              "factors": unique, "passed": passed, "policy_version": policy_version}
    identity = {**values, "conversion_factor": None if values["conversion_factor"] is None else str(values["conversion_factor"]),
                "factors": tuple(str(value) for value in values["factors"])}
    digest = content_hash({"schema_version": "DailyBarUnitEvidenceV1", **identity})
    return DailyBarUnitEvidenceV1(evidence_id=digest, content_hash=digest, **values)


@dataclass(frozen=True, slots=True)
class DailyBarUnitPolicyV1:
    policy_id: str
    volume_factor: Decimal
    amount_factor: Decimal
    evidence_ids: tuple[str, ...]
    policy_version: str
    content_hash: str

    @classmethod
    def create(cls, *, volume_factor, amount_factor, evidence_ids):
        values = {"volume_factor": Decimal(volume_factor), "amount_factor": Decimal(amount_factor),
                  "evidence_ids": tuple(sorted(set(evidence_ids))), "policy_version": "daily-bar-unit-policy-v1"}
        if values["volume_factor"] <= 0 or values["amount_factor"] <= 0 or not values["evidence_ids"]:
            raise ValueError("verified positive unit factors and evidence are required")
        identity = {**values, "volume_factor": str(values["volume_factor"]), "amount_factor": str(values["amount_factor"])}
        digest = content_hash({"schema_version": "DailyBarUnitPolicyV1", **identity})
        return cls(policy_id=digest, content_hash=digest, **values)
