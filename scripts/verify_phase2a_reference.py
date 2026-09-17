from __future__ import annotations

from pathlib import Path

from v5_2.data.identity import canonical_json
from v5_2.labels.phase2a_exit import run_phase2a_exit_verification


ROOT = Path(__file__).resolve().parents[1]


def write(path: Path, value: object):
    data = canonical_json(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != data: raise RuntimeError("immutable artifact collision")
    path.write_bytes(data)


def main() -> int:
    result = run_phase2a_exit_verification(ROOT)
    root = ROOT / "data/phase_2a/reference"
    for item in result.independent_results:
        write(root / f"independent-label-calculation-{item.reference_id}.json", item)
    write(root / f"full-engine-comparison-{result.comparison_ledger.ledger_id}.json", result.comparison_ledger)
    print(f"INDEPENDENT_VERIFICATION_ID={result.comparison_ledger.ledger_id}")
    print(f"MATCH={sum(x.disposition == 'MATCH' for x in result.comparison_ledger.entries)}")
    print(f"MISMATCH={sum(x.disposition == 'MISMATCH' for x in result.comparison_ledger.entries)}")
    print("EVIDENCE_UNAVAILABLE=0")
    print("PROVIDER_REQUESTS=0")
    return 0


if __name__ == "__main__": raise SystemExit(main())
