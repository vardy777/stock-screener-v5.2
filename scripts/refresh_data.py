from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _default_service_factory():
    from v5_2.refresh.runtime import build_refresh_service
    return build_refresh_service(ROOT)


def _display(result) -> dict[str, object]:
    value = result.as_dict()
    return {
        "TODAY": value["today"], "IS TRADING DAY": value["is_trading_day"],
        "TARGET SESSION": value["target_session"],
        "PREVIOUS APPROVED SESSION": value["latest_approved_session_before_refresh"],
        "MISSING SESSIONS": value["missing_sessions"],
        "REFRESH STATUS": value["refresh_status"],
        "LATEST APPROVED SESSION": value["latest_approved_session"],
        "DATA FRESHNESS": value["freshness_status"],
        "RESEARCH READY": value["research_ready"], "SNAPSHOT ID": value["snapshot_id"],
        "FAILED DATASETS": [key for key, item in value["dataset_results"].items()
                            if item["readiness"] == "NOT_READY"],
        "FAILURE REASONS": value["failure_reasons"],
        "LAST SUCCESSFUL SNAPSHOT": value["previous_successful_snapshot_id"],
        "DATASET RESULTS": value["dataset_results"],
    }


def main(*, service_factory: Callable[[], object] | None = None) -> int:
    service = (service_factory or _default_service_factory)()
    result = service.refresh()
    print(json.dumps(_display(result), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.research_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
