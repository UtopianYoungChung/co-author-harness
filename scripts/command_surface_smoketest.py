#!/usr/bin/env python3
"""Synthetic regression tests for command-surface policy enforcement."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from command_surface_check import validate


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fixture(root: Path) -> None:
    write(
        root / "skills/public-skill/SKILL.md",
        "---\nname: public-skill\ndescription: Public.\n---\n",
    )
    write(
        root / "skills/hidden-skill/SKILL.md",
        "---\nname: hidden-skill\ndescription: Hidden.\nuser-invocable: false\n---\n",
    )
    write(
        root / "skills/plugin-commands/SKILL.md",
        "---\nname: plugin-commands\ndescription: Catalog.\n---\n"
        "| Command | Purpose | Best use |\n|---|---|---|\n"
        "| `/plugin-commands` | Help. | Orientation. |\n"
        "| `/public-skill` | Public. | Now. |\n",
    )
    write(
        root / "references/policies/command_surface.v1.json",
        json.dumps(
            {
                "schema_version": "1.0.0",
                "public": ["plugin-commands", "public-skill"],
                "hidden": {"internal": ["hidden-skill"]},
            }
        ),
    )
    write(
        root / "references/capabilities.yaml",
        "capabilities:\n"
        "  plugin-commands: {exposure: public}\n"
        "  public-skill: {exposure: public}\n"
        "  hidden-skill: {exposure: internal}\n",
    )
    write(root / "AGENTS.md", "Use `/public-skill`.\n")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fixture(root)
        assert validate(root) == [], "positive fixture must pass"

        write(root / "commands/public-skill.md", "# duplicate\n")
        findings = validate(root)
        assert any("duplicate commands/*.md" in item for item in findings)
        (root / "commands/public-skill.md").unlink()

        hidden_path = root / "skills/hidden-skill/SKILL.md"
        hidden_path.write_text(
            hidden_path.read_text(encoding="utf-8").replace("user-invocable: false\n", ""),
            encoding="utf-8",
        )
        findings = validate(root)
        assert any("classifies it as hidden" in item for item in findings)

        fixture(root)
        catalog = root / "skills/plugin-commands/SKILL.md"
        catalog.write_text(
            catalog.read_text(encoding="utf-8")
            + "| `/hidden-skill` | Hidden. | Never. |\n",
            encoding="utf-8",
        )
        findings = validate(root)
        assert any("exposes hidden or unknown" in item for item in findings)

        fixture(root)
        write(root / "AGENTS.md", "Use `/ghost-command`.\n")
        findings = validate(root)
        assert any("advertises slash names outside" in item for item in findings)

        fixture(root)
        capabilities = root / "references/capabilities.yaml"
        capabilities.write_text(
            capabilities.read_text(encoding="utf-8").replace(
                "hidden-skill: {exposure: internal}",
                "hidden-skill: {exposure: public}",
            ),
            encoding="utf-8",
        )
        findings = validate(root)
        assert any("capability registry exposure drift" in item for item in findings)

    print("PASS: command surface policy rejects duplicates, visibility and capability drift, hidden catalog rows, and phantom advertised names")
    return 0


if __name__ == "__main__":
    sys.exit(main())
