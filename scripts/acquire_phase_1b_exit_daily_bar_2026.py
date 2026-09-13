from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.acquisition import AcquisitionControls, acquire_pages  # noqa: E402
from v5_2.data.checkpoints import CheckpointStore  # noqa: E402
from v5_2.data.historical_remediation import build_daily_bar_segment_inventory  # noqa: E402
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.raw_artifacts import RawArtifactStore  # noqa: E402
from v5_2.integrations.datahub_http import DataHubHttpTransport  # noqa: E402
from v5_2.providers.credentials import load_datahub_credential  # noqa: E402
from v5_2.providers.datahub import DataHubClient  # noqa: E402
from v5_2.providers.rate_limit import RateLimiter  # noqa: E402
from v5_2.providers.retry import RetryPolicyV1  # noqa: E402


RUNTIME = ROOT / "data" / "phase_1b_exit_daily_bar_2026"
CALENDAR_APPROVAL_ID = "4a900c7e4f2b171d7adac07088025ca4bb9fb0da13cfa1b15e91eff3dafea601"
MASTER_APPROVAL_ID = "828e0e722d3d66c84a48584aac14fde37f86cf471f3722f403ec19044f36345c"


def _calendar_sessions() -> tuple[str, ...]:
    sessions: set[str] = set()
    raw_root = ROOT / "data" / "phase_1b1_2026_extension" / "raw" / "datahubco_tushare_proxy" / "trade_calendar"
    for path in raw_root.rglob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload["provider_payload"]["rows"]:
            if row.get("is_open") in (1, "1") and "20260101" <= row["cal_date"] <= "20260910":
                sessions.add(row["cal_date"])
    if not sessions:
        raise RuntimeError("approved 2026 calendar lineage yielded no sessions")
    return tuple(sorted(sessions))


def _write_immutable(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError("immutable daily-bar remediation artifact collision")
    if not path.exists():
        path.write_bytes(encoded)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-only", action="store_true")
    args = parser.parse_args()
    inventory = build_daily_bar_segment_inventory(
        sessions=_calendar_sessions(),
        upstream_approval_ids=(CALENDAR_APPROVAL_ID, MASTER_APPROVAL_ID),
    )
    inventory_body = {
        "schema_version": "DailyBarSegmentInventoryV1", "inventory_id": inventory.inventory_id,
        "sessions": inventory.sessions, "upstream_approval_ids": inventory.upstream_approval_ids,
        "request_ids": tuple(item.request_id for item in inventory.requests),
        "content_hash": inventory.content_hash,
    }
    _write_immutable(RUNTIME / "governance" / f"inventory-{inventory.inventory_id}.json", inventory_body)

    credential = load_datahub_credential(env={}, env_file=ROOT / ".env", repository_root=ROOT)
    controls = AcquisitionControls(
        retry_policy=RetryPolicyV1(3, 1.0, 4.0, "datahub-retry-v1"),
        rate_limiter=RateLimiter(min_interval_seconds=.25), monotonic_clock=time.monotonic,
        sleeper=time.sleep, utc_clock=lambda: datetime.now(timezone.utc),
    )
    client = DataHubClient(transport=DataHubHttpTransport(timeout_seconds=30))
    store, checkpoints = RawArtifactStore(RUNTIME), CheckpointStore(RUNTIME)
    selected = inventory.requests[:1] if args.probe_only else inventory.requests
    payloads = []
    for request in selected:
        payloads.extend(acquire_pages(
            request=request, client=client, credential=credential, raw_store=store,
            checkpoint_store=checkpoints, acquisition_policy_version="datahub-acquisition-v1",
            controls=controls, resume=checkpoints.exists(request.request_id),
        ))
    body = {
        "schema_version": "DailyBar2026SegmentAcquisitionV1",
        "inventory_id": inventory.inventory_id,
        "mode": "PROBE" if args.probe_only else "FULL",
        "request_ids": tuple(item.request_id for item in selected),
        "payload_hashes": tuple(item.payload_hash for item in payloads),
        "row_count": sum(len(item.provider_payload["rows"]) for item in payloads),
    }
    artifact_id = content_hash(body)
    _write_immutable(RUNTIME / "governance" / f"acquisition-{artifact_id}.json",
                     {"artifact_id": artifact_id, **body})
    print(json.dumps({"artifact_id": artifact_id, "inventory_id": inventory.inventory_id,
                      "requests": len(selected), "rows": body["row_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
