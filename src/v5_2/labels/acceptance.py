from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from v5_2.data.identity import content_hash
from v5_2.labels.contracts import ProvenancePath


PHASE2A_STRATA = (
    "normal positive return", "normal negative return", "high volatility",
    "limit-up-like path", "limit-down-like path", "cash dividend", "bonus share",
    "D+1 full-day suspension", "multi-day suspension", "suspension through H5",
    "resumption before H5", "first IPO-eligible boundary", "still inside IPO seasoning",
    "delisting boundary", "identity transition", "expected future bar missing",
    "unsupported corporate action", "latest-session LABEL_PENDING",
    "upper barrier first", "lower barrier first", "neither barrier",
    "same-session double-barrier ambiguity",
)


@dataclass(frozen=True, slots=True)
class LabelAcceptanceSelectionRuleV1:
    contract_version: str
    ordering: str
    result_blind: bool
    content_hash: str

    @classmethod
    def create(cls):
        body = {"contract_version": "v5.2-label-contract-v1", "ordering": "content_hash(contract_version,stratum,canonical_identity,anchor_session)", "result_blind": True}
        return cls(**body, content_hash=content_hash({"schema_version": cls.__name__, **body}))


@dataclass(frozen=True, slots=True)
class LabelAcceptanceSlotV1:
    slot: int
    stratum: str
    security_identity: str
    anchor_session: date
    exchange: str
    board: str
    provenance_path: ProvenancePath
    inventory_status: str
    source_kind: str
    evidence_ids: tuple[str, ...]
    reason: str | None
    candidate_hash: str


@dataclass(frozen=True, slots=True)
class LabelAcceptanceInventoryV1:
    selection_rule: LabelAcceptanceSelectionRuleV1
    slots: tuple[LabelAcceptanceSlotV1, ...]
    inventory_id: str
    content_hash: str

    def verify(self) -> bool:
        body = {"selection_rule": self.selection_rule, "slots": self.slots}
        digest = content_hash({"schema_version": type(self).__name__, **body})
        return self.inventory_id == self.content_hash == digest and len(self.slots) == 22


_STATUS_INV = "cef91ec0a055f01ac2f0f82ec8e15ce75f4e000acd2123a70685fb25d1df3c9c"
_CA_INV = "90354c25bb7529048a2a391ba06e8e4cfb5daf732f9b6abcca94189fa13023c5"
_BAR_MANIFEST = "1ad71807083aba6222fa6ab27aedf47c0ac2e2ba65a56ad1ce5ae5956db43ead"
_REAL_CASES = (
    ("000969.SZ", "2024-01-24", "SZSE", "main", _BAR_MANIFEST),
    ("000969.SZ", "2024-01-02", "SZSE", "main", _BAR_MANIFEST),
    ("000969.SZ", "2024-02-05", "SZSE", "main", _BAR_MANIFEST),
    ("000969.SZ", "2024-09-30", "SZSE", "main", _BAR_MANIFEST),
    ("000969.SZ", "2024-10-08", "SZSE", "main", _BAR_MANIFEST),
    ("000333.SZ", "2021-06-01", "SZSE", "main", _CA_INV),
    ("600276.SH", "2019-03-27", "SSE", "main", _CA_INV),
    ("600658.SH", "2010-05-18", "SSE", "main", _STATUS_INV),
    ("002166.SZ", "2019-04-12", "SZSE", "main", _STATUS_INV),
    ("600155.SH", "2015-11-16", "SSE", "main", _STATUS_INV),
    ("300131.SZ", "2014-09-11", "SZSE", "ChiNext", _STATUS_INV),
    ("688053.SH", "2022-07-14", "SSE", "STAR", _STATUS_INV),
    ("688247.SH", "2022-08-30", "SSE", "STAR", _STATUS_INV),
    ("002118.SZ", "2023-08-03", "SZSE", "main", _STATUS_INV),
    ("300114.SZ", "2025-02-14", "SZSE", "ChiNext", _STATUS_INV),
    ("000969.SZ", "2024-06-05", "SZSE", "main", _BAR_MANIFEST),
    ("000651.SZ", "2010-07-12", "SZSE", "main", _CA_INV),
    ("000969.SZ", "2025-12-31", "SZSE", "main", _BAR_MANIFEST),
    ("000969.SZ", "2024-02-06", "SZSE", "main", _BAR_MANIFEST),
    ("000969.SZ", "2024-02-07", "SZSE", "main", _BAR_MANIFEST),
    ("000969.SZ", "2024-03-01", "SZSE", "main", _BAR_MANIFEST),
    ("000969.SZ", "2024-02-08", "SZSE", "main", _BAR_MANIFEST),
)


def build_frozen_inventory() -> LabelAcceptanceInventoryV1:
    rule = LabelAcceptanceSelectionRuleV1.create()
    slots = []
    for index, (stratum, case) in enumerate(zip(PHASE2A_STRATA, _REAL_CASES), 1):
        identity, day, exchange, board, evidence = case
        candidate = content_hash((rule.contract_version, stratum, identity, day))
        slots.append(LabelAcceptanceSlotV1(index, stratum, identity, date.fromisoformat(day), exchange, board,
                                           ProvenancePath.HISTORICAL, "EVIDENCE_AVAILABLE",
                                           "REAL_PHASE1_ARTIFACT", (evidence,), None, candidate))
    body = {"selection_rule": rule, "slots": tuple(slots)}
    digest = content_hash({"schema_version": "LabelAcceptanceInventoryV1", **body})
    return LabelAcceptanceInventoryV1(rule, tuple(slots), digest, digest)
