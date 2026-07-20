#!/usr/bin/env python3
"""
Static checks for snippet-based Markdown policy reuse.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List

from resolve_includes import check_all, plugin_root
from runtime_snippet_binding import RUNTIME_SNIPPET_BINDINGS, resolve_runtime_binding


OUTPUT_PROFILE_SNIPPET = Path("references/_snippets/output-profile.md")
MAX_SNIPPET_LINES = 60
def iter_markdown_files(root: Path) -> Iterable[Path]:
    excluded = {
        ".git",
        ".claude",
        ".worktrees",
        "worktrees",
        "releases",
        "unpacked",
        "archives",
    }
    for path in root.rglob("*.md"):
        if any(part in excluded for part in path.parts):
            continue
        yield path


def main() -> int:
    root = plugin_root()
    errors: List[str] = []

    errors.extend(check_all(root))

    for snippet_rel, expected_consumers in RUNTIME_SNIPPET_BINDINGS.items():
        observed: set[str] = set()
        for base in (root / "agents", root / "skills"):
            for path in base.rglob("*.md"):
                text = path.read_text(encoding="utf-8")
                rel = path.relative_to(root).as_posix()
                if "<!-- include:" in text:
                    errors.append(
                        f"{rel}: build-only include sentinel is incompatible with "
                        "Git-source marketplace installs"
                    )
                if snippet_rel in text and "**Runtime binding.**" in text:
                    observed.add(rel)
        if observed != set(expected_consumers):
            errors.append(
                f"{snippet_rel}: runtime consumers {sorted(observed)} != "
                f"expected {sorted(expected_consumers)}"
            )
        canonical = (root / snippet_rel).resolve()
        for consumer_rel, binding_rel in expected_consumers.items():
            consumer_text = (root / consumer_rel).read_text(encoding="utf-8")
            if binding_rel not in consumer_text or "relative to this" not in consumer_text:
                errors.append(
                    f"{consumer_rel}: missing explicit consumer-relative binding {binding_rel}"
                )
                continue
            try:
                resolved = resolve_runtime_binding(root, consumer_rel, binding_rel)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if resolved != canonical:
                errors.append(
                    f"{consumer_rel}: {binding_rel} resolves to {resolved}, expected {canonical}"
                )

    snippet_path = root / OUTPUT_PROFILE_SNIPPET
    if not snippet_path.is_file():
        errors.append(f"missing snippet {OUTPUT_PROFILE_SNIPPET}")
    else:
        snippet_text = snippet_path.read_text(encoding="utf-8").strip().replace("\r\n", "\n")
        line_count = len(snippet_text.splitlines())
        if line_count > MAX_SNIPPET_LINES:
            errors.append(
                f"{OUTPUT_PROFILE_SNIPPET}: {line_count} lines exceeds {MAX_SNIPPET_LINES}"
            )
        for path in iter_markdown_files(root):
            if path.resolve() == snippet_path.resolve():
                continue
            text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
            if snippet_text in text:
                rel = path.relative_to(root).as_posix()
                errors.append(
                    f"{rel}: duplicates {OUTPUT_PROFILE_SNIPPET}; bind the "
                    "canonical snippet by plugin-root runtime path instead"
                )

    if errors:
        for error in errors:
            print(f"[BLOCKER] {error}", file=sys.stderr)
        return 1
    print("OK snippets are runtime-bound and canonical blocks are not duplicated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
