from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.acquisition import AcquisitionControls, acquire_pages  # noqa: E402
from v5_2.data.checkpoints import CheckpointStore  # noqa: E402
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.raw_artifacts import RawArtifactStore  # noqa: E402
from v5_2.data.real_audits.phase2a_bar_backfill import build_bar_backfill_inventory  # noqa: E402
from v5_2.integrations.datahub_http import DataHubHttpTransport  # noqa: E402
from v5_2.providers.credentials import load_datahub_credential  # noqa: E402
from v5_2.providers.datahub import DataHubClient  # noqa: E402
from v5_2.providers.rate_limit import RateLimiter  # noqa: E402
from v5_2.providers.retry import RetryPolicyV1  # noqa: E402


RUNTIME = ROOT / "data/phase_2a/bar_backfill"


def _write(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError("immutable Phase 2A backfill acquisition collision")
    if not path.exists():
        path.write_bytes(encoded)


def main() -> int:
    inventory = build_bar_backfill_inventory(ROOT)
    credential = load_datahub_credential(env=os.environ, env_file=ROOT / ".env", repository_root=ROOT)
    controls = AcquisitionControls(
        retry_policy=RetryPolicyV1(3, 1.0, 4.0, "datahub-retry-v1"),
        rate_limiter=RateLimiter(min_interval_seconds=.25), monotonic_clock=time.monotonic,
        sleeper=time.sleep, utc_clock=lambda: datetime.now(timezone.utc),
    )
    client = DataHubClient(transport=DataHubHttpTransport(timeout_seconds=30))
    store, checkpoints = RawArtifactStore(RUNTIME), CheckpointStore(RUNTIME)
    payloads = []
    for item in inventory.requests:
        request = item.provider_request
        payloads.extend(acquire_pages(
            request=request, client=client, credential=credential, raw_store=store,
            checkpoint_store=checkpoints, acquisition_policy_version="datahub-acquisition-v1",
            controls=controls, resume=checkpoints.exists(request.request_id),
        ))
    body = {
        "schema_version": "Phase2ABarBackfillAcquisitionV1",
        "inventory_id": inventory.inventory_id,
        "request_ids": tuple(item.provider_request.request_id for item in inventory.requests),
        "payload_hashes": tuple(sorted(item.payload_hash for item in payloads)),
        "row_count": sum(len(item.provider_payload["rows"]) for item in payloads),
    }
    artifact_id = content_hash(body)
    _write(RUNTIME / "governance" / f"bar-backfill-acquisition-{artifact_id}.json",
           {"artifact_id": artifact_id, **body, "content_hash": artifact_id})
    print(json.dumps({"artifact_id": artifact_id, "inventory_id": inventory.inventory_id,
                      "requests": len(inventory.requests), "rows": body["row_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
