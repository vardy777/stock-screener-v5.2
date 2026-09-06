from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from v5_2.data.checkpoints import CheckpointStore, CheckpointV1
from v5_2.data.raw_artifacts import RawArtifactError, RawArtifactStore, RawPayloadArtifactV1
from v5_2.providers.contracts import ProviderRequestV1
from v5_2.providers.credentials import Credential
from v5_2.providers.rate_limit import RateLimiter
from v5_2.providers.retry import RetryPolicyV1
from v5_2.providers.tushare import ProviderPageV1


class AcquisitionError(RuntimeError):
    """Pagination cannot continue deterministically."""


class PageClient(Protocol):
    def fetch_page(
        self,
        request: ProviderRequestV1,
        credential: Credential,
        *,
        page_identity: dict[str, int],
    ) -> ProviderPageV1: ...


@dataclass(frozen=True, slots=True)
class AcquisitionControls:
    retry_policy: RetryPolicyV1
    rate_limiter: RateLimiter
    monotonic_clock: Callable[[], float]
    sleeper: Callable[[float], None]


def acquire_pages(
    *,
    request: ProviderRequestV1,
    client: PageClient,
    credential: Credential,
    raw_store: RawArtifactStore,
    checkpoint_store: CheckpointStore,
    acquisition_policy_version: str,
    controls: AcquisitionControls,
    resume: bool = False,
) -> tuple[RawPayloadArtifactV1, ...]:
    if resume:
        checkpoint = checkpoint_store.require_compatible(
            request.request_id,
            request.request_policy_version,
            acquisition_policy_version,
        )
        offset = checkpoint.next_offset
        accepted = list(checkpoint.accepted_payload_hashes)
        try:
            raw_store.require_payload_hashes(
                request.source_name,
                request.dataset_kind,
                request.request_id,
                checkpoint.accepted_payload_hashes,
            )
        except RawArtifactError:
            raise AcquisitionError("checkpoint references missing raw artifact") from None
    else:
        offset = 0
        accepted = []
    produced: list[RawPayloadArtifactV1] = []
    while True:
        expected_identity = {"offset": offset}
        controls.rate_limiter.acquire(controls.monotonic_clock, controls.sleeper)
        page = controls.retry_policy.run(
            lambda: client.fetch_page(
                request, credential, page_identity=expected_identity
            ),
            controls.sleeper,
        )
        if page.request_id != request.request_id or page.page_identity != expected_identity:
            raise AcquisitionError("provider page identity did not match request")
        artifact = RawPayloadArtifactV1.create(
            request_id=request.request_id,
            page_identity=expected_identity,
            provider_payload={"rows": page.rows},
            semantic_metadata={
                "response_code": page.response_code,
                "response_status": page.response_status,
            },
        )
        raw_store.put_payload(request.source_name, request.dataset_kind, artifact)
        produced.append(artifact)
        accepted.append(artifact.payload_hash)
        row_count = len(page.rows)
        next_offset = offset + row_count
        checkpoint_store.save(
            CheckpointV1.create(
                request_id=request.request_id,
                accepted_payload_hashes=tuple(accepted),
                next_offset=next_offset,
                request_policy_version=request.request_policy_version,
                acquisition_policy_version=acquisition_policy_version,
            )
        )
        if row_count < request.page_size:
            break
        if next_offset <= offset:
            raise AcquisitionError("pagination did not advance")
        offset = next_offset
    return tuple(produced)
