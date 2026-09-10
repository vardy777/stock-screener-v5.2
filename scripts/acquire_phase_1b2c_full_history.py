from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.checkpoints import CheckpointStore  # noqa: E402
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.raw_artifacts import RawArtifactStore  # noqa: E402
from v5_2.data.real_audits.corporate_action_acquisition import acquire_corporate_action_requests  # noqa: E402
from v5_2.data.real_audits.corporate_action_entry import build_corporate_action_inventory  # noqa: E402
from v5_2.integrations.datahub_http import DataHubHttpTransport  # noqa: E402
from v5_2.providers.credentials import load_datahub_credential  # noqa: E402
from v5_2.providers.datahub import DataHubClient  # noqa: E402
from v5_2.providers.rate_limit import RateLimiter  # noqa: E402


UNIVERSE_ID = "2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01"
UPSTREAM = (
    "1581b4d367dba1256247ddd13e09b53d0f95b5b1deeb40af9e6ed4a36606353b",
    "f208c17accba6b669359f476b2fdf3a1bc9ec6856e7fa1831ccdd1c42b80d8cf",
)
RUNTIME = ROOT / "data" / "phase_1b2c"


def _write_immutable(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError("immutable full-history artifact collision")
    if not path.exists():
        path.write_bytes(encoded)


def main() -> int:
    universe_path = ROOT / "data" / "phase_1b1" / "governance" / f"daily-bar-universe-{UNIVERSE_ID}.json"
    universe = json.loads(universe_path.read_text(encoding="utf-8"))
    symbols = tuple(universe["ordered_symbols"])
    inventory = build_corporate_action_inventory(
        symbols=symbols, endpoint="dividend", target_history_start=date(2010, 1, 4),
        baseline_validation_end=date(2025, 12, 31), rolling_coverage_end=date(2026, 9, 9),
        upstream_approval_ids=UPSTREAM, active_approval_ids=UPSTREAM, revoked_approval_ids=(),
    )
    inventory_body = {
        "schema_version": "CorporateActionFullHistoryInventoryV1",
        "universe_id": UNIVERSE_ID,
        "inventory_id": inventory.inventory_id,
        "upstream_approval_ids": UPSTREAM,
        "request_count": len(inventory.requests),
        "request_ids": tuple(item.request.request_id for item in inventory.requests),
        "target_history_start": "2010-01-04",
        "baseline_validation_end": "2025-12-31",
        "rolling_coverage_end": "2026-09-09",
    }
    _write_immutable(RUNTIME / "governance" / f"full-history-inventory-{inventory.inventory_id}.json", inventory_body)
    credential = load_datahub_credential(env_file=ROOT / ".env", repository_root=ROOT)
    client = DataHubClient(transport=DataHubHttpTransport(timeout_seconds=30))
    raw_store = RawArtifactStore(RUNTIME)
    checkpoints = CheckpointStore(RUNTIME)
    limiter = RateLimiter(min_interval_seconds=0.05)

    def acquire_one(item):
        return acquire_corporate_action_requests(
            (item.request,), client=client, credential=credential, raw_store=raw_store,
            checkpoint_store=checkpoints, limiter=limiter,
            utc_clock=lambda: datetime.now(timezone.utc), resume=True,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        partial = tuple(executor.map(acquire_one, inventory.requests))
    completed_requests = sum(item.completed_requests for item in partial)
    page_count = sum(item.page_count for item in partial)
    row_count = sum(item.row_count for item in partial)
    payload_hashes = tuple(payload for item in partial for payload in item.payload_hashes)
    summary_body = {
        "schema_version": "CorporateActionAcquisitionSummaryV1",
        "inventory_id": inventory.inventory_id,
        "completed_requests": completed_requests,
        "page_count": page_count,
        "row_count": row_count,
        "payload_hashes": payload_hashes,
    }
    summary_id = content_hash(summary_body)
    _write_immutable(RUNTIME / "governance" / f"acquisition-summary-{summary_id}.json", {"summary_id": summary_id, **summary_body})
    print(f"INVENTORY_ID={inventory.inventory_id} REQUESTS={completed_requests} PAGES={page_count} ROWS={row_count} SUMMARY_ID={summary_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
