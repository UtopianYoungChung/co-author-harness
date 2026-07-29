---
name: run-draft
description: 'Public draft stage entrypoint under the v0.15.0-pre stage × profile vocabulary. Legacy /run-phase-1 remains a compatibility body for the same Ph1 Plan & Draft workflow. stage=draft.'
trigger: 'when the user says "run draft," "begin draft," "stage = draft," or invokes "/run-draft" — equivalent to "/run-phase-1"'
version: 0.15.0-pre
---

# run-draft — public draft stage

`/run-draft` is the canonical public entrypoint for the draft stage. Legacy
`/run-phase-1` remains a compatibility entrypoint and implementation body for
the same workflow; behaviour is identical.

## What you do

Live Generator bytes are published only through `assignment_writer_commit.py`; the independent evaluation follows that exact publication.

Read `skills/run-phase-1/SKILL.md` and follow it as the compatibility
implementation body for this invocation. Treat its lifecycle gates, finding
format, and exit conditions as binding. **Do not duplicate or reinterpret**
that implementation body in this public router.

For native course essays, this public entrypoint invokes the M1→M2→M3→M4 auto-walk: resolve the assignment contract, derive one active target, bind the all-drafts policy while the artifact may still be absent, emit and reserve the READY receipt, run Generator publication under the obligations derived from the authoritative reader binding, then run the independent Evaluator governing-policy pass on the exact bytes. Reader-profile v2 with `semantic_usage: not_invoked` omits centroid work; a governed semantic binding retains its declared centroid obligations. Milestone record requires both verified envelopes. It dispatches one deliverable and stops at that milestone's user approval checkpoint. “Draft the whole paper” never skips open M1-M3 work, and file presence never supplies acceptance or policy evidence.

**Whole-lifecycle intent routes here.** "Harness full run," "full harness run," "draft me an essay," "draft the whole paper," "run the ladder" are `full_lifecycle` requests and enter this canonical lifecycle — they are not answered ad hoc. With **no project at all**, fail closed into the canonical bootstrap instruction rather than writing prose anywhere: `python scripts/full_run_contract_check.py authorize --project-root <p>` is the mechanical check, and a new native root is created only by `python scripts/native_project_bootstrap.py ...`, which must install reader-profile binding v2. Run scope, the child-dispatch prohibition, and the terminal gate are normative in `references/FULL_RUN_CONTRACT.md`; this router does not restate them.

**Three-scope router.** Route exactly `adhoc_review`, `lab_iteration`, or `full_lifecycle`, and put `run_scope:` matching the parent in every Planner, Generator, and Evaluator brief. `lab_iteration` is proposal-only: it requires an existing governed project, resolved assignment contract, and resolved staging/private-shipment output, with no lifecycle and no F9 authority. It never accepts milestones, consumes handoffs, writes authoritative research/final paths, or claims terminal completion.

## Vocabulary mapping

| Compatibility name | Public stage name | Stage | Profile |
|---|---|---|---|
| `/run-phase-1` | `/run-draft` | `draft` | — |
| `/run-phase-2` | `/run-iterate --profile refine` | `iterate` | refine |
| `/run-phase-3` | `/run-iterate` | `iterate` | refine / structural / deep |
| `/run-phase-3-stability` | `/run-iterate --profile stability` | `iterate` | stability |
| `/run-phase-4` | `/run-finalize` | `finalize` | — |

`/run-phase-2` is now a legacy compatibility route to `/run-iterate --profile refine`; it is not a separate public stage.

## Compatibility policy

Old names remain supported as compatibility entry points. New user-facing guidance should teach the public ladder as draft -> iterate -> finalize. The `stage` and `profile` shadow fields on every `SectionStateObject` carry that vocabulary in the ledger.

## Where the compatibility body lives

`skills/run-phase-1/SKILL.md` carries the full Ph1 implementation for backward
compatibility. This file owns the public draft-stage name and mapping.
