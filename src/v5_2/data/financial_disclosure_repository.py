from __future__ import annotations

from datetime import date, datetime

from v5_2.data.financial_disclosure_facts import FinancialDisclosureFactV1, StatementType


class NotResearchSafeError(RuntimeError):
    """The requested financial answer is not proven research-safe."""


class FinancialDisclosureRepository:
    def __init__(self, *, facts, supported_statement_types, supported_metrics,
                 validated_coverage, quarantined_keys, approval_valid: bool,
                 manifest_valid: bool):
        self._facts = tuple(facts)
        self._supported = frozenset(StatementType(value) for value in supported_statement_types)
        self._metrics = frozenset(supported_metrics)
        self._coverage = tuple(validated_coverage)
        self._quarantines = frozenset(quarantined_keys)
        self._approval_valid = approval_valid
        self._manifest_valid = manifest_valid

    def query(self, security: str, metric: str, period_end: date, cutoff: datetime) -> FinancialDisclosureFactV1:
        if cutoff.tzinfo is None or cutoff.utcoffset() is None or not self._approval_valid or not self._manifest_valid:
            raise NotResearchSafeError("NOT_RESEARCH_SAFE: invalid approval lineage or cutoff")
        if metric not in self._metrics or (security, metric, period_end) in self._quarantines:
            raise NotResearchSafeError("NOT_RESEARCH_SAFE: unsupported or quarantined key")
        if any(not fact.verify() for fact in self._facts):
            raise NotResearchSafeError("NOT_RESEARCH_SAFE: tampered fact")
        visible = [fact for fact in self._facts if fact.security_identity == security and fact.metric == metric
                   and fact.period_end == period_end and fact.available_at <= cutoff]
        if not visible: raise NotResearchSafeError("NOT_RESEARCH_SAFE: fact unavailable")
        statement = visible[0].statement_type
        if statement not in self._supported or not any(kind == statement and start <= period_end <= end for kind, start, end in self._coverage):
            raise NotResearchSafeError("NOT_RESEARCH_SAFE: uncovered statement")
        by_source = {fact.source_fact_id: fact for fact in visible}
        superseded = {fact.supersedes_source_fact_id for fact in visible if fact.supersedes_source_fact_id}
        latest = [fact for source_id, fact in by_source.items() if source_id not in superseded]
        if len(latest) != 1: raise NotResearchSafeError("NOT_RESEARCH_SAFE: ambiguous revision lineage")
        return latest[0]
