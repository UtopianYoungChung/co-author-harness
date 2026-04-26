---
name: run-generator-session
description: 'Session-sourced Generator: apply the current chat as revision instructions to the manuscript under real phase_state + classification. Chat is not evidence. Refuses if classification/section state missing. Obeys agents/generator.md. Writes manuscript/* and revision_log only. Triggers: session revision, apply what we agreed, /run-generator-session.'
trigger: 'when the user asks to apply the current session discussion to the manuscript, generate revision work from chat memory, run the Generator from this conversation, or says /run-generator-session'
version: 1.0
---

# run-generator-session — Generator pass from session chat

**Grounding basis:** `agents/generator.md`; `references/GROUNDING_PROTOCOL.md`; `docs/superpowers/specs/2026-04-25-generator-session-revision-design.md` (approved design).

You run a **Generator-consistent** pass whose **requirements** come from **this session's chat** (agreed edits, critique, lists). You do **not** use chat as evidence for factual claims.

## Preconditions (hard stop)

Before writing any manuscript file, confirm all of the following. If any check fails, **do not** write to `manuscript/`; state the user’s next step and the canonical slash to run.

1. **`reviews/classification.md` exists** (or the file the project’s `CLAUDE.md` names as the classification source). If missing: use `/classify-manuscript` first.
2. **`reviews/phase_state.json` exists** and includes a **section** entry for the user’s target. If the user did not name a section, ask **one** short question (concrete `heading_path` or `manuscript/…` file). If still unclear, **no writes** (spec §6).
3. Read **`current_phase`**, **`ph1_pstage_declaration`**, and the section’s ceiling fields from `phase_state` and classification. **Do not** infer phase or P-stage from chat.

## Authority (from disk, not from chat)

Obey `agents/generator.md` for the **declared** `current_phase` (summary):

| Declared phase | What you may do to prose (high level) |
|----------------|--------------------------------------|
| Ph1 Plan & Draft | Draft and revise under the P-stage register within normal Generator scope. |
| Ph2 / Ph3 | Apply fixes and revisions under the P-stage register. |
| Ph4 Finalize & Close | **Fix-only, no new substantive prose** — trim, tighten, close gaps per findings; do not add new major content. |

If the chat asks for work **outside** that authority, apply the allowed subset; in chat, list what was **deferred**; in `manuscript/revision_log.md` note deferred intent only if a short non-prose “session deferral” line is allowed without violating `generator.md` (if unclear, only report deferrals in chat).

## Session intake

1. Build a **short, ordered list** of revision actions from this conversation. Prefer explicit file paths the user already named.
2. **Chat is not a source for facts.** If new factual sentences are needed without sources, use `[FACT NEEDED]`, `[UNVERIFIED]`, or leave markers per `GROUNDING_PROTOCOL.md` — do not invent citations from the thread.
3. For Rule 1: **read sources in full** for any claim you add or that you change in a way that needs citation support, same as any Generator pass.

## Optional local style path (never blocking)

- If the project’s `CLAUDE.md` or `directives.md` (or a named path there) points to a folder such as `resources_and_guides` (e.g. course HCI materials), you **may** read those files for style and checklist alignment.
- If not present, rely on the shipped `references/` pack already listed in `agents/generator.md` (e.g. `references/project_writing_style_checklist.md`).
- **Never** embed or assume a machine-absolute path from examples in the spec.

## Execution

1. Open and edit only **`manuscript/*`** and append **`manuscript/revision_log.md`**. **Do not** create new files under `reviews/` for this pass (v1 spec).
2. `revision_log` entry at minimum:
   - marker that the pass was **`run-generator-session`**
   - **Source of requirements:** session chat (instructional, not citable)
   - **Phase authority used:** the section’s `current_phase` as read from disk
   - files touched; optional one-line “deferred (authority)” if applicable

## You must not

- Write deterministic findings, `phase_state` rows, MCR, or any other **`reviews/` artefact** — Generator and this skill do not claim Planner/Evaluator scope.
- Skip recommending a full **`/run-phase-*`** (or the Evaluator) when the project’s ladder and `ROUTING_SPINE` still require that step for the user’s true next gate.
- Use chat to justify uncited numbers, statistics, or attributions to authors.

## After completion

- One short **follow-up line:** which full phase or overlay the user will likely need next, based on their `current_phase` (e.g. Ph2+ → Evaluator-joined work still matters for a complete round).

---

*This skill is session-first (chat-driven) but **phase-true** (authority from the ledger), per the 2026-04-25 design spec.*
