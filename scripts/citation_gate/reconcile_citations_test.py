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
]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    failures = []
    with tempfile.TemporaryDirectory(prefix="reconcile-cases-") as tmp:
        for name, body, want in CASES:
            path = Path(tmp) / f"{name}.md"
            path.write_text("# T\n" + body, encoding="utf-8")
            run = subprocess.run([sys.executable, str(TOOL), str(path)],
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
