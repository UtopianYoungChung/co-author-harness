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
         vl.citation_targets("(Yu, 2024, p. 211)", CFG), ([("yu2024", (211, 211))], None))
    targets, why = vl.citation_targets("(Yu, 2024, pp. 211-214)", CFG)
    case("a page range is read as a span", targets, [("yu2024", (211, 214))])
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
         sorted([("yu2024", (11, 11)), ("smith2025", (7, 7))]))
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
    nextline = [(l, s, pre) for l, s, pre in found if l == 4]
    case("a citation on its own line finds the claim before it",
         bool(nextline) and nextline[0][2].startswith("Authority shifts"), True)
    case("an ordinary sentence needs no preamble",
         [pre for l, _, pre in found if l == 6], [""])

    # --- what a citation's scope leaves unaccounted for -------------------------------------
    def frags(scope, covering, frame=()):
        return [f for f, _ in vl.uncovered_residue(scope, covering, frame)]

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

    # The citation's own attribution is not an element. This is the one thing the residue
    # disposes of besides function words, and it is a named list rather than a length.
    cov_narr = [check("Participants share resources")]
    case("a reporting verb after a narrative citation is not an element",
         frags(" states: Participants share resources", cov_narr, {"tester"}), [])
    case("nor is the cited author's own name",
         frags(" Tester argues that Participants share resources", cov_narr, {"tester"}), [])
    case("but a negation inside the attribution still reports",
         len(frags(" states: Participants never share resources", cov_narr, {"tester"})), 1)
    case("and a subject that is not the cited author still reports",
         frags("Analysis shows Participants share resources", cov_narr, {"tester"}),
         ["Analysis shows"])

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

    if failures:
        print(f"\n[BLOCKER] {len(failures)} case(s) failed")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nOK verify_locators_test — all cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
