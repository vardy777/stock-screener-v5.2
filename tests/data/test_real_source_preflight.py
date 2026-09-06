from __future__ import annotations

from pathlib import Path

from v5_2.data.real_source_preflight import run_datahub_preflight


def test_missing_key_is_blocked_without_network(tmp_path: Path) -> None:
    result = run_datahub_preflight(
        repository_root=tmp_path,
        env={},
        probe=lambda *_: (_ for _ in ()).throw(AssertionError("must not run")),
    )
    assert result.status == "BLOCKED"
    assert result.reason == "MISSING_LOCAL_DATAHUB_API_KEY"
    assert result.source_name == "datahubco_tushare_proxy"
    assert result.credential_present is False


def test_local_env_runs_sanitized_allowlisted_probe(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("DATAHUB_API_KEY=sentinel\n", encoding="utf-8")
    observed = {}

    def probe(endpoint, key, params):
        observed.update(endpoint=endpoint, key=key, params=params)
        return {"code": 0, "data": {"fields": ["exchange"], "items": [], "has_more": False, "count": 0}}

    result = run_datahub_preflight(repository_root=tmp_path, env={}, probe=probe)
    assert result.status == "PASS"
    assert result.reason == "ALLOWLISTED_PROBE_SUCCEEDED"
    assert result.credential_present is True
    assert result.transport_security == "PLAINTEXT_HTTP"
    assert observed == {
        "endpoint": "trade-cal",
        "key": "sentinel",
        "params": {"exchange": "SSE", "start_date": "20250101", "end_date": "20250102", "limit": 1, "offset": 0},
    }
    assert "sentinel" not in repr(result)


def test_probe_failure_is_sanitized(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("DATAHUB_API_KEY=sentinel\n", encoding="utf-8")

    def probe(*_):
        raise RuntimeError("sentinel")

    result = run_datahub_preflight(repository_root=tmp_path, env={}, probe=probe)
    assert result.status == "BLOCKED"
    assert result.reason == "PROBE_FAILED"
    assert "sentinel" not in repr(result)
