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
MIN_FOLIO_PAGES = 3      # pages that must AGREE before an offset can be confirmed, and
FOLIO_AGREEMENT = 0.6    # the share of the pages stating a number that must agree with it
EDGE_CHARS = 160         # of the flattened page, at each end: its running head and its footer
BARE_FOLIO_RE = re.compile(r"^[\[(]?\s*(\d{1,4})\s*[\])]?$")


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
    import fitz
    d = fitz.open(pdf)
    return [re.sub(r"\s+", " ", d[i].get_text()) for i in range(d.page_count)]

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
        # evidence that the page prints 11 (2026-09-21 review, F6-01). edge_numbers() is
        # shared verbatim with verify_locators.py so both tools read the same page the
        # same way; verify_locators_test.py asserts they agree.
        # One rule, written identically in both tools, so 9c and the gate cannot disagree
        # about the same source; verify_locators_test.py asserts the two verdicts match.
        conf, hit, tot, why_not = offset_confirmed(raw, off)
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
