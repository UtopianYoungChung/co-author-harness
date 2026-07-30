#!/usr/bin/env python3
"""Fail closed unless the required JSON Schema runtime is operational."""

from __future__ import annotations

import json
import hashlib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REQUIRED_SCHEMAS = (
    "references/schemas/role_output_contract.schema.json",
    "references/schemas/shipment_manifest.schema.json",
    "references/schemas/consumer_compatibility_profile.schema.json",
    "references/schemas/consumer_observation_receipt.schema.json",
    "references/schemas/application_receipt.schema.json",
    "references/schemas/shipment_refusal_receipt.schema.json",
    "references/schemas/shipment_recovery_receipt.schema.json",
)


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unavailable"


def main() -> int:
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry

        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
            "required": ["value"],
            "properties": {"value": {"const": "qualified"}},
        }
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, registry=Registry())
        if list(validator.iter_errors({"value": "qualified"})):
            raise RuntimeError("Draft 2020-12 validator rejected its valid control")
        if not list(validator.iter_errors({"value": "other"})):
            raise RuntimeError("Draft 2020-12 validator accepted its invalid control")

        for relative in REQUIRED_SCHEMAS:
            candidate = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(candidate)

        role_contract = json.loads(
            (ROOT / "references/role_output_contract.json").read_text(encoding="utf-8")
        )
        role_schema = json.loads(
            (ROOT / "references/schemas/role_output_contract.schema.json").read_text(
                encoding="utf-8"
            )
        )
        role_errors = list(Draft202012Validator(role_schema).iter_errors(role_contract))
        if role_errors:
            raise RuntimeError(f"role/output contract 3.0.0 is invalid: {role_errors[0].message}")

        exact_copies = (
            ("references/schemas/shipment_manifest.schema.json", "references/compatibility/shipment-v2/shipment_manifest.schema.json"),
            ("references/role_output_contract.json", "references/compatibility/shipment-v2/role_output_contract.json"),
        )
        for authority, vendored in exact_copies:
            if (ROOT / authority).read_bytes() != (ROOT / vendored).read_bytes():
                raise RuntimeError(f"compatibility-kit byte drift: {vendored}")

        kit_root = ROOT / "references/compatibility/shipment-v2"
        profile = json.loads((kit_root / "compatibility_profile.json").read_text(encoding="utf-8"))
        profile_schema = json.loads(
            (ROOT / "references/schemas/consumer_compatibility_profile.schema.json").read_text(
                encoding="utf-8"
            )
        )
        profile_errors = list(Draft202012Validator(profile_schema).iter_errors(profile))
        if profile_errors:
            raise RuntimeError(f"compatibility profile is invalid: {profile_errors[0].message}")

        kit_names = (
            "shipment_manifest.schema.json",
            "role_output_contract.json",
            "contract_kernel_projection.json",
            "canonicalization.json",
            "diagnostic_map.json",
            "shared_fixture_corpus.json",
        )
        kit_rows = [
            {
                "path": name,
                "sha256": hashlib.sha256((kit_root / name).read_bytes()).hexdigest(),
            }
            for name in kit_names
        ]
        kit_bytes = (
            json.dumps(
                {"algorithm": "sha256-canonical-kit-file-map-v1", "files": kit_rows},
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        if profile["compatibility_kit"]["sha256"] != hashlib.sha256(kit_bytes).hexdigest():
            raise RuntimeError("compatibility-kit aggregate hash drift")

        projection = json.loads(
            (kit_root / "contract_kernel_projection.json").read_text(encoding="utf-8")
        )
        kernel_path = ROOT / "references/contract_kernel.v1.json"
        kernel = json.loads(kernel_path.read_text(encoding="utf-8"))
        kernel_sha256 = hashlib.sha256(kernel_path.read_bytes()).hexdigest()
        if projection["kernel"]["sha256"] != kernel_sha256:
            raise RuntimeError("compatibility-kit kernel projection hash drift")
        kernel_components = {row["id"]: row["sha256"] for row in kernel["components"]}
        for row in projection["components"]:
            if kernel_components.get(row["id"]) != row["sha256"]:
                raise RuntimeError(f"compatibility-kit component drift: {row['id']}")

        corpus = json.loads((kit_root / "shared_fixture_corpus.json").read_text(encoding="utf-8"))
        if profile["fixture_corpus"]["fixture_ids"] != [row["id"] for row in corpus["cases"]]:
            raise RuntimeError("compatibility profile fixture IDs differ from the shared corpus")
        if profile["fixture_corpus"]["sha256"] != hashlib.sha256(
            (kit_root / "shared_fixture_corpus.json").read_bytes()
        ).hexdigest():
            raise RuntimeError("compatibility profile fixture-corpus hash drift")
        if profile["diagnostic_map_sha256"] != hashlib.sha256(
            (kit_root / "diagnostic_map.json").read_bytes()
        ).hexdigest():
            raise RuntimeError("compatibility profile diagnostic-map hash drift")
    except Exception as exc:
        print(json.dumps({
            "status": "blocked",
            "reason_code": "SCHEMA-RUNTIME-UNAVAILABLE",
            "detail": str(exc),
        }))
        return 2
    print(json.dumps({
        "status": "passed",
        "jsonschema": _package_version("jsonschema"),
        "referencing": _package_version("referencing"),
        "draft": "2020-12",
        "required_schemas": len(REQUIRED_SCHEMAS),
        "compatibility_copies": 2,
        "compatibility_fixture_ids": len(profile["fixture_corpus"]["fixture_ids"]),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
