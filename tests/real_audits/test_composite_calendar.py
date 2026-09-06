from __future__ import annotations

from datetime import datetime, timezone

import pytest

from scripts.acquire_szse_calendar_audit import _fetch_with_retry, _load_cached_domains

from v5_2.data.real_audits.policy_adequacy import EvidenceResolution
from v5_2.data.real_audits.tier3_calendar import (
    CompositeIndependentCalendarEvidenceV1,
    CompleteSessionDomainV1,
    IndependentCalendarComparisonEvidenceV1,
    IndependentCalendarSampleRequestV1,
    IndependentSourceIdentityV1,
    CrossSourceEvidencePolicyAdoptionArtifactV1,
    compare_independent_calendar,
)
from v5_2.data.real_audits.policy_adequacy import CrossSourceEvidencePolicyV2


NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)


def _source(name: str, exchange: str) -> IndependentSourceIdentityV1:
    return IndependentSourceIdentityV1.create(
        source_name=name,
        provider_identity=name,
        dataset_kind="trade_calendar",
        endpoint_identity="full-month-calendar",
        source_independence_rationale="direct provider interface unrelated to current ingestion provider",
        coverage_capability={"start": "2010-01-01", "end": "2025-12-31", "exchanges": (exchange,)},
        schema_identity=("calendar_date", "is_open"),
        retrieved_at=NOW,
        policy_version="independent-source-v1",
        tls_certificate_verified=True,
        hostname_verified=True,
    )


def _requests(exchange: str, count: int, source: IndependentSourceIdentityV1):
    frozen = tuple(
        {
            "sample_id": f"{exchange}-{index:03d}",
            "exchange": exchange,
            "calendar_date": f"2025-01-{index + 1:02d}",
            "sample_stratum": "frozen",
            "provider_is_open": index % 2,
        }
        for index in range(count)
    )
    return IndependentCalendarSampleRequestV1.from_frozen(frozen, source)


def test_complete_domain_requires_every_calendar_date_before_absence_means_closed() -> None:
    with pytest.raises(ValueError, match="complete"):
        CompleteSessionDomainV1.create(
            exchange="SZSE", start="2025-01-01", end="2025-01-03",
            observations={"2025-01-01": 0, "2025-01-02": 1}, source_id="source",
            policy_version="complete-domain-v1",
        )

    domain = CompleteSessionDomainV1.create(
        exchange="SZSE", start="2025-01-01", end="2025-01-03",
        observations={"2025-01-01": 0, "2025-01-02": 1, "2025-01-03": 0},
        source_id="source", policy_version="complete-domain-v1",
    )
    assert domain.observation("2025-01-01") == 0
    assert domain.observation("2025-01-04") is None


def test_acquisition_resume_reuses_only_matching_immutable_month_domains(tmp_path) -> None:
    (tmp_path / "szse-calendar-domain-good.json").write_text(
        '{"exchange":"SZSE","start":"2025-01-01","end":"2025-01-02",'
        '"observations":{"2025-01-01":0,"2025-01-02":1},"source_id":"source",'
        '"policy_version":"szse-complete-month-domain-v1"}', encoding="utf-8",
    )
    (tmp_path / "szse-calendar-domain-wrong.json").write_text(
        '{"exchange":"SZSE","start":"2025-02-01","end":"2025-02-01",'
        '"observations":{"2025-02-01":0},"source_id":"other",'
        '"policy_version":"szse-complete-month-domain-v1"}', encoding="utf-8",
    )
    cached = _load_cached_domains(tmp_path, "source")
    assert tuple(cached) == ("2025-01",)
    assert cached["2025-01"].observation("2025-01-02") == 1


