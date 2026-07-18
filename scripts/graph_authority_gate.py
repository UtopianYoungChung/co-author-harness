#!/usr/bin/env python3
"""Unconditional graph-authority gate (Research Truth corrective delta 2).

This module hard-codes governed graph unavailability for the entire CD2 window.

Phase 4 must replace this behavior after defining and validating its governed
graph contract. This file intentionally contains no lookup of a Phase-4 unlock
artifact, no existence check for such an artifact, no parser, no environment or
configuration override, and no positive availability branch.

Graph authority is independent of Wiki-write authority
(WIKI_WRITE_TRANSACTION_UNAVAILABLE). A future governed-graph unlock must never
unlock Wiki mutation.
"""

from __future__ import annotations

from typing import Any, Dict


REASON_CODE = "GRAPH_GOVERNED_GENERATION_UNAVAILABLE"


def evaluate_graph_authority(*, structural_ok: bool | None = None) -> Dict[str, Any]:
    """Return graph-authority status.

    ``structural_ok`` may be supplied by callers for metadata only. It never
    changes ``governed_available``.
    """
    return {
        "governed_available": False,
        "reason_code": REASON_CODE,
        "legacy_structural_ok": structural_ok,
        "detail": (
            "Governed graph generation/activation is unavailable. "
            "Structural field-shape validity does not grant graph authority. "
            "Phase 4 must replace this unconditional gate after contract validation."
        ),
    }


def is_graph_governed_available() -> bool:
    """Always False for this delta."""
    return False
