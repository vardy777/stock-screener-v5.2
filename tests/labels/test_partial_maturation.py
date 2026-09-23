from datetime import date
from decimal import Decimal

import pytest

from tests.labels.test_reference_engine import NOW, SESSIONS, bar, bundle, status
from v5_2.data.corporate_action_facts import ActionType, CorporateActionFactV1, KnowledgeClass
from v5_2.data.daily_bar_facts import DailyBarFactV1
from v5_2.labels.contracts import LabelInputBundleV1, LabelReasonCode, LabelState
from v5_2.labels.engine import ReferenceLabelEngine


def partial_bundle(count: int, *, bars=None, statuses=None, **changes):
    original = bundle(latest=SESSIONS[count]) if count else bundle(latest=SESSIONS[0])
    values = {name: getattr(original, name) for name in (
        "canonical_security_identity", "anchor_session", "anchor_boundary", "reference_price",
        "provenance_path", "domain_lineage", "anchor_snapshot_id", "outcome_snapshot_id",
        "approved_exchange_sessions", "latest_completed_session", "corporate_actions",
        "action_coverage", "dated_identity_map", "delisting_session",
    )}
    values["future_bars"] = tuple(original.future_bars[:count] if bars is None else bars)
    values["future_statuses"] = tuple(original.future_statuses[:count] if statuses is None else statuses)
    values.update(changes)
    return LabelInputBundleV1.create(**values)


def states(result):
    return tuple(item.state for item in result.values)


def action(day, kind=ActionType.CASH_DIVIDEND):
    return CorporateActionFactV1.create(
        security_identity="000001.SZ", action_type=kind,
        knowledge_class=KnowledgeClass.KNOWN_IN_ADVANCE, published_at=NOW, available_at=NOW,
        ex_date=day, effective_date=day,
        cash_per_share=Decimal("1") if kind is ActionType.CASH_DIVIDEND else None,
        share_ratio=None, source_fact_id=f"{kind.value}-{day}", source_version_identity="v1",
        revision_marker="1", supersedes_source_fact_id=None, is_cancelled=False,
    )


def alternate_bar(day, close):
    value = Decimal(close)
    return DailyBarFactV1.create(
        source_symbol="001001.SZ", session=day, open=value, high=value + 1, low=value - 1,
        close=value, raw_volume=Decimal("1"), raw_amount=Decimal("1"),
        source_payload_hash="p", available_at=NOW, availability_policy_version="v1",
    )


def upper_only_bar(day):
    return DailyBarFactV1.create(
        source_symbol="000001.SZ", session=day, open=Decimal("10.1"), high=Decimal("10.5"),
        low=Decimal("10.0"), close=Decimal("10.4"), raw_volume=Decimal("1"),
        raw_amount=Decimal("1"), source_payload_hash="p", available_at=NOW,
        availability_policy_version="v1",
    )


def test_genuine_h0_without_future_evidence_is_all_pending():
    result = ReferenceLabelEngine().evaluate(partial_bundle(0))
    assert states(result) == (LabelState.LABEL_PENDING,) * 7


def test_genuine_h1_requires_no_h2_to_h5_evidence():
    result = ReferenceLabelEngine().evaluate(partial_bundle(1))
    assert result.values[0].state is LabelState.LABEL_AVAILABLE
    assert result.values[0].value == Decimal("0.10000000")
    assert states(result)[1:] == (LabelState.LABEL_PENDING,) * 6


def test_genuine_h3_requires_no_h4_or_h5_evidence():
    result = ReferenceLabelEngine().evaluate(partial_bundle(3))
    assert states(result)[:2] == (LabelState.LABEL_AVAILABLE, LabelState.LABEL_AVAILABLE)
    assert result.values[1].value == Decimal("0.30000000")
    assert states(result)[2:] == (LabelState.LABEL_PENDING,) * 5


def test_h1_value_at_h3_pins_only_h1_input_facts():
    h1 = ReferenceLabelEngine().evaluate(partial_bundle(1)).values[0]
    h3 = ReferenceLabelEngine().evaluate(partial_bundle(3)).values[0]
    assert h3.value == h1.value
    assert h3.input_fact_ids == h1.input_fact_ids
    assert h3.observed_at == h1.observed_at


