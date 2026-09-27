"""CA gate must pin real supported facts and reject unsupported boundaries."""

from dataclasses import fields
from datetime import date
from pathlib import Path

import pytest

from v5_2.labels.contracts import LabelInputBundleV1
from v5_2.labels.historical_five_domain_producer import HistoricalFiveDomainProducerV1
from v5_2.labels.phase2b_ca_safety_v2 import (
    compare_ca_bundle_to_source, derive_ca_safety_evidence_exact,
    read_ca_safety_evidence_exact, write_ca_safety_evidence,
)


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not (ROOT / "data/replay_status_authority/authority").is_dir(),
    reason="approved five-domain source artifacts are not installed",
)


def _copy_bundle(bundle, **changes):
    values = {field.name: getattr(bundle, field.name) for field in fields(bundle)
              if field.name != "content_hash"}
    return LabelInputBundleV1.create(**(values | changes))


def test_supported_action_omission_is_detected_from_pinned_real_source():
    producer = HistoricalFiveDomainProducerV1.load_exact(ROOT)
    anchor, lineage, window = producer.produce_anchor(
        "600276.SH", date(2019, 3, 27))
    source = producer.assemble(anchor, lineage, window)
    assert {item.action_type.value for item in source.corporate_actions} == {
        "CASH_DIVIDEND", "BONUS_SHARE"}
    assert compare_ca_bundle_to_source(source, source)
    omitted = _copy_bundle(source, corporate_actions=source.corporate_actions[:1])
    assert omitted.verify()
    assert not compare_ca_bundle_to_source(omitted, source)


def test_real_ca_gate_evidence_is_exact_and_unsupported_types_fail_closed(tmp_path):
    evidence = derive_ca_safety_evidence_exact(ROOT)
    assert evidence.verify()
    assert evidence.supported_action_types == ("BONUS_SHARE", "CASH_DIVIDEND")
    assert evidence.unsupported_rejections == (
        "RIGHTS_ISSUE", "SHARE_CONVERSION", "STOCK_SPLIT")
    path = write_ca_safety_evidence(tmp_path, evidence)
    assert read_ca_safety_evidence_exact(path, evidence.evidence_id) == evidence
    with pytest.raises(ValueError):
        read_ca_safety_evidence_exact(path, "f" * 64)
