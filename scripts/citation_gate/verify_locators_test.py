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
    scope = ("Analysis shows mismatches between a role and the agent playing it and all "
             "autonomous systems are always safe")
    covered = [check("mismatches between a role and the agent playing it")]
    residue = vl.uncovered_residue(scope, covered)
    case("an unchecked clause is residue", len(residue), 1)
    case("the residue is the unchecked clause",
         "autonomous systems are always safe" in (residue[0] if residue else ""), True)

    case("a fully covered scope leaves nothing",
         vl.uncovered_residue("mismatches between a role and the agent playing it", covered), [])
    # "Analysis shows" is framing, not a claim: two content words stay below the floor.
    case("framing is not reported as an element",
         vl.uncovered_residue("Analysis shows mismatches between a role and the agent playing it",
                              covered), [])
    case("an entirely unchecked scope is residue",
         len(vl.uncovered_residue("all autonomous systems are always safe", [])), 1)
    # A check that does not cover the text contributes no coverage.
    case("an unrelated check covers nothing",
         len(vl.uncovered_residue(scope, [check("something else entirely different")])), 1)

    if failures:
        print(f"\n[BLOCKER] {len(failures)} case(s) failed")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nOK verify_locators_test — all cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
