#!/usr/bin/env python3
"""register_dispersion_check - dispersion-side AI-register proxies (B4-B7).

DETERMINISTIC_CHECKS.md sections 4 and 6 measure prose register by CENTRAL
TENDENCY (average sentence length, max sentence length, per-pattern counts).
That leaves a gap this script fills: a manuscript can sit dead-on every average
and still read as machine-generated because its sentences are all the SAME.
Uniformity is a dispersion property, and nothing in the package measured
dispersion before.

Emits four proxy candidates:

  B4  rhythm uniformity        coefficient of variation of sentence length
  B5  clause-depth uniformity  rate of pre-predicate interrupting material
  B6  circular closure         paragraph first/last sentence content overlap
  B7  deflected complexity     "nuanced"-family claims with no explanation

READ-ONLY BY CONSTRUCTION. This script writes no files and creates no
directories. It prints to stdout and nothing else. That is deliberate: adding a
filesystem write would make it a census writer under
scripts/destination-coverage-check.py and require a registry entry plus a
sha256 pin. Keep it read-only; route any persistence through the caller.

PROVENANCE AND STATUS OF THE THRESHOLDS
---------------------------------------
The pattern inventory was prompted by a popular-audience video on AI writing
tells (Nail It With AI, "7 Hidden AI Writing Tells", 2026-02-12). That source
cites numeric findings (burstiness bands, detector accuracies, corpus
percentages) to unnamed or unverifiable studies. Under GROUNDING_PROTOCOL.md
those numbers may not enter the package as findings, and none of them appear
here. Every threshold below is a HARNESS CONVENTION chosen by local
calibration, is labelled as such, and is falsifiable by recalibration. See
DETERMINISTIC_CHECKS.md section 4b for the calibration record.

All outputs are proxy candidates for Evaluator judgment, never normative
semantic predicates -- the same status the reader-accessibility prefilters
carry.

C-7 INTERACTION (binding)
-------------------------
Uniform rhythm that recurs in the author's own accepted prose is idiolect, not
a defect (STYLE_COMMITMENTS.md C-7). Pass --baseline with the author's accepted
prose and the check scores the manuscript against THAT, not against a borrowed
register. Without a baseline B4/B5 are reported as measurements only and emit no
findings.

Run:
  python scripts/register_dispersion_check.py <file> [<file>...]
  python scripts/register_dispersion_check.py <file> --baseline <accepted.md>
  python scripts/register_dispersion_check.py <file> --json

Exit: 0 no candidates; 1 candidate(s) surfaced; 2 cannot analyse.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

# --- calibration constants (harness conventions; see module docstring) -------
#
# CALIBRATION RESULT, 2026-08-21 (recorded because it is a NEGATIVE result and
# constrains what this script is allowed to claim).
#
# Corpus: 4 LLM-authored harness memos under docs/analysis/ vs 3 human-authored
# craft/scholarly sources under references/ (Abbott, Suchman, Bacon).
#
#              B4 rhythm CV        B5 interruption rate
#   LLM        0.602 - 0.683       0.304 - 0.615
#   human      0.437 - 0.623       0.382 - 0.541
#
# The ranges OVERLAP and the direction is INVERTED: the LLM-authored sample
# scored more varied, not less. The popular claim that low burstiness indicates
# machine generation did not replicate here. An absolute low-CV threshold would
# have flagged Bacon's own published sentence-craft guide (CV 0.437) as
# machine-generated.
#
# Consequence, binding on this script: B4 and B5 HAVE NO ABSOLUTE THRESHOLD.
# They are computed and reported, and they produce a finding ONLY as a
# within-author delta against a supplied --baseline. That is also the C-7
# correct behaviour: the author's own prose is the yardstick, never a
# population constant. Do not reintroduce an absolute band without rerunning
# this calibration on a larger corpus and recording the result here.

# B4/B5: within-author sensitivity. A draft must fall to this fraction of the
# author's own baseline dispersion before it is worth surfacing.
B4_BASELINE_RATIO = 0.75
B5_BASELINE_RATIO = 0.75

# B6: content-word Jaccard overlap between a paragraph's first and last
# sentence, for paragraphs of at least B6_MIN_SENTENCES. This one DID separate:
# across both corpora above (48 qualifying paragraphs) the observed maximum was
# 0.250 and the 90th percentile 0.067, while a constructed circular paragraph
# scored 0.444. 0.35 sits in the empty band between them.
B6_OVERLAP_HIGH = 0.35
B6_MIN_SENTENCES = 3

# A sample smaller than this cannot support a dispersion statistic.
MIN_SENTENCES_FOR_STATS = 12

# --- lexical patterns --------------------------------------------------------

# B7: the "nuanced" family. A hit is only a candidate when the sentence does
# NOT go on to supply the complexity it claims (see _explains_complexity).
NUANCE_RE = re.compile(
    r"\b(nuanced|nuance|more complex than|multifaceted|it depends on context"
    r"|a range of factors|various factors)\b",
    re.IGNORECASE,
)

# Markers that a sentence actually discharges its complexity claim rather than
# merely naming it.
EXPLANATION_RE = re.compile(
    r"\b(because|since|depends on (?:whether|how|the)|specifically"
    r"|for (?:example|instance)|namely|that is|i\.e\.|e\.g\."
    r"|first|second|third|three|two|four)\b"
    r"|:",
    re.IGNORECASE,
)

# B5: constructions that interrupt or delay the predicate. Tagger-free.
RELATIVE_RE = re.compile(r"\b(who|whom|whose|which|that)\b", re.IGNORECASE)
SUBORDINATOR_RE = re.compile(
    r"^\s*(although|though|while|whereas|because|since|if|when|after|before"
    r"|unless|until|once|where|as)\b",
    re.IGNORECASE,
)
PARENTHETICAL_RE = re.compile(r"\([^)]{4,}\)|\u2014[^\u2014]{4,}\u2014|---[^-]{4,}---")

STOPWORDS = frozenset("""
a an the and or but nor for yet so of to in on at by with from as is are was
were be been being has have had do does did this that these those it its their
they them he she his her we us our you your i me my not no if then than which
who whom whose what when where why how can could will would shall should may
might must more most other such only own same too very s t just also there here
into over under again further once about against between through during before
after above below up down out off all any both each few
""".split())


def _strip_markup(text: str) -> str:
    """Remove LaTeX/markdown machinery that would corrupt sentence counts.

    Structural material (headings, table rows, bullet and numbered list items,
    block quotes) is dropped rather than flattened into the prose stream. This
    matters more than it looks: during calibration, list items such as
    "Changes:" and "- Delete the router." were being counted as one- and
    three-word sentences, which inflated the B4 dispersion statistic so far
    that LLM-authored memos scored as highly varied prose. Dispersion is only
    meaningful over running prose.
    """
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)      # fenced code
    text = re.sub(r"`[^`]*`", " ", text)                          # inline code
    text = re.sub(r"\$\$.*?\$\$", " ", text, flags=re.DOTALL)     # display math
    text = re.sub(r"\$[^$]*\$", " ", text)                        # inline math
    # Delete only environments whose bodies are non-prose. The former generic
    # ``\\begin{.*}...\\end{.*}`` pattern also erased an entire normal
    # ``document`` environment, leaving a LaTeX manuscript with zero sentences.
    non_prose_env = (
        r"(?P<env>equation\*?|align\*?|gather\*?|multline\*?|displaymath|math"
        r"|verbatim|Verbatim|lstlisting|minted|tikzpicture|tabular\*?|table\*?"
        r"|figure\*?|algorithm\*?)"
    )
    text = re.sub(
        rf"\\begin\{{{non_prose_env}\}}.*?\\end\{{(?P=env)\}}",
        " ",
        text,
        flags=re.DOTALL,
    )
    # Preserve prose inside document/abstract/quotation and other containers;
    # remove only their boundary commands.
    text = re.sub(r"\\(?:begin|end)\{[^}]+\}(?:\[[^\]]*\])?", " ", text)
    text = re.sub(r"\\(?:cite|ref|label|autoref)\w*\{[^}]*\}", " ", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{([^}]*)\})?", r" \1 ", text)
    # Structural lines -> blank, so they also break paragraphs correctly.
    text = re.sub(r"^\s{0,3}#{1,6}\s.*$", "", text, flags=re.MULTILINE)   # headings
    text = re.sub(r"^\s*[|>].*$", "", text, flags=re.MULTILINE)           # tables/quotes
    text = re.sub(r"^\s*(?:[-*+]|\d+\.)\s+.*$", "", text, flags=re.MULTILINE)  # lists
    # Bold/italic run-in labels ("**Changes:**", "*Sequencing rationale.*") that
    # open a line. Calibration showed these entering the stream as one- and
    # two-word "sentences" and inflating dispersion.
    text = re.sub(r"^\s*[*_]{1,3}[^*_\n]{1,60}[*_]{1,3}\s*:?\s*$", "",
                  text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[*_]{2,3}([^*_\n]{1,60}?)[*_]{2,3}\s*[:.]\s*", "",
                  text, flags=re.MULTILINE)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)                # links
    text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", text)             # emphasis
    text = text.replace("{", " ").replace("}", " ")
    return text


# A "sentence" with no finite-verb evidence is a label or caption fragment, not
# prose. Dispersion over labels measures layout, not rhythm.
_VERBISH = re.compile(
    r"\b(is|are|was|were|be|been|being|has|have|had|do|does|did|can|could"
    r"|will|would|shall|should|may|might|must|says?|makes?|takes?|gives?"
    r"|\w+(?:s|ed|es))\b",
    re.IGNORECASE,
)


def is_prose_sentence(sentence: str) -> bool:
    """Reject labels, captions, and stubs left behind by markup stripping."""
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", sentence)
    if len(words) < 3:
        return False
    if sentence.rstrip().endswith(":"):
        return False
    return bool(_VERBISH.search(sentence))


# Abbreviations that must not end a sentence. Python look-behind requires a
# fixed width, so these are re-joined after the split rather than excluded
# inside it.
_ABBREV = (
    "e.g.", "i.e.", "cf.", "vs.", "al.", "Dr.", "Prof.", "Fig.", "eq.",
    "no.", "pp.", "vol.", "ed.", "eds.", "St.", "Mr.", "Ms.", "Mrs.",
    "ca.", "ch.", "sec.", "approx.",
)
_ABBREV_END = re.compile(
    r"(?:^|[\s(])(?:" + "|".join(re.escape(item) for item in _ABBREV) + r")$",
    re.IGNORECASE,
)
_SENT_SPLIT = re.compile(r"(?<=[.!?])[\"')\]]*\s+(?=[A-Z\"'(\[])")


def split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def split_sentences(block: str) -> list[str]:
    block = re.sub(r"\s+", " ", block).strip()
    if not block:
        return []
    parts = [s.strip() for s in _SENT_SPLIT.split(block) if s.strip()]
    # Re-join fragments split after a complete abbreviation token. A raw
    # ``endswith("ed.")`` check would also merge ordinary words such as
    # ``nuanced.``, hiding B7 candidates and corrupting sentence counts.
    merged: list[str] = []
    for part in parts:
        if merged and _ABBREV_END.search(merged[-1]):
            merged[-1] = merged[-1] + " " + part
        else:
            merged.append(part)
    return merged


def word_count(sentence: str) -> int:
    return len(re.findall(r"[A-Za-z][A-Za-z'-]*", sentence))


def content_words(sentence: str) -> set[str]:
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", sentence.lower())
    out = set()
    for w in words:
        if w in STOPWORDS or len(w) < 4:
            continue
        # Crude suffix folding so "management"/"managing", "productivity"/
        # "productive" collapse to one token. Longest suffix first.
        for suf in ("ization", "ational", "iveness", "ability", "ement",
                    "ation", "ments", "ness", "ions", "ment", "ity", "ies",
                    "ive", "ing", "ion", "ed", "es", "ly", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[: -len(suf)]
                break
        out.add(w)
    return out


def has_interruption(sentence: str) -> bool:
    """Proxy for material sitting between the subject and its predicate.

    Tagger-free, so this measures the CONSTRUCTIONS that create subject-verb
    distance (leading subordinate clause, relative clause, appositive comma
    pair, parenthetical or dashed insertion) rather than counting the distance
    itself. spacy/nltk are not dependencies of this package; if either is added
    later, replace this function with a real dependency-parse measurement and
    recalibrate B5_INTERRUPT_LOW.
    """
    if SUBORDINATOR_RE.search(sentence):
        return True
    if PARENTHETICAL_RE.search(sentence):
        return True
    if RELATIVE_RE.search(sentence) and "," in sentence:
        return True
    # appositive / interrupter: a comma pair enclosing a short span, not a list
    for m in re.finditer(r",\s*([^,]{4,60}?),\s", sentence):
        span = m.group(1)
        if " and " not in span and " or " not in span:
            return True
    return False


def _explains_complexity(sentence: str) -> bool:
    return bool(EXPLANATION_RE.search(sentence))


def analyse(text: str) -> dict:
    clean = _strip_markup(text)
    paragraphs = split_paragraphs(clean)

    sentences: list[str] = []
    para_sentences: list[list[str]] = []
    for para in paragraphs:
        sents = [s for s in split_sentences(para) if is_prose_sentence(s)]
        if sents:
            para_sentences.append(sents)
            sentences.extend(sents)

    lengths = [word_count(s) for s in sentences]
    lengths = [n for n in lengths if n > 0]

    result: dict = {
        "sentences": len(lengths),
        "paragraphs": len(para_sentences),
        "sufficient": len(lengths) >= MIN_SENTENCES_FOR_STATS,
    }

    if not result["sufficient"]:
        result["note"] = (
            f"only {len(lengths)} sentences; dispersion statistics need at least "
            f"{MIN_SENTENCES_FOR_STATS}. B4/B5 not computed."
        )
        result["b6_circular"] = _b6(para_sentences)
        result["b7_nuance"] = _b7(sentences)
        return result

    mean = statistics.fmean(lengths)
    stdev = statistics.stdev(lengths)
    result["mean_length"] = round(mean, 2)
    result["stdev_length"] = round(stdev, 2)
    result["cv"] = round(stdev / mean, 3) if mean else 0.0
    result["min_length"] = min(lengths)
    result["max_length"] = max(lengths)
    result["short_sentences_under_10w"] = sum(1 for n in lengths if n < 10)

    interrupted = sum(1 for s in sentences if word_count(s) and has_interruption(s))
    result["interruption_rate"] = round(interrupted / len(lengths), 3)

    result["b6_circular"] = _b6(para_sentences)
    result["b7_nuance"] = _b7(sentences)
    return result


def _b6(para_sentences: list[list[str]]) -> list[dict]:
    hits = []
    for idx, sents in enumerate(para_sentences, start=1):
        if len(sents) < B6_MIN_SENTENCES:
            continue
        first, last = content_words(sents[0]), content_words(sents[-1])
        if not first or not last:
            continue
        overlap = len(first & last) / len(first | last)
        if overlap >= B6_OVERLAP_HIGH:
            hits.append({
                "paragraph": idx,
                "overlap": round(overlap, 3),
                "first": sents[0][:110],
                "last": sents[-1][:110],
            })
    return hits


def _b7(sentences: list[str]) -> list[dict]:
    hits = []
    for idx, s in enumerate(sentences, start=1):
        m = NUANCE_RE.search(s)
        if not m or _explains_complexity(s):
            continue
        # A complexity claim may legitimately open a short explanation rather
        # than discharge itself in the same sentence. Inspect the next two
        # sentences for an explicit explanatory marker before filing the proxy;
        # B7 targets complexity claimed and abandoned, not a signposted setup.
        continuation = " ".join(sentences[idx : idx + 2])
        if continuation and _explains_complexity(continuation):
            continue
        hits.append({
            "sentence": idx,
            "match": m.group(0),
            "text": s[:130],
        })
    return hits


def findings_for(name: str, stats: dict, baseline: dict | None) -> list[dict]:
    out: list[dict] = []
    grounded = baseline is not None and baseline.get("sufficient")

    if stats.get("sufficient"):
        # B4/B5 fire only as a within-author delta. See the calibration note at
        # the top of this file: the absolute low-dispersion claim did not
        # replicate, so with no baseline there is nothing defensible to assert.
        if grounded:
            cv, base_cv = stats["cv"], baseline["cv"]
            if base_cv and cv < base_cv * B4_BASELINE_RATIO:
                out.append({
                    "rule": "B4", "severity": "MINOR",
                    "detail": (f"rhythm CV {cv} is below this author's own baseline "
                               f"{base_cv}; the draft is flatter than the author writes"),
                })
            rate, base_rate = stats["interruption_rate"], baseline["interruption_rate"]
            if base_rate and rate < base_rate * B5_BASELINE_RATIO:
                out.append({
                    "rule": "B5", "severity": "MINOR",
                    "detail": (f"pre-predicate interruption rate {rate} below this "
                               f"author's baseline {base_rate}; clause depth flattened. "
                               f"Fix via Bacon sections 5-8: appositives, relative "
                               f"clauses, absolutes"),
                })

    for hit in stats.get("b6_circular", []):
        out.append({
            "rule": "B6", "severity": "MINOR",
            "detail": (f"paragraph {hit['paragraph']} closes on its own opening "
                       f"(content overlap {hit['overlap']}); end with forward "
                       f"momentum instead of restatement"),
        })

    for hit in stats.get("b7_nuance", []):
        out.append({
            "rule": "B7", "severity": "MINOR",
            "detail": (f"sentence {hit['sentence']} claims complexity "
                       f"(\"{hit['match']}\") without discharging it: "
                       f"\"{hit['text']}\""),
        })

    for f in out:
        f["file"] = name
    return out


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--baseline", type=Path, action="append", default=[],
                    help="author's accepted prose; enables C-7 baseline scoring")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    for p in list(args.files) + list(args.baseline):
        if not p.is_file():
            print(f"cannot validate: not a file: {p}", file=sys.stderr)
            return 2

    baseline = None
    try:
        if args.baseline:
            merged = "\n\n".join(read(p) for p in args.baseline)
            baseline = analyse(merged)
            if not baseline.get("sufficient"):
                print(f"warning: baseline too small ({baseline['sentences']} sentences); "
                      f"treating as absent", file=sys.stderr)
                baseline = None

        report = {"baseline_supplied": baseline is not None, "files": {}, "findings": []}
        if baseline:
            report["baseline"] = baseline

        for p in args.files:
            stats = analyse(read(p))
            report["files"][p.as_posix()] = stats
            report["findings"].extend(findings_for(p.as_posix(), stats, baseline))
    except OSError as exc:
        print(f"cannot analyse: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_human(report)

    return 1 if report["findings"] else 0


def _print_human(report: dict) -> None:
    print("## Register dispersion check (B4-B7)")
    print()
    if not report["baseline_supplied"]:
        print("**No author baseline supplied.** B4/B5 are reported as measurements")
        print("only and produce no findings: local calibration found no population")
        print("threshold that separates human from machine prose, and the author's")
        print("own dispersion is the only defensible yardstick (C-7). Pass")
        print("--baseline <accepted prose> to enable B4/B5 findings.")
        print()
    for name, s in report["files"].items():
        print(f"### {name}")
        print(f"- sentences: {s['sentences']}  paragraphs: {s['paragraphs']}")
        if s.get("sufficient"):
            print(f"- mean length: {s['mean_length']}w   stdev: {s['stdev_length']}w")
            print(f"- B4 rhythm CV: {s['cv']}  (range {s['min_length']}-{s['max_length']}w, "
                  f"{s['short_sentences_under_10w']} under 10w)")
            print(f"- B5 interruption rate: {s['interruption_rate']}")
        else:
            print(f"- {s.get('note', 'insufficient sample')}")
        print(f"- B6 circular paragraphs: {len(s.get('b6_circular', []))}")
        print(f"- B7 undischarged complexity claims: {len(s.get('b7_nuance', []))}")
        print()
    if report["findings"]:
        print("### Candidates")
        print()
        print("| Rule | Severity | File | Detail |")
        print("|---|---|---|---|")
        for f in report["findings"]:
            print(f"| {f['rule']} | {f['severity']} | {f['file']} | {f['detail']} |")
    else:
        print("No candidates.")


if __name__ == "__main__":
    sys.exit(main())
