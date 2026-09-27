"""The contract gate reads frozen authority, not caller-selected hashes."""

from pathlib import Path

import pytest

from v5_2.labels.phase2b_contract_pins_v2 import (
    derive_contract_pin_evidence_exact, read_contract_pin_evidence_exact,
    write_contract_pin_evidence,
)


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not (ROOT / "data/replay_status_authority/authority").is_dir(),
    reason="approved five-domain source artifacts are not installed",
)


def test_frozen_contract_pins_come_from_exact_immutable_artifacts(tmp_path):
    evidence = derive_contract_pin_evidence_exact(ROOT)
    assert evidence.verify()
    assert evidence.phase2a_acceptance_id == (
        "75df8940cfa5f31757fc9b105be172e60581ead32ff0494fb4c84a2baac43cf7")
    assert evidence.maturation_remediation_id == (
        "28b090531ece57fd41548e31eaa819cb02f7669f3fd8802a84d75b0a6f654fc9")
    assert evidence.private_corpus_manifest_id == (
        "0489978b34834817ee0e33dbd46d4e90b86a14e9827f89ba5b93433797c2ddd6")
    assert len(evidence.source_approval_ids) == 5
    path = write_contract_pin_evidence(tmp_path, evidence)
    assert read_contract_pin_evidence_exact(path, evidence.evidence_id) == evidence
    path.write_bytes(b"tampered")
    with pytest.raises(ValueError):
        read_contract_pin_evidence_exact(path, evidence.evidence_id)
