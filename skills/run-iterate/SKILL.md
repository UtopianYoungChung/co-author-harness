---
name: run-iterate
description: 'Public 0.50 iterate coordinator on staging. Coordinates Planner, Generator, Evaluator, and Reflector for refine/structural/deep/stability. Generator publishes only via assignment_writer_commit.py to staging. Parked paper-specific bodies: run-phase-2, run-phase-3, run-phase-3-stability.'
trigger: 'when the user says "run iterate," "iterate," "stage = iterate," or invokes "/run-iterate"'
version: 0.50.0
user-invocable: true
---

# run-iterate — public iterate coordinator (staging)

## Output Profile

**Runtime binding.** Before acting, resolve
`../../references/_snippets/output-profile.md` relative to this `SKILL.md`,
read it in full, and treat it as part of this skill contract. Its canonical
plugin-root identity is `references/_snippets/output-profile.md`. Do not rely
on build-time include expansion.

`/run-iterate` is a real public coordinator. It is not a degraded ad and not
a chat-to-manuscript bypass. It coordinates the four plugin hands **on
staging** after a draft exists.

Output authority is `references/role_output_contract.json` 3.0.0. A readable
legacy artifact or file presence never proves shipment-v2 application or
acceptance.

## Four hands

| Hand | Does | Does not |
|---|---|---|
| Planner | One active target, profile bind, READY reserve | Edit manuscript |
| Generator | Rewrite/fix-apply **on staging** via `assignment_writer_commit.py` only | Publish to `research/60_Workbench`; chat-apply (SK-32) |
| Evaluator | Certify **shipment / staging bytes** (exact hash); fire citation / claim / derivation / similar checks | Edit prose; mint scholarly CLEAN |
| Reflector | Probe / closeout after a certified shipment | Accept milestones; promote research artifacts |

**Outside** the plugin: Writer is the apply step — exact path, exact hash.
If Writer edits on apply, that is a new draft.

**R-plane authority.** Joseph is the only R-plane actor. Milestone accepts are ongoing until M5 is produced; a prior accept is the current working hash, not a freeze. First-start of M1–M4 is an earning order. After materials are in play, any of M1–M4 may be named for restage. File presence is never materials-in-play. M5 requires four current accepted hashes and is the one-way door. No agent promotes research artifacts.

## Profiles

| Invocation | Stage | Profile |
|---|---|---|
| `/run-iterate --profile refine` | `iterate` | `refine` |
| `/run-iterate --profile structural` | `iterate` | `structural` |
| `/run-iterate --profile deep` | `iterate` | `deep` |
| `/run-iterate --profile stability` | `iterate` | `stability` |

If no profile is supplied, read the project's F6 dispatch plan. If the F6 is
absent, default `refine` for ordinary revision. Stability cannot satisfy
pre-MCR deep-pass or mint CLEAN.

## Staging loop

1. Planner binds one active target and the selected profile. No manuscript write.
2. Generator publishes staging bytes only through
   `python scripts/assignment_writer_commit.py --project-root <project> --receipt <receipt> --plan <plan>`.
3. Evaluator certifies those exact shipment bytes (exact hash). Citation,
   claim, derivation, and similar checks stay invoke-able and still fire.
4. Reflector may probe after a certified shipment.
5. Writer (outside the plugin) applies exact path, exact hash.

**DEST-PROTECTED stays.** Refuse a direct write of manuscript bytes onto
`research/60_Workbench/<work-id>/`. Derived handoff remains valid. No CLEAN
mint. SK-32 stays `CLOSED_PUBLIC_BYPASS`.

Graph / centroid remain invoke-only / fail-closed. Do not auto-dispatch
`centroid-pass`, `centroid-sentence-logic`, `quick-deterministic`, or
`classify-manuscript` as scholarly CLEAN.

Dest-safe receipts may land under
`reviews/.harness/shipments/<id>/` and/or
`outputs/co-author-harness/staging/<work-id>/<run-id>/`.
`scripts/draft_governance.py` stays dest-safe (`evaluation-lane`,
`attach-verifier-receipt`; no CLEAN bind).

### Evaluator fire table

Evaluator must fire these skills against certified staging bytes. Dest-safe
evaluation-lane does not stamp them completed/INFO. Findings land under the
shipment lane. Evaluator (or `attach-verifier-receipt`) binds
`assignment_dispatch` receipts. `scripts/scholarly_evaluation.py` verifies the
C6 profile (claim, derivation, warrant, citation) on those exact bytes.
Evaluate verify refuses completion if those receipts or C6 results are missing.
Named-milestone evaluate of already-staged bytes uses `--stage evaluate` / `derive --purpose evaluate`; dest-safe sequence, source-hash, and wiki-grounding misses do not exit-4 that C6 path. File presence is never acceptance. FINAL still requires accepted M1-M4.
Fire table: grounding-protocol, citation-discipline, claim-coverage,
derivation-check, grammar-mechanics, contradictions, analytic-construction,
centroid-evaluation (graph fail-closes when semantic_usage=not_invoked).
Mechanical dest-safe preflight only: d-style-profile, deterministic-audit.
No scholarly CLEAN.

## Parked compatibility bodies

These remain on disk as **parked paper-specific compatibility bodies**. They
are not public 0.50 coordinators and are not the live implementation this
coordinator follows:

- `skills/run-phase-2/SKILL.md` — parked refine compatibility (`run-phase-2`)
- `skills/run-phase-3/SKILL.md` — parked full-iterate compatibility (`run-phase-3`)
- `skills/run-phase-3-stability/SKILL.md` — parked stability compatibility

Do not advertise `/run-phase-2`, `/run-phase-3`, or `/run-phase-4` as public
names.
