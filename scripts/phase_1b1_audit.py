from __future__ import annotations

import argparse
from datetime import datetime, timezone
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
from v5_2.integrations.datahub_http import DataHubHttpTransport  # noqa: E402
from v5_2.providers.credentials import load_datahub_credential  # noqa: E402
from v5_2.providers.datahub import DataHubClient  # noqa: E402
from v5_2.providers.rate_limit import RateLimiter  # noqa: E402
from v5_2.providers.retry import RetryPolicyV1  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="V5.2 Phase 1B-1 raw source audit")
    parser.add_argument(
        "dataset", choices=("preflight", "trade_calendar", "security_master")
    )
    parser.add_argument("--resume", action="store_true")
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
    pages = 0
    rows = 0
    for request in phase_1b1_requests()[args.dataset]:
        artifacts = acquire_pages(
            request=request,
            client=client,
            credential=credential,
            raw_store=raw_store,
            checkpoint_store=checkpoints,
            acquisition_policy_version="datahub-acquisition-v1",
            controls=controls,
            resume=args.resume,
        )
        pages += len(artifacts)
        rows += sum(len(item.provider_payload["rows"]) for item in artifacts)
    print(f"DATASET={args.dataset} RAW_ACQUISITION=PASS PAGES={pages} ROWS={rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
