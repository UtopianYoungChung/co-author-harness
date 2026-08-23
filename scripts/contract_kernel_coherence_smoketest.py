#!/usr/bin/env python3
"""Adversarial smoke tests for contract-kernel-check.py, plus the CORE-DECOUPLING proofs.

CORE-DECOUPLING (D1-D5) pins the project/tool independence boundary on the
consumer-compatibility interface: the shipped package template must not carry
one workspace's resolved identity, core qualification must not read a live
consumer workspace, and a consumer-supplied adapter must be integration input
with no authority in either direction.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CHECK = ROOT / "scripts" / "contract-kernel-check.py"
SPEC = importlib.util.spec_from_file_location("contract_kernel_check", CHECK)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def require_error(data: dict, needle: str) -> None:
    errors = MODULE.validate(ROOT, data)
    assert any(needle in error for error in errors), (needle, errors)


# --------------------------------------------------------------------------
# CORE-DECOUPLING support
# --------------------------------------------------------------------------

# The reusable consumer-compatibility interface: every artefact a consumer is
# told to copy or pin. This is the surface TOOL-0001 names. It is deliberately
# NOT the whole of references/: the reader-accessibility corpus roots are a
# separately governed provenance declaration with their own documented override
# seam (see scripts/corpus_root_portability_smoketest.py) and are audited there.
TIER1_SURFACE = (
    "references/contract_kernel.v1.json",
    "references/schemas/consumer_compatibility_profile.schema.json",
    "references/schemas/consumer_observation_receipt.schema.json",
    "references/schemas/consumer_integration_adapter.schema.json",
    "references/compatibility/shipment-v2/compatibility_profile.json",
    "references/compatibility/shipment-v2/contract_kernel_projection.json",
    "references/compatibility/shipment-v2/canonicalization.json",
    "references/compatibility/shipment-v2/diagnostic_map.json",
    "references/compatibility/shipment-v2/shared_fixture_corpus.json",
    "references/compatibility/shipment-v2/shipment_manifest.schema.json",
    "references/compatibility/shipment-v2/role_output_contract.json",
    "references/compatibility/shipment-v2/README.md",
)

# A drive-letter root not preceded by an identifier character, so "https://"
# and other URI schemes are not mistaken for "C:/".
_ABSOLUTE_DRIVE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")

# Live consumer identities and governed-plane locators. Generic synthetic
# strings (for example "reviews/phase_state.json") are permitted; these are not.
# Deliberately structural: this list names governed SHAPES and consumer TOOL
# names, never a consuming project's name. A reusable core must not carry one
# project's identity, not even in a denylist.
_FORBIDDEN_IDENTIFIERS = (
    "qe_workspace_guard",
    "ROOT_ARCHITECTURE_INDEX",
    "output_routing",
    "60_Workbench",
    "99_System",
    "10_Governance",
    "HARNESS_SHIPMENT_BOUNDARY",
    "WORKBENCH_ARTIFACT_ECONOMY",
)

# Sibling planes of the workspace root that a tool must never read during its
# own qualification.
_CONSUMER_PLANES = ("research", "knowledge", "governance", "outputs")

# Case-insensitive locator fragments that identify a governed consumer plane
# regardless of where the harness happens to be checked out.
_CONSUMER_MARKERS = (
    "60_workbench",
    "99_system",
    "10_governance",
    "graphify-out",
    "40_advisor",
    "65_deliverables",
    "30_streams",
)


def _workspace_root() -> Path | None:
    parents = ROOT.parents
    return parents[1] if len(parents) > 1 else None


def _adapter_validator():
    from jsonschema import Draft202012Validator

    schema = json.loads(
        (ROOT / "references" / "schemas" / "consumer_integration_adapter.schema.json")
        .read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _valid_adapter(sandbox: Path) -> dict:
    """A structurally valid adapter whose bindings name only synthetic sandbox files."""
    bound = sandbox / "consumer_policy.json"
    bound.write_text('{"synthetic": true}\n', encoding="utf-8", newline="")
    payload = bound.read_bytes()
    kernel = ROOT / "references" / "contract_kernel.v1.json"
    profile = json.loads(
        (ROOT / "references" / "compatibility" / "shipment-v2" / "compatibility_profile.json")
        .read_text(encoding="utf-8")
    )
    return {
        "schema_version": "1.0.0",
        "adapter_id": "synthetic-integration-adapter",
        "integration_project": {
            "work_id": "synthetic-integration-fixture",
            "governance": "synthetic-fixture-governance",
            "authorized_by": "synthetic-fixture-authority",
        },
        "core_identity": {
            "name": "co-author-harness",
            "version": profile["producer"]["version"],
            "contract_kernel_sha256": hashlib.sha256(kernel.read_bytes()).hexdigest(),
            "compatibility_kit_sha256": profile["compatibility_kit"]["sha256"],
            "output_contract_sha256": profile["output_contract"]["sha256"],
        },
        "consumer_identity": {
            "name": "synthetic-consumer",
            "governance": "synthetic-consumer-governance",
        },
        "bindings": [{
            "role": "policy",
            "path": bound.as_posix(),
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }],
        "authority": "integration-input-only",
        "grants": {
            "project_lifecycle": False, "approval": False, "promotion": False,
            "delivery": False, "release": False, "installation": False,
            "activation": False, "core_source_mutation": False,
            "consumer_source_mutation": False,
        },
    }


def _tier1_digest() -> dict[str, str]:
    return {
        rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        for rel in TIER1_SURFACE
    }


def check_d3_contract_language_is_schema_scoped() -> None:
    readme = (
        ROOT / "references" / "compatibility" / "shipment-v2" / "README.md"
    ).read_text(encoding="utf-8")
    overclaim = "A missing, malformed, stale, or authority-claiming adapter is refused"
    assert overclaim not in readme, (
        "D3: core documentation overclaims runtime refusal for a schema-only interface"
    )
    assert "Schema validation rejects malformed or authority-claiming adapters" in readme, (
        "D3: core documentation does not state the bounded schema guarantee"
    )
    integration_refusal = (
        "stale identities are detectable but must be refused by the integration project"
    )
    normalized_readme = " ".join(readme.lower().split())
    assert integration_refusal in normalized_readme, (
        "D3: core documentation does not assign stale-identity refusal to integration"
    )


# --------------------------------------------------------------------------
# D1 - the reusable interface carries no absolute path and no live identity
# --------------------------------------------------------------------------

def check_d1_no_workspace_paths_in_core() -> None:
    offences: list[str] = []
    for rel in TIER1_SURFACE:
        path = ROOT / rel
        assert path.is_file(), f"D1: Tier-1 surface member is missing: {rel}"
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            if _ABSOLUTE_DRIVE.search(line):
                offences.append(f"{rel}:{number}: absolute drive-rooted path")
            for token in _FORBIDDEN_IDENTIFIERS:
                if token in line:
                    offences.append(f"{rel}:{number}: live identifier {token!r}")
    assert not offences, "D1 failed:\n  " + "\n  ".join(offences)


def check_d1_template_is_unbound() -> None:
    profile = json.loads(
        (ROOT / "references" / "compatibility" / "shipment-v2" / "compatibility_profile.json")
        .read_text(encoding="utf-8")
    )
    assert profile["binding_state"] == "template", profile["binding_state"]
    assert profile["consumer"] is None, "D1: shipped template names a consumer"
    assert profile["external_snapshot"] == [], "D1: shipped template pins external files"

    from jsonschema import Draft202012Validator

    schema = json.loads(
        (ROOT / "references" / "schemas" / "consumer_compatibility_profile.schema.json")
        .read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(schema)
    assert list(validator.iter_errors(profile)) == [], "D1: shipped template is invalid"

    # The schema, not merely this instance, forbids a bound template.
    for mutation in (
        {"consumer": {"name": "x", "guard": {"version": "1", "sha256": "a" * 64},
                      "policy": {"version": "1", "sha256": "a" * 64},
                      "config": {"version": "1", "sha256": "a" * 64},
                      "tests": {"version": "1", "sha256": "a" * 64}}},
        {"external_snapshot": [{"path": "any/consumer/file", "bytes": 1, "sha256": "a" * 64}]},
    ):
        case = copy.deepcopy(profile)
        case.update(mutation)
        assert list(validator.iter_errors(case)), (
            "D1: template state accepted a consumer binding: " + ",".join(mutation)
        )

    # ... and a resolved profile still REQUIRES both, so the interface is not
    # weakened, only relocated to the consumer's own plane.
    resolved = copy.deepcopy(profile)
    resolved["binding_state"] = "resolved"
    resolved["producer"]["commit"] = "b" * 40
    resolved["producer"]["tree"] = "c" * 40
    resolved["scope_binding"] = {
        "work_id": "synthetic", "activation_baseline_sha256": "a" * 64,
        "canonical_role_registry_sha256": "a" * 64, "invocation_scope": "lab_iteration",
    }
    assert list(Draft202012Validator(schema).iter_errors(resolved)), (
        "D1: resolved profile accepted a null consumer / empty snapshot"
    )


# --------------------------------------------------------------------------
# D2 - core qualification does not read a live consumer workspace
# --------------------------------------------------------------------------

def check_d2_qualification_reads_no_consumer() -> None:
    opened: list[str] = []
    recording = {"on": False}

    def hook(event: str, args) -> None:
        if event == "open" and recording["on"]:
            target = args[0]
            if isinstance(target, (str, bytes, os.PathLike)):
                if isinstance(target, bytes):
                    target = target.decode("utf-8", "replace")
                opened.append(os.fspath(target))

    sys.addaudithook(hook)

    runtime_path = ROOT / "scripts" / "schema_runtime_check.py"
    spec = importlib.util.spec_from_file_location("schema_runtime_check_probe", runtime_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    recording["on"] = True
    try:
        with redirect_stdout(io.StringIO()) as captured:
            status = module.main()
    finally:
        recording["on"] = False

    assert status == 0, f"D2: core qualification did not pass: {captured.getvalue()}"
    assert opened, "D2: audit hook recorded nothing; the probe proved nothing"

    root_resolved = ROOT.resolve()
    workspace = _workspace_root()
    planes = []
    if workspace is not None:
        planes = [
            (workspace / name).resolve()
            for name in _CONSUMER_PLANES
            if (workspace / name).is_dir()
        ]

    offences: list[str] = []
    for raw in opened:
        try:
            resolved = Path(raw).resolve()
        except (OSError, ValueError):
            continue
        try:
            resolved.relative_to(root_resolved)
            continue  # inside the plugin root: the tool reading itself
        except ValueError:
            pass
        for plane in planes:
            try:
                resolved.relative_to(plane)
            except ValueError:
                continue
            offences.append(f"read consumer plane {plane.name}: {resolved}")
        lowered = resolved.as_posix().lower()
        for marker in _CONSUMER_MARKERS:
            if marker in lowered:
                offences.append(f"read governed-plane locator {marker!r}: {resolved}")
    assert not offences, "D2 failed:\n  " + "\n  ".join(sorted(set(offences)))


# --------------------------------------------------------------------------
# D3 - the schema boundary and identity checks have explicit, bounded semantics
# --------------------------------------------------------------------------

def check_d3_adapter_contract_is_bounded(sandbox: Path) -> None:
    validator = _adapter_validator()
    valid = _valid_adapter(sandbox)
    assert list(validator.iter_errors(valid)) == [], list(validator.iter_errors(valid))

    # MISSING: no adapter exists and no core surface consults one. Absence is
    # inert; this core does not claim to validate or refuse a nonexistent input.
    absent = sandbox / "no-such-adapter.json"
    assert not absent.exists()
    profile = json.loads(
        (ROOT / "references" / "compatibility" / "shipment-v2" / "compatibility_profile.json")
        .read_text(encoding="utf-8")
    )
    assert profile["consumer"] is None and profile["external_snapshot"] == [], (
        "D3: the core carries a consumer binding in the absence of an adapter"
    )

    # MALFORMED: not JSON, wrong type, missing required key, unknown key.
    broken = sandbox / "malformed-adapter.json"
    broken.write_text("{not json", encoding="utf-8", newline="")
    refused_malformed = False
    try:
        json.loads(broken.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        refused_malformed = True
    assert refused_malformed, "D3: unparseable adapter bytes were accepted"

    for label, mutate in (
        ("missing-required", lambda a: a.pop("core_identity")),
        ("wrong-type", lambda a: a.__setitem__("bindings", {})),
        ("empty-bindings", lambda a: a.__setitem__("bindings", [])),
        ("unknown-key", lambda a: a.__setitem__("apply_to", "any/consumer/path")),
        ("bad-schema-version", lambda a: a.__setitem__("schema_version", "2.0.0")),
    ):
        case = copy.deepcopy(valid)
        mutate(case)
        assert list(validator.iter_errors(case)), f"D3: malformed adapter accepted ({label})"

    # STALE: the adapter declares a core identity this core no longer has. The
    # generic schema intentionally accepts the shape; the separately authorized
    # integration project must compare and refuse stale identities before use.
    stale = copy.deepcopy(valid)
    stale["core_identity"]["contract_kernel_sha256"] = "0" * 64
    assert list(validator.iter_errors(stale)) == [], "stale case must be well-formed"
    live_kernel = hashlib.sha256(
        (ROOT / "references" / "contract_kernel.v1.json").read_bytes()
    ).hexdigest()
    assert stale["core_identity"]["contract_kernel_sha256"] != live_kernel, (
        "D3: staleness is undetectable"
    )
    assert valid["core_identity"]["contract_kernel_sha256"] == live_kernel, (
        "D3: a current adapter does not match the live core identity"
    )

    # UNTRUSTED: any adapter that claims authority is refused by the interface.
    for label, mutate in (
        ("authority-string", lambda a: a.__setitem__("authority", "apply")),
        ("grant-promotion", lambda a: a["grants"].__setitem__("promotion", True)),
        ("grant-release", lambda a: a["grants"].__setitem__("release", True)),
        ("grant-activation", lambda a: a["grants"].__setitem__("activation", True)),
        ("grant-lifecycle", lambda a: a["grants"].__setitem__("project_lifecycle", True)),
        ("grant-core-mutation", lambda a: a["grants"].__setitem__("core_source_mutation", True)),
        ("extra-grant", lambda a: a["grants"].__setitem__("anything_else", False)),
    ):
        case = copy.deepcopy(valid)
        mutate(case)
        assert list(validator.iter_errors(case)), f"D3: untrusted adapter accepted ({label})"


# --------------------------------------------------------------------------
# D4 - a valid adapter is integration input only and mutates nothing
# --------------------------------------------------------------------------

def check_d4_valid_adapter_grants_nothing(sandbox: Path) -> None:
    before = _tier1_digest()
    validator = _adapter_validator()
    adapter = _valid_adapter(sandbox)
    assert list(validator.iter_errors(adapter)) == []

    assert adapter["authority"] == "integration-input-only"
    assert set(adapter["grants"]) == {
        "project_lifecycle", "approval", "promotion", "delivery", "release",
        "installation", "activation", "core_source_mutation", "consumer_source_mutation",
    }
    assert all(value is False for value in adapter["grants"].values()), adapter["grants"]

    # The adapter names its own integration project; it never renames the core
    # or the consumer, and both identities survive it unchanged.
    assert adapter["integration_project"]["work_id"] != adapter["core_identity"]["name"]
    assert adapter["consumer_identity"]["name"] != adapter["core_identity"]["name"]

    after = _tier1_digest()
    assert before == after, (
        "D4: validating an adapter changed a core artefact: "
        + ", ".join(sorted(k for k in before if before[k] != after[k]))
    )
    profile = json.loads(
        (ROOT / "references" / "compatibility" / "shipment-v2" / "compatibility_profile.json")
        .read_text(encoding="utf-8")
    )
    assert profile["binding_state"] == "template" and profile["consumer"] is None, (
        "D4: a valid adapter promoted the shipped template to a bound state"
    )


# --------------------------------------------------------------------------
# D5 - every fixture is a synthetic temporary tree outside live project roots
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# TH N1-N3 — hermetic projection/kernel/file drift detection
# --------------------------------------------------------------------------

_N_PROJECTED_ID = "capability-registry"


def _load_kernel_and_projection() -> tuple[dict, dict]:
    kernel = json.loads((ROOT / "references" / "contract_kernel.v1.json").read_text(encoding="utf-8"))
    projection = json.loads(
        (ROOT / "references" / "compatibility" / "shipment-v2" / "contract_kernel_projection.json").read_text(
            encoding="utf-8"
        )
    )
    return kernel, projection


def _projection_kernel_component_errors(kernel: dict, projection: dict, kernel_file_sha256: str) -> list[str]:
    errors: list[str] = []
    if projection["kernel"]["sha256"] != kernel_file_sha256:
        errors.append("compatibility-kit kernel projection hash drift")
    kernel_components = {row["id"]: row["sha256"] for row in kernel["components"]}
    for row in projection["components"]:
        if kernel_components.get(row["id"]) != row["sha256"]:
            errors.append(f"compatibility-kit component drift: {row['id']}")
    return errors


def check_n1_projected_component_file_drift(sandbox: Path) -> None:
    """Projected component file bytes differ from the projection row hash."""
    kernel, projection = _load_kernel_and_projection()
    proj_row = next(row for row in projection["components"] if row["id"] == _N_PROJECTED_ID)
    krow = next(row for row in kernel["components"] if row["id"] == _N_PROJECTED_ID)
    source = ROOT / krow["path"]
    drifted = sandbox / "projected_component_file_drift.bin"
    drifted.write_bytes(source.read_bytes() + b"\n#n1-file-drift\n")
    file_sha = hashlib.sha256(drifted.read_bytes()).hexdigest()
    assert file_sha != proj_row["sha256"]
    mini = copy.deepcopy(kernel)
    mini_row = next(row for row in mini["components"] if row["id"] == _N_PROJECTED_ID)
    mini_row["path"] = drifted.name
    mini["components"] = [mini_row]
    (sandbox / "version.json").write_text(
        (ROOT / "version.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (sandbox / "README.md").write_text(
        (ROOT / "README.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (sandbox / "LICENSE").write_text(
        (ROOT / "LICENSE").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    errors = MODULE.validate(sandbox, mini)
    assert any("content hash drift" in error for error in errors), errors


def check_n2_projection_row_only_drift() -> None:
    """Projection component row hash differs; kernel row and file unchanged."""
    kernel, projection = _load_kernel_and_projection()
    kernel_file_sha = hashlib.sha256((ROOT / "references" / "contract_kernel.v1.json").read_bytes()).hexdigest()
    drifted = copy.deepcopy(projection)
    row = next(item for item in drifted["components"] if item["id"] == _N_PROJECTED_ID)
    original = row["sha256"]
    row["sha256"] = "0" * 64
    errors = _projection_kernel_component_errors(kernel, drifted, kernel_file_sha)
    assert f"compatibility-kit component drift: {_N_PROJECTED_ID}" in errors, errors
    clean = _projection_kernel_component_errors(kernel, projection, kernel_file_sha)
    # Live kernel.sha256 pin may still be stale; row-only case must not depend on it.
    assert f"compatibility-kit component drift: {_N_PROJECTED_ID}" not in clean
    assert original != "0" * 64


def check_n3_kernel_row_drift_without_file() -> None:
    """Kernel component row hash differs; component file bytes unchanged."""
    kernel, _projection = _load_kernel_and_projection()
    case = copy.deepcopy(kernel)
    row = next(item for item in case["components"] if item["id"] == _N_PROJECTED_ID)
    live_path = ROOT / row["path"]
    live_sha = hashlib.sha256(live_path.read_bytes()).hexdigest()
    assert row["sha256"] == live_sha
    row["sha256"] = "0" * 64
    require_error(case, f"{_N_PROJECTED_ID}: content hash drift")
    assert hashlib.sha256(live_path.read_bytes()).hexdigest() == live_sha


def check_d5_fixtures_are_synthetic(sandbox: Path) -> None:
    resolved = sandbox.resolve()
    assert resolved.is_dir()

    temp_root = Path(tempfile.gettempdir()).resolve()
    assert str(resolved).startswith(str(temp_root)), (
        f"D5: fixture root {resolved} is not under the system temp root {temp_root}"
    )

    try:
        resolved.relative_to(ROOT.resolve())
        raise AssertionError(f"D5: fixture root {resolved} is inside the package root")
    except ValueError:
        pass

    workspace = _workspace_root()
    if workspace is not None:
        for name in _CONSUMER_PLANES:
            plane = workspace / name
            if not plane.is_dir():
                continue
            try:
                resolved.relative_to(plane.resolve())
                raise AssertionError(f"D5: fixture root {resolved} is inside {plane}")
            except ValueError:
                pass

    lowered = resolved.as_posix().lower()
    for marker in _CONSUMER_MARKERS:
        assert marker not in lowered, f"D5: fixture root names a governed plane: {marker}"


def main() -> int:
    data = json.loads(
        (ROOT / "references" / "contract_kernel.v1.json").read_text(encoding="utf-8")
    )
    assert MODULE.validate(ROOT, data) == []

    case = copy.deepcopy(data)
    case["repository_policy"]["single_branch"] = "feature"
    require_error(case, "single_branch must be main")

    case = copy.deepcopy(data)
    case["lifecycle"]["milestones"] = ["M1", "M2", "M3", "M4"]
    require_error(case, "milestones must be M1 through M5")

    case = copy.deepcopy(data)
    case["components"][0]["sha256"] = "0" * 64
    require_error(case, "content hash drift")

    case = copy.deepcopy(data)
    case["components"][1]["id"] = case["components"][0]["id"]
    require_error(case, "duplicate component id")

    for required_id in (
        "assignment-process-gate",
        "assignment-dispatch-preflight",
        "assignment-receipt-transaction",
        "assignment-writer-commit",
        "assignment-receipt-invalidate",
        "assignment-receipt-recover",
        "assignment-receipt-schema",
        "assignment-receipt-template",
    ):
        case = copy.deepcopy(data)
        case["components"] = [
            row for row in case["components"] if row["id"] != required_id
        ]
        require_error(case, f"required components missing: {required_id}")

    case = copy.deepcopy(data)
    case["components"][0]["path"] = "../phase_state_schema.md"
    require_error(case, "missing or unsafe")

    case = copy.deepcopy(data)
    case.pop("kernel_id")
    require_error(case, "kernel_id is required")

    case = copy.deepcopy(data)
    case["plugin_identity_source"] = "../plugin.json"
    require_error(case, "plugin_identity_source is missing or unsafe")

    # The consumer-interface schemas are kernel-bound, so the decoupled shape is
    # versioned rather than incidental.
    bound = {row["id"]: row["path"] for row in data["components"]}
    assert bound.get("consumer-compatibility-profile-schema") == (
        "references/schemas/consumer_compatibility_profile.schema.json"
    )
    assert bound.get("consumer-integration-adapter-schema") == (
        "references/schemas/consumer_integration_adapter.schema.json"
    )

    sandbox = Path(tempfile.mkdtemp(prefix="coauthor-core-decoupling-"))
    try:
        check_d5_fixtures_are_synthetic(sandbox)
        check_n1_projected_component_file_drift(sandbox)
        check_n2_projection_row_only_drift()
        check_n3_kernel_row_drift_without_file()
        check_d1_no_workspace_paths_in_core()
        check_d1_template_is_unbound()
        check_d3_contract_language_is_schema_scoped()
        check_d3_adapter_contract_is_bounded(sandbox)
        check_d4_valid_adapter_grants_nothing(sandbox)
        check_d2_qualification_reads_no_consumer()
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)

    print("contract_kernel_coherence_smoketest: PASS (CORE-DECOUPLING D1-D5 included)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
