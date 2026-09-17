from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
import re
from v5_2.data.identity import content_hash


HEX64 = re.compile(r"^[0-9a-f]{64}$")
CORE_LABELS = (
    "return_1d", "return_3d", "return_5d",
    "max_favorable_excursion_5d", "max_adverse_excursion_5d",
    "hit_3pct_before_-2pct", "hit_5pct_before_-3pct",
)
REQUIRED_LABEL_DOMAINS = (
    "trade_calendar", "security_master", "daily_bar",
    "daily_security_status", "corporate_action",
)


class LabelState(StrEnum):
    LABEL_AVAILABLE = "LABEL_AVAILABLE"
    LABEL_PENDING = "LABEL_PENDING"
    NOT_LABEL_SAFE = "NOT_LABEL_SAFE"


class LabelReasonCode(StrEnum):
    HORIZON_NOT_COMPLETED = "HORIZON_NOT_COMPLETED"
    ANCHOR_NOT_RESEARCH_ELIGIBLE = "ANCHOR_NOT_RESEARCH_ELIGIBLE"
    ANCHOR_BAR_MISSING = "ANCHOR_BAR_MISSING"
    EXPECTED_BAR_MISSING = "EXPECTED_BAR_MISSING"
    STATUS_UNRESOLVED = "STATUS_UNRESOLVED"
    IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"
    DELISTING_IN_HORIZON = "DELISTING_IN_HORIZON"
    UNSUPPORTED_CORPORATE_ACTION = "UNSUPPORTED_CORPORATE_ACTION"
    CORPORATE_ACTION_COVERAGE_GAP = "CORPORATE_ACTION_COVERAGE_GAP"
    CORPORATE_ACTION_QUARANTINE = "CORPORATE_ACTION_QUARANTINE"
    CORPORATE_ACTION_REVISION_INVALID = "CORPORATE_ACTION_REVISION_INVALID"
    BARRIER_PATH_AMBIGUOUS = "BARRIER_PATH_AMBIGUOUS"
    INPUT_LINEAGE_INVALID = "INPUT_LINEAGE_INVALID"


class BarrierOutcomeV1(StrEnum):
    UPPER_FIRST = "UPPER_FIRST"
    LOWER_FIRST = "LOWER_FIRST"
    NEITHER = "NEITHER"


class ProvenancePath(StrEnum):
    HISTORICAL = "HISTORICAL"
    CONTEMPORANEOUS = "CONTEMPORANEOUS"


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _id(value: str, name: str) -> None:
    if not HEX64.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase 64-hex immutable ID")


def _hash_body(schema: str, values: dict[str, object]) -> str:
    def normalize(value: object) -> object:
        if is_dataclass(value) and not isinstance(value, type):
            return {field.name: normalize(getattr(value, field.name)) for field in fields(value)}
        if isinstance(value, Decimal):
            return format(value, "f")
        if isinstance(value, tuple):
            return tuple(normalize(item) for item in value)
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        return value
    return content_hash({"schema_version": schema, **normalize(values)})


@dataclass(frozen=True, slots=True)
class LabelContractV1:
    contract_version: str = "v5.2-label-contract-v1"
    horizons: tuple[int, ...] = (1, 3, 5)
    quantization: Decimal = Decimal("0.00000001")
    required_domains: tuple[str, ...] = REQUIRED_LABEL_DOMAINS
    supported_action_types: tuple[str, ...] = ("CASH_DIVIDEND", "BONUS_SHARE")


@dataclass(frozen=True, slots=True)
class AnchorKnowledgeBoundary:
    anchor_session: date
    anchor_cutoff: datetime
    eligibility_evidence_id: str
    research_eligible: bool
    content_hash: str

    @classmethod
    def create(cls, session: date, cutoff: datetime, evidence_id: str, eligible: bool):
        _aware(cutoff, "anchor_cutoff"); _id(evidence_id, "eligibility_evidence_id")
        body = {"anchor_session": session, "anchor_cutoff": cutoff, "eligibility_evidence_id": evidence_id, "research_eligible": eligible}
        return cls(session, cutoff, evidence_id, eligible, _hash_body(cls.__name__, body))

    def verify(self) -> bool:
        body = {"anchor_session": self.anchor_session, "anchor_cutoff": self.anchor_cutoff, "eligibility_evidence_id": self.eligibility_evidence_id, "research_eligible": self.research_eligible}
        return self.content_hash == _hash_body(type(self).__name__, body)


