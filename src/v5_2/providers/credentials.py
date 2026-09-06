from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


class CredentialError(RuntimeError):
    """Credential lookup failed without exposing credential material."""


class Credential:
    __slots__ = ("__value",)

    def __init__(self, value: str) -> None:
        if not value:
            raise CredentialError("TUSHARE_TOKEN is missing or empty")
        self.__value = value

    def __str__(self) -> str:
        return "<redacted>"

    def __repr__(self) -> str:
        return "Credential(<redacted>)"

    def reveal_for_transport(self) -> str:
        """Reveal only at the injected transport call boundary."""
        return self.__value


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator:
            raise CredentialError("invalid environment file")
        values[key.strip()] = value.strip()
    return values


def load_tushare_credential(
    *,
    env: Mapping[str, str] | None = None,
    env_file: Path | None = None,
    repository_root: Path | None = None,
) -> Credential:
    values = os.environ if env is None else env
    token = values.get("TUSHARE_TOKEN", "").strip()
    if not token and env_file is not None:
        root = (repository_root or Path.cwd()).resolve()
        candidate = env_file.resolve()
        try:
            candidate.relative_to(root)
        except ValueError as error:
            raise CredentialError("environment file must be repository-local") from error
        token = _read_env_file(candidate).get("TUSHARE_TOKEN", "").strip()
    return Credential(token)
