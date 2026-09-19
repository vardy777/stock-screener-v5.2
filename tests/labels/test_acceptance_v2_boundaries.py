import json
from pathlib import Path

import pytest

from v5_2.labels.acceptance_v2_boundaries import (
    build_unsupported_ca_boundary_case,
    execute_boundary_case,
)
from v5_2.labels.acceptance_v2_contracts import EvidenceClass


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_ID = "5086896d0066baa928fe44c3469b2c1362feb2068db04acb7336b38c13bdbe2c"
pytestmark = pytest.mark.skipif(not (ROOT / "data/phase_1b2c/governance").is_dir(), reason="immutable evidence excluded")


class ForbiddenEngine:
    def __init__(self): self.calls = 0
    def evaluate(self, _bundle):
        self.calls += 1
        raise AssertionError("engine must be structurally unreachable")


def manifest():
    return json.loads((ROOT / f"data/phase_1b2c/governance/corporate-action-manifest-{MANIFEST_ID}.json").read_text())


def test_unsupported_ca_uses_real_scope_plus_explicit_fixture_and_never_calls_engine():
    engine = ForbiddenEngine()
    case = build_unsupported_ca_boundary_case(manifest())
    result = execute_boundary_case(case, engine=engine)
    assert result.verify()
    assert result.evidence_class is EvidenceClass.REAL_MACHINE_VISIBLE_UNSUPPORTED_CONDITION
    assert result.observed_rejection_code == "UNSUPPORTED_CORPORATE_ACTION"
    assert result.engine_invocation_count == engine.calls == 0
    assert MANIFEST_ID in result.input_evidence_ids
    assert "DETERMINISTIC_CONTRACT_FIXTURE" in result.evidence_condition


def test_unsupported_ca_rejects_unpinned_or_promoted_scope():
    bad = dict(manifest(), dataset_id="0" * 64)
    with pytest.raises(ValueError, match="unsupported scope manifest"):
        build_unsupported_ca_boundary_case(bad)
    promoted = dict(manifest(), unsupported_action_types=[])
    with pytest.raises(ValueError, match="unsupported scope"):
        build_unsupported_ca_boundary_case(promoted)
