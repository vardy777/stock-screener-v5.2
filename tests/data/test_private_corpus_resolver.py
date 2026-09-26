"""Only manifest-pinned private bytes may enter a clean checkout."""

from dataclasses import replace
from hashlib import sha256
import os
from pathlib import Path
import subprocess

import pytest

from v5_2.data.private_corpus_manifest import (
    Phase2BPrivateCorpusManifestV1, PrivateCorpusEntryV1, read_manifest_exact,
)
from v5_2.data.private_corpus_resolver import (
    assert_private_objects_unreachable_from_refs, assert_private_objects_untracked,
    populate_private_cas,
    stage_verified_private_corpus,
)


ROLE = "data/replay_status_authority/authority/frozen.json"
PAYLOAD = b'{"frozen":true}'


def fixture_manifest():
    item = PrivateCorpusEntryV1(ROLE, "daily_security_status",
        sha256(PAYLOAD).hexdigest(), len(PAYLOAD), "application/json",
        "a" * 64, "b" * 64, "c" * 64, "2010-01-04", "2025-12-31", True)
    return Phase2BPrivateCorpusManifestV1.create((item,))


def test_populate_then_stage_only_verified_physical_bytes(tmp_path):
    source, cas, checkout = (tmp_path / name for name in ("source", "cas", "checkout"))
    source_file = source / ROLE
    source_file.parent.mkdir(parents=True)
    source_file.write_bytes(PAYLOAD)
    manifest = fixture_manifest()
    assert populate_private_cas(manifest, source, cas) == (manifest.entries[0].sha256,)
    assert populate_private_cas(manifest, source, cas) == (manifest.entries[0].sha256,)
    staged = stage_verified_private_corpus(manifest, cas, checkout)
    assert staged == (checkout / ROLE,)
    assert staged[0].read_bytes() == PAYLOAD
    assert staged[0].stat().st_nlink == 1
    assert stage_verified_private_corpus(manifest, cas, checkout) == staged


def test_missing_or_tampered_cas_never_falls_back_to_source(tmp_path):
    manifest = fixture_manifest()
    checkout = tmp_path / "checkout"
    with pytest.raises(ValueError, match="PRIVATE_CORPUS_UNAVAILABLE"):
        stage_verified_private_corpus(manifest, tmp_path / "missing-cas", checkout)
    assert not (checkout / ROLE).exists()
    source = tmp_path / "source"
    source_file = source / ROLE
    source_file.parent.mkdir(parents=True)
    source_file.write_bytes(PAYLOAD)
    cas = tmp_path / "cas"
    populate_private_cas(manifest, source, cas)
    object_path = cas / "sha256" / manifest.entries[0].sha256[:2] / manifest.entries[0].sha256
    object_path.write_bytes(b"same-size-wrong"[:len(PAYLOAD)])
    with pytest.raises(ValueError, match="hash"):
        stage_verified_private_corpus(manifest, cas, checkout)
    assert not (checkout / ROLE).exists()


def test_population_rejects_changed_source_and_stage_rejects_existing_different_bytes(tmp_path):
    manifest = fixture_manifest()
    source = tmp_path / "source"
    source_file = source / ROLE
    source_file.parent.mkdir(parents=True)
    source_file.write_bytes(b"different bytes")
    with pytest.raises(ValueError, match="source"):
        populate_private_cas(manifest, source, tmp_path / "cas")
    source_file.write_bytes(PAYLOAD)
    cas = tmp_path / "cas"
    populate_private_cas(manifest, source, cas)
    checkout = tmp_path / "checkout"
    target = checkout / ROLE
    target.parent.mkdir(parents=True)
    target.write_bytes(b"wrong")
    with pytest.raises(ValueError, match="collision"):
        stage_verified_private_corpus(manifest, cas, checkout)


def test_accidentally_tracked_private_object_is_rejected(tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    subprocess.run(("git", "init", str(repository)), check=True, capture_output=True)
    target = repository / ROLE
    target.parent.mkdir(parents=True)
    target.write_bytes(PAYLOAD)
    subprocess.run(("git", "-C", str(repository), "add", ROLE),
                   check=True, capture_output=True)
    with pytest.raises(ValueError, match="tracked"):
        assert_private_objects_untracked(fixture_manifest(), repository)


def test_staged_private_bytes_rejected_even_if_worktree_changed(tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    subprocess.run(("git", "init", str(repository)), check=True, capture_output=True)
    target = repository / "disguised.txt"
    target.write_bytes(PAYLOAD)
    subprocess.run(("git", "-C", str(repository), "add", "disguised.txt"),
                   check=True, capture_output=True)
    target.write_bytes(b"innocent worktree bytes")
    with pytest.raises(ValueError, match="tracked"):
        assert_private_objects_untracked(fixture_manifest(), repository)


def test_real_private_corpus_is_absent_from_git_index():
    root = Path(__file__).resolve().parents[2]
    if not (root / ".git").exists():
        pytest.skip("Git ref hygiene requires an actual checkout")
    manifest_id = "0489978b34834817ee0e33dbd46d4e90b86a14e9827f89ba5b93433797c2ddd6"
    path = root / "governance" / "phase2b" / f"private-corpus-manifest-{manifest_id}.json"
    manifest = read_manifest_exact(path, manifest_id)
    assert_private_objects_untracked(manifest, root)
    assert_private_objects_unreachable_from_refs(manifest, root)


def test_other_ref_reaching_private_blob_is_rejected(tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    subprocess.run(("git", "init", str(repository)), check=True, capture_output=True)
    subprocess.run(("git", "-C", str(repository), "config", "user.name", "Test"),
                   check=True, capture_output=True)
    subprocess.run(("git", "-C", str(repository), "config", "user.email", "test@local"),
                   check=True, capture_output=True)
    target = repository / "hidden.bin"
    target.write_bytes(PAYLOAD)
    subprocess.run(("git", "-C", str(repository), "add", "hidden.bin"),
                   check=True, capture_output=True)
    subprocess.run(("git", "-C", str(repository), "commit", "-m", "tainted"),
                   check=True, capture_output=True)
    subprocess.run(("git", "-C", str(repository), "branch", "tainted"),
                   check=True, capture_output=True)
    subprocess.run(("git", "-C", str(repository), "switch", "--orphan", "clean"),
                   check=True, capture_output=True)
    (repository / "clean.txt").write_bytes(b"safe")
    subprocess.run(("git", "-C", str(repository), "add", "clean.txt"),
                   check=True, capture_output=True)
    subprocess.run(("git", "-C", str(repository), "commit", "-m", "clean tree"),
                   check=True, capture_output=True)
    clean_objects = subprocess.run(("git", "-C", str(repository), "rev-list",
                                    "--objects", "clean"), capture_output=True,
                                   check=True).stdout
    assert b"hidden.bin" not in clean_objects
    assert_private_objects_untracked(fixture_manifest(), repository)
    with pytest.raises(ValueError, match="reachable"):
        assert_private_objects_unreachable_from_refs(fixture_manifest(), repository)
