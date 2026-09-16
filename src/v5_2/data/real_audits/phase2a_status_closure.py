from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path

from v5_2.data.identity import canonical_json, content_hash
from v5_2.data.manifests import DatasetManifestV1
from v5_2.data.raw_artifacts import RawArtifactStore
from v5_2.data.real_audits.status_availability import StatusAvailabilityPolicyV2
from v5_2.data.security_status_facts import DailySecurityStatusFactV1
from v5_2.data.source_approval import ApprovalDecision, SourceApprovalArtifactV1


APPROVAL_ID = "60d31609f590cf08f54ff682d5c4de5a987cdb670b13fe33eeb2466389d39edc"
MANIFEST_ID = "57b4d38523c32a31959fb8dc9e2335778f97ed86562413c95e7ff9716ec65e3d"
PIT_ID = "aabfbcd3e8d4d03ff400c52a12ff005638b259bf0185e802d96372b4015f3f8f"
FROZEN_STATUS_SESSIONS = (
    ("002166.SZ", date(2019, 4, 12)), ("002166.SZ", date(2019, 4, 16)),
    ("600155.SH", date(2015, 11, 16)), ("600155.SH", date(2015, 11, 18)),
    ("600155.SH", date(2015, 11, 19)), ("600155.SH", date(2015, 11, 20)),
    ("600155.SH", date(2015, 11, 23)), ("300131.SZ", date(2014, 9, 11)),
    ("002118.SZ", date(2023, 8, 3)),
)
NOW = datetime(2026, 9, 16, 12, 0, tzinfo=timezone(timedelta(hours=8)))


@dataclass(frozen=True, slots=True)
class StatusClosureEntryV1:
    security_identity: str
    session: date
    disposition: str
    request_id: str
    payload_hash: str
    receipt_hash: str
    raw_artifact_path: str
    receipt_artifact_path: str
    raw_hash_pinned: bool
    receipt_hash_pinned: bool
    identity_valid: bool
    exchange_open: bool
    provider_semantics: str


@dataclass(frozen=True, slots=True)
class StatusClosureAuditV1:
    entries: tuple[StatusClosureEntryV1, ...]
    source_approval_id: str
    source_manifest_id: str
    pit_evidence_id: str
    provider_request_count: int
    final_trading_session: date
    delisting_effective_session: date
    final_trading_boundary_evidence_ids: tuple[str, ...]
    audit_id: str
    content_hash: str

    def verify(self) -> bool:
        body = {
            "entries": self.entries,
            "source_approval_id": self.source_approval_id,
            "source_manifest_id": self.source_manifest_id,
            "pit_evidence_id": self.pit_evidence_id,
            "provider_request_count": self.provider_request_count,
            "final_trading_session": self.final_trading_session,
            "delisting_effective_session": self.delisting_effective_session,
            "final_trading_boundary_evidence_ids": self.final_trading_boundary_evidence_ids,
        }
        digest = content_hash({"schema_version": type(self).__name__, **body})
        return self.audit_id == self.content_hash == digest

    def as_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["schema_version"] = type(self).__name__
        return value


@dataclass(frozen=True, slots=True)
class StatusClosureMaterializationV1:
    facts: tuple[DailySecurityStatusFactV1, ...]
    manifest: DatasetManifestV1


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _approval(raw: dict[str, object]) -> SourceApprovalArtifactV1:
    values = dict(raw)
    values["decision"] = ApprovalDecision(values["decision"])
    values["coverage_start"] = date.fromisoformat(str(values["coverage_start"]))
    values["coverage_end"] = date.fromisoformat(str(values["coverage_end"]))
    values["verified_at"] = datetime.fromisoformat(str(values["verified_at"]))
    values["evidence_ids"] = tuple(values["evidence_ids"])
    return SourceApprovalArtifactV1(**values)  # type: ignore[arg-type]


def _write_immutable(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        if path.read_bytes() != encoded:
            raise RuntimeError("immutable status closure collision")
        return
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)


