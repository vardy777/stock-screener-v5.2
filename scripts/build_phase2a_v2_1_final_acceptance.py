from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.labels.acceptance_v2_1_final import run_final_acceptance_v2_1  # noqa: E402


def _write_create_or_identical(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    if path.exists():
        if path.read_bytes() != encoded:
            raise RuntimeError(f"immutable final acceptance collision: {path.name}")
        return
    path.write_bytes(encoded)


def materialize_final_acceptance_v2_1(repository_root: Path, output_root: Path):
    attempt_roots = (
        (repository_root / "data/phase_2a/v2_infrastructure").resolve(),
        (repository_root / "data/phase_2a/v2_1_attempt2").resolve(),
    )
    destination = output_root.resolve()
    if any(destination == root or root in destination.parents for root in attempt_roots):
        raise ValueError("final acceptance must not write into Attempt infrastructure")
    result = run_final_acceptance_v2_1(repository_root)
    output_root.mkdir(parents=True, exist_ok=True)
    _write_create_or_identical(
        output_root / f"final-phase2a-acceptance-v2-1-{result.acceptance_id}.json",
        result,
    )
    return result


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data/phase_2a/v2_1_final_acceptance"
    result = materialize_final_acceptance_v2_1(ROOT, destination)
    print(json.dumps({
        "FINAL ACCEPTANCE ID": result.acceptance_id,
        "FINAL V2.1 ACCEPTANCE": result.overall_status,
        "PHASE 2A": result.phase_2a_status,
        "READY FOR PHASE 2B": "YES" if result.ready_for_phase_2b else "NO",
        "PHASE 2B STARTED": "NO",
    }, indent=2, sort_keys=True))
