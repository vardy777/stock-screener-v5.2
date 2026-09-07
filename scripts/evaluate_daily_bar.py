from __future__ import annotations

from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sys


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
COVERAGE_START = "20240101"
COVERAGE_END = "20251231"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def decimal(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def security_intervals():
    intervals = {}
    root = RUNTIME / "raw" / "datahubco_tushare_proxy" / "security_master"
    for path in root.rglob("*.json"):
        for row in load(path)["provider_payload"]["rows"]:
            start = row.get("list_date") or "99999999"
            end = row.get("delist_date") or "99999999"
            current = intervals.get(row["ts_code"])
            candidate = (start, end)
            if current is None or candidate < current:
                intervals[row["ts_code"]] = candidate
    intervals["300114.SZ"] = ("20100827", "20250216")
    intervals["302132.SZ"] = ("20250217", "99999999")
    return intervals


def main() -> int:
    universe = load(GOVERNANCE / f"daily-bar-universe-{UNIVERSE_ID}.json")
    inventory = load(GOVERNANCE / f"daily-bar-request-inventory-{INVENTORY_ID}.json")
    plan = build_acquisition_plan(universe, inventory, active_approval_ids=UPSTREAM, revoked_approval_ids=())
    symbol_by_request = {
        item.provider_request.request_id: str(item.provider_request.parameters["ts_code"])
        for item in plan.requests
    }
    approved_sessions = set(universe["ordered_sessions"])
    research_sessions = tuple(s for s in universe["ordered_sessions"] if COVERAGE_START <= s <= COVERAGE_END)
    intervals = security_intervals()
    counters = Counter()
    symbols_with_data = set()
    observed_by_symbol = Counter()
    payload_hashes = []
    extrema = {"high_volatility": None, "limit_like": None, "zero_volume": None,
               "holiday_adjacent": None, "normal": None, "ipo_boundary": None,
               "delisting_boundary": None, "identity_transition": None}

    raw_root = RUNTIME / "raw" / "datahubco_tushare_proxy" / "daily_bar"
    for path in raw_root.rglob("*.json"):
        artifact = load(path)
        request_symbol = symbol_by_request.get(artifact.get("request_id"))
        payload_hashes.append(artifact["payload_hash"])
        metadata = artifact.get("semantic_metadata", {})
        if metadata.get("has_more") is not False:
            counters["nonterminal_pages"] += 1
        seen = set()
        for row in artifact["provider_payload"]["rows"]:
            counters["rows"] += 1
            required = ("ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount")
            if any(key not in row for key in required):
                counters["schema"] += 1
                continue
            symbol, session = str(row["ts_code"]), str(row["trade_date"])
            if symbol != request_symbol:
                counters["request_identity"] += 1
            key = (symbol, session)
            if key in seen:
                counters["duplicate"] += 1
            seen.add(key)
            if session not in approved_sessions:
                counters["session"] += 1
            values = [decimal(row[k]) for k in ("open", "high", "low", "close", "vol", "amount")]
            if any(v is None for v in values):
                counters["numeric"] += 1
                continue
            op, high, low, close, vol, amount = values
            if min(op, high, low, close) <= 0 or high < max(op, close, low) or low > min(op, close):
                counters["ohlc"] += 1
            if vol < 0 or amount < 0:
                counters["negative"] += 1
            start, end = intervals.get(symbol, ("99999999", "00000000"))
            known_transition_alias = symbol == "302132.SZ" and session < "20250217"
            if not known_transition_alias and not (start <= session <= end):
                counters["effective_identity"] += 1
            if COVERAGE_START <= session <= COVERAGE_END:
                effective_symbol = "300114.SZ" if symbol == "302132.SZ" and session < "20250217" else symbol
                symbols_with_data.add(effective_symbol)
                observed_by_symbol[effective_symbol] += 1
                record = {k: row[k] for k in required}
                record["sample_hash"] = content_hash(record)
                change = abs(close / op - 1) if op else Decimal(0)
                if extrema["normal"] is None or record["sample_hash"] < extrema["normal"]["sample_hash"]:
                    extrema["normal"] = record
                if extrema["high_volatility"] is None or change > Decimal(str(extrema["high_volatility"]["score"])):
                    extrema["high_volatility"] = {**record, "score": str(change)}
                limit_score = abs(change - Decimal("0.10"))
                if extrema["limit_like"] is None or limit_score < Decimal(str(extrema["limit_like"]["score"])):
                    extrema["limit_like"] = {**record, "score": str(limit_score)}
                if vol == 0 and (extrema["zero_volume"] is None or record["sample_hash"] < extrema["zero_volume"]["sample_hash"]):
                    extrema["zero_volume"] = record
                if session == start and extrema["ipo_boundary"] is None:
                    extrema["ipo_boundary"] = record
                if session == end and end != "99999999" and extrema["delisting_boundary"] is None:
                    extrema["delisting_boundary"] = record
                if symbol in {"300114.SZ", "302132.SZ"} and session in {"20250214", "20250217"}:
                    extrema["identity_transition"] = record
                if symbol == "000001.SZ" and session in {"20240208", "20240219"}:
                    previous = extrema["holiday_adjacent"]
                    rows = [] if previous is None else list(previous["rows"])
                    rows.append(record)
                    extrema["holiday_adjacent"] = {"rows": rows}
                if end != "99999999" and session <= end:
                    previous = extrema["delisting_boundary"]
                    distance = int(end) - int(session)
                    if previous is None or distance < previous["distance"]:
                        extrema["delisting_boundary"] = {**record, "distance": distance}

    expected = 0
    missing = 0
    missing_by_exchange = Counter()
    excess_by_symbol = {}
    effective_symbols = tuple(universe["ordered_symbols"]) + (() if "300114.SZ" in universe["ordered_symbols"] else ("300114.SZ",))
    for symbol in effective_symbols:
        start, end = intervals.get(symbol, ("99999999", "00000000"))
        applicable = sum(start <= session <= end for session in research_sessions)
        expected += applicable
        delta = max(0, applicable - observed_by_symbol[symbol])
        if observed_by_symbol[symbol] > applicable:
            excess_by_symbol[symbol] = observed_by_symbol[symbol] - applicable
        missing += delta
        missing_by_exchange[symbol[-2:]] += delta
    checkpoint_count = len(tuple((RUNTIME / "checkpoints").glob("*.json")))
    receipt_count = len(tuple((RUNTIME / "receipts").rglob("*.json")))
    result = {
        "schema_version": "DailyBarOfflineAuditV1",
        "universe_id": UNIVERSE_ID,
        "request_inventory_id": INVENTORY_ID,
        "plan_id": plan.plan_id,
        "upstream_approval_ids": UPSTREAM,
        "expected_request_count": len(plan.requests),
        "completed_request_count": len(payload_hashes),
        "page_count": len(payload_hashes),
        "checkpoint_count": checkpoint_count,
        "receipt_count": receipt_count,
        "row_count": counters["rows"],
        "symbol_count": len(symbols_with_data),
        "requested_symbol_count": len(universe["ordered_symbols"]),
        "effective_identity_count": len(effective_symbols),
        "requested_session_count": len(research_sessions),
        "coverage_start": COVERAGE_START,
        "coverage_end": COVERAGE_END,
        "applicable_symbol_sessions": expected,
        "observed_symbol_sessions": expected - missing,
        "missing_symbol_sessions": missing,
        "coverage_ratio": (expected - missing) / expected,
        "missing_by_exchange": dict(sorted(missing_by_exchange.items())),
        "excess_by_symbol": excess_by_symbol,
        "findings": dict(sorted(counters.items())),
        "payload_hashes": sorted(payload_hashes),
        "samples": extrema,
    }
    result["content_hash"] = content_hash(result)
    output = GOVERNANCE / f"daily-bar-offline-audit-{result['content_hash']}.json"
    output.write_bytes(canonical_json(result))
    print(json.dumps({k: v for k, v in result.items() if k not in {"payload_hashes", "samples"}}, indent=2))
    print(f"ARTIFACT={output.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
