---
name: run-reflection
description: "Public reflection router with two explicit modes: lightweight integrity probing during Ph1-Ph3, or full close-out after Ph4/G.4. The mode must be declared; the router never guesses."
trigger: 'when the user says "reflect," "run reflector," "check grounding," "what did we learn," or invokes "/run-reflection"'
version: 1.1
---

# Run Reflection — Public Mode Router

`/run-reflection` is the single public entrypoint for reflection. It selects
exactly one internal implementation prompt; it does not duplicate either
procedure.

> **File resolution.** Resolve package files beneath `${CLAUDE_PLUGIN_ROOT}`.
> If that variable is unavailable, resolve `skills/run-reflection/SKILL.md`
> from the workspace root the user opened. Never use a machine-pinned package
> path.

## 1. Resolve the project

Use the project root already established in the session. If no project root is
established, halt and ask for it. Reflection reads and writes project evidence;
it never substitutes the package root for the project root.

## 2. Require one mode

The dispatch must declare exactly one of:

| Declaration | Lifecycle use | Binding implementation |
|---|---|---|
| `mode: lightweight` | On-demand integrity probe during Ph1, Ph2, or Ph3 | `agents/reflector-probe.md` |
| `mode: full` | Ph4 close-out after G.4 PASS | `agents/reflector-closeout.md` |

The Planner may derive the declaration from an unambiguous lifecycle dispatch:
an optional Ph1-Ph3 probe means `mode: lightweight`; the mandatory Ph4
close-out means `mode: full`. A bare `/run-reflection`, legacy `reflector`
dispatch, or user request whose lifecycle position is ambiguous must **halt and
ask** for the mode. Never guess and never run both modes.

## 3. Load one implementation in full

- For `mode: lightweight`, read
  `${CLAUDE_PLUGIN_ROOT}/agents/reflector-probe.md` in full and follow it as the
  binding procedure. It may run the gated grounding and ledger-integrity audit;
  it must not emit skill or plugin-update proposals.
- For `mode: full`, read
  `${CLAUDE_PLUGIN_ROOT}/agents/reflector-closeout.md` in full and follow it as
  the binding procedure. It runs the Ph4 close-out envelope, including its
  proposal-routing and self-audit rules.

The shared epistemic contract is included by those implementation prompts from
`references/_snippets/reflection-grounding.md`. Do not separately inline or
reinterpret it here.

## Output contract

F7 evidence packets and F8 final reports are read-only inputs to reflection;
the Reflector does not create or amend them. Mode-specific reports and
project-memory writes follow only the selected implementation's write boundary
in `references/_snippets/reflection-grounding.md`. Lightweight mode emits its
probe report only. Full mode may emit the reflection report, approved project
memory updates, and proposal buffer described by the close-out procedure.

## Boundaries

- Do not edit manuscript prose.
- Do not modify package files from a project reflection run.
- Do not let lightweight mode emit close-out proposals.
- Do not let full mode run before its Ph4/G.4 admission conditions.
- Do not claim Wiki mutation success while the capability registry reports the
  corresponding service unavailable.
