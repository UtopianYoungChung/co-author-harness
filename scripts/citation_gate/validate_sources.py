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
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
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
        hit = tot = 0
        for i, t in enumerate(raw):
            n = str(i + 1 + off)
            if i + 1 + off < 1 or len(t) < 200:
                continue
            tot += 1
            edge = t[:70] + " | " + t[-70:]
            hit += bool(re.search(rf"(?<!\d){n}(?!\d)", edge) or re.search(rf"\bpage {n} of \d+|(?<!\d){n}/\d+\b", t))
        if v == "web_rendering":
            res.append("no pagination")
        elif tot and hit / tot >= 0.6:
            res.append(f"offset {off:+d} confirmed on {hit}/{tot} pages")
        else:
            reviews.append(f"9c {k}: offset {off:+d} matches a printed number on only {hit}/{tot} pages - confirm page convention by eye")
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
