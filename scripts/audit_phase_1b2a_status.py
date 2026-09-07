from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from phase_1b2a_acquire import PHASE_1B1, RUNTIME, UNIVERSE_ID, _load_inventory  # noqa: E402
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.real_audits.status_sampling import StatusSampleCandidateV1, select_status_samples  # noqa: E402
from v5_2.data.real_audits.status_validation import validate_status_observations  # noqa: E402


def _raw_rows(root: Path, dataset_kind: str):
    rows = []
    hashes = []
    for path in sorted(root.joinpath("raw", "datahubco_tushare_proxy", dataset_kind).rglob("*.json")):
        artifact = json.loads(path.read_text(encoding="utf-8"))
        hashes.append(artifact["payload_hash"])
        rows.extend(artifact["provider_payload"]["rows"])
    return tuple(rows), tuple(sorted(hashes))


def _candidate(row, stratum, event_fields, later_delisted):
    session = next(str(row.get(field)) for field in event_fields if row.get(field))
    identity = str(row["ts_code"])
    return StatusSampleCandidateV1(
        identity, session, stratum,
        content_hash({"stratum": stratum, "row": row}),
        identity in later_delisted,
    )


def main() -> int:
    universe = json.loads((PHASE_1B1 / "governance" / f"daily-bar-universe-{UNIVERSE_ID}.json").read_text(encoding="utf-8"))
    inventory, _ = _load_inventory()
    names, name_hashes = _raw_rows(RUNTIME, "risk_warning_history")
    suspensions, suspension_hashes = _raw_rows(RUNTIME, "suspension_history")
    masters, _ = _raw_rows(PHASE_1B1, "security_master")
    later_delisted = {
        str(row["ts_code"]) for row in masters
        if row.get("delist_date") or row.get("list_status") == "D"
    }

    ordinary = [
        StatusSampleCandidateV1(symbol, "20250102", "ordinary", content_hash({"symbol": symbol, "session": "20250102"}), symbol in later_delisted)
        for symbol in universe["ordered_symbols"]
    ]
    st = [_candidate(row, "st_transition", ("start_date",), later_delisted) for row in names if "ST" in str(row.get("name", "")).upper()]
    suspension = [_candidate(row, "suspension_transition", ("trade_date",), later_delisted) for row in suspensions if row.get("suspend_type") == "S"]
    boundaries = [_candidate(row, "listing_delisting_boundary", ("delist_date", "list_date"), later_delisted) for row in masters if row.get("delist_date") or row.get("list_date")]
    samples = select_status_samples(
        {"ordinary": ordinary, "st_transition": st, "suspension_transition": suspension,
         "listing_delisting_boundary": boundaries},
        identity_transition=("302132.SZ", "20250214", "300114-to-302132-v1"),
    )
    governance = RUNTIME / "governance"
    sample_path = governance / f"status-sample-inventory-{samples.inventory_id}.json"
    sample_path.write_bytes(canonical_json(asdict(samples)))

    result = validate_status_observations(
        namechange_rows=names,
        suspension_rows=suspensions,
        universe_symbols=universe["ordered_symbols"],
        coverage_start=inventory.coverage_start,
        coverage_end=inventory.coverage_end,
        later_delisted_symbols=tuple(sorted(later_delisted)),
        official_sample_matches=(),
    )
    body = {
        "schema_version": "Phase1B2AStatusAuditV1",
        "inventory_id": inventory.inventory_id,
        "sample_inventory_id": samples.inventory_id,
        "raw_payload_hashes": (*name_hashes, *suspension_hashes),
        "result": asdict(result),
        "provider_semantics": {
            "suspend_d": "daily observations; S covers each suspended date; R is resumption",
            "reference": "https://tushare.pro/document/2?doc_id=214",
        },
        "pit_findings": [
            "ann_date and trade_date contain dates without verified publication timestamps",
            "same-date D-close availability is fail-closed; acquisition time is ignored",
        ],
        "cross_source_findings": ["frozen 61-case inventory created", "official SSE/SZSE comparison not completed"],
        "decision": result.decision,
        "verified_at": datetime(2026, 9, 7, 6, 30, tzinfo=timezone.utc),
    }
    body["content_hash"] = content_hash(body)
    body["evidence_id"] = body["content_hash"]
    output = governance / f"status-audit-{body['evidence_id']}.json"
    output.write_bytes(canonical_json(body))
    print(json.dumps({**asdict(result), "sample_inventory_id": samples.inventory_id,
                      "evidence_id": body["evidence_id"]}, indent=2))
    print(f"SAMPLE_ARTIFACT={sample_path.name}")
    print(f"AUDIT_ARTIFACT={output.name}")
    return 0 if result.decision != "REJECTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
