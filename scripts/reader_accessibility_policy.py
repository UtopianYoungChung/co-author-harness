#!/usr/bin/env python3
"""Load, validate, and resolve the package reader-accessibility policy.

Production code is standard-library only. Project files may narrow register
scope and override lexicons only with the polarity declared by the package
profile. Every contributing file is returned with its SHA-256 binding.
"""

from __future__ import annotations

import argparse
import copy
import getpass
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from os import stat_result
from pathlib import Path, PurePosixPath
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "references" / "policies" / "reader_accessibility.v1.json"
PROFILE_SCHEMA = ROOT / "references" / "schemas" / "reader_accessibility_profile.schema.json"
CHECK8_SCHEMA = ROOT / "references" / "schemas" / "check8_evidence.schema.json"
CANDIDATE_SCHEMA = ROOT / "references" / "schemas" / "reader_accessibility_candidates.schema.json"
PHASES = ("Ph1", "Ph2", "Ph3", "Ph4")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SEMANTIC_ARTIFACT_SCHEMA_VERSION = "1.0.0"
ALLOWED_SEMANTIC_AUDIT_REVIEWERS = {"Claude Code", "Codex"}
FRESH_SEMANTIC_GRAPH_RE = re.compile(
    r"^knowledge/LLM wiki/graphify-out/semantic-qualifications/"
    r"(?P<transaction_id>semq-\d{8}T\d{6}Z-[0-9a-f]{8})/qualified\.graph\.json$"
)
DEFAULT_WIKI_ROOT = Path("B:/Agents/knowledge/LLM wiki")
DEFAULT_WORKSPACE_ROOT = Path("B:/Agents")
ROOT_ENV_VARS = {
    "wiki_root": "AGENT_WIKI_ROOT",
    "workspace_root": "AGENT_WORKSPACE_ROOT",
    "harness_root": "AGENT_HARNESS_ROOT",
}


class PolicyError(ValueError):
    pass


class CorpusRootError(PolicyError):
    """The declared corpus roots cannot locate a corpus in THIS environment.

    Distinct from a merely absent input: it says the *locator itself* is
    unusable here, before any filesystem lookup is meaningful.

    `corpus_binding.path_roots` records the roots the pinned corpus was
    declared under -- `B:/Agents/...` on the maintainer's Windows host. Those
    strings are provenance, NOT a portable filesystem locator: `B:/Agents` is
    absolute on Windows and an ordinary RELATIVE path everywhere else. So on
    Linux `Path("B:/Agents") / "knowledge/LLM wiki/graphify-out/graph.json"`
    silently resolved against the CWD, and the register reported

        domain-native input absent: graph_provenance_only:
        <cwd>/B:/Agents/knowledge/LLM wiki/graphify-out/graph.json

    -- an "absent input" at a path that could never have existed. The
    diagnosis pointed at the corpus; the defect was the locator. That is what
    kept `structural-checks` red on every Linux run since 2026-07-13 (the
    failure predates PR #11 and was never introduced by it).

    Raising here converts a silently wrong path into a named, actionable
    condition. It does NOT weaken the check: the register still resolves, and
    still fails closed, whenever roots are supplied that this host can use --
    via the explicit override seam that `resolve_policy` and
    `resolve_domain_native_register` already expose.
    """


def _profile_path_roots(profile: dict[str, Any]) -> dict[str, Path]:
    """Read corpus_binding.path_roots from the profile (authority for live wiki/workspace)."""
    try:
        declared = profile["domain_native_register"]["corpus_binding"]["path_roots"]
        return {
            "wiki_root": Path(declared["wiki_root"]),
            "workspace_root": Path(declared["workspace_root"]),
            "harness_root": Path(declared["harness_root"]),
        }
    except (KeyError, TypeError) as exc:
        raise PolicyError(
            "domain_native_register.corpus_binding.path_roots missing or malformed"
        ) from exc


def _resolve_register_roots(
    profile: dict[str, Any],
    *,
    wiki_root: Path | None,
    workspace_root: Path | None,
    harness_root: Path | None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    """Resolve roots from profile path_roots; allow fixture overrides.

    Live wiki/workspace roots come from the profile const. Module DEFAULT_* must
    match that const (guards hardcoded drift). Fixture callers may inject other
    roots; those are recorded as path_roots_mode=override. The running package
    root (ROOT / explicit harness_root) is the authority for relative package
    paths so worktrees and alternate installs stay valid even when they differ
    from path_roots.harness_root.
    """
    sources = {
        "wiki_root": "explicit" if wiki_root is not None else "profile",
        "workspace_root": "explicit" if workspace_root is not None else "profile",
        "harness_root": "explicit" if harness_root is not None else "runtime",
    }
    roots = {
        "wiki_root": wiki_root,
        "workspace_root": workspace_root,
        "harness_root": harness_root,
    }
    for label, variable in ROOT_ENV_VARS.items():
        if roots[label] is None:
            value = os.environ.get(variable)
            if value:
                roots[label] = Path(value)
                sources[label] = "environment"
    wiki_root = roots["wiki_root"]
    workspace_root = roots["workspace_root"]
    harness_root = roots["harness_root"]

    declared = _profile_path_roots(profile)
    profile_wiki = declared["wiki_root"]
    profile_workspace = declared["workspace_root"]
    profile_harness = declared["harness_root"]

    if wiki_root is None:
        wiki = profile_wiki
    else:
        wiki = Path(wiki_root)
        if wiki.resolve() == DEFAULT_WIKI_ROOT.resolve() and wiki.resolve() != profile_wiki.resolve():
            raise PolicyError(
                "wiki_root module default diverges from profile corpus_binding.path_roots.wiki_root"
            )

    if workspace_root is None:
        workspace = profile_workspace
    else:
        workspace = Path(workspace_root)
        if (
            workspace.resolve() == DEFAULT_WORKSPACE_ROOT.resolve()
            and workspace.resolve() != profile_workspace.resolve()
        ):
            raise PolicyError(
                "workspace_root module default diverges from profile "
                "corpus_binding.path_roots.workspace_root"
            )

    harness = Path(harness_root) if harness_root is not None else ROOT

    # PORTABILITY GATE. Every root that anchors a contained lookup must be
    # absolute ON THIS HOST before it is used. `Path.is_absolute()` is
    # platform-aware, which is exactly the property needed: "B:/Agents" is
    # absolute on Windows and relative on POSIX, and a relative anchor makes
    # `_contained()` join against the CWD -- producing a real path that names
    # a corpus nobody declared. Checked here, once, because this is the single
    # function where declared/override roots become EFFECTIVE roots.
    #
    # ALL THREE ROOTS, INCLUDING harness_root. The first cut gated wiki and
    # workspace only -- an under-narrow population, the same shape as every
    # other allowlist in this workstream. harness_root anchors contained
    # PACKAGE lookups (register_profile, package contributors), so a relative
    # one rebased beneath the CWD and surfaced as `_MissingInput` at, e.g.,
    # `C:\Windows\System32\relative\harness\references\policies\
    # reader_accessibility.v1.json` -- precisely the misleading resolution this
    # gate exists to eliminate, reproduced 2026-07-17. `harness` defaults to
    # ROOT (always absolute), so only an explicit override can trip this; the
    # guard is a property of ROOTS, not of who supplied them.
    for label, root in (("wiki_root", wiki), ("workspace_root", workspace),
                        ("harness_root", harness)):
        if not root.is_absolute():
            raise CorpusRootError(
                f"{label} {str(root)!r} is not an absolute path on this host "
                f"({sys.platform}). corpus_binding.path_roots records the roots "
                "the pinned corpus was declared under (a Windows drive path); it "
                "is provenance, not a portable locator. Supply roots this host "
                "can use via the explicit override seam -- resolve_policy("
                "wiki_root=..., workspace_root=..., harness_root=...) or "
                "run_all.py --wiki-root / --workspace-root -- or run where the "
                "declared corpus exists."
            )

    meta: dict[str, Any] = {
        "profile_path_roots": {
            "wiki_root": profile_wiki.as_posix(),
            "workspace_root": profile_workspace.as_posix(),
            "harness_root": profile_harness.as_posix(),
        },
        "effective": {
            "wiki_root": wiki.as_posix(),
            "workspace_root": workspace.as_posix(),
            "harness_root": harness.as_posix(),
        },
    }
    if (
        sources["wiki_root"] == "profile"
        and sources["workspace_root"] == "profile"
        and sources["harness_root"] == "runtime"
        and wiki.resolve() == profile_wiki.resolve()
        and workspace.resolve() == profile_workspace.resolve()
    ):
        meta["path_roots_mode"] = "profile"
    else:
        meta["path_roots_mode"] = "override"
        # Keep the no-override resolved object byte-compatible with existing
        # bindings.  Only an actual override introduces a new provenance field.
        meta["resolution_sources"] = sources
    if harness.resolve() != profile_harness.resolve():
        meta["harness_root_note"] = (
            "running package root differs from profile path_roots.harness_root "
            "(worktree or alternate install); relative package paths resolve from the running root"
        )
    return wiki, workspace, harness, meta


class _MissingInput(PolicyError):
    pass


def _schema_type(value: Any, expected: str) -> bool:
    checks = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
    }
    return expected in checks and checks[expected](value)


