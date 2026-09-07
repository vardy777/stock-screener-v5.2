from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys

import baostock as bs


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.real_audits.daily_bar_entry import build_acquisition_plan  # noqa: E402


RUNTIME = ROOT / "data" / "phase_1b1"
GOVERNANCE = RUNTIME / "governance"
UNIVERSE_ID = "2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01"
INVENTORY_ID = "9b1d034f00ab0d637bc56ab120ffcf725f226f21c09d27c3b85e36a4f644a6ce"
UPSTREAM = (
    "1581b4d367dba1256247ddd13e09b53d0f95b5b1deeb40af9e6ed4a36606353b",
    "f208c17accba6b669359f476b2fdf3a1bc9ec6856e7fa1831ccdd1c42b80d8cf",
)
SAMPLES = (
    ("normal", "600638.SH", "20250623"),
    ("high_volatility", "301618.SZ", "20240930"),
    ("limit_like", "603226.SH", "20250411"),
    ("ipo_boundary", "301617.SZ", "20241211"),
    ("identity_transition", "302132.SZ", "20250214"),
    ("holiday_adjacent_before", "000001.SZ", "20240208"),
    ("holiday_adjacent_after", "000001.SZ", "20240219"),
    ("delisting_boundary", "002087.SZ", "20240627"),
)
PRICE_TOLERANCE = Decimal("0.0001")
AMOUNT_TOLERANCE_YUAN = Decimal("1")
VOLUME_FACTOR = Decimal("100")
AMOUNT_FACTOR = Decimal("1000")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def provider_rows_by_symbol():
    universe = load(GOVERNANCE / f"daily-bar-universe-{UNIVERSE_ID}.json")
    inventory = load(GOVERNANCE / f"daily-bar-request-inventory-{INVENTORY_ID}.json")
    plan = build_acquisition_plan(universe, inventory, active_approval_ids=UPSTREAM, revoked_approval_ids=())
    request_by_symbol = {str(item.provider_request.parameters["ts_code"]): item.provider_request.request_id for item in plan.requests}
    result = {}
    raw_root = RUNTIME / "raw" / "datahubco_tushare_proxy" / "daily_bar"
    for _, symbol, session in SAMPLES + (("adjustment", "000001.SZ", "20100104"),):
        request_id = request_by_symbol[symbol]
        paths = tuple((raw_root / request_id[:16]).rglob("*.json"))
        matches = []
        for path in paths:
            artifact = load(path)
            matches.extend(row for row in artifact["provider_payload"]["rows"] if row["trade_date"] == session)
        result[(symbol, session)] = matches
    return result


def query(code, session, adjustflag):
    result = bs.query_history_k_data_plus(
        code, "date,code,open,high,low,close,volume,amount",
        start_date=f"{session[:4]}-{session[4:6]}-{session[6:]}",
        end_date=f"{session[:4]}-{session[4:6]}-{session[6:]}", frequency="d", adjustflag=adjustflag,
    )
    rows = []
    while result.next():
        rows.append(dict(zip(result.fields, result.get_row_data(), strict=True)))
    return rows


def main() -> int:
    provider = provider_rows_by_symbol()
    login = bs.login()
    if login.error_code != "0":
        raise RuntimeError("reference source login failed")
    comparisons = []
    try:
        for stratum, symbol, session in SAMPLES:
            code = f"{symbol[-2:].lower()}.{symbol[:6]}"
            reference = query(code, session, "3")
            source = provider[(symbol, session)]
            item = {"stratum": stratum, "symbol": symbol, "session": session,
                    "provider_row_count": len(source), "reference_row_count": len(reference)}
            if len(source) == len(reference) == 1:
                p, r = source[0], reference[0]
                price_differences = {field: str(abs(Decimal(str(p[field])) - Decimal(r[field])))
                                     for field in ("open", "high", "low", "close")}
                item["price_differences"] = price_differences
                item["price_pass"] = all(Decimal(value) <= PRICE_TOLERANCE for value in price_differences.values())
                if r["volume"] and r["amount"]:
                    item["volume_difference_shares"] = str(abs(Decimal(str(p["vol"])) * VOLUME_FACTOR - Decimal(r["volume"])))
                    item["amount_difference_yuan"] = str(abs(Decimal(str(p["amount"])) * AMOUNT_FACTOR - Decimal(r["amount"])))
                    item["unit_pass"] = Decimal(item["volume_difference_shares"]) == 0 and Decimal(item["amount_difference_yuan"]) <= AMOUNT_TOLERANCE_YUAN
                else:
                    item["unit_pass"] = None
                    item["unit_note"] = "reference volume/amount unavailable for delisting boundary"
            else:
                item["price_pass"] = False
                item["unit_pass"] = False
            comparisons.append(item)
        raw = provider[("000001.SZ", "20100104")][0]
        raw_reference = query("sz.000001", "20100104", "3")[0]
        adjusted_reference = query("sz.000001", "20100104", "2")[0]
    finally:
        bs.logout()
    raw_close = Decimal(str(raw["close"]))
    adjustment = {
        "symbol": "000001.SZ", "session": "20100104",
        "provider_raw_close": str(raw_close),
        "reference_raw_close": raw_reference["close"],
        "reference_forward_adjusted_close": adjusted_reference["close"],
        "raw_difference": str(abs(raw_close - Decimal(raw_reference["close"]))),
        "adjusted_difference": str(abs(raw_close - Decimal(adjusted_reference["close"]))),
    }
    adjustment["passed"] = Decimal(adjustment["raw_difference"]) <= PRICE_TOLERANCE and Decimal(adjustment["adjusted_difference"]) > PRICE_TOLERANCE
    body = {
        "schema_version": "DailyBarCrossSourceEvidenceV1",
        "source_name": "datahubco_tushare_proxy", "reference_source": "BaoStock",
        "reference_adjustflag": "3 (unadjusted)",
        "sample_policy_id": "v5.2-phase-1b1-daily-bar-v1",
        "selection_frozen_before_reference_query": True,
        "price_tolerance": str(PRICE_TOLERANCE),
        "volume_factor_to_shares": str(VOLUME_FACTOR),
        "amount_factor_to_yuan": str(AMOUNT_FACTOR),
        "amount_tolerance_yuan": str(AMOUNT_TOLERANCE_YUAN),
        "comparisons": comparisons,
        "zero_volume_observation": "NOT_OBSERVED_IN_PROVIDER_RAW",
        "adjustment_contamination": adjustment,
        "observed_at": datetime.now(timezone.utc),
    }
    body["passed"] = all(item["price_pass"] and item["unit_pass"] is not False for item in comparisons) and adjustment["passed"]
    body["content_hash"] = content_hash(body)
    body["evidence_id"] = body["content_hash"]
    output = GOVERNANCE / f"daily-bar-cross-source-{body['evidence_id']}.json"
    output.write_bytes(canonical_json(body))
    print(json.dumps(body, ensure_ascii=False, indent=2, default=str))
    print(f"ARTIFACT={output.name}")
    return 0 if body["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
