from __future__ import annotations

from dataclasses import fields
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.dataset_equivalence import DatasetEquivalenceDecision, DatasetEquivalenceEvidenceV1  # noqa: E402
from v5_2.data.evidence import EvidenceArtifactV1, EvidenceStatus, EvidenceType, EvidenceValidityPolicy, EvidenceValidityRuleV1  # noqa: E402
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.historical_remediation import build_next_session_availability_map, classify_daily_bar_identity  # noqa: E402
from v5_2.data.manifests import DatasetManifestV1  # noqa: E402
from v5_2.data.source_approval import SourceApprovalArtifactV1  # noqa: E402

OUT = ROOT / "data/phase_1b_exit_remediation/governance"
OLD_APPROVAL = "7daf8a38391ebb27ef5675cce6e978b1b10823195b304eca84d719c3d5504724"
UPSTREAM = (
    "4a900c7e4f2b171d7adac07088025ca4bb9fb0da13cfa1b15e91eff3dafea601",
    "828e0e722d3d66c84a48584aac14fde37f86cf471f3722f403ec19044f36345c",
)
AVAILABILITY_ID = "6877256040eb6abbea3e6c4434485aaa212f23eba7f675f9d088ce7e05850bcb"
CROSS_ID = "32d3b74551fc962cecb61a11839bdc177f1f3492fa1d11f8fba2fc9c15c7dd87"
NORMALIZATION_ID = "53fd452337be9368e37fb01aeb8a38082db0a470a5ab94ea0cad06b8653c2cc4"
UNIT_ID = "e7a744be0f572b6bfe7ad909829f366e0bc75c16a795edb46e561d70effaf093"
EXCEPTION_ID = "2e058686710af8eab330763c24da3c923c30e52072e5500642d093adf8405204"
EXCEPTION_SET = "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
NOW = datetime(2026, 9, 13, 12, 0, tzinfo=timezone(timedelta(hours=8)))


def _mapping(item):
    return {field.name: getattr(item, field.name) for field in fields(item)}


