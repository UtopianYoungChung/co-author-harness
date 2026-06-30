"""Craft-layer auditor -- concision and copyedit checks the style suite lacked.

Adds the prose-craft checks specified in
reference/writing-style-craft-architecture.md §8 (the Zinsser/Strunk/Penguin
tier) and mirrored in reference/style_lint.py: the `-ly` adverb hyphen (the
grammar-pass postmortem miss), filler phrases, hedge-qualifier density,
nominalization density, doubled words, and it's/its'. It does NOT duplicate
audit_style's em-dash, sentence-length, or voice checks.

All findings fire at severity=default (craft is advisory; dense or long prose
can pass after human judgment). Keep the LY_NONADVERB list and pattern set in
sync with reference/style_lint.py; the architecture doc §8 is the spec of record.

C-7 contract (voice-fingerprint preservation; see references/STYLE_COMMITMENTS.md
§1.0c and references/voice_preservation_guidelines.md). This auditor is
deterministic and therefore *cannot establish an author baseline*; it must not
decide what is idiolect and must not suppress findings on "voice" grounds. Its
output is a set of **candidates subject to C-7 review**, never defects on their
own. The judgment-sensitive checks here (CRAFT-DUP doubled words, which may be
deliberate repetition; CRAFT-NOM nominalization density and CRAFT-HEDGE qualifier
density, which may be register/voice) are the ones a C-7 baseline read most often
reclasses as disciplined idiolect. Consumers must keep these advisory: do NOT
hard-gate on craft findings (or on audit_style's sentence-length / passive / voice
findings) without a baseline read. The mechanical copyedit checks (CRAFT-LY,
CRAFT-ITS its', CRAFT-FILLER) sit on the mechanics layer and remain ordinary
copyedit candidates.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

from schema import Finding, locator_for
from audit_style import _mask_preserving_offsets, WORD_RE

RULE = "writing-style-craft-architecture.md#§8"
NOM_DENSITY = 0.09
QUAL_PER100 = 1.0

# -ly words that are NOT adverbs (legit compounds: family-owned, friendly-looking)
LY_NONADVERB = set("""family friendly early only holy ugly lovely lonely likely lively costly deadly
daily weekly monthly yearly quarterly orderly elderly scholarly worldly timely kindly curly silly jolly
manly womanly motherly fatherly brotherly sisterly neighborly cowardly miserly homely comely ghostly
ghastly grisly princely saintly stately courtly knightly earthly heavenly deathly sickly prickly wrinkly
wobbly measly beastly oily wily assembly supply apply reply rely ally rally tally folly bully jelly belly
roly anomaly homily melancholy""".split())
QUALIFIERS = ["very","rather","quite","somewhat","fairly","really","actually","basically",
              "virtually","essentially","pretty","simply","clearly","obviously"]
FILLERS = ["in order to","due to the fact that","the fact that","in terms of",
           "it should be noted that","for the purpose of","in the event that","with regard to",
           "at this point in time","a number of","in a timely manner","needless to say"]

LY_RE  = re.compile(r"\b([A-Za-z]+ly)-[A-Za-z]+")
ITSP_RE = re.compile(r"\bits'\b")
ITSC_RE = re.compile(r"\bit's\b")
DUP_RE = re.compile(r"\b(\w+)\s+\1\b", re.IGNORECASE)
NOM_RE = re.compile(r"\b\w{4,}(?:tion|ment|ance|ence|ity|ness)\b", re.IGNORECASE)


def _line(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def audit_craft(text: str, target: Path) -> List[Finding]:
    findings: List[Finding] = []
    cleaned = _mask_preserving_offsets(text)
    low = cleaned.lower()

    for m in LY_RE.finditer(cleaned):
        if m.group(1).lower() not in LY_NONADVERB:
            findings.append(Finding("CRAFT-LY", "style", "default",
                locator_for(target, _line(text, m.start())), m.group(0), RULE))
    for m in ITSP_RE.finditer(cleaned):
        findings.append(Finding("CRAFT-ITS", "style", "default",
            locator_for(target, _line(text, m.start())), "its' (never valid)", RULE))
    for m in ITSC_RE.finditer(cleaned):
        findings.append(Finding("CRAFT-ITS", "style", "default",
            locator_for(target, _line(text, m.start())), "it's contraction (verify it is/has)", RULE, True))
    for m in DUP_RE.finditer(cleaned):
        findings.append(Finding("CRAFT-DUP", "style", "default",
            locator_for(target, _line(text, m.start())), m.group(0), RULE))
    for ph in FILLERS:
        start = 0
        while True:
            i = low.find(ph, start)
            if i < 0:
                break
            findings.append(Finding("CRAFT-FILLER", "economy", "default",
                locator_for(target, _line(text, i)), ph, RULE))
            start = i + len(ph)

    nwords = max(1, len(WORD_RE.findall(cleaned)))
    nom = len(NOM_RE.findall(cleaned))
    if nom / nwords > NOM_DENSITY:
        findings.append(Finding("CRAFT-NOM", "economy", "default",
            locator_for(target, 1), "%.1f%% nominalizations (verbs may be hiding)" % (nom/nwords*100), RULE, True))
    qc = 0
    for q in QUALIFIERS:
        for m in re.finditer(r"\b"+re.escape(q)+r"\b", low):
            if q == "rather" and low[m.end():m.end()+5] == " than":
                continue
            qc += 1
    if qc / nwords * 100 > QUAL_PER100:
        findings.append(Finding("CRAFT-HEDGE", "economy", "default",
            locator_for(target, 1), "%d hedge qualifiers (%.1f/100w)" % (qc, qc/nwords*100), RULE, True))
    return findings
