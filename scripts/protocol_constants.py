# STATUS (2026-07-07 audit): the bash calibrator's detect_orchestrator does NOT
# currently pick this module up (.plugin-efficiency.json records chain-depth 0).
# Retained as the declared protocol-constants surface pending calibrator fix.
"""Protocol stage constants for the co-author-harness lifecycle ladder.

This module exists so that the plugin-calibrator's
``_declared_protocol_stage_count`` scanner can locate the authoritative
phase count via AST inspection rather than falling back to graph-traversal
depth.  The list below mirrors the Ph1–Ph4 ladder defined in
``references/PHASE_PROTOCOL.md``; update it if new phases are added.
"""

# Each entry is one rung on the Lifecycle-Phase Ladder (Ph1 → Ph4).
# ``run-phase-3-stability`` is an intra-Ph3 stability pass, not a new phase,
# so the operational pipeline remains 5 distinct stages.
PROTOCOL_STAGES = [
    "ph1_plan_draft",
    "ph2_review_revise",
    "ph3_iterate_converge",
    "ph3_stability_pass",
    "ph4_finalize_close",
]
