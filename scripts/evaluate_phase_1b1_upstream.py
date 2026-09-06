from __future__ import annotations

from dataclasses import fields
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.dataset_equivalence import DatasetEquivalenceDecision, DatasetEquivalenceEvidenceV1  # noqa: E402
from v5_2.data.evidence import EvidenceArtifactV1, EvidenceStatus, EvidenceType, EvidenceValidityPolicy, EvidenceValidityRuleV1  # noqa: E402
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.phase_1b1_policies import phase_1b1_policies  # noqa: E402
from v5_2.data.phase_1b1_requests import phase_1b1_requests  # noqa: E402
from v5_2.data.raw_artifacts import RawArtifactStore  # noqa: E402
from v5_2.data.real_audits.security_master_governance import CombinedUpstreamGateV1, QuarantineCoverageRuleV1  # noqa: E402
from v5_2.data.real_audits.validators import AuditDecision, audit_security_master, audit_trade_calendar  # noqa: E402
from v5_2.data.source_approval import SourceApprovalArtifactV1  # noqa: E402


AS_OF = datetime(2026, 9, 6, tzinfo=timezone.utc)
COMPOSITE_ID = "e5e42c14be97aa1bc8d4365f729dfa7d24bebf618141bfdf77f356c3072668d6"
ADOPTION_ID = "eaf31f1f1b96c2d2ec491b2f3149ad0d5bda0761defe9170c7e93937bd861c5c"
MASTER_SAMPLE_ID = "63acd57d97c01cbdf66dd7a8315a6b515fc0bf3a43ec7052602658db32f0a015"
MASTER_DISCREPANCY_ID = "7f198ffb8d6440e507873c3fad6f782992afa5a1cd4c678739eca1e9db2b2b56"
T600018_QUARANTINE_ID = "ab390fa0e61492777cf8c8711ed104cbc0f31e1ca83fa7a499235a91d45d51c2"


def _mapping(item):
    return {field.name: getattr(item, field.name) for field in fields(item)}


def _raw(kind: str):
    store = RawArtifactStore(ROOT / "data" / "phase_1b1")
    artifacts = []
    for request in phase_1b1_requests()[kind]:
        request_root = store.root / "raw" / request.source_name / kind / request.request_id[:16]
        artifacts.extend(store.read_payload(path) for path in sorted(request_root.rglob("*.json")))
    return tuple(artifacts)


def _validity():
    return EvidenceValidityPolicy(
        policy_version="phase-1b1-upstream-validity-v1",
        rules=tuple(EvidenceValidityRuleV1(kind, None, True, ("phase-1b1-upstream-evidence-v1",)) for kind in EvidenceType),
    )


def _evidence(source_version: str, inputs: tuple[str, ...], *, cross_source_pass: bool, findings: tuple[str, ...]):
    return tuple(EvidenceArtifactV1.create(
        evidence_type=kind,
        status=EvidenceStatus.PASS if kind is not EvidenceType.CROSS_SOURCE or cross_source_pass else EvidenceStatus.FAIL,
        observed_at=AS_OF, verified_at=AS_OF, policy_version="phase-1b1-upstream-evidence-v1",
        source_version_identity=source_version, input_artifact_ids=inputs,
        valid_until=None, findings=findings if kind is EvidenceType.CROSS_SOURCE else (),
    ) for kind in EvidenceType)


