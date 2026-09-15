from __future__ import annotations

from dataclasses import fields
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.real_audits.phase2a_bar_backfill import build_bar_backfill_inventory  # noqa: E402


def main() -> int:
    inventory = build_bar_backfill_inventory(ROOT)
    path = ROOT / "data/phase_2a/bar_backfill/governance" / f"bar-backfill-inventory-{inventory.inventory_id}.json"
    encoded = canonical_json({
        "schema_version": type(inventory).__name__,
        **{field.name: getattr(inventory, field.name) for field in fields(inventory)},
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError("immutable Phase 2A bar-backfill inventory collision")
    if not path.exists():
        path.write_bytes(encoded)
    sessions = {day for slot in inventory.slots for day in slot.required_bar_sessions}
    print(f"BAR_BACKFILL_INVENTORY_ID={inventory.inventory_id}")
    print(f"FROZEN_SLOTS={len(inventory.slots)}")
    print(f"UNIQUE_SECURITIES={len({slot.canonical_identity for slot in inventory.slots})}")
    print(f"UNIQUE_REQUIRED_BAR_SESSIONS={len(sessions)}")
    print(f"UNIQUE_REQUESTS={len(inventory.requests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
