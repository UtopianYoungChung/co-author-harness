---
name: run-draft
description: 'Alias for /run-phase-1 — Ph1 Plan & Draft under the v0.15.0-pre stage × profile vocabulary. Both /run-draft and /run-phase-1 resolve to the same canonical workflow. stage=draft.'
trigger: 'when the user says "run draft," "begin draft," "stage = draft," or invokes "/run-draft" — equivalent to "/run-phase-1"'
version: 0.15.0-pre
---

# run-draft — alias for /run-phase-1

**This skill is an alias.** Introduced at v0.15.0-pre PR-3b.3 to surface the new `stage × profile` vocabulary alongside the legacy phase-numbered names. Both `/run-draft` and `/run-phase-1` resolve to the same canonical workflow. Behaviour is identical.

## What you do

Read `skills/run-phase-1/SKILL.md` and follow it as the binding instruction set for this invocation. Treat that file as the authority for trigger conditions, gates, finding format, and exit conditions. **Do not duplicate or re-interpret** the canonical spec from this alias file.

## Vocabulary mapping

| Old name (canonical) | New alias (v0.15.0-pre) | Stage | Profile |
|---|---|---|---|
| `/run-phase-1` | `/run-draft` | `draft` | — |
| `/run-phase-3` | `/run-iterate` | `iterate` | refine / structural / deep / stability |
| `/run-phase-4` | `/run-finalize` | `finalize` | — |

`/run-phase-2` deliberately has no alias at PR-3b.3 — Ph2 is the rung the architecture intends to merge into `/run-iterate refine` later (PR-3b.4); aliasing it now would lock in a surface we may collapse.

## Why an alias rather than a rename

Old names remain **canonical** at v0.15.0-pre. The aliases exist so users can adopt the new vocabulary today without breaking project scripts, slash-command histories, or downstream references. The `stage` and `profile` shadow fields on every `SectionStateObject` (additive at PR-3b.1) already carry the new vocabulary in the ledger; this alias layer aligns the command surface.

## Where the canonical spec lives

`skills/run-phase-1/SKILL.md`. Always.
