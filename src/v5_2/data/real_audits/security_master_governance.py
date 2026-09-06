from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from types import MappingProxyType
from typing import Any

from v5_2.data.identity import content_hash


SECURITY_SAMPLE_STRATA = (
    "currently_listed", "recent_ipo", "old_ipo", "delisted",
    "SH_main", "SH_STAR", "SZ_main", "SZ_ChiNext",
)


def select_frozen_security_samples(rows: Sequence[Mapping[str, Any]], *, policy_id: str) -> tuple[Mapping[str, Any], ...]:
    predicates = {
        "currently_listed": lambda row: row.get("list_status") == "L",
        "recent_ipo": lambda row: str(row.get("list_date") or "") >= "20240101",
        "old_ipo": lambda row: str(row.get("list_date") or "") < "20000101",
        "delisted": lambda row: row.get("list_status") == "D",
        "SH_main": lambda row: row.get("exchange") == "SSE" and row.get("market") == "主板",
        "SH_STAR": lambda row: row.get("exchange") == "SSE" and row.get("market") == "科创板",
        "SZ_main": lambda row: row.get("exchange") == "SZSE" and row.get("market") in {"主板", "中小板"},
        "SZ_ChiNext": lambda row: row.get("exchange") == "SZSE" and row.get("market") == "创业板",
    }
    selected = []
    for stratum in SECURITY_SAMPLE_STRATA:
        candidates = [row for row in rows if predicates[stratum](row)]
        ranked = sorted(candidates, key=lambda row: content_hash({"seed": "v5.2-phase-1b1-security-master-v1", "stratum": stratum, "ts_code": row["ts_code"]}))
        if len(ranked) < 4:
            raise ValueError(f"frozen security sample stratum {stratum} has fewer than four records")
        for row in ranked[:4]:
            sample_id = content_hash({"policy_id": policy_id, "stratum": stratum, "ts_code": row["ts_code"]})
            selected.append(MappingProxyType({
                "sample_id": sample_id, "ts_code": row["ts_code"], "effective_identity": row["ts_code"],
                "exchange": row["exchange"], "sample_stratum": stratum,
                "fields_requiring_verification": ("symbol", "exchange", "listing_date", "delisting_date", "board"),
                "provider_values": MappingProxyType({
                    "symbol": row["symbol"], "exchange": row["exchange"], "listing_date": row.get("list_date"),
                    "delisting_date": row.get("delist_date"), "board": row.get("market"),
                }),
            }))
    return tuple(selected)


@dataclass(frozen=True, slots=True)
class SecurityMasterOfficialSampleInventoryV1:
    inventory_id: str
    records: tuple[Mapping[str, Any], ...]
    total: int
    verified: int
    mismatch: int
    unresolved: int
    verified_at: datetime
    policy_id: str
    policy_version: str
    content_hash: str

    @classmethod
    def create(cls, *, frozen_samples: Sequence[Mapping[str, Any]], official_evidence: Mapping[str, Mapping[str, Any]], verified_at: datetime, policy_id: str, policy_version: str):
        if verified_at.tzinfo is None or verified_at.utcoffset() is None:
            raise ValueError("verified_at must be timezone-aware")
        sample_ids = [str(item["sample_id"]) for item in frozen_samples]
        if len(sample_ids) != len(set(sample_ids)):
            raise ValueError("frozen sample IDs must be unique")
        unknown = set(official_evidence) - set(sample_ids)
        if unknown:
            raise ValueError("official evidence sample is not in frozen inventory")
        records = []
        for item in sorted(frozen_samples, key=lambda value: str(value["sample_id"])):
            evidence = official_evidence.get(str(item["sample_id"]), {})
            resolution = str(evidence.get("resolution", "UNRESOLVED"))
            if resolution not in {"VERIFIED", "MISMATCH", "UNRESOLVED"}:
                raise ValueError("invalid official evidence resolution")
            official_values = evidence.get("official_values")
            records.append(MappingProxyType({
                **dict(item),
                "official_evidence_id": evidence.get("evidence_id"),
                "official_source_identity": evidence.get("official_source_identity"),
                "official_values": None if official_values is None else MappingProxyType(dict(sorted(official_values.items()))),
                "official_evidence_status": resolution,
            }))
        counts = Counter(item["official_evidence_status"] for item in records)
        body = {"schema_version": "SecurityMasterOfficialSampleInventoryV1", "records": tuple(records), "total": len(records), "verified": counts["VERIFIED"], "mismatch": counts["MISMATCH"], "unresolved": counts["UNRESOLVED"], "verified_at": verified_at, "policy_id": policy_id, "policy_version": policy_version}
        digest = content_hash(body)
        return cls(inventory_id=digest, content_hash=digest, **{key: value for key, value in body.items() if key != "schema_version"})


