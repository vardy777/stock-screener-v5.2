from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402


def latest(directory, prefix):
    path = max(directory.glob(f"{prefix}-*.json"), key=lambda item: item.stat().st_mtime)
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    governance = ROOT / "data" / "phase_1b2a" / "governance"
    independent = latest(governance, "baostock-status-evidence")
    recovery = latest(governance, "status-evidence-recovery")
    master = {}
    master_evidence = {}
    for path in (ROOT / "data" / "phase_1b1" / "raw" / "datahubco_tushare_proxy" / "security_master").rglob("*.json"):
        artifact = json.loads(path.read_text(encoding="utf-8"))
        for row in artifact["provider_payload"]["rows"]:
            master[row["ts_code"]] = row
            master_evidence[row["ts_code"]] = artifact["payload_hash"]
    coverage = []
    for item in independent["observations"]:
        if item["resolution"] != "INDEPENDENT_EVIDENCE_UNAVAILABLE":
            continue
        row = master[item["security_identity"]]
        coverage.append({"event_id": item["event_id"], "security_identity": item["security_identity"],
            "session": item["session"], "semantic": "ordinary-status boundary",
            "attempted_sources": ({"source": independent["source_identity"], "method": independent["retrieval_method"],
                                   "evidence_id": independent["content_hash"]},),
            "unavailable_reason": f"sample session is after confirmed delist_date={row['delist_date']}; no exact-session trading record exists",
            "official_batch_record_available": False,
            "systematic_coverage_class": "frozen ordinary stratum selected later-delisted identities at a post-delisting 2025 session",
            "research_impact": "does not test ordinary active-session status; cannot support dataset-level ordinary-status equivalence",
            "input_artifact_ids": (independent["content_hash"], master_evidence[item["security_identity"]]),
            "content_hash": content_hash({"event_id": item["event_id"], "identity": item["security_identity"],
                                          "session": item["session"], "delist_date": row["delist_date"],
                                          "independent_evidence": independent["content_hash"]})})
    semantic_resolutions = (
        {"event_id": "f61a553ca2ec93dc00f9c0658e9fa9691edc8cf17ede02f412a048f3f03f84fc",
         "security_identity": "300029.SZ", "session": "20250102",
         "provider_value": "DataHub stock-st type=ST", "independent_value": "BaoStock isST=1, tradestatus=1",
         "semantic_divergence": "ordinary is a sampling stratum, not a non-ST value assertion",
         "disposition": "MAPPING_ERROR_FIXED_MATCH", "evidence_ids": (recovery["content_hash"], independent["content_hash"])},
        {"event_id": "300114-to-302132-v1", "security_identity": "302132.SZ", "session": "20250214",
         "provider_value": "frozen boundary denotes final old-code session before next-session transition",
         "independent_value": "BaoStock retrospectively labels the row 302132; SZSE notice says 300114 through T-1 and 302132 from 2025-02-17",
         "semantic_divergence": "independent daily API backfills the new identity and is unsuitable for PIT identity mapping",
         "disposition": "MAPPING_ERROR_FIXED_MATCH",
         "evidence_ids": (independent["content_hash"], "https://disc.static.szse.cn/disc/disk03/finalpage/2025-02-15/cedb693a-f5ee-4463-9682-ea33d406b569.PDF")},
    )
    pit_matrix = (
        ("listing", "PENDING", "planned/approved listing is distinct from first tradable session; frozen sample has no actual-listing case"),
        ("delisting", "PARTIAL", "five unique effective boundaries are observable, but announcement knowledge coverage is incomplete"),
        ("ST enter", "SAFE_WITH_RULE", "ten daily states observable by D close; announcement timestamp not required for D-close state"),
        ("ST exit", "SAFE_WITH_RULE", "D state may be observable by close; date-only interval end is next-session-safe until independently observed"),
        ("suspension", "SAFE_WITH_RULE", "ten full-day states independently observable by D close"),
        ("resumption", "SAFE_WITH_RULE", "actual D trading is observable by close; never infer D-1 knowledge without notice"),
        ("identity transition", "SAFE_WITH_RULE", "official effective chain prevents overlap and retrospective code backfill"),
        ("ordinary status", "PENDING", "29 cases are post-delisting and cannot validate active ordinary status"),
    )
    body = {"schema_version": "Phase1B2AEvidenceSufficiencyReviewV1", "coverage_ledger": tuple(coverage),
            "semantic_resolutions": semantic_resolutions, "pit_coverage_matrix": pit_matrix,
            "old_contract_satisfied": False, "proposed_policy_adopted": False,
            "decision": "PENDING", "publication_allowed": False}
    body["content_hash"] = content_hash(body)
    output = governance / f"status-evidence-sufficiency-review-{body['content_hash']}.json"
    output.write_bytes(canonical_json(body))
    print(json.dumps({"coverage_entries": len(coverage), "semantic_resolutions": len(semantic_resolutions),
                      "old_contract_satisfied": False, "decision": "PENDING",
                      "review_id": body["content_hash"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
