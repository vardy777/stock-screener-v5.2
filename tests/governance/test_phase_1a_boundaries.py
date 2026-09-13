from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "verify_standalone_phase1a", ROOT / "scripts" / "verify_standalone.py"
)
assert SPEC and SPEC.loader
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


def test_research_import_of_provider_or_raw_boundary_is_detected(tmp_path: Path) -> None:
    feature = tmp_path / "src" / "v5_2" / "features" / "bad.py"
    feature.parent.mkdir(parents=True)
    feature.write_text(
        "from v5_2.providers.credentials import Credential\n"
        "from v5_2.data.raw_artifacts import RawArtifactStore\n"
        "from v5_2.integrations.datahub_http import DataHubHttpTransport\n",
        encoding="utf-8",
    )
    findings = verifier.scan_phase1a_boundaries(tmp_path)
    assert len(findings) == 3
    assert all("research boundary" in finding for finding in findings)


def test_direct_network_client_import_is_detected(tmp_path: Path) -> None:
    provider = tmp_path / "src" / "v5_2" / "providers" / "bad.py"
    provider.parent.mkdir(parents=True)
    provider.write_text("import requests\nimport socket\n", encoding="utf-8")
    findings = verifier.scan_phase1a_boundaries(tmp_path)
    assert len(findings) == 2
    assert all("network client" in finding for finding in findings)


def test_only_allowlisted_integration_may_import_network_client(tmp_path: Path) -> None:
    allowed = tmp_path / "src" / "v5_2" / "integrations" / "datahub_http.py"
    allowed.parent.mkdir(parents=True)
    allowed.write_text("from urllib.request import urlopen\n", encoding="utf-8")
    assert verifier.scan_phase1a_boundaries(tmp_path) == []


def test_normalization_io_import_is_detected(tmp_path: Path) -> None:
    module = tmp_path / "src" / "v5_2" / "data" / "normalization.py"
    module.parent.mkdir(parents=True)
    module.write_text("from pathlib import Path\n", encoding="utf-8")
    assert "pure normalization" in verifier.scan_phase1a_boundaries(tmp_path)[0]


def test_current_repository_passes_phase_1a_boundaries() -> None:
    assert verifier.scan_phase1a_boundaries(ROOT) == []


def test_sentinel_scan_detects_secret_in_runtime_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "data" / "raw" / "page.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text('{"token":"V52_TEST_SECRET"}', encoding="utf-8")
    findings = verifier.scan_secret_leaks(tmp_path, ("V52_TEST_SECRET",))
    assert findings == ["data\\raw\\page.json: sentinel secret leak"]


def test_sentinel_scan_detects_secret_split_across_stream_chunks(tmp_path: Path, monkeypatch) -> None:
    artifact = tmp_path / "data" / "raw" / "large.bin"
    artifact.parent.mkdir(parents=True)
    sentinel = b"V52_BOUNDARY_SECRET"
    artifact.write_bytes(b"x" * (1024 * 1024 - 5) + sentinel)
    monkeypatch.setattr(Path, "read_bytes", lambda self: (_ for _ in ()).throw(
        AssertionError("secret scan must stream large runtime artifacts")))
    assert verifier.scan_secret_leaks(tmp_path, (sentinel.decode(),)) == [
        "data\\raw\\large.bin: sentinel secret leak"]


def test_current_runtime_areas_have_no_sentinel_leak() -> None:
    assert verifier.scan_secret_leaks(ROOT, ("SENTINEL_TUSHARE_SECRET",)) == []
