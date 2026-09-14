from datetime import date, datetime, timezone
from decimal import Decimal

from v5_2.data.daily_bar_facts import DailyBarFactV1
from v5_2.data.security_status_facts import DailySecurityStatusFactV1
from v5_2.labels.calculation import CorporateActionCoverageV1
from v5_2.labels.contracts import AnchorKnowledgeBoundary, DomainLineageV1, LabelContractV1, LabelInputBundleV1, LabelReasonCode, LabelReferencePrice, LabelState, ProvenancePath
from v5_2.labels.engine import ReferenceLabelEngine


NOW = datetime(2024, 1, 20, tzinfo=timezone.utc)
SESSIONS = tuple(date(2024, 1, x) for x in (2, 3, 4, 5, 8, 9))


def bar(day, close):
    value = Decimal(close)
    return DailyBarFactV1.create(source_symbol="000001.SZ", session=day, open=value, high=value + 1, low=value - 1, close=value, raw_volume=Decimal("1"), raw_amount=Decimal("1"), source_payload_hash="p", available_at=NOW, availability_policy_version="v1")


def status(day):
    return DailySecurityStatusFactV1.create(security_identity="000001.SZ", session=day, is_listed=True, is_delisted=False, is_risk_warning=False, is_suspended=False, effective_from=day, effective_to=day, available_at=NOW, source_fact_ids=("s",), source_name="test", policy_version="v1", risk_warning_excluded=False)


def bundle(*, latest=date(2024, 1, 9), eligible=True, provenance=ProvenancePath.HISTORICAL):
    domains = tuple(DomainLineageV1.create(domain=name, approval_id=str(i)*64, manifest_id=str(i+5)*64, fact_ids=(("abcdef"[i])*64,)) for i, name in enumerate(LabelContractV1().required_domains))
    kwargs = dict(canonical_security_identity="000001.SZ", anchor_session=SESSIONS[0], anchor_boundary=AnchorKnowledgeBoundary.create(SESSIONS[0], datetime(2024, 1, 2, 16, 30, tzinfo=timezone.utc), "a"*64, eligible), reference_price=LabelReferencePrice.create(SESSIONS[0], Decimal("10"), "b"*64, NOW), provenance_path=provenance, domain_lineage=domains, approved_exchange_sessions=SESSIONS, latest_completed_session=latest, future_bars=tuple(bar(day, str(10+i)) for i, day in enumerate(SESSIONS[1:], 1)), future_statuses=tuple(status(day) for day in SESSIONS[1:]), corporate_actions=(), action_coverage=CorporateActionCoverageV1.safe())
    if provenance is ProvenancePath.CONTEMPORANEOUS:
        kwargs.update(anchor_snapshot_id="c"*64, outcome_snapshot_id="d"*64)
    return LabelInputBundleV1.create(**kwargs)


def test_engine_returns_seven_canonical_labels_and_deterministic_hash():
    first = ReferenceLabelEngine().evaluate(bundle())
    second = ReferenceLabelEngine().evaluate(bundle())
    assert tuple(item.label_name for item in first.values) == ("return_1d", "return_3d", "return_5d", "max_favorable_excursion_5d", "max_adverse_excursion_5d", "hit_3pct_before_-2pct", "hit_5pct_before_-3pct")
    assert first.content_hash == second.content_hash and first.verify()


def test_one_day_available_while_five_day_labels_pending():
    result = ReferenceLabelEngine().evaluate(bundle(latest=date(2024, 1, 3)))
    by_name = {item.label_name: item for item in result.values}
    assert by_name["return_1d"].state is LabelState.LABEL_AVAILABLE
    assert by_name["return_5d"].state is LabelState.LABEL_PENDING
    assert by_name["return_5d"].reason_code is LabelReasonCode.HORIZON_NOT_COMPLETED


def test_anchor_ineligibility_fails_closed_before_outcomes():
    result = ReferenceLabelEngine().evaluate(bundle(eligible=False))
    assert all(item.state is LabelState.NOT_LABEL_SAFE and item.reason_code is LabelReasonCode.ANCHOR_NOT_RESEARCH_ELIGIBLE for item in result.values)


def test_historical_and_contemporaneous_snapshot_paths_have_same_values():
    historical = ReferenceLabelEngine().evaluate(bundle())
    current = ReferenceLabelEngine().evaluate(bundle(provenance=ProvenancePath.CONTEMPORANEOUS))
    assert tuple((x.state, x.value, x.reason_code) for x in historical.values) == tuple((x.state, x.value, x.reason_code) for x in current.values)
