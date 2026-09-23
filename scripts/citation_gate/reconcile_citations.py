#!/usr/bin/env python
"""reconcile_citations.py - Rule 3 item 13: every citation resolves, both ways.

Lists the in-text citations and the bibliography entries of one citing document (Markdown or plain text) and
reconciles them. Prints conclusions only.

  FAIL    an in-text citation that resolves to no bibliography entry (the work cannot be identified), or to
          more than one (ambiguous)
  REPORT  a bibliography entry that is never cited

Handles author-year forms - (Yu, 2024, pp. 211-214), Yu (2024, p. 211), Yu's (2024), Wand and Weber (2002),
(Chung & Hassan, 2026), Holldack et al. (2026), several citations inside one pair of brackets separated by ';',
a bare (2024) right after a named author - and numeric forms [3], [3,4], [3-5] against numbered entries.

Matching: same year; same first-author family name; two named authors need an entry with exactly those two;
"et al." needs an entry with three or more authors; a single name needs a single-author entry. An organisation
as author is matched on its first word.

usage: python reconcile_citations.py <document> [--bib-heading "Bibliography"] [--bib-start LINE] [--verbose]

Locating the list: a Markdown heading (`## References`); failing that, a bare label line
(`References` alone on its line) followed by entry-shaped lines, which is how PDF extractions
in the reading store print it; failing that, only a position the operator declares with
`--bib-start LINE` (1-based, the first entry line). An undeclared position is never used: the
tool names the likeliest run and fails. `## PDF page N` markers and running heads or feet that
recur down the document are not part of the list and do not end it.
Undated citations count: `(Author, n.d.)` is matched against an `n.d.` bibliography entry
like any other, and an unresolved one is a FAIL rather than a silence.

exit:  0 clean, 1 FAIL, 2 REPORT only
"""
import sys, re, io, hashlib
try:                                   # reconfigure, never replace: an orphaned wrapper
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # closes the caller's buffer
except (AttributeError, ValueError):   # not a TextIOWrapper, e.g. under a test harness
    pass
NAME = r"[A-Z][A-Za-zÀ-ſ'’\-]+"
DATED = r"(?:1[6-9]|20)\d\d[a-z]?"
NO_DATE = r"n\.\s?d\."
# An undated work is still a cited work. Requiring digits made `(Author, n.d.)` invisible to
# both inventories, so an unresolved undated citation reported clean (review, 2026-09-20).
YEAR = r"(?:" + DATED + r"|" + NO_DATE + r")"
BIB_HEADINGS = ("bibliography", "references", "reference list", "works cited")
# The reading store marks each PDF page with a heading. It is extraction apparatus, not a
# section of the document: treating it as one ended every reference list at its first page
# break (C-03, 2026-09-23).
PAGE_MARKER_RE = re.compile(r"^#{1,6}\s+PDF page \d+\s*$", re.I)
# A bare label line: the label alone, optionally emphasised or followed by a colon.
LABEL_RE = re.compile(r"^[*_\s]*(" + "|".join(BIB_HEADINGS) + r")[\s:*_]*$", re.I)
# The first line of an entry. Author-led: a family name and a comma, then an initial
# (`A.`, `A `, `A,`) or a given name (`Frank`) -- not any capital, or `Cambridge, MA: MIT`
# as a wrapped line would open an entry. `Management, vol. 3` and `Quantum Mechanics',
# Philosophy` are continuations. Physics style: `Jauch J 1968,`, `Joos E and Zee HD,` -- a
# family name and bare initials. Repeat-author: `———. 1996.` and `(1975) The meaning of`,
# which inherit the names of the entry above.
STATUS = r"(?:in press|in preparation|forthcoming)"
PARTICLE = r"(?:(?:[a-z]{1,3}|Van|Von|De|Del|Della|Der|Den|Di|Du|La|Le|Ten|Ter)\s)?"
# A family name, allowing an OCR spacing diacritic inside it: `Schr¨ odinger`.
FAM = r"[A-Z][A-Za-zÀ-ſ'’\-]+(?:[¨´`ˆ˜]\s?[a-zà-ÿ]+)*"
ENTRY_START_RE = re.compile(
    r"^" + PARTICLE + FAM + r",\s+[A-Z](?:\.|\s|,|$)"                       # Newell, A.
    r"|^" + PARTICLE + FAM + r"\s[A-Z]{1,3}(?:\s*,|\s+(?:and|&)\s|\s+\(?\s*(?:1[6-9]|20)\d\d)")  # Jauch J 1968, Adesman A (2009)