def main() -> int:
    output = ROOT / "data" / "phase_1b1" / "governance"
    policies = phase_1b1_policies()

    calendar_artifacts = _raw("trade_calendar")
    calendar_rows = tuple(row for artifact in calendar_artifacts for row in artifact.provider_payload["rows"])
    calendar_hashes = tuple(sorted(artifact.payload_hash for artifact in calendar_artifacts))
    calendar_audit = audit_trade_calendar(calendar_rows, start=date(2010, 1, 1), end=date(2025, 12, 31), exchanges=("SSE", "SZSE"))
    if calendar_audit.decision is AuditDecision.FAIL:
        raise RuntimeError("calendar structural gates failed")
    calendar_inputs = tuple(sorted((*calendar_hashes, COMPOSITE_ID, ADOPTION_ID)))
    calendar_version = content_hash(calendar_hashes)
    calendar_equivalence = DatasetEquivalenceEvidenceV1.create(
        source_name="datahubco_tushare_proxy", dataset_kind="trade_calendar",
        reference_contract="V5.2 trade_calendar Phase 1B-1 V2 adopted",
        tested_endpoints=("trade-cal",), tested_fields=("exchange", "cal_date", "is_open", "pretrade_date"),
        coverage_tested={"start": "2010-01-01", "end": "2025-12-31", "rows": len(calendar_rows)},
        sample_rule=dict(policies["trade_calendar"].sample_selection_rule),
        field_mapping={"cal_date": "calendar_date", "is_open": "is_open", "pretrade_date": "previous_session"},
        semantic_findings=(f"structural_audit={calendar_audit.decision.value}",), missing_fields=(), extra_fields=(),
        value_comparison_summary={"matched": 256, "mismatched": 0, "unresolved": 0, "provider_error": 0},
        pit_findings=("explicit daily session state; weekday inference forbidden",),
        revision_findings=("same request/page payload identity remains revision-sensitive",),
        pagination_findings=("all requested pages complete and replayed",),
        cross_source_findings=(f"composite={COMPOSITE_ID}", f"v2_adoption={ADOPTION_ID}"),
        limitations=("transport_security=PLAINTEXT_HTTP",),
        decision=DatasetEquivalenceDecision.EQUIVALENT_WITH_RULES,
        verified_at=AS_OF, input_artifact_ids=calendar_inputs, policy_version="phase-1b1-equivalence-v2",
    )
    calendar_approval = SourceApprovalArtifactV1.evaluate(
        source_name="datahubco_tushare_proxy", dataset_kind="trade_calendar",
        coverage_start=date(2010, 1, 1), coverage_end=date(2025, 12, 31), verified_at=AS_OF,
        source_version_identity=calendar_version, policy_version=policies["trade_calendar"].policy_version,
        evaluator_version="phase-1b1-upstream-evaluator-v1",
        evidence=_evidence(calendar_version, calendar_inputs, cross_source_pass=True, findings=("256/256 exact frozen samples match",)),
        required_evidence_types=tuple(EvidenceType),
        rule_set={"transport_security": "PLAINTEXT_HTTP", "cross_source_policy_v2_adoption_id": ADOPTION_ID, "composite_calendar_evidence_id": COMPOSITE_ID},
        evidence_validity_policy=_validity(), resolution_as_of=AS_OF,
        equivalence_evidence=calendar_equivalence,
        supersedes_approval_id="97f37b1b5983ee14728de550b9b649a7a86a0e550570b71c969d44b26279dc23",
    )

    master_artifacts = _raw("security_master")
    master_rows = tuple(row for artifact in master_artifacts for row in artifact.provider_payload["rows"])
    master_hashes = tuple(sorted(artifact.payload_hash for artifact in master_artifacts))
    master_audit = audit_security_master(master_rows)
    master_inputs = tuple(sorted((*master_hashes, MASTER_SAMPLE_ID, MASTER_DISCREPANCY_ID)))
    master_version = content_hash(master_hashes)
    master_equivalence = DatasetEquivalenceEvidenceV1.create(
        source_name="datahubco_tushare_proxy", dataset_kind="security_master",
        reference_contract="V5.2 security_master Phase 1B-1 frozen official sample",
        tested_endpoints=("stock-basic",), tested_fields=("symbol", "exchange", "list_date", "delist_date", "market"),
        coverage_tested={"as_of": "2025-12-31", "rows": len(master_rows)},
        sample_rule=dict(policies["security_master"].sample_selection_rule),
        field_mapping={"list_date": "listing_date", "delist_date": "delisting_date", "market": "board"},
        semantic_findings=(f"structural_audit={master_audit.decision.value}", "600747.SH delisting-date discrepancy remains unexplained"),
        missing_fields=("official board for three historical SZSE delist samples",), extra_fields=(),
        value_comparison_summary={"verified": 28, "mismatched": 1, "unresolved": 3},
        pit_findings=("effective-dated 300114.SZ to 302132.SZ identity graph preserved",),
        revision_findings=("identity changes require new effective-dated facts",),
        pagination_findings=("all listing-status pages complete",),
        cross_source_findings=(f"official_sample={MASTER_SAMPLE_ID}", f"discrepancy={MASTER_DISCREPANCY_ID}"),
        limitations=("one mismatch and three unresolved official board fields",),
        decision=DatasetEquivalenceDecision.NOT_EQUIVALENT,
        verified_at=AS_OF, input_artifact_ids=master_inputs, policy_version="phase-1b1-equivalence-v2",
    )
    coverage_rule = QuarantineCoverageRuleV1.create(
        quarantine_id=T600018_QUARANTINE_ID, effective_from=date(2000, 7, 19), effective_to=date(2006, 10, 20),
        minimum_coverage_start=date(2010, 1, 1), policy_version="coverage-rule-v1",
    )
    master_approval = SourceApprovalArtifactV1.evaluate(
        source_name="datahubco_tushare_proxy", dataset_kind="security_master",
        coverage_start=date(2010, 1, 1), coverage_end=date(2025, 12, 31), verified_at=AS_OF,
        source_version_identity=master_version, policy_version=policies["security_master"].policy_version,
        evaluator_version="phase-1b1-upstream-evaluator-v1",
        evidence=_evidence(master_version, master_inputs, cross_source_pass=False, findings=("official sample mismatch=1 unresolved=3",)),
        required_evidence_types=tuple(EvidenceType),
        rule_set={"coverage_rule_id": coverage_rule.rule_id, "minimum_coverage_start": "2010-01-01", "quarantine_id": T600018_QUARANTINE_ID},
        evidence_validity_policy=_validity(), resolution_as_of=AS_OF,
        equivalence_evidence=master_equivalence,
        supersedes_approval_id="d2d8fbdf4c57e2d981fd144a0879fd848939512ce9e2725edfe8d340d89e10b5",
    )
    gate = CombinedUpstreamGateV1.evaluate(
        trade_calendar_approval_id=calendar_approval.approval_id, trade_calendar_decision=calendar_approval.decision.value,
        security_master_approval_id=master_approval.approval_id, security_master_decision=master_approval.decision.value,
        revoked_approval_ids=(), evaluated_at=AS_OF,
    )
    for name, artifact in (
        (f"trade_calendar-equivalence-{calendar_equivalence.evidence_id}.json", calendar_equivalence),
        (f"trade_calendar-approval-{calendar_approval.approval_id}.json", calendar_approval),
        (f"security_master-equivalence-{master_equivalence.evidence_id}.json", master_equivalence),
        (f"security_master-approval-{master_approval.approval_id}.json", master_approval),
        (f"quarantine-coverage-rule-{coverage_rule.rule_id}.json", coverage_rule),
        (f"combined-upstream-gate-{gate.gate_id}.json", gate),
    ):
        (output / name).write_bytes(canonical_json(_mapping(artifact)))
    print(f"TRADE_CALENDAR EQUIVALENCE={calendar_equivalence.decision.value} APPROVAL={calendar_approval.decision.value} APPROVAL_ID={calendar_approval.approval_id}")
    print(f"SECURITY_MASTER EQUIVALENCE={master_equivalence.decision.value} APPROVAL={master_approval.decision.value} APPROVAL_ID={master_approval.approval_id}")
    print(f"QUARANTINE_COVERAGE_RULE={coverage_rule.rule_id} COVERAGE_OVERLAP=0")
    print(f"DAILY_BAR_ENTRY_UNLOCKED={'YES' if gate.daily_bar_entry_unlocked else 'NO'} GATE_ID={gate.gate_id}")
    print("DAILY_BAR_ACQUISITION=NOT_STARTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
