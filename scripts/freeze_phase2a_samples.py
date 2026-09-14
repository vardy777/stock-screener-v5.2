from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from v5_2.labels.acceptance import build_frozen_inventory


ROOT = Path(__file__).resolve().parents[1]


def default(value):
    if isinstance(value, date): return value.isoformat()
    if hasattr(value, "value"): return value.value
    raise TypeError(type(value).__name__)


def write_immutable(path: Path, value: object) -> None:
    data = json.dumps(value, default=default, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") != data:
        raise RuntimeError("immutable artifact collision")
    path.write_text(data, encoding="utf-8")


def main() -> int:
    inventory = build_frozen_inventory()
    root = ROOT / "data/phase_2a/governance"
    write_immutable(root / f"label-acceptance-selection-rule-{inventory.selection_rule.content_hash}.json", asdict(inventory.selection_rule))
    write_immutable(root / f"label-acceptance-inventory-{inventory.inventory_id}.json", asdict(inventory))
    print(f"SELECTION_RULE_ID={inventory.selection_rule.content_hash}")
    print(f"REAL_SAMPLE_INVENTORY_ID={inventory.inventory_id}")
    print(f"SLOTS={len(inventory.slots)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