# `Jackson, Frank (1986)`: opens an entry only with a DELIMITED year on the same line, or a
# wrapped `Company, Dordrecht` and `University, August 1993` would.
GIVEN_START_RE = re.compile(r"^" + PARTICLE + FAM + r",\s+[A-Z][a-z]+")
GIVEN_YEAR_RE = re.compile(r"[.(]\s*(?:(?:1[6-9]|20)\d\d|" + STATUS + r")", re.I)
REPEAT_RE = re.compile(r"^(?:[—–_]{2,}|-{3,})\s*[.,]?|^\((?:(?:1[6-9]|20)\d\d[a-z]?|" + STATUS + r")\)", re.I)
NUMBERED_RE = re.compile(r"^(?:\[\d+\]|\d+\.\s|\[[A-Z][A-Za-z+]{0,5}\d{2}[a-z]?\])")   # [3], 3., [ABH18]
# A list-item glyph an extractor left in front of each entry: `\uf0a7Dennett, D. C.`
BULLET_RE = re.compile(r"^[\uf0a7\uf0b7•▪◦·]\s*")


# `Ithaca, N.Y.: Cornell` -- a place and its state, running into the publisher's colon.
PLACE_RE = re.compile(r"^" + FAM + r",\s+(?:[A-Z]\.){1,3}\s*:")
PARTICLES = {"van", "von", "de", "del", "della", "der", "den", "di", "du", "da", "la", "le",
             "ten", "ter", "dos", "das"}


def starts_entry(t):
    """Whether this line opens a bibliography entry rather than continuing one."""
    t = BULLET_RE.sub("", t)
    if PLACE_RE.match(t):
        return False
    return bool(ENTRY_START_RE.match(t) or NUMBERED_RE.match(t) or REPEAT_RE.match(t)
                or (GIVEN_START_RE.match(t) and GIVEN_YEAR_RE.search(t)))
# The author list at the head of an entry whose year comes after the title:
# `Bell, C. G & Newell, A. Computer Structures ... McGraw-Hill 1971`.
AUTHOR_PREFIX_RE = re.compile(
    r"^((?:" + PARTICLE + FAM + r",?\s*(?:[A-Z](?![a-z])\.?\s*)+(?:,|&|and)?\s*)+)")


def norm_year(y):
    """`n. d.` and `n.d.` are one token; a dated year is itself."""
    y = " ".join((y or "").strip().lower().split())
    return "n.d." if re.fullmatch(r"n\.\s?d\.", y) else y


EDGE_LINES = 3


def furniture(lines):
    """Indexes of lines that are page apparatus rather than text: page markers, and running
    heads and feet -- a line among the first or last EDGE_LINES of a `## PDF page` segment whose
    form, numbers masked, sits at an edge on three or more pages. Recurrence alone is not
    enough: `Press.` and `3:417-57.` recur down any reference list and are entry text (C-03).
    Running matter recurs AT THE EDGE, the rule the locator gate uses for folios (F11-04).
    A document without page markers has no furniture."""
    out = {i for i, l in enumerate(lines) if PAGE_MARKER_RE.match(l.strip())}
    if len(out) < 3:
        return out
    bounds = sorted(out) + [len(lines)]
    edges = []
    for a, b in zip(bounds, bounds[1:]):
        body = [i for i in range(a + 1, b) if lines[i].strip()]
        edges.extend(set(body[:EDGE_LINES] + body[-EDGE_LINES:]))
    key = lambda i: re.sub(r"\d+", "#", " ".join(lines[i].split())).casefold()
    pages = {}
    for i in edges:
        pages.setdefault(key(i), set()).add(max(m for m in bounds if m <= i))
    for i in edges:
        t = lines[i].strip()
        if len(t) <= 80 and len(pages[key(i)]) >= 3:
            out.add(i)
    return out


def entry_shaped(lines, i, drop, look=12, need=3):
    """The first substantive line after line i opens an entry, or `need` of the next `look` do.
    The first-line route admits a list of one (a supplement citing a single work)."""
    got = n = 0
    for j in range(i + 1, len(lines)):
        t = lines[j].strip()
        if not t or j in drop:
            continue
        n += 1
        if starts_entry(t):
            got += 1
            if n == 1:
                return True
        if n >= look:
            break
    return got >= need


def section_end(lines, start):
    for j in range(start + 1, len(lines)):
        if re.match(r"^#{1,6}\s+\S", lines[j]) and not PAGE_MARKER_RE.match(lines[j].strip()):
            return j
    return len(lines)


