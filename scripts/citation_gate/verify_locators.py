#!/usr/bin/env python
"""verify_locators.py - quote-bound citation/claim verification gate.

A claim element is supported only by a verbatim quote that this script finds on the
stated printed page. Judgment (does the quote entail the claim?) is never silent: any
class other than VERBATIM must carry a written bridge, and a load-bearing claim term
missing from the quote forces MAPPED/EXTENDED. Prints conclusions only.

Per check: claim_text (the claim element's exact words in the citing text; key terms are DERIVED from it, not
chosen), optional inflections{term:[forms]}, dropped_terms{term:reason}; VERBATIM also needs modality_scope.
key_terms remains as the load-bearing subset whose absence forces MAPPED/EXTENDED.

exit:  0 clean, 1 failures/unsupported/uncovered, 3 GATE_UNAVAILABLE (PyMuPDF missing)

usage: python verify_locators.py checks.json [--verbose] [--legacy] [--citing-document PATH]
  --legacy           accept pre-amendment checks without claim_text; their classes are unpoliced
  --citing-document  bind the result to the text being gated (Rule 3 item 14). Defaults to
                     citing_document.path in the checks file. The run FAILS if that document's
                     sha256 differs from citing_document.sha256, or if a check's claim_text is
                     not in it; cited sentences no check covers are reported UNCOVERED.
                     Without a citing document a checks file that binds proves nothing about
                     any manuscript: the same evidence clears any text placed beside it.
"""
import sys, json, re, os, hashlib, unicodedata, io
try:                                   # reconfigure, never replace: an orphaned wrapper
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # closes the caller's buffer
except (AttributeError, ValueError):   # not a TextIOWrapper, e.g. under a test harness
    pass
CLASSES = ["VERBATIM", "PARAPHRASE", "MAPPED", "EXTENDED"]   # strongest -> weakest


class GateUnavailable(RuntimeError):
    """The gate cannot run here at all. An environment fault, not a verdict about citations.

    Reported as GATE_UNAVAILABLE and exit 3 so a caller can tell it apart from a crash: a
    crash means the evidence was not examined and must block, while this means the checker's
    machine cannot examine it and the citations simply stay unverified.
    """

# Overridable so a reviewer can isolate the cache instead of writing into the user's own.
# The pass-3 reviewer had to recover records they created here because the path was fixed.
CACHE = os.environ.get("LOCATOR_CACHE") or os.path.join(
    os.path.expanduser("~"), ".claude", "cache", "locator-text")

def norm(s):
    s = unicodedata.normalize("NFKD", s).replace("\u00ad", "").lower()
    return re.sub(r"[^a-z0-9]", "", s)

