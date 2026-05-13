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
| `/run-phase-2` | `/run-iterate --profile refine` | `iterate` | refine |
| `/run-phase-3` | `/run-iterate` | `iterate` | refine / structural / deep |
| `/run-phase-3-stability` | `/run-iterate --profile stability` | `iterate` | stability |
| `/run-phase-4` | `/run-finalize` | `finalize` | — |

`/run-phase-2` is now a legacy compatibility route to `/run-iterate --profile refine`; it is not a separate public stage.

## Why an alias rather than a rename

Old names remain supported as compatibility entry points. New user-facing guidance should teach the public ladder as draft -> iterate -> finalize. The `stage` and `profile` shadow fields on every `SectionStateObject` carry that vocabulary in the ledger.

## Where the canonical spec lives

`skills/run-phase-1/SKILL.md`. Always.
