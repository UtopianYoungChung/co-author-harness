#!/usr/bin/env python
"""validate_sources.py - companion to verify_locators.py for Rule 3 items 9-12.

Reads the same checks.json (extra keys are ignored by verify_locators.py). Prints conclusions only.

  item 9  VALIDATION   identity (first pages + Crossref record), declared version, page convention
  item 10 RETRACTION   Crossref update notices per DOI, with lookup date; no lookup -> NOT CHECKED
  item 11 EMPTY        attribution markers in the sentence that holds each bound quote
  item 12 COUNTER      sentences elsewhere in the same source joining a key term to a contrary marker

Items 11 and 12 are mechanical screens, not verdicts: a hit is REVIEW until the check carries a written
"empty_reviewed" / "counter_reviewed" note. A clean screen says the screen found nothing, no more.

Per-source keys:  pdf, offset, cite{author,year,title}, doi | no_doi_reason, version
                  version in: version_of_record | author_manuscript | web_rendering | official_print
Per-check keys:   (verify_locators keys) + optional counter_reviewed; for item 11, empty = confirmed |
                  resolved-by-attribution | not-empty, with an empty_reviewed note (and relies_on[] when resolved).
                  empty = confirmed is a FAIL. A screen hit with no disposition stays REVIEW.
Item 13 (citations reconcile with the bibliography) is a separate script: reconcile_citations.py <document>

usage: python validate_sources.py checks.json [--verbose] [--offline]
"""
import sys, json, re, os, io, unicodedata, datetime, difflib, urllib.request, urllib.parse
try:                                   # reconfigure, never replace: an orphaned wrapper
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # closes the caller's buffer
except (AttributeError, ValueError):   # not a TextIOWrapper, e.g. under a test harness
    pass
VERSIONS = ["version_of_record", "author_manuscript", "web_rendering", "official_print"]
EMPTY_DISPOSITIONS = ["confirmed", "resolved-by-attribution", "not-empty"]
CACHE = os.path.join(os.path.expanduser("~"), ".claude", "cache", "crossref")
TODAY = datetime.date.today().isoformat()
BAD_UPDATES = ("retraction", "withdrawal", "removal", "expression_of_concern", "expression-of-concern",
               "correction", "erratum", "corrigendum", "partial_retraction")

ATTRIB = [  # item 11: the quoted sentence leans on someone else
    (r"\([A-Z][A-Za-zÀ-ſ'\-]+(?: (?:et al\.?|and|&) ?[A-Z]?[A-Za-zÀ-ſ'\-]*)*,? (?:19|20)\d\d[a-z]?", "author-year citation"),
    (r"[A-Z][A-Za-zÀ-ſ'\-]+(?: et al\.?| and [A-Z][a-z]+)? \((?:19|20)\d\d[a-z]?", "Author (year) citation"),
    (r"\[\d{1,3}(?:[,–\-] ?\d{1,3})*\]", "numeric citation"),
    (r"\b(?:according to|as cited in|cited in|quoted in|reported by|as reported|as noted by|as described by)\b", "attribution phrase"),
    (r"\b(?:argues?|claims?|suggests?|found|reports?|shows?|showed|noted|observed) that\b.{0,80}\b(?:19|20)\d\d\b", "reporting verb + year"),
]
CONTRARY = (r"\b(?:however|although|though|nevertheless|nonetheless|whereas|despite|in contrast|on the contrary|"
            r"contrary to|except|unless|limitations?|caution|caveat|fail(?:s|ed)? to|no evidence|does not|do not|"
            r"did not|cannot|is not|are not|was not|were not|not always|not necessarily|rarely|seldom)\b")


