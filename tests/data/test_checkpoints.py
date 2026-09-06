from __future__ import annotations

from pathlib import Path

import pytest

from v5_2.data.checkpoints import CheckpointError, CheckpointStore, CheckpointV1


def checkpoint(request_id: str = "a" * 64) -> CheckpointV1:
    return CheckpointV1.create(
        request_id=request_id,
        accepted_payload_hashes=("b" * 64, "c" * 64),
        next_offset=200,
        request_policy_version="request-v1",
        acquisition_policy_version="acquisition-v1",
    )


def test_checkpoint_round_trip_is_content_verified(tmp_path: Path) -> None:
    store = CheckpointStore(tmp_path)
    store.save(checkpoint())
    assert store.load("a" * 64) == checkpoint()


def test_checkpoint_tampering_fails_closed(tmp_path: Path) -> None:
    store = CheckpointStore(tmp_path)
    path = store.save(checkpoint())
    path.write_text(path.read_text(encoding="utf-8").replace("200", "201"), encoding="utf-8")
    with pytest.raises(CheckpointError, match="hash mismatch"):
        store.load("a" * 64)


def test_resume_rejects_request_or_policy_mismatch(tmp_path: Path) -> None:
    store = CheckpointStore(tmp_path)
    store.save(checkpoint())
    with pytest.raises(CheckpointError, match="request policy"):
        store.require_compatible("a" * 64, "request-v2", "acquisition-v1")
    with pytest.raises(CheckpointError, match="not found"):
        store.require_compatible("d" * 64, "request-v1", "acquisition-v1")