@dataclass(frozen=True, slots=True)
class LabelReferencePrice:
    session: date
    price: Decimal
    price_basis: str
    daily_bar_fact_id: str
    available_at: datetime
    content_hash: str

    @classmethod
    def create(cls, session: date, price: Decimal, fact_id: str, available_at: datetime):
        if not isinstance(price, Decimal) or price <= 0: raise ValueError("reference price must be positive Decimal")
        _id(fact_id, "daily_bar_fact_id"); _aware(available_at, "available_at")
        body = {"session": session, "price": price, "price_basis": "UNADJUSTED_RAW", "daily_bar_fact_id": fact_id, "available_at": available_at}
        return cls(session, price, "UNADJUSTED_RAW", fact_id, available_at, _hash_body(cls.__name__, body))

    def verify(self) -> bool:
        body = {"session": self.session, "price": self.price, "price_basis": self.price_basis, "daily_bar_fact_id": self.daily_bar_fact_id, "available_at": self.available_at}
        return self.content_hash == _hash_body(type(self).__name__, body)


@dataclass(frozen=True, slots=True)
class DomainLineageV1:
    domain: str
    approval_id: str
    manifest_id: str
    fact_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    content_hash: str

    @classmethod
    def create(cls, *, domain: str, approval_id: str, manifest_id: str,
               fact_ids: tuple[str, ...], evidence_ids: tuple[str, ...] = ()):
        if domain not in REQUIRED_LABEL_DOMAINS: raise ValueError("unsupported label domain")
        _id(approval_id, "approval_id"); _id(manifest_id, "manifest_id")
        if len(fact_ids) != len(set(fact_ids)): raise ValueError("duplicate fact ID")
        if len(evidence_ids) != len(set(evidence_ids)): raise ValueError("duplicate evidence ID")
        for value in fact_ids: _id(value, "fact_id")
        for value in evidence_ids: _id(value, "evidence_id")
        if not fact_ids and not evidence_ids: raise ValueError("domain requires facts or evidence")
        body = {"domain": domain, "approval_id": approval_id, "manifest_id": manifest_id, "fact_ids": fact_ids, "evidence_ids": evidence_ids}
        return cls(domain, approval_id, manifest_id, fact_ids, evidence_ids, _hash_body(cls.__name__, body))

    def verify(self) -> bool:
        body = {"domain": self.domain, "approval_id": self.approval_id, "manifest_id": self.manifest_id, "fact_ids": self.fact_ids, "evidence_ids": self.evidence_ids}
        return self.domain in REQUIRED_LABEL_DOMAINS and self.content_hash == _hash_body(type(self).__name__, body)


@dataclass(frozen=True, slots=True)
class LabelValueV1:
    label_name: str
    state: LabelState
    value: Decimal | bool | None
    reason_code: LabelReasonCode | None
    horizon_end_session: date | None
    observed_at: datetime | None
    input_fact_ids: tuple[str, ...]
    contract_version: str
    content_hash: str

    @classmethod
    def create(cls, label_name: str, state: LabelState, value: Decimal | bool | None,
               reason_code: LabelReasonCode | None = None, *, horizon_end_session: date | None = None,
               observed_at: datetime | None = None, input_fact_ids: tuple[str, ...] = ()):
        if label_name not in CORE_LABELS: raise ValueError("unknown canonical label")
        state = LabelState(state)
        is_barrier = label_name.startswith("hit_")
        if state is LabelState.LABEL_AVAILABLE:
            if reason_code is not None or value is None: raise ValueError("available label requires value only")
            if is_barrier and not isinstance(value, bool): raise ValueError("barrier value must be bool")
            if not is_barrier and (not isinstance(value, Decimal) or isinstance(value, bool)): raise ValueError("numeric label must be Decimal")
        else:
            if value is not None or reason_code is None: raise ValueError("unavailable label requires reason and no value")
            if state is LabelState.LABEL_PENDING and reason_code is not LabelReasonCode.HORIZON_NOT_COMPLETED: raise ValueError("pending reason is fixed")
        if observed_at is not None: _aware(observed_at, "observed_at")
        body = {"label_name": label_name, "state": state, "value": value, "reason_code": reason_code,
                "horizon_end_session": horizon_end_session, "observed_at": observed_at,
                "input_fact_ids": input_fact_ids, "contract_version": LabelContractV1().contract_version}
        return cls(**body, content_hash=_hash_body(cls.__name__, body))

    def verify(self) -> bool:
        body = {name: getattr(self, name) for name in ("label_name", "state", "value", "reason_code", "horizon_end_session", "observed_at", "input_fact_ids", "contract_version")}
        return self.content_hash == _hash_body(type(self).__name__, body)


