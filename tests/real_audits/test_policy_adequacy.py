from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from v5_2.data.real_audits.policy_adequacy import (
    ApprovalPolicyAdequacyReviewV1,
    CrossSourceEvidencePolicyV2,
    EvidenceResolution,
    QuarantinedIdentityError,
    QuarantinedSecurityIdentityV1,
    UnresolvedIdentityImpactEvidenceV1,
    filter_research_universe,
)


NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)


def test_unresolved_is_not_mismatch_or_provider_error() -> None:
    assert EvidenceResolution.UNRESOLVED_EVIDENCE is not EvidenceResolution.MISMATCH
    assert EvidenceResolution.OFFICIAL_REFERENCE_UNAVAILABLE is not EvidenceResolution.PROVIDER_ERROR


def test_adequacy_review_is_deterministic_and_retains_v1_when_evidence_is_insufficient() -> None:
    review = ApprovalPolicyAdequacyReviewV1.evaluate(
        reviewed_policy_ids=("calendar-v1", "master-v1"),
        gate_findings={"calendar_cross_source": "251 unresolved", "master_identity": "2 unresolved"},
        independent_sample_available=False,
        quarantine_impact_bounded=False,
        reviewed_at=NOW,
        policy_version="adequacy-v1",
    )
    repeated = ApprovalPolicyAdequacyReviewV1.evaluate(
        reviewed_policy_ids=("master-v1", "calendar-v1"),
        gate_findings={"master_identity": "2 unresolved", "calendar_cross_source": "251 unresolved"},
        independent_sample_available=False,
        quarantine_impact_bounded=False,
        reviewed_at=NOW,
        policy_version="adequacy-v1",
    )
    assert review.review_id == review.content_hash == repeated.review_id
    assert review.decision == "RETAIN_V1_PENDING"
    assert review.unresolved_treated_as_mismatch is False


def test_cross_source_v2_has_honest_tiers_and_cannot_pass_without_independent_sample() -> None:
    policy = CrossSourceEvidencePolicyV2.create_default()
    assert policy.tiers[0][0] == "TIER_1"
    assert policy.tiers[-1][0] == "TIER_4"
    assert policy.evaluate(official_anchor_count=5, independent_sample_count=0, unexplained_mismatch_count=0) == "INSUFFICIENT_EVIDENCE"
    assert policy.evaluate(official_anchor_count=5, independent_sample_count=256, unexplained_mismatch_count=0) == "EQUIVALENT_WITH_RULES"
    assert policy.evaluate(official_anchor_count=5, independent_sample_count=256, unexplained_mismatch_count=1) == "NOT_EQUIVALENT"


def test_quarantined_identity_never_enters_universe_and_explicit_request_fails() -> None:
    quarantine = QuarantinedSecurityIdentityV1.create(
        identity="T600018.SH", reason="ambiguous historical identity",
        raw_artifact_ids=("raw",), evidence_ids=("official",),
        effective_at=NOW, policy_version="quarantine-v1",
    )
    assert filter_research_universe(("600000.SH", "T600018.SH"), (quarantine,)) == ("600000.SH",)
    with pytest.raises(QuarantinedIdentityError):
        filter_research_universe(("T600018.SH",), (quarantine,), explicitly_requested=("T600018.SH",))


def test_impact_evidence_records_bounded_and_unbounded_false_exclusion() -> None:
    bounded = UnresolvedIdentityImpactEvidenceV1.create(
        identity="T600018.SH", possible_effective_from=date(2000, 7, 19),
        possible_effective_to=date(2006, 10, 20), affected_sessions=1524,
        uncertainty="identity alias unresolved", maximum_research_impact="false exclusion",
        recommended_disposition="QUARANTINE", evidence_ids=("official",), policy_version="impact-v1",
    )
    unbounded = UnresolvedIdentityImpactEvidenceV1.create(
        identity="302132.SZ", possible_effective_from=date(2010, 8, 27),
        possible_effective_to=None, affected_sessions=None,
        uncertainty="code reassignment effective date unresolved", maximum_research_impact="false exclusion and identity corruption",
        recommended_disposition="QUARANTINE", evidence_ids=("official",), policy_version="impact-v1",
    )
    assert bounded.content_hash == bounded.evidence_id
    assert bounded.affected_sessions == 1524
    assert unbounded.possible_effective_to is None
    assert unbounded.affected_sessions is None
