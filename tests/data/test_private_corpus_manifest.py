"""Public metadata pins private bytes without containing them."""

from dataclasses import replace
import os
from pathlib import Path

import pytest

from v5_2.data.private_corpus_manifest import (
    PrivateCorpusEntryV1, Phase2BPrivateCorpusManifestV1,
    build_manifest_exact, read_manifest_exact, write_manifest,
)


def entry(role="data/replay_status_authority/authority/status.json"):
    return PrivateCorpusEntryV1(
        logical_role=role, domain="daily_security_status", sha256="a" * 64,
        byte_size=3, media_type="application/json", authority_id="b" * 64,
        approval_id="c" * 64, dataset_manifest_id="d" * 64,
        coverage_start="2010-01-04", coverage_end="2025-12-31",
        required_for_checkpoint18=True,
    )


def test_exact_manifest_is_canonical_and_public_metadata_only(tmp_path):
    item = entry()
    manifest = Phase2BPrivateCorpusManifestV1.create((item,))
    assert manifest.verify()
    path = write_manifest(tmp_path, manifest)
    assert read_manifest_exact(path, manifest.manifest_id) == manifest
    payload = path.read_bytes()
    assert b"private-cas" not in payload and b"C:/" not in payload
    assert b'"sha256"' in payload and b'"byte_size":3' in payload
    with pytest.raises(ValueError):
        read_manifest_exact(path, "e" * 64)
    path.write_bytes(payload + b" ")
    with pytest.raises(ValueError):
        read_manifest_exact(path, manifest.manifest_id)


@pytest.mark.parametrize("role", (
    "../data/escape.json", "/absolute.json", "C:/machine/path.json",
    "data//double.json", "data/./relative.json", "data\\windows.json",
))
def test_unsafe_logical_role_fails_closed(role):
    with pytest.raises(ValueError):
        Phase2BPrivateCorpusManifestV1.create((entry(role),))


def test_duplicate_role_and_noncanonical_order_fail_closed():
    first = entry("data/a.json")
    second = replace(first, logical_role="data/b.json", sha256="f" * 64)
    with pytest.raises(ValueError):
        Phase2BPrivateCorpusManifestV1.create((first, first))
    with pytest.raises(ValueError):
        Phase2BPrivateCorpusManifestV1.create((second, first))


def test_unverified_or_wrong_size_entry_fails_closed():
    with pytest.raises(ValueError):
        Phase2BPrivateCorpusManifestV1.create((replace(entry(), byte_size=-1),))
    with pytest.raises(ValueError):
        Phase2BPrivateCorpusManifestV1.create((replace(entry(), sha256="a" * 63),))


@pytest.mark.skipif(os.environ.get("V5_2_REAL_PRIVATE_CORPUS") != "1",
                    reason="explicit approved local private corpus required")
def test_real_inventory_has_only_current_untracked_authority_bytes():
    root = Path(__file__).resolve().parents[2]
    manifest = build_manifest_exact(root)
    assert manifest.verify()
    assert len(manifest.entries) == 44
    assert sum(item.domain == "daily_security_status" for item in manifest.entries) == 38
    assert sum(item.domain == "corporate_action" for item in manifest.entries) == 4
    assert sum(item.domain == "trade_calendar" for item in manifest.entries) == 2
    assert all(item.domain != "security_master" for item in manifest.entries)
    assert all("ab963f9f" not in item.logical_role for item in manifest.entries)
