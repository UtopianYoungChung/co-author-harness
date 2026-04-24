#!/usr/bin/env python3
"""
DETERMINISTIC_CHECKS.md §9d — Cumulative cognitive load pre-filter (Sub-check G).

Emits the §9d stub into reviews/deterministic_<cycle_id>.md (merging with any
existing file) so accessibility-overlay can seed Sub-check G. Spec:
references/DETERMINISTIC_CHECKS.md §9d.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

# Consolidation-cue lexicon (§9d table, row 3)
_CONSOL = re.compile(
    r"\b(?:(?:at this point)|(?:so far)|(?:to this point)|(?:up to now)|"
    r"(?:taking stock)|(?:we have seen)|(?:we have established)|"
    r"(?:the reader now)|(?:at this stage)|"
    r"(?:with (?:this|these) in place)|"
    r"(?:having (?:mapped|traced|identified|set out))|"
    r"(?:with the (?:foregoing|preceding))|"
    r"(?:what the (?:preceding|foregoing) (?:pages|sections)))\b",
    re.IGNORECASE,
)

# Backward-reference lexicon (§9d row 4, from §9b Sub-check D)
_BACKWARD = re.compile(
    r"\b(having|after|so far|in the preceding|this section|"
    r"the previous section|up to this point)\b",
    re.IGNORECASE,
)

# Major headings: Markdown ^# or ^##; LaTeX \chapter / \section
_RE_MD_HEAD = re.compile(r"(?m)^(?:(#{1,2})\s+.+)$")
_RE_TEX_HEAD = re.compile(r"\\(?:chapter|section)\*?\s*\{[^}]*\}")

_ENVELOPES = {"P0": 800, "P1": 700, "P2": 600}


def _word_count(s: str) -> int:
    return len(re.findall(r"[\w']+", s))


def _tex_simplify_for_wc(s: str) -> str:
    t = s
    for _ in range(4):
        n = len(t)
        t = re.sub(
            r"\\[a-zA-Z@]+\*?(\[[^\]]*\])?(\{[^{}]*\})?",
            " ",
            t,
        )
        t = re.sub(
            r"\\[a-zA-Z@]+\*?(\[[^\]]*\])?",
            " ",
            t,
        )
        if len(t) == n:
            break
    return t


def _split_paragraphs(block: str) -> List[str]:
    if not block.strip():
        return []
    parts = re.split(r"\n\s*\n+", block.strip())
    return [p.strip() for p in parts if p.strip()]


def _find_headings(path: Path, text: str) -> List[Tuple[int, int, str]]:
    """(start, end, locator label) for each major heading, document order."""
    if path.suffix.lower() in {".tex", ".ltx"}:
        hits: List[Tuple[int, int, str]] = []
        for m in _RE_TEX_HEAD.finditer(text):
            loc = m.group(0)[:64].replace("\n", " ")
            hits.append((m.start(), m.end(), f"TeX: {loc}"))
    else:
        hits = []
        for m in _RE_MD_HEAD.finditer(text):
            line = m.group(0).strip()
            loc = line[:120]
            hits.append((m.start(), m.end(), loc))
    hits.sort(key=lambda x: x[0])
    return hits


@dataclass
class BoundaryStats:
    locator: str
    preceding_wc: int
    para_count: int
    gap_exceeds_words: bool
    gap_exceeds_six_paras: bool
    pre_heading_cue_count: int
    opening_cue_count: int
    zero_pre_heading_cues: bool
    zero_opening_cues: bool
    g_candidate: bool = False


def _opening_paragraph_after(text: str, heading_end: int) -> str:
    tail = text[heading_end:].lstrip("\n")
    if not tail:
        return ""
    # First blank-line-bounded block
    paras = _split_paragraphs(tail)
    return paras[0] if paras else ""


def analyze(
    text: str,
    path: Path,
    p_stage: str,
) -> Tuple[List[BoundaryStats], int, int, bool]:
    """Returns (per-boundary stats for each major heading, total_wc, n_headings, over_5000)."""
    pkey = p_stage if p_stage in _ENVELOPES else "P1"
    env = _ENVELOPES[pkey]
    if path.suffix.lower() in {".tex", ".ltx"}:
        wc_text = _tex_simplify_for_wc(text)
    else:
        wc_text = text
    total_wc = _word_count(wc_text)
    over_5000 = total_wc > 5000

    headings = _find_headings(path, text)
    n = len(headings)
    out: List[BoundaryStats] = []

    for i, (_hs, he, loc) in enumerate(headings):
        span_start = 0 if i == 0 else headings[i - 1][1]
        span_text = text[span_start : _hs]
        if path.suffix.lower() in {".tex", ".ltx"}:
            span_for_wc = _tex_simplify_for_wc(span_text)
        else:
            span_for_wc = span_text
        pw = _word_count(span_for_wc)
        paras = _split_paragraphs(span_text)
        pc = len(paras)

        last_two = paras[-2:] if len(paras) >= 2 else paras
        pre_block = " ".join(last_two)
        pre_cue = len(_CONSOL.findall(pre_block))
        if pre_cue == 0:
            # zero pre-heading window (consolidation lexicon in two paras before)
            zh_pre = True
        else:
            zh_pre = False

        open_p = _opening_paragraph_after(text, he)
        if path.suffix.lower() in {".tex", ".ltx"}:
            open_s = _tex_simplify_for_wc(open_p)
        else:
            open_s = open_p
        o_cons = len(_CONSOL.findall(open_s))
        o_back = len(_BACKWARD.findall(open_s))
        opening_total = o_cons + o_back
        if opening_total == 0:
            z_open = True
        else:
            z_open = False
        o_cue = opening_total  # for reporting: total matches in opening para

        gap_w = pw > env
        gap_p = pc > 6 and gap_w
        g_cand = gap_w and (pre_cue == 0) and (opening_total == 0)

        out.append(
            BoundaryStats(
                locator=loc,
                preceding_wc=pw,
                para_count=pc,
                gap_exceeds_words=gap_w,
                gap_exceeds_six_paras=gap_p,
                pre_heading_cue_count=pre_cue,
                opening_cue_count=o_cue,
                zero_pre_heading_cues=zh_pre,
                zero_opening_cues=z_open,
                g_candidate=g_cand,
            )
        )

    return out, total_wc, n, over_5000


def _parse_pstage(project_root: Path) -> str:
    p = project_root / "reviews" / "classification.md"
    if not p.is_file():
        return "P1"
    t = p.read_text(encoding="utf-8", errors="replace")
    m = re.search(
        r"(?:P-stage|\*\*P-stage:\*\*)\s*:?\s*P([012])\b", t, re.IGNORECASE
    )
    if m:
        return f"P{m.group(1)}"
    m2 = re.search(r"\bP([012])\b", t)
    if m2:
        return f"P{m2.group(1)}"
    return "P1"


def render_block(
    p_stage: str,
    cycle_id: str,
    stats: List[BoundaryStats],
    total_wc: int,
    n_headings: int,
    over_5000: bool,
) -> str:
    env = _ENVELOPES.get(p_stage, _ENVELOPES["P1"])
    n_gap_w = sum(1 for s in stats if s.gap_exceeds_words)
    n_gap_p = sum(1 for s in stats if s.gap_exceeds_six_paras)
    n_zero_pre = sum(1 for s in stats if s.zero_pre_heading_cues)
    n_zero_op = sum(1 for s in stats if s.zero_opening_cues)
    n_gc = sum(1 for s in stats if s.g_candidate)
    lines = [
        f"### Cumulative cognitive load pre-filter (Sub-check G)",
        f"- **P-stage envelope (words):** {p_stage} -> {env} (§9d)",
        f"- **Tool:** `scripts/check8_g_prefilter.py`  **cycle_id:** `{cycle_id}`  **generated:** {datetime.now().isoformat(timespec='seconds')}",
        f"- Major headings scanned: {n_headings}",
        f"- Boundary gaps exceeding P-stage envelope (words): {n_gap_w}",
        f"- Boundary gaps exceeding six-paragraph ceiling: {n_gap_p}",
        f"- Zero-cue pre-heading windows: {n_zero_pre}",
        f"- Zero-cue section-opening paragraphs: {n_zero_op}",
        f"- G-candidate boundaries (both gap-exceeded AND zero-cue): {n_gc}",
    ]
    for s in stats:
        if s.g_candidate:
            lines.append(
                f"  - {s.locator}: preceding-span wc={s.preceding_wc}, "
                f"para count={s.para_count}, pre-heading cues={s.pre_heading_cue_count}, "
                f"opening cues={s.opening_cue_count}"
            )
    if n_gc == 0:
        lines.append("  - (none)")
    lines.append(f"- Manuscript word count total: {total_wc}")
    lines.append(
        f"- Manuscript over 5,000-word envelope (per Sub-check G BLOCKER rule): "
        f"{'yes' if over_5000 else 'no'}"
    )
    return "\n".join(lines) + "\n"


def _merge_markers(cycle_id: str, block: str) -> Tuple[str, str]:
    start = f"<!-- check8_g_prefilter:begin cycle_id={cycle_id} -->\n"
    end = f"<!-- check8_g_prefilter:end cycle_id={cycle_id} -->\n"
    return start + block + end, start.strip()


def merge_into_reviews(
    project_root: Path, cycle_id: str, new_block_wrapped: str, marker_start: str
) -> str:
    target = project_root / "reviews" / f"deterministic_{cycle_id}.md"
    if not target.is_file():
        return (
            f"# Deterministic pre-filter stubs -- cycle `{cycle_id}`\n\n" + new_block_wrapped
        )
    existing = target.read_text(encoding="utf-8", errors="replace")
    pat = (
        re.escape("<!-- check8_g_prefilter:begin cycle_id=")
        + re.escape(cycle_id)
        + re.escape(" -->")
        + r"(.*?)"
        + re.escape("<!-- check8_g_prefilter:end cycle_id=")
        + re.escape(cycle_id)
        + re.escape(" -->")
    )
    m = re.search(pat, existing, re.DOTALL)
    if m:
        return (
            existing[: m.start()] + new_block_wrapped + existing[m.end() :]
        )
    # Legacy: replace first §9d block
    m2 = re.search(
        r"### Cumulative cognitive load pre-filter \(Sub-check G\).*?(?=\n## |\n### |\Z)",
        existing,
        re.DOTALL,
    )
    if m2:
        return existing[: m2.start()] + new_block_wrapped + existing[m2.end() :]
    if existing.rstrip().endswith("---"):
        return existing.rstrip() + "\n\n" + new_block_wrapped
    return existing.rstrip() + "\n\n" + new_block_wrapped


def main() -> int:
    ap = argparse.ArgumentParser(
        description="§9d Check 8 Sub-check G deterministic pre-filter (DETERMINISTIC_CHECKS.md)."
    )
    ap.add_argument("--project-root", required=True, type=Path, help="Project root (contains reviews/)")
    ap.add_argument(
        "--manuscript",
        required=True,
        type=Path,
        help="Path to manuscript .md or .tex (absolute or relative to --project-root)",
    )
    ap.add_argument(
        "--cycle-id",
        default="iter0",
        help="Cycle id; output is reviews/deterministic_<cycle_id>.md",
    )
    ap.add_argument(
        "--p-stage",
        choices=["P0", "P1", "P2"],
        help="P-stage gap envelope; default: parse reviews/classification.md or P1",
    )
    ap.add_argument(
        "--stdout-only",
        action="store_true",
        help="Print stub to stdout; do not write reviews/deterministic_*.md",
    )
    args = ap.parse_args()
    project_root = args.project_root.resolve()
    ms_path = args.manuscript
    if not ms_path.is_file():
        ms_path = (project_root / args.manuscript).resolve()
    if not ms_path.is_file():
        raise SystemExit(f"manuscript not found: {args.manuscript}")

    p_stage = args.p_stage or _parse_pstage(project_root)
    text = ms_path.read_text(encoding="utf-8", errors="replace")
    stats, total_wc, n_head, over_5000 = analyze(text, ms_path, p_stage)
    block = render_block(
        p_stage, args.cycle_id, stats, total_wc, n_head, over_5000
    )
    wrapped, mstart = _merge_markers(args.cycle_id, block)

    if args.stdout_only:
        print(wrapped, end="")
        return 0

    (project_root / "reviews").mkdir(parents=True, exist_ok=True)
    merged = merge_into_reviews(
        project_root, args.cycle_id, wrapped, mstart
    )
    out = project_root / "reviews" / f"deterministic_{args.cycle_id}.md"
    out.write_text(merged, encoding="utf-8", newline="\n")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
