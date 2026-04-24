#!/usr/bin/env python3
"""tier_state_validate.py — DEPRECATED at v0.7.4 (forwarding shim).

[v0.7.3-READ-ONLY] — this script is retained as a one-line forwarding shim
during the v0.7.4 minor for back-compatibility with tooling that still
invokes the legacy filename. The authoritative validator now lives at
`scripts/phase_state_validate.py` and operates against `reviews/phase_state.json`
under the Lifecycle-Phase Ladder (Ph1/Ph2/Ph3/Ph4) vocabulary.

The shim re-execs phase_state_validate.py with identical argv and returns
its exit code unchanged. It also prints a one-line DEPRECATION_WARNING to
stderr (finding key W-DUAL-READ-LEGACY) so CI surfaces the legacy call-site.

Removed at v0.7.5 RC — callers must migrate to scripts/phase_state_validate.py
before upgrading beyond v0.7.4.
"""

from __future__ import annotations

import os
import pathlib
import sys


def main() -> int:
    sys.stderr.write(
        "[tier_state_validate] W-DUAL-READ-LEGACY — this script is a v0.7.4 "
        "deprecation shim; call scripts/phase_state_validate.py directly. "
        "Shim removed at v0.7.5 RC.\n"
    )
    here = pathlib.Path(__file__).resolve().parent
    target = here / "phase_state_validate.py"
    if not target.exists():
        sys.stderr.write(
            f"[tier_state_validate] forwarding target not found: {target}\n"
        )
        return 3
    os.execv(sys.executable, [sys.executable, str(target), *sys.argv[1:]])
    return 0  # unreachable


if __name__ == "__main__":
    sys.exit(main())
