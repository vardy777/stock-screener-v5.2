from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone
import json
from pathlib import Path
import ssl
import sys
import time
from collections.abc import Callable
from urllib.parse import urlencode
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.real_audits.policy_adequacy import CrossSourceEvidencePolicyV2, EvidenceResolution  # noqa: E402
from v5_2.data.real_audits.tier3_calendar import (  # noqa: E402
    CompleteSessionDomainV1,
    CompositeIndependentCalendarEvidenceV1,
    CrossSourceEvidencePolicyAdoptionArtifactV1,
    IndependentCalendarComparisonEvidenceV1,
    IndependentCalendarSampleRequestV1,
    IndependentSourceIdentityV1,
    compare_independent_calendar,
)


AS_OF = datetime(2026, 9, 6, tzinfo=timezone.utc)
FROZEN_INVENTORY_ID = "0242b7d10a358d81f5c1b40a42920ef75c55b1e42f6d1e6ea3a77d85b5e11cd0"
BAOSTOCK_EVIDENCE_ID = "0d7de5ea50303f43d9c09ecb49fcc9a7d45077c398830af26c0e73f6305aa733"
ENDPOINT = "https://www.szse.cn/api/report/exchange/onepersistenthour/monthList"


def _mapping(item):
    return {field.name: getattr(item, field.name) for field in fields(item)}


def _load(name: str):
    return json.loads((ROOT / "data" / "phase_1b1" / "governance" / name).read_text(encoding="utf-8"))


def _fetch_month(month: str) -> dict[str, int]:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    opener = build_opener(ProxyHandler({}), HTTPSHandler(context=context))
    request = Request(
        f"{ENDPOINT}?{urlencode({'month': month})}",
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.szse.cn/aboutus/calendar/"},
    )
    with opener.open(request, timeout=30) as response:
        payload = json.load(response)
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise RuntimeError(f"SZSE calendar provider error for {month}")
    observations = {str(row["jyrq"]): int(row["jybz"]) for row in rows}
    if len(observations) != len(rows):
        raise RuntimeError(f"SZSE calendar duplicate date for {month}")
    return observations


def _fetch_with_retry(fetch: Callable[[str], dict[str, int]], month: str, *, max_attempts: int = 3, sleeper: Callable[[float], None] = time.sleep) -> dict[str, int]:
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    for attempt in range(1, max_attempts + 1):
        try:
            return fetch(month)
        except (ConnectionError, OSError):
            if attempt == max_attempts:
                raise
            sleeper(float(attempt))
    raise RuntimeError("unreachable")


