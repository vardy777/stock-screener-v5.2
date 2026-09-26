"""Physical, exact-byte private content-addressed objects; no source fallback."""

from __future__ import annotations

from hashlib import sha256 as sha256_digest
import os
from pathlib import Path
import re
from typing import Mapping


_SHA = re.compile(r"^[0-9a-f]{64}$")


def resolve_cas_root(environ: Mapping[str, str], *, require_explicit: bool = False) -> Path:
    configured = environ.get("V5_2_PRIVATE_CAS_ROOT", "")
    if configured:
        return Path(configured)
    if require_explicit:
        raise ValueError("PRIVATE_CORPUS_UNAVAILABLE: explicit CAS root required")
    local_app_data = environ.get("LOCALAPPDATA", "")
    if not local_app_data:
        raise ValueError("PRIVATE_CORPUS_UNAVAILABLE: CAS root unavailable")
    return Path(local_app_data) / "V5_2" / "private-cas"


def _object_path(root: Path, sha256: str) -> Path:
    if not _SHA.fullmatch(sha256):
        raise ValueError("invalid CAS SHA-256")
    return root / "sha256" / sha256[:2] / sha256


def _require_physical(path: Path) -> None:
    if (os.path.normcase(os.path.realpath(path)) != os.path.normcase(os.path.abspath(path))
            or path.is_symlink()):
        raise ValueError("CAS link or junction is forbidden")
    try:
        metadata = path.stat()
    except OSError as error:
        raise ValueError("PRIVATE_CORPUS_UNAVAILABLE: CAS object missing") from error
    if not path.is_file() or metadata.st_nlink != 1:
        raise ValueError("CAS link or non-file object is forbidden")


def read_exact(root: Path, sha256: str, byte_size: int) -> bytes:
    """Verify physical object, exact size and SHA before releasing bytes."""
    if byte_size < 0:
        raise ValueError("invalid CAS byte size")
    path = _object_path(root, sha256)
    _require_physical(path)
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise ValueError("PRIVATE_CORPUS_UNAVAILABLE: CAS read failed") from error
    if len(payload) != byte_size:
        raise ValueError("CAS object size mismatch")
    if sha256_digest(payload).hexdigest() != sha256:
        raise ValueError("CAS object hash mismatch")
    return payload


def put_exact(root: Path, payload: bytes) -> str:
    """Create once, or verify an existing identical physical object."""
    if not isinstance(payload, bytes):
        raise TypeError("CAS payload must be exact bytes")
    identity = sha256_digest(payload).hexdigest()
    path = _object_path(root, identity)
    path.parent.mkdir(parents=True, exist_ok=True)
    if (os.path.normcase(os.path.realpath(path.parent))
            != os.path.normcase(os.path.abspath(path.parent))):
        raise ValueError("CAS link or junction is forbidden")
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                             getattr(os, "O_BINARY", 0), 0o600)
    except FileExistsError:
        if read_exact(root, identity, len(payload)) != payload:
            raise ValueError("CAS object bytes differ")
        return identity
    with os.fdopen(descriptor, "wb") as target:
        target.write(payload)
        target.flush()
        os.fsync(target.fileno())
    if read_exact(root, identity, len(payload)) != payload:
        raise ValueError("CAS object bytes differ after creation")
    return identity
