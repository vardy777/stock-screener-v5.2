from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.real_audits.pinned_artifacts import load_pinned_json  # noqa: E402
from v5_2.data.real_audits.status_knowledge_time import StatusPITKnowledgeTimeEvidenceV1  # noqa: E402

CONTRACT_ID = "3a9efd2f1047d9ad0432a72202bf1b8e7f926d153c339106475c37a694b20917"
INVENTORY_ID = "cef91ec0a055f01ac2f0f82ec8e15ce75f4e000acd2123a70685fb25d1df3c9c"
LEDGER_ID = "7aee446328623da71f2f0ca8ad3655399b8f7d389e4a71ea9304b075d3838cb9"
AUDIT_ID = "23fb236fd6d1fdf7e0691c3bf3bfb8db3cf5524f13bcddb510bd21fbc52e03b7"
UNIVERSE_ID = "a5ab86ff4fc0fbc84e3d5f06dbcb1bf51a123dd2e900246404b795d5e1149613"
CALENDAR_APPROVAL_ID = "1581b4d367dba1256247ddd13e09b53d0f95b5b1deeb40af9e6ed4a36606353b"
MASTER_APPROVAL_ID = "f208c17accba6b669359f476b2fdf3a1bc9ec6856e7fa1831ccdd1c42b80d8cf"


def main() -> int:
    governance = ROOT / "data" / "phase_1b2a" / "governance"
    phase_1b1 = ROOT / "data" / "phase_1b1" / "governance"
    ledger = load_pinned_json(governance / f"prospective-status-evidence-ledger-v2-{LEDGER_ID}.json",
        schema_version="ProspectiveStatusEvidenceLedgerV2", identity_field="content_hash", expected_identity=LEDGER_ID)
    inventory = load_pinned_json(governance / f"prospective-status-sample-inventory-v2-{INVENTORY_ID}.json",
        schema_version="ProspectiveStatusSampleInventoryV2", identity_field="inventory_id", expected_identity=INVENTORY_ID)
    audit = load_pinned_json(governance / f"status-audit-{AUDIT_ID}.json",
        schema_version="Phase1B2AStatusAuditV1", identity_field="evidence_id", expected_identity=AUDIT_ID)
    load_pinned_json(governance / f"historical-universe-reconciliation-{UNIVERSE_ID}.json",
        schema_version="HistoricalUniverseReconciliationV1", identity_field="content_hash", expected_identity=UNIVERSE_ID)
    for prefix, identity in (("trade_calendar-approval", CALENDAR_APPROVAL_ID),
                             ("security_master-approval", MASTER_APPROVAL_ID)):
        approval = json.loads((phase_1b1 / f"{prefix}-{identity}.json").read_text(encoding="utf-8"))
        if (approval.get("approval_id") != identity or approval.get("content_hash") != identity
                or approval.get("decision") not in {"APPROVED", "APPROVED_WITH_RULES"}):
            raise RuntimeError(f"pinned upstream approval is invalid: {prefix}")
    if len(ledger["observations"]) != 71 or any(item["resolution"] != "MATCH" for item in ledger["observations"]):
        raise RuntimeError("frozen V2 cross-source ledger is not 71/71 MATCH")
    if len(inventory["samples"]) != 71:
        raise RuntimeError("frozen V2 inventory is not 71 samples")

    rules = (
        ("ACTIVE_ORDINARY_STATUS", "MARKET_OBSERVABLE_BY_CLOSE", "actual D trading, non-ST, non-suspended, effective identity => D@16:30"),
        ("ACTUAL_FIRST_TRADABLE_SESSION", "MARKET_OBSERVABLE_BY_CLOSE", "actual first D trading => D@16:30; later documents are factual-only"),
        ("DELISTING", "NEXT_SESSION_SAFE", "unverified same-day publication => next approved session@16:30"),
        ("ST_ENTER", "MARKET_OBSERVABLE_BY_CLOSE", "actual D risk-warning state => D@16:30"),
        ("ST_EXIT", "MARKET_OBSERVABLE_BY_CLOSE", "actual D non-risk-warning state after risk warning => D@16:30"),
        ("FULL_DAY_SUSPENSION", "MARKET_OBSERVABLE_BY_CLOSE", "independently supported full-day D suspension => D@16:30"),
        ("RESUMPTION", "MARKET_OBSERVABLE_BY_CLOSE", "actual resumed D trading => D@16:30; no D-1 inference"),
        ("IDENTITY_TRANSITION", "NEXT_SESSION_SAFE", "official effective identity chain only; date-only => next approved session@16:30"),
    )
    artifact = StatusPITKnowledgeTimeEvidenceV1.create(
        policy_version="status-availability-after-close-v2", historical_cutoff="16:30:00+08:00",
        semantic_rules=rules,
        supporting_evidence_ids=(LEDGER_ID, INVENTORY_ID, AUDIT_ID, UNIVERSE_ID,
                                 CALENDAR_APPROVAL_ID, MASTER_APPROVAL_ID),
        safe_session_rules=("date-only or cutoff-unproven announcement => next approved session@16:30",
                            "historical acquisition time never becomes historical available_at"),
        contract_id=CONTRACT_ID, inventory_id=INVENTORY_ID,
        final_cross_source_evidence_id=LEDGER_ID,
        source_version_identity=content_hash(tuple(audit["raw_payload_hashes"])),
    )
    body = {"schema_version": "StatusPITKnowledgeTimeEvidenceV1", **asdict(artifact)}
    output = governance / f"status-pit-knowledge-time-{artifact.content_hash}.json"
    output.write_bytes(canonical_json(body))
    print(json.dumps({"artifact_id": artifact.content_hash, "complete": artifact.complete,
                      "covered_semantics": len(artifact.covered_semantics),
                      "cross_source_ledger_id": LEDGER_ID}, indent=2))
    return 0 if artifact.complete and artifact.verify() else 1


if __name__ == "__main__":
    raise SystemExit(main())
