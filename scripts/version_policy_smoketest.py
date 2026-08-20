#!/usr/bin/env python3
"""version_policy_smoketest - the manifest is the sole current-version authority.

WRITTEN BEFORE THE IMPLEMENTATION, AND PROVEN TO FAIL AGAINST c945245.

THE CONTRACT (AGENTS.md, clarified 2026-07-17)
----------------------------------------------
`.claude-plugin/plugin.json` is the SOLE authority for the CURRENT version.

  * Descriptive prose must not manually mirror it. A README badge and a
    standalone "## Version `X.Y.Z`" literal are duplicated authority: they
    drift, and the drift is invisible until someone reads the rendered page.
    version-check.py used to REQUIRE both, which is why AGENTS.md:7 ("No prose
    document in this tree asserts a version number") and the checker
    contradicted each other. The checker's own exemption list already encoded
    the right distinction -- it just carved out the README by mistake.
  * Changelog and release-history identifiers ARE permitted: `## v0.29.0 —
    2026-07-14` is a HISTORICAL RECORD of what shipped, not a claim about what
    the current version is. Deleting release headings would destroy history to
    satisfy a rule about authority. They are already exempt from the
    trailer-strip invariant (version-check.py `_VERSION_TRAILER_EXEMPT_PATHS`).
  * manifest <-> marketplace.json parity stays a HARD gate: both files ship
    inside the .plugin ZIP and the loader rejects the install when they
    disagree (v0.10.0 RC shipped exactly that skew).

So: the changelog is validated for STRUCTURE and RELEASE CONSISTENCY, but is
never treated as the authority for the current version.

Run:  python scripts/version_policy_smoketest.py
Exit: 0 all pass; 1 a case failed.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "version-check.py"
MANIFEST_COHERENCE_CHECK = ROOT / "scripts" / "manifest-coherence-check.py"
SSOT_CHECK = ROOT / "scripts" / "ssot-check.py"
FAILURES: list[str] = []

BADGE = ("[![Version](https://img.shields.io/badge/Version-{v}-0366D6?logo=semver"
         "&logoColor=white)](.claude-plugin/plugin.json)")


def check(name: str, ok: bool, detail=None) -> None:
    d = "" if detail in (None, "", []) else f" - {detail}"
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{d}")
    if not ok:
        FAILURES.append(name)


def blockers(out: str) -> list[str]:
    return [l.strip() for l in out.splitlines() if "[BLOCKER]" in l]


def blocked_for(out: str, *needles: str) -> bool:
    """True iff SOME blocker mentions every needle.

    Asserting rc==1 alone is not a test: the current checker exits 1 on these
    fixtures for unrelated reasons (a missing README literal it should not
    require in the first place). A gate that refuses for the wrong reason is
    not a gate, so every negative case names the reason it must refuse for.
    """
    return any(all(n.lower() in b.lower() for n in needles) for b in blockers(out))


def _w(p: Path, t: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="\n")
    return p


def fixture(base: Path, *, manifest="0.29.1", marketplace=None,
            manifest_license="MIT", marketplace_license=None, readme=None,
            changelog=None, marketplace_source=None) -> Path:
    """A minimal plugin root. Defaults are the COMPLIANT shape."""
    root = base / "plug"
    _w(root / ".claude-plugin/plugin.json",
       json.dumps({"name": "co-author-harness-claude", "version": manifest,
                   "description": "d", "keywords": [],
                   "license": manifest_license}, indent=2) + "\n")
    _w(root / ".claude-plugin/marketplace.json",
       json.dumps({"name": "m", "plugins": [
           {"name": "co-author-harness-claude", "source": (
                marketplace_source if marketplace_source is not None else {
                    "source": "url",
                    "url": "https://github.com/UtopianYoungChung/co-author-harness.git",
                }),
             "repository": "https://github.com/UtopianYoungChung/co-author-harness",
             "description": "d",
             "version": marketplace if marketplace is not None else manifest,
            "license": (marketplace_license if marketplace_license is not None
                        else manifest_license)}]},
           indent=2) + "\n")
    _w(root / ".claude-plugin/ssot.yaml", (
        "facts:\n"
        "  manifest_version:\n"
        "    authority:\n"
        "      method: json_field\n"
        "      path: .claude-plugin/plugin.json\n"
        "      field: version\n"
        "    consumers:\n"
        "      - path: .claude-plugin/marketplace.json\n"
        "        method: json_field\n"
        "        field: plugins[*].version\n"
    ))
    _w(root / "README.md", readme if readme is not None else
       "# co-author-harness\n\nSee `.claude-plugin/plugin.json` for the current "
       "version.\n\n## Version\n\nThe authoritative version is recorded in "
       "`.claude-plugin/plugin.json`.\n")
    _w(root / "CHANGELOG.md", changelog if changelog is not None else
       "# Changelog\n\n## v0.29.1 — 2026-07-17\n\nnotes\n\n"
       "## v0.29.0 — 2026-07-14\n\nnotes\n")
    return root


def run(root: Path) -> tuple[int, str]:
    return run_check(CHECK, root)


def run_check(check_path: Path, root: Path) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(check_path), "--plugin-root", str(root)],
                        capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=300)
    return r.returncode, r.stdout + r.stderr


def rewrite_marketplace(root: Path, mutate) -> None:
    path = root / ".claude-plugin/marketplace.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    _w(path, json.dumps(data, indent=2) + "\n")


# ==========================================================================
def case_compliant_readme_passes() -> None:
    """A README with NO version literal must PASS.

    This is the case that inverts today's behaviour: the checker currently
    BLOCKS a README that omits the badge/literal, which is precisely what
    AGENTS.md:7 requires it to omit.
    """
    with tempfile.TemporaryDirectory() as td:
        rc, out = run(fixture(Path(td)))
        check("README with no version literal PASSES", rc == 0,
              str(blockers(out)[:1]))


def case_retired_cursor_manifest_is_refused() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        _w(root / ".cursor-plugin/plugin.json", json.dumps({
            "name": "co-author-harness-claude",
            "version": "0.37.2",
        }, indent=2) + "\n")
        rc, out = run(root)
        check(
            "retired Cursor manifest is REFUSED",
            rc == 1 and blocked_for(out, ".cursor-plugin/plugin.json", "retired"),
            str(blockers(out)[:2]),
        )


def case_readme_badge_is_refused() -> None:
    """A hard-coded badge is duplicated authority -> BLOCKER."""
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td), readme="# h\n\n" + BADGE.format(v="0.29.1") + "\n")
        rc, out = run(root)
        check("README version badge is REFUSED for asserting a version",
              rc == 1 and blocked_for(out, "README", "badge", "assert"),
              str(blockers(out)[:2]))


def case_readme_badge_refused_even_when_matching() -> None:
    """Matching today is not the point: it is duplicated authority tomorrow."""
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td), manifest="0.29.1",
                       readme="# h\n\n" + BADGE.format(v="0.29.1") + "\n")
        rc, out = run(root)
        check("badge refused even when it MATCHES the manifest",
              rc == 1 and blocked_for(out, "README", "badge", "assert"),
              str(blockers(out)[:2]))


def case_readme_version_literal_is_refused() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td), readme="# h\n\n## Version\n\n`0.29.1`\n")
        rc, out = run(root)
        check("README standalone '## Version `X.Y.Z`' literal is REFUSED",
              rc == 1 and blocked_for(out, "README", "assert"),
              str(blockers(out)[:2]))


def case_marketplace_parity_is_a_hard_gate() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td), manifest="0.29.1", marketplace="0.29.0")
        rc, out = run(root)
        check("manifest<->marketplace skew is a HARD BLOCKER",
              rc == 1 and blocked_for(out, "marketplace", "0.29.0"),
              str(blockers(out)[:2]))


def case_marketplace_license_parity_is_a_hard_gate() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td), manifest_license="MIT",
                       marketplace_license="UNLICENSED")
        rc, out = run(root)
        check("manifest<->marketplace license skew is a HARD BLOCKER",
              rc == 1 and blocked_for(out, "marketplace", "license",
                                      "UNLICENSED", "MIT"),
              str(blockers(out)[:2]))


def case_codex_root_relative_marketplace_source_is_refused() -> None:
    """Claude accepts './' here; Codex cannot resolve a root plugin from it."""
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td), marketplace_source="./")
        rc, out = run(root)
        check("root-relative marketplace source is REFUSED for Codex compatibility",
              rc == 1 and blocked_for(out, "marketplace", "Codex", "root"),
              str(blockers(out)[:2]))


def case_remote_url_source_remains_a_parity_consumer() -> None:
    """Changing source shape must not make version parity silently disappear."""
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td), manifest="0.29.1", marketplace="0.29.0")
        rc, out = run(root)
        check("remote URL self-entry remains under manifest version parity",
              rc == 1 and blocked_for(out, "marketplace", "0.29.0"),
              str(blockers(out)[:2]))


def case_remote_url_source_must_match_repository() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td), marketplace_source={
            "source": "url", "url": "https://github.com/example/wrong.git"})
        rc, out = run(root)
        check("remote URL source must match repository metadata",
              rc == 1 and blocked_for(out, "different repositories"),
              str(blockers(out)[:2]))


def case_manifest_entry_cardinality_fails_closed() -> None:
    variants = {
        "missing": lambda data: data.__setitem__("plugins", []),
        "renamed": lambda data: data["plugins"][0].__setitem__("name", "other-plugin"),
        "duplicate": lambda data: data["plugins"].append(dict(data["plugins"][0])),
    }
    checks = (CHECK, MANIFEST_COHERENCE_CHECK, SSOT_CHECK)
    for variant, mutate in variants.items():
        with tempfile.TemporaryDirectory() as td:
            root = fixture(Path(td))
            rewrite_marketplace(root, mutate)
            for check_path in checks:
                rc, out = run_check(check_path, root)
                check(
                    f"{check_path.name} refuses {variant} manifest entry",
                    rc == 1 and "exactly one" in out.lower(),
                    f"rc={rc} {out[-180:]}",
                )


def case_remote_url_source_requires_repository_and_no_path() -> None:
    variants = {
        "missing repository": lambda data: data["plugins"][0].pop("repository"),
        "path-bearing URL": lambda data: data["plugins"][0]["source"].__setitem__(
            "path", "./"
        ),
        "unsupported source type": lambda data: data["plugins"][0].__setitem__(
            "source", {
                "source": "git-subdir",
                "url": "https://github.com/UtopianYoungChung/co-author-harness.git",
                "path": ".",
            }
        ),
    }
    for variant, mutate in variants.items():
        with tempfile.TemporaryDirectory() as td:
            root = fixture(Path(td))
            rewrite_marketplace(root, mutate)
            rc, out = run(root)
            check(f"marketplace source refuses {variant}",
                  rc == 1 and blocked_for(out, "INVALID_SOURCE_FORMAT"),
                  str(blockers(out)[:2]))


def case_changelog_headings_are_permitted() -> None:
    """Historical release headings must NOT be treated as a violation."""
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td), changelog=(
            "# Changelog\n\n## v0.29.1 — 2026-07-17\n\nn\n\n"
            "## v0.29.0 — 2026-07-14\n\nn\n\n## v0.28.0 — 2026-07-01\n\nn\n"))
        rc, out = run(root)
        check("historical changelog headings are PERMITTED", rc == 0,
              str(blockers(out)[:1]))


def case_changelog_is_not_current_version_authority() -> None:
    """A changelog lagging the manifest must not BLOCK.

    The manifest is the authority; the changelog is history. Today this is a
    BLOCKER, which makes the changelog a competing authority.
    """
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td), manifest="0.29.1", changelog=(
            "# Changelog\n\n## v0.29.0 — 2026-07-14\n\nnotes\n"))
        rc, out = run(root)
        check("changelog lagging the manifest is NOT a blocker", rc == 0,
              str(blockers(out)[:1]))


def case_changelog_structure_is_still_validated() -> None:
    """Not authoritative != unvalidated: duplicates are a real defect."""
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td), changelog=(
            "# Changelog\n\n## v0.29.1 — 2026-07-17\n\nn\n\n"
            "## v0.29.1 — 2026-07-16\n\nduplicate release id\n"))
        rc, out = run(root)
        check("duplicate changelog release heading is REFUSED",
              rc == 1 and blocked_for(out, "duplicate"), str(blockers(out)[:2]))


def case_changelog_ordering_is_validated() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td), changelog=(
            "# Changelog\n\n## v0.28.0 — 2026-07-01\n\nn\n\n"
            "## v0.29.1 — 2026-07-17\n\nout of order\n"))
        rc, out = run(root)
        check("out-of-order changelog releases are REFUSED",
              rc == 1 and blocked_for(out, "order"), str(blockers(out)[:2]))


def case_four_component_hotfix_is_not_a_duplicate() -> None:
    """`v0.7.4.1` and `v0.7.4` are DIFFERENT releases.

    Regression for a bug in this very checker, found by running it against the
    real CHANGELOG: a `v(\\d+\\.\\d+\\.\\d+)` pattern captures "0.7.4" out of
    "v0.7.4.1" and reports a duplicate that does not exist. Acting on that
    would have meant deleting a real hotfix release record to satisfy a
    parsing bug -- history destroyed to please a check.
    """
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td), manifest="0.29.1", changelog=(
            "# Changelog\n\n## v0.29.1 — 2026-07-17\n\nn\n\n"
            "## v0.7.4.1 — 2026-04-21\n\nhotfix\n\n"
            "## v0.7.4 — 2026-04-21\n\nrelease\n"))
        rc, out = run(root)
        check("v0.7.4.1 and v0.7.4 are not a duplicate", rc == 0,
              str(blockers(out)[:2]))


def case_four_component_ordering() -> None:
    """A hotfix sorts ABOVE its base release."""
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td), manifest="0.29.1", changelog=(
            "# Changelog\n\n## v0.29.1 — 2026-07-17\n\nn\n\n"
            "## v0.7.4 — 2026-04-21\n\nrelease\n\n"
            "## v0.7.4.1 — 2026-04-21\n\nhotfix listed after its base\n"))
        rc, out = run(root)
        check("hotfix listed below its base release is REFUSED (ordering)",
              rc == 1 and blocked_for(out, "order"), str(blockers(out)[:2]))


def case_real_changelog_is_accepted() -> None:
    """The repository's own CHANGELOG must satisfy the checker.

    A structure rule that the real corpus fails is a rule that is wrong about
    the corpus, not a corpus that is wrong about the rule -- unless the defect
    is real. This anchors the fixtures to reality.
    """
    rc, out = run(ROOT)
    check("the repository's real CHANGELOG passes structure validation",
          not any("CHANGELOG" in b for b in blockers(out)),
          str([b for b in blockers(out) if "CHANGELOG" in b][:2]))


def case_missing_changelog_is_refused() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td), changelog="# Changelog\n\nno releases here\n")
        rc, out = run(root)
        check("changelog with no release heading is REFUSED",
              rc == 1 and blocked_for(out, "release heading"),
              str(blockers(out)[:2]))


def case_alternate_version_assertions_are_refused() -> None:
    """A policy that only knows two spellings is a policy about two spellings.

    The refusal caught an exact, case-sensitive `![Version](...Version-X.Y.Z-)`
    badge and a backticked ``## Version `X.Y.Z` ``. Everything else sailed
    through: a lowercase `![version]` badge, a `Build`/`Release`-labelled
    shields badge, `## Current version` followed by a bare literal, a bolded
    `**Version:** 0.29.1`. Each asserts the current version in prose just as
    hard as the two spellings that were caught -- the gate was refusing a
    FORMAT, not a claim, and the next drift will be written in whatever format
    nobody enumerated.
    """
    for label, body in (
        ("lowercase shields badge",
         "# X\n\n![version](https://img.shields.io/badge/version-0.29.1-blue)\n"),
        ("Release-labelled shields badge",
         "# X\n\n![Release](https://img.shields.io/badge/Release-0.29.1-green)\n"),
        ("## Current version + bare literal",
         "# X\n\n## Current version\n\n0.29.1\n"),
        ("bolded **Version:** literal",
         "# X\n\n**Version:** 0.29.1\n"),
        ("plain `Version: X.Y.Z` line",
         "# X\n\nVersion: 0.29.1\n"),
        # v-prefixed badge VALUE -- `Version-v0.29.1-` rather than `Version-0.29.1-`.
        ("v-prefixed shields badge value",
         "# X\n\n![Version](https://img.shields.io/badge/Version-v0.29.1-blue)\n"),
        ("v-prefixed lowercase badge value",
         "# X\n\n![build](https://img.shields.io/badge/build-v0.29.1-blue)\n"),
        # Ordinary prose. The gate refused headings, badges and `Key: value`
        # lines -- i.e. the SHAPES someone thought of -- while a sentence
        # asserting the same fact walked through. A claim is a claim whatever
        # grammar carries it.
        ("prose claim 'The current version is X'",
         "# X\n\nThe current version is 0.29.1.\n"),
        ("prose claim 'the plugin version is vX'",
         "# X\n\nToday the plugin version is v0.29.1, which you can rely on.\n"),
        ("prose claim 'ships version X'",
         "# X\n\nThis package ships version 0.29.1 of the harness.\n"),
    ):
        with tempfile.TemporaryDirectory() as td:
            rc, out = run(fixture(Path(td), readme=body))
            check(f"README {label} is REFUSED",
                  rc == 1 and blocked_for(out, "README"),
                  f"rc={rc} {str(blockers(out) or '<no blocker>')[:56]}")


def case_legitimate_readme_prose_is_not_overmatched() -> None:
    """The other half of the claim: what must NOT be refused.

    Without this, "refuse version assertions" is satisfiable by refusing every
    README that mentions a number -- and the release-history table and the
    manifest-link prose, which this policy exists to PRESERVE, would be the
    first casualties. A rule that cannot say yes is not enforcing a distinction.
    """
    for label, body in (
        ("manifest-link prose (no numeric mirror)",
         "# X\n\n## Version\n\nThe current version is recorded in "
         "[`.claude-plugin/plugin.json`](.claude-plugin/plugin.json), which is "
         "its sole authority.\n"),
        ("release-history table",
         "# X\n\n## Version\n\n| Release | Date | Notes |\n|---|---|---|\n"
         "| v0.29.0 | 2026-07-14 | census parity |\n"
         "| v0.15.0 | 2026-06-01 | stage x profile |\n"),
        ("release-history headings with dates",
         "# X\n\n## v0.29.0 — 2026-07-14\n\n- shipped\n\n"
         "## v0.15.0 — 2026-06-01\n\n- shipped\n"),
        ("historical narrative",
         "# X\n\nIn v0.15.0 the badge and the literal drifted apart, which is "
         "why the manifest is now the sole authority.\n"),
        ("a non-version badge",
         "# X\n\n![CI](https://img.shields.io/badge/CI-passing-green)\n"),
    ):
        with tempfile.TemporaryDirectory() as td:
            rc, out = run(fixture(Path(td), readme=body))
            check(f"README {label} PASSES", rc == 0,
                  f"rc={rc} {str(blockers(out))[:64]}")


def case_malformed_release_heading_is_refused() -> None:
    """A heading the extractor cannot parse is not a heading that is not there.

    `extract_changelog_releases` silently skips any `## v...` line outside the
    accepted 2-4 component shape. So `## v1.2.3.4.5 — 2026-01-01` vanished, the
    remaining releases validated fine, and the check reported a well-formed
    changelog while a malformed release record sat in it. Silence on
    unparseable input is the failure mode this whole round is about: the
    checker did not disagree with the file, it failed to see it.
    """
    with tempfile.TemporaryDirectory() as td:
        rc, out = run(fixture(Path(td), changelog=(
            "# Changelog\n\n"
            "## v0.29.1 — 2026-07-17\n\n- ok\n\n"
            "## v1.2.3.4.5 — 2026-01-02\n\n- malformed identifier\n\n"
            "## v0.29.0 — 2026-07-14\n\n- ok\n")))
        check("malformed release-like heading is REFUSED",
              rc == 1 and blocked_for(out, "CHANGELOG", "malformed"),
              f"rc={rc} {str(blockers(out) or '<no blocker>')[:56]}")


def case_ssot_registry_agrees_with_the_ruling() -> None:
    """The live version authority and generic host identity must agree."""
    authority = json.loads((ROOT / "version.json").read_text(encoding="utf-8"))
    host = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    check(
        "version.json agrees with root plugin.json on identity fields",
        all(authority.get(key) == host.get(key) for key in ("name", "version", "license")),
        "root plugin identity drifted from version.json",
    )

    # timeout matches `run()`. Without it a hang in ssot-check.py hangs this
    # suite, and a suite that hangs takes CI with it -- an unbounded wait is not
    # a slow pass, it is a run with no verdict at all.
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "ssot-check.py")],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(ROOT), timeout=300)
    check("ssot-check.py passes on the real repository", r.returncode == 0,
          f"ssot-check.py exit {r.returncode}: {(r.stdout or '')[-200:]}")


def main() -> int:
    print("version_policy_smoketest")
    print("  contract: the manifest is the sole CURRENT-version authority;")
    print("            changelog/release identifiers are historical records.")
    print()
    for fn in (case_compliant_readme_passes,
               case_retired_cursor_manifest_is_refused,
               case_readme_badge_is_refused,
               case_readme_badge_refused_even_when_matching,
               case_readme_version_literal_is_refused,
               case_marketplace_parity_is_a_hard_gate,
               case_marketplace_license_parity_is_a_hard_gate,
               case_codex_root_relative_marketplace_source_is_refused,
               case_remote_url_source_remains_a_parity_consumer,
               case_remote_url_source_must_match_repository,
               case_manifest_entry_cardinality_fails_closed,
               case_remote_url_source_requires_repository_and_no_path,
               case_changelog_headings_are_permitted,
               case_changelog_is_not_current_version_authority,
               case_changelog_structure_is_still_validated,
               case_changelog_ordering_is_validated,
               case_four_component_hotfix_is_not_a_duplicate,
               case_four_component_ordering,
               case_real_changelog_is_accepted,
               case_missing_changelog_is_refused,
               case_alternate_version_assertions_are_refused,
               case_legitimate_readme_prose_is_not_overmatched,
               case_malformed_release_heading_is_refused,
               case_ssot_registry_agrees_with_the_ruling):
        print(f"{fn.__name__}:")
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            check(fn.__name__, False, f"raised {type(exc).__name__}: {exc}")
        print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)}: {FAILURES}")
        return 1
    print("PASS: the manifest is the sole current-version authority")
    return 0


if __name__ == "__main__":
    sys.exit(main())