# What may count as a printed folio. Any number in the edge window was enough, so the headings
# "Section 11 / 12 / 13" on a source printing 1, 2, 3 confirmed a declared offset of +10 and
# the tool announced "offset +10 confirmed on 3/3 pages" (2026-09-21 review, F6-01). A number
# a labelling word owns is that label's number, not the page's.
# --- shared with the sibling tool: this region is copied, not re-written. Rule 3 runs
# --- both tools on one checks file and item 9c is implemented in each, so a rule that
# --- lives in two hands drifts (2026-09-22 review, F9-05). The suite asserts the two
# --- regions are byte-identical and that both modules answer alike.
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
FOLIO_ZONE_LINES = 4     # the running head and foot: where a page prints its own number.
                         # Three missed the recto folio of a verso/recto journal, whose
                         # head runs title / issue / rule / folio -- 15 of 31 pages
                         # instead of 30, refusing a pagination printed throughout
                         # (2026-09-23, corpus finding C-01). Measured over every
                         # regression source: 4 costs nothing, 5 brings back the body
                         # table cell that F7-05 and F8-07 were about.


# What a page prints that could be its own number, and how strongly it says so. Confirmation
# used to accept any arithmetic that worked on enough pages, so a source headed
# "Experiment 11/12/13" confirmed an offset of +10 and a source headed "J 1/2/3/99" cleared a
# citation to its fourth page (2026-09-22 review, F9-01, F9-02).


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


ROLE_HEAD_RE = re.compile(
    r"^(?:sections?|secs?|chapters?|chaps?|ch|parts?|figures?|figs?|tables?|tabs?|appendix|"
    r"appendices|apps?|volumes?|vols?|numbers?|nos?|issues?|articles?|arts?|items?|steps?|"
    r"lines?|notes?|equations?|eqs?|paragraphs?|paras?|exhibits?|box|boxes|panels?|slides?|"
    r"rules?|footnotes?|versions?|editions?|eds?|weeks?|days?|phases?|levels?|rounds?|"
    r"experiments?|exps?|trials?|studies|study|runs?|samples?|cases?|tests?|questions?|"
    r"models?|datasets?|groups?|cohorts?|waves?|batches?|tasks?|stages?|sets?)\.?$", re.I)
OWNER_RE = re.compile(r"([A-Za-z][A-Za-z'\-]*)[ ]*$")
EXPLICIT_RE = re.compile(r"\bpage[ ]+(\d+)[ ]+of[ ]+(\d+)\b", re.I)
N_OF_M_RE = re.compile(r"^(\d{1,4})[ ]*/[ ]*(\d{1,4})$")
PAGE_OF_LINE_RE = re.compile(r"^page[ ]+(\d+)[ ]+of[ ]+(\d+)$", re.I)
HEAD_TAIL = " .:;,\u2014\u2013-([{\"'\u201c\u2018"
EXPLICIT, BARE, WEAK = 2, 1, 0    # the page said so / a folio on its own line / anything else


def zone_lines(text):
    """The lines of the running head and foot, where a page prints its own number."""
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    return lines[:FOLIO_ZONE_LINES] + lines[-FOLIO_ZONE_LINES:]


def prints_a_bare_folio(raw_pages):
    """Whether any page prints a number alone on a line at its edge.

    `N/M` is a bare ratio: a score, a progress count, a date. It is read as pagination only
    where the document offers no plainer folio, which is jergas's case and not the case of a
    document that foots 1, 2, 3 and happens to tally `Items completed 11/20`
    (2026-09-22 review, F10-02).
    """
    for text in raw_pages or []:
        for line in zone_lines(text):
            if BARE_FOLIO_RE.match(line):
                return True
    return False


def stated_total(raw_pages):
    """The denominator most pages print as "N/M" at their edge, when they agree on one.

    jergas prints no bare folio and no "page N of M"; it prints "2/20", "3/20", "6/20" as the
    last line of its running foot, which is the page saying which page it is and how many
    there are. Requiring the denominator to agree across the pages that show the form keeps a
    fraction or a date in a footer from passing as pagination.
    """
    if prints_a_bare_folio(raw_pages):
        return None
    seen, shown = {}, 0
    for text in raw_pages or []:
        for line in zone_lines(text):
            m = N_OF_M_RE.match(line)
            if m:
                seen[int(m.group(2))] = seen.get(int(m.group(2)), 0) + 1
                shown += 1
                break
    if not shown:
        return None
    total, n = max(seen.items(), key=lambda kv: kv[1])
    return total if n / shown >= FOLIO_AGREEMENT else None


