from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from v5_2.data.corporate_action_facts import ActionType, CorporateActionFactV1


class AdjustmentSemanticsError(RuntimeError):
    """A causal adjustment cannot be derived from these inputs."""


@dataclass(frozen=True, slots=True)
class CausalCorporateActionEffectV1:
    action_type: ActionType
    cash_per_share: Decimal | None
    share_ratio: Decimal | None
    source_fact_id: str


class CausalCorporateActionAdjustmentPolicyV1:
    policy_version = "causal-corporate-action-adjustment-v1"

    def effects_for_bar(self, *, bar, session: date, as_of: datetime, facts) -> tuple[CausalCorporateActionEffectV1, ...]:
        if bar.get("adjustment") != "UNADJUSTED_RAW":
            raise AdjustmentSemanticsError("input must be UNADJUSTED_RAW")
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise AdjustmentSemanticsError("as_of must include timezone")
        visible = []
        for fact in facts:
            if not fact.verify():
                raise AdjustmentSemanticsError("fact integrity failed")
            effective = fact.effective_date or fact.ex_date
            if not fact.is_cancelled and effective == session and fact.available_at <= as_of:
                visible.append(CausalCorporateActionEffectV1(
                    fact.action_type, fact.cash_per_share, fact.share_ratio, fact.source_fact_id))
        return tuple(sorted(visible, key=lambda item: (item.action_type, item.source_fact_id)))
