#!/usr/bin/env python3
"""
DETERMINISTIC_CHECKS.md §9e — Register pre-filter (Sub-check H).

Reference implementation of the three counter probes that feed
SAFEGUARD_LAYER §Check 8 Sub-check H (Register Appropriateness):

  - Nominalisation density (suffix-pattern match / passage word count)
  - Prepositional-phrase run length (longest consecutive of/in/for/...
    chain in a sentence)
  - Hedging density (hedge-marker hits per 100 words)

Per §9e (added v0.10.2), this script is a **reference implementation**:
the accessibility-overlay's Sub-check H step 1 reads the §9e bundle but
does not invoke this script at runtime. The script exists for development
and testing — running it on a manuscript produces the same bundle the
overlay would compute.

Spec: references/DETERMINISTIC_CHECKS.md §9e.

Usage:
  python scripts/check8_h_prefilter.py <manuscript_path>
  python scripts/check8_h_prefilter.py <manuscript_path> --register-class non-technical

Per Q4 adjudication 2026-04-27: per-project hedge override mechanism is
deferred to v0.10.3+. The script ships only the built-in 15-marker hedge
list. Override-by-project semantics are spec'd in §9e prose only.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Tuple

from reader_accessibility_policy import load_profile

_PROFILE = load_profile()

# Nominalisation suffix probe — five suffixes (-ing intentionally excluded
# per §9e exclusion-list rationale; pilot showed ~30% FP inflation on
# participial constructions).
_RE_NOMINAL = re.compile(
    r"\b\w+(?:" + "|".join(re.escape(item) for item in _PROFILE["lexicons"]["nominalisation_suffixes"]) + r")\b",
    re.IGNORECASE,
)

# Exclusion list — content-bearing nominals whose removal would lose
# meaning, not register inflation. Mirrors §9e table row 1 prose.
_NOMINAL_EXCLUSIONS = frozenset(_PROFILE["domain_token_exclusions"])

# Prepositional-phrase probe — 13-preposition cover set per §9e table row 2.
_RE_PREP_PHRASE = re.compile(
    r"\b(" + "|".join(re.escape(item) for item in _PROFILE["lexicons"]["prepositions"]) + r")\s+\w+",
    re.IGNORECASE,
)

# Hedging probe — built-in 15-marker default. Override-by-project mechanism
# spec'd in §9e but deferred to v0.10.3 per Q4 adjudication 2026-04-27.
_RE_HEDGE = re.compile(
    r"\b(" + "|".join(re.escape(item) for item in _PROFILE["lexicons"]["hedges"]) + r")\b",
    re.IGNORECASE,
)

# Default thresholds per §9e (Q1 adjudication 2026-04-27: adopt defaults).
_THRESHOLD_NOM = _PROFILE["thresholds"]["register"]["nominalisation_density_candidate"]
_THRESHOLD_PREP_RUN = _PROFILE["thresholds"]["register"]["prepositional_run_candidate"]
_THRESHOLD_HEDGE_PER100 = _PROFILE["thresholds"]["register"]["hedges_per_100_words_candidate"]


def _corpus_drift(manuscript_text: str, profile: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return deterministic source-phrase presence candidates for H adjudication."""
    active = profile or _PROFILE
    return [
        {"source_phrase": phrase, "present": phrase.casefold() in manuscript_text.casefold(), "candidate_status": "present" if phrase.casefold() in manuscript_text.casefold() else "drift_candidate"}
        for phrase in active["corpus_drift"]["source_phrases"]
    ]

# Sentence splitter — naive but sufficient for prepositional-run probe.
# Splits on `.`/`!`/`?` followed by whitespace + capital, with allowance
# for common abbreviation patterns. Not perfect; the prepositional-run
# probe is intentionally tolerant of off-by-one boundary cases.
_RE_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _word_count(s: str) -> int:
    """Word-count helper (alphanumeric tokens; excludes punctuation)."""
    return len(re.findall(r"[\w']+", s))


