from __future__ import annotations
import argparse
from dataclasses import asdict
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
from v5_2.data.real_audits.financial_disclosure_entry import build_financial_disclosure_inventory, run_bounded_retry_rounds  # noqa: E402
from v5_2.integrations.datahub_http import DataHubHttpTransport  # noqa: E402
from v5_2.providers.credentials import load_datahub_credential  # noqa: E402
from v5_2.providers.datahub import DataHubClient  # noqa: E402
from v5_2.providers.rate_limit import RateLimiter  # noqa: E402
from v5_2.providers.retry import RetryPolicyV1  # noqa: E402

RUNTIME = ROOT / "data" / "phase_1b2d"
HISTORICAL_UNIVERSE = "2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01"
UPSTREAM = ("4a900c7e4f2b171d7adac07088025ca4bb9fb0da13cfa1b15e91eff3dafea601",
            "828e0e722d3d66c84a48584aac14fde37f86cf471f3722f403ec19044f36345c")


def _write(path: Path, value: object) -> None:
    encoded = canonical_json(value); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded: raise RuntimeError("immutable financial artifact collision")
    if not path.exists(): path.write_bytes(encoded)


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--workers", type=int, default=24); parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    universe = json.loads((ROOT / "data" / "phase_1b1" / "governance" / f"daily-bar-universe-{HISTORICAL_UNIVERSE}.json").read_text(encoding="utf-8"))
    inventory = build_financial_disclosure_inventory(symbols=universe["ordered_symbols"], coverage_start="20100104",
        coverage_end="20260910", universe_id=HISTORICAL_UNIVERSE, upstream_approval_ids=UPSTREAM)
    inventory_body = {"schema_version": "FinancialDisclosureInventoryV1", "inventory_id": inventory.inventory_id,
        "content_hash": inventory.content_hash, "universe_id": inventory.universe_id, "upstream_approval_ids": inventory.upstream_approval_ids,
        "coverage_start": inventory.coverage_start, "coverage_end": inventory.coverage_end,
        "request_ids": tuple(request.request_id for request in inventory.requests), "request_count": len(inventory.requests)}
    _write(RUNTIME / "governance" / f"historical-inventory-{inventory.inventory_id}.json", inventory_body)
    credential = load_datahub_credential(env={}, env_file=ROOT / ".env", repository_root=ROOT)
    client, raw, checkpoints = DataHubClient(transport=DataHubHttpTransport(timeout_seconds=30)), RawArtifactStore(RUNTIME), CheckpointStore(RUNTIME)
    controls = AcquisitionControls(retry_policy=RetryPolicyV1(3, .5, 2.0, "financial-disclosure-retry-v1"),
        rate_limiter=RateLimiter(min_interval_seconds=0), monotonic_clock=time.monotonic, sleeper=time.sleep,
        utc_clock=lambda: datetime.now(timezone.utc))
    def acquire(request):
        return acquire_pages(request=request, client=client, credential=credential, raw_store=raw, checkpoint_store=checkpoints,
            acquisition_policy_version="financial-disclosure-acquisition-v1", controls=controls,
            resume=args.resume and checkpoints.exists(request.request_id))
    results = run_bounded_retry_rounds(inventory.requests, acquire, max_rounds=4, workers=args.workers)
    pages = [page for artifacts in results for page in artifacts]
    completed = len(results)
    body = {"schema_version": "FinancialDisclosureAcquisitionSummaryV1", "inventory_id": inventory.inventory_id,
        "completed_requests": completed, "page_count": len(pages),
        "raw_row_count": sum(len(page.provider_payload["rows"]) for page in pages),
        "payload_hashes": tuple(page.payload_hash for page in pages)}
    summary_id = content_hash(body); _write(RUNTIME / "governance" / f"acquisition-summary-{summary_id}.json",
        {"acquisition_summary_id": summary_id, "content_hash": summary_id, **body})
    (RUNTIME / "governance" / "current-acquisition-summary-id.txt").write_text(summary_id, encoding="ascii")
    print(f"FINANCIAL_ACQUISITION=PASS INVENTORY_ID={inventory.inventory_id} REQUESTS={completed} PAGES={len(pages)} ROWS={body['raw_row_count']} SUMMARY_ID={summary_id}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
