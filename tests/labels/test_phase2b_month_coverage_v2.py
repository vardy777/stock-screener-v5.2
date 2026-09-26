"""Independent Master/Calendar census, not a caller-supplied row count."""

from datetime import date
from types import SimpleNamespace

import pytest

from tests.labels.test_dataset_contracts import bundle_and_result
from v5_2.labels.anchor_enumerator import AnchorDispositionKind, AnchorDispositionV1
from v5_2.labels.dataset_contracts import LabelRowV1
from v5_2.labels.historical_five_domain_producer import ScopedAnchorExclusionV1
from v5_2.labels.historical_month_integration import ScopedMonthExclusionLedgerV1
from v5_2.labels.phase2b_month_coverage_v2 import (
    derive_month_coverage_evidence, read_month_coverage_evidence_exact,
    write_month_coverage_evidence,
)


def fixture():
    bundle, result = bundle_and_result()
    row = LabelRowV1.create(result=result, bundle=bundle,
                            materialization_version="phase2b-v1")
    day = date(2024, 1, 2)
    anchor = AnchorDispositionV1("000001.SZ", "000001.SZ", day,
        "SZSE", True, False, AnchorDispositionKind.ELIGIBLE, None)
    interval = SimpleNamespace(identity="000001.SZ",
                               effective_from=day, effective_to=None)
    master = SimpleNamespace(
        facts=(SimpleNamespace(provider_identity="000001.SZ",
                               intervals=(interval,)),), quarantines=(),
        authority={"authority_id": "a" * 64},
        approval={"approval_id": "b" * 64})
    calendar = SimpleNamespace(sse_sessions=(), szse_sessions=(day,),
        sessions=lambda exchange: (day,) if exchange == "SZSE" else (),
        approval_id="c" * 64)
    producer = SimpleNamespace(master=master, calendar=calendar,
        produce_anchor=lambda identity, session: (anchor, None, None))
    return producer, row


def test_independent_master_calendar_census_accounts_exact_eligible_row():
    producer, row = fixture()
    scoped = ScopedMonthExclusionLedgerV1.create("2024-01", ())
    evidence = derive_month_coverage_evidence(producer, (row,), scoped, "d" * 64)
    assert evidence.verify()
    assert evidence.effective_anchors == evidence.eligible_anchors == 1
    assert evidence.scoped_excluded_anchors == 0
    assert evidence.materialized_rows == 1


def test_independent_census_rejects_missing_row_and_forged_scoped_coverage():
    producer, row = fixture()
    scoped = ScopedMonthExclusionLedgerV1.create("2024-01", ())
    with pytest.raises(ValueError):
        derive_month_coverage_evidence(producer, (), scoped, "d" * 64)
    forged = ScopedMonthExclusionLedgerV1.create("2024-01", (
        ScopedAnchorExclusionV1("000001.SZ", date(2024, 1, 2),
                                "daily_bar", "UNEXPLAINED_MISSING_BAR", ("a" * 64,)),
    ))
    with pytest.raises(ValueError):
        derive_month_coverage_evidence(producer, (row,), forged, "d" * 64)


def test_independent_census_rejects_master_overlap_and_wrong_row_identity():
    producer, row = fixture()
    producer.master.facts = producer.master.facts + producer.master.facts
    with pytest.raises(ValueError, match="overlap"):
        derive_month_coverage_evidence(producer, (row,),
            ScopedMonthExclusionLedgerV1.create("2024-01", ()), "d" * 64)
    producer, row = fixture()
    from dataclasses import replace
    with pytest.raises(ValueError):
        derive_month_coverage_evidence(producer,
            (replace(row, canonical_security_identity="999999.SZ"),),
            ScopedMonthExclusionLedgerV1.create("2024-01", ()), "d" * 64)


def test_month_coverage_evidence_exact_read_and_tamper(tmp_path):
    producer, row = fixture()
    evidence = derive_month_coverage_evidence(producer, (row,),
        ScopedMonthExclusionLedgerV1.create("2024-01", ()), "d" * 64)
    path = write_month_coverage_evidence(tmp_path, evidence)
    assert read_month_coverage_evidence_exact(path, evidence.evidence_id) == evidence
    with pytest.raises(ValueError):
        read_month_coverage_evidence_exact(path, "e" * 64)
    path.write_bytes(path.read_bytes().replace(b'"materialized_rows":1',
                                               b'"materialized_rows":2'))
    with pytest.raises(ValueError):
        read_month_coverage_evidence_exact(path, evidence.evidence_id)
