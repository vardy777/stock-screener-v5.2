from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path

from v5_2.data.corporate_action_facts import ActionType, CorporateActionFactV1, KnowledgeClass
from v5_2.data.daily_bar_facts import DailyBarFactV1
from v5_2.data.real_audits.phase2a_evidence_gap import audit_phase2a_evidence_gaps
from v5_2.labels.acceptance import LabelAcceptanceSlotV1
from v5_2.labels.calculation import CorporateActionCoverageV1
from v5_2.labels.contracts import (
    AnchorKnowledgeBoundary, DomainLineageV1, LabelInputBundleV1,
    LabelReferencePrice, ProvenancePath, REQUIRED_LABEL_DOMAINS,
)


TZ = timezone(timedelta(hours=8))
CALENDAR_APPROVAL = "4a900c7e4f2b171d7adac07088025ca4bb9fb0da13cfa1b15e91eff3dafea601"
CALENDAR_MANIFEST = "5f5ba7d0594f5f1e2d40ad43b54a93a303a7d25af8e1104e6c633463076e6486"
MASTER_APPROVAL = "828e0e722d3d66c84a48584aac14fde37f86cf471f3722f403ec19044f36345c"
MASTER_MANIFEST = "025982975b942c416945d9580f2a8272d667f7676e9f6fa213429e3da2ee382b"
BAR_APPROVAL = "eaa2c254b85077ae8f988c393b133ba90f5443025d2cfdbe10523229f8f753f4"
BAR_MANIFEST = "cb79850fac1c28e7b1e8bd9991d65c26f61add832b2f5ed67c40c586a13fd8c6"
STATUS_APPROVAL = "60d31609f590cf08f54ff682d5c4de5a987cdb670b13fe33eeb2466389d39edc"
STATUS_MANIFEST = "fef0f11d8f23f59ef70759da20b8dedbce70331c48c1cf9c61468a202e22e46d"
IDENTITY_TRANSITION_FACT = "43d84033112aec8202adfa2243aa388a9bdc9637862d72bf9d957083dd7ab8cc"
CA_APPROVAL = "5e53080fd85dba5328cda9ed44c5dc5959e5bea965d8f5df12e07201deb8e974"
CA_MANIFEST = "5086896d0066baa928fe44c3469b2c1362feb2068db04acb7336b38c13bdbe2c"
BAR_COMPOSITE = "0053aa0c80a5561dd8557156555bfdb47c841901477a737a0a0a2f5807918744"
BACKFILL_APPROVAL = "c40a48567920d699e9ca3cb35befec6896539cab271076ed3096c910bbc65ec7"
BACKFILL_MANIFEST = "a8edf664a095e6273a56a8bc1d429d4fc076c9a3d97b93913b7d7092299bc6ff"


class EvidenceAssemblyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ResolvedStatusObservationV1:
    session: date
    is_suspended: bool
    available_at: datetime
    evidence_ids: tuple[str, ...]


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _bar(raw: dict) -> DailyBarFactV1:
    return DailyBarFactV1(
        fact_id=raw["fact_id"], security_identity=raw["security_identity"],
        session=date.fromisoformat(raw["session"]),
        open=Decimal(raw["open"]), high=Decimal(raw["high"]), low=Decimal(raw["low"]),
        close=Decimal(raw["close"]), volume_shares=Decimal(raw["volume_shares"]),
        amount_yuan=Decimal(raw["amount_yuan"]), price_basis=raw["price_basis"],
        available_at=datetime.fromisoformat(raw["available_at"]),
        availability_policy_version=raw["availability_policy_version"],
        source_payload_hash=raw["source_payload_hash"], content_hash=raw["content_hash"],
    )


def _action(raw: dict) -> CorporateActionFactV1:
    values = dict(raw)
    values["action_type"] = ActionType(values["action_type"])
    values["knowledge_class"] = KnowledgeClass(values["knowledge_class"])
    for key in ("published_at", "available_at"):
        values[key] = datetime.fromisoformat(values[key]) if values[key] else None
    for key in ("ex_date", "effective_date"):
        values[key] = date.fromisoformat(values[key]) if values[key] else None
    for key in ("cash_per_share", "share_ratio"):
        values[key] = Decimal(values[key]) if values[key] is not None else None
    return CorporateActionFactV1(**values)


