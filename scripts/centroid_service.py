#!/usr/bin/env python3
"""Prepare a deterministic, read-only centroid execution packet.

The public ``/centroid-pass`` orchestration uses this script to bind the live
reader-accessibility profile, corpus members, warrants, manuscript scope, and
hashes before a Generator or Evaluator performs the semantic pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reader_accessibility_policy as policy  # noqa: E402


SCHEMA_VERSION = "1.0.0"
EXIT_UNAVAILABLE = 4
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+)?\s*$")
WORD_RE = re.compile(r"[^\W_]+(?:['’-][^\W_]+)*", re.UNICODE)


class Unavailable(RuntimeError):
    def __init__(self, reason_code: str, detail: str):
        super().__init__(detail)
        self.reason_code = reason_code
        self.detail = detail


def _policy_reason(exc: Exception) -> str:
    """Preserve a policy's stable refusal code instead of flattening it."""
    detail = str(exc)
    if detail.startswith("GRAPH-SEMANTIC-INELIGIBLE:"):
        return "GRAPH-SEMANTIC-INELIGIBLE"
    return "PROFILE_UNRESOLVED"


def _base(status: str, reason_code: str | None) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "capability": "centroid-pass",
        "status": status,
        "reason_code": reason_code,
        "read_only": True,
        "writes_performed": False,
        "public_activation": "active",
    }


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_manuscript(path: Path) -> tuple[Path, bytes, str]:
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_file():
            raise OSError("not a regular file")
        payload = resolved.read_bytes()
        text = payload.decode("utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        raise Unavailable("MANUSCRIPT_UNREADABLE", f"cannot read UTF-8 manuscript: {exc}") from exc
    return resolved, payload, text


def _scope(text: str, heading: str | None) -> tuple[str, dict[str, Any]]:
    lines = text.splitlines()
    if heading is None:
        return text, {
            "kind": "full_manuscript",
            "heading": None,
            "start_line": 1,
            "end_line": max(1, len(lines)),
        }

    matches: list[tuple[int, int]] = []
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match and match.group(2).strip() == heading:
            matches.append((index, len(match.group(1))))
    if not matches:
        raise Unavailable("HEADING_NOT_RESOLVED", f"heading not found: {heading}")
    if len(matches) != 1:
        raise Unavailable("HEADING_AMBIGUOUS", f"heading occurs {len(matches)} times: {heading}")

    start, level = matches[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        match = HEADING_RE.match(lines[index])
        if match and len(match.group(1)) <= level:
            end = index
            break
    return "\n".join(lines[start:end]), {
        "kind": "heading",
        "heading": heading,
        "start_line": start + 1,
        "end_line": max(start + 1, end),
    }


def _prose_lines(text: str) -> list[str]:
    prose: list[str] = []
    fenced = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("```") or line.startswith("~~~"):
            fenced = not fenced
            continue
        if fenced or not line or HEADING_RE.match(line):
            continue
        if line.startswith("|") and line.endswith("|"):
            continue
        if re.fullmatch(r"!\[[^]]*\]\([^)]*\)", line):
            continue
        if re.fullmatch(r"[-:| ]+", line):
            continue
        if WORD_RE.search(line):
            prose.append(line)
    return prose


def _binding_provenance(project_root: Path | None, resolved: dict[str, Any]) -> str:
    if project_root is None:
        return "package-default"
    state_path = project_root / "reviews" / "phase_state.json"
    if not state_path.is_file():
        return "project" if any(
            item.get("scope") == "project" for item in resolved.get("source_bindings", [])
        ) else "package-default"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Unavailable("PROJECT_BINDING_UNREADABLE", f"cannot read phase_state.json: {exc}") from exc
    binding = (
        state.get("milestone_framework", {})
        .get("policy_bindings", {})
        .get("reader_accessibility")
    )
    if not isinstance(binding, dict):
        return "package-default"
    expected = {
        "profile_sha256": resolved["profile_sha256"],
        "attestation_view_pin": resolved["attestation_view_pin"],
        "exemplar_view_pin": resolved["exemplar_view_pin"],
    }
    mismatched = [key for key, value in expected.items() if binding.get(key) != value]
    if mismatched:
        raise Unavailable(
            "PROJECT_BINDING_STALE",
            "project reader-accessibility binding differs for: " + ", ".join(mismatched),
        )
    return "project"


def _member_view(items: Any) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or not isinstance(item.get("source_key"), str):
            continue
        output.append({
            key: str(item.get(key, ""))
            for key in ("source_key", "role", "grounding", "warrant_scope")
        })
    return sorted(output, key=lambda item: item["source_key"].encode("utf-8"))


def build_packet(args: argparse.Namespace) -> dict[str, Any]:
    project_root: Path | None = None
    if args.project_root is not None:
        try:
            project_root = Path(args.project_root).resolve(strict=True)
            if not project_root.is_dir():
                raise OSError("not a directory")
        except OSError as exc:
            raise Unavailable("PROJECT_ROOT_UNREADABLE", f"cannot resolve project root: {exc}") from exc

    manuscript_path, manuscript_bytes, full_text = _read_manuscript(Path(args.manuscript))
    scoped_text, scope = _scope(full_text, args.heading)
    prose = _prose_lines(scoped_text)
    if not prose:
        raise Unavailable("NO_PROSE", "resolved scope contains no prose")

    try:
        resolved = policy.resolve_policy(
            project_root,
            wiki_root=Path(args.wiki_root) if args.wiki_root else None,
            workspace_root=Path(args.workspace_root) if args.workspace_root else None,
            harness_root=Path(args.harness_root) if args.harness_root else None,
        )
    except (policy.PolicyError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Unavailable(_policy_reason(exc), str(exc)) from exc

    provenance = _binding_provenance(project_root, resolved)
    register = resolved["register_provenance"]
    members = _member_view(register.get("exemplar_members"))
    surface_keys = sorted(
        item["source_key"] for item in _member_view(register.get("surface_exemplar_members"))
    )
    argument_keys = sorted(
        item["source_key"] for item in _member_view(register.get("argument_exemplar_members"))
    )
    selected = {
        "surface": surface_keys,
        "argument": argument_keys,
        "both": sorted(set(surface_keys) | set(argument_keys)),
    }[args.exemplar_warrant]
    model = resolved["resolved_profile"]["domain_native_register"]
    derivation = model["derivations"][args.mode]
    scope_bytes = scoped_text.encode("utf-8")
    words = WORD_RE.findall("\n".join(prose))

    packet = _base("ready", None)
    packet.update({
        "binding_provenance": provenance,
        "manuscript": {
            "path": str(manuscript_path),
            "sha256": _sha256(manuscript_bytes),
            "scope": {**scope, "sha256": _sha256(scope_bytes)},
        },
        "policy": {
            "profile_path": resolved["profile_path"],
            "profile_sha256": resolved["profile_sha256"],
            "attestation_view_pin": resolved["attestation_view_pin"],
            "exemplar_view_pin": resolved["exemplar_view_pin"],
            "members": members,
            "surface_member_keys": surface_keys,
            "argument_member_keys": argument_keys,
            "c7_fence": model["c7_fence"],
        },
        "analysis_contract": {
            "derivation": args.mode,
            "profile_keys": derivation["profile_keys"],
            "discipline": derivation["discipline"],
            "exemplar_warrant": args.exemplar_warrant,
            "selected_member_keys": selected,
        },
        "scope_metrics": {
            "utf8_bytes": len(scope_bytes),
            "characters": len(scoped_text),
            "words": len(words),
            "prose_lines": len(prose),
        },
        "semantic_findings": [],
        "limitations": [
            "This script resolves policy, pins, members, scope, hashes, and deterministic text metrics only.",
            "The dispatched Generator or Evaluator must retrieve grounded passages and perform the semantic judgment.",
            "It performs no manuscript, lifecycle, review, graph, or Wiki write.",
        ],
    })
    return packet


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript", required=True, help="UTF-8 manuscript path to read")
    parser.add_argument("--project-root", help="Optional project root for policy overrides/binding checks")
    parser.add_argument("--heading", help="Exact Markdown heading text; default is the full manuscript")
    parser.add_argument("--mode", choices=("write", "review", "revise"), default="review")
    parser.add_argument("--exemplar-warrant", choices=("surface", "argument", "both"), default="both")
    parser.add_argument("--wiki-root", help="Explicit corpus root for portable resolution")
    parser.add_argument("--workspace-root", help="Explicit workspace root for portable resolution")
    parser.add_argument("--harness-root", help="Explicit running package root")
    args = parser.parse_args(argv)
    try:
        packet = build_packet(args)
    except Unavailable as exc:
        packet = _base("unavailable", exc.reason_code)
        packet["detail"] = exc.detail
        print(json.dumps(packet, indent=2, ensure_ascii=False))
        return EXIT_UNAVAILABLE
    print(json.dumps(packet, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
