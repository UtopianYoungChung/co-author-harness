---
name: run-reflection
description: 'Public 0.50 reflection coordinator on staging. Coordinates Planner, Generator, Evaluator, and Reflector after a certified shipment. Mode must be declared (lightweight or full). Does not apply to the workbench.'
trigger: 'when the user says "reflect," "run reflector," "check grounding," "what did we learn," or invokes "/run-reflection"'
version: 0.50.0
---

# run-reflection — public reflection coordinator (staging)

`/run-reflection` is a real public coordinator. It is not a degraded ad.
It coordinates the four plugin hands **on staging** after a certified
shipment. It does not accept milestones and does not apply to the workbench.

## Four hands

| Hand | Does | Does not |
|---|---|---|
| Planner | Declare mode; bind the certified shipment (exact path, exact hash) | Edit manuscript |
| Generator | No new publish unless a later coordinator run reserves a new READY | Chat-apply (SK-32); write the workbench |
| Evaluator | Prior certification of shipment bytes remains the object of reflection | Re-mint scholarly CLEAN; edit prose |
| Reflector | Probe (lightweight) or closeout (full) on the certified shipment | Accept milestones; apply to the workbench |

**Outside** the plugin: Writer remains the only apply step. Reflection never
applies.

## Require one mode

The dispatch must declare exactly one of:

| Declaration | Use | Binding implementation |
|---|---|---|
| `mode: lightweight` | Integrity probe after a certified staging shipment | `agents/reflector-probe.md` |
| `mode: full` | Close-out after a certified finalize shipment | `agents/reflector-closeout.md` |

A bare `/run-reflection` or an ambiguous request must **halt and ask** for
the mode. Never guess and never run both modes.

## Staging bound

Resolve the project root already established in the session. Reflection
reads project evidence; it never substitutes the package root for the
project root. It may write dest-safe reflection receipts under
`reviews/.harness/shipments/<id>/` and/or
`outputs/co-author-harness/staging/<work-id>/<run-id>/`.

**DEST-PROTECTED stays.** Do not write manuscript bytes onto
`research/60_Workbench/<work-id>/`. Do not edit manuscript prose. Do not
modify package files from a project reflection run. SK-32 stays closed.
No scholarly CLEAN mint.

Graph / centroid remain invoke-only / fail-closed. Citation / claim /
derivation / similar checks stay invoke-able; Evaluator still fires them
on shipment bytes. Do not fold them away here.

## Load one implementation in full

- For `mode: lightweight`, read `agents/reflector-probe.md` in full and
  follow it. It must not emit skill or plugin-update proposals.
- For `mode: full`, read `agents/reflector-closeout.md` in full and follow
  it. Full mode may emit the reflection report, approved project memory
  updates, and the proposal buffer described by the close-out procedure.

The shared epistemic contract is
`references/_snippets/reflection-grounding.md`. Do not separately inline or
reinterpret it here.

F7 evidence packets and F8 final reports are read-only inputs to
reflection. Lightweight mode emits its probe report only.
