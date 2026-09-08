from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.real_audits.historical_universe import (  # noqa: E402
    HistoricalUniverseReconciliationItemV1, HistoricalUniverseReconciliationV1,
    HistoricalUniverseSupplementIdentityV1, HistoricalUniverseSupplementV1,
)
from v5_2.data.real_audits.status_official_samples import (  # noqa: E402
    OfficialStatusSampleEntryV1, OfficialStatusSampleLedgerV1,
)
from v5_2.data.real_audits.status_validation import evaluate_status_gates  # noqa: E402
from v5_2.data.real_audits.pinned_artifacts import load_pinned_json  # noqa: E402

INVENTORY_ID = "cef91ec0a055f01ac2f0f82ec8e15ce75f4e000acd2123a70685fb25d1df3c9c"
LEDGER_ID = "d5c80b3e38a4d459dba53eab37cccecfecffad3bbdea95511140c71be7315e99"
UNIVERSE_ID = "a5ab86ff4fc0fbc84e3d5f06dbcb1bf51a123dd2e900246404b795d5e1149613"
EXCEPTION_ID = "5e54d212b5f67b5a7d450698c72a71cebae1aa143cb173cb81883528f51f381d"
AUDIT_ID = "23fb236fd6d1fdf7e0691c3bf3bfb8db3cf5524f13bcddb510bd21fbc52e03b7"


def latest(directory: Path, prefix: str):
    path = max(directory.glob(f"{prefix}-*.json"), key=lambda value: value.stat().st_mtime)
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    directory = ROOT / "data" / "phase_1b2a" / "governance"
    prospective = load_pinned_json(directory / f"prospective-status-evidence-ledger-v2-{LEDGER_ID}.json",
        schema_version="ProspectiveStatusEvidenceLedgerV2", identity_field="content_hash", expected_identity=LEDGER_ID)
    inventory = load_pinned_json(directory / f"prospective-status-sample-inventory-v2-{INVENTORY_ID}.json",
        schema_version="ProspectiveStatusSampleInventoryV2", identity_field="inventory_id", expected_identity=INVENTORY_ID)
    observations = {item["candidate_hash"]: item for item in prospective["observations"]}
    entries = tuple(OfficialStatusSampleEntryV1(
        sample_id=item["candidate_hash"], event_id=item["candidate_hash"],
        security_identity=item["security_identity"], session=item["session"], stratum=item["semantic"],
        provider_observation=item["provider_value"],
        official_observation=str(observations[item["candidate_hash"]].get("independent_value")),
        official_evidence_id=(observations[item["candidate_hash"]].get("official_anchor_evidence_id")
                              or observations[item["candidate_hash"]].get("source_document_hash")),
        semantic_mapping=item["semantic_assertion"],
        resolution=observations[item["candidate_hash"]]["resolution"],
    ) for item in inventory["samples"])
    counts = tuple(sorted((key, sum(entry.resolution == key for entry in entries))
                          for key in {entry.resolution for entry in entries}))
    ledger_body = {"inventory_id": inventory["inventory_id"], "entries": entries,
                   "unique_event_count": len(entries), "counts": counts,
                   "systematic_defect": any(entry.resolution == "MISMATCH" for entry in entries)}
    from v5_2.data.identity import content_hash  # noqa: E402
    ledger = OfficialStatusSampleLedgerV1(**ledger_body, content_hash=content_hash(ledger_body))
    raw_universe = load_pinned_json(directory / f"historical-universe-reconciliation-{UNIVERSE_ID}.json",
        schema_version="HistoricalUniverseReconciliationV1", identity_field="content_hash", expected_identity=UNIVERSE_ID)
    raw_supplement = raw_universe["supplement"]
    supplement = HistoricalUniverseSupplementV1(raw_supplement["original_universe_id"],
        tuple(HistoricalUniverseSupplementIdentityV1(**item) for item in raw_supplement["identities"]), raw_supplement["content_hash"])
    reconciliation = HistoricalUniverseReconciliationV1(raw_universe["original_universe_id"], raw_universe["total"],
        tuple(tuple(item) for item in raw_universe["counts"]),
        tuple(HistoricalUniverseReconciliationItemV1(**item) for item in raw_universe["items"]), supplement,
        raw_universe["content_hash"])
    audit = load_pinned_json(directory / f"status-audit-{AUDIT_ID}.json",
        schema_version="Phase1B2AStatusAuditV1", identity_field="evidence_id", expected_identity=AUDIT_ID)
    exceptions = load_pinned_json(directory / f"status-exception-audit-{EXCEPTION_ID}.json",
        schema_version="StatusExceptionAuditV2", identity_field="content_hash", expected_identity=EXCEPTION_ID)
    # No complete PIT evidence artifact exists yet; endpoint diagnostics are not promoted to PIT proof.
    revocations = tuple(json.loads(path.read_text(encoding="utf-8"))["approval_id"]
                        for path in ROOT.joinpath("data").rglob("approval-revocation-*.json"))
    registry = {"schema_version": "SourceApprovalRevocationRegistryV1",
                "revoked_approval_ids": tuple(sorted(revocations))}
    registry["content_hash"] = content_hash(registry)
    (directory / f"source-approval-revocation-registry-{registry['content_hash']}.json").write_bytes(canonical_json(registry))
    source_version = content_hash(tuple(audit["raw_payload_hashes"]))
    result = evaluate_status_gates(structural_status=audit["result"]["structural_status"], pit_evidence=None,
        official_ledger=ledger, reconciliation=reconciliation,
        exception_budget_pass=exceptions["result"]["passed"], systematic_defect=exceptions["result"]["systematic_pattern"],
        source_version_identity=source_version, revoked_artifact_ids=revocations,
        expected_inventory_id=inventory["inventory_id"])
    output = directory / "status-gate-evaluation-v2.json"
    output.write_bytes(canonical_json({"schema_version": "StatusGateEvaluationV2", **asdict(result),
                                       "input_artifact_ids": (prospective["content_hash"], inventory["inventory_id"],
                                                              ledger.content_hash, raw_universe["content_hash"],
                                                              exceptions["content_hash"], audit["evidence_id"],
                                                              registry["content_hash"])}))
    print(json.dumps(asdict(result), indent=2))
    return 0 if result.decision in {"PENDING", "REJECTED"} and not result.publication_allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
