import json

import pytest

from v5_2.foundations.core import ContractViolation
from v5_2.foundations.immutable_facts import (
    ImmutableFactStore,
    canonical_json,
    content_id,
)


def test_canonical_json_and_content_id_are_unicode_and_order_stable():
    left = {"name": "浦发银行", "symbol": "600000"}
    right = {"symbol": "600000", "name": "浦发银行"}
    assert canonical_json(left) == canonical_json(right)
    assert "浦发银行" in canonical_json(left)
    assert content_id("fact", left) == content_id("fact", right)


def test_immutable_store_is_idempotent_and_rejects_conflict_or_tampering(tmp_path):
    store = ImmutableFactStore(tmp_path)
    payload = {"fact_id": "fact-1", "value": 3}
    path = store.save("facts/fact-1.json", payload)
    assert store.save("facts/fact-1.json", payload) == path
    with pytest.raises(ContractViolation):
        store.save("facts/fact-1.json", {"fact_id": "fact-1", "value": 4})
    path.write_text(json.dumps({"fact_id": "fact-1", "value": 9}), encoding="utf-8")
    with pytest.raises(ContractViolation):
        store.load("facts/fact-1.json", expected=payload)


def test_immutable_store_rejects_escape_from_repository_root(tmp_path):
    store = ImmutableFactStore(tmp_path / "facts")
    with pytest.raises(ContractViolation):
        store.save("../escape.json", {"value": 1})
