from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.real_audits.upstream_extension import (  # noqa: E402
    EffectiveDatedUniverseV1, IncrementalCalendarExtensionV1,
)
from v5_2.data.manifests import DatasetManifestV1  # noqa: E402
from v5_2.data.source_approval import ApprovalDecision, SourceApprovalArtifactV1  # noqa: E402
from v5_2.data.real_audits.security_master_normalization import SecurityMasterNormalizationPolicyV1  # noqa: E402

RUNTIME = ROOT / "data" / "phase_1b1_2026_extension"
OLD_CALENDAR = "1581b4d367dba1256247ddd13e09b53d0f95b5b1deeb40af9e6ed4a36606353b"
OLD_MASTER = "f208c17accba6b669359f476b2fdf3a1bc9ec6856e7fa1831ccdd1c42b80d8cf"
OLD_UNIVERSE = "2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01"
OFFICIAL = {
    "calendar_sse": "https://www.sse.com.cn/disclosure/dealinstruc/closed/?from=timeline&isappinstalled=0",
    "calendar_szse": "https://www.szse.cn/disclosure/notice/t20260206_618970.html",
    "603352.SH": "https://big5.sse.com.cn/site/cht/www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2026-01-14/603352_20260114_GE8P.pdf",
    "688820.SH": "https://www.sse.com.cn/disclosure/announcement/listing/ipo/c/c_20260420_10815741.shtml",
    "001220.SZ": "https://www.szse.cn/www/certificate/maind/maindynamice/t20260203_618890.html",
    "301666.SZ": "https://www.szse.cn/www/disclosure/notice/t20260415_619965.html",
    "688287.SH": "https://www.sse.com.cn/disclosure/announcement/listing/stock/c/c_20260608_10821090.shtml",
}
EXPECTED = {
    "603352.SH": "20260115", "688820.SH": "20260421", "001220.SZ": "20260203",
    "301666.SZ": "20260416", "688287.SH": "20260610",
}
NOW = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)


def _write(path: Path, value: object) -> None:
    encoded = canonical_json(value); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError("immutable extension artifact collision")
    if not path.exists(): path.write_bytes(encoded)


def _rows(kind: str) -> list[dict]:
    rows = []
    for path in (RUNTIME / "raw" / "datahubco_tushare_proxy" / kind).rglob("*.json"):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("payload_hash") != path.stem: raise RuntimeError("raw hash mismatch")
        rows.extend(raw["provider_payload"]["rows"])
    return rows


def _official_evidence() -> tuple[dict, ...]:
    existing = tuple((RUNTIME / "governance").glob("official-anchors-*.json"))
    if existing:
        artifact = json.loads(existing[0].read_text(encoding="utf-8"))
        if content_hash({"schema_version": artifact["schema_version"], "entries": tuple(artifact["entries"])}) != artifact["artifact_id"]:
            raise RuntimeError("official anchor artifact integrity failed")
        return tuple(artifact["entries"])
    result = []
    for name, url in OFFICIAL.items():
        with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as response:
            payload = response.read()
        result.append({"name": name, "url": url, "sha256": hashlib.sha256(payload).hexdigest(),
                       "byte_count": len(payload), "http_status": 200})
    body = {"schema_version": "OfficialUpstreamAnchorBundleV1", "entries": tuple(result)}
    artifact_id = content_hash(body)
    _write(RUNTIME / "governance" / f"official-anchors-{artifact_id}.json", {"artifact_id": artifact_id, **body})
    return tuple(result)


def _approval(*, kind: str, coverage_end: date, source_version: str,
              evidence_ids: tuple[str, ...], supersedes: str, rules: dict) -> SourceApprovalArtifactV1:
    body = {"schema_version": "SourceApprovalArtifactV1", "source_name": "datahubco_tushare_proxy",
            "dataset_kind": kind, "decision": ApprovalDecision.APPROVED_WITH_RULES,
            "coverage_start": date(2010, 1, 1), "coverage_end": coverage_end, "verified_at": NOW,
            "source_version_identity": source_version, "policy_version": "phase-1b1-rolling-extension-v1",
            "rule_set": rules, "evidence_ids": tuple(sorted(evidence_ids)),
            "evidence_bundle_hash": content_hash(tuple(sorted(evidence_ids))),
            "evaluator_version": "phase-1b1-rolling-extension-evaluator-v1",
            "evidence_validity_policy_version": "phase-1b1-upstream-validity-v1",
            "equivalence_evidence_id": evidence_ids[-1], "supersedes_approval_id": supersedes}
    digest = content_hash(body)
    return SourceApprovalArtifactV1(approval_id=digest, content_hash=digest,
        **{key: value for key, value in body.items() if key != "schema_version"})


