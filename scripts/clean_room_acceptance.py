from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


IGNORED = {".git", ".venv", ".pytest_cache", "__pycache__", "build", "dist", "*.egg-info"}
FORBIDDEN_PARTS = {".hermes", "g1", "v2", "v4", "v5", "v5_1", "shared_core"}
FORBIDDEN_FILES = {"V5_1_RC1.zip", "V5_1_RC2.zip", ".env"}


def scan_archive(path: Path) -> list[str]:
    findings: list[str] = []
    if path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as handle:
            names = handle.getnames()
    else:
        with zipfile.ZipFile(path) as handle:
            names = handle.namelist()
    for name in names:
        member = PurePosixPath(name)
        parts = set(member.parts)
        lowered = name.lower()
        if parts & FORBIDDEN_PARTS or member.name in FORBIDDEN_FILES:
            findings.append(name)
        elif "runtime_facts" in lowered or "credentials" in lowered or "register_task" in lowered:
            findings.append(name)
    return sorted(findings)


def run(command: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)


def python_in(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def main() -> int:
    source = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    results: dict[str, object] = {"python": sys.version.split()[0]}
    with tempfile.TemporaryDirectory(prefix="v52-clean-room-") as temporary:
        room = Path(temporary) / "source"
        shutil.copytree(
            source,
            room,
            ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__", "build", "dist", "*.egg-info"),
        )
        venv = Path(temporary) / "test-venv"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, env=env)
        py = python_in(venv)
        install_tools = run([str(py), "-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements.lock"], room, env)
        results["clean_room_dependencies"] = install_tools.returncode == 0
        install = run([str(py), "-m", "pip", "install", "--disable-pip-version-check", "."], room, env)
        results["clean_room_install"] = install.returncode == 0
        tests = run([str(py), "-m", "pytest", "-q"], room, env)
        results["clean_room_tests"] = tests.returncode == 0
        results["test_output"] = tests.stdout.strip().splitlines()[-1] if tests.stdout.strip() else tests.stderr.strip()
        if tests.returncode:
            results["test_diagnostics"] = tests.stdout + tests.stderr
        build = run([str(py), "-m", "build", "--no-isolation"], room, env)
        results["build"] = build.returncode == 0
        if build.returncode:
            results["build_diagnostics"] = build.stdout + build.stderr
        archives = sorted((room / "dist").glob("*")) if (room / "dist").exists() else []
        results["archives"] = [path.name for path in archives]
        archive_findings = {path.name: scan_archive(path) for path in archives if path.suffix in {".whl", ".gz", ".zip"}}
        results["archive_findings"] = archive_findings
        wheel = next((path for path in archives if path.suffix == ".whl"), None)
        smoke_venv = Path(temporary) / "smoke-venv"
        subprocess.run([sys.executable, "-m", "venv", str(smoke_venv)], check=True, env=env)
        smoke_py = python_in(smoke_venv)
        wheel_install = run([str(smoke_py), "-m", "pip", "install", "--disable-pip-version-check", str(wheel)], room, env) if wheel else None
        smoke = run([str(smoke_py), "-c", "import v5_2; assert v5_2.RESEARCH_LOCKED and not v5_2.BROKER_ORDERS_ENABLED; print(v5_2.__version__)"], room, env) if wheel_install and wheel_install.returncode == 0 else None
        results["wheel_install"] = bool(wheel_install and wheel_install.returncode == 0)
        results["wheel_smoke"] = bool(smoke and smoke.returncode == 0 and smoke.stdout.strip() == "5.2.0")
        results["old_pythonpath_removed"] = "PYTHONPATH" not in env
    passed = all(
        results.get(key) is True
        for key in ("clean_room_dependencies", "clean_room_install", "clean_room_tests", "build", "wheel_install", "wheel_smoke", "old_pythonpath_removed")
    ) and not any(results.get("archive_findings", {}).values())
    results["zero_dependency_acceptance"] = passed
    print(json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
