#!/usr/bin/env python
"""Negative cases for reconcile_citations.py, from the cross-family review of 2026-09-20.

Each case is a defect the tool shipped with: it reported clean, or reported a failure that
was not there. A parser that only proves it can resolve correct citations proves nothing
about the ones it silently drops.

usage: python reconcile_citations_test.py
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / "reconcile_citations.py"

PAGED = "## PDF page 1\nBody citing (Adlam & Rovelli, 2022) and Bell and Newell (1971).\nAI MAGAZINE Summer 1981 1\n## PDF page 2\nMore body, and (Jackson, 1986).\nAI MAGAZINE Summer 1981 2\n## PDF page 3\nReferences\nAdlam, E. & Rovelli, C. (2022). Information is physical.\nPhilosophy of Physics 1.\nBell, C. G & Newell, A. Computer Structures: Readings and\nAI MAGAZINE Summer 1981 3\n## PDF page 4\nExamples New York McGraw-Hill 1971\nJackson, F. (1986). What Mary didn't know. Journal of\nPhilosophy 83.\nAI MAGAZINE Summer 1981 4\n"

UNLABELLED = 'Claims rest on (Price, 2011) and (Reichenbach, 1956).\n\nPrice, H. (2011). Naturalism without mirrors. Oxford University Press.\nReichenbach, H. (1956). The direction of time. Dover.\nRovelli, C. (2014). Where is knowledge. Unpublished notes.\n'

CASES = [
    (
        "apa_single_author_initial",
        # "Tester, T." lost its period to rstrip, so "T" became a second family name and the
        # citation failed against its own entry.
        "Tester (2026) argues the point, and so does (Tester, 2026).\n"
        "\n## Bibliography\n\nTester, T. (2026). A Work. Journal of Things.\n",
        {"exit": 0, "must_not_contain": ["NO ENTRY", "AMBIGUOUS", "unparsed"]},
    ),
    (
        "duplicate_numeric_labels",
        # Two entries labelled [1]: the dict kept the last, so the citation resolved silently
        # and the shadowed entry was reported merely uncited.
        "First claim [1]. Second claim [2].\n"
        "\n## Bibliography\n\n[1] Alpha. 2020. First. Journal.\n"
        "[1] Beta. 2021. Second. Journal.\n[2] Gamma. 2022. Third. Journal.\n",
        {"exit": 1, "must_contain": ["AMBIGUOUS", "label [1]"]},
    ),
    (
        "undated_unresolved_is_a_failure",
        # (Ghost, n.d.) matched no year pattern, so it vanished from the inventory entirely.
        "An unresolved undated claim (Ghost, n.d.). A dated one (Alpha, 2020, p. 3).\n"
        "\n## Bibliography\n\nAlpha. 2020. First. Journal.\n",
        {"exit": 1, "must_contain": ["NO ENTRY", "(Ghost, n.d.)", "1 undated"]},
    ),
    (
        "undated_resolved_is_clean",
        "A resolved undated one (Tester, n.d.).\n"
        "\n## Bibliography\n\nTester, T. (n.d.). An Undated Work. Journal of Things.\n",
        {"exit": 0, "must_not_contain": ["NO ENTRY"], "must_contain": ["1 undated"]},
    ),
    (
        "narrative_parenthetical_is_not_unparsed",
        # "Tester (2026)" is one citation, not a citation plus a stray "(2026)".
        "Tester (2026) argues the point.\n"
        "\n## Bibliography\n\nTester, T. (2026). A Work. Journal of Things.\n",
        {"exit": 0, "must_not_contain": ["unparsed"]},
    ),
    # --- C-03, 2026-09-23: the reading store's reference lists -----------------------------
    (
        "label_line_wrapped_entries_across_page_breaks",
        # A bare `References` line with no `#`; entries wrapping with no blank line between;
        # `## PDF page N` inside the list; a running foot between entries; a year after the
        # title. All five corpus units exited "no bibliography section found" before this.
        PAGED,
        {"exit": 0, "must_contain": ["label line", "bibliography entries: 3", "resolved: 3"],
         "must_not_contain": ["NO ENTRY", "no parseable year", "NOT FOUND"]},
    ),
    (
        "repeat_author_entries_open_and_inherit",
        # `(1975) The meaning of` and `———. 1996.` open entries and take the names above them;
        # each was swallowed by the entry before it.
        "Cites (Putnam, 1975), (Putnam, 1978) and (Rouse, 1996).\n"
        "\nReferences\n"
        "Putnam, H. (1974) Comment on Sellars. Synthese 27.\n"
        "(1975) The meaning of meaning. In: Mind, language and\n"
        "reality. Cambridge University Press.\n"
        "(1978) Meaning and the moral sciences. Routledge.\n"
        "Rouse, J. 1987. Knowledge and power.\n"
        "———. 1996. Engaging science.\n",
        {"exit": 2, "must_contain": ["bibliography entries: 5", "resolved: 3", "uncited entries: 2"],
         "must_not_contain": ["NO ENTRY"]},
    ),
    (
        "physics_style_and_capitalised_particles",
        # `Jauch J 1968,` -- family and bare initials -- and `Van Fraassen B`, whose capitalised
        # particle is part of the family name because the name is written family-first.
        "See (Jauch, 1968) and (Joos & Zee, 1985).\n"
        "\nReferences\n"
        "Jauch J 1968, Foundations of Quantum Mechanics ,\n"
        "Adison Wesley.\n"
        "Joos E and Zee HD 1985, Zeitschrift fur Physik B59, 223\n"
        "Van Fraassen B 1991, Quantum Mechanics: an Empiri-\n"
        "cist View , Oxford University Press\n",
        {"exit": 2, "args": ["--verbose"],
         "must_contain": ["bibliography entries: 3", "resolved: 2", "['Van Fraassen'] 1991",
                          "['Joos', 'Zee'] 1985"],
         "must_not_contain": ["NO ENTRY", "no parseable year"]},
    ),
    (
        "wrapped_places_and_dates_are_continuations",
        # `Ithaca, N.Y.:`, `University, August 1993`, `Quantenmechanik, Springer` and
        # `Cambridge, MA:` have the shape of an author line; each opened a spurious entry.
        "Cites (Newman, 1993), (Rouse, 1996) and (Winograd, 1986).\n"
        "\nReferences\n"
        "Newman, E. T. (1993). Talk at the inaugural ceremony. Penn State\n"
        "University, August 1993.\n"
        "Rouse, J. (1996). Engaging science.\n"
        "Ithaca, N.Y.: Cornell University Press.\n"
        "Von Neumann, J. (1932). Mathematische Grundlagen der\n"
        "Quantenmechanik, Springer, Berlin.\n"
        "Winograd, T. (1986). Understanding computers.\n"
        "Cambridge, MA: MIT Press.\n",
        {"exit": 2, "args": ["--verbose"],
         "must_contain": ["bibliography entries: 4", "resolved: 3", "['Von Neumann'] 1932"],
         "must_not_contain": ["NO ENTRY", "no parseable year"]},
    ),
    (
        "particle_kept_in_entry_given_name_is_not_one",
        # The entry keeps `de Waal`. The CITATION `(de Waal, 1986)` is not parsed at all --
        # find_citations wants one capitalised word -- and must be REPORTED, never dropped.
        # `Di Brown`, given name first, must not become a family `Di Brown`: the tool's own
        # self-test document caught that in the 58-document regression diff.
        "Cites (de Waal, 1986) and (Brown et al., 2021).\n"
        "\n## Bibliography\n\n"
        "de Waal, F. (1986). Deception in the natural communication of chimpanzees. Book.\n\n"
        "Di Brown, Ed Green, and Flo White. 2021. Third. Venue.\n",
        {"exit": 2, "args": ["--verbose"],
         "must_contain": ["resolved: 1", "['de Waal'] 1986", "['Brown', 'Green', 'White'] 2021",
                          "unparsed citation-shaped text: (de Waal, 1986)"],
         "must_not_contain": ["NO ENTRY", "['Di Brown'"]},
    ),
    (
        "alphanumeric_labels_and_bullet_glyphs",
        "Cites (Dennett, 1988) and (Markus & Nurius, 1986).\n"
        "\nReferences\n"
        "\uf0a7Dennett, D. C. (1988). Precis of the intentional stance. BBS 11.\n"
        "\uf0a7Markus, H., & Nurius, P. (1986). Possible selves.\n"
        "\nWorks cited\n"
        "[ABH18] van der Aalst, W. M. P.; Bichler, M.: Robotic process automation, 2018.\n",
        {"exit": 2, "must_contain": ["label line", "bibliography entries: 3", "resolved: 2",
                                     "uncited entries: 1"],
         "must_not_contain": ["NO ENTRY", "no parseable year"]},
    ),
    (
        "table_of_contents_label_is_not_the_list",
        # A `References` line in a contents list is followed by more contents, not entries.
        "Contents\nIntroduction\nReferences\nAppendix\n"
        "\n## Introduction\n\nAs argued (Price, 2011).\n"
        "\nReferences\n"
        "Price, H. (2011). Naturalism without mirrors. Oxford University Press.\n",
        {"exit": 0, "must_contain": ["label line 11", "resolved: 1"],
         "must_not_contain": ["NO ENTRY", "label line 4"]},
    ),
    (
        "unlabelled_list_is_named_never_used",
        # No heading and no label: the tool names the likeliest run and still fails. A
        # position it chose for itself is a guess.
        UNLABELLED,
        {"exit": 1, "must_contain": ["no bibliography section found",
                                     "most entry-shaped run begins at line 4", "Not used"]},
    ),
    (
        "declared_bib_start_is_used",
        UNLABELLED,
        {"exit": 2, "args": ["--bib-start", "4"],
         "must_contain": ["declared by --bib-start at line 4", "resolved: 2", "uncited entries: 1"],
         "must_not_contain": ["NO ENTRY"]},
    ),
    # --- C-05, 2026-09-23: Chicago and MLA invert only the first author ---------------------
    (
        "chicago_given_name_is_not_a_family",
        # `Price, Huw` parsed as families ['Price', 'Huw'], so the one-name citation found no
        # one-author entry; U2 and U4 resolved 0 of 14. `Adlam, Emily and Carlo Rovelli` is two
        # authors, and a same-year single-author `Rovelli, Carlo` must stay distinct from it.
        "As argued (Price 2011), (Rovelli 2022) and (Adlam & Rovelli 2022).\n"
        "\nReferences\n"
        "Adlam, Emily and Carlo Rovelli (2022) Information is physical. Philosophy of Physics 1.\n"
        "Price, Huw (2011) Naturalism without mirrors. Oxford University Press.\n"
        "Rovelli, Carlo (2022) Agency in physics. Unpublished.\n",
        {"exit": 0, "args": ["--verbose"],
         "must_contain": ["resolved: 3", "['Adlam', 'Rovelli'] 2022", "['Price'] 2011",
                          "['Rovelli'] 2022"],
         "must_not_contain": ["NO ENTRY", "AMBIGUOUS", "'Huw'", "'Emily'", "'Carlo'"]},
    ),
    (
        "one_name_still_needs_a_one_author_entry",
        # The names now parse; the matching rule is unchanged. `(Kingsley 2020)` against a
        # two-author entry still fails -- U4 prints exactly this -- and must not be loosened by
        # accident while names are being fixed.
        "As argued (Kingsley 2020).\n"
        "\nReferences\n"
        "Kingsley, K Scarlett and Richard Parry (2020) Empedocles. Stanford Encyclopedia.\n",
        {"exit": 1, "args": ["--verbose"],
         "must_contain": ["AUTHORS DIFFER (citation parsed as 1; entry parsed as 2 ['Kingsley', 'Parry'])",
                          "['Kingsley', 'Parry'] 2020", "uncited entry"],
         # It is a failure with a true name, not a resolution: never NO ENTRY, never resolved.
         "must_not_contain": ["'Scarlett'", "NO ENTRY", "resolved: 1"]},
    ),
    # --- the two misreadings, and what fixing them ran into, 2026-09-23 ------------------------
    (
        "year_after_title_reads_the_author_prefix",
        # `Berliner ... Artificial Intelligence, 1980` parsed as ['Berliner', 'Intelligence'].
        # A hyphenated initial (`Ewert, J.-P.`) was kept as a name. Editor markers were names.
        "As shown by Berliner (1980), (Simon, 1969), Ewert's (1987) and (Roitblat, Bever & Terrace, 1984).\n"
        "\nReferences\n"
        "Berliner, H. J. Backgammon computer program beats world champion Artificial\n"
        "Intelligence, 1980, 14, 205-220\n"
        "Simon, H A Science of the Artificial Cambridge, MA: MIT Press, 1969\n"
        "Ewert, J.-P. (1987) Neuroethology of releasing mechanisms. BBS 10.\n"
        "Roitblat, H. L., Bever, T. G. & Terrace, H. S., eds. (1984) Animal cognition. Erlbaum.\n",
        {"exit": 0, "args": ["--verbose"],
         "must_contain": ["resolved: 4", "['Berliner'] 1980", "['Simon'] 1969", "['Ewert'] 1987",
                          "['Roitblat', 'Bever', 'Terrace'] 1984"],
         "must_not_contain": ["Intelligence'", "'J.-P'", "'eds'", "NO ENTRY", "AUTHORS DIFFER"]},
    ),
    (
        "author_lists_the_prefix_must_not_cut_short",
        # Each of these lost an author to a prefix reading before it was guarded: an
        # organisation after a connector, a two-name author with given names, an OCR-mangled
        # `&` (`or`, `6:`), an accent split before its letters, a hyphenated surname.
        "Cites (Rumelhart, McClelland & Group, 1986), (Kingsley & Parry, 2020), (Brown & Fish, 1983),\n"
        "(Nicolis & Prigogine, 1977) and (Corrales-Garay et al., 2024).\n"
        "\nReferences\n"
        "Rumelhart, D. E., McClelland, J. L. & the PDP Research Group (1986) Parallel distributed processing.\n"
        "Kingsley, K Scarlett and Richard Parry ( 2020 ) Empedocles, in The Stanford Encyclopedia.\n"
        "Brown, R. or Fish, D. (1983) The psychological causality implicit in language.\n"
        "Nicolis, G. 6: Prigogine, I. (1977) Self-organization in nonequilibrium systems.\n"
        "Corrales-Garay, D., Rodríguez-S ´anchez, J.L., Montero-Navarro, A., 2024. Co-creating value.\n",
        {"exit": 0, "args": ["--verbose"],
         "must_contain": ["resolved: 5", "['Rumelhart', 'McClelland', 'Group'] 1986",
                          "['Kingsley', 'Parry'] 2020", "['Brown', 'Fish'] 1983",
                          "['Nicolis', 'Prigogine'] 1977",
                          "['Corrales-Garay', 'Rodríguez-S´anchez', 'Montero-Navarro'] 2024"],
         "must_not_contain": ["NO ENTRY", "AUTHORS DIFFER", "'the'", "'Rodríguez-S']"]},
    ),
]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    failures = []
    with tempfile.TemporaryDirectory(prefix="reconcile-cases-") as tmp:
        for name, body, want in CASES:
            path = Path(tmp) / f"{name}.md"
            path.write_text("# T\n" + body, encoding="utf-8")
            run = subprocess.run([sys.executable, str(TOOL), str(path)] + want.get("args", []),
                                 capture_output=True, text=True, encoding="utf-8",
                                 errors="replace")
            out = run.stdout
            problems = []
            if run.returncode != want["exit"]:
                problems.append(f"exit {run.returncode}, expected {want['exit']}")
            for needle in want.get("must_contain", []):
                if needle not in out:
                    problems.append(f"missing {needle!r}")
            for needle in want.get("must_not_contain", []):
                if needle in out:
                    problems.append(f"unexpected {needle!r}")
            if problems:
                failures.append(f"{name}: " + "; ".join(problems))
                print(f"  FAIL {name}: {'; '.join(problems)}")
                print(re.sub(r"^", "        ", out.strip(), flags=re.M))
            else:
                print(f"  OK   {name}")

    if failures:
        print(f"\n[BLOCKER] {len(failures)} case(s) failed")
        return 1
    print(f"\nOK reconcile_citations_test — {len(CASES)}/{len(CASES)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
