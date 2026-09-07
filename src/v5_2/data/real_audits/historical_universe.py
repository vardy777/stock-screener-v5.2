from __future__ import annotations

from dataclasses import dataclass

from v5_2.data.identity import content_hash


TARGET_PREFIXES = {"SSE": ("600", "601", "603", "605", "688"),
                   "SZSE": ("000", "001", "002", "003", "300", "301")}


@dataclass(frozen=True, slots=True)
class HistoricalUniverseReconciliationItemV1:
    security_identity: str
    category: str
    effective_from: str | None
    effective_to: str | None
    item_hash: str


@dataclass(frozen=True, slots=True)
class HistoricalUniverseSupplementIdentityV1:
    security_identity: str
    effective_from: str
    effective_to: str | None
    official_evidence_ids: tuple[str, ...]
    reason: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class HistoricalUniverseSupplementV1:
    original_universe_id: str
    identities: tuple[HistoricalUniverseSupplementIdentityV1, ...]
    content_hash: str


@dataclass(frozen=True, slots=True)
class HistoricalUniverseReconciliationV1:
    original_universe_id: str
    total: int
    counts: tuple[tuple[str, int], ...]
    items: tuple[HistoricalUniverseReconciliationItemV1, ...]
    supplement: HistoricalUniverseSupplementV1
    content_hash: str


def reconcile_historical_universe(*, observed_symbols, original_symbols, master_rows, aliases,
                                  coverage_start, coverage_end, original_universe_id,
                                  official_evidence):
    originals = set(original_symbols)
    items = []
    supplements = []
    counts = {}
    for symbol in sorted(set(observed_symbols) - originals):
        row = master_rows.get(symbol)
        start = None if row is None else row.get("list_date")
        end = None if row is None else row.get("delist_date")
        if symbol in aliases and aliases[symbol] in originals:
            category = "IDENTITY_ALIAS"
        elif row is None:
            category = "UNRESOLVED"
        else:
            exchange = str(row.get("exchange"))
            native = str(row.get("symbol"))
            if exchange not in TARGET_PREFIXES or not native.startswith(TARGET_PREFIXES[exchange]):
                category = "NON_TARGET"
            elif (end and end < coverage_start) or (start and start > coverage_end):
                category = "OUTSIDE_RESEARCH_COVERAGE"
            else:
                category = "TARGET_A_SHARE_REQUIRED"
        body = {"schema_version": "HistoricalUniverseReconciliationItemV1",
                "security_identity": symbol, "category": category,
                "effective_from": start, "effective_to": end}
        items.append(HistoricalUniverseReconciliationItemV1(symbol, category, start, end, content_hash(body)))
        counts[category] = counts.get(category, 0) + 1
        evidence = tuple(sorted(set(official_evidence.get(symbol, ()))))
        if category == "TARGET_A_SHARE_REQUIRED" and evidence and start:
            supplement_body = {"schema_version": "HistoricalUniverseSupplementIdentityV1",
                               "security_identity": symbol, "effective_from": start,
                               "effective_to": end, "official_evidence_ids": evidence,
                               "reason": "historical eligible A-share omitted from frozen universe"}
            supplements.append(HistoricalUniverseSupplementIdentityV1(
                symbol, start, end, evidence, supplement_body["reason"], content_hash(supplement_body)))
    supplement_values = {"schema_version": "HistoricalUniverseSupplementV1",
                         "original_universe_id": original_universe_id,
                         "identity_hashes": tuple(item.content_hash for item in supplements)}
    supplement = HistoricalUniverseSupplementV1(original_universe_id, tuple(supplements),
                                                  content_hash(supplement_values))
    ordered_counts = tuple(sorted(counts.items()))
    digest = content_hash({"schema_version": "HistoricalUniverseReconciliationV1",
                           "original_universe_id": original_universe_id, "total": len(items),
                           "counts": ordered_counts, "item_hashes": tuple(item.item_hash for item in items),
                           "supplement_hash": supplement.content_hash})
    return HistoricalUniverseReconciliationV1(original_universe_id, len(items), ordered_counts,
                                                tuple(items), supplement, digest)
