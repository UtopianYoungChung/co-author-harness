#!/usr/bin/env python3
"""Argument-coherence pre-filter: unit inventory and cheap candidate markers.

Two-layer pattern, the same one `DETERMINISTIC_CHECKS.md` sections 9a and 9b use
for SAFEGUARD Checks 7 and 8. This layer surfaces candidates cheaply and supplies
the **coverage denominator** (the prose units a review must cover). It assigns
no severity, reaches no verdict, and every emitted object carries
``judgment: "not_performed"`` so a pre-filter run can never be read as a review.
`references/ARGUMENT_COHERENCE.md` section 1 is the obligation; SAFEGUARD Check 9 is
where a reviewer judges these candidates.

    python scripts/coherence_prefilter.py <file> [--json]

Markers are deliberately lexical and over-inclusive. A marker is not a defect:
a source-status remark that IS used argumentatively matches `source_status`
exactly as loudly as one that is not. Only Check 9 can tell them apart.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA = 'coherence-prefilter/v1'

# A prose unit is a blank-line-separated block that is not a heading, fence,
# list, table, or block quote. Only prose units enter the coverage denominator.
_FENCE = re.compile(r'^(?:```|~~~)')
_HEADING = re.compile(r'^(#{1,6})[ \t]+(\S.*)$')
_LIST = re.compile(r'^[ \t]*(?:[-*+]\s|\d+[.)]\s)')
_TABLE = re.compile(r'^[ \t]*\|')
_QUOTE = re.compile(r'^[ \t]*>')

# Sentence segmentation is load-bearing, and it must never merge two sentences
# silently. A single sentence record may not span a boundary this splitter finds
# unless the record declares that boundary an abbreviation, with a reason
# (`coherence_review.mergeable`). So an over-split costs a reviewer one
# declaration, while an under-split would let one record hold two sentences with
# no declaration at all ("option A. Costs remain high."). Only forms that
# practically never end a sentence are protected: e.g., i.e., cf., vs., pp.,
# Fig., and titles before a name. Anything that can end a sentence -- a single
# capital, "et al.", "Inc.", "No." -- is a boundary, left to the reviewer to
# declare and justify when it is not one.
_ABBREV = (r'(?<!\be\.g)(?<!\bi\.e)(?<!\bcf)(?<!\bvs)(?<!\bpp)(?<!\bFig)'
           r'(?<!\bDr)(?<!\bMr)(?<!\bMrs)(?<!\bMs)(?<!\bProf)')
# Group 1 keeps closing quotes and brackets with the sentence they close, so the
# pieces partition the unit exactly ('He said "stop." Then ...').
_SENTENCE_END = re.compile(_ABBREV + r'([.!?][\"”\')\]]*)\s+(?=[\"“(\[]*[A-Z0-9])')

MARKERS = {
    # A commitment the document owes a method or an evaluation (AC-4).
    'commitment': re.compile(
        r'\b(?:we|i|this\s+(?:paper|study|proposal|thesis|article|chapter)|the\s+(?:proposed|resulting)\s+\w+)'
        r'\s+will\b|\bwill\s+(?:show|demonstrate|deliver|provide|develop|evaluate|produce|build|establish|yield)\b'
        r'|\b(?:we|i)\s+(?:propose|intend|aim)\s+to\b',
        re.I),
    # A remark about the state of the literature, corpus, or method (AC-1).
    'source_status': re.compile(
        r'\b(?:prior|previous|existing|earlier|extant)\s+(?:work|studies|research|literature|accounts)\b'
        r'|\bthe\s+literature\s+(?:is|remains|has)\b'
        r'|\bis\s+(?:largely|mostly|chiefly|primarily)\s+[\w-]+(?:-based|ly\s+\w+)?\b'
        r'|\bremains?\s+(?:untested|unvalidated|scarce|limited|contested|underexplored)\b',
        re.I),
    # An explicit or implicit re-specification of a term already in use (AC-3).
    'meaning_change': re.compile(
        r'\bas\s+used\s+here\b|\bas\s+(?:we|i)\s+use\s+(?:it|them|the\s+term)\s+here\b'
        r'|\bin\s+(?:this|the\s+present)\s+(?:paper|study|proposal|section|sense)\s*,?\s*'
        r'(?:means|we\s+mean)\b'
        r'|\b(?:we|i)\s+(?:now\s+)?(?:use|treat|define|take)\b[^.]{0,60}\bto\s+mean\b'
        r'|\b(?:earlier|previously|above)\s+(?:we|i)\s+(?:treated|used|defined|called)\b'
        r'|\b(?:by|on)\s+\w+\s+(?:we|i)\s+mean\b',
        re.I),
    # A plain definition. `meaning_change` catches marked re-specifications; this
    # catches the unmarked "A case means one trip", whose revision can silently
    # change every later use of the term (AC-3).
    'definition': re.compile(
        r'\b(?:means|is\s+defined\s+as|are\s+defined\s+as|refers?\s+to|denotes?|'
        r'is\s+understood\s+as|stands?\s+for|(?:we|i)\s+define)\b',
        re.I),
    # A question the document undertakes to answer (AC-4 when unanswered).
    'question': re.compile(
        r'\?|\bresearch\s+questions?\b|\bRQ\s?\d\b'
        r'|\b(?:we|i|this\s+(?:paper|study|proposal|thesis|article|chapter))\s+'
        r'(?:asks?|examines?\s+whether|investigates?\s+whether)\b',
        re.I),
    # An inferential bridge: its premises must be adjacent and on the page.
    'inferential_bridge': re.compile(
        r'(?:^|(?<=[.;:]\s))\s*(?:therefore|thus|hence|consequently|accordingly|it\s+follows\s+that)\b'
        r'|\b(?:therefore|thus|hence|consequently)\b',
        re.I),
    # A named artefact the document may or may not carry downstream (AC-4).
    'deliverable': re.compile(
        r'\b(?:instrument|framework|toolkit|taxonomy|protocol|guideline|artefact|artifact|method|'
        r'model|procedure|checklist|apparatus)s?\b',
        re.I),
}

# Markers whose unit states something the rest of the document owes or depends
# on: a promise, a definition or re-definition, a question. A review must assess
# each such unit in its required scope explicitly (`coherence_review`
# COHERENCE-COMMITMENT-UNCHECKED). `deliverable` stays advisory: it matches any
# mention of a method or a model, and a promised deliverable is already caught
# by `commitment` ("will deliver", "will provide", "will develop").
COMMITMENT_MARKERS = ('commitment', 'definition', 'meaning_change', 'question')

# Headings under which a commitment is normally discharged. Absence is a
# candidate for AC-4, never a finding: a document may discharge a commitment in
# prose under a heading this list does not name.
_PAYOFF_HEADING = re.compile(
    r'\b(?:method|methodology|methods|design|evaluation|validation|analysis|'
    r'procedure|study|experiment|results?|instrument)\b', re.I)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized(text: str) -> str:
    return ' '.join(text.split())


def split_sentences(text: str) -> list[str]:
    """Advisory segmentation; see the module docstring."""
    flat = normalized(text)
    if not flat:
        return []
    parts, start = [], 0
    for match in _SENTENCE_END.finditer(flat):
        parts.append(flat[start:match.end(1)].strip())
        start = match.end()
    tail = flat[start:].strip()
    if tail:
        parts.append(tail)
    return [p for p in parts if p]


def _classify(block: str) -> str:
    first = block.lstrip('\n').split('\n', 1)[0]
    if _HEADING.match(first):
        return 'heading'
    if _FENCE.match(first.lstrip()):
        return 'fence'
    if _TABLE.match(first):
        return 'table'
    if _LIST.match(first):
        return 'list'
    if _QUOTE.match(first):
        return 'quote'
    return 'prose'


def inventory(text: str) -> dict:
    """Prose-unit inventory plus candidate markers. No verdict is reached."""
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    units: list[dict] = []
    heading_path: list[str] = []
    headings: list[dict] = []
    in_fence = False
    block: list[str] = []
    block_start = 1
    index = 0

    def flush(end_line: int) -> None:
        nonlocal block, index
        raw = '\n'.join(block).strip('\n')
        block = []
        if not raw.strip():
            return
        kind = _classify(raw)
        if kind != 'prose':
            return
        sentences = split_sentences(raw)
        units.append({
            'unit_id': f'u{index:03d}',
            'kind': 'prose',
            'line': block_start,
            'end_line': end_line,
            'heading_path': list(heading_path),
            'sha256': digest(raw.encode('utf-8')),
            'chars': len(raw),
            'sentence_count_advisory': len(sentences),
            'markers': sorted({name for name, pattern in MARKERS.items()
                               if pattern.search(raw)}),
            'text': raw,
        })
        index += 1

    for number, line in enumerate(lines, start=1):
        if _FENCE.match(line.lstrip()):
            in_fence = not in_fence
            block.append(line)
            continue
        if in_fence:
            block.append(line)
            continue
        heading = _HEADING.match(line)
        if heading:
            flush(number - 1)
            level, title = len(heading.group(1)), heading.group(2).strip()
            del heading_path[level - 1:]
            heading_path.append(title)
            headings.append({'line': number, 'level': level, 'title': title,
                             'payoff_candidate': bool(_PAYOFF_HEADING.search(title))})
            block_start = number + 1
            continue
        if not line.strip():
            flush(number - 1)
            block_start = number + 1
            continue
        if not block:
            block_start = number
        block.append(line)
    flush(len(lines))

    commitments = [
        {'unit_id': unit['unit_id'], 'line': unit['line'], 'sentence': sentence,
         'kinds': kinds}
        for unit in units if set(COMMITMENT_MARKERS) & set(unit['markers'])
        for sentence in split_sentences(unit['text'])
        for kinds in [[name for name in COMMITMENT_MARKERS if MARKERS[name].search(sentence)]]
        if kinds
    ]
    payoff_units = [u for u in units
                    if any(_PAYOFF_HEADING.search(h) for h in u['heading_path'])]
    return {
        'schema': SCHEMA,
        'judgment': 'not_performed',
        'authority': 'references/ARGUMENT_COHERENCE.md',
        'judged_by': 'SAFEGUARD_LAYER.md Check 9',
        'target_sha256': digest(text.encode('utf-8')),
        'units': units,
        'unit_ids': [u['unit_id'] for u in units],
        'coverage_denominator': len(units),
        'headings': headings,
        'has_payoff_heading': any(h['payoff_candidate'] for h in headings),
        'payoff_unit_ids': [u['unit_id'] for u in payoff_units],
        'commitment_candidates': commitments,
        'candidate_unit_ids': [u['unit_id'] for u in units if u['markers']],
        'note': ('Markers are over-inclusive candidates. A matched marker is not a '
                 'defect and an unmatched unit is not cleared; every prose unit in '
                 'scope must still be covered by Check 9.'),
    }


def units_for(text: str) -> list[dict]:
    """Coverage denominator without unit bodies, for evidence validation."""
    return [{k: v for k, v in unit.items() if k != 'text'}
            for unit in inventory(text)['units']]


def changed_unit_ids(before: str, after: str) -> list[str]:
    """Units of `after` that a review must treat as affected by the change.

    Two kinds, returned together in document order:

    * units that are new or altered: inserted, rewritten, or moved here;
    * surviving units that a deletion or a move made newly adjacent. A deleted
      paragraph has no unit in `after`, so the units on either side of the gap
      stand in for it: "Both conditions must hold" is affected when the
      paragraph defining the conditions is removed, even though its own bytes
      did not change.

    Identity comes from an **ordered** alignment of unit hashes, not set
    membership. Set membership misses a repeated paragraph inserted a second
    time, and lets an unrelated edit elsewhere mask a deletion.

    Inside a run of identical paragraphs the bytes cannot say which copy was
    removed or added, and the alignment picks one end of the run. Every
    equivalent position is therefore treated as affected: a unit claiming the
    caveat "appears three times" is required when one of three copies goes,
    wherever the alignment happened to put the gap.
    """
    old = [u['sha256'] for u in inventory(before)['units']]
    new_units = inventory(after)['units']
    new = [u['sha256'] for u in new_units]
    affected: set[int] = set()
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_opcodes():
        if tag in ('replace', 'insert'):
            lo, hi = _slide(new, j1, j2)
            affected.update(range(lo, hi))
        if tag in ('delete', 'replace') and i2 - i1 > j2 - j1:
            # More units left than arrived: every surviving unit that may border
            # the gap, over all equivalent placements of the removed run.
            lo, hi = _slide(old, i1, i2)
            first, last = j1 - (i1 - lo), j2 + (hi - i2)
            affected.update(x for x in range(first - 1, last + 1) if 0 <= x < len(new))
    return [new_units[x]['unit_id'] for x in sorted(affected)]


def _slide(seq: list[str], start: int, stop: int) -> tuple[int, int]:
    """Widest window over which the block seq[start:stop] could equally sit.

    A block that repeats its neighbours can be shifted left while the unit
    before it equals its last unit, and right while the unit after it equals
    its first; each shift is an alignment the bytes cannot rule out.
    """
    lo, hi = start, stop
    while lo > 0 and hi > lo and seq[lo - 1] == seq[hi - 1]:
        lo, hi = lo - 1, hi - 1
    left = lo
    lo, hi = start, stop
    while hi < len(seq) and hi > lo and seq[lo] == seq[hi]:
        lo, hi = lo + 1, hi + 1
    return left, hi


def stub(result: dict) -> str:
    lines = ['### Argument-coherence pre-filter (feeds SAFEGUARD Check 9)',
             f'- Prose units in scope (coverage denominator): {result["coverage_denominator"]}',
             f'- Units carrying candidate markers: {len(result["candidate_unit_ids"])}',
             f'- Commitment sentences: {len(result["commitment_candidates"])}',
             f'- Payoff-candidate heading present: {"yes" if result["has_payoff_heading"] else "no"}']
    for unit in result['units']:
        if unit['markers']:
            lines.append(f'  - {unit["unit_id"]}, line {unit["line"]}: '
                         f'[{", ".join(unit["markers"])}]')
    lines.append('- Judgment: not performed here (Check 9 assigns severity).')
    return '\n'.join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('target', type=Path)
    ap.add_argument('--json', action='store_true', help='emit the full inventory')
    ap.add_argument('--no-text', action='store_true', help='omit unit bodies from --json')
    args = ap.parse_args(argv)
    try:
        text = args.target.read_text(encoding='utf-8-sig')
    except (OSError, UnicodeError) as exc:
        print(json.dumps({'schema': SCHEMA, 'ok': False, 'message': str(exc)}))
        return 2
    result = inventory(text)
    if args.json:
        if args.no_text:
            result = {**result, 'units': [{k: v for k, v in u.items() if k != 'text'}
                                          for u in result['units']]}
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(stub(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
