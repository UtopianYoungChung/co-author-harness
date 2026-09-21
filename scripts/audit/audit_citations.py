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
#
# Symmetry (2026-09-19). Absence of evidence is treated exactly like failed
# evidence: `inviolable`. Before this, a manuscript that bound nothing produced a
# `default` finding while one that bound honestly and failed was blocked, so the
# cheapest way past the gate was to skip it. The three no-evidence states are
# no checks file (CIT-LOC-000) and a checks file that yields no verdict
# (CIT-LOC-002: the gate crashed on it, or it ran clean having bound zero checks).
# Gate availability (2026-09-20). CIT-LOC-001 remains `default`: an environment fault is a
# diagnosis, not a citation error, and an author cannot fix a missing dependency by citing
# better. It no longer stands alone. A gate that did not execute -- absent tools, a missing
# dependency, a timeout -- also raises CIT-LOC-003 at `inviolable`, because an unexecuted gate
# cannot clear a citation; the review that prompted this showed an empty CITATION_GATE_TOOLS
# yielding advisory-only findings, which was the cheapest remaining route past the gate.
# CIT-LOC-011, an UNSUPPORTED element, stays `default`: that is a disclosed gap under Rule 3
# item 8, such as a closed-access source, rather than a skipped gate.
#
# Outcome reconciliation (2026-09-20). The auditor relays a tool's conclusions, so it must
# relay all of them and must not disagree with the tool about whether anything was wrong.
# CIT-LOC-014 carries UNCOVERED: a cited sentence no check covers is a citation with no
# evidence, which is what CIT-LOC-000 says about a whole manuscript, so it blocks for the same
# reason. And a tool's exit status is now reconciled with what was parsed from its output: a
# non-zero exit the auditor cannot account for, or a clean exit alongside a failure line, means
# the two disagree and the run is not evidence of anything. Before this, UNCOVERED was printed
# by the verifier and read by nobody -- the verifier exited 1 and the auditor returned no
# finding at all.

SOURCE_CITATION_RE = re.compile(
    r"\([^()\n]*?(?:\b(?:1[89]|20)\d\d[a-z]?\b|\bn\.\s?d\.)[^()\n]*?\)"
    r"|\[\d{1,3}(?:\s?[,–-]\s?\d{1,3})*\]"
    r"|\\cite[tp]?\*?\{"
)
CHECKS_FILENAME = "citation_checks.json"
# Validation before verification: Rule 3 item 9 makes validation a separate gate that runs
# first, and identity/version/page-convention failures decide whether verification means
# anything at all.
GATE_TOOLS = ("validate_sources.py", "verify_locators.py")
GATE_RULE_REF = "GROUNDING_PROTOCOL.md#gp-1"
# Each tool's completion marker. A tool that never prints its marker never reached a verdict,
# whatever it exited with: a Python traceback also exits 1, which is a legitimate verdict code
# for both tools, so the exit status alone cannot tell success from collapse.
GATE_SUMMARY_RE = re.compile(r"^checks:\s*(\d+)\s+bound\s*/\s*\d+\s+failed\s*/\s*(\d+)\s+total")
GATE_COMPLETION_RE = {
    "verify_locators.py": GATE_SUMMARY_RE,
    "validate_sources.py": re.compile(r"^validation \(item 9/10\):\s*\d+\s+sources"),
}


def _find_checks_file(target: Path) -> Path | None:
    for base in list(target.parents)[:3]:
        candidate = base / "reviews" / CHECKS_FILENAME
        if candidate.is_file():
            return candidate
    return None


BUNDLED_GATE_TOOLS = HARNESS / "scripts" / "citation_gate"


def _resolve_gate_tools() -> tuple[Path, str | None]:
    """(directory, configuration problem) — the first COMPLETE gate, most specific first.

    CITATION_GATE_TOOLS, then the author's working copy, then the copy bundled with the
    harness. Completeness is what is ranked, not mere precedence: an override naming a
    directory without the tools used to win and leave the gate unexecuted, so one environment
    variable disabled citation checking entirely. A valid complete override still wins; an
    incomplete one falls back and is reported.
    """
    import os

    candidates: list[tuple[str, Path]] = []
    override = os.environ.get("CITATION_GATE_TOOLS")
    if override:
        candidates.append(("CITATION_GATE_TOOLS", Path(override)))
    candidates.append(("the author's working copy", Path.home() / ".claude" / "tools"))
    candidates.append(("the copy bundled with the harness", BUNDLED_GATE_TOOLS))

    for index, (label, path) in enumerate(candidates):
        missing = [name for name in GATE_TOOLS if not (path / name).is_file()]
        if missing:
            continue
        if index == 0:
            return path, None
        problem = None
        if override:
            absent = [name for name in GATE_TOOLS if not (Path(override) / name).is_file()]
            problem = (f"CITATION_GATE_TOOLS is set to {override}, which is missing "
                       f"{', '.join(absent)}; fell back to {label} at {path}")
        return path, problem

    searched = "; ".join(f"{label} at {path}" for label, path in candidates)
    return candidates[-1][1], f"no complete quote-binding gate found ({searched})"


def _gate_tools_dir() -> Path:
    """The gate directory alone. Kept for callers that do not need the diagnosis."""
    return _resolve_gate_tools()[0]


