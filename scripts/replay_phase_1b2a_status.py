from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from phase_1b2a_acquire import RUNTIME, _load_inventory  # noqa: E402
from v5_2.data.checkpoints import CheckpointStore  # noqa: E402
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.raw_artifacts import RawArtifactStore  # noqa: E402
from v5_2.data.real_audits.status_acquisition import acquire_status_requests  # noqa: E402
from v5_2.integrations.datahub_http import DataHubHttpTransport  # noqa: E402
from v5_2.providers.credentials import load_datahub_credential  # noqa: E402
from v5_2.providers.datahub import DataHubClient  # noqa: E402
from v5_2.providers.rate_limit import RateLimiter  # noqa: E402


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    inventory, _ = _load_inventory()
    selected = (
        inventory.requests[0],
        inventory.requests[len(inventory.requests) // 2],
        inventory.requests[-1],
    )
    store = RawArtifactStore(RUNTIME)
    checkpoints = CheckpointStore(RUNTIME)
    client = DataHubClient(transport=DataHubHttpTransport(timeout_seconds=30))
    credential = load_datahub_credential(env={}, env_file=ROOT / ".env", repository_root=ROOT)
    observations = []
    for request in selected:
        previous = tuple(
            _load(RUNTIME / "checkpoints" / f"{request.request_id}.json")
            ["accepted_payload_hashes"]
        )
        before_receipts = set((RUNTIME / "receipts").rglob("*.json"))
        replay = acquire_status_requests(
            (request,),
            client=client,
            credential=credential,
            raw_store=store,
            checkpoint_store=checkpoints,
            rate_limiter=RateLimiter(min_interval_seconds=0.25),
            utc_clock=lambda: datetime.now(timezone.utc),
            resume=False,
        )
        after_receipts = set((RUNTIME / "receipts").rglob("*.json"))
        observations.append(
            {
                "dataset_kind": request.dataset_kind,
                "request_id": request.request_id,
                "previous_payload_hashes": previous,
                "replayed_payload_hashes": replay.payload_hashes,
                "same_payload_identity": previous == replay.payload_hashes,
                "new_receipt_count": len(after_receipts - before_receipts),
            }
        )
    body = {
        "schema_version": "StatusRealReplayEvidenceV1",
        "inventory_id": inventory.inventory_id,
        "sample_policy_id": "first-middle-last-v1",
        "observations": observations,
        "same_payload_different_receipt_pass": all(
            item["same_payload_identity"] and item["new_receipt_count"] >= 1
            for item in observations
        ),
        "revision_detection_contract": "covered by synthetic changed-payload contract test",
        "observed_at": datetime.now(timezone.utc),
    }
    body["content_hash"] = content_hash(body)
    body["evidence_id"] = body["content_hash"]
    output = RUNTIME / "governance" / f"status-replay-{body['evidence_id']}.json"
    output.write_bytes(canonical_json(body))
    print(json.dumps(body, indent=2, default=str))
    print(f"ARTIFACT={output.name}")
    return 0 if body["same_payload_different_receipt_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
