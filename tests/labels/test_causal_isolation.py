import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def python_files(relative: str):
    root = ROOT / relative
    return tuple(root.rglob("*.py")) if root.exists() else ()


def imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def future_fact_findings(paths):
    forbidden = ("LabelInputBundleV1", "LabelReferencePrice", "future_bars", "outcome_snapshot_id")
    return tuple((path, token) for path in paths for token in forbidden if token in path.read_text(encoding="utf-8"))


def engine_import_closure():
    """Scan the pure engine and its local imports, not offline evidence readers."""
    labels = ROOT / "src/v5_2/labels"
    pending = [labels / "engine.py"]
    visited = set()
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        for name in imports(path):
            if name.startswith("v5_2.labels."):
                dependency = labels / f"{name.rsplit('.', 1)[-1]}.py"
                if dependency.exists():
                    pending.append(dependency)
    return tuple(sorted(visited))


def forbidden_pure_engine_calls(paths):
    forbidden_calls = {"open", "Path", "getenv", "urlopen"}
    findings = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
                if name in forbidden_calls:
                    findings.append((path, name))
    return findings


def test_features_cannot_import_labels_or_label_only_types():
    findings = [(path, name) for path in python_files("src/v5_2/features") for name in imports(path) if name.startswith("v5_2.labels")]
    assert findings == []


def test_feature_sources_and_fixtures_cannot_contain_label_future_facts():
    paths = (*python_files("src/v5_2/features"), *python_files("tests/features"))
    assert future_fact_findings(paths) == ()


def test_label_engine_cannot_import_provider_integration_or_acquisition():
    forbidden = ("v5_2.providers", "v5_2.integrations", "v5_2.data.acquisition", "requests", "urllib")
    findings = [(path, name) for path in python_files("src/v5_2/labels") for name in imports(path) if name.startswith(forbidden)]
    assert findings == []


def test_label_engine_has_no_filesystem_network_environment_or_pointer_access():
    closure = engine_import_closure()
    assert {path.stem for path in closure} == {"engine", "calculation", "contracts"}
    assert forbidden_pure_engine_calls(closure) == []


def test_label_engine_forbidden_call_sentinel_is_detected(tmp_path):
    planted = tmp_path / "engine.py"
    planted.write_text("from pathlib import Path\nx = Path('current')", encoding="utf-8")
    assert forbidden_pure_engine_calls((planted,)) == [(planted, "Path")]


def test_future_fact_sentinel_is_detected(tmp_path):
    planted = tmp_path / "feature.py"
    planted.write_text("x = LabelReferencePrice", encoding="utf-8")
    assert future_fact_findings((planted,)) == ((planted, "LabelReferencePrice"),)
