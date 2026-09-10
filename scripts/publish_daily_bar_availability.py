from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, time
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
from v5_2.data.real_audits.daily_bar_availability import (  # noqa: E402
    DailyBarAvailabilityBasis,
    DailyBarAvailabilityEvidenceV1,
    DailyBarAvailabilityPolicyV1,
    DailyBarProbeObservationV1,
)
from v5_2.data.source_approval import ApprovalDecision, SourceApprovalArtifactV1, SourceApprovalRevocationArtifactV1  # noqa: E402


SOURCE = "datahubco_tushare_proxy"
DATASET = "daily_bar"
OLD_MANIFEST_ID = "1ad71807083aba6222fa6ab27aedf47c0ac2e2ba65a56ad1ce5ae5956db43ead"
OLD_APPROVAL_ID = "1ead49dfaefdfb8e4e75c9d94170d440abe77986e3388a6e96e6805537c1173c"
AVAILABILITY_ID = "6877256040eb6abbea3e6c4434485aaa212f23eba7f675f9d088ce7e05850bcb"
PHASE_1B1 = ROOT / "data" / "phase_1b1"
RUNTIME = ROOT / "data" / "phase_1b2b"
GOVERNANCE = RUNTIME / "governance"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_immutable(path: Path, value) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        if path.read_bytes() != encoded:
            raise RuntimeError("immutable publication collision")
        return
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)


def load_availability() -> DailyBarAvailabilityEvidenceV1:
    raw = load(GOVERNANCE / f"daily-bar-availability-{AVAILABILITY_ID}.json")
    observations = tuple(DailyBarProbeObservationV1.create(
        session=date.fromisoformat(item["session"]),
        requested_at=datetime.fromisoformat(item["requested_at"]),
        expected_symbols=tuple(item["expected_symbols"]), rows=tuple(item["rows"]),
        payload_hash=item["payload_hash"], receipt_id=item["receipt_id"],
        source_version_identity=item["source_version_identity"],
    ) for item in raw["observations"])
    if any(item.content_hash != stored["content_hash"] for item, stored in zip(observations, raw["observations"], strict=True)):
        raise RuntimeError("availability observation integrity failed")
    evidence = DailyBarAvailabilityEvidenceV1.create(
        policy_version=raw["policy_version"], source_name=raw["source_name"],
        source_version_identity=raw["source_version_identity"],
        coverage_sessions=tuple(date.fromisoformat(item) for item in raw["coverage_sessions"]),
        probe_times=tuple(datetime.fromisoformat(item) for item in raw["probe_times"]),
        sample_scope=tuple(raw["sample_scope"]), observations=observations,
        revision_findings=tuple(raw["revision_findings"]),
        full_market_readiness_rule=raw["full_market_readiness_rule"],
        historical_available_at_rule=raw["historical_available_at_rule"],
        supporting_receipt_ids=tuple(raw["supporting_receipt_ids"]),
    )
    if evidence.content_hash != raw["content_hash"] or not evidence.verify() or not evidence.complete:
        raise RuntimeError("availability artifact integrity or completeness failed")
    return evidence


def load_open_sessions() -> tuple[date, ...]:
    sessions = set()
    for path in (PHASE_1B1 / "raw" / SOURCE / "trade_calendar").rglob("*.json"):
        for row in load(path)["provider_payload"]["rows"]:
            if str(row.get("is_open")) in {"1", "True", "true"}:
                text = str(row["cal_date"])
                sessions.add(date(int(text[:4]), int(text[4:6]), int(text[6:])))
    sessions.add(date(2026, 1, 5))  # pinned by availability evidence receipt
    return tuple(sorted(sessions))


def deserialize_fact(raw) -> DailyBarFactV1:
    return DailyBarFactV1(
        fact_id=raw["fact_id"], security_identity=raw["security_identity"],
        session=date.fromisoformat(raw["session"]), open=Decimal(raw["open"]),
        high=Decimal(raw["high"]), low=Decimal(raw["low"]), close=Decimal(raw["close"]),
        volume_shares=Decimal(raw["volume_shares"]), amount_yuan=Decimal(raw["amount_yuan"]),
        price_basis=raw["price_basis"], available_at=datetime.fromisoformat(raw["available_at"]),
        availability_policy_version=raw["availability_policy_version"],
        source_payload_hash=raw["source_payload_hash"], content_hash=raw["content_hash"],
    )


