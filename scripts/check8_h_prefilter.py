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
from manuscript_geometry import heading_sections


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
    passage_role: str
    role_confidence: str
    role_reason: str
    binding_status: str
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


def _regex(items: list[str], *, capture: bool = False) -> re.Pattern[str]:
    body = "|".join(re.escape(item) for item in sorted(items, key=len, reverse=True))
    return re.compile(r"\b(" + body + r")\b" if capture else r"\b\w+(?:" + body + r")\b", re.IGNORECASE)


def _probe_nominalisation(text: str, wc: int, profile: dict[str, Any]) -> ProbeResult:
    """Nominalisation density probe (§9e table row 1)."""
    if wc == 0:
        return ProbeResult("nominalisation", 0, 0.0, profile["thresholds"]["register"]["nominalisation_density_candidate"], False)
    raw_hits = _regex(profile["lexicons"]["nominalisation_suffixes"]).findall(text)
    # Apply exclusion list (case-insensitive).
    exclusions = {item.casefold() for item in profile["domain_token_exclusions"]}
    filtered = [hit for hit in raw_hits if hit.casefold() not in exclusions]
    count = len(filtered)
    ratio = count / wc
    return ProbeResult(
        "nominalisation",
        count,
        round(ratio, 4),
        profile["thresholds"]["register"]["nominalisation_density_candidate"],
        ratio > profile["thresholds"]["register"]["nominalisation_density_candidate"],
    )


def _probe_prep_run(text: str, profile: dict[str, Any]) -> ProbeResult:
    """Prepositional-phrase longest-run probe (§9e table row 2)."""
    sentences = _RE_SENTENCE_SPLIT.split(text)
    longest_run = 0
    for sent in sentences:
        # Find all PP matches in order; consecutive matches share a chain.
        # Approximate consecutivity via char-distance threshold (≤8 chars
        # of intervening text means "consecutive" in practice — captures
        # cases like "of the X of the Y" where the "the" is the gap).
        prep = re.compile(r"\b(" + "|".join(re.escape(item) for item in profile["lexicons"]["prepositions"]) + r")\s+\w+", re.IGNORECASE)
        matches = list(prep.finditer(sent))
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
        float(profile["thresholds"]["register"]["prepositional_run_candidate"]),
        longest_run >= profile["thresholds"]["register"]["prepositional_run_candidate"],
    )


def _probe_hedging(text: str, wc: int, profile: dict[str, Any]) -> ProbeResult:
    """Hedging density probe (§9e table row 3)."""
    if wc == 0:
        return ProbeResult("hedging", 0, 0.0, profile["thresholds"]["register"]["hedges_per_100_words_candidate"], False)
    count = len(_regex(profile["lexicons"]["hedges"], capture=True).findall(text))
    per100 = (count / wc) * 100.0
    return ProbeResult(
        "hedging",
        count,
        round(per100, 2),
        profile["thresholds"]["register"]["hedges_per_100_words_candidate"],
        per100 > profile["thresholds"]["register"]["hedges_per_100_words_candidate"],
    )


def analyse_passage(text: str, locator: str, is_tex: bool, profile: dict[str, Any], passage_role: str, binding_status: str, role_confidence: str = "high", role_reason: str = "explicit caller role") -> PassageBundle:
    """Run all three probes on a single passage (paragraph-or-equivalent)."""
    probe_text = _tex_simplify(text) if is_tex else text
    wc = _word_count(probe_text)
    return PassageBundle(
        locator=locator,
        passage_role=passage_role,
        role_confidence=role_confidence,
        role_reason=role_reason,
        binding_status=binding_status,
        word_count=wc,
        nominalisation=_probe_nominalisation(probe_text, wc, profile),
        prep_run=_probe_prep_run(probe_text, profile),
        hedging=_probe_hedging(probe_text, wc, profile),
    )


