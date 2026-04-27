---
name: extend-snowball-incremental
description: "Ph2 in-loop micro-iteration — extend the snowball pool against a single uncovered claim (or short claim list). Reads the claim text, the section's section-topic register, and the full existing references/REFERENCES.md as anchor for SCHOLAR_GATEWAY_BACKWARD / FORWARD probes. Runs the seed-and-saturate procedure with max_iterations=2 and per_seed_cap=5 (narrower than SK-NEW-A to prevent Ph2 token blow-out). Writes a delta to REFERENCES.md under the `snowball` table only (NOT core corpus) and one row to reviews/snowball_log.md. Auto-dispatched by run-phase-2 Step 0.5 (per uncovered claim from the BELOW_THRESHOLD audit) and by the Evaluator at Step 4 (per claim newly surfaced in the Generator's draft); manually invokable via /extend-snowball-incremental <claim>."
trigger: when run-phase-2 Step 0.5's claim-coverage audit returns BELOW_THRESHOLD (Planner auto-dispatches one invocation per uncovered claim), when the Evaluator's Ph2 Step 4 surfaces a new claim with no resolving source in the current pool, or when the user runs /extend-snowball-incremental <claim> manually
version: 1.0
---

# extend-snowball-incremental — Per-Claim Snowball Micro-Iteration at Ph2

