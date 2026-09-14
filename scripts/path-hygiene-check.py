#!/usr/bin/env python3
"""
co-author-harness — path-hygiene-check.py

Five path-hygiene checks:

1. **Forbidden local absolute paths.** Blocks maintainer-local absolute
   paths (e.g., `C:\\Users\\young\\`, `/Users/young/`) from install-facing
   files. Original v0.10.x check; preserved.

2. **README-orphan rule (v0.11.0 c8).** Files surfaced as link targets in
   README.md must exist on disk. Surfaces drift between the user-facing
   table of contents and the actual filesystem.

3. **Untracked-files-in-tracked-directories rule (v0.11.0 c8).** Selected
   tracked directories (`releases/`, `tmp/`) should not carry untracked
   working files. Forensic §4 Gap 3: c2.5/c2.6 surfaced three test
   artefacts in `releases/` that the v0.10.x validators failed to detect;
   the resulting clean-up was P4 of the §5 punch list. The new rule
   prevents regression.

4. **No captured build-state files in the plugin manifest directory.** Shell
   listings and error captures are neither package metadata nor release
   receipts; if tracked, the package builder ships them as product bytes.

5. **No package-local project staging.** Project outputs belong under the
   governed workspace root, never under the harness package. The package-local
   lookalike is blocked even when empty so general file tools cannot bypass the
   runtime destination classifier.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List

from package_enumeration import validate_package_membership


BLOCKED_PATTERNS = [
    re.compile(r"C:\\Users\\young\\", re.I),
    re.compile(r"/Users/young/"),
]

# README markdown link patterns we resolve against the filesystem.
README_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

# External link prefixes that are not filesystem paths.
EXTERNAL_LINK_PREFIXES = (
    "http://",
    "https://",
    "mailto:",
    "tel:",
    "ftp://",
    "git@",
    "#",  # in-page anchors
)

# Directories that must remain free of untracked working files.
UNTRACKED_GUARDED_DIRS = ("releases", "tmp")
FORBIDDEN_TRACKED_STATE = (
    ".claude-plugin/_listing.txt",
    ".claude-plugin/_state.txt",
)
FORBIDDEN_PACKAGE_PROJECT_OUTPUT = Path("outputs") / "co-author-harness"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def iter_target_files(plugin_root: Path) -> Iterable[Path]:
    yield plugin_root / "README.md"
    yield plugin_root / "CHANGELOG.md"

    for pattern in ("skills/*/SKILL.md", "agents/*.md", "scripts/*.py", "scripts/*.sh"):
        for path in sorted(plugin_root.glob(pattern)):
            if path.name == "path-hygiene-check.py":
                continue
            yield path


def check_forbidden_paths(plugin_root: Path) -> List[str]:
    findings: List[str] = []
    for path in iter_target_files(plugin_root):
        if not path.exists() or path.is_dir():
            continue
        text = read_text(path)
        for patt in BLOCKED_PATTERNS:
            if patt.search(text):
                findings.append(
                    f"{path}: matched forbidden path pattern '{patt.pattern}'"
                )
    return findings


def check_readme_link_resolution(plugin_root: Path) -> List[str]:
    """Verify every relative link target in README.md exists on disk.

    External URLs (http(s), mailto, tel, ftp, git@) and in-page anchors are
    skipped. A link with a fragment like `docs/foo.md#section` resolves
    against the path component only.
    """
    readme_path = plugin_root / "README.md"
    if not readme_path.exists():
        return []
    text = read_text(readme_path)
    findings: List[str] = []
    seen: set = set()
    for match in README_LINK_PATTERN.finditer(text):
        target = match.group(1).strip()
        if not target or target in seen:
            continue
        seen.add(target)
        if any(target.startswith(prefix) for prefix in EXTERNAL_LINK_PREFIXES):
            continue
        # Strip any fragment / query suffix.
        path_component = target.split("#", 1)[0].split("?", 1)[0]
        if not path_component:
            continue
        candidate = (plugin_root / path_component).resolve()
        if not candidate.exists():
            findings.append(
                f"README.md link target does not resolve: {target} "
                f"(expected at {path_component})"
            )
    return findings


def check_untracked_in_guarded_dirs(plugin_root: Path) -> List[str]:
    """Refuse untracked working files in guarded directories.

    Uses `git status --porcelain` over each guarded directory. Untracked
    entries (status code "??") are blockers; modifications to tracked
    files are not the concern of this check (other validators handle
    diff hygiene).

    If git is not available or the directory is not a git repo, the check
    silently no-ops — it cannot make a determination without git, and
    BLOCKERing on tooling absence would be a false positive.
    """
    findings: List[str] = []
    if not (plugin_root / ".git").exists():
        return findings
    for dirname in UNTRACKED_GUARDED_DIRS:
        guarded = plugin_root / dirname
        if not guarded.is_dir():
            continue
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain", "--", dirname],
                cwd=plugin_root,
                check=False,
                capture_output=True,
                text=True,
                errors="strict", encoding="utf-8",
                timeout=10,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            return findings  # tooling absent — silent skip
        for line in result.stdout.splitlines():
            if not line:
                continue
            # Porcelain v1: first two cols = status; cols 3+ = path.
            status = line[:2]
            path = line[3:].strip()
            if status.startswith("??"):
                findings.append(
                    f"untracked file in guarded directory '{dirname}/': {path} "
                    f"(forensic §4 Gap 3 — c2.5/c2.6 cleanup must not regress)"
                )
    return findings


def check_captured_build_state(plugin_root: Path) -> List[str]:
    return [
        f"captured build-state file must not ship: {rel}"
        for rel in FORBIDDEN_TRACKED_STATE
        if (plugin_root / rel).exists()
    ]


REQUIRED_PACK_IDENTITY = re.compile(
    r"return\s+plugin_root\s*/\s*[\'\"]\.claude-plugin[\'\"]\s*/\s*[\'\"]plugin\.json[\'\"]"
)
IDENTITY_CHECK_SCRIPTS = (
    "scripts/version-check.py",
    "scripts/ssot-check.py",
    "scripts/path-hygiene-check.py",
)


def check_required_pack_identity(plugin_root: Path) -> List[str]:
    """Fail if cheap identity checks still treat the Claude pack as required."""
    findings: List[str] = []
    for rel in IDENTITY_CHECK_SCRIPTS:
        path = plugin_root / rel
        if not path.is_file():
            continue
        body = read_text(path)
        if REQUIRED_PACK_IDENTITY.search(body):
            findings.append(
                f"{rel} treats .claude-plugin/plugin.json as an identity fallback "
                "or required path; version.json is the sole identity authority"
            )
        if re.search(
            r"SOLE authority for the CURRENT version",
            body,
            re.I,
        ) and ".claude-plugin" in body.split("SOLE authority for the CURRENT version", 1)[0][-80:]:
            findings.append(
                f"{rel} still names .claude-plugin as the sole current-version authority"
            )
    return findings


def check_repo_local_project_staging(plugin_root: Path) -> List[str]:
    forbidden = plugin_root / FORBIDDEN_PACKAGE_PROJECT_OUTPUT
    if not forbidden.exists():
        return []
    return [
        "package-local project staging is forbidden: "
        f"{FORBIDDEN_PACKAGE_PROJECT_OUTPUT.as_posix()} exists; project outputs "
        "belong under <governed workspace root>/outputs/co-author-harness/"
        "staging/<work-id>/<run-id>/"
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check for forbidden local absolute paths, README link "
        "drift, untracked files in guarded directories, and package-local "
        "project staging."
    )
    parser.add_argument(
        "--plugin-root",
        default=None,
        help="Plugin root path (defaults to parent directory of this script).",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    plugin_root = Path(args.plugin_root).resolve() if args.plugin_root else script_dir.parent

    blockers: List[str] = []
    blockers.extend(check_forbidden_paths(plugin_root))
    blockers.extend(check_readme_link_resolution(plugin_root))
    blockers.extend(check_untracked_in_guarded_dirs(plugin_root))
    blockers.extend(check_captured_build_state(plugin_root))
    blockers.extend(check_repo_local_project_staging(plugin_root))
    blockers.extend(check_required_pack_identity(plugin_root))
    tracked = subprocess.run(
        ['git', '-C', str(plugin_root), 'ls-files', '-z'],
        capture_output=True, check=False,
    )
    if tracked.returncode == 0:
        try:
            validate_package_membership([
                name.decode('utf-8') for name in tracked.stdout.split(b'\0') if name
            ])
        except ValueError as exc:
            blockers.append(str(exc))

    print("PATH HYGIENE CHECK")
    print(f"- Plugin root: {plugin_root}")
    print(f"- Blockers: {len(blockers)}")
    for item in blockers:
        print(f"[BLOCKER] {item}")

    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
