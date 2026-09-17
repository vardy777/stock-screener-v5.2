from __future__ import annotations

import json
from pathlib import Path

from v5_2.data.identity import canonical_json
from v5_2.labels.pilot import run_pilot


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    pilot = run_pilot(ROOT)
    target = ROOT / "data/phase_2a/pilot" / f"phase2a-pilot-{pilot.pilot_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_json(pilot)
    if target.exists() and target.read_bytes() != encoded:
        raise RuntimeError("immutable pilot artifact collision")
    target.write_bytes(encoded)
    print(f"PILOT_ID={pilot.pilot_id}")
    print(f"PILOT_SLOTS={','.join(map(str, pilot.slots))}")
    print(f"PILOT_MATCH={sum(item.disposition == 'MATCH' for item in pilot.entries)}")
    print(f"PILOT_MISMATCH={sum(item.disposition == 'MISMATCH' for item in pilot.entries)}")
    print("PROVIDER_REQUESTS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
