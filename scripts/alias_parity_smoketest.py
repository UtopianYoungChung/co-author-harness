#!/usr/bin/env python3
"""Smoketest for public-stage and compatibility-entrypoint routing.

Asserts that for every public/compatibility pair:
  (1) both `skills/<name>/SKILL.md` files exist and parse;
  (2) public skills are user-invocable and compatibility skills are hidden;
  (3) both names appear in `references/SKILL_REGISTRY.md`;
  (4) only public names appear in the `skills/plugin-commands/SKILL.md` catalog;
  (5) the public SKILL.md owns the public vocabulary and names its
      compatibility body;
  (6) the compatibility skill identifies itself as such;
  (7) the capability registry exposes exactly the public member as public;
  (8) legacy Ph2 remains a compatibility router to /run-iterate refine, not
      a new public stage alias;
  (9) legacy stability remains a compatibility router to /run-iterate
      profile=stability, not a peer public stage.

This test is structural -- it does not invoke the workflows. It guarantees
the dispatch surface resolves through the old and new names before any
host-side routing test.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = HERE.parent

STAGE_PAIRS = [
    # (public stage entrypoint, compatibility body)
    ("run-draft", "run-phase-1"),
    ("run-iterate", "run-phase-3"),
    ("run-finalize", "run-phase-4"),
]
PH2_LEGACY = "run-phase-2"
STABILITY_LEGACY = "run-phase-3-stability"


def _read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        raise AssertionError(f"{path}: no YAML frontmatter")
    return yaml.safe_load(m.group(1)) or {}


def _read_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^---\n.*?\n---\s*(.*)$", text, re.S)
    return m.group(1) if m else text


def test_canonical_and_alias_skill_files_exist() -> None:
    for public, compatibility in STAGE_PAIRS:
        for name in (public, compatibility):
            path = PLUGIN_ROOT / "skills" / name / "SKILL.md"
            assert path.is_file(), f"missing skill: {path}"
            fm = _read_frontmatter(path)
            assert fm.get("name") == name, (
                f"{path}: frontmatter name={fm.get('name')!r} != {name!r}"
            )


def test_public_visible_and_compatibility_hidden() -> None:
    for public, compatibility in STAGE_PAIRS:
        public_fm = _read_frontmatter(PLUGIN_ROOT / "skills" / public / "SKILL.md")
        compatibility_fm = _read_frontmatter(
            PLUGIN_ROOT / "skills" / compatibility / "SKILL.md"
        )
        assert public_fm.get("user-invocable", True) is True
        assert compatibility_fm.get("user-invocable") is False


def test_both_names_in_skill_registry() -> None:
    registry = (PLUGIN_ROOT / "references" / "SKILL_REGISTRY.md").read_text(
        encoding="utf-8"
    )
    for public, compatibility in STAGE_PAIRS:
        for name in (public, compatibility):
            pat = re.compile(rf"^###\s+SK-\d+\.\s+`{re.escape(name)}`", re.MULTILINE)
            assert pat.search(registry), (
                f"SKILL_REGISTRY.md has no `### SK-N. \\`{name}\\`` heading"
            )


def test_only_public_names_in_plugin_commands_catalog() -> None:
    catalog = (PLUGIN_ROOT / "skills" / "plugin-commands" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    for public, compatibility in STAGE_PAIRS:
        public_pat = re.compile(rf"^\|\s*`/{re.escape(public)}`\s*\|", re.MULTILINE)
        compatibility_pat = re.compile(
            rf"^\|\s*`/{re.escape(compatibility)}`\s*\|", re.MULTILINE
        )
        assert public_pat.search(catalog), f"plugin-commands catalog has no `/{public}` row"
        assert not compatibility_pat.search(catalog), (
            f"plugin-commands catalog exposes hidden compatibility skill `/{compatibility}`"
        )


def test_public_body_owns_vocabulary_and_names_compatibility_body() -> None:
    for public, compatibility in STAGE_PAIRS:
        body = _read_body(PLUGIN_ROOT / "skills" / public / "SKILL.md")
        assert compatibility in body, (
            f"public `{public}` SKILL body must mention compatibility body "
            f"`{compatibility}` verbatim"
        )
        assert re.search(r"\bpublic\b", body, re.IGNORECASE), (
            f"public `{public}` SKILL body must identify the public surface"
        )
        fm = _read_frontmatter(PLUGIN_ROOT / "skills" / public / "SKILL.md")
        desc = str(fm.get("description", ""))
        assert not desc.startswith("Alias for /"), (
            f"public `{public}` description must not identify itself as an alias"
        )


def test_compatibility_surfaces_are_explicit() -> None:
    for public, compatibility in STAGE_PAIRS:
        path = PLUGIN_ROOT / "skills" / compatibility / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        assert "compatibility" in text.lower(), (
            f"{path}: legacy surface must identify itself as compatibility"
        )
        assert public in text, f"{path}: must route readers to `{public}`"


def test_capability_exposure_matches_public_ownership() -> None:
    registry = yaml.safe_load(
        (PLUGIN_ROOT / "references" / "capabilities.yaml").read_text(encoding="utf-8")
    )["capabilities"]
    for public, compatibility in STAGE_PAIRS:
        assert registry[public]["exposure"] == "public"
        assert registry[compatibility]["exposure"] == "compatibility"


def test_ph2_legacy_surface_routes_to_iterate_refine() -> None:
    """The Ph2 name is retained only for compatibility after PR-3b.4."""
    assert (PLUGIN_ROOT / "skills" / PH2_LEGACY / "SKILL.md").is_file(), (
        f"legacy {PH2_LEGACY} skill went missing"
    )
    skill = (PLUGIN_ROOT / "skills" / PH2_LEGACY / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "compatibility" in skill.lower(), "skill must say compatibility"
    assert "run-iterate" in skill, "skill must route to run-iterate"
    assert "refine" in skill, "skill must route with refine profile"


def test_run_phase_3_stability_routes_to_iterate_stability() -> None:
    """Stability is now an /run-iterate profile with a hidden legacy skill."""
    assert (PLUGIN_ROOT / "skills" / STABILITY_LEGACY / "SKILL.md").is_file()
    skill = (PLUGIN_ROOT / "skills" / STABILITY_LEGACY / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "compatibility" in skill.lower(), "skill must say compatibility"
    assert "run-iterate" in skill, "skill must route to run-iterate"
    assert "stability" in skill, "skill must route with stability profile"
    registry = (PLUGIN_ROOT / "references" / "SKILL_REGISTRY.md").read_text(
        encoding="utf-8"
    )
    assert "### SK-31. `run-phase-3-stability`" in registry


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tests = [
        test_canonical_and_alias_skill_files_exist,
        test_public_visible_and_compatibility_hidden,
        test_both_names_in_skill_registry,
        test_only_public_names_in_plugin_commands_catalog,
        test_public_body_owns_vocabulary_and_names_compatibility_body,
        test_compatibility_surfaces_are_explicit,
        test_capability_exposure_matches_public_ownership,
        test_ph2_legacy_surface_routes_to_iterate_refine,
        test_run_phase_3_stability_routes_to_iterate_stability,
    ]
    failures = []
    for t in tests:
        try:
            t()
            print(f"  OK  {t.__name__}")
        except AssertionError as exc:
            failures.append(f"{t.__name__}: {exc}")
            print(f"  FAIL {t.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(f"[BLOCKER] {len(failures)} test(s) failed", file=sys.stderr)
        return 1
    print(f"OK alias_parity_smoketest -- {len(tests)}/{len(tests)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
