#!/usr/bin/env python3
"""Print GitHub Release notes for one version from CHANGELOG.md.

Usage: python scripts/release_notes.py <X.Y.Z>

The body is the CHANGELOG section headed `## vX.Y.Z — <date>` (empty when the
version has no heading), followed by install guidance for the attached
bundle. Read-only: writes nothing but stdout. Used by
.github/workflows/release.yml.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INSTALL = """\
## Install

**Claude Code** — add the repository as a marketplace; installs then track `main`:

```
/plugin marketplace add UtopianYoungChung/co-author-harness
/plugin install co-author-harness@joseph-chung-co-author-harness
```

**Claude Desktop / Cowork (file upload)** — download `co-author-harness.plugin`
(or the identical `co-author-harness.zip`) below and load it in the plugin
loader. `SHA256SUMS` lists both files' digests.
"""


def section(changelog: str, version: str) -> str:
    heading = re.compile(rf"^## v{re.escape(version)}(?:\s|$)", re.M)
    match = heading.search(changelog)
    if match is None:
        return ""
    body_start = changelog.find("\n", match.start())
    if body_start < 0:
        return ""
    following = re.search(r"^## ", changelog[body_start + 1:], re.M)
    end = body_start + 1 + following.start() if following else len(changelog)
    return changelog[body_start + 1:end].strip().rstrip("-").strip()


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", argv[0]):
        print("usage: release_notes.py <X.Y.Z>", file=sys.stderr)
        return 2
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    body = section(changelog, argv[0])
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(body or f"No CHANGELOG section is headed v{argv[0]}.")
    print()
    print(INSTALL, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
