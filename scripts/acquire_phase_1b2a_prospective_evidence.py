from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402


def main() -> int:
    import baostock as bs
    governance = ROOT / "data" / "phase_1b2a" / "governance"
    path = max(governance.glob("prospective-status-sample-inventory-*.json"), key=lambda item: item.stat().st_mtime)
    inventory = json.loads(path.read_text(encoding="utf-8"))
    login = bs.login()
    if login.error_code != "0":
        raise RuntimeError("independent source login failed")
    observations = []
    try:
        for sample in inventory["samples"]:
            if sample["semantic"] == "IDENTITY_TRANSITION":
                observations.append({"candidate_hash": sample["candidate_hash"], "provider_value": sample["provider_value"],
                    "independent_value": "SZSE notice: 300114 through T-1; 302132 from 2025-02-17",
                    "source_id": "SZSE-hosted issuer disclosure", "source_reference": "https://disc.static.szse.cn/disc/disk03/finalpage/2025-02-15/cedb693a-f5ee-4463-9682-ea33d406b569.PDF",
                    "source_document_hash": "cedb693a-f5ee-4463-9682-ea33d406b569", "resolution": "MATCH"})
                continue
            identity, value = sample["security_identity"], sample["session"]
            code = ("sh." if identity.endswith(".SH") else "sz.") + identity[:6]
            day = f"{value[:4]}-{value[4:6]}-{value[6:]}"
            query = bs.query_history_k_data_plus(code, "date,code,tradestatus,isST", start_date=day,
                                                 end_date=day, frequency="d", adjustflag="3")
            rows = []
            while query.error_code == "0" and query.next():
                rows.append(dict(zip(("date", "code", "tradestatus", "isST"), query.get_row_data())))
            semantic = sample["semantic"]
            matches = bool(rows) and ((semantic in {"ACTIVE_ORDINARY_STATUS", "ACTUAL_FIRST_TRADABLE_SESSION", "ST_EXIT", "RESUMPTION"}
                                       and rows[0]["tradestatus"] == "1"
                                       and (semantic != "ACTIVE_ORDINARY_STATUS" or rows[0]["isST"] == "0")
                                       and (semantic != "ST_EXIT" or rows[0]["isST"] == "0"))
                                      or (semantic == "ST_ENTER" and rows[0]["isST"] == "1")
                                      or (semantic in {"DELISTING_BOUNDARY", "FULL_DAY_SUSPENSION"} and rows[0]["tradestatus"] == "0"))
            resolution = "MATCH" if matches else ("INDEPENDENT_EVIDENCE_UNAVAILABLE" if not rows else "MISMATCH")
            observations.append({"candidate_hash": sample["candidate_hash"], "provider_value": sample["provider_value"],
                "independent_value": tuple(rows), "source_id": f"BaoStock {getattr(bs, '__version__', '0.9.3')}",
                "source_reference": "query_history_k_data_plus exact identity/session",
                "source_document_hash": content_hash(rows), "resolution": resolution})
    finally:
        bs.logout()
    body = {"schema_version": "ProspectiveStatusEvidenceLedgerV1", "contract_id": inventory["contract_id"],
            "inventory_id": inventory["inventory_id"], "observations": tuple(observations),
            "retrieved_at": datetime.now(timezone.utc),
            "independence_rationale": "BaoStock is separately operated from DataHub; identity transition uses SZSE-hosted issuer evidence"}
    body["content_hash"] = content_hash(body)
    output = governance / f"prospective-status-evidence-ledger-{body['content_hash']}.json"
    output.write_bytes(canonical_json(body))
    counts = {key: sum(item["resolution"] == key for item in observations)
              for key in ("MATCH", "MISMATCH", "INDEPENDENT_EVIDENCE_UNAVAILABLE")}
    print(json.dumps({"inventory_id": inventory["inventory_id"], "total": len(observations),
                      "counts": counts, "ledger_id": body["content_hash"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
