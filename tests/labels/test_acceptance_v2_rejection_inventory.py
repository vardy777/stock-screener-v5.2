from dataclasses import replace
from pathlib import Path

import pytest

from v5_2.data.label_evidence_assembler import EvidenceAssemblyError, Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import build_frozen_inventory
from v5_2.labels.calculation import CorporateActionCoverageV1, UnsafeLabelInput, build_economic_wealth_path
from v5_2.labels.contracts import LabelReasonCode
from v5_2.data.corporate_action_facts import ActionType, CorporateActionFactV1, KnowledgeClass


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "data/phase_2a/governance").is_dir(), reason="immutable evidence excluded")


def test_existing_assembler_rejection_contracts_are_exact():
    assembler = Phase2AEvidenceAssemblerV1(ROOT)
    slot = build_frozen_inventory().slots[0]
    expected = {
        "REVOKED_APPROVAL": "REVOKED_APPROVAL",
        "TAMPERED_ARTIFACT": "TAMPERED_ARTIFACT",
        "IDENTITY_AMBIGUITY": "IDENTITY_AMBIGUITY",
        "MALFORMED_CALENDAR": "MALFORMED_CALENDAR",
        "ROLE_SWAP": "ROLE_SWAP",
        "DUPLICATE_DOMAIN": "DUPLICATE_DOMAIN",
    }
    for fault, message in expected.items():
        with pytest.raises(EvidenceAssemblyError) as error:
            assembler.assemble(slot, injected_fault=fault)
        assert str(error.value) == message


def test_missing_domain_and_unexplained_bar_contracts_are_exact():
    assembler = Phase2AEvidenceAssemblerV1(ROOT)
    slot = build_frozen_inventory().slots[0]
    with pytest.raises(EvidenceAssemblyError) as missing:
        assembler.assemble(slot, forbidden_domain="calendar")
    assert str(missing.value) == "MISSING_DOMAIN:calendar"
    with pytest.raises(EvidenceAssemblyError) as bar:
        assembler.assemble(slot, injected_fault="REMOVE_FUTURE_BAR")
    assert str(bar.value).startswith("UNEXPLAINED_MISSING_BAR:")


def test_unsupported_ca_keeps_existing_reason():
    bundle = Phase2AEvidenceAssemblerV1(ROOT).assemble(build_frozen_inventory().slots[0])
    sessions = tuple(day for day in bundle.approved_exchange_sessions if day > bundle.anchor_session)[:5]
    session = sessions[0]
    fact = CorporateActionFactV1.create(
        security_identity="000001.SZ", action_type=ActionType.RIGHTS_ISSUE,
        knowledge_class=KnowledgeClass.KNOWN_IN_ADVANCE, published_at=None,
        available_at=bundle.anchor_boundary.anchor_cutoff, ex_date=session, effective_date=None,
        cash_per_share=None, share_ratio=None, source_fact_id="a" * 64,
        source_version_identity="b" * 64, revision_marker="v1",
        supersedes_source_fact_id=None, is_cancelled=False,
    )
    with pytest.raises(UnsafeLabelInput) as error:
        build_economic_wealth_path(bundle.reference_price, sessions, (), (fact,), CorporateActionCoverageV1.safe())
    assert error.value.reason is LabelReasonCode.UNSUPPORTED_CORPORATE_ACTION


def test_invalid_lineage_message_is_exact():
    assembler = Phase2AEvidenceAssemblerV1(ROOT)
    bundle = assembler.assemble(build_frozen_inventory().slots[0])
    bad = replace(bundle.domain_lineage[0], content_hash="0" * 64)
    with pytest.raises(ValueError) as error:
        type(bundle).create(**{
            field: getattr(bundle, field)
            for field in bundle.__dataclass_fields__
            if field not in {"bundle_id", "content_hash", "domain_lineage"}
        }, domain_lineage=(bad, *bundle.domain_lineage[1:]))
    assert str(error.value) == "invalid domain lineage"
