from __future__ import annotations

from dataclasses import asdict, fields
from datetime import date
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.real_audits.status_exceptions import StatusExceptionBudgetV2, StatusExceptionalRecordV1  # noqa: E402


P1 = ROOT / "data" / "phase_1b1"
P2 = ROOT / "data" / "phase_1b2a"
CLASSIFICATION_ID = "23a660b27dc476a582401780603d3e7458b823951b5d54c55ef40ef71c9f127d"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def mapping(item):
    return {field.name: getattr(item, field.name) for field in fields(item)}


def main() -> int:
    classification = load(P2 / "governance" / f"missing-bar-classification-{CLASSIFICATION_ID}.json")
    master = {}
    for path in (P1 / "raw" / "datahubco_tushare_proxy" / "security_master").rglob("*.json"):
        for row in load(path)["provider_payload"]["rows"]:
            master[row["ts_code"]] = row
    budget = StatusExceptionBudgetV2.default()
    inputs = []
    exceptions = []
    for item in classification["items"]:
        if item["category"] != "UNEXPLAINED":
            continue
        symbol, session = item["security_identity"], item["session"]
        row = master.get(symbol, {})
        listed = row.get("list_date")
        delisted = row.get("delist_date")
        interval_known = bool(listed and listed <= session and (not delisted or session <= delisted))
        exchange = symbol[-2:]
        board = row.get("market") or "UNKNOWN"
        reason = "provider suspension semantic gap"
        evidence = (CLASSIFICATION_ID,)
        if symbol == "688766.SH":
            reason = "special merger suspension absent from provider daily coverage"
            evidence = (CLASSIFICATION_ID, "sse-688766-2025-merger-suspension")
        inputs.append({
            "security_identity": symbol, "session": session, "exchange": exchange,
            "year": int(session[:4]), "month": f"{session[:4]}-{session[4:6]}",
            "board": board, "listing_age_days": (date.fromisoformat(f"{session[:4]}-{session[4:6]}-{session[6:]}") - date.fromisoformat(f"{listed[:4]}-{listed[4:6]}-{listed[6:]}")).days if listed else None,
            "status_source_coverage": "MISSING", "effective_interval_known": interval_known,
        })
        exceptions.append(StatusExceptionalRecordV1.create(
            security_identity=symbol,
            effective_date=date(int(session[:4]), int(session[4:6]), int(session[6:])),
            affected_fields=("suspension",), reason=reason, evidence_ids=evidence,
            disposition="QUARANTINE",
            dimensions={"exchange": exchange, "year": int(session[:4]), "month": session[:6],
                        "field": "suspension", "board": board},
            policy_version="status-exception-v2",
        ))
    result = budget.evaluate_records(inputs, applicable_symbol_sessions=2_487_799)
    body = {
        "schema_version": "StatusExceptionAuditV2", "classification_id": CLASSIFICATION_ID,
        "budget": {key: str(value) if key in {"ratio_limit", "exchange_concentration_limit"} else value
                   for key, value in asdict(budget).items()}, "result": {"passed": result.passed,
        "systematic_pattern": result.systematic_pattern, "reasons": result.reasons,
        "metrics": dict(result.metrics)}, "records": tuple(mapping(record) for record in exceptions),
        "record_count": len(exceptions), "research_excluded": True,
    }
    body["content_hash"] = content_hash(body)
    output = P2 / "governance" / f"status-exception-audit-{body['content_hash']}.json"
    output.write_bytes(canonical_json(body))
    print(json.dumps({"budget_id": budget.budget_id, "record_count": len(exceptions),
                      "passed": result.passed, "systematic_pattern": result.systematic_pattern,
                      "reasons": result.reasons, "metrics": dict(result.metrics),
                      "artifact": output.name}, indent=2))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