@dataclass(frozen=True, slots=True)
class LabelInputBundleV1:
    canonical_security_identity: str
    anchor_session: date
    anchor_boundary: AnchorKnowledgeBoundary
    reference_price: LabelReferencePrice | None
    provenance_path: ProvenancePath
    domain_lineage: tuple[DomainLineageV1, ...]
    anchor_snapshot_id: str | None
    outcome_snapshot_id: str | None
    approved_exchange_sessions: tuple[date, ...]
    latest_completed_session: date
    future_bars: tuple[object, ...]
    future_statuses: tuple[object, ...]
    corporate_actions: tuple[object, ...]
    action_coverage: object | None
    dated_identity_map: tuple[tuple[date, str, str], ...]
    delisting_session: date | None
    content_hash: str = ""

    @classmethod
    def create(cls, *, canonical_security_identity: str, anchor_session: date,
               anchor_boundary: AnchorKnowledgeBoundary, reference_price: LabelReferencePrice | None,
               provenance_path: ProvenancePath, domain_lineage: tuple[DomainLineageV1, ...],
               anchor_snapshot_id: str | None = None, outcome_snapshot_id: str | None = None,
               approved_exchange_sessions: tuple[date, ...] = (), latest_completed_session: date | None = None,
               future_bars: tuple[object, ...] = (), future_statuses: tuple[object, ...] = (),
               corporate_actions: tuple[object, ...] = (), action_coverage: object | None = None,
               dated_identity_map: tuple[tuple[date, str, str], ...] = (), delisting_session: date | None = None):
        provenance_path = ProvenancePath(provenance_path)
        if anchor_boundary.anchor_session != anchor_session or (reference_price is not None and reference_price.session != anchor_session): raise ValueError("anchor session mismatch")
        if tuple(item.domain for item in domain_lineage) != REQUIRED_LABEL_DOMAINS: raise ValueError("exact ordered five-domain lineage required")
        if not all(item.verify() for item in domain_lineage): raise ValueError("invalid domain lineage")
        if provenance_path is ProvenancePath.CONTEMPORANEOUS and (anchor_snapshot_id is None or outcome_snapshot_id is None): raise ValueError("contemporaneous snapshots required")
        for name, value in (("anchor_snapshot_id", anchor_snapshot_id), ("outcome_snapshot_id", outcome_snapshot_id)):
            if value is not None: _id(value, name)
        body = {"canonical_security_identity": canonical_security_identity, "anchor_session": anchor_session,
                "anchor_boundary": anchor_boundary, "reference_price": reference_price,
                "provenance_path": provenance_path, "domain_lineage": domain_lineage,
                "anchor_snapshot_id": anchor_snapshot_id, "outcome_snapshot_id": outcome_snapshot_id,
                "approved_exchange_sessions": approved_exchange_sessions,
                "latest_completed_session": latest_completed_session or anchor_session,
                "future_bars": future_bars, "future_statuses": future_statuses,
                "corporate_actions": corporate_actions, "action_coverage": action_coverage,
                "dated_identity_map": dated_identity_map, "delisting_session": delisting_session}
        return cls(**body, content_hash=_hash_body(cls.__name__, body))

    def verify(self) -> bool:
        body = {name: getattr(self, name) for name in ("canonical_security_identity", "anchor_session", "anchor_boundary", "reference_price", "provenance_path", "domain_lineage", "anchor_snapshot_id", "outcome_snapshot_id", "approved_exchange_sessions", "latest_completed_session", "future_bars", "future_statuses", "corporate_actions", "action_coverage", "dated_identity_map", "delisting_session")}
        reference_valid = self.reference_price is None or self.reference_price.verify()
        return self.anchor_boundary.verify() and reference_valid and all(x.verify() for x in self.domain_lineage) and self.content_hash == _hash_body(type(self).__name__, body)


@dataclass(frozen=True, slots=True)
class LabelResultV1:
    canonical_security_identity: str
    anchor_session: date
    values: tuple[LabelValueV1, ...]
    bundle_hash: str
    barrier_evidence: tuple[object, ...]
    content_hash: str

    @classmethod
    def create(cls, identity: str, session: date, values: tuple[LabelValueV1, ...], bundle_hash: str, barrier_evidence: tuple[object, ...] = ()):
        body = {"canonical_security_identity": identity, "anchor_session": session, "values": values, "bundle_hash": bundle_hash, "barrier_evidence": barrier_evidence}
        return cls(identity, session, values, bundle_hash, barrier_evidence, _hash_body(cls.__name__, body))

    def verify(self) -> bool:
        body = {"canonical_security_identity": self.canonical_security_identity, "anchor_session": self.anchor_session, "values": self.values, "bundle_hash": self.bundle_hash, "barrier_evidence": self.barrier_evidence}
        return all(x.verify() for x in self.values) and self.content_hash == _hash_body(type(self).__name__, body)
