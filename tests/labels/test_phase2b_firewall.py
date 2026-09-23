import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "phase2b_standalone_verifier", ROOT / "scripts" / "verify_standalone.py"
)
assert SPEC and SPEC.loader
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


def _plant(tmp_path: Path, relative: str, source: str) -> None:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_feature_namespace_rejects_label_values_future_bundles_and_reason_codes(tmp_path):
    _plant(tmp_path, "src/v5_2/features/returns.py", "from v5_2.labels.dataset_contracts import LabelRowV1\n")
    assert "feature label boundary" in verifier.scan_phase2b_firewall(tmp_path)[0]
    _plant(tmp_path, "src/v5_2/features/returns.py", "from v5_2.labels.contracts import LabelInputBundleV1, LabelReasonCode\n")
    assert "feature label boundary" in verifier.scan_phase2b_firewall(tmp_path)[0]
    _plant(tmp_path, "src/v5_2/features/returns.py", "import v5_2.labels.partition_store\n")
    assert "feature label boundary" in verifier.scan_phase2b_firewall(tmp_path)[0]
    _plant(tmp_path, "src/v5_2/features/returns.py", "from v5_2 import labels\n")
    assert "feature label boundary" in verifier.scan_phase2b_firewall(tmp_path)[0]


def test_materialization_and_evidence_assembler_reject_provider_imports(tmp_path):
    _plant(tmp_path, "src/v5_2/labels/materializer.py", "from v5_2.providers import datahub\n")
    assert "materialization provider boundary" in verifier.scan_phase2b_firewall(tmp_path)[0]
    _plant(tmp_path, "src/v5_2/labels/materializer.py", "from datetime import date\n")
    _plant(tmp_path, "src/v5_2/data/label_evidence_assembler.py", "import v5_2.integrations.datahub_http\n")
    assert "materialization provider boundary" in verifier.scan_phase2b_firewall(tmp_path)[0]


def test_feature_and_materialization_sources_pass_static_firewall():
    assert verifier.scan_phase2b_firewall(ROOT) == []
