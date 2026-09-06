from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .core import ContractViolation


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_id(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest}"


class ImmutableFactStore:
    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()

    def _resolve(self, relative: Path | str) -> Path:
        target = (self.root / relative).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise ContractViolation("fact path escapes repository root") from exc
        return target

    def save(self, relative: Path | str, payload: Any) -> Path:
        path = self._resolve(relative)
        raw = canonical_json(payload)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_text(encoding="utf-8") != raw:
                raise ContractViolation("immutable fact collision")
            return path
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(raw, encoding="utf-8")
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_text(encoding="utf-8") != raw:
                raise ContractViolation("immutable fact collision")
        finally:
            temporary.unlink(missing_ok=True)
        return path

    def load(self, relative: Path | str, *, expected: Any | None = None) -> Any:
        path = self._resolve(relative)
        try:
            raw = path.read_text(encoding="utf-8")
            value = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractViolation("immutable fact unreadable") from exc
        if raw != canonical_json(value):
            raise ContractViolation("immutable fact is not canonical")
        if expected is not None and canonical_json(value) != canonical_json(expected):
            raise ContractViolation("immutable fact content mismatch")
        return value
