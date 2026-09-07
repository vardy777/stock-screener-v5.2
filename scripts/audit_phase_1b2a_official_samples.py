from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.real_audits.status_official_samples import build_official_sample_ledger  # noqa: E402

INVENTORY_ID = "7ca99bfecd2731d5442ea62eb496afe3cff9b01a7ba32c1434a461c1a931a9c0"


def main() -> int:
    directory = ROOT / "data" / "phase_1b2a" / "governance"
    inventory = json.loads((directory / f"status-sample-inventory-{INVENTORY_ID}.json").read_text(encoding="utf-8"))
    # No exact official retrieval result has yet been archived for these event IDs. Keep unresolved; never infer MATCH.
    official = {
        "dd3afde7031cf1a439063446d6d9b33b636a50a8fd028aaab7416f5d1180c762": {
            "resolution": "MATCH",
            "observation": "SZSE-hosted issuer record states 002699.SZ entered other-risk-warning status from 2022-06-06 open",
            "evidence_id": "https://disc.static.szse.cn/disc/disk03/finalpage/2022-10-11/8e84e52b-9e8e-4b8c-a6ff-3f59c13144f6.PDF",
            "semantic_mapping": "other risk warning effective at session open maps to provider ST state on 2022-06-06",
        },
    }
    ledger = build_official_sample_ledger(INVENTORY_ID, inventory["samples"], official=official)
    output = directory / f"status-official-sample-ledger-{ledger.content_hash}.json"
    output.write_bytes(canonical_json({"schema_version": "OfficialStatusSampleLedgerV1", **asdict(ledger)}))
    print(json.dumps({"entries": len(ledger.entries), "unique_events": ledger.unique_event_count,
                      "counts": dict(ledger.counts), "systematic_defect": ledger.systematic_defect,
                      "ledger_id": ledger.content_hash}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
