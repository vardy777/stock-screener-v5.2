from __future__ import annotations

from pathlib import Path

import pytest

from v5_2.providers.credentials import CredentialError, load_tushare_credential


SENTINEL = "SENTINEL_TUSHARE_SECRET"


def test_environment_credential_is_opaque_and_redacted(tmp_path: Path) -> None:
    credential = load_tushare_credential(
        env={"TUSHARE_TOKEN": SENTINEL}, repository_root=tmp_path
    )
    assert str(credential) == "<redacted>"
    assert repr(credential) == "Credential(<redacted>)"
    assert SENTINEL not in str(credential)


def test_repository_local_env_can_supply_token(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(f"TUSHARE_TOKEN={SENTINEL}\n", encoding="utf-8")
    credential = load_tushare_credential(
        env={}, env_file=env_file, repository_root=tmp_path
    )
    assert credential.reveal_for_transport() == SENTINEL


def test_env_file_outside_repository_is_rejected(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    outside = tmp_path / ".env"
    outside.write_text(f"TUSHARE_TOKEN={SENTINEL}\n", encoding="utf-8")
    with pytest.raises(CredentialError, match="repository-local"):
        load_tushare_credential(env={}, env_file=outside, repository_root=repository)


@pytest.mark.parametrize("env", [{}, {"TUSHARE_TOKEN": ""}, {"OTHER_TOKEN": SENTINEL}])
def test_missing_or_empty_tushare_token_fails_without_secret(env: dict[str, str]) -> None:
    with pytest.raises(CredentialError) as caught:
        load_tushare_credential(env=env)
    assert SENTINEL not in str(caught.value)
