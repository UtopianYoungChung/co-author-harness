#!/usr/bin/env python3
"""centroid-bind — bind policy + graph eligibility + named manuscript bytes.

This CLI is centroid-bind. It is not centroid-source and not a centroid-check.

  centroid-source  live policy member yu-et-al-2011-social-modeling (role
                   centroid). Retrieval is the Yu-authored window only: book
                   pp. 3-10 (volume introduction) and pp. 11-52 (i* core
                   chapter). That object does not move when a check binds new
                   manuscript bytes.
  centroid-check   sentence-logic on named manuscript bytes against that
                   source (scripts/centroid_sentence_logic.py). A check of
                   live M4 is a check, not a redefinition of centroid-source.
  centroid-bind    this packet: policy + graph eligibility + named bytes.
                   GRAPH-SEMANTIC-INELIGIBLE is eligibility, not a pair
                   verdict. Empty semantic_findings means no role judgment
                   ran, not a pass.

Public skill folder remains skills/centroid-pass (catalog id). Capability
row remains centroid-pass. Instrument name is centroid-bind.
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
POLICY_PATH = Path(__file__).resolve().parents[1] / "references" / "policies" / "reader_accessibility.v1.json"
CENTROID_SOURCE_KEY = "yu-et-al-2011-social-modeling"
OBJECT_NAMES = {
    "centroid-source": (
        "live policy member yu-et-al-2011-social-modeling (role centroid); "
        "Yu-authored window book pp. 3-10 and 11-52"
    ),
    "centroid-check": (
        "sentence-logic on named manuscript bytes against centroid-source; "
        "a check does not redefine the source"
    ),
    "centroid-bind": (
        "this packet: policy + graph eligibility + named bytes; "
        "GRAPH-SEMANTIC-INELIGIBLE is eligibility, not a pair verdict"
    ),
}


class Unavailable(RuntimeError):
    def __init__(self, reason_code: str, detail: str, recovery: dict[str, str] | None = None):
        super().__init__(detail)
        self.reason_code = reason_code
        self.detail = detail
        self.recovery = recovery


def _policy_reason(exc: Exception) -> str:
    """Preserve a policy's stable refusal code instead of flattening it."""
    detail = str(exc)
    if detail.startswith("GRAPH-SEMANTIC-INELIGIBLE:"):
        return "GRAPH-SEMANTIC-INELIGIBLE"
    return "PROFILE_UNRESOLVED"


def _live_centroid_source() -> dict[str, str]:
    """Read the policy centroid member without resolving the wiki graph."""
    try:
        profile = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        members = profile["domain_native_register"]["exemplar_members"]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise Unavailable("CENTROID_SOURCE_UNRESOLVED", f"cannot read live centroid-source: {exc}") from exc
    hits = [item for item in members if isinstance(item, dict) and item.get("role") == "centroid"]
    if len(hits) != 1 or hits[0].get("source_key") != CENTROID_SOURCE_KEY:
        raise Unavailable(
            "CENTROID_SOURCE_UNRESOLVED",
            "live policy must have exactly one centroid member yu-et-al-2011-social-modeling",
        )
    member = hits[0]
    return {
        "source_key": CENTROID_SOURCE_KEY,
        "role": "centroid",
        "retrieval_scope": str(member.get("retrieval_scope", "")),
    }


def _with_names(packet: dict[str, Any]) -> dict[str, Any]:
    packet["instrument"] = "centroid-bind"
    packet["centroid_source"] = _live_centroid_source()
    packet["object_names"] = dict(OBJECT_NAMES)
    return packet