def pages_of(pdf):
    """{"sha256", "pages" (normalised), "raw"}, bound to the exact bytes they were read from.

    The raw text is kept because a printed folio can only be found in it: norm() strips the
    line structure that tells a header or footer from the body.

    The cache was keyed on path, size and modification time, so a source replaced by
    different bytes of the same length at the same timestamp served the OLD text and the gate
    bound a quote that is no longer in the file (2026-09-21 review, F5-05). The bytes are now
    read once, hashed, and parsed from memory, so the key, the stored record and the text all
    describe one snapshot and nothing can change between hashing and reading.
    """
    with open(pdf, "rb") as fh:
        data = fh.read()
    digest = hashlib.sha256(data).hexdigest()
    os.makedirs(CACHE, exist_ok=True)
    cp = os.path.join(CACHE, digest + ".json")
    if os.path.exists(cp):
        try:
            with open(cp, encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            rec = None
        # A record names the bytes it came from; anything else is ignored and re-extracted.
        if isinstance(rec, dict) and rec.get("sha256") == digest and "raw" in rec:
            return rec
    try:
        import fitz
    except ImportError:
        raise GateUnavailable(
            "PyMuPDF (fitz) is not installed, so no page text can be read and no quote can "
            "be bound. Install it with: pip install pymupdf")
    d = fitz.open(stream=data, filetype="pdf")
    raw = [d[i].get_text() for i in range(d.page_count)]
    d.close()
    out = {"sha256": digest, "pages": [norm(t) for t in raw], "raw": raw}
    with open(cp, "w", encoding="utf-8") as fh:
        json.dump(out, fh)
    return out

MIN_FOLIO_PAGES = 3      # pages that must show a number at their edge before an offset can
FOLIO_AGREEMENT = 0.6    # be confirmed, and the share of those that must agree with it


# What may count as a printed folio. Any number in the edge window was enough, so the headings
# "Section 11 / 12 / 13" on a source printing 1, 2, 3 confirmed a declared offset of +10 and
# the tool announced "offset +10 confirmed on 3/3 pages" (2026-09-21 review, F6-01). A number
# a labelling word owns is that label's number, not the page's.
FOLIO_LABEL_RE = re.compile(
    r"\b(?:sections?|secs?|chapters?|chaps?|ch|parts?|figures?|figs?|tables?|tabs?|appendix|"
    r"appendices|apps?|volumes?|vols?|numbers?|nos?|issues?|articles?|arts?|items?|steps?|"
    r"lines?|notes?|equations?|eqs?|paragraphs?|paras?|exhibits?|box|boxes|panels?|slides?|"
    r"rules?|footnotes?|versions?|editions?|eds?|weeks?|days?|phases?|levels?|rounds?)"
    r"\.?\s*(?:nos?\.?\s*)?$", re.I)
EDGE_NUMBER_RE = re.compile(r"(?<!\d)(\d{1,4})(?!\d)")
# Wide enough to hold a running foot with the folio in it. At 70 the folio of a journal
# that prints "1673 ... pp. 1672-1694, (c) 2023 INFORMS" or a Scientific Reports DOI line
# falls outside the window and the page states no number at all; measured over every live
# source, 160 loses none and recovers two (2026-09-21, re-gating the manuscript).
EDGE_CHARS = 160         # of the flattened page, at each end: its running head and its footer
BARE_FOLIO_RE = re.compile(r"^[\[(]?\s*(\d{1,4})\s*[\])]?$")
FOLIO_ZONE_LINES = 3     # the running head and foot: where a page prints its own number


def edge_numbers(raw_text):
    """Numbers printed at a page's edge that could be its folio. Loose, deliberately.

    Shared verbatim with the sibling tool; the test asserts the two implementations agree.
    """
    flat = re.sub(r"\s+", " ", raw_text or "")
    out = []
    for m in EDGE_NUMBER_RE.finditer(flat):
        if m.start() >= EDGE_CHARS and m.end() <= len(flat) - EDGE_CHARS:
            continue                             # body text, not the page's edge
        if FOLIO_LABEL_RE.search(flat[max(0, m.start() - 24):m.start()]):
            continue                             # that label's number, not the page's
        out.append(int(m.group(1)))
    return out


def printed_folios(raw_pages):
    """Per page, the folio the page itself prints, on the strict rule: a line whose whole
    content is a number, whose value appears on one page only.

    Loose evidence may confirm a declared offset; only this may refute one. Measured on the
    live sources, the loose rule refuses five correct checks -- jergas p.1 and greenberg p.1
    read their submission dates and DOI, cope reads the date its HTML rendering was taken --
    and without the uniqueness guard holldack2026's bare "5", printed on both p.6 and p.8,
    refuses five more. A folio is unique to its page; a number repeated across pages is a
    label (2026-09-21 review, F6-02).

    Only the running head and foot are read. This rule used to scan every line, so a body
    table cell -- a standalone "99" under "Sample count" -- refused a correct p.3 citation as
    a contradicted locator (2026-09-21 review, F7-05). The confirming rule reads a page's
    edges; a rule that may overrule it cannot read more of the page than it does.
    """
    per, seen = [], {}
    for text in raw_pages or []:
        page = set()
        lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
        for line in lines[:FOLIO_ZONE_LINES] + lines[-FOLIO_ZONE_LINES:]:
            m = BARE_FOLIO_RE.match(line)
            if m:
                page.add(int(m.group(1)))
        for n in page:
            seen[n] = seen.get(n, 0) + 1
        per.append(page)
    return [{n for n in page if seen[n] == 1} for page in per]
def folio_evidence(raw_pages):
    """Per page, the numbers the page itself states: its edge numbers and any "page N of M"."""
    per = []
    for text in raw_pages or []:
        flat = re.sub(r"\s+", " ", text or "")
        nums = set(edge_numbers(text))
        m = re.search(r"\bpage (\d+) of \d+", flat, re.I)
        if m:
            nums.add(int(m.group(1)))
        per.append(nums)
    return per


def supported_offsets(raw_pages):
    """(offsets the source's own numbers support, pages that state a number, the floor).

    A source that supports more than one offset has ambiguous pagination: a page states at
    most one folio, so two arithmetic runs mean the numbers are not all folios and the gate
    cannot tell which are (2026-09-21 review, F7-03). This replaces arguing about vocabulary;
    "Experiment 11/12/13" printed over folios 1/2/3 supports +10 and +0 and now confirms
    neither.
    """
    per = folio_evidence(raw_pages)
    stating = [i for i, nums in enumerate(per) if nums]
    floor = min(MIN_FOLIO_PAGES, len([t for t in (raw_pages or []) if t.strip()])) or 1
    out = []
    for off in sorted({n - (i + 1) for i in stating for n in per[i]}):
        agree = sum(1 for i in stating if (i + 1 + off) in per[i])
        # An offset competes only if it reaches the bar confirmation itself has to clear: the
        # floor AND the agreement share. Dropping the share made allea support 9 offsets and
        # cfr93 support 63, because a 160-character edge window on a real page holds
        # citations, years and DOIs, and coincidental agreement on two pages is ordinary.
        # The max(2, ...) is what a one-page source needs: with a floor of one, every number
        # on its only page would otherwise support an offset of its own.
        if agree >= max(2, floor) and agree / len(stating) >= FOLIO_AGREEMENT:
            out.append((off, agree))
    return out, stating, floor


def offset_confirmed(raw_pages, offset):
    """(confirmed, agreeing, pages that state a number, why not) for a declared page offset.

    Rule 3 item 9c asks which pagination a locator uses. The gate took the answer from the
    checks file and never required it to hold: a source printing 1, 2, 3 with an offset of 10
    declared bound a citation to p. 11 and exited 0 (2026-09-21 sweep, S1).

    The evidence is the same the validator's 9c screen uses -- a number in the page's edge
    window -- deliberately, and not the stricter bare-number-line rule used to REFUTE a
    declared page. Confirming a declared offset and refuting one need different thresholds:
    measured across the live sources, the strict rule reads no folio at all on four documents
    whose pagination 9c confirms at 19/20, 14/14 and 14/15, because their folios share a line
    with a running head.
    """
    supported, stating, floor = supported_offsets(raw_pages)
    per = folio_evidence(raw_pages)
    hit = sum(1 for i in stating if (i + 1 + offset) in per[i])
    if not stating:
        return False, 0, 0, "no page of it states a readable number"
    if len(supported) > 1:
        return (False, hit, len(stating),
                "its own numbers support " + str(len(supported)) + " different offsets ("
                + ", ".join(f"{o:+d}" for o, _ in supported[:4]) + "), so which of them is "
                "the printed pagination cannot be told from the source")
    if supported and supported[0][0] != offset:
        return (False, hit, len(stating),
                f"the pages that state a number agree on an offset of {supported[0][0]:+d}, "
                f"not {offset:+d}")
    if hit < floor or hit / len(stating) < FOLIO_AGREEMENT:
        return (False, hit, len(stating),
                f"only {hit} of {len(stating)} pages that state a number agree with it, and "
                f"a confirmed pagination needs {floor}")
    return True, hit, len(stating), ""


WEB_RENDERING = "web_rendering"   # an HTML page printed to PDF: the pages are the printer's


def web_locator(check, source):
    """(problems, render page) for a check into a web rendering.

    A web page prints no page numbers, so a page is not a locator for it and the gate does not
    ask the source to confirm one. What it does have is its sections, so that is what a check
    must name: the section has to be in the source and has to open at or before the quote.
    The quote is sought in the whole rendering, because which printed page a browser put it on
    is a fact about the printer (2026-09-21, the three COPE checks).
    """
    q = norm(check["quote"])
    doc, page_of = "", []
    for i, page in enumerate(source["pages"]):
        doc += page
        page_of += [i] * len(page)
    hits = [m.start() for m in re.finditer(re.escape(q), doc)]
    if not hits:
        return ["QUOTE_NOT_FOUND anywhere in source (fabricated or mistyped)"], None
    at = hits[0]
    render_page = page_of[at] + 1
    section = (check.get("section") or "").strip()
    if not norm(section):
        return ([f"UNLOCATED: {check['source']} is a web rendering and prints no page numbers, "
                 f"so p.{check.get('page')} names a page of the printout, not of the source. "
                 "Declare the section the quote sits in (Rule 3 item 8)"], render_page)
    opens = [m.start() for m in re.finditer(re.escape(norm(section)), doc)]
    if not opens:
        return ([f"SECTION_NOT_FOUND: no section {section!r} in {check['source']}"], render_page)
    # Any occurrence of the quote that follows any occurrence of the section name. Taking
    # the first of each refused a sentence that appears in the Abstract and again in the cited
    # Methods section, on the Abstract copy, while the Methods copy sat there unexamined
    # (2026-09-21 review, F7-06).
    #
    # This is not containment, and does not pretend to be: F7-02 showed the named section need
    # not hold the quote at all -- a section heading occurring anywhere earlier is enough --
    # and that finding is open. Anything here that reads like a membership test is wrong.
    after = [h for h in hits if min(opens) <= h]
    if not after:
        return ([f"SECTION_AFTER_QUOTE: every occurrence of the quoted passage precedes "
                 f"{section!r}, so the quote is not in that section"], render_page)
    return [], page_of[after[0]] + 1


def term_ok(term, text):            # "a|b" = alternatives
    return any(norm(t) in text for t in term.split("|"))

# Rule 3 item 1 (amended 2026-09-19): key terms are derived from the claim's own words, not chosen.
STOP = set("""a an the and or but nor so yet for of in on at to from by with without within into onto over under between among
across through during before after above below up down out off about against as than then that this these those there here
it its they them their theirs he she his her hers him we us our ours you your yours i me my mine who whom whose which what
when where why how is are was were be been being am do does did doing done have has had having can could may might must
shall should will would not no nor only also too very more most less least such each every any some all both either neither
other another same own just even still ever never always often if while because since although though unless until whether
et al pp p vs via per one two""".split())

# Negation, modality and quantifier scope. Every one of these is in STOP, so none of them
# survives derive_terms: a claim and its own negation derive identical terms. Rule 3 item 6
# requires modality and scope to be checked, so they are read separately here rather than
# being silently dropped with the function words (2026-09-20 review, finding G4).
NEGATION_RE = re.compile(
    r"\b(?:not|never|no|none|neither|nor|cannot|without|unable|unlikely|fails?\s+to|"
    r"rather\s+than|instead\s+of)\b|n\u2019t\b|n't\b", re.I)
MODALITY_RE = re.compile(
    r"\b(?:may|might|must|should|shall|would|could|can|will|always|often|sometimes|rarely|"
    r"seldom|all|every|each|any|most|likely|possibly|potentially|generally|typically|"
    r"usually|necessarily|merely|only)\b", re.I)


def claim_markers(text):
    """The negation, modality and scope markers a piece of text carries."""
    found = set()
    for rx in (NEGATION_RE, MODALITY_RE):
        for m in rx.finditer(text or ""):
            found.add(re.sub(r"\s+", " ", m.group(0)).strip().lower())
    return sorted(found)


# For the class check the question is not whether the two texts use the same words but
# whether the claim says something STRONGER than the quote. Measured over the 54 live checks,
# comparing marker sets fired 14 times and was wrong 11 times: "no reference cites" against
# "none of the references cite" is one negation in two spellings, "one fourth of all
# references" is a quantifier inside a noun phrase, and a claim that drops the quote's
# "should" is weaker than its source, not stronger. Only these three differences survive.
HEDGE_RE = re.compile(
    r"\b(?:may|might|can|could|would|possibly|potentially|perhaps|likely|unlikely|often|"
    r"sometimes|rarely|seldom|generally|typically|usually|appears?|seems?|suggests?)\b", re.I)
STRENGTHENER_RE = re.compile(
    r"\b(?:must|always|necessarily|invariably|certainly|entirely|all|every|each|any)\b", re.I)


# Prescription and description are different kinds of claim, not two strengths of one.
# Repair (k) left deontic modals out of the comparison on the reasoning that a claim dropping
# the quote's "should" is WEAKER than its source and so over-claims nothing. That was wrong:
# "participants should share resources" and "participants share resources" are not the same
# assertion at two strengths, and the second does not follow from the first at any strength.
# The gate certified the second as VERBATIM against the first at 5/5 derived terms
# (2026-09-20 review, F6).
DEONTIC_RE = re.compile(
    r"\b(?:should|shall|must|ought\s+to|needs?\s+to|has\s+to|have\s+to|"
    r"(?:is|are|was|were)\s+(?:required|expected|obliged|advised)\s+to|"
    r"recommends?|recommended|mandates?|mandated|requires\s+that)\b", re.I)


def prescriptive(text):
    """Does this text say what ought to happen, rather than what does?"""
    return bool(DEONTIC_RE.search(text or ""))


def _hits(rx, text):
    return sorted({re.sub(r"\s+", " ", m.group(0)).strip().lower() for m in rx.finditer(text or "")})


def negated(text):
    return bool(NEGATION_RE.search(text or ""))


def marker_delta(claim_text, quote):
    """Ways the claim asserts more than its quote does. [] when it does not.

    Three, each one-directional:
      - one text negates and the other does not, either way round;
      - the quote hedges and the claim states it flatly;
      - the claim strengthens or universalises where the quote does not.
    A claim that is weaker than its quote is not flagged: it over-claims nothing.
    """
    problems = []
    if negated(claim_text) != negated(quote):
        which = "claim" if negated(claim_text) else "quote"
        problems.append(f"the {which} negates and the other does not")
    hedges = [h for h in _hits(HEDGE_RE, quote) if h not in _hits(HEDGE_RE, claim_text)]
    if hedges and not _hits(HEDGE_RE, claim_text) and not negated(quote):
        problems.append("the quote hedges with " + ", ".join(hedges)
                        + " and the claim states it flatly")
    added = [t for t in _hits(STRENGTHENER_RE, claim_text)
             if t not in _hits(STRENGTHENER_RE, quote)]
    if added:
        problems.append("the claim strengthens with " + ", ".join(added)
                        + ", which the quote does not say")
    return problems


def derive_terms(claim_text):
    """Content words of the claim element: everything that is not a function word. No chooser."""
    out = []
    for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9’'\-]*", claim_text):
        acronym = len(w) == 2 and w.isupper()            # "AI", "RE", "IS": a named entity, not a function word
        w = re.sub(r"(’|')s$", "", w).strip("-'’").lower()
        if not w or w in STOP or (len(w) < 3 and not w.isdigit() and not acronym) or w in out:
            continue
        out.append(w)
    return out

def present(term, q, raw):
    """short terms (acronyms, numbers) need word boundaries in the quote as written: 'ai' must not match 'maintain'."""
    if len(norm(term)) <= 3:
        return bool(re.search(r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])", raw))
    return norm(term) in q

def coverage(c, q):
    """(derived, missing, dropped) for a check; a term is present as itself or as a LISTED inflection."""
    derived = derive_terms(c.get("claim_text", ""))
    dropped = {k.lower(): v for k, v in (c.get("dropped_terms") or {}).items()}
    infl = {k.lower(): v for k, v in (c.get("inflections") or {}).items()}
    missing, raw = [], c.get("quote", "").lower()
    for t in derived:
        if t in dropped:
            continue
        if present(t, q, raw) or any(present(v, q, raw) for v in infl.get(t, [])):
            continue
        missing.append(t)
    return derived, missing, dropped

# Must admit every form the harness auditor's SOURCE_CITATION_RE admits, or a citation can be
# invisible to the coverage inventory while the auditor treats the document as cited.
CITATION_RE = re.compile(
    r"\([^()\n]*?(?:\b(?:1[89]|20)\d\d[a-z]?\b|\bn\.\s?d\.)[^()\n]*?\)"
    r"|\[\d{1,3}(?:\s*[,\u2013-]\s*\d{1,3})*\]"
    r"|\\cite[tp]?\*?\{[^}]*\}")
CITED_SENTENCE_RE = CITATION_RE
# A citation governs the clauses before it. Splitting on coordination is how "and all
# autonomous systems are always safe" stops hiding behind a checked first clause.
CLAUSE_SPLIT_RE = re.compile(
    r";|(?<=[a-z0-9\)\u201d])\s*,?\s+(?:and|but|while|whereas|although|though|yet)\s+")
PAGE_IN_CITATION_RE = re.compile(
    r"\b(?:pp?\.|pages?|slides?|\u00a7)\s*([0-9]+)(?:\s*[\u2013-]\s*([0-9]+))?", re.I)
# The suffix is what tells 2026a from 2026b, so it belongs to the token. Capturing only the
# digits made a "2026b" citation resolve to a "2026" source, and a "2026a" citation fail
# against a "2026a" source (2026-09-20 review, finding G5).
CITE_YEAR_RE = re.compile(r"\b((?:1[89]|20)\d\d[a-z]?)\b|(n\.\s?d\.)")
FAMILY_RE = re.compile(r"\b([A-Z][A-Za-z\u00c0-\u017f'\u2019\-]{1,})\b")
BIB_HEADING_RE = re.compile(r"^#{1,6}\s+(?:Bibliography|References|Works Cited)\s*$", re.I)
# "Tester (2026, p. 1) states: ..." names its work as plainly as "(Tester, 2026, p. 1)" does.
# The parenthesis holds no family name, so the citation resolved to nothing at all (G6).
NARRATIVE_AUTHOR_RE = re.compile(
    r"([A-Z][A-Za-z\u00c0-\u017f'\u2019\-]+"
    r"(?:\s+(?:et\s+al\.?|and|&)\s+[A-Z][A-Za-z\u00c0-\u017f'\u2019\-]+)*)"
    # An author cited in the possessive is still the author. Without this, "Ratto et al.'s
    # (2026, pp. 3-6)" matched nothing and the citation was reported as naming no source,
    # which reads as the author's error rather than the tool's (2026-09-21, three live
    # citations of the re-gated manuscript).
    r"(?:\s+et\s+al\.?)?(?:['\u2019]s)?\s*$")
POSSESSIVE_RE = re.compile(r"['\u2019]s$")
# A citation's own attribution is not a claim element. This is a named, closed list, not a
# length threshold: everything that is not the cited author or a reporting verb is reported.
REPORTING_VERBS = frozenset("""show shows showed state states stated argue argues argued note
notes noted find finds found observe observes observed suggest suggests suggested report
reports reported write writes wrote claim claims claimed contend contends contended conclude
concludes concluded demonstrate demonstrates demonstrated explain explains explained describe
describes described maintain maintains emphasise emphasises emphasize emphasizes""".split())


# An attribution is identified by where it stands, not by the words in it. Exempting every
# residual word that happens to be in REPORTING_VERBS cleared "... and write (Tester, 2026)",
# where "write" is a second predicate about the participants and no attribution at all
# (2026-09-20 review, F5). The exemption now applies to one span: the reporting clause
# immediately following a NARRATIVE citation, which is the only place a citation's own
# attribution can sit. A parenthetical citation is its own attribution and exempts nothing.
ATTRIBUTION_TAIL_RE = re.compile(
    r"^\s*[,;]?\s*(?:who|which)?\s*(?:" + "|".join(sorted(REPORTING_VERBS)) +
    r")\b\s*(?:that\b|:)?\s*", re.I)


def narrative_attribution(text_before):
    """(author name, where it starts in text_before) for a narrative citation, else (None, None)."""
    m = NARRATIVE_AUTHOR_RE.search((text_before or "").rstrip())
    if not m:
        return (None, None)
    # "Yu's" is matched whole by the name pattern, so the possessive comes off here rather
    # than in the pattern; the offset is the name's either way.
    return POSSESSIVE_RE.sub("", m.group(1)), m.start(1)


def narrative_author(text_before):
    """The author name standing immediately before a parenthetical citation, if any."""
    return narrative_attribution(text_before)[0]


BIB_ENTRY_RE = re.compile(r"^\s*[\[(]?(\d{1,3})[\]).]\s+(.+)$")


TITLE_TOKEN_RE = re.compile(r"[a-z0-9]+")


def title_tokens(text):
    """A title as words: case-folded, "&" read as "and", punctuation dropped, order kept."""
    flat = unicodedata.normalize("NFKD", text or "").replace("\u00ad", "").lower()
    return TITLE_TOKEN_RE.findall(flat.replace("&", " and "))


def title_parts_absent(title, entry):
    """[] if the entry contains the declared title as one contiguous run of words, else what
    is missing.

    Every word counts, including the function words a term derivation drops: "without" is
    what distinguishes the work from the one the entry names. Whole words only, so "stable"
    is not found inside "unstable". Punctuation is dropped rather than parsed, so an entry
    that writes a subtitle after a dash matches one declared after a colon.

    The title used to be split at its colons, with each part asked to occur SOMEWHERE in the
    entry. That cleared a reversed title, and cleared one whose required subtitle came from
    the journal name (2026-09-21 review, F7-04). A title is a sequence, so it is matched as
    one. An entry that drops a declared subtitle is still reported: a main title alone
    identifies no work.
    """
    want = title_tokens(title)
    if not want:
        return []
    have = title_tokens(entry)
    if any(have[i:i + len(want)] == want for i in range(len(have) - len(want) + 1)):
        return []
    # Name the words the entry does not carry at all; if it carries them all, the fault is
    # their order or their placement, and the report says so instead of listing nothing.
    absent = [w for w in dict.fromkeys(want) if w not in have]
    return absent or [" ".join(want) + " (not in this order, or not as the entry's title)"]


def numbered_bibliography(doc_text):
    """{label: entry text} from the citing document's own numbered reference list.

    Continuation lines are joined: a reference that wraps carries its title on the second
    line as often as the first, and the identity check below needs the whole entry.
    """
    lines = (doc_text or "").split("\n")
    start = next((i for i, l in enumerate(lines) if BIB_HEADING_RE.match(l.strip(" *"))), None)
    if start is None:
        return {}
    out, label = {}, None
    for line in lines[start + 1:]:
        m = BIB_ENTRY_RE.match(line)
        if m:
            label = m.group(1) if m.group(1) not in out else None
            if label:
                out[label] = flat(m.group(2))
        elif label and line.strip():
            out[label] = flat(out[label] + " " + line)
        elif not line.strip():
            label = None
    return out


def check_bib_numbers(cfg, doc_text):
    """The declared numeric mapping must agree with the document's own numbered list.

    `bib_numbers` was taken on the author's word, so a checks file could map [2] to one work
    while the manuscript's bibliography assigned [2] to another, and every check bound to [2]
    would be about the wrong source (finding G2).
    """
    mapping = {str(k): v for k, v in (cfg.get("bib_numbers") or {}).items()}
    if not mapping or doc_text is None:
        return []
    entries = numbered_bibliography(doc_text)
    if not entries:
        return [f"bib_numbers declares {len(mapping)} label(s), but the citing document has no "
                "numbered bibliography to check them against, so the mapping rests on nothing"]
    sources = cfg.get("sources", {})
    problems = []
    for label in sorted(mapping, key=lambda x: int(x) if x.isdigit() else 0):
        key = mapping[label]
        entry = entries.get(label)
        if entry is None:
            problems.append(f"bib_numbers maps [{label}] to {key}, but the document's "
                            f"bibliography has no entry [{label}]")
            continue
        cite = (sources.get(key) or {}).get("cite") or {}
        author = str(cite.get("author", "")).strip()
        year = str(cite.get("year", "")).strip().lower()
        title = str(cite.get("title", "")).strip()
        family = author.split(",")[0].split()[-1].lower() if author else ""
        low = entry.lower()
        missing = []
        if family and family not in low:
            missing.append(f"author {family!r}")
        # The full year token, matched as a token. Stripping the suffix let a check declaring
        # 2026a clear an entry declaring 2026b, and a plain substring let 2026 match inside
        # "2026a" (finding F2).
        if year and year not in {t.lower() for t in
                                 re.findall(r"\b(?:1[89]|20)\d\d[a-z]?\b", entry)}:
            missing.append(f"year {year}")
        # And the work itself. Author and year alone cleared an entry for a different paper by
        # the same author in the same year, which is exactly what a numeric label must
        # distinguish. Compared on the leading run of the title so a dropped subtitle does not
        # fail an otherwise correct entry.
        if title:
            # Content words let "Resource Sharing Without Authority" clear an entry titled
            # "... With Authority" -- both relation words are function words, so neither
            # survived derivation -- and a substring test let "Stable Networks" clear
            # "Unstable Networks" (2026-09-21 review, F6-03). A title is matched as written.
            absent = title_parts_absent(title, entry)
            if absent:
                missing.append(f"title {absent} (declared {title[:44]!r})")
        if missing:
            says = ("does not name its " + missing[0] if len(missing) == 1
                    else "names neither its " + " nor its ".join(missing))
            problems.append(f"bib_numbers maps [{label}] to {key}, but the document's entry "
                            f"[{label}] {says}: {entry[:90]!r}")
    return problems
HAS_CONTENT_RE = re.compile(r"[A-Za-z0-9]")
# A bullet or a numbered item opens its own block. Joining a paragraph's lines is what lets a
# wrapped citation be seen (F5-01), but a list is not a wrapped paragraph: joining one pulled
# the next bullet's prose into the previous bullet's citation scope and reported it uncovered.
# A continuation line of a wrapped item carries no marker and still joins.
LIST_ITEM_RE = re.compile(r"^(?:[-*+]\s|\(?\d{1,3}[.)]\s)")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\[\u201C\"])")


def flat(text):
    return re.sub(r"\s+", " ", text).strip()


def paragraphs(doc_text):
    """[(joined text, [(char offset, source line)])] for each paragraph above the bibliography.

    The lines of a paragraph are joined before anything is looked for in them. A citation may
    wrap past the margin -- "(Tester," on one line and "2026, p. 1)." on the next -- and a
    line-by-line scan cannot see it: the verifier reported ZERO citation occurrences and
    exited 0, so a document whose citations all wrapped looked like a document that cites
    nothing (2026-09-21 review, F5-01). The offsets are kept so a finding still names the line
    it came from.
    """
    lines = doc_text.split("\n")
    stop = next((i for i, l in enumerate(lines) if BIB_HEADING_RE.match(l.strip(" *"))), len(lines))
    out, buf, spans = [], [], []

    def flush():
        if buf:
            out.append((" ".join(buf), list(spans)))
        buf.clear()
        spans.clear()

    for n, line in enumerate(lines[:stop], 1):
        text = line.strip()
        if not text:
            flush()                        # a blank line ends the paragraph, and the scope
            continue
        if text.startswith("#"):
            flush()                        # a heading opens its own scope
            head = text.lstrip("#").strip()
            if head:
                out.append((head, [(0, n)]))
            continue
        if LIST_ITEM_RE.match(text):
            flush()                        # so does each item of a list
        spans.append((sum(len(b) + 1 for b in buf), n))
        buf.append(text)
    flush()
    return out


def line_at(spans, offset):
    """The source line a character offset in a joined paragraph came from."""
    n = spans[0][1] if spans else 1
    for start, line in spans:
        if start > offset:
            break
        n = line
    return n


def cited_sentences(doc_text):
    """(line, sentence, preamble) for every sentence carrying a citation.

    `preamble` is the rest of the same paragraph before that sentence. A citation written on
    its own line has nothing before it there, and an empty scope used to count as a fully
    covered one, so a wholly unchecked claim cleared (2026-09-20 review, finding G3).

    Headings are inventoried rather than skipped. A heading that carries a citation makes a
    cited claim like any other line, and skipping it meant the claim was never looked at.
    """
    out = []
    for text, spans in paragraphs(doc_text):
        para, at = [], 0
        for sent in SENTENCE_SPLIT_RE.split(text):
            if CITED_SENTENCE_RE.search(sent):
                out.append((line_at(spans, at), flat(sent), flat(" ".join(para))))
            para.append(sent)
            at += len(sent) + 1
    return out


def uncovered_residue(scope, covering):
    """[(fragment, why it is claim-bearing)] for every part of a citation's scope no check covers.

    Rule 3 item 1 as amended: every clause of a sentence carrying a citation is an element of
    the cited claim. Rather than guess clause boundaries -- splitting on "and" tore
    "a role and the agent playing it" in half -- mark what the checks actually cover and
    report what is left.

    What is left is now disposed of rather than filtered by length. A leftover used to be
    reported only if it carried three content words, on the reasoning that anything shorter
    was framing such as "Analysis shows". Word count cannot establish that: "and authority
    shifts" is a claim and was discarded, and "Participants never" is the whole difference
    between a claim and its opposite and was discarded too. A fragment is now reported when it
    carries any content word at all, or any negation, modality or scope marker even if it
    carries no content word. Only pure function words and punctuation are disposed of in
    silence, and the count of those is reported.
    """
    flat_scope = flat(scope)
    if not flat_scope:
        return []
    mask = bytearray(len(flat_scope))
    for c in covering:
        needle = flat(c["claim_text"])
        if not needle:
            continue
        at = flat_scope.find(needle)
        while at != -1:
            for i in range(at, at + len(needle)):
                mask[i] = 1
            at = flat_scope.find(needle, at + 1)
    residues, run = [], []
    for ch, seen in zip(flat_scope, mask):
        if seen:
            if run:
                residues.append("".join(run)); run = []
        else:
            run.append(ch)
    if run:
        residues.append("".join(run))
    out = []
    for r in residues:
        r = r.strip(" ,;:\u2014-")
        if not r:
            continue
        marks = claim_markers(r)
        if marks:
            out.append((r, "carries " + ", ".join(marks) + ": a negation, modality or scope "
                           "marker no check accounts for, which can invert the cited claim"))
            continue
        if derive_terms(r):
            out.append((r, "no check for this citation accounts for it"))
    return out


MAX_NUMERIC_RANGE = 50    # "[1-400]" is not a citation this tool will enumerate


MAX_LOCATOR_SPAN = 200   # "pp. 1-500" is not a page claim this tool will enumerate
PAGE_LIST_RE = re.compile(
    r"\b(?:pp?\.|pages?|slides?|\u00a7)\s*"
    r"(\d{1,4}(?:\s*(?:[-\u2013\u2014]|,|&|\band\b)\s*\d{1,4})*)", re.I)
PART_RE = re.compile(r"(\d{1,4})(?:\s*[-\u2013\u2014]\s*(\d{1,4}))?")


def member_pages(text):
    """(pages the member states, fully parsed) -- (None, True) when it states none.

    This kept only the first page or the first dash range, so "(Tester, 2026, pp. 1, 99)"
    cleared against a one-page source checked at page 1, and "pp. 1, 3" was reported as
    naming only page 1 and refused a check correctly bound to page 3 (2026-09-21 review,
    F5-03). It is the same defect repaired in the wiki producer as W4 on 2026-09-20 and never
    looked for here, which is what the cross-tool sweep was run to find.
    """
    m = PAGE_LIST_RE.search(text)
    if not m:
        return None, True
    pages, supported = set(), True
    for part in re.sub(r"\s*(?:&|\band\b)\s*", ",", m.group(1), flags=re.I).split(","):
        part = part.strip()
        if not part:
            continue
        mm = PART_RE.fullmatch(part)
        if not mm:
            supported = False
            continue
        lo = int(mm.group(1))
        if mm.group(2) is None:
            pages.add(lo)
            continue
        hi = int(mm.group(2))
        if hi < lo or hi - lo > MAX_LOCATOR_SPAN:
            supported = False
            continue
        pages.update(range(lo, hi + 1))
    return (frozenset(pages) if pages else None), (supported and bool(pages))


def numeric_labels(citation):
    """([labels named], [parts that could not be read]) for "[1]", "[1,3]", "[1-3]".

    The range is expanded. Taking every run of digits turned "[1-3]" into labels 1 and 3, so
    the interior work was never looked for at all (finding G1).
    """
    labels, bad = [], []
    for part in re.split(r"[,;]", citation.strip("[]")):
        part = part.strip()
        if not part:
            continue
        rm = re.fullmatch(r"(\d{1,3})\s*[\u2013-]\s*(\d{1,3})", part)
        if rm:
            lo, hi = int(rm.group(1)), int(rm.group(2))
            if lo <= hi <= lo + MAX_NUMERIC_RANGE:
                labels.extend(str(n) for n in range(lo, hi + 1))
            else:
                bad.append(part)
        elif part.isdigit():
            labels.append(part)
        else:
            bad.append(part)
    return labels, bad


def year_tokens(part):
    """[(year, position)] for every work an author-year member names.

    "(Tester, 2026, 2025, p. 1)" names two works, and reading only the first year left the
    second neither resolved nor reported (2026-09-20 review, F3). Anything at or after the
    page locator is a page number, not a year: "pp. 2019-2020" is two pages.
    """
    pm = PAGE_IN_CITATION_RE.search(part)
    cut = pm.start() if pm else len(part)
    out = []
    for m in CITE_YEAR_RE.finditer(part):
        if m.start() >= cut:
            break
        out.append((re.sub(r"\s+", "", m.group(1) or m.group(2)).lower(), m.start()))
    return out


def keys_for(families, year, sources):
    """Source keys whose author family and full year token both match."""
    keys = []
    for key, src in sources.items():
        cite = src.get("cite") or {}
        author = str(cite.get("author", "")).strip()
        src_year = str(cite.get("year", "")).strip().lower()
        if not author or not src_year:
            continue
        family = author.split(",")[0].split()[-1].lower()
        if family and family in families and src_year == year:
            keys.append(key)
    return keys


def author_year_keys(text, sources):
    """Source keys the FIRST year in an author-year member names."""
    ys = year_tokens(text)
    if not ys:
        return []
    families = {f.lower() for f in FAMILY_RE.findall(text[:ys[0][1]])}
    return keys_for(families, ys[0][0], sources)


def citation_targets(citation, cfg, author_hint=None):
    """([(source key, the page span THAT member states)], why it could not fully resolve).

    Every member of a grouped citation is inventoried and resolved on its own, and each
    carries its own locator. A citation that names three works and resolves one is not a
    resolved citation: the unresolved members used to be dropped silently, leaving the first
    valid member to clear the whole group (2026-09-20 review, finding G1).
    """
    sources = cfg.get("sources", {})
    resolved, unresolved, bad_locators = [], [], []

    m = re.match(r"\\cite[tp]?\*?\{([^}]*)\}", citation)
    if m:
        for k in [x.strip() for x in m.group(1).split(",") if x.strip()]:
            if k in sources:
                resolved.append((k, None))
            else:
                unresolved.append(k)
    elif citation.startswith("["):
        mapping = {str(k): v for k, v in (cfg.get("bib_numbers") or {}).items()}
        labels, bad = numeric_labels(citation)
        if not mapping:
            return [], ("numeric citation, and the checks file declares no bib_numbers "
                        "mapping, so the work it names cannot be identified")
        unresolved.extend(bad)
        for n in labels:
            key = mapping.get(n)
            if key and key in sources:
                resolved.append((key, None))
            else:
                unresolved.append("[" + n + "]")
    else:
        for part in citation.strip("()").split(";"):
            part = part.strip()
            if not part:
                continue
            years = year_tokens(part)
            if not years:
                unresolved.append(part)
                continue
            families = {f.lower() for f in FAMILY_RE.findall(part[:years[0][1]])}
            if not families and author_hint:
                # "Tester (2026, p. 1)": the family sits outside the parenthesis.
                families = {f.lower() for f in FAMILY_RE.findall(author_hint)}
            pages, locator_ok = member_pages(part)
            if not locator_ok:
                bad_locators.append(part)
                continue
            for year, _ in years:
                keys = keys_for(families, year, sources)
                if keys:
                    resolved.extend((k, pages) for k in keys)
                else:
                    unresolved.append(("/".join(sorted(families)) + " " + year).strip())

    if bad_locators and not resolved:
        # Kept apart from the identity failure below: a citation whose WORK cannot be
        # identified and one whose PAGE cannot be parsed call for different corrections, and
        # the reviewer's R3 fixture asserts the wording of the first.
        return [], ("states a page locator this tool cannot parse: "
                    + "; ".join(repr(b) for b in bad_locators[:3]))
    if not resolved:
        return [], "names no source in this checks file"
    if bad_locators:
        return resolved, ("states a page locator this tool cannot parse: "
                          + "; ".join(repr(b) for b in bad_locators[:3]))
    if unresolved:
        return resolved, ("names " + str(len(resolved) + len(unresolved))
                          + " work(s), and " + str(len(unresolved))
                          + " of them cannot be identified from this checks file: "
                          + "; ".join(unresolved[:4]))
    return resolved, None


def bind_citing_document(cfg, override):
    """(doc_text, problems). A verdict is valid for one version of one text (Rule 3 item 14)."""
    decl = cfg.get("citing_document") or {}
    path = override or decl.get("path")
    if not path:
        # A checks set can legitimately bind something other than a manuscript - rule
        # provenance, say. That is allowed only when it is written down and shown.
        why = str(decl.get("not_a_manuscript") or "").strip()
        if len(why) >= 20:
            return None, ["NOTE not_a_manuscript: " + why]
        return None, ["UNBOUND: no citing document, so this result proves nothing about any "
                      "manuscript. Pass --citing-document PATH, set citing_document.path, or "
                      "record citing_document.not_a_manuscript with a written reason"]
    if not os.path.isfile(path):
        return None, ["CITING_DOCUMENT_MISSING: " + str(path)]
    raw = open(path, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    declared = decl.get("sha256")
    problems = []
    if declared and declared != sha:
        problems.append("CITING_DOCUMENT_CHANGED: checks were built for " + declared[:16]
                        + ", target is " + sha[:16] + ". Re-gate; do not rely on this result")
    return raw.decode("utf-8-sig"), problems


def main():
    try:
        return _main()
    except GateUnavailable as exc:
        print(f"GATE_UNAVAILABLE: {exc}")
        sys.exit(3)


def _main():
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    verbose = "--verbose" in sys.argv
    legacy = "--legacy" in sys.argv       # pre-amendment checks files: bind quotes, but say the classes are unpoliced
    override = (sys.argv[sys.argv.index("--citing-document") + 1]
                if "--citing-document" in sys.argv else None)
    doc_text, doc_problems = bind_citing_document(cfg, override)
    doc_problems += check_bib_numbers(cfg, doc_text)
    doc_flat = flat(doc_text) if doc_text is not None else None
    unbound_claims = []
    src = {}
    for k, v in cfg["sources"].items():
        read = pages_of(v["pdf"])
        web = v.get("version") == WEB_RENDERING
        # Nothing to confirm or refute: the pages of a printed web page are the printer's.
        ok, agree, readable, why_not = ((True, 0, 0, "") if web
                                        else offset_confirmed(read["raw"], v.get("offset", 0)))
        src[k] = dict(v, pages=read["pages"], raw=read["raw"], web_rendering=web,
                      offset_confirmed=ok, folio_agreement=(agree, readable),
                      offset_why_not=why_not,
                      folios=[] if web else printed_folios(read["raw"]))
    fails, best = [], {}
    where_bound = {}                             # checks whose locator is not a printed page
    cov_rows, no_claim = [], 0
    for c in cfg["checks"]:
        cid, s = c["id"], src[c["source"]]
        q, cls = norm(c["quote"]), c.get("class", "")
        idx = c["page"] - s.get("offset", 0) - 1
        problems = []
        if s.get("web_rendering"):
            pass                                 # no printed pagination to confirm or refute
        elif not s.get("offset_confirmed", True):
            why = s.get("offset_why_not") or "the source states no readable number"
            problems.append(
                f"PAGE_CONVENTION_UNCONFIRMED: the declared offset {s.get('offset', 0):+d} "
                f"for {c['source']} cannot be confirmed against the source's own printed "
                f"pages -- {why}. Rule 3 item 9c: a locator names a pagination, and an "
                "unconfirmed pagination cannot place a quote on a printed page")
        # An offset agreeing with most pages does not overrule the folio printed on the one
        # page the claim rests on. The per-check path consulted only the document-wide verdict,
        # so a source printing 1, 2, 99 bound a quote on its third page to p.3 and exited 0
        # (2026-09-21 review, F6-02).
        stated = [] if s.get("web_rendering") else (s.get("folios") or [])
        if 0 <= idx < len(stated) and stated[idx] and c["page"] not in stated[idx]:
            problems.append(
                f"PAGE_LOCATOR_REFUTED: the page this check reads prints "
                f"{sorted(stated[idx])}, not p.{c['page']}. Rule 3 item 9c: a locator names "
                "the pagination the source prints, and the cited page contradicts it")
        if cls not in CLASSES:
            problems.append(f"bad class '{cls}'")
        if len(q) < 25:
            problems.append("quote too short to bind (<25 alnum chars)")
        if s.get("web_rendering"):
            web_problems, render_page = web_locator(c, s)
            problems += web_problems
            if not web_problems:
                where_bound[cid] = (f"section {c['section']!r} of {c['source']}, a web "
                                    f"rendering (render page {render_page}, not a printed page)")
        elif not (0 <= idx < len(s["pages"])) or q not in s["pages"][idx]:
            elsewhere = [i + 1 + s.get("offset", 0) for i, t in enumerate(s["pages"]) if q in t]
            problems.append(f"WRONG_PAGE: quote is on p.{elsewhere}" if elsewhere
                            else "QUOTE_NOT_FOUND anywhere in source (fabricated or mistyped)")
        missing = [t for t in c.get("key_terms", []) if not term_ok(t, q)]
        if missing and cls in ("VERBATIM", "PARAPHRASE"):
            where = {t: [i + 1 + s.get("offset", 0) for i, p in enumerate(s["pages"]) if term_ok(t, p)] for t in missing}
            problems.append(f"CONFLATION_RISK: claim term(s) {missing} not in quote; class must be MAPPED/EXTENDED. "
                            f"Term occurs in source at pp. {where}")
        if cls != "VERBATIM" and not c.get("bridge", "").strip():
            problems.append("no bridge: non-VERBATIM support must state the inference from quote to claim")
        # items 1 and 3 (amended): derived key terms, coverage, and the modality-and-scope statement
        if not c.get("claim_text", "").strip():
            no_claim += 1
            if not legacy:
                problems.append("no claim_text: the check must carry the claim element's exact words as they stand in the citing text")
        else:
            if doc_flat is not None and flat(c["claim_text"]) not in doc_flat:
                unbound_claims.append(cid)
                problems.append("claim_text is not in the citing document: this check describes "
                                "another text, so it cannot support a claim in this one")
            derived, miss_d, dropped = coverage(c, q)
            bad_drop = [t for t, why in dropped.items() if len(str(why).strip()) < 10]
            if bad_drop:
                problems.append(f"dropped_terms without a written reason: {bad_drop}")
            counted = [t for t in derived if t not in dropped]
            cov_rows.append((cid, cls, len(counted) - len(miss_d), len(counted), miss_d))
            # Rule 3 item 3, as ratified: "A claim term missing from the quote forces MAPPED or
            # EXTENDED." That binds PARAPHRASE too. Enforcing it on VERBATIM alone left the
            # chosen-keyword route open: a PARAPHRASE naming two easy key_terms passed with none
            # of its derived terms in the quote (cross-family review, 2026-09-20).
            if cls in ("VERBATIM", "PARAPHRASE") and miss_d:
                problems.append(f"{cls}_INCOMPLETE: derived claim term(s) not in quote: {miss_d}. "
                                "Rule 3 item 3: a missing claim term forces MAPPED or EXTENDED. "
                                "List an inflection, drop the term with a written reason, or lower the class")
            # Rule 3 item 6: modality and scope, not only topic. Every negation and modality
            # word is a function word, so derive_terms drops all of them and a claim derives
            # exactly the terms of its own negation. Before this, "participants never share
            # resources" scored 5/5 against a quote saying they do, and certified VERBATIM.
            # A check with no claim_text has nothing to compare, and is already failed above
            # for that. Running the comparison on an empty string made every modal in the
            # quote look like an unmatched one.
            if c.get("claim_text", "").strip() and \
                    prescriptive(c.get("quote", "")) != prescriptive(c["claim_text"]):
                # Not restricted to VERBATIM and PARAPHRASE. MAPPED and EXTENDED carry a
                # written bridge, and no bridge establishes that a prescribed behaviour
                # occurs; the reviewer's words: "reclassification with a generic bridge does
                # not establish occurrence".
                if prescriptive(c.get("quote", "")):
                    detail = ("the quote states what should happen and the claim states that "
                              "it does")
                else:
                    detail = ("the claim states what should happen and the quote only reports "
                              "what does")
                problems.append("PRESCRIPTIVE_NOT_OBSERVED: " + detail + ". A source that "
                                "prescribes a behaviour is not evidence that the behaviour "
                                "occurs (Rule 3 item 6). Bind a passage that reports it, or "
                                "write the claim as the norm it is; no class or bridge closes "
                                "this gap")
            mod = marker_delta(c["claim_text"], c.get("quote", "")) if c.get("claim_text", "").strip() else []
            if cls in ("VERBATIM", "PARAPHRASE") and mod:
                problems.append(f"{cls}_MODALITY: " + "; ".join(mod) + ". Rule 3 item 6: a "
                                "difference in negation, modality or scope forces MAPPED or "
                                "EXTENDED with a written bridge, whatever the term coverage")
            if cls == "VERBATIM" and len(c.get("modality_scope", "").strip()) < 15:
                problems.append("VERBATIM needs a written modality_scope statement (item 6): term coverage alone never yields VERBATIM")
        if problems:
            fails.append((cid, c["element"], problems))
        else:
            e = c["element"]
            if e not in best or CLASSES.index(cls) < CLASSES.index(best[e][0]):
                best[e] = (cls, cid)
    elements = [e for cl in cfg.get("claims", []) for e in cl["elements"]]
    unsupported = [e for e in elements if e not in best]
    weak = [(e, *best[e]) for e in elements if e in best and best[e][0] in ("MAPPED", "EXTENDED")]
    n = len(cfg["checks"])
    print(f"checks: {n - len(fails)} bound / {len(fails)} failed / {n} total")
    print(f"claim elements: {len(elements) - len(unsupported)} supported / {len(unsupported)} UNSUPPORTED / {len(elements)} total")
    tally = {k: sum(1 for e in elements if e in best and best[e][0] == k) for k in CLASSES}
    print("best support per element: " + ", ".join(f"{k}={v}" for k, v in tally.items()))
    if cov_rows:
        for k in CLASSES:
            rows = [r for r in cov_rows if r[1] == k]
            if rows:
                have, tot = sum(r[2] for r in rows), sum(r[3] for r in rows)
                print(f"derived-term coverage {k}: {have}/{tot} claim terms in quote across {len(rows)} check(s)")
        if verbose:
            for cid, cls, have, tot, miss in cov_rows:
                if miss: print(f"   {cid} {cls} {have}/{tot} missing: {miss}")
    uncovered, n_citations = [], 0
    if doc_text is not None:
        bound_path = override or (cfg.get("citing_document") or {}).get("path")
        checks_with_claims = [c for c in cfg["checks"] if c.get("claim_text", "").strip()]
        for line_no, sentence, preamble in cited_sentences(doc_text):
            spots = list(CITATION_RE.finditer(sentence))
            for i, m in enumerate(spots):
                n_citations += 1
                citation = m.group(0)
                before = sentence[(spots[i - 1].end() if i else 0):m.start()]
                after = sentence[m.end():(spots[i + 1].start() if i + 1 < len(spots) else len(sentence))]
                # A parenthetical citation governs what precedes it; a narrative one --
                # "Tester (2026, p. 1) states: ..." -- governs what follows, and its author
                # stands outside the parenthesis (finding G6).
                author_hint, author_at = narrative_attribution(before)
                attribution = ""
                # Text after the LAST citation of a sentence belongs to no other citation, so
                # discarding it left it accounted for by nothing: "... (Tester, 2026, p. 1)
                # and authority shifts." was reported fully covered with only the first clause
                # checked (2026-09-21 review, F5-02). For an earlier citation the same text is
                # the next one's `before`, and is disposed of there.
                last = i == len(spots) - 1
                # The author's name is attribution whether or not anything follows the
                # citation. Requiring content after it sent "... in Ratto et al. (2026, p. 3)."
                # down the parenthetical branch, which kept the name in scope and reported it.
                if author_hint:
                    # The claim follows the citation, but whatever stood before the author's
                    # name is still part of the sentence and still cited. Taking only the
                    # following text erased it: "All autonomous systems are safe according to
                    # Tester (2026, p. 1), who states: ..." cleared on the second clause
                    # alone (2026-09-20 review, F4). The author's name is dropped as
                    # attribution; the rest of the prefix stays in scope.
                    tail = ATTRIBUTION_TAIL_RE.match(after)
                    attribution = tail.group(0) if tail else ""
                    scope = before[:author_at] + " " + (after if last else "")
                else:
                    scope = before + (after if last else "")
                    # "Carries no content", not "is whitespace": a citation whose sentence is
                    # just "[2]." has a trailing period for a scope, and treating that as
                    # non-empty killed the preamble fallback that G3 added.
                    if not HAS_CONTENT_RE.search(scope):
                        scope = preamble
                targets, why = citation_targets(citation, cfg, author_hint)
                if why:
                    uncovered.append((line_no, citation, citation, why))
                    continue
                if not scope.strip():
                    uncovered.append((line_no, citation, citation,
                                      "the citation has no claim text in its scope, so there "
                                      "is nothing here for it to support"))
                    continue
                keys = {k for k, _ in targets}
                matched = [c for c in checks_with_claims
                           if flat(c["claim_text"]) and flat(c["claim_text"]) in flat(scope)]

                def binds(c, key, pages):
                    return (c["source"] == key
                            and (pages is None
                                 or (str(c["page"]).isdigit() and int(c["page"]) in pages)))

                # Rule 3 item 8: a citation names a work, and every work it names is cited for
                # the claim. Evidence for one member is not evidence for another, so each is
                # discharged on its own checks and its own stated page. Pooling them let a
                # single checked reference clear the rest of its group, including a second
                # locator naming a page the source does not have (2026-09-20 review, F1).
                per_member = [((key, span), [c for c in matched if binds(c, key, span)])
                              for key, span in targets]
                right_source = [c for _, own in per_member for c in own]
                if matched and not right_source:
                    stated = ", ".join(sorted(keys))
                    spans = {k: pg for k, pg in targets if pg}
                    same_work = [c for c in matched if c["source"] in keys]
                    clash = next((c for c in same_work if spans.get(c["source"])), None)
                    if clash is not None:
                        detail = (f"the check(s) for {stated} bind p."
                                  + str(sorted({c["page"] for c in same_work}))
                                  + ", but the citation states p."
                                  + str(sorted(spans[clash["source"]])))
                    else:
                        detail = ("the check(s) covering it cite "
                                  + ", ".join(sorted({c["source"] for c in matched}))
                                  + f", not {stated}")
                    uncovered.append((line_no, citation, scope.strip() or citation, detail))
                    continue
                # The attribution clause of a narrative citation is how the sentence names
                # its source, so it is covered rather than reported.
                covered_extra = [{"claim_text": attribution}] if attribution.strip() else []
                for (key, span), own in per_member:
                    where = ("p." + str(sorted(span))) if span else "no stated page"
                    # Parsing the whole locator is only half of it: a page the citation names
                    # must also exist in the work it names. "(Tester, 2026, pp. 1, 99)" against
                    # a one-page source cleared on page 1 alone, because nothing asked whether
                    # page 99 was there (2026-09-21 review, F5-03).
                    known = src.get(key) or {}
                    have = len(known.get("pages") or [])
                    off = known.get("offset", 0)
                    outside = sorted(n for n in (span or ())
                                     if not 0 <= n - off - 1 < have)
                    if have and outside:
                        uncovered.append((line_no, citation, flat(scope) or citation,
                                          f"the citation states p.{outside} for {key}, which "
                                          f"that source does not have: it is {have} page(s) "
                                          f"at offset {off:+d}"))
                        # No check can bind a page the source has not got, so the generic
                        # "nothing binds this member" finding below would say the same thing
                        # less precisely.
                        continue
                    if not own:
                        uncovered.append((line_no, citation, flat(scope) or citation,
                                          f"no check binds {key} at {where} to anything in this "
                                          "sentence; a citation's other members do not support it"))
                        continue
                    for residue, why in uncovered_residue(scope, own + covered_extra):
                        uncovered.append((line_no, citation, residue, f"{why} (for {key})"))
        distinct = len({(l, c) for l, c, _, _ in uncovered})
        print(f"citing document: {os.path.basename(str(bound_path))}"
              f" | citation occurrences {n_citations}, fully covered {n_citations - distinct},"
              f" UNCOVERED {len(uncovered)} element(s)"
              f" | claim_text bound to document: {len(checks_with_claims) - len(unbound_claims)}"
              f"/{len(checks_with_claims)}")
    hard_doc_problems = [d for d in doc_problems if not d.startswith("NOTE ")]
    for d in doc_problems:
        print(d if d.startswith("NOTE ") else "FAIL " + d)
    for line_no, citation, clause, why in uncovered:
        print(f"UNCOVERED L{line_no} {citation[:38]}: {clause[:110]} - {why}")
    if no_claim:
        print(f"{'LEGACY' if legacy else 'FAIL'}: {no_claim} check(s) carry no claim_text; their classes rest on chosen key_terms and are unpoliced (Rule 3 item 1)")
    for cid, e, ps in fails:
        print(f"FAIL {cid} [{e}]"); [print(f"     - {p}") for p in ps]
    for e in unsupported:
        print(f"UNSUPPORTED [{e}] - no bound quote; do not issue a verdict, do not cite")
    for e, cls, cid in weak:
        print(f"DISCLOSE {cls} [{e}] via {cid} - report to author as inference, not as PASS")
    # A locator that is not a printed page is never reported as one (Rule 3 item 9c).
    for cid in sorted(where_bound):
        print(f"LOCATOR {cid} is {where_bound[cid]}")
    if verbose:
        for e in elements:
            if e in best: print(f"ok {best[e][0]:10s} [{e}] via {best[e][1]}")
    sys.exit(1 if fails or unsupported or hard_doc_problems or uncovered else 0)

if __name__ == "__main__":
    main()
