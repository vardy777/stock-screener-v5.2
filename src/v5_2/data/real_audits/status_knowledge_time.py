from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from v5_2.data.identity import content_hash
from v5_2.data.real_audits.status_availability import StatusAvailabilityPolicyV2


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
        if status_semantic == "ACTUAL_FIRST_TRADABLE_SESSION" and "planned listing" in independent_observation.lower():
            raise ValueError("planned listing is not an actual tradable listing")
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
