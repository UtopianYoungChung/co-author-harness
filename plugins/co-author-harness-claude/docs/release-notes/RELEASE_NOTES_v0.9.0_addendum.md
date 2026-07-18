# Release Notes — co-author-harness-claude v0.9.0 (Addendum)

**Addendum date:** 2026-04-26
**Closes:** Decision 4-α (deferred empirical economics re-run) from `RELEASE_NOTES_v0.9.0.md` "Open items for next audit"
**Theme:** Empirical confirmation of the v0.9.0 model-allocation pin and adjudication of the F4/F8 conservative-keep question.
**Verdict:** v0.9.0 audit prediction empirically confirmed. F4/F8 conservative-keep upheld under the current calibrator schema; the underlying schema-fidelity gap is real but is downstream of, not load-bearing on, Item #3 of the cost plan.
**Artifacts:** `artifacts/efficiency/20260426T183110Z/report.json` (full per-artefact breakdown), `artifacts/efficiency/latest.json` (alias).

---

## One-paragraph summary

The v0.9.0 release shipped on a paper-only model-allocation correction, with the empirical economics re-run deferred under Decision 4-α because the bash-environment calibrator at release time shipped a truncated `main()` (efficiency.py line 1081) and was unsuited to a clean run. This addendum closes that defer. The patched `audit_plugin()` / `write_report()` entry points were called directly against the harness root with the post-v0.9.0 `.plugin-efficiency.json` `role_overrides` and the retuned `assumed_invocations_per_run: {executor: 5, orchestrator: 2}`. Projected cost-per-invocation lands at **$5.87**, a 41.5% reduction from the v0.8.7 baseline of $10.03 and inside the v0.9.0 audit's predicted $5.50–$7.00 envelope. The orchestrator-tier cost share collapsed from $9.03 (90.0% of total) to $2.41 (41.0%), confirming that the seven downshifts mechanically rebalanced the cost basin. The dispatch multiplier dropped from 12.84× to 9.57×, but this is **almost entirely a denominator effect**: the raw `dispatch_reference_hits` count moved only from 379 to 377 (Δ = −2), while the artefact-count denominator widened from 32 to 44 because of the twelve `commands/*.md` UI loadability shims. Item #2's substantive headroom — ceremonial Reflector-lightweight calls at Ph1, per-step Evaluator dispatches that could be batched — is therefore intact, just hiding behind a smaller-looking multiplier. The F4 (Reflector) and F8 (Phase-3-stability) conservative-keeps each contribute non-trivially to the post-v0.9.0 cost — **F4 ≈ $0.723 (12.3% of invocation cost)** and **F8 ≈ $0.309 (5.3%)** — but the contribution is an artifact of the calibrator's "every orchestrator artefact is loaded into every orchestrator dispatch context" assumption. Phase-gated context loading (cost plan Item #3) removes the F4/F8 cost lever without requiring any tier reclassification, which makes the schema-fidelity argument for tri-tier representation a downstream concern rather than the load-bearing fix.

## Method

The shipped CLI (`python -m plugin_calibrator.efficiency …`) is broken in the present `unified-superkit` snapshot — `efficiency.py` ends at line 1081 with the `main()` function truncated mid-statement (`return 2 / r…`). The functional substrate (`audit_plugin`, `audit_economics`, `write_report` at lines 951, 325, 1003 respectively) is intact and was invoked directly:

```python
from plugin_calibrator.efficiency import audit_plugin, write_report
report = audit_plugin(plugin_root)        # reads .plugin-efficiency.json
write_report(plugin_root, report)         # persists artifacts/efficiency/<timestamp>/report.json
```

The configuration consumed: `.plugin-efficiency.json` as committed at v0.9.0 (rates pinned to `MODEL_ALLOCATION.md §2`; seven `role_overrides` downshifts applied; `assumed_invocations_per_run: {executor: 5, orchestrator: 2}`; `extra_clarity_section_tags` declared; `assumed_output_tokens_per_invocation: 800`).

A reconciliation pass against the formula in `audit_economics()` lines 364–375 confirmed the report values are correctly driven by the configured invocation counts and rates — i.e., the calibrator did read and apply `assumed_invocations_per_run` as committed, despite the report not embedding the consumed config block.

## Findings

### Headline economics, v0.8.7 → v0.9.0


