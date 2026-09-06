from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


FORBIDDEN_MODULES = {"g1", "v2", "v4", "v5", "v5_1", "shared_core"}
FORBIDDEN_ROOTS = {
    ".hermes", "g1", "v2", "v4", "v5", "v5_1", "shared_core",
    "V5_1_RC1.zip", "V5_1_RC2.zip",
}
IGNORED_PARTS = {".git", ".venv", ".pytest_cache", "__pycache__", "build", "dist"}


def _files(root: Path, areas: tuple[str, ...]):
    for area in areas:
        target = root / area
        if target.is_file():
            yield target
        elif target.is_dir():
            for path in target.rglob("*"):
                ignored = any(part in IGNORED_PARTS or part.endswith(".egg-info") for part in path.parts)
                if path.is_file() and not ignored:
                    yield path


def scan_imports(root: Path) -> list[str]:
    findings: list[str] = []
    source = root / "src" / "v5_2"
    if not source.is_dir():
        return ["src/v5_2: package missing"]
    for path in source.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".", 1)[0])
        for module in sorted(roots & FORBIDDEN_MODULES):
            findings.append(f"{path.relative_to(root)}: forbidden import {module}")
    return findings


def scan_active_paths(root: Path) -> list[str]:
    old_absolute = "c:" + chr(92) + "users" + chr(92) + "lisha" + chr(92) + "stock-screener"
    patterns = {
        old_absolute,
        ".." + "/stock-screener",
        "file" + "://",
        "-" + "e ",
        "@ " + "git+",
    }
    findings: list[str] = []
    for path in _files(root, ("src", "tests", "pyproject.toml", "requirements.lock")):
        try:
            text = path.read_text(encoding="utf-8").lower()
        except UnicodeDecodeError:
            continue
        for pattern in patterns:
            if pattern in text:
                findings.append(f"{path.relative_to(root)}: forbidden active path/dependency {pattern}")
    return findings


def scan_inventory(root: Path) -> list[str]:
    findings = [f"{name}: forbidden root entry" for name in sorted({p.name for p in root.iterdir()} & FORBIDDEN_ROOTS)]
    prohibited = re.compile(r"(?i)(pushplus|register.*task|runtime[_ -]?facts|credentials?)")
    for path in _files(root, ("src", "tests", "scripts")):
        if prohibited.search(path.name):
            findings.append(f"{path.relative_to(root)}: prohibited asset name")
    if (root / ".gitmodules").exists():
        findings.append(".gitmodules: submodules prohibited")
    return findings


def verify(root: Path) -> list[str]:
    root = root.resolve()
    return scan_imports(root) + scan_active_paths(root) + scan_inventory(root)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    findings = verify(root)
    if findings:
        for finding in findings:
            print(f"FAIL {finding}")
        return 1
    print("PASS forbidden imports: 0")
    print("PASS forbidden active paths/dependencies: 0")
    print("PASS prohibited repository inventory: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
