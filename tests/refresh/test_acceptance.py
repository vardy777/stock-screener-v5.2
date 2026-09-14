from v5_2.refresh.acceptance import PHASE_1C_GATES, Phase1CRefreshAcceptanceV1


def test_acceptance_passes_only_when_every_frozen_gate_passes():
    artifact = Phase1CRefreshAcceptanceV1.create(
        starting_head="822025a", design_commit="bd6c0ea", implementation_head="abc123",
        gate_results={gate: "PASS" for gate in PHASE_1C_GATES},
        snapshot_ids=("s" * 64,), test_results={"focused": "31 passed"},
    )
    assert artifact.final_decision == "PASS"
    assert artifact.ready_for_phase_2_implementation is True
    assert artifact.acceptance_id == artifact.content_hash


def test_any_failed_gate_fails_closed_and_replay_is_deterministic():
    gates = {gate: "PASS" for gate in PHASE_1C_GATES}
    gates["SNAPSHOT_ATOMICITY"] = "FAIL"
    values = dict(starting_head="822025a", design_commit="bd6c0ea", implementation_head="abc123",
                  gate_results=gates, snapshot_ids=(), test_results={"focused": "failed"})
    first = Phase1CRefreshAcceptanceV1.create(**values)
    second = Phase1CRefreshAcceptanceV1.create(**values)
    assert first == second
    assert first.final_decision == "FAIL"
    assert first.ready_for_phase_2_implementation is False