def _load_cached_domains(governance: Path, source_id: str) -> dict[str, CompleteSessionDomainV1]:
    result = {}
    for path in governance.glob("szse-calendar-domain-*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("source_id") != source_id:
            continue
        domain = CompleteSessionDomainV1.create(
            exchange=payload["exchange"], start=payload["start"], end=payload["end"],
            observations=payload["observations"], source_id=payload["source_id"],
            policy_version=payload["policy_version"],
        )
        result[domain.start[:7]] = domain
    return dict(sorted(result.items()))


def main() -> int:
    governance = ROOT / "data" / "phase_1b1" / "governance"
    frozen = _load(f"trade-calendar-unresolved-{FROZEN_INVENTORY_ID}.json")
    old_payload = _load(f"baostock-calendar-comparison-{BAOSTOCK_EVIDENCE_ID}.json")
    old = IndependentCalendarComparisonEvidenceV1.from_records(records=old_payload["records"], source_id=old_payload["source_id"])
    if old.evidence_id != BAOSTOCK_EVIDENCE_ID:
        raise RuntimeError("immutable BaoStock evidence identity changed")
    unresolved_ids = {
        record["sample_id"] for record in old.records
        if record["exchange"] == "SZSE" and record["resolution"] == EvidenceResolution.UNRESOLVED_EVIDENCE
    }
    selected = tuple(sample for sample in frozen["samples"] if sample["sample_id"] in unresolved_ids)
    if len(selected) != 128 or {sample["exchange"] for sample in selected} != {"SZSE"}:
        raise RuntimeError("exact frozen SZSE unresolved sample count is not 128")

    source = IndependentSourceIdentityV1.create(
        source_name="Shenzhen Stock Exchange official calendar",
        provider_identity="SZSE www.szse.cn",
        dataset_kind="trade_calendar",
        endpoint_identity=ENDPOINT,
        source_independence_rationale="direct exchange-operated endpoint unrelated to the DataHub ingestion provider",
        coverage_capability={"start": "2010-01-01", "end": "2025-12-31", "exchanges": ("SZSE",), "domain": "explicit every calendar date by month"},
        schema_identity=("jyrq", "jybz"), retrieved_at=AS_OF,
        policy_version="independent-source-v1",
    )
    requests = IndependentCalendarSampleRequestV1.from_frozen(selected, source)
    months = sorted({request.calendar_date[:7] for request in requests})
    observations: dict[str, int] = {}
    domains = []
    cached = _load_cached_domains(governance, source.source_id)
    for month in months:
        domain = cached.get(month)
        if domain is None:
            values = _fetch_with_retry(_fetch_month, month)
            domain = CompleteSessionDomainV1.create(
                exchange="SZSE", start=min(values), end=max(values), observations=values,
                source_id=source.source_id, policy_version="szse-complete-month-domain-v1",
            )
            (governance / f"szse-calendar-domain-{domain.domain_id}.json").write_bytes(canonical_json(_mapping(domain)))
        values = dict(domain.observations)
        observations.update(values)
        domains.append(domain)
    comparison = compare_independent_calendar(requests, observations, source, official_anchors={request.sample_id: observations[request.calendar_date] for request in requests})
    baostock_sse = IndependentCalendarComparisonEvidenceV1.from_records(
        records=tuple(record for record in old.records if record["exchange"] == "SSE"),
        source_id=old.source_id,
    )
    composite = CompositeIndependentCalendarEvidenceV1.create(
        frozen_sample_ids=tuple(sample["sample_id"] for sample in frozen["samples"]),
        components=(baostock_sse, comparison), preserved_evidence_ids=(old.evidence_id,),
        policy_version="composite-independent-calendar-v1",
    )
    policy = CrossSourceEvidencePolicyV2.create_default()
    adoption = CrossSourceEvidencePolicyAdoptionArtifactV1.create(
        v1_policy_id=frozen["policy_id"], v2_policy=policy, independent_source=source,
        sample_evidence_id=composite.evidence_id, total=composite.total,
        matches=composite.match_count, mismatches=composite.mismatch_count,
        unresolved=composite.unresolved_count, provider_errors=composite.provider_error_count,
        official_anchor_evidence_ids=tuple(domain.domain_id for domain in domains),
        adopted_at=AS_OF, methodological_reason="frozen 256-sample inventory fully matched by immutable BaoStock SSE and direct SZSE official calendar evidence",
    )
    for name, artifact in (
        (f"independent-source-{source.source_id}.json", source),
        (f"baostock-sse-projection-{baostock_sse.evidence_id}.json", baostock_sse),
        (f"szse-calendar-comparison-{comparison.evidence_id}.json", comparison),
        (f"composite-calendar-{composite.evidence_id}.json", composite),
        (f"cross-source-policy-v2-adoption-{adoption.adoption_id}.json", adoption),
    ):
        (governance / name).write_bytes(canonical_json(_mapping(artifact)))
    print(f"SECOND_SOURCE={source.source_id} INDEPENDENCE=PASS EXACT_SZSE_UNRESOLVED={len(selected)}")
    print(f"COMPOSITE={composite.evidence_id} TOTAL={composite.total} MATCH={composite.match_count} MISMATCH={composite.mismatch_count} UNRESOLVED={composite.unresolved_count} PROVIDER_ERROR={composite.provider_error_count}")
    print(f"CROSS_SOURCE_V2=ADOPTED ADOPTION_ID={adoption.adoption_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
