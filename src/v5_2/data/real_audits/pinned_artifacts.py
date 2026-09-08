from __future__ import annotations

import json
import hashlib
from pathlib import Path


def document_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def load_pinned_json(path: Path, *, schema_version: str, identity_field: str,
                     expected_identity: str) -> dict:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if artifact.get("schema_version") != schema_version:
        raise ValueError("pinned artifact schema mismatch")
    if artifact.get(identity_field) != expected_identity:
        raise ValueError("pinned artifact identity mismatch")
    return artifact
