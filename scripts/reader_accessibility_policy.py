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
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from os import stat_result
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "references" / "policies" / "reader_accessibility.v1.json"
PROFILE_SCHEMA = ROOT / "references" / "schemas" / "reader_accessibility_profile.schema.json"
CHECK8_SCHEMA = ROOT / "references" / "schemas" / "check8_evidence.schema.json"
CANDIDATE_SCHEMA = ROOT / "references" / "schemas" / "reader_accessibility_candidates.schema.json"
PHASES = ("Ph1", "Ph2", "Ph3", "Ph4")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DEFAULT_WIKI_ROOT = Path("B:/Agents/knowledge/LLM wiki")
DEFAULT_WORKSPACE_ROOT = Path("B:/Agents")


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
    if wiki.resolve() == profile_wiki.resolve() and workspace.resolve() == profile_workspace.resolve():
        meta["path_roots_mode"] = "profile"
    else:
        meta["path_roots_mode"] = "override"
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
            return self.data.decode("utf-8")
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
            return self._items[resolved]
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
                current = _stamp(item.path.stat())
            except OSError as exc:
                raise PolicyError(f"domain-native input changed during resolution: {item.role}: {item.path}: {exc}") from exc
            if current != item.stamp:
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
    graph_path = _contained(workspace_root, graph_rel)
    snapshots = _SnapshotSet(_snapshot_hook)
    try:
        graph_snapshot = snapshots.capture(graph_path, "graph_provenance_only")
        graph = json.loads(graph_snapshot.text())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PolicyError(f"domain-native graph unreadable: {graph_path}: {exc}") from exc
    if not isinstance(graph, dict):
        raise PolicyError("domain-native graph root must be an object")
    nodes = graph.get("nodes"); links = graph.get("links")
    if not isinstance(nodes, list) or not isinstance(links, list):
        raise PolicyError("domain-native graph requires nodes and links arrays")
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
            all_candidate_ids = [node["id"] for node in candidates]
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
    primary = sorted({by_id[node_id]["community"] for node_id in resolution.values()})
    primary_members = {node["id"] for node in nodes if node["community"] in primary}
    membership = set(primary_members)
    for index, link in enumerate(links):
        if not isinstance(link, dict) or not isinstance(link.get("source"), str) or not isinstance(link.get("target"), str):
            raise PolicyError(f"domain-native graph link {index} lacks canonical endpoints")
        if "_src" not in link or "_tgt" not in link or link["source"] != link["_src"] or link["target"] != link["_tgt"]:
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
        admitted_members.append({
            "source_key": key,
            "role": member["role"],
            "grounding": normalize_tier(grounding),
            "warrant_scope": _effective_warrant_scope(member),
        })
    exemplar_pin = hashlib.sha256("\n".join(sorted(exemplar_lines, key=_utf8_key)).encode("utf-8")).hexdigest()
    graph_hash = graph_snapshot.sha256
    harness_profile = _contained(harness_root, "references/policies/reader_accessibility.v1.json")
    profile_snapshot = snapshots.capture(harness_profile, "register_profile")
    provenance.extend([
        {"role":"graph_provenance_only","path":str(graph_path),"sha256":graph_hash},
        {"role":"register_profile","path":str(harness_profile),"sha256":profile_snapshot.sha256},
    ])
    warnings=[]
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
    surface_keys = {item["source_key"] for item in surface_exemplar_members(profile)}
    return {"register_class":"domain-native","attestation_view_pin":attestation_pin,"exemplar_view_pin":exemplar_pin,"graph_sha256_provenance":graph_hash,"graph_mtime_utc_provenance":datetime.fromtimestamp(graph_snapshot.stamp[3] / 1_000_000_000, tz=timezone.utc).isoformat().replace("+00:00", "Z"),"seed_resolution_map":resolution,"seed_resolution_ties":ties,"unresolved_seed_ids":unresolved,"primary_communities":primary,"attestation_member_ids":sorted(membership,key=_utf8_key),"exemplar_hash_lines":sorted(exemplar_lines,key=_utf8_key),"exemplar_members":admitted_members,"surface_exemplar_members":[item for item in admitted_members if item["source_key"] in surface_keys],"argument_exemplar_members":admitted_members,"warnings":warnings,"path_roots":path_roots_meta,"provenance":provenance}


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
        data = json.loads(payload.decode("utf-8"))
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


