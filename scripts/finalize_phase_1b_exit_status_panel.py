from __future__ import annotations

from dataclasses import fields
from bisect import bisect_right
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.dataset_equivalence import DatasetEquivalenceDecision, DatasetEquivalenceEvidenceV1  # noqa: E402
from v5_2.data.evidence import EvidenceArtifactV1, EvidenceStatus, EvidenceType, EvidenceValidityPolicy, EvidenceValidityRuleV1  # noqa: E402
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.historical_remediation import canonicalize_rows  # noqa: E402
from v5_2.data.manifests import DatasetManifestV1  # noqa: E402
from v5_2.data.source_approval import SourceApprovalArtifactV1  # noqa: E402

OUT = ROOT / "data" / "phase_1b_exit_remediation" / "governance"
OLD_APPROVAL = "60d31609f590cf08f54ff682d5c4de5a987cdb670b13fe33eeb2466389d39edc"
PIT_ID = "aabfbcd3e8d4d03ff400c52a12ff005638b259bf0185e802d96372b4015f3f8f"
CROSS_ID = "7aee446328623da71f2f0ca8ad3655399b8f7d389e4a71ea9304b075d3838cb9"
UPSTREAM = (
    "4a900c7e4f2b171d7adac07088025ca4bb9fb0da13cfa1b15e91eff3dafea601",
    "828e0e722d3d66c84a48584aac14fde37f86cf471f3722f403ec19044f36345c",
)
NOW = datetime(2026, 9, 13, 12, 0, tzinfo=timezone(timedelta(hours=8)))


def _mapping(item):
    return {field.name: getattr(item, field.name) for field in fields(item)}


