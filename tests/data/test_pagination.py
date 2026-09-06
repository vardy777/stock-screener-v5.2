from __future__ import annotations

from pathlib import Path

import pytest

from v5_2.data.acquisition import AcquisitionError, acquire_pages
from v5_2.data.checkpoints import CheckpointStore, CheckpointV1
from v5_2.data.raw_artifacts import RawArtifactStore, RawPayloadArtifactV1
from v5_2.providers.contracts import ProviderRequestV1
from v5_2.providers.credentials import load_tushare_credential
from v5_2.providers.tushare import ProviderPageV1


def request() -> ProviderRequestV1:
    return ProviderRequestV1.create(
        source_name="synthetic",
        dataset_kind="synthetic_daily_bar",
        endpoint="fixture",
        parameters={},
        requested_fields=("id",),
        page_size=2,
        request_policy_version="request-v1",
    )


class FakeClient:
    def __init__(self, rows: list[dict[str, object]], wrong_identity: bool = False) -> None:
        self.rows = rows
        self.offsets: list[int] = []
        self.wrong_identity = wrong_identity

    def fetch_page(self, req, credential, *, page_identity):
        offset = page_identity["offset"]
        self.offsets.append(offset)
        returned_offset = offset + 1 if self.wrong_identity else offset
        return ProviderPageV1(
            request_id=req.request_id,
            page_identity={"offset": returned_offset},
            response_code=0,
            response_status="ok",
            rows=tuple(self.rows[offset : offset + req.page_size]),
        )


def test_pagination_stops_on_short_page_and_checkpoints_each_page(tmp_path: Path) -> None:
    client = FakeClient([{"id": value} for value in range(5)])
    artifacts = acquire_pages(
        request=request(),
        client=client,
        credential=load_tushare_credential(env={"TUSHARE_TOKEN": "sentinel"}),
        raw_store=RawArtifactStore(tmp_path),
        checkpoint_store=CheckpointStore(tmp_path),
        acquisition_policy_version="acquisition-v1",
    )
    assert client.offsets == [0, 2, 4]
    assert len(artifacts) == 3
    assert CheckpointStore(tmp_path).load(request().request_id).next_offset == 5


def test_resume_starts_at_checkpoint_next_offset(tmp_path: Path) -> None:
    raw_store = RawArtifactStore(tmp_path)
    prior = RawPayloadArtifactV1.create(
        request_id=request().request_id,
        page_identity={"offset": 0},
        provider_payload={"rows": ({"id": 0}, {"id": 1})},
        semantic_metadata={"response_code": 0, "response_status": "ok"},
    )
    raw_store.put_payload("synthetic", "synthetic_daily_bar", prior)
    CheckpointStore(tmp_path).save(
        CheckpointV1.create(
            request_id=request().request_id,
            accepted_payload_hashes=(prior.payload_hash,),
            next_offset=2,
            request_policy_version="request-v1",
            acquisition_policy_version="acquisition-v1",
        )
    )
    client = FakeClient([{"id": value} for value in range(3)])
    acquire_pages(
        request=request(),
        client=client,
        credential=load_tushare_credential(env={"TUSHARE_TOKEN": "sentinel"}),
        raw_store=raw_store,
        checkpoint_store=CheckpointStore(tmp_path),
        acquisition_policy_version="acquisition-v1",
        resume=True,
    )
    assert client.offsets == [2]


def test_resume_rejects_checkpoint_with_missing_raw_artifact(tmp_path: Path) -> None:
    CheckpointStore(tmp_path).save(
        CheckpointV1.create(
            request_id=request().request_id,
            accepted_payload_hashes=("f" * 64,),
            next_offset=2,
            request_policy_version="request-v1",
            acquisition_policy_version="acquisition-v1",
        )
    )
    with pytest.raises(AcquisitionError, match="missing raw artifact"):
        acquire_pages(
            request=request(),
            client=FakeClient([]),
            credential=load_tushare_credential(env={"TUSHARE_TOKEN": "sentinel"}),
            raw_store=RawArtifactStore(tmp_path),
            checkpoint_store=CheckpointStore(tmp_path),
            acquisition_policy_version="acquisition-v1",
            resume=True,
        )


def test_nonmatching_page_identity_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(AcquisitionError, match="page identity"):
        acquire_pages(
            request=request(),
            client=FakeClient([{"id": 1}], wrong_identity=True),
            credential=load_tushare_credential(env={"TUSHARE_TOKEN": "sentinel"}),
            raw_store=RawArtifactStore(tmp_path),
            checkpoint_store=CheckpointStore(tmp_path),
            acquisition_policy_version="acquisition-v1",
        )
