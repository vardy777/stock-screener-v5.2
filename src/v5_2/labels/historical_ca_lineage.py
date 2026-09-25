"""Exact Phase 1 corporate-action facts plus explicit unsupported-event coverage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Mapping

from v5_2.data.corporate_action_facts import ActionType, CorporateActionFactV1, KnowledgeClass
from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.calculation import CorporateActionCoverageV1
from v5_2.labels.contracts import DomainLineageV1


APPROVAL_ID = "5e53080fd85dba5328cda9ed44c5dc5959e5bea965d8f5df12e07201deb8e974"
MANIFEST_ID = "5086896d0066baa928fe44c3469b2c1362feb2068db04acb7336b38c13bdbe2c"
BUNDLE_ID = "3e4a5604e555c036effe66fa5297cffcf374aa34dbd9a8b14eab873c165b6410"
AUDIT_ID = "8cf46a3dbaf6170cd64a1f2514f47ea87609200886fb2d8eebf60f888b11d28d"


def _verified(path: Path, schema: str, id_field: str, expected_id: str,
              *, stored_schema: bool) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, ValueError) as error:
        raise ValueError(f"exact CA {schema} missing or malformed") from error
    if not isinstance(value, dict) or canonical_json(value) != raw:
        raise ValueError(f"exact CA {schema} bytes changed")
    body = {key: item for key, item in value.items() if key not in {id_field, "content_hash", "manifest_hash"}}
    if stored_schema:
        if body.get("schema_version") != schema:
            raise ValueError(f"exact CA {schema} type mismatch")
    else:
        if "schema_version" in body:
            raise ValueError(f"exact CA {schema} stored type mismatch")
        body = {"schema_version": schema, **body}
    if value.get(id_field) != expected_id or content_hash(body) != expected_id:
        raise ValueError(f"exact CA {schema} content mismatch")
    if "content_hash" in value and value["content_hash"] != expected_id:
        raise ValueError(f"exact CA {schema} content hash mismatch")
    if "manifest_hash" in value and value["manifest_hash"] != expected_id:
        raise ValueError(f"exact CA {schema} manifest hash mismatch")
    return value


def _fact(value: dict[str, Any]) -> CorporateActionFactV1:
    decoded = dict(value)
    decoded["action_type"] = ActionType(decoded["action_type"])
    decoded["knowledge_class"] = KnowledgeClass(decoded["knowledge_class"])
    for key in ("published_at", "available_at"):
        decoded[key] = datetime.fromisoformat(decoded[key]) if decoded[key] else None
    for key in ("ex_date", "effective_date"):
        decoded[key] = date.fromisoformat(decoded[key]) if decoded[key] else None
    for key in ("cash_per_share", "share_ratio"):
        decoded[key] = Decimal(decoded[key]) if decoded[key] is not None else None
    fact = CorporateActionFactV1(**decoded)
    if not fact.verify():
        raise ValueError("approved CA fact content changed")
    return fact


@dataclass(frozen=True, slots=True)
class HistoricalCorporateActionLineageV1:
    facts: tuple[CorporateActionFactV1, ...]
    quarantines: tuple[dict[str, Any], ...]
    approved_intervals: tuple[tuple[str, date, date], ...]
    approval_id: str
    manifest_id: str
    bundle_id: str
    audit_id: str
    supported_action_types: tuple[str, ...]
    unsupported_action_types: tuple[str, ...]
    facts_by_identity: Mapping[str, tuple[CorporateActionFactV1, ...]]
    quarantines_by_identity: Mapping[str, tuple[dict[str, Any], ...]]

    @staticmethod
    def audit_path() -> Path:
        return Path(f"governance/materialization-audit-{AUDIT_ID}.json")

    @staticmethod
    def required_paths() -> tuple[Path, ...]:
        return (
            Path(f"approved/corporate-action-facts-{BUNDLE_ID}.json"),
            Path(f"governance/corporate_action-approval-{APPROVAL_ID}.json"),
            Path(f"governance/corporate-action-manifest-{MANIFEST_ID}.json"),
            HistoricalCorporateActionLineageV1.audit_path(),
        )

    @classmethod
    def load_exact(cls, root: Path, *, revoked_approval_ids: tuple[str, ...] = ()) -> "HistoricalCorporateActionLineageV1":
        bundle = _verified(root / cls.required_paths()[0], "ApprovedCorporateActionFactBundleV1",
                           "fact_bundle_id", BUNDLE_ID, stored_schema=True)
        approval = _verified(root / cls.required_paths()[1], "SourceApprovalArtifactV1",
                             "approval_id", APPROVAL_ID, stored_schema=False)
        manifest = _verified(root / cls.required_paths()[2], "DatasetManifestV1",
                             "dataset_id", MANIFEST_ID, stored_schema=False)
        audit = _verified(root / cls.audit_path(), "CorporateActionMaterializationAuditV1",
                          "audit_id", AUDIT_ID, stored_schema=True)
        if (APPROVAL_ID in revoked_approval_ids
                or approval.get("decision") != "APPROVED_WITH_RULES"
                or approval.get("dataset_kind") != "corporate_action"
                or manifest.get("approval_id") != APPROVAL_ID
                or manifest.get("dataset_kind") != "corporate_action"
                or manifest.get("pit_validation_status") != "PASS"
                or manifest.get("rule_compliance_status") != "PASS"
                or bundle.get("approval_id") != APPROVAL_ID
                or bundle.get("gate_id") != manifest.get("audit_policy_id")
                or tuple(manifest.get("supported_action_types", ())) != ("BONUS_SHARE", "CASH_DIVIDEND")
                or tuple(manifest.get("unsupported_action_types", ())) !=
                    ("RIGHTS_ISSUE", "SHARE_CONVERSION", "STOCK_SPLIT")
                or approval.get("rule_set", {}).get("unsupported_events") != "FAIL_CLOSED_QUARANTINE"
                or AUDIT_ID not in approval.get("evidence_ids", ())
                or audit.get("candidate_fact_count") != manifest.get("row_count")
                or audit.get("quarantine_count") != manifest.get("quarantined_count")
                or tuple(item["quarantine_id"] for item in audit.get("quarantines", ()))
                    != tuple(manifest.get("quarantined_identity_hashes", ()))):
            raise ValueError("approved CA facts, audit, and governance differ")
        facts = tuple(_fact(value) for value in bundle["facts"])
        if (len(facts) != manifest["row_count"]
                or tuple(item.fact_id for item in facts) != tuple(manifest["fact_content_hashes"])):
            raise ValueError("approved CA fact membership changed")
        intervals = tuple((kind, date.fromisoformat(start), date.fromisoformat(end))
                          for kind, start, end in manifest["materialized_coverage_by_action_type"])
        by_identity: dict[str, list[CorporateActionFactV1]] = {}
        for fact in facts:
            by_identity.setdefault(fact.security_identity, []).append(fact)
        quarantine_by_identity: dict[str, list[dict[str, Any]]] = {}
        for item in audit["quarantines"]:
            quarantine_by_identity.setdefault(item["security_identity"], []).append(item)
        return cls(facts, tuple(audit["quarantines"]), intervals,
                   APPROVAL_ID, MANIFEST_ID, BUNDLE_ID, AUDIT_ID,
                   tuple(manifest["supported_action_types"]),
                   tuple(manifest["unsupported_action_types"]),
                   {key: tuple(value) for key, value in by_identity.items()},
                   {key: tuple(value) for key, value in quarantine_by_identity.items()})

    @property
    def fact_count(self) -> int:
        return len(self.facts)

    @property
    def quarantine_count(self) -> int:
        return len(self.quarantines)

    @property
    def first_quarantine(self) -> dict[str, Any]:
        return self.quarantines[0]

    def window(self, identity: str, sessions: tuple[date, ...]) -> tuple[
            tuple[CorporateActionFactV1, ...], CorporateActionCoverageV1, DomainLineageV1]:
        if not sessions or sessions != tuple(sorted(set(sessions))):
            raise ValueError("CA window sessions must be canonical")
        wanted = set(sessions)
        facts = tuple(item for item in self.facts_by_identity.get(identity, ())
                      if (item.effective_date or item.ex_date) in wanted)
        quarantines = tuple(item for item in self.quarantines_by_identity.get(identity, ())
                            if date.fromisoformat(item["effective_date"].replace("-", "")) in wanted)
        covered = all(any(kind == action.value and start <= day <= end
                          for kind, start, end in self.approved_intervals)
                      for action in (ActionType.CASH_DIVIDEND, ActionType.BONUS_SHARE)
                      for day in sessions)
        coverage = CorporateActionCoverageV1(covered=covered, quarantined=bool(quarantines))
        lineage = DomainLineageV1.create(
            domain="corporate_action", approval_id=self.approval_id,
            manifest_id=self.manifest_id, fact_ids=tuple(item.fact_id for item in facts),
            evidence_ids=(self.bundle_id, self.audit_id,
                          *(item["quarantine_id"] for item in quarantines)),
        )
        return facts, coverage, lineage