def audit_existing_status_evidence(repository_root: Path, raw_runtime: Path) -> StatusClosureAuditV1:
    governance = repository_root / "data/phase_1b2a/governance"
    manifest = _load(governance / f"daily_security_status-manifest-{MANIFEST_ID}.json")
    approval = _load(governance / f"daily_security_status-approval-{APPROVAL_ID}.json")
    pit = _load(governance / f"status-pit-knowledge-time-{PIT_ID}.json")
    if (manifest.get("approval_id") != APPROVAL_ID or approval.get("decision") != "APPROVED_WITH_RULES"
            or not pit.get("complete") or pit.get("policy_version") != "status-availability-after-close-v2"):
        raise RuntimeError("approved Status lineage is missing or invalid")
    pinned_raw = set(manifest["raw_payload_hashes"])
    pinned_receipts = set(manifest["receipt_hashes"])
    wanted = {(identity, session.strftime("%Y%m%d")) for identity, session in FROZEN_STATUS_SESSIONS}
    found: dict[tuple[str, str], StatusClosureEntryV1] = {}
    delisting_suspension_dates: set[date] = set()
    store = RawArtifactStore(raw_runtime)
    raw_base = raw_runtime / "raw/datahubco_tushare_proxy/suspension_history"
    for path in sorted(raw_base.rglob("*.json")):
        try:
            artifact = store.read_payload(path)
        except Exception as exc:
            if path.stem in pinned_raw:
                raise RuntimeError("required status raw is missing or tampered") from exc
            continue
        matching = [row for row in artifact.provider_payload["rows"]
                    if (str(row.get("ts_code")), str(row.get("trade_date"))) in wanted]
        for row in artifact.provider_payload["rows"]:
            if (str(row.get("ts_code")) == "002118.SZ" and row.get("suspend_type") == "S"
                    and row.get("suspend_timing") in (None, "")):
                value = str(row.get("trade_date"))
                delisting_suspension_dates.add(date(int(value[:4]), int(value[4:6]), int(value[6:])))
        if not matching:
            continue
        receipt_paths = tuple((raw_runtime / "receipts" / artifact.payload_hash[:16]).glob("*.json"))
        receipts = []
        for receipt_path in receipt_paths:
            receipt = store.read_receipt(receipt_path)
            if receipt.payload_hash == artifact.payload_hash:
                receipts.append((receipt_path, receipt))
        if len(receipts) != 1:
            raise RuntimeError("required status receipt is missing or ambiguous")
        receipt_path, receipt = receipts[0]
        for row in matching:
            key = (str(row["ts_code"]), str(row["trade_date"]))
            if row.get("suspend_type") != "S" or row.get("suspend_timing") not in (None, ""):
                raise RuntimeError("exact status evidence does not prove full-day suspension")
            session = date(int(key[1][:4]), int(key[1][4:6]), int(key[1][6:]))
            found[key] = StatusClosureEntryV1(
                security_identity=key[0], session=session, disposition="FULL_DAY_SUSPENSION",
                request_id=artifact.request_id, payload_hash=artifact.payload_hash,
                receipt_hash=receipt.receipt_hash,
                raw_artifact_path=path.relative_to(raw_runtime).as_posix(),
                receipt_artifact_path=receipt_path.relative_to(raw_runtime).as_posix(),
                raw_hash_pinned=artifact.payload_hash in pinned_raw,
                receipt_hash_pinned=receipt.receipt_hash in pinned_receipts,
                identity_valid=True, exchange_open=True,
                provider_semantics="suspend-d S with null timing means full-day suspension",
            )
    ordered = tuple(found[(identity, session.strftime("%Y%m%d"))]
                    for identity, session in FROZEN_STATUS_SESSIONS
                    if (identity, session.strftime("%Y%m%d")) in found)
    if len(ordered) != 9 or any(not item.raw_hash_pinned or not item.receipt_hash_pinned for item in ordered):
        raise RuntimeError("required status raw is missing or tampered")
    calendar = _load(repository_root / "data/phase_1b_exit_remediation/governance/"
                     "historical-calendar-fact-bundle-d64a2ef0823e9a55a33d3b8111337fb71fcb43ce778235694ebfadfed1396dcc.json")
    required_suspension_dates = {
        date(int(row["cal_date"][:4]), int(row["cal_date"][4:6]), int(row["cal_date"][6:]))
        for row in calendar["ordered_rows"] if row["exchange"] == "SZSE" and row["is_open"] == 1
        and "20230616" <= row["cal_date"] <= "20230803"
    }
    if not required_suspension_dates or not required_suspension_dates <= delisting_suspension_dates:
        raise RuntimeError("002118 final-trading suspension chain is incomplete")
    daily_hash = "801a5179a86c0415e23d9764716bc77b3bca2087907a9c5a282c05fad1a2356a"
    daily_paths = tuple((raw_runtime.parent / "phase_1b1/raw/datahubco_tushare_proxy/daily_bar").rglob(f"{daily_hash}.json"))
    if len(daily_paths) != 1:
        raise RuntimeError("002118 approved Daily Bar boundary evidence is missing")
    daily = RawArtifactStore(raw_runtime.parent / "phase_1b1").read_payload(daily_paths[0])
    sessions = sorted(str(row["trade_date"]) for row in daily.provider_payload["rows"]
                      if row.get("ts_code") == "002118.SZ")
    if not sessions or sessions[-1] != "20230615":
        raise RuntimeError("002118 final trading session is not proven")
    body = {"entries": ordered, "source_approval_id": APPROVAL_ID,
            "source_manifest_id": MANIFEST_ID, "pit_evidence_id": PIT_ID,
            "provider_request_count": 0,
            "final_trading_session": date(2023, 6, 15),
            "delisting_effective_session": date(2023, 8, 4),
            "final_trading_boundary_evidence_ids": (
                daily_hash, "bf95765f9514415d1e65ea4564a894eb4b1bb6c2945b91d6ec2d41d2a4c6d03f",
                *tuple(sorted({item.payload_hash for item in ordered if item.security_identity == "002118.SZ"})),
            )}
    digest = content_hash({"schema_version": "StatusClosureAuditV1", **body})
    return StatusClosureAuditV1(**body, audit_id=digest, content_hash=digest)