def main() -> int:
    official = _official_evidence()
    calendar_rows = _rows("trade_calendar")
    official_ids = tuple(item["sha256"] for item in official[:2])
    calendar = IncrementalCalendarExtensionV1.create(
        previous_approval_id=OLD_CALENDAR, coverage_start=date(2026, 1, 1),
        coverage_end=date(2026, 9, 11), rows=calendar_rows, official_anchor_ids=official_ids)
    # The official holiday anchors are validations only; every daily state remains provider-derived.
    expected_closed = ("20260101", "20260216", "20260406", "20260504", "20260619")
    expected_open = ("20260105", "20260224", "20260407", "20260506", "20260622", "20260909", "20260910", "20260911")
    by_day = {(row["exchange"], row["cal_date"]): row["is_open"] for row in calendar_rows}
    if any(by_day[(exchange, day)] != 0 for exchange in ("SSE", "SZSE") for day in expected_closed):
        raise RuntimeError("official holiday cross-check mismatch")
    if any(by_day[(exchange, day)] != 1 for exchange in ("SSE", "SZSE") for day in expected_open):
        raise RuntimeError("official open-session cross-check mismatch")
    _write(RUNTIME / "governance" / f"calendar-extension-{calendar.extension_id}.json", asdict(calendar))

    master_rows = _rows("security_master")
    by_code = {row["ts_code"]: row for row in master_rows}
    for code, expected in EXPECTED.items():
        row = by_code.get(code)
        actual = row.get("delist_date") if code == "688287.SH" else row.get("list_date") if row else None
        if actual != expected:
            raise RuntimeError(f"official security sample mismatch: {code}")
    delta = [row for row in master_rows if str(row.get("list_date") or "") > "20251231" or str(row.get("delist_date") or "") > "20251231"]
    historical = json.loads((ROOT / "data" / "phase_1b1" / "governance" / f"daily-bar-universe-{OLD_UNIVERSE}.json").read_text(encoding="utf-8"))
    policy = SecurityMasterNormalizationPolicyV1.create_default()
    historical_symbols = set(historical["ordered_symbols"])
    baseline_symbols = tuple(row["ts_code"] for row in master_rows
        if row["ts_code"] in historical_symbols and policy.disposition(row) == "NORMALIZED_ELIGIBLE"
        and str(row.get("list_date") or "") <= "20251231"
        and (not row.get("delist_date") or str(row["delist_date"]) > "20251231"))
    changes = tuple({"security_identity": row["ts_code"], "listing_date": row["list_date"],
                     "delisting_date": row.get("delist_date")} for row in delta)
    universe = EffectiveDatedUniverseV1.create(
        previous_approval_id=OLD_MASTER, previous_universe_id=OLD_UNIVERSE,
        baseline_symbols=baseline_symbols, changes=changes,
        coverage_end=date(2026, 9, 10), evidence_ids=tuple(item["sha256"] for item in official[2:]))
    _write(RUNTIME / "governance" / f"universe-extension-{universe.universe_id}.json", asdict(universe))

    acquisitions = {}
    for kind in ("trade_calendar", "security_master"):
        paths = tuple((RUNTIME / "governance").glob(f"{kind}-acquisition-*.json"))
        if len(paths) != 1: raise RuntimeError("incremental acquisition identity is ambiguous")
        acquisitions[kind] = json.loads(paths[0].read_text(encoding="utf-8"))
    calendar_approval = _approval(kind="trade_calendar", coverage_end=date(2026, 9, 11),
        source_version=content_hash(tuple(acquisitions["trade_calendar"]["payload_hashes"])),
        evidence_ids=(calendar.extension_id, *official_ids), supersedes=OLD_CALENDAR,
        rules={"incremental_start": "2026-01-01", "weekday_inference": False,
               "official_cross_check": "SSE_AND_SZSE_PASS"})
    master_approval = _approval(kind="security_master", coverage_end=date(2026, 9, 10),
        source_version=content_hash(tuple(acquisitions["security_master"]["payload_hashes"])),
        evidence_ids=(universe.universe_id, *(item["sha256"] for item in official[2:])), supersedes=OLD_MASTER,
        rules={"incremental_start": "2026-01-01", "effective_dated_universe": universe.universe_id,
               "official_sample_count": len(EXPECTED), "missing_identity": "FAIL_CLOSED"})
    _write(RUNTIME / "governance" / f"trade_calendar-approval-{calendar_approval.approval_id}.json", asdict(calendar_approval))
    _write(RUNTIME / "governance" / f"security_master-approval-{master_approval.approval_id}.json", asdict(master_approval))

    calendar_manifest = DatasetManifestV1.create(created_at=NOW, source_name="datahubco_tushare_proxy", dataset_kind="trade_calendar",
        approval=calendar_approval, approval_resolution_as_of=NOW, coverage_start=date(2026, 1, 1), coverage_end=date(2026, 9, 11),
        row_count=len(calendar_rows), symbol_count=2, raw_payload_hashes=tuple(acquisitions["trade_calendar"]["payload_hashes"]),
        normalized_content_hashes=(calendar.extension_id,), fact_content_hashes=(calendar.extension_id,), normalizer_version="trade-calendar-normalizer-v1",
        availability_policy_version="session-calendar-v1", quality_findings=(), pit_validation_status="PASS", rule_compliance_status="PASS",
        pagination_complete=True, audit_policy_id="phase-1b1-rolling-extension-v1", endpoint_identities=("trade-cal",),
        receipt_hashes=(acquisitions["trade_calendar"]["artifact_id"],), approval_policy_id="phase-1b1-rolling-extension-v1")
    master_manifest = DatasetManifestV1.create(created_at=NOW, source_name="datahubco_tushare_proxy", dataset_kind="security_master",
        approval=master_approval, approval_resolution_as_of=NOW, coverage_start=date(2026, 1, 1), coverage_end=date(2026, 9, 10),
        row_count=len(universe.approved_universe_as_of_session(date(2026, 9, 10))), symbol_count=len(universe.approved_universe_as_of_session(date(2026, 9, 10))), raw_payload_hashes=tuple(acquisitions["security_master"]["payload_hashes"]),
        normalized_content_hashes=(universe.universe_id,), fact_content_hashes=(universe.universe_id,), normalizer_version="security-master-normalization-v1",
        availability_policy_version="effective-dated-security-identity-v1", quality_findings=(), pit_validation_status="PASS", rule_compliance_status="PASS",
        pagination_complete=True, audit_policy_id="phase-1b1-rolling-extension-v1", endpoint_identities=("stock-basic",),
        receipt_hashes=(acquisitions["security_master"]["artifact_id"],), approval_policy_id="phase-1b1-rolling-extension-v1",
        input_count=len(master_rows), eligible_count=len(universe.approved_universe_as_of_session(date(2026, 9, 10))), excluded_non_target_count=len(master_rows)-len(universe.approved_universe_as_of_session(date(2026, 9, 10))),
        quarantined_count=0, quarantined_identity_hashes=())
    _write(RUNTIME / "governance" / f"trade_calendar-manifest-{calendar_manifest.dataset_id}.json", asdict(calendar_manifest))
    _write(RUNTIME / "governance" / f"security_master-manifest-{master_manifest.dataset_id}.json", asdict(master_manifest))

    audit = {
        "schema_version": "Phase1B1Upstream2026ExtensionAuditV1", "decision": "PASS",
        "calendar_extension_id": calendar.extension_id, "calendar_supersedes": OLD_CALENDAR,
        "calendar_approval_id": calendar_approval.approval_id, "calendar_manifest_id": calendar_manifest.dataset_id,
        "calendar_approved_through": "2026-09-11", "calendar_rows": len(calendar_rows),
        "calendar_cross_check": {"closed": expected_closed, "open": expected_open},
        "universe_id": universe.universe_id, "master_supersedes": OLD_MASTER,
        "master_approval_id": master_approval.approval_id, "master_manifest_id": master_manifest.dataset_id,
        "security_master_approved_through": "2026-09-10", "target_universe_approved_through": "2026-09-10",
        "new_listings": sum(str(row.get("list_date") or "") > "20251231" for row in delta),
        "delistings": sum(str(row.get("delist_date") or "") > "20251231" for row in delta),
        "identity_transitions": 0, "official_sample_count": len(EXPECTED),
        "official_sample_disposition": "MATCH", "weekday_inference": False,
    }
    audit_id = content_hash(audit)
    _write(RUNTIME / "governance" / f"upstream-extension-audit-{audit_id}.json", {"audit_id": audit_id, **audit})
    (RUNTIME / "governance" / "current-extension-id.txt").write_text(audit_id, encoding="ascii")
    print(f"UPSTREAM_2026=PASS AUDIT_ID={audit_id} CALENDAR_ID={calendar.extension_id} UNIVERSE_ID={universe.universe_id} NEW_LISTINGS={audit['new_listings']} DELISTINGS={audit['delistings']}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
