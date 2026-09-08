import json

import pytest

from v5_2.data.real_audits.pinned_artifacts import document_sha256, load_pinned_json


def test_document_bytes_use_raw_sha256_identity() -> None:
    assert document_sha256(b"official evidence") == "d16e5d73662be9dd7855b7404eb385ffcb7604a3a709edfeb5501977eef923c8"


def test_load_pinned_json_rejects_wrong_schema_or_identity(tmp_path) -> None:
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps({"schema_version": "V2", "inventory_id": "expected"}), encoding="utf-8")
    assert load_pinned_json(path, schema_version="V2", identity_field="inventory_id",
                            expected_identity="expected")["inventory_id"] == "expected"
    with pytest.raises(ValueError, match="schema"):
        load_pinned_json(path, schema_version="V1", identity_field="inventory_id", expected_identity="expected")
    with pytest.raises(ValueError, match="identity"):
        load_pinned_json(path, schema_version="V2", identity_field="inventory_id", expected_identity="other")
