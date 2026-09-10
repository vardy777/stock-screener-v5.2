from __future__ import annotations

from collections import defaultdict
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


def classify_implemented_rows(
    rows: Sequence[Mapping[str, object]], *, start: str, end: str,
) -> tuple[tuple[Mapping[str, object], ...], tuple[Mapping[str, object], ...]]:
    grouped: dict[tuple[str, str, str, str], list[Mapping[str, object]]] = defaultdict(list)
    quarantines: list[Mapping[str, object]] = []
    for row in rows:
        if str(row.get("div_proc") or "").strip() != "实施":
            continue
        ex_date = str(row.get("ex_date") or "")
        if not (start <= ex_date <= end):
            continue
        identity = str(row.get("ts_code") or "")
        implementation_date = str(row.get("imp_ann_date") or "")
        end_date = str(row.get("end_date") or "")
        if not identity or not implementation_date or not end_date:
            quarantines.append({
                "quarantine_id": content_hash(dict(row)),
                "security_identity": identity,
                "effective_date": ex_date,
                "reason": "INCOMPLETE_IMPLEMENTATION_IDENTITY",
            })
            continue
        grouped[(identity, end_date, ex_date, implementation_date)].append(row)

    selected = []
    for key, versions in sorted(grouped.items()):
        signatures = {
            tuple(format(_decimal(row.get(field)), "f") for field in (
                "cash_div_tax", "stk_bo_rate", "stk_co_rate"
            ))
            for row in versions
        }
        reason = None
        if any(_decimal(row.get("stk_co_rate")) > 0 for row in versions):
            reason = "UNSUPPORTED_SHARE_CONVERSION"
        elif len(signatures) != 1:
            reason = "CONFLICTING_IMPLEMENTED_ECONOMICS"
        if reason:
            quarantines.append({
                "quarantine_id": content_hash({"event_key": key, "reason": reason}),
                "security_identity": key[0], "effective_date": key[2], "reason": reason,
            })
            continue
        selected.append(max(
            versions,
            key=lambda row: (
                sum(value not in (None, "") for value in row.values()),
                str(row.get("ann_date") or ""),
                content_hash(dict(row)),
            ),
        ))
    return tuple(selected), tuple(sorted(quarantines, key=lambda item: str(item["quarantine_id"])))


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
        conversion = _decimal(row.get("stk_co_rate"))
        if conversion > 0:
            raise CorporateActionNormalizationError("share conversion remains unsupported")
        share = _decimal(row.get("stk_bo_rate"))
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
