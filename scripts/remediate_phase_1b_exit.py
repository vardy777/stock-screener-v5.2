from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.historical_lineage import HistoricalDatasetCompositionV1  # noqa: E402
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.manifests import DatasetManifestV1  # noqa: E402
from v5_2.data.source_approval import ApprovalDecision, SourceApprovalArtifactV1  # noqa: E402


BASE = ROOT / "data/phase_1b1"
EXTENSION = ROOT / "data/phase_1b1_2026_extension"
OUTPUT = ROOT / "data/phase_1b_exit_remediation/governance"
BASE_CALENDAR_APPROVAL = "1581b4d367dba1256247ddd13e09b53d0f95b5b1deeb40af9e6ed4a36606353b"
CURRENT_CALENDAR_APPROVAL = "4a900c7e4f2b171d7adac07088025ca4bb9fb0da13cfa1b15e91eff3dafea601"
CALENDAR_EXTENSION_MANIFEST = "9653175fa933cd83c975d0a3aff1c3583a75e38c7e906d0c458107911e338385"
BASE_MASTER_APPROVAL = "f208c17accba6b669359f476b2fdf3a1bc9ec6856e7fa1831ccdd1c42b80d8cf"
CURRENT_MASTER_APPROVAL = "828e0e722d3d66c84a48584aac14fde37f86cf471f3722f403ec19044f36345c"
MASTER_EXTENSION_MANIFEST = "3c53b5a99c54c6f1520d31af6c434170011544c19d310ea2e50115dc5f42c940"
BASE_UNIVERSE = "2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_immutable(path: Path, value) -> None:
    encoded = canonical_json(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError(f"immutable artifact collision: {path.name}")
    if not path.exists():
        path.write_bytes(encoded)


def approval_from_mapping(value) -> SourceApprovalArtifactV1:
    return SourceApprovalArtifactV1(
        approval_id=value["approval_id"], source_name=value["source_name"],
        dataset_kind=value["dataset_kind"], decision=ApprovalDecision(value["decision"]),
        coverage_start=date.fromisoformat(value["coverage_start"]),
        coverage_end=date.fromisoformat(value["coverage_end"]),
        verified_at=datetime.fromisoformat(value["verified_at"]),
        source_version_identity=value["source_version_identity"], policy_version=value["policy_version"],
        rule_set=value["rule_set"], evidence_ids=tuple(value["evidence_ids"]),
        evidence_bundle_hash=value["evidence_bundle_hash"], evaluator_version=value["evaluator_version"],
        evidence_validity_policy_version=value["evidence_validity_policy_version"],
        equivalence_evidence_id=value.get("equivalence_evidence_id"),
        supersedes_approval_id=value.get("supersedes_approval_id"), content_hash=value["content_hash"])


def raw_lineage(kind: str, root: Path):
    values = [load(path) for path in sorted((root / "raw/datahubco_tushare_proxy" / kind).rglob("*.json"))]
    payload_hashes = {value["payload_hash"] for value in values}
    receipts = []
    for path in (root / "receipts").rglob("*.json"):
        value = load(path)
        if value.get("payload_hash") in payload_hashes:
            receipts.append(value["receipt_hash"])
    return tuple(sorted(value["payload_hash"] for value in values)), tuple(sorted(receipts)), values


def manifest(*, approval, kind, coverage, rows, symbols, raw_hashes, receipt_hashes,
             fact_hashes, upstream=(), master_counts=None):
    counts = master_counts or (None, None, None, None, ())
    return DatasetManifestV1.create(created_at=datetime.fromisoformat("2026-09-13T04:00:00+00:00"),
        source_name="datahubco_tushare_proxy", dataset_kind=kind, approval=approval,
        approval_resolution_as_of=datetime.fromisoformat("2026-09-13T04:00:00+00:00"),
        coverage_start=coverage[0], coverage_end=coverage[1], row_count=rows, symbol_count=symbols,
        raw_payload_hashes=raw_hashes, normalized_content_hashes=fact_hashes,
        fact_content_hashes=fact_hashes, normalizer_version=f"{kind}-historical-base-v1",
        availability_policy_version="historical-pit-v1", quality_findings=(),
        pit_validation_status="PASS", rule_compliance_status="PASS", pagination_complete=True,
        audit_policy_id=f"{kind}-historical-base-audit-v1", endpoint_identities=(kind,),
        receipt_hashes=receipt_hashes, input_count=counts[0], eligible_count=counts[1],
        excluded_non_target_count=counts[2], quarantined_count=counts[3],
        quarantined_identity_hashes=counts[4], approval_policy_id=f"{kind}-historical-base-v1",
        upstream_approval_ids=upstream)


def main() -> int:
    calendar_raw, calendar_receipts, calendar_pages = raw_lineage("trade_calendar", BASE)
    calendar_rows = sorted((row for page in calendar_pages for row in page["provider_payload"]["rows"]),
                           key=lambda row: (row["cal_date"], row["exchange"]))
    if len(calendar_rows) != 11688 or any(day not in {row["cal_date"] for row in calendar_rows}
        for day in ("20120629", "20181001", "20250630")):
        raise RuntimeError("historical calendar facts are incomplete")
    calendar_bundle_body = {"schema_version": "HistoricalCalendarFactBundleV1",
        "coverage_start": "2010-01-01", "coverage_end": "2025-12-31",
        "source_payload_hashes": calendar_raw, "ordered_rows": calendar_rows,
        "weekday_inference": False,
        "cross_source_evidence_ids": ("e5e42c14be97aa1bc8d4365f729dfa7d24bebf618141bfdf77f356c3072668d6",)}
    calendar_bundle_id = content_hash(calendar_bundle_body)
    calendar_bundle = {**calendar_bundle_body, "fact_bundle_id": calendar_bundle_id, "content_hash": calendar_bundle_id}
    write_immutable(OUTPUT / f"historical-calendar-fact-bundle-{calendar_bundle_id}.json", calendar_bundle)

    base_calendar = approval_from_mapping(load(BASE / f"governance/trade_calendar-approval-{BASE_CALENDAR_APPROVAL}.json"))
    current_calendar = approval_from_mapping(load(EXTENSION / f"governance/trade_calendar-approval-{CURRENT_CALENDAR_APPROVAL}.json"))
    calendar_base_manifest = manifest(approval=base_calendar, kind="trade_calendar",
        coverage=(date(2010, 1, 1), date(2025, 12, 31)), rows=len(calendar_rows), symbols=2,
        raw_hashes=calendar_raw, receipt_hashes=calendar_receipts, fact_hashes=(calendar_bundle_id,))
    write_immutable(OUTPUT / f"trade-calendar-base-manifest-{calendar_base_manifest.dataset_id}.json", asdict(calendar_base_manifest))
    extension_calendar = load(EXTENSION / f"governance/trade_calendar-manifest-{CALENDAR_EXTENSION_MANIFEST}.json")
    calendar_complete = manifest(approval=current_calendar, kind="trade_calendar",
        coverage=(date(2010, 1, 1), date(2026, 9, 11)), rows=len(calendar_rows)+extension_calendar["row_count"], symbols=2,
        raw_hashes=calendar_raw + tuple(extension_calendar["raw_payload_hashes"]),
        receipt_hashes=calendar_receipts + tuple(extension_calendar["receipt_hashes"]),
        fact_hashes=(calendar_bundle_id, *extension_calendar["fact_content_hashes"]),
        upstream=(BASE_CALENDAR_APPROVAL,))
    write_immutable(OUTPUT / f"trade-calendar-complete-manifest-{calendar_complete.dataset_id}.json", asdict(calendar_complete))
    calendar_composition = HistoricalDatasetCompositionV1.create(dataset_kind="trade_calendar",
        base_manifest_id=calendar_base_manifest.dataset_id, extension_manifest_id=CALENDAR_EXTENSION_MANIFEST,
        base_fact_bundle_id=calendar_bundle_id, base_coverage=(date(2010, 1, 1), date(2025, 12, 31)),
        extension_coverage=(date(2026, 1, 1), date(2026, 9, 11)), composition_rule="ADJACENT_UNION_V1")
    write_immutable(OUTPUT / f"trade-calendar-composition-{calendar_composition.composition_id}.json", asdict(calendar_composition))

    master_raw, master_receipts, _ = raw_lineage("security_master", BASE)
    universe = load(BASE / f"governance/daily-bar-universe-{BASE_UNIVERSE}.json")
    symbols = tuple(universe["ordered_symbols"])
    master_bundle_body = {"schema_version": "HistoricalSecurityMasterFactBundleV1",
        "coverage_start": "2010-01-01", "coverage_end": "2025-12-31",
        "ordered_security_identities": symbols, "effective_identity_graph_ids": (
            "6275f4df087e40a11eb12b4ece0e569865814002d4da301342c2279af98acda0",
            "d67d886299be85bb5585c9103140ef327fe13b78161903f7e5120646a8ee9e8f"),
        "source_payload_hashes": master_raw, "current_snapshot_backfill": False}
    master_bundle_id = content_hash(master_bundle_body)
    master_bundle = {**master_bundle_body, "fact_bundle_id": master_bundle_id, "content_hash": master_bundle_id}
    write_immutable(OUTPUT / f"historical-security-master-fact-bundle-{master_bundle_id}.json", master_bundle)
    base_master = approval_from_mapping(load(BASE / f"governance/security_master-approval-{BASE_MASTER_APPROVAL}.json"))
    current_master = approval_from_mapping(load(EXTENSION / f"governance/security_master-approval-{CURRENT_MASTER_APPROVAL}.json"))
    counts = (5549, len(symbols), 1, 0, ())
    master_base_manifest = manifest(approval=base_master, kind="security_master",
        coverage=(date(2010, 1, 1), date(2025, 12, 31)), rows=len(symbols), symbols=len(symbols),
        raw_hashes=master_raw, receipt_hashes=master_receipts, fact_hashes=(master_bundle_id,), master_counts=counts)
    write_immutable(OUTPUT / f"security-master-base-manifest-{master_base_manifest.dataset_id}.json", asdict(master_base_manifest))
    extension_master = load(EXTENSION / f"governance/security_master-manifest-{MASTER_EXTENSION_MANIFEST}.json")
    extension_universe = load(EXTENSION / "governance" /
        f"universe-extension-{extension_master['fact_content_hashes'][0]}.json")
    complete_symbols = tuple(sorted(set(symbols) | {str(row[0]) for row in extension_universe["changes"]}))
    complete_bundle_body = {"schema_version": "CompleteHistoricalSecurityMasterFactBundleV1",
        "coverage_start": "2010-01-01", "coverage_end": "2026-09-10",
        "base_fact_bundle_id": master_bundle_id,
        "extension_universe_id": extension_universe["universe_id"],
        "ordered_security_identities": complete_symbols,
        "current_snapshot_backfill": False}
    complete_bundle_id = content_hash(complete_bundle_body)
    write_immutable(OUTPUT / f"complete-security-master-fact-bundle-{complete_bundle_id}.json",
        {**complete_bundle_body, "fact_bundle_id": complete_bundle_id, "content_hash": complete_bundle_id})
    complete_counts = (5898, len(complete_symbols), 5898 - len(complete_symbols), 0, ())
    master_complete = manifest(approval=current_master, kind="security_master",
        coverage=(date(2010, 1, 1), date(2026, 9, 10)), rows=len(complete_symbols), symbols=len(complete_symbols),
        raw_hashes=master_raw + tuple(extension_master["raw_payload_hashes"]),
        receipt_hashes=master_receipts + tuple(extension_master["receipt_hashes"]),
        fact_hashes=(master_bundle_id, *extension_master["fact_content_hashes"], complete_bundle_id),
        upstream=(BASE_MASTER_APPROVAL,), master_counts=complete_counts)
    write_immutable(OUTPUT / f"security-master-complete-manifest-{master_complete.dataset_id}.json", asdict(master_complete))
    master_composition = HistoricalDatasetCompositionV1.create(dataset_kind="security_master",
        base_manifest_id=master_base_manifest.dataset_id, extension_manifest_id=MASTER_EXTENSION_MANIFEST,
        base_fact_bundle_id=master_bundle_id, base_coverage=(date(2010, 1, 1), date(2025, 12, 31)),
        extension_coverage=(date(2026, 1, 1), date(2026, 9, 10)), composition_rule="ADJACENT_UNION_V1")
    write_immutable(OUTPUT / f"security-master-composition-{master_composition.composition_id}.json", asdict(master_composition))
    print(json.dumps({"calendar_base_manifest": calendar_base_manifest.dataset_id,
        "calendar_complete_manifest": calendar_complete.dataset_id,
        "calendar_composition": calendar_composition.composition_id,
        "master_base_manifest": master_base_manifest.dataset_id,
        "master_complete_manifest": master_complete.dataset_id,
        "master_composition": master_composition.composition_id}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
