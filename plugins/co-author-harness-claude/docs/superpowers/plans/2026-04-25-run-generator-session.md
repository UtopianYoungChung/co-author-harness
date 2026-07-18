# run-generator-session Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the shipped skill `run-generator-session` (`/run-generator-session`) that applies Generator-consistent manuscript edits from **current-session chat** per `docs/superpowers/specs/2026-04-25-generator-session-revision-design.md`, and update catalog/registry/version docs so `skill-check.py` and `catalog-check.py` pass.

**Architecture:** One new `skills/run-generator-session/SKILL.md` (instructional contract; no new Python). Update `plugin-commands` and `SKILL_REGISTRY` in lockstep. Bump plugin patch version and mirror version strings in the same places the repo already updates for releases.

**Tech stack:** Markdown skills, PyYAML (front matter), `python scripts/skill-check.py` / `catalog-check.py` / `version-check.py` / `path-hygiene-check.py`, `bash scripts/release-gate.sh` (optional before merge).

---

## File map (create / modify)

| File | Action |
|------|--------|
| `skills/run-generator-session/SKILL.md` | **Create** — full front matter + body |
| `skills/plugin-commands/SKILL.md` | **Modify** — routing table + `Command catalog` row for `` `/run-generator-session` `` |
| `references/SKILL_REGISTRY.md` | **Modify** — new `### SK-32. \`run-generator-session\`` block before the `---` that precedes `## Orchestration Commands` (after the `### SK-29. \`run-phase-2\`` block, ~line 340) |
| `README.md` | **Modify** — `### Skills (27)` → `### Skills (28)`; version table if bumping in same PR |
| `CHANGELOG.md` | **Modify** — new `v0.8.7` section (or agreed version) |
| `.claude-plugin/plugin.json` | **Modify** — `version`, `description` (≤ **400** chars; see `scripts/build-release-zip.sh`) |
| `CLAUDE.md` | **Modify** — substrate version strings if project convention ties them to `plugin.json` |
| `docs/agent-instructions/harness-architecture.md` | **Modify** — `v0.8.6+` / heading line to match new version if this is the standard release sweep |
| `docs/agent-instructions/harness-reference-index.md` | **Modify** — manifest version row |
| `docs/agent-instructions/harness-history.md` | **Modify** — substrate line if this is the standard release sweep |
| `docs/release-notes/RELEASE_NOTES_v0.8.7.md` | **Create** — if other releases in this repo always add one; else fold highlights into `CHANGELOG` only and skip |
| `agents/generator.md` | **Optional** — 2–3 lines after the role block pointing to the new skill |

---

### Task 1: Create `skills/run-generator-session/SKILL.md`

**Files:**

- **Create:** `skills/run-generator-session/SKILL.md`

- [ ] **Step 1: Write the file with this exact content** (set `version: 1.0` in front matter; do not add extra keys beyond what `REQUIRED_FRONTMATTER_KEYS` in `scripts/skill-check.py` lists — the script requires only `name`, `description`, `trigger`, `version`).

- [ ] **Step 2: Run description length** — `description` in front matter must be **≤ 500** characters. From repo root:  
  `python -c "import yaml,re; t=open('skills/run-generator-session/SKILL.md',encoding='utf-8').read(); m=re.search(r'^---\n(.*?)\n---',t,re.S); d=yaml.safe_load(m.group(1))['description']; print(len(d), d[:80])"`  
  **Expected:** First number is **500 or less**, script prints without error.

- [ ] **Step 3: Commit**

```bash
git add skills/run-generator-session/SKILL.md
git commit -m "feat(skill): add run-generator-session for session-sourced Generator passes"
```

**File content (full):**

```markdown
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
```

---

### Task 2: Update `plugin-commands` catalog and routing

**Files:**

- **Modify:** `skills/plugin-commands/SKILL.md`

- [ ] **Step 1: Add a routing row** in `## Command routing (quick)` after the `Advisor MCP` row (or a sensible row). Example row:

```markdown
| Session chat should become manuscript edits (Generator) — requirements from thread, not from formal revision_plan only | `/run-generator-session` — load `agents/generator.md` authority from real `phase_state` + `classification` |
```

- [ ] **Step 2: Add a catalog table row** in `## Command catalog` in **alphabetical** order with other `run-*` / `g*` commands — match column pattern `| \`/name\` | ... |` exactly so `parse_plugin_commands` in `scripts/skill-check.py` still matches `^\|\s*\`/([^`]+)\`\s*\|`.

Use this text (tune for length if the table over-wraps, but keep the pipe structure):

