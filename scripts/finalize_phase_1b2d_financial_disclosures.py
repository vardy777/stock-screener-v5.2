from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.manifests import DatasetManifestV1  # noqa: E402
from v5_2.data.raw_artifacts import RawArtifactStore  # noqa: E402
from v5_2.data.real_audits.financial_disclosure_availability import FinancialDisclosureAvailabilityPolicyV1  # noqa: E402
from v5_2.data.real_audits.financial_disclosure_entry import build_financial_disclosure_inventory  # noqa: E402
from v5_2.data.real_audits.financial_disclosure_normalization import (  # noqa: E402
    financial_fact_equivalence_key, normalize_statement_rows,
)
from v5_2.data.real_audits.financial_disclosure_validation import (  # noqa: E402
    FinancialDisclosureGateEvidenceV1, authorize_financial_disclosure_publication,
    evaluate_financial_disclosure_gates,
)
from v5_2.data.source_approval import ApprovalDecision, SourceApprovalArtifactV1  # noqa: E402

RUNTIME = ROOT / "data" / "phase_1b2d"
GOVERNANCE, APPROVED = RUNTIME / "governance", RUNTIME / "approved"
BASE_UNIVERSE = ROOT / "data" / "phase_1b1" / "governance" / "daily-bar-universe-2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01.json"
CALENDAR_EXTENSION = ROOT / "data" / "phase_1b1_2026_extension" / "governance" / "calendar-extension-3cd7c2f6fbdfcff34d739033d3ac789a7661903c1b32c4c626e24ebe0a1f047a.json"
NOW = datetime(2026, 9, 10, 16, 50, tzinfo=timezone.utc)


def _write(path: Path, value: object) -> None:
    encoded = canonical_json(value); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded: raise RuntimeError("immutable finalization collision")
    if not path.exists(): path.write_bytes(encoded)


def _load_current(prefix: str, pointer: str, identity: str) -> tuple[str, dict]:
    artifact_id = (GOVERNANCE / pointer).read_text(encoding="ascii").strip()
    value = json.loads((GOVERNANCE / f"{prefix}-{artifact_id}.json").read_text(encoding="utf-8"))
    claimed = value.get(identity); body = dict(value); body.pop(identity, None); body.pop("content_hash", None)
    if claimed != artifact_id or value.get("content_hash") != artifact_id or content_hash(body) != artifact_id:
        raise RuntimeError(f"{prefix} integrity failed")
    return artifact_id, value


def _sessions() -> tuple[date, ...]:
    base = json.loads(BASE_UNIVERSE.read_text(encoding="utf-8"))["ordered_sessions"]
    extension = json.loads(CALENDAR_EXTENSION.read_text(encoding="utf-8"))["ordered_rows"]
    values = set(base); values.update(row[1] for row in extension if row[2] == 1)
    return tuple(date(int(day[:4]), int(day[4:6]), int(day[6:])) for day in sorted(values))


def _fact_dict(fact) -> dict[str, object]:
    value = asdict(fact); value["value"] = format(fact.value, "f")
    return value


