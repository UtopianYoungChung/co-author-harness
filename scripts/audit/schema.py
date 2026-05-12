"""Canonical finding schema for the v0.15.0 audit suite.

A Finding is the atomic output of any deterministic auditor. The schema is
stable so downstream consumers (skills, agents, release-gate) can rely on
field names without reading auditor implementations.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

SEVERITY_INVIOLABLE = "inviolable"
SEVERITY_DEFAULT = "default"

VALID_SEVERITY = {SEVERITY_INVIOLABLE, SEVERITY_DEFAULT}
VALID_CATEGORY = {"style", "register", "citation", "structure", "passive", "economy"}


@dataclass
class Finding:
    check_id: str
    category: str
    severity: str
    locator: str
    evidence: str
    rule_ref: str
    tentative: bool = False

    def __post_init__(self) -> None:
        if self.severity not in VALID_SEVERITY:
            raise ValueError(f"invalid severity {self.severity!r}")
        if self.category not in VALID_CATEGORY:
            raise ValueError(f"invalid category {self.category!r}")


@dataclass
class FindingsReport:
    schema_version: str = "0.15.0"
    target: str = ""
    findings: List[Finding] = field(default_factory=list)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def extend(self, findings: List[Finding]) -> None:
        self.findings.extend(findings)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "target": self.target,
            "findings": [asdict(f) for f in self.findings],
            "counts": self.counts(),
        }

    def counts(self) -> dict:
        c: dict = {"total": len(self.findings), "by_severity": {}, "by_category": {}}
        for f in self.findings:
            c["by_severity"][f.severity] = c["by_severity"].get(f.severity, 0) + 1
            c["by_category"][f.category] = c["by_category"].get(f.category, 0) + 1
        return c

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


def locator_for(path: Path, line: int) -> str:
    return f"{path.as_posix()}:{line}"
