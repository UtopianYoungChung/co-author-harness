# ROUTING_SPINE — Derived Intent Routing

**Purpose.** This file maps a user request to the canonical milestone and
lifecycle contracts. It does not define a second phase system.

## 1. Authorities

The persisted lifecycle states and legal edges are defined only by
`lifecycle_transitions.v1.json`. Exact M1–M4 writer, path, timing, review, and
acceptance responsibilities are defined only by `role_output_contract.json`.
`reviews/phase_state.json` is project state, and the Planner is its sole writer.

The labels **Think, Plan, Build, Review, Test, Ship, Reflect** are derived intent
labels. They help select an entry point but are never persisted as lifecycle
state, never authorize a transition, and never replace Ph1–Ph4 or M1–M5.

## 2. Intent routing

| User intent | Derived label | Milestone / state route | First responsible role |
|---|---|---|---|
| Frame a new research problem | Think | M1 in Ph1 | Planner dispatches Generator |
| Build annotated references | Plan | M2 in Ph1 | Planner dispatches Generator |
| Create a structured outline | Plan | M3 in Ph1 | Planner dispatches Generator |
| Assemble the first complete manuscript | Build | M4 initial assembly in Ph1 | Planner dispatches Generator |
| Review or revise the manuscript | Review | M4 in Ph2 or Ph3 | Evaluator, then Generator |
| Run deterministic or policy checks | Test | Current canonical state; no implied movement | Role named by the invoked check |
| Finalize a submission-bound artifact | Ship | M5 in Ph4, after MCR admission | Planner-orchestrated society |
| Extract lessons from a round | Reflect | Current state; full close-out in Ph4 | Reflector |

Whole-lifecycle or academic-deliverable requests first resolve the project and
assignment contract under `FULL_RUN_CONTRACT.md`. They are never decomposed into
an informal seven-step lifecycle.

Transient proposal work declares `lab_iteration` and remains inside its
resolved governed staging/private-shipment destination. It cannot mutate the
lifecycle, create F9 authority, promote, claim terminal, or disseminate.

## 3. Milestone and phase discipline

- M1, M2, and M3 are separately presented and explicitly approved while the
  project remains in Ph1. Approval advances the milestone chain, not the phase.
- The Generator writes the exact M1–M4 deliverable bytes. The Planner dispatches,
  records approval, writes policy-correct handoff representations (including
  F9 only when required or explicitly requested), and mutates lifecycle state; it does not
  co-author the deliverable.
- The Evaluator performs the bounded all-drafts binding-derived applicable-policy pass for M1–M4 in Ph1, including centroid review only when the authoritative reader binding enables it. Full revision-maturity review first engages in Ph2
  to independently review M4.
- M3 is a structured outline only. Prose stubs belong to M4 initial assembly.
- M4 begins with initial manuscript assembly in Ph1, is independently reviewed in
  Ph2, iterates in Ph3, and becomes acceptance-ready only at `Ph3_converged`.
- Ph4 admission is licensed only by `mcr_admission` from `Ph3_converged` (subject
  to the canonical ceiling rules); user approval alone cannot jump to Ph4.
- Plain `user_approval` is not a Ph3 event: continuing work uses an iteration
  trigger, while convergence uses `ph3_convergence_signoff_terminal`.

## 4. Dispatch procedure

1. Resolve the project, assignment contract, active milestone, and current
   lifecycle state from authoritative state.
2. Use the table above to choose the entry intent; never write that label to the
   ledger.
3. Validate the requested move against `lifecycle_transitions.v1.json` and the
   deliverable dispatch against `role_output_contract.json`.
4. Run the applicable preflight and receipt transaction before any deliverable
   bytes are written.
5. Dispatch only the role authorized for the active milestone and state.
6. Present the resulting deliverable at its explicit user checkpoint. Record an
   approved milestone separately from any phase exit.

Ambiguity about the desired artifact is resolved with the user. Ambiguity never
licenses a guessed state transition, inferred acceptance, or Evaluator dispatch
inside Ph1.

## 5. Recovery

Recovery is a state-machine operation, not a free-form return to an intent label.
The exact recovery triggers and targets are enumerated in
`lifecycle_transitions.v1.json`. A reopened or invalidated upstream milestone
propagates staleness through the milestone framework without silently demoting
phase state; an actual phase demotion requires a licensed recovery transition.

## 6. Relationship to orchestration

`AGENT_ORCHESTRATION.md` defines cooperation inside the selected canonical state.
`PHASE_PROTOCOL.md` defines lifecycle semantics. `ASSIGNMENT_MILESTONE_PROCESS.md`
and `MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md` define milestone acceptance and
handoff. This file only connects user intent to those authorities.

The derived labels originate in the MIT-licensed gstack vocabulary. License and
attribution metadata live in `third_party_components.yaml` and `NOTICE`.