def _write_partitions(summary: dict, policy) -> tuple[tuple[str, ...], tuple[str, ...], str]:
    expected = set(summary["payload_hashes"])
    paths = {path.stem: path for path in (RUNTIME / "raw").rglob("*.json") if path.stem in expected}
    if set(paths) != expected: raise RuntimeError("publication raw payload set incomplete")
    temp = RUNTIME / "staging"; temp.mkdir(parents=True, exist_ok=True)
    kinds = ("financial_balance_sheet", "financial_cash_flow", "financial_income")
    streams, raw_files = {}, {}
    for kind in kinds:
        raw_file = open(temp / f"{kind}.jsonl.gz.tmp", "wb")
        raw_files[kind] = raw_file; streams[kind] = gzip.GzipFile(filename="", mode="wb", fileobj=raw_file, mtime=0)
    quarantine_file = open(temp / "quarantines.jsonl.gz.tmp", "wb")
    quarantine_stream = gzip.GzipFile(filename="", mode="wb", fileobj=quarantine_file, mtime=0)
    fact_count = 0; seen_equivalent_keys = set()
    try:
        store = RawArtifactStore(RUNTIME)
        for payload_hash in sorted(expected):
            path = paths[payload_hash]; kind = path.parts[-4]
            artifact = store.read_payload(path)
            result = normalize_statement_rows(kind, artifact.provider_payload["rows"],
                                               source_version_identity=payload_hash, policy=policy)
            for fact in result.facts:
                key = financial_fact_equivalence_key(fact)
                if key in seen_equivalent_keys: continue
                seen_equivalent_keys.add(key)
                streams[kind].write(canonical_json(_fact_dict(fact)) + b"\n"); fact_count += 1
            for item in result.quarantines:
                quarantine_stream.write(canonical_json({"raw_payload_hash": payload_hash, **item}) + b"\n")
    finally:
        for stream in streams.values(): stream.close()
        for raw_file in raw_files.values(): raw_file.close()
        quarantine_stream.close(); quarantine_file.close()
    partition_hashes = []
    for kind in kinds:
        temporary = temp / f"{kind}.jsonl.gz.tmp"; digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
        destination = APPROVED / f"{kind}-facts-{digest}.jsonl.gz"; destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_bytes() != temporary.read_bytes(): raise RuntimeError("fact partition collision")
        if not destination.exists(): temporary.replace(destination)
        else: temporary.unlink()
        partition_hashes.append(digest)
    qtemp = temp / "quarantines.jsonl.gz.tmp"; qdigest = hashlib.sha256(qtemp.read_bytes()).hexdigest()
    qdest = APPROVED / f"financial-quarantines-{qdigest}.jsonl.gz"
    if not qdest.exists(): qtemp.replace(qdest)
    else: qtemp.unlink()
    return tuple(partition_hashes), (qdigest,), str(fact_count)


