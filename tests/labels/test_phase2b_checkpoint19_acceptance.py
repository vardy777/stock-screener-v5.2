"""Public Checkpoint 19 acceptance binds private outcomes without publishing them."""

from dataclasses import replace
import json
import os
from pathlib import Path

import pytest

from v5_2.labels.pilot_phase2b import (
    read_candidate_census_exact, read_pilot_contract_exact,
)


ROOT = Path(__file__).resolve().parents[2]
CID = "1a1f2465a2d60e84f61874feccf6538c1c1daec3f69369600255d78379285a8d"
PID = "5a5d9aa9f72a00e63a5712cf6f6f0bed23823119641a563ff68ea141e808dccc"
RID = "f9bd6d10ba10532717a63f5f8b584f71e34db4d651fc96f98445c352c618d4dd"


@pytest.mark.skipif(os.environ.get("V52_CHECKPOINT19_PILOT") != "1",
                    reason="exact private pilot result required")
def test_acceptance_capsule_binds_private_result_without_label_values(tmp_path):
    from v5_2.labels.phase2b_checkpoint19_acceptance import (
        create_checkpoint19_acceptance_exact, read_checkpoint19_acceptance_exact,
        write_checkpoint19_acceptance_exact,
    )
    pre = ROOT / "data/phase_2b_checkpoint18_real_month/pilot_prereg"
    census = read_candidate_census_exact(pre / f"census-{CID}.json", CID)
    contract = read_pilot_contract_exact(pre / f"pilot-{PID}.json", PID, census)
    private = (ROOT / "data/phase_2b_checkpoint19/pilot_results"
               / f"pilot-result-{RID}.json")
    capsule = create_checkpoint19_acceptance_exact(private, RID, contract)
    assert capsule.verify()
    assert len(capsule.case_ids) == 4
    assert capsule.alpha_conclusion == "NOT_EVALUATED"
    path = write_checkpoint19_acceptance_exact(tmp_path, capsule)
    assert write_checkpoint19_acceptance_exact(tmp_path, capsule) == path
    assert read_checkpoint19_acceptance_exact(path, capsule.acceptance_id) == capsule
    raw = path.read_bytes()
    assert b'"label_values"' not in raw
    assert b'"return_1d"' not in raw
    assert not replace(capsule, selected_candidate_ids=tuple(
        reversed(capsule.selected_candidate_ids))).verify()
    value = json.loads(raw)
    value["provider_request_count"] = 1
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError):
        read_checkpoint19_acceptance_exact(path, capsule.acceptance_id)