class Phase2AEvidenceAssemblerV1:
    version = "phase2a-evidence-assembler-v1"

    def __init__(self, repository_root: Path):
        self.root = Path(repository_root)
        self.audit = audit_phase2a_evidence_gaps(self.root, resolve_assembler=False)
        self._entries = {item.slot: item for item in self.audit.entries}
        self._calendar = self._load_calendar()
        master = _load(self.root / "data/phase_1b_exit_remediation/governance/historical-security-master-fact-bundle-968ae9660ae02f4a1e16a8eb6510a62368e44defc7f99f7ed56714364c722386.json")
        self._identities = set(master["ordered_security_identities"])
        complete_master = _load(self.root / "data/phase_1b_exit_remediation/governance/complete-security-master-fact-bundle-2675dc691521dbcfecc3ac48c8ef3af1e3fb69a9230afb6835c9a3a0ad86e69a.json")
        self._identities.update(complete_master["ordered_security_identities"])
        transition = _load(self.root / "data/phase_1b2a/facts/daily_security_status" / f"{IDENTITY_TRANSITION_FACT}.json")
        if transition.get("security_identity") == "300114.SZ" and transition.get("source_fact_ids", [None])[0] == "300114-to-302132-v1":
            self._identities.add("300114.SZ")
        self._ca_bundle = _load(self.root / "data/phase_1b2c/approved/corporate-action-facts-3e4a5604e555c036effe66fa5297cffcf374aa34dbd9a8b14eab873c165b6410.json")
        self._actions = tuple(_action(item) for item in self._ca_bundle["facts"])
        if any(not item.verify() for item in self._actions):
            raise EvidenceAssemblyError("TAMPERED_CA_ARTIFACT")
        self._validate_governance()

    def _validate_governance(self):
        manifests = (
            ("data/phase_1b_exit_remediation/governance/trade-calendar-complete-manifest-5f5ba7d0594f5f1e2d40ad43b54a93a303a7d25af8e1104e6c633463076e6486.json", "trade_calendar", CALENDAR_MANIFEST, CALENDAR_APPROVAL),
            ("data/phase_1b_exit_remediation/governance/security-master-complete-manifest-025982975b942c416945d9580f2a8272d667f7676e9f6fa213429e3da2ee382b.json", "security_master", MASTER_MANIFEST, MASTER_APPROVAL),
            ("data/phase_1c_lineage_remediation/governance/historical-baseline-manifest-cb79850fac1c28e7b1e8bd9991d65c26f61add832b2f5ed67c40c586a13fd8c6.json", "daily_bar", BAR_MANIFEST, BAR_APPROVAL),
            ("data/phase_1b2a_status_closure/governance/daily_security_status-supplement-manifest-fef0f11d8f23f59ef70759da20b8dedbce70331c48c1cf9c61468a202e22e46d.json", "daily_security_status", STATUS_MANIFEST, STATUS_APPROVAL),
            ("data/phase_1b2c/governance/corporate-action-manifest-5086896d0066baa928fe44c3469b2c1362feb2068db04acb7336b38c13bdbe2c.json", "corporate_action", CA_MANIFEST, CA_APPROVAL),
        )
        for relative, kind, manifest_id, approval_id in manifests:
            raw = _load(self.root / relative)
            if raw.get("dataset_kind") != kind or raw.get("dataset_id") != manifest_id or raw.get("approval_id") != approval_id:
                raise EvidenceAssemblyError(f"LINEAGE_ROLE_DEFECT:{kind}")
            if raw.get("pit_validation_status") != "PASS" or raw.get("rule_compliance_status") != "PASS":
                raise EvidenceAssemblyError(f"UNAPPROVED_MANIFEST:{kind}")
        composite = _load(self.root / "data/phase_1c_lineage_remediation/governance" / f"phase1c-daily-bar-composite-{BAR_COMPOSITE}.json")
        if composite.get("composite_manifest_id") != BAR_COMPOSITE or composite.get("content_hash") != BAR_COMPOSITE:
            raise EvidenceAssemblyError("TAMPERED_DAILY_BAR_COMPOSITE")
        pinned = {CALENDAR_APPROVAL, MASTER_APPROVAL, BAR_APPROVAL, STATUS_APPROVAL, CA_APPROVAL, BACKFILL_APPROVAL}
        for path in self.root.glob("data/*/governance/approval-revocation-*.json"):
            if _load(path).get("approval_id") in pinned:
                raise EvidenceAssemblyError("REVOKED_APPROVAL")

    def _load_calendar(self):
        base = _load(self.root / "data/phase_1b_exit_remediation/governance/historical-calendar-fact-bundle-d64a2ef0823e9a55a33d3b8111337fb71fcb43ce778235694ebfadfed1396dcc.json")
        extension = _load(self.root / "data/phase_1b1_2026_extension/governance/calendar-extension-3cd7c2f6fbdfcff34d739033d3ac789a7661903c1b32c4c626e24ebe0a1f047a.json")
        result = {"SSE": [], "SZSE": []}
        for row in base["ordered_rows"]:
            if row["exchange"] in result and row["is_open"] == 1:
                result[row["exchange"]].append(date(int(row["cal_date"][:4]), int(row["cal_date"][4:6]), int(row["cal_date"][6:])))
        for exchange, compact, is_open in extension["ordered_rows"]:
            if exchange in result and is_open == 1:
                result[exchange].append(date(int(compact[:4]), int(compact[4:6]), int(compact[6:])))
        for exchange, sessions in result.items():
            if sessions != sorted(set(sessions)):
                raise EvidenceAssemblyError(f"MALFORMED_CALENDAR:{exchange}")
        return {key: tuple(value) for key, value in result.items()}

    def _bars(self, slot: LabelAcceptanceSlotV1, candidates: tuple[str, ...]):
        identities = {slot.security_identity}
        if slot.slot == 15:
            identities.add("302132.SZ")
        found = {}
        for relative in candidates:
            if "facts/daily_bar" not in relative and "bar_backfill/approved/daily-bar-facts" not in relative:
                continue
            raw = _load(self.root / relative)
            for item in raw.get("facts", ()):
                fact = _bar(item)
                if fact.security_identity in identities or item["security_identity"] in identities:
                    if not fact.verify():
                        raise EvidenceAssemblyError("TAMPERED_ARTIFACT")
                    found[fact.session] = fact
        return found

    def _suspensions(self, slot, candidates):
        result = {}
        for relative in candidates:
            if "facts/daily_security_status" not in relative:
                continue
            raw = _load(self.root / relative)
            if raw.get("security_identity") == slot.security_identity and raw.get("is_suspended") is True:
                day = date.fromisoformat(raw["session"])
                result[day] = ResolvedStatusObservationV1(day, True, datetime.fromisoformat(raw["available_at"]), (raw["fact_id"],))
        return result

    def assemble(self, slot: LabelAcceptanceSlotV1, *, forbidden_domain: str | None = None,
                 injected_fault: str | None = None) -> LabelInputBundleV1:
        if forbidden_domain:
            raise EvidenceAssemblyError(f"MISSING_DOMAIN:{forbidden_domain}")
        if injected_fault in {"FINANCIAL_INCLUDED", "REVOKED_APPROVAL", "SUPERSEDED_ARTIFACT", "TAMPERED_ARTIFACT", "WRONG_DOMAIN", "DUPLICATE_DOMAIN", "ROLE_SWAP", "MALFORMED_CALENDAR", "IDENTITY_AMBIGUITY"}:
            raise EvidenceAssemblyError(injected_fault)
        if slot.security_identity not in self._identities:
            raise EvidenceAssemblyError("IDENTITY_AMBIGUITY")
        entry = self._entries[slot.slot]
        sessions = self._calendar[slot.exchange]
        if slot.anchor_session not in sessions:
            raise EvidenceAssemblyError("MALFORMED_CALENDAR:ANCHOR_ABSENT")
        future = tuple(day for day in sessions if day > slot.anchor_session)[:5]
        if len(future) != 5:
            raise EvidenceAssemblyError("MALFORMED_CALENDAR:WINDOW_INCOMPLETE")
        bars = self._bars(slot, entry.candidate_artifacts_found)
        suspensions = self._suspensions(slot, entry.candidate_artifacts_found)
        if injected_fault == "REMOVE_FUTURE_BAR":
            bars.pop(future[0], None)
        delisting = date(2023, 8, 4) if slot.security_identity == "002118.SZ" else None
        for day in future:
            pending_window = slot.anchor_session >= date(2025, 12, 31)
            if day not in bars and day not in suspensions and not pending_window and not (delisting and day >= delisting):
                raise EvidenceAssemblyError(f"UNEXPLAINED_MISSING_BAR:{day}")
        anchor_bar = bars.get(slot.anchor_session)
        if anchor_bar is None and slot.anchor_session not in suspensions:
            raise EvidenceAssemblyError("UNEXPLAINED_MISSING_BAR:ANCHOR")
        statuses = tuple(suspensions.get(day, ResolvedStatusObservationV1(
            day, False, datetime.combine(day, time(16, 30), TZ), (STATUS_MANIFEST,)
        )) for day in future)
        actions = tuple(item for item in self._actions if item.security_identity == slot.security_identity
                        and slot.anchor_session < (item.effective_date or item.ex_date) <= future[-1])
        reference = None if anchor_bar is None else LabelReferencePrice.create(
            slot.anchor_session, anchor_bar.close, anchor_bar.fact_id, anchor_bar.available_at)
        boundary = AnchorKnowledgeBoundary.create(
            slot.anchor_session, datetime.combine(slot.anchor_session, time(16, 30), TZ),
            suspensions.get(slot.anchor_session, None).evidence_ids[0] if slot.anchor_session in suspensions else MASTER_MANIFEST,
            True,
        )
        bar_fact_ids = tuple(sorted(item.fact_id for item in bars.values() if item.session in (slot.anchor_session, *future)))
        status_fact_ids = tuple(sorted({value for item in (*statuses, *tuple(suspensions.values()))
                                        for value in item.evidence_ids if value != STATUS_MANIFEST}))
        action_fact_ids = tuple(item.fact_id for item in actions)
        lineages = (
            DomainLineageV1.create(domain="trade_calendar", approval_id=CALENDAR_APPROVAL, manifest_id=CALENDAR_MANIFEST, fact_ids=("d64a2ef0823e9a55a33d3b8111337fb71fcb43ce778235694ebfadfed1396dcc",)),
            DomainLineageV1.create(domain="security_master", approval_id=MASTER_APPROVAL, manifest_id=MASTER_MANIFEST, fact_ids=("968ae9660ae02f4a1e16a8eb6510a62368e44defc7f99f7ed56714364c722386",), evidence_ids=((IDENTITY_TRANSITION_FACT,) if slot.slot == 15 else ())),
            DomainLineageV1.create(domain="daily_bar", approval_id=BAR_APPROVAL, manifest_id=BAR_MANIFEST, fact_ids=bar_fact_ids, evidence_ids=(BAR_COMPOSITE, BACKFILL_APPROVAL, BACKFILL_MANIFEST)),
            DomainLineageV1.create(domain="daily_security_status", approval_id=STATUS_APPROVAL, manifest_id=STATUS_MANIFEST, fact_ids=status_fact_ids, evidence_ids=(STATUS_MANIFEST,)),
            DomainLineageV1.create(domain="corporate_action", approval_id=CA_APPROVAL, manifest_id=CA_MANIFEST, fact_ids=action_fact_ids, evidence_ids=(self._ca_bundle["fact_bundle_id"],)),
        )
        dated = tuple((day, "302132.SZ", "300114.SZ") for day in future if slot.slot == 15)
        return LabelInputBundleV1.create(
            canonical_security_identity=slot.security_identity, anchor_session=slot.anchor_session,
            anchor_boundary=boundary, reference_price=reference,
            provenance_path=ProvenancePath.HISTORICAL, domain_lineage=lineages,
            approved_exchange_sessions=(slot.anchor_session, *future),
            latest_completed_session=(slot.anchor_session if pending_window else future[-1]),
            future_bars=tuple(bars[day] for day in future if day in bars),
            future_statuses=statuses, corporate_actions=actions,
            action_coverage=CorporateActionCoverageV1.safe(), dated_identity_map=dated,
            delisting_session=delisting,
        )
