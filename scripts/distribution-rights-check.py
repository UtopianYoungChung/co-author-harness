#!/usr/bin/env python3
"""Fail closed when known non-distributable source material can ship."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath


SCHEMA = "coauthor-distribution-rights/v1"
HISTORY_SCOPE = "current-tree-and-future-artifacts-only"
ALLOWED_DISPOSITIONS = {"excluded", "replaced-with-summary", "replaced-with-synthetic"}
ARCHIVE_SUFFIXES = (".plugin", ".zip")
MARKDOWN_PREFIX = re.compile(r"^(?:#{1,6}\s+|[-*+]\s+|\d+[.)]\s+)")


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def safe_rel(value: object, field: str) -> str:
    text = str(value).strip().replace("\\", "/")
    path = PurePosixPath(text)
    if not text or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field} must be a safe repository-relative path: {value!r}")
    return path.as_posix()


def candidate_files(root: Path) -> list[tuple[str, Path]]:
    """Return tracked and non-ignored candidate files, or a walk fallback."""
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--others",
         "--exclude-standard", "-z"],
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        names = [item.decode("utf-8", errors="strict")
                 for item in proc.stdout.split(b"\0") if item]
    else:
        names = [path.relative_to(root).as_posix() for path in root.rglob("*")
                 if path.is_file() and ".git" not in path.relative_to(root).parts]

    result: list[tuple[str, Path]] = []
    for name in sorted(set(names)):
        rel = name.replace("\\", "/")
        path = root / rel
        if not path.is_file() or rel.endswith(ARCHIVE_SUFFIXES):
            continue
        result.append((rel, path))
    return result


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalized_text_segment_hashes(path: Path) -> set[str]:
    """Hash normalized UTF-8 lines and paragraphs without storing source text."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return set()
    segments: set[str] = set()
    paragraph: list[str] = []

    def add(value: str) -> None:
        normalized = " ".join(value.split())
        if normalized:
            segments.add(hashlib.sha256(normalized.encode("utf-8")).hexdigest())

    for raw in text.splitlines():
        line = raw.strip()
        while line.startswith(">"):
            line = line[1:].lstrip()
        while MARKDOWN_PREFIX.match(line):
            line = MARKDOWN_PREFIX.sub("", line, count=1).lstrip()
        if not line:
            if paragraph:
                add(" ".join(paragraph))
                paragraph = []
            continue
        add(line)
        paragraph.append(line)
    if paragraph:
        add(" ".join(paragraph))
    return segments