| Metric | v0.8.7 baseline | v0.9.0 post-audit | Δ |
| --- | --- | --- | --- |
| `projected_cost_per_invocation_usd` | $10.0326 | **$5.8686** | **−41.5%** |
| `per_tier_cost_usd.orchestrator` | $9.0340 (90.0%) | $2.4070 (41.0%) | −73.4% |
| `per_tier_cost_usd.executor` | $0.9986 (10.0%) | $3.4616 (59.0%) | +246.6% |
| `per_tier_token_totals.orchestrator.tokens` | 94,567 | 52,232 | −44.8% |
| `per_tier_token_totals.executor.tokens` | 38,954 | 82,773 | +112.5% |
| `per_tier_token_totals.orchestrator.count` | 14 | 7 | −7 |
| `per_tier_token_totals.executor.count` | 18 | 37 | +19 |
| `subagent_dispatch_multiplier` | 12.844 | **9.568** | −25.5% |
| `prompt_tokens_estimate` | (≈133,521) | 135,005 | +1.1% |
| `artefact_count` | 32 | 44 | +12 |


The +12 artefact delta corresponds to the twelve `commands/*.md` UI loadability shims landed in v0.9.0. The dispatch-multiplier drop is a **denominator effect**, not a substantive reduction in dispatch ceremony: per `audit_economics()` (multiplier formula `1 + dispatch_hits / artefact_count`), `dispatch_reference_hits` moved 379 → 377 (Δ = −2) while the denominator widened 32 → 44. Item #2's actual lever — restructuring the Planner's sub-call dispatch logic — has not been touched and the headroom is intact.

### F4/F8 contribution analysis

Of the seven artefacts that remain `orchestrator` in v0.9.0 (`agents/evaluator.md`, `agents/reflector.md`, `skills/run-phase-{2,3,3-stability,4}/SKILL.md`, `skills/response-letter-review/SKILL.md`), **F4 (`agents/reflector.md`) alone accounts for 38.5% of the residual orchestrator-tier token mass** at 20,108 tokens. F8 (`skills/run-phase-3-stability/SKILL.md`) accounts for a further 12.1% at 6,305 tokens. Translating to invocation cost via the calibrator's formula — input cost prorated by tokens, output cost prorated by artefact count (`audit_economics()` lines 364–375; output is `output_tokens × invocations × count`, billed once per artefact regardless of body size):


| Artefact | Tokens | Input $ (prorated by tokens) | Output $ (prorated by count) | Total $/invocation | Share of total cost |
| --- | --- | --- | --- | --- | --- |
| F4 — `agents/reflector.md` | 20,108 | $0.6032 | $0.1200 | **$0.7232** | **12.3%** |
| F8 — `skills/run-phase-3-stability/SKILL.md` | 6,305 | $0.1891 | $0.1200 | **$0.3091** | **5.3%** |


For reference, the full per-orchestrator-artefact decomposition at full precision:


| Artefact | Tokens | Total $/invocation | Share |
| --- | --- | --- | --- |
| `agents/reflector.md` | 20,108 | $0.7232 | 12.3% |
| `agents/evaluator.md` | 7,442 | $0.3433 | 5.8% |
| `skills/run-phase-3-stability/SKILL.md` | 6,305 | $0.3091 | 5.3% |
| `skills/run-phase-3/SKILL.md` | 5,459 | $0.2838 | 4.8% |
| `skills/run-phase-4/SKILL.md` | 4,952 | $0.2686 | 4.6% |
| `skills/response-letter-review/SKILL.md` | 4,282 | $0.2485 | 4.2% |
| `skills/run-phase-2/SKILL.md` | 3,684 | $0.2305 | 3.9% |
| **Sum** | **52,232** | **$2.4070** | **41.0%** |



### Why F4 and F8 still keep `orchestrator` — and why this is the right call

The v0.9.0 release notes flagged both files as conservative-keeps under the binary `executor`/`orchestrator` schema constraint. The empirical numbers do not change that verdict; they refine the trade-off:

1. **F4 is loaded for all four phase paths but only engages Opus at T4 close-out.** A flat downshift to `executor` would mis-bill the T4 close-out (genuinely Opus per `MODEL_ALLOCATION.md §3` row 4), while keeping `orchestrator` over-bills the T1/T2/T3 paths where the file is loaded but the Reflector-lightweight runs at Haiku per the H-MA-2 30-day pilot. The truth requires a tri-tier `{Haiku, Sonnet, Opus}` schema — not representable in the present `.plugin-efficiency.json` shape.

2. **F8 is structurally analogous.** Per `MODEL_ALLOCATION.md §2` row 2, the Evaluator dispatches at Opus even at reduced scope in the stability sub-mode, but the actual token volume processed by the orchestrator-tier model is a fraction of a full Phase-3 pass. Same schema-fidelity gap, smaller cost lever.

