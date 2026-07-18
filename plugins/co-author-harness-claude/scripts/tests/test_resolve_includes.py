"""Unit tests for resolve_includes.py — covers PR-1 hardening #3.

Verifies: _snippets/ prefix resolution under references/, recursive include
cycle detection, missing-file error surface, and idempotence on includes-free
files.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
sys.path.insert(0, str(SCRIPTS))

from resolve_includes import (  # noqa: E402
    resolve_include_path,
    resolve_includes_in_text,
)


def _make_tree(root: Path) -> None:
    (root / "references" / "_snippets").mkdir(parents=True)
    (root / "skills" / "demo").mkdir(parents=True)


def test_snippets_prefix_resolves_under_references() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)
        snip = root / "references" / "_snippets" / "foo.md"
        snip.write_text("FOO", encoding="utf-8")
        source = root / "skills" / "demo" / "SKILL.md"
        source.write_text("<!-- include: _snippets/foo.md -->", encoding="utf-8")
        rendered = resolve_includes_in_text(source.read_text(encoding="utf-8"), source, root)
        assert "FOO" in rendered, rendered


def test_missing_include_raises() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)
        source = root / "skills" / "demo" / "SKILL.md"
        source.write_text("<!-- include: _snippets/missing.md -->", encoding="utf-8")
        try:
            resolve_includes_in_text(source.read_text(encoding="utf-8"), source, root)
        except FileNotFoundError:
            return
        raise AssertionError("expected FileNotFoundError")


def test_recursive_include_cycle_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)
        a = root / "references" / "_snippets" / "a.md"
        b = root / "references" / "_snippets" / "b.md"
        a.write_text("<!-- include: _snippets/b.md -->", encoding="utf-8")
        b.write_text("<!-- include: _snippets/a.md -->", encoding="utf-8")
        try:
            resolve_includes_in_text(a.read_text(encoding="utf-8"), a, root)
        except ValueError as exc:
            assert "recursive include" in str(exc)
            return
        raise AssertionError("expected ValueError for cycle")


def test_no_includes_is_identity() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)
        source = root / "skills" / "demo" / "SKILL.md"
        text = "# Heading\n\nPlain prose with no sentinel.\n"
        source.write_text(text, encoding="utf-8")
        rendered = resolve_includes_in_text(text, source, root)
        assert rendered == text


def main() -> int:
    tests = [
        test_snippets_prefix_resolves_under_references,
        test_missing_include_raises,
        test_recursive_include_cycle_detected,
        test_no_includes_is_identity,
    ]
    failures: list[str] = []
    for t in tests:
        try:
            t()
            print(f"  OK  {t.__name__}")
        except AssertionError as exc:
            failures.append(f"{t.__name__}: {exc}")
            print(f"  FAIL {t.__name__}: {exc}", file=sys.stderr)
    if failures:
        return 1
    print(f"OK all {len(tests)} resolve_includes tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
