---
name: run-draft
description: 'Public 0.50 draft coordinator on staging. Coordinates Planner, Generator, Evaluator, and Reflector. Generator publishes only via assignment_writer_commit.py to staging. Writer (outside the plugin) is the apply step. Parked paper-specific body: run-phase-1.'
trigger: 'when the user says "run draft," "begin draft," "stage = draft," or invokes "/run-draft"'
version: 0.50.0
---

# run-draft — public draft coordinator (staging)

`/run-draft` is a real public coordinator. It is not a degraded ad and not a
chat-to-manuscript bypass. It coordinates the four plugin hands **on staging**.

Output authority is `references/role_output_contract.json` 3.0.0. A readable
legacy artifact or file presence never proves shipment-v2 application or
acceptance.

## Four hands

| Hand | Does | Does not |
|---|---|---|
| Planner | One active target, assignment/phase bind, READY reserve | Edit manuscript |
| Generator | Rewrite/fix-apply **on staging** via `assignment_writer_commit.py` only | Publish to `research/60_Workbench`; chat-apply (SK-32) |
| Evaluator | Certify **shipment / staging bytes** (exact hash); fire citation / claim / derivation / similar checks | Edit prose; mint scholarly CLEAN |
| Reflector | Probe / closeout after a certified shipment | Accept milestones; promote research artifacts |

**Outside** the plugin: Writer is the apply step onto
`research/60_Workbench/<work-id>/` — exact path, exact hash. If Writer edits
on apply, that is a **new draft**, not the certified shipment. Grok Writer,
Reviewer, Wiki, Orchestrator, and Overseer are not plugin roles.

**R-plane authority.** Joseph is the only R-plane actor. Milestone accepts are ongoing until M5 is produced; a prior accept is the current working hash, not a freeze. Any iteration may require revision of any of M1–M4. No agent promotes research artifacts.

## Staging loop

1. Planner binds one active target and reserves READY. No manuscript write.
2. Generator publishes staging bytes only through
   `python scripts/assignment_writer_commit.py --project-root <project> --receipt <receipt> --plan <plan>`.
   Staging roots are
   `<workspace-root>/outputs/co-author-harness/staging/<work-id>/<run-id>/`
   and dest-safe receipts under
   `research/60_Workbench/<work-id>/reviews/.harness/shipments/<shipment-id>/`.
3. Evaluator certifies those exact shipment bytes (exact hash). Citation,
   claim, derivation, and similar checks stay invoke-able and still fire here.
   Do not fold them away. Do not mint scholarly CLEAN.
4. Reflector may probe after a certified shipment. It does not accept
   milestones and does not apply to the workbench.
5. Writer (outside the plugin) is the only apply step: exact path, exact hash.

**DEST-PROTECTED stays.** Refuse a direct write of manuscript bytes onto
`research/60_Workbench/<work-id>/`. `scripts/destination_capability.py` is the
write chokepoint. Derived handoff remains valid. No F9 invention. No CLEAN
mint. SK-32 `/run-generator-session` stays `CLOSED_PUBLIC_BYPASS`.

**Rule 6 enforcement (v0.50.0).** Generator must leave marked gaps
(`[CONCRETE EXAMPLE NEEDED]`, `[FACT NEEDED]`) rather than inventing plausible
scenes, named cases, or vivid details when no vault/plan case exists.
Grounding Protocol Rule 6 beats all stylistic pressure to add concrete details
(MASTER §I.2.3, Sexton, humanness guidance). No fabrication, even when it
would improve prose texture. See `agents/generator.md` "Rule 6 precedence"
binding constraint.

Graph / centroid remain invoke-only / fail-closed. Do not auto-dispatch
`centroid-pass`, `centroid-sentence-logic`, `quick-deterministic`, or
`classify-manuscript` as scholarly CLEAN. `GRAPH-SEMANTIC-INELIGIBLE` is
fail-closed, not a fabricated retrieval.

## Scope

Route exactly `adhoc_review`, `lab_iteration`, or `full_lifecycle`, and put
`run_scope:` matching the parent in every Planner, Generator, and Evaluator
brief. `lab_iteration` is proposal-only: existing governed project, resolved
assignment contract, resolved staging/private-shipment output, no lifecycle
and no F9 authority. It never accepts milestones, consumes handoffs, writes
authoritative research/final paths, or claims terminal completion.

Whole-lifecycle intent ("harness full run," "draft the whole paper") enters
this coordinator. With **no project at all**, fail closed into the canonical
bootstrap instruction rather than writing prose anywhere:
`python scripts/full_run_contract_check.py authorize --project-root <p>` is
the mechanical check, and a new native root is created only by
`python scripts/native_project_bootstrap.py ...`, which must install
reader-profile binding v2. Resolve the live
`milestone_framework.policy_bindings.reader_accessibility` binding
(path, sha256, `semantic_usage`) before any centroid or reader-conditioned
dispatch; do not treat the phrase "authoritative reader binding" as the
binding.

**Handoff policy.** New native bootstrap creates contract `1.1.0` with
explicit `derived` policy unless `--handoff-policy audited` is requested.
Valid `1.0.0` projects remain implicit audited without rewrite. Audited
requires exact F9 publication and consumption; derived acceptance is
authoritative without F9.

## Parked compatibility body

`skills/run-phase-1/SKILL.md` remains on disk as a **parked paper-specific
compatibility body**. It is not a public 0.50 coordinator and is not the
live implementation this coordinator follows. Keep it for old slash history
and paper-specific automation. Do not advertise `/run-phase-1` as a public
name.

| Parked name | Public coordinator | Stage |
|---|---|---|
| `run-phase-1` | `/run-draft` | `draft` |
| `run-phase-2` | `/run-iterate --profile refine` | `iterate` |
| `run-phase-3` | `/run-iterate` | `iterate` |
| `run-phase-4` | `/run-finalize` | `finalize` |
