from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402

RUNTIME = ROOT / "data" / "phase_1b2d"

# Fixed before comparison with any independent value.  Each tuple is
# (dataset kind, metric, exchange, report type, period era).
STRATA = (
    ("financial_income", "revenue", "SH", "4", "EARLY"),
    ("financial_income", "n_income_attr_p", "SZ", "1", "EARLY"),
    ("financial_balance_sheet", "total_assets", "SZ", "2", "EARLY"),
    ("financial_cash_flow", "n_cashflow_act", "SH", "3", "EARLY"),
    ("financial_income", "revenue", "SZ", "2", "MIDDLE"),
    ("financial_income", "n_income_attr_p", "SH", "3", "MIDDLE"),
    ("financial_balance_sheet", "total_liab", "SH", "4", "MIDDLE"),
    ("financial_cash_flow", "n_cashflow_inv_act", "SZ", "1", "MIDDLE"),
    ("financial_balance_sheet", "total_assets", "SH", "1", "RECENT"),
    ("financial_cash_flow", "n_cashflow_act", "SZ", "2", "RECENT"),
    ("financial_income", "revenue", "SH", "3", "RECENT"),
    ("financial_balance_sheet", "total_liab", "SZ", "4", "RECENT"),
    ("financial_income", "n_income_attr_p", "SH", "1", "CATCH_UP_2026"),
    ("financial_cash_flow", "n_cashflow_inv_act", "SZ", "2", "CATCH_UP_2026"),
)


def era(period: str) -> str:
    year = int(period[:4])
    if year <= 2014: return "EARLY"
    if year <= 2020: return "MIDDLE"
    if year <= 2025: return "RECENT"
    return "CATCH_UP_2026"


def main() -> int:
    target = {(kind, metric, exchange, report, band): [] for kind, metric, exchange, report, band in STRATA}
    for path in sorted((RUNTIME / "raw").rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        kind = path.parts[-4]
        for row in payload["provider_payload"]["rows"]:
            exchange = str(row.get("ts_code", ""))[-2:]
            report = str(row.get("end_type", ""))
            period = str(row.get("end_date", ""))
            if len(period) != 8: continue
            for metric in (item[1] for item in STRATA if item[0] == kind):
                key = kind, metric, exchange, report, era(period)
                if key in target and row.get(metric) is not None:
                    candidate = {
                        "dataset_kind": kind, "security_identity": row["ts_code"],
                        "period_end": period, "report_type": report,
                        "publication_date": row.get("f_ann_date") or row.get("ann_date"),
                        "metric": metric, "provider_value": str(row[metric]), "unit": "CNY",
                        "provider_row_hash": content_hash(row), "raw_payload_hash": payload["payload_hash"],
                    }
                    target[key].append(candidate)
    missing = [key for key, values in target.items() if not values]
    if missing: raise RuntimeError(f"sample strata unavailable: {missing}")
    samples = tuple(min(values, key=content_hash) for values in target.values())
    acquisition_inventory = next((RUNTIME / "governance").glob("historical-inventory-*.json"))
    acquisition_inventory_id = json.loads(acquisition_inventory.read_text(encoding="utf-8"))["inventory_id"]
    body = {"schema_version": "FinancialDisclosureCrossSourceInventoryV1",
            "selection_policy_version": "financial-cross-source-stratified-v1",
            "acquisition_inventory_id": acquisition_inventory_id,
            "frozen_before_independent_comparison": True, "samples": samples}
    inventory_id = content_hash(body)
    output = {"inventory_id": inventory_id, "content_hash": inventory_id, **body}
    path = RUNTIME / "governance" / f"cross-source-inventory-{inventory_id}.json"
    encoded = canonical_json(output); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded: raise RuntimeError("immutable inventory collision")
    if not path.exists(): path.write_bytes(encoded)
    (path.parent / "current-cross-source-inventory-id.txt").write_text(inventory_id, encoding="ascii")
    print(f"FROZEN_SAMPLE_INVENTORY_ID={inventory_id} SAMPLES={len(samples)}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
