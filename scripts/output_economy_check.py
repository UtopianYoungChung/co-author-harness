#!/usr/bin/env python3
"""
output_economy_check.py — static guard that phase skills and agent contracts
retain output-economy vocabulary (v0.14.0).

Fails when required phrases are missing or when discouraged default-report
language appears outside Markdown sections titled for exceptions / legacy
compatibility (heading-depth traversal).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable, List, Set, Tuple


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ALLOWED_DISCOURAGED_SECTION_RE = re.compile(
    r"\b(exception output|exception report|legacy compatibility|backward compatibility)\b",
    re.IGNORECASE,
)

PHASE_FILES = [
    "skills/run-phase-1/SKILL.md",
    "skills/run-phase-2/SKILL.md",
    "skills/run-phase-3/SKILL.md",
    "skills/run-phase-3-stability/SKILL.md",
    "skills/run-phase-4/SKILL.md",
]

AGENT_AND_CONTRACT_FILES = [
    "agents/planner.md",
    "agents/evaluator.md",
    "agents/generator.md",
    "agents/reflector.md",
    "references/AGENT_CONTRACTS.md",
]

PHASE_REQUIRED_PHRASES = [
    "Output Profile",
    "reviews/.harness/evidence/<event_id>.json",
    "round_id",
    "event_id",
]

PLANNER_REQUIRED_PHRASES = [
    "Output Profile Routing",
    "evidence packet",
    "final report",
]

AGENT_REQUIRED_PHRASES = [
    "evidence packet",
    "final report",
]

CONTRACT_REQUIRED_PHRASES = [
    "Output Economy Contract",
    "evidence packet",
    "final report",
]

DISCOURAGED_DEFAULTS = [
    "per-step findings",
    "writes its findings",
    "full report per iteration",
    "routine Markdown findings report",
]
# Match case-insensitively against lowercased lines (phrases may contain capitals).
DISCOURAGED_DEFAULTS_LOWER = tuple(s.lower() for s in DISCOURAGED_DEFAULTS)

PROTOCOL_REQUIRED_SUBSTRINGS = [
    "round_id",
    "event_id",
    "final_round_report_<round_id>.md",
]


def plugin_root() -> Path:
    return Path(__file__).resolve().parent.parent


def allowed_discouraged_line_numbers(lines: List[str]) -> Set[int]:
    allowed: Set[int] = set()
    active_depth: int | None = None
    for lineno, line in enumerate(lines, start=1):
        match = HEADING_RE.match(line)
        if match:
            depth = len(match.group(1))
            title = match.group(2)
            if active_depth is not None and depth <= active_depth:
                active_depth = None
            if ALLOWED_DISCOURAGED_SECTION_RE.search(title):
                active_depth = depth
        if active_depth is not None:
            allowed.add(lineno)
    return allowed


def check_file(
    rel: str,
    text: str,
    required: Iterable[str],
    check_discouraged: bool,
) -> List[str]:
    errors: List[str] = []
    lines = text.splitlines()
    allowed_lines = allowed_discouraged_line_numbers(lines) if check_discouraged else set()

    for phrase in required:
        if phrase not in text:
            errors.append(f"{rel}: missing required phrase {phrase!r}")

    if check_discouraged:
        for lineno, line in enumerate(lines, start=1):
            if lineno in allowed_lines:
                continue
            lower = line.lower()
            for canon, phrase in zip(DISCOURAGED_DEFAULTS, DISCOURAGED_DEFAULTS_LOWER):
                if phrase in lower:
                    errors.append(
                        f"{rel}:{lineno}: discouraged phrase {canon!r} outside "
                        f"allowed exception/compatibility heading section"
                    )
    return errors


def main() -> int:
    root = plugin_root()
    errors: List[str] = []

    for rel in PHASE_FILES:
        path = root / rel
        if not path.is_file():
            errors.append(f"missing file {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        errors.extend(check_file(rel, text, PHASE_REQUIRED_PHRASES, True))

    planner_path = root / "agents" / "planner.md"
    if planner_path.is_file():
        pt = planner_path.read_text(encoding="utf-8")
        errors.extend(
            check_file(
                "agents/planner.md",
                pt,
                PLANNER_REQUIRED_PHRASES,
                True,
            )
        )
    else:
        errors.append("missing file agents/planner.md")

    for rel in ("agents/evaluator.md", "agents/generator.md", "agents/reflector.md"):
        path = root / rel
        if not path.is_file():
            errors.append(f"missing file {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        errors.extend(check_file(rel, text, AGENT_REQUIRED_PHRASES, True))

    contracts = root / "references" / "AGENT_CONTRACTS.md"
    if contracts.is_file():
        ct = contracts.read_text(encoding="utf-8")
        errors.extend(
            check_file(
                "references/AGENT_CONTRACTS.md",
                ct,
                CONTRACT_REQUIRED_PHRASES,
                True,
            )
        )
    else:
        errors.append("missing file references/AGENT_CONTRACTS.md")

    proto = root / "references" / "OUTPUT_ECONOMY_PROTOCOL.md"
    if proto.is_file():
        prot = proto.read_text(encoding="utf-8")
        for sub in PROTOCOL_REQUIRED_SUBSTRINGS:
            if sub not in prot:
                errors.append(
                    f"references/OUTPUT_ECONOMY_PROTOCOL.md: missing {sub!r}"
                )
    else:
        errors.append("missing file references/OUTPUT_ECONOMY_PROTOCOL.md")

    for msg in errors:
        print(msg)

    if errors:
        return 3
    print("output_economy_check: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
