#!/usr/bin/env python3
"""v0.15.0-pre PR-4a — deterministic citation resolution for GROUNDING_PROTOCOL.

Closes the citation self-attestation loop the v0.15.0 architecture flagged:
under v0.14.0 and earlier, the same LLM that cited a rule also "verified"
the citation. This auditor breaks the circle by mechanically resolving
every `GROUNDING_PROTOCOL.md` rule citation in a target tree against the
HTML anchors landed at PR-3a (`<a id="gp-N"></a>` above each rule heading).

Citation forms recognised
-------------------------
1. `GROUNDING_PROTOCOL.md §Rule N`       (the existing corpus convention)
2. `GROUNDING_PROTOCOL.md §Rule Na`      (sub-rules like 7a)
3. `§§Rule N, Rule M, Rule N`            (comma-separated multi-rule lists)
4. `[GP §N]`                             (architecture-canonical short form;
                                          forward compatibility)
5. `[GP §Na]`                            (short-form sub-rules)

Other free-text references like `Rule 1` without the `GROUNDING_PROTOCOL.md`
qualifier are *not* matched here — too many false positives across the corpus
(`Rule 1` appears as an ordinal in many unrelated lists). The same applies to
the bare `GROUNDING_PROTOCOL.md` Rule N form (no `§`) — agents/ uses this in
prose where the citation is contextual rather than indexable. The auditor
errs on the side of precision over recall: every citation it flags is
verifiable against the live anchor file. A later slice may add a
citation-style normalisation pass that promotes bare forms to canonical.

Severity
--------
`inviolable` — citation is a truth claim, not a style choice (per the
v0.15.0 architecture's two-tier vocabulary). An unresolved citation
fails CI closed. By contrast, `category=style` findings from the existing
audit_style.py are `default` severity.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, List, Set

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from schema import Finding, FindingsReport, locator_for  # noqa: E402

HARNESS = HERE.parent.parent
GP_PATH_DEFAULT = HARNESS / "references" / "GROUNDING_PROTOCOL.md"

ANCHOR_RE = re.compile(r'<a id="gp-(\d+[a-z]?)"></a>')

# Match `GROUNDING_PROTOCOL.md §Rule N` or `§§Rule N, Rule M`.
# The leading filename anchors the match so we don't grab unrelated "Rule N"
# tokens from other contexts.
GP_RULE_PROSE_RE = re.compile(
    r"GROUNDING_PROTOCOL\.md\s+§+\s*((?:Rule\s+\d+[a-z]?(?:\s*[,()][^,)]{0,40})?\s*,?\s*)+)",
    re.IGNORECASE,
)
RULE_TOKEN_RE = re.compile(r"Rule\s+(\d+[a-z]?)", re.IGNORECASE)

# Match `[GP §N]` short form
GP_SHORT_RE = re.compile(r"\[GP\s*§\s*(\d+[a-z]?)\]")

# Files to skip when walking a target tree
SKIP_DIR_NAMES = {
    ".git", ".claude", "releases", "tmp", "unpacked", "archives",
    "node_modules", "__pycache__", ".plugin-cache", ".mcpb-cache",
}


def load_valid_anchors(gp_path: Path) -> Set[str]:
    """Return the set of rule IDs (e.g. '1', '7a') with stable anchors."""
    if not gp_path.is_file():
        raise FileNotFoundError(f"GROUNDING_PROTOCOL.md not found at {gp_path}")
    text = gp_path.read_text(encoding="utf-8")
    return set(ANCHOR_RE.findall(text))


def iter_markdown_targets(root: Path) -> Iterable[Path]:
    if root.is_file():
        if root.suffix.lower() == ".md":
            yield root
        return
    for p in root.rglob("*.md"):
        if any(part in SKIP_DIR_NAMES for part in p.relative_to(root).parts):
            continue
        # Skip the GROUNDING_PROTOCOL itself — it's the resolution source,
        # not a citer subject to its own discipline.
        if p.resolve() == GP_PATH_DEFAULT.resolve():
            continue
        yield p


def _emit_unresolved(
    findings: List[Finding],
    target: Path,
    lineno: int,
    cited_rule: str,
    evidence: str,
) -> None:
    findings.append(Finding(
        check_id="CIT-001",
        category="citation",
        severity="inviolable",
        locator=locator_for(target, lineno),
        evidence=evidence.strip()[:200],
        rule_ref=f"GROUNDING_PROTOCOL.md#gp-{cited_rule}",
    ))


def audit_file(path: Path, valid_anchors: Set[str]) -> List[Finding]:
    findings: List[Finding] = []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    for lineno, line in enumerate(lines, start=1):
        # Prose form: `GROUNDING_PROTOCOL.md §Rule N` and multi-rule lists
        for m in GP_RULE_PROSE_RE.finditer(line):
            cluster = m.group(1)
            for rm in RULE_TOKEN_RE.finditer(cluster):
                cited = rm.group(1).lower()
                if cited not in valid_anchors:
                    _emit_unresolved(findings, path, lineno, cited, m.group(0))

        # Short form: `[GP §N]`
        for m in GP_SHORT_RE.finditer(line):
            cited = m.group(1).lower()
            if cited not in valid_anchors:
                _emit_unresolved(findings, path, lineno, cited, m.group(0))

    return findings


def audit_tree(root: Path, valid_anchors: Set[str]) -> FindingsReport:
    report = FindingsReport(target=root.as_posix())
    for f in iter_markdown_targets(root):
        report.extend(audit_file(f, valid_anchors))
    return report


# --- Source locators (bibliographic citations) --------------------------------
# The rule-anchor audit above checks the harness's own citations. This auditor
# covers a manuscript's citations to sources. It issues no verdict itself: it runs
# the two quote-binding gates on the project's checks file and relays their
# conclusions, and it says so when no such evidence exists.

SOURCE_CITATION_RE = re.compile(
    r"\([^()\n]*?\b(?:1[89]|20)\d\d[a-z]?\b[^()\n]*?\)"
    r"|\[\d{1,3}(?:\s?[,–-]\s?\d{1,3})*\]"
    r"|\\cite[tp]?\*?\{"
)
CHECKS_FILENAME = "citation_checks.json"
GATE_TOOLS = ("verify_locators.py", "validate_sources.py")
GATE_RULE_REF = "GROUNDING_PROTOCOL.md#gp-1"


def _find_checks_file(target: Path) -> Path | None:
    for base in list(target.parents)[:3]:
        candidate = base / "reviews" / CHECKS_FILENAME
        if candidate.is_file():
            return candidate
    return None


def _gate_tools_dir() -> Path:
    import os

    return Path(os.environ.get("CITATION_GATE_TOOLS") or (Path.home() / ".claude" / "tools"))


def audit_source_locators(text: str, target: Path) -> List[Finding]:
    import subprocess

    first = next(
        (i for i, line in enumerate(text.splitlines(), 1) if SOURCE_CITATION_RE.search(line)),
        None,
    )
    if first is None:
        return []

    def finding(check_id: str, severity: str, evidence: str, tentative: bool = False) -> Finding:
        return Finding(
            check_id=check_id,
            category="citation",
            severity=severity,
            locator=locator_for(target, first),
            evidence=evidence[:400],
            rule_ref=GATE_RULE_REF,
            tentative=tentative,
        )

    checks = _find_checks_file(target)
    if checks is None:
        return [finding(
            "CIT-LOC-000", "default",
            f"manuscript cites sources but no reviews/{CHECKS_FILENAME} exists; no citation "
            "has a quote bound to its stated page, so all are UNVERIFIED",
        )]
    tools = _gate_tools_dir()
    missing = [name for name in GATE_TOOLS if not (tools / name).is_file()]
    if missing:
        return [finding(
            "CIT-LOC-001", "default",
            f"quote-binding gate unavailable ({', '.join(missing)} not found under "
            "CITATION_GATE_TOOLS); citations remain UNVERIFIED",
        )]
    out: List[Finding] = []
    for name in GATE_TOOLS:
        command = [sys.executable, str(tools / name), str(checks)]
        if name == "validate_sources.py":
            command.append("--offline")  # a pre-flight makes no network calls
        try:
            run = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                 errors="replace", timeout=300)
        except (OSError, subprocess.TimeoutExpired) as exc:
            out.append(finding("CIT-LOC-001", "default",
                               f"{name} did not complete ({type(exc).__name__}); citations remain UNVERIFIED"))
            continue
        lines = [line.strip() for line in run.stdout.splitlines()]
        for idx, line in enumerate(lines):
            if line.startswith("FAIL"):
                follow = lines[idx + 1] if idx + 1 < len(lines) else ""
                detail = follow.lstrip("- ") if follow.startswith("-") else ""
                out.append(finding("CIT-LOC-010", "inviolable", f"{name}: {line} {detail}".strip()))
            elif line.startswith("UNSUPPORTED"):
                out.append(finding("CIT-LOC-011", "default", f"{name}: {line}"))
            elif line.startswith("DISCLOSE"):
                out.append(finding("CIT-LOC-012", "default", f"{name}: {line}", tentative=True))
            elif line.startswith("REVIEW"):
                out.append(finding("CIT-LOC-013", "default", f"{name}: {line}", tentative=True))
    return out


def main(argv: List[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("target", type=Path, nargs="?",
                        help="File or directory to audit. Required.")
    parser.add_argument("--gp", type=Path, default=GP_PATH_DEFAULT,
                        help=f"Path to GROUNDING_PROTOCOL.md (default: {GP_PATH_DEFAULT})")
    parser.add_argument("--out", type=Path, default=None,
                        help="Write findings.json here (default: stdout)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress per-finding stdout (still writes --out)")
    args = parser.parse_args(argv)

    if args.target is None:
        print("[BLOCKER] target path is required", file=sys.stderr)
        return 2
    if not args.target.exists():
        print(f"[BLOCKER] target not found: {args.target}", file=sys.stderr)
        return 2

    try:
        valid_anchors = load_valid_anchors(args.gp)
    except FileNotFoundError as exc:
        print(f"[BLOCKER] {exc}", file=sys.stderr)
        return 2

    report = audit_tree(args.target, valid_anchors)

    if args.out:
        report.write(args.out)

    if not args.quiet:
        counts = report.counts()
        unresolved = counts["by_severity"].get("inviolable", 0)
        print(
            f"audit_citations: {counts['total']} citation finding(s); "
            f"{unresolved} unresolved (BLOCKER) against {len(valid_anchors)} "
            f"valid anchors"
        )
        for f in report.findings:
            print(f"  [BLOCKER] {f.check_id} {f.locator}  {f.evidence}  "
                  f"(rule_ref={f.rule_ref})")

    # Exit 1 if any inviolable findings; truth-class citations failing
    # resolution must block the release gate.
    inviolable_count = sum(1 for f in report.findings if f.severity == "inviolable")
    return 1 if inviolable_count > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
