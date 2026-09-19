import json
from pathlib import Path

import pytest

from scripts.build_phase2a_acceptance_v2_1_attempt2_infrastructure import build_infrastructure
from v5_2.labels.acceptance_v2_contracts import ATTEMPT1_INFRASTRUCTURE_IDS


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "data/phase_2a/reference").is_dir(), reason="immutable evidence excluded")


def snapshot(directory):
    return {path.name: path.read_bytes() for path in sorted(directory.glob("*.json"))}


def test_attempt2_materialization_is_seven_file_byte_deterministic_and_nonfinal(tmp_path):
    first = tmp_path / "first"; second = tmp_path / "second"
    report1 = build_infrastructure(ROOT, first)
    report2 = build_infrastructure(ROOT, second)
    assert report1 == report2
    assert snapshot(first) == snapshot(second)
    assert len(snapshot(first)) == 7
    assert not any("final-acceptance" in name for name in snapshot(first))
    assert report1["FINAL V2.1 ACCEPTANCE"] == "NOT RUN"
    assert report1["PHASE 2A"] == "FAIL / OPEN"
    assert report1["READY FOR PHASE 2B"] == "NO"
    new_ids = set(report1["ATTEMPT 2 ARTIFACT IDS"])
    assert len(new_ids) == 6
    assert new_ids.isdisjoint(ATTEMPT1_INFRASTRUCTURE_IDS)


def test_replay_is_identical_and_collision_never_overwrites(tmp_path):
    output = tmp_path / "attempt2"
    build_infrastructure(ROOT, output)
    original = snapshot(output)
    build_infrastructure(ROOT, output)
    assert snapshot(output) == original
    target = next(iter(sorted(output.glob("*.json"))))
    target.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="immutable infrastructure collision"):
        build_infrastructure(ROOT, output)
    assert target.read_bytes() == b"{}"


def test_attempt1_files_remain_byte_identical(tmp_path):
    old = ROOT / "data/phase_2a/v2_infrastructure"
    before = snapshot(old)
    build_infrastructure(ROOT, tmp_path / "attempt2")
    assert snapshot(old) == before


def test_supersession_pins_exact_six_old_and_new_ids(tmp_path):
    output = tmp_path / "attempt2"
    report = build_infrastructure(ROOT, output)
    supersession_path = next(output.glob("attempt1-to-attempt2-supersession-*.json"))
    value = json.loads(supersession_path.read_text(encoding="utf-8"))
    assert tuple(value["attempt1_ids"]) == ATTEMPT1_INFRASTRUCTURE_IDS
    assert tuple(value["attempt2_ids"]) == tuple(report["ATTEMPT 2 ARTIFACT IDS"])
    assert value["reason"] == "INFRASTRUCTURE_ACCEPTANCE_CORRECTNESS_DEFECT"
