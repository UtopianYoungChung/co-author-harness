#!/usr/bin/env python3
"""release_manifest_check - the finished artifact's manifest IS HEAD's manifest.

Why this exists (2026-07-16): both release paths validated the requested
version against the DIRTY WORKTREE manifest while packaging COMMITTED HEAD
bytes, and never read the archive's embedded manifest at all. Consequence: a
worktree bumped to v0.30.0 produced a v0.30.0-NAMED zip whose embedded
manifest still said v0.29.0 -- filename and content free to disagree. And the
old drift check compared version string + description LENGTH, so a same-length
description mutation (or any keyword change) passed.

The check here is an exact cryptographic digest: sha256 of the archive member
`.claude-plugin/plugin.json` must equal sha256 of `HEAD:.claude-plugin/
plugin.json`. No field allowlist -- a field-by-field comparison is the same
under-narrow population as every other in this workstream.

Called by scripts/build-release-zip.sh and scripts/release-gate.sh Phase 1;
independently testable against tampered archives.

Usage
    python scripts/release_manifest_check.py <archive.zip-or-.plugin> [--repo <root>]

Exit
    0  archive manifest == HEAD manifest (digest-exact)
    1  mismatch (or manifest member absent -- an archive without a manifest
       cannot claim to match anything)
    2  environment error (unreadable archive, git failure)
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

from package_enumeration import GIT  # same directory when run as a script

MANIFEST_REL = ".claude-plugin/plugin.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archive", type=Path)
    ap.add_argument("--repo", type=Path,
                    default=Path(__file__).resolve().parent.parent)
    args = ap.parse_args()

    try:
        head = subprocess.run(
            [GIT, "-C", str(args.repo), "show", f"HEAD:{MANIFEST_REL}"],
            capture_output=True, check=True)
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"[ERROR] cannot read HEAD manifest: {exc}", file=sys.stderr)
        return 2
    head_sha = hashlib.sha256(head.stdout).hexdigest()

    try:
        with zipfile.ZipFile(args.archive) as z:
            names = z.namelist()
            # UNIQUENESS BEFORE CONTENT (2026-07-16, review F4).
            #
            # A ZIP may legally carry two members with the same name.
            # `MANIFEST_REL in names` then passes and `z.read(MANIFEST_REL)`
            # returns whichever ONE Python's dict lookup kept -- so an archive
            # with a malicious manifest first and a HEAD-identical manifest
            # second verified clean while a consumer reading the other member
            # (or extracting sequentially, last-write-wins) got the malicious
            # one. Membership is not identity; the digest below can only speak
            # for the member it read.
            #
            # This is the same defect class the builder's own readback names:
            # "cardinality is not correspondence". Reject 0 or >1 before
            # reading any content.
            count = names.count(MANIFEST_REL)
            if count == 0:
                print(f"[FAIL] archive carries no {MANIFEST_REL}", file=sys.stderr)
                return 1
            if count > 1:
                print(f"[FAIL] duplicate membership: archive carries {count} "
                      f"members named {MANIFEST_REL}; exactly one is required. "
                      "A digest check can only describe the member it reads, "
                      "so a duplicate manifest is unverifiable by construction.",
                      file=sys.stderr)
                return 1
            arc_sha = hashlib.sha256(z.read(MANIFEST_REL)).hexdigest()
    except (OSError, zipfile.BadZipFile) as exc:
        print(f"[ERROR] cannot read archive: {exc}", file=sys.stderr)
        return 2

    if arc_sha != head_sha:
        print(f"[FAIL] archive manifest {arc_sha[:12]} != HEAD manifest "
              f"{head_sha[:12]}: the artifact's embedded manifest is not the "
              "committed one", file=sys.stderr)
        return 1
    print(f"[OK] archive manifest == HEAD manifest ({head_sha[:12]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
