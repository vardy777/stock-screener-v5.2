"""Content-addressed receipt for an explicit private-CAS clean-room run."""

from __future__ import annotations

from dataclasses import dataclass, fields
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from v5_2.data.identity import canonical_json, content_hash
from v5_2.data.private_cas import resolve_cas_root
from v5_2.data.private_corpus_manifest import read_manifest_exact
from v5_2.data.private_corpus_resolver import (
    assert_private_objects_untracked, stage_verified_private_corpus,
)


_SHA = re.compile(r"[0-9a-f]{64}")
_COMMIT = re.compile(r"[0-9a-f]{40}")
_PYTHON_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
_COMMANDS = ("LOCAL_CLONE", "FRESH_ENV", "INSTALL_LOCK", "INSTALL_PROJECT",
             "STAGE_PRIVATE_CAS", "PRIVATE_CAS_REPLAY", "STANDALONE",
             "ORDINARY_CLEAN_ROOM", "BUILD_WHEEL")
_MANIFEST_ID = "0489978b34834817ee0e33dbd46d4e90b86a14e9827f89ba5b93433797c2ddd6"
_INVENTORY_HASH = "a559e02eb8726289bb19c80daa37f78c8041e58bf6884d6c92c382da91ab6536"
_PARTITION_ID = "3c194baf309486c16dd8f7f9e1916f4a1a4af49c9b108bcc06ce693eee615ba9"
_INTEGRATION_ID = "df54c5a80093115d469ec0257127ecd59c304f7c6d440ad2dc8bd4b85d641f67"


@dataclass(frozen=True, slots=True)
class CleanRoomCommandV2:
    name: str
    exit_code: int
    semantic_output_hash: str

    def verify(self) -> bool:
        return (self.name in _COMMANDS and type(self.exit_code) is int
                and self.exit_code == 0 and bool(_SHA.fullmatch(self.semantic_output_hash)))


@dataclass(frozen=True, slots=True)
class CleanRoomEvidenceV2:
    repository_commit: str
    corpus_manifest_id: str
    inventory_hash: str
    python_version: str
    requirements_sha256: str
    wheel_content_hash: str
    commands: tuple[CleanRoomCommandV2, ...]
    reproduced_partition_id: str
    reproduced_integration_id: str
    evidence_id: str

    @classmethod
    def create(cls, *, repository_commit: str, corpus_manifest_id: str,
               inventory_hash: str, python_version: str,
               requirements_sha256: str, wheel_content_hash: str,
               commands: tuple[CleanRoomCommandV2, ...],
               reproduced_partition_id: str,
               reproduced_integration_id: str) -> "CleanRoomEvidenceV2":
        body = dict(repository_commit=repository_commit,
                    corpus_manifest_id=corpus_manifest_id,
                    inventory_hash=inventory_hash, python_version=python_version,
                    requirements_sha256=requirements_sha256,
                    wheel_content_hash=wheel_content_hash, commands=commands,
                    reproduced_partition_id=reproduced_partition_id,
                    reproduced_integration_id=reproduced_integration_id)
        result = cls(**body, evidence_id=content_hash({
            "schema_version": cls.__name__, **body}))
        if not result.verify():
            raise ValueError("clean-room evidence violates frozen contract")
        return result

    def verify(self) -> bool:
        body = {item.name: getattr(self, item.name) for item in fields(self)
                if item.name != "evidence_id"}
        return (bool(_COMMIT.fullmatch(self.repository_commit))
                and self.corpus_manifest_id == _MANIFEST_ID
                and self.inventory_hash == _INVENTORY_HASH
                and bool(_PYTHON_VERSION.fullmatch(self.python_version))
                and all(_SHA.fullmatch(value) for value in (
                    self.requirements_sha256, self.wheel_content_hash))
                and tuple(item.name for item in self.commands) == _COMMANDS
                and all(item.verify() for item in self.commands)
                and self.reproduced_partition_id == _PARTITION_ID
                and self.reproduced_integration_id == _INTEGRATION_ID
                and self.evidence_id == content_hash({
                    "schema_version": type(self).__name__, **body}))


