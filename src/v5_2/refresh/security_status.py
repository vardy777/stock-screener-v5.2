from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Mapping, Sequence

from v5_2.data.identity import canonical_json, content_hash
from v5_2.data.raw_artifacts import RawPayloadArtifactV1
from v5_2.refresh.adapters import AvailabilityMode, DatasetStateV1, SHANGHAI
from v5_2.refresh.contracts import DatasetReadiness


class SecurityStatusPublicationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SecurityStatusCoverageV1:
    coverage_id: str
    expected_research_safe_securities: int
    resolved_status_securities: int
    security_scoped_exclusions: tuple[str, ...]
    exclusion_reason_counts: tuple[tuple[str, int], ...]
    coverage_ratio: float
    systematic_defect: bool
    content_hash: str


@dataclass(frozen=True, slots=True)
class SecurityStatusIncrementV1:
    fact_bundle_id: str
    session: date
    available_at: datetime
    facts: tuple[Mapping[str, object], ...]
    coverage: SecurityStatusCoverageV1
    content_hash: str


@dataclass(frozen=True, slots=True)
class SecurityStatusPublicationV1:
    state: DatasetStateV1
    increment: SecurityStatusIncrementV1
    approval_id: str
    manifest_id: str

    @property
    def coverage(self) -> SecurityStatusCoverageV1:
        return self.increment.coverage


def security_status_state_at(state: DatasetStateV1, now: datetime) -> DatasetStateV1:
    if state.reason_codes != ("AVAILABILITY_NOT_REACHED",) or not state.watermark.startswith("visibility:"):
        return state
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("clock must be aware")
    boundary = datetime.fromisoformat(state.watermark.split(":", 1)[1])
    if now.astimezone(SHANGHAI) < boundary.astimezone(SHANGHAI):
        return state
    from dataclasses import replace
    return replace(state, readiness=DatasetReadiness.READY, reason_codes=())


def _valid(value: Mapping[str, object], ids: tuple[str, str], schema: str) -> bool:
    body = {key: item for key, item in value.items() if key not in ids}
    return value.get(ids[0]) == value.get(ids[1]) == content_hash({"schema_version": schema, **body})


def _status_lineage_coverage_valid(previous_panel: Mapping[str, object],
                                   previous_manifest: Mapping[str, object]) -> bool:
    panel_end = previous_panel.get("coverage_end")
    manifest_end = previous_manifest.get("coverage_end")
    return isinstance(panel_end, str) and isinstance(manifest_end, str) and panel_end <= manifest_end


def _write(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        if path.read_bytes() != encoded:
            raise SecurityStatusPublicationError("immutable status artifact collision") from None
    else:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)


def _rows_by_endpoint(raws: Sequence[RawPayloadArtifactV1]):
    name_rows, suspension_rows = [], []
    for raw in raws:
        rows = tuple(dict(row) for row in raw.provider_payload.get("rows", ()))
        if all("trade_date" in row and "suspend_type" in row for row in rows) and rows:
            suspension_rows.extend(rows)
        elif all("start_date" in row and "name" in row for row in rows) and rows:
            name_rows.extend(rows)
        elif not rows:
            request_tag = raw.request_id[0]
            (name_rows if request_tag == "n" else suspension_rows).extend(rows)
        else:
            raise SecurityStatusPublicationError("unrecognized status endpoint payload")
    if len(raws) != 2:
        raise SecurityStatusPublicationError("both status endpoints are required")
    return name_rows, suspension_rows


