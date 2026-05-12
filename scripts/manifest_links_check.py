#!/usr/bin/env python3
"""v0.15.0-pre PR-4b — MANIFEST link and CLAUDE.md preservation check.

Verifies two invariants:

(A) Every backticked file reference in `references/MANIFEST.md` that names
    a Markdown file under `references/`, `agents/`, `skills/`, `commands/`,
    or `scripts/` resolves to an existing path.

(B) `references/CLAUDE.md` continues to satisfy the binding-preservation
    guarantees PR-4b made when slimming the prelude:
      * GROUNDING_PROTOCOL.md is named as the always-loaded floor.
      * MANIFEST.md is named as the routing index.
      * The §4 precedence ladder is present with all seven numbered items
        and the closing "When in doubt, name the conflict" line.
      * The §4 note that the Grounding Protocol sits above user instruction
        is preserved.

The check is intentionally narrow: it does not validate ref-file freshness
or routing-table accuracy. Its role is to fail closed on accidental
deletion of the binding-preservation hooks PR-4b relies on.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
MANIFEST = HARNESS / "references" / "MANIFEST.md"
CLAUDE_MD = HARNESS / "references" / "CLAUDE.md"

# Filename patterns we expect to resolve. Conservative: only match tokens
# that look like a real Markdown filename (no spaces, ends in .md or .yaml).
FILENAME_RE = re.compile(r"`([A-Za-z0-9_\-./]+\.(?:md|yaml|json|py))`")

# Plausible roots a backticked filename in MANIFEST could resolve under.
SEARCH_ROOTS = [
    "references", "references/examples", "agents", "skills", "commands",
    "scripts",
]

# Names that don't correspond to a single file in the harness package
# (project-local artifacts, glob patterns, template placeholders). They
# are valid in MANIFEST prose but skipped from path resolution because
# they are created per-project rather than shipped with the package.
SKIP_TOKENS = {
    "_snippets/output-profile.md",   # path resolved via relative prefix
    "_snippets/<name>.md",           # template placeholder
    "agents/<role>.md",              # template placeholder
    "examples/*.md",                 # glob, not a single file
    "research_notes/review/lessons_caise_revision.md",  # cross-project example
    "research_notes/",               # directory reference
    "manuscript/main.md",            # project-local
    # Per-project ledger and round artifacts created by the Planner.
    "phase_state.json",
    "conductor.md",
    "round_program.md",
    "revision_log.md",
    "reviews/graph_overlay_YYYY-MM-DD.md",
}


def _resolve(token: str) -> Path | None:
    """Resolve a token relative to HARNESS, trying each search root."""
    # Strip leading "references/" if present
    norm = token
    for root in SEARCH_ROOTS:
        candidates = [
            HARNESS / norm,
            HARNESS / root / norm,
            HARNESS / root / Path(norm).name,
        ]
        for c in candidates:
            if c.is_file():
                return c
    # Also accept top-level absolute references like "scripts/foo.py" style
    direct = HARNESS / norm
    if direct.is_file():
        return direct
    return None


def check_manifest_links() -> list[str]:
    errors: list[str] = []
    if not MANIFEST.is_file():
        return [f"missing: {MANIFEST}"]
    text = MANIFEST.read_text(encoding="utf-8")
    seen: set[str] = set()
    for m in FILENAME_RE.finditer(text):
        token = m.group(1)
        if token in seen or token in SKIP_TOKENS:
            continue
        seen.add(token)
        # Heuristic: skip tokens that look like a renamed-to-from reference
        # in a parenthetical (e.g. "(renamed from TIER_PROTOCOL.md ...)") —
        # we still want them to resolve if they're alive in the tree, but
        # if they don't we don't fail. Use a positive-list of "must resolve"
        # tokens via filename allowlist below.
        resolved = _resolve(token)
        if resolved is None:
            # Special-case: TIER_PROTOCOL.md is intentionally retired but
            # kept around as a legacy stub; tolerate either presence or
            # absence to avoid coupling this check to a specific decision.
            if token in {"TIER_PROTOCOL.md", "tier_notifications.yaml"}:
                continue
            errors.append(f"MANIFEST.md references unresolved file: `{token}`")
    return errors


REQUIRED_CLAUDE_MD_MENTIONS = [
    ("GROUNDING_PROTOCOL.md", "GROUNDING_PROTOCOL.md must be named in CLAUDE.md"),
    ("MANIFEST.md", "MANIFEST.md must be named in CLAUDE.md (PR-4b routing pointer)"),
]

REQUIRED_PRECEDENCE_LINES = [
    "User's explicit instruction",
    "Venue author guide",
    "Advisor or instructor instruction",
    "Project-specific supplements",
    "Component files",
    "MASTER",
    "Default behavior",
    "When in doubt, name the conflict",
]

REQUIRED_GROUNDING_PRECEDENCE_NOTE_FRAGMENTS = [
    "Grounding Protocol sits",
    "above",
    "precedence ladder",
]


def check_claude_md_preservation() -> list[str]:
    errors: list[str] = []
    if not CLAUDE_MD.is_file():
        return [f"missing: {CLAUDE_MD}"]
    text = CLAUDE_MD.read_text(encoding="utf-8")

    for needle, msg in REQUIRED_CLAUDE_MD_MENTIONS:
        if needle not in text:
            errors.append(f"CLAUDE.md preservation broken: {msg}")

    for line in REQUIRED_PRECEDENCE_LINES:
        if line not in text:
            errors.append(
                f"CLAUDE.md §4 precedence missing required line fragment: {line!r}"
            )

    for fragment in REQUIRED_GROUNDING_PRECEDENCE_NOTE_FRAGMENTS:
        if fragment not in text:
            errors.append(
                f"CLAUDE.md §4 must preserve the Grounding-above-precedence "
                f"note; missing fragment: {fragment!r}"
            )

    return errors


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    errors = check_manifest_links() + check_claude_md_preservation()
    if errors:
        for e in errors:
            print(f"  [BLOCKER] {e}", file=sys.stderr)
        print(f"[BLOCKER] manifest_links_check failed with {len(errors)} issue(s)",
              file=sys.stderr)
        return 1
    print("OK manifest_links_check — MANIFEST links resolve and CLAUDE.md "
          "preservation invariants hold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