def _tex_simplify(s: str) -> str:
    """Strip LaTeX command markup for word-counting / probe purposes."""
    t = s
    for _ in range(4):
        n = len(t)
        t = re.sub(r"\\[a-zA-Z@]+\*?(\[[^\]]*\])?(\{[^{}]*\})?", " ", t)
        t = re.sub(r"\\[a-zA-Z@]+\*?(\[[^\]]*\])?", " ", t)
        if len(t) == n:
            break
    return t


def _split_paragraphs(block: str) -> List[str]:
    """Blank-line-delimited paragraph split."""
    if not block.strip():
        return []
    parts = re.split(r"\n\s*\n+", block.strip())
    return [p.strip() for p in parts if p.strip()]


def _find_paragraph_locator(text: str, para_start: int) -> str:
    """Best-effort heading_path locator for a paragraph at offset para_start."""
    line_no = text.count("\n", 0, para_start) + 1
    # Walk backward to find the nearest preceding heading.
    preceding = text[:para_start]
    md_heads = list(re.finditer(r"(?m)^(#{1,6})\s+(.+)$", preceding))
    if md_heads:
        last = md_heads[-1]
        head_text = last.group(2).strip()[:64]
        return f"§{head_text} | line {line_no}"
    tex_heads = list(
        re.finditer(r"\\(chapter|section|subsection)\*?\s*\{([^}]+)\}", preceding)
    )
    if tex_heads:
        last = tex_heads[-1]
        head_text = last.group(2).strip()[:64]
        return f"§{head_text} | line {line_no}"
    return f"line {line_no}"


@dataclass
class ProbeResult:
    name: str
    raw_count: int
    normalised: float
    threshold: float
    fired: bool


@dataclass
class PassageBundle:
    locator: str
    word_count: int
    nominalisation: ProbeResult
    prep_run: ProbeResult
    hedging: ProbeResult

    @property
    def any_fired(self) -> bool:
        return (
            self.nominalisation.fired
            or self.prep_run.fired
            or self.hedging.fired
        )


def _probe_nominalisation(text: str, wc: int) -> ProbeResult:
    """Nominalisation density probe (§9e table row 1)."""
    if wc == 0:
        return ProbeResult("nominalisation", 0, 0.0, _THRESHOLD_NOM, False)
    raw_hits = _RE_NOMINAL.findall(text)
    # Apply exclusion list (case-insensitive).
    filtered = [h for h in raw_hits if h.lower() not in _NOMINAL_EXCLUSIONS]
    count = len(filtered)
    ratio = count / wc
    return ProbeResult(
        "nominalisation",
        count,
        round(ratio, 4),
        _THRESHOLD_NOM,
        ratio > _THRESHOLD_NOM,
    )


def _probe_prep_run(text: str) -> ProbeResult:
    """Prepositional-phrase longest-run probe (§9e table row 2)."""
    sentences = _RE_SENTENCE_SPLIT.split(text)
    longest_run = 0
    for sent in sentences:
        # Find all PP matches in order; consecutive matches share a chain.
        # Approximate consecutivity via char-distance threshold (≤8 chars
        # of intervening text means "consecutive" in practice — captures
        # cases like "of the X of the Y" where the "the" is the gap).
        matches = list(_RE_PREP_PHRASE.finditer(sent))
        if not matches:
            continue
        run = 1
        run_max = 1
        for i in range(1, len(matches)):
            gap_text = sent[matches[i - 1].end() : matches[i].start()]
            # "Consecutive" = gap is short and contains only function-word
            # tokens (articles, possessives, modifiers).
            gap_clean = gap_text.strip()
            if len(gap_clean) <= 8 and not re.search(r"\b(but|and|or|because|so|while|if|when)\b", gap_clean, re.IGNORECASE):
                run += 1
                run_max = max(run_max, run)
            else:
                run = 1
        longest_run = max(longest_run, run_max)
    return ProbeResult(
        "prep_run",
        longest_run,
        float(longest_run),
        float(_THRESHOLD_PREP_RUN),
        longest_run >= _THRESHOLD_PREP_RUN,
    )