3. **Phase-gated context loading (Item #3) supersedes the schema question.** The $0.7232 and $0.3091 figures rest entirely on the calibrator's assumption that every orchestrator artefact is loaded into every orchestrator dispatch context. If the orchestrator lazy-loads only the agent file actually being dispatched (the load-bearing change in Item #3), F4's marginal cost collapses to whatever fraction of dispatches actually reach T4 close-out — i.e., the schema gap stops mattering. The right sequencing is therefore: solve Item #3 first; the F4/F8 schema question becomes either moot (fix #3 absorbs the lever) or a clean follow-up (residual lever post-#3 is small enough that tri-tier schema change is justifiable on bookkeeping accuracy alone).

**Verdict:** F4/F8 conservative-keep upheld. No `role_overrides` edit. The tri-tier schema extension is a deferred follow-up; phase-gated context loading is the substantive next move.

## Refreshed picture of cost plan Items #2–#5

The v0.8.7 cost plan ranked items by projected return against a $10.03 cost basin. The v0.9.0 reclassification has not just lowered the basin to $5.87 — it has redistributed where the remaining headroom sits.


| Item | Original framing (v0.8.7) | Refreshed framing (post-v0.9.0) |
| --- | --- | --- |
| #1 — Model allocation | $10.03 baseline; 4 orchestrator agents | **CLOSED.** $5.87 actual; orchestrator share of cost dropped from 90.0% to 41.0%. |
| #2 — Dispatch multiplier (12.84× → ≤8×) | Multiplicative return on full $10.03 basin | **NOT YET CAPTURED.** The reported drop (12.84 → 9.57) is a denominator effect from the v0.9.0 shims (raw `dispatch_reference_hits` moved only 379 → 377). The substantive lever — Planner-side dispatch logic audit, ceremonial Reflector-lightweight calls at Ph1, per-step Evaluator batching — is untouched. Headroom intact, on a now-smaller $5.87 basin. |
| #3 — Phase-gated context loading | "~35k tokens saved per non-reflector dispatch" | **PROMOTED.** Now the highest single-step lever: it absorbs the F4/F8 schema question, materially reduces F4's effective contribution (which is the largest single artefact at 20,108 tokens contributing $0.72/invocation under the load-everything assumption), and removes the calibrator's "load-everything" assumption that is currently inflating projected cost relative to actual runtime. |
| #4 — Agent prompt compression | "~5–8k tokens via GP extraction; Reflector trim" | **DEFER until #3 lands.** Compression of F4 changes only how much is loaded when F4 *is* loaded; #3 changes whether F4 is loaded at all on most dispatches. Order-of-operation: do #3 first, re-measure, then revisit. |
| #5 — Prompt caching | "Static prefix discount" | **REVISIT after #2/#3.** Caching only realizes savings if the static prefix is stable. #3 reshapes what is in the prefix; it is premature to engineer for cache stability before #3 has settled the prefix. |


## Implications for the next maintenance window

The substantive next axis is **Item #3 (phase-gated context loading)**. The work shape:

1. Determine empirically whether the orchestrator (i.e., the dispatch logic in `agents/planner.md`) loads all four agent files into every Agent-tool call context, or whether the Claude Agent SDK already lazy-loads agent files by `subagent_type`. If the latter is already true at the SDK level, Item #3 is partially or fully absorbed by the platform and the calibrator's assumption is the false friend, not the runtime.
2. If lazy-loading is not present, the modification is local to `agents/planner.md` — pass only the dispatched agent's file into the round context, log the dispatched-agent set per round in `phase_state.json`, and update the calibrator schema to optionally consume per-dispatch token sets rather than the cartesian-product assumption.
3. Re-measure. The expected post-#3 cost-per-invocation falls below $5.00; F4's effective cost share drops by ~75% (T4 close-out frequency); the F4/F8 schema-fidelity question loses urgency.

Item #2 (dispatch multiplier) is parallelizable to Item #3 — they touch different parts of the Planner's dispatch logic — but Item #3 yields more on the now-smaller basin and resolves the F4/F8 question as a side-effect.

## Validation

- `python3 audit_plugin(...)` — exit 0; report written to `artifacts/efficiency/20260426T183110Z/report.json`.
- Cost reconciliation: `audit_economics()` formula at lines 364–375 verified against report numbers at full precision (executor cost = $3.461595 = `(82773×5/1e6 × 3.0) + (800×5×37/1e6 × 15.0)` ✓; orchestrator cost = $2.40696 = `(52232×2/1e6 × 15.0) + (800×2×7/1e6 × 75.0)` ✓).
- v0.9.0 prediction envelope: $5.50–$7.00 — empirical $5.87 lands at the midpoint. Audit methodology vindicated; no follow-up correction needed to `MODEL_ALLOCATION.md §2`.

## Authorship and provenance

Drafted under the v0.9.0 release session as a closing addendum. The empirical run was executed against `B:\Agents\co-author-harness` (mounted at `/sessions/zealous-practical-albattani/mnt/co-author-harness/`) using the patched-but-truncated `plugin_calibrator` in `unified-superkit/plugin_01Q7iXHRyKL2TPd9xCgb4j2p`; the truncation in `efficiency.py:main` is a separate `unified-superkit` defect and is documented inline above for the next maintainer of that package.
