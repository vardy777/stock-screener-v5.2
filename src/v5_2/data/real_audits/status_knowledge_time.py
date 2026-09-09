from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from v5_2.data.identity import content_hash
from v5_2.data.real_audits.status_availability import StatusAvailabilityPolicyV2


REQUIRED_STATUS_SEMANTICS = (
    "ACTIVE_ORDINARY_STATUS", "ACTUAL_FIRST_TRADABLE_SESSION", "DELISTING",
    "ST_ENTER", "ST_EXIT", "FULL_DAY_SUSPENSION", "RESUMPTION", "IDENTITY_TRANSITION",
)


@dataclass(frozen=True, slots=True)
class StatusPITKnowledgeTimeEvidenceV1:
    policy_version: str
    historical_cutoff: str
    covered_semantics: tuple[str, ...]
    semantic_rules: tuple[tuple[str, str, str], ...]
    supporting_evidence_ids: tuple[str, ...]
    safe_session_rules: tuple[str, ...]
    contract_id: str
    inventory_id: str
    final_cross_source_evidence_id: str
    source_version_identity: str
    complete: bool
    content_hash: str

    @classmethod
    def create(cls, *, policy_version, historical_cutoff, semantic_rules,
               supporting_evidence_ids, safe_session_rules, contract_id, inventory_id,
               final_cross_source_evidence_id, source_version_identity):
        rules = tuple(sorted(tuple(item) for item in semantic_rules))
        covered = tuple(sorted({item[0] for item in rules}))
        supporting = tuple(sorted(set(supporting_evidence_ids)))
        safe_rules = tuple(sorted(set(safe_session_rules)))
        complete = (set(covered) == set(REQUIRED_STATUS_SEMANTICS)
                    and len(rules) == len(REQUIRED_STATUS_SEMANTICS)
                    and all(len(item) == 3 and all(str(value).strip() for value in item) for item in rules)
                    and bool(supporting) and bool(safe_rules)
                    and final_cross_source_evidence_id in supporting)
        body = {"schema_version": "StatusPITKnowledgeTimeEvidenceV1",
                "policy_version": policy_version, "historical_cutoff": historical_cutoff,
                "covered_semantics": covered, "semantic_rules": rules,
                "supporting_evidence_ids": supporting, "safe_session_rules": safe_rules,
                "contract_id": contract_id, "inventory_id": inventory_id,
                "final_cross_source_evidence_id": final_cross_source_evidence_id,
                "source_version_identity": source_version_identity, "complete": complete}
        return cls(**{key: value for key, value in body.items() if key != "schema_version"},
                   content_hash=content_hash(body))

    def verify(self) -> bool:
        body = {"schema_version": "StatusPITKnowledgeTimeEvidenceV1",
                "policy_version": self.policy_version, "historical_cutoff": self.historical_cutoff,
                "covered_semantics": self.covered_semantics, "semantic_rules": self.semantic_rules,
                "supporting_evidence_ids": self.supporting_evidence_ids,
                "safe_session_rules": self.safe_session_rules, "contract_id": self.contract_id,
                "inventory_id": self.inventory_id,
                "final_cross_source_evidence_id": self.final_cross_source_evidence_id,
                "source_version_identity": self.source_version_identity, "complete": self.complete}
        return self.content_hash == content_hash(body)


@dataclass(frozen=True, slots=True)
class StatusKnowledgeTimeObservationV1:
    event_id: str
    sample_entry_id: str
    security_identity: str
    status_semantic: str
    effective_session: date
    provider_observation: str
    independent_observation: str
    independent_source_id: str
    source_reference: str
    source_document_hash: str
    publication_date: date | None
    publication_timestamp: datetime | None
    availability_basis: str
    derived_available_at: datetime
    research_cutoff: datetime
    usable_at_D_cutoff: bool
    semantic_mapping_version: str
    input_artifact_ids: tuple[str, ...]
    content_hash: str

    @classmethod
    def create(cls, *, event_id, sample_entry_id, security_identity, status_semantic, effective_session,
               provider_observation, independent_observation, independent_source_id, source_reference,
               source_document_hash, publication_date, publication_timestamp, availability_basis,
               approved_sessions, semantic_mapping_version, input_artifact_ids):
        if not all(str(value).strip() for value in (
                independent_observation, independent_source_id, source_reference, source_document_hash)):
            raise ValueError("independent evidence is incomplete")
        if status_semantic == "ACTUAL_FIRST_TRADABLE_SESSION" and "planned listing" in independent_observation.lower():
            raise ValueError("planned listing is not an actual tradable listing")
        if status_semantic == "ST_EXIT" and provider_observation.strip().upper().startswith(("ST", "*ST", "SST", "S*ST")):
            raise ValueError("ST exit cannot be asserted while the observed state is still risk-warning")
        if (status_semantic == "IDENTITY_TRANSITION"
                and "retrospective provider" in independent_observation.lower()):
            raise ValueError("identity transition requires the official effective identity chain")
        factories = {
            "PUBLICATION_TIMESTAMP_BASED": StatusAvailabilityPolicyV2.publication_timestamp,
            "MARKET_OBSERVABLE_BY_CLOSE": StatusAvailabilityPolicyV2.market_observable_by_close,
            "CONSERVATIVE_AFTER_CLOSE": StatusAvailabilityPolicyV2.conservative_after_close,
            "NEXT_SESSION_SAFE": StatusAvailabilityPolicyV2.next_session_safe,
        }
        if availability_basis not in factories:
            raise ValueError("unsupported availability basis")
        policy = factories[availability_basis](status_semantic)
        available = policy.derive(event_date=effective_session, published_at=publication_timestamp,
                                  approved_sessions=approved_sessions)
        zone = timezone(timedelta(hours=8), "Asia/Shanghai")
        cutoff = datetime.combine(effective_session, time(16, 30), zone)
        inputs = tuple(sorted(set(input_artifact_ids)))
        body = {"schema_version": "StatusKnowledgeTimeObservationV1", "event_id": event_id,
                "sample_entry_id": sample_entry_id, "security_identity": security_identity,
                "status_semantic": status_semantic, "effective_session": effective_session,
                "provider_observation": provider_observation, "independent_observation": independent_observation,
                "independent_source_id": independent_source_id, "source_reference": source_reference,
                "source_document_hash": source_document_hash, "publication_date": publication_date,
                "publication_timestamp": publication_timestamp, "availability_basis": availability_basis,
                "derived_available_at": available, "research_cutoff": cutoff,
                "usable_at_D_cutoff": available <= cutoff, "semantic_mapping_version": semantic_mapping_version,
                "input_artifact_ids": inputs}
        values = {key: value for key, value in body.items() if key != "schema_version"}
        return cls(**values, content_hash=content_hash(body))