def test_complete_h5_keeps_all_frozen_outputs_available():
    result = ReferenceLabelEngine().evaluate(partial_bundle(5))
    assert states(result) == (LabelState.LABEL_AVAILABLE,) * 7


@pytest.mark.parametrize("count,missing_index,safe_prefix", ((1, 0, 0), (3, 1, 1)))
def test_missing_completed_status_is_horizon_scoped(count, missing_index, safe_prefix):
    original = bundle(latest=SESSIONS[count])
    observed = tuple(item for index, item in enumerate(original.future_statuses[:count]) if index != missing_index)
    result = ReferenceLabelEngine().evaluate(partial_bundle(count, statuses=observed))
    assert all(item.state is LabelState.LABEL_AVAILABLE for item in result.values[:safe_prefix])
    assert result.values[safe_prefix].state is LabelState.NOT_LABEL_SAFE
    assert result.values[safe_prefix].reason_code is LabelReasonCode.STATUS_UNRESOLVED
    assert all(item.state is LabelState.LABEL_PENDING for item in result.values[count and 2 or 1:])


@pytest.mark.parametrize("count,missing_index,safe_prefix", ((1, 0, 0), (3, 1, 1)))
def test_missing_completed_bar_without_suspension_is_horizon_scoped(count, missing_index, safe_prefix):
    original = bundle(latest=SESSIONS[count])
    observed = tuple(item for index, item in enumerate(original.future_bars[:count]) if index != missing_index)
    result = ReferenceLabelEngine().evaluate(partial_bundle(count, bars=observed))
    assert all(item.state is LabelState.LABEL_AVAILABLE for item in result.values[:safe_prefix])
    assert result.values[safe_prefix].state is LabelState.NOT_LABEL_SAFE
    assert result.values[safe_prefix].reason_code is LabelReasonCode.EXPECTED_BAR_MISSING


def test_proven_suspension_in_completed_prefix_carries_wealth():
    original = bundle(latest=SESSIONS[3])
    suspended = list(original.future_statuses[:3])
    suspended[1] = status(SESSIONS[2]).__class__.create(
        security_identity="000001.SZ", session=SESSIONS[2], is_listed=True, is_delisted=False,
        is_risk_warning=False, is_suspended=True, effective_from=SESSIONS[2], effective_to=SESSIONS[2],
        available_at=suspended[1].available_at, source_fact_ids=("s",), source_name="test",
        policy_version="v1", risk_warning_excluded=False,
    )
    observed_bars = (original.future_bars[0], original.future_bars[2])
    result = ReferenceLabelEngine().evaluate(partial_bundle(3, bars=observed_bars, statuses=tuple(suspended)))
    assert states(result)[:2] == (LabelState.LABEL_AVAILABLE, LabelState.LABEL_AVAILABLE)
    assert states(result)[2:] == (LabelState.LABEL_PENDING,) * 5


def test_proven_h1_suspension_carries_reference_wealth_without_a_bar():
    original = bundle(latest=SESSIONS[1])
    suspended = status(SESSIONS[1]).__class__.create(
        security_identity="000001.SZ", session=SESSIONS[1], is_listed=True, is_delisted=False,
        is_risk_warning=False, is_suspended=True, effective_from=SESSIONS[1], effective_to=SESSIONS[1],
        available_at=original.future_statuses[0].available_at, source_fact_ids=("s",),
        source_name="test", policy_version="v1", risk_warning_excluded=False,
    )
    result = ReferenceLabelEngine().evaluate(partial_bundle(1, bars=(), statuses=(suspended,)))
    assert result.values[0].state is LabelState.LABEL_AVAILABLE
    assert result.values[0].value == Decimal("0E-8")
    assert states(result)[1:] == (LabelState.LABEL_PENDING,) * 6


def test_cash_dividend_inside_h1_changes_only_mature_return():
    result = ReferenceLabelEngine().evaluate(partial_bundle(1, corporate_actions=(action(SESSIONS[1]),)))
    assert result.values[0].value == Decimal("0.20000000")
    assert states(result)[1:] == (LabelState.LABEL_PENDING,) * 6


def test_cash_dividend_at_h2_affects_h3_but_not_h1():
    result = ReferenceLabelEngine().evaluate(partial_bundle(3, corporate_actions=(action(SESSIONS[2]),)))
    assert result.values[0].value == Decimal("0.10000000")
    assert result.values[1].value == Decimal("0.40000000")
    assert states(result)[2:] == (LabelState.LABEL_PENDING,) * 5


