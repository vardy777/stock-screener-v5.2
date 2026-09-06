from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.real_audits.tier3_calendar import IndependentCalendarSampleRequestV1, IndependentSourceIdentityV1, compare_independent_calendar  # noqa: E402


INVENTORY_ID = "0242b7d10a358d81f5c1b40a42920ef75c55b1e42f6d1e6ea3a77d85b5e11cd0"
AS_OF = datetime(2026, 9, 6, tzinfo=timezone.utc)


def _mapping(item):
    return {field.name: getattr(item, field.name) for field in fields(item)}


def main() -> int:
    try:
        bs = importlib.import_module("baostock")
    except ImportError:
        print("BLOCKED optional audit dependency baostock is unavailable")
        return 2
    identity = IndependentSourceIdentityV1.create(
        source_name="baostock", provider_identity=f"BaoStock {getattr(bs, '__version__', '0.9.3')}",
        dataset_kind="trade_calendar", endpoint_identity="query_trade_dates",
        source_independence_rationale="separate provider, protocol, package distribution and calendar interface; not a DataHub wrapper",
        coverage_capability={"start": "1990-01-01", "end": "current", "exchanges": ("SSE",)},
        schema_identity=("calendar_date", "is_trading_day"), retrieved_at=AS_OF,
        policy_version="independent-source-v1",
    )
    login = bs.login()
    if login.error_code != "0":
        print("BLOCKED BaoStock login failed")
        return 2
    try:
        result = bs.query_trade_dates(start_date="2010-01-01", end_date="2025-12-31")
        observations = {}
        while result.error_code == "0" and result.next():
            day, state = result.get_row_data()
            observations[day] = int(state)
        if result.error_code != "0" or len(observations) != 5844:
            print("BLOCKED BaoStock calendar coverage incomplete")
            return 2
    finally:
        bs.logout()
    governance = ROOT / "data" / "phase_1b1" / "governance"
    frozen_path = governance / f"trade-calendar-unresolved-{INVENTORY_ID}.json"
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    requests = IndependentCalendarSampleRequestV1.from_frozen(frozen["samples"], identity)
    comparison = compare_independent_calendar(requests, observations, identity, official_anchors={})
    (governance / f"independent-source-{identity.source_id}.json").write_bytes(canonical_json(_mapping(identity)))
    (governance / f"baostock-calendar-comparison-{comparison.evidence_id}.json").write_bytes(canonical_json(_mapping(comparison)))
    print(f"TIER3_SOURCE_ID={identity.source_id} INDEPENDENCE=PASS COVERAGE=SSE")
    print(f"TOTAL={comparison.total} MATCH={comparison.match_count} MISMATCH={comparison.mismatch_count} UNRESOLVED={comparison.unresolved_count} PROVIDER_ERROR={comparison.provider_error_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
