---
name: plugin-commands
description: 'Show all slash commands in the co-author-harness plugin, each with purpose and invocation moment, plus the manual script commands (sk20 preflight/overlay/autonomous-loop, release-gate). Use when: "what commands are available", "list plugin skills", "slash command help", first-time orientation, host omits a slash, or unclassified project routing.'
trigger: 'Catalog and routing for this package’s shipped slash names and script entrypoints (details in description and body).'
version: 1.2
---

# Plugin Commands

List slash commands shipped in this plugin: use the **Command routing** table to pick a path, then the full **Command catalog** for detail.

## What to output

Return a concise command catalog with:
- command name
- one-line purpose
- best-use moment

If routing is ambiguous, state the single recommended next command in one line and why.

## Command routing (quick)

| Situation | Start here |
|---|---|
| New project, unknown P-stage, or no `reviews/classification.md` yet | `/classify-manuscript` before phase runs that expect classification. |
| New section, ceiling T1 | `/run-phase-1` (Step 4.5 auto-invokes `/seed-snowball-discovery` if `references_initialized: false`) |
| Fresh section needs a saturated reference pool before drafting (Ph1 entry; v0.10.0+) | `/seed-snowball-discovery` — Wohlin-style snowball; wiki-graph substrate first; Class 1 fall-through |
| After T1 approval, section climbing | `/run-phase-2` |
| Default T3 full iteration | `/run-phase-3` |
| Substrate byte-identical to last Ph3 close; same bytes, another pass | `/run-phase-3-stability` (escalate to full `/run-phase-3` on any finding) |
| Final sign-off, MCR, external handoff | `/run-phase-4` (only when ladder/MCR preconditions in project docs are met) |
| Pre-release, external verifier contract check | `/tool-contract-roundtrip` |
| **Advisor MCP** — after Ph2, before Ph3 (EP-1) or after Ph3_converged, before MCR/Ph4 (EP-2) | `/advisor-escalation` — see `references/ADVISOR_MCP.md`; host must expose advisor MCP |
| Session chat should become manuscript edits (Generator) — requirements from thread, not from formal `revision_plan` only | `/run-generator-session` — load `agents/generator.md` authority from real `phase_state` + `classification` |
| Orientation only: “what exists in this package?” | `/plugin-commands` (this file) |

## Command catalog

