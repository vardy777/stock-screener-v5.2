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


@dataclass(frozen=True, slots=True)
class CorporateActionAcquisitionResultV1:
    completed_requests: int
    page_count: int
    row_count: int
    payload_hashes: tuple[str, ...]


def acquire_corporate_action_requests(
    requests: Sequence[ProviderRequestV1], *, client: PageClient, credential: Credential,
    raw_store: RawArtifactStore, checkpoint_store: CheckpointStore, limiter: RateLimiter,
    utc_clock: Callable[[], datetime], resume: bool,
    monotonic_clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> CorporateActionAcquisitionResultV1:
    controls = AcquisitionControls(
        retry_policy=RetryPolicyV1(max_attempts=3, base_delay_seconds=1.0,
                                  max_delay_seconds=4.0,
                                  policy_version="phase-1b2c-acquisition-v1"),
        rate_limiter=limiter, monotonic_clock=monotonic_clock,
        sleeper=sleeper, utc_clock=utc_clock,
    )
    pages = []
    for request in requests:
        pages.extend(acquire_pages(
            request=request, client=client, credential=credential, raw_store=raw_store,
            checkpoint_store=checkpoint_store,
            acquisition_policy_version="phase-1b2c-acquisition-v1",
            controls=controls, resume=resume and checkpoint_store.exists(request.request_id),
        ))
    return CorporateActionAcquisitionResultV1(
        completed_requests=len(requests), page_count=len(pages),
        row_count=sum(len(page.provider_payload["rows"]) for page in pages),
        payload_hashes=tuple(page.payload_hash for page in pages),
    )