def page_evidence(text, total=None):
    """{number: (rank, place)} -- what one page states about itself, and where it states it.

    A page's own statement outranks anything inferred from arithmetic, which is what F9-04
    was: a one-page source saying "Page 1 of 1" was refused because a copyright year competed
    with it for the same standing.

    A number a role word heads keeps its entry, with a place that can never confirm anything.
    Dropping it outright let a one page source printing "Experiment 11" AND "Journal of
    Tests 1" confirm p.1, where the reviewer's pair of controls says the labelled number is
    exactly what should make that page doubtful (2026-09-22 review, F9-02/F9-04).
    """
    flat = re.sub(r"\s+", " ", text or "")
    # The statement must be the whole of a line. Searching the flattened page read
    # "See page 11 of 20 in the accompanying manual." as this page's own number and deleted
    # the folio printed beneath it (F10-02). The line rule keeps greenberg, which prints
    # "page 1 of 14" alone on line 110 of 120 -- outside any edge window.
    for line in [l.strip() for l in (text or "").splitlines() if l.strip()]:
        m = PAGE_OF_LINE_RE.match(line.strip(HEAD_TAIL))
        if m:
            return {int(m.group(1)): (EXPLICIT, "page-of")}
    zone = zone_lines(text)
    if total:
        for line in zone:
            nm = N_OF_M_RE.match(line)
            if nm and int(nm.group(2)) == total:
                return {int(nm.group(1)): (EXPLICIT, "n-of-m")}
    out = {}
    for line in zone:
        bm = BARE_FOLIO_RE.match(line)
        if bm:
            out[int(bm.group(1))] = (BARE, "line")
            continue
        for mm in EDGE_NUMBER_RE.finditer(line):
            n = int(mm.group(1))
            if n in out and out[n][0] >= BARE:
                continue
            head = line[:mm.start()].strip(HEAD_TAIL)
            if head and ROLE_HEAD_RE.match(head):
                out[n] = (WEAK, "role:" + head.lower().rstrip("."))
            elif not head:
                # The folio opens the running foot: "1 Journal of Synthetic Data, ...". No
                # word owns it, and calling that no place refused a positive control.
                out[n] = (WEAK, "start")
            else:
                om = OWNER_RE.search(line[:mm.start()].strip(HEAD_TAIL))
                out[n] = (WEAK, "end:" + om.group(1).lower() if om else "mid")
    for mm in EDGE_NUMBER_RE.finditer(flat):     # edge material no zone line held
        if mm.start() >= EDGE_CHARS and mm.end() <= len(flat) - EDGE_CHARS:
            continue                             # body text, not the page's edge
        n = int(mm.group(1))
        if n in out:
            continue
        om = OWNER_RE.search(flat[max(0, mm.start() - 40):mm.start()])
        out[n] = (WEAK, "end:" + om.group(1).lower() if om else "")
    return out


def folio_evidence(raw_pages, year=None):
    """Per page, {number: (rank, place)} for the numbers the page states about itself.

    A number equal to the source's declared year is a date, not a folio -- unless the page
    stated it outright, in which case the page is a better witness than the arithmetic.
    """
    total = stated_total(raw_pages)
    per = []
    for text in raw_pages or []:
        e = page_evidence(text, total)
        if year:
            e = {n: v for n, v in e.items() if v[0] == EXPLICIT or abs(n - int(year)) > 1}
        per.append(e)
    return per


