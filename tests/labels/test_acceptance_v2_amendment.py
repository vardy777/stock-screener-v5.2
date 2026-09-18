import pytest

from v5_2.labels.acceptance_v2_contracts import build_frozen_amendment_v2


def test_frozen_amendment_preserves_literal_22_slot_history():
    amendment = build_frozen_amendment_v2()
    assert amendment.verify()
    assert tuple(x.slot for x in amendment.migration) == tuple(range(1, 23))
    by_slot = {x.slot: x.layers for x in amendment.migration}
    assert by_slot[16] == ("B",)
    assert by_slot[17] == ("B",)
    assert by_slot[22] == ("A", "C")
    assert all(by_slot[i] == ("A",) for i in (*range(1, 16), *range(18, 22)))
    assert amendment.design_commit == "f92f0a564c802ddc28dc71153be44d409b6858ee"
    assert amendment.plan_commits == (
        "4db0f4ecb9e61853190f755d1bee164d9f84fe9a",
        "390149882f3265b778b736a16380c13d9a64652a",
    )


def test_migration_is_literal_and_cannot_be_reordered():
    amendment = build_frozen_amendment_v2()
    with pytest.raises(ValueError, match="exact 22-slot migration"):
        type(amendment).create(
            design_commit=amendment.design_commit,
            plan_commits=amendment.plan_commits,
            v1_artifact_ids=amendment.v1_artifact_ids,
            migration=tuple(reversed(amendment.migration)),
        )
