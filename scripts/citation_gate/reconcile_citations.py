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

usage: python reconcile_citations.py <document> [--bib-heading "Bibliography"] [--verbose]
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


def norm_year(y):
    """`n. d.` and `n.d.` are one token; a dated year is itself."""
    y = (y or "").strip().lower()
    return "n.d." if re.fullmatch(r"n\.\s?d\.", y) else y


def split_doc(text, heading=None):
    lines = text.split("\n")
    wanted = [heading.lower()] if heading else BIB_HEADINGS
    start = end = None
    for i, l in enumerate(lines):
        m = re.match(r"^#{1,6}\s+(.*\S)\s*$", l)
        if not m:
            continue
        if start is None and m.group(1).strip(" *_").lower() in wanted:
            start = i
        elif start is not None and end is None:
            end = i
    if start is None:
        return text, "", None
    end = end if end is not None else len(lines)
    return "\n".join(lines[:start] + lines[end:]), "\n".join(lines[start + 1:end]), lines[start].strip()


def families(author_part):
    """family names from the author segment of a bibliography entry, in order."""
    part = re.sub(r"\s+(?:and|&)\s+", ", ", author_part.strip().rstrip("."))
    out = []
    for a in [x.strip() for x in part.split(",") if x.strip()]:
        # Initials belonging to the previous "Family, I." name. The period is optional
        # because the author segment's own trailing period has already been stripped: in
        # "Tester, T. (2026)" that left a bare "T", which was then read as a second family
        # name, so `(Tester, 2026)` failed against its own entry (review, 2026-09-20).
        if re.fullmatch(r"(?:[A-Z]\.?\s*)+", a):
            continue
        toks = a.split()
        if len(toks) > 1 and all(re.fullmatch(r"(?:[A-Z]\.)+|[A-Z]", t) for t in toks[1:]):
            out.append(toks[0])                          # "Yu E." / "Yu, E."
        else:
            out.append(toks[-1])                         # "Eric Yu"
    return out


def parse_bib(bib):
    entries = []
    for raw in [b.strip() for b in re.split(r"\n\s*\n|\n(?=\[\d+\]|\d+\.\s)", bib) if b.strip()]:
        e = re.sub(r"\s+", " ", raw)
        num = None
        m = re.match(r"^\[(\d+)\]\s*|^(\d+)\.\s+", e)
        if m:
            num = int(m.group(1) or m.group(2)); e = e[m.end():]
        y = re.search(rf"[.(,]\s*({YEAR})", e)
        if not y:
            entries.append({"num": num, "raw": e, "year": None, "fams": [], "cited": 0}); continue
        entries.append({"num": num, "raw": e, "year": norm_year(y.group(1)),
                        "fams": families(e[:y.start()]), "cited": 0})
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
    raw = open(args[0], "rb").read()
    body, bib, found = split_doc(raw.decode("utf-8-sig"), heading)
    print(f"document sha256[:16] {hashlib.sha256(raw).hexdigest()[:16]} | bibliography heading: {found or 'NOT FOUND'}")
    if found is None:
        print("FAIL   no bibliography section found; no citation can resolve"); sys.exit(1)
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