def _base(status: str, reason_code: str | None) -> dict[str, Any]:
    return _with_names({
        "schema_version": SCHEMA_VERSION,
        "capability": "centroid-pass",
        "status": status,
        "reason_code": reason_code,
        "read_only": True,
        "writes_performed": False,
        "public_activation": "active",
    })


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
    if (
        binding.get("binding_version") == "2.0.0"
        and binding.get("binding_kind") == "reader_profile"
        and binding.get("semantic_usage") == "not_invoked"
    ):
        # General skill still binds; graph-governed semantic use is not claimed.
        return "package-default"
    expected = {
        "profile_sha256": resolved["profile_sha256"],
        "attestation_view_pin": resolved["attestation_view_pin"],
        "exemplar_view_pin": resolved["exemplar_view_pin"],
    }
    mismatched = [key for key, value in expected.items() if binding.get(key) != value]
    if mismatched:
        request = project_root / "reviews" / "repin_rebind_request.json"
        if request.is_file():
            command = (
                "python scripts/assignment_milestone_checkpoint.py "
                f"rebind-reader-policy --project-root \"{project_root}\""
            )
            raise Unavailable(
                "PROJECT_BINDING_REBIND_AVAILABLE",
                "project binding differs from current canon and a pending Planner rebind request is present for: "
                + ", ".join(mismatched),
                {"classification": "routine_rebind", "owner": "planner", "command": command},
            )
        raise Unavailable(
            "PROJECT_BINDING_STALE",
            "project reader-accessibility binding differs for: " + ", ".join(mismatched),
        )
    return "project"


def _reader_profile_v2_is_dormant(project_root: Path | None) -> bool:
    """Recognize the graph-independent project binding without reading Graphify.

    The semantic centroid remains unavailable for this binding kind.  This
    deliberately returns False for absent or unreadable state so ordinary
    semantic-policy diagnostics retain their existing behavior unless a valid
    v2 declaration can be established.
    """
    if project_root is None:
        return False
    state_path = project_root / "reviews" / "phase_state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    binding = (
        state.get("milestone_framework", {})
        .get("policy_bindings", {})
        .get("reader_accessibility")
    )
    return bool(
        isinstance(binding, dict)
        and binding.get("binding_version") == "2.0.0"
        and binding.get("binding_kind") == "reader_profile"
        and binding.get("semantic_usage") == "not_invoked"
    )


def _member_view(items: Any) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or not isinstance(item.get("source_key"), str):
            continue
        member = {
            key: str(item.get(key, ""))
            for key in ("source_key", "role", "grounding", "warrant_scope")
        }
        if item.get("retrieval_scope"):
            member["retrieval_scope"] = str(item["retrieval_scope"])
        output.append(member)
    return sorted(output, key=lambda item: item["source_key"].encode("utf-8"))



def _general_packet(
    *,
    manuscript_path: Path,
    manuscript_bytes: bytes,
    scoped_text: str,
    scope: dict[str, Any],
    prose: list[str],
    mode: str,
    reason_code: str,
    detail: str,
) -> dict[str, Any]:
    """Manuscript binding without graph-governed semantic corpus."""
    scope_bytes = scoped_text.encode("utf-8")
    words = WORD_RE.findall("\n".join(prose))
    packet = _base("binding_resolved", reason_code)
    packet.update({
        "binding_provenance": "general",
        "detail": detail,
        "manuscript": {
            "path": str(manuscript_path),
            "sha256": _sha256(manuscript_bytes),
            "scope": {**scope, "sha256": _sha256(scope_bytes)},
        },
        "policy": {
            "profile_path": None,
            "members": [],
            "surface_member_keys": [],
            "argument_member_keys": [],
        },
        "analysis_contract": {
            "derivation": mode,
            "exemplar_warrant": None,
            "selected_member_keys": [],
            "primary_member_keys": [],
            "retrieval_order": [],
        },
        "scope_metrics": {
            "utf8_bytes": len(scope_bytes),
            "characters": len(scoped_text),
            "words": len(words),
            "prose_lines": len(prose),
        },
        "semantic_findings": [],
        "limitations": [
            "This is a centroid-bind of named manuscript bytes against centroid-source yu-et-al-2011-social-modeling.",
            "GRAPH-SEMANTIC-INELIGIBLE is eligibility, not a pair verdict.",
            "Empty semantic_findings means no role judgment ran, not a pass.",
            "General binding packet: manuscript scope, hashes, and text metrics only.",
            "Graph-governed semantic corpus was not used. Do not mint CLEAN from this binder.",
            "centroid-source remains yu-et-al-2011-social-modeling; this bind does not redefine it.",
            "It performs no manuscript, lifecycle, review, graph, or Wiki write.",
        ],
    })
    return packet