def likeliest_run(lines, drop, window=30):
    """(first line, entry-start count) of the densest entry-shaped window. Named, never used."""
    starts = [i for i, l in enumerate(lines) if i not in drop and starts_entry(l.strip())]
    if len(starts) < 3:
        return None
    best = max(starts, key=lambda i: sum(1 for j in starts if i <= j < i + window))
    return best + 1, sum(1 for j in starts if best <= j < best + window)


def split_doc(text, heading=None, bib_start=None):
    """(body, bibliography, how it was found). `how` is None when there is no list."""
    lines = text.split("\n")
    drop = furniture(lines)
    wanted = [heading.lower()] if heading else BIB_HEADINGS
    start = found = None
    for i, l in enumerate(lines):
        m = re.match(r"^#{1,6}\s+(.*\S)\s*$", l)
        if m and not PAGE_MARKER_RE.match(l.strip()) and m.group(1).strip(" *_").lower() in wanted:
            start, found = i, l.strip()
            break
    if start is None and not heading:
        for i, l in enumerate(lines):
            if LABEL_RE.match(l) and not l.lstrip().startswith("#") and entry_shaped(lines, i, drop):
                start = i
                found = f"{l.strip()} (label line {i + 1}, no Markdown heading)"
                break
    if start is None and bib_start:
        start = bib_start - 2                   # the list begins ON the declared line
        found = f"declared by --bib-start at line {bib_start}"
    if start is None:
        return text, "", None
    end = section_end(lines, start)
    # A second label inside the run (`Works cited` after `References`) is structure, not an
    # entry: it became a year-less entry and a FAIL (C-03).
    bib = [l for j, l in enumerate(lines[start + 1:end], start + 1)
           if j not in drop and not LABEL_RE.match(l)]
    keep = start + 1 if found.startswith("declared") else start   # no heading line to remove
    return "\n".join(lines[:keep] + lines[end:]), "\n".join(bib), found


def families(author_part):
    """family names from the author segment of a bibliography entry, in order."""
    part = re.sub(r"([¨´`ˆ˜])\s+", r"\1", author_part.strip().rstrip("."))   # Schr¨ odinger
    part = re.sub(r"\s+(?:and|&)\s+", ", ", part)
    out = []
    chunks = [x.strip() for x in part.split(",") if x.strip()]
    initials = lambda c: bool(re.fullmatch(r"(?:[A-Z]\.?\s*)+", c))
    # A given name: one to three capitalised words or bare initials -- `Huw`, `K Scarlett`,
    # `Sue V.`. Only ever read as one straight after a bare family name (C-05).
    given = lambda c: bool(re.fullmatch(r"[A-Z][a-zà-ÿ'’\-]*\.?(?:\s+[A-Z][a-zà-ÿ'’\-]*\.?){0,2}", c))
    expect_given = False
    for n, a in enumerate(chunks):
        # Initials belonging to the previous "Family, I." name. The period is optional
        # because the author segment's own trailing period has already been stripped: in
        # "Tester, T. (2026)" that left a bare "T", which was then read as a second family
        # name, so `(Tester, 2026)` failed against its own entry (review, 2026-09-20).
        if re.fullmatch(r"(?:[A-Z]\.?\s*)+", a):
            expect_given = False
            continue
        # Chicago and MLA invert only the first author -- `Price, Huw`, `Adlam, Emily and Carlo
        # Rovelli` -- so the chunk after a bare family name is that author's given name. Read as
        # a second family, `(Price 2011)` found no one-author entry: U2 and U4 resolved 0 of 14
        # (C-05, 2026-09-23).
        if expect_given and given(a):
            expect_given = False
            continue
        toks = a.split()
        popped = False
        while len(toks) > 1 and re.fullmatch(r"(?:[A-Z]\.)+|[A-Z]{1,3}", toks[-1]):
            toks.pop()                                   # "Yu E." / "Van Fraassen B" / "Zee HD"
            popped = True
        family_first = popped or (n + 1 < len(chunks) and initials(chunks[n + 1]))
        fam = [toks.pop()]                               # the family name: "Yu", "Fraassen"
        # A lowercase particle is one wherever it stands; a capitalised one only in a name
        # written family-first -- `Von Neumann J`, `Van Kleeck, M. H.` -- and not `Di Brown`,
        # given name first (C-03; the self-test caught it).
        while toks and toks[-1].lower() in PARTICLES and (toks[-1].islower() or family_first):
            fam.insert(0, toks.pop())                    # ... with its particle: "de Waal"
        expect_given = not toks and not popped           # the chunk was a bare family name
        out.append(" ".join(fam))
    return out


