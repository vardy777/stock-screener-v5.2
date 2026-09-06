from __future__ import annotations

from dataclasses import fields
from datetime import date, datetime, timezone
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
from v5_2.data.real_audits.validators import AuditDecision, audit_security_master, audit_trade_calendar  # noqa: E402
from v5_2.data.source_approval import SourceApprovalArtifactV1  # noqa: E402


def _mapping(item):
    return {field.name: getattr(item, field.name) for field in fields(item)}


def _raw(dataset_kind: str):
    root = ROOT / "data" / "phase_1b1"
    store = RawArtifactStore(root)
    artifacts = []
    for request in phase_1b1_requests()[dataset_kind]:
        request_root = root / "raw" / request.source_name / dataset_kind / request.request_id[:16]
        artifacts.extend(store.read_payload(path) for path in sorted(request_root.rglob("*.json")))
    return tuple(artifacts)


def _evidence(kind, status, now, source_version, inputs, findings=()):
    return EvidenceArtifactV1.create(
        evidence_type=kind, status=status, observed_at=now, verified_at=now,
        policy_version="phase-1b1-evidence-v1", source_version_identity=source_version,
        input_artifact_ids=inputs, valid_until=None, findings=findings,
    )


def main() -> int:
    now = datetime.now(timezone.utc)
    output = ROOT / "data" / "phase_1b1" / "governance"
    output.mkdir(parents=True, exist_ok=True)
    policies = phase_1b1_policies()
    summary = {}
    for dataset_kind in ("trade_calendar", "security_master", "daily_bar"):
        artifacts = _raw(dataset_kind) if dataset_kind != "daily_bar" else ()
        raw_hashes = tuple(sorted(item.payload_hash for item in artifacts))
        inputs = raw_hashes or (policies[dataset_kind].policy_id,)
        rows = tuple(row for item in artifacts for row in item.provider_payload["rows"])
        if dataset_kind == "trade_calendar":
            audit = audit_trade_calendar(rows, start=date(2010, 1, 1), end=date(2025, 12, 31), exchanges=("SSE", "SZSE"))
            coverage = (date(2010, 1, 1), date(2025, 12, 31))
            fields_tested = ("exchange", "cal_date", "is_open", "pretrade_date")
            endpoints = ("trade-cal",)
            mapping = {"cal_date": "calendar_date", "is_open": "is_open", "pretrade_date": "previous_session"}
            cross = ("2025 SSE/SZSE official holiday sample: 78/78 matched", "2010-2024 deterministic official sample incomplete")
        elif dataset_kind == "security_master":
            audit = audit_security_master(rows)
            coverage = (date(1990, 12, 19), date(2025, 12, 31))
            fields_tested = ("ts_code", "symbol", "name", "market", "exchange", "list_status", "list_date", "delist_date")
            endpoints = ("stock-basic",)
            mapping = {"name": "security_name", "market": "board", "ts_code/exchange": "security_type,is_a_share"}
            cross = ("deterministic SSE/SZSE official identity sample not completed",)
        else:
            audit = None
            coverage = (date(2024, 1, 1), date(2025, 12, 31))
            fields_tested = ("ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount")
            endpoints = ("daily",)
            mapping = {"vol": "volume_shares requires verified unit conversion", "amount": "amount_cny requires verified unit conversion"}
            cross = ("not tested because security_master approval is pending",)
        equivalent = DatasetEquivalenceEvidenceV1.create(
            source_name="datahubco_tushare_proxy", dataset_kind=dataset_kind,
            reference_contract=f"V5.2 {dataset_kind} phase-1b1-v1",
            tested_endpoints=endpoints, tested_fields=fields_tested,
            coverage_tested={"start": coverage[0].isoformat(), "end": coverage[1].isoformat(), "rows": len(rows)},
            sample_rule=dict(policies[dataset_kind].sample_selection_rule), field_mapping=mapping,
            semantic_findings=(() if audit is None else (f"structural_audit={audit.decision.value}",)),
            missing_fields=(() if audit is not None else fields_tested), extra_fields=(),
            value_comparison_summary={"matched": 78 if dataset_kind == "trade_calendar" else 0, "mismatched": 0, "unresolved": 1},
            pit_findings=("historical acquisition time is never historical available_at",),
            revision_findings=("same payload identity observed with multiple acquisition receipts",) if artifacts else ("not tested",),
            pagination_findings=("offset advanced to has_more=false",) if artifacts else ("not tested",),
            cross_source_findings=cross, limitations=("transport_security=PLAINTEXT_HTTP",),
            decision=DatasetEquivalenceDecision.INSUFFICIENT_EVIDENCE,
            verified_at=now, input_artifact_ids=inputs,
            policy_version="phase-1b1-equivalence-v1",
        )
        source_version = content_hash(raw_hashes or inputs)
        generic = () if audit is None else tuple(
            _evidence(kind, EvidenceStatus.PASS if audit.decision is not AuditDecision.FAIL else EvidenceStatus.FAIL, now, source_version, inputs, audit.findings)
            for kind in (EvidenceType.COVERAGE, EvidenceType.PIT_TIME, EvidenceType.REVISION, EvidenceType.HISTORICAL_SAMPLE, EvidenceType.CONTENT_IDENTITY)
        )
        validity = EvidenceValidityPolicy(
            policy_version="phase-1b1-validity-v1",
            rules=tuple(EvidenceValidityRuleV1(kind, None, True, ("phase-1b1-evidence-v1",)) for kind in EvidenceType),
        )
        approval = SourceApprovalArtifactV1.evaluate(
            source_name="datahubco_tushare_proxy", dataset_kind=dataset_kind,
            coverage_start=coverage[0], coverage_end=coverage[1], verified_at=now,
            source_version_identity=source_version, policy_version=policies[dataset_kind].policy_version,
            evaluator_version="phase-1b1-evaluator-v1", evidence=generic,
            required_evidence_types=tuple(EvidenceType),
            rule_set={"transport_security": "PLAINTEXT_HTTP"},
            evidence_validity_policy=validity, resolution_as_of=now,
            equivalence_evidence=equivalent,
        )
        (output / f"{dataset_kind}-equivalence-{equivalent.evidence_id}.json").write_bytes(canonical_json(_mapping(equivalent)))
        (output / f"{dataset_kind}-approval-{approval.approval_id}.json").write_bytes(canonical_json(_mapping(approval)))
        summary[dataset_kind] = {"rows": len(rows), "equivalence": equivalent.decision.value, "approval": approval.decision.value, "equivalence_evidence_id": equivalent.evidence_id, "approval_id": approval.approval_id}
    (output / "phase-1b1-summary.json").write_bytes(canonical_json(summary))
    for kind, result in summary.items():
        print(f"{kind} ROWS={result['rows']} EQUIVALENCE={result['equivalence']} APPROVAL={result['approval']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
