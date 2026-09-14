import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from v5_2.data.raw_artifacts import RawPayloadArtifactV1
from v5_2.refresh.calendar import CalendarPublicationError, publish_calendar_increment

pytestmark=pytest.mark.skipif(not (Path(__file__).resolve().parents[2]/'data/phase_1b1_2026_extension').is_dir(),reason='repository-local governance artifacts are excluded from clean room')


ROOT = Path(__file__).resolve().parents[2]
APPROVAL = ROOT / "data/phase_1b1_2026_extension/governance/trade_calendar-approval-4a900c7e4f2b171d7adac07088025ca4bb9fb0da13cfa1b15e91eff3dafea601.json"
MANIFEST = ROOT / "data/phase_1b_exit_remediation/governance/trade-calendar-complete-manifest-5f5ba7d0594f5f1e2d40ad43b54a93a303a7d25af8e1104e6c633463076e6486.json"


def prior():
    return json.loads(APPROVAL.read_text(encoding="utf-8")), json.loads(MANIFEST.read_text(encoding="utf-8"))


def raws(malformed=False):
    result = []
    for exchange in ("SSE", "SZSE"):
        rows = [
            {"exchange": exchange, "cal_date": "20260912", "is_open": 0, "pretrade_date": "20260911"},
            {"exchange": exchange, "cal_date": "20260913", "is_open": 0, "pretrade_date": "20260911"},
            {"exchange": exchange, "cal_date": "20260914", "is_open": 1, "pretrade_date": "20260911"},
        ]
        if malformed and exchange == "SZSE": rows.pop()
        result.append(RawPayloadArtifactV1.create(
            request_id=exchange.lower() * 10, page_identity={"offset": 0},
            provider_payload={"rows": rows},
            semantic_metadata={"has_more": False, "total_count": len(rows)},
        ))
    return tuple(result)


def publish(tmp_path, **overrides):
    approval, manifest = prior()
    values = dict(
        output_root=tmp_path, previous_approval=approval, previous_manifest=manifest,
        raws=raws(), receipt_hashes=("r" * 64, "s" * 64),
        missing_dates=(date(2026, 9, 12), date(2026, 9, 13), date(2026, 9, 14)),
        observed_at=datetime(2026, 9, 14, 0, 5, tzinfo=timezone.utc),
        prior_open_sessions=(date(2026, 9, 11),),
    )
    values.update(overrides)
    return publish_calendar_increment(**values)


def test_calendar_valid_raw_publishes_approval_manifest_and_ready_state(tmp_path):
    result = publish(tmp_path)
    assert result.state.readiness.value == "READY"
    assert result.state.latest_approved_session == date(2026, 9, 14)
    assert date(2026, 9, 14) in result.state.completed_sessions
    assert len(list((tmp_path / "governance").glob("*.json"))) == 5
    assert (tmp_path / "trade_calendar-current-state-id.txt").is_file()


def test_calendar_malformed_raw_publishes_nothing(tmp_path):
    with pytest.raises(CalendarPublicationError, match="coverage"):
        publish(tmp_path, raws=raws(malformed=True))
    assert not (tmp_path / "governance").exists()


@pytest.mark.parametrize("invalid", ["tampered", "revoked"])
def test_calendar_invalid_or_revoked_approval_fails_closed(tmp_path, invalid):
    approval, _ = prior()
    if invalid == "tampered":
        approval["coverage_end"] = "2099-01-01"
        with pytest.raises(CalendarPublicationError, match="integrity"):
            publish(tmp_path, previous_approval=approval)
    else:
        with pytest.raises(CalendarPublicationError, match="revoked"):
            publish(tmp_path, revoked_approval_ids=frozenset({approval["approval_id"]}))


def test_calendar_identical_rerun_reuses_same_immutable_publication(tmp_path):
    first = publish(tmp_path)
    second = publish(tmp_path)
    assert first == second
    assert len(list((tmp_path / "governance").glob("*.json"))) == 5
