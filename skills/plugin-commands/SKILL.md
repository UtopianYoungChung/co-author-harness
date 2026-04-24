---
name: plugin-commands
description: 'Show all slash commands in the co-author-harness plugin, each with purpose and invocation moment, plus the manual script commands (sk20 preflight/overlay/autonomous-loop, release-gate). Use when: "what commands are available", "list plugin skills", "slash command help", first-time orientation.'
trigger: when the user asks for slash-command help, command list, available skills, or how to invoke plugin commands
version: 1.0
---

# Plugin Commands

You are listing the slash commands available in this plugin.

## What to output

Return a concise command catalog with:
- command name
- one-line purpose
- best-use moment

## Command catalog

| Command | Purpose | Best use |
|---|---|---|
| `/plugin-commands` | List all plugin slash commands and usage moments. | First-time orientation or quick recall. |
| `/classify-manuscript` | Classify paper type, P-stage, venue, and default final tier (T1–T4 / T3R) of the v0.7.0 Lifecycle-Stage Ladder. | Before any review work starts. |
| `/run-phase-1` | T1 Plan & Draft — Planner bootstraps the 15-field section state; Generator drafts under the declared P-stage register. **When `sd_sr_required: true` in `reviews/classification.md`** (v0.7.1 opt-in; default `false`), the Planner additionally authors i* SD/SR models and runs the §3.1.1 structural-completeness validator. No Evaluator; no Self-T1 Verdict (retired at v0.7.0). | First rung for a new section or section whose ceiling is T1. |
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
| `/advisor-escalation` | Escalate strategic questions to advisor MCP with safeguards. | Complex planning/theory decisions. |
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
| `bash scripts/release-gate.sh --build` | Run pre-release structural checks and build a package bundle. | Before version bumps and distribution packaging. |

## Guardrails

- Do not invent commands that are not shipped in this plugin.
- If a command is unavailable, say so explicitly.
- Keep names exact so users can invoke them directly.
