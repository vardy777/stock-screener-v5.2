from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from v5_2.labels.acceptance import IndependentLabelCalculationV1, build_comparison_ledger, build_frozen_inventory


ROOT = Path(__file__).resolve().parents[1]


def write(path: Path, value: object):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") != data: raise RuntimeError("immutable artifact collision")
    path.write_text(data, encoding="utf-8")


def main() -> int:
    inventory = build_frozen_inventory()
    calculations = tuple(IndependentLabelCalculationV1.create(
        slot=item.slot, inventory_evidence_id=item.evidence_ids[0], status="EVIDENCE_UNAVAILABLE",
        horizons=(), inputs_hash=None, result_summary=(), method_version="phase2a-independent-v1",
        reason="EXACT_FIVE_DOMAIN_BUNDLE_NOT_YET_ASSEMBLED") for item in inventory.slots)
    ledger = build_comparison_ledger(calculations, {})
    root = ROOT / "data/phase_2a/reference"
    for item in calculations: write(root / f"independent-label-calculation-{item.calculation_id}.json", asdict(item))
    write(root / f"engine-comparison-{ledger.ledger_id}.json", asdict(ledger))
    print(f"INDEPENDENT_VERIFICATION_ID={ledger.ledger_id}")
    print(f"MATCH={sum(x.disposition == 'MATCH' for x in ledger.entries)}")
    print(f"MISMATCH={sum(x.disposition == 'MISMATCH' for x in ledger.entries)}")
    print(f"EVIDENCE_UNAVAILABLE={sum(x.disposition == 'EVIDENCE_UNAVAILABLE' for x in ledger.entries)}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
