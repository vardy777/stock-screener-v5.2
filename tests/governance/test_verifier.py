from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("verify_standalone", ROOT / "scripts" / "verify_standalone.py")
assert SPEC and SPEC.loader
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


def test_import_scan_matches_exact_top_level_module(tmp_path):
    package = tmp_path / "src" / "v5_2"
    package.mkdir(parents=True)
    (package / "allowed.py").write_text("import v5_2\n", encoding="utf-8")
    assert verifier.scan_imports(tmp_path) == []
    (package / "blocked.py").write_text("from shared_core import calendar\n", encoding="utf-8")
    findings = verifier.scan_imports(tmp_path)
    assert len(findings) == 1
    assert "shared_core" in findings[0]


def test_inventory_and_active_path_scans_detect_prohibited_content(tmp_path):
    (tmp_path / ".hermes").mkdir()
    source = tmp_path / "src" / "v5_2"
    source.mkdir(parents=True)
    bad_value = ".." + "/stock-screener"
    (source / "bad.py").write_text(f"ROOT = '{bad_value}'\n", encoding="utf-8")
    assert verifier.scan_inventory(tmp_path)
    assert verifier.scan_active_paths(tmp_path)


def test_current_repository_passes_verifier():
    assert verifier.verify(ROOT) == []


def test_generated_egg_info_is_not_active_source(tmp_path):
    package = tmp_path / "src" / "v5_2"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    metadata = tmp_path / "src" / "stock_screener_v5_2.egg-info"
    metadata.mkdir()
    editable_example = "-" + "e ."
    (metadata / "PKG-INFO").write_text(f"editable example: {editable_example}", encoding="utf-8")
    assert verifier.scan_active_paths(tmp_path) == []
