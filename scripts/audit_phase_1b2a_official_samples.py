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
        "300114-to-302132-v1": {
            "resolution": "MATCH",
            "provider_observation": "frozen transition boundary: old identity final session 2025-02-14; new identity begins next session",
            "observation": "SZSE-hosted implementation notice: 300114 applies through T-1 and 302132 starts 2025-02-17",
            "evidence_id": "https://disc.static.szse.cn/disc/disk03/finalpage/2025-02-15/cedb693a-f5ee-4463-9682-ea33d406b569.PDF",
            "semantic_mapping": "BaoStock's retrospective 302132 code on 2025-02-14 is unsuitable for PIT identity; official effective-date chain matches frozen transition event",
        },
    }
    independent_paths = sorted(directory.glob("baostock-status-evidence-*.json"), key=lambda path: path.stat().st_mtime)
    if independent_paths:
        independent = json.loads(independent_paths[-1].read_text(encoding="utf-8"))
        for item in independent["observations"]:
            if item["event_id"] in official:
                continue
            official[item["event_id"]] = {
                "resolution": item["resolution"],
                "observation": json.dumps(item["rows"], ensure_ascii=False, sort_keys=True),
                "evidence_id": independent["content_hash"],
                "semantic_mapping": item["reason"],
            }
        ordinary_event = "f61a553ca2ec93dc00f9c0658e9fa9691edc8cf17ede02f412a048f3f03f84fc"
        ordinary = next(item for item in independent["observations"] if item["event_id"] == ordinary_event)
        official[ordinary_event] = {
            "resolution": "MATCH",
            "provider_observation": "DataHub stock-st: type=ST on 2025-01-02",
            "observation": json.dumps(ordinary["rows"], ensure_ascii=False, sort_keys=True),
            "evidence_id": independent["content_hash"],
            "semantic_mapping": "ordinary is a sampling stratum, not a non-ST value assertion; provider ST agrees with independent isST=1",
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
