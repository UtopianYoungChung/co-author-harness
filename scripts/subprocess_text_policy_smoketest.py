#!/usr/bin/env python3
"""Enforce deterministic decoding for subprocess and explicit byte decoding.

Windows inherits an arbitrary ANSI code page unless callers select one.  A
``text=True`` subprocess without both ``encoding`` and ``errors`` can therefore
crash while merely rendering a UTF-8 child diagnostic.  Explicit UTF-8 byte
decodes must likewise state their malformed-input policy.
"""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SUBPROCESS_APIS = {"call", "check_call", "check_output", "Popen", "run"}
ALLOWED_ERRORS = {"replace", "strict"}


def _constant_string(node: ast.AST | None) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _true(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _keyword_map(call: ast.Call) -> dict[str, ast.AST]:
    return {keyword.arg: keyword.value for keyword in call.keywords if keyword.arg is not None}


def _subprocess_api(call: ast.Call) -> str | None:
    function = call.func
    if (
        isinstance(function, ast.Attribute)
        and isinstance(function.value, ast.Name)
        and function.value.id == "subprocess"
        and function.attr in SUBPROCESS_APIS
    ):
        return function.attr
    return None


def _is_cmd_mklink(call: ast.Call) -> bool:
    if not call.args or not isinstance(call.args[0], (ast.List, ast.Tuple)):
        return False
    command = call.args[0].elts
    values = [_constant_string(item) for item in command[:3]]
    return values == ["cmd", "/c", "mklink"]


def _preferred_locale_call(node: ast.AST | None) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "locale"
        and node.func.attr == "getpreferredencoding"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value is False
    )


def _explicit_utf8_decode(call: ast.Call) -> bool:
    if not isinstance(call.func, ast.Attribute) or call.func.attr != "decode" or not call.args:
        return False
    encoding = _constant_string(call.args[0])
    return encoding is not None and encoding.lower().replace("_", "-") in {"utf-8", "utf8"}


def violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        api = _subprocess_api(node)
        if api is not None:
            keywords = _keyword_map(node)
            text_mode = _true(keywords.get("text")) or _true(keywords.get("universal_newlines"))
            if text_mode:
                encoding = _constant_string(keywords.get("encoding"))
                errors = _constant_string(keywords.get("errors"))
                utf8 = encoding is not None and encoding.lower().replace("_", "-") in {"utf-8", "utf8"}
                locale_mklink = _is_cmd_mklink(node) and _preferred_locale_call(keywords.get("encoding"))
                if not (utf8 or locale_mklink):
                    found.append(f"{path.relative_to(ROOT)}:{node.lineno}: subprocess.{api} text mode lacks encoding='utf-8'")
                if errors not in ALLOWED_ERRORS:
                    found.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: subprocess.{api} text mode lacks errors='replace' or 'strict'"
                    )

        if _explicit_utf8_decode(node):
            keywords = _keyword_map(node)
            positional_errors = _constant_string(node.args[1]) if len(node.args) > 1 else None
            errors = positional_errors or _constant_string(keywords.get("errors"))
            if errors not in ALLOWED_ERRORS:
                found.append(
                    f"{path.relative_to(ROOT)}:{node.lineno}: decode('utf-8') lacks explicit errors='replace' or 'strict'"
                )
    return found


def main() -> int:
    failures: list[str] = []
    files = sorted(SCRIPTS.rglob("*.py"))
    for path in files:
        failures.extend(violations(path))
    if failures:
        print(f"FAIL: {len(failures)} deterministic text-decoding policy violation(s)")
        for failure in failures:
            print(f"  {failure}")
        return 1
    print(f"PASS: deterministic text-decoding policy ({len(files)} Python files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
