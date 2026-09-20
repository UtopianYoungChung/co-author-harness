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
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
CLASSES = ["VERBATIM", "PARAPHRASE", "MAPPED", "EXTENDED"]   # strongest -> weakest


class GateUnavailable(RuntimeError):
    """The gate cannot run here at all. An environment fault, not a verdict about citations.

    Reported as GATE_UNAVAILABLE and exit 3 so a caller can tell it apart from a crash: a
    crash means the evidence was not examined and must block, while this means the checker's
    machine cannot examine it and the citations simply stay unverified.
    """

CACHE = os.path.join(os.path.expanduser("~"), ".claude", "cache", "locator-text")

def norm(s):
    s = unicodedata.normalize("NFKD", s).replace("\u00ad", "").lower()
    return re.sub(r"[^a-z0-9]", "", s)

def pages_of(pdf):
    os.makedirs(CACHE, exist_ok=True)
    st = os.stat(pdf)
    key = hashlib.sha256(f"{os.path.abspath(pdf)}|{st.st_size}|{st.st_mtime_ns}".encode()).hexdigest()[:24]
    cp = os.path.join(CACHE, key + ".json")
    if os.path.exists(cp):
        return json.load(open(cp, encoding="utf-8"))
    try:
        import fitz
    except ImportError:
        raise GateUnavailable(
            "PyMuPDF (fitz) is not installed, so no page text can be read and no quote can "
            "be bound. Install it with: pip install pymupdf")
    d = fitz.open(pdf)
    out = [norm(d[i].get_text()) for i in range(d.page_count)]
    json.dump(out, open(cp, "w", encoding="utf-8"))
    return out

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
CITE_YEAR_RE = re.compile(r"\b((?:1[89]|20)\d\d)[a-z]?\b|(n\.\s?d\.)")
FAMILY_RE = re.compile(r"\b([A-Z][A-Za-z\u00c0-\u017f'\u2019\-]{1,})\b")
BIB_HEADING_RE = re.compile(r"^#{1,6}\s+(?:Bibliography|References|Works Cited)\s*$", re.I)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\[\u201C\"])")


def flat(text):
    return re.sub(r"\s+", " ", text).strip()


def cited_sentences(doc_text):
    """(line, sentence, preamble) for every sentence carrying a citation.

    `preamble` is the rest of the same paragraph before that sentence. A citation written on
    its own line - a display quotation's attribution, a citation wrapped past the margin -
    has nothing before it on its own line, and an empty scope used to count as a fully
    covered one, so a wholly unchecked claim cleared (2026-09-20 review, finding G3).

    Headings are inventoried rather than skipped. A heading that carries a citation makes a
    cited claim like any other line, and skipping it meant the claim was never looked at.
    """
    lines = doc_text.split("\n")
    stop = next((i for i, l in enumerate(lines) if BIB_HEADING_RE.match(l.strip(" *"))), len(lines))
    out, para = [], []
    for n, l in enumerate(lines[:stop], 1):
        if not l.strip():
            para = []                      # a blank line ends the paragraph, and the scope
            continue
        text = l.strip()
        if text.startswith("#"):
            para = []                      # a heading opens its own scope
            text = text.lstrip("#").strip()
            if not text:
                continue
        for sent in SENTENCE_SPLIT_RE.split(text):
            if CITED_SENTENCE_RE.search(sent):
                out.append((n, flat(sent), flat(" ".join(para))))
            para.append(sent)
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
        elif derive_terms(r):
            out.append((r, "no check for this citation accounts for it"))
    return out


MAX_NUMERIC_RANGE = 50   # "[1-400]" is not a citation this tool will enumerate


def member_page_span(text):
    """The page span a single citation member states, or None."""
    pm = PAGE_IN_CITATION_RE.search(text)
    if not pm:
        return None
    lo = int(pm.group(1))
    return (lo, int(pm.group(2)) if pm.group(2) else lo)


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


def author_year_keys(text, sources):
    """Source keys one author-year member names."""
    ym = CITE_YEAR_RE.search(text)
    if not ym:
        return []
    year = re.sub(r"\s+", "", ym.group(1) or ym.group(2)).lower()
    families = {f.lower() for f in FAMILY_RE.findall(text[:ym.start()])}
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


def citation_targets(citation, cfg):
    """([(source key, the page span THAT member states)], why it could not fully resolve).

    Every member of a grouped citation is inventoried and resolved on its own, and each
    carries its own locator. A citation that names three works and resolves one is not a
    resolved citation: the unresolved members used to be dropped silently, leaving the first
    valid member to clear the whole group (2026-09-20 review, finding G1).
    """
    sources = cfg.get("sources", {})
    resolved, unresolved = [], []

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
            keys = author_year_keys(part, sources)
            if keys:
                span = member_page_span(part)
                resolved.extend((k, span) for k in keys)
            else:
                unresolved.append(part)

    if not resolved:
        return [], "names no source in this checks file"
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
    doc_flat = flat(doc_text) if doc_text is not None else None
    unbound_claims = []
    src = {k: dict(v, pages=pages_of(v["pdf"])) for k, v in cfg["sources"].items()}
    fails, best = [], {}
    cov_rows, no_claim = [], 0
    for c in cfg["checks"]:
        cid, s = c["id"], src[c["source"]]
        q, cls = norm(c["quote"]), c.get("class", "")
        idx = c["page"] - s.get("offset", 0) - 1
        problems = []
        if cls not in CLASSES:
            problems.append(f"bad class '{cls}'")
        if len(q) < 25:
            problems.append("quote too short to bind (<25 alnum chars)")
        if not (0 <= idx < len(s["pages"])) or q not in s["pages"][idx]:
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
            cursor = 0
            for m in CITATION_RE.finditer(sentence):
                n_citations += 1
                citation = m.group(0)
                scope, cursor = sentence[cursor:m.start()], m.end()
                if not scope.strip():
                    # Nothing precedes the citation on its own line, so its claim is the rest
                    # of the paragraph. An empty scope must never read as a covered one.
                    scope = preamble
                targets, why = citation_targets(citation, cfg)
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
                right_source = [c for c in matched
                                if any(c["source"] == k
                                       and (span is None
                                            or (str(c["page"]).isdigit()
                                                and span[0] <= int(c["page"]) <= span[1]))
                                       for k, span in targets)]
                if matched and not right_source:
                    stated = ", ".join(sorted(keys))
                    spans = {k: sp for k, sp in targets if sp}
                    same_work = [c for c in matched if c["source"] in keys]
                    clash = next((c for c in same_work if spans.get(c["source"])), None)
                    if clash is not None:
                        lo, hi = spans[clash["source"]]
                        detail = (f"the check(s) for {stated} bind p."
                                  + str(sorted({c["page"] for c in same_work}))
                                  + f", but the citation states p.{lo}"
                                  + (f"-{hi}" if hi != lo else ""))
                    else:
                        detail = ("the check(s) covering it cite "
                                  + ", ".join(sorted({c["source"] for c in matched}))
                                  + f", not {stated}")
                    uncovered.append((line_no, citation, scope.strip() or citation, detail))
                    continue
                for residue, why in uncovered_residue(scope, right_source):
                    uncovered.append((line_no, citation, residue, why))
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
    if verbose:
        for e in elements:
            if e in best: print(f"ok {best[e][0]:10s} [{e}] via {best[e][1]}")
    sys.exit(1 if fails or unsupported or hard_doc_problems or uncovered else 0)

if __name__ == "__main__":
    main()