def build_packet(args: argparse.Namespace) -> dict[str, Any]:
    requested_source = str(getattr(args, "centroid_source", CENTROID_SOURCE_KEY) or CENTROID_SOURCE_KEY)
    if requested_source != CENTROID_SOURCE_KEY:
        raise Unavailable(
            "CENTROID_SOURCE_LOCKED",
            "centroid-source is the live policy member yu-et-al-2011-social-modeling; "
            "this flag does not move that object",
        )
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

    general_only = _reader_profile_v2_is_dormant(project_root)

    try:
        resolved = policy.resolve_policy(
            project_root,
            wiki_root=Path(args.wiki_root) if args.wiki_root else None,
            workspace_root=Path(args.workspace_root) if args.workspace_root else None,
            harness_root=Path(args.harness_root) if args.harness_root else None,
        )
    except (policy.PolicyError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        reason = _policy_reason(exc)
        if reason == "GRAPH-SEMANTIC-INELIGIBLE":
            return _general_packet(
                manuscript_path=manuscript_path,
                manuscript_bytes=manuscript_bytes,
                scoped_text=scoped_text,
                scope=scope,
                prose=prose,
                mode=args.mode,
                reason_code="GRAPH-SEMANTIC-INELIGIBLE",
                detail=str(exc),
            )
        raise Unavailable(reason, str(exc)) from exc

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
    primary = sorted(
        item["source_key"] for item in members if item.get("role") == "centroid"
    )
    retrieval_order = primary + [key for key in selected if key not in set(primary)]
    model = resolved["resolved_profile"]["domain_native_register"]
    derivation = model["derivations"][args.mode]
    scope_bytes = scoped_text.encode("utf-8")
    words = WORD_RE.findall("\n".join(prose))

    packet = _base("binding_resolved", None)
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
            "primary_member_keys": primary,
            "retrieval_order": retrieval_order,
        },
        "scope_metrics": {
            "utf8_bytes": len(scope_bytes),
            "characters": len(scoped_text),
            "words": len(words),
            "prose_lines": len(prose),
        },
        "semantic_findings": [],
        "limitations": [
            "This is a centroid-bind of named manuscript bytes against centroid-source yu-et-al-2011-social-modeling.",
            "GRAPH-SEMANTIC-INELIGIBLE is eligibility, not a pair verdict.",
            "Empty semantic_findings means no role judgment ran, not a pass.",
            "This script resolves policy, pins, members, scope, hashes, and deterministic text metrics only.",
            "The dispatched Generator or Evaluator must retrieve grounded passages and perform the semantic judgment.",
            "A later centroid-check of these bytes is a check, not a redefinition of centroid-source.",
            "It performs no manuscript, lifecycle, review, graph, or Wiki write.",
        ],
    })
    if general_only:
        packet["limitations"].append(
            "reader-profile v2 semantic_usage is not_invoked; this is a general binding packet, not a graph-governed scholarly pass."
        )
    return packet


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript", required=True, help="UTF-8 manuscript path to bind (centroid-bind input bytes; not centroid-source)")
    parser.add_argument(
        "--centroid-source",
        default=CENTROID_SOURCE_KEY,
        help="centroid-source key. Locked to yu-et-al-2011-social-modeling. Does not move the policy centroid.",
    )
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
        if exc.recovery is not None:
            packet["recovery"] = exc.recovery
        print(json.dumps(packet, indent=2, ensure_ascii=False))
        return EXIT_UNAVAILABLE
    print(json.dumps(packet, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
