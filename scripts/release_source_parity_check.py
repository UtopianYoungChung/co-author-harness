#!/usr/bin/env python3
"""Require every packaged source member to equal its committed HEAD bytes.

Remote marketplace installs consume the Git source tree directly. The release
archive may add only ``PROVENANCE.json``; build-only rewriting would otherwise
give Claude/Codex marketplace installs different policy from the audited
archive.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Mapping

from package_enumeration import GIT, enumerate_package_files, resolve_head

PROVENANCE = "PROVENANCE.json"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compare_archive(archive: Path, expected: Mapping[str, bytes]) -> list[str]:
    findings: list[str] = []
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        duplicates = sorted(name for name, count in Counter(names).items() if count != 1)
        if duplicates:
            findings.append(f"duplicate archive membership: {duplicates[:8]}")
        actual_names = set(names)
        wanted_names = set(expected) | {PROVENANCE}
        missing = sorted(wanted_names - actual_names)
        extra = sorted(actual_names - wanted_names)
        if missing:
            findings.append(f"archive missing committed members: {missing[:8]}")
        if extra:
            findings.append(f"archive has non-HEAD members beyond {PROVENANCE}: {extra[:8]}")
        mismatches = []
        for name, expected_bytes in expected.items():
            if name in actual_names and names.count(name) == 1:
                actual = bundle.read(name)
                if actual != expected_bytes:
                    mismatches.append(
                        f"{name} archive={_sha(actual)[:12]} HEAD={_sha(expected_bytes)[:12]}"
                    )
        if mismatches:
            findings.append(f"archive source bytes differ from HEAD: {mismatches[:8]}")
    return findings


def committed_population(repo: Path) -> tuple[str, dict[str, bytes]]:
    repo = repo.resolve()
    module_repo = Path(__file__).resolve().parent.parent
    if repo != module_repo:
        raise ValueError(
            f"checker must run from its owning repository: repo={repo}, module={module_repo}"
        )
    commit = resolve_head()
    files, _excluded = enumerate_package_files(commit)
    expected: dict[str, bytes] = {}
    for rel in files:
        proc = subprocess.run(
            [GIT, "-C", str(repo), "show", f"{commit}:{rel}"],
            capture_output=True,
            check=True,
        )
        expected[rel] = proc.stdout
    return commit, expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    try:
        commit, expected = committed_population(Path(args.repo))
        findings = compare_archive(Path(args.archive), expected)
    except (OSError, ValueError, zipfile.BadZipFile, subprocess.SubprocessError) as exc:
        print(f"[ENV] release source parity check failed: {exc}", file=sys.stderr)
        return 2
    print("RELEASE SOURCE PARITY CHECK")
    print(f"- Commit: {commit}")
    print(f"- Expected HEAD members: {len(expected)}")
    print(f"- Blockers: {len(findings)}")
    for finding in findings:
        print(f"[BLOCKER] {finding}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
