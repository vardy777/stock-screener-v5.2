import importlib.util
import json
from datetime import date
from pathlib import Path

from v5_2.refresh.contracts import FreshnessStatus, RefreshResultV1, RefreshStatus


ROOT = Path(__file__).resolve().parents[2]


def load_cli():
    spec = importlib.util.spec_from_file_location("refresh_data", ROOT / "scripts/refresh_data.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Service:
    def __init__(self, result): self.result = result
    def refresh(self): return self.result


def result(ready=True):
    return RefreshResultV1(
        today=date(2026, 9, 14), is_trading_day=True,
        target_session=date(2026, 9, 14), latest_completed_session=date(2026, 9, 14),
        latest_approved_session_before_refresh=date(2026, 9, 11),
        missing_sessions=(date(2026, 9, 14),), dataset_results={},
        refresh_status=RefreshStatus.SUCCESS if ready else RefreshStatus.FAILED,
        latest_approved_session=date(2026, 9, 14) if ready else date(2026, 9, 11),
        freshness_status=FreshnessStatus.CURRENT if ready else FreshnessStatus.FAILED,
        research_ready=ready, snapshot_id="s" * 64 if ready else None,
        previous_successful_snapshot_id="p" * 64, failure_reasons=() if ready else ("STATUS_FAILED",),
    )


def test_cli_serializes_service_result_without_own_refresh_logic(capsys):
    cli = load_cli()
    assert cli.main(service_factory=lambda: Service(result())) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["TARGET SESSION"] == "2026-09-14"
    assert payload["RESEARCH READY"] is True
    assert payload["SNAPSHOT ID"] == "s" * 64


def test_cli_failure_reports_reasons_and_last_snapshot(capsys):
    cli = load_cli()
    assert cli.main(service_factory=lambda: Service(result(False))) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["FAILURE REASONS"] == ["STATUS_FAILED"]
    assert payload["LAST SUCCESSFUL SNAPSHOT"] == "p" * 64
