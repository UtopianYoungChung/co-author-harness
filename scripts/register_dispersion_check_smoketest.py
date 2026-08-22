#!/usr/bin/env python3
"""Permanent regression tests for register_dispersion_check.py."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "register_dispersion_check.py"
SPEC = importlib.util.spec_from_file_location("register_dispersion_check_under_test", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def check(condition: bool, label: str, detail: object = "") -> None:
    if not condition:
        raise AssertionError(f"{label}: {detail}")


def sentence_set(count: int = 12) -> str:
    openings = (
        "Evidence",
        "The policy",
        "This mechanism",
        "A reviewer",
        "The source",
        "Our analysis",
    )
    verbs = ("supports", "bounds", "clarifies", "tests", "records", "explains")
    return "\n\n".join(
        f"{openings[index % len(openings)]} {verbs[index % len(verbs)]} claim number {index + 1} because the cited record names a concrete boundary."
        for index in range(count)
    )


def case_markdown_and_latex() -> None:
    prose = sentence_set()
    check(MODULE.analyse(prose)["sentences"] == 12, "markdown sentence count")

    slash = "\\"
    latex = (
        f"{slash}begin{{document}}\n"
        f"{slash}begin{{abstract}}{prose}{slash}end{{abstract}}\n"
        f"{slash}begin{{equation}}x = 1.{slash}end{{equation}}\n"
        f"{slash}end{{document}}"
    )
    stripped = MODULE._strip_markup(latex)
    check(MODULE.analyse(latex)["sentences"] == 12, "latex prose preserved")
    check("x = 1" not in stripped, "equation body removed", stripped)


def case_abbreviation_boundaries() -> None:
    ordinary = MODULE.split_sentences("The issue is nuanced. Evidence follows.")
    check(len(ordinary) == 2, "ordinary ed suffix is not abbreviation", ordinary)
    abbreviated = MODULE.split_sentences("Dr. Young wrote this. Evidence follows.")
    check(len(abbreviated) == 2, "complete abbreviation token rejoins", abbreviated)


def base_stats(cv: float, interruption: float) -> dict:
    return {
        "sufficient": True,
        "cv": cv,
        "interruption_rate": interruption,
        "b6_circular": [],
        "b7_nuance": [],
    }


def case_baseline_rules() -> None:
    draft = base_stats(0.19, 0.19)
    baseline = base_stats(0.40, 0.40)
    without = {row["rule"] for row in MODULE.findings_for("draft", draft, None)}
    check(not {"B4", "B5"}.intersection(without), "B4/B5 absent without baseline", without)
    with_baseline = {row["rule"] for row in MODULE.findings_for("draft", draft, baseline)}
    check({"B4", "B5"}.issubset(with_baseline), "B4/B5 fire below baseline ratio", with_baseline)

    boundary = base_stats(0.30, 0.30)
    at_boundary = {row["rule"] for row in MODULE.findings_for("draft", boundary, baseline)}
    check(not {"B4", "B5"}.intersection(at_boundary), "strict-below 0.75 boundary", at_boundary)


def case_b6_and_b7() -> None:
    circular = (
        "Governance structure controls delegated work. "
        "Middle evidence explains how controls operate. "
        "Governance structure controls delegated work."
    )
    check(bool(MODULE.analyse(circular)["b6_circular"]), "B6 circular close detected")

    explained = (
        "The relationship is nuanced. "
        "It depends on whether authority is explicit. "
        "Evidence then fixes the boundary."
    )
    check(not MODULE.analyse(explained)["b7_nuance"], "B7 following explanation clears")

    abandoned = (
        "The relationship is nuanced. "
        "The report repeats that label. "
        "The conclusion repeats the claim."
    )
    check(bool(MODULE.analyse(abandoned)["b7_nuance"]), "B7 abandoned complexity detected")


def invoke(argv: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = MODULE.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def case_cli_exit_codes() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        clean = root / "clean.md"
        clean.write_text(sentence_set(), encoding="utf-8")
        code, output, error = invoke([str(clean), "--json"])
        check(code == 0, "clean CLI exit", (code, output, error))
        json.loads(output)

        circular = root / "circular.md"
        circular.write_text(
            "Governance structure controls delegated work. Middle evidence explains how controls operate. Governance structure controls delegated work.",
            encoding="utf-8",
        )
        code, output, error = invoke([str(circular), "--json"])
        check(code == 1, "finding CLI exit", (code, output, error))
        json.loads(output)

        missing = root / "missing.md"
        code, output, error = invoke([str(missing), "--json"])
        check(code == 2 and not output and "not a file" in error, "missing-file CLI exit", (code, output, error))

        original_read = MODULE.read
        MODULE.read = lambda path: (_ for _ in ()).throw(OSError("simulated read failure"))
        try:
            code, output, error = invoke([str(clean), "--json"])
            check(
                code == 2 and not output and "cannot analyse: simulated read failure" in error,
                "manuscript read failure exit",
                (code, output, error),
            )
            code, output, error = invoke([str(clean), "--baseline", str(clean), "--json"])
            check(
                code == 2 and not output and "cannot analyse: simulated read failure" in error,
                "baseline read failure exit",
                (code, output, error),
            )
        finally:
            MODULE.read = original_read


def main() -> int:
    cases = (
        case_markdown_and_latex,
        case_abbreviation_boundaries,
        case_baseline_rules,
        case_b6_and_b7,
        case_cli_exit_codes,
    )
    failures: list[str] = []
    for case in cases:
        try:
            case()
            print(f"PASS {case.__name__}")
        except Exception as exc:  # noqa: BLE001 - aggregate all regression failures
            failures.append(f"{case.__name__}: {exc}")
            print(f"FAIL {case.__name__}: {exc}")
    if failures:
        print(f"register-dispersion smoketest: FAIL ({len(failures)} case(s))")
        return 1
    print(f"register-dispersion smoketest: PASS ({len(cases)} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
