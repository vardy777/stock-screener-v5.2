from datetime import date, datetime, timezone
from decimal import Decimal

from v5_2.labels.anchor_enumerator import AnchorDispositionKind, AnchorDispositionV1
from v5_2.labels.contracts import (
    AnchorKnowledgeBoundary,
    CORE_LABELS,
    DomainLineageV1,
    LabelInputBundleV1,
    LabelReasonCode,
    LabelReferencePrice,
    LabelResultV1,
    LabelState,
    LabelValueV1,
    ProvenancePath,
    REQUIRED_LABEL_DOMAINS,
)
from v5_2.labels.dataset_contracts import CoverageAccountingV1, LabelRowV1


NOW = datetime(2024, 1, 31, tzinfo=timezone.utc)
REASONS = (
    LabelReasonCode.UNSUPPORTED_CORPORATE_ACTION,
    LabelReasonCode.DELISTING_IN_HORIZON,
    LabelReasonCode.IDENTITY_UNRESOLVED,
    LabelReasonCode.STATUS_UNRESOLVED,
    LabelReasonCode.EXPECTED_BAR_MISSING,
    LabelReasonCode.BARRIER_PATH_AMBIGUOUS,
)


def row(index: int, state: LabelState, reason: LabelReasonCode | None = None) -> LabelRowV1:
    anchor = date(2024, 1, index + 1)
    lineages = tuple(DomainLineageV1.create(
        domain=domain, approval_id=f"{domain_index + 1:x}" * 64,
        manifest_id=f"{domain_index + 6:x}" * 64,
        fact_ids=(f"{domain_index + 11:x}" * 64,),
    ) for domain_index, domain in enumerate(REQUIRED_LABEL_DOMAINS))
    bundle = LabelInputBundleV1.create(
        canonical_security_identity=f"0000{index:02d}.SZ", anchor_session=anchor,
        anchor_boundary=AnchorKnowledgeBoundary.create(anchor, NOW, "a" * 64, True),
        reference_price=LabelReferencePrice.create(anchor, Decimal("10"), "b" * 64, NOW),
        provenance_path=ProvenancePath.HISTORICAL, domain_lineage=lineages,
        approved_exchange_sessions=(anchor,), latest_completed_session=anchor,
    )
    values = tuple(LabelValueV1.create(
        name, state,
        Decimal("0.01000000") if state is LabelState.LABEL_AVAILABLE and not name.startswith("hit_") else (
            True if state is LabelState.LABEL_AVAILABLE else None
        ),
        reason,
    ) for name in CORE_LABELS)
    result = LabelResultV1.create(bundle.canonical_security_identity, anchor, values, bundle.content_hash)
    return LabelRowV1.create(result=result, bundle=bundle, materialization_version="phase2b-v1")


def inputs():
    rows = (
        row(1, LabelState.LABEL_AVAILABLE),
        row(2, LabelState.LABEL_PENDING, LabelReasonCode.HORIZON_NOT_COMPLETED),
        *tuple(row(index + 3, LabelState.NOT_LABEL_SAFE, reason) for index, reason in enumerate(REASONS)),
    )
    dispositions = tuple(AnchorDispositionV1(
        item.canonical_security_identity, item.canonical_security_identity,
        item.anchor_session, "SZSE", True, False, AnchorDispositionKind.ELIGIBLE, None,
    ) for item in rows) + (
        AnchorDispositionV1(
            "009999.SZ", "009999.SZ", date(2024, 1, 31), "SZSE", True, False,
            AnchorDispositionKind.EXCLUDED_BEFORE_LABEL, "IPO_SEASONING",
        ),
    )
    return dispositions, rows


def test_coverage_accounts_every_anchor_label_state_and_unsafe_reason():
    dispositions, rows = inputs()
    accounting = CoverageAccountingV1.from_dispositions(dispositions, rows)

    assert accounting.effective_anchors == 9
    assert accounting.eligible_anchors == 8
    assert accounting.excluded_before_label == 1
    assert accounting.materialized_rows == 8
    for label in CORE_LABELS:
        assert accounting.state_counts[label] == {
            "LABEL_AVAILABLE": 1, "LABEL_PENDING": 1, "NOT_LABEL_SAFE": 6,
        }
    assert accounting.reason_counts["HORIZON_NOT_COMPLETED"] == 7
    for reason in REASONS:
        assert accounting.reason_counts[reason.value] == 7
    assert accounting.exclusion_reason_counts == {"IPO_SEASONING": 1}
    assert accounting.verify_against(dispositions, rows)


def test_coverage_rejects_missing_materialized_eligible_anchor():
    dispositions, rows = inputs()
    try:
        CoverageAccountingV1.from_dispositions(dispositions, rows[:-1])
    except ValueError as error:
        assert "eligible" in str(error)
    else:
        raise AssertionError("missing eligible anchor was accepted")


def test_count_preserving_reason_swap_fails_semantic_verification():
    dispositions, rows = inputs()
    accounting = CoverageAccountingV1.from_dispositions(dispositions, rows)
    mutated = (
        *rows[:2], row(3, LabelState.NOT_LABEL_SAFE, REASONS[1]),
        row(4, LabelState.NOT_LABEL_SAFE, REASONS[0]), *rows[4:],
    )

    assert accounting.reason_counts[REASONS[0].value] == accounting.reason_counts[REASONS[1].value]
    assert not accounting.verify_against(dispositions, mutated)
