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
from v5_2.data.raw_artifacts import RawArtifactStore  # noqa: E402
from v5_2.integrations.datahub_http import DataHubHttpTransport  # noqa: E402
from v5_2.providers.contracts import ProviderRequestV1  # noqa: E402
from v5_2.providers.credentials import load_datahub_credential  # noqa: E402
from v5_2.providers.datahub import DataHubClient  # noqa: E402
from v5_2.providers.rate_limit import RateLimiter  # noqa: E402
from v5_2.providers.retry import RetryPolicyV1  # noqa: E402

RUNTIME = ROOT / "data" / "phase_1b_exit_status_2026"
UPSTREAM = (
    "4a900c7e4f2b171d7adac07088025ca4bb9fb0da13cfa1b15e91eff3dafea601",
    "828e0e722d3d66c84a48584aac14fde37f86cf471f3722f403ec19044f36345c",
)


def requests() -> tuple[ProviderRequestV1, ...]:
    specs = (
        ("risk_warning_history", "namechange", ("ts_code", "name", "start_date", "end_date", "ann_date", "change_reason")),
        ("suspension_history", "suspend-d", ("ts_code", "trade_date", "suspend_timing", "suspend_type")),
    )
    return tuple(ProviderRequestV1.create(
        source_name="datahubco_tushare_proxy", dataset_kind=kind, endpoint=endpoint,
        parameters={"start_date": "20260101", "end_date": "20260910", "fields": ",".join(fields)},
        requested_fields=fields, page_size=5000, request_policy_version="status-2026-segment-v1",
    ) for kind, endpoint, fields in specs)


def _write(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError("immutable status remediation artifact collision")
    if not path.exists():
        path.write_bytes(encoded)


def main() -> int:
    frozen = requests()
    inventory_body = {"schema_version": "HistoricalStatusSegmentInventoryV1",
                      "coverage_start": "2026-01-01", "coverage_end": "2026-09-10",
                      "upstream_approval_ids": UPSTREAM,
                      "request_ids": tuple(item.request_id for item in frozen)}
    inventory_id = content_hash(inventory_body)
    _write(RUNTIME / "governance" / f"inventory-{inventory_id}.json",
           {"inventory_id": inventory_id, **inventory_body, "content_hash": inventory_id})
    credential = load_datahub_credential(env={}, env_file=ROOT / ".env", repository_root=ROOT)
    controls = AcquisitionControls(
        retry_policy=RetryPolicyV1(3, 1.0, 4.0, "datahub-retry-v1"),
        rate_limiter=RateLimiter(min_interval_seconds=.25), monotonic_clock=time.monotonic, sleeper=time.sleep,
        utc_clock=lambda: datetime.now(timezone.utc))
    store, checkpoints = RawArtifactStore(RUNTIME), CheckpointStore(RUNTIME)
    client = DataHubClient(transport=DataHubHttpTransport(timeout_seconds=30))
    outputs = []
    for request in frozen:
        artifacts = acquire_pages(request=request, client=client, credential=credential,
            raw_store=store, checkpoint_store=checkpoints,
            acquisition_policy_version="datahub-acquisition-v1", controls=controls,
            resume=checkpoints.exists(request.request_id))
        outputs.append((request.dataset_kind, tuple(item.payload_hash for item in artifacts),
                        sum(len(item.provider_payload["rows"]) for item in artifacts)))
    body = {"schema_version": "HistoricalStatusSegmentAcquisitionV1", "inventory_id": inventory_id,
            "results": outputs}
    artifact_id = content_hash(body)
    _write(RUNTIME / "governance" / f"acquisition-{artifact_id}.json",
           {"artifact_id": artifact_id, **body, "content_hash": artifact_id})
    print(json.dumps({"artifact_id": artifact_id, "inventory_id": inventory_id,
                      "results": outputs}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
