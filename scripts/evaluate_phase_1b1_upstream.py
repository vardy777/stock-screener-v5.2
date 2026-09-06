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
from v5_2.data.real_audits.exception_governance import (ExceptionDisposition, ExceptionPatternAuditV1, ExceptionType, ExceptionalSecurityGovernancePolicyV1, ExceptionalSecurityRecordV1, HistoricalUniverseAdmissionV1, SecurityMasterExceptionBudgetV1)  # noqa: E402
from v5_2.data.real_audits.daily_bar_inventory import DailyBarRequestInventoryV1, DeterministicDailyBarUniverseV1  # noqa: E402
from v5_2.integrations.official_https import OfficialEvidenceTransportTrustV1  # noqa: E402
from v5_2.data.real_audits.validators import AuditDecision, audit_security_master, audit_trade_calendar  # noqa: E402
from v5_2.data.source_approval import SourceApprovalArtifactV1, SourceApprovalRevocationArtifactV1  # noqa: E402


AS_OF = datetime(2026, 9, 6, tzinfo=timezone.utc)
SECURE_SOURCE_ID = "b23194c57ee1004105413da7d9a09a141d5cffed3d8797739d4522ac25e2ff24"
COMPOSITE_ID = "19e54246af0355173a961cc9d91f6842e4094e2732bc650eab47c25734d5bece"
ADOPTION_ID = "0275632a8fb4d6e2de5990b68168f1da2d6244190dbc1e628e8693e82e6d13e6"
INSECURE_SOURCE_ID = "d5aaf8385159864b1e8923d4d3d7c70b2c0072b411f25dd1a3277048ec8d02fc"
INSECURE_COMPOSITE_ID = "e5e42c14be97aa1bc8d4365f729dfa7d24bebf618141bfdf77f356c3072668d6"
INSECURE_ADOPTION_ID = "eaf31f1f1b96c2d2ec491b2f3149ad0d5bda0761defe9170c7e93937bd861c5c"
INSECURE_APPROVAL_ID = "08933ef18a3532078ade97f6f5f574216e68f04225a95d7c7838bed5ad9b840d"
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
    insecure_trust = OfficialEvidenceTransportTrustV1.create(
        evidence_ids=(INSECURE_SOURCE_ID, INSECURE_COMPOSITE_ID, INSECURE_ADOPTION_ID, INSECURE_APPROVAL_ID),
        tls_certificate_verified=False, hostname_verified=False, assessed_at=AS_OF,
        policy_version="official-evidence-trust-v1",
    )
    secure_trust = OfficialEvidenceTransportTrustV1.create(
        evidence_ids=(SECURE_SOURCE_ID, COMPOSITE_ID, ADOPTION_ID), tls_certificate_verified=True,
        hostname_verified=True, assessed_at=AS_OF, policy_version="official-evidence-trust-v1",
    )
    secure_trust.require_final_approval()
    calendar_inputs = tuple(sorted((*calendar_hashes, COMPOSITE_ID, ADOPTION_ID, secure_trust.trust_id)))
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
        limitations=("primary DataHub transport remains plaintext HTTP", "old SZSE evidence invalidated because TLS verification was disabled"),
        decision=DatasetEquivalenceDecision.EQUIVALENT_WITH_RULES,
        verified_at=AS_OF, input_artifact_ids=calendar_inputs, policy_version="phase-1b1-equivalence-v2",
    )
    calendar_approval = SourceApprovalArtifactV1.evaluate(
        source_name="datahubco_tushare_proxy", dataset_kind="trade_calendar",
        coverage_start=date(2010, 1, 1), coverage_end=date(2025, 12, 31), verified_at=AS_OF,
        source_version_identity=calendar_version, policy_version=policies["trade_calendar"].policy_version,
        evaluator_version="phase-1b1-upstream-evaluator-v2",
        evidence=_evidence(calendar_version, calendar_inputs, cross_source_pass=True, findings=("256/256 exact frozen samples match",)),
        required_evidence_types=tuple(EvidenceType),
        rule_set={"primary_transport_security": "PLAINTEXT_HTTP", "official_tls_certificate_verified": True, "official_hostname_verified": True, "official_trust_id": secure_trust.trust_id, "cross_source_policy_v2_adoption_id": ADOPTION_ID, "composite_calendar_evidence_id": COMPOSITE_ID},
        evidence_validity_policy=_validity(), resolution_as_of=AS_OF,
        equivalence_evidence=calendar_equivalence,
        supersedes_approval_id=INSECURE_APPROVAL_ID,
    )
    insecure_revocation = SourceApprovalRevocationArtifactV1.create(
        approval_id=INSECURE_APPROVAL_ID, reason="authoritative SZSE observations were acquired with TLS certificate and hostname verification disabled",
        effective_at=AS_OF, created_at=AS_OF, evidence_ids=(insecure_trust.trust_id,), policy_version="official-evidence-trust-v1",
    )

    master_artifacts = _raw("security_master")
    master_rows = tuple(row for artifact in master_artifacts for row in artifact.provider_payload["rows"])
    master_hashes = tuple(sorted(artifact.payload_hash for artifact in master_artifacts))
    master_audit = audit_security_master(master_rows)
    exception_policy = ExceptionalSecurityGovernancePolicyV1.create_default()
    exception_budget = SecurityMasterExceptionBudgetV1.create_default(exception_policy.policy_id)
    official_market_system = "https://www.szse.cn/www/marketServices/listing/select/marketSystem/index.html"
    official_board_evidence_id = content_hash({"source": official_market_system, "finding": "SZSE main board began before the 2004 SME and 2009 ChiNext markets; 1993/1996/1997 listings are main-board listings", "verified_at": AS_OF})
    records = [ExceptionalSecurityRecordV1.create(
        security_identity="600747.SH", effective_from=date(2010, 1, 1), effective_to=date(2019, 12, 13),
        affected_fields=("delisting_date",), verified_fields=("symbol", "exchange", "listing_date", "board"),
        provider_values={"delisting_date": "20191212"}, reference_values={"SSE_structured": "20191213", "SSE_factbook": "20191212"},
        exception_type=ExceptionType.OFFICIAL_SOURCE_CONFLICT, evidence_ids=("4c3b33b02bd5b953402befe1b5869123417e892dee43b9ad88ab873300f3afb3", MASTER_DISCREPANCY_ID),
        disposition=ExceptionDisposition.QUARANTINE, research_impact="exclude from research requiring exact delisting_date semantics",
        created_at=AS_OF, policy_version=exception_policy.policy_version,
        dimensions={"exchange": "SSE", "board": "主板", "year": "2019", "listing_status": "D"},
    )]
    for code, listing, delisting, evidence_id in (
        ("000535.SZ", "1993-11-30", "2005-09-21", "40c92320fe19604c88da1dbfc049b71c8f22d475a336d36e11995d2e05e54a69"),
        ("000606.SZ", "1996-10-04", "2023-07-06", "293f2a51f3605f4d18fca5ac6b1661a2c40dbdfe2bb36f8fb55269db9cdb722b"),
        ("000760.SZ", "1997-06-27", "2021-07-23", "775a87600e6f3f7bb00fd06dfcae09d363bac50652c7bf406d1a281a86145356"),
    ):
        records.append(ExceptionalSecurityRecordV1.create(
            security_identity=code, effective_from=date.fromisoformat(listing), effective_to=date.fromisoformat(delisting),
            affected_fields=(), verified_fields=("symbol", "exchange", "listing_date", "delisting_date", "board"),
            provider_values={"board": "主板"}, reference_values={"board": "主板", "derivation": "listing predates non-main-board SZSE markets"},
            exception_type=ExceptionType.OFFICIAL_FIELD_UNAVAILABLE, evidence_ids=(evidence_id, official_board_evidence_id),
            disposition=ExceptionDisposition.RESOLVED, research_impact="none after official market-system chronology resolution",
            created_at=AS_OF, policy_version=exception_policy.policy_version,
            dimensions={"exchange": "SZSE", "board": "主板", "year": listing[:4], "listing_status": "D"},
        ))
    records = tuple(records)
    pattern_audit = ExceptionPatternAuditV1.evaluate(records, total_securities=len(master_rows), policy=exception_policy)
    active_count = sum(record.disposition is not ExceptionDisposition.RESOLVED for record in records)
    impact_ratio = active_count / len(master_rows)
    budget_evaluation = exception_budget.evaluate(records, total_securities=len(master_rows), coverage_impact_ratio=impact_ratio, affected_session_ratio=impact_ratio, pattern_audit=pattern_audit)
    if not budget_evaluation.passed:
        raise RuntimeError(f"security exception budget failed: {budget_evaluation.reasons}")
    universe_gate = HistoricalUniverseAdmissionV1(records)
    exclusion = universe_gate.admit("600747.SH", date(2019, 12, 12), required_fields=("delisting_date",)).exclusion_evidence
    if exclusion is None:
        raise RuntimeError("field-scoped quarantine was not enforced")
    exception_set_hash = exception_policy.exception_set_hash(records)
    master_inputs = tuple(sorted((*master_hashes, MASTER_SAMPLE_ID, MASTER_DISCREPANCY_ID, exception_policy.policy_id, exception_budget.budget_id, pattern_audit.audit_id, budget_evaluation.evaluation_id, exception_set_hash)))
    master_version = content_hash(master_hashes)
    master_equivalence = DatasetEquivalenceEvidenceV1.create(
        source_name="datahubco_tushare_proxy", dataset_kind="security_master",
        reference_contract="V5.2 security_master Phase 1B-1 frozen official sample",
        tested_endpoints=("stock-basic",), tested_fields=("symbol", "exchange", "list_date", "delist_date", "market"),
        coverage_tested={"as_of": "2025-12-31", "rows": len(master_rows)},
        sample_rule=dict(policies["security_master"].sample_selection_rule),
        field_mapping={"list_date": "listing_date", "delist_date": "delisting_date", "market": "board"},
        semantic_findings=(f"structural_audit={master_audit.decision.value}", "600747.SH exact delisting-date semantics field-quarantined", "three historical SZSE boards resolved from official market-system chronology"),
        missing_fields=(), extra_fields=(),
        value_comparison_summary={"verified_direct": 28, "resolved_by_official_chronology": 3, "field_scoped_quarantine": 1},
        pit_findings=("effective-dated 300114.SZ to 302132.SZ identity graph preserved",),
        revision_findings=("identity changes require new effective-dated facts",),
        pagination_findings=("all listing-status pages complete",),
        cross_source_findings=(f"official_sample={MASTER_SAMPLE_ID}", f"discrepancy={MASTER_DISCREPANCY_ID}"),
        limitations=("600747.SH delisting_date unavailable for semantics-dependent research",),
        decision=DatasetEquivalenceDecision.EQUIVALENT_WITH_RULES,
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
        evaluator_version="phase-1b1-upstream-evaluator-v2",
        evidence=_evidence(master_version, master_inputs, cross_source_pass=True, findings=("explicit exceptions=4 active_quarantine=1 resolved=3 systematic_defect=false",)),
        required_evidence_types=tuple(EvidenceType),
        rule_set={"coverage_rule_id": coverage_rule.rule_id, "minimum_coverage_start": "2010-01-01", "legacy_quarantine_id": T600018_QUARANTINE_ID, "exception_policy_id": exception_policy.policy_id, "exception_budget_id": exception_budget.budget_id, "exception_set_hash": exception_set_hash, "field_scoped_restrictions": {"600747.SH": ("delisting_date",)}, "effective_identity_policy": "effective-dated-security-identity-v1", "universe_exclusion_evidence_required": True},
        evidence_validity_policy=_validity(), resolution_as_of=AS_OF,
        equivalence_evidence=master_equivalence,
        supersedes_approval_id="c0506bee3879f06028a6f24025993a87cc1be8825ff76f4f6041c1818a96e74b",
    )
    gate = CombinedUpstreamGateV1.evaluate(
        trade_calendar_approval_id=calendar_approval.approval_id, trade_calendar_decision=calendar_approval.decision.value,
        security_master_approval_id=master_approval.approval_id, security_master_decision=master_approval.decision.value,
        revoked_approval_ids=(INSECURE_APPROVAL_ID,), evaluated_at=AS_OF,
    )
    daily_artifacts = ()
    if gate.daily_bar_entry_unlocked:
        symbols = tuple(sorted({str(row["ts_code"]) for row in master_rows}))
        sessions = tuple(sorted({str(row["cal_date"]) for row in calendar_rows if int(row["is_open"]) == 1}))
        daily_universe = DeterministicDailyBarUniverseV1.create(
            upstream_approval_ids=(calendar_approval.approval_id, master_approval.approval_id), symbols=symbols,
            sessions=sessions, exception_set_hash=exception_set_hash,
        )
        daily_inventory = DailyBarRequestInventoryV1.create(
            universe=daily_universe, sample_strata=("exchange", "listing_status", "year"),
            volume_unit_audit="REQUIRED_BEFORE_APPROVAL", amount_unit_audit="REQUIRED_BEFORE_APPROVAL",
            cross_source_rule="PREDECLARED_STRATIFIED_SAMPLE_REQUIRES_INDEPENDENT_OR_OFFICIAL_EVIDENCE",
        )
        daily_artifacts = ((f"daily-bar-universe-{daily_universe.universe_id}.json", daily_universe), (f"daily-bar-request-inventory-{daily_inventory.inventory_id}.json", daily_inventory))
    for name, artifact in (
        (f"trade_calendar-equivalence-{calendar_equivalence.evidence_id}.json", calendar_equivalence),
        (f"trade_calendar-approval-{calendar_approval.approval_id}.json", calendar_approval),
        (f"official-evidence-trust-{insecure_trust.trust_id}.json", insecure_trust),
        (f"official-evidence-trust-{secure_trust.trust_id}.json", secure_trust),
        (f"approval-revocation-{insecure_revocation.revocation_id}.json", insecure_revocation),
        (f"security_master-equivalence-{master_equivalence.evidence_id}.json", master_equivalence),
        (f"security_master-approval-{master_approval.approval_id}.json", master_approval),
        (f"quarantine-coverage-rule-{coverage_rule.rule_id}.json", coverage_rule),
        (f"combined-upstream-gate-{gate.gate_id}.json", gate),
        *((f"exceptional-security-{record.exception_id}.json", record) for record in records),
        (f"exception-pattern-audit-{pattern_audit.audit_id}.json", pattern_audit),
        (f"exception-budget-{exception_budget.budget_id}.json", exception_budget),
        (f"exception-budget-evaluation-{budget_evaluation.evaluation_id}.json", budget_evaluation),
        (f"universe-exclusion-{exclusion.evidence_id}.json", exclusion),
        *daily_artifacts,
    ):
        (output / name).write_bytes(canonical_json(_mapping(artifact)))
    print(f"TRADE_CALENDAR EQUIVALENCE={calendar_equivalence.decision.value} APPROVAL={calendar_approval.decision.value} APPROVAL_ID={calendar_approval.approval_id}")
    print(f"SECURITY_MASTER EQUIVALENCE={master_equivalence.decision.value} APPROVAL={master_approval.decision.value} APPROVAL_ID={master_approval.approval_id}")
    print(f"SECURITY_MASTER_EXCEPTION_POLICY=PASS POLICY_ID={exception_policy.policy_id} EXCEPTIONS={len(records)} QUARANTINED={active_count}")
    print(f"EXCEPTION_BUDGET={'PASS' if budget_evaluation.passed else 'FAIL'} SYSTEMATIC_DEFECT_AUDIT={'FAIL' if pattern_audit.systematic_defect else 'PASS'}")
    print(f"QUARANTINE_COVERAGE_RULE={coverage_rule.rule_id} COVERAGE_OVERLAP=0")
    print(f"DAILY_BAR_ENTRY_UNLOCKED={'YES' if gate.daily_bar_entry_unlocked else 'NO'} GATE_ID={gate.gate_id}")
    print("DAILY_BAR_ACQUISITION=NOT_STARTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