def supported_offsets(raw_pages, year=None):
    """(offsets the source's own numbers support, pages that state a number, the floor).

    A source that supports more than one offset has ambiguous pagination: a page states at
    most one folio, so two arithmetic runs mean the numbers are not all folios and the gate
    cannot tell which are (2026-09-21 review, F7-03).
    """
    per = folio_evidence(raw_pages, year)
    stating = [i for i, e in enumerate(per) if e]
    floor = min(MIN_FOLIO_PAGES, len([t for t in (raw_pages or []) if t.strip()])) or 1
    counts = {}
    for i in stating:
        for n in per[i]:
            counts[n - (i + 1)] = counts.get(n - (i + 1), 0) + 1
    out = []
    for off in sorted(counts):
        if counts[off] >= floor and counts[off] / len(stating) >= FOLIO_AGREEMENT:
            out.append((off, counts[off]))
    # Where two paginations both clear the arithmetic, the better-evidenced one wins: a bare
    # folio outranks a number a heading owns, so "Section 11" printed above a bare "1" does
    # not make the source ambiguous, while two numbers of equal standing still do
    # (2026-09-22 review, F9-02 and F9-04, and the F6-01 regression case).
    if len(out) > 1:
        rank = {off: max(per[i].get(i + 1 + off, (WEAK, ""))[0]
                         for i in stating if (i + 1 + off) in per[i]) for off, _ in out}
        best = max(rank.values())
        out = [(off, n) for off, n in out if rank[off] == best]
    return out, stating, floor


def folio_place(per, offset):
    """(where the agreeing pages print their folio, those pages).

    "" when they agree on no place: a number after a comma or a bracket has no owner, and
    "no owner" is not a place. Keying refutation on it refused 18 live checks.
    """
    agreeing = [i for i in range(len(per)) if (i + 1 + offset) in per[i]]
    if not agreeing:
        return "", []
    places = {}
    for i in agreeing:
        pl = per[i][i + 1 + offset][1]
        places[pl] = places.get(pl, 0) + 1
    place, n = max(places.items(), key=lambda kv: kv[1])
    # A role word's place is not the folio's place: it is where that experiment or table
    # prints ITS number, so it can neither establish a pagination nor overrule a locator.
    # "mid" is not a place either -- it is the absence of one, and accepting it let
    # "Experiment (11) / Trial (12) / Study (13)" share a position (F10-05).
    if (not place or place == "mid" or place.startswith("role:")
            or n / len(agreeing) < FOLIO_AGREEMENT):
        return "", agreeing
    return place, agreeing


def offset_confirmed(raw_pages, offset, year=None):
    """(confirmed, agreeing, pages that state a number, why not) for a declared page offset.

    Rule 3 item 9c asks which pagination a locator uses. The gate took the answer from the
    checks file and never required it to hold: a source printing 1, 2, 3 with an offset of 10
    declared bound a citation to p. 11 and exited 0 (2026-09-21 sweep, S1).

    Arithmetic is necessary and is not sufficient. The agreeing numbers must also be the
    pages' own: stated outright, printed alone on a line, or printed after one running head
    the agreeing pages share. A sequence that survives the arithmetic and sits in no
    consistent place leaves the pagination unresolved -- it does not confirm it
    (2026-09-22 review, F9-01, F9-02).
    """
    per = folio_evidence(raw_pages, year)
    supported, stating, floor = supported_offsets(raw_pages, year)
    hit = sum(1 for i in stating if (i + 1 + offset) in per[i])
    if not stating:
        return False, 0, 0, "no page of it states a number that could be its own"
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
    place, agreeing = folio_place(per, offset)
    # Evidence that can carry a SHIFT has to clear the bar on its own. One bare number let
    # role-labelled numbers on the other pages confirm +10 (F10-05), and a running head
    # saying "Observation 11" is the same observation as one saying "Journal of Tests 11".
    strong = [i for i in agreeing if per[i][i + 1 + offset][0] >= BARE]
    if len(strong) >= floor and len(strong) / len(stating) >= FOLIO_AGREEMENT:
        return True, hit, len(stating), ""       # the pages said so, or printed folios
    # At an offset of zero the numbers coincide with the document's own sequence, so the
    # claim adds nothing beyond "page N is page N" and a running head is evidence enough.
    if offset == 0 and place:
        return True, hit, len(stating), ""
    return (False, hit, len(stating),
            "nothing establishes that the numbers agreeing with it are the pages' own: "
            f"only {len(strong)} of {len(stating)} state their number outright or print it "
            "on a line of its own, and a pagination shifted from the document's own sequence "
            "cannot rest on a running head alone")


