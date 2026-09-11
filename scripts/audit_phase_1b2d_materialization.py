from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.raw_artifacts import RawArtifactStore  # noqa: E402
from v5_2.data.real_audits.financial_disclosure_availability import FinancialDisclosureAvailabilityPolicyV1  # noqa: E402
from v5_2.data.real_audits.financial_disclosure_normalization import (  # noqa: E402
    CONFIG, financial_fact_equivalence_key, normalize_statement_rows,
)

RUNTIME = ROOT / "data" / "phase_1b2d"
BASE_UNIVERSE = ROOT / "data" / "phase_1b1" / "governance" / "daily-bar-universe-2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01.json"
CALENDAR_EXTENSION = ROOT / "data" / "phase_1b1_2026_extension" / "governance" / "calendar-extension-3cd7c2f6fbdfcff34d739033d3ac789a7661903c1b32c4c626e24ebe0a1f047a.json"


def _write(path: Path, value: object) -> None:
    encoded = canonical_json(value); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded: raise RuntimeError("immutable audit collision")
    if not path.exists(): path.write_bytes(encoded)


def _sessions() -> tuple[date, ...]:
    base = json.loads(BASE_UNIVERSE.read_text(encoding="utf-8"))["ordered_sessions"]
    extension = json.loads(CALENDAR_EXTENSION.read_text(encoding="utf-8"))["ordered_rows"]
    days = set(base)
    days.update(row[1] for row in extension if row[2] == 1)
    return tuple(date(int(day[:4]), int(day[4:6]), int(day[6:])) for day in sorted(days))