def segments(bib):
    """One string per entry. Blank lines separate entries; so does a line that begins one --
    a PDF extraction wraps entries with no blank line between them, and splitting on blank
    lines alone made a page of entries into one (C-03)."""
    out = []
    for chunk in re.split(r"\n\s*\n", bib):
        cur = []
        for line in chunk.split("\n"):
            t = BULLET_RE.sub("", line.strip())
            if not t:
                continue
            if cur and starts_entry(t):
                out.append(" ".join(cur))
                cur = []
            cur.append(t)
        if cur:
            out.append(" ".join(cur))
    return out


def parse_bib(bib):
    entries = []
    prev_fams = []
    for raw in segments(bib):
        e = re.sub(r"\s+", " ", raw)
        num = None
        m = re.match(r"^\[(\d+)\]\s*|^(\d+)\.\s+", e)
        if m:
            num = int(m.group(1) or m.group(2)); e = e[m.end():]
        repeat = bool(REPEAT_RE.match(e))
        head = None
        # A year straight after the author list is the entry's year. Searching for the first
        # delimited year instead took `Rovelli C 1995;1997, ... 1997` and read title words as
        # family names (C-03).
        a = AUTHOR_PREFIX_RE.match(e)
        y = re.match(rf"\(?\s*({YEAR}|{STATUS})", e[a.end():], re.I) if a else None
        if y:
            head = a.group(1)
        else:
            y = re.search(rf"[.(,]\s*({YEAR}|{STATUS})", e, re.I)
        if not y:
            # Year after the title, as in `... New York McGraw-Hill 1971`. Taken only when the
            # entry opens with an author list that can be read by itself, so the family names
            # never include title words.
            a = AUTHOR_PREFIX_RE.match(e)
            y = re.search(rf"(?<![\w\-]){YEAR}(?![\w\-])", e) if a else None
            head = a.group(1) if a and y else None
        if not y:
            entries.append({"num": num, "raw": e, "year": None, "fams": [], "cited": 0}); continue
        yr = y.group(1) if y.groups() else y.group(0)
        fams = (list(prev_fams) if repeat else
                families(head if head is not None else e[:y.start()]))
        prev_fams = fams
        entries.append({"num": num, "raw": e, "year": norm_year(yr), "fams": fams, "cited": 0})
    return entries


def parse_authors(s):
    s = s.strip().rstrip(",")
    etal = bool(re.search(r"\bet al\.?$", s))
    s = re.sub(r"\s*,?\s*et al\.?$", "", s)
    s = re.sub(r"(’|')s$", "", s)
    names = [re.sub(r"(’|')s$", "", n) for n in re.split(r"\s+(?:and|&)\s+|,\s*", s) if n.strip()]
    return names, etal