def materialize_status_closure(repository_root: Path, audit: StatusClosureAuditV1,
                               output_root: Path) -> StatusClosureMaterializationV1:
    if not audit.verify() or audit.provider_request_count != 0:
        raise RuntimeError("Status closure audit is invalid")
    governance = repository_root / "data/phase_1b2a/governance"
    approval = _approval(_load(governance / f"daily_security_status-approval-{APPROVAL_ID}.json"))
    if approval.decision is not ApprovalDecision.APPROVED_WITH_RULES:
        raise RuntimeError("Status approval is not publication-capable")
    sessions = tuple(sorted({entry.session for entry in audit.entries}))
    policy = StatusAvailabilityPolicyV2.market_observable_by_close("FULL_DAY_SUSPENSION")
    facts = tuple(DailySecurityStatusFactV1.create(
        security_identity=entry.security_identity, session=entry.session,
        is_listed=True, is_delisted=False, is_risk_warning=False, is_suspended=True,
        effective_from=entry.session, effective_to=entry.session,
        available_at=policy.derive(event_date=entry.session, published_at=None, approved_sessions=sessions),
        source_fact_ids=(entry.payload_hash, entry.receipt_hash, audit.audit_id),
        source_name="datahubco_tushare_proxy", policy_version=policy.policy_version,
        risk_warning_excluded=True,
    ) for entry in audit.entries)
    manifest = DatasetManifestV1.create(
        created_at=NOW, source_name="datahubco_tushare_proxy", dataset_kind="daily_security_status",
        approval=approval, approval_resolution_as_of=NOW,
        coverage_start=min(entry.session for entry in audit.entries),
        coverage_end=max(entry.session for entry in audit.entries), row_count=len(facts),
        symbol_count=len({fact.security_identity for fact in facts}),
        raw_payload_hashes=tuple(sorted({entry.payload_hash for entry in audit.entries})),
        normalized_content_hashes=tuple(sorted(content_hash({"security_identity": entry.security_identity,
            "session": entry.session, "status": entry.disposition}) for entry in audit.entries)),
        fact_content_hashes=tuple(sorted(fact.content_hash for fact in facts)),
        normalizer_version="phase2a-status-closure-normalizer-v1",
        availability_policy_version=policy.policy_version,
        quality_findings=("nine frozen sessions reuse existing approved immutable suspend-d evidence",),
        pit_validation_status="PASS", rule_compliance_status="PASS", pagination_complete=True,
        audit_policy_id=PIT_ID, endpoint_identities=("suspend-d",),
        receipt_hashes=tuple(sorted({entry.receipt_hash for entry in audit.entries})),
        approval_policy_id=approval.evidence_validity_policy_version,
        request_inventory_id=audit.audit_id, cross_source_evidence_id=approval.rule_set["cross_source_evidence_id"],
    )
    for fact in facts:
        _write_immutable(output_root / "data/phase_1b2a_status_closure/facts/daily_security_status" / f"{fact.fact_id}.json", fact)
    _write_immutable(output_root / "data/phase_1b2a_status_closure/governance" /
                     f"daily_security_status-supplement-manifest-{manifest.dataset_id}.json", manifest)
    return StatusClosureMaterializationV1(facts=facts, manifest=manifest)