def _first_citation_line(text: str) -> int | None:
    """The line of the document's first citation, looking across wrapped lines.

    The scan was line by line, so a citation wrapping past the margin -- "(Tester," on one
    line, "2026, p. 1)." on the next -- was invisible, and a manuscript whose citations all
    wrapped produced no finding at all because it appeared to cite nothing (2026-09-21
    review, F5-01). Paragraphs are joined before the search, and the offset of the match is
    mapped back to the line it started on.
    """
    lines = text.splitlines()
    buf: List[str] = []
    spans: List[tuple] = []

    def search():
        if not buf:
            return None
        m = SOURCE_CITATION_RE.search(" ".join(buf))
        if not m:
            return None
        found = spans[0][1]
        for start, line in spans:
            if start > m.start():
                break
            found = line
        return found

    for n, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            hit = search()
            if hit is not None:
                return hit
            buf, spans = [], []
            continue
        spans.append((sum(len(b) + 1 for b in buf), n))
        buf.append(stripped)
    return search()


def audit_source_locators(text: str, target: Path) -> List[Finding]:
    import subprocess

    first = _first_citation_line(text)
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
            "CIT-LOC-000", "inviolable",
            f"manuscript cites sources but no reviews/{CHECKS_FILENAME} exists; no citation "
            "has a quote bound to its stated page, so all are UNVERIFIED",
        )]
    tools, config_problem = _resolve_gate_tools()
    missing = [name for name in GATE_TOOLS if not (tools / name).is_file()]
    if missing:
        # The diagnosis and the consequence are separate findings on purpose: one says what
        # is wrong with the machine, the other says that nothing has been cleared.
        return [
            finding("CIT-LOC-001", "default",
                    f"quote-binding gate unavailable: {config_problem or 'missing ' + ', '.join(missing)}"),
            finding("CIT-LOC-002", "inviolable",
                    "no quote-binding gate could be executed, so no citation has a bound quote "
                    "and all are UNVERIFIED. An unexecuted gate clears nothing"),
        ]
    out: List[Finding] = []
    if config_problem:
        out.append(finding("CIT-LOC-001", "default", config_problem
                           + ". The gate ran from the fallback; fix the configuration"))
    totals: tuple[int, int] | None = None          # (bound, total) from verify_locators.py
    for name in GATE_TOOLS:
        command = [sys.executable, str(tools / name), str(checks)]
        if name == "validate_sources.py":
            command.append("--offline")  # a pre-flight makes no network calls
        if name == "verify_locators.py":
            # Bind the verdict to the bytes being audited. Without this the tools read only the
            # checks file, so evidence built for another manuscript clears this one.
            command += ["--citing-document", str(target)]
        try:
            run = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                 errors="replace", timeout=300)
        except (OSError, subprocess.TimeoutExpired) as exc:
            out.append(finding("CIT-LOC-001", "default",
                               f"{name} did not complete ({type(exc).__name__})"))
            out.append(finding(
                "CIT-LOC-003", "inviolable",
                f"{name} did not complete, so its checks are UNVERIFIED. An unexecuted gate "
                "clears nothing, whatever the reason it could not run"))
            continue
        lines = [line.strip() for line in run.stdout.splitlines()]
        before_this_tool = len(out)
        unavailable = next((l for l in lines if l.startswith("GATE_UNAVAILABLE:")), None)
        if unavailable:
            out.append(finding(
                "CIT-LOC-001", "default",
                f"{name}: {unavailable[len('GATE_UNAVAILABLE:'):].strip()} "
                "This is an environment fault, not evidence",
            ))
            out.append(finding(
                "CIT-LOC-003", "inviolable",
                f"{name} could not execute, so its checks are UNVERIFIED. An unexecuted gate "
                "clears nothing, whatever the reason it could not run",
            ))
            continue
        marker = GATE_COMPLETION_RE[name]
        completion = next((m for m in (marker.match(x) for x in lines) if m), None)
        if completion is None:
            detail = (run.stderr or "").strip().splitlines()
            out.append(finding(
                "CIT-LOC-002", "inviolable",
                f"{name} exited {run.returncode} without reaching a verdict on {checks.name} "
                f"({detail[-1][:120] if detail else 'no output'}); its checks are UNVERIFIED. "
                "A tool that crashes has not cleared anything",
            ))
            continue
        if name == "verify_locators.py":
            totals = (int(completion.group(1)), int(completion.group(2)))
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
            elif line.startswith("UNCOVERED"):
                out.append(finding("CIT-LOC-014", "inviolable", f"{name}: {line}"))
        # The tool's own verdict and the auditor's reading of it have to agree. A summary line
        # proves the tool got far enough to have an opinion; it does not prove the opinion was
        # understood.
        relayed = out[before_this_tool:]
        blocking = [f for f in relayed if f.severity == "inviolable"]
        if run.returncode != 0 and not relayed:
            out.append(finding(
                "CIT-LOC-002", "inviolable",
                f"{name} exited {run.returncode} but reported nothing this auditor recognises. "
                "Its verdict and this relay disagree, so the run clears nothing",
            ))
        elif run.returncode == 0 and blocking:
            out.append(finding(
                "CIT-LOC-002", "inviolable",
                f"{name} exited 0 while reporting {len(blocking)} blocking result(s). Its exit "
                "status and its output disagree, so the run clears nothing",
            ))
    # Only an EMPTY checks file lands here. A file whose checks all failed has already been
    # reported, once per failure, as CIT-LOC-010; adding "binds no checks at all" to that
    # would be both duplicative and untrue.
    if totals is not None and totals == (0, 0):
        out.append(finding(
            "CIT-LOC-002", "inviolable",
            f"manuscript cites sources and {checks.name} contains no checks at all; an empty "
            "checks file is not evidence, so no citation has a quote bound to its stated page "
            "and all are UNVERIFIED",
        ))
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
