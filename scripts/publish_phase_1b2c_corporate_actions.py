from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE = ROOT / "data" / "phase_1b2c" / "governance"


def main() -> int:
    gate_id = (GOVERNANCE / "current-gate-id.txt").read_text(encoding="ascii").strip()
    gate = json.loads((GOVERNANCE / f"gate-{gate_id}.json").read_text(encoding="utf-8"))
    if not gate.get("publication_allowed") or gate.get("source_approval") != "APPROVED_WITH_RULES":
        print("APPROVED_FACTS=0")
        print("DATASET_MANIFEST=none")
        return 0
    raise RuntimeError("approval artifact and fact publication inputs are not present")


if __name__ == "__main__":
    raise SystemExit(main())
