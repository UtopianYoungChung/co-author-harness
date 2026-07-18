"""Style/LLM-tic detector for academic prose.

Promotes the regex catalogue in references/DETERMINISTIC_CHECKS.md §§2–6 from
markdown-resident patterns to executable code. The LLM no longer counts —
this script does. Findings carry `rule_ref` anchors back to the markdown so
the human or LLM can adjudicate severity in context.

All rules fire at `severity=default` (style is taste, not truth). Promotion
to `inviolable` is reserved for grounding/citation auditors elsewhere.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List

from schema import Finding, FindingsReport, locator_for

# §2 — Absolute language
ABSOLUTE_RE = re.compile(r"\b(cannot|must|comprehensiv\w*|anticipat\w*)\b")

# §3 — Em-dash family
EMDASH_PLAIN_RE = re.compile(r"—")
EMDASH_LATEX_RE = re.compile(r"---")

# §4 — LLM tics
NOT_X_BUT_Y_RE = re.compile(r"\bnot (?:just |only |merely )?\S+ but\b", re.IGNORECASE)
HEDGED_TRANSITION_RE = re.compile(
    r"^(Accordingly|Likewise|Therefore|In practical terms|Moreover|Furthermore|Additionally),",
    re.MULTILINE,
)
DEMONSTRATIVE_PIVOT_RE = re.compile(
    r"\b[Tt]his\s+\w+\s+(illustrates?|supports?|strengthens?|confirms?|sharpens?)\b"
)
THIRD_PERSON_SELF_RE = re.compile(
    r"\b[Tt]he\s+(essay|paper|article|argument)\s+"
    r"(draws|asks|argues|develops|shows|claims|examines|grounds|considers|notes|suggests|proposes|identifies|traces)\b"
)
FORWARD_POINTER_RE = re.compile(r"\b[Tt]he (next|following) section\b")

# §5 — Sentence focus and voice
THERE_IS_RE = re.compile(r"\b[Tt]here (is|are|remain\w*)\b")
OVERCLAIM_RE = re.compile(r"\b(reveal\w*|expose\w*|prove\w*)\b")
STANDARD_X_RE = re.compile(r"\bstandard\s+(approach\w*|method\w*|practice\w*)\b", re.IGNORECASE)
FIRST_CLASS_RE = re.compile(r"\bfirst[\s-]class\b", re.IGNORECASE)

# §6 — Sentence length
LONG_SENTENCE_WARN = 60
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\[])")
WORD_RE = re.compile(r"\b\w+\b")


def _emit_per_line(
    findings: List[Finding],
    text: str,
    target: Path,
    pattern: re.Pattern[str],
    *,
    check_id: str,
    rule_ref: str,
    tentative: bool = False,
) -> None:
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in pattern.finditer(line):
            findings.append(
                Finding(
                    check_id=check_id,
                    category="style",
                    severity="default",
                    locator=locator_for(target, lineno),
                    evidence=match.group(0),
                    rule_ref=rule_ref,
                    tentative=tentative,
                )
            )


def audit_absolutes(text: str, target: Path) -> List[Finding]:
    findings: List[Finding] = []
    _emit_per_line(
        findings, text, target, ABSOLUTE_RE,
        check_id="ABS-001",
        rule_ref="DETERMINISTIC_CHECKS.md#§2",
        tentative=True,  # "cannot" / "must" require human judgment for severity
    )
    return findings


def audit_emdash(text: str, target: Path) -> List[Finding]:
    findings: List[Finding] = []
    paragraphs = re.split(r"\n\s*\n", text)
    line_cursor = 1
    for para in paragraphs:
        plain = len(EMDASH_PLAIN_RE.findall(para))
        latex = len(EMDASH_LATEX_RE.findall(para))
        pairs = max(plain, latex) // 2 + (plain + latex - 2 * (max(plain, latex) // 2))
        # Conservative: count any paragraph with > 2 em-dashes as exceeding "1 pair"
        if (plain + latex) > 2:
            findings.append(
                Finding(
                    check_id="EMD-001",
                    category="style",
                    severity="default",
                    locator=locator_for(target, line_cursor),
                    evidence=f"{plain + latex} em-dashes in paragraph",
                    rule_ref="EMDASH_BUNDLE_DISCIPLINE.md#§3",
                )
            )
        line_cursor += para.count("\n") + 2
    return findings


def audit_llm_tics(text: str, target: Path) -> List[Finding]:
    findings: List[Finding] = []
    _emit_per_line(findings, text, target, NOT_X_BUT_Y_RE,
        check_id="TIC-001", rule_ref="DETERMINISTIC_CHECKS.md#§4-not-x-but-y")
    _emit_per_line(findings, text, target, HEDGED_TRANSITION_RE,
        check_id="TIC-002", rule_ref="DETERMINISTIC_CHECKS.md#§4-hedged-transitions")
    _emit_per_line(findings, text, target, DEMONSTRATIVE_PIVOT_RE,
        check_id="TIC-003", rule_ref="DETERMINISTIC_CHECKS.md#§4-demonstrative-pivots")
    _emit_per_line(findings, text, target, THIRD_PERSON_SELF_RE,
        check_id="TIC-004", rule_ref="DETERMINISTIC_CHECKS.md#§4-third-person-self",
        tentative=True)
    _emit_per_line(findings, text, target, FORWARD_POINTER_RE,
        check_id="TIC-005", rule_ref="DETERMINISTIC_CHECKS.md#§4-forward-pointer")
    return findings


def audit_voice(text: str, target: Path) -> List[Finding]:
    findings: List[Finding] = []
    _emit_per_line(findings, text, target, THERE_IS_RE,
        check_id="VOI-001", rule_ref="DETERMINISTIC_CHECKS.md#§5-there-is",
        tentative=True)
    _emit_per_line(findings, text, target, OVERCLAIM_RE,
        check_id="VOI-002", rule_ref="DETERMINISTIC_CHECKS.md#§5-overclaim",
        tentative=True)
    _emit_per_line(findings, text, target, STANDARD_X_RE,
        check_id="VOI-003", rule_ref="DETERMINISTIC_CHECKS.md#§5-standard")
    _emit_per_line(findings, text, target, FIRST_CLASS_RE,
        check_id="VOI-004", rule_ref="DETERMINISTIC_CHECKS.md#§5-first-class")
    return findings


def _mask_preserving_offsets(text: str) -> str:
    """Blank out code fences and LaTeX commands while preserving byte and
    newline positions so downstream locators map back to the original file."""

    def _blank(match: re.Match[str]) -> str:
        return "".join("\n" if ch == "\n" else " " for ch in match.group(0))

    masked = re.sub(r"```.*?```", _blank, text, flags=re.DOTALL)
    masked = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", _blank, masked)
    return masked


def audit_sentence_length(text: str, target: Path) -> List[Finding]:
    findings: List[Finding] = []
    cleaned = _mask_preserving_offsets(text)

    # Walk sentence spans via the splitter's match boundaries so we can derive
    # each sentence's start offset in the ORIGINAL text and convert to a line
    # number. SENTENCE_SPLIT_RE matches the inter-sentence whitespace.
    starts: List[int] = [0]
    ends: List[int] = []
    for sep in SENTENCE_SPLIT_RE.finditer(cleaned):
        ends.append(sep.start())
        starts.append(sep.end())
    ends.append(len(cleaned))

    for start, end in zip(starts, ends):
        sentence = cleaned[start:end]
        word_count = len(WORD_RE.findall(sentence))
        if word_count > LONG_SENTENCE_WARN:
            lineno = text.count("\n", 0, start) + 1
            findings.append(
                Finding(
                    check_id="LEN-001",
                    category="style",
                    severity="default",
                    locator=locator_for(target, lineno),
                    evidence=f"{word_count}-word sentence",
                    rule_ref="DETERMINISTIC_CHECKS.md#§6",
                )
            )
    return findings


def audit_passive_voice(text: str, target: Path) -> List[Finding]:
    """Advisor-recommended addition: passive-voice quantification (~70% recall)."""
    findings: List[Finding] = []
    pattern = re.compile(r"\b(is|are|was|were|been|being)\s+(\w+ed)\b", re.IGNORECASE)
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in pattern.finditer(line):
            findings.append(
                Finding(
                    check_id="PAS-001",
                    category="passive",
                    severity="default",
                    locator=locator_for(target, lineno),
                    evidence=match.group(0),
                    rule_ref="STYLE_COMMITMENTS.md#passive-voice",
                    tentative=True,
                )
            )
    return findings


def audit_file(path: Path) -> FindingsReport:
    text = path.read_text(encoding="utf-8")
    report = FindingsReport(target=path.as_posix())
    report.extend(audit_absolutes(text, path))
    report.extend(audit_emdash(text, path))
    report.extend(audit_llm_tics(text, path))
    report.extend(audit_voice(text, path))
    report.extend(audit_sentence_length(text, path))
    report.extend(audit_passive_voice(text, path))
    return report


def main(argv: List[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="Manuscript file to audit")
    parser.add_argument("--out", type=Path, default=None, help="Write findings.json here")
    args = parser.parse_args(argv)

    if not args.target.is_file():
        print(f"[BLOCKER] target not found: {args.target}", file=sys.stderr)
        return 2

    report = audit_file(args.target)
    if args.out:
        report.write(args.out)
        print(f"OK wrote {args.out} ({report.counts()['total']} findings)")
    else:
        import json
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
