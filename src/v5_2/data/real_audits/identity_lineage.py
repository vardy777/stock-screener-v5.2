from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

from v5_2.data.identity import content_hash


class IdentityLineageError(RuntimeError):
    """An effective-dated identity graph is ambiguous or unsupported."""


@dataclass(frozen=True, slots=True)
class HistoricalSecurityIdentityQuestionV1:
    question_id: str
    provider_identity: str
    provider_listing_date: date
    questions: tuple[str, ...]
    input_artifact_ids: tuple[str, ...]
    policy_version: str
    content_hash: str

    @classmethod
    def create(cls, *, provider_identity: str, provider_listing_date: date, questions: Sequence[str], input_artifact_ids: Sequence[str], policy_version: str):
        body = {"schema_version": "HistoricalSecurityIdentityQuestionV1", "provider_identity": provider_identity, "provider_listing_date": provider_listing_date, "questions": tuple(sorted(set(questions))), "input_artifact_ids": tuple(sorted(set(input_artifact_ids))), "policy_version": policy_version}
        digest = content_hash(body)
        return cls(question_id=digest, content_hash=digest, **{k: v for k, v in body.items() if k != "schema_version"})


@dataclass(frozen=True, slots=True)
class IdentityIntervalV1:
    identity: str
    effective_from: date
    effective_to: date | None
    security_type: str
    board: str


@dataclass(frozen=True, slots=True)
class EffectiveDatedSecurityIdentityV1:
    graph_id: str
    provider_identity: str
    intervals: tuple[IdentityIntervalV1, ...]
    transition_event: str
    transition_effective_at: date
    evidence_ids: tuple[str, ...]
    policy_version: str
    content_hash: str

    @classmethod
    def create(cls, *, provider_identity: str, intervals: Sequence[IdentityIntervalV1], transition_event: str, transition_effective_at: date | None, evidence_ids: Sequence[str], policy_version: str):
        ordered = tuple(sorted(intervals, key=lambda value: value.effective_from))
        if transition_event == "UNKNOWN" or transition_effective_at is None or len(ordered) < 2 or len(set(evidence_ids)) < 2:
            raise IdentityLineageError("identity transition evidence is incomplete")
        for previous, current in zip(ordered, ordered[1:]):
            if previous.effective_to is None or previous.effective_to >= current.effective_from:
                raise IdentityLineageError("identity intervals overlap illegally")
        if ordered[-1].identity != provider_identity or ordered[-1].effective_from != transition_effective_at:
            raise IdentityLineageError("current identity transition boundary is inconsistent")
        body = {"schema_version": "EffectiveDatedSecurityIdentityV1", "provider_identity": provider_identity, "intervals": ordered, "transition_event": transition_event, "transition_effective_at": transition_effective_at, "evidence_ids": tuple(sorted(set(evidence_ids))), "policy_version": policy_version}
        digest = content_hash(body)
        return cls(graph_id=digest, content_hash=digest, **{k: v for k, v in body.items() if k != "schema_version"})
