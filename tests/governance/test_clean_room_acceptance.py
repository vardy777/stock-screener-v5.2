from __future__ import annotations

import importlib.util
import io
import tarfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "clean_room_acceptance", ROOT / "scripts" / "clean_room_acceptance.py"
)
assert SPEC and SPEC.loader
acceptance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acceptance)


def test_archive_scan_rejects_legacy_or_secret_members(tmp_path):
    archive = tmp_path / "bad.whl"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("v5_2/__init__.py", "")
        handle.writestr(".hermes/config.json", "{}")
    findings = acceptance.scan_archive(archive)
    assert findings == [".hermes/config.json"]


def test_archive_scan_allows_v5_2_package_name(tmp_path):
    archive = tmp_path / "good.whl"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("v5_2/__init__.py", "")
        handle.writestr("stock_screener_v5_2-5.2.0.dist-info/METADATA", "")
    assert acceptance.scan_archive(archive) == []


def test_archive_scan_allows_only_the_credential_contract_module(tmp_path):
    archive = tmp_path / "contracts.whl"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("v5_2/providers/credentials.py", "")
    assert acceptance.scan_archive(archive) == []

    bad_archive = tmp_path / "secret.whl"
    with zipfile.ZipFile(bad_archive, "w") as handle:
        handle.writestr("v5_2/providers/credentials.json", "{}")
    assert acceptance.scan_archive(bad_archive) == [
        "v5_2/providers/credentials.json"
    ]


def test_sdist_scan_rejects_legacy_member(tmp_path):
    archive = tmp_path / "bad.tar.gz"
    payload = b"{}"
    with tarfile.open(archive, "w:gz") as handle:
        info = tarfile.TarInfo("project/.hermes/config.json")
        info.size = len(payload)
        handle.addfile(info, io.BytesIO(payload))
    assert acceptance.scan_archive(archive) == ["project/.hermes/config.json"]
