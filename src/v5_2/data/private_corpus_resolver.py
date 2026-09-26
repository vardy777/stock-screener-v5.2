"""Verified private CAS transport into a fresh repository checkout."""

from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import subprocess

from v5_2.data.private_cas import put_exact, read_exact
from v5_2.data.private_corpus_manifest import Phase2BPrivateCorpusManifestV1


def _physical_file(path: Path) -> bool:
    return (path.is_file() and not path.is_symlink()
            and path.stat().st_nlink == 1
            and os.path.normcase(os.path.realpath(path))
                == os.path.normcase(os.path.abspath(path)))


def populate_private_cas(manifest: Phase2BPrivateCorpusManifestV1,
                         source_root: Path, cas_root: Path) -> tuple[str, ...]:
    """One-time import from already-approved local exact bytes, never a provider."""
    if not manifest.verify():
        raise ValueError("private corpus manifest is invalid")
    imported = []
    for item in manifest.entries:
        source = source_root / item.logical_role
        if not _physical_file(source):
            raise ValueError("private source is missing or linked")
        raw = source.read_bytes()
        if len(raw) != item.byte_size or sha256(raw).hexdigest() != item.sha256:
            raise ValueError("private source differs from frozen manifest")
        if put_exact(cas_root, raw) != item.sha256:
            raise ValueError("private CAS identity changed")
        if read_exact(cas_root, item.sha256, item.byte_size) != raw:
            raise ValueError("private CAS readback changed")
        imported.append(item.sha256)
    return tuple(imported)


def stage_verified_private_corpus(manifest: Phase2BPrivateCorpusManifestV1,
                                  cas_root: Path, checkout_root: Path
                                  ) -> tuple[Path, ...]:
    """Verify complete exact set, then copy physical bytes at pinned roles."""
    if not manifest.verify():
        raise ValueError("private corpus manifest is invalid")
    payloads = tuple(read_exact(cas_root, item.sha256, item.byte_size)
                     for item in manifest.entries)
    staged = []
    for item, raw in zip(manifest.entries, payloads):
        target = checkout_root / item.logical_role
        target.parent.mkdir(parents=True, exist_ok=True)
        if (os.path.normcase(os.path.realpath(target.parent))
                != os.path.normcase(os.path.abspath(target.parent))):
            raise ValueError("private corpus stage link or junction is forbidden")
        if target.exists() or target.is_symlink():
            if not _physical_file(target) or target.read_bytes() != raw:
                raise ValueError("private corpus stage collision")
        else:
            try:
                descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                                     getattr(os, "O_BINARY", 0), 0o600)
            except FileExistsError as error:
                raise ValueError("private corpus stage collision") from error
            with os.fdopen(descriptor, "wb") as output:
                output.write(raw)
                output.flush()
                os.fsync(output.fileno())
        if (not _physical_file(target) or target.stat().st_size != item.byte_size
                or sha256(target.read_bytes()).hexdigest() != item.sha256):
            raise ValueError("private corpus stage verification failed")
        staged.append(target)
    return tuple(staged)


def assert_private_objects_untracked(manifest: Phase2BPrivateCorpusManifestV1,
                                     checkout_root: Path) -> None:
    """Reject private roles or bytes in the Git index, even if the worktree changed."""
    if not manifest.verify():
        raise ValueError("private corpus manifest is invalid")
    git = ("git", "-C", str(checkout_root))
    result = subprocess.run((*git, "ls-files", "--stage", "-z"),
                            capture_output=True, check=False)
    if result.returncode:
        raise ValueError("Git tracked-object audit unavailable")
    roles = {item.logical_role for item in manifest.entries}
    hashes_by_size: dict[int, set[str]] = {}
    for item in manifest.entries:
        hashes_by_size.setdefault(item.byte_size, set()).add(item.sha256)
    entries = []
    for raw_entry in result.stdout.split(b"\0"):
        if not raw_entry:
            continue
        metadata, raw_name = raw_entry.split(b"\t", 1)
        oid = metadata.split()[1].decode("ascii")
        name = os.fsdecode(raw_name).replace("\\", "/")
        if name in roles:
            raise ValueError("private corpus object is Git-tracked")
        entries.append((oid, name))
    sizes = subprocess.run((*git, "cat-file", "--batch-check"),
                           input=b"".join(oid.encode("ascii") + b"\n"
                                          for oid, _ in entries),
                           capture_output=True, check=False)
    if sizes.returncode or len(sizes.stdout.splitlines()) != len(entries):
        raise ValueError("Git tracked-object audit unavailable")
    for (oid, name), detail in zip(entries, sizes.stdout.splitlines()):
        parts = detail.split()
        if len(parts) != 3 or parts[0].decode("ascii") != oid or parts[1] != b"blob":
            raise ValueError("Git tracked-object audit unavailable")
        size = int(parts[2])
        if size in hashes_by_size:
            blob = subprocess.run((*git, "cat-file", "blob", oid),
                                  capture_output=True, check=False)
            if blob.returncode or len(blob.stdout) != size:
                raise ValueError("Git tracked-object audit unavailable")
            if sha256(blob.stdout).hexdigest() in hashes_by_size[size]:
                raise ValueError("private corpus bytes are Git-tracked")
        path = checkout_root / name
        if path.is_file() and path.stat().st_size in hashes_by_size:
            if sha256(path.read_bytes()).hexdigest() in hashes_by_size[path.stat().st_size]:
                raise ValueError("private corpus bytes are Git-tracked")
