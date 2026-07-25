#!/usr/bin/env python3
"""Build immutable, hash-bound package/release evidence indices and reports."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator

import destination_capability as destinations


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "references/schemas/release_evidence_index.schema.json"


class IndexRefusal(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _pairs(pairs: list[tuple[str, Any]], *, source: Path) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise IndexRefusal("RELEASE-INDEX-JSON", f"duplicate key in {source}: {key}")
        value[key] = item
    return value


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8", errors="strict"),
            object_pairs_hook=lambda pairs: _pairs(pairs, source=path),
            parse_constant=lambda token: (_ for _ in ()).throw(
                IndexRefusal("RELEASE-INDEX-JSON", f"non-finite value in {path}: {token}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IndexRefusal("RELEASE-INDEX-JSON", f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise IndexRefusal("RELEASE-INDEX-JSON", "index must be an object")
    return value


def _canonical(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(root: Path, raw: str) -> Path:
    relative = PurePosixPath(raw)
    if relative.is_absolute() or not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise IndexRefusal("RELEASE-INDEX-PATH", f"unsafe repository-relative path: {raw!r}")
    unresolved = root / Path(*relative.parts)
    cursor = root
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
    for part in relative.parts:
        cursor = cursor / part
        try:
            metadata = os.lstat(cursor)
        except OSError as exc:
            raise IndexRefusal("RELEASE-INDEX-PATH", f"cannot inspect binding: {raw}") from exc
        if stat.S_ISLNK(metadata.st_mode) or bool(
            getattr(metadata, "st_file_attributes", 0) & reparse_flag
        ):
            raise IndexRefusal(
                "RELEASE-INDEX-PATH",
                f"binding traverses a link or reparse point: {raw}",
            )
    path = unresolved.resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise IndexRefusal("RELEASE-INDEX-PATH", f"binding escapes repository root: {raw}") from exc
    if path.is_symlink() or not path.is_file():
        raise IndexRefusal("RELEASE-INDEX-PATH", f"binding is not a plain file: {raw}")
    return path


def _bindings(value: Any):
    if isinstance(value, dict):
        if set(value) >= {"path", "sha256"} and isinstance(value.get("path"), str):
            yield value
        for child in value.values():
            yield from _bindings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _bindings(child)


def validate(root: Path, value: dict[str, Any]) -> None:
    try:
        Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(value)
    except Exception as exc:
        raise IndexRefusal("RELEASE-INDEX-SCHEMA", str(exc)) from exc
    seen: dict[str, str] = {}
    for binding in _bindings(value):
        raw = binding["path"]
        if raw in seen and seen[raw] != binding["sha256"]:
            raise IndexRefusal(
                "RELEASE-INDEX-DUPLICATE",
                f"one evidence path carries conflicting digests: {raw}",
            )
        seen[raw] = binding["sha256"]
        path = _resolve(root, raw)
        if _sha(path) != binding["sha256"]:
            raise IndexRefusal("RELEASE-INDEX-STALE", f"digest mismatch: {raw}")


def _write_exact(path: Path, data: bytes, *, purpose: str) -> None:
    destinations.assert_writable(path, purpose=purpose)
    if path.exists():
        if path.is_file() and not path.is_symlink() and path.read_bytes() == data:
            return
        raise IndexRefusal("RELEASE-INDEX-IMMUTABLE", f"refusing to replace {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def build(spec: Path, output: Path, root: Path) -> None:
    value = _load(spec)
    validate(root, value)
    _write_exact(output, _canonical(value), purpose="release evidence index")


def append_release(package_index: Path, spec: Path, output: Path, root: Path) -> None:
    package = _load(package_index)
    validate(root, package)
    if package.get("index_type") != "package":
        raise IndexRefusal("RELEASE-INDEX-CHAIN", "package predecessor is not a package index")
    value = _load(spec)
    expected = {
        "path": package_index.resolve().relative_to(root).as_posix(),
        "sha256": _sha(package_index),
    }
    if value.get("index_type") != "release" or value.get("package_index") != expected:
        raise IndexRefusal("RELEASE-INDEX-CHAIN", "release index does not bind the exact package index")
    validate(root, value)
    _write_exact(output, _canonical(value), purpose="release evidence index")


def render(index: Path, output: Path, root: Path) -> None:
    value = _load(index)
    validate(root, value)
    lines = [
        f"# Verification and Shipment Report — v{value['release_version']}",
        "",
        f"**Index type:** `{value['index_type']}`  ",
        f"**Status:** `{value['status']}`  ",
        f"**Source commit:** `{value['source']['commit']}`",
        "",
        "## Runtime planes",
        "",
    ]
    lines.extend(f"- `{row['name']}`: `{row['status']}`" for row in value["planes"])
    lines.extend(["", "## Evidence", ""])
    lines.extend(f"- `{row['id']}`: `{row['result']}` — `{row['path']}`" for row in value["evidence"])
    for title, key in (("Warnings", "warnings"), ("Omitted checks", "omissions"), ("No-claim statements", "no_claims")):
        lines.extend(["", f"## {title}", ""])
        lines.extend(f"- {item}" for item in value[key])
    lines.append("")
    _write_exact(output, "\n".join(lines).encode("utf-8"), purpose="release report")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("build-package", "append-release"):
        command = sub.add_parser(name)
        command.add_argument("--spec", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        if name == "append-release":
            command.add_argument("--package-index", type=Path, required=True)
    report = sub.add_parser("render-report")
    report.add_argument("--index", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    try:
        if args.command == "build-package":
            build(args.spec.resolve(strict=True), args.output.resolve(strict=False), root)
        elif args.command == "append-release":
            append_release(args.package_index.resolve(strict=True), args.spec.resolve(strict=True), args.output.resolve(strict=False), root)
        else:
            render(args.index.resolve(strict=True), args.output.resolve(strict=False), root)
    except (IndexRefusal, destinations.DestinationRefused) as exc:
        print(str(exc))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
