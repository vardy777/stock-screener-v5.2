from __future__ import annotations

from dataclasses import fields
from datetime import date, datetime, timezone
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.phase_1b1_policies import phase_1b1_policies  # noqa: E402
from v5_2.data.phase_1b1_requests import phase_1b1_requests  # noqa: E402
from v5_2.data.raw_artifacts import RawArtifactStore  # noqa: E402
from v5_2.data.real_audits.policy_adequacy import ApprovalPolicyAdequacyReviewV1, CrossSourceEvidencePolicyV2, QuarantinedSecurityIdentityV1, UnresolvedIdentityImpactEvidenceV1  # noqa: E402
from v5_2.data.real_audits.identity_lineage import EffectiveDatedSecurityIdentityV1, HistoricalSecurityIdentityQuestionV1, IdentityIntervalV1  # noqa: E402
from v5_2.data.real_audits.security_master_normalization import SecurityMasterNormalizationPolicyV1  # noqa: E402


AS_OF = datetime(2026, 9, 6, tzinfo=timezone.utc)


def _mapping(item):
    return {field.name: getattr(item, field.name) for field in fields(item)}


def main() -> int:
    output = ROOT / "data" / "phase_1b1" / "governance"
    output.mkdir(parents=True, exist_ok=True)
    policies = phase_1b1_policies()
    cross_v2 = CrossSourceEvidencePolicyV2.create_default()
    review = ApprovalPolicyAdequacyReviewV1.evaluate(
        reviewed_policy_ids=(policies["trade_calendar"].policy_id, policies["security_master"].policy_id),
        gate_findings={
            "trade_calendar": "251 unresolved official-resolution samples; zero mismatches",
            "security_master": "one confirmed non-target, one resolved effective-dated graph and one quarantined legacy identity",
            "cross_source_v2": "designed but Tier 3 independent deterministic sample is absent",
            "survivorship": "remaining quarantine ends in 2006 and has zero overlap with research coverage beginning 2010",
        },
        independent_sample_available=False,
        quarantine_impact_bounded=True,
        reviewed_at=AS_OF,
        policy_version="approval-policy-adequacy-v1",
    )
    exception_evidence_id = "b3e050a611fa0772473341eedb1ba97fcddc33cf204db27c3cc82126e46e48c6"
    question = HistoricalSecurityIdentityQuestionV1.create(
        provider_identity="302132.SZ", provider_listing_date=date(2010, 8, 27),
        questions=("historical owner of listing_date", "code transition effective date", "predecessor identity"),
        input_artifact_ids=(exception_evidence_id,), policy_version="identity-question-v1",
    )
    graph = EffectiveDatedSecurityIdentityV1.create(
        provider_identity="302132.SZ",
        intervals=(
            IdentityIntervalV1("300114.SZ", date(2010, 8, 27), date(2025, 2, 16), "A_SHARE", "CHINEXT"),
            IdentityIntervalV1("302132.SZ", date(2025, 2, 17), None, "A_SHARE", "CHINEXT"),
        ), transition_event="SECURITY_CODE_CHANGE", transition_effective_at=date(2025, 2, 17),
        evidence_ids=("szse-listing-2010-300114", "szse-code-change-2025-302132"),
        policy_version="effective-identity-v1",
    )
    quarantines = (
        QuarantinedSecurityIdentityV1.create(
            identity="T600018.SH", reason="legacy absorbed-company provider identity is not a canonical exchange code",
            raw_artifact_ids=(exception_evidence_id,), evidence_ids=("sse-absorption-record-2011",),
            effective_at=AS_OF, policy_version="security-quarantine-v1",
        ),
    )
    impacts = (
        UnresolvedIdentityImpactEvidenceV1.create(
            identity="T600018.SH", possible_effective_from=date(2000, 7, 19),
            possible_effective_to=date(2006, 10, 20), affected_sessions=None,
            uncertainty="interval is bounded but predates the acquired 2010-2025 calendar, so affected session count is unavailable",
            maximum_research_impact="false exclusion for the bounded historical interval",
            recommended_disposition="QUARANTINE_OUTSIDE_APPROVED_COVERAGE", evidence_ids=(quarantines[0].quarantine_id,), policy_version="identity-impact-v1",
        ),
    )
    store = RawArtifactStore(ROOT / "data" / "phase_1b1")
    normalization = SecurityMasterNormalizationPolicyV1.create_default()
    master_rows = []
    for request in phase_1b1_requests()["security_master"]:
        request_root = store.root / "raw" / request.source_name / request.dataset_kind / request.request_id[:16]
        for path in sorted(request_root.rglob("*.json")):
            master_rows.extend(store.read_payload(path).provider_payload["rows"])
    dispositions = [normalization.disposition(row) for row in master_rows]
    resolved_rows = sum(row.get("ts_code") == graph.provider_identity for row in master_rows)
    native_eligible = dispositions.count("NORMALIZED_ELIGIBLE")
    excluded_count = dispositions.count("EXCLUDED_NON_TARGET")
    quarantined_count = len(master_rows) - native_eligible - excluded_count - resolved_rows
    reevaluation_body = {
        "schema_version": "SecurityMasterReevaluationEvidenceV1",
        "input_count": len(master_rows),
        "eligible_input_count": native_eligible + resolved_rows,
        "normalized_effective_dated_fact_count": native_eligible + len(graph.intervals),
        "excluded_non_target_count": excluded_count,
        "quarantined_count": quarantined_count,
        "quarantined_identity_hashes": tuple(item.quarantine_id for item in quarantines),
        "resolved_identity_graph_ids": (graph.graph_id,),
        "research_coverage_start": date(2010, 1, 1),
        "quarantine_coverage_overlap": False,
        "decision": "PENDING",
        "pending_reason": "frozen official deterministic identity sample remains incomplete",
        "policy_version": "security-master-reevaluation-v1",
    }
    reevaluation_id = content_hash(reevaluation_body)
    reevaluation = {**reevaluation_body, "evidence_id": reevaluation_id, "content_hash": reevaluation_id}
    artifacts = {
        f"approval-policy-adequacy-{review.review_id}.json": review,
        f"cross-source-policy-v2-{cross_v2.policy_id}.json": cross_v2,
        f"identity-question-{question.question_id}.json": question,
        f"effective-identity-{graph.graph_id}.json": graph,
        **{f"quarantine-{item.quarantine_id}.json": item for item in quarantines},
        **{f"identity-impact-{item.evidence_id}.json": item for item in impacts},
    }
    for name, item in artifacts.items():
        (output / name).write_bytes(canonical_json(_mapping(item)))
    (output / f"security-master-reevaluation-{reevaluation_id}.json").write_bytes(canonical_json(reevaluation))
    print(f"ADEQUACY_REVIEW={review.review_id} DECISION={review.decision}")
    print(f"CROSS_SOURCE_V2={cross_v2.policy_id} STATUS=DESIGNED_NOT_ADOPTED")
    print(f"IDENTITY_302132=RESOLVED GRAPH={graph.graph_id}")
    print(f"QUARANTINED_IDENTITIES={len(quarantines)} COVERAGE_OVERLAP=0")
    print(f"MASTER_REEVALUATION={reevaluation_id} INPUT={len(master_rows)} ELIGIBLE_INPUT={native_eligible + resolved_rows} NORMALIZED_FACTS={native_eligible + len(graph.intervals)} EXCLUDED={excluded_count} QUARANTINED={quarantined_count} APPROVAL=PENDING")
    print("CALENDAR_V1=RETAINED MASTER_V1=RETAINED DAILY_BAR_ENTRY_UNLOCKED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
