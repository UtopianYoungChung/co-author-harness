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
from runtime_snippet_binding import (  # noqa: E402
    read_with_runtime_bindings,
    resolve_runtime_binding,
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


def test_consumer_relative_runtime_binding_resolves() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)
        target = root / "references" / "_snippets" / "foo.md"
        target.write_text("FOO", encoding="utf-8")
        consumer = root / "skills" / "demo" / "SKILL.md"
        consumer.write_text("binding", encoding="utf-8")
        resolved = resolve_runtime_binding(
            root, "skills/demo/SKILL.md", "../../references/_snippets/foo.md"
        )
        assert resolved == target.resolve()


def test_ambiguous_or_escaping_runtime_binding_is_refused() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root)
        target = root / "references" / "_snippets" / "foo.md"
        target.write_text("FOO", encoding="utf-8")
        consumer = root / "skills" / "demo" / "SKILL.md"
        consumer.write_text("binding", encoding="utf-8")
        for bad in ("references/_snippets/foo.md", "../../../outside.md"):
            try:
                resolve_runtime_binding(root, "skills/demo/SKILL.md", bad)
            except ValueError:
                continue
            raise AssertionError(f"expected refusal for {bad!r}")


def test_runtime_reader_loads_declared_snippet_and_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "references" / "_snippets").mkdir(parents=True)
        (root / "skills" / "run-phase-1").mkdir(parents=True)
        target = root / "references" / "_snippets" / "output-profile.md"
        target.write_text("BOUND POLICY", encoding="utf-8")
        consumer = root / "skills" / "run-phase-1" / "SKILL.md"
        binding = "../../references/_snippets/output-profile.md"
        consumer.write_text(
            f"**Runtime binding.** Resolve `{binding}` relative to this `SKILL.md`.",
            encoding="utf-8",
        )
        text = read_with_runtime_bindings(root, "skills/run-phase-1/SKILL.md")
        assert "BOUND POLICY" in text, text
        consumer.write_text("binding omitted", encoding="utf-8")
        try:
            read_with_runtime_bindings(root, "skills/run-phase-1/SKILL.md")
        except ValueError:
            return
        raise AssertionError("expected missing runtime declaration to fail closed")


def main() -> int:
    tests = [
        test_snippets_prefix_resolves_under_references,
        test_missing_include_raises,
        test_recursive_include_cycle_detected,
        test_no_includes_is_identity,
        test_consumer_relative_runtime_binding_resolves,
        test_ambiguous_or_escaping_runtime_binding_is_refused,
        test_runtime_reader_loads_declared_snippet_and_fails_closed,
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
