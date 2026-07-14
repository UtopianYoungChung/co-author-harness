#!/usr/bin/env python3
"""Load, validate, and resolve the package reader-accessibility policy.

Production code is standard-library only. Project files may narrow register
scope and override lexicons only with the polarity declared by the package
profile. Every contributing file is returned with its SHA-256 binding.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
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


class _SnapshotSet:
    def __init__(self, hook: Callable[[str, str, Path | None], None] | None = None):
        self._hook = hook
        self._items: dict[Path, _Snapshot] = {}

    def capture(self, path: Path, role: str) -> _Snapshot:
        resolved = path.resolve()
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
        except OSError as exc:
            raise PolicyError(f"domain-native input unreadable: {role}: {resolved}: {exc}") from exc

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


def normalize_tier(value: str) -> str:
    """Return the stable grounding class, ignoring free-text annotations."""
    token = re.split(r"\s+(?:—|–|-)\s+", value.strip().lower(), maxsplit=1)[0].strip()
    return {"full-text-pass": "full-read", "section-read-verified": "section-read"}.get(token, token)


def grounding_admitted(value: str) -> bool:
    return normalize_tier(value) not in {"stub", "unresolved"}


def _source_metadata(text: str, fallback: str) -> tuple[str, str | None]:
    match = re.search(r"(?mi)^\s*grounding_status\s*:\s*['\"]?([^\r\n'\"]+)", text)
    source = re.search(r"(?mi)^\s*source_loc\s*:\s*['\"]?([^\r\n'\"]+)", text)
    return (match.group(1).strip() if match else fallback, source.group(1).strip() if source else None)


def _utf8_key(value: str) -> bytes:
    return value.encode("utf-8")


def resolve_domain_native_register(
    profile: dict[str, Any], *, wiki_root: Path = DEFAULT_WIKI_ROOT,
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT, harness_root: Path = ROOT,
    _snapshot_hook: Callable[[str, str, Path | None], None] | None = None,
) -> dict[str, Any]:
    """Resolve the two semantic register views with explicit injected roots."""
    model = profile.get("domain_native_register")
    if not isinstance(model, dict):
        raise PolicyError("profile.domain_native_register is missing")
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
    for member in model["exemplar_members"]:
        key = member["source_key"]; source_rel = f"wiki/sources/{key}.md"; source_path = _contained(wiki_root, source_rel)
        source_snapshot = snapshots.capture(source_path, "exemplar_source_page")
        grounding, source_pdf = _source_metadata(source_snapshot.text(), member["grounding"])
        provenance.append({"role":"exemplar_source_page","path":str(source_path),"sha256":source_snapshot.sha256})
        if not grounding_admitted(grounding): continue
        pdf_hash = "-"
        pdf_rel = source_pdf or member.get("pdf")
        if pdf_rel:
            pdf_path = _contained(wiki_root, pdf_rel)
            if pdf_path.is_file():
                pdf_snapshot = snapshots.capture(pdf_path, "surface_warrant_pdf")
                pdf_hash = pdf_snapshot.sha256; provenance.append({"role":"surface_warrant_pdf","path":str(pdf_path),"sha256":pdf_hash})
                if wiki_root.resolve() == DEFAULT_WIKI_ROOT.resolve() and member.get("pdf_sha256") and pdf_hash != member["pdf_sha256"]:
                    raise PolicyError(f"expected exemplar PDF hash mismatch: {key}")
        exemplar_lines.append(f"{key}\t{normalize_tier(grounding)}\t{pdf_hash}")
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
    snapshots.verify_all()
    return {"register_class":"domain-native","attestation_view_pin":attestation_pin,"exemplar_view_pin":exemplar_pin,"graph_sha256_provenance":graph_hash,"graph_mtime_utc_provenance":datetime.fromtimestamp(graph_snapshot.stamp[3] / 1_000_000_000, tz=timezone.utc).isoformat().replace("+00:00", "Z"),"seed_resolution_map":resolution,"seed_resolution_ties":ties,"unresolved_seed_ids":unresolved,"primary_communities":primary,"attestation_member_ids":sorted(membership,key=_utf8_key),"exemplar_hash_lines":sorted(exemplar_lines,key=_utf8_key),"warnings":warnings,"provenance":provenance}


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


def validate_profile(profile: dict[str, Any]) -> None:
    validate_schema_file(profile, PROFILE_SCHEMA)
    required = {"schema_version", "profile_version", "decision_status", "decision_record", "normative_authority", "package_contributors", "policy_telos", "domain_native_register", "phase_values", "passage_roles", "sub_checks", "aggregate", "adjacent_advisory_checks", "thresholds", "transitions", "runtime_modes", "register_scope", "lexicons", "domain_token_exclusions", "override_contract", "remediation_order", "recurrence"}
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
    if profile["schema_version"] != "1.0.0" or profile["profile_version"] != "1.0.0":
        raise PolicyError("unsupported profile version")
    if profile["decision_record"] != "ADR-ACCESS-01" or profile["normative_authority"] != "references/READER_ACCESSIBILITY.md":
        raise PolicyError("decision record or normative authority is invalid")
    _strings(profile["package_contributors"], "package_contributors")
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
    cadence = _object(thresholds["cadence"], "thresholds.cadence", {"unit", "hard_ceiling_words", "bands", "turn_point_candidates", "candidate_semantics", "functional_confirmation_required", "functional_classes", "internal_sentence_break_signals", "above_ceiling", "persistence"})
    if cadence.get("hard_ceiling_words") != 300 or not cadence.get("functional_confirmation_required"):
        raise PolicyError("provisional cadence decision is malformed")
    if cadence["candidate_semantics"] != "nomination_only":
        raise PolicyError("thresholds.cadence.candidate_semantics must be nomination_only")
    for key in ("turn_point_candidates", "functional_classes", "internal_sentence_break_signals"): _strings(cadence[key], f"thresholds.cadence.{key}")
    bands = cadence["bands"]
    if not isinstance(bands, list) or len(bands) != 3:
        raise PolicyError("thresholds.cadence.bands must contain three bands")
    expected_min = 0
    for index, band_value in enumerate(bands):
        band = _object(band_value, f"thresholds.cadence.bands[{index}]", {"min_words", "max_words", "required_functional_turn_points", "deficit_severity"})
        for key in ("min_words", "max_words", "required_functional_turn_points"):
            _number(band[key], f"thresholds.cadence.bands[{index}].{key}", integer=True)
        if band["min_words"] != expected_min or band["max_words"] < band["min_words"]:
            raise PolicyError("thresholds.cadence.bands must be ordered and contiguous")
        if band["deficit_severity"] not in {"CLEAN", "MINOR", "MAJOR"}:
            raise PolicyError("thresholds.cadence band deficit severity is invalid")
        expected_min = band["max_words"] + 1
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
    if profile.get("decision_status") != "provisional":
        raise PolicyError("ADR-ACCESS-01 has no proven acceptance; status must remain provisional")
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


def load_profile(path: Path = DEFAULT_PROFILE) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"profile unreadable: {exc}") from exc
    if not isinstance(data, dict):
        raise PolicyError("profile root must be an object")
    try:
        validate_profile(data)
    except PolicyError:
        raise
    except (TypeError, KeyError, AttributeError, IndexError) as exc:
        raise PolicyError(f"profile nested shape is invalid: {exc}") from exc
    return data


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
                   wiki_root: Path = DEFAULT_WIKI_ROOT, workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
                   harness_root: Path = ROOT) -> dict[str, Any]:
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
    return {"profile_path": resolved["profile_path"], "profile_sha256": resolved["profile_sha256"], "resolved_path": relative, "resolved_sha256": _hash(path), "source_bindings": copy.deepcopy(resolved["source_bindings"]), "project_identity": resolved.get("project_identity"), "attestation_view_pin": resolved["attestation_view_pin"], "exemplar_view_pin": resolved["exemplar_view_pin"], "graph_sha256_provenance": resolved["graph_sha256_provenance"], "register_provenance": copy.deepcopy(resolved["register_provenance"]), "transitions": {key: {"state": "active", "observed_count": 0, "last_event_sequence": None, "events": []} for key in ("G", "H", "VE")}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--wiki-root", type=Path, default=DEFAULT_WIKI_ROOT)
    parser.add_argument("--workspace-root", type=Path, default=DEFAULT_WORKSPACE_ROOT)
    parser.add_argument("--harness-root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--render-view", action="store_true", help="render the generated human-readable numeric policy view")
    args = parser.parse_args(argv)
    try:
        result = resolve_policy(args.project_root, profile_path=args.profile, wiki_root=args.wiki_root, workspace_root=args.workspace_root, harness_root=args.harness_root)
    except PolicyError as exc:
        print(json.dumps({"status": "MISCONFIGURED", "code": "RA-POLICY", "message": str(exc)}))
        return 4
    payload = render_policy_view(result["resolved_profile"]) if args.render_view else json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8", newline="\n")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
