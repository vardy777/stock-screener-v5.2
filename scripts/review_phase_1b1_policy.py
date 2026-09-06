from __future__ import annotations

from dataclasses import fields
from datetime import date, datetime, timezone
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.phase_1b1_policies import phase_1b1_policies  # noqa: E402
from v5_2.data.real_audits.policy_adequacy import ApprovalPolicyAdequacyReviewV1, CrossSourceEvidencePolicyV2, QuarantinedSecurityIdentityV1, UnresolvedIdentityImpactEvidenceV1  # noqa: E402


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
            "security_master": "one confirmed non-target and two quarantined unresolved identities",
            "cross_source_v2": "designed but Tier 3 independent deterministic sample is absent",
            "survivorship": "one quarantined identity has an unbounded possible effective interval",
        },
        independent_sample_available=False,
        quarantine_impact_bounded=False,
        reviewed_at=AS_OF,
        policy_version="approval-policy-adequacy-v1",
    )
    exception_evidence_id = "b3e050a611fa0772473341eedb1ba97fcddc33cf204db27c3cc82126e46e48c6"
    quarantines = tuple(
        QuarantinedSecurityIdentityV1.create(
            identity=identity, reason=reason, raw_artifact_ids=(exception_evidence_id,),
            evidence_ids=(official,), effective_at=AS_OF, policy_version="security-quarantine-v1",
        )
        for identity, reason, official in (
            ("T600018.SH", "legacy absorbed-company provider identity is not a canonical exchange code", "sse-absorption-record-2011"),
            ("302132.SZ", "current code is paired with an older listing date and needs effective-dated identity evidence", "szse-current-code-record-2025"),
        )
    )
    impacts = (
        UnresolvedIdentityImpactEvidenceV1.create(
            identity="T600018.SH", possible_effective_from=date(2000, 7, 19),
            possible_effective_to=date(2006, 10, 20), affected_sessions=None,
            uncertainty="interval is bounded but predates the acquired 2010-2025 calendar, so affected session count is unavailable",
            maximum_research_impact="false exclusion for the bounded historical interval",
            recommended_disposition="QUARANTINE", evidence_ids=(quarantines[0].quarantine_id,), policy_version="identity-impact-v1",
        ),
        UnresolvedIdentityImpactEvidenceV1.create(
            identity="302132.SZ", possible_effective_from=date(2010, 8, 27),
            possible_effective_to=None, affected_sessions=None,
            uncertainty="effective date and predecessor/current-code lineage unresolved",
            maximum_research_impact="unbounded false exclusion or cross-identity historical corruption",
            recommended_disposition="QUARANTINE", evidence_ids=(quarantines[1].quarantine_id,), policy_version="identity-impact-v1",
        ),
    )
    artifacts = {
        f"approval-policy-adequacy-{review.review_id}.json": review,
        f"cross-source-policy-v2-{cross_v2.policy_id}.json": cross_v2,
        **{f"quarantine-{item.quarantine_id}.json": item for item in quarantines},
        **{f"identity-impact-{item.evidence_id}.json": item for item in impacts},
    }
    for name, item in artifacts.items():
        (output / name).write_bytes(canonical_json(_mapping(item)))
    print(f"ADEQUACY_REVIEW={review.review_id} DECISION={review.decision}")
    print(f"CROSS_SOURCE_V2={cross_v2.policy_id} STATUS=DESIGNED_NOT_ADOPTED")
    print(f"QUARANTINED_IDENTITIES={len(quarantines)} BOUNDED_IMPACT=1 UNBOUNDED_IMPACT=1")
    print("CALENDAR_V1=RETAINED MASTER_V1=RETAINED DAILY_BAR_ENTRY_UNLOCKED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
