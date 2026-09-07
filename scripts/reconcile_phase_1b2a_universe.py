from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.real_audits.historical_universe import reconcile_historical_universe  # noqa: E402


P1 = ROOT / "data" / "phase_1b1"
P2 = ROOT / "data" / "phase_1b2a"
UNIVERSE_ID = "2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    universe = load(P1 / "governance" / f"daily-bar-universe-{UNIVERSE_ID}.json")
    master = {}
    for path in (P1 / "raw" / "datahubco_tushare_proxy" / "security_master").rglob("*.json"):
        for row in load(path)["provider_payload"]["rows"]:
            master[row["ts_code"]] = row
    observed = set()
    observations = {}
    for kind in ("risk_warning_history", "suspension_history"):
        for path in (P2 / "raw" / "datahubco_tushare_proxy" / kind).rglob("*.json"):
            artifact = load(path)
            for row in artifact["provider_payload"]["rows"]:
                symbol = row["ts_code"]
                observed.add(symbol)
                event_date = row.get("trade_date") or row.get("start_date") or row.get("ann_date")
                slot = observations.setdefault(symbol, {"dates": [], "evidence": set()})
                if event_date:
                    slot["dates"].append(event_date)
                slot["evidence"].add(artifact["payload_hash"])
    overrides = {}
    for symbol in observed:
        if symbol.endswith(".BJ") or symbol.startswith("X"):
            slot = observations[symbol]
            overrides[symbol] = {
                "category": "NON_TARGET" if symbol.endswith(".BJ") else "LEGACY_CODE",
                "effective_from": min(slot["dates"]) if slot["dates"] else None,
                "effective_to": max(slot["dates"]) if slot["dates"] else None,
                "evidence_ids": tuple(sorted(slot["evidence"])),
                "research_scope_impact": ("BSE identity excluded from frozen SSE/SZSE A-share research scope"
                                          if symbol.endswith(".BJ") else
                                          "non-canonical temporary exchange identity excluded from target A-share universe"),
            }
    result = reconcile_historical_universe(
        observed_symbols=tuple(observed), original_symbols=tuple(universe["ordered_symbols"]),
        master_rows=master, aliases={"302132.SZ": "300114.SZ"},
        coverage_start="20100104", coverage_end="20251231", original_universe_id=UNIVERSE_ID,
        official_evidence={
            "600747.SH": ("https://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20191018_4929400.shtml",),
        },
        resolution_overrides=overrides,
    )
    body = asdict(result)
    body["schema_version"] = "HistoricalUniverseReconciliationV1"
    output = P2 / "governance" / f"historical-universe-reconciliation-{result.content_hash}.json"
    output.write_bytes(canonical_json(body))
    supplement = P2 / "governance" / f"historical-universe-supplement-{result.supplement.content_hash}.json"
    supplement.write_bytes(canonical_json(asdict(result.supplement)))
    print(json.dumps({"total": result.total, "counts": dict(result.counts),
                      "supplement_count": len(result.supplement.identities),
                      "supplement_identities": [item.security_identity for item in result.supplement.identities],
                      "reconciliation_id": result.content_hash,
                      "supplement_id": result.supplement.content_hash}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
