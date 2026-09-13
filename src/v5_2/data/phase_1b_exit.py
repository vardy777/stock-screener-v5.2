from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, fields
from datetime import date, datetime, timedelta, timezone
from typing import Mapping, Sequence

from v5_2.data.identity import content_hash


SHANGHAI = timezone(timedelta(hours=8), name="Asia/Shanghai")
BASE_DATASETS = ("trade_calendar", "security_master", "daily_bar", "daily_security_status")


class ExitContractError(ValueError):
    """An Exit input cannot establish a causal research context."""


@dataclass(frozen=True, slots=True)
class HistoricalResearchCutoffContractV1:
    session: date
    cutoff: datetime
    timezone_name: str
    calendar_approval_id: str
    contract_version: str
    contract_id: str
    content_hash: str

    @classmethod
    def create(cls, *, session: date, cutoff: datetime, timezone_name: str,
               calendar_approval_id: str, approved_open_sessions: Sequence[date]):
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise ExitContractError("cutoff must be timezone-aware")
        if timezone_name != "Asia/Shanghai" or cutoff.utcoffset() != timedelta(hours=8):
            raise ExitContractError("cutoff must use Asia/Shanghai UTC+8")
        if session not in set(approved_open_sessions):
            raise ExitContractError("session is not an approved open session")
        if cutoff.astimezone(SHANGHAI).date() != session:
            raise ExitContractError("cutoff does not belong to declared research session context")
        if not calendar_approval_id:
            raise ExitContractError("calendar approval lineage is required")
        body = {"schema_version": "HistoricalResearchCutoffContractV1", "session": session,
                "cutoff": cutoff, "timezone_name": timezone_name,
                "calendar_approval_id": calendar_approval_id,
                "contract_version": "historical-research-cutoff-v1"}
        digest = content_hash(body)
        return cls(session, cutoff, timezone_name, calendar_approval_id,
                   "historical-research-cutoff-v1", digest, digest)

    def verify(self) -> bool:
        body = {"schema_version": "HistoricalResearchCutoffContractV1", "session": self.session,
                "cutoff": self.cutoff, "timezone_name": self.timezone_name,
                "calendar_approval_id": self.calendar_approval_id,
                "contract_version": self.contract_version}
        return self.contract_id == self.content_hash == content_hash(body)


@dataclass(frozen=True, slots=True)
class Phase1BCoverageEntryV1:
    dataset: str
    coverage_start: date
    coverage_end: date
    approval_id: str
    manifest_id: str
    completeness_mode: str
    approved_scope: tuple[str, ...]
    unsupported_scope: tuple[str, ...]
    known_gaps: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Phase1BCoverageMatrixV1:
    entries: tuple[Phase1BCoverageEntryV1, ...]
    coverage_matrix_id: str
    content_hash: str

    @classmethod
    def create(cls, values: Sequence[Mapping[str, object]]):
        entries = tuple(sorted((Phase1BCoverageEntryV1(
            dataset=str(value["dataset"]), coverage_start=value["coverage_start"],
            coverage_end=value["coverage_end"], approval_id=str(value["approval_id"]),
            manifest_id=str(value["manifest_id"]), completeness_mode=str(value["completeness_mode"]),
            approved_scope=tuple(sorted(set(value.get("approved_scope", ())))),
            unsupported_scope=tuple(sorted(set(value.get("unsupported_scope", ())))),
            known_gaps=tuple(sorted(set(value.get("known_gaps", ())))),
        ) for value in values), key=lambda item: item.dataset))
        if len(entries) != 6 or {item.dataset for item in entries} != {
            "trade_calendar", "security_master", "daily_bar", "daily_security_status",
            "corporate_action", "financial_disclosure"}:
            raise ExitContractError("coverage matrix requires exactly six Phase 1B datasets")
        if any(item.coverage_end < item.coverage_start or not item.approval_id or not item.manifest_id for item in entries):
            raise ExitContractError("coverage matrix entry is invalid")
        body = {"schema_version": "Phase1BCoverageMatrixV1", "entries": entries}
        digest = content_hash(body)
        return cls(entries, digest, digest)

    def entry(self, dataset: str) -> Phase1BCoverageEntryV1:
        try:
            return next(item for item in self.entries if item.dataset == dataset)
        except StopIteration as error:
            raise ExitContractError(f"missing coverage entry: {dataset}") from error

    def covers(self, dataset: str, session: date) -> bool:
        item = self.entry(dataset)
        return item.coverage_start <= session <= item.coverage_end

    def verify(self) -> bool:
        return self.coverage_matrix_id == self.content_hash == content_hash(
            {"schema_version": "Phase1BCoverageMatrixV1", "entries": self.entries})


