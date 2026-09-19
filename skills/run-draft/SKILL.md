---
name: run-draft
description: 'Draft from a brief without a pre-existing project using distinct native Generator, Evaluator and Reflector contexts, exact-byte review and required closeout. Explicit governed lifecycle requests retain assignment publication and acceptance gates.'
trigger: 'when the user says "run draft," "begin draft," "stage = draft," or invokes "/run-draft"'
version: 0.50.0
user-invocable: true
---

## Ordinary drafting and revision

Ordinary requests use `project_independent`; follow
`references/PROJECT_INDEPENDENT_WORKFLOW.md` before the governed workflow below.
The caller may be Planner; Generator, Evaluator and Reflector are distinct real
native child contexts. Bind the brief, input, scope, rules, exclusions and output
authority; wait for actual child outcomes. Reflection closeout is required.
Task completion is verified separately from scholarly CLEAN, lifecycle terminal
status and research acceptance. A missing child capability blocks this workflow
with `PIW-HOST-CAPABILITY-UNAVAILABLE`; read-only passes remain available.

For an existing manuscript, independent diagnosis precedes the Planner's revision
plan and Generator edits. Preserve unrequested bytes, terms, claims and citations.
Proposal-only delivery leaves the original untouched. Every correction returns to
Evaluator, with three correction cycles by default; unresolved findings end
`needs_revision`. New Reflector findings reopen correction and evaluation.

Chung voice applies only when selected and never when explicitly excluded.
Propagate the exclusion through every role brief, applied-rule list, fire table
and correction. A required file read does not activate an excluded overlay.
Graph unavailability limits graph-dependent checks; requested rule-based checks
and admitted-source sentence judgments can still run. See the shared runbook.

The remainder is the **governed project workflow**, used for an explicit
`full_lifecycle` or `lab_iteration` operation. Its assignment, source, publication,
protected-destination and author-acceptance prerequisites remain in force.



# run-draft — public draft coordinator (staging)

**Bibliography evidence.** Apply `references/CITATION_DISCIPLINE.md` §6 through discovery, generation and evaluation. Require complete reference/use assessments in existing role evidence before substantive completion; current-state claims need current evidence, and advisor guidance is not automatically a reference.

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

**R-plane authority.** Joseph is the only R-plane actor. Milestone accepts are ongoing until M5 is produced; a prior accept is the current working hash, not a freeze. First-start of M1–M4 is an earning order. After materials are in play, any of M1–M4 may be named for restage. File presence is never materials-in-play. M5 requires four current accepted hashes and is the one-way door. No agent promotes research artifacts.

## Staging loop

1. Planner binds one active target and reserves READY. No manuscript write.
2. Generator publishes staging bytes only through
   `python scripts/assignment_writer_commit.py --project-root <project> --receipt <receipt> --plan <plan>`.
   Staging roots are
   `<workspace-root>/outputs/co-author-harness/staging/<work-id>/<run-id>/`
   and dest-safe receipts under
   `research/60_Workbench/<work-id>/reviews/harness/shipments/<shipment-id>/`.
3. Evaluator certifies those exact shipment bytes (exact hash).
4. Reflector performs the required scoped closeout after a certified shipment. It does not accept
   milestones and does not promote research artifacts.
5. Writer (outside the plugin) is the only apply step: exact path, exact hash.

### Evaluator fire table

Evaluator must fire these skills against certified staging bytes. Dest-safe
evaluation-lane does not stamp them completed/INFO. Findings land under the
shipment lane. Evaluator (or `attach-verifier-receipt`) binds
`assignment_dispatch` receipts. `scripts/scholarly_evaluation.py` verifies the
C6 profile (claim, derivation, warrant, citation) on those exact bytes.
Bind `SCAFFOLD-NOTE.json` / `EVALUATION-LANE.json` `dest_safe_scholarly_profile.scholarly_profile`
as the evaluation `scholarly_profile`. Do not point C6 at a missing
`policy/scholarly-profile.json`. Evaluate verify refuses completion if those
receipts or C6 results are missing.
Named-milestone evaluate of already-staged bytes uses `--stage evaluate` / `derive --purpose evaluate`; dest-safe sequence, source-hash, and wiki-grounding misses do not exit-4 that C6 path. A missing Generator envelope or empty `assignment_dispatch` does not prevent C6 claim/derivation/warrant/citation of those bytes; C6 does not invent an envelope or mint CLEAN. Present stale/wrong envelopes still refuse. File presence is never acceptance. FINAL still requires accepted M1-M4.
- **Grounding protocol** (grounding-protocol): Rule 4 quote-before-attribute, Rule 6 no-gap-filling
- **Citation discipline** (citation-discipline): citation integrity, source traceback
- **Claim coverage** (claim-coverage): evidence coverage for load-bearing claims
- **Derivation check** (derivation-check): stipulated vs. derived terms
- **Grammar mechanics** (grammar-mechanics): mechanical correctness
- **Contradictions** (contradictions): SAFEGUARD Check 4 same-diff contradictions
- **Analytic construction** (analytic-construction): Abbott 7-move audit when applicable
- **Abstract-body** (check-abstract-body): title/abstract payoff, §1 roadmap, abstract citation polarity (named `abstract_citation_policy` only; `tbd` is INFO and not an insert/strip mandate)
- **Chung academic voice** (chung-academic-voice-pass): only when selected and not explicitly excluded; record exclusion separately from any required read
- **Centroid bind/join** (centroid-evaluation): graph retrieval is unavailable when semantic_usage=not_invoked; requested admitted-passage judgment remains available

Mechanical dest-safe preflight only: d-style-profile, deterministic-audit. Do not mint scholarly CLEAN.

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

Declare exactly `adhoc_review`, `project_independent`, `lab_iteration`, or
`full_lifecycle`; put the same `run_scope:` in every child brief, including
Reflector. Ordinary drafting does not require bootstrap. Explicit whole-lifecycle
intent ("harness full run", "run the ladder", Ph4, M1-M5 acceptance/finalization)
retains the native project prerequisites in `references/FULL_RUN_CONTRACT.md`.
If no governed project exists, stop at the canonical
`python scripts/native_project_bootstrap.py ...` instruction; that bootstrap
must install reader-profile binding v2 before governed drafting or evaluation.
`lab_iteration` is proposal-only with an existing governed project, resolved
assignment contract and staging/private-shipment output, no lifecycle and no F9
authority. It never accepts milestones or writes authoritative research.

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
