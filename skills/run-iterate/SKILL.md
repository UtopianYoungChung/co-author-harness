---
name: run-iterate
description: 'Alias for /run-phase-3 -- public iterate stage under the v0.15.x stage x profile vocabulary. /run-iterate is the canonical public surface; legacy /run-phase-2 routes here with profile=refine, and /run-phase-3-stability routes here with profile=stability.'
trigger: 'when the user says "run iterate," "iterate," "stage = iterate," invokes "/run-iterate", or invokes a legacy review/stability command that routes to iterate'
version: 0.15.1
---

# run-iterate -- iterate stage router

**This skill began as an alias for `run-phase-3`.** After PR-3b.4 it is the
public stage surface for all post-draft iteration profiles. The compatibility
relationship is still explicit: `/run-phase-3` and `/run-iterate` resolve to
the same full iterate workflow, while legacy `/run-phase-2` and
`/run-phase-3-stability` route here with fixed profiles.

## Profile Router

| Invocation | Stage | Profile | Binding body |
|---|---|---|---|
| `/run-iterate --profile refine` | `iterate` | `refine` | first-pass review or diff-scoped tightening |
| `/run-iterate --profile structural` | `iterate` | `structural` | structure, heading, boundary, and cross-section changes |
| `/run-iterate --profile deep` | `iterate` | `deep` | full Ph3 parity and pre-MCR safety-net pass |
| `/run-iterate --profile stability` | `iterate` | `stability` | byte-stable inheritance pass |
| `/run-phase-2` | `iterate` | `refine` | legacy compatibility route |
| `/run-phase-3` | `iterate` | F6-selected | legacy canonical route |
| `/run-phase-3-stability` | `iterate` | `stability` | legacy compatibility route |

If no profile is supplied, read the project's F6 dispatch plan. If the F6 is
absent and the invocation came from `/run-phase-2`, use `refine`. If the F6 is
absent and the invocation came from `/run-phase-3-stability`, use `stability`.
Otherwise use the `skills/run-phase-3/SKILL.md` safety default for absent F6
profile fields.

## Refine Profile

The refine profile absorbs the former named Ph2 first-pass review. It is also
used for ordinary diff-scoped iteration once a section is already in the iterate
stage.

For a legacy project with `current_phase: "Ph2"`, do not block dispatch merely
because the phase field is still old vocabulary. Treat it as:

```yaml
stage: iterate
profile: refine
legacy_current_phase: Ph2
```

Run the former first Evaluator engagement envelope as a refine-profile iterate
round: claim-coverage and snowball checks may still run as discovery-layer
preflight, the Evaluator performs the local findings pass, the Generator applies
fixes, and the Planner writes F7 evidence packets. New ledger writes should add
or preserve the shadow fields `stage: iterate` and `profile: refine` so future
rounds no longer need to infer intent from `current_phase`.

## Structural And Deep Profiles

For `structural` and `deep`, read `skills/run-phase-3/SKILL.md` and follow its
profile-selected envelope. That file remains the compatibility body for the full
Ph3 semantics: convergence tracking, Check 8 terminal gating, pre-MCR deep-pass
accounting, re-engagement rows, and escalation ownership.

## Stability Profile

The stability profile absorbs the former `run-phase-3-stability` peer skill. It
keeps the same reduced envelope:

- S-0 byte-stability gate over the F1/F2/F3/F5 substrate.
- Grounding audit over the inherited source basis.
- Deterministic Check 8 counter comparison.
- Trigger-30 escalation to a full iterate pass on any finding.
- No TerminalSignoffRow and no pre-MCR deep-pass satisfaction from stability.

Historical `stability_sub_mode_anticipated: true` F6 rows remain valid. New F6
rows should also include:

```yaml
stage: iterate
profile: stability
```

## Output Profile

<!-- include: _snippets/output-profile.md -->

Every profile writes F7 evidence packets at
`reviews/.harness/evidence/<event_id>.json` plus the matching `events.jsonl` row
with `round_id` and `event_id`. Human-facing Markdown reports are exception
surfaces, not the default output contract.

## Vocabulary Mapping

| Old name | Public stage name | Stage | Profile |
|---|---|---|---|
| `/run-phase-1` | `/run-draft` | `draft` | n/a |
| `/run-phase-2` | `/run-iterate --profile refine` | `iterate` | `refine` |
| `/run-phase-3` | `/run-iterate` | `iterate` | `refine` / `structural` / `deep` |
| `/run-phase-3-stability` | `/run-iterate --profile stability` | `iterate` | `stability` |
| `/run-phase-4` | `/run-finalize` | `finalize` | n/a |

Old names remain valid compatibility entry points. New user-facing guidance
should teach the three-stage ladder: draft -> iterate -> finalize.

## Where the compatibility body lives

`skills/run-phase-3/SKILL.md` remains the compatibility body for the full
iterate workflow. This router owns the public stage/profile mapping and the
legacy command absorption rules.
