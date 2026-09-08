from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.real_audits.official_anchor_gaps import build_official_anchor_gap_inventory  # noqa: E402
from v5_2.data.real_audits.pinned_artifacts import load_pinned_json  # noqa: E402

CONTRACT_ID = "3a9efd2f1047d9ad0432a72202bf1b8e7f926d153c339106475c37a694b20917"
INVENTORY_ID = "cef91ec0a055f01ac2f0f82ec8e15ce75f4e000acd2123a70685fb25d1df3c9c"
LEDGER_ID = "0f6772947b821a5819614c652d08544ac8bc14b789b796eb0f4338f71c79e473"


def main() -> int:
    governance = ROOT / "data" / "phase_1b2a" / "governance"
    inventory = load_pinned_json(governance / f"prospective-status-sample-inventory-v2-{INVENTORY_ID}.json",
        schema_version="ProspectiveStatusSampleInventoryV2", identity_field="inventory_id",
        expected_identity=INVENTORY_ID)
    ledger = load_pinned_json(governance / f"prospective-status-evidence-ledger-v2-{LEDGER_ID}.json",
        schema_version="ProspectiveStatusEvidenceLedgerV2", identity_field="content_hash",
        expected_identity=LEDGER_ID)
    gaps = build_official_anchor_gap_inventory(CONTRACT_ID, INVENTORY_ID, inventory["samples"],
                                               ledger["observations"])
    body = {"schema_version": "OfficialAnchorGapInventoryV1", **asdict(gaps)}
    path = governance / f"official-anchor-gap-inventory-{gaps.content_hash}.json"
    path.write_bytes(canonical_json(body))
    print(json.dumps({"gap_inventory_id": gaps.content_hash, "total": len(gaps.entries),
                      "counts": dict(gaps.counts)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