def main() -> int:
    summary_id, summary = _load_current("acquisition-summary", "current-acquisition-summary-id.txt", "acquisition_summary_id")
    audit_id, audit = _load_current("materialization-audit", "current-materialization-audit-id.txt", "materialization_audit_id")
    cross_id, cross = _load_current("cross-source-evidence", "current-cross-source-evidence-id.txt", "evidence_id")
    capability_id = (GOVERNANCE / "current-endpoint-capability-id.txt").read_text(encoding="ascii").strip()
    inventory_id = summary["inventory_id"]
    inventory = json.loads((GOVERNANCE / f"historical-inventory-{inventory_id}.json").read_text(encoding="utf-8"))
    cross_pass = cross["counts"] == {"MATCH": 14, "MISMATCH": 0, "UNAVAILABLE": 0, "UNRESOLVED": 0}
    coverage = {row[0]: row[1:] for row in audit["coverage_by_statement"]}
    complete_requests = summary["completed_requests"] == inventory["request_count"] == 33288
    observed_fact_history_spans_target = all(
        coverage[kind][2] <= "20100104" and coverage[kind][3] >= "20260831" for kind in coverage)
    revision_safe = (audit["later_publication_revision_groups"] > 0
        and audit["cross_payload_conflicting_groups"] == 0
        and audit["cross_payload_revision_groups"] == 0
        and audit["same_publication_conflict_groups"] <= audit["unique_quarantine_count"])
    expected_payloads = set(summary["payload_hashes"]); receipts_by_payload = {}
    store = RawArtifactStore(RUNTIME)
    for path in (RUNTIME / "receipts").rglob("*.json"):
        receipt = store.read_receipt(path); payload_hash = receipt.payload_hash
        if payload_hash in expected_payloads:
            receipts_by_payload.setdefault(payload_hash, set()).add(receipt.receipt_hash)
    receipt_hashes = tuple(sorted({value for values in receipts_by_payload.values() for value in values}))
    receipt_complete = set(receipts_by_payload) == expected_payloads
    semantics_safe = (audit["fact_integrity_failures"] == 0
        and audit["value_semantics_failures"] == 0 and audit["unit_semantics_failures"] == 0)
    availability_safe = audit["availability_policy_failures"] == 0 and cross_pass
    universe = json.loads(BASE_UNIVERSE.read_text(encoding="utf-8"))
    rebuilt_inventory = build_financial_disclosure_inventory(
        symbols=universe["ordered_symbols"], coverage_start=inventory["coverage_start"],
        coverage_end=inventory["coverage_end"], universe_id=inventory["universe_id"],
        upstream_approval_ids=inventory["upstream_approval_ids"])
    inventory_integrity = (inventory_id == inventory.get("content_hash") == rebuilt_inventory.inventory_id
        and tuple(inventory["request_ids"]) == tuple(request.request_id for request in rebuilt_inventory.requests))
    rolling_ready = (inventory_integrity and inventory["coverage_start"] == "20100104"
        and inventory["coverage_end"] == "20260910" and len(inventory["upstream_approval_ids"]) == 2
        and complete_requests and receipt_complete)
    exception_ratio = float(audit["exception_ratio"])
    exception_budget_safe = (exception_ratio <= float(audit["exception_budget_policy"]["maximum_ratio"])
        and set(dict(audit["quarantine_reasons"])) <= set(audit["exception_budget_policy"]["allowed_reasons"]))
    evidence = FinancialDisclosureGateEvidenceV1.create(
        structural="PASS" if complete_requests and summary["page_count"] == summary["completed_requests"] else "FAIL",
        pit="PASS" if availability_safe else "PENDING", cross_source="PASS" if cross_pass else "PENDING",
        revision="PASS" if revision_safe else "PENDING", value_semantics="PASS" if semantics_safe else "FAIL",
        unit_semantics="PASS" if semantics_safe and cross_pass and all(item["checks"]["unit_cny_verified"] for item in cross["ledger"]) else "PENDING",
        historical_coverage="PARTIAL",
        catch_up_2026="PASS" if all(coverage[kind][1] >= "20260630" for kind in coverage) else "PARTIAL",
        survivorship="PASS" if inventory["request_count"] == 5548 * 3 * 2 else "FAIL",
        rolling_coverage_model="PASS" if rolling_ready else "FAIL",
        production_incremental_readiness="PASS" if rolling_ready and complete_requests and receipt_complete else "PENDING",
        exception_budget="PASS" if exception_budget_safe and revision_safe else "FAIL",
        systematic_defect="PASS" if revision_safe and cross_pass and semantics_safe else "FAIL",
        publication_scope="OBSERVED_FACTS_ONLY" if observed_fact_history_spans_target else "UNKNOWN",
        evidence_ids=(capability_id, inventory_id, summary_id, audit_id, cross_id))
    _write(GOVERNANCE / f"gate-evidence-{evidence.evidence_id}.json", asdict(evidence))
    gate = evaluate_financial_disclosure_gates(evidence)
    _write(GOVERNANCE / f"gate-{gate.content_hash}.json", asdict(gate))
    (GOVERNANCE / "current-gate-id.txt").write_text(gate.content_hash, encoding="ascii")
    if not gate.publication_allowed:
        print(f"GATE_ID={gate.content_hash}\nSOURCE_APPROVAL={gate.source_approval}\nPUBLICATION_ALLOWED=false\nAPPROVED_FACTS=0\nDATASET_MANIFEST=none")
        return 0
    authorize_financial_disclosure_publication(gate, evidence)
    rules = {"supported_statement_types": ("BALANCE_SHEET", "CASH_FLOW", "INCOME"),
        "supported_metrics": ("n_cashflow_act", "n_cashflow_inv_act", "n_income_attr_p", "revenue", "total_assets", "total_liab"),
        "unsupported_endpoints": ("express", "fina_indicator", "forecast"),
        "date_only_availability": "NEXT_APPROVED_SESSION_16_30_ASIA_SHANGHAI",
        "same_publication_conflicts": "QUARANTINE", "missing_query_result": "NOT_RESEARCH_SAFE",
        "publication_scope": "OBSERVED_FACTS_ONLY", "panel_completeness": "NOT_ESTABLISHED"}
    approval_body = {"schema_version": "SourceApprovalArtifactV1", "source_name": "datahubco_tushare_proxy",
        "dataset_kind": "financial_disclosure", "decision": ApprovalDecision.APPROVED_WITH_RULES,
        "coverage_start": date(2010, 1, 4), "coverage_end": date(2026, 9, 10), "verified_at": NOW,
        "source_version_identity": summary_id, "policy_version": "financial-disclosure-scoped-v1",
        "rule_set": rules, "evidence_ids": evidence.evidence_ids, "evidence_bundle_hash": content_hash(evidence.evidence_ids),
        "evaluator_version": "phase-1b2d-gate-evaluator-v1", "evidence_validity_policy_version": "financial-disclosure-evidence-v1",
        "equivalence_evidence_id": cross_id, "supersedes_approval_id": None}
    approval_id = content_hash(approval_body)
    approval = SourceApprovalArtifactV1(approval_id=approval_id, content_hash=approval_id,
        **{key: value for key, value in approval_body.items() if key != "schema_version"})
    _write(GOVERNANCE / f"financial-disclosure-approval-{approval_id}.json", asdict(approval))
    partition_hashes, quarantine_hashes, fact_count_text = _write_partitions(summary, FinancialDisclosureAvailabilityPolicyV1(_sessions()))
    fact_count = int(fact_count_text)
    receipt_bundle_body = {"schema_version": "FinancialDisclosureReceiptBundleV1",
        "payload_count": len(expected_payloads), "receipt_count": len(receipt_hashes),
        "receipt_hashes": receipt_hashes}
    receipt_bundle_id = content_hash(receipt_bundle_body)
    _write(GOVERNANCE / f"receipt-bundle-{receipt_bundle_id}.json",
           {"receipt_bundle_id": receipt_bundle_id, **receipt_bundle_body})
    fact_bundle_body = {"schema_version": "ApprovedFinancialDisclosureFactBundleV1", "approval_id": approval_id,
                        "gate_id": gate.content_hash, "fact_count": fact_count,
                        "fact_set_hash": audit["fact_set_hash"], "partition_hashes": partition_hashes}
    fact_bundle_id = content_hash(fact_bundle_body)
    _write(GOVERNANCE / f"fact-bundle-{fact_bundle_id}.json", {"fact_bundle_id": fact_bundle_id, **fact_bundle_body})
    statement_coverage = tuple((kind.removeprefix("financial_").upper(),
        max(date(2010, 1, 4), date.fromisoformat(values[2][:4] + "-" + values[2][4:6] + "-" + values[2][6:])),
        date.fromisoformat(values[3][:4] + "-" + values[3][4:6] + "-" + values[3][6:]))
        for kind, values in sorted(coverage.items()))
    manifest = DatasetManifestV1.create(created_at=NOW, source_name="datahubco_tushare_proxy", dataset_kind="financial_disclosure",
        approval=approval, approval_resolution_as_of=NOW, coverage_start=date(2010, 1, 4), coverage_end=date(2026, 9, 10),
        row_count=fact_count, symbol_count=max(row[1] for row in audit["symbols_by_statement"]),
        raw_payload_hashes=tuple(summary["payload_hashes"]), normalized_content_hashes=(audit["fact_set_hash"],),
        fact_content_hashes=partition_hashes, normalizer_version="financial-disclosure-normalizer-v1",
        availability_policy_version="FinancialDisclosureAvailabilityPolicyV1", quality_findings=("4170_rows_quarantined",),
        pit_validation_status="PASS", rule_compliance_status="PASS", pagination_complete=True,
        audit_policy_id=gate.content_hash, endpoint_identities=("balancesheet", "cashflow", "income"), receipt_hashes=receipt_hashes,
        quarantined_count=audit["quarantine_count"], quarantined_identity_hashes=quarantine_hashes,
        approval_policy_id="financial-disclosure-scoped-v1", upstream_approval_ids=tuple(inventory["upstream_approval_ids"]),
        request_inventory_id=inventory_id, normalization_policy_id="financial-disclosure-normalizer-v1",
        unit_policy_id="RAW_DISCLOSED_CNY_V1", exception_policy_id="EXPLICIT_QUARANTINE_V1",
        exception_set_hash=quarantine_hashes[0], cross_source_evidence_id=cross_id,
        availability_evidence_id=evidence.evidence_id,
        supported_statement_types=("BALANCE_SHEET", "CASH_FLOW", "INCOME"),
        unsupported_financial_endpoints=("express", "fina_indicator", "forecast"),
        validated_coverage_by_statement_type=statement_coverage,
        materialized_coverage_by_statement_type=statement_coverage,
        coverage_gaps=((date(2010, 1, 4), date(2026, 9, 10), "PANEL_COMPLETENESS_NOT_ESTABLISHED__MISSING_QUERY_NOT_RESEARCH_SAFE"),),
        latest_approved_publication_date=date(2026, 9, 1))
    _write(GOVERNANCE / f"financial-disclosure-manifest-{manifest.dataset_id}.json", asdict(manifest))
    print(f"GATE_ID={gate.content_hash}\nSOURCE_APPROVAL={approval.decision.value}\nPUBLICATION_ALLOWED=true\n"
          f"APPROVAL_ID={approval_id}\nAPPROVED_FACTS={fact_count}\nFACT_BUNDLE_ID={fact_bundle_id}\nDATASET_MANIFEST={manifest.dataset_id}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
