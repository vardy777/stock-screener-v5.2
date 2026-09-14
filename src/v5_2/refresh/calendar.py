from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Mapping, Sequence

from v5_2.data.identity import canonical_json, content_hash
from v5_2.data.raw_artifacts import RawPayloadArtifactV1
from v5_2.refresh.adapters import AvailabilityMode, DatasetStateV1
from v5_2.refresh.contracts import DatasetReadiness


class CalendarPublicationError(RuntimeError):
    """A calendar increment cannot safely extend approved coverage."""


def _valid_artifact(value: Mapping[str, object], identity: tuple[str, str], schema: str) -> bool:
    left, right = identity
    body = {key: item for key, item in value.items() if key not in identity}
    return value.get(left) == value.get(right) == content_hash({"schema_version": schema, **body})


def _write_immutable(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        if path.read_bytes() != encoded:
            raise CalendarPublicationError("immutable calendar artifact collision") from None
    else:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)


@dataclass(frozen=True, slots=True)
class CalendarPublicationV1:
    state: DatasetStateV1
    approval_id: str
    manifest_id: str
    fact_id: str
    validation_id: str


def publish_calendar_increment(
    *, output_root: Path, previous_approval: Mapping[str, object],
    previous_manifest: Mapping[str, object], raws: Sequence[RawPayloadArtifactV1],
    receipt_hashes: tuple[str, ...], missing_dates: tuple[date, ...],
    observed_at: datetime, prior_open_sessions: tuple[date, ...] = (),
    revoked_approval_ids: frozenset[str] = frozenset(),
) -> CalendarPublicationV1:
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CalendarPublicationError("calendar observation time must be timezone-aware")
    if not _valid_artifact(previous_approval, ("approval_id", "content_hash"), "SourceApprovalArtifactV1"):
        raise CalendarPublicationError("previous calendar approval integrity invalid")
    if not _valid_artifact(previous_manifest, ("dataset_id", "manifest_hash"), "DatasetManifestV1"):
        raise CalendarPublicationError("previous calendar manifest integrity invalid")
    if previous_approval["approval_id"] in revoked_approval_ids:
        raise CalendarPublicationError("previous calendar approval is revoked")
    if (previous_manifest.get("approval_id") != previous_approval.get("approval_id")
            or previous_manifest.get("dataset_kind") != "trade_calendar"):
        raise CalendarPublicationError("previous calendar lineage mismatch")
    if not raws or not receipt_hashes:
        raise CalendarPublicationError("calendar raw and receipt lineage are required")

    rows = [dict(row) for raw in raws for row in raw.provider_payload.get("rows", ())]
    expected_days = {day.strftime("%Y%m%d") for day in missing_dates}
    expected = {(exchange, day) for exchange in ("SSE", "SZSE") for day in expected_days}
    actual: dict[tuple[str, str], dict[str, object]] = {}
    for row in rows:
        key = (str(row.get("exchange")), str(row.get("cal_date")))
        if key in actual or row.get("is_open") not in (0, 1) or not row.get("pretrade_date"):
            raise CalendarPublicationError("calendar row structure invalid")
        actual[key] = row
    if set(actual) != expected:
        raise CalendarPublicationError("calendar coverage is incomplete or out of scope")
    for day in expected_days:
        if actual[("SSE", day)]["is_open"] != actual[("SZSE", day)]["is_open"]:
            raise CalendarPublicationError("exchange calendar semantics conflict")

    normalized = tuple(sorted(rows, key=lambda row: (str(row["cal_date"]), str(row["exchange"]))))
    fact_body = {"schema_version": "CalendarIncrementFactBundleV1", "rows": normalized}
    fact_id = content_hash(fact_body)
    validation_body = {
        "schema_version": "CalendarIncrementValidationV1", "fact_id": fact_id,
        "coverage_start": min(missing_dates), "coverage_end": max(missing_dates),
        "exchanges": ("SSE", "SZSE"), "row_count": len(normalized),
        "cross_exchange_consistency": "PASS", "decision": "PASS",
    }
    validation_id = content_hash(validation_body)
    payload_hashes = tuple(sorted(raw.payload_hash for raw in raws))
    evidence_ids = tuple(sorted((*previous_approval.get("evidence_ids", ()), validation_id)))
    approval_body = {
        "schema_version": "SourceApprovalArtifactV1",
        "source_name": previous_approval["source_name"], "dataset_kind": "trade_calendar",
        "decision": "APPROVED_WITH_RULES", "coverage_start": previous_approval["coverage_start"],
        "coverage_end": max(missing_dates), "verified_at": observed_at,
        "source_version_identity": content_hash((previous_approval["source_version_identity"], payload_hashes)),
        "policy_version": previous_approval["policy_version"],
        "rule_set": previous_approval["rule_set"], "evidence_ids": evidence_ids,
        "evidence_bundle_hash": content_hash(evidence_ids),
        "evaluator_version": "phase-1c-calendar-increment-evaluator-v1",
        "evidence_validity_policy_version": previous_approval["evidence_validity_policy_version"],
        "equivalence_evidence_id": previous_approval["equivalence_evidence_id"],
        "supersedes_approval_id": previous_approval["approval_id"],
    }
    approval_id = content_hash(approval_body)
    approval = {"approval_id": approval_id, "content_hash": approval_id,
                **{key: value for key, value in approval_body.items() if key != "schema_version"}}

    manifest_body = {key: value for key, value in previous_manifest.items()
                     if key not in {"dataset_id", "manifest_hash"}}
    manifest_body.update({
        "created_at": observed_at, "approval_id": approval_id,
        "approval_content_hash": approval_id, "approval_resolution_as_of": observed_at,
        "coverage_end": max(missing_dates),
        "row_count": int(previous_manifest["row_count"]) + len(normalized),
        "raw_payload_hashes": tuple((*previous_manifest["raw_payload_hashes"], *payload_hashes)),
        "normalized_content_hashes": tuple((*previous_manifest["normalized_content_hashes"], fact_id)),
        "fact_content_hashes": tuple((*previous_manifest["fact_content_hashes"], fact_id)),
        "receipt_hashes": tuple((*previous_manifest["receipt_hashes"], *receipt_hashes)),
        "upstream_approval_ids": tuple((*previous_manifest.get("upstream_approval_ids", ()),
                                         previous_approval["approval_id"])),
    })
    manifest_id = content_hash({"schema_version": "DatasetManifestV1", **manifest_body})
    manifest = {"dataset_id": manifest_id, "manifest_hash": manifest_id, **manifest_body}

    governance = output_root / "governance"
    _write_immutable(governance / f"calendar-increment-facts-{fact_id}.json",
                     {"fact_id": fact_id, **fact_body})
    _write_immutable(governance / f"calendar-increment-validation-{validation_id}.json",
                     {"validation_id": validation_id, **validation_body})
    _write_immutable(governance / f"trade_calendar-approval-{approval_id}.json", approval)
    _write_immutable(governance / f"trade_calendar-manifest-{manifest_id}.json", manifest)
    open_sessions = tuple(sorted(
        date(int(day[:4]), int(day[4:6]), int(day[6:]))
        for day in expected_days if actual[("SSE", day)]["is_open"] == 1
    ))
    state = DatasetStateV1(
        "trade_calendar", approval_id, manifest_id, max(missing_dates),
        tuple(sorted(set((*prior_open_sessions, *open_sessions)))), max(missing_dates).isoformat(),
        DatasetReadiness.READY,
        availability_modes=(AvailabilityMode.CONTEMPORANEOUS_OBSERVED.value,),
    )
    state_body = {
        "schema_version": "Phase1CDatasetStateV1", "dataset_kind": state.dataset_kind,
        "approval_id": state.approval_id, "manifest_id": state.manifest_id,
        "latest_approved_session": state.latest_approved_session,
        "completed_sessions": state.completed_sessions, "watermark": state.watermark,
        "readiness": state.readiness, "reason_codes": state.reason_codes,
        "affected_security_ids": state.affected_security_ids,
        "availability_modes": state.availability_modes,
    }
    state_id = content_hash(state_body)
    _write_immutable(governance / f"trade_calendar-state-{state_id}.json",
                     {"state_id": state_id, **state_body})
    pointer = output_root / "trade_calendar-current-state-id.txt"
    temporary = pointer.with_suffix(".tmp")
    temporary.write_text(state_id, encoding="ascii")
    os.replace(temporary, pointer)
    return CalendarPublicationV1(state, approval_id, manifest_id, fact_id, validation_id)
