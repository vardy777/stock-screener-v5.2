from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from v5_2.labels.contracts import (
    AnchorKnowledgeBoundary,
    BarrierOutcomeV1,
    DomainLineageV1,
    LabelContractV1,
    LabelInputBundleV1,
    LabelReasonCode,
    LabelReferencePrice,
    LabelState,
    LabelValueV1,
    ProvenancePath,
)


H = "a" * 64


def lineage(domain: str, suffix: str = "a") -> DomainLineageV1:
    return DomainLineageV1.create(
        domain=domain,
        approval_id=suffix * 64,
        manifest_id=("b" if suffix != "b" else "c") * 64,
        fact_ids=(("d" if suffix != "d" else "e") * 64,),
    )


def test_available_value_requires_value_and_forbids_reason():
    value = LabelValueV1.create("return_1d", LabelState.LABEL_AVAILABLE, Decimal(".1"))
    assert value.value == Decimal(".1")
    with pytest.raises(ValueError):
        LabelValueV1.create("return_1d", LabelState.LABEL_AVAILABLE, Decimal(".1"), LabelReasonCode.EXPECTED_BAR_MISSING)


def test_pending_and_not_safe_values_require_reason_and_no_value():
    pending = LabelValueV1.create("return_5d", LabelState.LABEL_PENDING, None, LabelReasonCode.HORIZON_NOT_COMPLETED)
    unsafe = LabelValueV1.create("return_5d", LabelState.NOT_LABEL_SAFE, None, LabelReasonCode.EXPECTED_BAR_MISSING)
    assert pending.value is None and unsafe.value is None
    with pytest.raises(ValueError):
        LabelValueV1.create("return_5d", LabelState.LABEL_PENDING, Decimal("0"), LabelReasonCode.HORIZON_NOT_COMPLETED)


def test_numeric_value_must_be_decimal_and_boolean_only_for_barrier():
    with pytest.raises(ValueError):
        LabelValueV1.create("return_1d", LabelState.LABEL_AVAILABLE, 0.1)
    with pytest.raises(ValueError):
        LabelValueV1.create("return_1d", LabelState.LABEL_AVAILABLE, True)
    assert LabelValueV1.create("hit_3pct_before_-2pct", LabelState.LABEL_AVAILABLE, True).value is True


def test_canonical_names_exclude_ui_aliases():
    with pytest.raises(ValueError):
        LabelValueV1.create("max_upside_5d", LabelState.LABEL_AVAILABLE, Decimal("0"))


def test_domain_lineage_is_role_specific_and_deterministic():
    item = lineage("daily_bar")
    assert item.verify()
    assert item == lineage("daily_bar")
    with pytest.raises(ValueError):
        DomainLineageV1.create(domain="daily_bar", approval_id="", manifest_id="b" * 64, fact_ids=("d" * 64,))
    with pytest.raises(ValueError):
        DomainLineageV1.create(domain="daily_bar", approval_id="a" * 64, manifest_id="", fact_ids=("d" * 64,))
    with pytest.raises(ValueError):
        DomainLineageV1.create(domain="daily_bar", approval_id="a" * 64, manifest_id="b" * 64, fact_ids=("d" * 64, "d" * 64))
    assert not replace(item, approval_id="f" * 64).verify()


def test_bundle_requires_exact_five_domains_and_historical_snapshots_are_optional():
    domains = tuple(lineage(name, chr(97 + i)) for i, name in enumerate(LabelContractV1().required_domains))
    boundary = AnchorKnowledgeBoundary.create(date(2024, 1, 2), datetime(2024, 1, 2, 16, 30, tzinfo=timezone.utc), H, True)
    reference = LabelReferencePrice.create(date(2024, 1, 2), Decimal("10"), H, datetime(2024, 1, 3, tzinfo=timezone.utc))
    bundle = LabelInputBundleV1.create(
        canonical_security_identity="000001.SZ", anchor_session=date(2024, 1, 2),
        anchor_boundary=boundary, reference_price=reference, provenance_path=ProvenancePath.HISTORICAL,
        domain_lineage=domains,
    )
    assert bundle.anchor_snapshot_id is None and bundle.verify()
    with pytest.raises(ValueError):
        LabelInputBundleV1.create(
            canonical_security_identity="000001.SZ", anchor_session=date(2024, 1, 2),
            anchor_boundary=boundary, reference_price=reference, provenance_path=ProvenancePath.HISTORICAL,
            domain_lineage=domains[:-1],
        )
    with pytest.raises(ValueError):
        LabelInputBundleV1.create(
            canonical_security_identity="000001.SZ", anchor_session=date(2024, 1, 2),
            anchor_boundary=boundary, reference_price=reference, provenance_path=ProvenancePath.CONTEMPORANEOUS,
            domain_lineage=domains,
        )


def test_barrier_outcome_is_three_valued():
    assert {x.value for x in BarrierOutcomeV1} == {"UPPER_FIRST", "LOWER_FIRST", "NEITHER"}
