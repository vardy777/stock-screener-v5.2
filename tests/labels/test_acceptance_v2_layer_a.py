import json
from pathlib import Path

import pytest

from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import build_frozen_inventory
from v5_2.labels.acceptance_v2_contracts import EvidenceClass, build_frozen_amendment_v2
from v5_2.labels.acceptance_v2_layer_a import build_real_reference_coverage_ledger


ROOT = Path(__file__).resolve().parents[2]
LEDGER_ID = "0ee799a175a5e6832b9ca79d88ff9a0b9583ff92e204849274f96a031c397247"
pytestmark = pytest.mark.skipif(not (ROOT / "data/phase_2a/reference").is_dir(), reason="immutable evidence excluded")


def inputs():
    source = json.loads((ROOT / f"data/phase_2a/reference/full-engine-comparison-{LEDGER_ID}.json").read_text())
    inventory = build_frozen_inventory()
    assembler = Phase2AEvidenceAssemblerV1(ROOT)
    bundles = tuple(assembler.assemble(slot) for slot in inventory.slots if slot.slot not in {16, 17})
    return source, bundles


def test_builds_truthful_20_case_real_ledger_from_exact_checkpoint7_pin():
    source, bundles = inputs()
    result = build_real_reference_coverage_ledger(build_frozen_amendment_v2(), source, bundles)
    assert result.verify()
    assert result.checkpoint7_comparison_ledger_id == LEDGER_ID
    assert tuple(x.slot for x in result.cases) == (*range(1, 16), *range(18, 23))
    assert all(x.evidence_class is EvidenceClass.REAL_MARKET_EVIDENCE for x in result.cases)
    assert all(len(x.five_domain_lineage_ids) == 5 and x.disposition == "MATCH" for x in result.cases)
    assert "ACTUAL" in result.cases[-1].semantic_roles[0]


def test_rejects_wrong_pin_mismatch_and_synthetic_case():
    source, bundles = inputs()
    wrong = dict(source, ledger_id="0" * 64)
    with pytest.raises(ValueError, match="checkpoint7 comparison ledger"):
        build_real_reference_coverage_ledger(build_frozen_amendment_v2(), wrong, bundles)
    mismatch = json.loads(json.dumps(source)); mismatch["entries"][0]["disposition"] = "MISMATCH"
    with pytest.raises(ValueError):
        build_real_reference_coverage_ledger(build_frozen_amendment_v2(), mismatch, bundles)
