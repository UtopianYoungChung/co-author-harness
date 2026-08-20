#!/usr/bin/env python3
"""release_manifest_negative_check - the release paths cannot name one version
and ship another.

Negative cases for the 2026-07-16 repair (scripts/release_manifest_check.py +
HEAD-derived naming in build-release-zip.sh and release-gate.sh Phase 1), each
in a disposable local clone so the user's checkout is never written:

  clean-committed        wrapper end-to-end succeeds (guard)
  duplicate-manifest     archive with a malicious manifest member FIRST and a
                         HEAD-identical one SECOND -> verifier must FAIL on
                         duplicate membership before reading content
  dirty-version-bump     worktree bumps version; requesting the bumped
                         version must FAIL (committed version differs)
  committed-vs-requested requesting a version HEAD does not carry must FAIL
  tamper-same-length     archive authority name mutated, SAME LENGTH
                        (escapes any length check) -> verifier must FAIL
  tamper-license-only    archive authority license mutated -> verifier FAIL
  tamper-missing-member  archive without a manifest member -> verifier FAIL
  gate-dirty-manifest    release-gate --build on a dirty-manifest clone must
                         report BLOCKED and name the dirty-manifest blocker

DELIBERATELY NOT IN THE SUITE UNIVERSE (no fixture marker in the filename):
the gate case runs several minutes and this file exists for the release
tooling, not the fixture corpus.

Run:  python scripts/analysis/release_manifest_negative_check.py [--skip-gate]
Exit: 0 all pass; 1 a check failed; 2 environment error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

MANIFEST_REL = "version.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HARNESS = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(HARNESS / "scripts"))
from package_enumeration import GIT  # noqa: E402
from worktree_paths import sandbox_base  # noqa: E402

BASH_CANDIDATES = [r"C:\Program Files\Git\bin\bash.exe", "bash"]
BASH = next((b for b in BASH_CANDIDATES if Path(b).is_file() or b == "bash"), "bash")

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


def _git(repo: Path, *args: str, check_rc: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run([GIT, "-C", str(repo), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="strict",
                          check=check_rc)


def _rmtree_force(path: Path) -> None:
    def _on_error(func, p, _exc):
        os.chmod(p, 0o700)
        func(p)
    for attempt in range(6):
        try:
            try:
                shutil.rmtree(path, onexc=_on_error)
            except TypeError:
                shutil.rmtree(path, onerror=lambda f, p, e: _on_error(f, p, e))
            return
        except (PermissionError, OSError):
            if attempt == 5:
                raise
            time.sleep(0.05 * (2 ** attempt))


def _make_clone(base: Path, name: str) -> Path:
    repo = base / name
    subprocess.run([GIT, "clone", "--quiet", "--local", str(HARNESS), str(repo)],
                   capture_output=True, check=True)
    head = _git(HARNESS, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "checkout", "--quiet", "--detach", head)
    # Overlay the tooling under test, then commit it so re-exec runs the
    # retargeted builder. Overlay alone leaves the child at source HEAD,
    # which still fail-closes on missing .claude-plugin/plugin.json (rc=3)
    # even when version.json exists. Do not plant a fake pack.
    for rel in ("scripts/build-release-zip.sh", "scripts/build-plugin.py",
                "scripts/release-gate.sh", "scripts/release_manifest_check.py",
                "scripts/worktree_paths.py",
                "scripts/package_enumeration.py",
                "scripts/resolve_includes.py",
                "scripts/destination_capability.py",
                "scripts/qualification_environment.py",
                "scripts/qualification_plane_topology.py"):
        src = HARNESS / rel
        if src.is_file():
            shutil.copy2(src, repo / rel)
            _git(repo, "add", "--", rel)
    staged = _git(repo, "diff", "--cached", "--name-only")
    if staged.stdout.strip():
        _git(repo, "-c", "user.name=sbx", "-c", "user.email=sbx@localhost",
             "-c", "commit.gpgsign=false",
             "commit", "--quiet", "-m", "sbx: packaging tooling under test")
    return repo


def _posix(p: Path) -> str:
    s = str(p).replace("\\", "/")
    if len(s) > 1 and s[1] == ":":
        s = f"/{s[0].lower()}{s[2:]}"
    return s


def _wrapper(repo: Path, version: str, timeout: int = 240) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BASH, "-c",
         f'cd "{_posix(repo)}" && scripts/build-release-zip.sh "{_posix(repo)}" "{version}"'],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout)


def _head_version(repo: Path) -> str:
    blob = _git(repo, "show", "HEAD:version.json").stdout
    return json.loads(blob)["version"]


def _verifier(repo: Path, archive: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(repo / "scripts" / "release_manifest_check.py"),
         str(archive), "--repo", str(repo)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120)


def _tamper(archive: Path, out: Path, mutate, target: str = MANIFEST_REL) -> None:
    """Rebuild `archive` at `out` with one identity manifest mutated
    (or dropped when mutate is None)."""
    with zipfile.ZipFile(archive) as zin, zipfile.ZipFile(out, "w") as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename == target:
                if mutate is None:
                    continue
                data = mutate(data)
            zout.writestr(info, data)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-gate", action="store_true",
                    help="skip the multi-minute release-gate dirty case")
    args = ap.parse_args()

    print("release_manifest_negative_check (disposable clones)")
    # Repo-global base (F1): `HARNESS.parent` is outside the repo only for the
    # primary checkout; under `.worktrees/` it nested clones in the real repo.
    base = Path(tempfile.mkdtemp(prefix="rmnc-",
                                 dir=str(sandbox_base(HARNESS, ".coauthor-rmnc-sbx"))))
    try:
        repo = _make_clone(base, "repo")
        head_version = _head_version(repo)

        print("clean-committed:")
        r = _wrapper(repo, head_version)
        check("wrapper succeeds on clean committed clone", r.returncode == 0,
              f"rc={r.returncode} " + (r.stdout + r.stderr).strip().splitlines()[-1][:80])
        zip_path = repo / "releases" / f"co-author-harness-v{head_version}.zip"
        check("zip named from COMMITTED version", zip_path.is_file(), zip_path.name)

        print("dirty-version-bump:")
        manifest = repo / "version.json"
        original = manifest.read_text(encoding="utf-8")
        bumped = json.loads(original)
        bumped["version"] = "0.99.0"
        manifest.write_text(json.dumps(bumped, indent=2), encoding="utf-8")
        r = _wrapper(repo, "0.99.0")
        check("requesting the dirty-bumped version FAILS", r.returncode == 3,
              f"rc={r.returncode}")
        check("failure names the committed manifest",
              "COMMITTED" in (r.stdout + r.stderr))
        stray = repo / "releases" / "co-author-harness-v0.99.0.zip"
        check("no v0.99.0-named zip produced", not stray.is_file())
        manifest.write_text(original, encoding="utf-8")

        print("committed-vs-requested:")
        r = _wrapper(repo, "9.9.9")
        check("requesting a version HEAD does not carry FAILS", r.returncode == 3,
              f"rc={r.returncode}")

        print("archive tampering (shared verifier):")
        r = _verifier(repo, zip_path)
        check("verifier passes the untampered archive (guard)", r.returncode == 0,
              f"rc={r.returncode}")

        man = json.loads(original)
        name = man["name"]
        mutated_name = ("X" + name[1:]) if name[0] != "X" else ("Y" + name[1:])
        assert len(mutated_name) == len(name)

        def same_length(data: bytes) -> bytes:
            d = json.loads(data)
            d["name"] = mutated_name
            return json.dumps(d, indent=2).encode("utf-8")

        def license_only(data: bytes) -> bytes:
            d = json.loads(data)
            d["license"] = "UNLICENSED"
            return json.dumps(d, indent=2).encode("utf-8")

        def host_description_only(data: bytes) -> bytes:
            d = json.loads(data)
            description = d["description"]
            d["description"] = ("X" if description[0] != "X" else "Y") + description[1:]
            return json.dumps(d, indent=2).encode("utf-8")

        for label, mutate, target in (("same-length name", same_length, MANIFEST_REL),
                                     ("license-only", license_only, MANIFEST_REL),
                                     ("host-description-only", host_description_only, "plugin.json"),
                                     ("missing manifest member", None, MANIFEST_REL)):
            tampered = base / f"tampered-{label.split()[0]}.zip"
            _tamper(zip_path, tampered, mutate, target)
            r = _verifier(repo, tampered)
            check(f"tamper [{label}] blocks", r.returncode == 1,
                  f"rc={r.returncode}")

        # DUPLICATE MEMBERSHIP (review F4). A ZIP may legally carry two
        # members with the same name: `name in namelist()` passes and
        # `z.read(name)` returns whichever one Python kept. With the MALICIOUS
        # manifest first and a HEAD-IDENTICAL manifest second, the old
        # verifier read the matching one and returned 0 while the archive
        # still carried the malicious member -- membership is not identity.
        dup = base / "tampered-duplicate.zip"
        head_manifest = subprocess.run(
            [GIT, "-C", str(repo), "show", "HEAD:version.json"],
            capture_output=True, check=True).stdout
        malicious = json.loads(head_manifest)
        malicious["version"] = "6.6.6"
        malicious["description"] = "MALICIOUS: shipped under a duplicate member"
        with zipfile.ZipFile(zip_path) as zin, zipfile.ZipFile(dup, "w") as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename == MANIFEST_REL:
                    # malicious FIRST, HEAD-identical SECOND
                    zout.writestr(info, json.dumps(malicious, indent=2).encode("utf-8"))
                    zout.writestr(info, head_manifest)
                else:
                    zout.writestr(info, data)
        with zipfile.ZipFile(dup) as z:
            names = z.namelist()
        check("duplicate fixture really carries 2 manifest members (guard)",
              names.count(MANIFEST_REL) == 2, f"count={names.count(MANIFEST_REL)}")
        check("duplicate fixture's read-selected member matches HEAD (guard: "
              "this is what fooled the old verifier)",
              hashlib.sha256(zipfile.ZipFile(dup).read(MANIFEST_REL)).hexdigest()
              == hashlib.sha256(head_manifest).hexdigest())
        r = _verifier(repo, dup)
        check("tamper [duplicate manifest members] blocks", r.returncode == 1,
              f"rc={r.returncode}")
        check("duplicate diagnostic names duplicate membership",
              "duplicate membership" in (r.stdout + r.stderr).lower(),
              (r.stdout + r.stderr).strip().splitlines()[-1][:80] if (r.stdout + r.stderr).strip() else "silent")

        if args.skip_gate:
            print("gate-dirty-manifest: SKIPPED (--skip-gate)")
        else:
            print("gate-dirty-manifest (multi-minute):")
            host_manifest = repo / "plugin.json"
            host_original = host_manifest.read_text(encoding="utf-8")
            d = json.loads(host_original)
            d["description"] = "X" + d["description"][1:]
            host_manifest.write_text(json.dumps(d, indent=2), encoding="utf-8")
            r = subprocess.run(
                [BASH, "-c",
                 f'cd "{_posix(repo)}" && scripts/release-gate.sh --build'],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=900)
            out = r.stdout + r.stderr
            check("gate exits nonzero on dirty manifest", r.returncode != 0,
                  f"rc={r.returncode}")
            check("gate names the dirty-manifest blocker",
                  "worktree manifest differs from HEAD" in out)
            check("gate verdict is BLOCKED", "VERDICT: BLOCKED" in out)
            host_manifest.write_text(host_original, encoding="utf-8")
    finally:
        _rmtree_force(base)
        # sandbox_base() creates the parent; remove it when empty so this
        # suite leaves nothing behind.
        import contextlib
        with contextlib.suppress(OSError):
            base.parent.rmdir()
        print()
        print("  ok     clones removed" if not base.exists()
              else "  ERROR  clone base left behind")
        if base.exists():
            FAILURES.append("clone-teardown")

    if FAILURES:
        print(f"\nFAIL: {len(FAILURES)}: {FAILURES}")
        return 1
    print("\nPASS: release filenames and embedded manifests cannot disagree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
