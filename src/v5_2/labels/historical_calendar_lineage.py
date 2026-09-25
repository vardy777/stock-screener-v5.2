"""Strictly ordered Phase 1 trade calendar for historical label anchors."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path

from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.contracts import DomainLineageV1


APPROVAL_ID = "4a900c7e4f2b171d7adac07088025ca4bb9fb0da13cfa1b15e91eff3dafea601"
MANIFEST_ID = "5f5ba7d0594f5f1e2d40ad43b54a93a303a7d25af8e1104e6c633463076e6486"
BUNDLE_ID = "d64a2ef0823e9a55a33d3b8111337fb71fcb43ce778235694ebfadfed1396dcc"
EXTENSION_ID = "3cd7c2f6fbdfcff34d739033d3ac789a7661903c1b32c4c626e24ebe0a1f047a"


def _load(path: Path, *, schema: str, id_field: str, identity: str,
          stored_schema: bool, second_id_field: str | None = None,
          legacy_crlf: bool = False) -> dict:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, ValueError) as error:
        raise ValueError(f"calendar {schema} missing or malformed") from error
    canonical = canonical_json(value)
    allowed_bytes = (canonical + b"\r\n", canonical + b"\n") if legacy_crlf else (canonical,)
    if not isinstance(value, dict) or raw not in allowed_bytes:
        raise ValueError(f"calendar {schema} bytes changed")
    body = {key: item for key, item in value.items()
            if key not in {id_field, "content_hash", second_id_field}}
    if stored_schema:
        if body.get("schema_version") != schema:
            raise ValueError(f"calendar {schema} type mismatch")
    else:
        if "schema_version" in body:
            raise ValueError(f"calendar {schema} stored type mismatch")
        body = {"schema_version": schema, **body}
    if (value.get(id_field) != identity
            or value.get("content_hash", identity) != identity
            or (second_id_field and value.get(second_id_field) != identity)
            or content_hash(body) != identity):
        raise ValueError(f"calendar {schema} content mismatch")
    return value


@dataclass(frozen=True, slots=True)
class HistoricalCalendarLineageV1:
    approval_id: str
    manifest_id: str
    bundle_id: str
    extension_id: str
    sse_sessions: tuple[date, ...]
    szse_sessions: tuple[date, ...]

    @staticmethod
    def extension_path() -> Path:
        return Path("data/phase_1b1_2026_extension/governance") / f"calendar-extension-{EXTENSION_ID}.json"

    @staticmethod
    def required_paths() -> tuple[Path, ...]:
        return (
            Path("data/phase_1b_exit_remediation/governance") / f"historical-calendar-fact-bundle-{BUNDLE_ID}.json",
            HistoricalCalendarLineageV1.extension_path(),
            Path("data/phase_1b_exit_remediation/governance") / f"trade-calendar-complete-manifest-{MANIFEST_ID}.json",
            Path("data/phase_1b1_2026_extension/governance") / f"trade_calendar-approval-{APPROVAL_ID}.json",
        )

    @classmethod
    def load_exact(cls, root: Path, *, revoked_approval_ids: tuple[str, ...] = ()) -> "HistoricalCalendarLineageV1":
        paths = tuple(root / item for item in cls.required_paths())
        bundle = _load(paths[0], schema="HistoricalCalendarFactBundleV1",
                       id_field="fact_bundle_id", identity=BUNDLE_ID, stored_schema=True,
                       legacy_crlf=True)
        extension = _load(paths[1], schema="IncrementalCalendarExtensionV1", id_field="extension_id",
                          identity=EXTENSION_ID, stored_schema=False)
        manifest = _load(paths[2], schema="DatasetManifestV1", id_field="dataset_id",
                         identity=MANIFEST_ID, stored_schema=False,
                         second_id_field="manifest_hash", legacy_crlf=True)
        approval = _load(paths[3], schema="SourceApprovalArtifactV1", id_field="approval_id",
                         identity=APPROVAL_ID, stored_schema=False)
        if (APPROVAL_ID in revoked_approval_ids
                or approval.get("decision") not in {"APPROVED", "APPROVED_WITH_RULES"}
                or approval.get("dataset_kind") != "trade_calendar"
                or manifest.get("approval_id") != APPROVAL_ID
                or manifest.get("dataset_kind") != "trade_calendar"
                or manifest.get("pit_validation_status") != "PASS"
                or manifest.get("rule_compliance_status") != "PASS"
                or tuple(manifest.get("fact_content_hashes", ())) != (BUNDLE_ID, EXTENSION_ID)
                or manifest.get("row_count") != len(bundle["ordered_rows"]) + len(extension["ordered_rows"])):
            raise ValueError("calendar approval or manifest chain mismatch")
        sessions: dict[str, list[date]] = {"SSE": [], "SZSE": []}
        for item in bundle["ordered_rows"]:
            if item["exchange"] not in sessions or item["is_open"] not in (0, 1):
                raise ValueError("calendar base row invalid")
            if item["is_open"]:
                sessions[item["exchange"]].append(date.fromisoformat(item["cal_date"]))
        for exchange, compact, is_open in extension["ordered_rows"]:
            if exchange not in sessions or is_open not in (0, 1):
                raise ValueError("calendar extension row invalid")
            if is_open:
                sessions[exchange].append(date.fromisoformat(compact))
        if any(values != sorted(set(values)) for values in sessions.values()):
            raise ValueError("calendar approved sessions are malformed; no repair allowed")
        return cls(APPROVAL_ID, MANIFEST_ID, BUNDLE_ID, EXTENSION_ID,
                   tuple(sessions["SSE"]), tuple(sessions["SZSE"]))

    def sessions(self, exchange: str) -> tuple[date, ...]:
        if exchange == "SSE":
            return self.sse_sessions
        if exchange == "SZSE":
            return self.szse_sessions
        raise ValueError("unknown exchange")

    def window(self, exchange: str, anchor: date) -> tuple[date, ...]:
        sessions = self.sessions(exchange)
        if anchor not in sessions:
            raise ValueError("anchor absent from approved calendar")
        index = sessions.index(anchor)
        result = sessions[index:index + 6]
        if len(result) != 6:
            raise ValueError("approved H5 calendar window incomplete")
        return result

    def lineage(self) -> DomainLineageV1:
        return DomainLineageV1.create(
            domain="trade_calendar", approval_id=self.approval_id,
            manifest_id=self.manifest_id, fact_ids=(self.bundle_id, self.extension_id),
        )
