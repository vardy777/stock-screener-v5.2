from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.real_audits.official_anchor_gaps import (  # noqa: E402
    OfficialAnchorEvidenceV1, merge_official_anchor_supplement,
)
from v5_2.data.real_audits.pinned_artifacts import load_pinned_json  # noqa: E402

CONTRACT_ID = "3a9efd2f1047d9ad0432a72202bf1b8e7f926d153c339106475c37a694b20917"
INVENTORY_ID = "cef91ec0a055f01ac2f0f82ec8e15ce75f4e000acd2123a70685fb25d1df3c9c"
LEDGER_ID = "0f6772947b821a5819614c652d08544ac8bc14b789b796eb0f4338f71c79e473"


def latest(directory: Path, prefix: str):
    return max(directory.glob(f"{prefix}-*.json"), key=lambda path: path.stat().st_mtime)


def main() -> int:
    governance = ROOT / "data" / "phase_1b2a" / "governance"
    original = load_pinned_json(governance / f"prospective-status-evidence-ledger-v2-{LEDGER_ID}.json",
        schema_version="ProspectiveStatusEvidenceLedgerV2", identity_field="content_hash", expected_identity=LEDGER_ID)
    supplement_path = latest(governance, "official-anchor-supplement")
    supplement = json.loads(supplement_path.read_text(encoding="utf-8"))
    evidence = tuple(OfficialAnchorEvidenceV1(**item) for item in supplement["evidence"])
    observations = merge_official_anchor_supplement(original["observations"], evidence)
    body = {"schema_version": "ProspectiveStatusEvidenceLedgerV2", "contract_id": CONTRACT_ID,
            "inventory_id": INVENTORY_ID, "observations": observations,
            "independence_rationale": original["independence_rationale"],
            "official_anchor_supplement_id": supplement["content_hash"],
            "supersedes_ledger_id": LEDGER_ID}
    body["content_hash"] = content_hash(body)
    output = governance / f"prospective-status-evidence-ledger-v2-{body['content_hash']}.json"
    output.write_bytes(canonical_json(body))
    counts = {key: sum(item["resolution"] == key for item in observations)
              for key in ("MATCH", "MISMATCH", "INDEPENDENT_EVIDENCE_UNAVAILABLE")}
    status = "FAIL" if counts["MISMATCH"] else "PASS" if counts["MATCH"] == 71 else "PENDING"
    print(json.dumps({"total": len(observations), "counts": counts, "cross_source": status,
                      "ledger_id": body["content_hash"], "supplement_id": supplement["content_hash"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