def resolve_policy(project_root: Path | None, *, profile_path: Path = DEFAULT_PROFILE,
                   wiki_root: Path | None = None, workspace_root: Path | None = None,
                   harness_root: Path | None = None) -> dict[str, Any]:
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
    register = resolve_domain_native_register(profile, wiki_root=wiki_root, workspace_root=workspace_root, harness_root=harness_root)
    for source in bindings:
        owner = ROOT if source["scope"] == "package" else project_root
        if owner is not None:
            recorded_path = str((owner / source["path"]).resolve()) if source["scope"] == "package" else f"project://{source['path']}"
            register["provenance"].append({"role": source["role"], "path": recorded_path, "sha256": source["sha256"]})
    return {"contract_version": "1.1.0", "profile_path": profile_relative, "profile_sha256": _hash(profile_path), "register_class": "domain-native", "passage_scope_class": passage_scope_class, "project_identity": project_identity, "resolved_profile": resolved, "source_bindings": bindings, "attestation_view_pin": register["attestation_view_pin"], "exemplar_view_pin": register["exemplar_view_pin"], "graph_sha256_provenance": register["graph_sha256_provenance"], "register_provenance": register}


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
    return {"profile_path": resolved["profile_path"], "profile_sha256": resolved["profile_sha256"], "resolved_path": relative, "resolved_sha256": _hash(path), "source_bindings": copy.deepcopy(resolved["source_bindings"]), "project_identity": resolved.get("project_identity"), "attestation_view_pin": resolved["attestation_view_pin"], "exemplar_view_pin": resolved["exemplar_view_pin"], "pin_epoch": expected["pin_epoch"], "pinned_at": expected["pinned_at"], "graph_sha256_provenance": resolved["graph_sha256_provenance"], "register_provenance": copy.deepcopy(resolved["register_provenance"]), "transitions": {key: {"state": "active", "observed_count": 0, "last_event_sequence": None, "events": []} for key in ("G", "H", "VE")}}


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
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise PolicyError(f"destination appeared concurrently; refusing overwrite: {path}") from exc
        except OSError as exc:
            raise PolicyError(f"exclusive atomic publication failed for {path}: {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)


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


def _delta_class(old_attestation: str, new_attestation: str, old_exemplar: str, new_exemplar: str) -> str:
    attestation = old_attestation != new_attestation
    exemplar = old_exemplar != new_exemplar
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
    lock_path = harness_root / "reviews/.repin.lock"
    token = _acquire_repin_lock(lock_path, force_lock=False, confirm=confirm or _confirmation)
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
        return {"status": "READY", "epoch": epoch, "commit": commit, "pins_recomputed": False}
    finally:
        _release_repin_lock(lock_path, token)


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


def _acquire_repin_lock(lock_path: Path, *, force_lock: bool, confirm: Callable[[str], bool]) -> str:
    """Acquire with O_EXCL and return the ownership token used for safe release."""
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
    try:
        descriptor = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise PolicyError("re-pin lock was acquired concurrently; retry after the holder exits") from exc
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(_json_bytes(value))
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        lock_path.unlink(missing_ok=True)
        raise
    return token


def _release_repin_lock(lock_path: Path, token: str) -> None:
    try:
        current = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if current.get("lock_id") == token:
        lock_path.unlink(missing_ok=True)


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
    "centroid": "yu-1995-istar",
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
        effective_wiki, effective_workspace, _, _ = _resolve_register_roots(
            profile, wiki_root=wiki_root, workspace_root=workspace_root, harness_root=harness_root
        )
        prospective, members_added, members_dropped, ingested_key = _stage_exemplar_change(
            profile, wiki_root=effective_wiki, add_key=add_exemplar, drop_key=drop_exemplar,
            role=role, warrant_scope=warrant_scope,
            confirm_drop_locked_role=confirm_drop_locked_role,
        )
        validate_profile(prospective, schema_path)
        graph_path = _contained(effective_workspace, profile["domain_native_register"]["corpus_binding"]["graph"]["path"])
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
        delta_class = _delta_class(expected["attestation_view_pin"], current["attestation_view_pin"], expected["exemplar_view_pin"], current["exemplar_view_pin"])
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
            "attestation_view_pin": current["attestation_view_pin"], "exemplar_view_pin": current["exemplar_view_pin"],
            "seed_resolution_map": current["seed_resolution_map"], "seed_resolution_ties": current["seed_resolution_ties"],
            "unresolved_seed_ids": current["unresolved_seed_ids"], "primary_communities": current["primary_communities"],
            "warnings": current["warnings"], "attestation_member_ids": current["attestation_member_ids"],
            "member_count": len(current["attestation_member_ids"]), "exemplar_hash_lines": current["exemplar_hash_lines"],
            "exemplar_members": current["exemplar_members"],
            "surface_exemplar_members": current["surface_exemplar_members"],
            "argument_exemplar_members": current["argument_exemplar_members"],
        }
        _atomic_bytes(harness_root / snapshot_ref, _json_bytes(snapshot))
        report = _delta_report(previous_snapshot, current)
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
        ledger_before = ledger_path.read_bytes() if ledger_path.is_file() else None
        ledger_after = (b"" if ledger_before is None else ledger_before) + (json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        markdown_path = harness_root / "references/policies/repin_log.md"
        markdown_before = markdown_path.read_bytes() if markdown_path.is_file() else None
        if profile_path.read_bytes() != old_profile_bytes:
            (harness_root / snapshot_ref).unlink(missing_ok=True)
            raise PolicyError("profile changed after compute/confirmation; refusing concurrent overwrite")
        try:
            if applied:
                _atomic_bytes(profile_path, intended_profile_bytes)
            _atomic_bytes(ledger_path, ledger_after)
            _atomic_bytes(markdown_path, _render_repin_log(rows).encode("utf-8"))
            if applied and (profile_path.read_bytes() != intended_profile_bytes or _hash(profile_path) != new_profile_hash):
                raise PolicyError("atomic profile full-byte read-back assertion failed")
        except Exception:
            if markdown_before is None:
                markdown_path.unlink(missing_ok=True)
            else:
                _atomic_bytes(markdown_path, markdown_before)
            if ledger_before is None:
                ledger_path.unlink(missing_ok=True)
            else:
                _atomic_bytes(ledger_path, ledger_before)
            if applied and profile_path.is_file() and profile_path.read_bytes() == intended_profile_bytes:
                _atomic_bytes(profile_path, old_profile_bytes)
            (harness_root / snapshot_ref).unlink(missing_ok=True)
            raise
        request_path = None
        request_reused = False
        if project_root is not None:
            if _open_project_round(project_root.resolve()):
                raise PolicyError("project opened a round during re-pin; request write refused")
            current_expected = (updated if applied else profile)["domain_native_register"]["expected_verification"]
            current_profile_hash = new_profile_hash if applied else old_profile_hash
            source_row = next((item for item in reversed(rows) if item.get("delta_class") != "none" and item.get("profile_sha256", {}).get("new") == current_profile_hash), row)
            request_path = project_root.resolve() / "reviews/repin_rebind_request.json"
            request_fields = {"pin_epoch": current_expected["pin_epoch"], "profile_sha256": current_profile_hash,
                              "attestation_view_pin": current["attestation_view_pin"], "exemplar_view_pin": current["exemplar_view_pin"],
                              "delta_class": source_row["delta_class"], "repin_log_ref": f"references/policies/repin_log.jsonl#epoch-{source_row['epoch']}", "status": "pending"}
            existed = request_path.exists()
            if existed:
                try:
                    existing_request = json.loads(request_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise PolicyError(f"existing rebind request changed or is unreadable; refusing overwrite: {exc}") from exc
                comparable = {key: existing_request.get(key) for key in request_fields}
                if comparable != request_fields or not isinstance(existing_request.get("request_id"), str):
                    raise PolicyError("a different rebind request is already pending; Planner must apply or archive it before retry")
                request_reused = True
            else:
                request = {"request_id": str(uuid.uuid4()), **request_fields}
                _atomic_create_bytes(request_path, _json_bytes(request))
        return {"status": "READY", "delta_class": delta_class, "delta_report": report, "epoch": event_epoch,
                "applied": applied, "dry_run": dry_run, "snapshot_ref": snapshot_ref,
                "rebind_request": str(request_path) if request_path else None, "request_reused": request_reused,
                "read_back_verified": applied, "warnings": current["warnings"],
                "commit_proposal": "chore(accessibility): re-pin domain-native register views" if applied else None}
    finally:
        _release_repin_lock(lock_path, lock_token)


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
    parser.add_argument("--backfill-repin-commit", metavar="OBJECT_ID", help="backfill the commit field for an existing re-pin event; never recomputes pins")
    parser.add_argument("--repin-epoch", type=int, help="ledger event epoch used with --backfill-repin-commit")
    args = parser.parse_args(argv)
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
