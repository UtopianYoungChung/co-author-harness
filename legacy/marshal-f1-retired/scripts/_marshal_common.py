"""Shared helpers for the Tier Marshal scripts.

The Tier Marshal (see `references/TIER_MARSHAL_CONTRACT.md` §8.3 and
`research_notes/tier_marshal_design_v1.md`) is an enforcement agent
that brackets the Planner's Phase 0 (preflight) and post-Phase-5.5
(postflight). These scripts implement the two deterministic predicate
sets. The helpers here are stdlib-only by design — the Marshal must be
runnable in any environment that can run the package's other release
gates.

Module conventions.

- Every public function takes a ``Path`` to the project root (not the
  plugin root) and returns data structures the caller can feed to the
  check table. Callers never read files directly; this module owns the
  parsing.
- Frontmatter parsing is deliberately minimal: key/value pairs and
  bracketed lists. PyYAML is not imported.
- ``CheckResult`` is the single surface by which checks communicate
  back to the emission layer. Severity is one of ``"pass"``, ``"warn"``,
  ``"block"``, matching the three-valued verdict grammar.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


# --- Schema and verdict constants --------------------------------------------------

MARSHAL_SCHEMA_VERSION = 1
LEGAL_TIERS = ("T0", "T1", "T2", "T3", "T3R", "T4")
LEGAL_OVERRIDE_REASONS = (
    "DIGEST-UNAVAILABLE",
    "CLASSIFICATION-PENDING",
    "USER-TIME-CRITICAL",
    "EXPERIMENTAL-SKIP",
)
OVERRIDE_TAG_RE = re.compile(r"\[MARSHAL-OVERRIDE-([A-Z][A-Z0-9\-]*)\]")


@dataclass
class CheckResult:
    """One check outcome.

    severity is ``pass``, ``warn``, or ``block``. ``na`` is reserved
    for checks that do not apply to the requested tier; ``na`` never
    influences the overall verdict.
    """

    check_id: str
    severity: str  # "pass" | "warn" | "block" | "na"
    message: str
    remediation: str = ""

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "severity": self.severity,
            "message": self.message,
            "remediation": self.remediation,
        }


@dataclass
class MarshalReport:
    """Aggregated verdict emitted by each script."""

    kind: str  # "preflight" | "postflight"
    round_id: int
    tier: str
    date: str
    plugin_version: str
    first_run: bool = False
    tier_entered_via: str = ""
    overrides_read: list[str] = field(default_factory=list)
    overrides_applied: list[str] = field(default_factory=list)
    checks: list[CheckResult] = field(default_factory=list)

    def verdict(self) -> str:
        if any(c.severity == "block" for c in self.checks):
            return "BLOCK"
        if any(c.severity == "warn" for c in self.checks):
            return "WARN"
        return "PASS"

    def exit_code(self) -> int:
        return {"PASS": 0, "WARN": 1, "BLOCK": 2}[self.verdict()]

    def to_dict(self) -> dict:
        return {
            "marshal_schema_version": MARSHAL_SCHEMA_VERSION,
            "kind": self.kind,
            "round": self.round_id,
            "tier": self.tier,
            "date": self.date,
            "plugin_version": self.plugin_version,
            "first_run": self.first_run,
            "tier_entered_via": self.tier_entered_via,
            "overrides_read": list(self.overrides_read),
            "overrides_applied": list(self.overrides_applied),
            "verdict": self.verdict(),
            "checks": [c.to_dict() for c in self.checks],
        }


# --- Frontmatter parsing -----------------------------------------------------------

def read_frontmatter(path: Path) -> tuple[dict[str, object], str]:
    """Parse a minimal YAML-style frontmatter block at the top of a markdown file.

    Returns a tuple ``(frontmatter_dict, remainder_text)``. If no
    frontmatter block is present, returns ``({}, full_text)``. Missing
    file raises ``FileNotFoundError`` — callers are expected to check
    existence first.
    """
    if not path.is_file():
        raise FileNotFoundError(str(path))
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    # Find the closing '---' line.
    lines = text.splitlines(keepends=False)
    close_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            close_idx = i
            break
    if close_idx is None:
        return {}, text
    fm_lines = lines[1:close_idx]
    body = "\n".join(lines[close_idx + 1 :])
    fm: dict[str, object] = {}
    for raw in fm_lines:
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        key = key.strip()
        value = value.strip()
        fm[key] = _parse_fm_value(value)
    return fm, body


def _parse_fm_value(value: str) -> object:
    """Parse a single YAML-lite value (string, int, bool, bracketed list)."""
    if value == "":
        return ""
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        items = [item.strip().strip("'\"") for item in inner.split(",")]
        return [item for item in items if item]
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value.strip("'\"")


# --- Plugin and digest --------------------------------------------------------------

def read_plugin_version(plugin_root: Path) -> str:
    manifest = plugin_root / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        return ""
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    version = data.get("version")
    return version if isinstance(version, str) else ""


def find_rule_digest(project_root: Path, plugin_version: str) -> Path | None:
    """Return the path to ``reviews/_rule_digest_<plugin-version>.json`` if present.

    The digest file may be versioned under either ``_rule_digest_<v>.json`` or
    ``_rule_digest.json``; the Marshal treats only the version-qualified
    name as the contract-compliant one.
    """
    reviews = project_root / "reviews"
    if not reviews.is_dir():
        return None
    expected = reviews / f"_rule_digest_{plugin_version}.json"
    return expected if expected.is_file() else None


# --- Artefact discovery -------------------------------------------------------------

TIER_SCOPED_ARTEFACT_PATTERNS: dict[str, tuple[str, ...]] = {
    "T1": (r"patch_report_.*\.md$",),
    "T2": (r"local_findings_.*\.md$",),
    "T3": (r"consolidated_findings_report_.*\.md$",),
    "T3R": (r"letter_findings_.*\.md$", r"response_letter_review_.*\.md$"),
    "T4": (r"consolidated_findings_report_.*\.md$",),
}

REGISTERED_ARTEFACT_PATTERNS: tuple[str, ...] = (
    r"^classification\.md$",
    r"^escalation_log\.md$",
    r"^tier_decisions_log\.md$",
    r"^round_program\.md$",
    r"^revision_plan.*\.md$",
    r"^reflection_report.*\.md$",
    r"^state_probe_.*\.md$",
    r"^tier_closeout_.*\.md$",
    r"^marshal_preflight_.*\.(md|json)$",
    r"^marshal_postflight_.*\.(md|json)$",
    r"^patch_report_.*\.md$",
    r"^local_findings_.*\.md$",
    r"^consolidated_findings_report_.*\.md$",
    r"^letter_findings_.*\.md$",
    r"^response_letter_review_.*\.md$",
    r"^step_[0-9a-z]+_.*\.md$",
    r"^_rule_digest_.*\.json$",
    r"^findings_report.*\.md$",
    r"^review_plan.*\.md$",
    r"^signoff.*\.md$",
)


def list_reviews(project_root: Path) -> list[Path]:
    reviews = project_root / "reviews"
    if not reviews.is_dir():
        return []
    return sorted(p for p in reviews.iterdir() if p.is_file())


def is_registered(name: str) -> bool:
    return any(re.match(p, name) for p in REGISTERED_ARTEFACT_PATTERNS)


def scoped_artefacts_for(tier: str, project_root: Path, date: str) -> list[Path]:
    patterns = TIER_SCOPED_ARTEFACT_PATTERNS.get(tier, ())
    reviews = list_reviews(project_root)
    matches: list[Path] = []
    for p in reviews:
        for pat in patterns:
            if re.match(pat, p.name) and (date in p.name or True):
                matches.append(p)
                break
    return matches


# --- Round-program override-tag parsing ---------------------------------------------

def read_override_tags(project_root: Path) -> list[str]:
    rp = project_root / "reviews" / "round_program.md"
    if not rp.is_file():
        return []
    text = rp.read_text(encoding="utf-8")
    return OVERRIDE_TAG_RE.findall(text)


def classify_override_tags(tags: Iterable[str]) -> tuple[list[str], list[str]]:
    """Split raw reason-codes into legal and illegal sets."""
    legal = [t for t in tags if t in LEGAL_OVERRIDE_REASONS]
    illegal = [t for t in tags if t not in LEGAL_OVERRIDE_REASONS]
    return legal, illegal


# --- Markdown and JSON emission -----------------------------------------------------

def emit_artefact(
    report: MarshalReport,
    project_root: Path,
    out_basename: str,
) -> tuple[Path, Path]:
    """Write both the ``.md`` and ``.json`` sidecars under ``reviews/``.

    Returns the absolute paths of the written files.
    """
    reviews = project_root / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    md_path = reviews / f"{out_basename}.md"
    json_path = reviews / f"{out_basename}.json"

    md_path.write_text(_render_markdown(report), encoding="utf-8")
    json_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return md_path, json_path


def _render_markdown(report: MarshalReport) -> str:
    lines: list[str] = []
    lines.append("---")
    lines.append(f"round: {report.round_id}")
    if report.kind == "preflight":
        lines.append(f"tier_requested: {report.tier}")
    else:
        lines.append(f"tier_entered: {report.tier}")
        if report.tier_entered_via:
            lines.append(f"tier_entered_via: {report.tier_entered_via}")
    lines.append(f"date: {report.date}")
    lines.append(f"plugin_version: {report.plugin_version}")
    lines.append(f"marshal_schema_version: {MARSHAL_SCHEMA_VERSION}")
    if report.first_run:
        lines.append("first_run: true")
    lines.append("---")
    lines.append("")

    if report.kind == "preflight":
        title = f"# Marshal Preflight — Round {report.round_id} ({report.tier} requested)"
    else:
        title = f"# Marshal Postflight — Round {report.round_id} ({report.tier})"
    lines.append(title)
    lines.append("")
    lines.append(f"STATUS: {report.verdict()}")
    lines.append("")

    blocking = [c for c in report.checks if c.severity in ("pass", "block")]
    advisory = [c for c in report.checks if c.severity in ("warn", "na")]

    lines.append("## Blocking checks")
    lines.append("")
    if not blocking:
        lines.append("_(no blocking checks in scope for this tier)_")
    for c in blocking:
        badge = "PASS" if c.severity == "pass" else "FAIL"
        lines.append(f"- **{c.check_id}** — {c.message}: {badge}")
        if c.remediation and c.severity == "block":
            lines.append(f"  - Remediation: {c.remediation}")
    lines.append("")

    lines.append("## Advisory checks")
    lines.append("")
    if not advisory:
        lines.append("_(no advisory checks fired)_")
    for c in advisory:
        badge = "WARN" if c.severity == "warn" else "N/A"
        lines.append(f"- **{c.check_id}** — {c.message}: {badge}")
        if c.remediation and c.severity == "warn":
            lines.append(f"  - Recommendation: {c.remediation}")
    lines.append("")

    lines.append("## Override record")
    lines.append("")
    lines.append(f"- Round program override-tags read: {report.overrides_read or []}")
    lines.append(f"- Overrides applied this round: {report.overrides_applied or []}")
    lines.append("")
    return "\n".join(lines) + "\n"


# --- Path resolution ----------------------------------------------------------------

def resolve_plugin_root(start: Path | None = None) -> Path:
    """Walk up from this file's location to find the plugin root (the dir with .claude-plugin)."""
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / ".claude-plugin" / "plugin.json").is_file():
            return candidate
    # Fallback: parent of the scripts directory.
    return Path(__file__).resolve().parent.parent
