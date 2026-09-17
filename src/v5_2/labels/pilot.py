from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path

from v5_2.data.identity import content_hash
from v5_2.labels.acceptance import build_frozen_inventory
from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1
from v5_2.labels.contracts import CORE_LABELS
from v5_2.labels.engine import ReferenceLabelEngine


PILOT_SLOTS = (1, 6, 8, 11, 18)
Q = Decimal("0.00000001")


def _q(value: Decimal) -> Decimal:
    return value.quantize(Q, rounding=ROUND_HALF_EVEN)


def _summary(result):
    return tuple((item.label_name, item.state.value, str(item.value), item.reason_code.value if item.reason_code else "") for item in result.values)


def independent_calculate(bundle):
    """Independent reference: deliberately does not import production calculation code."""
    if bundle.delisting_session is not None:
        reason = "DELISTING_IN_HORIZON"
        return tuple((name, "NOT_LABEL_SAFE", "None", reason) for name in CORE_LABELS)
    if bundle.reference_price is None:
        return tuple((name, "NOT_LABEL_SAFE", "None", "ANCHOR_BAR_MISSING") for name in CORE_LABELS)
    sessions = tuple(day for day in bundle.approved_exchange_sessions if day > bundle.anchor_session)[:5]
    if sessions and sessions[0] > bundle.latest_completed_session:
        return tuple((name, "LABEL_PENDING", "None", "HORIZON_NOT_COMPLETED") for name in CORE_LABELS)
    bars = {item.session: item for item in bundle.future_bars}
    statuses = {item.session: item for item in bundle.future_statuses}
    shares, cash = Decimal("1"), Decimal("0")
    previous = bundle.reference_price.price
    points = []
    for day in sessions:
        todays = tuple(item for item in bundle.corporate_actions if (item.effective_date or item.ex_date) == day and not item.is_cancelled)
        pre_shares = shares
        for item in todays:
            if item.action_type.value == "CASH_DIVIDEND":
                cash += pre_shares * (item.cash_per_share or Decimal("0"))
            elif item.action_type.value == "BONUS_SHARE":
                shares *= Decimal("1") + (item.share_ratio or Decimal("0"))
            else:
                return tuple((name, "NOT_LABEL_SAFE", "None", "UNSUPPORTED_CORPORATE_ACTION") for name in CORE_LABELS)
        bar = bars.get(day)
        if bar is None:
            if not statuses.get(day) or not statuses[day].is_suspended:
                return tuple((name, "NOT_LABEL_SAFE", "None", "EXPECTED_BAR_MISSING") for name in CORE_LABELS)
            points.append((day, None, None, previous, False))
        else:
            high, low, close = cash + shares * bar.high, cash + shares * bar.low, cash + shares * bar.close
            points.append((day, high, low, close, True))
            previous = close
    denominator = bundle.reference_price.price
    numeric = (
        _q(points[0][3] / denominator - 1), _q(points[2][3] / denominator - 1),
        _q(points[4][3] / denominator - 1),
        _q(max([Decimal("0"), *[point[1] / denominator - 1 for point in points if point[1] is not None]])),
        _q(min([Decimal("0"), *[point[2] / denominator - 1 for point in points if point[2] is not None]])),
    )
    barrier_values = []
    for upper, lower in ((Decimal(".03"), Decimal("-.02")), (Decimal(".05"), Decimal("-.03"))):
        value = False
        for _, high, low, _, traded in points:
            if not traded:
                continue
            up, down = high / denominator - 1 >= upper, low / denominator - 1 <= lower
            if up and down:
                return tuple((name, "NOT_LABEL_SAFE", "None", "BARRIER_PATH_AMBIGUOUS") for name in CORE_LABELS)
            if up or down:
                value = up
                break
        barrier_values.append(value)
    values = (*numeric, *barrier_values)
    return tuple((name, "LABEL_AVAILABLE", str(value), "") for name, value in zip(CORE_LABELS, values))


@dataclass(frozen=True, slots=True)
class PilotEntryV1:
    slot: int
    bundle_id: str
    engine_summary: tuple[tuple[str, str, str, str], ...]
    independent_summary: tuple[tuple[str, str, str, str], ...]
    disposition: str


@dataclass(frozen=True, slots=True)
class Phase2APilotV1:
    inventory_id: str
    slots: tuple[int, ...]
    entries: tuple[PilotEntryV1, ...]
    assembler_version: str
    provider_requests: int
    pilot_id: str
    content_hash: str

    def verify(self):
        body = {name: getattr(self, name) for name in ("inventory_id", "slots", "entries", "assembler_version", "provider_requests")}
        digest = content_hash({"schema_version": type(self).__name__, **body})
        return self.pilot_id == self.content_hash == digest

    def as_dict(self):
        return {"schema_version": type(self).__name__, **asdict(self)}


def run_pilot(root: Path) -> Phase2APilotV1:
    inventory = build_frozen_inventory()
    assembler = Phase2AEvidenceAssemblerV1(root)
    engine = ReferenceLabelEngine()
    entries = []
    for number in PILOT_SLOTS:
        bundle = assembler.assemble(inventory.slots[number - 1])
        produced = _summary(engine.evaluate(bundle))
        independent = independent_calculate(bundle)
        entries.append(PilotEntryV1(number, bundle.content_hash, produced, independent, "MATCH" if produced == independent else "MISMATCH"))
    body = {"inventory_id": inventory.inventory_id, "slots": PILOT_SLOTS, "entries": tuple(entries),
            "assembler_version": assembler.version, "provider_requests": 0}
    digest = content_hash({"schema_version": "Phase2APilotV1", **body})
    return Phase2APilotV1(**body, pilot_id=digest, content_hash=digest)
