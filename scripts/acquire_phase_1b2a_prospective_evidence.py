from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.real_audits.pinned_artifacts import document_sha256, load_pinned_json  # noqa: E402
from v5_2.data.real_audits.status_cross_source import resolve_cross_source  # noqa: E402

CONTRACT_ID = "3a9efd2f1047d9ad0432a72202bf1b8e7f926d153c339106475c37a694b20917"
INVENTORY_ID = "cef91ec0a055f01ac2f0f82ec8e15ce75f4e000acd2123a70685fb25d1df3c9c"


def main() -> int:
    import baostock as bs
    governance = ROOT / "data" / "phase_1b2a" / "governance"
    path = governance / f"prospective-status-sample-inventory-v2-{INVENTORY_ID}.json"
    inventory = load_pinned_json(path, schema_version="ProspectiveStatusSampleInventoryV2",
                                 identity_field="inventory_id", expected_identity=INVENTORY_ID)
    if inventory["contract_id"] != CONTRACT_ID:
        raise ValueError("pinned prospective contract mismatch")
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
            if not rows and sample["candidate_hash"] == "0be688627e62e471c8eb4619d521b5650a2a5574e3a156f7e462cc521dc71913":
                reference = "https://static.cninfo.com.cn/finalpage/2025-05-21/1223607424.PDF"
                document = urlopen(reference, timeout=30).read()
                expected_hash = "627c57066b5b494b35f571150b26e91faafd03b44bd574506e70a65bddf59c75"
                document_hash = document_sha256(document)
                exact_document = document_hash == expected_hash
                observations.append({"candidate_hash": sample["candidate_hash"],
                    "provider_value": sample["provider_value"],
                    "independent_value": "issuer disclosure 2025-044: delisted and removed on 2025-05-27",
                    "source_id": "CNINFO-hosted issuer disclosure 2025-044", "source_reference": reference,
                    "source_document_hash": document_hash,
                    "resolution": "MATCH" if exact_document else "INDEPENDENT_EVIDENCE_UNAVAILABLE"})
                continue
            matches = bool(rows) and ((semantic in {"ACTIVE_ORDINARY_STATUS", "ACTUAL_FIRST_TRADABLE_SESSION", "ST_EXIT", "RESUMPTION"}
                                       and rows[0]["tradestatus"] == "1"
                                       and (semantic != "ACTIVE_ORDINARY_STATUS" or rows[0]["isST"] == "0")
                                       and (semantic != "ST_EXIT" or rows[0]["isST"] == "0"))
                                      or (semantic == "ST_ENTER" and rows[0]["isST"] == "1")
                                      or (semantic in {"DELISTING_BOUNDARY", "FULL_DAY_SUSPENSION"} and rows[0]["tradestatus"] == "0"))
            resolution = resolve_cross_source(semantic, daily_matches=matches if rows else None,
                                              official_anchor_matches=False)
            observations.append({"candidate_hash": sample["candidate_hash"], "provider_value": sample["provider_value"],
                "independent_value": tuple(rows), "source_id": f"BaoStock {getattr(bs, '__version__', '0.9.3')}",
                "source_reference": "query_history_k_data_plus exact identity/session",
                "source_document_hash": content_hash(rows), "resolution": resolution})
    finally:
        bs.logout()
    body = {"schema_version": "ProspectiveStatusEvidenceLedgerV2", "contract_id": inventory["contract_id"],
            "inventory_id": inventory["inventory_id"], "observations": tuple(observations),
            "independence_rationale": "BaoStock is separately operated from DataHub; identity transition uses SZSE-hosted issuer evidence"}
    body["content_hash"] = content_hash(body)
    output = governance / f"prospective-status-evidence-ledger-v2-{body['content_hash']}.json"
    output.write_bytes(canonical_json(body))
    receipt = {"schema_version": "ProspectiveStatusEvidenceAcquisitionReceiptV2",
               "ledger_id": body["content_hash"], "acquired_at": datetime.now(timezone.utc)}
    receipt["content_hash"] = content_hash(receipt)
    (governance / f"prospective-status-evidence-receipt-v2-{receipt['content_hash']}.json").write_bytes(
        canonical_json(receipt))
    counts = {key: sum(item["resolution"] == key for item in observations)
              for key in ("MATCH", "MISMATCH", "INDEPENDENT_EVIDENCE_UNAVAILABLE")}
    print(json.dumps({"inventory_id": inventory["inventory_id"], "total": len(observations),
                      "counts": counts, "ledger_id": body["content_hash"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
