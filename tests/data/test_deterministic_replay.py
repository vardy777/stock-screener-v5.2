from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from v5_2.data.acquisition import AcquisitionControls, acquire_pages
from v5_2.data.checkpoints import CheckpointStore
from v5_2.data.normalization import NormalizerRegistry
from v5_2.data.raw_artifacts import RawArtifactStore
from v5_2.providers.contracts import ProviderRequestV1
from v5_2.providers.credentials import load_tushare_credential
from v5_2.providers.rate_limit import RateLimiter
from v5_2.providers.retry import RetryPolicyV1
from v5_2.providers.tushare import ProviderPageV1


class ReplayClient:
    def fetch_page(self, request, credential, *, page_identity):
        rows = ({"id": "B", "value": 2}, {"id": "A", "value": 1})
        return ProviderPageV1(
            request.request_id, page_identity, 0, "ok", rows
        )


def replay(root: Path, acquired_at: datetime):
    request = ProviderRequestV1.create(
        source_name="synthetic",
        dataset_kind="synthetic_replay",
        endpoint="fixture",
        parameters={},
        requested_fields=("id", "value"),
        page_size=10,
        request_policy_version="request-v1",
    )
    artifacts = acquire_pages(
        request=request,
        client=ReplayClient(),
        credential=load_tushare_credential(env={"TUSHARE_TOKEN": "sentinel"}),
        raw_store=RawArtifactStore(root),
        checkpoint_store=CheckpointStore(root),
        acquisition_policy_version="acquisition-v1",
        controls=AcquisitionControls(
            RetryPolicyV1(1, 0.0, 0.0, "retry-v1"),
            RateLimiter(min_interval_seconds=0.0),
            lambda: 0.0,
            lambda _: None,
            lambda: acquired_at,
        ),
    )
    normalizers = NormalizerRegistry()
    normalizers.register(
        dataset_kind="synthetic_replay",
        normalizer=lambda artifact: artifact.provider_payload["rows"],
        output_fields=("id", "value"),
        key_fields=("id",),
        normalizer_version="normalizer-v1",
    )
    normalized = normalizers.normalize("synthetic_replay", artifacts[0])
    checkpoint = CheckpointStore(root).load(request.request_id)
    receipts = tuple((root / "receipts").rglob("*.json"))
    return artifacts, normalized, checkpoint, receipts


def test_replay_identity_ignores_acquisition_observation_time(tmp_path: Path) -> None:
    first = replay(tmp_path / "first", datetime(2026, 1, 1, tzinfo=timezone.utc))
    second = replay(tmp_path / "second", datetime(2026, 2, 1, tzinfo=timezone.utc))
    assert tuple(item.payload_hash for item in first[0]) == tuple(
        item.payload_hash for item in second[0]
    )
    assert first[1] == second[1]
    assert first[2].checkpoint_hash == second[2].checkpoint_hash
    assert first[3][0].name != second[3][0].name