def _schema_ref(root: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise PolicyError(f"only local schema references are supported: {reference}")
    value: Any = root
    for token in reference[2:].split("/"):
        value = value[token.replace("~1", "/").replace("~0", "~")]
    if not isinstance(value, dict):
        raise PolicyError(f"schema reference is not an object: {reference}")
    return value


def _strict_schema_validate(instance: Any, schema: dict[str, Any], root: dict[str, Any], path: str = "$") -> None:
    """Bounded Draft 2020-12 evaluator for the shipped accessibility schemas."""
    if "$ref" in schema:
        _strict_schema_validate(instance, _schema_ref(root, schema["$ref"]), root, path)
    if "oneOf" in schema:
        matches = 0
        for subschema in schema["oneOf"]:
            try:
                _strict_schema_validate(instance, subschema, root, path)
            except PolicyError:
                continue
            matches += 1
        if matches != 1:
            raise PolicyError(f"{path}: expected exactly one matching schema branch")
        return
    for subschema in schema.get("allOf", []):
        _strict_schema_validate(instance, subschema, root, path)
    expected = schema.get("type")
    if expected is not None:
        allowed = [expected] if isinstance(expected, str) else expected
        if not any(_schema_type(instance, kind) for kind in allowed):
            raise PolicyError(f"{path}: expected {allowed}, got {type(instance).__name__}")
    if "const" in schema and instance != schema["const"]:
        raise PolicyError(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        raise PolicyError(f"{path}: value is outside enum")
    if isinstance(instance, dict):
        missing = [key for key in schema.get("required", []) if key not in instance]
        if missing:
            raise PolicyError(f"{path}: missing required properties {missing}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(instance) - set(properties))
            if extra:
                raise PolicyError(f"{path}: additional properties forbidden: {extra}")
        for key, subschema in properties.items():
            if key in instance:
                _strict_schema_validate(instance[key], subschema, root, f"{path}.{key}")
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            for key in set(instance) - set(properties):
                _strict_schema_validate(instance[key], additional, root, f"{path}.{key}")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            raise PolicyError(f"{path}: too few items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise PolicyError(f"{path}: too many items")
        if schema.get("uniqueItems") and len({json.dumps(value, sort_keys=True) for value in instance}) != len(instance):
            raise PolicyError(f"{path}: items must be unique")
        if "items" in schema:
            for index, value in enumerate(instance):
                _strict_schema_validate(value, schema["items"], root, f"{path}[{index}]")
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            raise PolicyError(f"{path}: string is too short")
        if "pattern" in schema and re.fullmatch(schema["pattern"], instance) is None:
            raise PolicyError(f"{path}: string does not match schema pattern")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise PolicyError(f"{path}: value is below minimum")
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            raise PolicyError(f"{path}: value is not above exclusive minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            raise PolicyError(f"{path}: value is above maximum")
        if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
            raise PolicyError(f"{path}: value is not below exclusive maximum")


def validate_schema_file(instance: Any, schema_path: Path) -> None:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"schema unreadable: {schema_path}: {exc}") from exc
    _strict_schema_validate(instance, schema, schema)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stamp(stat: stat_result) -> tuple[int, int, int, int]:
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


@dataclass(frozen=True)
class _Snapshot:
    path: Path
    role: str
    data: bytes
    sha256: str
    stamp: tuple[int, int, int, int]

    def text(self) -> str:
        try:
            return self.data.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise PolicyError(f"domain-native input is not UTF-8: {self.role}: {self.path}: {exc}") from exc


@dataclass(frozen=True)
class _AbsentSnapshot:
    path: Path
    role: str
    anchor: Path
    anchor_stamp: tuple[int, int, int, int]


class _SnapshotSet:
    def __init__(self, hook: Callable[[str, str, Path | None], None] | None = None):
        self._hook = hook
        self._items: dict[Path, _Snapshot] = {}
        self._absent: dict[Path, _AbsentSnapshot] = {}

    def capture(self, path: Path, role: str) -> _Snapshot:
        try:
            resolved = path.resolve()
        except OSError as exc:
            raise PolicyError(f"domain-native input unreadable: {role}: {path}: {exc}") from exc
        if resolved in self._items:
            item = self._items[resolved]
            if self._hook:
                self._hook("after_capture", role, resolved)
            try:
                if _stamp(resolved.stat()) != item.stamp:
                    raise PolicyError(f"domain-native input changed during resolution: {role}: {resolved}")
            except PolicyError:
                raise
            except OSError as exc:
                raise PolicyError(f"domain-native input changed during resolution: {role}: {resolved}: {exc}") from exc
            return item
        try:
            with resolved.open("rb") as stream:
                before = _stamp(os.fstat(stream.fileno()))
                data = stream.read()
                after = _stamp(os.fstat(stream.fileno()))
            if before != after or len(data) != before[2]:
                raise PolicyError(f"domain-native input changed during resolution: {role}: {resolved}")
            item = _Snapshot(resolved, role, data, hashlib.sha256(data).hexdigest(), before)
            self._items[resolved] = item
            if self._hook:
                self._hook("after_capture", role, resolved)
            if _stamp(resolved.stat()) != before:
                raise PolicyError(f"domain-native input changed during resolution: {role}: {resolved}")
            return item
        except PolicyError:
            raise
        except FileNotFoundError as exc:
            raise _MissingInput(f"domain-native input absent: {role}: {resolved}") from exc
        except OSError as exc:
            raise PolicyError(f"domain-native input unreadable: {role}: {resolved}: {exc}") from exc

    def capture_optional(self, path: Path, role: str) -> _Snapshot | None:
        try:
            return self.capture(path, role)
        except _MissingInput:
            self.track_absent(path, role)
            return None

    def track_absent(self, path: Path, role: str) -> None:
        try:
            resolved = path.resolve()
        except OSError as exc:
            raise PolicyError(f"domain-native absence token unreadable: {role}: {path}: {exc}") from exc
        anchor = resolved.parent
        while True:
            try:
                anchor_stamp = _stamp(anchor.stat())
                break
            except FileNotFoundError:
                if anchor == anchor.parent:
                    raise PolicyError(f"domain-native absence anchor missing: {role}: {resolved}")
                anchor = anchor.parent
            except OSError as exc:
                raise PolicyError(f"domain-native absence token unreadable: {role}: {resolved}: {exc}") from exc
        if self._hook:
            self._hook("before_absence_anchor", role, resolved)
        try:
            if _stamp(anchor.stat()) != anchor_stamp:
                raise PolicyError(f"domain-native input changed during resolution: {role}: {resolved}")
        except PolicyError:
            raise
        except OSError as exc:
            raise PolicyError(f"domain-native input changed during resolution: {role}: {resolved}: {exc}") from exc
        try:
            resolved.stat()
        except FileNotFoundError:
            item = _AbsentSnapshot(resolved, role, anchor, anchor_stamp)
            self._absent[resolved] = item
            if self._hook:
                self._hook("after_absence", role, resolved)
            self._verify_absent(item)
            return
        except OSError as exc:
            raise PolicyError(f"domain-native absence token unreadable: {role}: {resolved}: {exc}") from exc
        raise PolicyError(f"domain-native input changed during resolution: {role}: {resolved}")

    @staticmethod
    def _verify_absent(item: _AbsentSnapshot) -> None:
        try:
            item.path.stat()
        except FileNotFoundError:
            try:
                if _stamp(item.anchor.stat()) == item.anchor_stamp:
                    return
            except OSError as exc:
                raise PolicyError(f"domain-native input changed during resolution: {item.role}: {item.path}: {exc}") from exc
        except OSError as exc:
            raise PolicyError(f"domain-native input changed during resolution: {item.role}: {item.path}: {exc}") from exc
        raise PolicyError(f"domain-native input changed during resolution: {item.role}: {item.path}")

    def verify_all(self) -> None:
        if self._hook:
            self._hook("before_final_verify", "*", None)
        for item in self._items.values():
            try:
                with item.path.open("rb") as stream:
                    before = _stamp(os.fstat(stream.fileno()))
                    data = stream.read()
                    after = _stamp(os.fstat(stream.fileno()))
            except OSError as exc:
                raise PolicyError(f"domain-native input changed during resolution: {item.role}: {item.path}: {exc}") from exc
            if before != after or after != item.stamp or hashlib.sha256(data).hexdigest() != item.sha256:
                raise PolicyError(f"domain-native input changed during resolution: {item.role}: {item.path}")
        for item in self._absent.values():
            self._verify_absent(item)


def normalize_tier(value: str) -> str:
    """Return the stable grounding class, ignoring free-text annotations."""
    token = re.split(r"\s+(?:—|–|-)\s+", value.strip().lower(), maxsplit=1)[0].strip()
    return {"full-text-pass": "full-read", "section-read-verified": "section-read"}.get(token, token)


def grounding_admitted(value: str) -> bool:
    return normalize_tier(value) not in {"stub", "unresolved"}


def _effective_warrant_scope(member: dict[str, Any]) -> str:
    return member.get("warrant_scope", "both")


def surface_exemplar_members(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Return admitted register-definition members usable as surface exemplars."""
    members = profile["domain_native_register"]["exemplar_members"]
    return [copy.deepcopy(item) for item in members if _effective_warrant_scope(item) == "both"]


def argument_exemplar_members(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Return all admitted register-definition members for argument warrant."""
    return [copy.deepcopy(item) for item in profile["domain_native_register"]["exemplar_members"]]


def _source_metadata(text: str, fallback: str) -> tuple[str, str | None]:
    match = re.search(r"(?mi)^\s*grounding_status\s*:\s*['\"]?([^\r\n'\"]+)", text)
    source = re.search(r"(?mi)^\s*source_loc\s*:\s*['\"]?([^\r\n'\"]+)", text)
    return (match.group(1).strip() if match else fallback, source.group(1).strip() if source else None)


def _live_grounding_status(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PolicyError(f"exemplar source page unreadable: {path}: {exc}") from exc
    match = re.search(r"(?mi)^\s*grounding_status\s*:\s*['\"]?([^\r\n'\"]+)", text)
    if match is None:
        raise PolicyError(f"exemplar source page lacks live grounding_status: {path}")
    grounding = match.group(1).strip()
    if not grounding_admitted(grounding):
        raise PolicyError(f"exemplar grounding tier is denied for {path.stem}: {normalize_tier(grounding)}")
    return normalize_tier(grounding)


def _utf8_key(value: str) -> bytes:
    return value.encode("utf-8")


def validate_graph_semantic_eligibility(
    graph: dict[str, Any], contract: dict[str, Any]
) -> dict[str, str]:
    """Refuse provisional graph material before any semantic pin is computed."""
    modes = contract.get("extraction_modes")
    statuses = contract.get("semantic_statuses")
    failure_code = contract.get("failure_code")
    if (
        not isinstance(modes, list)
        or not modes
        or not all(isinstance(value, str) and value for value in modes)
        or not isinstance(statuses, list)
        or not statuses
        or not all(isinstance(value, str) and value for value in statuses)
        or contract.get("semantic_scope_required") is not True
        or contract.get("inventory_directories") != ["wiki/sources", "wiki/concepts", "wiki/entities", "wiki/syntheses"]
        or contract.get("inventory_root_files") != ["wiki/identity-sensitive-re-for-delegated-agency.md"]
        or contract.get("inventory_digest_required") is not True
        or failure_code != "GRAPH-SEMANTIC-INELIGIBLE"
    ):
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: malformed semantic eligibility contract")
    metadata = graph.get("graph")
    if not isinstance(metadata, dict):
        raise PolicyError(f"{failure_code}: graph metadata object is required")
    # AGGREGATE, DO NOT SHORT-CIRCUIT. The first cut raised on the first
    # mismatch, which made `extraction_mode` the only visible defect on a
    # structural-only graph and hid the fact that the same graph also carries
    # none of the thirteen required semantic-provenance keys. A caller reading
    # that single reason could conclude that flipping the mode is a repair. It
    # is not: it only relocates the refusal. Every independently checkable
    # defect is collected and reported in one refusal so the true remaining
    # distance to eligibility is legible from a single run. Recorded
    # 2026-08-06. Single-defect messages stay byte-identical to the previous
    # contract, so existing needle assertions are unaffected.
    reasons: list[str] = []
    extraction_mode = metadata.get("extraction_mode")
    mode_admitted = extraction_mode in modes
    if not mode_admitted:
        reasons.append(
            f"extraction_mode {extraction_mode!r} is not one of {sorted(modes)}"
        )
    semantic_status = metadata.get("semantic_status")
    status_admitted = semantic_status in statuses
    if not status_admitted:
        reasons.append(
            f"semantic_status {semantic_status!r} is not one of {sorted(statuses)}"
        )
    if (
        mode_admitted
        and status_admitted
        and (extraction_mode, semantic_status) not in {
            ("semantic", "complete"),
            ("hybrid-structural-semantic", "validated"),
        }
    ):
        reasons.append(f"extraction mode/status pair is not admitted: {extraction_mode}/{semantic_status}")
    semantic_scope = metadata.get("semantic_scope") or metadata.get("semantic_scope_note")
    if not isinstance(semantic_scope, str) or not semantic_scope.strip():
        reasons.append("non-empty semantic_scope is required")
    required_metadata = (
        "semantic_manifest", "semantic_manifest_sha256", "semantic_audit",
        "semantic_audit_sha256", "semantic_outputs_sha256", "semantic_output_files",
        "semantic_report", "semantic_receipt", "semantic_pages_expected",
        "semantic_pages_represented", "research_inventory_sha256",
        "semantic_node_count", "semantic_edge_count",
    )
    missing = [key for key in required_metadata if key not in metadata]
    if missing:
        reasons.append(f"required semantic provenance metadata missing: {missing}")
    for key in ("semantic_manifest", "semantic_audit", "semantic_report", "semantic_receipt"):
        if key in metadata and (not isinstance(metadata[key], str) or not metadata[key].strip()):
            reasons.append(f"{key} must be a non-empty relative path")
    for key in ("semantic_manifest_sha256", "semantic_audit_sha256", "semantic_outputs_sha256", "research_inventory_sha256"):
        if key in metadata and (
            not isinstance(metadata[key], str)
            or re.fullmatch(r"[0-9a-f]{64}", metadata[key]) is None
        ):
            reasons.append(f"{key} must be a lowercase SHA-256")
    if "semantic_output_files" in metadata:
        output_files = metadata["semantic_output_files"]
        if not isinstance(output_files, list) or not output_files:
            reasons.append("semantic_output_files must be a non-empty array")
        else:
            seen_output_paths: set[str] = set()
            rows_valid = True
            for row in output_files:
                if (
                    not isinstance(row, dict)
                    or set(row) != {"path", "sha256"}
                    or not isinstance(row.get("path"), str)
                    or not row["path"].strip()
                    or row["path"] in seen_output_paths
                    or not isinstance(row.get("sha256"), str)
                    or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None
                ):
                    rows_valid = False
                    break
                seen_output_paths.add(row["path"])
            if not rows_valid:
                reasons.append("semantic_output_files contains an invalid or duplicate row")
            elif [row["path"] for row in output_files] != sorted(
                (row["path"] for row in output_files), key=_utf8_key
            ):
                reasons.append("semantic_output_files must be sorted by path")
    counts_valid: dict[str, bool] = {}
    for key in ("semantic_pages_expected", "semantic_pages_represented", "semantic_node_count", "semantic_edge_count"):
        valid = (
            key in metadata
            and isinstance(metadata[key], int)
            and not isinstance(metadata[key], bool)
            and metadata[key] >= 1
        )
        counts_valid[key] = valid
        if key in metadata and not valid:
            reasons.append(f"{key} must be a positive integer")
    if (
        counts_valid["semantic_pages_expected"]
        and counts_valid["semantic_pages_represented"]
        and metadata["semantic_pages_expected"] != metadata["semantic_pages_represented"]
    ):
        reasons.append("semantic_pages expected/represented mismatch")
    if reasons:
        raise PolicyError(f"{failure_code}: " + "; ".join(reasons))
    return {
        "extraction_mode": extraction_mode,
        "semantic_status": semantic_status,
        "semantic_scope": semantic_scope.strip(),
    }


def resolve_domain_native_register(
    profile: dict[str, Any], *, wiki_root: Path | None = None,
    workspace_root: Path | None = None, harness_root: Path | None = None,
    _snapshot_hook: Callable[[str, str, Path | None], None] | None = None,
    _ingested_key: str | None = None,
) -> dict[str, Any]:
    """Resolve the two semantic register views.

    Omitting wiki/workspace roots uses profile ``corpus_binding.path_roots``.
    Fixture callers may inject alternate roots (recorded as override).
    """
    model = profile.get("domain_native_register")
    if not isinstance(model, dict):
        raise PolicyError("profile.domain_native_register is missing")
    wiki_root, workspace_root, harness_root, path_roots_meta = _resolve_register_roots(
        profile, wiki_root=wiki_root, workspace_root=workspace_root, harness_root=harness_root
    )
    profile_wiki = Path(path_roots_meta["profile_path_roots"]["wiki_root"])
    graph_rel = model["corpus_binding"]["graph"]["path"]
    fresh_match = FRESH_SEMANTIC_GRAPH_RE.fullmatch(graph_rel.replace("\\", "/"))
    fresh_transaction_id = fresh_match.group("transaction_id") if fresh_match else None
    graph_path = _contained(workspace_root, graph_rel)
    snapshots = _SnapshotSet(_snapshot_hook)
    try:
        graph_snapshot = snapshots.capture(graph_path, "graph_provenance_only")
        graph = json.loads(graph_snapshot.text())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PolicyError(f"domain-native graph unreadable: {graph_path}: {exc}") from exc
    if not isinstance(graph, dict):
        raise PolicyError("domain-native graph root must be an object")
    graph_eligibility = validate_graph_semantic_eligibility(
        graph, model["corpus_binding"]["graph"]["semantic_eligibility"]
    )
    nodes = graph.get("nodes"); links = graph.get("links")
    if not isinstance(nodes, list) or not isinstance(links, list):
        raise PolicyError("domain-native graph requires nodes and links arrays")
    metadata = graph["graph"]
    transaction_prefix: str | None = None
    if fresh_transaction_id is not None:
        transaction_prefix = (
            f"graphify-out/semantic-qualifications/{fresh_transaction_id}"
        )
        expected_paths = {
            "semantic_manifest": f"{transaction_prefix}/manifest.json",
            "semantic_audit": f"{transaction_prefix}/audit.json",
            "semantic_report": f"{transaction_prefix}/QUALIFICATION_REPORT.md",
            "semantic_receipt": f"{transaction_prefix}/receipt.json",
        }
        identity_fields = (
            "semantic_producer", "semantic_producer_model",
            "semantic_auditor", "semantic_auditor_model",
        )
        if (
            metadata.get("publication_mode") != "consumer-only-semantic-composite"
            or metadata.get("semantic_transaction_id") != fresh_transaction_id
            or any(metadata.get(key) != value for key, value in expected_paths.items())
            or any(not isinstance(metadata.get(key), str) or not metadata[key].strip() for key in identity_fields)
            or metadata.get("semantic_producer") not in ALLOWED_SEMANTIC_AUDIT_REVIEWERS
            or metadata.get("semantic_auditor") not in ALLOWED_SEMANTIC_AUDIT_REVIEWERS
            or metadata.get("semantic_producer") == metadata.get("semantic_auditor")
        ):
            raise PolicyError(
                "GRAPH-SEMANTIC-INELIGIBLE: fresh semantic transaction identity, paths, or model roles are invalid"
            )
        base_graph_path = _contained(wiki_root, "graphify-out/graph.json")
        base_graph_snapshot = snapshots.capture(base_graph_path, "semantic_base_graph")
        if metadata.get("base_graph_sha256") != base_graph_snapshot.sha256:
            raise PolicyError(
                "GRAPH-SEMANTIC-INELIGIBLE: fresh semantic transaction base graph binding is stale"
            )
    semantic_nodes = [node for node in nodes if isinstance(node, dict) and node.get("semantic_status") == "validated"]
    semantic_edges = [edge for edge in links if isinstance(edge, dict) and edge.get("semantic_status") == "validated" and isinstance(edge.get("semantic_edge_id"), str)]
    if len(semantic_nodes) != metadata["semantic_node_count"]:
        raise PolicyError(f"GRAPH-SEMANTIC-INELIGIBLE: semantic_node_count mismatch: metadata={metadata['semantic_node_count']} actual={len(semantic_nodes)}")
    if len(semantic_edges) != metadata["semantic_edge_count"]:
        raise PolicyError(f"GRAPH-SEMANTIC-INELIGIBLE: semantic_edge_count mismatch: metadata={metadata['semantic_edge_count']} actual={len(semantic_edges)}")
    semantic_edge_by_id = {edge["semantic_edge_id"]: edge for edge in semantic_edges}
    if len(semantic_edge_by_id) != len(semantic_edges):
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic edge identifiers are duplicated")
    semantic_node_by_id = {node.get("id"): node for node in semantic_nodes}
    if len(semantic_node_by_id) != len(semantic_nodes) or None in semantic_node_by_id:
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic node identifiers are missing or duplicated")
    semantic_page_sources = {node.get("source_file") for node in semantic_nodes if isinstance(node.get("source_file"), str)}
    if len(semantic_page_sources) != metadata["semantic_pages_represented"]:
        raise PolicyError(f"GRAPH-SEMANTIC-INELIGIBLE: semantic page coverage mismatch: metadata={metadata['semantic_pages_represented']} actual={len(semantic_page_sources)}")
    semantic_artifacts: list[tuple[str, Any]] = []
    for role, path_key, hash_key in (
        ("semantic_manifest", "semantic_manifest", "semantic_manifest_sha256"),
        ("semantic_audit", "semantic_audit", "semantic_audit_sha256"),
    ):
        artifact_path = _contained(wiki_root, metadata[path_key])
        artifact_snapshot = snapshots.capture(artifact_path, role)
        if artifact_snapshot.sha256 != metadata[hash_key]:
            raise PolicyError(f"GRAPH-SEMANTIC-INELIGIBLE: {role} hash mismatch")
        semantic_artifacts.append((role, artifact_snapshot))
    output_binding_rows: list[dict[str, str]] = []
    output_snapshots: list[Any] = []
    for index, output_row in enumerate(metadata["semantic_output_files"]):
        output_path = _contained(wiki_root, output_row["path"])
        output_snapshot = snapshots.capture(output_path, f"semantic_output_{index + 1:03d}")
        if output_snapshot.sha256 != output_row["sha256"]:
            raise PolicyError(f"GRAPH-SEMANTIC-INELIGIBLE: semantic output hash mismatch: {output_row['path']}")
        output_binding_rows.append({"path": output_row["path"], "sha256": output_snapshot.sha256})
        output_snapshots.append(output_snapshot)
        semantic_artifacts.append((f"semantic_output_{index + 1:03d}", output_snapshot))
    output_binding_payload = "\n".join(
        f"{row['path']}\t{row['sha256']}" for row in output_binding_rows
    ).encode("utf-8")
    output_binding_sha256 = hashlib.sha256(output_binding_payload).hexdigest()
    if output_binding_sha256 != metadata["semantic_outputs_sha256"]:
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic output aggregate hash mismatch")
    report_path = _contained(wiki_root, metadata["semantic_report"])
    report_snapshot = snapshots.capture(report_path, "semantic_report")
    semantic_artifacts.append(("semantic_report", report_snapshot))
    receipt_path = _contained(wiki_root, metadata["semantic_receipt"])
    receipt_snapshot = snapshots.capture(receipt_path, "semantic_receipt")
    try:
        receipt = json.loads(receipt_snapshot.text())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PolicyError(f"GRAPH-SEMANTIC-INELIGIBLE: semantic receipt unreadable: {exc}") from exc
    if not isinstance(receipt, dict):
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic receipt must be a JSON object")
    if receipt.get("schema_version") != SEMANTIC_ARTIFACT_SCHEMA_VERSION:
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic receipt schema_version is unsupported")
    receipt_expected = {
        "final_graph_sha256": graph_snapshot.sha256,
        "manifest_sha256": metadata["semantic_manifest_sha256"],
        "audit_sha256": metadata["semantic_audit_sha256"],
        "semantic_outputs_sha256": metadata["semantic_outputs_sha256"],
        "research_inventory_sha256": metadata["research_inventory_sha256"],
        "report_sha256": report_snapshot.sha256,
        "extraction_mode": graph_eligibility["extraction_mode"],
        "semantic_status": graph_eligibility["semantic_status"],
        "semantic_scope": graph_eligibility["semantic_scope"],
        "page_count": metadata["semantic_pages_represented"],
        "semantic_node_count": metadata["semantic_node_count"],
        "semantic_edge_count": metadata["semantic_edge_count"],
    }
    for key, expected_value in receipt_expected.items():
        if receipt.get(key) != expected_value:
            raise PolicyError(f"GRAPH-SEMANTIC-INELIGIBLE: semantic receipt {key} mismatch")
    rollback_artifact = None
    if fresh_transaction_id is not None and transaction_prefix is not None:
        fresh_identity = {
            "transaction_id": fresh_transaction_id,
            "publication_mode": "consumer-only-semantic-composite",
            "producer": metadata["semantic_producer"],
            "producer_model": metadata["semantic_producer_model"],
            "auditor": metadata["semantic_auditor"],
            "auditor_model": metadata["semantic_auditor_model"],
            "base_graph_sha256": metadata["base_graph_sha256"],
        }
        if any(receipt.get(key) != value for key, value in fresh_identity.items()):
            raise PolicyError(
                "GRAPH-SEMANTIC-INELIGIBLE: fresh semantic receipt identity or model provenance mismatch"
            )
        expected_rollback_path = f"{transaction_prefix}/rollback.json"
        if receipt.get("rollback_path") != expected_rollback_path:
            raise PolicyError(
                "GRAPH-SEMANTIC-INELIGIBLE: fresh semantic receipt rollback path is not transaction-local"
            )
        rollback_snapshot = snapshots.capture(
            _contained(wiki_root, expected_rollback_path), "semantic_rollback"
        )
        if receipt.get("rollback_sha256") != rollback_snapshot.sha256:
            raise PolicyError(
                "GRAPH-SEMANTIC-INELIGIBLE: fresh semantic receipt rollback hash mismatch"
            )
        semantic_artifacts.append(("semantic_rollback", rollback_snapshot))
        try:
            rollback_artifact = json.loads(rollback_snapshot.text())
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise PolicyError(
                f"GRAPH-SEMANTIC-INELIGIBLE: semantic rollback unreadable: {exc}"
            ) from exc
        if (
            not isinstance(rollback_artifact, dict)
            or rollback_artifact.get("schema_version") != SEMANTIC_ARTIFACT_SCHEMA_VERSION
            or rollback_artifact.get("transaction_id") != fresh_transaction_id
            or rollback_artifact.get("live_graph_mutated") is not False
            or rollback_artifact.get("base_graph_path") != "graphify-out/graph.json"
            or rollback_artifact.get("base_graph_sha256") != metadata["base_graph_sha256"]
        ):
            raise PolicyError(
                "GRAPH-SEMANTIC-INELIGIBLE: fresh semantic rollback provenance is invalid"
            )
        for role, filename, receipt_hash_key in (
            ("semantic_audit_request", "audit_request.json", "audit_request_sha256"),
            ("semantic_audit_prompt", "audit.prompt.md", "audit_prompt_sha256"),
            ("semantic_audit_submission", "audit.submission.json", "audit_submission_sha256"),
        ):
            artifact_path = _contained(wiki_root, f"{transaction_prefix}/{filename}")
            artifact_snapshot = snapshots.capture(artifact_path, role)
            if receipt.get(receipt_hash_key) != artifact_snapshot.sha256:
                raise PolicyError(
                    f"GRAPH-SEMANTIC-INELIGIBLE: fresh semantic receipt {receipt_hash_key} mismatch"
                )
            semantic_artifacts.append((role, artifact_snapshot))
    try:
        manifest_artifact = json.loads(semantic_artifacts[0][1].text())
        audit_artifact = json.loads(semantic_artifacts[1][1].text())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PolicyError(f"GRAPH-SEMANTIC-INELIGIBLE: semantic manifest/audit unreadable: {exc}") from exc
    if not isinstance(manifest_artifact, dict) or not isinstance(audit_artifact, dict):
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic manifest and audit must be JSON objects")
    if manifest_artifact.get("schema_version") != SEMANTIC_ARTIFACT_SCHEMA_VERSION:
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic manifest schema_version is unsupported")
    if audit_artifact.get("schema_version") != SEMANTIC_ARTIFACT_SCHEMA_VERSION:
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic audit schema_version is unsupported")
    if fresh_transaction_id is not None:
        fresh_manifest_expected = {
            "transaction_id": fresh_transaction_id,
            "publication_mode": "consumer-only-semantic-composite",
            "producer": metadata["semantic_producer"],
            "producer_model": metadata["semantic_producer_model"],
            "base_graph_path": "graphify-out/graph.json",
            "base_graph_sha256": metadata["base_graph_sha256"],
            "structural_graph_sha256": metadata["base_graph_sha256"],
        }
        if any(manifest_artifact.get(key) != value for key, value in fresh_manifest_expected.items()):
            raise PolicyError(
                "GRAPH-SEMANTIC-INELIGIBLE: fresh semantic manifest identity or model provenance mismatch"
            )
        fresh_audit_expected = {
            "transaction_id": fresh_transaction_id,
            "producer": metadata["semantic_producer"],
            "producer_model": metadata["semantic_producer_model"],
            "auditor": metadata["semantic_auditor"],
            "auditor_model": metadata["semantic_auditor_model"],
            "reviewer": metadata["semantic_auditor"],
            "reviewer_model": metadata["semantic_auditor_model"],
        }
        if any(audit_artifact.get(key) != value for key, value in fresh_audit_expected.items()):
            raise PolicyError(
                "GRAPH-SEMANTIC-INELIGIBLE: fresh semantic audit identity or model provenance mismatch"
            )
    manifest_pages = manifest_artifact.get("pages")
    if not isinstance(manifest_pages, list) or any(
        not isinstance(row, dict) or not isinstance(row.get("source_file"), str) or not row["source_file"]
        for row in manifest_pages
    ):
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic manifest pages are malformed")
    manifest_page_sources = {row["source_file"] for row in manifest_pages}
    if len(manifest_page_sources) != len(manifest_pages):
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic manifest contains duplicate pages")
    semantic_edge_sources = {edge.get("source_file") for edge in semantic_edges if isinstance(edge.get("source_file"), str)}
    if manifest_artifact.get("page_count") != metadata["semantic_pages_represented"] or len(manifest_page_sources) != metadata["semantic_pages_represented"]:
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic manifest page_count mismatch")
    if manifest_artifact.get("chunk_count") != len(output_binding_rows):
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic manifest/output chunk count mismatch")
    manifest_chunks = manifest_artifact.get("chunks")
    if not isinstance(manifest_chunks, list) or len(manifest_chunks) != len(output_binding_rows):
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic manifest chunks are malformed")
    manifest_page_by_source = {row["source_file"]: row for row in manifest_pages}
    manifest_parent = PurePosixPath(metadata["semantic_manifest"]).parent
    expected_output_paths: list[str] = []
    chunk_source_files: list[str] = []
    seen_chunk_ids: set[str] = set()
    for chunk in manifest_chunks:
        chunk_keys = frozenset(chunk) if isinstance(chunk, dict) else frozenset()
        if (
            not isinstance(chunk, dict)
            or chunk_keys not in ({
                frozenset({
                    "chunk_id", "page_count", "source_files",
                    "request_sha256", "prompt_sha256",
                }),
            } if fresh_transaction_id is not None else {
                frozenset({"chunk_id", "page_count", "source_files"}),
                frozenset({
                    "chunk_id", "page_count", "source_files",
                    "request_sha256", "prompt_sha256",
                }),
            })
            or not isinstance(chunk.get("chunk_id"), str)
            or chunk["chunk_id"] in seen_chunk_ids
            or not isinstance(chunk.get("source_files"), list)
            or chunk.get("page_count") != len(chunk["source_files"])
            or any(not isinstance(value, str) for value in chunk["source_files"])
        ):
            raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic manifest chunk contract is invalid")
        seen_chunk_ids.add(chunk["chunk_id"])
        expected_output_paths.append((manifest_parent / "chunks" / f"{chunk['chunk_id']}.output.json").as_posix())
        chunk_source_files.extend(chunk["source_files"])
        if "request_sha256" in chunk:
            for role, suffix, hash_key in (
                ("semantic_model_request", "request.json", "request_sha256"),
                ("semantic_model_prompt", "prompt.md", "prompt_sha256"),
            ):
                expected_hash = chunk.get(hash_key)
                if not isinstance(expected_hash, str) or re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None:
                    raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic model prompt/request hash is malformed")
                artifact_relative = (
                    manifest_parent / "chunks" / f"{chunk['chunk_id']}.{suffix}"
                ).as_posix()
                artifact_snapshot = snapshots.capture(
                    _contained(wiki_root, artifact_relative),
                    f"{role}_{chunk['chunk_id']}",
                )
                if artifact_snapshot.sha256 != expected_hash:
                    raise PolicyError(
                        "GRAPH-SEMANTIC-INELIGIBLE: semantic model prompt/request hash mismatch"
                    )
                semantic_artifacts.append((f"{role}_{chunk['chunk_id']}", artifact_snapshot))
    if fresh_transaction_id is not None and transaction_prefix is not None:
        created_rows = rollback_artifact.get("created_paths") if isinstance(rollback_artifact, dict) else None
        if (
            not isinstance(created_rows, list)
            or any(
                not isinstance(row, dict)
                or set(row) != {"path", "sha256"}
                or not isinstance(row.get("path"), str)
                or not row["path"]
                or SHA256_RE.fullmatch(str(row.get("sha256"))) is None
                for row in created_rows
            )
        ):
            raise PolicyError(
                "GRAPH-SEMANTIC-INELIGIBLE: fresh semantic rollback inventory is malformed"
            )
        created_paths = [row["path"] for row in created_rows]
        if (
            created_paths != sorted(created_paths, key=lambda value: value.encode("utf-8"))
            or len(set(created_paths)) != len(created_paths)
            or any(PurePosixPath(value).is_absolute() or ".." in PurePosixPath(value).parts for value in created_paths)
        ):
            raise PolicyError(
                "GRAPH-SEMANTIC-INELIGIBLE: fresh semantic rollback inventory is not canonical or contained"
            )
        stage_root = _contained(wiki_root, transaction_prefix)
        live_stage_files = sorted(
            (
                path for path in stage_root.rglob("*")
                if path.is_file() and path.name not in {"rollback.json", "receipt.json"}
            ),
            key=lambda path: path.relative_to(stage_root).as_posix().encode("utf-8"),
        )
        live_rows = []
        for index, path in enumerate(live_stage_files):
            snapshot = snapshots.capture(path, f"semantic_transaction_file_{index + 1:03d}")
            live_rows.append({
                "path": path.relative_to(stage_root).as_posix(),
                "sha256": snapshot.sha256,
            })
        if created_rows != live_rows:
            raise PolicyError(
                "GRAPH-SEMANTIC-INELIGIBLE: fresh semantic rollback inventory does not bind the complete transaction"
            )
    if [row["path"] for row in output_binding_rows] != expected_output_paths:
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic output paths differ from manifest chunks")
    if chunk_source_files != [row["source_file"] for row in manifest_pages] or len(set(chunk_source_files)) != len(chunk_source_files):
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic manifest chunk/page partition mismatch")
    derived_node_ids: set[str] = set()
    derived_edge_ids: set[str] = set()
    for chunk, output_snapshot in zip(manifest_chunks, output_snapshots):
        try:
            output = json.loads(output_snapshot.text())
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise PolicyError(f"GRAPH-SEMANTIC-INELIGIBLE: semantic output unreadable: {exc}") from exc
        results = output.get("pages") if isinstance(output, dict) else None
        if not isinstance(output, dict) or output.get("schema_version") != SEMANTIC_ARTIFACT_SCHEMA_VERSION or output.get("chunk_id") != chunk["chunk_id"] or not isinstance(results, list) or len(results) != chunk["page_count"]:
            raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic output schema/chunk/page count mismatch")
        if fresh_transaction_id is not None and (
            output.get("producer") != metadata["semantic_producer"]
            or output.get("producer_model") != metadata["semantic_producer_model"]
        ):
            raise PolicyError(
                "GRAPH-SEMANTIC-INELIGIBLE: fresh semantic output producer or model provenance mismatch"
            )
        if [row.get("source_file") for row in results if isinstance(row, dict)] != chunk["source_files"]:
            raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic output page partition mismatch")
        for result in results:
            spec = manifest_page_by_source[result["source_file"]]
            if result.get("sha256") != spec.get("sha256") or not isinstance(result.get("nodes"), list) or not isinstance(result.get("edges"), list):
                raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic output page/hash/payload mismatch")
            for output_node in result["nodes"]:
                node_id = output_node.get("id") if isinstance(output_node, dict) else None
                actual_node = semantic_node_by_id.get(node_id)
                if actual_node is None or node_id in derived_node_ids:
                    raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic output node is absent or duplicated in graph")
                if "norm_label" in actual_node:
                    label = output_node.get("label") if isinstance(output_node, dict) else None
                    expected_norm_label = "".join(
                        character
                        for character in unicodedata.normalize("NFKD", label or "")
                        if not unicodedata.combining(character)
                    ).lower()
                    if actual_node.get("norm_label") != expected_norm_label:
                        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic graph norm_label differs from the output label")
                normalized_node = {key:value for key,value in actual_node.items() if key not in {"community", "extraction_status", "norm_label"}}
                normalized_node["semantic_status"] = "candidate"
                if normalized_node != output_node:
                    raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic output node payload differs from graph")
                derived_node_ids.add(node_id)
            for edge_index, output_edge in enumerate(result["edges"]):
                if not isinstance(output_edge, dict):
                    raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic output edge is malformed")
                if fresh_transaction_id is not None:
                    confidence = output_edge.get("confidence")
                    warrant = output_edge.get("warrant")
                    if (
                        warrant not in {"model-textual", "model-inferential"}
                        or (confidence == "EXTRACTED" and warrant != "model-textual")
                        or (confidence in {"INFERRED", "AMBIGUOUS"} and warrant != "model-inferential")
                    ):
                        raise PolicyError(
                            "GRAPH-SEMANTIC-INELIGIBLE: fresh semantic edge warrant does not match model confidence"
                        )
                expected_edge_id = f"{chunk['chunk_id']}:" + hashlib.sha256(
                    (result["source_file"] + ":" + str(edge_index) + ":" + str(output_edge.get("source")) + ":" + str(output_edge.get("target"))).encode("utf-8")
                ).hexdigest()[:16]
                actual_edge = semantic_edge_by_id.get(expected_edge_id)
                actual_edge_id = expected_edge_id
                if actual_edge is None:
                    fallback_matches = []
                    for edge_id, candidate_edge in semantic_edge_by_id.items():
                        if edge_id in derived_edge_ids:
                            continue
                        candidate_endpoints = (candidate_edge.get("source"), candidate_edge.get("target"))
                        output_endpoints = (output_edge.get("source"), output_edge.get("target"))
                        candidate_normalized = {key:value for key,value in candidate_edge.items() if key not in {"_src", "_tgt", "semantic_edge_id", "semantic_status"}}
                        candidate_normalized["source"], candidate_normalized["target"] = output_endpoints
                        if candidate_endpoints in {output_endpoints, output_endpoints[::-1]} and candidate_normalized == output_edge:
                            fallback_matches.append((edge_id, candidate_edge))
                    if len(fallback_matches) != 1:
                        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic output edge id is absent or ambiguous in graph")
                    actual_edge_id, actual_edge = fallback_matches[0]
                if actual_edge_id in derived_edge_ids:
                    raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic output edge is duplicated in graph")
                actual_endpoints = (actual_edge.get("source"), actual_edge.get("target"))
                output_endpoints = (output_edge.get("source"), output_edge.get("target"))
                if actual_endpoints not in {output_endpoints, output_endpoints[::-1]}:
                    raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic output edge endpoints differ from graph")
                normalized_edge = {key:value for key,value in actual_edge.items() if key not in {"_src", "_tgt", "semantic_edge_id", "semantic_status"}}
                normalized_edge["source"], normalized_edge["target"] = output_endpoints
                if normalized_edge != output_edge:
                    raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic output edge payload is absent or ambiguous in graph")
                derived_edge_ids.add(actual_edge_id)
    if derived_node_ids != set(semantic_node_by_id) or derived_edge_ids != set(semantic_edge_by_id):
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic outputs do not exactly derive graph nodes and edges")
    if manifest_page_sources != semantic_page_sources or manifest_page_sources != semantic_edge_sources:
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic manifest/node/edge page sets differ")
    manifest_hash_rows = [
        {"source_file": row["source_file"], "sha256": row.get("sha256")}
        for row in manifest_pages
    ]
    if any(not isinstance(row["sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None for row in manifest_hash_rows):
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic manifest page hashes are malformed")
    expected_manifest_order = sorted(
        manifest_hash_rows, key=lambda row: row["source_file"].encode("utf-8")
    )
    if manifest_hash_rows != expected_manifest_order:
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic manifest pages are not canonically ordered")
    for row in manifest_hash_rows:
        _contained(wiki_root, row["source_file"])
    manifest_inventory_payload = "\n".join(
        f"{row['source_file']}\t{row['sha256']}" for row in manifest_hash_rows
    ).encode("utf-8")
    manifest_inventory_sha256 = hashlib.sha256(manifest_inventory_payload).hexdigest()
    if manifest_artifact.get("research_inventory_sha256") != manifest_inventory_sha256:
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic manifest inventory hash mismatch")
    if metadata["research_inventory_sha256"] != manifest_inventory_sha256:
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic graph inventory binding mismatch")
    live_inventory_paths: list[Path] = []
    for relative_dir in model["corpus_binding"]["graph"]["semantic_eligibility"]["inventory_directories"]:
        live_inventory_paths.extend(_contained(wiki_root, relative_dir).glob("*.md"))
    for relative_file in model["corpus_binding"]["graph"]["semantic_eligibility"]["inventory_root_files"]:
        candidate = _contained(wiki_root, relative_file)
        if candidate.is_file():
            live_inventory_paths.append(candidate)
    live_inventory_paths = sorted(set(live_inventory_paths), key=lambda path: path.relative_to(wiki_root).as_posix().encode("utf-8"))
    live_inventory_rows = []
    for inventory_path in live_inventory_paths:
        inventory_snapshot = snapshots.capture(inventory_path, "semantic_inventory_page")
        live_inventory_rows.append({"source_file":inventory_path.relative_to(wiki_root).as_posix(), "sha256":inventory_snapshot.sha256})
    manifest_hash_by_source = {row["source_file"]: row["sha256"] for row in manifest_hash_rows}
    live_hash_by_source = {row["source_file"]: row["sha256"] for row in live_inventory_rows}
    missing_pinned_pages = sorted(set(manifest_hash_by_source) - set(live_hash_by_source), key=_utf8_key)
    if missing_pinned_pages:
        raise PolicyError(
            "GRAPH-SEMANTIC-INELIGIBLE: pinned semantic page missing from live wiki: "
            + ", ".join(missing_pinned_pages)
        )
    mismatched_pinned_pages = sorted(
        (
            source_file for source_file, pinned_sha256 in manifest_hash_by_source.items()
            if live_hash_by_source[source_file] != pinned_sha256
        ),
        key=_utf8_key,
    )
    if mismatched_pinned_pages:
        raise PolicyError(
            "GRAPH-SEMANTIC-INELIGIBLE: pinned semantic page hash mismatch: "
            + ", ".join(mismatched_pinned_pages)
        )
    enrichment_candidates = sorted(set(live_hash_by_source) - set(manifest_hash_by_source), key=_utf8_key)
    if audit_artifact.get("manifest_sha256") != metadata["semantic_manifest_sha256"]:
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic audit manifest binding mismatch")
    if audit_artifact.get("semantic_outputs_sha256") != metadata["semantic_outputs_sha256"]:
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic audit output binding mismatch")
    counts = audit_artifact.get("verdict_counts")
    reviewers = audit_artifact.get("reviewers")
    multi_reviewer = reviewers is not None
    if multi_reviewer:
        if (
            not isinstance(reviewers, list)
            or not reviewers
            or reviewers != sorted(set(reviewers), key=lambda value: value.encode("utf-8") if isinstance(value, str) else b"")
            or not set(reviewers) <= ALLOWED_SEMANTIC_AUDIT_REVIEWERS
            or audit_artifact.get("reviewer") != (reviewers[0] if len(reviewers) == 1 else "multiple")
        ):
            raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic audit reviewer provenance is invalid")
    elif audit_artifact.get("reviewer") not in ALLOWED_SEMANTIC_AUDIT_REVIEWERS:
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic audit reviewer is not approved")
    if not isinstance(counts, dict) or counts.get("unclear") != 0 or counts.get("unsupported") != 0 or counts.get("supported") != audit_artifact.get("sample_count"):
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic audit is absent, incomplete, or not fully supported")
    audit_rows = audit_artifact.get("edges")
    if not isinstance(audit_rows, list) or len(audit_rows) != audit_artifact.get("sample_count") or len({row.get("semantic_edge_id") for row in audit_rows if isinstance(row, dict)}) != len(audit_rows) or any(not isinstance(row, dict) or row.get("verdict") != "supported" or not isinstance(row.get("note"), str) or not row["note"].strip() for row in audit_rows):
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic audit rows are incomplete, duplicated, or not fully supported")
    if multi_reviewer:
        row_reviewer_counts = {
            reviewer: sum(1 for row in audit_rows if row.get("reviewer") == reviewer)
            for reviewer in reviewers
        }
        if (
            any(row.get("reviewer") not in reviewers for row in audit_rows)
            or audit_artifact.get("reviewer_counts") != row_reviewer_counts
            or sum(row_reviewer_counts.values()) != len(audit_rows)
        ):
            raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic audit row reviewer provenance mismatch")
    audit_edge_ids = {row["semantic_edge_id"] for row in audit_rows}
    if not audit_edge_ids <= set(semantic_edge_by_id):
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic audit references unknown graph edges")
    audit_page_sources = {semantic_edge_by_id[edge_id]["source_file"] for edge_id in audit_edge_ids}
    if audit_page_sources != manifest_page_sources:
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic audit does not cover every manifest page")
    semantic_sorted = sorted(semantic_edges, key=lambda edge: edge["semantic_edge_id"].encode("utf-8"))
    by_semantic_page: dict[str, list[dict[str, Any]]] = {}
    for edge in semantic_sorted:
        by_semantic_page.setdefault(edge["source_file"], []).append(edge)
    expected_audit_edges = [edges[0] for _, edges in sorted(by_semantic_page.items(), key=lambda item:item[0].encode("utf-8"))]
    chosen_audit_ids = {edge["semantic_edge_id"] for edge in expected_audit_edges}
    register_seed_pages = {f"wiki/sources/{member['source_key']}.md" for member in model["exemplar_members"]}
    for edge in semantic_sorted:
        if edge["source_file"] in register_seed_pages and edge["semantic_edge_id"] not in chosen_audit_ids:
            expected_audit_edges.append(edge); chosen_audit_ids.add(edge["semantic_edge_id"])
    represented_classes = {(edge.get("relation"), edge.get("confidence")) for edge in expected_audit_edges}
    if any(not all(isinstance(value, str) and value for value in edge_class) for edge_class in represented_classes):
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic graph lacks audit relation/confidence classes")
    for edge in semantic_sorted:
        edge_class = (edge.get("relation"), edge.get("confidence"))
        if edge_class not in represented_classes:
            expected_audit_edges.append(edge); chosen_audit_ids.add(edge["semantic_edge_id"]); represented_classes.add(edge_class)
    if audit_edge_ids != {edge["semantic_edge_id"] for edge in expected_audit_edges}:
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic audit sample differs from page/seed/class policy")
    if not isinstance(audit_artifact.get("sample_count"), int) or audit_artifact["sample_count"] < metadata["semantic_pages_represented"] or receipt.get("audit_sample_count") != audit_artifact["sample_count"]:
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: semantic audit does not cover every represented page")
    by_id: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if (not isinstance(node, dict) or not isinstance(node.get("id"), str) or not node.get("id")
                or not isinstance(node.get("community"), int) or isinstance(node.get("community"), bool)
                or ("source_file" in node and node["source_file"] is not None and not isinstance(node["source_file"], str))
                or ("file_type" in node and node["file_type"] is not None and not isinstance(node["file_type"], str))):
            raise PolicyError("domain-native graph nodes require unique string id and integer community")
        if node["id"] in by_id: raise PolicyError(f"duplicate graph node id: {node['id']}")
        by_id[node["id"]] = node
    resolution: dict[str, str] = {}; ties: dict[str, list[str]] = {}; unresolved: list[str] = []
    for member in model["exemplar_members"]:
        key = member["source_key"]
        chosen = by_id.get(key)
        if chosen is None:
            source_file = f"wiki/sources/{key}.md"
            candidates = [node for node in nodes if node.get("source_file") == source_file]
            all_candidate_ids = [node["id"] for node in candidates if node.get("semantic_status") != "validated"]
            preferred = [node for node in candidates if node.get("file_type") in {"document", "source"}]
            candidates = preferred or candidates
            preferred = [node for node in candidates if node["id"].endswith("_source")]
            candidates = preferred or candidates
            candidates = sorted(candidates, key=lambda node: _utf8_key(node["id"]))
            if candidates:
                chosen = candidates[0]
                discarded = sorted((node_id for node_id in all_candidate_ids if node_id != chosen["id"]), key=_utf8_key)
                if discarded: ties[key] = discarded
        if chosen is None: unresolved.append(key)
        else: resolution[key] = chosen["id"]
    semantic_node_sources = semantic_page_sources
    for key in resolution:
        required_source = f"wiki/sources/{key}.md"
        if required_source not in semantic_node_sources or required_source not in semantic_edge_sources:
            raise PolicyError(f"GRAPH-SEMANTIC-INELIGIBLE: resolved register seed lacks semantic node/edge coverage: {required_source}")
    primary = sorted({by_id[node_id]["community"] for node_id in resolution.values()})
    primary_members = {node["id"] for node in nodes if node["community"] in primary}
    membership = set(primary_members)
    for index, link in enumerate(links):
        if not isinstance(link, dict) or not isinstance(link.get("source"), str) or not isinstance(link.get("target"), str):
            raise PolicyError(f"domain-native graph link {index} lacks canonical endpoints")
        canonical_endpoints = (link["source"], link["target"])
        serialized_endpoints = (link.get("_src"), link.get("_tgt"))
        if (
            "_src" not in link
            or "_tgt" not in link
            or serialized_endpoints not in (canonical_endpoints, canonical_endpoints[::-1])
        ):
            raise PolicyError(f"link endpoint divergence at links[{index}]")
        source, target = link["source"], link["target"]
        if source not in by_id or target not in by_id: raise PolicyError(f"domain-native graph link {index} references missing node")
        if source in primary_members and by_id[target]["community"] not in primary: membership.add(target)
        if target in primary_members and by_id[source]["community"] not in primary: membership.add(source)
    member_bytes = "\n".join(sorted(membership, key=_utf8_key)).encode("utf-8")
    attestation_pin = hashlib.sha256(member_bytes).hexdigest()
    exemplar_lines: list[str] = []; provenance: list[dict[str, str]] = []
    admitted_members: list[dict[str, Any]] = []
    missing_pdf_keys: list[str] = []
    for member in model["exemplar_members"]:
        key = member["source_key"]; source_rel = f"wiki/sources/{key}.md"; source_path = _contained(wiki_root, source_rel)
        source_snapshot = snapshots.capture(source_path, "exemplar_source_page")
        grounding, source_pdf = _source_metadata(source_snapshot.text(), member["grounding"])
        provenance.append({"role":"exemplar_source_page","path":str(source_path),"sha256":source_snapshot.sha256})
        if not grounding_admitted(grounding):
            if key == _ingested_key:
                raise PolicyError(f"exemplar grounding tier is denied for {key}: {normalize_tier(grounding)}")
            continue
        pdf_hash = "-"
        pdf_rel = source_pdf or member.get("pdf")
        if pdf_rel:
            pdf_path = _contained(wiki_root, pdf_rel)
            pdf_snapshot = snapshots.capture_optional(pdf_path, "surface_warrant_pdf")
            if pdf_snapshot is not None:
                pdf_hash = pdf_snapshot.sha256; provenance.append({"role":"surface_warrant_pdf","path":str(pdf_path),"sha256":pdf_hash})
                if wiki_root.resolve() == profile_wiki.resolve() and member.get("pdf_sha256") and pdf_hash != member["pdf_sha256"]:
                    raise PolicyError(f"expected exemplar PDF hash mismatch: {key}")
            elif key == _ingested_key:
                missing_pdf_keys.append(key)
        elif key == _ingested_key:
            missing_pdf_keys.append(key)
        exemplar_lines.append(f"{key}\t{normalize_tier(grounding)}\t{pdf_hash}")
        admitted_member = {
            "source_key": key,
            "role": member["role"],
            "grounding": normalize_tier(grounding),
            "warrant_scope": _effective_warrant_scope(member),
        }
        if member.get("retrieval_scope"):
            admitted_member["retrieval_scope"] = member["retrieval_scope"]
        admitted_members.append(admitted_member)
    fixture_hash_lines = metadata.get("fixture_exemplar_hash_lines")
    if fixture_hash_lines is not None:
        if (
            os.environ.get("COAUTHOR_HARNESS_SEMANTIC_FIXTURE") != "1"
            or path_roots_meta["path_roots_mode"] != "override"
            or graph_eligibility["semantic_scope"] != "synthetic-fixture"
        ):
            raise PolicyError(
                "GRAPH-SEMANTIC-INELIGIBLE: fixture exemplar hashes are forbidden "
                "outside an explicit synthetic fixture override"
            )
        if (
            not isinstance(fixture_hash_lines, list)
            or not fixture_hash_lines
            or len(fixture_hash_lines) != len(set(fixture_hash_lines))
            or any(not isinstance(line, str) for line in fixture_hash_lines)
        ):
            raise PolicyError(
                "GRAPH-SEMANTIC-INELIGIBLE: fixture exemplar hashes are malformed"
            )
        parsed_fixture_lines: dict[str, tuple[str, str]] = {}
        for line in fixture_hash_lines:
            fields = line.split("\t")
            if (
                len(fields) != 3
                or not fields[0]
                or fields[0] in parsed_fixture_lines
                or not grounding_admitted(fields[1])
                or re.fullmatch(r"[0-9a-f]{64}", fields[2]) is None
            ):
                raise PolicyError(
                    "GRAPH-SEMANTIC-INELIGIBLE: fixture exemplar hash row is invalid"
                )
            parsed_fixture_lines[fields[0]] = (normalize_tier(fields[1]), fields[2])
        admitted_grounding = {
            row["source_key"]: normalize_tier(row["grounding"])
            for row in admitted_members
        }
        if (
            set(parsed_fixture_lines) != set(admitted_grounding)
            or any(
                parsed_fixture_lines[key][0] != tier
                for key, tier in admitted_grounding.items()
            )
        ):
            raise PolicyError(
                "GRAPH-SEMANTIC-INELIGIBLE: fixture exemplar hashes do not match "
                "the admitted live source-page grounding set"
            )
        exemplar_lines = list(fixture_hash_lines)
    exemplar_pin = hashlib.sha256("\n".join(sorted(exemplar_lines, key=_utf8_key)).encode("utf-8")).hexdigest()
    graph_hash = graph_snapshot.sha256
    harness_profile = _contained(harness_root, "references/policies/reader_accessibility.v1.json")
    profile_snapshot = snapshots.capture(harness_profile, "register_profile")
    provenance.extend([
        {"role":"graph_provenance_only","path":str(graph_path),"sha256":graph_hash},
        {"role":"register_profile","path":str(harness_profile),"sha256":profile_snapshot.sha256},
        *({"role":role,"path":str(snapshot.path),"sha256":snapshot.sha256} for role, snapshot in semantic_artifacts),
        {"role":"semantic_receipt","path":str(receipt_path),"sha256":receipt_snapshot.sha256},
    ])
    warnings=[
        {
            "code":"RA-DNR-SEMANTIC-ENRICHMENT",
            "severity":"WARNING",
            "source_file":source_file,
            "message":"live wiki page is outside the pinned semantic inventory and is an enrichment candidate",
        }
        for source_file in enrichment_candidates
    ]
    guard = model["corpus_binding"]["related_to_RE_predicate"]["degeneracy_guard"]
    if len(resolution) <= guard["resolved_seed_count_lte"] or len(primary) < guard["primary_communities_lt"]:
        warnings.append({"code":"RA-DNR-DEGENERATE","severity":"WARNING","message":"semantic attestation view is based on a thin resolved seed set"})
    for key in missing_pdf_keys:
        warnings.append({"code":"RA-DNR-PDF-MISSING","severity":"WARNING","source_key":key,"message":"exemplar has no staged PDF; surface warrant is weak and the pin tuple uses '-'"})
    if _ingested_key:
        baseline_resolution = {key: value for key, value in resolution.items() if key != _ingested_key}
        baseline_primary = {by_id[node_id]["community"] for node_id in baseline_resolution.values()}
        baseline_primary_members = {node["id"] for node in nodes if node["community"] in baseline_primary}
        baseline_membership = set(baseline_primary_members)
        for link in links:
            source, target = link["source"], link["target"]
            if source in baseline_primary_members and by_id[target]["community"] not in baseline_primary:
                baseline_membership.add(target)
            if target in baseline_primary_members and by_id[source]["community"] not in baseline_primary:
                baseline_membership.add(source)
        if _ingested_key not in resolution or resolution[_ingested_key] not in baseline_membership:
            warnings.append({"code":"RA-DNR-COHERENCE","severity":"WARNING","source_key":_ingested_key,"message":"exemplar lies outside the current attestation membership and its one-hop halo; review centroid dilution"})
    snapshots.verify_all()
    final_inventory_paths: list[Path] = []
    for relative_dir in model["corpus_binding"]["graph"]["semantic_eligibility"]["inventory_directories"]:
        final_inventory_paths.extend(_contained(wiki_root, relative_dir).glob("*.md"))
    for relative_file in model["corpus_binding"]["graph"]["semantic_eligibility"]["inventory_root_files"]:
        candidate = _contained(wiki_root, relative_file)
        if candidate.is_file():
            final_inventory_paths.append(candidate)
    final_inventory_paths = sorted(set(final_inventory_paths), key=lambda path:path.relative_to(wiki_root).as_posix().encode("utf-8"))
    final_inventory_rows = [
        {"source_file":path.relative_to(wiki_root).as_posix(), "sha256":_hash(path)}
        for path in final_inventory_paths
    ]
    if final_inventory_rows != live_inventory_rows:
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: live research page inventory changed during resolution")
    surface_keys = {item["source_key"] for item in surface_exemplar_members(profile)}
    return {"register_class":"domain-native","attestation_view_pin":attestation_pin,"exemplar_view_pin":exemplar_pin,"graph_sha256_provenance":graph_hash,"graph_mtime_utc_provenance":datetime.fromtimestamp(graph_snapshot.stamp[3] / 1_000_000_000, tz=timezone.utc).isoformat().replace("+00:00", "Z"),"graph_extraction_mode":graph_eligibility["extraction_mode"],"graph_semantic_status":graph_eligibility["semantic_status"],"graph_semantic_scope":graph_eligibility["semantic_scope"],"seed_resolution_map":resolution,"seed_resolution_ties":ties,"unresolved_seed_ids":unresolved,"primary_communities":primary,"attestation_member_ids":sorted(membership,key=_utf8_key),"exemplar_hash_lines":sorted(exemplar_lines,key=_utf8_key),"exemplar_members":admitted_members,"surface_exemplar_members":[item for item in admitted_members if item["source_key"] in surface_keys],"argument_exemplar_members":admitted_members,"warnings":warnings,"path_roots":path_roots_meta,"provenance":provenance}


def _contained(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip() or "\x00" in relative or Path(relative).is_absolute():
        raise PolicyError(f"invalid contained relative path: {relative!r}")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise PolicyError(f"override path escapes project root: {relative}") from exc
    return candidate


def _list_file(path: Path) -> list[str]:
    values = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            values.append(value)
    return list(dict.fromkeys(values))


def _object(value: Any, path: str, required: set[str], optional: set[str] = set()) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PolicyError(f"{path} must be an object")
    missing = required - set(value)
    if missing:
        raise PolicyError(f"{path} missing: {', '.join(sorted(missing))}")
    extra = set(value) - required - optional
    if extra:
        raise PolicyError(f"{path} has unexpected fields: {', '.join(sorted(extra))}")
    return value


def _strings(value: Any, path: str, *, nonempty: bool = True) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise PolicyError(f"{path} must be a{' non-empty' if nonempty else ''} string array")
    if len(value) != len(set(value)):
        raise PolicyError(f"{path} must contain unique values")
    return value


def _number(value: Any, path: str, *, integer: bool = False, minimum: float = 0) -> float:
    valid = isinstance(value, int) and not isinstance(value, bool) if integer else isinstance(value, (int, float)) and not isinstance(value, bool)
    if not valid or value < minimum:
        raise PolicyError(f"{path} must be a number >= {minimum}")
    return value


def validate_profile(profile: dict[str, Any], schema_path: Path = PROFILE_SCHEMA) -> None:
    validate_schema_file(profile, schema_path)
    required = {"schema_version", "profile_version", "decision_status", "decision_record", "decision_approval", "normative_authority", "package_contributors", "policy_telos", "domain_native_register", "phase_values", "passage_roles", "sub_checks", "aggregate", "adjacent_advisory_checks", "thresholds", "transitions", "runtime_modes", "register_scope", "lexicons", "domain_token_exclusions", "override_contract", "remediation_order", "recurrence"}
    _object(profile, "profile", required)
    def reject_self_hash(value: Any, path: str = "profile") -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                if key == "canonical_sha256":
                    raise PolicyError(f"canonical_sha256 forbidden at {path}.{key}")
                reject_self_hash(nested, f"{path}.{key}")
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                reject_self_hash(nested, f"{path}[{index}]")
    reject_self_hash(profile)
    if profile["schema_version"] != "1.0.0" or not re.fullmatch(r"1\.0\.\d+", profile["profile_version"]):
        raise PolicyError("unsupported profile version")
    if profile["decision_record"] != "ADR-ACCESS-01" or profile["normative_authority"] != "references/READER_ACCESSIBILITY.md":
        raise PolicyError("decision record or normative authority is invalid")
    if profile["decision_status"] != "accepted" or profile["decision_approval"] != {"authority": "user", "approved_at": "2026-07-13", "provenance": "user_approval_in_session"}:
        raise PolicyError("ADR-ACCESS-01 acceptance requires the recorded user approval provenance")
    _strings(profile["package_contributors"], "package_contributors")
    register_members = profile["domain_native_register"]["exemplar_members"]
    source_keys = [item["source_key"] for item in register_members]
    if len(source_keys) != len(set(source_keys)):
        raise PolicyError("domain_native_register.exemplar_members source_key values must be unique")
    for locked_role, locked_key in _LOCKED_EXEMPLAR_ROLES.items():
        occupants = [item["source_key"] for item in register_members if item.get("role") == locked_role]
        if len(occupants) > 1 or (occupants and occupants != [locked_key]):
            raise PolicyError(f"singleton role {locked_role} is locked to {locked_key}")
    for item in register_members:
        if not grounding_admitted(item["grounding"]):
            raise PolicyError(f"exemplar member has denied grounding tier: {item['source_key']}")
        if item.get("role") == "centroid" and not item.get("retrieval_scope"):
            raise PolicyError("centroid exemplar requires a non-empty retrieval_scope")
        if item.get("role") == "intentional-root" and _effective_warrant_scope(item) != "argument-only":
            raise PolicyError("intentional-root requires warrant_scope argument-only")
    if tuple(profile["phase_values"]) != PHASES:
        raise PolicyError("phase_values must be exactly Ph1-Ph4")
    _strings(profile["passage_roles"], "passage_roles")
    checks = _object(profile["sub_checks"], "sub_checks", set("ABCDEFGH"))
    common = {"name", "scope", "deterministic_disposition", "gate_contribution", "binds_at", "advisory_at"}
    for letter, value in checks.items():
        check = _object(value, f"sub_checks.{letter}", common, {"threshold_key", "register_model_key", "do_not_flag_guards", "ph2_role_overrides"})
        for key in ("name", "scope"):
            if not isinstance(check[key], str) or not check[key].strip(): raise PolicyError(f"sub_checks.{letter}.{key} must be non-empty")
        if check["deterministic_disposition"] not in {"candidate_probe", "judgment_only"}:
            raise PolicyError(f"sub_checks.{letter}.deterministic_disposition is invalid")
        expected_gate = "aggregate_after_transition" if letter in {"G", "H"} else "aggregate"
        if check["gate_contribution"] != expected_gate:
            raise PolicyError(f"sub_checks.{letter}.gate_contribution is invalid")
        for key in ("binds_at", "advisory_at"):
            values = _strings(check[key], f"sub_checks.{letter}.{key}")
            if any(v not in PHASES for v in values):
                raise PolicyError(f"sub_checks.{letter}.{key} contains invalid phase")
    expected_h = {"name":"register_appropriateness","scope":"resolved_passages","deterministic_disposition":"candidate_probe","gate_contribution":"aggregate_after_transition","binds_at":["Ph3","Ph4"],"advisory_at":["Ph2"],"ph2_role_overrides":{"orienting_clause":"blocker_candidate"},"threshold_key":"thresholds.register","register_model_key":"domain_native_register"}
    if checks["H"] != expected_h:
        raise PolicyError("sub_checks.H must use the closed domain-native register routing contract")
    aggregate = _object(profile["aggregate"], "aggregate", {"members", "clean", "borderline", "major", "blocker"})
    for key in ("clean", "borderline", "major", "blocker"):
        if not isinstance(aggregate[key], str) or not aggregate[key].strip(): raise PolicyError(f"aggregate.{key} must be non-empty")
    if set(profile["sub_checks"]) != set("ABCDEFGH") or aggregate["members"] != list("ABCDEFGH"):
        raise PolicyError("Check 8 aggregate membership must be exactly A-H")
    adjacent = _object(profile["adjacent_advisory_checks"], "adjacent_advisory_checks", {"VE"})
    ve = _object(adjacent["VE"], "adjacent_advisory_checks.VE", {"name", "scope", "gate_contribution", "aggregate_member", "route", "transition_key", "follow_up_home", "threshold_key"})
    if ve.get("gate_contribution") != "none" or ve.get("aggregate_member") is not False:
        raise PolicyError("VE must remain outside the Check 8 aggregate")
    thresholds = _object(profile["thresholds"], "thresholds", {"cadence", "rhythm", "first_use", "section_signpost", "jargon", "worked_example", "consolidation", "register", "verdict_edge"})
    cadence = _object(thresholds["cadence"], "thresholds.cadence", {"calibration_status", "unit", "hard_ceiling_words", "bands", "turn_point_candidates", "candidate_semantics", "functional_confirmation_required", "functional_classes", "internal_sentence_break_signals", "above_ceiling", "persistence"})
    if cadence["calibration_status"] != "provisional":
        raise PolicyError("cadence numeric calibration must remain provisional")
    _number(cadence["hard_ceiling_words"], "thresholds.cadence.hard_ceiling_words", integer=True, minimum=1)
    if not cadence.get("functional_confirmation_required"):
        raise PolicyError("provisional cadence decision is malformed")
    if cadence["candidate_semantics"] != "nomination_only":
        raise PolicyError("thresholds.cadence.candidate_semantics must be nomination_only")
    for key in ("turn_point_candidates", "functional_classes", "internal_sentence_break_signals"): _strings(cadence[key], f"thresholds.cadence.{key}")
    bands = cadence["bands"]
    if not isinstance(bands, list) or not bands:
        raise PolicyError("thresholds.cadence.bands must contain at least one band")
    expected_min = 0
    previous_required = -1
    for index, band_value in enumerate(bands):
        band = _object(band_value, f"thresholds.cadence.bands[{index}]", {"min_words", "max_words", "required_functional_turn_points", "deficit_severity"})
        for key in ("min_words", "max_words", "required_functional_turn_points"):
            _number(band[key], f"thresholds.cadence.bands[{index}].{key}", integer=True, minimum=0)
        if band["min_words"] != expected_min or band["max_words"] < band["min_words"]:
            raise PolicyError("thresholds.cadence.bands must be ordered and contiguous")
        required = band["required_functional_turn_points"]
        if (index == 0 and required != 0) or (index > 0 and required <= previous_required):
            raise PolicyError("thresholds.cadence band turn-point requirements must start at zero and strictly increase")
        if band["deficit_severity"] not in {"CLEAN", "MINOR", "MAJOR"}:
            raise PolicyError("thresholds.cadence band deficit severity is invalid")
        expected_min = band["max_words"] + 1
        previous_required = required
    if bands[-1]["max_words"] != cadence["hard_ceiling_words"]:
        raise PolicyError("thresholds.cadence.bands must end at hard ceiling")
    above = _object(cadence["above_ceiling"], "thresholds.cadence.above_ceiling", {"current_severity_floor", "mandatory_split", "blocker_when"})
    if above != {"current_severity_floor": "MAJOR", "mandatory_split": True, "blocker_when": "zero functional turn-points AND zero internal sentence-break signals"}:
        raise PolicyError("thresholds.cadence.above_ceiling is invalid")
    persistence = _object(cadence["persistence"], "thresholds.cadence.persistence", {"identity_key", "reset_on_content_hash_change", "changes_current_severity", "planner_workflow_trigger_after_unchanged_rounds"})
    if persistence["identity_key"] != "paragraph_content_sha256" or persistence["reset_on_content_hash_change"] is not True or persistence["changes_current_severity"] is not False:
        raise PolicyError("thresholds.cadence.persistence semantics are invalid")
    _number(persistence["planner_workflow_trigger_after_unchanged_rounds"], "thresholds.cadence.persistence.planner_workflow_trigger_after_unchanged_rounds", integer=True, minimum=1)
    rhythm = _object(thresholds["rhythm"], "thresholds.rhythm", {"minimum_sentence_count", "mean_words_above", "standard_deviation_below", "short_sentence_words_at_most", "long_sentence_words_at_least"})
    for key, value in rhythm.items(): _number(value, f"thresholds.rhythm.{key}")
    first_use = _object(thresholds["first_use"], "thresholds.first_use", {"definition_window_paragraphs", "manuscript_major_section_failures_min"})
    for key, value in first_use.items(): _number(value, f"thresholds.first_use.{key}", integer=True)
    signpost = _object(thresholds["section_signpost"], "thresholds.section_signpost", {"opening_sentences_min", "opening_sentences_max"})
    for key, value in signpost.items(): _number(value, f"thresholds.section_signpost.{key}", integer=True, minimum=1)
    if signpost["opening_sentences_min"] > signpost["opening_sentences_max"]: raise PolicyError("thresholds.section_signpost sentence range is inverted")
    jargon = _object(thresholds["jargon"], "thresholds.jargon", {"new_domain_terms_per_paragraph"})
    stages = _object(jargon["new_domain_terms_per_paragraph"], "thresholds.jargon.new_domain_terms_per_paragraph", {"P0", "P1", "P2"})
    for key, value in stages.items(): _number(value, f"thresholds.jargon.new_domain_terms_per_paragraph.{key}", integer=True)
    worked = _object(thresholds["worked_example"], "thresholds.worked_example", {"rhetorical_question_stack_min", "example_window_paragraphs"})
    for key, value in worked.items(): _number(value, f"thresholds.worked_example.{key}", integer=True)
    consolidation = _object(thresholds["consolidation"], "thresholds.consolidation", {"construct_accumulation", "prior_sections_dependency", "candidate_gap_words", "candidate_gap_paragraphs", "pre_heading_scan_paragraphs", "short_manuscript_guidance_words", "long_manuscript_candidate_words", "deterministic_gap_is_proxy_only"})
    gaps = _object(consolidation["candidate_gap_words"], "thresholds.consolidation.candidate_gap_words", {"P0", "P1", "P2"})
    for key, value in gaps.items(): _number(value, f"thresholds.consolidation.candidate_gap_words.{key}", integer=True)
    for key in ("construct_accumulation", "prior_sections_dependency", "candidate_gap_paragraphs", "short_manuscript_guidance_words", "long_manuscript_candidate_words"): _number(consolidation[key], f"thresholds.consolidation.{key}")
    _number(consolidation["pre_heading_scan_paragraphs"], "thresholds.consolidation.pre_heading_scan_paragraphs", integer=True, minimum=1)
    if consolidation["deterministic_gap_is_proxy_only"] is not True: raise PolicyError("consolidation proxy flag must be true")
    register = _object(thresholds["register"], "thresholds.register", {"minimum_positive_markers", "positive_marker_count", "nominalisation_density_candidate", "prepositional_run_candidate", "hedges_per_100_words_candidate", "functional_removability_required", "severity_model"})
    for key, value in register.items():
        if key not in {"functional_removability_required", "severity_model"}: _number(value, f"thresholds.register.{key}")
    if register["functional_removability_required"] is not True: raise PolicyError("register functional-removability flag must be true")
    severity_model = _object(register["severity_model"], "thresholds.register.severity_model", {"minor_negative_markers_min", "minor_negative_markers_max", "major_consecutive_passages", "weighted_roles", "ph2_orienting_zero_positive", "nontechnical_blocker_major_fraction_above"})
    for key in ("minor_negative_markers_min", "minor_negative_markers_max", "major_consecutive_passages"): _number(severity_model[key], f"thresholds.register.severity_model.{key}", integer=True, minimum=1)
    _strings(severity_model["weighted_roles"], "thresholds.register.severity_model.weighted_roles")
    if severity_model["ph2_orienting_zero_positive"] != "blocker_candidate" or not 0 < severity_model["nontechnical_blocker_major_fraction_above"] < 1: raise PolicyError("thresholds.register.severity_model is invalid")
    verdict_edge = _object(thresholds["verdict_edge"], "thresholds.verdict_edge", {"intensifier_tokens_min", "intensifier_classes_min"})
    for key, value in verdict_edge.items(): _number(value, f"thresholds.verdict_edge.{key}", integer=True, minimum=1)
    transitions = _object(profile["transitions"], "transitions", {"G", "H", "VE"})
    for key, value in transitions.items():
        required_transition = {"meaning", "required_observed_count", "retirement_event", "workflow_effect_while_active", "stability_mode_effect", "state_owner"}
        optional_transition = {"workflow_effect_after_retirement"}
        transition = _object(value, f"transitions.{key}", required_transition, optional_transition)
        _number(transition["required_observed_count"], f"transitions.{key}.required_observed_count", integer=True, minimum=1)
        if transition["retirement_event"] != "planner_transition_approved": raise PolicyError(f"transitions.{key}.retirement_event invalid")
        expected_owner = f"phase_state.json.milestone_framework.policy_bindings.reader_accessibility.transitions.{key}"
        if transition["state_owner"] != expected_owner: raise PolicyError(f"transitions.{key}.state_owner invalid")
    modes = _object(profile["runtime_modes"], "runtime_modes", {"stability"})
    stability = _object(modes["stability"], "runtime_modes.stability", {"aggregation_source", "independent_member_exclusions", "negative_prefilter_short_circuit"})
    if stability != {"aggregation_source": "resolved_profile_and_bound_transition_state", "independent_member_exclusions": False, "negative_prefilter_short_circuit": False}:
        raise PolicyError("runtime_modes.stability semantics are invalid")
    scope = _object(profile["register_scope"], "register_scope", {"technical", "mixed", "non-technical"})
    for key, value in scope.items(): _strings(value, f"register_scope.{key}")
    lexicons = _object(profile["lexicons"], "lexicons", {"plain_connectives", "latinate_whitelist", "hedges", "nominalisation_suffixes", "prepositions"})
    for key, value in lexicons.items(): _strings(value, f"lexicons.{key}")
    _strings(profile["domain_token_exclusions"], "domain_token_exclusions")
    contract = _object(profile["override_contract"], "override_contract", {"directives", "plain_connectives", "hedges", "latinate_whitelist", "terminology", "glossary"})
    _object(contract["directives"], "override_contract.directives", {"path", "passage_scope_class_key", "legacy_register_class_alias", "project_identity_key"})
    if contract["directives"] != {"path": "research_notes/directives.md", "passage_scope_class_key": "passage_scope_class", "legacy_register_class_alias": True, "project_identity_key": "project_id"}:
        raise PolicyError("override_contract.directives path or keys are invalid")
    expected_paths = {"plain_connectives": "research_notes/plain_connectives.txt", "hedges": "research_notes/hedges.txt", "latinate_whitelist": "research_notes/latinate_whitelist.txt", "terminology": "research_notes/terminology.txt", "glossary": "research_notes/glossary.txt"}
    for key in ("plain_connectives", "hedges", "latinate_whitelist", "terminology", "glossary"):
        _object(contract[key], f"override_contract.{key}", {"path", "polarity"})
        if contract[key]["path"] != expected_paths[key]: raise PolicyError(f"override_contract.{key} path is invalid")
    _strings(profile["remediation_order"], "remediation_order")
    recurrence = _object(profile["recurrence"], "recurrence", {"project_lesson_consecutive_rounds", "package_lesson_distinct_projects", "state_owner", "semantic_severity_effect"})
    for key in ("project_lesson_consecutive_rounds", "package_lesson_distinct_projects"): _number(recurrence[key], f"recurrence.{key}", integer=True, minimum=1)
    if not isinstance(recurrence["state_owner"], str) or not recurrence["state_owner"].strip(): raise PolicyError("recurrence.state_owner must be non-empty")
    if recurrence["semantic_severity_effect"] != "none": raise PolicyError("recurrence cannot change semantic severity")
    serialized = json.dumps(profile).lower()
    if any(token in serialized for token in ("todo", "tbd", "placeholder", "fill me")):
        raise PolicyError("profile contains unfinished data")
    identity = set(profile["domain_native_register"]["c7_fence"]["protected_identity_layer"])
    auto_remediation = json.dumps({"remediation_order": profile["remediation_order"], "derivations": profile["domain_native_register"]["derivations"]}).lower()
    if any(token.lower() in auto_remediation for token in identity):
        raise PolicyError("C-7 identity-layer key appears in auto-remediation path")
    for key, expected in (("plain_connectives", "replace"), ("hedges", "replace"), ("latinate_whitelist", "supplement"), ("terminology", "extend_domain_token_exclusions"), ("glossary", "extend_domain_token_exclusions")):
        if profile["override_contract"][key].get("polarity") != expected:
            raise PolicyError(f"override polarity mismatch: {key}")


def _load_profile_bytes(payload: bytes, schema_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(payload.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PolicyError(f"profile unreadable: {exc}") from exc
    if not isinstance(data, dict):
        raise PolicyError("profile root must be an object")
    try:
        validate_profile(data, schema_path)
    except PolicyError:
        raise
    except (TypeError, KeyError, AttributeError, IndexError) as exc:
        raise PolicyError(f"profile nested shape is invalid: {exc}") from exc
    return data


def load_profile(path: Path = DEFAULT_PROFILE, schema_path: Path = PROFILE_SCHEMA) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise PolicyError(f"profile unreadable: {exc}") from exc
    return _load_profile_bytes(payload, schema_path)


def evaluate_cadence(word_count: int, functional_turn_points: int, internal_break_signals: int, profile: dict[str, Any]) -> dict[str, Any]:
    cadence = profile["thresholds"]["cadence"]
    ceiling = cadence["hard_ceiling_words"]
    required = 0
    deficit = "CLEAN"
    for band in cadence["bands"]:
        if band["min_words"] <= word_count <= band["max_words"]:
            required = band["required_functional_turn_points"]
            deficit = band["deficit_severity"]
            break
    mandatory_split = word_count > ceiling
    if word_count > ceiling:
        severity = "BLOCKER" if functional_turn_points == 0 and internal_break_signals == 0 else "MAJOR"
    elif functional_turn_points < required:
        severity = deficit
    else:
        severity = "CLEAN"
    return {"word_count": word_count, "required_functional_turn_points": required, "functional_turn_points": functional_turn_points, "internal_break_signals": internal_break_signals, "current_severity": severity, "mandatory_split": mandatory_split}


def recompute_check8(evidence: dict[str, Any], transitions: dict[str, Any]) -> dict[str, Any]:
    """Validate structured Check 8 findings and recompute transition-aware A-H aggregate."""
    if not isinstance(evidence, dict) or not isinstance(evidence.get("subchecks"), dict) or set(evidence["subchecks"]) != set("ABCDEFGH"):
        raise PolicyError("Check 8 evidence must contain exactly A-H subcheck objects")
    ve = evidence.get("ve")
    if not isinstance(ve, dict) or ve.get("aggregate_member") is not False or ve.get("gate_contribution") != "none" or not isinstance(ve.get("findings"), list):
        raise PolicyError("VE must be a nonaggregate advisory with a findings array")
    allowed = {"CLEAN": 0, "MINOR": 1, "MAJOR": 2, "BLOCKER": 3}
    included_findings: list[dict[str, Any]] = []
    verdicts: dict[str, str] = {}
    for letter in "ABCDEFGH":
        row = evidence["subchecks"][letter]
        if not isinstance(row, dict) or set(row) != {"findings"} or not isinstance(row["findings"], list):
            raise PolicyError(f"subchecks.{letter} must contain only a findings array")
        severities = []
        seen_ids = set()
        for finding in row["findings"]:
            if not isinstance(finding, dict) or set(finding) != {"finding_id", "severity", "independence_group"}:
                raise PolicyError(f"subchecks.{letter} finding shape is invalid")
            if finding["severity"] not in allowed or not all(isinstance(finding[key], str) and finding[key].strip() for key in ("finding_id", "independence_group")):
                raise PolicyError(f"subchecks.{letter} finding severity or identity is invalid")
            if finding["finding_id"] in seen_ids: raise PolicyError(f"subchecks.{letter} duplicate finding_id")
            seen_ids.add(finding["finding_id"]); severities.append(finding["severity"])
        verdicts[letter] = max(severities, key=lambda item: allowed[item]) if severities else "CLEAN"
        include = letter not in {"G", "H"} or transitions.get(letter, {}).get("state") == "retired"
        if include: included_findings.extend(row["findings"])
    blockers = {f["independence_group"] for f in included_findings if f["severity"] == "BLOCKER"}
    majors = {f["independence_group"] for f in included_findings if f["severity"] == "MAJOR"}
    aggregate = "BLOCKER" if blockers else ("MAJOR" if len(majors) >= 2 else ("BORDERLINE" if len(majors) == 1 else "CLEAN"))
    return {"subcheck_verdicts": verdicts, "aggregate_verdict": aggregate, "included_members": [letter for letter in "ABCDEFGH" if letter not in {"G", "H"} or transitions.get(letter, {}).get("state") == "retired"]}


def validate_candidate_artifact(candidate: dict[str, Any]) -> None:
    validate_schema_file(candidate, CANDIDATE_SCHEMA)


def validate_check8_evidence(evidence: dict[str, Any]) -> None:
    validate_schema_file(evidence, CHECK8_SCHEMA)
    version = evidence.get("schema_version") if isinstance(evidence, dict) else None
    if version == "check8_evidence.v1":
        if any(evidence.get(key) is None for key in ("attestation_view_pin", "exemplar_view_pin")):
            raise PolicyError("Check 8 v1 requires both semantic register pins")
    elif version == "check8_evidence.v2":
        if evidence.get("semantic_usage") != "not_invoked":
            raise PolicyError("Check 8 v2 requires semantic_usage not_invoked")
        if any(key in evidence for key in ("attestation_view_pin", "exemplar_view_pin")):
            raise PolicyError("Check 8 v2 cannot assert semantic register pins")
    else:
        raise PolicyError("unsupported Check 8 schema version")


def render_policy_view(profile: dict[str, Any]) -> str:
    """Render the sole generated human-readable numeric policy view."""
    validate_profile(profile)
    payload = {
        "decision_approval": profile["decision_approval"],
        "decision_status": profile["decision_status"],
        "runtime_modes": profile["runtime_modes"],
        "thresholds": profile["thresholds"],
        "transitions": {key: {field: profile["transitions"][key].get(field) for field in ("meaning", "required_observed_count", "workflow_effect_while_active", "workflow_effect_after_retirement", "stability_mode_effect")} for key in ("G", "H", "VE")},
        "recurrence": profile["recurrence"],
    }
    return "# Reader Accessibility Policy View (Generated)\n\nDo not edit. Generated from `references/policies/reader_accessibility.v1.json`; operational prose cites profile keys.\n\n```json\n" + json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n```\n"


def update_persistence(previous_content_sha256: str | None, current_content_sha256: str, prior_unchanged_rounds: int, current_severity: str, approved_revision_evidence: list[dict[str, Any]] | None = None, previous_approval_sequence: int | None = None) -> dict[str, Any]:
    eligible = [event for event in (approved_revision_evidence or []) if isinstance(event, dict) and event.get("event") == "revision_approved" and event.get("approved") is True and event.get("content_sha256") == current_content_sha256 and isinstance(event.get("sequence"), int)]
    newest_sequence = max((event["sequence"] for event in eligible), default=None)
    approved = newest_sequence is not None and (previous_approval_sequence is None or newest_sequence > previous_approval_sequence)
    unchanged = prior_unchanged_rounds + 1 if previous_content_sha256 == current_content_sha256 and approved else (prior_unchanged_rounds if previous_content_sha256 == current_content_sha256 else 0)
    return {"paragraph_content_sha256": current_content_sha256, "unchanged_rounds": unchanged, "current_severity": current_severity, "planner_workflow_escalation_candidate": unchanged >= 2 and approved, "approved_revision_evidence_observed": approved, "last_approval_sequence": newest_sequence if approved else previous_approval_sequence}


def resolve_policy_scaffold(
    project_root: Path | None, *, profile_path: Path = DEFAULT_PROFILE,
) -> dict[str, Any]:
    """Resolve policy and project inputs without asserting graph semantics."""
    profile_path = profile_path.resolve()
    profile = load_profile(profile_path)
    resolved = copy.deepcopy(profile)
    try:
        profile_relative = profile_path.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise PolicyError("profile path must be contained by package root") from exc
    bindings = [{"scope": "package", "path": profile_relative, "sha256": _hash(profile_path), "role": "package_profile"}]
    for relative in profile["package_contributors"]:
        contributor = (ROOT / relative).resolve()
        try:
            contributor.relative_to(ROOT)
        except ValueError as exc:
            raise PolicyError(f"package contributor escapes harness root: {relative}") from exc
        if not contributor.is_file():
            raise PolicyError(f"package contributor is missing: {relative}")
        bindings.append({"scope": "package", "path": Path(relative).as_posix(), "sha256": _hash(contributor), "role": "package_contributor"})
    passage_scope_class = "technical"
    project_identity = None
    if project_root is not None:
        project_root = project_root.resolve()
        if not project_root.is_dir():
            raise PolicyError(f"project root is not a directory: {project_root}")
        contract = profile["override_contract"]
        directives = _contained(project_root, contract["directives"]["path"])
        if directives.is_file():
            text = directives.read_text(encoding="utf-8")
            raw_scope = re.search(r"(?mi)^\s*passage_scope_class\s*:\s*([^#\r\n]+?)\s*$", text)
            raw_register = raw_scope or re.search(r"(?mi)^\s*register_class\s*:\s*([^#\r\n]+?)\s*$", text)
            if raw_register:
                passage_scope_class = raw_register.group(1).strip().lower()
                if passage_scope_class not in {"technical", "mixed", "non-technical"}:
                    raise PolicyError(f"invalid passage_scope_class: {passage_scope_class}")
            identity = re.search(r"(?mi)^\s*project_id\s*:\s*([^#\r\n]+?)\s*$", text)
            if identity: project_identity = identity.group(1).strip()
            bindings.append({"scope": "project", "path": directives.relative_to(project_root).as_posix(), "sha256": _hash(directives), "role": "directives"})
        for key in ("plain_connectives", "hedges", "latinate_whitelist", "terminology", "glossary"):
            rule = contract[key]
            path = _contained(project_root, rule["path"])
            if not path.is_file():
                continue
            values = _list_file(path)
            if rule["polarity"] == "replace":
                if not values:
                    raise PolicyError(f"replace override is empty: {rule['path']}")
                resolved["lexicons"][key] = values
            elif rule["polarity"] == "supplement":
                resolved["lexicons"][key] = list(dict.fromkeys(resolved["lexicons"][key] + values))
            else:
                resolved["domain_token_exclusions"] = list(dict.fromkeys(resolved["domain_token_exclusions"] + values))
            bindings.append({"scope": "project", "path": path.relative_to(project_root).as_posix(), "sha256": _hash(path), "role": f"project_{key}", "polarity": rule["polarity"]})
    return {
        "profile": profile,
        "resolved_profile": resolved,
        "profile_path": profile_relative,
        "profile_sha256": _hash(profile_path),
        "source_bindings": bindings,
        "passage_scope_class": passage_scope_class,
        "project_identity": project_identity,
        "project_root": project_root,
    }


def resolve_reader_profile(
    project_root: Path | None, *, profile_path: Path = DEFAULT_PROFILE,
) -> dict[str, Any]:
    """Resolve reader/source policy without invoking a semantic graph capability."""
    scaffold = resolve_policy_scaffold(project_root, profile_path=profile_path)
    return {
        "contract_version": "2.0.0",
        "binding_kind": "reader_profile",
        "semantic_usage": "not_invoked",
        "profile_path": scaffold["profile_path"],
        "profile_sha256": scaffold["profile_sha256"],
        "register_class": "domain-native",
        "passage_scope_class": scaffold["passage_scope_class"],
        "project_identity": scaffold["project_identity"],
        "resolved_profile": scaffold["resolved_profile"],
        "source_bindings": scaffold["source_bindings"],
    }


def resolve_policy(project_root: Path | None, *, profile_path: Path = DEFAULT_PROFILE,
                   wiki_root: Path | None = None, workspace_root: Path | None = None,
                   harness_root: Path | None = None) -> dict[str, Any]:
    scaffold = resolve_policy_scaffold(project_root, profile_path=profile_path)
    profile = scaffold["profile"]
    resolved = scaffold["resolved_profile"]
    profile_relative = scaffold["profile_path"]
    bindings = scaffold["source_bindings"]
    passage_scope_class = scaffold["passage_scope_class"]
    project_identity = scaffold["project_identity"]
    project_root = scaffold["project_root"]
    register = resolve_domain_native_register(profile, wiki_root=wiki_root, workspace_root=workspace_root, harness_root=harness_root)
    for source in bindings:
        owner = ROOT if source["scope"] == "package" else project_root
        if owner is not None:
            recorded_path = str((owner / source["path"]).resolve()) if source["scope"] == "package" else f"project://{source['path']}"
            register["provenance"].append({"role": source["role"], "path": recorded_path, "sha256": source["sha256"]})
    return {"contract_version": "1.1.0", "profile_path": profile_relative, "profile_sha256": scaffold["profile_sha256"], "register_class": "domain-native", "passage_scope_class": passage_scope_class, "project_identity": project_identity, "resolved_profile": resolved, "source_bindings": bindings, "attestation_view_pin": register["attestation_view_pin"], "exemplar_view_pin": register["exemplar_view_pin"], "graph_sha256_provenance": register["graph_sha256_provenance"], "register_provenance": register}


def resolve_unavailable_policy(
    project_root: Path,
    reason: str,
    *,
    profile_path: Path = DEFAULT_PROFILE,
    wiki_root: Path | None = None,
    workspace_root: Path | None = None,
    harness_root: Path | None = None,
) -> dict[str, Any]:
    """Bind a structural graph observation without granting semantic authority."""
    if not reason.startswith("GRAPH-SEMANTIC-INELIGIBLE:"):
        raise PolicyError("unavailable policy requires GRAPH-SEMANTIC-INELIGIBLE")
    scaffold = resolve_policy_scaffold(project_root, profile_path=profile_path)
    profile = scaffold["profile"]
    effective_wiki, effective_workspace, _, _ = _resolve_register_roots(
        profile,
        wiki_root=wiki_root,
        workspace_root=workspace_root,
        harness_root=harness_root,
    )
    del effective_wiki
    graph_relative = profile["domain_native_register"]["corpus_binding"]["graph"]["path"]
    graph_path = _contained(effective_workspace, graph_relative)
    try:
        graph_bytes = graph_path.read_bytes()
        graph = json.loads(graph_bytes.decode("utf-8", errors="strict"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PolicyError(f"GRAPH-SEMANTIC-INELIGIBLE: structural graph observation failed: {exc}") from exc
    metadata = graph.get("graph") if isinstance(graph, dict) else None
    if not isinstance(metadata, dict):
        raise PolicyError("GRAPH-SEMANTIC-INELIGIBLE: graph metadata object is required")
    extraction_mode = metadata.get("extraction_mode")
    semantic_status = metadata.get("semantic_status")
    if extraction_mode != "structural-only" or semantic_status != "pending":
        raise PolicyError(
            "GRAPH-SEMANTIC-INELIGIBLE: unavailable bootstrap only admits "
            f"structural-only/pending, observed {extraction_mode}/{semantic_status}"
        )
    return {
        "contract_version": "1.0.0",
        "availability": "semantic_graph_unavailable",
        "profile_path": scaffold["profile_path"],
        "profile_sha256": scaffold["profile_sha256"],
        "register_class": "domain-native",
        "passage_scope_class": scaffold["passage_scope_class"],
        "project_identity": scaffold["project_identity"],
        "resolved_profile": scaffold["resolved_profile"],
        "source_bindings": scaffold["source_bindings"],
        "blocker": {
            "code": "GRAPH-SEMANTIC-INELIGIBLE",
            "reason": reason,
            "graph_path": graph_relative,
            "graph_sha256": hashlib.sha256(graph_bytes).hexdigest(),
            "extraction_mode": extraction_mode,
            "semantic_status": semantic_status,
        },
    }


def unavailable_phase_state_binding(
    resolved: dict[str, Any], resolved_path: Path, project_root: Path,
) -> dict[str, Any]:
    """Build an M1-only binding for a currently unavailable semantic graph."""
    path = resolved_path.resolve()
    try:
        relative = path.relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise PolicyError("resolved artifact escapes project root") from exc
    if not path.is_file():
        raise PolicyError("resolved artifact is missing")
    if resolved.get("availability") != "semantic_graph_unavailable":
        raise PolicyError("unavailable binding requires an unavailable resolver artifact")
    return {
        "availability": "semantic_graph_unavailable",
        "profile_path": resolved["profile_path"],
        "profile_sha256": resolved["profile_sha256"],
        "resolved_path": relative,
        "resolved_sha256": _hash(path),
        "source_bindings": copy.deepcopy(resolved["source_bindings"]),
        "project_identity": resolved.get("project_identity"),
        "blocker": copy.deepcopy(resolved["blocker"]),
        "transitions": {
            key: {"state": "active", "observed_count": 0, "last_event_sequence": None, "events": []}
            for key in ("G", "H", "VE")
        },
    }


def reader_profile_phase_state_binding(
    resolved: dict[str, Any], resolved_path: Path, project_root: Path,
) -> dict[str, Any]:
    """Build the graph-independent v2 reader-profile binding."""
    path = resolved_path.resolve()
    try:
        relative = path.relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise PolicyError("resolved artifact escapes project root") from exc
    if not path.is_file():
        raise PolicyError("resolved artifact is missing")
    if (
        resolved.get("contract_version") != "2.0.0"
        or resolved.get("binding_kind") != "reader_profile"
        or resolved.get("semantic_usage") != "not_invoked"
    ):
        raise PolicyError("reader-profile binding requires a v2 graph-independent resolver artifact")
    return {
        "binding_version": "2.0.0",
        "binding_kind": "reader_profile",
        "semantic_usage": "not_invoked",
        "profile_path": resolved["profile_path"],
        "profile_sha256": resolved["profile_sha256"],
        "resolved_path": relative,
        "resolved_sha256": _hash(path),
        "source_bindings": copy.deepcopy(resolved["source_bindings"]),
        "project_identity": resolved.get("project_identity"),
        "transitions": {
            key: {"state": "active", "observed_count": 0, "last_event_sequence": None, "events": []}
            for key in ("G", "H", "VE")
        },
    }


def phase_state_binding(resolved: dict[str, Any], resolved_path: Path, project_root: Path) -> dict[str, Any]:
    """Build the exact phase-state binding shape from a written resolver artifact."""
    path = resolved_path.resolve()
    try: relative = path.relative_to(project_root.resolve()).as_posix()
    except ValueError as exc: raise PolicyError("resolved artifact escapes project root") from exc
    if not path.is_file(): raise PolicyError("resolved artifact is missing")
    expected = resolved.get("resolved_profile", {}).get("domain_native_register", {}).get("expected_verification", {})
    for key in ("attestation_view_pin", "exemplar_view_pin"):
        if expected.get(key) != resolved.get(key):
            raise PolicyError(f"initial semantic pin mismatch for {key}; deliberate profile repin required")
    register_provenance = copy.deepcopy(resolved["register_provenance"])
    # These eligibility facts remain in the resolver artifact and repin
    # snapshot. The milestone schema's register provenance is a stable pin
    # surface, so it carries the verified artifact hashes in ``provenance``
    # without widening its top-level shape.
    for key in ("graph_extraction_mode", "graph_semantic_status", "graph_semantic_scope"):
        register_provenance.pop(key, None)
    return {"profile_path": resolved["profile_path"], "profile_sha256": resolved["profile_sha256"], "resolved_path": relative, "resolved_sha256": _hash(path), "source_bindings": copy.deepcopy(resolved["source_bindings"]), "project_identity": resolved.get("project_identity"), "attestation_view_pin": resolved["attestation_view_pin"], "exemplar_view_pin": resolved["exemplar_view_pin"], "pin_epoch": expected["pin_epoch"], "pinned_at": expected["pinned_at"], "graph_sha256_provenance": resolved["graph_sha256_provenance"], "register_provenance": register_provenance, "transitions": {key: {"state": "active", "observed_count": 0, "last_event_sequence": None, "events": []} for key in ("G", "H", "VE")}}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _atomic_bytes(path: Path, payload: bytes) -> None:
    """Same-directory, fsynced atomic replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_create_bytes(path: Path, payload: bytes) -> None:
    """Publish complete bytes only when the destination is still absent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    published = False
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
            published = True
        except FileExistsError as exc:
            raise PolicyError(f"destination appeared concurrently; refusing overwrite: {path}") from exc
        except OSError as exc:
            raise PolicyError(f"exclusive atomic publication failed for {path}: {exc}") from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            if not published:
                raise


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def repin_pin_affecting_paths() -> set[str]:
    return {
        "references/policies/reader_accessibility.v1.json",
        "references/policies/repin_log.jsonl",
        "references/policies/repin_log.md",
        "reviews/.repin.lock",
    }


def classify_repin_dirty_paths(paths: list[str], pin_paths: set[str] | None = None) -> tuple[list[str], list[str]]:
    pin_paths = pin_paths or repin_pin_affecting_paths()
    normalized = sorted({Path(path).as_posix() for path in paths})
    pin = [path for path in normalized if path in pin_paths or path.startswith("reviews/.harness/repin/")]
    return pin, [path for path in normalized if path not in pin]


def repin_dirty_refusal(pin_paths: list[str], unrelated_paths: list[str], *, allow_unrelated_dirty: bool) -> str | None:
    if pin_paths:
        return "pin-affecting paths are dirty: " + ", ".join(pin_paths)
    if unrelated_paths and not allow_unrelated_dirty:
        return "unrelated dirty paths require --allow-unrelated-dirty: " + ", ".join(unrelated_paths)
    return None


def repin_prior_diff_refusal(paths: list[str]) -> str | None:
    prior = [path for path in paths if path in repin_pin_affecting_paths() or path.startswith("reviews/.harness/repin/")]
    return "uncommitted prior re-pin diff: " + ", ".join(sorted(prior)) if prior else None


def _git_dirty_paths(root: Path) -> list[str]:
    if not (root / ".git").exists():
        return []
    top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=root,
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if top.returncode != 0:
        raise PolicyError(f"git worktree discovery failed during re-pin preflight: {top.stderr.strip()}")
    if Path(top.stdout.strip()).resolve() != root.resolve():
        raise PolicyError("re-pin harness root is not the git worktree root")
    proc = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if proc.returncode != 0:
        raise PolicyError(f"git status failed during re-pin preflight: {proc.stderr.strip()}")
    paths: list[str] = []
    fields = proc.stdout.split("\0")
    index = 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if not entry:
            continue
        if len(entry) < 4 or entry[2] != " ":
            raise PolicyError(f"git status returned malformed porcelain entry: {entry!r}")
        status = entry[:2]
        paths.append(entry[3:])
        if "R" in status or "C" in status:
            if index >= len(fields) or not fields[index]:
                raise PolicyError("git status returned a rename/copy without its source path")
            paths.append(fields[index])
            index += 1
    return paths


def _tracked_path_dirty(path: Path) -> bool:
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=path.parent, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if top.returncode != 0:
        return False
    repository = Path(top.stdout.strip()).resolve()
    try:
        relative = path.resolve().relative_to(repository).as_posix()
    except ValueError:
        return False
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "--", relative], cwd=repository, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if tracked.returncode != 0:
        return False
    status = subprocess.run(["git", "status", "--porcelain=v1", "--", relative], cwd=repository, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if status.returncode != 0:
        raise PolicyError(f"git status failed for tracked graph during re-pin preflight: {status.stderr.strip()}")
    return bool(status.stdout.strip())


def _schema_supports_repin(schema_path: Path) -> bool:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        expected = schema["properties"]["domain_native_register"]["properties"]["expected_verification"]
        return {"pin_epoch", "pinned_at"} <= set(expected.get("required", [])) and {"pin_epoch", "pinned_at"} <= set(expected.get("properties", {}))
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return False


def _patch_bump(version: str) -> str:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise PolicyError(f"profile_version is not semantic: {version}")
    return f"{match.group(1)}.{match.group(2)}.{int(match.group(3)) + 1}"


def _delta_class(old_attestation: str, new_attestation: str, old_exemplar: str, new_exemplar: str,
                 *, corpus_changed: bool = False) -> str:
    attestation = old_attestation != new_attestation
    exemplar = old_exemplar != new_exemplar
    if corpus_changed:
        changes = ["corpus"]
        if attestation and exemplar:
            changes.append("both")
        elif attestation:
            changes.append("attestation")
        elif exemplar:
            changes.append("exemplar")
        return "+".join(changes)
    if attestation and exemplar:
        return "both"
    if attestation:
        return "attestation"
    if exemplar:
        return "exemplar"
    return "none"


def _read_repin_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    result = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PolicyError(f"repin ledger line {number} is invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise PolicyError(f"repin ledger line {number} is not an object")
        result.append(row)
    return result


def _render_repin_log(rows: list[dict[str, Any]]) -> str:
    lines = ["# Register Re-pin Log", "", "Derived from `repin_log.jsonl`; do not edit.", "", "| Event epoch | Pinned at | Dry run | Delta | Trigger | Snapshot |", "|---:|---|---|---|---|---|"]
    for row in rows:
        lines.append(f"| {row['epoch']} | {row['pinned_at']} | {str(row['dry_run']).lower()} | {row['delta_class']} | {row['trigger']} | `{row['snapshot_ref']}` |")
    return "\n".join(lines) + "\n"


def backfill_repin_commit(harness_root: Path, epoch: int, commit: str, *, confirm: Callable[[str], bool] | None = None) -> dict[str, Any]:
    """Backfill the post-commit audit pointer without recomputing any pin."""
    if re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", commit) is None:
        raise PolicyError("re-pin commit must be a 40- or 64-character lowercase hex object id")
    harness_root = harness_root.resolve()
    top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=harness_root,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != harness_root:
        raise PolicyError("re-pin commit backfill requires the harness git worktree root")
    commit_object = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=harness_root,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if commit_object.returncode != 0:
        raise PolicyError(f"re-pin commit does not identify an existing commit object: {commit}")
    reachable = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "main"], cwd=harness_root,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if reachable.returncode != 0:
        raise PolicyError(f"re-pin commit is not reachable from main: {commit}")
    lock_path = harness_root / "reviews/.repin.lock"
    token = _acquire_repin_lock(lock_path, force_lock=False, confirm=confirm or _confirmation)
    result: dict[str, Any] | None = None
    try:
        ledger_path = harness_root / "references/policies/repin_log.jsonl"
        rows = _read_repin_rows(ledger_path)
        matches = [row for row in rows if row.get("epoch") == epoch]
        if len(matches) != 1:
            raise PolicyError(f"re-pin epoch {epoch} must identify exactly one ledger row")
        if matches[0].get("commit") not in {None, commit}:
            raise PolicyError(f"re-pin epoch {epoch} already records a different commit")
        matches[0]["commit"] = commit
        markdown_path = harness_root / "references/policies/repin_log.md"
        ledger_before = ledger_path.read_bytes()
        markdown_before = markdown_path.read_bytes() if markdown_path.is_file() else None
        try:
            _atomic_bytes(ledger_path, b"".join((json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8") for row in rows))
            _atomic_bytes(markdown_path, _render_repin_log(rows).encode("utf-8"))
        except Exception:
            _atomic_bytes(ledger_path, ledger_before)
            if markdown_before is None:
                markdown_path.unlink(missing_ok=True)
            else:
                _atomic_bytes(markdown_path, markdown_before)
            raise
        result = {"status": "READY", "epoch": epoch, "commit": commit, "pins_recomputed": False}
        return result
    finally:
        try:
            _release_repin_lock(lock_path, token)
        except Exception as exc:
            if result is not None:
                result["status"] = "COMMITTED_CLEANUP_REQUIRED"
                result["cleanup_errors"] = [str(exc)]
            else:
                sys.stderr.write(f"cleanup warning while preserving primary re-pin commit-backfill failure: {exc}\n")


def _confirmation(message: str) -> bool:
    sys.stderr.write(message + " [yes/no]: ")
    sys.stderr.flush()
    return sys.stdin.readline().strip().lower() in {"yes", "y"}


def _lock_state(lock_path: Path) -> tuple[bool, str]:
    try:
        value = json.loads(lock_path.read_text(encoding="utf-8"))
        started = datetime.fromisoformat(str(value["started_at"]).replace("Z", "+00:00"))
        stale_after = int(value.get("stale_after", 1800))
        stale = (datetime.now(timezone.utc) - started).total_seconds() > stale_after
        return stale, f"lock held by pid={value.get('pid')} host={value.get('host')} since {value.get('started_at')}"
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return True, f"lock is unreadable: {exc}"


def _acquire_repin_lock(lock_path: Path, *, force_lock: bool, confirm: Callable[[str], bool]) -> bytes:
    """Acquire with O_EXCL and return the exact ownership bytes for safe release."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        stale, detail = _lock_state(lock_path)
        if not stale:
            raise PolicyError(detail + "; active re-pin locks cannot be force-recovered")
        if not force_lock:
            raise PolicyError(detail + "; stale lock recovery requires --force-lock plus explicit confirmation")
        if not confirm("Force recovery of existing re-pin lock?"):
            raise PolicyError("force-lock requires explicit user confirmation")
        try:
            lock_path.unlink()
        except OSError as exc:
            raise PolicyError(f"could not remove confirmed stale lock: {exc}") from exc
    token = uuid.uuid4().hex
    value = {"lock_id": token, "pid": os.getpid(), "host": socket.gethostname(), "started_at": _utc_now(), "stale_after": 1800}
    payload = _json_bytes(value)
    try:
        descriptor = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise PolicyError("re-pin lock was acquired concurrently; retry after the holder exits") from exc
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        lock_path.unlink(missing_ok=True)
        raise
    return payload


def _release_repin_lock(lock_path: Path, ownership: bytes) -> None:
    try:
        current = lock_path.read_bytes()
    except OSError as exc:
        raise PolicyError(f"re-pin lock ownership was lost: {lock_path}: {exc}") from exc
    if current != ownership:
        raise PolicyError(f"re-pin lock ownership changed; refusing to unlink: {lock_path}")
    lock_path.unlink()


def _acquire_graph_boundary(wiki_root: Path) -> tuple[Path, bytes]:
    """Coordinate a re-pin read transaction with every compliant graph writer."""
    lock_path = wiki_root.resolve() / "graphify-out/.graph-write.lock"
    payload = (json.dumps({
        "pid": os.getpid(), "token": str(uuid.uuid4()), "created_at": _utc_now(),
    }, sort_keys=True) + "\n").encode("utf-8")
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0))
    except FileExistsError as exc:
        raise PolicyError(f"graph write lock already exists; re-pin read boundary refused: {lock_path}") from exc
    except OSError as exc:
        raise PolicyError(f"graph write lock could not be created: {lock_path}: {exc}") from exc
    descriptor_open = True
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor_open = False
            written = stream.write(payload)
            if written != len(payload):
                raise OSError(f"short graph lock write: {written}/{len(payload)} bytes")
            stream.flush()
            os.fsync(stream.fileno())
    except Exception as exc:
        if descriptor_open:
            os.close(descriptor)
        try:
            lock_path.unlink(missing_ok=True)
        except OSError as cleanup_exc:
            raise PolicyError(f"graph write lock acquisition failed and cleanup failed: {exc}; {cleanup_exc}") from exc
        raise PolicyError(f"graph write lock acquisition failed: {exc}") from exc
    return lock_path, payload


def _release_graph_boundary(lock_path: Path, payload: bytes) -> None:
    try:
        current = lock_path.read_bytes()
    except OSError as exc:
        raise PolicyError(f"graph write lock ownership was lost during re-pin: {lock_path}: {exc}") from exc
    if current != payload:
        raise PolicyError(f"graph write lock ownership changed during re-pin; refusing to unlink: {lock_path}")
    lock_path.unlink()


def _open_project_round(project_root: Path) -> bool:
    """Read Planner-owned per-section log tails; never infer from global mtimes."""
    phase_path = project_root / "reviews/phase_state.json"
    if not phase_path.is_file():
        return False
    try:
        state = json.loads(phase_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"project phase_state.json is unreadable while checking open rounds: {exc}") from exc
    sections = state.get("sections", {})
    if not isinstance(sections, dict):
        raise PolicyError("project phase_state.json sections must be an object while checking open rounds")
    opening = {
        "initial_dispatch",
        "ph3_iteration_round",
        "ph3_iteration_round_manuscript",
        "stability_mode_escalated_to_full_ph3",
    }
    for name, section in sections.items():
        if not isinstance(section, dict) or not isinstance(section.get("phase_entry_log", []), list):
            raise PolicyError(f"project section {name!r} has malformed phase_entry_log")
        events = section.get("phase_entry_log", [])
        if events and isinstance(events[-1], dict) and events[-1].get("trigger") in opening:
            return True
    return False


def _delta_report(old_snapshot: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    old_snapshot = old_snapshot or {}
    old_members = set(old_snapshot.get("attestation_member_ids", []))
    new_members = set(current["attestation_member_ids"])
    old_lines = set(old_snapshot.get("exemplar_hash_lines", []))
    new_lines = set(current["exemplar_hash_lines"])
    old_unresolved = set(old_snapshot.get("unresolved_seed_ids", []))
    new_unresolved = set(current["unresolved_seed_ids"])
    old_warning = any(row.get("code") == "RA-DNR-DEGENERATE" for row in old_snapshot.get("warnings", []) if isinstance(row, dict))
    new_warning = any(row.get("code") == "RA-DNR-DEGENERATE" for row in current["warnings"])
    return {
        "resolved_seed_count": [len(old_snapshot.get("seed_resolution_map", {})) if old_snapshot else None, len(current["seed_resolution_map"])],
        "primary_communities": [old_snapshot.get("primary_communities") if old_snapshot else None, current["primary_communities"]],
        "degeneracy_warning": ["present" if old_warning else ("cleared" if old_snapshot else None), "present" if new_warning else "cleared"],
        "unresolved_seed_ids": {"added": sorted(new_unresolved - old_unresolved, key=_utf8_key), "removed": sorted(old_unresolved - new_unresolved, key=_utf8_key)},
        "membership": {"added_count": len(new_members - old_members), "removed_count": len(old_members - new_members), "added_sample": sorted(new_members - old_members, key=_utf8_key)[:10], "removed_sample": sorted(old_members - new_members, key=_utf8_key)[:10]},
        "exemplar_tuples_changed": sorted(old_lines ^ new_lines, key=_utf8_key),
    }


_LOCKED_EXEMPLAR_ROLES = {
    "centroid": "yu-et-al-2011-social-modeling",
    "intentional-root": "dennett-1987-intentional-stance",
}


def _stage_exemplar_change(
    profile: dict[str, Any], *, wiki_root: Path, add_key: str | None,
    drop_key: str | None, role: str | None, warrant_scope: str | None,
    confirm_drop_locked_role: bool,
) -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, str]], str | None]:
    """Validate and stage one register-definition mutation in memory."""
    staged = copy.deepcopy(profile)
    members = staged["domain_native_register"]["exemplar_members"]
    if add_key and drop_key:
        raise PolicyError("--add-exemplar and --drop-exemplar are mutually exclusive")
    if not add_key and not drop_key:
        if role is not None or warrant_scope is not None or confirm_drop_locked_role:
            raise PolicyError("exemplar modifier flags require --add-exemplar or --drop-exemplar")
        return staged, [], [], None
    if add_key:
        page = _contained(wiki_root, f"wiki/sources/{add_key}.md")
        if not page.is_file():
            raise PolicyError(f"exemplar source page missing: {page}; create wiki/sources/{add_key}.md and ground it before retrying")
        live_grounding = _live_grounding_status(page)
        if role is None:
            raise PolicyError("--add-exemplar requires --role")
        locked_key = _LOCKED_EXEMPLAR_ROLES.get(role)
        if locked_key is not None and add_key != locked_key:
            raise PolicyError(f"role {role} is locked to {locked_key}")
        if locked_key is not None and any(item.get("role") == role for item in members):
            raise PolicyError(f"singleton role {role} is already occupied and locked")
        if role == "intentional-root" and warrant_scope == "both":
            raise PolicyError("intentional-root requires warrant_scope argument-only; explicit both is contradictory")
        effective_scope = warrant_scope or ("argument-only" if role == "intentional-root" else "both")
        if any(item["source_key"] == add_key for item in members):
            raise PolicyError(f"duplicate exemplar source_key: {add_key}")
        member = {"source_key": add_key, "role": role, "grounding": live_grounding, "warrant_scope": effective_scope}
        members.append(member)
        return staged, [{"source_key": add_key, "warrant_scope": effective_scope}], [], add_key
    if role is not None or warrant_scope is not None:
        raise PolicyError("--role and --warrant-scope apply only to --add-exemplar")
    matched = next((item for item in members if item["source_key"] == drop_key), None)
    if matched is None:
        raise PolicyError(f"cannot drop absent exemplar source_key: {drop_key}")
    if matched.get("role") in _LOCKED_EXEMPLAR_ROLES and not confirm_drop_locked_role:
        raise PolicyError("dropping a locked-role member requires --confirm-drop-locked-role")
    effective_scope = _effective_warrant_scope(matched)
    members.remove(matched)
    return staged, [], [{"source_key": str(drop_key), "warrant_scope": effective_scope}], None


def run_repin(*, harness_root: Path, profile_path: Path, wiki_root: Path | None, workspace_root: Path | None,
              project_root: Path | None, trigger: str, dry_run: bool, allow_unrelated_dirty: bool,
              force_lock: bool, add_exemplar: str | None = None, drop_exemplar: str | None = None,
              role: str | None = None, warrant_scope: str | None = None,
              semantic_graph_path: str | None = None,
              confirm_drop_locked_role: bool = False,
              confirm: Callable[[str], bool] = _confirmation) -> dict[str, Any]:
    """Execute the accepted two-phase re-pin contract without writing phase_state.json."""
    harness_root = harness_root.resolve()
    profile_path = profile_path.resolve()
    canonical_profile = (harness_root / "references/policies/reader_accessibility.v1.json").resolve()
    if profile_path != canonical_profile:
        raise PolicyError(f"re-pin profile must be the canonical package profile: {canonical_profile}")
    schema_path = harness_root / "references/schemas/reader_accessibility_profile.schema.json"
    if not _schema_supports_repin(schema_path):
        raise PolicyError("schema migration required: add expected_verification.pin_epoch and pinned_at before re-pin")
    lock_path = harness_root / "reviews/.repin.lock"
    lock_token = _acquire_repin_lock(lock_path, force_lock=force_lock, confirm=confirm)
    graph_boundary: tuple[Path, bytes] | None = None
    result: dict[str, Any] | None = None
    try:
        # The O_EXCL lock is already held, so its untracked status is owned by
        # this invocation rather than a prior re-pin diff. A pre-existing lock
        # cannot reach this point because acquisition refuses it first.
        dirty = [path for path in _git_dirty_paths(harness_root) if path != "reviews/.repin.lock"]
        prior_refusal = repin_prior_diff_refusal(dirty)
        if prior_refusal:
            raise PolicyError(prior_refusal)
        pin_dirty, unrelated = classify_repin_dirty_paths(dirty)
        refusal = repin_dirty_refusal(pin_dirty, unrelated, allow_unrelated_dirty=allow_unrelated_dirty)
        if refusal:
            raise PolicyError(refusal)
        if project_root is not None and _open_project_round(project_root.resolve()):
            raise PolicyError("project has an open round; rebind request is deferred until it closes")
        try:
            old_profile_bytes = profile_path.read_bytes()
        except OSError as exc:
            raise PolicyError(f"profile unreadable: {exc}") from exc
        profile = _load_profile_bytes(old_profile_bytes, schema_path)
        old_profile_hash = hashlib.sha256(old_profile_bytes).hexdigest()
        if harness_root == ROOT.resolve() and (wiki_root is not None or workspace_root is not None):
            raise PolicyError("canonical package re-pin refuses wiki/workspace root overrides; use the profile-bound corpus")
        effective_wiki, effective_workspace, _, _ = _resolve_register_roots(
            profile, wiki_root=wiki_root, workspace_root=workspace_root, harness_root=harness_root
        )
        graph_boundary = _acquire_graph_boundary(effective_wiki)
        prospective, members_added, members_dropped, ingested_key = _stage_exemplar_change(
            profile, wiki_root=effective_wiki, add_key=add_exemplar, drop_key=drop_exemplar,
            role=role, warrant_scope=warrant_scope,
            confirm_drop_locked_role=confirm_drop_locked_role,
        )
        old_graph_relative = profile["domain_native_register"]["corpus_binding"]["graph"]["path"]
        if semantic_graph_path is not None:
            if add_exemplar is not None or drop_exemplar is not None:
                raise PolicyError("--semantic-graph-path cannot be combined with exemplar membership changes")
            normalized_graph_path = semantic_graph_path.replace("\\", "/")
            if re.fullmatch(
                r"knowledge/LLM wiki/graphify-out/semantic-qualifications/"
                r"semq-\d{8}T\d{6}Z-[0-9a-f]{8}/qualified\.graph\.json",
                normalized_graph_path,
            ) is None:
                raise PolicyError(
                    "--semantic-graph-path must name a fresh semantic-qualification qualified.graph.json"
                )
            prospective["domain_native_register"]["corpus_binding"]["graph"]["path"] = normalized_graph_path
        validate_profile(prospective, schema_path)
        new_graph_relative = prospective["domain_native_register"]["corpus_binding"]["graph"]["path"]
        graph_path = _contained(effective_workspace, new_graph_relative)
        if _tracked_path_dirty(graph_path):
            raise PolicyError(f"pin-affecting tracked graph is dirty: {graph_path}")
        current = resolve_domain_native_register(
            prospective, wiki_root=wiki_root, workspace_root=workspace_root,
            harness_root=harness_root, _ingested_key=ingested_key,
        )
        if ingested_key:
            resolved_ingest = next(item for item in current["exemplar_members"] if item["source_key"] == ingested_key)
            next(item for item in prospective["domain_native_register"]["exemplar_members"] if item["source_key"] == ingested_key)["grounding"] = resolved_ingest["grounding"]
        expected = profile["domain_native_register"]["expected_verification"]
        delta_class = _delta_class(
            expected["attestation_view_pin"], current["attestation_view_pin"],
            expected["exemplar_view_pin"], current["exemplar_view_pin"],
            corpus_changed=old_graph_relative != new_graph_relative,
        )
        ledger_path = harness_root / "references/policies/repin_log.jsonl"
        prior_rows = _read_repin_rows(ledger_path)
        event_epoch = max([expected["pin_epoch"], *[int(row.get("epoch", 0)) for row in prior_rows]]) + 1
        snapshot_ref = f"reviews/.harness/repin/epoch-{event_epoch}.snapshot.json"
        previous_snapshot = None
        if prior_rows:
            candidate = harness_root / prior_rows[-1].get("snapshot_ref", "")
            if candidate.is_file():
                previous_snapshot = json.loads(candidate.read_text(encoding="utf-8"))
        snapshot = {
            "epoch": event_epoch, "captured_at": _utc_now(),
            "graph_sha256_provenance": current["graph_sha256_provenance"],
            "graph_mtime_utc_provenance": current["graph_mtime_utc_provenance"],
            "graph_extraction_mode": current["graph_extraction_mode"],
            "graph_semantic_status": current["graph_semantic_status"],
            "graph_semantic_scope": current["graph_semantic_scope"],
            "attestation_view_pin": current["attestation_view_pin"], "exemplar_view_pin": current["exemplar_view_pin"],
            "seed_resolution_map": current["seed_resolution_map"], "seed_resolution_ties": current["seed_resolution_ties"],
            "unresolved_seed_ids": current["unresolved_seed_ids"], "primary_communities": current["primary_communities"],
            "warnings": current["warnings"], "attestation_member_ids": current["attestation_member_ids"],
            "member_count": len(current["attestation_member_ids"]), "exemplar_hash_lines": current["exemplar_hash_lines"],
            "exemplar_members": current["exemplar_members"],
            "surface_exemplar_members": current["surface_exemplar_members"],
            "argument_exemplar_members": current["argument_exemplar_members"],
        }
        report = _delta_report(previous_snapshot, current)
        report["graph_path"] = {"old": old_graph_relative, "new": new_graph_relative}
        report["exemplar_members_added"] = members_added
        report["exemplar_members_dropped"] = members_dropped
        pinned_at = _utc_now()
        new_profile_hash = old_profile_hash
        intended_profile_bytes = old_profile_bytes
        applied = False
        if delta_class != "none" and not dry_run:
            sys.stderr.write("Register re-pin delta report:\n" + json.dumps(report, indent=2, ensure_ascii=False) + "\n")
            sys.stderr.flush()
            if not confirm("Apply the reported semantic register re-pin?"):
                (harness_root / snapshot_ref).unlink(missing_ok=True)
                raise PolicyError("real re-pin delta requires explicit user confirmation")
            try:
                verified = resolve_domain_native_register(
                    prospective, wiki_root=wiki_root, workspace_root=workspace_root,
                    harness_root=harness_root, _ingested_key=ingested_key,
                )
            except Exception:
                (harness_root / snapshot_ref).unlink(missing_ok=True)
                raise
            if verified != current:
                (harness_root / snapshot_ref).unlink(missing_ok=True)
                raise PolicyError("domain-native inputs changed during confirmation; refusing stale re-pin apply")
            updated = copy.deepcopy(prospective)
            updated["profile_version"] = _patch_bump(updated["profile_version"])
            updated_expected = updated["domain_native_register"]["expected_verification"]
            updated_expected.update(attestation_view_pin=current["attestation_view_pin"], exemplar_view_pin=current["exemplar_view_pin"], pin_epoch=event_epoch, pinned_at=pinned_at)
            updated["domain_native_register"]["corpus_binding"]["graph"]["observed_sha256_at_review"] = current["graph_sha256_provenance"]
            validate_profile(updated, schema_path)
            intended_profile_bytes = _json_bytes(updated)
            new_profile_hash = hashlib.sha256(intended_profile_bytes).hexdigest()
            applied = True
        unchanged_fields = delta_class == "none"
        row = {
            "epoch": event_epoch, "pinned_at": pinned_at, "dry_run": dry_run,
            "attestation_view_pin": {"old": None if unchanged_fields else expected["attestation_view_pin"], "new": None if unchanged_fields else current["attestation_view_pin"]},
            "exemplar_view_pin": {"old": None if unchanged_fields else expected["exemplar_view_pin"], "new": None if unchanged_fields else current["exemplar_view_pin"]},
            "profile_sha256": {"old": None if unchanged_fields else old_profile_hash, "new": None if unchanged_fields else (new_profile_hash if applied else None)},
            "graph_sha256_provenance": current["graph_sha256_provenance"], "delta_class": delta_class,
            "delta_summary": report, "snapshot_ref": snapshot_ref, "trigger": trigger,
            "operator": getpass.getuser(), "commit": None,
        }
        rows = prior_rows + [row]
        event_bytes = (json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        ledger_before = ledger_path.read_bytes() if ledger_path.is_file() else None
        ledger_after = (b"" if ledger_before is None else ledger_before) + event_bytes
        markdown_path = harness_root / "references/policies/repin_log.md"
        markdown_before = markdown_path.read_bytes() if markdown_path.is_file() else None
        markdown_after = _render_repin_log(rows).encode("utf-8")
        snapshot_bytes = _json_bytes(snapshot)
        if profile_path.read_bytes() != old_profile_bytes:
            (harness_root / snapshot_ref).unlink(missing_ok=True)
            raise PolicyError("profile changed after compute/confirmation; refusing concurrent overwrite")
        request_path: Path | None = None
        request_reused = False
        request_to_create: bytes | None = None
        if project_root is not None and not dry_run:
            resolved_project_root = project_root.resolve()
            if _open_project_round(resolved_project_root):
                raise PolicyError("project opened a round during re-pin; request write refused")
            current_expected = (updated if applied else profile)["domain_native_register"]["expected_verification"]
            current_profile_hash = new_profile_hash if applied else old_profile_hash
            source_row = next((item for item in reversed(rows) if item.get("delta_class") != "none" and item.get("profile_sha256", {}).get("new") == current_profile_hash), row)
            request_path = resolved_project_root / "reviews/repin_rebind_request.json"
            if semantic_graph_path is not None:
                phase_state_path = resolved_project_root / "reviews/phase_state.json"
                try:
                    phase_state_bytes = phase_state_path.read_bytes()
                    phase_state = json.loads(phase_state_bytes)
                    prior_binding = phase_state["milestone_framework"]["policy_bindings"]["reader_accessibility"]
                except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
                    raise PolicyError(f"cannot bind semantic activation request to phase state: {exc}") from exc
                if (
                    not isinstance(prior_binding, dict)
                    or prior_binding.get("binding_version") != "2.0.0"
                    or prior_binding.get("binding_kind") != "reader_profile"
                    or prior_binding.get("semantic_usage") != "not_invoked"
                    or not isinstance(prior_binding.get("resolved_path"), str)
                    or not isinstance(prior_binding.get("resolved_sha256"), str)
                ):
                    raise PolicyError("semantic activation request requires a current reader-profile-v2 binding")
                prior_resolved = _contained(resolved_project_root, prior_binding["resolved_path"])
                if not prior_resolved.is_file() or _hash(prior_resolved) != prior_binding["resolved_sha256"]:
                    raise PolicyError("reader-profile-v2 resolved artifact is missing or stale")
                receipt_entry = next(
                    (item for item in current["provenance"] if item.get("role") == "semantic_receipt"),
                    None,
                )
                if not isinstance(receipt_entry, dict):
                    raise PolicyError("qualified semantic graph lacks receipt provenance")
                receipt_path = Path(str(receipt_entry.get("path"))).resolve()
                try:
                    receipt_relative = receipt_path.relative_to(effective_wiki.resolve()).as_posix()
                except ValueError as exc:
                    raise PolicyError("semantic qualification receipt escapes the bound wiki root") from exc
                if not receipt_path.is_file() or _hash(receipt_path) != receipt_entry.get("sha256"):
                    raise PolicyError("semantic qualification receipt provenance is stale")
                if source_row is not row:
                    raise PolicyError(
                        "semantic activation request must bind the re-pin event created by this transaction"
                    )
                request_fields = {
                    "schema_version": "reader-semantic-activation.v1",
                    "operation": "reader_profile_v2_to_semantic",
                    "phase_state_sha256": hashlib.sha256(phase_state_bytes).hexdigest(),
                    "prior_binding_sha256": hashlib.sha256(
                        (json.dumps(prior_binding, indent=2, sort_keys=True) + "\n").encode("utf-8")
                    ).hexdigest(),
                    "prior_resolved_sha256": prior_binding["resolved_sha256"],
                    "pin_epoch": current_expected["pin_epoch"],
                    "profile_sha256": current_profile_hash,
                    "attestation_view_pin": current["attestation_view_pin"],
                    "exemplar_view_pin": current["exemplar_view_pin"],
                    "delta_class": source_row["delta_class"],
                    "repin_log_ref": f"references/policies/repin_log.jsonl#epoch-{source_row['epoch']}",
                    "repin_event_sha256": hashlib.sha256(event_bytes).hexdigest(),
                    "repin_ledger_sha256": hashlib.sha256(ledger_after).hexdigest(),
                    "repin_snapshot_ref": source_row["snapshot_ref"],
                    "repin_snapshot_sha256": hashlib.sha256(snapshot_bytes).hexdigest(),
                    "graph_path": new_graph_relative,
                    "graph_sha256": current["graph_sha256_provenance"],
                    "qualification_receipt_path": receipt_relative,
                    "qualification_receipt_sha256": receipt_entry["sha256"],
                    "status": "pending",
                }
            else:
                request_fields = {
                    "pin_epoch": current_expected["pin_epoch"],
                    "profile_sha256": current_profile_hash,
                    "attestation_view_pin": current["attestation_view_pin"],
                    "exemplar_view_pin": current["exemplar_view_pin"],
                    "delta_class": source_row["delta_class"],
                    "repin_log_ref": f"references/policies/repin_log.jsonl#epoch-{source_row['epoch']}",
                    "status": "pending",
                }
            if request_path.exists():
                try:
                    existing_request = json.loads(request_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise PolicyError(f"existing rebind request changed or is unreadable; refusing overwrite: {exc}") from exc
                comparable = {key: existing_request.get(key) for key in request_fields}
                if comparable != request_fields or not isinstance(existing_request.get("request_id"), str):
                    raise PolicyError("a different rebind request is already pending; Planner must apply or archive it before retry")
                request_reused = True
            else:
                request_to_create = _json_bytes({"request_id": str(uuid.uuid4()), **request_fields})
        snapshot_path = harness_root / snapshot_ref
        request_published = False
        try:
            _atomic_create_bytes(snapshot_path, snapshot_bytes)
            if applied:
                _atomic_bytes(profile_path, intended_profile_bytes)
            _atomic_bytes(ledger_path, ledger_after)
            _atomic_bytes(markdown_path, markdown_after)
            if applied and (profile_path.read_bytes() != intended_profile_bytes or _hash(profile_path) != new_profile_hash):
                raise PolicyError("atomic profile full-byte read-back assertion failed")
            post_install = resolve_domain_native_register(
                updated if applied else prospective,
                wiki_root=wiki_root, workspace_root=workspace_root,
                harness_root=harness_root, _ingested_key=ingested_key,
            )
            stable_keys = (
                "graph_sha256_provenance", "graph_extraction_mode", "graph_semantic_status",
                "graph_semantic_scope", "attestation_view_pin", "exemplar_view_pin",
                "seed_resolution_map", "seed_resolution_ties", "unresolved_seed_ids",
                "primary_communities", "attestation_member_ids", "exemplar_hash_lines",
                "exemplar_members", "surface_exemplar_members", "argument_exemplar_members",
            )
            if any(post_install[key] != current[key] for key in stable_keys):
                raise PolicyError("domain-native inputs changed during final installation; re-pin transaction rolled back")
            if request_to_create is not None and request_path is not None:
                _atomic_create_bytes(request_path, request_to_create)
                request_published = True
                post_publish = resolve_domain_native_register(
                    updated if applied else prospective,
                    wiki_root=wiki_root, workspace_root=workspace_root,
                    harness_root=harness_root, _ingested_key=ingested_key,
                )
                if any(post_publish[key] != current[key] for key in stable_keys):
                    raise PolicyError("domain-native inputs changed during rebind request publication; package transaction rolled back")
        except Exception as exc:
            conflicts: list[str] = []

            def restore_owned(path: Path, before: bytes | None, owned_postimage: bytes) -> None:
                if not path.exists():
                    if before is not None:
                        conflicts.append(str(path))
                    return
                live = path.read_bytes()
                if live == owned_postimage:
                    if before is None:
                        path.unlink()
                    else:
                        _atomic_bytes(path, before)
                elif before is None or live != before:
                    conflicts.append(str(path))

            restore_owned(markdown_path, markdown_before, markdown_after)
            restore_owned(ledger_path, ledger_before, ledger_after)
            if applied:
                restore_owned(profile_path, old_profile_bytes, intended_profile_bytes)
            restore_owned(snapshot_path, None, snapshot_bytes)
            if conflicts:
                detail = (
                    f"{exc}; rollback preserved external conflicting bytes: "
                    + ", ".join(sorted(set(conflicts)))
                )
                if request_published and request_path is not None:
                    detail += "; published rebind request remains inert for Planner inspection"
                raise PolicyError(detail) from exc
            if request_published and request_path is not None:
                raise PolicyError(
                    f"{exc}; published rebind request was preserved but is inert after package rollback; "
                    "Planner must inspect and archive it before retry"
                ) from exc
            raise
        result = {"status": "READY", "delta_class": delta_class, "delta_report": report, "epoch": event_epoch,
                  "applied": applied, "dry_run": dry_run, "snapshot_ref": snapshot_ref,
                  "rebind_request": str(request_path) if request_path else None, "request_reused": request_reused,
                  "read_back_verified": applied, "warnings": current["warnings"],
                  "commit_proposal": "chore(accessibility): re-pin domain-native register views" if applied else None}
        return result
    finally:
        cleanup_errors: list[str] = []
        try:
            if graph_boundary is not None:
                _release_graph_boundary(*graph_boundary)
        except Exception as exc:
            cleanup_errors.append(str(exc))
        try:
            _release_repin_lock(lock_path, lock_token)
        except Exception as exc:
            cleanup_errors.append(str(exc))
        if cleanup_errors:
            if result is not None:
                result["status"] = "COMMITTED_CLEANUP_REQUIRED"
                result["cleanup_errors"] = cleanup_errors
            else:
                sys.stderr.write("cleanup warning while preserving primary re-pin failure: " + "; ".join(cleanup_errors) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument(
        "--wiki-root",
        type=Path,
        default=None,
        help="override wiki root (default: profile corpus_binding.path_roots.wiki_root)",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=None,
        help="override workspace root (default: profile corpus_binding.path_roots.workspace_root)",
    )
    parser.add_argument(
        "--harness-root",
        type=Path,
        default=None,
        help="override harness/package root (default: directory containing this package)",
    )
    parser.add_argument("--out", type=Path)
    parser.add_argument("--render-view", action="store_true", help="render the generated human-readable numeric policy view")
    parser.add_argument("--repin", action="store_true", help="run the deliberate semantic register re-pin workflow")
    parser.add_argument("--dry-run", action="store_true", help="record and snapshot a re-pin computation without applying a real delta")
    parser.add_argument("--trigger", choices=("milestone", "snowball", "mf-policy-discovery", "manual"), default="manual")
    parser.add_argument("--allow-unrelated-dirty", action="store_true")
    parser.add_argument("--force-lock", action="store_true")
    parser.add_argument("--add-exemplar", metavar="SOURCE_KEY")
    parser.add_argument("--drop-exemplar", metavar="SOURCE_KEY")
    parser.add_argument("--role", help="register role for --add-exemplar")
    parser.add_argument("--warrant-scope", choices=("both", "argument-only"))
    parser.add_argument("--confirm-drop-locked-role", action="store_true")
    parser.add_argument(
        "--semantic-graph-path",
        help="stage a fresh semantic-qualification graph as a confirmed corpus-binding migration",
    )
    parser.add_argument("--backfill-repin-commit", metavar="OBJECT_ID", help="backfill the commit field for an existing re-pin event; never recomputes pins")
    parser.add_argument("--repin-epoch", type=int, help="ledger event epoch used with --backfill-repin-commit")
    args = parser.parse_args(argv)
    if args.project_root is not None:
        from destination_capability import (
            DestinationRefused,
            guard_project_root,
            guard_repin_project_root,
        )
        # Re-pin writes are confined to the re-pin lane inside one work-id root;
        # every other subcommand keeps the strict project-root guard.
        try:
            if args.repin:
                guard_repin_project_root(args.project_root)
            else:
                guard_project_root(args.project_root)
        except DestinationRefused as exc:
            print(f"[BLOCKER] {exc}")
            return 4
    try:
        if args.backfill_repin_commit:
            if args.repin_epoch is None:
                raise PolicyError("--backfill-repin-commit requires --repin-epoch")
            result = backfill_repin_commit(args.harness_root or ROOT, args.repin_epoch, args.backfill_repin_commit)
        elif args.repin:
            effective_harness = args.harness_root or ROOT
            result = run_repin(
                harness_root=effective_harness, profile_path=args.profile,
                wiki_root=args.wiki_root, workspace_root=args.workspace_root,
                project_root=args.project_root, trigger=args.trigger, dry_run=args.dry_run,
                allow_unrelated_dirty=args.allow_unrelated_dirty, force_lock=args.force_lock,
                add_exemplar=args.add_exemplar, drop_exemplar=args.drop_exemplar,
                role=args.role, warrant_scope=args.warrant_scope,
                semantic_graph_path=args.semantic_graph_path,
                confirm_drop_locked_role=args.confirm_drop_locked_role,
            )
        else:
            result = resolve_policy(args.project_root, profile_path=args.profile, wiki_root=args.wiki_root, workspace_root=args.workspace_root, harness_root=args.harness_root)
    except PolicyError as exc:
        print(json.dumps({"status": "MISCONFIGURED", "code": "RA-POLICY", "message": str(exc)}))
        return 4
    payload = render_policy_view(result["resolved_profile"]) if args.render_view and not args.repin else json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8", newline="\n")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