| Command | Purpose | Best use |
|---|---|---|
| `/plugin-commands` | List all plugin slash commands and usage moments. | First-time orientation or quick recall. |
| `/classify-manuscript` | Classify paper type, P-stage, venue, and default final tier (T1–T4 / T3R) of the v0.7.0 Lifecycle-Stage Ladder. | Before any review work starts. |
| `/run-generator-session` | **Session-sourced Generator** — apply the current session’s agreed revision instructions to `manuscript/*` under the real `current_phase` from `reviews/phase_state.json`; requires `classification` + a resolvable section. Chat is not evidence. Writes `manuscript` + `revision_log` only. | After extended chat about a section: turn decisions into on-disk draft/fixes without re-typing a formal plan. |
| `/run-phase-1` | T1 Plan & Draft — Planner bootstraps the 15-field section state; Generator drafts under the declared P-stage register. **When `sd_sr_required: true` in `reviews/classification.md`** (v0.7.1 opt-in; default `false`), the Planner additionally authors i* SD/SR models and runs the §3.1.1 structural-completeness validator. No Evaluator; no Self-T1 Verdict (retired at v0.7.0). | First rung for a new section or section whose ceiling is T1. |
| `/seed-snowball-discovery` | Ph1 entry — assemble references/REFERENCES.md from a section's claim register via Wohlin-style snowball saturation; wiki-graph substrate first; Class 1 verifier fall-through; in-loop wiki/sources/ stub write-back. Auto-invoked by `/run-phase-1` Step 4.5 when `references_initialized: false`. New at v0.10.0. | Fresh section with no curated reference pool; wiki-linked or unlinked. |
| `/run-phase-2` | T2 Review & Revise — first Evaluator-joined rung; full local-scope pass every entry (Confirmation Mode retired at v0.7.0). Pre-tier-advance check enforces non-null `t1_pstage_declaration`; i* validator-pass and SD/SR read-prerequisite checks fire only when `sd_sr_required: true` (v0.7.1). | After a T1 approval when the section is climbing toward T3 or its ceiling. |
| `/run-phase-3` | T3 Iterate & Converge — unbounded loop with convergence_metric two-round stability test; full four-agent loop + SAFEGUARD + Coupling E.2 overlay; pre-T4 admission gate. `[T3-STALE]` computed from `t3_last_activity_at` against wall-clock (Option A). | Most manuscript reviews; the default `default_final_tier: T3` dispatch. |
| `/run-phase-3-stability` | Ph3 stability sub-mode (v0.7.4, P-2) — reduced-envelope iteration admissible only when the manuscript is byte-stable (S-0 SHA-256 hash-match of the F1/F2/F3/F5 substrate) against the prior Ph3 close. Runs grounding audit + Check 8 deterministic pre-filter only; escalates to full `/run-phase-3` on any surfaced finding; section-scoped (no P-7 batching); cannot substitute for a full Ph3 pass as a Ph4 MCR admission precondition. | Byte-stable cycling on a section that has not moved since the prior Ph3 close — avoids the full seven-step pass when the signal substrate is unchanged. |
| `/run-phase-4` | T4 Finalize & Close — strict superset of T3 with external verifiers required and G.4 sign-off; gated by the Manuscript Convergence Report (MCR — renamed from LCR at v0.7.0); Reflector-full close-out with SK-16 Coupling D wiki ingest. | Final drafts for journal/conference/thesis committee; resubmissions; any review that must sign off before external handoff. |
| `/run-reflection` | Run post-round reflection and learning audit. | After review/edit rounds complete. |
| `/quick-deterministic` | Run fast mechanical pre-flight checks. | Quick health scan before deep review. |
| `/check-contradictions` | Run contradiction audit across co-invoked sources. | Theory consistency checks. |
| `/check-abstract-body` | Verify abstract promises are paid off in body. | Abstract/body alignment checks. |
| `/sentence-level-pass` | Run Bacon-style sentence craft pass. | Line-level prose tightening. |
| `/narrative-structure-pass` | Run Sexton-style narrative arc pass. | Structure and flow improvements. |
| `/IS-theory-pass` | Run Baird IS-theory criteria pass. | IS venue/theory manuscript checks. |
| `/p-stage-checker` | Verify manuscript matches declared P-stage. | Stage drift and anti-pattern checks. |
| `/response-letter-review` | Review rebuttal/response letter quality and traceability. | Revise-and-resubmit response drafting. |
| `/grounding-audit` | Run grounding protocol compliance audit. | Evidence and citation integrity checks. |
| `/accessibility-overlay` | Overlay SAFEGUARD Check 8's six reader-accessibility Sub-checks (A–F: Cadence, Rhythm, First-Use, Signpost, Jargon-Density, Worked-Example) onto a section's prose; emits MINOR / MAJOR / BLOCKER findings and an aggregate verdict the Planner consumes for the §3.3.3 TerminalSignoffRow accessibility gate. Dormant at T1, T2 severity-floored, full severity at T3/T4. | When the Evaluator runs Step 8.5, when a user asks to audit a section for reader accessibility, or when the Reflector Phase 2g recurrence audit replays Check 8 across rounds. |
| `/suchman-register-audit` | Audit Suchman register and asymmetric argument quality. | Suchman-style manuscript validation. |
| `/public-interest-accountability-pass` | Run an optional Eubanks-style policy-critical writing pass. | Inequality/public-service accountability sections. |
| `/advisor-escalation` | **Advisor MCP** — plugin bridge to the host’s **advisor** MCP (`consult_advisor`); external feedback with EXTERNAL reclassification and `reviews/advisor_consultation_*.md`. **EP-1** post-Ph2 pre-Ph3; **EP-2** post-Ph3_converged pre-MCR/Ph4 (`ADVISOR_MCP.md`). | Strategic or fresh-eyes questions; **scheduled** EP-1/EP-2 for submission defensibility; not for mechanical checks. |
| `/graph-grounding-overlay` | Overlay graphify findings onto manuscript citation set. | Wiki-linked graph-assisted reviews. |
| `/tool-contract-roundtrip` | Probe external verifier tool contracts before release. | Pre-release plugin validation. |
| `/backfill-source-stubs-from-references` | Generate wiki source-page stubs from a project's REFERENCES.md (Coupling A-revised). | Populating the external-source layer before concept-page grounding retrofits. |
| `/retrofit-concept-grounding` | Retrofit wiki concept pages with wikilinks to source pages (Coupling B). | Closing the grounding loop after source stubs exist. |
| `/promote-lessons-to-wiki` | Promote a project's lessons_learned entries into a wiki synthesis (Coupling C). | Round-close handoff of project lessons to cross-project memory. |
| `/ingest-m5-to-wiki` | Ingest an M5 submission-bound manuscript into the wiki as a full source page (Coupling D). | After G.4 sign-off, to close out a project with a first-class wiki record. |

## Manual script commands

Use these when you want deterministic, script-level execution outside slash-command flow.

