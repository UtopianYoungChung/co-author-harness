#!/usr/bin/env python3
r"""Portability contract for the domain-native corpus roots.

THE CONTRACT
------------
``corpus_binding.path_roots`` records the roots the pinned corpus was
DECLARED under (`B:/Agents/...`, the maintainer's Windows host). Those strings
are provenance. They are not a portable filesystem locator, because
absoluteness is platform-dependent:

    Path("B:/Agents").is_absolute()   ->  True  on Windows
                                          False on POSIX

An effective root that is not absolute on the running host silently joins
against the CWD, so ``_contained()`` yields a real path naming a corpus nobody
declared -- and the register then reports ``domain-native input absent`` at a
path that could never have existed. The locator was wrong; the diagnosis
accused the corpus. That kept `structural-checks` red on every Linux run from
2026-07-13 (predating PR #11).

So the resolver refuses a non-absolute effective root with ``CorpusRootError``
BEFORE any lookup, and hosts that do not carry the declared corpus bind their
own roots through the explicit override seam
(``resolve_policy(wiki_root=..., workspace_root=...)`` /
``run_all.py --wiki-root/--workspace-root``), which is recorded as
``path_roots_mode=override``.

WHAT THIS SUITE PINS
--------------------
1. Windows-style declared roots, executed on a NON-Windows host, raise
   CorpusRootError -- named, not a mystery "absent input" (skipped on Windows,
   where those roots are genuinely absolute: the case is meaningless there).
2. The same declared roots on Windows ARE absolute -- the platform predicate
   itself, asserted symmetrically so this is a portability contract and not a
   POSIX-only carve-out.
3. The override seam resolves on EVERY host and is recorded as `override`.
4. Overriding with a relative root is refused on every host -- the guard is a
   property of roots, not of the profile.
5. `_contained()` still refuses escapes under an overridden root: containment
   is preserved, not traded away for portability.
6. Provenance survives: the declared roots stay readable in the resolved
   artifact even when effective roots differ.

Run:  python scripts/corpus_root_portability_smoketest.py
Exit: 0 all pass; 1 a check failed.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import reader_accessibility_policy as policy  # noqa: E402
from domain_native_register_smoketest import write_fixture  # noqa: E402

FAILURES: list[str] = []
IS_WINDOWS = os.name == "nt"


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


def case_platform_predicate() -> None:
    """The asymmetry itself, asserted on both sides via pure path types.

    PureWindowsPath/PurePosixPath make the claim testable on ANY host, so this
    is not a "runs only on Linux" assertion about a platform-specific bug.
    """
    declared = "B:/Agents"
    check("declared root is absolute under Windows semantics",
          PureWindowsPath(declared).is_absolute())
    check("declared root is NOT absolute under POSIX semantics",
          not PurePosixPath(declared).is_absolute())
    check("live Path() agrees with this host",
          Path(declared).is_absolute() == IS_WINDOWS,
          f"os.name={os.name}")


def case_declared_roots_on_foreign_host() -> None:
    """Windows-style configured roots executed on a non-Windows host."""
    if IS_WINDOWS:
        print("  SKIP  declared-roots-are-foreign case is meaningless on Windows "
              "(B:/Agents is genuinely absolute here); the POSIX side is pinned "
              "by case_platform_predicate + CI")
        return
    profile = policy.load_profile()
    try:
        policy.resolve_domain_native_register(profile)
    except policy.CorpusRootError as exc:
        msg = str(exc)
        check("declared Windows roots raise CorpusRootError on POSIX", True)
        check("error names the offending root", "workspace_root" in msg or "wiki_root" in msg,
              msg[:80])
        check("error names the host", sys.platform in msg, msg[:80])
        check("error names the override seam", "--wiki-root" in msg or "resolve_policy(" in msg)
        check("error is NOT reported as an absent input",
              "input absent" not in msg, msg[:80])
    except policy.PolicyError as exc:
        check("declared Windows roots raise CorpusRootError on POSIX", False,
              f"got {type(exc).__name__}: {exc}")
    else:
        check("declared Windows roots raise CorpusRootError on POSIX", False,
              "resolution unexpectedly succeeded")


def case_override_resolves_everywhere() -> None:
    """The portable path: bind roots this host can use."""
    profile = policy.load_profile()
    with tempfile.TemporaryDirectory() as td:
        wiki, workspace = write_fixture(Path(td), all_members=True)
        resolved = policy.resolve_domain_native_register(
            profile, wiki_root=wiki, workspace_root=workspace)
        meta = resolved["path_roots"]
        check("override roots resolve on this host", True)
        check("mode recorded as override", meta["path_roots_mode"] == "override",
              meta["path_roots_mode"])
        check("effective roots are the supplied ones",
              meta["effective"]["workspace_root"] == workspace.as_posix())
        check("declared roots preserved as provenance",
              meta["profile_path_roots"]["workspace_root"]
              == profile["domain_native_register"]["corpus_binding"]["path_roots"]["workspace_root"])
        check("pins computed under override", bool(resolved["attestation_view_pin"]))


def case_relative_override_refused() -> None:
    """The guard is a property of ROOTS, not of the profile -- true on Windows too."""
    profile = policy.load_profile()
    try:
        policy.resolve_domain_native_register(
            profile, wiki_root=Path("relative/wiki"),
            workspace_root=Path("relative/workspace"))
    except policy.CorpusRootError as exc:
        check("relative override root refused on this host", True, str(exc)[:60])
    except policy.PolicyError as exc:
        check("relative override root refused on this host", False,
              f"got {type(exc).__name__}: {exc}")
    else:
        check("relative override root refused on this host", False, "accepted")


def case_relative_harness_root_refused() -> None:
    """EVERY anchoring root is gated -- harness_root included.

    The first cut of the gate covered wiki_root and workspace_root only. But
    harness_root anchors contained PACKAGE lookups, so with perfectly good
    wiki/workspace roots and ``harness_root=Path("relative/harness")`` the
    resolver accepted it, rebased it under the CWD, and failed later with

        _MissingInput: domain-native input absent: register_profile:
        C:\\Windows\\System32\\relative\\harness\\references\\policies\\
        reader_accessibility.v1.json

    -- a real path naming a package nobody declared: the exact misleading
    resolution class this suite exists to pin. Reproduced 2026-07-17.

    The refusal must come from the GATE (before any filesystem lookup), which
    is what distinguishes a portability diagnosis from a missing-input one --
    so this asserts the exception TYPE, not merely that something raised.
    """
    profile = policy.load_profile()
    with tempfile.TemporaryDirectory() as td:
        wiki, workspace = write_fixture(Path(td), all_members=True)
        try:
            policy.resolve_domain_native_register(
                profile, wiki_root=wiki, workspace_root=workspace,
                harness_root=Path("relative/harness"))
        except policy.CorpusRootError as exc:
            msg = str(exc)
            check("relative harness_root refused before lookup", True)
            check("harness diagnostic names the offending root",
                  "harness_root" in msg, msg[:70])
            check("harness diagnostic names the host", sys.platform in msg)
            check("harness diagnostic names the override seam",
                  "harness_root=..." in msg or "resolve_policy(" in msg)
            check("harness failure is NOT reported as an absent input",
                  "input absent" not in msg and "register_profile" not in msg,
                  msg[:70])
        except policy.PolicyError as exc:
            check("relative harness_root refused before lookup", False,
                  f"got {type(exc).__name__} (lookup happened): {str(exc)[:60]}")
        else:
            check("relative harness_root refused before lookup", False,
                  "resolution accepted a relative harness_root")


def case_absolute_harness_root_accepted() -> None:
    """The positive complement: gating roots did not break overriding them.

    An explicit ABSOLUTE harness_root must still resolve -- worktrees and
    alternate installs depend on it (the running package root is authority for
    relative package paths even when it differs from path_roots.harness_root).
    Without this, 'refuse relative' could be satisfied by refusing everything.
    """
    profile = policy.load_profile()
    with tempfile.TemporaryDirectory() as td:
        wiki, workspace = write_fixture(Path(td), all_members=True)
        resolved = policy.resolve_domain_native_register(
            profile, wiki_root=wiki, workspace_root=workspace,
            harness_root=ROOT)  # absolute, and a real package root
        meta = resolved["path_roots"]
        check("explicit absolute harness_root still resolves", True)
        check("effective harness_root is the supplied one",
              meta["effective"]["harness_root"] == ROOT.as_posix(),
              meta["effective"]["harness_root"])
        check("pins still computed under an explicit harness root",
              bool(resolved["attestation_view_pin"]))


def case_containment_preserved() -> None:
    """Portability did not buy an escape hatch."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        try:
            policy._contained(root, "../escape.json")
        except policy.PolicyError:
            check("relative escape still refused under an absolute root", True)
        else:
            check("relative escape still refused under an absolute root", False)
        try:
            policy._contained(root, str(root / "abs.json"))
        except policy.PolicyError:
            check("absolute contained-path argument still refused", True)
        else:
            check("absolute contained-path argument still refused", False)


def main() -> int:
    print("corpus_root_portability_smoketest")
    print(f"  host: os.name={os.name} sys.platform={sys.platform}")
    print()
    for fn in (case_platform_predicate, case_declared_roots_on_foreign_host,
               case_override_resolves_everywhere, case_relative_override_refused,
               case_relative_harness_root_refused, case_absolute_harness_root_accepted,
               case_containment_preserved):
        print(f"{fn.__name__}:")
        fn()
        print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)}: {FAILURES}")
        return 1
    print("PASS: corpus roots resolve portably; declared roots stay provenance")
    return 0


if __name__ == "__main__":
    sys.exit(main())