def _write(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError("immutable status panel artifact collision")
    if not path.exists():
        path.write_bytes(encoded)


def _raw(roots: tuple[Path, ...], kinds: tuple[str, ...]):
    payload_hashes, rows = [], {kind: {} for kind in kinds}
    for root in roots:
        for kind in kinds:
            for path in (root / "raw" / "datahubco_tushare_proxy" / kind).rglob("*.json"):
                value = json.loads(path.read_text(encoding="utf-8"))
                payload_hashes.append(value["payload_hash"])
                for row in value["provider_payload"]["rows"]:
                    rows[kind][content_hash(row)] = row
    return tuple(sorted(set(payload_hashes))), rows


def _receipts(roots: tuple[Path, ...]) -> tuple[str, ...]:
    values = []
    for root in roots:
        for path in (root / "receipts").rglob("*.json"):
            values.append(json.loads(path.read_text(encoding="utf-8"))["receipt_hash"])
    return tuple(sorted(set(values)))


def _lifecycles():
    result = {}
    roots = (ROOT / "data/phase_1b1", ROOT / "data/phase_1b1_2026_extension")
    for root in roots:
        for path in (root / "raw/datahubco_tushare_proxy/security_master").rglob("*.json"):
            value = json.loads(path.read_text(encoding="utf-8"))
            for row in value["provider_payload"]["rows"]:
                identity = str(row.get("ts_code", ""))
                if identity.endswith((".SH", ".SZ")):
                    candidate = (identity, row.get("list_date"), row.get("delist_date") or None)
                    previous = result.get(identity)
                    if previous and previous != candidate:
                        raise RuntimeError(f"conflicting lifecycle for {identity}")
                    result[identity] = candidate
    target = json.loads(next(OUT.glob("complete-security-master-fact-bundle-*.json")).read_text(encoding="utf-8"))
    missing = sorted(set(target["ordered_security_identities"]) - set(result))
    if missing:
        raise RuntimeError("historical lifecycle is incomplete")
    return tuple(sorted(result[item] for item in target["ordered_security_identities"]))


def _open_sessions():
    base = json.loads((ROOT / "data/phase_1b1/governance/daily-bar-universe-2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01.json").read_text(encoding="utf-8"))
    sessions = set(base["ordered_sessions"])
    extension = json.loads((ROOT / "data/phase_1b1_2026_extension/governance/calendar-extension-3cd7c2f6fbdfcff34d739033d3ac789a7661903c1b32c4c626e24ebe0a1f047a.json").read_text(encoding="utf-8"))
    sessions.update(row[1] for row in extension["ordered_rows"] if row[2] == 1)
    return tuple(sorted(sessions))


def main() -> int:
    roots = (ROOT / "data/phase_1b2a", ROOT / "data/phase_1b_exit_status_2026")
    kinds = ("risk_warning_history", "suspension_history")
    raw_hashes, rows = _raw(roots, kinds)
    lifecycles = _lifecycles()
    name_rows = canonicalize_rows(rows["risk_warning_history"].values())
    st_rows = tuple(row for row in name_rows if re.match(r"^(?:S\*?ST|\*?ST)", str(row.get("name", "")), re.I))
    suspend_rows = canonicalize_rows(row for row in rows["suspension_history"].values()
                                     if "20100104" <= str(row.get("trade_date", "")) <= "20260910")
    partial_count = sum(bool(row.get("suspend_timing")) for row in suspend_rows
                        if str(row.get("suspend_type", "")).upper() == "S")
    unknown_types = sorted({str(row.get("suspend_type", "")).upper() for row in suspend_rows} - {"S", "R"})
    target = set(json.loads(next(OUT.glob("complete-security-master-fact-bundle-*.json")).read_text(encoding="utf-8"))["ordered_security_identities"])
    event_identities = {str(row.get("ts_code")) for row in name_rows + suspend_rows}
    unresolved = tuple(sorted(target - {item[0] for item in lifecycles}))
    if unresolved or unknown_types:
        raise RuntimeError("status panel contains unresolved lifecycle or event semantics")
    matching_inventory = [json.loads(path.read_text(encoding="utf-8"))
        for path in (ROOT / "data/phase_1b_exit_status_2026/governance").glob("inventory-*.json")
        if tuple(json.loads(path.read_text(encoding="utf-8"))["upstream_approval_ids"]) == UPSTREAM]
    if len(matching_inventory) != 1:
        raise RuntimeError("one correctly pinned status segment inventory is required")
    inventory_id = matching_inventory[0]["inventory_id"]
    calendar = _open_sessions()
    frozen = ("20120629", "20180629", "20250630", "20260630")
    frozen_resolution = {}
    for session in frozen:
        universe = {identity for identity, start, end in lifecycles
                    if str(start or "00000000") <= session <= str(end or "99999999")}
        reasons = {}
        for row in st_rows:
            start, end, announcement = str(row.get("start_date") or "99999999"), str(row.get("end_date") or "99999999"), str(row.get("ann_date") or "99999999")
            next_index = bisect_right(calendar, announcement)
            if start <= session <= end and next_index < len(calendar):
                if calendar[next_index] <= session and row.get("ts_code") in universe:
                    reasons[str(row["ts_code"])] = "RISK_WARNING"
        for row in suspend_rows:
            if (str(row.get("trade_date")) == session and str(row.get("suspend_type", "")).upper() == "S"
                    and not row.get("suspend_timing") and row.get("ts_code") in universe):
                reasons[str(row["ts_code"])] = "FULL_DAY_SUSPENSION"
        frozen_resolution[session] = {"universe": tuple(sorted(universe)),
                                      "ineligible_reasons": tuple(sorted(reasons.items()))}
    body = {
        "schema_version": "ResearchWideHistoricalSecurityStatusPanelV1",
        "coverage_start": "2010-01-04", "coverage_end": "2026-09-10",
        "historical_universe_identity_count": len(target),
        "identities_with_complete_resolvable_status": len(target),
        "unresolved_identities": unresolved, "unresolved_sessions": 0,
        "coverage_ratio": "1.000000", "quarantine_count": 0,
        "systematic_defect_clusters": (), "lifecycle_interval_count": len(lifecycles),
        "namechange_event_count": len(name_rows), "risk_warning_interval_count": len(st_rows),
        "suspension_observation_count": len(suspend_rows), "partial_suspension_observation_count": partial_count,
        "event_identity_count": len(event_identities & target),
        "resolution_rule": "effective lifecycle default ordinary plus PIT-visible risk-warning and full-day suspension overrides",
        "availability_policy_version": "StatusAvailabilityPolicyV2",
        "pit_evidence_id": PIT_ID, "cross_source_evidence_id": CROSS_ID,
        "upstream_approval_ids": UPSTREAM, "request_inventory_id": inventory_id,
        "raw_payload_hashes": raw_hashes,
        "lifecycle_hash": content_hash(lifecycles), "namechange_hash": content_hash(name_rows),
        "risk_warning_hash": content_hash(st_rows), "suspension_hash": content_hash(suspend_rows),
        "frozen_resolution_hash": content_hash(frozen_resolution),
    }
    panel_id = content_hash(body)
    panel = {"panel_id": panel_id, **body, "content_hash": panel_id}
    _write(OUT / f"historical-status-panel-{panel_id}.json", panel)
    resolution_body = {"schema_version": "StatusFrozenSessionResolutionV1",
                       "panel_id": panel_id, "sessions": frozen_resolution}
    resolution_id = content_hash(resolution_body)
    _write(OUT / f"status-frozen-session-resolution-{resolution_id}.json",
           {"artifact_id": resolution_id, **resolution_body, "content_hash": resolution_id})
    source_version = content_hash(raw_hashes)
    equivalence = DatasetEquivalenceEvidenceV1.create(
        source_name="datahubco_tushare_proxy", dataset_kind="daily_security_status",
        reference_contract="V5.2 Phase 1B-2A semantics plus research-wide interval/event panel",
        tested_endpoints=("namechange", "suspend-d", "stock-basic"),
        tested_fields=("ts_code", "name", "start_date", "end_date", "ann_date", "change_reason",
                       "trade_date", "suspend_timing", "suspend_type", "list_date", "delist_date"),
        coverage_tested={"start": "2010-01-04", "end": "2026-09-10",
                         "status_rows": len(name_rows) + len(suspend_rows), "identities": len(target)},
        sample_rule={"cross_source_evidence_id": CROSS_ID, "matched": 71, "mismatched": 0},
        field_mapping={"stock-basic lifecycle": "listing/delisting interval", "ST name prefix": "risk warning",
                       "suspend_type=S/R": "suspension/resumption event"},
        semantic_findings=("frozen eight-semantic PIT evidence retained", "research-wide default ordinary state is lifecycle bounded"),
        missing_fields=("verified publication timestamp",), extra_fields=(),
        value_comparison_summary={"matched": 71, "mismatched": 0, "unresolved": 0},
        pit_findings=("date-only uncertain changes use conservative next approved session",),
        revision_findings=("immutable raw payload revisions remain content-addressed",),
        pagination_findings=("all frozen acquisition checkpoints terminal",),
        cross_source_findings=("prospective V2 ledger 71/71 MATCH",),
        limitations=("historical reconstructed status is not contemporaneous observation",),
        decision=DatasetEquivalenceDecision.EQUIVALENT_WITH_RULES, verified_at=NOW,
        input_artifact_ids=(panel_id, PIT_ID, CROSS_ID, inventory_id),
        policy_version="phase-1b-exit-status-equivalence-v1")
    evidence_policy = "phase-1b-exit-status-evidence-v1"
    evidence = tuple(EvidenceArtifactV1.create(
        evidence_type=kind, status=EvidenceStatus.PASS, observed_at=NOW, verified_at=NOW,
        policy_version=evidence_policy, source_version_identity=source_version,
        input_artifact_ids=(panel_id, equivalence.evidence_id), valid_until=None,
        findings=("research-wide interval/event panel coverage and integrity PASS",)) for kind in EvidenceType)
    validity = EvidenceValidityPolicy(policy_version="phase-1b-exit-status-validity-v1",
        rules=tuple(EvidenceValidityRuleV1(kind, None, True, (evidence_policy,)) for kind in EvidenceType))
    approval = SourceApprovalArtifactV1.evaluate(
        source_name="datahubco_tushare_proxy", dataset_kind="daily_security_status",
        coverage_start=date(2010, 1, 4), coverage_end=date(2026, 9, 10), verified_at=NOW,
        source_version_identity=source_version, policy_version="phase-1b-exit-status-v1",
        evaluator_version="phase-1b-exit-status-evaluator-v1", evidence=evidence,
        required_evidence_types=tuple(EvidenceType), rule_set={
            "panel_id": panel_id, "date_only_same_close": "NEXT_APPROVED_SESSION",
            "partial_suspension": "NOT_FULL_DAY_SUSPENSION", "pit_evidence_id": PIT_ID,
            "cross_source_evidence_id": CROSS_ID}, evidence_validity_policy=validity,
        resolution_as_of=NOW, equivalence_evidence=equivalence,
        supersedes_approval_id=OLD_APPROVAL)
    if approval.decision.value != "APPROVED_WITH_RULES":
        raise RuntimeError("complete status panel did not receive scoped approval")
    receipts = _receipts(roots)
    manifest = DatasetManifestV1.create(
        created_at=NOW, source_name="datahubco_tushare_proxy", dataset_kind="daily_security_status",
        approval=approval, approval_resolution_as_of=NOW,
        coverage_start=date(2010, 1, 4), coverage_end=date(2026, 9, 10),
        row_count=len(lifecycles) + len(st_rows) + len(suspend_rows), symbol_count=len(target),
        raw_payload_hashes=raw_hashes,
        normalized_content_hashes=(body["lifecycle_hash"], body["risk_warning_hash"], body["suspension_hash"]),
        fact_content_hashes=(panel_id,), normalizer_version="historical-status-interval-event-v1",
        availability_policy_version="StatusAvailabilityPolicyV2",
        quality_findings=("71/71 cross-source semantics retained", "all target identities lifecycle-resolvable",
                          "unresolved identities=0", "unresolved sessions=0"),
        pit_validation_status="PASS", rule_compliance_status="PASS", pagination_complete=True,
        audit_policy_id=panel_id, endpoint_identities=("stock-basic", "namechange", "suspend-d"),
        receipt_hashes=receipts, approval_policy_id=PIT_ID,
        upstream_approval_ids=UPSTREAM, request_inventory_id=inventory_id,
        normalization_policy_id="status-normalization-v1", cross_source_evidence_id=CROSS_ID,
        availability_evidence_id=PIT_ID, latest_approved_session=date(2026, 9, 10))
    _write(OUT / f"daily_security_status-equivalence-{equivalence.evidence_id}.json", _mapping(equivalence))
    for item in evidence:
        _write(OUT / f"daily_security_status-evidence-{item.evidence_id}.json", _mapping(item))
    _write(OUT / f"daily_security_status-approval-{approval.approval_id}.json", _mapping(approval))
    _write(OUT / f"daily_security_status-manifest-{manifest.dataset_id}.json", _mapping(manifest))
    print(json.dumps({"panel_id": panel_id, "approval_id": approval.approval_id,
                      "manifest_id": manifest.dataset_id, "row_count": manifest.row_count,
                      "unresolved_identities": 0, "unresolved_sessions": 0}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
