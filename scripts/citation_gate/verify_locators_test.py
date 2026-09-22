#!/usr/bin/env python
"""Unit cases for verify_locators.py's citation-bound coverage (repair f, 2026-09-20).

Coverage used to be "any check's claim_text appears anywhere in the sentence". The
cross-family review showed that tests nothing: a check for one clause cleared the rest of the
sentence, a check naming one work cleared a citation naming another, and numeric citations
were not inventoried at all. These cases hold the repair in place.

Hermetic: exercises the coverage logic directly, so no PDF or corpus is needed and the file
travels with the tool when it is vendored into the harness.

usage: python verify_locators_test.py
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("vl", HERE / "verify_locators.py")
vl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vl)

CFG = {
    "sources": {
        "yu2024": {"cite": {"author": "Yu", "year": 2024}},
        "ratto2026": {"cite": {"author": "Ratto", "year": 2026}},
    },
}
CFG_GROUP = {"sources": dict(CFG["sources"],
                             smith2025={"cite": {"author": "Smith", "year": 2025}})}
CFG_NUM = dict(CFG, bib_numbers={"3": "yu2024"})


def check(claim, source="yu2024", page=214):
    return {"claim_text": claim, "source": source, "page": page}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    failures = []

    def case(name, got, want):
        if got != want:
            failures.append(f"{name}: got {got!r}, expected {want!r}")
            print(f"  FAIL {name}: {got!r} != {want!r}")
        else:
            print(f"  OK   {name}")

    # --- every citation form the harness auditor admits must be visible here ---------------
    for label, text in [("author-year", "(Yu, 2024, p. 211)"), ("undated", "(Tester, n.d.)"),
                        ("numeric", "[3]"), ("numeric range", "[3-5]"),
                        ("latex", r"\citep{yu2024}")]:
        case(f"CITATION_RE sees {label}", bool(vl.CITATION_RE.search(text)), True)

    # --- a citation is resolved to the work it names, and the page it states ---------------
    case("author-year resolves to its source",
         vl.citation_targets("(Yu, 2024, p. 211)", CFG), ([("yu2024", frozenset({211}))], None))
    targets, why = vl.citation_targets("(Yu, 2024, pp. 211-214)", CFG)
    case("a page range is read as a span", targets,
         [("yu2024", frozenset({211, 212, 213, 214}))])
    targets, why = vl.citation_targets("(Other, 2025, p. 9)", CFG)
    case("an unknown work does not resolve", (targets, why),
         ([], "names no source in this checks file"))
    targets, why = vl.citation_targets("(Yu, 2026, p. 1)", CFG)
    case("right family, wrong year does not resolve", targets, [])
    targets, why = vl.citation_targets("[3]", CFG)
    case("numeric without a mapping cannot be identified",
         (targets, "bib_numbers" in (why or "")), ([], True))
    case("numeric with a mapping resolves",
         vl.citation_targets("[3]", CFG_NUM), ([("yu2024", None)], None))
    case("a latex key resolves",
         vl.citation_targets(r"\citep{ratto2026}", CFG), ([("ratto2026", None)], None))

    # --- every member of a grouped citation is inventoried (repair j, finding G1) ----------
    targets, why = vl.citation_targets("(Yu, 2024; Unknown, 1999)", CFG)
    case("an unknown member of a group is reported",
         ([k for k, _ in targets], bool(why)), (["yu2024"], True))
    case("a group whose members all resolve is clean",
         vl.citation_targets("(Yu, 2024; Smith, 2025)", CFG_GROUP),
         ([("yu2024", None), ("smith2025", None)], None))
    targets, why = vl.citation_targets("(Yu, 2024, p. 11; Smith, 2025, p. 7)", CFG_GROUP)
    case("each member carries its own locator", sorted(targets),
         sorted([("yu2024", frozenset({11})), ("smith2025", frozenset({7}))]))
    targets, why = vl.citation_targets("[1-3]", {"sources": CFG["sources"],
                                                 "bib_numbers": {"1": "yu2024"}})
    case("a numeric range names every number in it",
         ([k for k, _ in targets], "2" in (why or "")), (["yu2024"], True))
    targets, why = vl.citation_targets(r"\cite{yu2024,ghost}", CFG)
    case("an unknown latex key is reported",
         ([k for k, _ in targets], "ghost" in (why or "")), (["yu2024"], True))

    # --- a citation's scope, including the line before it (repair j, finding G3) -----------
    doc = ("# A cited heading (Yu, 2024, p. 1)\n\nAuthority shifts across the enterprise.\n"
           "(Yu, 2024, p. 1)\n\nAn ordinary sentence (Yu, 2024, p. 1).\n")
    found = vl.cited_sentences(doc)
    case("a cited heading is inventoried", any(l == 1 for l, _, _ in found), True)
    # A citation on the next line is joined into its claim's sentence now that paragraphs are
    # read whole, so the claim sits in the citation's own scope rather than in the preamble.
    # The preamble path still covers a citation that opens a paragraph.
    joined = [(l, sent) for l, sent, _ in found if "Authority shifts" in sent]
    case("a citation on its own line is joined to the claim before it",
         bool(joined) and "(Yu, 2024, p. 1)" in joined[0][1], True)
    case("an ordinary sentence needs no preamble",
         [pre for l, _, pre in found if l == 6], [""])

    # --- what a citation's scope leaves unaccounted for -------------------------------------
    def frags(scope, covering, attribution=""):
        extra = [{"claim_text": attribution}] if attribution.strip() else []
        return [f for f, _ in vl.uncovered_residue(scope, covering + extra)]

    scope = ("Analysis shows mismatches between a role and the agent playing it and all "
             "autonomous systems are always safe")
    covered = [check("mismatches between a role and the agent playing it")]
    residue = frags(scope, covered)
    case("the unchecked clause is residue",
         any("autonomous systems are always safe" in r for r in residue), True)

    case("a fully covered scope leaves nothing",
         frags("mismatches between a role and the agent playing it", covered), [])
    case("an entirely unchecked scope is residue",
         len(frags("all autonomous systems are always safe", [])), 1)
    # A check that does not cover the text contributes no coverage.
    case("an unrelated check covers nothing",
         len(frags(scope, [check("something else entirely different")])), 1)
    # Connective tissue between two covered clauses is not a claim.
    case("a bare connective is disposed of, not reported",
         frags("roles are reassigned and authority shifts",
               [check("roles are reassigned"), check("authority shifts")]), [])

    # --- repair k: disposition replaces the word-count floor (finding G4) -------------------
    # Two content words used to be treated as framing and dropped. "authority shifts" is a
    # claim, and no word count can tell it from "Analysis shows".
    case("a two-word clause is reported, not filtered by length",
         frags("roles are reassigned and authority shifts", [check("roles are reassigned")]),
         ["and authority shifts"])
    case("a reporting frame is reported too, since length cannot excuse it",
         frags("Analysis shows mismatches between a role and the agent playing it", covered),
         ["Analysis shows"])
    # The polarity case: a check for the affirmative must not clear its own negation.
    neg = vl.uncovered_residue("Participants never share resources within stable networks",
                               [check("share resources within stable networks")])
    case("a negation left uncovered is reported", len(neg), 1)
    case("and the reason names the marker",
         bool(neg) and "never" in neg[0][1], True)

    # --- repair k: the class check sees polarity, modality and scope ------------------------
    q = "Participants share resources within stable networks."
    case("an affirmative claim on an affirmative quote is clean",
         vl.marker_delta("Participants share resources within stable networks", q), [])
    case("a negated claim cannot be VERBATIM or PARAPHRASE",
         bool(vl.marker_delta("Participants never share resources", q)), True)
    case("a strengthened claim cannot either",
         bool(vl.marker_delta("All participants always share resources", q)), True)
    case("a flat claim on a hedged quote cannot either",
         bool(vl.marker_delta("RE guides the search", "RE can guide the systematic search")), True)
    # Direction matters: these are the false positives the first cut of this rule produced on
    # the live checks files, and each one must stay clean.
    case("the same negation in different words is not a difference",
         vl.marker_delta("no reference cites a retracted article",
                         "none of the references cite retracted articles"), [])
    case("not-any is the same negation as no",
         vl.marker_delta("empty reference = no original evidence",
                         "references that do not contain any original evidence"), [])
    case("a quantifier inside the quote's noun phrase is not a scope change",
         vl.marker_delta("about a quarter of quotations contain an error",
                         "one fourth of all references is wrong or problematic"), [])
    case("dropping the quote's deontic makes the claim weaker, not stronger",
         vl.marker_delta("direct references to original research sources whenever possible",
                         "Authors should provide direct references to original research "
                         "sources whenever possible."), [])

    # --- repair l: the year suffix names the work (finding G5) ------------------------------
    CFG_SUFFIX = {"sources": {
        "t2026a": {"cite": {"author": "Tester", "year": "2026a"}},
        "t2026b": {"cite": {"author": "Tester", "year": "2026b"}}}}
    for cite, want in [("(Tester, 2026a, p. 1)", ["t2026a"]),
                       ("(Tester, 2026b, p. 1)", ["t2026b"]),
                       ("(Tester, 2026, p. 1)", [])]:
        targets, _ = vl.citation_targets(cite, CFG_SUFFIX)
        case(f"{cite} resolves to {want or 'nothing'}", [k for k, _ in targets], want)

    # --- repair l: the author outside the parentheses (finding G6) --------------------------
    case("a narrative author is read", vl.narrative_author("Tester "), "Tester")
    case("so is a two-author narrative", vl.narrative_author("Yu and Mylopoulos "),
         "Yu and Mylopoulos")
    case("a trailing common noun is not an author", vl.narrative_author("analysis of the data "), None)
    targets, why = vl.citation_targets("(2026a, p. 1)", CFG_SUFFIX, "Tester")
    case("a narrative citation resolves with its author",
         ([k for k, _ in targets], why), (["t2026a"], None))
    targets, why = vl.citation_targets("(2026a, p. 1)", CFG_SUFFIX, None)
    case("and without one it still cannot", [k for k, _ in targets], [])

    # --- repair n: an attribution is a position, not a vocabulary (finding F5) -------------
    # The exemption used to remove any residual word in REPORTING_VERBS. That cleared
    # "... and write (Tester, 2026)", where "write" is a second predicate about the
    # participants. Only the reporting clause following a narrative citation is exempt now,
    # and it is passed in as covered text rather than matched by word list.
    cov_narr = [check("Participants share resources")]
    case("the reporting clause of a narrative citation is covered",
         frags(" states: Participants share resources", cov_narr, " states: "), [])
    case("a reporting verb that is not an attribution is reported",
         frags("Participants share resources and write", cov_narr), ["and write"])
    case("a negation inside the attribution still reports",
         len(frags(" states: Participants never share resources", cov_narr, " states: ")), 1)
    case("a subject that is not the cited author still reports",
         frags("Analysis shows Participants share resources", cov_narr), ["Analysis shows"])
    for tail, want in [(" states: ", True), (", who states: ", True), (" argues that ", True),
                       (" and write ", False), (" resources ", False)]:
        case(f"attribution tail {tail!r}",
             bool(vl.ATTRIBUTION_TAIL_RE.match(tail)), want)

    # --- repair n: the narrative author's position is what is dropped (finding F4) ---------
    case("a narrative author reports where it starts",
         vl.narrative_attribution("All systems are safe according to Tester ")[1] is not None, True)
    name, at = vl.narrative_attribution("All systems are safe according to Tester ")
    case("and the prefix before it survives",
         "All systems are safe according to".startswith(
             "All systems are safe according to"[:at].strip()[:20]), True)
    case("a prefix with no author yields nothing",
         vl.narrative_attribution("analysis of the data "), (None, None))

    # --- repair l: the declared numeric mapping is checked (finding G2) ---------------------
    doc_num = ("Text with a numeric citation [2].\n\n## References\n\n"
               "[1] Tester, A. (2026a). Synthetic Fixture.\n"
               "[2] Other, B. (2025). A Different Work.\n")
    case("a mapping the bibliography contradicts is a failure",
         bool(vl.check_bib_numbers(dict(CFG_SUFFIX, bib_numbers={"2": "t2026a"}), doc_num)), True)
    case("a mapping the bibliography agrees with is clean",
         vl.check_bib_numbers(dict(CFG_SUFFIX, bib_numbers={"1": "t2026a"}), doc_num), [])
    case("a label the bibliography does not carry is a failure",
         bool(vl.check_bib_numbers(dict(CFG_SUFFIX, bib_numbers={"7": "t2026a"}), doc_num)), True)
    case("a mapping with no bibliography to check rests on nothing",
         bool(vl.check_bib_numbers(dict(CFG_SUFFIX, bib_numbers={"1": "t2026a"}),
                                   "Text with a citation [1] and no reference list.")), True)
    case("no declared mapping is nothing to check",
         vl.check_bib_numbers(CFG_SUFFIX, doc_num), [])

    # --- repair o: prescribed is not observed (finding F6) ---------------------------------
    # Repair (k) left deontic modals out of the comparison, reasoning that a claim which drops
    # the quote's "should" is weaker and so over-claims nothing. Wrong: a norm and a report of
    # behaviour are different kinds of claim, and the second does not follow from the first at
    # any strength or under any bridge.
    for text, want in [("Participants should share resources.", True),
                       ("Authors must verify every reference.", True),
                       ("Authors are required to verify references.", True),
                       ("The guideline recommends direct citation.", True),
                       ("Participants share resources.", False),
                       ("Participants shared resources in every case.", False),
                       ("Participants may share resources.", False)]:
        case(f"prescriptive({text[:34]!r})", vl.prescriptive(text), want)

    obs = "Participants share resources within stable networks."
    pre = "Participants should share resources within stable networks."
    case("a norm and a report differ", vl.prescriptive(pre) != vl.prescriptive(obs), True)
    case("two norms do not", vl.prescriptive(pre) != vl.prescriptive("Participants must share"), False)
    case("two reports do not", vl.prescriptive(obs) != vl.prescriptive("Participants share"), False)

    # --- repair p: one author, several years (finding F3) ----------------------------------
    CFG_YEARS = {"sources": {"t2026": {"cite": {"author": "Tester", "year": 2026}},
                             "t2025": {"cite": {"author": "Tester", "year": 2025}}}}
    ONE = {"sources": {"t2026": CFG_YEARS["sources"]["t2026"]}}
    targets, why = vl.citation_targets("(Tester, 2026, 2025, p. 1)", ONE)
    case("a second year with no source is reported",
         ([k for k, _ in targets], "2025" in (why or "")), (["t2026"], True))
    targets, why = vl.citation_targets("(Tester, 2026, 2025, p. 1)", CFG_YEARS)
    case("and resolves when both works are declared",
         (sorted(k for k, _ in targets), why), (["t2025", "t2026"], None))
    case("both years carry the member's page",
         [sorted(sp) for sp in {sp for _, sp in targets}], [[1]])
    # A page range in the 2000s is pages, not years.
    targets, why = vl.citation_targets("(Yu, 2024, pp. 2019-2020)",
                                       {"sources": {"y": {"cite": {"author": "Yu", "year": 2024}}}})
    case("a page range is not read as years",
         ([k for k, _ in targets], [sorted(sp) for _, sp in targets], why),
         (["y"], [[2019, 2020]], None))

    # --- repair p: a numbered entry must be the work (finding F2) ---------------------------
    doc_p = ("Text [1] and [2].\n\n## References\n\n"
             "[1] Tester, A. (2026). Synthetic Fixture. Journal of\n    Software Test Data, 4(2).\n"
             "[2] Tester, A. (2026). A Completely Different Work.\n")
    SRC_P = {"fixture": {"cite": {"author": "Tester", "year": 2026, "title": "Synthetic Fixture"}}}
    case("the entry naming the work is clean",
         vl.check_bib_numbers({"sources": SRC_P, "bib_numbers": {"1": "fixture"}}, doc_p), [])
    case("same author and year, different title, is not",
         bool(vl.check_bib_numbers({"sources": SRC_P, "bib_numbers": {"2": "fixture"}}, doc_p)), True)
    case("a wrapped entry is read whole",
         "Software Test Data" in vl.numbered_bibliography(doc_p)["1"], True)
    doc_sfx = "Text [1].\n\n## References\n\n[1] Tester, A. (2026b). Some Work.\n"
    for y, want in [("2026a", True), ("2026b", False), ("2026", True)]:
        probs = vl.check_bib_numbers(
            {"sources": {"f": {"cite": {"author": "Tester", "year": y, "title": "Some Work"}}},
             "bib_numbers": {"1": "f"}}, doc_sfx)
        case(f"a {y} check against a 2026b entry {'fails' if want else 'passes'}",
             bool(probs), want)

    # --- repair q: an extraction names the bytes it came from (finding F5-05) --------------
    # Needs a real PDF, so it is skipped where pymupdf is absent rather than failing: the
    # rest of this suite is deliberately hermetic.
    try:
        import fitz
    except ImportError:
        print("  SKIP the extraction cache binds its bytes (pymupdf not installed)")
    else:
        import os, tempfile
        with tempfile.TemporaryDirectory(prefix="vl-cache-") as td:
            td = Path(td)
            cache = td / "cache"
            vl.CACHE = str(cache)

            def build(path, sentence):
                doc = fitz.open()
                pg = doc.new_page()
                pg.insert_textbox(fitz.Rect(50, 50, 540, 700), sentence, fontsize=11)
                doc.save(path)
                doc.close()

            live = td / "s.pdf"
            build(live, "Participants share resources within stable networks.")
            first = vl.pages_of(str(live))
            st = os.stat(live)
            other = td / "o.pdf"
            build(other, "Participants spare resources within stable networks.")
            data = other.read_bytes()
            data = (data + b" " * (st.st_size - len(data))) if len(data) < st.st_size else data[:st.st_size]
            live.write_bytes(data)
            os.utime(live, ns=(st.st_atime_ns, st.st_mtime_ns))
            second = vl.pages_of(str(live))
            case("replaced bytes are re-extracted, not served from cache",
                 first["pages"] != second["pages"], True)
            case("the replacement's own text is what comes back",
                 "spare" in second["pages"][0], True)
            # a record that does not name its bytes is ignored
            import json as _json
            key = next(iter(cache.glob("*.json")))
            rec = _json.loads(key.read_text(encoding="utf-8"))
            case("the record names the bytes it came from",
                 isinstance(rec, dict) and len(rec.get("sha256", "")) == 64
                 and "raw" in rec, True)
            key.write_text(_json.dumps({"sha256": "0" * 64, "pages": ["poisoned"]}),
                           encoding="utf-8")
            case("a record naming other bytes is ignored",
                 vl.pages_of(str(live))["pages"] != ["poisoned"], True)

    # --- repair u (S1): a declared page offset must be confirmed by the source ------------
    case("no pages, nothing to confirm", vl.offset_confirmed([], 0)[0], False)
    pages = [f"Body text for this page.{chr(10)}{i + 1}{chr(10)}" for i in range(6)]
    case("an honest offset confirms", vl.offset_confirmed(pages, 0)[0], True)
    case("a wrong offset does not", vl.offset_confirmed(pages, 10)[0], False)
    case("a source stating no numbers cannot confirm",
         vl.offset_confirmed(["Body text with no numerals at all."] * 6, 0)[0], False)
    # the floor scales, so a short document may confirm on the pages it has
    case("a two-page source can confirm on both its pages",
         vl.offset_confirmed([f"Body.{chr(10)}{i+1}{chr(10)}" for i in range(2)], 0)[0], True)
    # but a long one stating numbers on only two pages cannot
    case("a long source with only two numbered pages cannot",
         vl.offset_confirmed(["Body with no numerals."] * 8
                             + [f"Body.{chr(10)}{i+9}{chr(10)}" for i in range(2)], 0)[0], False)
    # a folio stated as "page N of M" counts: the live BMJ source states its pagination that
    # way and states no bare folio at all
    case("'page N of M' is a statement of pagination",
         vl.offset_confirmed([f"Body text. page {i+1} of 6. More body." for i in range(6)], 0)[0],
         True)

    # --- F9-01/F9-02/F9-04: confirmation must establish that the numbers are the pages' ----
    nl_ = chr(10)
    body = "Body text of the page."
    run = lambda head, ns: [f"{head} {n}{nl_}{body}{nl_}" for n in ns]

    # F9-01: the contradiction used to be found by comparing a letter-soup context against a
    # nine-character floor, so a one-letter running head made the contrary number vanish while
    # the confirmation stood.
    case("a long running head confirms its own numbering",
         vl.offset_confirmed(run("Journal of Tests", (1, 2, 3, 4)), 0)[0], True)
    case("and a one-letter one does too",
         vl.offset_confirmed(run("J", (1, 2, 3, 4)), 0)[0], True)
    case("a page printing another number under a long head is refuted",
         bool(vl.page_contradicts(run("Journal of Tests", (1, 2, 3, 99)), 0, 3)), True)
    case("and under a one-letter head just the same",
         bool(vl.page_contradicts(run("J", (1, 2, 3, 99)), 0, 3)), True)

    # F9-02: a sequence that survives the arithmetic in no consistent place is not a pagination
    case("a labelled sequence does not confirm an offset",
         vl.offset_confirmed(run("Experiment", (11, 12, 13)), 10)[0], False)
    case("and varying labels are not a running head",
         vl.offset_confirmed(["Experiment 11" + nl_ + body, "Trial 12" + nl_ + body,
                              "Study 13" + nl_ + body], 10)[0], False)

    # F9-04: the page saying which page it is outranks anything else printed on it
    for label, extra in (("alone", ""), ("beside a copyright year", "Copyright 2024" + nl_),
                         ("beside a DOI", "doi:10.8888/9" + nl_),
                         ("beside a labelled number", "Experiment 11" + nl_)):
        case(f"an explicit page-of-total confirms {label}",
             vl.offset_confirmed([f"Page 1 of 1{nl_}{extra}{body}{nl_}"], 0)[0], True)

    # jergas prints "2/20" in its running foot and nothing else about its pages
    case("N/M in a running foot is the page stating its number",
         vl.offset_confirmed([f"{body}{nl_}Journal, DOI 10.1/x{nl_}{n}/3{nl_}"
                              for n in (1, 2, 3)], 0)[0], True)
    # The guard is on the denominator: disagreeing totals are not a page-of-total statement,
    # so those pages are read as ordinary edge numbers rather than as the page speaking.
    case("a total is read only when the pages agree on one",
         vl.stated_total([f"{body}{nl_}J{nl_}{n}/3{nl_}" for n in (1, 2, 3)]), 3)
    case("and disagreeing totals are no statement at all",
         vl.stated_total([f"{body}{nl_}J{nl_}1/3{nl_}", f"{body}{nl_}J{nl_}2/7{nl_}",
                          f"{body}{nl_}J{nl_}3/9{nl_}"]), None)

    # a folio may open the running foot, owned by nothing at all
    foot = "Journal of Synthetic Data, published by the imaginary review institute."
    case("a folio opening the running foot confirms",
         vl.offset_confirmed([f"{body}{nl_}{body}{nl_}{n} {foot}" for n in (1, 2, 3)], 0)[0],
         True)

    # a bare number in the zone must not silence the folio printed beside it
    tabled = [f"{body}{nl_}{body}{nl_}Journal of Tests {n}" for n in (1, 2)]
    tabled.append(f"{body}{nl_}{body}{nl_}99{nl_}{body}{nl_}Journal of Tests 3")
    case("a table cell does not displace the folio on its own page",
         vl.offset_confirmed(tabled, 0)[0], True)
    case("and does not refute the citation to that page",
         vl.page_contradicts(tabled, 0, 2), None)

    # but a labelled number of equal standing does make a page doubtful
    one = f"Title{nl_}Tester 2026{nl_}{body}{nl_}Journal of Tests 1"
    case("one weak number confirms a one-page source",
         vl.offset_confirmed([one], 0, 2026)[0], True)
    case("two of equal standing do not",
         vl.offset_confirmed([f"Experiment 11{nl_}{one}"], 0, 2026)[0], False)

    # --- repair v1: loose evidence may confirm a pagination, only strict may refute it -----
    # A number in the edge window was folio evidence, so the headings "Section 11/12/13" on a
    # source printing 1, 2, 3 confirmed a declared offset of +10 and the tool announced it
    # (2026-09-21 review, F6-01).
    nl = chr(10)
    heads = [f"Section {i + 11} Body text of the page.{nl}{i + 1}{nl}" for i in range(3)]
    case("a heading number does not confirm an offset",
         vl.offset_confirmed(heads, 10)[0], False)
    case("and the page's own folio still does", vl.offset_confirmed(heads, 0)[0], True)
    case("a labelled number is not read as a folio",
         vl.edge_numbers("Section 11 Body text of this page."), [])
    case("an unlabelled one is", vl.edge_numbers(f"Body text of this page.{nl}11{nl}"), [11])
    # the label must be seen even when it sits at the window's own edge: building the window
    # as head + tail truncated "Section 12" to " 12" and counted it (first cut of v1)
    long_body = "Body text that runs on. " * 12
    case("a label truncated by the window is still a label",
         vl.edge_numbers(f"Section 12 {long_body}"), [])
    case("a number in the body is not edge evidence",
         vl.edge_numbers(f"{long_body}fully 47 of them{nl}{long_body}"), [])

    # F6-02: a document-wide offset does not overrule the folio on the cited page. Only a
    # bare-number line refutes, and only if that number is unique: holldack2026 prints a bare
    # "5" on two pages, and treating that as a folio refuses five correct live checks.
    pages = [f"Body.{nl}1{nl}", f"Body.{nl}2{nl}", f"Body.{nl}99{nl}"]
    case("the cited page's own folio is readable", vl.printed_folios(pages)[2], {99})
    case("a repeated bare number is not a folio",
         vl.printed_folios([f"Body.{nl}5{nl}"] * 3), [set()] * 3)
    case("a page printing nothing states no folio",
         vl.printed_folios(["Body with no numerals."])[0], set())
    case("dates and a DOI at the edge are not a folio",
         vl.printed_folios(["Submitted 28 July 2015 Accepted 9 October 2015 "
                            "DOI 10.7717/peerj.1364"])[0], set())

    # the two tools must read the same page the same way: F5-03 was one tool repaired and its
    # twin left alone, and 9c is now implemented in both
    vs_spec = importlib.util.spec_from_file_location("vs", HERE / "validate_sources.py")
    vs = importlib.util.module_from_spec(vs_spec)
    vs_spec.loader.exec_module(vs)
    probes = [f"Section 11 Body.{nl}1{nl}", f"Body text only.{nl}", f"12 Running head Body.{nl}",
              f"Body.{nl}page 3 of 9{nl}", "Submitted 28 July 2015 DOI 10.7717/peerj.1364",
              f"{long_body}{nl}207{nl}"]
    case("both tools read a page's edge identically",
         [vs.edge_numbers(t) for t in probes], [vl.edge_numbers(t) for t in probes])

    # The case above passed through four repairs while the twins drifted, because it compares
    # the PRIMITIVE and every divergence was in the decisions built on it (F9-05). The rule
    # now lives in one delimited region, copied rather than re-written, and parity is asserted
    # over the region, over the decision, and over the text the decision reads.
    def shared_region(path):
        t = Path(path).read_text(encoding="utf-8")
        o = t.index("# --- shared with the sibling tool")
        c = t.index("# --- end shared region")
        return t[o:c]

    case("the shared folio region is byte-identical in both tools",
         shared_region(HERE / "verify_locators.py") == shared_region(HERE / "validate_sources.py"),
         True)
    for name, const in (("MIN_FOLIO_PAGES", "MIN_FOLIO_PAGES"), ("FOLIO_AGREEMENT", "FOLIO_AGREEMENT"),
                        ("EDGE_CHARS", "EDGE_CHARS"), ("FOLIO_ZONE_LINES", "FOLIO_ZONE_LINES")):
        case(f"both tools use the same {name}", getattr(vs, const), getattr(vl, const))

    # one-, two- and many-page sources, positive and ambiguous, as the reviewer asked
    decisions = [
        ("many pages, bare folios", [f"Body.{nl}{i}{nl}" for i in (1, 2, 3, 4)], 0, None),
        ("many pages, running head", [f"Journal of Tests {i}{nl}Body.{nl}" for i in (1, 2, 3)], 0, None),
        ("many pages, contradicted", [f"Journal of Tests {i}{nl}Body.{nl}" for i in (1, 2, 3, 99)], 0, None),
        ("many pages, wrong offset", [f"Body.{nl}{i}{nl}" for i in (1, 2, 3)], 10, None),
        ("labelled sequence", [f"Experiment {i}{nl}Body.{nl}" for i in (11, 12, 13)], 10, None),
        ("N/M running foot", [f"Body.{nl}J, DOI{nl}{i}/3{nl}" for i in (1, 2, 3)], 0, None),
        ("two pages, bare folios", [f"Body.{nl}{i}{nl}" for i in (1, 2)], 0, None),
        ("two pages with a constant year", [f"Copyright 2024{nl}Body.{nl}{i}{nl}" for i in (1, 2)], 0, 2024),
        ("one page, explicit", [f"Page 1 of 1{nl}Body.{nl}"], 0, None),
        ("one page, explicit beside a year", [f"Page 1 of 1{nl}Copyright 2024{nl}Body.{nl}"], 0, 2024),
        ("one page, two weak numbers", [f"Experiment 11{nl}Body.{nl}Journal of Tests 1"], 0, None),
        ("no numbers anywhere", [f"Body text only.{nl}"] * 4, 0, None),
    ]
    case("both tools decide a page convention identically",
         [vs.offset_confirmed(pp, off, yr) for _, pp, off, yr in decisions],
         [vl.offset_confirmed(pp, off, yr) for _, pp, off, yr in decisions])
    case("and place a folio in the same place",
         [vs.folio_place(vs.folio_evidence(pp, yr), off) for _, pp, off, yr in decisions],
         [vl.folio_place(vl.folio_evidence(pp, yr), off) for _, pp, off, yr in decisions])

    # Identical code still disagreed, because the validator flattened every page before
    # reading it and a folio is found in the line structure. Both extractors, same bytes.
    try:
        import fitz
        d = fitz.open()
        for i, line in enumerate(("Journal of Tests", "Body text of the page.")):
            pg = d.new_page()
            pg.insert_text((72, 72), line)
            pg.insert_text((72, 700), str(i + 1))
        blob = d.tobytes()
        d.close()
        tmp = HERE / "_parity_probe.pdf"
        tmp.write_bytes(blob)
        try:
            case("both tools read the same text from the same bytes",
                 vs.folio_pages(str(tmp)), vl.pages_of(str(tmp))["raw"])
        finally:
            tmp.unlink(missing_ok=True)
            (HERE / "_parity_probe.pages.json").unlink(missing_ok=True)
    except ImportError:
        print("  SKIP extractor parity: pymupdf not installed")

    # --- repair w1: a title is matched as written (finding F6-03) --------------------------
    # "without" and "with" are both function words, so neither survived term derivation and
    # the works were indistinguishable; and a substring test read "stable" inside "unstable".
    case("a relation word distinguishes the work",
         vl.title_parts_absent("Resource Sharing Without Authority",
                               "[2] Tester. (2026). Resource Sharing With Authority."),
         ["without"])
    case("a title word is matched whole",
         bool(vl.title_parts_absent("Resource Sharing in Stable Networks",
                                    "[2] Tester. (2026). Resource Sharing in Unstable Networks.")),
         True)
    case("the entry's own title is accepted",
         vl.title_parts_absent("Resource Sharing Without Authority",
                               "[2] Tester. (2026). Resource Sharing Without Authority. J. Test."),
         [])
    case("a subtitle is matched as its own part",
         vl.title_parts_absent("Resource Sharing: A Study of Networks",
                               "[2] Tester. Resource Sharing - A Study of Networks. J. Test."), [])
    case("a dropped subtitle is reported",
         vl.title_parts_absent("Resource Sharing: A Study of Networks",
                               "[2] Tester. (2026). Resource Sharing. J. Test."),
         ["a", "study", "of", "networks"])

    # --- F7-04: a title is a sequence, and the entry's own title at that ------------------
    # Splitting at colons and asking each part to occur somewhere cleared a reversed title,
    # and cleared one whose required subtitle came from the journal name.
    case("a reversed title is not the same work",
         bool(vl.title_parts_absent("Authority: Resource Sharing",
                                    "[2] T. (2026). Resource Sharing: Authority. J. Test.")),
         True)
    case("and the finding says the order is wrong",
         "not in this order" in vl.title_parts_absent(
             "Authority: Resource Sharing",
             "[2] T. (2026). Resource Sharing: Authority. J. Test.")[0], True)
    case("a subtitle supplied by the journal name is refused",
         bool(vl.title_parts_absent(
             "Authority: Resource Sharing",
             "[2] T. (2026). Authority: Market Competition. Journal of Resource Sharing.")),
         True)
    case("the entry's own title, punctuated differently, is accepted",
         vl.title_parts_absent("Resource Sharing: A Study of Networks",
                               "[2] T. Resource Sharing - A Study of Networks. J."), [])
    case("an ampersand reads as 'and'",
         vl.title_parts_absent("Trust & Authority", "[2] Tester. Trust and Authority."), [])

    # --- repair y: a web rendering is located by section, not by page ---------------------
    # Its pages are the printer's, so the gate asked a document that prints no page numbers to
    # confirm a page convention, and refused three live checks for failing to. What a web page
    # does have is sections (2026-09-21, the three COPE checks).
    nl_y = chr(10)
    # Line structure, because a section locator is a claim about structure: the first version
    # of these fixtures passed one normalised string and could not hold a heading at all.
    web = {"raw": [nl_y.join(["COPE position",
                              "The use of AI tools is expanding rapidly.",
                              "AI tools cannot be listed as an author of a paper.",
                              "Later heading",
                              "Something else entirely."])],
           "web_rendering": True}

    def web_check(**kw):
        base = {"source": "cope", "page": 1,
                "quote": "AI tools cannot be listed as an author of a paper"}
        return dict(base, **kw)

    case("a section locator binds",
         vl.web_locator(web_check(section="COPE position"), web)[0], [])
    case("and reports the render page",
         vl.web_locator(web_check(section="COPE position"), web)[1], 1)
    problems, _ = vl.web_locator(web_check(), web)
    case("no section is UNLOCATED",
         bool(problems) and problems[0].startswith("UNLOCATED"), True)
    case("and the finding says the page is the printout's",
         bool(problems) and "not of the source" in problems[0], True)
    problems, _ = vl.web_locator(web_check(section="A section that is not there"), web)
    case("a section the source has not got is refused",
         bool(problems) and problems[0].startswith("SECTION_NOT_A_HEADING"), True)
    problems, _ = vl.web_locator(web_check(section="Later heading"), web)
    case("a section that does not contain the quote is refused",
         bool(problems) and problems[0].startswith("SECTION_DOES_NOT_CONTAIN_QUOTE"), True)
    problems, _ = vl.web_locator(web_check(quote="Nothing like this is in the rendering"), web)
    case("a quote in no section at all is still not found",
         bool(problems) and problems[0].startswith("QUOTE_NOT_FOUND"), True)
    # the quote is sought in the whole rendering: which printed page it landed on is the
    # printer's business, so a second render page binds the same way
    split = {"raw": [nl_y.join(["COPE position",
                                "The use of AI tools is expanding rapidly."]),
                     "AI tools cannot be listed as an author of a paper."],
             "web_rendering": True}
    problems, render = vl.web_locator(web_check(section="COPE position"), split)
    case("a quote on the second render page still binds", problems, [])
    case("and its render page is named", render, 2)

    # --- repair z1: a folio in a long running foot is still the page's --------------------
    # Anthony et al. 2023 prints "pp. 1672-1694, (c) 2023 INFORMS" and Rani et al. 2025 a
    # Scientific Reports DOI line; at 70 characters the folio of each falls outside the
    # window and the page reads as stating no number (2026-09-21, re-gating the manuscript).
    foot = ("13 | https://doi.org/10.1038/s41598-025-90916-1 "
            "www.nature.com/scientificreports/")
    long_page = "Body text that runs on and on. " * 4 + chr(10) + foot
    case("a folio behind a long footer is read", 13 in vl.edge_numbers(long_page), True)
    case("a number in the middle of the body still is not",
         vl.edge_numbers("Body. " * 40 + "fully 47 of them " + "Body. " * 40), [])
    # and the label rule still holds at the wider width
    case("a labelled number is still not a folio",
         vl.edge_numbers("Section 12 " + "Body text that runs on. " * 3), [])

    # --- repair z2: an author cited in the possessive is still the author ------------------
    # "Ratto et al.'s (2026, pp. 3-6)" matched nothing, so the citation was reported as
    # naming no source -- the author's error, apparently, rather than the tool's.
    for label, text, want in [
            ("et al. possessive", "Drawing on Ratto et al.\u2019s ", "Ratto"),
            ("straight apostrophe", "Drawing on Ratto et al.'s ", "Ratto"),
            ("single-author possessive", "Yu\u2019s ", "Yu"),
            ("two authors, possessive", "Yu and Lapouchnian\u2019s ", "Yu and Lapouchnian"),
            ("no possessive is unchanged", "Drawing on Ratto et al. ", "Ratto"),
            ("a plain name is unchanged", "The models follow Yu ", "Yu")]:
        case(f"narrative author: {label}", vl.narrative_attribution(text)[0], want)
    # a name that merely ends in s keeps its s
    case("a name ending in s is not a possessive",
         vl.narrative_attribution("As Jones ")[0], "Jones")
    # and the citation resolves to its source
    cfg = {"sources": {"ratto2026": {"cite": {"author": "Ratto", "year": 2026}}}}
    name = vl.narrative_attribution("Drawing on Ratto et al.\u2019s ")[0]
    case("and a possessive citation resolves",
         vl.citation_targets("(2026, pp. 3-6)", cfg, name)[0],
         [("ratto2026", frozenset({3, 4, 5, 6}))])

    # --- F7-05: a rule that may overrule a locator may not read more of the page than the
    # rule it overrules. printed_folios scanned every line, so a body table cell -- a
    # standalone "99" under "Sample count" -- refused a correct p.3 citation.
    nl = chr(10)
    edge_pages = [nl.join(["Body.", "Body.", "Body.", "Body.", str(i + 1)]) for i in range(2)]
    table_page = nl.join(["Body line of real prose."] * 6 + ["Sample count", "99"]
                         + ["More body prose."] * 6 + ["3"])
    case("a body table value is not the page's folio",
         vl.printed_folios(edge_pages + [table_page])[2], {3})
    case("a number in the running foot still is",
         vl.printed_folios(edge_pages + [nl.join(["Body."] * 4 + ["99"])])[2], {99})
    case("and one in the running head still is",
         vl.printed_folios(edge_pages + [nl.join(["99"] + ["Body."] * 4)])[2], {99})
    # the refutation these controls must not disarm (F6-02)
    case("a contradicted cited page is still refuted",
         vl.printed_folios([nl.join(["Body.", "1"]), nl.join(["Body.", "2"]),
                            nl.join(["Body.", "99"])])[2], {99})

    # --- F7-06 / F7-02: a section is a heading with an interval, and the quote must be in it
    Q = "Participants share resources within stable networks"
    nl2 = chr(10)

    def rendering(*lines):
        return {"raw": [nl2.join(lines)], "pages": [vl.norm(" ".join(lines))],
                "web_rendering": True}

    def web_case(**kw):
        return dict({"source": "src", "page": 1, "quote": Q, "section": "Methods"}, **kw)

    twice = rendering("Synthetic Fixture", "Abstract", Q + ".", "Methods", Q + ".",
                      "Results", "Other prose entirely.")
    case("a repeated quotation binds inside its cited section",
         vl.web_locator(web_case(), twice)[0], [])
    # F7-02.1 the quote is under Results and the check says Methods
    wrong = rendering("Synthetic Fixture", "Methods", "Body prose of the methods.",
                      "Results", Q + ".")
    problems, _ = vl.web_locator(web_case(), wrong)
    case("a quote under another heading does not bind",
         bool(problems) and problems[0].startswith("SECTION_DOES_NOT_CONTAIN_QUOTE"), True)
    # F7-02.2 the section name occurs only inside prose
    prose = rendering("Synthetic Fixture", "Introduction",
                      "Methods were described in a separate document.", "Results", Q + ".")
    problems, _ = vl.web_locator(web_case(), prose)
    case("a section name inside a sentence is not a heading",
         bool(problems) and problems[0].startswith("SECTION_NOT_A_HEADING"), True)
    case("and the finding says where it does appear",
         bool(problems) and "prose, not a section" in problems[0], True)
    # the positive control
    right = rendering("Synthetic Fixture", "Methods", Q + ".", "Results", "Other prose.")
    case("the quote inside its named section binds",
         vl.web_locator(web_case(), right)[0], [])
    case("a section the source has not got at all is refused",
         bool(vl.web_locator(web_case(section="Nowhere"), right)[0]), True)

    # F7-02.3 the citation's own section locator is read
    case("a citation's section locator is parsed",
         vl.citation_section("(Tester, 2026, Methods section)"), "Methods")
    case("and a page locator is not mistaken for one",
         vl.citation_section("(Tester, 2026, p. 1)"), "")

    # --- no source file may contain a control character where an escape was meant ----------
    # A Git Bash heredoc rewrites \b inside a Python string literal as a literal backspace.
    # The damage is invisible: sed, inspect.getsource and ast all render it as nothing, and
    # only the compiled constants show it. It silently turned "\\bpage N of" into a pattern
    # requiring a backspace character, which matched nothing, while every reading of the file
    # looked correct.
    control = {"\x07": "a", "\x08": "b", "\x0b": "v", "\x0c": "f", "\x00": "0"}
    for sibling in ("verify_locators.py", "verify_locators_test.py", "validate_sources.py",
                    "reconcile_citations.py"):
        f = HERE / sibling
        if not f.is_file():
            continue
        body = f.read_text(encoding="utf-8")
        found = sorted({f"\\{name} written as a raw control character"
                        for ch, name in control.items() if ch in body})
        case(f"{sibling} carries no mangled escape", found, [])

    # --- repair r: a citation wrapped across lines is still seen (finding F5-01) -----------
    nl = chr(10)
    wrapped = f"Participants share resources within stable networks (Tester,{nl}2026, p. 1).{nl}"
    found = vl.cited_sentences(wrapped)
    case("a wrapped citation is inventoried", len(found), 1)
    case("and its sentence carries the whole citation",
         bool(found) and "(Tester, 2026, p. 1)" in found[0][1], True)
    case("a wrapped citation reports the line it starts on",
         bool(found) and found[0][0], 1)
    # paragraphs are joined; a blank line still separates them
    two = f"First paragraph cites (A, 2024).{nl}{nl}Second paragraph cites (B,{nl}2025).{nl}"
    case("each paragraph is enumerated separately", len(vl.cited_sentences(two)), 2)
    case("the second paragraph's line is its own",
         [ln for ln, _, _ in vl.cited_sentences(two)], [1, 3])
    case("a heading is still its own scope",
         len(vl.cited_sentences(f"# A heading (Yu, 2024, p. 1){nl}{nl}Body.{nl}")), 1)

    # --- repair r: the clause after the last citation is disposed of (finding F5-02) -------
    # The trailing clause belongs to no later citation, so discarding it left it accounted
    # for by nothing. An earlier citation's trailing text is the next one's `before`.
    scope = "Participants share resources within stable networks and authority shifts."
    covered = [check("Participants share resources within stable networks")]
    case("an unchecked trailing clause is residue",
         [f for f, _ in vl.uncovered_residue(scope, covered)], ["and authority shifts."])
    case("a fully checked sentence leaves nothing",
         vl.uncovered_residue(scope, [check(scope)]), [])

    # --- repair s: the whole locator, not its first page (finding F5-03) ------------------
    # The same defect as W4 in the wiki producer, repaired there on 2026-09-20 and never
    # looked for here until the cross-tool sweep.
    for text, want_pages, want_ok in [
        ("p. 1", {1}, True),
        ("pp. 1, 99", {1, 99}, True),
        ("pp. 1-3", {1, 2, 3}, True),
        ("pp. 1, 3-4", {1, 3, 4}, True),
        ("pp. 1 and 3", {1, 3}, True),
        ("pp. 3-1", None, False),
        ("pp. 1-400", None, False),
    ]:
        pages, ok = vl.member_pages(text)
        case(f"member_pages({text!r})",
             (set(pages) if pages else None, ok), (want_pages, want_ok))
    case("a member stating no page", vl.member_pages("(Tester, 2026)"), (None, True))
    targets, why = vl.citation_targets("(Yu, 2024, pp. 211, 214)", CFG)
    case("both stated pages reach the target",
         (targets[0][0], sorted(targets[0][1])), ("yu2024", [211, 214]))
    targets, why = vl.citation_targets("(Yu, 2024, pp. 5-1)", CFG)
    case("a locator that cannot be parsed is reported",
         (targets, "cannot parse" in (why or "")), ([], True))

    # --- repair s: a title prefix is not a work identity (finding F5-04) ------------------
    doc_t = ("Text [2].\n\n## References\n\n[1] Other, B. (2000). Irrelevant.\n"
             "[2] Tester, A. (2026). A Comparative Investigation of Resource Sharing in "
             "Dynamic Networks.\n")
    def bib(title):
        return vl.check_bib_numbers(
            {"sources": {"f": {"cite": {"author": "Tester", "year": 2026, "title": title}}},
             "bib_numbers": {"2": "f"}}, doc_t)
    case("a title differing after 40 characters is caught",
         bool(bib("A Comparative Investigation of Resource Sharing in Stable Networks")), True)
    # F8-06 changed the report: it names the entry's title FIELD against the declared title,
    # which is what a reader needs when the two are different works.
    case("and the finding names the entry's title field",
         "title field" in str(bib("A Comparative Investigation of Resource Sharing in Stable "
                                  "Networks")).lower(), True)
    case("the entry's own title is clean",
         bib("A Comparative Investigation of Resource Sharing in Dynamic Networks"), [])

    if failures:
        print(f"\n[BLOCKER] {len(failures)} case(s) failed")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nOK verify_locators_test — all cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