def validate(root: Path) -> tuple[list[str], dict[str, object]]:
    blockers: list[str] = []
    registry_path = root / "references" / "distribution_rights.json"
    try:
        registry = read_json(registry_path)
    except Exception as exc:  # noqa: BLE001
        return [f"rights registry invalid: {exc}"], {}

    if registry.get("schema") != SCHEMA:
        blockers.append(f"rights registry schema must be {SCHEMA!r}")
    if registry.get("history_scope") != HISTORY_SCOPE:
        blockers.append(
            f"history_scope must be {HISTORY_SCOPE!r}; this gate cannot clean Git history"
        )

    try:
        manifest = read_json(root / ".claude-plugin" / "plugin.json")
        manifest_license = str(manifest.get("license", "")).strip()
    except Exception as exc:  # noqa: BLE001
        blockers.append(f"plugin manifest invalid: {exc}")
        manifest_license = "<invalid>"
    registry_license = str(registry.get("package_license", "")).strip()
    if manifest_license != registry_license:
        blockers.append(
            f"manifest license ({manifest_license}) != rights registry license ({registry_license})"
        )

    try:
        notice_rel = safe_rel(registry.get("notice_path"), "notice_path")
        notice_text = (root / notice_rel).read_text(encoding="utf-8")
        if "current tree and future artifacts only" not in notice_text.lower():
            blockers.append(
                f"notice {notice_rel} must state current-tree/future-artifact scope"
            )
    except Exception as exc:  # noqa: BLE001
        blockers.append(f"rights notice invalid: {exc}")
        notice_rel = "<invalid>"

    local_roots: list[str] = []
    raw_local = registry.get("local_only_roots")
    if not isinstance(raw_local, list) or not raw_local:
        blockers.append("local_only_roots must be a non-empty list")
    else:
        for index, value in enumerate(raw_local):
            try:
                rel = safe_rel(value, f"local_only_roots[{index}]").rstrip("/") + "/"
                local_roots.append(rel)
            except ValueError as exc:
                blockers.append(str(exc))
    gitignore = (root / ".gitignore").read_text(encoding="utf-8").splitlines() \
        if (root / ".gitignore").is_file() else []
    ignore_rules = {line.strip().replace("\\", "/") for line in gitignore
                    if line.strip() and not line.lstrip().startswith("#")}
    for rel in local_roots:
        if rel not in ignore_rules:
            blockers.append(f"local-only root {rel} is not an exact .gitignore rule")

    materials = registry.get("materials")
    if not isinstance(materials, list) or not materials:
        blockers.append("materials must be a non-empty list")
        materials = []

    forbidden: dict[str, str] = {}
    forbidden_text: dict[str, str] = {}
    replacements: dict[str, str] = {}
    ids: set[str] = set()
    for index, material in enumerate(materials):
        if not isinstance(material, dict):
            blockers.append(f"materials[{index}] must be an object")
            continue
        material_id = str(material.get("id", "")).strip()
        if not material_id or material_id in ids:
            blockers.append(f"materials[{index}] id is empty or duplicate: {material_id!r}")
        ids.add(material_id)
        disposition = str(material.get("disposition", "")).strip()
        if disposition not in ALLOWED_DISPOSITIONS:
            blockers.append(
                f"material {material_id or index} disposition {disposition!r} is invalid"
            )
        hashes = material.get("forbidden_sha256")
        if not isinstance(hashes, list) or not hashes:
            blockers.append(
                f"material {material_id or index} forbidden_sha256 must be non-empty"
            )
            hashes = []
        for value in hashes:
            value = str(value).lower().strip()
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                blockers.append(f"material {material_id or index} has invalid SHA256 {value!r}")
            elif value in forbidden:
                blockers.append(f"forbidden SHA256 {value} is duplicated")
            else:
                forbidden[value] = material_id

        text_hashes = material.get("forbidden_text_sha256", [])
        if not isinstance(text_hashes, list):
            blockers.append(
                f"material {material_id or index} forbidden_text_sha256 must be a list"
            )
            text_hashes = []
        for value in text_hashes:
            value = str(value).lower().strip()
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                blockers.append(
                    f"material {material_id or index} has invalid text SHA256 {value!r}"
                )
            elif value in forbidden_text:
                blockers.append(f"forbidden text SHA256 {value} is duplicated")
            else:
                forbidden_text[value] = material_id

        historical = material.get("historical_paths")
        if not isinstance(historical, list) or not historical:
            blockers.append(f"material {material_id or index} historical_paths must be non-empty")
            historical = []
        historical_paths: list[str] = []
        for value in historical:
            try:
                historical_paths.append(safe_rel(value, "historical_paths"))
            except ValueError as exc:
                blockers.append(str(exc))

        replacement_paths = material.get("replacement_paths")
        replacement_hashes = material.get("replacement_sha256")
        if not isinstance(replacement_paths, list) or not replacement_paths:
            blockers.append(f"material {material_id or index} replacement_paths must be non-empty")
            replacement_paths = []
        if not isinstance(replacement_hashes, dict):
            blockers.append(f"material {material_id or index} replacement_sha256 must be an object")
            replacement_hashes = {}
        normalized_replacements: list[str] = []
        for value in replacement_paths:
            try:
                rel = safe_rel(value, "replacement_paths")
                normalized_replacements.append(rel)
                expected = str(replacement_hashes.get(rel, "")).lower().strip()
                if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
                    blockers.append(
                        f"replacement {rel} has missing or invalid replacement SHA256"
                    )
                else:
                    if rel in replacements and replacements[rel] != expected:
                        blockers.append(
                            f"replacement {rel} has conflicting SHA256 pins"
                        )
                    replacements[rel] = expected
            except ValueError as exc:
                blockers.append(str(exc))
        if set(replacement_hashes) != set(normalized_replacements):
            blockers.append(
                f"material {material_id or index} replacement path/hash keys disagree"
            )
        for rel in historical_paths:
            if rel not in normalized_replacements and (root / rel).exists():
                blockers.append(
                    f"historical path must remain absent unless it is the "
                    f"registered replacement: {rel}"
                )

    files = candidate_files(root)
    for rel, _path in files:
        if any(rel == prefix.rstrip("/") or rel.startswith(prefix)
               for prefix in local_roots):
            blockers.append(
                f"local-only path enters distributable population: {rel}"
            )
    observed: dict[str, str] = {}
    for rel, path in files:
        value = digest(path)
        observed[rel] = value
        if value in forbidden:
            blockers.append(
                f"forbidden SHA256 {value} from {forbidden[value]} is present at {rel}"
            )
        for text_value in normalized_text_segment_hashes(path):
            if text_value in forbidden_text:
                blockers.append(
                    f"forbidden text SHA256 {text_value} from "
                    f"{forbidden_text[text_value]} is present at {rel}"
                )
    for rel, expected in replacements.items():
        path = root / rel
        if not path.is_file():
            blockers.append(f"replacement missing: {rel}")
        elif observed.get(rel, digest(path)) != expected:
            blockers.append(
                f"replacement SHA256 mismatch for {rel}: "
                f"expected {expected}, observed {digest(path)}"
            )

    surfaces = registry.get("enforcement_surfaces")
    if not isinstance(surfaces, dict) or not surfaces:
        blockers.append("enforcement_surfaces must be a non-empty object")
        surfaces = {}
    for raw_path, raw_needle in surfaces.items():
        try:
            rel = safe_rel(raw_path, "enforcement_surfaces path")
            needle = str(raw_needle)
            text = (root / rel).read_text(encoding="utf-8")
            if not needle or needle not in text:
                blockers.append(f"enforcement wiring missing from {rel}: {needle!r}")
        except Exception as exc:  # noqa: BLE001
            blockers.append(f"enforcement surface invalid: {raw_path}: {exc}")

    summary = {
        "materials": len(materials),
        "forbidden_hashes": len(forbidden),
        "forbidden_text_hashes": len(forbidden_text),
        "replacement_paths": len(replacements),
        "candidate_files": len(files),
        "notice_path": notice_rel,
    }
    return blockers, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-root", default=None)
    args = parser.parse_args()
    root = Path(args.plugin_root).resolve() if args.plugin_root else Path(__file__).resolve().parents[1]
    blockers, summary = validate(root)
    print("DISTRIBUTION RIGHTS CHECK")
    print(f"- Plugin root: {root}")
    for key, value in summary.items():
        print(f"- {key.replace('_', ' ').title()}: {value}")
    print(f"- Blockers: {len(blockers)}")
    for blocker in blockers:
        print(f"[BLOCKER] {blocker}")
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
