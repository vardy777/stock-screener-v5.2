from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.checkpoints import CheckpointStore  # noqa: E402
from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.raw_artifacts import RawArtifactStore  # noqa: E402
from v5_2.data.real_audits.status_acquisition import acquire_status_requests  # noqa: E402
from v5_2.data.real_audits.status_entry import build_status_request_inventory  # noqa: E402
from v5_2.data.real_source_preflight import run_datahub_preflight  # noqa: E402
from v5_2.integrations.datahub_http import DataHubHttpTransport  # noqa: E402
from v5_2.providers.credentials import load_datahub_credential  # noqa: E402
from v5_2.providers.datahub import DataHubClient  # noqa: E402
from v5_2.providers.rate_limit import RateLimiter  # noqa: E402


PHASE_1B1 = ROOT / "data" / "phase_1b1"
RUNTIME = ROOT / "data" / "phase_1b2a"
UNIVERSE_ID = "2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01"
UPSTREAM_APPROVAL_IDS = (
    "1581b4d367dba1256247ddd13e09b53d0f95b5b1deeb40af9e6ed4a36606353b",
    "f208c17accba6b669359f476b2fdf3a1bc9ec6856e7fa1831ccdd1c42b80d8cf",
    "1ead49dfaefdfb8e4e75c9d94170d440abe77986e3388a6e96e6805537c1173c",
)


def _load_inventory():
    path = PHASE_1B1 / "governance" / f"daily-bar-universe-{UNIVERSE_ID}.json"
    universe = json.loads(path.read_text(encoding="utf-8"))
    inventory = build_status_request_inventory(
        universe,
        daily_bar_approval_id=UPSTREAM_APPROVAL_IDS[2],
        active_approval_ids=UPSTREAM_APPROVAL_IDS,
        revoked_approval_ids=(),
    )
    body = {
        "schema_version": "StatusRequestInventoryV1",
        "inventory_id": inventory.inventory_id,
        "universe_id": inventory.universe_id,
        "upstream_approval_ids": inventory.upstream_approval_ids,
        "ordered_symbols": inventory.ordered_symbols,
        "coverage_start": inventory.coverage_start,
        "coverage_end": inventory.coverage_end,
        "request_ids": tuple(request.request_id for request in inventory.requests),
        "content_hash": inventory.content_hash,
    }
    governance = RUNTIME / "governance"
    governance.mkdir(parents=True, exist_ok=True)
    output = governance / f"status-request-inventory-{inventory.inventory_id}.json"
    content = canonical_json(body)
    if output.exists() and output.read_bytes() != content:
        raise RuntimeError("immutable status inventory collision")
    if not output.exists():
        output.write_bytes(content)
    return inventory, output


def _probe_status_endpoints(client, credential, inventory) -> None:
    for dataset_kind in ("risk_warning_history", "suspension_history"):
        request = next(item for item in inventory.requests if item.dataset_kind == dataset_kind)
        page = client.fetch_page(request, credential, page_identity={"offset": 0})
        required = set(request.requested_fields)
        observed = set().union(*(row.keys() for row in page.rows)) if page.rows else set()
        if page.rows and not required.issubset(observed):
            missing = ",".join(sorted(required - observed))
            raise RuntimeError(f"{dataset_kind} probe missing required fields: {missing}")
        print(
            f"ENDPOINT_PROBE={dataset_kind} STATUS=PASS ROWS={len(page.rows)} "
            f"TOTAL={page.total_count}",
            flush=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="V5.2 Phase 1B-2A status acquisition")
    parser.add_argument("mode", choices=("preflight", "probe", "acquire"))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    transport = DataHubHttpTransport(timeout_seconds=30)
    preflight = run_datahub_preflight(repository_root=ROOT, env={}, probe=transport)
    print(
        f"SOURCE={preflight.source_name} STATUS={preflight.status} "
        f"REASON={preflight.reason} TRANSPORT={preflight.transport_security}",
        flush=True,
    )
    if preflight.status != "PASS":
        return 2
    if args.mode == "preflight":
        return 0

    credential = load_datahub_credential(env={}, env_file=ROOT / ".env", repository_root=ROOT)
    client = DataHubClient(transport=transport)
    inventory, inventory_path = _load_inventory()
    print(
        f"STATUS_INVENTORY={inventory.inventory_id} REQUESTS={len(inventory.requests)} "
        f"ARTIFACT={inventory_path.name}",
        flush=True,
    )
    _probe_status_endpoints(client, credential, inventory)
    if args.mode == "probe":
        return 0

    result = acquire_status_requests(
        inventory.requests,
        client=client,
        credential=credential,
        raw_store=RawArtifactStore(RUNTIME),
        checkpoint_store=CheckpointStore(RUNTIME),
        rate_limiter=RateLimiter(min_interval_seconds=0.25),
        utc_clock=lambda: datetime.now(timezone.utc),
        resume=args.resume,
    )
    print(
        f"STATUS_ACQUISITION=PASS COMPLETED_REQUESTS={result.completed_requests} "
        f"PAGES={result.page_count} ROWS={result.row_count} "
        f"PAYLOAD_HASHES={len(result.payload_hashes)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