def test_future_h4_action_does_not_leak_into_h3():
    result = ReferenceLabelEngine().evaluate(partial_bundle(3, corporate_actions=(action(SESSIONS[4]),)))
    assert result.values[0].value == Decimal("0.10000000")
    assert result.values[1].value == Decimal("0.30000000")
    assert states(result)[2:] == (LabelState.LABEL_PENDING,) * 5


def test_unsupported_action_at_h2_preserves_h1_and_rejects_h3():
    result = ReferenceLabelEngine().evaluate(partial_bundle(
        3, corporate_actions=(action(SESSIONS[2], ActionType.RIGHTS_ISSUE),)
    ))
    assert result.values[0].state is LabelState.LABEL_AVAILABLE
    assert result.values[1].state is LabelState.NOT_LABEL_SAFE
    assert result.values[1].reason_code is LabelReasonCode.UNSUPPORTED_CORPORATE_ACTION
    assert states(result)[2:] == (LabelState.LABEL_PENDING,) * 5


def test_identity_transition_inside_mature_prefix_requires_exact_map():
    original = bundle(latest=SESSIONS[3])
    changed = (original.future_bars[0], alternate_bar(SESSIONS[2], "12"), original.future_bars[2])
    unsafe = ReferenceLabelEngine().evaluate(partial_bundle(3, bars=changed))
    safe = ReferenceLabelEngine().evaluate(partial_bundle(
        3, bars=changed, dated_identity_map=((SESSIONS[2], "001001.SZ", "000001.SZ"),)
    ))
    assert unsafe.values[0].state is LabelState.LABEL_AVAILABLE
    assert unsafe.values[1].reason_code is LabelReasonCode.IDENTITY_UNRESOLVED
    assert states(safe)[:2] == (LabelState.LABEL_AVAILABLE, LabelState.LABEL_AVAILABLE)


def test_delisting_inside_mature_prefix_preserves_frozen_full_row_unsafety():
    result = ReferenceLabelEngine().evaluate(partial_bundle(3, delisting_session=SESSIONS[2]))
    assert result.values[0].state is LabelState.LABEL_AVAILABLE
    assert result.values[1].state is LabelState.NOT_LABEL_SAFE
    assert result.values[1].reason_code is LabelReasonCode.DELISTING_IN_HORIZON
    assert states(result)[2:] == (LabelState.LABEL_PENDING,) * 5


def test_barriers_never_mature_before_h5_even_when_decisive_at_h1():
    original = bundle(latest=SESSIONS[1])
    decisive = upper_only_bar(SESSIONS[1])
    h1 = ReferenceLabelEngine().evaluate(partial_bundle(1, bars=(decisive,)))
    h3 = ReferenceLabelEngine().evaluate(partial_bundle(3, bars=(decisive, *original.future_bars[1:3])))
    assert states(h1)[-2:] == (LabelState.LABEL_PENDING, LabelState.LABEL_PENDING)
    assert states(h3)[-2:] == (LabelState.LABEL_PENDING, LabelState.LABEL_PENDING)
    h5 = ReferenceLabelEngine().evaluate(partial_bundle(5, bars=(decisive, *bundle().future_bars[1:])))
    assert all(item.state is LabelState.LABEL_AVAILABLE for item in h5.values[-2:])


def test_same_session_barrier_ambiguity_retains_frozen_h5_full_row_behavior():
    ambiguous = DailyBarFactV1.create(
        source_symbol="000001.SZ", session=SESSIONS[1], open=Decimal("10"), high=Decimal("11"),
        low=Decimal("9"), close=Decimal("10"), raw_volume=Decimal("1"), raw_amount=Decimal("1"),
        source_payload_hash="p", available_at=NOW, availability_policy_version="v1",
    )
    result = ReferenceLabelEngine().evaluate(partial_bundle(5, bars=(ambiguous, *bundle().future_bars[1:])))
    assert states(result) == (LabelState.NOT_LABEL_SAFE,) * 7
    assert all(item.reason_code is LabelReasonCode.BARRIER_PATH_AMBIGUOUS for item in result.values)
    assert len(result.barrier_evidence) == 2
