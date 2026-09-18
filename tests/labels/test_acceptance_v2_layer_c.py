from v5_2.labels.acceptance_v2_contracts import EvidenceClass, build_frozen_amendment_v2
from v5_2.labels.acceptance_v2_layer_c import build_frozen_edge_fixtures


def test_exact_four_precalculation_synthetic_fixtures_are_frozen():
    fixtures = build_frozen_edge_fixtures(build_frozen_amendment_v2())
    assert tuple(x.name for x in fixtures) == (
        "UPPER_FIRST", "LOWER_FIRST", "NEITHER", "SAME_SESSION_BARRIER_AMBIGUITY",
    )
    assert all(x.verify() for x in fixtures)
    assert all(x.fixture_id == x.content_hash for x in fixtures)
    assert all(x.evidence_class is EvidenceClass.SYNTHETIC_CONTRACT_FIXTURE for x in fixtures)
    assert all(not hasattr(x, "phase1_lineage") for x in fixtures)
    assert len({x.fixture_id for x in fixtures}) == 4
