from __future__ import annotations

from dataclasses import dataclass

from v5_2.data.identity import content_hash


TARGET_PREFIXES = {"SSE": ("600", "601", "603", "605", "688"),
                   "SZSE": ("000", "001", "002", "003", "300", "301")}


@dataclass(frozen=True, slots=True)
class NeverConfirmedTradableExclusionV1:
    security_identity: str
    observed_source_record_ids: tuple[str, ...]
    absence_of_trading_evidence_ids: tuple[str, ...]
    classification: str
    reason: str
    effective_research_impact: str
    research_eligible: bool
    survivorship_blocking: bool
    content_hash: str

    @classmethod
    def create(cls, *, security_identity, observed_source_record_ids, absence_of_trading_evidence_ids,
               has_approved_daily_bar, has_verified_trading_session, has_reliable_tradability_proof, reason):
        if has_approved_daily_bar or has_verified_trading_session or has_reliable_tradability_proof:
            raise ValueError("cannot exclude an identity with actual trading proof")
        observed = tuple(sorted(set(observed_source_record_ids)))
        absence = tuple(sorted(set(absence_of_trading_evidence_ids)))
        if not observed or not absence or not str(reason).strip():
            raise ValueError("exclusion requires observed records, absence evidence, and reason")
        body = {"schema_version": "NeverConfirmedTradableExclusionV1", "security_identity": security_identity,
                "observed_source_record_ids": observed, "absence_of_trading_evidence_ids": absence,
                "classification": "NEVER_CONFIRMED_TRADABLE", "reason": str(reason).strip(),
                "effective_research_impact": "conservative exclusion from historical research universe",
                "research_eligible": False, "survivorship_blocking": False}
        values = {key: value for key, value in body.items() if key != "schema_version"}
        return cls(**values, content_hash=content_hash(body))


@dataclass(frozen=True, slots=True)
class HistoricalUniverseReconciliationItemV1:
    security_identity: str
    category: str
    effective_from: str | None
    effective_to: str | None
    evidence_ids: tuple[str, ...]
    research_scope_impact: str
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
                                  official_evidence, resolution_overrides=None):
    resolution_overrides = resolution_overrides or {}
    originals = set(original_symbols)
    items = []
    supplements = []
    counts = {}
    for symbol in sorted(set(observed_symbols) - originals):
        row = master_rows.get(symbol)
        start = None if row is None else row.get("list_date")
        end = None if row is None else row.get("delist_date")
        override = resolution_overrides.get(symbol)
        if override:
            category = str(override["category"])
            if category not in {"TARGET_A_SHARE_REQUIRED", "NON_TARGET", "OUTSIDE_RESEARCH_COVERAGE",
                                "IDENTITY_ALIAS", "EFFECTIVE_IDENTITY_ALREADY_PRESENT", "LEGACY_CODE",
                                "LOCAL_EXCEPTION", "NEVER_CONFIRMED_TRADABLE", "UNRESOLVED"}:
                raise ValueError("invalid historical universe disposition")
            start, end = override.get("effective_from"), override.get("effective_to")
            evidence_ids = tuple(sorted(set(override.get("evidence_ids", ()))))
            impact = str(override.get("research_scope_impact", ""))
            if category != "UNRESOLVED" and (not evidence_ids or not impact):
                raise ValueError("resolved identity requires evidence and research scope impact")
        elif symbol in aliases and aliases[symbol] in originals:
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
        if not override:
            evidence_ids = tuple(sorted(set(official_evidence.get(symbol, ()))))
            impact = "requires inclusion" if category == "TARGET_A_SHARE_REQUIRED" else "classified by frozen master and scope"
        body = {"schema_version": "HistoricalUniverseReconciliationItemV1",
                "security_identity": symbol, "category": category,
                "effective_from": start, "effective_to": end, "evidence_ids": evidence_ids,
                "research_scope_impact": impact}
        items.append(HistoricalUniverseReconciliationItemV1(symbol, category, start, end, evidence_ids, impact, content_hash(body)))
        counts[category] = counts.get(category, 0) + 1
        evidence = evidence_ids
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
