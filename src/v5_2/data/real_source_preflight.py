from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from v5_2.providers.credentials import CredentialError, load_datahub_credential


Probe = Callable[[str, str, dict[str, object]], dict[str, object]]


@dataclass(frozen=True, slots=True)
class RealSourcePreflightResult:
    source_name: str
    status: str
    reason: str
    credential_present: bool
    transport_security: str


def run_datahub_preflight(
    *, repository_root: Path, env: Mapping[str, str], probe: Probe
) -> RealSourcePreflightResult:
    common = {
        "source_name": "datahubco_tushare_proxy",
        "transport_security": "PLAINTEXT_HTTP",
    }
    try:
        credential = load_datahub_credential(
            env=env,
            env_file=repository_root / ".env",
            repository_root=repository_root,
        )
    except (CredentialError, OSError):
        return RealSourcePreflightResult(
            **common,
            status="BLOCKED",
            reason="MISSING_LOCAL_DATAHUB_API_KEY",
            credential_present=False,
        )
    try:
        payload = probe(
            "trade-cal",
            credential.reveal_for_transport(),
            {
                "exchange": "SSE",
                "start_date": "20250101",
                "end_date": "20250102",
                "limit": 1,
                "offset": 0,
            },
        )
        data = payload.get("data")
        if payload.get("code") != 0 or not isinstance(data, Mapping):
            raise ValueError("invalid probe")
        if credential.is_exposed_in(payload):
            raise ValueError("credential echo")
    except Exception:
        return RealSourcePreflightResult(
            **common,
            status="BLOCKED",
            reason="PROBE_FAILED",
            credential_present=True,
        )
    return RealSourcePreflightResult(
        **common,
        status="PASS",
        reason="ALLOWLISTED_PROBE_SUCCEEDED",
        credential_present=True,
    )