@dataclass(frozen=True, slots=True)
class QuarantineCoverageRuleV1:
    rule_id: str
    quarantine_id: str
    effective_from: date
    effective_to: date
    minimum_coverage_start: date
    policy_version: str
    content_hash: str

    @classmethod
    def create(cls, **values):
        body = {"schema_version": "QuarantineCoverageRuleV1", **values}
        digest = content_hash(body)
        return cls(rule_id=digest, content_hash=digest, **values)

    def admits(self, coverage_start: date, coverage_end: date) -> bool:
        if coverage_start < self.minimum_coverage_start or coverage_end < coverage_start:
            return False
        return coverage_end < self.effective_from or coverage_start > self.effective_to


@dataclass(frozen=True, slots=True)
class ApprovalWithCoverageRulesV1:
    artifact_id: str
    source_approval_id: str
    coverage_rule_id: str
    minimum_coverage_start: date
    quarantine_id: str
    quarantine_effective_interval: tuple[date, date]
    normalization_policy_id: str
    identity_lineage_policy_id: str
    approval_policy_id: str
    approved_at: datetime
    content_hash: str

    @classmethod
    def create(cls, *, source_approval_id: str, coverage_rule: QuarantineCoverageRuleV1, normalization_policy_id: str, identity_lineage_policy_id: str, approval_policy_id: str, approved_at: datetime):
        body = {"schema_version": "ApprovalWithCoverageRulesV1", "source_approval_id": source_approval_id, "coverage_rule_id": coverage_rule.rule_id, "minimum_coverage_start": coverage_rule.minimum_coverage_start, "quarantine_id": coverage_rule.quarantine_id, "quarantine_effective_interval": (coverage_rule.effective_from, coverage_rule.effective_to), "normalization_policy_id": normalization_policy_id, "identity_lineage_policy_id": identity_lineage_policy_id, "approval_policy_id": approval_policy_id, "approved_at": approved_at}
        digest = content_hash(body)
        return cls(artifact_id=digest, content_hash=digest, **{key: value for key, value in body.items() if key != "schema_version"})


@dataclass(frozen=True, slots=True)
class CombinedUpstreamGateV1:
    gate_id: str
    trade_calendar_approval_id: str
    security_master_approval_id: str
    daily_bar_entry_unlocked: bool
    evaluated_at: datetime
    content_hash: str

    @classmethod
    def evaluate(cls, *, trade_calendar_approval_id: str, trade_calendar_decision: str, security_master_approval_id: str, security_master_decision: str, revoked_approval_ids: Sequence[str], evaluated_at: datetime):
        valid = {"APPROVED", "APPROVED_WITH_RULES"}
        revoked = set(revoked_approval_ids)
        unlocked = trade_calendar_decision in valid and security_master_decision in valid and trade_calendar_approval_id not in revoked and security_master_approval_id not in revoked
        body = {"schema_version": "CombinedUpstreamGateV1", "trade_calendar_approval_id": trade_calendar_approval_id, "security_master_approval_id": security_master_approval_id, "daily_bar_entry_unlocked": unlocked, "evaluated_at": evaluated_at}
        digest = content_hash(body)
        return cls(gate_id=digest, content_hash=digest, **{key: value for key, value in body.items() if key != "schema_version"})
