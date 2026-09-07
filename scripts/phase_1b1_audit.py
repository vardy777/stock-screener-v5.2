from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.acquisition import AcquisitionControls, acquire_pages  # noqa: E402
from v5_2.data.checkpoints import CheckpointStore  # noqa: E402
from v5_2.data.phase_1b1_requests import phase_1b1_requests  # noqa: E402
from v5_2.data.raw_artifacts import RawArtifactStore  # noqa: E402
from v5_2.data.real_source_preflight import run_datahub_preflight  # noqa: E402
from v5_2.data.real_audits.daily_bar_entry import build_acquisition_plan  # noqa: E402
from v5_2.integrations.datahub_http import DataHubHttpTransport  # noqa: E402
from v5_2.providers.credentials import load_datahub_credential  # noqa: E402
from v5_2.providers.datahub import DataHubClient  # noqa: E402
from v5_2.providers.rate_limit import RateLimiter  # noqa: E402
from v5_2.providers.retry import RetryPolicyV1  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="V5.2 Phase 1B-1 raw source audit")
    parser.add_argument(
        "dataset", choices=("preflight", "trade_calendar", "security_master", "daily_bar")
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=32)
    args = parser.parse_args()

    transport = DataHubHttpTransport(timeout_seconds=30)
    preflight = run_datahub_preflight(repository_root=ROOT, env={}, probe=transport)
    print(
        f"SOURCE={preflight.source_name} STATUS={preflight.status} "
        f"REASON={preflight.reason} TRANSPORT={preflight.transport_security}"
    )
    if preflight.status != "PASS":
        return 2
    if args.dataset == "preflight":
        return 0

    credential = load_datahub_credential(
        env={}, env_file=ROOT / ".env", repository_root=ROOT
    )
    client = DataHubClient(transport=transport)
    runtime_root = ROOT / "data" / "phase_1b1"
    raw_store = RawArtifactStore(runtime_root)
    checkpoints = CheckpointStore(runtime_root)
    controls = AcquisitionControls(
        retry_policy=RetryPolicyV1(3, 1.0, 4.0, "datahub-retry-v1"),
        rate_limiter=RateLimiter(min_interval_seconds=0.25),
        monotonic_clock=time.monotonic,
        sleeper=time.sleep,
        utc_clock=lambda: datetime.now(timezone.utc),
    )
    requests = phase_1b1_requests()[args.dataset]
    if args.dataset == "daily_bar":
        governance = runtime_root / "governance"
        universe = json.loads((governance / "daily-bar-universe-2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01.json").read_text(encoding="utf-8"))
        inventory = json.loads((governance / "daily-bar-request-inventory-9b1d034f00ab0d637bc56ab120ffcf725f226f21c09d27c3b85e36a4f644a6ce.json").read_text(encoding="utf-8"))
        plan = build_acquisition_plan(
            universe, inventory,
            active_approval_ids=("1581b4d367dba1256247ddd13e09b53d0f95b5b1deeb40af9e6ed4a36606353b", "f208c17accba6b669359f476b2fdf3a1bc9ec6856e7fa1831ccdd1c42b80d8cf"),
            revoked_approval_ids=(),
        )
        requests = tuple(item.provider_request for item in plan.requests)
        print(f"DAILY_BAR_PLAN={plan.plan_id} UNIVERSE={plan.universe_id} INVENTORY={plan.inventory_id} EXPECTED_REQUESTS={len(requests)}", flush=True)
    pages = 0
    rows = 0
    completed = 0
    def acquire_one(request):
        has_checkpoint = (runtime_root / "checkpoints" / f"{request.request_id}.json").is_file()
        return acquire_pages(
            request=request,
            client=client,
            credential=credential,
            raw_store=raw_store,
            checkpoint_store=checkpoints,
            acquisition_policy_version="datahub-acquisition-v1",
            controls=controls,
            resume=args.resume and has_checkpoint,
        )
    if args.workers < 1 or args.workers > 64:
        raise ValueError("workers must be between 1 and 64")
    if args.dataset == "daily_bar":
        with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="daily-bar") as executor:
            results = executor.map(acquire_one, requests)
            for artifacts in results:
                pages += len(artifacts)
                rows += sum(len(item.provider_payload["rows"]) for item in artifacts)
                completed += 1
                if completed % 100 == 0:
                    print(f"PROGRESS COMPLETED_REQUESTS={completed}/{len(requests)} PAGES={pages} ROWS={rows}", flush=True)
    else:
        for request in requests:
            artifacts = acquire_one(request)
            pages += len(artifacts)
            rows += sum(len(item.provider_payload["rows"]) for item in artifacts)
            completed += 1
    print(f"DATASET={args.dataset} RAW_ACQUISITION=PASS COMPLETED_REQUESTS={completed} PAGES={pages} ROWS={rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
