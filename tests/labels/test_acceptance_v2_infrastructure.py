import ast
from pathlib import Path

import pytest

from scripts.build_phase2a_acceptance_v2_infrastructure import build_infrastructure


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "data/phase_2a/reference").is_dir(), reason="immutable evidence excluded")


def test_materializer_is_offline_deterministic_and_excludes_final_acceptance(tmp_path):
    first, second = tmp_path / "one", tmp_path / "two"
    one = build_infrastructure(ROOT, first)
    two = build_infrastructure(ROOT, second)
    assert one == two
    first_files = {x.name: x.read_bytes() for x in first.iterdir()}
    second_files = {x.name: x.read_bytes() for x in second.iterdir()}
    assert first_files == second_files
    assert len(first_files) == 6
    assert not any("Phase2AAcceptanceV2" in value.decode("utf-8") or "phase2a-acceptance-v2" in name for name, value in first_files.items())
    assert one["FINAL V2 ACCEPTANCE"] == "NOT RUN"
    assert one["READY FOR PHASE 2B"] == "NO"


def test_materializer_has_no_network_provider_or_final_resolver_call():
    path = ROOT / "scripts/build_phase2a_acceptance_v2_infrastructure.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imports |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert not any(name.startswith(("requests", "urllib", "v5_2.providers")) for name in imports)
    called = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert "resolve_phase2a_acceptance_v2" not in called
