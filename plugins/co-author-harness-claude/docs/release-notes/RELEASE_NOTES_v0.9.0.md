# Release Notes — co-author-harness-claude v0.9.0

**Release date:** 2026-04-26
**Theme:** **UI loadability** via the conventional `.claude-plugin/plugin.json` + `commands/` shim contract, paired with a **model allocation audit** that restores the `.plugin-efficiency.json` calibrator pin to `references/MODEL_ALLOCATION.md §2`.
**Verdict:** CLEARED (minor release; non-breaking surface addition + bookkeeping correction; no schema changes, no agent retirements, no ladder restructuring).

---

## One-paragraph summary

v0.9.0 closes two distinct drift hazards that the v0.8.x line had accumulated. First, the plugin advertised twenty-eight slash commands across `skills/plugin-commands/SKILL.md`, the root `CLAUDE.md` trigger table, and the manifest description, but shipped zero `commands/<name>.md` shim files — the conventional binding for `/<name>` slash commands when a Claude host loads a plugin via `.claude-plugin/plugin.json`. The package depended on host-side skill-name → slash-command resolution, which is host-dependent and produced inconsistent UI behavior. v0.9.0 lands twelve `commands/<name>.md` shim files for the headline-cut commands (the six phase-ladder rungs plus `/run-generator-session`, `/classify-manuscript`, `/plugin-commands`, `/run-reflection`, `/quick-deterministic`, `/check-contradictions`, and `/grounding-audit`); rewrites the manifest `description` to point at `/plugin-commands` rather than privilege any single slash; corrects the `CLAUDE.md` trigger table to flag itself as illustrative and to include the v0.8.7 headline `/run-generator-session`; and extends `scripts/catalog-check.py` with a prefix-tolerant parity rule that prevents future drift between the shim frontmatter `description` field and the `plugin-commands` SKILL catalog Purpose column. Second, an audit of `.plugin-efficiency.json` `role_overrides` against the binding `MODEL_ALLOCATION.md §2` allocation table revealed that fourteen of thirty-one classified artefacts were billed at the orchestrator (Opus 4.7) tier in the calibrator's cost projection while their actual runtime dispatch under §2 is Sonnet 4.6 (`agents/planner.md`, `agents/generator.md`, `skills/run-phase-1/SKILL.md`, `skills/run-reflection/SKILL.md`, `skills/classify-manuscript/SKILL.md`) or external/structured (`skills/advisor-escalation/SKILL.md`, `skills/tool-contract-roundtrip/SKILL.md`); a further artefact (`skills/run-generator-session/SKILL.md`, the v0.8.7 headline skill) was unclassified entirely. v0.9.0 restores the calibrator pin: seven artefacts move from `orchestrator` to `executor`, one is added, and `assumed_invocations_per_run` retunes from `{executor: 3, orchestrator: 4}` to `{executor: 5, orchestrator: 2}` to match the §2 dispatch counts. Because the Planner resolves runtime model dispatch from `MODEL_ALLOCATION.md §2`, not from `.plugin-efficiency.json`, this is a **bookkeeping correction**: no agent behavior changes, no review quality is at risk, and no behavioral-fidelity validation is required.

## Headline change — UI loadability via the `commands/` convention

```
  Before v0.9.0:                              After v0.9.0:
  .claude-plugin/plugin.json                  .claude-plugin/plugin.json
        │                                           │
        ▼                                           ▼
  (host-dependent)                            commands/<name>.md  (12 shims)
  skills/<name>/SKILL.md                            │
        │                                           ▼  delegates to
        ▼                                     skills/<name>/SKILL.md
  /<name> resolves only if                          │
  the host's palette matches                        ▼
  skill names to slash names                  binding instruction set
  (lossy, not portable)                       (single source of truth;
                                              unchanged from v0.8.7)
```

