"""Offline create-or-identical inventory for physically copied Master sources."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.historical_security_master_authority import (  # noqa: E402
    _put_exact,
    create_master_source_corpus_inventory,
)
from v5_2.data.identity import canonical_json  # noqa: E402


def main() -> int:
    source = ROOT / "data/phase_1b_historical_master_portable/source"
    inventory = create_master_source_corpus_inventory(source)
    destination = source / f"source-corpus-inventory-{inventory['inventory_id']}.json"
    _put_exact(destination, canonical_json(inventory))
    print(f"SOURCE_CORPUS_INVENTORY_ID={inventory['inventory_id']}")
    print(f"SOURCE_FILES={len(inventory['files'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
