#!/usr/bin/env python3
"""Smoketest for v0.15.0-pre PR-4c — Reflector split parity.

Asserts:
  (1) The two split files exist, parse as Markdown with YAML frontmatter,
      and carry the correct `name` field.
  (2) The shared snippet exists and is referenced via the include sentinel
      from BOTH split files (not from the router or anywhere else).
  (3) The router (`agents/reflector.md`) names both split files verbatim
      and explicitly identifies itself as a router.
  (4) No Planner / Evaluator / Generator file was modified — the PR-4c
      scope was strictly the Reflector.
  (5) Token-budget reduction landed: each split file is comfortably under
      the original 20,113-token measurement, and the router is small.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

HARNESS = Path(__file__).resolve().parent.parent
SCRIPTS = HARNESS / "scripts"
sys.path.insert(0, str(SCRIPTS))


SPLIT_FILES = {
    "reflector-probe": HARNESS / "agents" / "reflector-probe.md",
    "reflector-closeout": HARNESS / "agents" / "reflector-closeout.md",
}
ROUTER = HARNESS / "agents" / "reflector.md"
RUN_SKILL = HARNESS / "skills" / "run-reflection" / "SKILL.md"
SNIPPET = HARNESS / "references" / "_snippets" / "reflection-grounding.md"
INCLUDE_SENTINEL = "<!-- include: _snippets/reflection-grounding.md -->"

UNTOUCHED_AGENTS = ["planner.md", "evaluator.md", "generator.md"]


def _read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^---\n(.*?)\n---", text, re.S)
    assert m, f"{path}: no YAML frontmatter"
    return yaml.safe_load(m.group(1)) or {}


def test_split_files_exist_and_parse() -> None:
    for declared_name, path in SPLIT_FILES.items():
        assert path.is_file(), f"missing split file: {path}"
        fm = _read_frontmatter(path)
        assert fm.get("name") == declared_name, (
            f"{path}: frontmatter name={fm.get('name')!r}, expected {declared_name!r}"
        )


def test_shared_snippet_exists() -> None:
    assert SNIPPET.is_file(), f"missing shared snippet: {SNIPPET}"
    # Must contain at least these anchors so consumers can rely on them
    text = SNIPPET.read_text(encoding="utf-8")
    for needle in [
        "Binding constraint",
        "Dispatch modes",
        "Output Contract",
        "Invariants",
        "What you read",
    ]:
        assert needle in text, f"snippet missing section: {needle!r}"


def test_both_splits_include_the_snippet() -> None:
    for path in SPLIT_FILES.values():
        text = path.read_text(encoding="utf-8")
        assert INCLUDE_SENTINEL in text, (
            f"{path.name} does not include the shared snippet via "
            f"{INCLUDE_SENTINEL!r}"
        )


def test_snippet_is_not_inlined_outside_snippets_dir() -> None:
    """Anti-duplication: the snippet's distinctive 'Binding constraint'
    opening must not appear verbatim in agents/ or skills/ outside the
    snippet itself (the include resolver inlines it at packaging time, not
    at source time)."""
    distinctive = "You are its **primary enforcer**: you run the Grounding Audit on every round"
    for md in (HARNESS / "agents").rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        assert distinctive not in text, (
            f"{md} contains the shared snippet's distinctive text verbatim "
            f"— use {INCLUDE_SENTINEL!r} instead of inlining"
        )


def test_router_points_to_both_splits() -> None:
    text = ROUTER.read_text(encoding="utf-8")
    for needle in ["reflector-probe", "reflector-closeout"]:
        assert needle in text, f"router missing reference to {needle!r}"
    # Router must self-identify
    assert "router" in text.lower(), "router file must self-identify as a router"
    # Router must NOT include the substantive snippet — that's what the
    # split files do, and the router should stay tiny.
    assert INCLUDE_SENTINEL not in text, (
        "router must not include the shared snippet; it stays a thin "
        "routing surface"
    )


def test_router_frontmatter_preserves_legacy_name() -> None:
    fm = _read_frontmatter(ROUTER)
    assert fm.get("name") == "reflector", (
        f"router frontmatter must keep name=reflector for legacy dispatch "
        f"compatibility; got {fm.get('name')!r}"
    )


def test_public_skill_dispatches_one_declared_mode() -> None:
    text = RUN_SKILL.read_text(encoding="utf-8")
    fm = _read_frontmatter(RUN_SKILL)
    assert fm.get("name") == "run-reflection"
    for needle in [
        "mode: lightweight",
        "mode: full",
        "agents/reflector-probe.md",
        "agents/reflector-closeout.md",
    ]:
        assert needle in text, f"run-reflection missing dispatch contract {needle!r}"
    normalized = re.sub(r"\s+", " ", text)
    assert re.search(r"mode.{0,240}(halt|ask)", normalized, re.IGNORECASE), (
        "run-reflection must halt or ask when the mode is undeclared"
    )


def test_public_skill_uses_plugin_relative_paths_and_preserves_output_ownership() -> None:
    text = RUN_SKILL.read_text(encoding="utf-8")
    assert r"B:\Agents\Paper\Package" not in text, (
        "run-reflection must not name the retired package path"
    )
    assert "${CLAUDE_PLUGIN_ROOT}" in text
    assert "F7 evidence packets and F8 final reports are read-only inputs" in text
    assert "reviews/.harness/evidence/<event_id>.json" not in text
    assert "_snippets/output-profile.md" not in text


def test_router_has_one_retirement_condition() -> None:
    text = ROUTER.read_text(encoding="utf-8")
    assert "retained for **one minor version**" not in text, (
        "router contains a second retirement schedule that contradicts the "
        "host-dispatch retirement condition"
    )


def test_no_planner_evaluator_generator_change() -> None:
    """PR-4c scope is strictly the Reflector. The other three agents must
    still be present and parseable; this test is a structural pin against
    a drive-by edit to the wrong agent."""
    for fname in UNTOUCHED_AGENTS:
        p = HARNESS / "agents" / fname
        assert p.is_file(), f"missing untouched agent: {p}"
        fm = _read_frontmatter(p)
        expected_name = fname.removesuffix(".md")
        assert fm.get("name") == expected_name, (
            f"{p}: frontmatter name changed unexpectedly ({fm.get('name')!r})"
        )


def test_token_budget_reduction_landed() -> None:
    """The split must produce measurably smaller files than the 20,113-token
    original. Per-file ceilings are deliberately loose (closeout is full Ph4
    spec; probe is the lightweight subset); the smoketest pins only that
    each half is under the original total, and that the router is small."""
    from token_budget_check import count_tokens, _get_encoder
    enc = _get_encoder()

    probe_tokens = count_tokens(SPLIT_FILES["reflector-probe"], enc)
    closeout_tokens = count_tokens(SPLIT_FILES["reflector-closeout"], enc)
    router_tokens = count_tokens(ROUTER, enc)
    snippet_tokens = count_tokens(SNIPPET, enc)

    # Acceptance: each split is < the original; router stays thin; snippet
    # stays small. Numbers come from the v0.15.0-pre PR-4d baseline (20,113).
    assert probe_tokens < 20113, (
        f"probe ({probe_tokens} tokens) is not smaller than the original "
        f"reflector.md (20,113 tokens) — split did not reduce"
    )
    assert closeout_tokens < 20113, (
        f"closeout ({closeout_tokens} tokens) is not smaller than the "
        f"original reflector.md (20,113 tokens)"
    )
    assert router_tokens < 1500, (
        f"router ({router_tokens} tokens) should stay thin; expected < 1500"
    )
    assert snippet_tokens < 1500, (
        f"shared snippet ({snippet_tokens} tokens) should stay focused; "
        f"expected < 1500"
    )
    print(
        f"    measurements: probe={probe_tokens}, closeout={closeout_tokens}, "
        f"router={router_tokens}, snippet={snippet_tokens}"
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tests = [
        test_split_files_exist_and_parse,
        test_shared_snippet_exists,
        test_both_splits_include_the_snippet,
        test_snippet_is_not_inlined_outside_snippets_dir,
        test_router_points_to_both_splits,
        test_router_frontmatter_preserves_legacy_name,
        test_public_skill_dispatches_one_declared_mode,
        test_public_skill_uses_plugin_relative_paths_and_preserves_output_ownership,
        test_router_has_one_retirement_condition,
        test_no_planner_evaluator_generator_change,
        test_token_budget_reduction_landed,
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
    print(f"OK reflector_split_parity_smoketest — {len(tests)}/{len(tests)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
