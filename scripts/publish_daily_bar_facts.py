from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields
from datetime import date, datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.daily_bar_facts import DailyBarFactV1  # noqa: E402
from v5_2.data.dataset_equivalence import DatasetEquivalenceDecision, DatasetEquivalenceEvidenceV1  # noqa: E402
from v5_2.data.evidence import EvidenceArtifactV1, EvidenceStatus, EvidenceType, EvidenceValidityPolicy, EvidenceValidityRuleV1  # noqa: E402
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.manifests import DatasetManifestV1  # noqa: E402
from v5_2.data.real_audits.daily_bar_exceptions import DailyBarExceptionBudgetV1  # noqa: E402
from v5_2.data.real_audits.daily_bar_normalization import DailyBarNormalizationPolicyV1  # noqa: E402
from v5_2.data.real_audits.daily_bar_units import DailyBarUnitPolicyV1  # noqa: E402
from v5_2.data.source_approval import ApprovalDecision, SourceApprovalArtifactV1, SourceApprovalRevocationArtifactV1  # noqa: E402


RUNTIME = ROOT / "data" / "phase_1b1"
GOVERNANCE = RUNTIME / "governance"
SOURCE = "datahubco_tushare_proxy"
DATASET = "daily_bar"
UPSTREAM = (
    "1581b4d367dba1256247ddd13e09b53d0f95b5b1deeb40af9e6ed4a36606353b",
    "f208c17accba6b669359f476b2fdf3a1bc9ec6856e7fa1831ccdd1c42b80d8cf",
)
INVENTORY_ID = "9b1d034f00ab0d637bc56ab120ffcf725f226f21c09d27c3b85e36a4f644a6ce"
AUDIT_ID = "c090d1762828db2b713a9c7e70ab076a2a37efc4a9a5f111bf7fdb61de9a0939"
CROSS_ID = "32d3b74551fc962cecb61a11839bdc177f1f3492fa1d11f8fba2fc9c15c7dd87"
REPLAY_ID = "f2dc6b315eef600dc83baa74224d8149f2c1ea83bc6ebed7586dd3c4cb8c19cf"
VERIFIED_AT = datetime(2026, 9, 7, 0, 5, tzinfo=timezone.utc)
SUPERSEDED_APPROVAL_ID = "50777e6ca46c0149885f0218291a0ce539f36cbfc1ef71e6e56a9f8131a12eee"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_immutable(path: Path, value) -> None:
    data = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        if path.read_bytes() != data:
            raise RuntimeError("immutable publication collision")
        return
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


def serializable(item):
    def convert(value):
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, Mapping):
            return {key: convert(nested) for key, nested in value.items()}
        if isinstance(value, (list, tuple)):
            return tuple(convert(nested) for nested in value)
        return value
    return convert({field.name: getattr(item, field.name) for field in fields(item)})


