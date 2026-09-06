from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from v5_2.data.raw_artifacts import (
    AcquisitionReceiptV1,
    RawArtifactError,
    RawArtifactStore,
    RawPayloadArtifactV1,
    observe_revision,
)


def payload(close: float = 10.5) -> RawPayloadArtifactV1:
    return RawPayloadArtifactV1.create(
        request_id="a" * 64,
        page_identity={"offset": 0},
        provider_payload={"fields": ["ts_code", "close"], "rows": [["000001.SZ", close]]},
        semantic_metadata={"provider_api_version": "daily-v1"},
    )


def test_identical_reacquisition_has_same_payload_hash() -> None:
    assert payload().payload_hash == payload().payload_hash
    assert observe_revision(payload(), payload()) is False


def test_acquisition_time_changes_receipt_but_not_payload_identity() -> None:
    artifact = payload()
    first = AcquisitionReceiptV1.create(
        payload_hash=artifact.payload_hash,
        acquired_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        attempt_metadata={"attempt": 1},
        transport_metadata={"elapsed_ms": 10},
    )
    second = AcquisitionReceiptV1.create(
        payload_hash=artifact.payload_hash,
        acquired_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        attempt_metadata={"attempt": 1},
        transport_metadata={"elapsed_ms": 10},
    )
    assert first.payload_hash == second.payload_hash
    assert first.receipt_hash != second.receipt_hash


def test_changed_provider_payload_is_revision_observation() -> None:
    assert payload(10.5).payload_hash != payload(10.6).payload_hash
    assert observe_revision(payload(10.5), payload(10.6)) is True


def test_revision_comparison_rejects_different_logical_page() -> None:
    other = RawPayloadArtifactV1.create(
        request_id="a" * 64,
        page_identity={"offset": 100},
        provider_payload={"rows": []},
        semantic_metadata={},
    )
    with pytest.raises(RawArtifactError, match="logical page"):
        observe_revision(payload(), other)


def test_store_is_idempotent_and_verifies_round_trip(tmp_path: Path) -> None:
    store = RawArtifactStore(tmp_path)
    path = store.put_payload("tushare_pro", "daily_bar", payload())
    assert store.put_payload("tushare_pro", "daily_bar", payload()) == path
    assert store.read_payload(path).payload_hash == payload().payload_hash


def test_store_rejects_existing_path_with_different_content(tmp_path: Path) -> None:
    store = RawArtifactStore(tmp_path)
    path = store.payload_path("tushare_pro", "daily_bar", payload())
    path.parent.mkdir(parents=True)
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(RawArtifactError, match="collision"):
        store.put_payload("tushare_pro", "daily_bar", payload())


@pytest.mark.parametrize("forbidden", ["token", "credential", "authorization", "api_key"])
def test_artifacts_reject_secret_shaped_fields(forbidden: str) -> None:
    with pytest.raises(RawArtifactError, match="secret-shaped"):
        RawPayloadArtifactV1.create(
            request_id="a" * 64,
            page_identity={"offset": 0},
            provider_payload={forbidden: "value"},
            semantic_metadata={},
        )
