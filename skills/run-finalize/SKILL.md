---
name: run-finalize
description: 'Alias for /run-phase-4 — Ph4 Finalize & Close under the v0.15.0-pre stage × profile vocabulary. Both /run-finalize and /run-phase-4 resolve to the same canonical workflow. stage=finalize.'
trigger: 'when the user says "run finalize," "finalize," "stage = finalize," "ship," or invokes "/run-finalize" — equivalent to "/run-phase-4"'
version: 0.15.0-pre
---

# run-finalize — alias for /run-phase-4

**This skill is an alias.** Introduced at v0.15.0-pre PR-3b.3 to surface the new `stage × profile` vocabulary alongside the legacy phase-numbered names. Both `/run-finalize` and `/run-phase-4` resolve to the same canonical workflow. Behaviour is identical.

## What you do

Read `skills/run-phase-4/SKILL.md` and follow it as the binding instruction set for this invocation. Treat that file as the authority for MCR admission gates, G.4 sign-off, external-verifier requirements, and exit conditions. **Do not duplicate or re-interpret** the canonical spec from this alias file.

For course essays, FINAL remains eligible for the M4-onward exemplar envelope: Yu may condition surface register; Dennett is argument-only when admitted. The canonical workflow emits a fresh FINAL receipt, reserves it once with `assignment_dispatch_preflight.py --expected-target FINAL --consumer planner --write-path manuscript/main.md`, then requires Generator staging and `assignment_writer_commit.py` publication. The final gate still requires accepted M1-M4 and current wiki-grounding evidence or an authorized opt-out.

## MCR convergence evidence

If `reviews/convergence_log.md` carries the `profile:` field per iteration row, `scripts/pre_phase_advance_check.py` may emit the advisory `W-MCR-CONVERGENCE-EVIDENCE` at the MCR boundary (PR-3b.2). The advisory is evidence-only and does **not** authorize MCR admission — the `TerminalSignoffRow` in `ph3_convergence_signoff.md` remains the sole authority.

## Vocabulary mapping

| Old name (canonical) | New alias (v0.15.0-pre) | Stage | Profile |
|---|---|---|---|
| `/run-phase-1` | `/run-draft` | `draft` | — |
| `/run-phase-2` | `/run-iterate --profile refine` | `iterate` | refine |
| `/run-phase-3` | `/run-iterate` | `iterate` | refine / structural / deep |
| `/run-phase-3-stability` | `/run-iterate --profile stability` | `iterate` | stability |
| `/run-phase-4` | `/run-finalize` | `finalize` | — |

`/run-phase-2` is now a legacy compatibility route to `/run-iterate --profile refine`; it is not a separate public stage.

## Where the canonical spec lives

`skills/run-phase-4/SKILL.md`. Always.
