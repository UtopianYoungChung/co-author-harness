#!/usr/bin/env python3
"""Regression test for concept-introduction and derivation continuity."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(path: str, phrases: tuple[str, ...]) -> list[str]:
    text = (ROOT / path).read_text(encoding="utf-8").lower()
    return [f"{path}: missing {phrase!r}" for phrase in phrases if phrase.lower() not in text]


def main() -> int:
    failures: list[str] = []
    failures += require(
        "skills/sentence-level-pass/SKILL.md",
        (
            "introduction-provenance test",
            "derivation-continuity test",
            "the field's working unit is the *actor*",
            "the next step is to represent those parties",
            "priority gate",
        ),
    )
    failures += require(
        "references/bacon_2009_well_crafted_sentence_guidelines.md",
        ("introduction-provenance test", "where did this term come from?"),
    )
    failures += require(
        "references/project_writing_style_checklist.md",
        ("introduction-provenance test", "derivation-continuity test"),
    )
    failures += require(
        "references/REVIEW_ORCHESTRATION.md",
        ("concept-introduction priority gate",),
    )
    failures += require(
        "agents/evaluator.md",
        ("concept-introduction priority gate", "mandatory at every applicable review depth"),
    )

    if failures:
        print("concept-introduction contract: FAIL")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("concept-introduction contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
