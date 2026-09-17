from pathlib import Path

import pytest

from v5_2.data.label_evidence_assembler import EvidenceAssemblyError, Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import build_frozen_inventory
from v5_2.labels.contracts import LabelReasonCode, LabelState, REQUIRED_LABEL_DOMAINS
from v5_2.labels.engine import ReferenceLabelEngine


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not (ROOT / "data/phase_2a/governance").is_dir(),
    reason="repository-local immutable evidence is excluded from clean room",
)


@pytest.fixture(scope="module")
def assembler():
    return Phase2AEvidenceAssemblerV1(ROOT)


def test_exact_five_domains_construct_real_bundle(assembler):
    bundle = assembler.assemble(build_frozen_inventory().slots[0])
    assert tuple(item.domain for item in bundle.domain_lineage) == REQUIRED_LABEL_DOMAINS
    assert bundle.verify()


@pytest.mark.parametrize("missing", REQUIRED_LABEL_DOMAINS)
def test_each_missing_domain_fails_closed(assembler, missing):
    slot = build_frozen_inventory().slots[0]
    with pytest.raises(EvidenceAssemblyError, match="MISSING_DOMAIN"):
        assembler.assemble(slot, forbidden_domain=missing)


@pytest.mark.parametrize("fault", [
    "FINANCIAL_INCLUDED", "REVOKED_APPROVAL", "SUPERSEDED_ARTIFACT",
    "TAMPERED_ARTIFACT", "WRONG_DOMAIN", "DUPLICATE_DOMAIN", "ROLE_SWAP",
    "MALFORMED_CALENDAR", "IDENTITY_AMBIGUITY",
])
def test_integrity_and_role_faults_fail_closed(assembler, fault):
    with pytest.raises(EvidenceAssemblyError):
        assembler.assemble(build_frozen_inventory().slots[0], injected_fault=fault)


def test_anchor_suspension_builds_bundle_then_engine_is_not_label_safe(assembler):
    slot = build_frozen_inventory().slots[10]
    bundle = assembler.assemble(slot)
    result = ReferenceLabelEngine().evaluate(bundle)
    assert bundle.reference_price is None
    assert all(value.state is LabelState.NOT_LABEL_SAFE for value in result.values)
    assert all(value.reason_code is LabelReasonCode.ANCHOR_BAR_MISSING for value in result.values)


def test_delisting_horizon_builds_bundle_then_engine_is_not_label_safe(assembler):
    slot = build_frozen_inventory().slots[13]
    bundle = assembler.assemble(slot)
    result = ReferenceLabelEngine().evaluate(bundle)
    assert bundle.delisting_session.isoformat() == "2023-08-04"
    assert all(value.state is LabelState.NOT_LABEL_SAFE for value in result.values)
    assert all(value.reason_code is LabelReasonCode.DELISTING_IN_HORIZON for value in result.values)


def test_missing_bar_without_suspension_fails_but_proven_suspension_passes(assembler):
    normal = build_frozen_inventory().slots[0]
    with pytest.raises(EvidenceAssemblyError, match="UNEXPLAINED_MISSING_BAR"):
        assembler.assemble(normal, injected_fault="REMOVE_FUTURE_BAR")
    suspended = assembler.assemble(build_frozen_inventory().slots[7])
    assert suspended.verify()