def main() -> int:
    summary_id = (RUNTIME / "governance" / "current-acquisition-summary-id.txt").read_text(encoding="ascii").strip()
    summary = json.loads((RUNTIME / "governance" / f"acquisition-summary-{summary_id}.json").read_text(encoding="utf-8"))
    if summary.get("content_hash") != summary_id: raise RuntimeError("acquisition summary identity mismatch")
    expected = set(summary["payload_hashes"])
    paths = {path.stem: path for path in (RUNTIME / "raw").rglob("*.json") if path.stem in expected}
    if set(paths) != expected: raise RuntimeError("exact acquisition payload set is incomplete")
    store = RawArtifactStore(RUNTIME); policy = FinancialDisclosureAvailabilityPolicyV1(_sessions())
    rows_by_kind, facts_by_kind, symbols_by_kind = Counter(), Counter(), defaultdict(set)
    quarantine_reasons, quarantine_ids, fact_ids, equivalent_fact_keys = Counter(), set(), set(), set()
    coverage = {kind: [None, None, None, None] for kind in CONFIG}  # period min/max and publication min/max
    revision_values = defaultdict(lambda: defaultdict(set))
    logical_key_payloads = defaultdict(set)
    integrity_failures = semantics_failures = unit_failures = availability_failures = 0
    for payload_hash in sorted(expected):
        artifact = store.read_payload(paths[payload_hash])
        kind = paths[payload_hash].parts[-4]
        if kind not in CONFIG: raise RuntimeError("unexpected dataset kind in acquisition summary")
        rows = artifact.provider_payload["rows"]
        rows_by_kind[kind] += len(rows)
        result = normalize_statement_rows(kind, rows, source_version_identity=payload_hash, policy=policy)
        new_facts = tuple(fact for fact in result.facts if financial_fact_equivalence_key(fact) not in equivalent_fact_keys)
        facts_by_kind[kind] += len(new_facts)
        equivalent_fact_keys.update(financial_fact_equivalence_key(fact) for fact in new_facts)
        fact_ids.update(fact.fact_id for fact in new_facts)
        symbols_by_kind[kind].update(fact.security_identity for fact in result.facts)
        quarantine_reasons.update(item["reason"] for item in result.quarantines)
        quarantine_ids.update(item["quarantine_id"] for item in result.quarantines)
        expected_semantics = CONFIG[kind][2]
        for fact in result.facts:
            integrity_failures += not fact.verify()
            semantics_failures += fact.reported_value_semantics is not expected_semantics
            unit_failures += fact.unit != "CNY" or fact.currency != "CNY"
            availability_failures += fact.available_at != policy.date_only(fact.published_at)
            period, publication = fact.period_end.strftime("%Y%m%d"), fact.published_at.strftime("%Y%m%d")
            coverage[kind][0] = period if coverage[kind][0] is None else min(coverage[kind][0], period)
            coverage[kind][1] = period if coverage[kind][1] is None else max(coverage[kind][1], period)
            coverage[kind][2] = publication if coverage[kind][2] is None else min(coverage[kind][2], publication)
            coverage[kind][3] = publication if coverage[kind][3] is None else max(coverage[kind][3], publication)
            logical_key_payloads[(kind, fact.security_identity, period, fact.metric)].add(payload_hash)
        metrics = CONFIG[kind][1]
        for row in rows:
            period = row.get("end_date"); publication = row.get("f_ann_date") or row.get("ann_date")
            for metric in metrics:
                if row.get(metric) is not None and period and publication:
                    revision_values[(kind, row.get("ts_code"), period, metric)][publication].add(str(row[metric]))
    later_revision_groups = sum(len(publications) > 1 for publications in revision_values.values())
    same_time_conflicts = sum(any(len(values) > 1 for values in publications.values()) for publications in revision_values.values())
    cross_payload = {key: payloads for key, payloads in logical_key_payloads.items() if len(payloads) > 1}
    cross_payload_conflicts = sum(
        any(len(values) > 1 for values in revision_values[key].values()) for key in cross_payload
    )
    cross_payload_revision_groups = sum(len(revision_values[key]) > 1 for key in cross_payload)
    body = {"schema_version": "FinancialDisclosureMaterializationAuditV1", "acquisition_summary_id": summary_id,
        "inventory_id": summary["inventory_id"], "raw_row_count": sum(rows_by_kind.values()),
        "raw_rows_by_statement": tuple(sorted(rows_by_kind.items())), "staging_fact_count": len(fact_ids),
        "staging_facts_by_statement": tuple(sorted(facts_by_kind.items())),
        "symbols_by_statement": tuple(sorted((kind, len(values)) for kind, values in symbols_by_kind.items())),
        "coverage_by_statement": tuple(sorted((kind, *values) for kind, values in coverage.items())),
        "later_publication_revision_groups": later_revision_groups,
        "same_publication_conflict_groups": same_time_conflicts,
        "quarantine_count": sum(quarantine_reasons.values()),
        "unique_quarantine_count": len(quarantine_ids),
        "quarantine_reasons": tuple(sorted(quarantine_reasons.items())),
        "cross_payload_equivalent_duplicate_groups": len(cross_payload) - cross_payload_conflicts,
        "cross_payload_conflicting_groups": cross_payload_conflicts,
        "cross_payload_revision_groups": cross_payload_revision_groups,
        "fact_integrity_failures": integrity_failures,
        "value_semantics_failures": semantics_failures,
        "unit_semantics_failures": unit_failures,
        "availability_policy_failures": availability_failures,
        "fact_set_hash": content_hash(tuple(sorted(fact_ids))),
        "availability_policy_version": policy.policy_version,
        "reported_value_semantics": (("financial_balance_sheet", "POINT_IN_TIME"),
            ("financial_cash_flow", "PERIOD_CUMULATIVE"), ("financial_income", "PERIOD_CUMULATIVE")),
        "unit_policy": "RAW_DISCLOSED_CNY_V1",
        "exception_budget_policy": {"maximum_ratio": "0.005", "allowed_reasons": tuple(sorted(quarantine_reasons))},
        "exception_ratio": format(sum(quarantine_reasons.values()) / (len(fact_ids) + sum(quarantine_reasons.values())), ".12f")}
    audit_id = content_hash(body)
    _write(RUNTIME / "governance" / f"materialization-audit-{audit_id}.json",
           {"materialization_audit_id": audit_id, "content_hash": audit_id, **body})
    (RUNTIME / "governance" / "current-materialization-audit-id.txt").write_text(audit_id, encoding="ascii")
    print(f"MATERIALIZATION_AUDIT_ID={audit_id} ROWS={body['raw_row_count']} FACTS={body['staging_fact_count']} "
          f"REVISIONS={later_revision_groups} CONFLICTS={same_time_conflicts} QUARANTINES={body['quarantine_count']}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
