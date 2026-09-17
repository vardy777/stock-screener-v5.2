from pathlib import Path

import pytest

from v5_2.labels.pilot import PILOT_SLOTS, run_pilot


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "data/phase_2a").is_dir(), reason="real evidence excluded")


def test_frozen_five_slot_pilot_matches_independent_calculator():
    pilot = run_pilot(ROOT)
    assert pilot.slots == PILOT_SLOTS == (1, 6, 8, 11, 18)
    assert len(pilot.entries) == 5
    assert all(item.disposition == "MATCH" for item in pilot.entries)
    assert pilot.provider_requests == 0
    assert pilot.verify()


def test_pilot_covers_required_states_and_paths():
    pilot = run_pilot(ROOT)
    summaries = {item.slot: item.engine_summary for item in pilot.entries}
    assert all(row[1] == "LABEL_AVAILABLE" for row in summaries[1])
    assert all(row[1] == "LABEL_AVAILABLE" for row in summaries[6])
    assert all(row[1] == "LABEL_AVAILABLE" for row in summaries[8])
    assert all(row[1:] == ("NOT_LABEL_SAFE", "None", "ANCHOR_BAR_MISSING") for row in summaries[11])
    assert all(row[1:] == ("LABEL_PENDING", "None", "HORIZON_NOT_COMPLETED") for row in summaries[18])