def find_citations(body):
    cites, unparsed = [], []
    auth = rf"{NAME}(?:(?:,\s*|\s+(?:and|&)\s+){NAME})*(?:\s+et al\.?)?"
    # narrative: Author (2024, ...) / Author's (2024) / Author and Author (2024)
    for m in re.finditer(rf"({auth})(?:’s|'s)?\s+\(({YEAR})", body):
        cites.append((m.start(), m.group(1), m.group(2), m.group(0)))
    # parenthetical groups: (Author, 2024, pp. ..; Author & Author, 2025, slide 17)
    for g in re.finditer(r"\(([^()]*?\b" + YEAR + r"[^()]*?)\)", body):
        for part in g.group(1).split(";"):
            m = re.match(rf"\s*(?:see |e\.g\.,? |cf\. )?({auth}),?\s+({YEAR})", part)
            if m:
                cites.append((g.start(), m.group(1), m.group(2), "(" + part.strip() + ")"))
            elif part.strip() and not re.match(rf"\s*{YEAR}", part):
                # Citation-shaped, but the author segment did not parse. Dropping these
                # silently let unresolved candidates vanish from the inventory.
                unparsed.append((g.start(), "(" + part.strip()[:80] + ")"))
    seen, out = set(), []
    for pos, a, y, shown in sorted(cites):
        key = (a, y, pos // 40)
        if key not in seen:
            seen.add(key); out.append((pos, a, y, shown))
    nums = []
    for m in re.finditer(r"\[(\d{1,3}(?:\s*[,–\-]\s*\d{1,3})*)\]", body):
        for piece in re.split(r"\s*,\s*", m.group(1)):
            r = re.split(r"\s*[–\-]\s*", piece)
            nums += list(range(int(r[0]), int(r[-1]) + 1)) if len(r) == 2 else [int(r[0])]
    return out, nums, unparsed


def match(entry, names, etal, year):
    if entry["year"] != year or not entry["fams"] or not names:
        return False
    first = names[0].split()[-1].lower() if " " not in names[0] else names[0].split()[0].lower()
    if entry["fams"][0].lower() != first and entry["fams"][0].lower() != names[0].lower():
        return False
    if etal:
        return len(entry["fams"]) >= 3
    if len(names) == 2:
        return len(entry["fams"]) == 2 and entry["fams"][1].lower() == names[1].lower()
    if len(names) >= 3:
        return [f.lower() for f in entry["fams"]] == [n.lower() for n in names]
    return len(entry["fams"]) == 1


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    verbose = "--verbose" in sys.argv
    heading = sys.argv[sys.argv.index("--bib-heading") + 1] if "--bib-heading" in sys.argv else None
    if heading in args: args.remove(heading)
    bib_start = None
    if "--bib-start" in sys.argv:
        v = sys.argv[sys.argv.index("--bib-start") + 1]
        bib_start = int(v)
        if v in args: args.remove(v)
    raw = open(args[0], "rb").read()
    text = raw.decode("utf-8-sig")
    body, bib, found = split_doc(text, heading, bib_start)
    print(f"document sha256[:16] {hashlib.sha256(raw).hexdigest()[:16]} | bibliography heading: {found or 'NOT FOUND'}")
    if found is None:
        lines = text.split("\n")
        cand = likeliest_run(lines, furniture(lines))
        print("FAIL   no bibliography section found; no citation can resolve")
        if cand:
            print(f"REPORT no heading or label line; the most entry-shaped run begins at line {cand[0]} "
                  f"({cand[1]} entry-like lines in 30). Not used: declare it with --bib-start {cand[0]} "
                  f"if that is the reference list")
        sys.exit(1)
    entries = parse_bib(bib)
    cites, nums, unparsed = find_citations(body)
    fails, unparsed_bib = [], [e for e in entries if not e["year"]]
    for pos, a, y, shown in cites:
        names, etal = parse_authors(a)
        y = norm_year(y)
        hits = [e for e in entries if match(e, names, etal, y)]
        if len(hits) == 1:
            hits[0]["cited"] += 1
        else:
            line = body.count("\n", 0, pos) + 1
            fails.append(f"{'NO ENTRY' if not hits else 'AMBIGUOUS (' + str(len(hits)) + ' entries)'}: {shown[:90]}  [about line {line}]")
    by_num = {}
    for e in entries:
        if e["num"] is not None:
            by_num.setdefault(e["num"], []).append(e)
    # A label that names two entries identifies neither. The old dict kept only the last,
    # so `[1]` resolved silently and the shadowed entry was reported merely uncited.
    for n, group in sorted(by_num.items()):
        if len(group) > 1:
            fails.append(f"AMBIGUOUS ({len(group)} entries) share bibliography label [{n}]: "
                         + " || ".join(g["raw"][:45] for g in group))
    for n in nums:
        group = by_num.get(n)
        if not group:
            fails.append(f"NO ENTRY: numeric citation [{n}]")
        elif len(group) == 1:
            group[0]["cited"] += 1
        else:
            for g in group:
                g["cited"] += 1     # already reported ambiguous; do not also report uncited
    uncited = [e for e in entries if e["cited"] == 0]
    undated = sum(1 for _, _, y, _ in cites if norm_year(y) == "n.d.")
    print(f"in-text citations: {len(cites)} author-year ({undated} undated), {len(nums)} numeric"
          f" | bibliography entries: {len(entries)}")
    print(f"resolved: {len(cites) + len(nums) - len(fails)} | unresolved or ambiguous: {len(fails)} | uncited entries: {len(uncited)}")
    for f in sorted(set(fails)): print("FAIL   " + f)
    for e in unparsed_bib: print("FAIL   bibliography entry has no parseable year: " + e["raw"][:90])
    for pos, shown in unparsed:
        print(f"REPORT unparsed citation-shaped text: {shown}  [about line {body.count(chr(10), 0, pos) + 1}]")
    for e in uncited: print("REPORT uncited entry: " + (f"[{e['num']}] " if e["num"] else "") + e["raw"][:90])
    if verbose:
        for e in entries: print(f"   {e['cited']:>2}x {e['fams']} {e['year']}")
    sys.exit(1 if fails or unparsed_bib else (2 if uncited or unparsed else 0))


if __name__ == "__main__":
    main()
