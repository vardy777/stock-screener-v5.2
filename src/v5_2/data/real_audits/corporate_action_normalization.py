from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal, InvalidOperation

from v5_2.data.corporate_action_facts import ActionType, CorporateActionFactV1
from v5_2.data.identity import content_hash
from v5_2.data.real_audits.corporate_action_availability import CorporateActionAvailabilityPolicyV1


class CorporateActionNormalizationError(RuntimeError):
    """A provider dividend row cannot become a PIT-safe fact."""


def _date(value: object):
    text = str(value or "").strip()
    if len(text) != 8 or not text.isdigit():
        raise CorporateActionNormalizationError("required date is invalid")
    return datetime.strptime(text, "%Y%m%d").date()


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except InvalidOperation as error:
        raise CorporateActionNormalizationError("economic value is invalid") from error


def normalize_dividend_rows(
    rows: Sequence[Mapping[str, object]], *, source_version_identity: str,
    policy: CorporateActionAvailabilityPolicyV1,
) -> tuple[CorporateActionFactV1, ...]:
    facts = []
    for row in rows:
        identity = str(row.get("ts_code") or "").strip()
        if not identity or str(row.get("div_proc") or "").strip() != "实施":
            raise CorporateActionNormalizationError("only identified implemented plans are accepted")
        publication_date = _date(row.get("imp_ann_date") or row.get("ann_date"))
        ex_date = _date(row.get("ex_date"))
        availability = policy.historical(published_at=None, publication_date=publication_date)
        source_fact_id = content_hash(dict(row))
        common = dict(
            security_identity=identity, knowledge_class=availability.knowledge_class,
            published_at=None, available_at=availability.available_at, ex_date=ex_date,
            effective_date=ex_date, source_version_identity=source_version_identity,
            revision_marker=str(row.get("div_proc")), supersedes_source_fact_id=None,
            is_cancelled=False,
        )
        share = _decimal(row.get("stk_div"))
        cash = _decimal(row.get("cash_div_tax"))
        if share > 0:
            facts.append(CorporateActionFactV1.create(
                action_type=ActionType.BONUS_SHARE, cash_per_share=None,
                share_ratio=share, source_fact_id=f"{source_fact_id}:bonus", **common,
            ))
        if cash > 0:
            facts.append(CorporateActionFactV1.create(
                action_type=ActionType.CASH_DIVIDEND, cash_per_share=cash,
                share_ratio=None, source_fact_id=f"{source_fact_id}:cash", **common,
            ))
    return tuple(sorted(facts, key=lambda fact: (fact.security_identity, fact.effective_date, fact.action_type)))
