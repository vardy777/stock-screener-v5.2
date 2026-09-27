"""The formal clean-room receipt must be exact, complete and nonlocal."""

from dataclasses import replace

import pytest

from v5_2.labels.phase2b_cleanroom_gate_v2 import (
    CleanRoomCommandV2, CleanRoomEvidenceV2,
    read_cleanroom_evidence_exact, write_cleanroom_evidence,
)


def test_cleanroom_receipt_rejects_missing_phase_failure_and_local_path(tmp_path):
    names = ("LOCAL_CLONE", "FRESH_ENV", "INSTALL_LOCK", "INSTALL_PROJECT",
             "STAGE_PRIVATE_CAS", "PRIVATE_CAS_REPLAY", "STANDALONE",
             "ORDINARY_CLEAN_ROOM", "BUILD_WHEEL")
    commands = tuple(CleanRoomCommandV2(name, 0, "a" * 64) for name in names)
    evidence = CleanRoomEvidenceV2.create(
        repository_commit="b" * 40,
        corpus_manifest_id="0489978b34834817ee0e33dbd46d4e90b86a14e9827f89ba5b93433797c2ddd6",
        inventory_hash="a559e02eb8726289bb19c80daa37f78c8041e58bf6884d6c92c382da91ab6536",
        python_version="3.11.15", requirements_sha256="c" * 64,
        wheel_content_hash="d" * 64, commands=commands,
        reproduced_partition_id="3c194baf309486c16dd8f7f9e1916f4a1a4af49c9b108bcc06ce693eee615ba9",
        reproduced_integration_id="df54c5a80093115d469ec0257127ecd59c304f7c6d440ad2dc8bd4b85d641f67")
    assert evidence.verify()
    path = write_cleanroom_evidence(tmp_path, evidence)
    assert read_cleanroom_evidence_exact(path, evidence.evidence_id) == evidence
    assert not replace(evidence, commands=commands[:-1]).verify()
    assert not replace(evidence, commands=commands[:-1] + (
        CleanRoomCommandV2("BUILD_WHEEL", 1, "a" * 64),)).verify()
    assert not replace(evidence, python_version=r"C:\\Users\\private\\python.exe").verify()
    with pytest.raises(ValueError):
        read_cleanroom_evidence_exact(path, "0" * 64)