def page_contradicts(raw_pages, offset, idx):
    """(number, place) when the cited page prints another number in the folio's own place.

    Refutation may read only a place that can be named. Where the agreeing pages show none,
    nothing occupies the folio's place and this says nothing: refuting a locator is the
    destructive direction, and it should not be done on a guess.
    """
    per = folio_evidence(raw_pages)
    if not (0 <= idx < len(per)):
        return None
    want = idx + 1 + offset
    # A page that states its own number outright refutes a locator that disagrees with it,
    # whatever the other pages do. This asked for the majority's place first, so a cited page
    # printing "Page 99 of 100" among pages printing bare folios was ignored at exactly the
    # point where the locator is bound (2026-09-22 review, F10-03).
    for n, (rank, pl) in per[idx].items():
        if rank >= EXPLICIT and n != want:
            return n, pl
    place, agreeing = folio_place(per, offset)
    if not place:
        return None
    if place == "line":
        # A folio is unique to its page; a bare number repeated across pages is a label, and
        # without that guard a "5" printed on two pages refused five correct checks (F6-02).
        # But a repeated number IS a folio when one of its occurrences agrees with the
        # declared offset: the document numbers a page that way, so the same number on
        # another page contradicts that page's locator. Without this, numbering that restarts
        # -- 1, 2, 3, 4, 1, 2 -- certified a p.6 the document never prints, because the 2 on
        # its sixth page also appears on its second (2026-09-22 review, F10-04).
        seen, folios = {}, set()
        for i, e in enumerate(per):
            for n, (r, pl) in e.items():
                if pl != "line":
                    continue
                seen[n] = seen.get(n, 0) + 1
                if n == i + 1 + offset:
                    folios.add(n)
        for n, (r, pl) in per[idx].items():
            if pl == "line" and n != want and (seen.get(n) == 1 or n in folios):
                return n, pl
        return None
    for n, (r, pl) in per[idx].items():
        if pl == place and n != want:
            return n, pl
    return None


# --- end shared region ---------------------------------------------------------------


def nchar(ch):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", ch).replace("­", "").lower())

def norm(s):
    return "".join(nchar(c) for c in s)

def norm_map(raw):
    """normalized text plus, for each normalized char, its index in raw."""
    out, idx = [], []
    for i, ch in enumerate(raw):
        for c in nchar(ch):
            out.append(c); idx.append(i)
    return "".join(out), idx

def raw_pages(pdf):
    """Page text flattened to single spaces: what the item 11 and 12 screens read."""
    import fitz
    d = fitz.open(pdf)
    return [re.sub(r"\s+", " ", d[i].get_text()) for i in range(d.page_count)]


def folio_pages(pdf):
    """Page text with its lines intact, read exactly as verify_locators.pages_of does.

    Item 9c asks where on the page a number is printed, and flattening the page destroys the
    only evidence that answers it. With the shared rule reading flattened text, the validator
    refused two sources the gate confirms from the same bytes -- identical code, different
    input (2026-09-22 review, F9-05). The suite asserts both extractors return the same text.
    """
    import fitz
    d = fitz.open(pdf)
    return [d[i].get_text() for i in range(d.page_count)]

def dehyph(t):
    return re.sub(r"(?<=[a-z])- (?=[a-z])", "", t)

def sentences(t):
    return re.split(r"(?<=[.?!;:]) (?=[A-Z(“\"§•])", t)

