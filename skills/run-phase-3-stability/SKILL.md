---
name: run-phase-3-stability
user-invocable: false
description: "Legacy compatibility router for the former Ph3 stability sub-mode. Route to /run-iterate with profile=stability; the stability envelope is now an iterate profile."
trigger: when the user says "run a stability pass," "Ph3 stability check," "byte-stable iteration," "S-0 gate check," or older automation invokes /run-phase-3-stability
version: 0.15.1
---

# run-phase-3-stability -- compatibility router to /run-iterate stability

`/run-phase-3-stability` is retained for backward compatibility with installed
projects, old slash-command histories, and references that have not yet
migrated. It is no longer a peer public skill beside `/run-iterate`; it is the
stability profile of the iterate stage.

Treat this invocation as:

```yaml
stage: iterate
profile: stability
legacy_command: /run-phase-3-stability
canonical_command: /run-iterate
canonical_skill: skills/run-iterate/SKILL.md
```

## What you do

Read `skills/run-iterate/SKILL.md` and follow the `profile: stability` branch.
The compatibility name preserves the old S-0 byte-stability trigger, but the
public routing vocabulary is `/run-iterate --profile stability`.

Before evaluating Check 8, load `runtime_modes.stability` from the resolved
reader-accessibility profile and the validated G/H/VE transition projection
from `phase_state.json`. This compatibility router owns no accessibility mode
behavior beyond those machine-bound values.

The S-0 gate, grounding audit, deterministic Check 8 counter comparison,
trigger-30 escalation to a full iterate pass, and the rule that stability cannot
satisfy the pre-MCR deep-pass requirement remain unchanged. The canonical body
for those rules now lives in `skills/run-iterate/SKILL.md`.

## 3. Legacy Stability Envelope Anchor

This section preserves historical references to `run-phase-3-stability §3`. The
behavior is now `/run-iterate --profile stability`, but the reduced envelope is
unchanged:

- S-0 byte-stability gate over F1/F2/F3/F5 substrate hashes.
- Grounding audit with the Rule 1 full-file read floor.
- Deterministic Check 8 counter comparison.
- No seven-step judgment pass, no Coupling E.2, no external-verifier probes, and
  no SAFEGUARD checks outside the inherited/check-counter path.
- Trigger-30 escalation to a full iterate pass on any finding.

### 3.2a Profile-bound G/H and adjacent VE treatment

This subsection preserves the historical `§3.2a` anchor cited by
`references/SAFEGUARD_LAYER.md`. Under `/run-iterate --profile stability`, all
accessibility aggregation and workflow effects are computed from
`runtime_modes.stability` plus the validated bound transition state. Do not add
a stability-only flag, member exclusion, severity rewrite, or escalation
exception in this router.

## Output Profile

Default profile: `silent_evidence`.

Compatibility invocations still write F7 evidence packets at
`reviews/.harness/evidence/<event_id>.json` and the matching event row with
`round_id` and `event_id`. Clean stability admissions should stay compact;
legacy Markdown reports are reserved for exception report paths such as
escalation, frontmatter drift, or verifier-contract failure.

## Legacy Compatibility

Do not delete or rewrite historical stability artefacts. Existing
`stability_mode_escalated_to_full_ph3` trigger rows, `stability_mode: true`
notes, and old F6 fields such as `stability_sub_mode_anticipated: true` remain
valid evidence. New dispatch plans should also write:

```yaml
stage: iterate
profile: stability
```
