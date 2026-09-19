from pathlib import Path

import pytest

from v5_2.labels.acceptance import ACCEPTANCE_GATES
from v5_2.labels.acceptance_v2_1_final import (
    FROZEN_ATTEMPT2_ARTIFACT_IDS,
    FROZEN_SUPERSESSION_ID,
    run_final_acceptance_v2_1,
    verify_frozen_infrastructure_v2_1,
)


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "data/phase_2a/reference").is_dir(), reason="immutable evidence excluded")


def test_fresh_final_acceptance_reloads_exact_artifacts_and_executes_all_gates():
    checked = verify_frozen_infrastructure_v2_1(ROOT)
    result = run_final_acceptance_v2_1(ROOT)
    assert checked.supersession.supersession_id == FROZEN_SUPERSESSION_ID
    assert result.infrastructure_artifact_ids == FROZEN_ATTEMPT2_ARTIFACT_IDS
    assert result.supersession_id == FROZEN_SUPERSESSION_ID
    assert result.gate_results == tuple((gate, "PASS") for gate in ACCEPTANCE_GATES)
    assert result.overall_status == "PASS"
    assert result.phase_2a_status == "PASS / CLOSED"
    assert result.ready_for_phase_2b is True
    assert result.phase_2b_started is False
    assert result.verify()


def test_wrong_pinned_artifact_id_fails_closed_before_final_acceptance():
    wrong = (*FROZEN_ATTEMPT2_ARTIFACT_IDS[:-1], "0" * 64)
    with pytest.raises(ValueError, match="exact frozen Attempt 2 artifact IDs required"):
        verify_frozen_infrastructure_v2_1(ROOT, artifact_ids=wrong)


def test_final_acceptance_is_deterministic_for_same_frozen_inputs():
    first = run_final_acceptance_v2_1(ROOT)
    second = run_final_acceptance_v2_1(ROOT)
    assert first == second
    assert first.acceptance_id == second.acceptance_id
