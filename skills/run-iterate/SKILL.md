---
name: run-iterate
description: 'Alias for /run-phase-3 — Ph3 Iterate & Converge under the v0.15.0-pre stage × profile vocabulary. Both /run-iterate and /run-phase-3 resolve to the same canonical workflow. stage=iterate; profile dial follows /run-phase-3 §4.5.'
trigger: 'when the user says "run iterate," "iterate," "stage = iterate," or invokes "/run-iterate" — equivalent to "/run-phase-3"'
version: 0.15.0-pre
---

# run-iterate — alias for /run-phase-3

**This skill is an alias.** Introduced at v0.15.0-pre PR-3b.3 to surface the new `stage × profile` vocabulary alongside the legacy phase-numbered names. Both `/run-iterate` and `/run-phase-3` resolve to the same canonical workflow. Behaviour is identical.

## What you do

Read `skills/run-phase-3/SKILL.md` and follow it as the binding instruction set for this invocation. Treat that file as the authority for trigger conditions, gates, profile selection (§4.5), convergence semantics, and exit conditions. **Do not duplicate or re-interpret** the canonical spec from this alias file.

## Stability sub-mode

For the byte-stable inheritance pass, continue to invoke `/run-phase-3-stability` directly. PR-3b.3 does **not** thin or collapse that skill — it remains the canonical home for the reduced-envelope iteration. A future PR may fold stability into `/run-iterate --profile stability`; until then, the direct command is the supported surface.

## Vocabulary mapping

| Old name (canonical) | New alias (v0.15.0-pre) | Stage | Profile |
|---|---|---|---|
| `/run-phase-1` | `/run-draft` | `draft` | — |
| `/run-phase-3` | `/run-iterate` | `iterate` | refine / structural / deep / stability |
| `/run-phase-4` | `/run-finalize` | `finalize` | — |

`/run-phase-2` deliberately has no alias at PR-3b.3 — Ph2 is the rung the architecture intends to merge into `/run-iterate refine` later (PR-3b.4); aliasing it now would lock in a surface we may collapse.

## Where the canonical spec lives

`skills/run-phase-3/SKILL.md`. Always.
