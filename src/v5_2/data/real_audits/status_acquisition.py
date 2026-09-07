from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

from v5_2.data.acquisition import AcquisitionControls, PageClient, acquire_pages
from v5_2.data.checkpoints import CheckpointStore
from v5_2.data.raw_artifacts import RawArtifactStore
from v5_2.providers.contracts import ProviderRequestV1
from v5_2.providers.credentials import Credential
from v5_2.providers.rate_limit import RateLimiter
from v5_2.providers.retry import RetryPolicyV1


ACQUISITION_POLICY_VERSION = "phase-1b2a-status-acquisition-v1"


@dataclass(frozen=True, slots=True)
class StatusAcquisitionResultV1:
    completed_requests: int
    page_count: int
    row_count: int
    payload_hashes: tuple[str, ...]


def acquire_status_requests(
    requests: Sequence[ProviderRequestV1],
    *,
    client: PageClient,
    credential: Credential,
    raw_store: RawArtifactStore,
    checkpoint_store: CheckpointStore,
    rate_limiter: RateLimiter,
    utc_clock: Callable[[], datetime],
    resume: bool,
    monotonic_clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> StatusAcquisitionResultV1:
    controls = AcquisitionControls(
        retry_policy=RetryPolicyV1(
            max_attempts=3,
            base_delay_seconds=1.0,
            max_delay_seconds=4.0,
            policy_version=ACQUISITION_POLICY_VERSION,
        ),
        rate_limiter=rate_limiter,
        monotonic_clock=monotonic_clock,
        sleeper=sleeper,
        utc_clock=utc_clock,
    )
    completed_requests = 0
    page_count = 0
    row_count = 0
    payload_hashes: list[str] = []
    for request in requests:
        checkpoint_exists = checkpoint_store.exists(request.request_id)
        pages = acquire_pages(
            request=request,
            client=client,
            credential=credential,
            raw_store=raw_store,
            checkpoint_store=checkpoint_store,
            acquisition_policy_version=ACQUISITION_POLICY_VERSION,
            controls=controls,
            resume=resume and checkpoint_exists,
        )
        completed_requests += 1
        page_count += len(pages)
        row_count += sum(len(page.provider_payload["rows"]) for page in pages)
        payload_hashes.extend(page.payload_hash for page in pages)
    return StatusAcquisitionResultV1(
        completed_requests=completed_requests,
        page_count=page_count,
        row_count=row_count,
        payload_hashes=tuple(payload_hashes),
    )