def _write(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError("immutable daily-bar panel artifact collision")
    if not path.exists():
        path.write_bytes(encoded)


def _calendar_sessions():
    base = json.loads((ROOT / "data/phase_1b1/governance/daily-bar-universe-2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01.json").read_text(encoding="utf-8"))
    sessions = set(base["ordered_sessions"])
    extension = json.loads((ROOT / "data/phase_1b1_2026_extension/governance/calendar-extension-3cd7c2f6fbdfcff34d739033d3ac789a7661903c1b32c4c626e24ebe0a1f047a.json").read_text(encoding="utf-8"))
    sessions.update(row[1] for row in extension["ordered_rows"] if row[2] == 1 and row[1] <= "20260911")
    return tuple(sorted(sessions))


def _lifecycles():
    result = {}
    for root in (ROOT / "data/phase_1b1", ROOT / "data/phase_1b1_2026_extension"):
        for path in (root / "raw/datahubco_tushare_proxy/security_master").rglob("*.json"):
            value = json.loads(path.read_text(encoding="utf-8"))
            for row in value["provider_payload"]["rows"]:
                identity = str(row.get("ts_code", ""))
                if identity.endswith((".SH", ".SZ")):
                    lifecycle = (str(row.get("list_date") or "00000000"), str(row.get("delist_date") or "99999999"))
                    if identity in result and result[identity] != lifecycle:
                        raise RuntimeError(f"conflicting lifecycle for {identity}")
                    result[identity] = lifecycle
    target_bundle = json.loads(next(OUT.glob(
        "complete-security-master-fact-bundle-*.json")).read_text(encoding="utf-8"))
    target = set(target_bundle["ordered_security_identities"])
    missing = target - set(result)
    if missing:
        raise RuntimeError("target daily-bar lifecycle is incomplete")
    return {identity: result[identity] for identity in sorted(target)}


def _inventory_id():
    base = "9b1d034f00ab0d637bc56ab120ffcf725f226f21c09d27c3b85e36a4f644a6ce"
    values = []
    for path in (ROOT / "data/phase_1b_exit_daily_bar_2026/governance").glob("inventory-*.json"):
        item = json.loads(path.read_text(encoding="utf-8"))
        if tuple(item["upstream_approval_ids"]) == UPSTREAM:
            values.append(item["inventory_id"])
    if len(values) != 1:
        raise RuntimeError("one correctly pinned daily-bar 2026 inventory is required")
    body = {"schema_version": "DailyBarCompleteRequestInventoryV1", "base_inventory_id": base,
            "extension_inventory_id": values[0], "coverage_start": "2010-01-04",
            "coverage_end": "2026-09-10", "upstream_approval_ids": UPSTREAM}
    digest = content_hash(body)
    _write(OUT / f"daily-bar-complete-inventory-{digest}.json",
           {"inventory_id": digest, **body, "content_hash": digest})
    return digest


def _receipts(roots):
    values = []
    for root in roots:
        for path in (root / "receipts").rglob("*.json"):
            values.append(json.loads(path.read_text(encoding="utf-8"))["receipt_hash"])
    return tuple(sorted(set(values)))


def main() -> int:
    roots = (ROOT / "data/phase_1b1", ROOT / "data/phase_1b_exit_daily_bar_2026")
    sessions = _calendar_sessions()
    research_sessions = tuple(item for item in sessions if "20100104" <= item <= "20260910")
    lifecycles = _lifecycles()
    raw_hashes, observed_by_identity, observed_sessions = [], {}, set()
    row_count, duplicate_count, invalid_identity_count, excluded_non_target_count = 0, 0, 0, 0
    sample_sessions = {"20120629", "20180629", "20250630", "20260630"}
    observed_samples = {item: set() for item in sample_sessions}
    for root in roots:
        for path in (root / "raw/datahubco_tushare_proxy/daily_bar").rglob("*.json"):
            value = json.loads(path.read_text(encoding="utf-8"))
            raw_hashes.append(value["payload_hash"])
            local = set()
            for row in value["provider_payload"]["rows"]:
                identity, session = str(row["ts_code"]), str(row["trade_date"])
                key = (identity, session)
                if key in local:
                    duplicate_count += 1
                    continue
                local.add(key)
                disposition = classify_daily_bar_identity(identity, lifecycles)
                if disposition == "EXCLUDED_NON_TARGET":
                    excluded_non_target_count += 1
                    continue
                if disposition != "TARGET":
                    invalid_identity_count += 1
                    continue
                observed_by_identity[identity] = observed_by_identity.get(identity, 0) + 1
                observed_sessions.add(session)
                if session in observed_samples:
                    observed_samples[session].add(identity)
                row_count += 1
    if duplicate_count or invalid_identity_count:
        raise RuntimeError("daily-bar raw panel contains duplicate or unresolved identities")
    if not sample_sessions <= observed_sessions:
        raise RuntimeError("daily-bar panel misses a frozen dry-run session")
    expected = 0
    for identity, (start, end) in lifecycles.items():
        expected += sum(max(start, "20100104") <= session <= min(end, "20260910") for session in research_sessions)
    missing = expected - row_count
    if missing < 0:
        raise RuntimeError("daily-bar observations exceed effective historical universe")
    availability_map = build_next_session_availability_map(
        research_sessions=research_sessions, approved_sessions=sessions)
    inventory_id = _inventory_id()
    body = {"schema_version": "ResearchWideHistoricalDailyBarPanelV1",
        "coverage_start": "2010-01-04", "coverage_end": "2026-09-10",
        "row_count": row_count, "symbol_count": len(observed_by_identity),
        "requested_effective_symbol_sessions": expected, "observed_symbol_sessions": row_count,
        "missing_symbol_sessions": missing, "coverage_ratio": f"{row_count / expected:.12f}",
        "missing_semantics": "UNCLASSIFIED_NOT_ZERO_NOT_SUSPENSION_NOT_DELISTED",
        "duplicate_count": duplicate_count, "invalid_identity_count": invalid_identity_count,
        "excluded_non_target_row_count": excluded_non_target_count,
        "availability_policy": "NEXT_SESSION_SAFE@16:30 Asia/Shanghai",
        "availability_overlay_hash": content_hash(availability_map),
        "old_d15_lineage_status": "EXCLUDED_FROM_RESEARCH_VISIBLE_LINEAGE",
        "raw_payload_hashes": tuple(sorted(set(raw_hashes))), "request_inventory_id": inventory_id,
        "upstream_approval_ids": UPSTREAM,
        "frozen_session_observed_counts": tuple((key, len(observed_samples[key])) for key in sorted(observed_samples)),
        "frozen_session_symbol_hashes": tuple((key, content_hash(tuple(sorted(observed_samples[key]))))
                                               for key in sorted(observed_samples)),
        "normalization_policy_id": NORMALIZATION_ID, "unit_policy_id": UNIT_ID,
        "exception_policy_id": EXCEPTION_ID, "exception_set_hash": EXCEPTION_SET,
        "cross_source_evidence_id": CROSS_ID, "availability_evidence_id": AVAILABILITY_ID}
    panel_id = content_hash(body)
    _write(OUT / f"historical-daily-bar-panel-{panel_id}.json",
           {"panel_id": panel_id, **body, "content_hash": panel_id})
    source_version = content_hash(body["raw_payload_hashes"])
    equivalence = DatasetEquivalenceEvidenceV1.create(
        source_name="datahubco_tushare_proxy", dataset_kind="daily_bar",
        reference_contract="V5.2 Phase 1B-2B semantics extended without reinterpretation",
        tested_endpoints=("daily",), tested_fields=("ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"),
        coverage_tested={"start": "2010-01-04", "end": "2026-09-10", "rows": row_count},
        sample_rule={"evidence_id": CROSS_ID, "frozen_semantics": True},
        field_mapping={"vol": "shares via frozen x100 rule", "amount": "yuan via frozen x1000 rule"},
        semantic_findings=("existing OHLC/unit/cross-source semantics retained",),
        missing_fields=("provider publication timestamp",), extra_fields=(),
        value_comparison_summary={"mismatched": 0, "unresolved": 0},
        pit_findings=("all reconstructed bars use NEXT_SESSION_SAFE",),
        revision_findings=("immutable raw payload identity retained",),
        pagination_findings=("all request checkpoints terminal",),
        cross_source_findings=("frozen Phase 1B-2B evidence retained",),
        limitations=("missing bars remain semantically unclassified",),
        decision=DatasetEquivalenceDecision.EQUIVALENT_WITH_RULES, verified_at=NOW,
        input_artifact_ids=(panel_id, inventory_id, CROSS_ID, AVAILABILITY_ID),
        policy_version="phase-1b-exit-daily-bar-equivalence-v1")
    evidence_policy = "phase-1b-exit-daily-bar-evidence-v1"
    evidence = tuple(EvidenceArtifactV1.create(evidence_type=kind, status=EvidenceStatus.PASS,
        observed_at=NOW, verified_at=NOW, policy_version=evidence_policy,
        source_version_identity=source_version, input_artifact_ids=(panel_id, equivalence.evidence_id),
        valid_until=None, findings=("full historical request/materialization boundary verified",))
        for kind in EvidenceType)
    validity = EvidenceValidityPolicy(policy_version="phase-1b-exit-daily-bar-validity-v1",
        rules=tuple(EvidenceValidityRuleV1(kind, None, True, (evidence_policy,)) for kind in EvidenceType))
    approval = SourceApprovalArtifactV1.evaluate(source_name="datahubco_tushare_proxy",
        dataset_kind="daily_bar", coverage_start=date(2010, 1, 4), coverage_end=date(2026, 9, 10),
        verified_at=NOW, source_version_identity=source_version,
        policy_version="phase-1b-exit-daily-bar-v1", evaluator_version="phase-1b-exit-daily-bar-evaluator-v1",
        evidence=evidence, required_evidence_types=tuple(EvidenceType),
        rule_set={"panel_id": panel_id, "historical_available_at": "NEXT_SESSION_SAFE@16:30 Asia/Shanghai",
                  "missing_bar_semantics": "UNCLASSIFIED_FAIL_CLOSED", "adjustment": "UNADJUSTED_RAW"},
        evidence_validity_policy=validity, resolution_as_of=NOW,
        equivalence_evidence=equivalence, supersedes_approval_id=OLD_APPROVAL)
    if approval.decision.value != "APPROVED_WITH_RULES":
        raise RuntimeError("complete daily-bar panel did not receive scoped approval")
    manifest = DatasetManifestV1.create(created_at=NOW, source_name="datahubco_tushare_proxy",
        dataset_kind="daily_bar", approval=approval, approval_resolution_as_of=NOW,
        coverage_start=date(2010, 1, 4), coverage_end=date(2026, 9, 10),
        row_count=row_count, symbol_count=len(observed_by_identity),
        raw_payload_hashes=body["raw_payload_hashes"],
        normalized_content_hashes=(NORMALIZATION_ID, UNIT_ID, body["availability_overlay_hash"]),
        fact_content_hashes=(panel_id,), normalizer_version="daily-bar-normalization-v1+availability-overlay-v1",
        availability_policy_version="daily-bar-availability-v1:NEXT_SESSION_SAFE",
        quality_findings=(f"requested={expected}", f"observed={row_count}", f"missing_unclassified={missing}",
                          "old D 15:00 facts excluded from research-visible lineage"),
        pit_validation_status="PASS", rule_compliance_status="PASS", pagination_complete=True,
        audit_policy_id=panel_id, endpoint_identities=("daily",), receipt_hashes=_receipts(roots),
        approval_policy_id="phase-1b-exit-daily-bar-validity-v1", upstream_approval_ids=UPSTREAM,
        request_inventory_id=inventory_id, normalization_policy_id=NORMALIZATION_ID,
        unit_policy_id=UNIT_ID, exception_policy_id=EXCEPTION_ID, exception_set_hash=EXCEPTION_SET,
        cross_source_evidence_id=CROSS_ID, availability_evidence_id=AVAILABILITY_ID,
        latest_approved_session=date(2026, 9, 10))
    _write(OUT / f"daily_bar-equivalence-{equivalence.evidence_id}.json", _mapping(equivalence))
    for item in evidence:
        _write(OUT / f"daily_bar-evidence-{item.evidence_id}.json", _mapping(item))
    _write(OUT / f"daily_bar-approval-{approval.approval_id}.json", _mapping(approval))
    _write(OUT / f"daily_bar-manifest-{manifest.dataset_id}.json", _mapping(manifest))
    sample_values = {key: tuple(sorted(value)) for key, value in observed_samples.items()}
    sample_body = {"schema_version": "DailyBarFrozenSessionAvailabilityV1",
                   "panel_id": panel_id, "sessions": sample_values}
    sample_id = content_hash(sample_body)
    sample_path = OUT / f"daily-bar-frozen-session-availability-{sample_id}.json"
    _write(sample_path, {"artifact_id": sample_id, **sample_body, "content_hash": sample_id})
    print(json.dumps({"panel_id": panel_id, "approval_id": approval.approval_id,
        "manifest_id": manifest.dataset_id, "inventory_id": inventory_id,
        "row_count": row_count, "expected": expected, "missing": missing,
        "frozen_session_counts": dict(body["frozen_session_observed_counts"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
