# Design: Generator session-revision skill

**Status:** Approved (2026-04-25)  
**Scope:** co-author-harness plugin (co-author-harness-claude)  
**Related:** `agents/generator.md`, `references/GROUNDING_PROTOCOL.md`, `skills/plugin-commands/SKILL.md`

## 1. Problem

The shipped plugin exposes the **Generator** agent through **phase skills** (`/run-phase-1` … `/run-phase-4`) and separate **overlay** passes (e.g. sentence/narrative). It does **not** offer a dedicated way to turn **current-session chat** (agreed changes, critique, instructions) into **Generator-consistent revision work** on disk in one step. Users who drive work from conversation need a first-class invocation that does not require re-typing the same intent into a formal `revision_plan` flow.

## 2. Goal

Add a **slash skill** that:

1. Uses **this session’s chat memory** as the **instruction** layer for what to revise.
2. Applies **direct application (choice A):** concrete edits to `manuscript/*` and an entry in `manuscript/revision_log.md` in the same run (after at most a short in-chat clarification if scope is ambiguous).
3. Remains **always available** in the command catalog (“regardless of phase” in the sense of **discoverability**).
4. Still enforces **Generator authority** from real project state: `reviews/phase_state.json` and `reviews/classification.md` — not a fictional phase implied only by chat.

## 3. Non-goals (v1)

- **No writes under `reviews/`** by the Generator for this pass. Session intent is not persisted as a new Planner artefact in v1. The run may **read** `reviews/classification.md`, `reviews/phase_state.json`, and other allowed inputs; it does not add `session_revision_*.md` to `reviews/`.
- **Chat is not evidence** for new factual claims. `GROUNDING_PROTOCOL.md` still applies. Session content supplies **what to do**, not citable support for new assertions.
- **Not a ladder bypass:** this does not replace a full Evaluator-joined pass when the project’s workflow still requires it. The skill may **remind** the user to run the appropriate phase/overlay after a session pass.

## 4. User stories

- As an author, I can invoke a single command after a long chat about a section and have the model **apply** those edits to the manuscript without manually duplicating the thread into a plan file.
- As a maintainer, I can find this capability in `plugin-commands` and in release **skill** checks, with a **description** under the 500-character safety margin.

## 5. Authority and phase rules

- **Invocation** is not blocked by which phase the project is in (the skill is always listed when shipped).
- **Edits** must obey `agents/generator.md` for the **declared** `current_phase` and P-stage (from classification + phase state for the **target section**), including **Ph4 fix-only, no new prose** where that applies.
- If **minimum state is missing** (e.g. no `reviews/classification.md` or no applicable section in `reviews/phase_state.json`), the run **refuses to apply** and points to `/classify-manuscript` and the appropriate first phase skill. The skill does **not** invent phase or P-stage from chat.

- If session instructions would require **out-of-authority** work (e.g. large new content at Ph4), the run **applies** only what is allowed and **states in chat** what was deferred (and may note deferrals in `revision_log` as non-applied intent where consistent with `generator.md`).

## 6. Data flow (runtime)

1. **Intake:** Derive a bounded set of revision actions from the **current session** plus any explicit paths or section names the user gave in-thread.
2. **Disk state:** Read `reviews/classification.md`, `reviews/phase_state.json` (target section), and target `manuscript` files. Resolve which files to edit; if ambiguous, one short clarifying round in chat; if still unclear, **no file writes**.
3. **Authority map:** Map actions to allowed Generator operations for this phase/P-stage. Trim or split instructions that exceed authority; document the rest in chat (and, where allowed, in `revision_log` as non-applied).
4. **Execute:** Apply changes per `agents/generator.md` to `manuscript/*` and append `manuscript/revision_log.md` with a clear line that the **requirement source** was **session-sourced** and that grounding rules were followed (no new facts from chat without sources).
5. **Follow-up hint:** Suggest the next **phase** or **overlay** (e.g. full `/run-phase-2` or later) when the project’s ladder would normally expect it.

## 7. Optional INF3130 / external style path

- The plugin does **not** hardcode `B:\...` or any machine-specific path.
- If the project’s `CLAUDE.md` or `directives.md` names a local folder (e.g. INF3130 `resources_and_guides`), the **implementing** skill text may tell the model to read those files **when present** as an extra **style and checklist** layer, in addition to existing harness `references/` files already bound in `agents/generator.md`.
- If the path is absent, behavior uses only the shipped `references/` material (e.g. `project_writing_style_checklist.md` under the plugin root) — no failure.

**Follow-up (out of v1 spec):** optional strengthening of `sentence-level-pass` / `narrative-structure-pass` with the same path convention is a **separate** change set.

## 8. Command naming (decision)

- **Skill id (folder name):** `run-generator-session` (or equivalent kebab-case under the plugin’s `skills/` tree; exact name to match `SKILL.md` `name` field and one slash command the host exposes).
- **User-facing command:** e.g. `/run-generator-session` (exact string fixed at implementation; must be added to `plugin-commands` and stay consistent with the registry of shipped skills).

## 9. Safety and error handling

- **Ambiguous scope:** at most one short clarifying exchange; if unresolved, no writes.
- **Grounding:** new factual claims in prose require normal protocol (sources, `FACT NEEDED`, `UNVERIFIED` as appropriate). Chat does not add citations.
- **Phase mismatch:** no silent expansion of allowed operations; user sees what was not done and why.

## 10. Verification (implementation phase)

- **Release gates:** `python scripts/skill-check.py` (and related maintainer checks) pass; new skill `description` under 500 characters; `plugin-commands` updated.
- **Manual:** a small fixture project with set `phase_state` + short simulated chat instructions; confirm writes only under `manuscript/` and that refusal paths work when classification/phase state is missing.

## 11. Files to add or change (implementation — not part of this document’s approval)

- New: `skills/run-generator-session/SKILL.md` (or the chosen id).
- Update: `skills/plugin-commands/SKILL.md` (command routing + catalog row).
- Optional: `references/SESSION_GENERATOR_ROUTING.md` (or similar) only if the `SKILL.md` body would exceed maintainable size — progressive disclosure.
- Optional: cross-link from `agents/generator.md` or a harness index — implementation choice.

## 12. Open decisions (resolved for v1)

| Topic | Resolution |
|-------|------------|
| Plan vs direct apply | **Direct apply (A)**; optional brief clarifying questions only. |
| `reviews/` session artefact | **None in v1.** |
| Phase source of truth | **`phase_state` + `classification` only;** not chat. |
| INF3130 path | **Optional project directive;** not bundled. |

## 13. Self-review checklist (author)

- [x] No unresolved “TBD” in normative sections.
- [x] Aligned with `generator.md` (no `reviews` writes; tier authority).
- [x] Scope is one skill + `plugin-commands` update; larger checklist alignment is explicitly deferred.

---

*Next step: implementation plan (writing-plans workflow), then implementation PR.*