def _probe_hedging(text: str, wc: int) -> ProbeResult:
    """Hedging density probe (§9e table row 3)."""
    if wc == 0:
        return ProbeResult("hedging", 0, 0.0, _THRESHOLD_HEDGE_PER100, False)
    count = len(_RE_HEDGE.findall(text))
    per100 = (count / wc) * 100.0
    return ProbeResult(
        "hedging",
        count,
        round(per100, 2),
        _THRESHOLD_HEDGE_PER100,
        per100 > _THRESHOLD_HEDGE_PER100,
    )


def analyse_passage(text: str, locator: str, is_tex: bool) -> PassageBundle:
    """Run all three probes on a single passage (paragraph-or-equivalent)."""
    probe_text = _tex_simplify(text) if is_tex else text
    wc = _word_count(probe_text)
    return PassageBundle(
        locator=locator,
        word_count=wc,
        nominalisation=_probe_nominalisation(probe_text, wc),
        prep_run=_probe_prep_run(probe_text),
        hedging=_probe_hedging(probe_text, wc),
    )


def analyse(text: str, path: Path) -> List[PassageBundle]:
    """Probe every paragraph in the manuscript and return bundles."""
    is_tex = path.suffix.lower() in {".tex", ".ltx"}
    bundles: List[PassageBundle] = []
    # Walk paragraphs at offsets so we can build per-paragraph locators.
    cursor = 0
    for para in _split_paragraphs(text):
        idx = text.find(para, cursor)
        if idx < 0:
            idx = cursor
        loc = _find_paragraph_locator(text, idx)
        bundle = analyse_passage(para, loc, is_tex)
        bundles.append(bundle)
        cursor = idx + len(para)
    return bundles


def emit_stub(
    bundles: List[PassageBundle],
    register_class: str,
    out_stream,
) -> None:
    """Emit the §9e output stub described in DETERMINISTIC_CHECKS.md."""
    in_scope = len(bundles)
    short_circuit = sum(1 for b in bundles if not b.any_fired)
    nom_fired = sum(1 for b in bundles if b.nominalisation.fired)
    prep_fired = sum(1 for b in bundles if b.prep_run.fired)
    hedge_fired = sum(1 for b in bundles if b.hedging.fired)

    print("### Register pre-filter (Sub-check H)", file=out_stream)
    print(f"- Passages in scope: {in_scope}", file=out_stream)
    print(f"- register_class_resolved: {register_class}", file=out_stream)
    print(f"- Bundles emitted: {in_scope}", file=out_stream)
    print(
        f"- Short-circuit (no probe fired): {short_circuit} / {in_scope}",
        file=out_stream,
    )
    print("- Probe firings:", file=out_stream)
    print(f"  - Nominalisation density: {nom_fired} fired", file=out_stream)
    print(f"  - Prepositional-phrase run length: {prep_fired} fired", file=out_stream)
    print(f"  - Hedging density: {hedge_fired} fired", file=out_stream)

    fired_bundles = [b for b in bundles if b.any_fired]
    if fired_bundles:
        print("- Per-passage detail (fired-only):", file=out_stream)
        for b in fired_bundles:
            n = b.nominalisation
            p = b.prep_run
            h = b.hedging
            print(
                f"  - {b.locator}: "
                f"nom={n.raw_count}/{b.word_count}={n.normalised} "
                f"[thr {n.threshold}] fired={n.fired}; "
                f"prep_run={p.raw_count} [thr {int(p.threshold)}] fired={p.fired}; "
                f"hedge={h.raw_count}/{h.normalised}per100 "
                f"[thr {h.threshold}] fired={h.fired}",
                file=out_stream,
            )


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manuscript", type=Path, help="Path to manuscript file (.md or .tex)")
    ap.add_argument(
        "--register-class",
        default="technical",
        choices=["technical", "mixed", "non-technical"],
        help="register_class resolved from directives.md (default: technical)",
    )
    args = ap.parse_args(argv)

    if not args.manuscript.exists():
        print(f"ERROR: manuscript not found: {args.manuscript}", flush=True)
        return 2

    text = args.manuscript.read_text(encoding="utf-8")
    bundles = analyse(text, args.manuscript)
    import sys
    emit_stub(bundles, args.register_class, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
