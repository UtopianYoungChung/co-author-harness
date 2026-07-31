#!/usr/bin/env python3
"""Red-first contract for five-plane release qualification topology."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE = ROOT / "scripts" / "qualification_plane_topology.py"


def main() -> int:
    assert MODULE.is_file(), f"RED: missing {MODULE.relative_to(ROOT)}"
    spec = importlib.util.spec_from_file_location("qualification_plane_topology", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "validate_topology")
    required = {
        "missing_plane_kind", "unknown_plane_kind", "five_planes_required",
        "attached_build_refused", "dirty_build_refused", "wrong_commit_refused",
        "overlap_refused", "casefold_alias_refused", "nfc_alias_refused",
        "reparse_refused", "archive_provenance_mismatch_refused",
        "git_metadata_outside_source_build_refused",
        "post_build_source_residue_refused_before_suites",
    }
    advertised = set(getattr(module, "REGRESSION_CONTRACT", ()))
    assert required <= advertised, f"missing topology contracts: {sorted(required-advertised)}"
    print(f"qualification_plane_topology_smoketest: PASS {len(required)} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
