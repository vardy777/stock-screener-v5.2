from __future__ import annotations

from datetime import date, datetime

from v5_2.data.corporate_action_facts import ActionType, CorporateActionFactV1


class NotResearchSafeError(RuntimeError):
    """The requested corporate-action answer is not proven research-safe."""


class CorporateActionRepository:
    def __init__(
        self, *, facts, supported_action_types, validated_coverage,
        materialized_coverage, quarantined_security_periods,
        approval_valid: bool, manifest_valid: bool,
    ):
        self._facts = tuple(facts)
        self._supported = frozenset(ActionType(value) for value in supported_action_types)
        self._validated = tuple(validated_coverage)
        self._materialized = tuple(materialized_coverage)
        self._quarantines = tuple(quarantined_security_periods)
        self._approval_valid = approval_valid
        self._manifest_valid = manifest_valid

    @staticmethod
    def _covers(intervals, kind, start, end):
        return any(ActionType(item_kind) is kind and item_start <= start and end <= item_end
                   for item_kind, item_start, item_end in intervals)

    def query(
        self, security_identity: str, start: date, end: date,
        action_type: ActionType, as_of: datetime,
    ) -> tuple[CorporateActionFactV1, ...]:
        kind = ActionType(action_type)
        if as_of.tzinfo is None or as_of.utcoffset() is None or end < start:
            raise NotResearchSafeError("NOT_RESEARCH_SAFE: invalid query")
        if not self._approval_valid or not self._manifest_valid:
            raise NotResearchSafeError("NOT_RESEARCH_SAFE: invalid approval lineage")
        if kind not in self._supported:
            raise NotResearchSafeError("NOT_RESEARCH_SAFE: unsupported action type")
        if not self._covers(self._validated, kind, start, end) or not self._covers(self._materialized, kind, start, end):
            raise NotResearchSafeError("NOT_RESEARCH_SAFE: uncovered interval")
        if any(identity == security_identity and not (end < q_start or q_end < start)
               for identity, q_start, q_end in self._quarantines):
            raise NotResearchSafeError("NOT_RESEARCH_SAFE: quarantined security-period")
        relevant = [fact for fact in self._facts if fact.verify()
                    and fact.security_identity == security_identity and fact.action_type is kind
                    and start <= (fact.effective_date or fact.ex_date) <= end and fact.available_at <= as_of]
        if any(not fact.verify() for fact in self._facts):
            raise NotResearchSafeError("NOT_RESEARCH_SAFE: tampered fact")
        by_id = {fact.source_fact_id: fact for fact in relevant}
        superseded = {fact.supersedes_source_fact_id for fact in relevant if fact.supersedes_source_fact_id}
        latest = tuple(sorted((fact for source_id, fact in by_id.items() if source_id not in superseded and not fact.is_cancelled),
                              key=lambda fact: (fact.effective_date or fact.ex_date, fact.fact_id)))
        return latest
