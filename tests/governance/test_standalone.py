from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

import v5_2


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_MODULES = {"g1", "v2", "v4", "v5", "v5_1", "shared_core"}
FORBIDDEN_ROOTS = {
    ".hermes", "g1", "v2", "v4", "v5", "v5_1", "shared_core",
    "V5_1_RC1.zip", "V5_1_RC2.zip",
}


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def test_package_hard_gates():
    assert v5_2.__version__ == "5.2.0"
    assert v5_2.RESEARCH_LOCKED is True
    assert v5_2.BROKER_ORDERS_ENABLED is False


def test_forbidden_imports_use_exact_module_names():
    source_files = list((ROOT / "src" / "v5_2").rglob("*.py"))
    assert source_files
    for path in source_files:
        assert imported_roots(path).isdisjoint(FORBIDDEN_MODULES), path
    assert "v5_2" not in FORBIDDEN_MODULES


def test_forbidden_active_paths_and_dependencies():
    old_absolute = "c:" + chr(92) + "users" + chr(92) + "lisha" + chr(92) + "stock-screener"
    active = [ROOT / "pyproject.toml", ROOT / "requirements.lock"]
    active += list((ROOT / "src").rglob("*")) + list((ROOT / "tests").rglob("*.py"))
    patterns = [
        old_absolute,
        ".." + "/stock-screener",
        "file" + "://",
        "-" + "e ",
        "@ " + "git+",
    ]
    for path in active:
        generated = any(part == "__pycache__" or part.endswith(".egg-info") for part in path.parts)
        if not path.is_file() or generated:
            continue
        text = path.read_text(encoding="utf-8").lower()
        assert not any(pattern in text for pattern in patterns), path


def test_repository_inventory_excludes_legacy_projects():
    names = {path.name for path in ROOT.iterdir()}
    assert names.isdisjoint(FORBIDDEN_ROOTS)
    prohibited = re.compile(r"(?i)(pushplus|register.*task|runtime[_ -]?facts|credentials?)")
    tracked_candidates = [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]
    assert not [p for p in tracked_candidates if prohibited.search(p.name)]


def test_project_configuration_is_self_contained():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "stock-screener-v5-2"' in pyproject
    assert 'package-dir = {"" = "src"}' in pyproject
    assert "dependencies = []" in pyproject
    assert "setuptools==" in (ROOT / "requirements.lock").read_text(encoding="utf-8")
    assert (ROOT / "README.md").is_file()
    assert (ROOT / "AGENTS.md").is_file()


def test_raw_cache_ignore_rule_does_not_hide_source_packages():
    source_probe = "src/v5_2/data/identity.py"
    raw_probe = "data/raw/tushare/page.json"
    source = subprocess.run(
        ["git", "check-ignore", "-q", source_probe], cwd=ROOT, check=False
    )
    raw = subprocess.run(
        ["git", "check-ignore", "-q", raw_probe], cwd=ROOT, check=False
    )
    assert source.returncode == 1
    assert raw.returncode == 0