**Grounding basis:** `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §§4.5 (incremental extension trigger at Ph2), 5.1 SK-NEW-C (skill specification), 5.2 Edit-2 (Ph2-side dispatch contract), 6.5 (S4 deliverable scope), 7 (R-3 grey-literature escalation, R-6 atomic-rename contract on REFERENCES.md)`; `docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md §5.5 (S4 stage specification)`; `references/GROUNDING_PROTOCOL.md §§Rule 4 (quote-before-attribute), Rule 6 (no gap-filling), Rule 7a (chain-of-verification for every admitted source)`; `references/EXTERNAL_VERIFIERS.md §§1.5 (wiki-first discovery ordering — SK-NEW-C is the named Ph2 operationaliser per architecture §5.6), 2 (Class 1 verifier registry), 3 (Planner clause for source-resolution discipline)`; `references/PHASE_PROTOCOL.md §3.2 (Ph2 charter; admission grammar)`; `references/phase_state_schema.md §5 (atomic-write convention for REFERENCES.md)`; `skills/seed-snowball-discovery/SKILL.md` (SK-33; this skill micro-iterates against the pool SK-33 produced); `skills/claim-coverage-audit/SKILL.md` (SK-34; the audit whose `## Uncovered` table this skill drains); `agents/planner.md §Phase 3.8` (canonical Ph2 dispatch contract; halt-vs-continue authoritative); `references/phase_notifications.yaml §4` (`W-COVERAGE-BELOW-THRESHOLD`, `E-COVERAGE-AUDIT-FAILED` codes that gate this skill's auto-dispatch).

---

## 1. What this stage does

`extend-snowball-incremental` runs a narrow, claim-anchored snowball micro-iteration against the existing reference pool. It is the Ph2-side *resolution-focused* counterpart to SK-NEW-A's Ph1-side *seed-and-saturate* run: where SK-NEW-A constructs the pool from the section's full claim register at Ph1 entry, SK-NEW-C extends the pool by one or a few rows, anchored on a *single uncovered claim* surfaced at Ph2.

The skill is invoked in three contexts (architecture §5.1 row 3, Trigger):

1. **Auto-dispatch from `run-phase-2` Step 0.5**, one invocation per uncovered claim in the audit's `## Uncovered` table when SK-NEW-B (`claim-coverage-audit`) returned a BELOW_THRESHOLD verdict. The Planner's Phase 3.8 (`agents/planner.md`) drives the dispatch; SK-NEW-C runs in parallel with the Ph2 Evaluator pass so the Evaluator's Step 4 may read the extended REFERENCES.md if SK-NEW-C lands sources before Step 4 reaches the affected claim.
2. **Auto-dispatch from the Evaluator at Step 4** when a claim in the Generator's Ph1 draft has no resolving source under Rule 7a and the audit did not surface it (e.g., a new claim introduced in a Ph2 revision round, or a claim the Ph1 audit lexical-match heuristic missed). The Evaluator emits `propose_extend_snowball` as the remediation hint; the Planner reads the hint and dispatches.
3. **Manual invocation** via `/extend-snowball-incremental <claim>` (single-claim form) or `/extend-snowball-incremental --section <section>` (drains the most recent audit's `## Uncovered` table for that section). Manual mode is the failsafe for cases where auto-dispatch is suppressed or the user wants an out-of-cycle extension.

The skill's output is a **delta** to `references/REFERENCES.md` — new rows added to the `snowball` table only — and a single row appended to `reviews/snowball_log.md` recording the micro-iteration's procedure trace. The skill does NOT modify the `core corpus` or `cited-via` tables in REFERENCES.md (those are managed by SK-NEW-A and by the Generator's drafting respectively); the Ph2 micro-iteration is by construction a snowball extension, never a core-corpus insertion.

The skill is **bounded by design**: `max_iterations = 2` and `per_seed_cap = 5`, both narrower than SK-NEW-A's defaults, prevent the per-claim micro-iteration from absorbing more token / API budget than the Ph2 round can afford. If two iterations admit zero papers resolving the claim, the skill writes a `[BLOCKER]` finding to the Evaluator's Ph2 findings file naming the claim and the failed search trace; the Generator must then downgrade the claim to Indirect tier (per `GROUNDING_PROTOCOL.md` Rule 4 explicit indirection) or remove it.

## 2. Preconditions

Before running, verify all of the following. On any failure that is not gracefully degradable, abort with a clear `extend-snowball-incremental: no-op (<reason>)` message and write the no-op JSON described below; do not proceed to iteration.

1. **Target claim is resolvable.** Either (a) the user supplied `<claim>` as a quoted string or as a `claim_id` referencing the most recent `claim_coverage_*.md` audit's `## Uncovered` table, OR (b) the Planner's Phase 3.8 auto-dispatch supplied a `claim_id` from the audit, OR (c) the Evaluator's Step 4 dispatch supplied a claim text + locus tuple. On ambiguity (multiple matches in the audit), no-op with `CLAIM_AMBIGUOUS` and surface the candidate `claim_id` list.

2. **Anchor pool is non-empty.** `references/REFERENCES.md` must exist with at least one row. The pool is the seed substrate for backward / forward snowball — SK-NEW-C cannot anchor a micro-iteration on an empty pool. No-op with `EMPTY_REFERENCES_POOL` and surface the suggested-fix `Run /seed-snowball-discovery first to populate the pool, then re-run`.

3. **`reviews/classification.md` parses.** Reads `paper_type` and `p_stage` to scope the admission criterion (P0 admits exploratory matches; P2 demands precise matches). Reads `per_seed_cap_extend_snowball` (default 5) and `max_iterations_extend_snowball` (default 2) if present; uses defaults otherwise. Reads `auto_redlink_snowball: bool` (S4.5 field; ignored at S4 — the red-link auto-trigger lands at S4.5 per architecture §5.5.4) and `red_link_cap_per_round` (S4.5 field; ignored at S4). On parse failure, no-op with `CLASSIFICATION_MISSING`.

4. **At least one Class 1 verifier handle is reachable.** Probe `mcp__70599628-...__semanticSearch` (Scholar Gateway), `mcp__zotero__*` (Zotero+Scite), or `mcp__7e98b9aa-...__answer` (Consensus, when registered). The micro-iteration cannot run without at least one external verifier handle; SK-NEW-C is by construction a Rule 7a logging exercise and the verifier provides the row content. No-op with `NO_REACHABLE_VERIFIER` and surface the suggested-fix `Verify the Scholar Gateway / Zotero / Consensus MCP is connected at the workspace; see EXTERNAL_VERIFIERS.md §2`.

5. **Idempotency.** Read `reviews/snowball_log.md`. If a prior `extend-snowball-incremental` row exists for the same `claim_id` AND the section's REFERENCES.md hash is unchanged from the prior row's `pool_hash_at_run`, no-op with `IDEMPOTENT_HIT` and surface the prior log row's pointer. The user can force a re-run with `/extend-snowball-incremental <claim> --force`. The idempotency hash anchor is REFERENCES.md (not the manuscript) because the micro-iteration's input space is the existing pool plus the claim text; the manuscript's surrounding prose is informational context, not search input.

### No-op reason codes

```json
{
  "skill": "extend-snowball-incremental",
  "status": "noop",
  "reason_code": "<code>",
  "message": "<human-readable>",
  "claim_id": "<canonical-id-or-null>",
  "section": "<heading_path_or_filename>",
  "timestamp": "YYYY-MM-DDTHH:MM:SSZ"
}
```

Codes: `CLAIM_AMBIGUOUS`, `EMPTY_REFERENCES_POOL`, `CLASSIFICATION_MISSING`, `NO_REACHABLE_VERIFIER`, `IDEMPOTENT_HIT`.

The no-op file is written to `reviews/extend_snowball_noop_<YYYY-MM-DD>_<claim_id>.json`. Downstream consumers (the Planner's Phase 3.8 outcome handler) read this file when no log-row update arrives within the round.

## 3. Procedure

### Phase 1 — Anchor selection

Read the target claim's text and locus. Read `references/REFERENCES.md` in full. Construct the **anchor seed set** as follows:

1. Select up to `per_seed_cap` papers from the existing pool whose title or annotation (column 3) lexically matches the claim's load-bearing nouns above the SK-NEW-B similarity threshold (default 0.6 cosine over normalised noun phrases; falls back to Jaccard 0.3 over normalised tokens when no embedding model is available). The match procedure mirrors SK-NEW-B's source-mapping logic verbatim — same tokeniser, same threshold, same canonical-citation-key sort — so SK-NEW-C's anchor selection is reproducible against SK-NEW-B's audit output.
2. If fewer than 2 papers match, broaden to claim-kind matching: select papers whose `claim_anchors` metadata (when present) references the claim's kind (existential / comparison / mechanism / result / theoretical commitment per SK-NEW-B §3 Phase 1). If still fewer than 2, accept the smaller set; the per-seed cap is an upper bound, not a floor.
3. The anchor set is the input to backward / forward snowball. If the anchor set is empty (no lexical match, no claim-kind match), advance directly to the **direct-claim probe** sub-phase (Phase 2.5 below) without an iteration loop.

The anchor selection logs to `snowball_log.md` as `anchor_seed_set: [<citation_key_1>, <citation_key_2>, ...]` for downstream audit traceability.

### Phase 2 — Snowball micro-iteration

Run the SK-NEW-A iteration body verbatim with two parameter overrides — `max_iterations = max_iterations_extend_snowball` (default 2) and `per_seed_cap = per_seed_cap_extend_snowball` (default 5) — and one admission-criterion override:

> **Narrowed admission criterion.** A candidate paper is admitted iff its title or abstract resolves *the target claim*, not the full section claim register. The narrowing is the load-bearing distinction from SK-NEW-A: SK-NEW-A admits per-section claim coverage; SK-NEW-C admits per-claim coverage. A paper that resolves a different uncovered claim in the same audit is not admitted by *this* invocation; the Planner's Phase 3.8 dispatches a separate SK-NEW-C invocation for that claim.

The iteration loop is:

```
SK-NEW-C MICRO-ITERATION:
  S = anchor_seed_set
  for iteration_index in 1 .. max_iterations:
    backward = SCHOLAR_GATEWAY_BACKWARD(S)        # bibliography-of-seeds
    forward  = SCHOLAR_GATEWAY_FORWARD(S)         # citing-papers-of-seeds
    candidates = (backward ∪ forward) \ S
    admits = filter_by_claim_resolution(candidates, target_claim)
    log(EXTEND_ITERATE, iteration_index,
        |candidates|, |admits|,
        rate = |admits| / max(1, |S|))
    if |admits| == 0 and iteration_index == max_iterations:
      goto Phase 2.5  (direct-claim probe fallback)
    if |admits| == 0:
      continue                # iteration zero-admits but not yet at max
    S = S ∪ admits
    write_admits_to_REFERENCES_snowball_table(admits)
    log_external_verification_rows(admits)
    break                     # one iteration with non-zero admits suffices
```

The early-break-on-first-non-zero-admits is intentional: SK-NEW-C is resolution-focused, not saturation-focused. One resolving source for the target claim is the goal; further saturation is SK-NEW-A's job at the next Ph1 entry, not Ph2's. (The `max_iterations = 2` budget is an upper bound that fires only when iteration 1 returns zero admits.)

### Phase 2.5 — Direct-claim probe (fallback)

When Phase 2's two iterations both return zero admits, OR the anchor seed set was empty, attempt one final **direct-claim probe** against `mcp__70599628-...__semanticSearch` (Scholar Gateway) with the claim text itself as the query and `inferred_intent: "find a Class 1-verifiable source that resolves this single claim for Ph2 admission"`. Admit any returned paper whose abstract resolves the claim under the SK-NEW-B admission criteria.

If the direct-claim probe admits at least one paper, write the admit to REFERENCES.md and proceed to Phase 3. If the direct-claim probe also returns zero resolving papers, the skill enters its **failure mode** (§4 below): writes the `[BLOCKER]` finding to the Evaluator's Ph2 findings file and exits with `status: failed`.

### Phase 3 — Atomic write to REFERENCES.md

Per architecture §7 R-6 mitigation, REFERENCES.md is written under the **single-writer atomic-rename convention** anchored at `references/phase_state_schema.md §5` (the same convention SK-NEW-A uses): write all new admit rows to `references/REFERENCES.md.tmp`, fsync, atomic-rename to `references/REFERENCES.md`. Concurrent SK-NEW-C invocations across different claims in the same Ph2 cycle serialise on a `references/REFERENCES.md.lock` advisory lockfile; cross-claim concurrency rarely arises in practice (the Planner's Phase 3.8 dispatches sequentially per uncovered claim) but the lock is the correctness guard.

The Evaluator reads only the canonical `references/REFERENCES.md` path during Ph2 Step 4; readers see either the pre-extension pool or the post-extension pool, never an inconsistent intermediate state. The atomic-rename is the load-bearing race mitigation between SK-NEW-C and the parallel Evaluator pass per architecture §5.2 Edit-2 paragraph 3.

### Phase 4 — Snowball-log row append

Append one row to `reviews/snowball_log.md` recording the micro-iteration. Row schema (mirrors SK-NEW-A's iteration-row schema with the additional `target_claim_id` field):

```yaml
- timestamp: "<ISO-8601 UTC>"
  skill: extend-snowball-incremental
  invocation: <auto_step_0_5 | auto_evaluator_step_4 | manual>
  section: "<heading_path_slug>"
  cycle_id: "<run-phase-2 cycle id>"
  target_claim_id: "<from claim_coverage_*.md audit OR null for direct-Evaluator-dispatch>"
  target_claim_text: "<load-bearing claim text, ≤200 chars>"
  anchor_seed_set: ["<citation_key_1>", ...]
  iterations_run: <1 or 2>
  total_candidates: <int>
  total_admits: <int>
  rate: <float, ≤3 decimal places>
  saturation_signal: <"first-iteration-success" | "second-iteration-success" | "max-met-then-direct-probe-success" | "max-met-then-direct-probe-fail" | "anchor-empty-then-direct-probe-success" | "anchor-empty-then-direct-probe-fail">
  pool_hash_at_run: "<sha256 of REFERENCES.md before this run>"
  pool_hash_after_run: "<sha256 of REFERENCES.md after admits, or unchanged hash if no admits>"
  wiki_access_mode: <"filesystem" | "mcp_fastpath" | "mcp_unreachable">
  external_verification_log_rows_appended: <int>
```

The `external_verification_log_rows_appended` field is the row count appended to `reviews/external_verification_log.md` by Phase 2 / 2.5; every admitted paper triggers exactly one Rule 7a row, so this field equals `total_admits` on success cases and `0` on failure / no-op cases.

## 4. Output artefacts

On **success** (Phase 2 or Phase 2.5 admitted at least one paper):

- `references/REFERENCES.md` — extended with one or more new rows under the `snowball` table. The `core corpus` and `cited-via` tables are unchanged.
- `reviews/snowball_log.md` — appended with one row per the schema above. `saturation_signal` records which sub-phase succeeded.
- `reviews/external_verification_log.md` — appended with one row per admitted paper, per the canonical Rule 7a row format (`EXTERNAL_VERIFIERS.md §5`).

On **failure** (both Phase 2 iterations returned zero admits AND Phase 2.5 direct-claim probe also returned zero resolving papers):

- `references/REFERENCES.md` — **unchanged** (no atomic-rename triggered; the temp file is deleted).
- `reviews/snowball_log.md` — appended with one row whose `saturation_signal: max-met-then-direct-probe-fail` records the exhausted search.
- `reviews/external_verification_log.md` — **unchanged** (no admits, no Rule 7a rows).
- `reviews/ph2_findings_<YYYY-MM-DD>_<cycle_id>.md` — appended with a `[BLOCKER]` finding naming the claim, the search trace, and the suggested resolutions:

  > `[BLOCKER]` claim does not resolve via Class 1 snowball. Target claim: `<claim_text>` at locus `<heading_path:line_range>`. SK-NEW-C searched `<anchor_seed_set>` over `<iterations_run>` iterations + direct-claim probe; zero papers admitted. **Suggested resolutions**: (i) downgrade the claim to Indirect tier per `GROUNDING_PROTOCOL.md` Rule 4 with explicit indirection (cite a source that *discusses* the claim's domain rather than *establishes* the claim itself); (ii) cite grey literature (technical report, preprint, white paper) and accept a Class 2 verification per `EXTERNAL_VERIFIERS.md §2`; (iii) remove the claim from the section if neither (i) nor (ii) is acceptable to the section's P-stage register. **The Generator must address this finding before the Ph2 round closes.**

The BLOCKER finding is the architecture §5.1 row 3 failure-mode contract verbatim. The Evaluator's existing BLOCKER-handling flow (`agents/evaluator.md` Phase 5.5 finding emission + `agents/generator.md` Phase 2 fix-against-BLOCKERs) absorbs the finding without any new contract; the BLOCKER text is the only new surface this skill introduces to the Ph2 findings stream.

## 5. Determinism contract

The skill MUST be deterministic across two consecutive invocations on unchanged inputs (same claim text, same REFERENCES.md hash, same classification.md). Sources of non-determinism to avoid:

- **Anchor seed-set selection.** Sort the existing pool by canonical citation key (alphabetical) before lexical matching; tied scores resolve by alphabetical citation key. Round similarity to three decimal places before threshold comparison.
- **Iteration order over backward / forward results.** Sort Scholar Gateway results by their canonical DOI (alphabetical) before the admission filter. Do not preserve API result order.
- **Tiebreaks among admits.** When more than one candidate paper resolves the same target claim, list all of them alphabetically by DOI in the snowball-log row's implicit ordering. Do not pick "best."
- **Timestamp leakage into other fields.** Only the snowball-log row's `timestamp` field varies between runs; the `pool_hash_after_run` and the admitted-row content in REFERENCES.md are byte-identical across two invocations on unchanged inputs.

The strategy §5.5 stage-close gate validates this implicitly through the auto-dispatch chain test: SK-NEW-B → SK-NEW-C is exercised end-to-end on a section with at least one ungrounded claim, and SK-NEW-C lands the resolving source within the round. Determinism is validated via the SK-NEW-B audit's reproducibility (which already includes SK-NEW-C-extended pools) plus the snowball-log diff across two consecutive runs of the same claim.

## 6. What this skill does NOT do

- **Not a saturation run.** SK-NEW-C is resolution-focused (one resolving source per target claim suffices); SK-NEW-A is saturation-focused (`rate < ε` stop rule). The two skills have different stop rules by construction.
- **Not a core-corpus extender.** New admits land in the `snowball` table only. The `core corpus` table is curated by SK-NEW-A at Ph1 and is not modified at Ph2; the user can promote a snowball admit to core corpus manually if a downstream judgment justifies the promotion.
- **Not an audit dispatcher.** SK-NEW-C does not re-run SK-NEW-B's coverage audit after admits — re-auditing is the Planner's responsibility on the next Ph2 entry (typically the next round after Generator fix). The current round's Evaluator reads the extended pool directly (per architecture §5.2 Edit-2 race semantics).
- **Not a synthesis-aware extender (yet).** S4.5 amends this skill's anchor-selection phase to consult `wiki/syntheses/*.md` before the Class 1 fallthrough (per architecture §5.5.3 / §5.5.4). At S4 the anchor selection is lexical / claim-kind only.
- **Not a wiki-graph-substrate extender.** The graph-substrate iteration variant (architecture §5.5.1) is implemented in SK-NEW-A only; SK-NEW-C's micro-iteration uses Class 1 verifiers directly, without the graph-local fast-path. Rationale: the per-claim micro-iteration's seed set is small (≤ 5 papers) and the graph-local cost saving is marginal at that scale; the implementation simplification is worth the modest external-API cost.
- **Not a substitute for the Evaluator's judgment.** A claim that SK-NEW-C admits a paper for is admitted under lexical / claim-kind resolution; the Evaluator's Step 4 still applies Rule 7a chain-of-verification before accepting the admission as a citation in the manuscript. SK-NEW-C produces the *candidate* source; the Evaluator adjudicates *whether the candidate resolves the claim under domain judgment*.

## 7. Auto-dispatch and manual-invocation status (v0.10.0-S4)

At v0.10.0-S4 this skill is invoked in three contexts (per §1):

- **Auto from `run-phase-2` Step 0.5** when SK-NEW-B's audit returned BELOW_THRESHOLD. The Planner's Phase 3.8 (`agents/planner.md`) dispatches one SK-NEW-C invocation per uncovered claim listed in `claim_coverage_<date>_<cycle_id>.md`'s `## Uncovered` table. Dispatches run in parallel with the Ph2 Evaluator pass.
- **Auto from the Evaluator at Step 4** when the Evaluator surfaces a claim with no resolving source in the current pool. The Evaluator emits `propose_extend_snowball` as the remediation hint; the Planner reads the hint and dispatches.
- **Manual** via `/extend-snowball-incremental <claim>` (single claim) or `/extend-snowball-incremental --section <section>` (drains the most recent audit's `## Uncovered` table for that section). The `--force` flag bypasses the §2 clause-5 idempotency hit.

At v0.10.0-S4.5 this skill's anchor-selection phase is amended with the synthesis-alignment fast-path (architecture §5.5.3): before the Class 1 fallthrough, the skill consults `wiki/syntheses/*.md` for claim-kind matches and admits via `[via-synthesis: <synthesis_key>]` annotation when the alignment crosses the §5.5.3 threshold. Additionally, SK-16's red-link auto-trigger (architecture §5.5.4) becomes a fourth invocation context, gated on `auto_redlink_snowball: true` in `classification.md` and capped by `red_link_cap_per_round`. At S4 these extensions are out of scope; the procedure stops at the lexical / claim-kind anchor selection and Class 1 verification described in §3 above.

---

*Normative status.* This skill is the named operationaliser of the Ph2 incremental-extension trigger defined in architecture §4.5 and the named Ph2 executor of the wiki-first ladder per `EXTERNAL_VERIFIERS.md §1.5` (S5 documentation amendment). It is bound to `references/GROUNDING_PROTOCOL.md` Rule 6 (no gap-filling — when SK-NEW-C cannot find a resolving source, the failure surfaces as a BLOCKER, not as a fabricated `[INFERRED]` annotation) and to Rule 7a (every admit triggers an `external_verification_log.md` row). The skill is registered as **SK-35** in `references/SKILL_REGISTRY.md`. The S4.5 synthesis fast-path / red-link auto-trigger and the S5 documentation amendments are out of scope for this S4 ship.