def main() -> int:
    offline = load(GOVERNANCE / f"daily-bar-offline-audit-{AUDIT_ID}.json")
    cross = load(GOVERNANCE / f"daily-bar-cross-source-{CROSS_ID}.json")
    replay = load(GOVERNANCE / f"daily-bar-replay-{REPLAY_ID}.json")
    if offline["findings"] != {"rows": offline["row_count"]} or not cross["passed"] or not replay["same_payload_different_receipt_pass"]:
        raise RuntimeError("daily-bar publication gate failed")
    payload_hashes = tuple(offline["payload_hashes"])
    source_version = content_hash(payload_hashes)
    evidence = []
    finding_by_type = {
        EvidenceType.COVERAGE: (f"observed_only_coverage_ratio={offline['coverage_ratio']}", f"unclassified_missing={offline['missing_symbol_sessions']}"),
        EvidenceType.PIT_TIME: ("D-close available_at=15:00 Asia/Shanghai", "acquired_at excluded from historical availability"),
        EvidenceType.REVISION: ("real first-middle-last replay payload identity stable", "changed payload revision contract test PASS"),
        EvidenceType.HISTORICAL_SAMPLE: ("full structural scan PASS", "OHLC/schema/session/effective identity PASS"),
        EvidenceType.CONTENT_IDENTITY: ("immutable raw payload hashes pinned", "request/page identity verified"),
        EvidenceType.LICENSE_USAGE: ("user-authorized source", "raw cache local and excluded from distribution"),
        EvidenceType.CROSS_SOURCE: ("BaoStock deterministic sample PASS", "volume factor=100 amount factor=1000"),
    }
    inputs = (AUDIT_ID, CROSS_ID, REPLAY_ID, *UPSTREAM, INVENTORY_ID)
    for kind in EvidenceType:
        evidence.append(EvidenceArtifactV1.create(
            evidence_type=kind, status=EvidenceStatus.PASS, observed_at=VERIFIED_AT,
            verified_at=VERIFIED_AT, policy_version="daily-bar-evidence-v1",
            source_version_identity=source_version, input_artifact_ids=inputs,
            valid_until=None, findings=finding_by_type[kind],
        ))
    validity = EvidenceValidityPolicy(
        policy_version="daily-bar-validity-v1",
        rules=tuple(EvidenceValidityRuleV1(kind, None, True, ("daily-bar-evidence-v1",)) for kind in EvidenceType),
    )
    equivalence = DatasetEquivalenceEvidenceV1.create(
        source_name=SOURCE, dataset_kind=DATASET,
        reference_contract="BaoStock adjustflag=3 independent unadjusted daily bar",
        tested_endpoints=("daily",), tested_fields=("ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"),
        coverage_tested={"start": "2010-01-04", "end": "2025-12-31", "rows": offline["row_count"]},
        sample_rule={"policy_id": "v5.2-phase-1b1-daily-bar-v1", "strata": 8},
        field_mapping={"vol": "volume_shares*0.01", "amount": "amount_yuan*0.001"},
        semantic_findings=("UNADJUSTED_RAW confirmed", "effective identity graph required"),
        missing_fields=(), extra_fields=(),
        value_comparison_summary={"price_tolerance": "0.0001", "volume_factor": "100", "amount_factor": "1000", "passed": True},
        pit_findings=("session bar available at D-close",),
        revision_findings=("real replay stable",), pagination_findings=("5548 terminal pages for 5548 requests",),
        cross_source_findings=("8 frozen strata price PASS", "7 unit-comparable strata PASS"),
        limitations=("missing bars are not security-status facts", "zero-volume observation absent", "plaintext provider transport"),
        decision=DatasetEquivalenceDecision.EQUIVALENT_WITH_RULES, verified_at=VERIFIED_AT,
        input_artifact_ids=inputs, policy_version="daily-bar-equivalence-v1",
    )
    approval = SourceApprovalArtifactV1.evaluate(
        source_name=SOURCE, dataset_kind=DATASET, coverage_start=date(2024, 1, 1), coverage_end=date(2025, 12, 31),
        verified_at=VERIFIED_AT, source_version_identity=source_version, policy_version="phase-1b1-daily-bar-v1",
        evaluator_version="phase-1b1-daily-bar-evaluator-v1", evidence=evidence,
        required_evidence_types=tuple(EvidenceType),
        rule_set={
            "price_basis": "UNADJUSTED_RAW", "volume_factor_to_shares": "100", "amount_factor_to_yuan": "1000",
            "availability_policy": "daily-bar-d-close-v1", "effective_identity_graph": "6275f4df087e40a11eb12b4ece0e569865814002d4da301342c2279af98acda0",
            "observed_bars_only": True, "missing_bar_has_no_status_semantics": True,
            "zero_volume_has_no_suspension_semantics": True, "transport_security": "PLAINTEXT_HTTP",
        },
        evidence_validity_policy=validity, resolution_as_of=VERIFIED_AT,
        equivalence_evidence=equivalence, supersedes_approval_id=SUPERSEDED_APPROVAL_ID,
    )
    if approval.decision is not ApprovalDecision.APPROVED_WITH_RULES:
        raise RuntimeError(f"unexpected approval decision: {approval.decision.value}")

    normalization = DailyBarNormalizationPolicyV1.create_default()
    volume_evidence_id = content_hash({"cross_source_evidence_id": CROSS_ID, "field": "vol", "factor": "100"})
    amount_evidence_id = content_hash({"cross_source_evidence_id": CROSS_ID, "field": "amount", "factor": "1000"})
    unit_policy = DailyBarUnitPolicyV1.create(volume_factor="100", amount_factor="1000", evidence_ids=(volume_evidence_id, amount_evidence_id))
    exception_policy = DailyBarExceptionBudgetV1.create_default()
    exception_set_hash = content_hash(())
    facts_root = RUNTIME / "facts" / "daily_bar"
    shard_hashes = []
    fact_count = 0
    fact_symbols = set()
    raw_root = RUNTIME / "raw" / SOURCE / DATASET
    for path in raw_root.rglob("*.json"):
        artifact = load(path)
        facts = []
        for row in artifact["provider_payload"]["rows"]:
            if not "20240101" <= row["trade_date"] <= "20251231":
                continue
            session = date(int(row["trade_date"][:4]), int(row["trade_date"][4:6]), int(row["trade_date"][6:]))
            fact = DailyBarFactV1.create(
                source_symbol=row["ts_code"], session=session,
                open=Decimal(str(row["open"])), high=Decimal(str(row["high"])), low=Decimal(str(row["low"])), close=Decimal(str(row["close"])),
                raw_volume=Decimal(str(row["vol"])), raw_amount=Decimal(str(row["amount"])), source_payload_hash=artifact["payload_hash"],
            )
            facts.append(serializable(fact))
            fact_symbols.add(fact.security_identity)
        if not facts:
            continue
        shard = {"schema_version": "DailyBarFactShardV1", "approval_id": approval.approval_id, "facts": facts}
        shard_hash = content_hash(shard)
        shard["content_hash"] = shard_hash
        write_immutable(facts_root / artifact["request_id"][:16] / f"{shard_hash}.json", shard)
        shard_hashes.append(shard_hash)
        fact_count += len(facts)

    receipt_hashes = []
    payload_set = set(payload_hashes)
    for path in (RUNTIME / "receipts").rglob("*.json"):
        receipt = load(path)
        if receipt["payload_hash"] in payload_set:
            receipt_hashes.append(receipt["receipt_hash"])
    manifest = DatasetManifestV1.create(
        created_at=VERIFIED_AT, source_name=SOURCE, dataset_kind=DATASET, approval=approval,
        approval_resolution_as_of=VERIFIED_AT, coverage_start=date(2024, 1, 1), coverage_end=date(2025, 12, 31),
        row_count=fact_count, symbol_count=len(fact_symbols), raw_payload_hashes=payload_hashes,
        normalized_content_hashes=tuple(sorted(shard_hashes)), fact_content_hashes=tuple(sorted(shard_hashes)),
        normalizer_version=normalization.policy_version, availability_policy_version="daily-bar-d-close-v1",
        quality_findings=(f"unclassified_missing_symbol_sessions={offline['missing_symbol_sessions']}", "observed_bars_only"),
        pit_validation_status="PASS", rule_compliance_status="PASS", pagination_complete=True,
        audit_policy_id="phase-1b1-daily-bar-v1", endpoint_identities=("daily",),
        receipt_hashes=tuple(sorted(receipt_hashes)), approval_policy_id="daily-bar-validity-v1",
        upstream_approval_ids=UPSTREAM, request_inventory_id=INVENTORY_ID,
        normalization_policy_id=normalization.policy_id, unit_policy_id=unit_policy.policy_id,
        exception_policy_id=exception_policy.budget_id, exception_set_hash=exception_set_hash,
        cross_source_evidence_id=CROSS_ID,
    )
    artifacts = (
        (f"daily_bar-equivalence-{equivalence.evidence_id}.json", equivalence),
        (f"daily_bar-approval-{approval.approval_id}.json", approval),
        (f"daily-bar-manifest-{manifest.manifest_hash}.json", manifest),
        (f"daily-bar-normalization-policy-{normalization.policy_id}.json", normalization),
        (f"daily-bar-unit-policy-{unit_policy.policy_id}.json", unit_policy),
        (f"daily-bar-exception-policy-{exception_policy.budget_id}.json", exception_policy),
    )
    for name, artifact in artifacts:
        write_immutable(GOVERNANCE / name, serializable(artifact))
    for item in evidence:
        write_immutable(GOVERNANCE / f"daily-bar-evidence-{item.evidence_id}.json", serializable(item))
    revocation = SourceApprovalRevocationArtifactV1.create(
        approval_id=SUPERSEDED_APPROVAL_ID,
        reason="superseded after effective-identity coverage accounting correction",
        effective_at=VERIFIED_AT, created_at=VERIFIED_AT,
        evidence_ids=(AUDIT_ID,), policy_version="daily-bar-revocation-v1",
    )
    write_immutable(GOVERNANCE / f"approval-revocation-{revocation.revocation_id}.json", serializable(revocation))
    print(f"DAILY_BAR_APPROVAL={approval.decision.value} APPROVAL_ID={approval.approval_id}")
    print(f"FACTS_PUBLICATION=PASS ROWS={fact_count} SYMBOLS={len(fact_symbols)} SHARDS={len(shard_hashes)}")
    print(f"DATASET_MANIFEST=PASS MANIFEST_ID={manifest.manifest_hash} RECEIPTS={len(receipt_hashes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
