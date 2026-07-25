#!/usr/bin/env python3
"""Fail closed unless the required JSON Schema runtime is operational."""

from __future__ import annotations

import json
from importlib.metadata import PackageNotFoundError, version


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
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
