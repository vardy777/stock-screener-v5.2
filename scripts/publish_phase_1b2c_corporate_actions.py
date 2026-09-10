from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "data" / "phase_1b2c" / "governance" / "latest-gate.json"


def main() -> int:
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    if not gate.get("publication_allowed") or gate.get("source_approval") != "APPROVED_WITH_RULES":
        print("APPROVED_FACTS=0")
        print("DATASET_MANIFEST=none")
        return 0
    raise RuntimeError("approval artifact and fact publication inputs are not present")


if __name__ == "__main__":
    raise SystemExit(main())