@dataclass(frozen=True, slots=True)
class HistoricalResearchSessionV1:
    session: date
    cutoff: datetime
    session_valid: bool
    base_universe_count: int
    base_eligible_count: int
    blocked_security_count: int
    security_dataset_eligibility: tuple[tuple[str, str, str, str], ...]
    reason_histogram: tuple[tuple[str, int], ...]
    dataset_approval_ids: tuple[str, ...]
    dataset_manifest_ids: tuple[str, ...]
    coverage_matrix_hash: str
    session_result_hash: str

    @classmethod
    def evaluate(cls, *, cutoff_contract: HistoricalResearchCutoffContractV1,
                 coverage_matrix: Phase1BCoverageMatrixV1, base_universe: Sequence[str],
                 lineage_valid: bool, base_availability: Mapping[str, Sequence[str]],
                 fatal_reason: str = "MANIFEST_INVALID",
                 requires_corporate_action_safe: bool = False,
                 corporate_action_unsafe: Mapping[str, str] | None = None,
                 required_financial_metrics: Sequence[str] = (),
                 financial_unsafe: Mapping[tuple[str, str], str] | None = None,
                 base_ineligible: Mapping[str, str] | None = None):
        universe = tuple(sorted(set(base_universe)))
        approval_ids = tuple(item.approval_id for item in coverage_matrix.entries)
        manifest_ids = tuple(item.manifest_id for item in coverage_matrix.entries)
        fatal = None
        if not cutoff_contract.verify() or not coverage_matrix.verify():
            fatal = "MANIFEST_INVALID"
        elif cutoff_contract.calendar_approval_id != coverage_matrix.entry("trade_calendar").approval_id:
            fatal = "APPROVAL_INVALID"
        elif not lineage_valid:
            fatal = fatal_reason
        elif any(not coverage_matrix.covers(dataset, cutoff_contract.session) for dataset in BASE_DATASETS):
            fatal = "OUTSIDE_APPROVED_COVERAGE"
        if fatal:
            return cls._build(cutoff_contract, False, universe, (), (), Counter({fatal: 1}),
                              approval_ids, manifest_ids, coverage_matrix.content_hash)

        rows: list[tuple[str, str, str, str]] = []
        base_eligible = set(universe)
        base_reason = {"security_master": "IDENTITY_UNRESOLVED", "daily_bar": "DAILY_BAR_UNAVAILABLE",
                       "daily_security_status": "STATUS_UNAVAILABLE"}
        for dataset, reason in base_reason.items():
            available = set(base_availability.get(dataset, ()))
            for security in universe:
                if security not in available:
                    rows.append((security, dataset, "NOT_RESEARCH_SAFE", reason))
                    base_eligible.discard(security)
                else:
                    rows.append((security, dataset, "SAFE", ""))
        for security, reason in sorted((base_ineligible or {}).items()):
            if security in universe and security in set(base_availability.get("daily_security_status", ())):
                rows = [row for row in rows
                        if not (row[0] == security and row[1] == "daily_security_status")]
                rows.append((security, "daily_security_status", "NOT_RESEARCH_SAFE", reason))
                base_eligible.discard(security)
        ca_unsafe = corporate_action_unsafe or {}
        financial_failures = financial_unsafe or {}
        financial_scope = set(coverage_matrix.entry("financial_disclosure").approved_scope)
        for security in sorted(base_eligible):
            if requires_corporate_action_safe:
                reason = ca_unsafe.get(security, "")
                rows.append((security, "corporate_action", "NOT_RESEARCH_SAFE" if reason else "SAFE", reason))
            for metric in sorted(set(required_financial_metrics)):
                reason = ("FINANCIAL_METRIC_UNSUPPORTED" if metric not in financial_scope
                          else financial_failures.get((security, metric), ""))
                rows.append((security, f"financial:{metric}", "NOT_RESEARCH_SAFE" if reason else "SAFE", reason))
        reasons = Counter(row[3] for row in rows if row[3])
        blocked = {row[0] for row in rows if row[2] == "NOT_RESEARCH_SAFE"}
        return cls._build(cutoff_contract, True, universe, tuple(sorted(base_eligible)),
                          tuple(sorted(rows)), reasons, approval_ids, manifest_ids,
                          coverage_matrix.content_hash, blocked_count=len(blocked))

    @classmethod
    def _build(cls, cutoff, valid, universe, eligible, rows, reasons, approvals, manifests,
               matrix_hash, blocked_count=None):
        values = {"session": cutoff.session, "cutoff": cutoff.cutoff, "session_valid": valid,
            "base_universe_count": len(universe), "base_eligible_count": len(eligible),
            "blocked_security_count": (len(universe) if not valid else int(blocked_count or 0)),
            "security_dataset_eligibility": tuple(rows),
            "reason_histogram": tuple(sorted(reasons.items())),
            "dataset_approval_ids": tuple(approvals), "dataset_manifest_ids": tuple(manifests),
            "coverage_matrix_hash": matrix_hash}
        digest = content_hash({"schema_version": "HistoricalResearchSessionV1", **values})
        return cls(**values, session_result_hash=digest)


@dataclass(frozen=True, slots=True)
class Phase1BExitAcceptanceV1:
    repository_head: str
    cutoff_contract_id: str
    coverage_matrix_id: str
    dataset_approval_ids: tuple[str, ...]
    dataset_manifest_ids: tuple[str, ...]
    dry_run_ids: tuple[str, ...]
    chaos_test_evidence_id: str
    deterministic_replay_id: str
    gate_results: tuple[tuple[str, str], ...]
    known_limitations: tuple[str, ...]
    content_hash: str

    @classmethod
    def create(cls, **values):
        canonical = dict(values)
        for name in ("dataset_approval_ids", "dataset_manifest_ids", "dry_run_ids", "known_limitations"):
            canonical[name] = tuple(sorted(set(canonical[name])))
        canonical["gate_results"] = tuple(sorted(canonical["gate_results"]))
        digest = content_hash({"schema_version": "Phase1BExitAcceptanceV1", **canonical})
        return cls(**canonical, content_hash=digest)

    def verify(self) -> bool:
        body = {field.name: getattr(self, field.name) for field in fields(self) if field.name != "content_hash"}
        return self.content_hash == content_hash({"schema_version": "Phase1BExitAcceptanceV1", **body})
