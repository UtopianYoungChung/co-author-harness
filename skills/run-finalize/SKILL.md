---
name: run-finalize
description: 'Public 0.50 finalize coordinator on staging. Coordinates Planner, Generator, Evaluator, and Reflector. Generator publishes only via assignment_writer_commit.py to staging. Evaluator certifies shipment bytes. Writer is the apply step. Parked paper-specific body: run-phase-4.'
trigger: 'when the user says "run finalize," "finalize," "stage = finalize," "ship," or invokes "/run-finalize"'
version: 0.50.0
user-invocable: true
---

# run-finalize — public finalize coordinator (staging)

`/run-finalize` is a real public coordinator. It is not a degraded ad and not
a mechanical generate+evaluate onto the live workbench. It coordinates the
four plugin hands **on staging**.

Output authority is `references/role_output_contract.json` 3.0.0. A readable
legacy artifact or file presence never proves shipment-v2 application,
terminal state, or acceptance.

## Four hands

| Hand | Does | Does not |
|---|---|---|
| Planner | One active FINAL/close target, READY reserve | Edit manuscript; accept the workbench |
| Generator | Publish **on staging** via `assignment_writer_commit.py` only | Land M4 bytes on `research/60_Workbench` |
| Evaluator | Certify **shipment / staging bytes** (exact hash); fire citation / claim / derivation / similar checks | Edit prose; mint scholarly CLEAN |
| Reflector | Full closeout after a certified shipment | Apply to the workbench |

**Outside** the plugin: Writer is the apply step — exact path, exact hash.
If Writer edits on apply, that is a new draft, not the certified shipment.

## Staging loop

1. Planner binds the finalize target and reserves READY.
2. Generator publishes staging bytes only through
   `python scripts/assignment_writer_commit.py --project-root <project> --receipt <receipt> --plan <plan>`.
3. Evaluator certifies those exact shipment bytes (exact hash).
4. Reflector may run full closeout after a certified shipment.
5. Writer (outside the plugin) applies exact path, exact hash.

### Evaluator fire table

Evaluator must fire these skills against certified staging bytes. Dest-safe
evaluation-lane does not stamp them completed/INFO. Findings land under the
shipment lane. Evaluator (or `attach-verifier-receipt`) binds
`assignment_dispatch` receipts. `scripts/scholarly_evaluation.py` verifies the
C6 profile (claim, derivation, warrant, citation) on those exact bytes.
Evaluate verify refuses completion if those receipts or C6 results are missing.
Fire table: grounding-protocol, citation-discipline, claim-coverage,
derivation-check, grammar-mechanics, contradictions, analytic-construction,
centroid-evaluation (graph fail-closes when semantic_usage=not_invoked).
Mechanical dest-safe preflight only: d-style-profile, deterministic-audit.
No scholarly CLEAN.

**DEST-PROTECTED stays.** Refuse a direct write of manuscript bytes onto
`research/60_Workbench/<work-id>/`. Dest-safe receipts only under
`reviews/.harness/shipments/<id>/` and/or
`outputs/co-author-harness/staging/<work-id>/<run-id>/`.
Derived handoff remains valid. No CLEAN mint. SK-32 stays closed.

Graph / centroid remain invoke-only / fail-closed. Do not auto-dispatch
those skills as scholarly CLEAN.

This coordinator does not open M4 on the live workbench and does not lift
DEST-PROTECTED. Finalize means certify a shipment on staging, then hand
Writer the exact path and exact hash.

## Parked compatibility body

`skills/run-phase-4/SKILL.md` remains on disk as a **parked paper-specific
compatibility body**. It is not a public 0.50 coordinator and is not the
live implementation this coordinator follows. Do not advertise
`/run-phase-4` as a public name.
