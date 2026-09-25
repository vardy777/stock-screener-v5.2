"""Replay the narrow official-evidence ratification without network access."""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.real_audits.identity_graph_ratification import (  # noqa: E402
    GRAPH_ID,
    GraphRatificationError,
    OfficialGraphEvidenceV1,
    SecurityIdentityGraphApprovalV1,
    ratify_existing_graph,
)

BASE = ROOT / "data" / "phase_1b1_identity_graph_ratification"
LISTING_SHA = "e0357fb6ddc81f4ae93f0423f7f668ebb8ba53e3ffd80baed73341baa4381f20"
TRANSITION_SHA = "dd68049c48df826848f361fd9e7b23dd20b6805144a2e5bc36e54db638611488"
LISTING_URL = "https://www.szse.cn/aboutus/trends/news/t20100827_518017.html"
TRANSITION_URL = "https://disc.static.szse.cn/download/disc/disk03/finalpage/2025-02-15/cedb693a-f5ee-4463-9682-ea33d406b569.PDF"
LISTING_RETRIEVED_AT = datetime(2026, 9, 25, 8, 21, 22, tzinfo=timezone.utc)
TRANSITION_RETRIEVED_AT = datetime(2026, 9, 25, 8, 23, 13, tzinfo=timezone.utc)
VERIFIED_AT = datetime(2026, 9, 25, 8, 33, 48, tzinfo=timezone.utc)


def _exact_bytes(path: Path, expected_hash: str) -> bytes:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_hash:
        raise GraphRatificationError(f"raw official document hash mismatch: {path.name}")
    return raw


def _write_immutable(path: Path, value: object) -> None:
    encoded = canonical_json(asdict(value))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != encoded:
            raise GraphRatificationError(f"immutable artifact collision: {path.name}")
        return
    path.write_bytes(encoded)


def main() -> int:
    graph = json.loads((BASE / "graph" / f"effective-identity-{GRAPH_ID}.json").read_bytes())
    listing_raw = _exact_bytes(BASE / "official" / f"raw-listing-{LISTING_SHA}.html", LISTING_SHA)
    transition_raw = _exact_bytes(BASE / "official" / f"raw-transition-{TRANSITION_SHA}.pdf", TRANSITION_SHA)
    listing = OfficialGraphEvidenceV1.from_bytes(raw_bytes=listing_raw, url=LISTING_URL,
        claim_scope="ORIGINAL_LISTING", document_date="2010-08-27", retrieved_at=LISTING_RETRIEVED_AT)
    transition = OfficialGraphEvidenceV1.from_bytes(raw_bytes=transition_raw, url=TRANSITION_URL,
        claim_scope="CODE_TRANSITION", document_date="2025-02-14", retrieved_at=TRANSITION_RETRIEVED_AT)
    ratification = ratify_existing_graph(graph, ((listing, listing_raw), (transition, transition_raw)),
        verified_at=VERIFIED_AT)
    approval = SecurityIdentityGraphApprovalV1.create(ratification)
    output = BASE / "governance"
    for item, name in (
        (listing, f"official-graph-evidence-{listing.artifact_id}.json"),
        (transition, f"official-graph-evidence-{transition.artifact_id}.json"),
        (ratification, f"identity-graph-ratification-{ratification.evidence_id}.json"),
        (approval, f"identity-graph-approval-{approval.approval_id}.json"),
    ):
        _write_immutable(output / name, item)
    print(json.dumps({"graph_id": GRAPH_ID, "listing_evidence_id": listing.artifact_id,
        "transition_evidence_id": transition.artifact_id, "ratification_evidence_id": ratification.evidence_id,
        "graph_scoped_approval_id": approval.approval_id, "decision": approval.decision}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