def write_cleanroom_evidence(root: Path, evidence: CleanRoomEvidenceV2) -> Path:
    if not evidence.verify():
        raise ValueError("verified clean-room evidence required")
    path = root / "gate_evidence" / f"cleanroom-{evidence.evidence_id}.json"
    payload = canonical_json(evidence)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("immutable clean-room evidence collision")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return path


def read_cleanroom_evidence_exact(path: Path, expected_id: str) -> CleanRoomEvidenceV2:
    if not _SHA.fullmatch(expected_id) or path.name != f"cleanroom-{expected_id}.json":
        raise ValueError("clean-room evidence ID/path mismatch")
    try:
        raw = path.read_bytes()
        values = json.loads(raw)
        values["commands"] = tuple(CleanRoomCommandV2(**item)
                                    for item in values["commands"])
        evidence = CleanRoomEvidenceV2(**values)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("clean-room evidence unavailable or malformed") from error
    if (evidence.evidence_id != expected_id or not evidence.verify()
            or canonical_json(evidence) != raw):
        raise ValueError("clean-room evidence identity mismatch")
    return evidence


def derive_cleanroom_evidence_exact(source_root: Path) -> CleanRoomEvidenceV2:
    """Build from a fresh local clone and explicit external private CAS.

    No provider invocation or fallback to the source checkout's ignored data.
    Only normalized outcome identities enter the receipt; volatile command
    output, temporary paths and timing never enter its content identity.
    """
    source_root = source_root.resolve()
    cas_root = resolve_cas_root(os.environ, require_explicit=True).resolve()
    if cas_root.is_relative_to(source_root) or source_root.is_relative_to(cas_root):
        raise ValueError("private CAS must be external to source checkout")
    commit = subprocess.run(
        ("git", "-C", str(source_root), "rev-parse", "HEAD"),
        capture_output=True, text=True, check=True).stdout.strip()
    branch = subprocess.run(
        ("git", "-C", str(source_root), "branch", "--show-current"),
        capture_output=True, text=True, check=True).stdout.strip()
    dirty = subprocess.run(
        ("git", "-C", str(source_root), "status", "--porcelain"),
        capture_output=True, text=True, check=True).stdout
    if not _COMMIT.fullmatch(commit) or branch != "phase2a-implementation" or dirty:
        raise ValueError("clean committed feature HEAD required")
    commands: list[CleanRoomCommandV2] = []
    environment = dict(os.environ)
    for key in ("PYTHONPATH", "TUSHARE_TOKEN", "V52_REAL_MONTH_GATES",
                "V52_REAL_MONTH_REPLAY", "V52_PRIVATE_CAS_CLEANROOM"):
        environment.pop(key, None)

    def run(name: str, argv: tuple[str, ...], cwd: Path,
            *, private_replay: bool = False) -> str:
        actual_env = dict(environment)
        if private_replay:
            actual_env["V52_PRIVATE_CAS_CLEANROOM"] = "1"
            actual_env["V5_2_PRIVATE_CAS_ROOT"] = str(cas_root)
        result = subprocess.run(argv, cwd=cwd, env=actual_env,
                                capture_output=True, text=True)
        if result.returncode:
            raise ValueError(f"{name} failed with exit {result.returncode}")
        return result.stdout

    def record(name: str, value: object) -> None:
        commands.append(CleanRoomCommandV2(
            name, 0, content_hash({"command": name, "result": value})))

    with TemporaryDirectory(prefix="v52-phase2b-private-cleanroom-") as temporary:
        room = Path(temporary)
        clone = room / "checkout"
        run("LOCAL_CLONE", ("git", "clone", "--no-local", "--depth", "1",
                            "--single-branch", "--branch", branch,
                            source_root.as_uri(), str(clone)), room)
        cloned_commit = subprocess.run(
            ("git", "-C", str(clone), "rev-parse", "HEAD"),
            capture_output=True, text=True, check=True).stdout.strip()
        if cloned_commit != commit:
            raise ValueError("fresh clone differs from frozen repository commit")
        record("LOCAL_CLONE", cloned_commit)
        venv = room / "venv"
        run("FRESH_ENV", (sys.executable, "-m", "venv", str(venv)), room)
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        version = subprocess.run((str(python), "-c",
                                  "import sys; print('.'.join(map(str,sys.version_info[:3])))"),
                                 cwd=clone, env=environment, capture_output=True,
                                 text=True, check=True).stdout.strip()
        record("FRESH_ENV", version)
        lock_hash = sha256((clone / "requirements.lock").read_bytes()).hexdigest()
        run("INSTALL_LOCK", (str(python), "-m", "pip", "install",
                             "--disable-pip-version-check", "-r",
                             "requirements.lock"), clone)
        record("INSTALL_LOCK", lock_hash)
        run("INSTALL_PROJECT", (str(python), "-m", "pip", "install",
                                "--disable-pip-version-check", "."), clone)
        record("INSTALL_PROJECT", commit)
        manifest = read_manifest_exact(
            clone / "governance" / "phase2b"
            / f"private-corpus-manifest-{_MANIFEST_ID}.json", _MANIFEST_ID)
        if manifest.inventory_hash != _INVENTORY_HASH or manifest.object_count != 44:
            raise ValueError("private corpus inventory differs from frozen contract")
        assert_private_objects_untracked(manifest, clone)
        staged = stage_verified_private_corpus(manifest, cas_root, clone)
        if len(staged) != 44:
            raise ValueError("private CAS staging incomplete")
        record("STAGE_PRIVATE_CAS", manifest.inventory_hash)
        replay_output = run("PRIVATE_CAS_REPLAY", (str(python), "-m", "pytest", "-q",
                                   "tests/labels/test_phase2b_private_cas_cleanroom.py"),
            clone, private_replay=True)
        if not re.search(r"\b1 passed\b", replay_output):
            raise ValueError("private-CAS replay test result absent")
        record("PRIVATE_CAS_REPLAY", (_PARTITION_ID, _INTEGRATION_ID, "1 passed"))
        standalone = run("STANDALONE", (str(python), "scripts/verify_standalone.py"), clone)
        if standalone.count("PASS ") != 5:
            raise ValueError("standalone boundary output incomplete")
        record("STANDALONE", tuple(line.strip() for line in standalone.splitlines()))
        ordinary = run("ORDINARY_CLEAN_ROOM",
                       (str(python), "scripts/clean_room_acceptance.py"), clone)
        try:
            ordinary_result = json.loads(ordinary)
        except json.JSONDecodeError as error:
            raise ValueError("ordinary clean-room output malformed") from error
        if ordinary_result.get("zero_dependency_acceptance") is not True:
            raise ValueError("ordinary clean-room acceptance failed")
        summary = re.search(r"(\d+ passed, \d+ skipped)",
                            ordinary_result.get("test_output", ""))
        if summary is None or any(ordinary_result.get("archive_findings", {}).values()):
            raise ValueError("ordinary clean-room output incomplete")
        record("ORDINARY_CLEAN_ROOM", (summary.group(1),
                                      ordinary_result.get("archives"),
                                      ordinary_result.get("zero_dependency_acceptance")))
        run("BUILD_WHEEL", (str(python), "-m", "build", "--no-isolation"), clone)
        wheels = tuple((clone / "dist").glob("*.whl"))
        if len(wheels) != 1:
            raise ValueError("fresh build must produce exactly one wheel")
        with ZipFile(wheels[0]) as archive:
            wheel_hash = content_hash(tuple(sorted(
                (name, sha256(archive.read(name)).hexdigest())
                for name in archive.namelist() if not name.endswith("/"))))
        record("BUILD_WHEEL", wheel_hash)
    return CleanRoomEvidenceV2.create(
        repository_commit=commit, corpus_manifest_id=manifest.manifest_id,
        inventory_hash=manifest.inventory_hash, python_version=version,
        requirements_sha256=lock_hash, wheel_content_hash=wheel_hash,
        commands=tuple(commands), reproduced_partition_id=_PARTITION_ID,
        reproduced_integration_id=_INTEGRATION_ID)
