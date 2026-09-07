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


def latest(directory: Path, prefix: str):
    path = max(directory.glob(f"{prefix}-*.json"), key=lambda value: value.stat().st_mtime)
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    directory = ROOT / "data" / "phase_1b2a" / "governance"
    raw_ledger = latest(directory, "status-official-sample-ledger")
    ledger = OfficialStatusSampleLedgerV1(raw_ledger["inventory_id"],
        tuple(OfficialStatusSampleEntryV1(**item) for item in raw_ledger["entries"]), raw_ledger["unique_event_count"],
        tuple(tuple(item) for item in raw_ledger["counts"]), raw_ledger["systematic_defect"], raw_ledger["content_hash"])
    raw_universe = latest(directory, "historical-universe-reconciliation")
    raw_supplement = raw_universe["supplement"]
    supplement = HistoricalUniverseSupplementV1(raw_supplement["original_universe_id"],
        tuple(HistoricalUniverseSupplementIdentityV1(**item) for item in raw_supplement["identities"]), raw_supplement["content_hash"])
    reconciliation = HistoricalUniverseReconciliationV1(raw_universe["original_universe_id"], raw_universe["total"],
        tuple(tuple(item) for item in raw_universe["counts"]),
        tuple(HistoricalUniverseReconciliationItemV1(**item) for item in raw_universe["items"]), supplement,
        raw_universe["content_hash"])
    audit = latest(directory, "status-audit")
    exceptions = latest(directory, "status-exception-audit")
    # No complete PIT evidence artifact exists yet; endpoint diagnostics are not promoted to PIT proof.
    result = evaluate_status_gates(structural_status=audit["result"]["structural_status"], pit_evidence=None,
        official_ledger=ledger, reconciliation=reconciliation,
        exception_budget_pass=exceptions["result"]["passed"], systematic_defect=exceptions["result"]["systematic_pattern"],
        source_version_identity="not-applicable-without-pit-artifact", revoked_artifact_ids=(),
        expected_inventory_id=raw_ledger["inventory_id"])
    output = directory / "status-gate-evaluation-v2.json"
    output.write_bytes(canonical_json({"schema_version": "StatusGateEvaluationV2", **asdict(result),
                                       "input_artifact_ids": (raw_ledger["content_hash"], raw_universe["content_hash"],
                                                              exceptions["content_hash"], audit["evidence_id"])}))
    print(json.dumps(asdict(result), indent=2))
    return 0 if result.decision in {"PENDING", "REJECTED"} and not result.publication_allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
