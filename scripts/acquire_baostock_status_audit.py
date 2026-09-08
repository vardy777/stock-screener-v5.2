from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402

INVENTORY_ID = "7ca99bfecd2731d5442ea62eb496afe3cff9b01a7ba32c1434a461c1a931a9c0"


def main() -> int:
    import baostock as bs
    directory = ROOT / "data" / "phase_1b2a" / "governance"
    inventory = json.loads((directory / f"status-sample-inventory-{INVENTORY_ID}.json").read_text(encoding="utf-8"))
    unique = {item["event_id"]: item for item in inventory["samples"]}
    login = bs.login()
    if login.error_code != "0":
        raise RuntimeError("independent source login failed")
    observations = []
    try:
        for sample in unique.values():
            identity, session, stratum = sample["security_identity"], sample["session"], sample["stratum"]
            prefix = "sh." if identity.endswith(".SH") else "sz."
            day = f"{session[:4]}-{session[4:6]}-{session[6:]}"
            query = bs.query_history_k_data_plus(prefix + identity[:6], "date,code,tradestatus,isST",
                                                 start_date=day, end_date=day, frequency="d", adjustflag="3")
            rows = []
            while query.error_code == "0" and query.next():
                rows.append(dict(zip(("date", "code", "tradestatus", "isST"), query.get_row_data())))
            resolution, reason = "UNRESOLVED", "semantic mapping is not sufficient"
            if not rows:
                resolution, reason = "INDEPENDENT_EVIDENCE_UNAVAILABLE", "independent source has no coverage for exact session"
            elif stratum == "st_transition" and rows[0]["isST"] == "1":
                resolution, reason = "MATCH", "independent daily isST confirms risk-warning state"
            elif stratum == "suspension_transition" and rows[0]["tradestatus"] == "0":
                resolution, reason = "MATCH", "independent daily tradestatus confirms full-day non-trading state"
            elif stratum == "listing_delisting_boundary" and rows[0]["tradestatus"] == "0":
                resolution, reason = "MATCH", "independent record confirms no trading on provider delisting effective date"
            observations.append({"event_id": sample["event_id"], "security_identity": identity, "session": session,
                "stratum": stratum, "rows": tuple(rows), "resolution": resolution, "reason": reason,
                "source_document_hash": content_hash(rows)})
    finally:
        bs.logout()
    body = {"schema_version": "IndependentStatusEvidenceV1", "inventory_id": INVENTORY_ID,
            "source_identity": f"BaoStock {getattr(bs, '__version__', '0.9.3')}",
            "retrieval_method": "query_history_k_data_plus exact security and session",
            "semantic_suitability": "tradestatus for full-day trading state; isST for daily risk-warning state",
            "independence_rationale": "separate BaoStock service and protocol from DataHub/Tushare-compatible provider",
            "observed_at": datetime.now(timezone.utc), "observations": tuple(observations)}
    body["content_hash"] = content_hash(body)
    output = directory / f"baostock-status-evidence-{body['content_hash']}.json"
    output.write_bytes(canonical_json(body))
    counts = {key: sum(item["resolution"] == key for item in observations) for key in
              ("MATCH", "MISMATCH", "UNRESOLVED", "INDEPENDENT_EVIDENCE_UNAVAILABLE")}
    print(json.dumps({"unique_events": len(observations), "counts": counts, "evidence_id": body["content_hash"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
