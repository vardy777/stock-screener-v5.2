from datetime import date
from pathlib import Path

import pytest

from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.historical_daily_bar_lineage import (
    HistoricalDailyBarLineageV1,
    _governance,
)


ROOT = Path(__file__).resolve().parents[2] / "data/phase_1b_historical_daily_bar_fact_authority"
requires_real_evidence = pytest.mark.skipif(
    not ROOT.is_dir(), reason="repository-local immutable evidence excluded from clean room",
)
PINS = {
    "authority_id": "12ea218b47389979561423a2289791bfe504040b4bbe6d667af26967dad55933",
    "approval_id": "834d20964081575ec758abc3f28584b35ff414ac347a04e028d86ecf9752a656",
    "manifest_id": "232a5ebaece1a8c3552ccb4c9bdebd40048afae19c6086f246aa377c9235e546",
    "coverage_ledger_id": "632484c08fb7e9e24f59bbb33129dcabaf192b80529c35eaffceed731893508d",
    "composition_id": "c2ebb472773fe595cb87703ec03bf6206bacddb3cd34eb68576176ae3d518482",
    "replay_id": "0abffb860b3f4de201c5fd24431c4905b9e7ce5e1707fa59bc5b5fd902b0772c",
}


@requires_real_evidence
def test_real_approved_window_lineage_contains_only_consumed_fact_ids():
    source = HistoricalDailyBarLineageV1.load_exact(ROOT, **PINS, revoked_approval_ids=())
    rows = source.reader.read_window("2010-01", date(2010, 1, 11))
    first = rows[0]
    window = source.read_window("2010-01", date(2010, 1, 11))
    selected = window.facts_for(first.security_identity, (first.session,))
    lineage = window.lineage_for(first.security_identity, (first.session,))

    assert selected == (first,)
    assert lineage.domain == "daily_bar"
    assert lineage.fact_ids == (first.fact_id,)
    assert lineage.approval_id == PINS["approval_id"]
    assert lineage.manifest_id == PINS["manifest_id"]
    assert all(value in lineage.evidence_ids for value in (
        PINS["authority_id"], PINS["coverage_ledger_id"],
        PINS["composition_id"], PINS["replay_id"],
        PINS["approval_id"], PINS["manifest_id"],
    ))


@requires_real_evidence
def test_absent_bar_is_not_fabricated_or_classified():
    source = HistoricalDailyBarLineageV1.load_exact(ROOT, **PINS, revoked_approval_ids=())
    window = source.read_window("2010-01", date(2010, 1, 11))
    assert window.facts_for("NO_SUCH_IDENTITY.SZ", (date(2010, 1, 4),)) == ()
    assert window.lineage_for("NO_SUCH_IDENTITY.SZ", (date(2010, 1, 4),)).fact_ids == ()


@requires_real_evidence
def test_wrong_governance_pin_and_revocation_fail_closed():
    with pytest.raises(ValueError):
        HistoricalDailyBarLineageV1.load_exact(
            ROOT, **{**PINS, "composition_id": "f" * 64}, revoked_approval_ids=(),
        )
    with pytest.raises(ValueError):
        HistoricalDailyBarLineageV1.load_exact(
            ROOT, **PINS, revoked_approval_ids=(PINS["approval_id"],),
        )


def test_tampered_governance_bytes_fail_closed(tmp_path):
    body = {"schema_version": "PinnedTestV1", "value": "approved"}
    identity = content_hash(body)
    artifact = {**body, "artifact_id": identity, "content_hash": identity}
    path = tmp_path / "governance" / f"pinned-{identity}.json"
    path.parent.mkdir()
    path.write_bytes(canonical_json(artifact))
    assert _governance(tmp_path, "pinned", identity, "PinnedTestV1", "artifact_id") == artifact
    path.write_bytes(canonical_json({**artifact, "value": "tampered"}))
    with pytest.raises(ValueError, match="content address"):
        _governance(tmp_path, "pinned", identity, "PinnedTestV1", "artifact_id")
