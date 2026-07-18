#!/usr/bin/env python3
"""Regression test for the semantic-predication judgment contract."""

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
            "semantic-predication integrity",
            "bearer test",
            "contrast-set test",
            "domain-collocation test",
            "conceptual-debt test",
            "saying that a hospital wants patient safety",
        ),
    )
    failures += require(
        "references/bacon_2009_well_crafted_sentence_guidelines.md",
        ("semantic-predication integrity", "bearer test", "contrast-set test", "conceptual-debt test"),
    )
    failures += require(
        "references/project_writing_style_checklist.md",
        ("semantic-predication integrity", "domain-collocation test", "conceptual-debt test"),
    )
    failures += require(
        "references/REVIEW_ORCHESTRATION.md",
        ("semantic-predication integrity",),
    )
    failures += require(
        "agents/evaluator.md",
        ("semantic-predication integrity", "mandatory at every applicable review depth"),
    )

    if failures:
        print("semantic-predication contract: FAIL")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("semantic-predication contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