```markdown
| `/run-generator-session` | **Session-sourced Generator** — apply the current session’s agreed revision instructions to `manuscript/*` under the real `current_phase` from `reviews/phase_state.json`; requires `classification` + a resolvable section. Chat is not evidence. Writes `manuscript` + `revision_log` only. | After extended chat about a section: turn decisions into on-disk draft/fixes without re-typing a formal plan. |
```

- [ ] **Step 3: If `## NEVER` or guardrails need one bullet** (optional): add: “Do not treat `/run-generator-session` as a substitute for a full Ph2+ Evaluator pass when the ladder requires that round.”

- [ ] **Step 4: Commit**

```bash
git add skills/plugin-commands/SKILL.md
git commit -m "docs(plugin-commands): register /run-generator-session"
```

---

### Task 3: Add `SK-32` to `references/SKILL_REGISTRY.md`

**Files:**

- **Modify:** `references/SKILL_REGISTRY.md` (insert before the `---` that precedes `## Orchestration Commands`).

- [ ] **Step 1: Insert this block** (after the `### SK-29. \`run-phase-2\`` section’s content, before `---` / `## Orchestration Commands`).

```markdown
### SK-32. `run-generator-session`
- **File:** `skills/run-generator-session/SKILL.md`
- **Pattern:** **Session-sourced Generator** pass — the current chat supplies revision *instructions*; `reviews/classification.md` and `reviews/phase_state.json` supply *authority* (phase, P-stage, ceiling). No new `reviews/` session artefacts in v1. Aligned with `docs/superpowers/specs/2026-04-25-generator-session-revision-design.md` and `agents/generator.md` (manuscript + `manuscript/revision_log.md` only; no `reviews` writes by the Generator).
- **Created:** 2026-04-25
- **Source:** Brainstorming + approved design spec `docs/superpowers/specs/2026-04-25-generator-session-revision-design.md`
- **Tier:** Package
- **Status:** Active
- **Depends on:** `agents/generator.md`, `references/GROUNDING_PROTOCOL.md`, `reviews/classification.md`, `reviews/phase_state.json`, optional project-local style path via `CLAUDE.md` / `directives.md`
- **Sibling:** SK-25 `run-phase-1` … SK-27 `run-phase-4` (full ladder entry points with Planner/Evaluator packaging); SK-23 `plugin-commands` (discovery); SK-07 `sentence-level-pass` / SK-08 `narrative-structure-pass` (craft overlays, not the Generator role file)
- **Not a replacement for:** full `/run-phase-2+` with Evaluator when the project’s governance still requires that round; does not create Planner artefacts
```

- [ ] **Step 2: Commit**

```bash
git add references/SKILL_REGISTRY.md
git commit -m "docs(registry): add SK-32 run-generator-session"
```

---

### Task 4: Version and documentation sweep (0.8.6 → 0.8.7)

**Files (modify as listed; keep `plugin.json` `description` ≤ 400 characters — count with `python` like Task 1).**

- [ ] **Step 1:** `README.md` — `### Skills (27)` → `### Skills (28)`; update badge, `## Version` value, and add table row for **0.8.7** with one-line highlight (`run-generator-session`).

- [ ] **Step 2:** `CHANGELOG.md` — new top section:

```markdown
## v0.8.7 — 2026-04-25

**Theme.** Session-sourced Generator skill and catalog wiring.

### Changes

- **New skill** — `run-generator-session` (`/run-generator-session`): apply chat-originated revision instructions under real `phase_state` + `classification` per approved design `docs/superpowers/specs/2026-04-25-generator-session-revision-design.md`.
- **Registry** — `SKILL_REGISTRY` SK-32; `plugin-commands` routing + catalog.
```

(Adjust the date in the `##` line if the ship date is not 2026-04-25.)

- [ ] **Step 3:** `.claude-plugin/plugin.json` — `"version": "0.8.7"`; refresh `description` to mention the new skill in <400 characters (e.g. end with "… v0.8.7: /run-generator-session; see CHANGELOG").

- [ ] **Step 4:** `CLAUDE.md` — set harness substrate string(s) to **v0.8.7** where they currently read **v0.8.6** (see grep results from planning).

- [ ] **Step 5:** `docs/agent-instructions/harness-architecture.md` — `v0.8.6` / `v0.8.6+` → **v0.8.7** / **v0.8.7+** as in prior releases.

- [ ] **Step 6:** `docs/agent-instructions/harness-reference-index.md` — manifest table **v0.8.6** → **v0.8.7**.

- [ ] **Step 7:** `docs/agent-instructions/harness-history.md` — substrate line **v0.8.6+** → **v0.8.7+** if that is the project pattern.

- [ ] **Step 8 (optional, match v0.8.6 pattern):** create `docs/release-notes/RELEASE_NOTES_v0.8.7.md` from the `RELEASE_NOTES_v0.8.6.md` template with version strings replaced.

- [ ] **Step 9: Commit documentation**

```bash
git add README.md CHANGELOG.md .claude-plugin/plugin.json CLAUDE.md docs/agent-instructions/harness-architecture.md docs/agent-instructions/harness-reference-index.md docs/agent-instructions/harness-history.md
# plus release notes if created
git commit -m "chore(release): v0.8.7 — run-generator-session"
```

---

### Task 5: Optional one-line in `agents/generator.md`

**Files:**

- **Modify:** `agents/generator.md` (top “Role” or “File resolution” area)

- [ ] **Step 1: Insert 2–3 sentences**, for example after the first **Role** paragraph:

```markdown
**Session-sourced work.** If the user invokes the shipped skill `run-generator-session` (`/run-generator-session`), treat the *requirements* as coming from the current session; **authority** (phase, P-stage, what prose operations are allowed) still comes from `reviews/phase_state.json` and `reviews/classification.md` — see `skills/run-generator-session/SKILL.md` and `docs/superpowers/specs/2026-04-25-generator-session-revision-design.md`.
```

- [ ] **Step 2: Commit** (or squash with Task 1 if you prefer a single feature commit; separate commit is fine for review clarity).

```bash
git add agents/generator.md
git commit -m "docs(generator): point to run-generator-session skill"
```

---

### Task 6: Verify (must pass before merge)

**Run from the plugin root** (`co-author-harness`).

- [ ] **Step 1**

```bash
python scripts/skill-check.py
python scripts/catalog-check.py
python scripts/version-check.py
python scripts/path-hygiene-check.py
```

**Expected:** `Blockers: 0` in each `skill-check` / `catalog-check` / `version-check` output; `path-hygiene` reports `Blockers: 0`.

- [ ] **Step 2 (optional but recommended)**

```bash
bash scripts/release-gate.sh
```

**Expected:** `VERDICT: CLEARED` (or the same end state the repo used for the last good release; fix any new WARNs).

- [ ] **Step 3: Manual** — per spec §10: a toy project with `reviews/classification.md` and `reviews/phase_state.json` and a `manuscript` file; run the new skill in the harness and confirm (a) refusal if classification/phase state missing, (b) `manuscript` + `revision_log` updated when preconditions pass, (c) no new `reviews/` file from the Generator path.

**No new pytest** — this feature is contract Markdown + registry parity; automated checks are the four Python scripts above.

---

## Self-review (plan vs spec)

| Spec section | Task coverage |
|--------------|---------------|
| Session → instructions, direct apply, no reviews artefacts | Task 1 body + Task 1 “must not” |
| Phase from `phase_state` + `classification` only | Task 1 preconditions + authority table |
| GROUNDING: chat not evidence | Task 1 intake + must not |
| Optional INF3130 / path via `CLAUDE.md` | Task 1 “Optional local style path” |
| `plugin-commands` + `SKILL_REGISTRY` + `skill-check` | Tasks 2–3, Task 6 |
| Version / README count | Task 4 |
| Verification / manual | Task 6 |

**Placeholder scan:** This plan has no TBD’s in executable steps; the only “optional” path is the optional `release-gate` and optional `RELEASE_NOTES` and optional `generator.md` line.

**Consistency:** Skill name `run-generator-session` is used in front matter, registry, and catalog row; slash command `` `/run-generator-session` `` matches the `name` in `skill-check` (command table key is the part after the slash, same as `plugin-commands` for other skills).

---

## Execution handoff

**Plan complete and saved to** `docs/superpowers/plans/2026-04-25-run-generator-session.md`. **Two execution options:**

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task; review between tasks. **Use** `superpowers:subagent-driven-development` per task in order.

2. **Inline execution** — run tasks in this session with checkpoints. **Use** `superpowers:executing-plans` for batching and review gates.

**Which approach?**

After implementation, you may bundle `build-release-zip` and a tag as a separate release step (not in this file’s checkboxes) per maintainer process.

---

## Commit: plan file (this repository)

- [ ] **Commit the plan itself** (if not already committed):

```bash
git add docs/superpowers/plans/2026-04-25-run-generator-session.md
git commit -m "docs(plans): implementation plan for run-generator-session (v0.8.7)"
```
