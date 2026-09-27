"""Real full-day suspension must carry wealth without extending H1-H5."""

from dataclasses import fields, replace
from datetime import date
from pathlib import Path

import pytest

from v5_2.labels.contracts import LabelInputBundleV1
from v5_2.labels.historical_five_domain_producer import HistoricalFiveDomainProducerV1
from v5_2.labels.phase2b_suspension_safety_v2 import (
    compare_suspension_bundle_to_source, derive_suspension_evidence_exact,
    read_suspension_evidence_exact, write_suspension_evidence,
)


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not (ROOT / "data/replay_status_authority/authority").is_dir(),
    reason="approved five-domain source artifacts are not installed",
)


def test_full_day_to_ordinary_mutation_fails_suspension_gate():
    producer = HistoricalFiveDomainProducerV1.load_exact(ROOT)
    source = producer.assemble(*producer.produce_anchor(
        "600658.SH", date(2010, 5, 18)))
    assert source.future_statuses[0].is_suspended
    assert source.future_statuses[0].session not in {
        bar.session for bar in source.future_bars}
    assert compare_suspension_bundle_to_source(source, source)
    values = {field.name: getattr(source, field.name) for field in fields(source)
              if field.name != "content_hash"}
    values["future_statuses"] = (replace(source.future_statuses[0],
        is_suspended=False), *source.future_statuses[1:])
    forged = LabelInputBundleV1.create(**values)
    assert not compare_suspension_bundle_to_source(forged, source)


def test_suspension_evidence_is_content_addressed_and_exact(tmp_path):
    evidence = derive_suspension_evidence_exact(ROOT)
    assert evidence.verify()
    assert evidence.full_day_session == "2010-05-19"
    assert evidence.horizon_session_count == 5
    path = write_suspension_evidence(tmp_path, evidence)
    assert read_suspension_evidence_exact(path, evidence.evidence_id) == evidence
    with pytest.raises(ValueError):
        read_suspension_evidence_exact(path, "f" * 64)
