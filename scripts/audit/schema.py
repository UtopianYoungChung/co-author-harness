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
VALID_CATEGORY = {"style", "register", "grounding", "citation", "structure", "passive", "economy"}


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


# ---------------------------------------------------------------------------
# READ-SIDE VALIDATION
#
# `FindingsReport` above is the WRITE side: it produces the canonical payload.
# Nothing owned the READ side, so `full_run_contract_check.py` was checking
# `reviews/findings.json` by asking whether the file existed -- which an empty
# file satisfies. The fix does not belong in the terminal gate: audit-report
# semantics are this module's business, and a second module deciding what a
# valid report is would be exactly the duplicate-authority problem the terminal
# gate exists to stop repeating. So the check lives here, next to the writer it
# mirrors, and the gate composes it.
# ---------------------------------------------------------------------------

SUPPORTED_SCHEMA_VERSIONS = frozenset({"0.15.0"})

_FINDING_FIELDS = {"check_id", "category", "severity", "locator", "evidence",
                   "rule_ref", "tentative"}
_FINDING_REQUIRED = _FINDING_FIELDS - {"tentative"}


def _recount(findings: List[dict]) -> dict:
    c: dict = {"total": len(findings), "by_severity": {}, "by_category": {}}
    for f in findings:
        sev, cat = f.get("severity"), f.get("category")
        c["by_severity"][sev] = c["by_severity"].get(sev, 0) + 1
        c["by_category"][cat] = c["by_category"].get(cat, 0) + 1
    return c


def validate_report_payload(payload: object, *, expected_target: Optional[str] = None
                            ) -> List[tuple]:
    """Validate a parsed findings report. Returns [(code, path, message), ...].

    Empty list == valid. Codes are stable and are the contract for callers; the
    messages are not. `expected_target` binds the report to the deliverable the
    caller expects, so a real report about a DIFFERENT manuscript cannot stand in
    for one about this one -- a report is evidence about a specific artefact, and
    detached from that artefact it is just a well-formed file.

    Counts are RECOMPUTED and compared, not trusted: `counts` is derived data,
    and derived data that disagrees with its source means one of them is a lie.
    """
    out: List[tuple] = []
    if not isinstance(payload, dict):
        return [("AUDIT-REPORT-NOT-OBJECT", "$",
                 f"findings report must be a JSON object, got {type(payload).__name__}")]

    version = payload.get("schema_version")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        out.append(("AUDIT-REPORT-SCHEMA-VERSION", "schema_version",
                    f"must be one of {sorted(SUPPORTED_SCHEMA_VERSIONS)}, got {version!r}"))

    target = payload.get("target")
    if not isinstance(target, str) or not target.strip():
        out.append(("AUDIT-REPORT-TARGET-EMPTY", "target",
                    f"must be a non-empty string, got {target!r}"))
    elif expected_target is not None and target != expected_target:
        out.append(("AUDIT-REPORT-TARGET-MISMATCH", "target",
                    f"report targets {target!r}, but this project's deliverable is "
                    f"{expected_target!r}: a report about another artefact is not "
                    "evidence about this one"))

    findings = payload.get("findings")
    if not isinstance(findings, list):
        out.append(("AUDIT-REPORT-FINDINGS-NOT-LIST", "findings",
                    f"must be a list, got {type(findings).__name__}"))
        return out

    for i, row in enumerate(findings):
        where = f"findings[{i}]"
        if not isinstance(row, dict):
            out.append(("AUDIT-FINDING-NOT-OBJECT", where,
                        f"must be an object, got {type(row).__name__}"))
            continue
        missing = sorted(_FINDING_REQUIRED - set(row))
        if missing:
            out.append(("AUDIT-FINDING-FIELDS", where,
                        f"missing required field(s) {missing}"))
        unknown = sorted(set(row) - _FINDING_FIELDS)
        if unknown:
            out.append(("AUDIT-FINDING-FIELDS", where,
                        f"unknown field(s) {unknown}"))
        if "severity" in row and row["severity"] not in VALID_SEVERITY:
            out.append(("AUDIT-FINDING-SEVERITY", f"{where}.severity",
                        f"must be one of {sorted(VALID_SEVERITY)}, got {row['severity']!r}"))
        if "category" in row and row["category"] not in VALID_CATEGORY:
            out.append(("AUDIT-FINDING-CATEGORY", f"{where}.category",
                        f"must be one of {sorted(VALID_CATEGORY)}, got {row['category']!r}"))
        if "tentative" in row and not isinstance(row["tentative"], bool):
            out.append(("AUDIT-FINDING-FIELDS", f"{where}.tentative",
                        f"must be a boolean, got {type(row['tentative']).__name__}"))

    recorded = payload.get("counts")
    if not isinstance(recorded, dict):
        out.append(("AUDIT-REPORT-COUNTS-MISSING", "counts",
                    f"must be an object, got {type(recorded).__name__}"))
    else:
        expected = _recount([f for f in findings if isinstance(f, dict)])
        if recorded != expected:
            out.append(("AUDIT-REPORT-COUNTS-MISMATCH", "counts",
                        f"recorded {recorded!r} != recomputed {expected!r}"))
    return out
