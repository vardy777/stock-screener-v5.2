from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Mapping

from v5_2.data.identity import content_hash
from v5_2.refresh.contracts import DatasetReadiness, DatasetRefreshResultV1


BASE = ("trade_calendar", "security_master", "daily_bar", "daily_security_status")
ALL = (*BASE, "corporate_action", "financial_disclosure")


@dataclass(frozen=True, slots=True)
class RefreshReadinessArtifactV1:
    artifact_id: str
    target_session: date
    evaluated_at: datetime
    dataset_results: Mapping[str, DatasetRefreshResultV1]
    gates: Mapping[str, str]
    scoped_exclusions: Mapping[str, tuple[str, ...]]
    failure_reasons: tuple[str, ...]
    research_ready: bool
    content_hash: str

    @classmethod
    def evaluate(cls, target_session: date,
                 dataset_results: Mapping[str, DatasetRefreshResultV1],
                 evaluated_at: datetime) -> RefreshReadinessArtifactV1:
        if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
            raise ValueError("evaluated_at must be timezone-aware")
        results = dict(dataset_results)
        reasons: list[str] = []
        for kind in BASE:
            item = results.get(kind)
            if item is None or item.readiness is not DatasetReadiness.READY:
                reasons.append(kind.upper() + "_READY")
        dimensions = {
            "APPROVAL_VALIDITY": "approval_valid", "MANIFEST_VALIDITY": "manifest_valid",
            "TARGET_COVERAGE": "coverage_valid", "PIT": "pit_valid",
            "IDENTITY_CONSISTENCY": "identity_valid",
        }
        gates = {}
        for gate, field in dimensions.items():
            valid = all(kind in results and bool(getattr(results[kind], field)) for kind in BASE)
            gates[gate] = "PASS" if valid else "FAIL"
            if not valid:
                reasons.append(gate)
        cross_ready = not reasons
        gates["CROSS_DATASET_READINESS"] = "PASS" if cross_ready else "FAIL"
        scoped = {
            kind: tuple(results[kind].affected_security_ids)
            for kind in ("corporate_action", "financial_disclosure")
            if kind in results and results[kind].affected_security_ids
        }
        body = {
            "schema_version": "RefreshReadinessArtifactV1", "target_session": target_session,
            "evaluated_at": evaluated_at,
            "dataset_results": {key: value.as_dict() for key, value in sorted(results.items())},
            "gates": gates, "scoped_exclusions": scoped,
            "failure_reasons": tuple(sorted(set(reasons))), "research_ready": cross_ready,
        }
        digest = content_hash(body)
        return cls(digest, target_session, evaluated_at, results, gates, scoped,
                   body["failure_reasons"], cross_ready, digest)
