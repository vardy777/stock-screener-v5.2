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
from v5_2.data.real_audits.daily_bar_entry import build_acquisition_plan  # noqa: E402
from v5_2.integrations.datahub_http import DataHubHttpTransport  # noqa: E402
from v5_2.providers.credentials import load_datahub_credential  # noqa: E402
from v5_2.providers.datahub import DataHubClient  # noqa: E402
from v5_2.providers.rate_limit import RateLimiter  # noqa: E402
from v5_2.providers.retry import RetryPolicyV1  # noqa: E402


RUNTIME = ROOT / "data" / "phase_1b1"
GOVERNANCE = RUNTIME / "governance"
UNIVERSE_ID = "2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01"
INVENTORY_ID = "9b1d034f00ab0d637bc56ab120ffcf725f226f21c09d27c3b85e36a4f644a6ce"
UPSTREAM = (
    "1581b4d367dba1256247ddd13e09b53d0f95b5b1deeb40af9e6ed4a36606353b",
    "f208c17accba6b669359f476b2fdf3a1bc9ec6856e7fa1831ccdd1c42b80d8cf",
)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    universe = load(GOVERNANCE / f"daily-bar-universe-{UNIVERSE_ID}.json")
    inventory = load(GOVERNANCE / f"daily-bar-request-inventory-{INVENTORY_ID}.json")
    plan = build_acquisition_plan(universe, inventory, active_approval_ids=UPSTREAM, revoked_approval_ids=())
    selected = (plan.requests[0], plan.requests[len(plan.requests) // 2], plan.requests[-1])
    store = RawArtifactStore(RUNTIME)
    client = DataHubClient(transport=DataHubHttpTransport(timeout_seconds=30))
    credential = load_datahub_credential(env={}, env_file=ROOT / ".env", repository_root=ROOT)
    controls = AcquisitionControls(
        retry_policy=RetryPolicyV1(3, 1.0, 4.0, "datahub-retry-v1"),
        rate_limiter=RateLimiter(min_interval_seconds=0.25), monotonic_clock=time.monotonic,
        sleeper=time.sleep, utc_clock=lambda: datetime.now(timezone.utc),
    )
    observations = []
    for selected_request in selected:
        request = selected_request.provider_request
        checkpoint = load(RUNTIME / "checkpoints" / f"{request.request_id}.json")
        previous = tuple(checkpoint["accepted_payload_hashes"])
        before_receipts = set((RUNTIME / "receipts").rglob("*.json"))
        replayed = acquire_pages(
            request=request, client=client, credential=credential, raw_store=store,
            checkpoint_store=CheckpointStore(RUNTIME), acquisition_policy_version="datahub-acquisition-v1",
            controls=controls, resume=False,
        )
        current = tuple(item.payload_hash for item in replayed)
        after_receipts = set((RUNTIME / "receipts").rglob("*.json"))
        observations.append({
            "logical_request_id": selected_request.logical_request_id,
            "request_id": request.request_id,
            "previous_payload_hashes": previous,
            "replayed_payload_hashes": current,
            "same_payload_identity": previous == current,
            "new_receipt_count": len(after_receipts - before_receipts),
        })
    body = {
        "schema_version": "DailyBarRealReplayEvidenceV1",
        "sample_policy_id": "first-middle-last-v1", "observations": observations,
        "same_payload_different_receipt_pass": all(
            item["same_payload_identity"] and item["new_receipt_count"] >= 1 for item in observations
        ),
        "revision_detection_contract": "covered by synthetic changed-payload contract test",
        "observed_at": datetime.now(timezone.utc),
    }
    body["content_hash"] = content_hash(body)
    body["evidence_id"] = body["content_hash"]
    output = GOVERNANCE / f"daily-bar-replay-{body['evidence_id']}.json"
    output.write_bytes(canonical_json(body))
    print(json.dumps(body, indent=2, default=str))
    print(f"ARTIFACT={output.name}")
    return 0 if body["same_payload_different_receipt_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
