---
name: run-phase-2
user-invocable: false
description: "Legacy compatibility router for the former Ph2 Review & Revise rung. Route to /run-iterate with profile=refine; preserve old invocations without advertising Ph2 as a public stage."
trigger: when the user says "Ph2 review-and-revise," "run phase 2," "first evaluator pass," or when older project automation invokes /run-phase-2
version: 0.15.1
---

# run-phase-2 -- compatibility router to /run-iterate refine

`/run-phase-2` is retained for backward compatibility with installed projects,
old slash-command histories, and references that have not yet migrated. It is no
longer a distinct public ladder stage. Treat this invocation as:

```yaml
stage: iterate
profile: refine
legacy_command: /run-phase-2
canonical_command: /run-iterate
canonical_skill: skills/run-iterate/SKILL.md
```

## What you do

Read `skills/run-iterate/SKILL.md`, then run the first-pass review under
`profile: refine`. If the project still has a legacy `current_phase: "Ph2"` row,
accept that row as a compatibility state and write the next ledger event using
the new shadow fields:

```yaml
stage: iterate
profile: refine
```

The compatibility rule is one-way: do not introduce a new public alias for Ph2,
and do not describe Ph2 as a fourth stage in user-facing command help. The public
ladder is now draft -> iterate -> finalize.

## Output Profile

**Runtime binding.** Before acting, resolve
`../../references/_snippets/output-profile.md` relative to this `SKILL.md`,
read it in full, and treat it as part of this skill contract. Its canonical
plugin-root identity is `references/_snippets/output-profile.md`. Do not rely
on build-time include expansion.

Compatibility invocations still write F7 evidence packets at
`reviews/.harness/evidence/<event_id>.json` and the matching event row with
`round_id` and `event_id`. Legacy Markdown exception artefacts remain allowed
when an escalation, verifier failure, or project directive requires a readable
report.

## 4. Legacy Step 0.5 Anchor

This section preserves the historical cross-reference
`skills/run-phase-2/SKILL.md §4 Step 0.5`. The behavior now belongs to
`/run-iterate --profile refine`, but the contract remains active for older
Planner and skill references.

0.5. **Planner: snowball-gate re-test + claim-coverage audit dispatch.** On a
first refine pass after draft approval, the Planner may re-test
`references_initialized`, dispatch `claim-coverage-audit`, and fan out
`extend-snowball-incremental` for uncovered claims exactly as anchored in
`agents/planner.md §Phase 3.8`. This preflight is discovery-layer work: it does
not block iterate/refine admission, does not rewrite manuscript prose, and does
not replace the Evaluator's judgment pass. It writes or consumes
`last_coverage_score` and emits the existing W/E notification codes declared in
`references/phase_notifications.yaml §4`.

If the audit returns CLEAN, proceed with the refine pass. If it returns
BELOW_THRESHOLD, continue the refine pass while bounded snowball extension runs
under the Planner cap. If it fails, surface `E-COVERAGE-AUDIT-FAILED` and still
continue unless the user or project directives halt the round.

## Legacy Compatibility

Older projects may still contain:

- `reviews/ph2_review_completion.md`
- `reviews/ph2_findings_<YYYY-MM-DD>_<cycle_id>.md`
- `current_phase: "Ph2"`
- references to `ph2_review_completion_signed`

Do not delete or rewrite those historical artefacts. Consume them as evidence
of the first review pass, then continue through `/run-iterate` with
`profile: refine`. New prose should call this the refine profile of the iterate
stage, not the Ph2 stage.
