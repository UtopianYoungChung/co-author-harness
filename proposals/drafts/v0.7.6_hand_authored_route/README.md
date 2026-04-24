---
document_type: hand_authored_route_cover
filed_for: v0.7.6_calibrator_audit_optimization_proposal.md (§3 Tier A + §4 Tier C P-C1)
filed_on: 2026-04-22
author_of_record: Joseph Chung (user-directed)
status: DRAFT-FOR-REVIEW — not yet applied to the canonical substrate
pairing: paired review recommended (user + one additional reader) before either artefact lands
---

# Hand-authored route — v0.7.6 proposal §3 + §4 P-C1

This folder is the **hand-authored option** to the fork the v0.7.6 proposal offered at §8: "draft the `.plugin-efficiency.json` content and the Evaluator-prompt pointer-demotion as a unified-diff artefact for review" (vs. dispatching the calibrator's `efficiency-auditor` subagent). The two artefacts below are drafts; neither has been applied to the canonical substrate.

## What's in this folder

| File | Target of application | Proposal clause | Sensitivity | Expected effect |
|---|---|---|---|---|
| `plugin-efficiency.json.draft` | Copy to `research-writing-harness/.plugin-efficiency.json` | §3 Tier A | LOW | Clears MINOR `efficiency_config_missing`; flips `assumed_rates_verified` from `false` to `true`; makes the `projected_cost_per_invocation_usd` figure quotable externally; pins model tiers per §12.9 MODEL_ALLOCATION.md |
| `evaluator.md.pointer-demotion.diff` | Apply to `research-writing-harness/agents/evaluator.md` | §4 Tier C P-C1 | MEDIUM | Reduces the Evaluator prompt from ~7,551 tokens (economics-audit observation) to ~4,100–4,300 tokens; saves ~3,200–3,400 tokens per Opus-4.7 Evaluator invocation at Ph2/Ph3/Ph4 × the invocation count per round |

## Why two artefacts, not one

§3 Tier A and §4 Tier C P-C1 are independent changes with different sensitivity profiles:

**Tier A (the config)** is a pure self-declaration of rates and thresholds the calibrator reads. No agent behaviour changes; no prompt surface changes. It can ship on its own schedule and is the highest-leverage single change because it unblocks quotable cost figures without touching any agent contract.

**Tier C P-C1 (the pointer demotion)** is a prompt-surface edit that changes what the Evaluator reads on every invocation. It is reversible (one `git revert` away), but the reversibility does not absolve paired review — a demotion that erodes a binding rule under the table will only surface as a missed finding on a later round, and that round will cost an Opus-4.7 Evaluator pass to diagnose.

Applying the config first, then observing one full Ph2/Ph3 round under the new config before applying the diff, is the recommended sequence. It isolates the signal from each change.

## Line-by-line review guidance

### `plugin-efficiency.json.draft`

**Rates (`model_tiers`).** Executor is `claude-sonnet-4-6` at $3/Mtok input, $15/Mtok output. Orchestrator is `claude-opus-4-7` at $15/Mtok input, $75/Mtok output. These are pinned against `references/MODEL_ALLOCATION.md §2` and the portfolio-root `CLAUDE.md §12.9` model assignments. The calibrator's binary executor/orchestrator tier split cannot represent Haiku 4.5 at Reflector-lightweight (H-MA-2 pilot); that fourth slot is a known modelling gap and is documented in the `_comment` field of the JSON object.

**Thresholds.**
  - `max_cyclomatic_complexity: 20` — catches the `sk20_overlay_run.py` CC=48 hotspot (Tier D) while not tripping on migration-script clusters that will age out at v0.7.5 RC. Default 15 would flag five modules; 20 flags only the production-path outlier.
  - `min_prompt_clarity_score: 0.5` — UNCHANGED from the calibrator default. The writing harness's 0.229 score is a known vocabulary mismatch, not real illegibility; proposal §5 P-C1 deliberately declines to tune the threshold downward because doing so would hide the underlying Path A / Path B question. Leaving at 0.5 keeps the honest signal until the heading-lexicon reconciliation lands.
  - `min_parallelisable_fraction: 0.25` — UNCHANGED from default. The observed 0.304 currently clears; the number will not move without P-E2 (batch-dispatchable tag).
  - `max_chain_depth: 15` — RAISED from default 6. The writing harness's four-phase ladder with four-agent dispatch at every rung has a structural floor around 12–14 hops; 15 is the v0.7.5 RC target after the `run-tier-*` alias removal. Leaving at 6 would emit a permanent MINOR no architectural change can clear.
  - `max_duplication_score: 0.5` — RAISED from default 0.25. The Grounding-Protocol quotation appearing in all four agent prompts is not sprawl; it is load-bearing shared contract text. Observed duplication is 0.014; the raise is to signal intent rather than to paper over a finding.

**Role overrides.** Explicit for the four agents (all orchestrator), the three Ph3/Ph4 runners + stability + response-letter-review + run-reflection + classify-manuscript (all orchestrator), and eleven executor-tier skills (the Evaluator's diagnostic-probe cluster and the three-pass craft stack). The explicit table overrides the calibrator's filename-regex heuristic and is the authoritative tier assignment.

**Throughput.** `input_tokens_per_second: 2000` — PLACEHOLDER. The audit observed that 500 tok/s is "three to five times below" actual Opus 4.7 input-processing throughput; 2000 is a defensible mid-range estimate pending a measured calibration. Run a measured throughput probe on a warm Opus 4.7 connection and adjust before quoting any wall-clock figure externally.

**Output assumptions.** `assumed_output_tokens_per_invocation: 800` — RAISED from default 400. Writing-harness agent invocations produce full review artefacts (consolidated findings reports, convergence-log entries, reflection reports) that routinely exceed 400 output tokens; 800 is a closer estimate to observed round output.

**Round multiplier.** `assumed_invocations_per_run: {executor: 3, orchestrator: 4}` — RAISED from default {1, 1}. A standard Ph3 round dispatches Planner + Evaluator + Generator + Reflector (four orchestrator invocations) and the Evaluator's diagnostic-probe cluster (three executor invocations). Note this is the round multiplier, NOT the subagent dispatch multiplier (which is 10.0 in the economics-audit JSON and is an annotation, not a cost inflator).

### `evaluator.md.pointer-demotion.diff`

**What is demoted.** Two sections:
  1. "Tier-conditioned engagement" (lines ~157–196) — four sub-sections narrating T1/T2/T3/T4 behaviour that is canonically specified in `references/TIER_PROTOCOL.md §5` and `references/AGENT_CONTRACTS.md §2`. Replaced with a five-column pointer table + four binding call-outs below (T1 rationale, T2 SD/SR rule, T3 terminal-signoff discipline, T4 grounding-demotion discipline).
  2. "Gate set (v0.7.0)" table (lines ~198–210) — already acknowledged at line 210 as a cross-reference index, not a spec. Replaced with a one-line pointer to `references/TIER_PROTOCOL.md §4`.

**What is NOT demoted.**
  - The "Procedure" section (lines ~87–156). On re-read the delegation to REVIEW_ORCHESTRATION.md is clean; the per-step bullets ARE the one-line preconditions the proposal named. Trimming further would erode usable runbook.
  - "Evaluator-specific rules" (lines ~212–225). Unique and compressed; not flagged by the audit.
  - The "v0.7.0 vocabulary" section (lines ~23–36). Documentary; belongs in the prompt because it guards against legacy ledger entries the Evaluator may encounter on projects still migrating.
  - The header-declared v0.7.0 surface vocabulary (T1/T2/T3/T4/`tier_state.json`/`t3_last_activity_at`) is PRESERVED. The Tier → Phase rewrite per CLAUDE.md §12.8 is orthogonal and should land in a separate pass to keep the revert path clean.

**Binding-rule preservation check.** Before applying, verify that every binding rule in the deleted narrative appears either in the table or in one of the four "binding" call-outs:
  - T1-dormant behaviour → table row 1 + T1 rationale call-out
  - T2 scope budget → table row 2
  - T2 SD/SR read-prerequisite → table row 2 + T2 SD/SR call-out
  - T2 convergence-metric MINOR → table row 2 (implicit — check during the first post-demotion round)
  - T3 scope budget → table row 3
  - `[T3-STALE]` advisory (EG-6) → table row 3
  - TerminalSignoffRow groundwork → table row 3 + T3 discipline call-out
  - ReengagementSignoffRow groundwork → table row 3 (condensed; verify sufficient)
  - Convergence-metric two-iteration rule → T3 discipline call-out
  - T4 scope + Coupling E.2 mandatory → table row 4
  - G.4 certification block fields → table row 4
  - EG-1 grounding demotion → table row 4 + T4 discipline call-out
  - EG-7 MCR re-admission → table row 4
  - Reflector-full handoff after G.4 PASS → DROPPED (this is the Planner's responsibility, not the Evaluator's; the demotion is appropriate)

If any binding rule above cannot be located in the post-demotion prompt, the pointer table has under-shot and must be widened before the patch lands.

## Post-apply verification

The unified-diff artefact's trailing "Post-apply verification checklist" names four mechanical checks (`grep` header-count; re-run `audit-package-economics` on the harness root; `reviews/safeguard_layer_results.md` Check 1 Regression Guard on the first post-demotion round; paired-review binding-rule preservation). Run all four before any v0.7.5-RC or v0.7.6 release-gate.

## Honesty notes

**Throughput placeholder.** The 2000 tok/s figure in the JSON is not measured — it is a defensible mid-range estimate. Quoting any wall-clock figure externally from this config before a measured calibration lands would be an honesty violation. The `_comment` field of the JSON is explicit about this.

**v0.7.0 vocabulary preservation.** The diff targets the v0.7.0-labeled evaluator.md that ships in v0.7.4.1. If the Tier → Phase rewrite (CLAUDE.md §12.8, scheduled for v0.7.5 RC) lands before this patch is applied, the line numbers in the diff may drift and the patch may need to be re-authored against the new surface.

**Haiku 4.5 representation gap.** The calibrator's binary tier split models only executor/orchestrator. Haiku 4.5 at Reflector-lightweight (H-MA-2 pilot, 30-day) cannot be distinguished from Sonnet 4.6 at the executor tier in this file. This is a calibrator limitation, not a plugin limitation; the Reflector's `model_dispatch_audit` block in `reviews/reflection_report.md` is the authoritative record of what the Reflector-lightweight slot actually ran on.

**Ship-on-iter-7 caveat carries forward.** The v0.7.4 economic-efficiency package's ~80% cost overrun observation is n=1 (CHANGELOG honesty note). INF3001H's first Ph3 round under v0.7.4 with this config pinned will serve as the independent replication. If the overrun does not reappear, the framing in both the CHANGELOG and this README steps down from "80% observed" to "80% observed on a single round."

---

*Last updated: 2026-04-22. Filed alongside `proposals/v0.7.6_calibrator_audit_optimization_proposal.md`.*