- The shims are **redirects, not duplicates**. Each `commands/<name>.md` body says "Read `${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md` and follow it as the binding instruction set" — the SKILL is the authority for trigger conditions, gates, finding format, and exit conditions. Future SKILL edits propagate without a parallel `commands/` edit.
- The shim frontmatter `description` field is a **prefix of** the matching `plugin-commands` SKILL catalog Purpose column. The new `scripts/catalog-check.py` rule asserts this on every release, normalizing markdown bold markers (`**`), inline code (`` ` ``), and Unicode smart quotes before the prefix comparison.
- The cut is the **headline-12** subset, not all twenty-eight. Sixteen long-tail commands (style passes, Coupling-A/B/C/D wiki ingest, response-letter and overlay routines, advisor escalation, `/tool-contract-roundtrip`) remain skill-resolved at this scope. They are invoked from inside Evaluator/Reflector orchestration far more often than from a user-typed slash, so the cost of host-dependent resolution is low. If any of them get UI-promoted later, the same shim pattern extends one file at a time.

## Headline change — model allocation pin restored to MODEL_ALLOCATION.md §2

The `.plugin-efficiency.json` `_comment` field claims the file's rates, models, and thresholds are "pinned against `references/MODEL_ALLOCATION.md §2`." That pin had drifted. The audit restored it.

### Findings table (per the conservative-max rule)


| Artefact | v0.8.7 | v0.9.0 | Per §2 max model dispatched | Verdict |
| -------- | ------ | ------ | --------------------------- | ------- |
| `agents/planner.md` | orchestrator | **executor** | Sonnet 4.6 (all 4 tiers, row 1) | DOWNSHIFTED |
| `agents/evaluator.md` | orchestrator | orchestrator | Opus 4.7 (T2/T3/T4 §3 floor) | KEEP |
| `agents/generator.md` | orchestrator | **executor** | Sonnet 4.6 (all 4 tiers, row 3) | DOWNSHIFTED |
| `agents/reflector.md` | orchestrator | orchestrator | Opus 4.7 (T4 close-out §3 floor) | KEEP |
| `skills/run-phase-1/SKILL.md` | orchestrator | **executor** | Sonnet (Planner + Generator; Evaluator dormant) | DOWNSHIFTED |
| `skills/run-phase-2/SKILL.md` | orchestrator | orchestrator | Opus (Evaluator joins) | KEEP |
| `skills/run-phase-3/SKILL.md` | orchestrator | orchestrator | Opus (full four-agent loop) | KEEP |
| `skills/run-phase-3-stability/SKILL.md` | orchestrator | orchestrator | Opus (Evaluator dispatches at reduced scope; §2 row 2 is unconditional at T2/T3/T4) | KEEP |
| `skills/run-phase-4/SKILL.md` | orchestrator | orchestrator | Opus + Reflector-full (two §3 floor slots) | KEEP |
| `skills/response-letter-review/SKILL.md` | orchestrator | orchestrator | Opus (Evaluator-class adversarial reading) | KEEP |
| `skills/run-reflection/SKILL.md` | orchestrator | **executor** | Haiku (Reflector-lightweight at T1/T2/T3) | DOWNSHIFTED |
| `skills/classify-manuscript/SKILL.md` | orchestrator | **executor** | Sonnet (Planner-class structured output) | DOWNSHIFTED |
| `skills/advisor-escalation/SKILL.md` | orchestrator | **executor** | Sonnet (harness-side bridge; external advisor cost metered separately) | DOWNSHIFTED |
| `skills/tool-contract-roundtrip/SKILL.md` | orchestrator | **executor** | Sonnet (structured contract probing) | DOWNSHIFTED |
| `skills/run-generator-session/SKILL.md` | **(unset)** | **executor** | Sonnet (Generator-class) | ADDED |


- **Net orchestrator pool: 14 → 7** (50% reduction in orchestrator-tier artefact count).
- **Net executor pool: 17 → 25** (47% increase).
- **`assumed_invocations_per_run`: `{executor: 3, orchestrator: 4}` → `{executor: 5, orchestrator: 2}`** to match the §2 dispatch counts (Planner + Generator + Reflector-lightweight + skills are mostly executor-class; Evaluator + occasional Reflector-full are the orchestrator-class invocations).

### Bookkeeping framing — why no behavioral validation is required

The handoff that scoped this audit named "behavioral fidelity risk: reclassifying Generator or Reflector-lightweight from Opus to Sonnet may degrade review quality." That risk does not hold. Two observations from the source files settle the question:

1. **The `role_overrides` field is consumed only by the external calibrator package (`plugin_calibrator/efficiency.py`, part of `unified-superkit`).** Repo-wide grep confirms zero in-repo readers of `role_overrides`. The field exists for cost-projection purposes only.
2. **Actual runtime dispatch is governed by `references/MODEL_ALLOCATION.md §2`**, resolved at dispatch time by the Planner. `agents/planner.md` line 48 ("**Authoritative for every dispatch**") and lines 325–336 describe the resolution: read §2, resolve the model string, pass it as the Agent tool's `model` parameter, write `model_dispatch:{agent}:={model}` to the round log.

The audit therefore changes **what the calibrator's cost projection reports**, not **what model the Planner dispatches**. Manuscript output, agent behavior, review quality, and the §3 capability-inversion floor (Hazard H-MA-1) are all unaffected.

## What changes at the file level

### New files

- `commands/run-phase-1.md` · `commands/run-phase-2.md` · `commands/run-phase-3.md` · `commands/run-phase-3-stability.md` · `commands/run-phase-4.md` · `commands/run-reflection.md` · `commands/quick-deterministic.md` · `commands/check-contradictions.md` · `commands/run-generator-session.md` · `commands/classify-manuscript.md` · `commands/plugin-commands.md` · `commands/grounding-audit.md` — twelve UI loadability shim files following the `commands/<name>.md` convention. Each shim has frontmatter `description` (a prefix of the matching `plugin-commands` SKILL catalog Purpose column) and a body that delegates to the matching `skills/<name>/SKILL.md` as the binding authority.
- `docs/release-notes/RELEASE_NOTES_v0.9.0.md` — this file.

### Edited files

- `.claude-plugin/plugin.json` — `version` 0.8.7 → 0.9.0; `description` rewritten to point at `/plugin-commands` for the full slash catalog rather than privilege a single slash by name.
- `.plugin-efficiency.json` — seven `role_overrides` entries downshifted from `orchestrator` to `executor` (F1, F3, F5, F11, F12, F13, F14 in the audit findings table); one entry added (F15 = `skills/run-generator-session/SKILL.md`); `assumed_invocations_per_run` retuned to `{executor: 5, orchestrator: 2}`.
- `CLAUDE.md` — root trigger table line 40 now flags itself as "illustrative — full catalog at `/plugin-commands`" and adds the missing `/run-generator-session` to the slash list. The eight original slashes remain.
- `scripts/catalog-check.py` — extended with three new functions (`parse_plugin_commands_purposes`, `discover_commands`, `check_commands_parity`) and a Unicode-quote normalization helper. The new check runs on every invocation: every `commands/<name>.md` frontmatter description must be a prefix of the matching `plugin-commands` SKILL catalog Purpose column, after stripping markdown bold markers, inline-code backticks, and curly quotes.

## Open items for next audit

These are deliberately captured as forward-looking notes per the v0.9.0 ship decision (Decision 4-α: bookkeeping correctness is its own justification; cost reduction is a downstream consequence, not the contract).

- **Empirical calibrator economics re-run.** The bash-environment calibrator at the time of release shipped pre-Phase-1.1 patches and was unsuited to a clean economics measurement against the v0.9.0 `role_overrides`. The projected cost-per-invocation drop (from $10.03 toward an estimated $5.50–$7.00) is order-of-magnitude only; an empirical re-run on the patched Windows-side `plugin_calibrator/efficiency.py` is recommended for the next maintenance window. If the empirical figure does not drop materially, two follow-up hypotheses are worth testing: (a) the `assumed_invocations_per_run` retune is too aggressive — Evaluator may dispatch more than twice in a typical Ph3 round; (b) the `assumed_output_tokens_per_invocation: 800` figure is a per-invocation constant, so reclassifying tokens from orchestrator to executor saves on input rates only, not on output rates, and the 5x/5x rate ratio masks an output-tier-locked floor.
- **F4 / F8 conservative keeps revisitable.** `agents/reflector.md` (F4) and `skills/run-phase-3-stability/SKILL.md` (F8) were kept at `orchestrator` under the conservative-max rule. F4 is debatable because the file is loaded for all four phase paths but only one (T4 close-out) actually engages Opus. F8 is debatable because Evaluator dispatches at Opus even at reduced scope, but the actual token volume processed by the orchestrator-tier model in the stability sub-mode is a fraction of a full Ph3 pass. A future audit could split the calibrator schema beyond binary `executor`/`orchestrator` to a tri-tier representation (matching MODEL_ALLOCATION.md §2's actual capability ordering `{Haiku 4.5} ≺ {Sonnet 4.6} ≺ {Opus 4.7}`) and bill these two files at a finer granularity.
- **Long-tail commands UI promotion.** The sixteen commands not in the headline-12 cut remain skill-resolved. If user-facing-frequency data accumulates and any of them merits UI promotion, the same shim pattern extends one file at a time. The `scripts/catalog-check.py` parity rule will assert frontmatter-description prefix consistency on each addition.

## Migration / back-compat

- **Absent-`commands/`-directory passes.** The `scripts/catalog-check.py` extension treats an absent or empty `commands/` directory as a `[WARN]` (UI loadability shims not present), not a `[BLOCKER]`. Pre-v0.9.0 forks and downstream tools that consume the harness without UI loadability remain compatible.
- **No `phase_state.json` schema or trigger-enum change.**
- **No `MODEL_ALLOCATION.md` edit.** The audit *restores* the calibrator pin to the existing §2 allocation table; it does not modify the binding contract.
- **No agent prompt change.** Agent files are untouched; the runtime dispatch resolved by the Planner is unaffected.

## Validation — at-release

- `python scripts/skill-check.py` — PASS (28 skills discovered, 0 blockers, 0 warnings).
- `python scripts/version-check.py` — PASS (manifest 0.9.0, README 0.9.0, CHANGELOG 0.9.0).
- `python scripts/catalog-check.py` — PASS (28 skills + 12 commands discovered, 0 blockers, 0 warnings).
- `python scripts/path-hygiene-check.py` — PASS (0 blockers).

## Authorship

Drafted under the v0.9.0 release session in cooperation with the harness's own audit and validation discipline; audit findings derived from `references/MODEL_ALLOCATION.md §2` (the binding allocation table at v0.7.3, carried forward unchanged through the Tier → Phase rename) and reconciled against `.plugin-efficiency.json` as it stood at v0.8.7.