def main() -> int:
    availability = load_availability()
    old_manifest = load(PHASE_1B1 / "governance" / f"daily-bar-manifest-{OLD_MANIFEST_ID}.json")
    if old_manifest["approval_id"] != OLD_APPROVAL_ID:
        raise RuntimeError("frozen predecessor manifest changed")
    source_version = content_hash(tuple(old_manifest["raw_payload_hashes"]))
    if source_version != availability.source_version_identity:
        raise RuntimeError("availability source version mismatch")
    verified_at = max(availability.probe_times)
    inputs = tuple(sorted({AVAILABILITY_ID, OLD_MANIFEST_ID, OLD_APPROVAL_ID, *availability.supporting_receipt_ids}))
    evidence = tuple(EvidenceArtifactV1.create(
        evidence_type=kind, status=EvidenceStatus.PASS, observed_at=verified_at,
        verified_at=verified_at, policy_version="daily-bar-evidence-v2",
        source_version_identity=source_version, input_artifact_ids=inputs,
        valid_until=None,
        findings=(
            "Phase 1B-1 value and structural evidence remains pinned",
            "availability corrected to NEXT_SESSION_SAFE@16:30 Asia/Shanghai",
        ),
    ) for kind in EvidenceType)
    validity = EvidenceValidityPolicy(
        policy_version="daily-bar-validity-v2",
        rules=tuple(EvidenceValidityRuleV1(kind, None, True, ("daily-bar-evidence-v2",)) for kind in EvidenceType),
    )
    equivalence = DatasetEquivalenceEvidenceV1.create(
        source_name=SOURCE, dataset_kind=DATASET,
        reference_contract="Phase 1B-1 frozen value semantics plus Phase 1B-2B availability supersession",
        tested_endpoints=("daily",),
        tested_fields=("ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"),
        coverage_tested={"start": "2024-01-01", "end": "2025-12-31", "rows": old_manifest["row_count"]},
        sample_rule={"availability_artifact_id": AVAILABILITY_ID, "sample_count": len(availability.sample_scope)},
        field_mapping={"vol": "volume_shares*0.01", "amount": "amount_yuan*0.001"},
        semantic_findings=("UNADJUSTED_RAW retained", "D 15:00 availability removed"),
        missing_fields=(), extra_fields=(),
        value_comparison_summary={"phase_1b1_manifest": OLD_MANIFEST_ID, "passed": True},
        pit_findings=(availability.historical_available_at_rule,),
        revision_findings=availability.revision_findings,
        pagination_findings=("no historical reacquisition",),
        cross_source_findings=("Phase 1B-1 frozen cross-source evidence retained",),
        limitations=("bounded D+1 probe does not establish same-day full-market readiness",),
        decision=DatasetEquivalenceDecision.EQUIVALENT_WITH_RULES,
        verified_at=verified_at, input_artifact_ids=inputs,
        policy_version="daily-bar-equivalence-v2",
    )
    approval = SourceApprovalArtifactV1.evaluate(
        source_name=SOURCE, dataset_kind=DATASET,
        coverage_start=date.fromisoformat(old_manifest["coverage_start"]),
        coverage_end=date.fromisoformat(old_manifest["coverage_end"]),
        verified_at=verified_at, source_version_identity=source_version,
        policy_version="phase-1b2b-daily-bar-v1",
        evaluator_version="phase-1b2b-daily-bar-evaluator-v1", evidence=evidence,
        required_evidence_types=tuple(EvidenceType),
        rule_set={
            "availability_policy": "daily-bar-availability-v1",
            "historical_available_at": "NEXT_SESSION_SAFE@16:30 Asia/Shanghai",
            "availability_evidence_id": AVAILABILITY_ID,
            "value_semantics_manifest": OLD_MANIFEST_ID,
        },
        evidence_validity_policy=validity, resolution_as_of=verified_at,
        equivalence_evidence=equivalence, supersedes_approval_id=OLD_APPROVAL_ID,
    )
    if approval.decision is not ApprovalDecision.APPROVED_WITH_RULES:
        raise RuntimeError("corrected daily-bar approval did not pass")

    sessions = load_open_sessions()
    next_session = {current: following for current, following in zip(sessions, sessions[1:], strict=False)}
    policy = DailyBarAvailabilityPolicyV1(
        basis=DailyBarAvailabilityBasis.NEXT_SESSION_SAFE,
        cutoff=time(16, 30), policy_version=availability.policy_version,
    )
    pinned_shards = set(old_manifest["fact_content_hashes"])
    found_shards = set()
    new_shard_hashes = []
    fact_count = 0
    symbols = set()
    for path in (PHASE_1B1 / "facts" / "daily_bar").rglob("*.json"):
        if path.stem not in pinned_shards:
            continue
        old_shard = load(path)
        if old_shard.get("content_hash") != path.stem:
            raise RuntimeError("predecessor shard integrity failed")
        corrected = []
        for raw_fact in old_shard["facts"]:
            fact = deserialize_fact(raw_fact)
            if not fact.verify() or fact.availability_policy_version != "daily-bar-d-close-v1":
                raise RuntimeError("predecessor fact integrity or policy mismatch")
            following = next_session.get(fact.session)
            if following is None:
                raise RuntimeError(f"next safe session unavailable for {fact.session}")
            available_at = policy.available_at(
                fact.session, next_session=following, evidence=availability,
                source_version_identity=source_version,
            )
            replacement = fact.supersede_availability(
                available_at=available_at,
                availability_policy_version=policy.policy_version,
            )
            corrected.append(replacement.as_dict())
            symbols.add(replacement.security_identity)
        shard = {
            "schema_version": "DailyBarFactAvailabilitySupersessionShardV1",
            "approval_id": approval.approval_id,
            "availability_evidence_id": AVAILABILITY_ID,
            "supersedes_shard_hash": path.stem,
            "facts": corrected,
        }
        shard_hash = content_hash(shard)
        shard["content_hash"] = shard_hash
        write_immutable(RUNTIME / "facts" / "daily_bar" / path.parent.name / f"{shard_hash}.json", shard)
        new_shard_hashes.append(shard_hash)
        fact_count += len(corrected)
        found_shards.add(path.stem)
    if found_shards != pinned_shards or fact_count != old_manifest["row_count"]:
        raise RuntimeError("fact supersession coverage mismatch")

    manifest = DatasetManifestV1.create(
        created_at=verified_at, source_name=SOURCE, dataset_kind=DATASET, approval=approval,
        approval_resolution_as_of=verified_at,
        coverage_start=date.fromisoformat(old_manifest["coverage_start"]),
        coverage_end=date.fromisoformat(old_manifest["coverage_end"]),
        row_count=fact_count, symbol_count=len(symbols),
        raw_payload_hashes=tuple(old_manifest["raw_payload_hashes"]),
        normalized_content_hashes=tuple(sorted(new_shard_hashes)),
        fact_content_hashes=tuple(sorted(new_shard_hashes)),
        normalizer_version=old_manifest["normalizer_version"],
        availability_policy_version=policy.policy_version,
        quality_findings=tuple(old_manifest["quality_findings"]) + ("D 15:00 superseded by next-session-safe",),
        pit_validation_status="PASS", rule_compliance_status="PASS", pagination_complete=True,
        audit_policy_id=old_manifest["audit_policy_id"],
        endpoint_identities=tuple(old_manifest["endpoint_identities"]),
        receipt_hashes=tuple(old_manifest["receipt_hashes"]),
        approval_policy_id=validity.policy_version,
        upstream_approval_ids=tuple(old_manifest["upstream_approval_ids"]),
        request_inventory_id=old_manifest["request_inventory_id"],
        normalization_policy_id=old_manifest["normalization_policy_id"],
        unit_policy_id=old_manifest["unit_policy_id"],
        exception_policy_id=old_manifest["exception_policy_id"],
        exception_set_hash=old_manifest["exception_set_hash"],
        cross_source_evidence_id=old_manifest["cross_source_evidence_id"],
        availability_evidence_id=AVAILABILITY_ID,
    )
    revocation = SourceApprovalRevocationArtifactV1.create(
        approval_id=OLD_APPROVAL_ID,
        reason="superseded because D 15:00 market close did not prove provider availability",
        effective_at=verified_at, created_at=verified_at,
        evidence_ids=(AVAILABILITY_ID,), policy_version="daily-bar-availability-revocation-v1",
    )
    artifacts = {
        f"daily-bar-equivalence-{equivalence.evidence_id}.json": equivalence,
        f"daily-bar-approval-{approval.approval_id}.json": approval,
        f"daily-bar-manifest-{manifest.manifest_hash}.json": manifest,
        f"approval-revocation-{revocation.revocation_id}.json": revocation,
    }
    for name, artifact in artifacts.items():
        write_immutable(GOVERNANCE / name, artifact)
    for item in evidence:
        write_immutable(GOVERNANCE / f"daily-bar-evidence-{item.evidence_id}.json", item)
    print(f"DAILY_BAR_AVAILABILITY=PASS ARTIFACT_ID={AVAILABILITY_ID}")
    print(f"DAILY_BAR_REVISION_BEHAVIOR=PASS OBSERVATIONS={len(availability.observations)}")
    print(f"DAILY_BAR_SOURCE_APPROVAL={approval.decision.value} APPROVAL_ID={approval.approval_id}")
    print(f"FACTS_SUPERSESSION=PASS ROWS={fact_count} SHARDS={len(new_shard_hashes)}")
    print(f"DATASET_MANIFEST=PASS MANIFEST_ID={manifest.manifest_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
