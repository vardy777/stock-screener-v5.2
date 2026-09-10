from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.acquisition import AcquisitionControls, acquire_pages  # noqa: E402
from v5_2.data.checkpoints import CheckpointStore  # noqa: E402
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.phase_1b1_requests import phase_1b1_2026_extension_requests  # noqa: E402
from v5_2.data.raw_artifacts import RawArtifactStore  # noqa: E402
from v5_2.integrations.datahub_http import DataHubHttpTransport  # noqa: E402
from v5_2.providers.credentials import load_datahub_credential  # noqa: E402
from v5_2.providers.datahub import DataHubClient  # noqa: E402
from v5_2.providers.rate_limit import RateLimiter  # noqa: E402
from v5_2.providers.retry import RetryPolicyV1  # noqa: E402

END = "20260911"
RUNTIME = ROOT / "data" / "phase_1b1_2026_extension"


def _write(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError("immutable extension artifact collision")
    if not path.exists():
        path.write_bytes(encoded)


def main() -> int:
    credential = load_datahub_credential(env={}, env_file=ROOT / ".env", repository_root=ROOT)
    client = DataHubClient(transport=DataHubHttpTransport(timeout_seconds=30))
    controls = AcquisitionControls(
        retry_policy=RetryPolicyV1(3, 1.0, 4.0, "datahub-retry-v1"),
        rate_limiter=RateLimiter(min_interval_seconds=.25), monotonic_clock=time.monotonic,
        sleeper=time.sleep, utc_clock=lambda: datetime.now(timezone.utc),
    )
    store, checkpoints = RawArtifactStore(RUNTIME), CheckpointStore(RUNTIME)
    result = {}
    for kind, requests in phase_1b1_2026_extension_requests(end_date=END).items():
        artifacts = []
        for request in requests:
            artifacts.extend(acquire_pages(
                request=request, client=client, credential=credential, raw_store=store,
                checkpoint_store=checkpoints, acquisition_policy_version="datahub-acquisition-v1",
                controls=controls, resume=False,
            ))
        body = {
            "schema_version": "Phase1B1IncrementalAcquisitionV1", "dataset_kind": kind,
            "coverage_start": "2026-01-01", "coverage_end": "2026-09-11" if kind == "trade_calendar" else "2026-09-10",
            "request_ids": tuple(request.request_id for request in requests),
            "payload_hashes": tuple(item.payload_hash for item in artifacts),
            "row_count": sum(len(item.provider_payload["rows"]) for item in artifacts),
        }
        artifact_id = content_hash(body)
        _write(RUNTIME / "governance" / f"{kind}-acquisition-{artifact_id}.json", {"artifact_id": artifact_id, **body})
        result[kind] = {"artifact_id": artifact_id, "rows": body["row_count"]}
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