def crossref(doi, offline):
    os.makedirs(CACHE, exist_ok=True)
    cp = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9]", "_", doi) + ".json")
    if os.path.exists(cp):
        c = json.load(open(cp, encoding="utf-8"))
        if c.get("fetched") == TODAY or offline:
            return c
    if offline:
        return None
    try:
        r = urllib.request.Request("https://api.crossref.org/works/" + urllib.parse.quote(doi),
                                   headers={"User-Agent": "validate_sources/1.0 (citation validation; local use)"})
        m = json.load(urllib.request.urlopen(r, timeout=45))["message"]
    except Exception as e:
        try:                                       # DataCite etc.: identity only, no update notices
            r = urllib.request.Request("https://doi.org/" + urllib.parse.quote(doi),
                                       headers={"Accept": "application/vnd.citationstyles.csl+json",
                                                "User-Agent": "validate_sources/1.0"})
            m = json.load(urllib.request.urlopen(r, timeout=45))
            a0 = (m.get("author") or [{}])[0]
            c = {"fetched": TODAY, "registry": "doi.org (non-Crossref)", "title": m.get("title", ""),
                 "family": a0.get("family") or a0.get("literal", ""),
                 "year": ((m.get("issued", {}).get("date-parts") or [[None]])[0] or [None])[0],
                 "page": "", "updates": None}
            json.dump(c, open(cp, "w", encoding="utf-8"))
            return c
        except Exception:
            return {"error": f"{type(e).__name__}: {e}"[:120]}
    c = {"fetched": TODAY, "registry": "Crossref",
         "title": (m.get("title") or [""])[0],
         "family": (m.get("author") or [{}])[0].get("family", ""),
         "year": ((m.get("issued", {}).get("date-parts") or [[None]])[0] or [None])[0],
         "container": (m.get("container-title") or [""])[0],
         "volume": m.get("volume", ""), "issue": m.get("issue", ""), "page": m.get("page", ""),
         "updates": [{"type": u.get("type", ""), "doi": u.get("DOI", "")} for u in m.get("updated-by", [])]}
    json.dump(c, open(cp, "w", encoding="utf-8"))
    return c


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    verbose, offline = "--verbose" in sys.argv, "--offline" in sys.argv
    cfg = json.load(open(args[0], encoding="utf-8"))
    fails, reviews, lines = [], [], []
    src = {}

    # ---- items 9 and 10, per source -------------------------------------------------------------
    for k, s in cfg["sources"].items():
        try:
            raw = raw_pages(s["pdf"])
        except Exception as e:
            fails.append(f"9a {k}: cannot open pdf ({type(e).__name__})"); continue
        src[k] = dict(s, raw=raw)
        cite, off = s.get("cite") or {}, s.get("offset", 0)
        head = norm(" ".join(raw[:2]))
        res = []
        # 9a identity against the file
        if not cite.get("title") or not cite.get("author"):
            fails.append(f"9a {k}: no cite{{author,title,year}} declared; identity not checkable")
        else:
            miss = [f for f in ("author", "title") if norm(str(cite[f])) not in head]
            if miss:
                fails.append(f"9a {k}: first two pages do not contain cited {miss} - wrong file or wrong citation")
            else:
                res.append("file=cited work")
            if cite.get("year") and str(cite["year"]) not in " ".join(raw[:2]):
                res.append(f"year {cite['year']} not on first pages (soft)")
        # 9a identity against the registry, and item 10
        doi = s.get("doi")
        if doi:
            c = crossref(doi, offline)
            if not c or c.get("error"):
                reviews.append(f"9a/10 {k}: Crossref lookup failed ({(c or {}).get('error', 'offline, no cache')}) - "
                               f"registry identity and retraction status NOT CHECKED")
            else:
                sim = difflib.SequenceMatcher(None, norm(cite.get("title", "")), norm(c["title"])).ratio()
                ct, rt = norm(cite.get("title", "")), norm(c["title"])
                if sim < 0.85 and len(ct) >= 20 and (ct in rt or rt in ct):
                    res.append("DOI=cited work (cited title is a substring of the registry title; subtitle differs)")
                elif sim < 0.85:
                    fails.append(f"9a {k}: DOI {doi} resolves to a different title (similarity {sim:.2f}): '{c['title'][:80]}'")
                elif cite.get("author") and c["family"] and norm(cite["author"]) not in norm(c["family"]) and norm(c["family"]) not in norm(cite["author"]):
                    fails.append(f"9a {k}: DOI first author is '{c['family']}', cited '{cite['author']}'")
                else:
                    res.append(f"DOI=cited work ({sim:.2f})")
                if cite.get("year") and c["year"] and abs(int(cite["year"]) - int(c["year"])) >= 1:
                    reviews.append(f"9a {k}: cited year {cite['year']}, Crossref issued {c['year']}")
                bad = [u for u in (c["updates"] or []) if any(b in u["type"].lower() for b in BAD_UPDATES)]
                if c["updates"] is None:
                    reviews.append(f"10 {k}: DOI is not in Crossref ({c.get('registry')}); retraction status NOT CHECKED")
                elif bad:
                    fails.append(f"10 {k}: update notice(s) on {doi}: " + ", ".join(f"{u['type']} {u['doi']}" for u in bad))
                else:
                    res.append(f"no retraction/correction notice (Crossref, {c['fetched']})")
                src[k]["registry_pages"] = c["page"]
        elif s.get("no_doi_reason"):
            res.append(f"no DOI ({s['no_doi_reason']}); retraction N/A")
        else:
            fails.append(f"10 {k}: neither doi nor no_doi_reason declared; retraction status NOT CHECKED")
        # 9b version
        v = s.get("version")
        if v not in VERSIONS:
            fails.append(f"9b {k}: version not declared (one of {VERSIONS})")
        else:
            res.append(v)
        # 9c page convention: does the printed number implied by offset appear at the page edge?
        # Pages under 200 characters were skipped, so a sparse source -- a slide, a figure
        # page, a short article -- reported "0/0 pages" and the convention was never tested
        # (2026-09-21 sweep, S1). Length is the wrong filter: what matters is whether the page
        # shows a number at its edge at all. One that shows none states no folio and is not
        # evidence either way, so it is skipped rather than counted as a miss.
        # A number a labelling word owns is that label's number: "Section 11" is not
        # evidence that the page prints 11 (2026-09-21 review, F6-01).
        # The rule itself lives in the shared region above, copied from verify_locators.py by
        # script rather than by hand, and the gate's suite asserts both that the regions are
        # byte-identical and that the two modules answer alike. The previous arrangement said
        # the same thing in a comment and was false for four repairs (F9-05).
        conf, hit, tot, why_not = offset_confirmed(folio_pages(s["pdf"]), off,
                                                    (s.get("cite") or {}).get("year"))
        if v == "web_rendering":
            # Item 9c asks which pagination a locator uses. A printed web page has none, so
            # its checks must name a section instead, and verify_locators.py binds against
            # that. Validation runs first, so the requirement is refused here.
            res.append("no printed pagination; LOCATORS ARE WEB-PAGE SECTIONS, not pages")
            unlocated = [c["id"] for c in cfg["checks"]
                         if c.get("source") == k and not str(c.get("section", "")).strip()]
            if unlocated:
                fails.append(f"9c {k}: a web rendering prints no page numbers, but check(s) "
                             f"{unlocated} declare no section locator (Rule 3 item 8)")
        elif conf:
            res.append(f"offset {off:+d} confirmed on {hit}/{tot} pages")
        else:
            reviews.append(f"9c {k}: offset {off:+d} is not confirmed -- {why_not}"
                           " - confirm page convention by eye")
        if v == "author_manuscript":
            rp = src[k].get("registry_pages", "")
            res.append(f"LOCATORS ARE MANUSCRIPT PAGES, not journal pages{(' ' + rp) if rp else ''}")
        lines.append(f"  {k}: " + "; ".join(res))

    # ---- items 11 and 12, per check -------------------------------------------------------------
    n11 = n12 = c11 = c12 = 0
    empty_tally = {}
    for c in cfg["checks"]:
        s = src.get(c["source"])
        if not s:
            continue
        idx = c["page"] - s.get("offset", 0) - 1
        if not (0 <= idx < len(s["raw"])):
            continue                                   # verify_locators.py reports the bad locator
        raw = dehyph(s["raw"][idx])
        nt, mp = norm_map(raw)
        q = norm(c["quote"])
        pos = nt.find(q)
        if pos < 0:
            continue
        a, b = mp[pos], mp[pos + len(q) - 1] + 1
        ends = [x.end() for x in re.finditer(r"[.?!][”\"’')\]]?\d{0,2}(?: (?=[A-Z“\"(])|(?<![A-Z]\.)(?=[A-Z][a-z]))", raw[:a])]
        st = ends[-1] if ends else 0                # sentence start: after the last terminator, incl. .” , footnote marks, and text layers that drop the space after a period
        m = re.search(r"[.?!][”\"’')\]]?\d{0,2}(?= [A-Z(“\"]|(?<![A-Z]\.)[A-Z][a-z]|$)", raw[b:])
        en = b + (m.end() if m else min(len(raw) - b, 200))
        sent = raw[st:en]
        # item 11
        n11 += 1
        marks = sorted({name for pat, name in ATTRIB if re.search(pat, sent)})
        # EMPTY is a disposition recorded beside the class, not a fifth class (item 11, amended 2026-09-19).
        disp, note = c.get("empty", ""), c.get("empty_reviewed", "").strip()
        if disp and disp not in EMPTY_DISPOSITIONS:
            fails.append(f"11 {c['id']}: bad empty disposition '{disp}' (one of {EMPTY_DISPOSITIONS})")
        elif disp == "confirmed":
            fails.append(f"11 {c['id']} [{c['element'][:60]}]: EMPTY confirmed - the source relays another work and the citing "
                         f"sentence neither attributes the statement to the source as its synthesis nor marks the indirection")
        elif disp == "resolved-by-attribution" and (len(note) < 20 or not c.get("relies_on")):
            fails.append(f"11 {c['id']}: resolved-by-attribution needs an empty_reviewed note saying how the citing sentence "
                         f"attributes or marks the indirection, and a relies_on list of the works the source relies on")
        elif disp == "not-empty" and len(note) < 20:
            fails.append(f"11 {c['id']}: not-empty needs an empty_reviewed note giving the reason")
        elif marks and not disp:
            reviews.append(f"11 {c['id']} [{c['element'][:60]}]: EMPTY risk - quoted sentence carries {marks}. Read it, then record "
                           f"empty = confirmed | resolved-by-attribution | not-empty with an empty_reviewed note"
                           + (" (a note exists but no disposition)" if note else ""))
            if verbose: reviews.append(f"      > {sent[:300]}")
        else:
            c11 += 1
            if disp: empty_tally[disp] = empty_tally.get(disp, 0) + 1
        # item 12
        terms = [norm(t) for kt in c.get("key_terms", []) for t in kt.split("|") if len(norm(t)) >= 5]
        if not terms:
            continue
        n12 += 1
        hits = []
        for pi, pt in enumerate(s["raw"]):
            for se in sentences(dehyph(pt)):
                ns = norm(se)
                if q[:40] in ns or ns in q:
                    continue
                present = [t for t in terms if t in ns]
                if len(present) < min(2, len(terms)):
                    continue
                near = False
                for mk in re.finditer(CONTRARY, se, re.I):
                    win = norm(se[max(0, mk.start() - 90): mk.end() + 90])
                    near = near or any(t in win for t in present)
                if near:
                    hits.append((pi + 1 + s.get("offset", 0), se))
        if hits and not c.get("counter_reviewed", "").strip():
            pages = sorted({p for p, _ in hits})
            reviews.append(f"12 {c['id']} [{c['element'][:60]}]: {len(hits)} sentence(s) join a key term to a contrary marker, "
                           f"pp. {pages}. Read them; then record counter_reviewed.")
            if verbose:
                for p, se in hits[:6]: reviews.append(f"      > p.{p}: {se[:260]}")
        else:
            c12 += 1

    print(f"validation (item 9/10): {len(src)} sources")
    for l in lines: print(l)
    print(f"empty-reference screen (item 11): {c11} clear or reviewed / {n11 - c11} REVIEW or FAIL / {n11} quotes located"
          + (f"  dispositions: {empty_tally}" if empty_tally else ""))
    print(f"counter-evidence screen (item 12): {c12} clear or reviewed / {n12 - c12} REVIEW / {n12} checks with searchable key terms"
          f"  [scope: the cited source only, not the literature]")
    for f in fails: print("FAIL   " + f)
    for r in reviews: print(("       " if r.startswith("      >") else "REVIEW ") + r)
    sys.exit(1 if fails else (2 if reviews else 0))


if __name__ == "__main__":
    main()
