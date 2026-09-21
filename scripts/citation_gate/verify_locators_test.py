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
    case("and the finding names the word that differs",
         "stable" in str(bib("A Comparative Investigation of Resource Sharing in Stable "
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