def nominate_passage_roles(text: str, path: Path) -> list[dict[str, str]]:
    """Nominate non-overlapping manuscript spans; headings are geometry, never passages."""
    clean, geometry = heading_sections(text, path)
    entries: list[dict[str, str]] = []
    sections: list[tuple[str, int, int, bool]] = []
    if geometry:
        if clean[:geometry[0]["heading_start"]].strip():
            sections.append(("", 0, geometry[0]["heading_start"], True))
        for index, section in enumerate(geometry):
            sections.append((section["title"], section["body_start"], section["body_end"], index + 1 < len(geometry)))
    else:
        sections.append(("", 0, len(clean), False))

    orienting = re.compile(r"\b(having established|after the preceding|previous section|so far|up to this point)\b", re.I)
    contribution = re.compile(r"\b(this section (?:shows|argues|develops|examines)|we (?:show|argue)|i (?:show|argue)|the contribution here)\b", re.I)
    example = re.compile(r"\b(for example|to illustrate|consider)\b", re.I)
    anchor = re.compile(r"\b(in summary|to consolidate|taken together|these constructs)\b", re.I)
    transition = re.compile(r"\b(however|by contrast|turning now|the next section)\b", re.I)

    for title, start, end, has_next_heading in sections:
        section_atoms: list[tuple[int, int, str, int]] = []
        body = clean[start:end]
        for paragraph_index, paragraph_match in enumerate(re.finditer(r"\S[\s\S]*?(?=\n\s*\n|\Z)", body)):
            paragraph = paragraph_match.group(0)
            paragraph_start = start + paragraph_match.start()
            for sentence in re.finditer(r"\S[\s\S]*?(?:[.!?](?=\s|\Z)|\Z)", paragraph):
                sentence_text = sentence.group(0)
                sentence_start = paragraph_start + sentence.start()
                for clause in re.finditer(r"[^,;:]+(?:[,;:]|$)", sentence_text):
                    raw = clause.group(0)
                    left = len(raw) - len(raw.lstrip())
                    right = len(raw.rstrip())
                    if right <= left:
                        continue
                    atom_start = sentence_start + clause.start() + left
                    atom_end = sentence_start + clause.start() + right
                    section_atoms.append((atom_start, atom_end, clean[atom_start:atom_end], paragraph_index))
        section_role = title.casefold() if title.casefold() in {"abstract", "introduction", "conclusion"} else None
        for atom_index, (atom_start, atom_end, atom, paragraph_index) in enumerate(section_atoms):
            if orienting.search(atom): role, confidence, reason = "orienting_clause", "high", "cue-local backward orientation"
            elif contribution.search(atom): role, confidence, reason = "contribution_clause", "high", "cue-local contribution statement"
            elif example.search(atom): role, confidence, reason = "worked_example_vignette", "medium", "cue-local example span"
            elif anchor.search(atom): role, confidence, reason = "consolidation_anchor", "medium", "cue-local consolidation span"
            elif transition.search(atom): role, confidence, reason = "inter_section_transition", "medium", "cue-local transition span"
            elif section_role: role, confidence, reason = section_role, "high", f"body span under explicit {title} heading"
            elif paragraph_index == 0: role, confidence, reason = "section_framing", "medium", "uncued opening span after a heading"
            else: role, confidence, reason = "technical_body", "low", "uncued technical-body remainder; overlay must classify"
            line = clean.count("\n", 0, atom_start) + 1
            entries.append({"text": atom, "locator": f"line {line}:chars {atom_start}-{atom_end}", "role": role, "confidence": confidence, "reason": reason})
    if len({entry["locator"] for entry in entries}) != len(entries):
        raise ValueError("passage role nomination produced duplicate locators")
    return entries


def analyse(text: str, path: Path, profile: dict[str, Any] | None = None, *, phase: str = "Ph3", register_class: str = "technical", passage_roles: list[str] | None = None) -> List[PassageBundle]:
    """Probe every paragraph in the manuscript and return bundles."""
    active = profile or load_profile()
    is_tex = path.suffix.lower() in {".tex", ".ltx"}
    bundles: List[PassageBundle] = []
    # Walk paragraphs at offsets so we can build per-paragraph locators.
    cursor = 0
    if passage_roles is not None:
        paragraphs = _split_paragraphs(text)
        candidates = [{"text": para, "locator": "", "role": role, "confidence": "high", "reason": "explicit caller role"} for para, role in zip(paragraphs, passage_roles)]
    else:
        candidates = nominate_passage_roles(text, path)
    for candidate in candidates:
        para, role = candidate["text"], candidate["role"]
        idx = text.find(para, cursor)
        if idx < 0:
            idx = cursor
        loc = _find_paragraph_locator(text, idx)
        allowed_roles = active["register_scope"][register_class]
        in_scope = "all_passages" in allowed_roles or role in allowed_roles
        binding = "binding" if phase in active["sub_checks"]["H"]["binds_at"] else "advisory"
        if not in_scope: binding = "scope_candidate"
        if phase == "Ph2" and role in active["sub_checks"]["H"].get("ph2_role_overrides", {}):
            binding = active["sub_checks"]["H"]["ph2_role_overrides"][role]
        bundle = analyse_passage(para, candidate.get("locator") or loc, is_tex, active, role, binding, candidate["confidence"], candidate["reason"])
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
    negative_clear = sum(1 for b in bundles if not b.any_fired)
    nom_fired = sum(1 for b in bundles if b.nominalisation.fired)
    prep_fired = sum(1 for b in bundles if b.prep_run.fired)
    hedge_fired = sum(1 for b in bundles if b.hedging.fired)

    print("### Register pre-filter (Sub-check H)", file=out_stream)
    print(f"- Passages in scope: {in_scope}", file=out_stream)
    print("- register_class_resolved: domain-native", file=out_stream)
    print(f"- passage_scope_class_resolved: {register_class}", file=out_stream)
    print(f"- Bundles emitted: {in_scope}", file=out_stream)
    print(
        f"- Negative pre-filter clear (positive-marker audit still required): {negative_clear} / {in_scope}",
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
        "--passage-scope-class", "--register-class",
        dest="register_class",
        default="technical",
        choices=["technical", "mixed", "non-technical"],
        help="passage_scope_class resolved from directives.md; --register-class is a legacy alias",
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