def test_official_month_fetch_uses_bounded_retry() -> None:
    attempts = []

    def flaky(month):
        attempts.append(month)
        if len(attempts) < 3:
            raise ConnectionError("temporary")
        return {"2025-01-01": 0}

    assert _fetch_with_retry(flaky, "2025-01", max_attempts=3, sleeper=lambda _: None) == {"2025-01-01": 0}
    assert attempts == ["2025-01", "2025-01", "2025-01"]
    with pytest.raises(ConnectionError):
        _fetch_with_retry(lambda month: (_ for _ in ()).throw(ConnectionError(month)), "2025-02", max_attempts=2, sleeper=lambda _: None)


def test_only_exact_128_unresolved_szse_ids_are_reused() -> None:
    source = _source("SZSE official", "SZSE")
    requests = _requests("SZSE", 128, source)
    assert len(requests) == 128
    assert {item.sample_id for item in requests} == {f"SZSE-{index:03d}" for index in range(128)}


def test_composite_preserves_old_evidence_and_rejects_duplicate_or_conflicting_ids() -> None:
    sse_source = _source("BaoStock", "SSE")
    szse_source = _source("SZSE official", "SZSE")
    sse_requests = _requests("SSE", 2, sse_source)
    szse_requests = _requests("SZSE", 2, szse_source)
    sse = compare_independent_calendar(
        sse_requests, {item.calendar_date: item.datahub_observation for item in sse_requests},
        sse_source, official_anchors={},
    )
    szse = compare_independent_calendar(
        szse_requests, {item.calendar_date: item.datahub_observation for item in szse_requests},
        szse_source, official_anchors={},
    )
    old_hash = sse.content_hash
    composite = CompositeIndependentCalendarEvidenceV1.create(
        frozen_sample_ids=tuple(item.sample_id for item in (*sse_requests, *szse_requests)),
        components=(sse, szse), preserved_evidence_ids=(old_hash,), policy_version="composite-v1",
    )
    assert composite.total == 4
    assert composite.match_count == 4
    assert sse.content_hash == old_hash
    assert composite.preserved_evidence_ids == (old_hash,)

    with pytest.raises(ValueError, match="duplicate"):
        CompositeIndependentCalendarEvidenceV1.create(
            frozen_sample_ids=tuple(item.sample_id for item in sse_requests),
            components=(sse, sse), policy_version="composite-v1",
        )


def test_composite_conflict_and_unavailable_fail_closed() -> None:
    source = _source("SZSE official", "SZSE")
    requests = _requests("SZSE", 1, source)
    match = compare_independent_calendar(
        requests, {requests[0].calendar_date: requests[0].datahub_observation}, source, official_anchors={},
    )
    conflicting_record = dict(match.records[0])
    conflicting_record["resolution"] = EvidenceResolution.MISMATCH
    conflict = IndependentCalendarComparisonEvidenceV1.from_records(
        records=(conflicting_record,), source_id="another-independent-source",
    )
    with pytest.raises(ValueError, match="duplicate|conflict"):
        CompositeIndependentCalendarEvidenceV1.create(
            frozen_sample_ids=(requests[0].sample_id,), components=(match, conflict), policy_version="composite-v1",
        )

    unavailable = compare_independent_calendar(requests, {}, source, official_anchors={})
    composite = CompositeIndependentCalendarEvidenceV1.create(
        frozen_sample_ids=(requests[0].sample_id,), components=(unavailable,), policy_version="composite-v1",
    )
    assert composite.match_count == 0
    assert composite.unresolved_count == 1


def test_v2_adoption_pins_v1_without_rewriting_it() -> None:
    source = _source("SZSE official", "SZSE")
    v1_id = "immutable-v1-policy"
    adoption = CrossSourceEvidencePolicyAdoptionArtifactV1.create(
        v1_policy_id=v1_id, v2_policy=CrossSourceEvidencePolicyV2.create_default(),
        independent_source=source, sample_evidence_id="composite", total=256,
        matches=256, mismatches=0, unresolved=0, provider_errors=0,
        official_anchor_evidence_ids=("a", "b", "c", "d", "e"),
        adopted_at=NOW, methodological_reason="frozen complete evidence",
    )
    assert adoption.v1_policy_id == v1_id
    assert adoption.sample_evidence_id == "composite"
