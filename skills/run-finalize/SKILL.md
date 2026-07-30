---
name: run-finalize
description: 'Public finalize stage entrypoint under the v0.15.0-pre stage × profile vocabulary. Legacy /run-phase-4 remains a compatibility body for the same Ph4 Finalize & Close workflow. stage=finalize.'
trigger: 'when the user says "run finalize," "finalize," "stage = finalize," "ship," or invokes "/run-finalize" — equivalent to "/run-phase-4"'
version: 0.15.0-pre
---

# run-finalize — public finalize stage

Output authority is `references/role_output_contract.json` 3.0.0. Resolve the six fixed roles and nine triggered F1-F9 classes, including context, cardinality, ordering, and typed suppression, from that contract. A readable legacy artifact or file presence never proves shipment-v2 application, terminal state, or acceptance.

`/run-finalize` is the canonical public entrypoint for the finalize stage.
Legacy `/run-phase-4` remains a compatibility entrypoint and implementation
body for the same workflow; behaviour is identical.

## What you do

Read `skills/run-phase-4/SKILL.md` and follow it as the compatibility
implementation body for this invocation. Treat its MCR admission gates, G.4
sign-off, external-verifier requirements, and exit conditions as binding.
**Do not duplicate or reinterpret** that implementation body in this public
router.

For course essays, FINAL remains eligible for the M4-onward exemplar envelope: Yu may condition surface register; Dennett is argument-only when admitted. The canonical workflow begins public `FINAL` through `assignment_milestone_checkpoint.py`, emits a fresh FINAL receipt, reserves it once with `assignment_dispatch_preflight.py --expected-target FINAL --consumer planner --write-path milestones/M5_final_paper.md --write-path submission_bundle/final_manuscript.md`, then requires Generator staging and `assignment_writer_commit.py` publication. Planner records FINAL and closes it through the same checkpoint command with structured terminal evidence and explicit current-byte approval. The final gate requires accepted M1-M4, M5 in progress, all sections at Ph4, and current wiki-grounding evidence or an authorized opt-out.

## MCR convergence evidence

If `reviews/convergence_log.md` carries the `profile:` field per iteration row, `scripts/pre_phase_advance_check.py` may emit the advisory `W-MCR-CONVERGENCE-EVIDENCE` at the MCR boundary (PR-3b.2). The advisory is evidence-only and does **not** authorize MCR admission — the `TerminalSignoffRow` in `ph3_convergence_signoff.md` remains the sole authority.

## Vocabulary mapping

| Compatibility name | Public stage name | Stage | Profile |
|---|---|---|---|
| `/run-phase-1` | `/run-draft` | `draft` | — |
| `/run-phase-2` | `/run-iterate --profile refine` | `iterate` | refine |
| `/run-phase-3` | `/run-iterate` | `iterate` | refine / structural / deep |
| `/run-phase-3-stability` | `/run-iterate --profile stability` | `iterate` | stability |
| `/run-phase-4` | `/run-finalize` | `finalize` | — |

`/run-phase-2` is now a legacy compatibility route to `/run-iterate --profile refine`; it is not a separate public stage.

## Where the compatibility body lives

`skills/run-phase-4/SKILL.md` carries the full Ph4 implementation for backward
compatibility. This file owns the public finalize-stage name and mapping.