def publish_security_status_increment(*, output_root: Path,
    previous_approval: Mapping[str, object], previous_manifest: Mapping[str, object],
    previous_panel: Mapping[str, object], prior_risk_warning_rows: Sequence[Mapping[str, object]],
    raws: Sequence[RawPayloadArtifactV1],
    receipt_hashes: tuple[str, ...], research_safe_symbols: tuple[str, ...],
    upstream_master_approval_id: str, upstream_master_manifest_id: str,
    target_session: date, next_approved_session: date, observed_at: datetime,
    prior_completed_sessions: tuple[date, ...] = ()) -> SecurityStatusPublicationV1:
    if not _valid(previous_approval, ("approval_id", "content_hash"), "SourceApprovalArtifactV1"):
        raise SecurityStatusPublicationError("approval integrity invalid")
    if not _valid(previous_manifest, ("dataset_id", "manifest_hash"), "DatasetManifestV1"):
        raise SecurityStatusPublicationError("manifest integrity invalid")
    if previous_manifest.get("approval_id") != previous_approval.get("approval_id"):
        raise SecurityStatusPublicationError("lineage mismatch")
    if previous_panel.get("panel_id") != previous_panel.get("content_hash") or previous_panel.get("panel_id") != previous_approval.get("rule_set", {}).get("panel_id"):
        raise SecurityStatusPublicationError("prior status panel integrity invalid")
    if not _status_lineage_coverage_valid(previous_panel, previous_manifest):
        raise SecurityStatusPublicationError("prior status coverage mismatch")
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise SecurityStatusPublicationError("observation time must be aware")
    if not raws or len(receipt_hashes) != len(raws):
        raise SecurityStatusPublicationError("raw and receipt lineage required")
    name_rows, suspension_rows = _rows_by_endpoint(raws)
    target_text = target_session.strftime("%Y%m%d")
    expected = tuple(sorted(set(research_safe_symbols)))
    expected_set = set(expected)
    suspended: set[str] = set()
    for row in suspension_rows:
        if str(row.get("trade_date")) != target_text:
            raise SecurityStatusPublicationError("status session drift")
        kind = str(row.get("suspend_type", "")).upper()
        if kind not in {"S", "R"}:
            raise SecurityStatusPublicationError("unknown suspension semantics")
        if kind == "S" and row.get("ts_code") in expected_set and not row.get("suspend_timing"):
            suspended.add(str(row["ts_code"]))
    risk_warning: set[str] = set()
    for row in (*prior_risk_warning_rows, *name_rows):
        required = {"ts_code", "name", "start_date", "end_date", "ann_date", "change_reason"}
        if set(row) < required:
            raise SecurityStatusPublicationError("status field missing")
        if str(row["ts_code"]) not in expected_set:
            continue
        if str(row["start_date"]) > target_text or (row.get("end_date") and str(row["end_date"]) < target_text):
            continue
        name = str(row["name"]).upper()
        if name.startswith(("ST", "SST", "S*ST", "*ST")):
            risk_warning.add(str(row["ts_code"]))
    contemporaneous = observed_at.astimezone(SHANGHAI).date() == target_session
    available_at = observed_at if contemporaneous else datetime.combine(next_approved_session, time(16, 30), SHANGHAI)
    availability_mode = (AvailabilityMode.CONTEMPORANEOUS_OBSERVED.value if contemporaneous
                         else AvailabilityMode.HISTORICAL_RECONSTRUCTED.value)
    source_ids = tuple(sorted((str(previous_panel["panel_id"]), *(raw.payload_hash for raw in raws))))
    facts = tuple({
        "security_identity": symbol, "session": target_session,
        "is_listed": True, "is_delisted": False,
        "is_risk_warning": symbol in risk_warning, "is_suspended": symbol in suspended,
        "is_eligible": True, "is_tradable": symbol not in risk_warning | suspended,
        "effective_from": target_session, "effective_to": target_session,
        "available_at": available_at, "availability_basis": availability_mode,
        "source_fact_ids": source_ids, "source_name": "v5.2-status-projection",
        "policy_version": "StatusAvailabilityPolicyV2",
    } for symbol in expected)
    coverage_body = {"schema_version": "SecurityStatusCoverageV1",
        "expected_research_safe_securities": len(expected), "resolved_status_securities": len(facts),
        "security_scoped_exclusions": (), "exclusion_reason_counts": (),
        "coverage_ratio": len(facts) / len(expected) if expected else 0.0, "systematic_defect": False}
    coverage_id = content_hash(coverage_body)
    coverage = SecurityStatusCoverageV1(coverage_id, content_hash=coverage_id,
        **{key: value for key, value in coverage_body.items() if key != "schema_version"})
    increment_body = {"schema_version": "SecurityStatusIncrementV1", "session": target_session,
        "available_at": available_at, "facts": facts, "coverage_id": coverage_id,
        "prior_panel_id": previous_panel["panel_id"], "upstream_master_approval_id": upstream_master_approval_id,
        "upstream_master_manifest_id": upstream_master_manifest_id}
    fact_bundle_id = content_hash(increment_body)
    increment = SecurityStatusIncrementV1(fact_bundle_id, target_session, available_at, facts, coverage, fact_bundle_id)
    payloads = tuple(sorted(raw.payload_hash for raw in raws))
    evidence = tuple(sorted((*previous_approval.get("evidence_ids", ()), coverage_id, fact_bundle_id)))
    approval_body = {"schema_version": "SourceApprovalArtifactV1", "source_name": previous_approval["source_name"],
        "dataset_kind": "daily_security_status", "decision": "APPROVED_WITH_RULES",
        "coverage_start": previous_approval["coverage_start"], "coverage_end": target_session,
        "verified_at": observed_at, "source_version_identity": content_hash((previous_approval["source_version_identity"], payloads)),
        "policy_version": previous_approval["policy_version"],
        "rule_set": {**previous_approval["rule_set"], "incremental_coverage_id": coverage_id,
            "upstream_master_manifest_id": upstream_master_manifest_id, "availability": "NEXT_SESSION_SAFE"},
        "evidence_ids": evidence, "evidence_bundle_hash": content_hash(evidence),
        "evaluator_version": "phase-1c-security-status-increment-v1",
        "evidence_validity_policy_version": previous_approval["evidence_validity_policy_version"],
        "equivalence_evidence_id": previous_approval["equivalence_evidence_id"],
        "supersedes_approval_id": previous_approval["approval_id"]}
    approval_id = content_hash(approval_body)
    approval = {"approval_id": approval_id, "content_hash": approval_id,
        **{key: value for key, value in approval_body.items() if key != "schema_version"}}
    manifest_body = {key: value for key, value in previous_manifest.items() if key not in {"dataset_id", "manifest_hash"}}
    manifest_body.update({"created_at": observed_at, "approval_id": approval_id, "approval_content_hash": approval_id,
        "approval_resolution_as_of": observed_at, "coverage_end": target_session, "latest_approved_session": target_session,
        "row_count": int(previous_manifest["row_count"]) + len(facts), "symbol_count": len(expected),
        "raw_payload_hashes": tuple((*previous_manifest["raw_payload_hashes"], *payloads)),
        "normalized_content_hashes": tuple((*previous_manifest["normalized_content_hashes"], fact_bundle_id, coverage_id)),
        "fact_content_hashes": tuple((*previous_manifest["fact_content_hashes"], fact_bundle_id)),
        "receipt_hashes": tuple((*previous_manifest["receipt_hashes"], *receipt_hashes)),
        "upstream_approval_ids": tuple((*previous_manifest.get("upstream_approval_ids", ()), upstream_master_approval_id)),
        "quality_findings": tuple((*previous_manifest["quality_findings"], "phase-1c target projected from approved baseline plus complete increment"))})
    manifest_id = content_hash({"schema_version": "DatasetManifestV1", **manifest_body})
    manifest = {"dataset_id": manifest_id, "manifest_hash": manifest_id, **manifest_body}
    gov = output_root / "governance"
    _write(gov / f"security-status-facts-{fact_bundle_id}.json", {"fact_bundle_id": fact_bundle_id, **increment_body})
    _write(gov / f"security-status-coverage-{coverage_id}.json", asdict(coverage))
    _write(gov / f"daily_security_status-approval-{approval_id}.json", approval)
    _write(gov / f"daily_security_status-manifest-{manifest_id}.json", manifest)
    readiness = DatasetReadiness.READY if observed_at.astimezone(SHANGHAI) >= available_at else DatasetReadiness.NOT_READY
    reasons = () if readiness is DatasetReadiness.READY else ("AVAILABILITY_NOT_REACHED",)
    state = DatasetStateV1("daily_security_status", approval_id, manifest_id, target_session,
        tuple(sorted(set((*prior_completed_sessions, target_session)))), f"visibility:{available_at.isoformat()}", readiness,
        reason_codes=reasons, affected_security_ids=coverage.security_scoped_exclusions,
        availability_modes=(availability_mode,))
    state_body = {"schema_version": "Phase1CDatasetStateV1", **asdict(state)}
    state_id = content_hash(state_body)
    _write(gov / f"daily_security_status-state-{state_id}.json", {"state_id": state_id, **state_body})
    pointer = output_root / "daily_security_status-current-state-id.txt"
    temporary = pointer.with_suffix(".tmp")
    temporary.write_text(state_id, encoding="ascii")
    os.replace(temporary, pointer)
    return SecurityStatusPublicationV1(state, increment, approval_id, manifest_id)