| Script command | Purpose | Best use |
|---|---|---|
| `python scripts/sk20_preflight_gate.py --project-root "<project-root>" --date "YYYY-MM-DD"` | Run deterministic SK-20 readiness gate and emit readiness/no-op artifacts. | Before evaluator pre-flight or when diagnosing why SK-20 is skipping. |
| `python scripts/sk20_overlay_run.py --project-root "<project-root>" --wiki-linked true --coupling-e-on-review true --wiki-path "<wiki-root>" --manuscript-path "<manuscript>" --references-path "<references>" --classification-path "<advisor-or-classification>" --allow-missing-project-claude --allow-legacy-graph-confidence true` | Run readiness + overlay generation in one deterministic command. | Manual SK-20 execution in non-standard project layouts (e.g., absolute-path runs). |
| `python scripts/sk20_autonomous_loop.py --project-root "<project-root>" --wiki-path "<wiki-root>" --manuscript-path "<manuscript>" --references-path "<references>" --classification-path "<advisor-or-classification>" --allow-missing-project-claude --wiki-linked true --coupling-e-on-review true --allow-legacy-graph-confidence true --graphify-src-root "<graphify-root>"` | Run the full autonomous loop: bibliography ingest to wiki, graph rebuild, then SK-20 overlay. | End-to-end feed + rebuild + infer cycle from a single command. |
| `python scripts/coupling_health_report.py --project-root "<project-root>"` | Aggregate readiness/no-op history into Coupling E.2 health telemetry reports. | Round-close monitoring of gate stability and graph health trends. |
| `python scripts/check8_g_prefilter.py --project-root "<project-root>" --manuscript "<path-to-ms>" --cycle-id "<cycle_id>"` | Emit DETERMINISTIC_CHECKS.md §9d cumulative cognitive load pre-filter into `reviews/deterministic_<cycle_id>.md` (merges with existing stubs). | Ph3/Ph4 full-manuscript pass before `accessibility-overlay` Sub-check G, or when seeding the G work queue. |
| `python scripts/provenance_prewrite_check.py --project-root "<project-root>"` | Verify every `phase_deliverable_path` under `reviews/phase_state.json` resolves on disk. | Planner pre-write gate before a ledger row that cites section paths. |
| `bash scripts/release-gate.sh --build` | Run pre-release structural checks and build a package bundle. | Before version bumps and distribution packaging. |

## NEVER (common mistakes)

- **NEVER** use `/run-phase-3-stability` in place of **full** `/run-phase-3` when Ph4 or MCR rules require a complete Ph3 pass for admission — stability is a reduced envelope; “byte-stable” is not a shortcut past documented admission tests.
- **NEVER** open `/run-phase-4` for “one last polish” if MCR, G.4, or T4 preconditions in the project’s ladder docs are not satisfied — T4 adds external verifiers and close-out; skipping gates is a ladder break, not a time save.
- **NEVER** skip `/classify-manuscript` (or the project’s declared equivalent) and run tiered phase skills on a project that has no `reviews/classification.md` / declared tier — the Planner/Evaluator contract assumes declared P-stage and tier defaults.
- **NEVER** run `/retrofit-concept-grounding` (Coupling B) before `/backfill-source-stubs-from-references` (Coupling A) when source pages are still missing — B assumes the source layer from A exists.
- **NEVER** treat `/accessibility-overlay` as ignorable at T3/T4 when the workflow expects Check 8/terminal signoff — it is **dormant** at T1 and severity-floored at T2; at T3+ it feeds real gates; skipping it to “save time” leaves BLOCKER-class debt.
- **NEVER** add slash commands to the catalog that are not shipped in this package’s `skills/` tree — the registry is the authority; the host’s UI may lag or differ.
- **NEVER** use `/tool-contract-roundtrip` as a substitute for reading the project’s own `EXTERNAL_VERIFIERS` / policy docs — the skill probes contracts; it does not replace release governance in `CLAUDE.md` or the project wiki.
- **NEVER** treat `/run-generator-session` as a substitute for a full `/run-phase-2`+ Evaluator-joined pass when the ladder and project governance still require that round.

## Guardrails

- Do not invent commands that are not shipped in this plugin. The tables above match `skills/*/SKILL.md` names; if something is not listed, it is not part of this package.
- If a user’s **host** (e.g. Claude Code, Cursor) does not show a slash in the palette but the name is in the table, say so: the command is still a shipped skill; the user can type the slash command manually, update/install the package, or rely on the agent to load the skill from the repository. Do not fabricate a different command to replace a missing host entry.
- If a command is **unavailable** in the current session (e.g. skill not loaded, wrong workspace root), say so explicitly and give the exact canonical name for retry.
- Keep names **exact** (leading slash, kebab-case) so users can invoke them directly.
- **Pre-classification:** If the project has no `reviews/classification.md` (or project `CLAUDE.md` defers to one), point to `/classify-manuscript` first unless the user explicitly overrules for a one-off pass.
