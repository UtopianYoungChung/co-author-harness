---
name: claim-coverage-audit
description: "Ph1 → Ph2 admission audit. Reads manuscript/{section}.md and references/REFERENCES.md, extracts the section's claims, maps each claim to resolving sources in the pool, emits a three-set coverage map (covered / partially-covered / uncovered) plus a coverage score at reviews/claim_coverage_{date}_{cycle_id}.md. Manually invokable via /claim-coverage-audit; auto-invoked by run-phase-2 Step 0.5. Deterministic — same inputs produce byte-identical findings modulo timestamp."
trigger: when the user runs /claim-coverage-audit on a section, when the user wants a coverage check on a Ph1-completed draft before Ph2 dispatch, or (from S4 onward) when run-phase-2 Step 0.5 dispatches the audit before Evaluator Step 0a
version: 1.0
---

# claim-coverage-audit — Per-Claim Source Mapping for Ph1 → Ph2 Admission

**Bibliography boundary.** Apply `references/CITATION_DISCIPLINE.md` §6. This score and source-resolution map are discovery/coverage aids, not scholarly bibliography clearance. Synthesis similarity, metadata resolution or a passing threshold cannot clear unassessed references or citation uses; full role/currency/directness judgments require inspected evidence and final-version coverage.

**Grounding basis:** `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §§4.1 (claim definition), 4.4 (per-claim coverage map), 5.1 SK-NEW-B (skill specification), 5.5.3 (synthesis-alignment fast-path; v0.10.0-S4.5 R1), 6.4 (S3 deliverable scope), 6.6 (S4.5 deliverable scope)`; `docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md §§5.4 (S3 stage specification), 5.6 (S4.5 stage specification)`; `references/GROUNDING_PROTOCOL.md §§Rule 4 (quote-before-attribute), Rule 6 (no gap-filling)`; `references/EXTERNAL_VERIFIERS.md §3 (Planner clause for source-resolution discipline)`; `references/PHASE_PROTOCOL.md §3.2 (Ph2 admission preconditions)`; `skills/seed-snowball-discovery/SKILL.md` (SK-33; this skill audits the pool SK-NEW-A produces).

---

## 1. What this stage does

`claim-coverage-audit` reads a Ph1-completed section, the project's reference pool, and (from v0.10.0-S4.5 R1 onward) the project's wiki synthesis layer, and tells the user, claim by claim, whether each claim has a resolving source. The output is a **coverage map** — four named sets of claims (covered, synthesis-covered, partially-covered, uncovered) — and a **coverage score** (`(covered + synthesis-covered) / total`). The synthesis-covered set is populated by the synthesis-alignment fast-path (§3 Phase 2.5; introduced v0.10.0-S4.5 R1 per architecture §5.5.3) when the project's `wiki/syntheses/` layer contains a synthesis brief that aligns with the section's claim above the configured threshold. The map is the artefact a downstream Ph2 dispatch consumes to decide whether Ph2 should proceed at all or whether the section needs more sources first.

At v0.10.0-S3 the skill is **manually-invokable only**. The user runs `/claim-coverage-audit <section>` after Ph1 drafting, reads the report, and decides whether to extend the snowball pool (manually re-running SK-33 or, from S4, dispatching SK-NEW-C `extend-snowball-incremental`). Auto-dispatch from `run-phase-2` Step 0.5 lands at v0.10.0-S4.

The audit is **deterministic**. Two consecutive runs against the same `manuscript/<section>.md`, `references/REFERENCES.md`, and `wiki/syntheses/` state produce byte-identical findings modulo the timestamp and cycle_id fields. Determinism is required for the strategy §5.4 stage-close gate ("score is reproducible across two consecutive runs") and for the Reflector Phase 2g recurrence audit (consumer logic landing at v0.10.0-S4.5 R2 per the cross-round regression-detection wiring), which compares coverage maps round-over-round to detect score regressions.

The skill does **not** modify the manuscript. It does not modify `references/REFERENCES.md`. It does not invoke Class 1 verifiers (no Scholar Gateway probes, no Consensus probes). It reads what is already on disk and produces a report. Source extension is the sibling skill SK-NEW-C's job, not this one's.

## 2. Preconditions

Before running, verify all of the following. On any failure that is not gracefully degradable, abort with a clear `claim-coverage-audit: no-op (<reason>)` message and write the no-op JSON described below; do not proceed to scoring.

1. **Target section is resolvable.** Either (a) the user supplied `<section>` as a heading path or filename, OR (b) the project carries a single in-flight section identifiable from `reviews/phase_state.json` (most recent `current_phase: "Ph1"` or `Ph1_approved` row). On ambiguity, no-op with `SECTION_AMBIGUOUS` and ask the user to specify.

2. **`manuscript/<section>.md` exists with non-empty body.** A section file with no prose has no claims to audit. No-op with `EMPTY_SECTION_BODY`.

3. **`references/REFERENCES.md` exists with at least one source row.** A reference pool with zero sources cannot resolve any claim. No-op with `EMPTY_REFERENCES_POOL` and surface the suggested-fix `Run /seed-snowball-discovery first to populate the pool`.

4. **`reviews/classification.md` exists and parses.** Reads the project parameter `claim_coverage_threshold` (default 0.8 if absent). Reads `paper_type` and `p_stage` to condition the claim-extraction strictness (P0 admits exploratory claims; P2 demands precise claims). On parse failure, no-op with `CLASSIFICATION_MISSING`.

5. **Idempotency.** Read `reviews/phase_state.json`. If a prior `claim_coverage_*.md` exists for the same section AND the section's manuscript file hash is unchanged AND the REFERENCES.md hash is unchanged AND (from v0.10.0-S4.5 R1) the `wiki/syntheses/` content-hash (sha256 over the alphabetised concatenation of every `wiki/syntheses/*.md` body; empty string when the directory is absent or empty) is unchanged, no-op with `IDEMPOTENT_HIT` and surface the prior report path. The user can force a re-run with `/claim-coverage-audit <section> --force`. The third hash component ensures that wiki-synthesis additions invalidate the cache and re-trigger the fast-path; existing S3-S4 reports cached without the syntheses hash will appear stale at first S4.5 invocation and re-run, producing reports with the new four-set output shape.

### No-op reason codes

```json
{
  "skill": "claim-coverage-audit",
  "status": "noop",
  "reason_code": "<code>",
  "message": "<human-readable>",
  "section": "<heading_path_or_filename>",
  "timestamp": "YYYY-MM-DDTHH:MM:SSZ"
}
```

Codes: `SECTION_AMBIGUOUS`, `EMPTY_SECTION_BODY`, `EMPTY_REFERENCES_POOL`, `CLASSIFICATION_MISSING`, `IDEMPOTENT_HIT`.

The no-op file is written to `reviews/claim_coverage_audit_noop_<YYYY-MM-DD>.json` and is authoritative — downstream consumers (the future Ph2 Step 0.5 dispatch at S4) read the no-op file when no findings file exists.

## 3. Procedure

### Phase 1 — Claim extraction

Read the section body and enumerate **claims**. A claim is a proposition that requires evidence. Per architecture §4.1, the five claim kinds are:

- **Existential** — a claim that some entity, phenomenon, or condition exists ("RPA is widely deployed in financial services").
- **Comparison** — a claim that one thing differs from, exceeds, or relates to another ("Approach A scales better than approach B").
- **Mechanism** — a claim about how or why something happens ("Increased cognitive load impairs working memory recall").
- **Result** — a claim about an empirical or theoretical finding ("In study X, treatment Y produced effect Z").
- **Theoretical commitment** — a claim that adopts or extends a theoretical framework ("This work treats organisations as activity systems in Engeström's sense").

Extraction is **rule-based and deterministic**, not heuristic. The procedure:

1. Split the section body into paragraphs, then into sentences (per `references/PARAGRAPH_DEFINITIONS.md` if present; otherwise standard markdown paragraph rules).

2. For each sentence, apply five sequential test patterns:
   - Existential: subject-verb-object pattern with verbs `is`, `are`, `exists`, `occurs`, `appears`, `has been observed`, plus a domain-bearing object.
   - Comparison: contains comparative markers (`more`, `less`, `greater`, `fewer`, `outperforms`, `differs from`, `exceeds`, `approaches`).
   - Mechanism: contains causal markers (`because`, `therefore`, `due to`, `as a result of`, `leads to`, `causes`, `enables`).
   - Result: contains finding markers (`found that`, `showed that`, `demonstrated`, `reported`, `observed`, `revealed`).
   - Theoretical commitment: contains framing markers (`we treat X as`, `following Y's framework`, `in the sense of`, `extending Z's account`).

3. A sentence matching any pattern emits a claim row: `(claim_id, claim_kind, claim_text, claim_locus, citations_present)` where `claim_locus` is the heading_path + line range and `citations_present` is the list of citation keys present in or immediately adjacent to the sentence.

4. Subsume nested claims under their containing sentence — a complex sentence may emit one claim, not three. The rule: extract the **load-bearing proposition**, not every sub-clause.

5. Skip sentences that are pure framing (signposts, transitions, methodology-narrative, results-table-references). The signposting / transition heuristic mirrors Sub-check D's signpost detection in `skills/accessibility-overlay/SKILL.md`.

The output is a deterministic ordered list of claims. Two consecutive runs against the same section body produce identical lists.

### Phase 2 — Source mapping

For each extracted claim, resolve the set of sources in `references/REFERENCES.md` that **resolve** the claim. A source resolves a claim iff at least one of:

- The claim sentence carries an explicit citation key matching a row in REFERENCES.md (`covered-explicit`).
- A source row in REFERENCES.md carries `claim_anchors:` metadata referencing the claim's locus or kind (`covered-anchored`).
- A source row's title or annotation (the third REFERENCES.md column) lexically matches the claim's load-bearing nouns above a similarity threshold (`covered-lexical`; default similarity 0.6 cosine over normalised noun phrases).

The mapping is **conservative**. A source counts as resolving a claim only if its match falls into one of the three categories. Speculative resolutions ("the source is on the right topic") do not count.

The result is a per-claim source set:

- **Covered.** At least one source resolves the claim across all of its named aspects (the claim's load-bearing nouns are all matched).
- **Partially-covered.** At least one source resolves the claim for some but not all named aspects. A claim like *"X causes Y in context Z under conditions C"* has four aspects (X, Y, Z, C); a source matching X and Y but not Z and C lands the claim in partially-covered.
- **Uncovered.** Zero sources resolve the claim under any of the three categories.

The classification is exclusive: a claim is in exactly one of the three sets *at this phase*. A partially-covered or uncovered claim may be promoted to `synthesis-covered` at Phase 2.5 if a wiki synthesis aligns with it; a `covered` claim stays `covered` regardless of synthesis alignment (the stronger evidence wins).

### Phase 2.5 — Synthesis-alignment fast-path (v0.10.0-S4.5 R1)

When the project's `wiki/syntheses/` directory exists and is non-empty, run the synthesis-alignment fast-path on every claim that did not land in `covered` at Phase 2 (i.e., the partially-covered and uncovered subsets). The fast-path checks whether any synthesis brief in the wiki asserts a claim that aligns with the section's claim; if so, promote the section's claim to `synthesis-covered`. This is the core of the v0.10.0-S4.5 R1 amendment per architecture §5.5.3.

The procedure:

1. **Enumerate syntheses.** List every `wiki/syntheses/<key>.md` file in deterministic order (sorted alphabetically by `<key>`). For each synthesis, read the body and extract the synthesis brief's anchor sentence(s) — typically the first paragraph after the H1, or the explicit `## Claim` block when present. Skip syntheses whose frontmatter carries `grounding_status: stub` (a stub synthesis cannot ground a section's claim).

2. **Compute alignment.** For each (section claim, synthesis anchor) pair, compute alignment conditioned on the project's `wiki_access_mode` (per architecture §5.5.6):
   - **`mcp_fastpath`** — cosine similarity over text embeddings (the MCP supplies the embedding endpoint). Threshold: **0.6** (alignment ≥ 0.6 ⇒ promote). The threshold parameter is `synthesis_alignment_threshold_cosine` in `reviews/classification.md` (default 0.6; surfaces at S4.5 R2 for project-side override).
   - **`filesystem`** (or `mcp_fastpath` failed mid-call and the runtime fell through per architecture §5.5.6) — Jaccard similarity over normalised noun-phrase sets. Threshold: **0.3** (alignment ≥ 0.3 ⇒ promote). The threshold parameter is `synthesis_alignment_threshold_jaccard` in `reviews/classification.md` (default 0.3; surfaces at S4.5 R2).
   The two thresholds are calibrated to roughly equivalent precision on a synthesis-aligned corpus; the cosine-vs-Jaccard divergence in alignment shapes is the calibration source.

3. **Apply precedence.** A claim that landed `covered` at Phase 2 stays `covered`. A claim that landed `partially-covered` or `uncovered` at Phase 2 is promoted to `synthesis-covered` if any synthesis aligns above threshold; otherwise the Phase 2 verdict stands. The promotion is exclusive — a promoted claim leaves its Phase 2 set entirely.

4. **Annotate.** Each synthesis-covered claim carries the annotation `[via-synthesis: <synthesis_key>]` in the report — naming the highest-scoring synthesis (ties broken by alphabetical `<synthesis_key>` and emitting only the top-scoring one).

The fast-path is a **conservative accelerant**, not a substitute for direct citation. A synthesis-covered claim is still subject to the Reflector Phase 2.5 Category 7 spot-check (sample-of-3 per round per architecture R-11) — the Reflector verifies that the synthesis brief actually supports the claim it has been credited against. If the spot-check disagrees, the claim's classification is downgraded at the next round and the alignment threshold may need calibration in `classification.md`.

**No-op condition.** If `wiki/syntheses/` does not exist, is empty, or contains only stub-status syntheses, the fast-path is silently skipped and the report's `synthesis-covered` set is empty. This is not a failure — it is the normal behaviour for projects that have not yet accumulated a synthesis layer. The skill's Phase 3 scoring uses `(covered + synthesis-covered) / total` regardless, which collapses to `covered / total` when the fast-path no-ops. Backward compatibility with the v0.10.0-S3..S4 three-set behaviour is therefore preserved.

**Determinism.** Like the rest of the skill, Phase 2.5 must be deterministic. Sort syntheses alphabetically before iteration. Round similarity scores to three decimal places before threshold comparison. Break ties (when multiple syntheses align above threshold for the same claim) by alphabetical `<synthesis_key>` and emit only the top-scoring one in the annotation. Two consecutive runs with the same wiki state produce identical synthesis-covered sets.

### Phase 3 — Coverage scoring

The **coverage score** is `(|covered| + |synthesis-covered|) / |total|`. Partially-covered and uncovered claims do not contribute to the numerator. The score is recorded with three decimal places.

The score is reported alongside two component subscores in the output artefact (§4): `direct_coverage = |covered| / |total|` and `synthesis_coverage = |synthesis-covered| / |total|`. The headline score is the union; the subscores let downstream consumers — the cross-round regression-detection consumer landing at S4.5 R2 (`coverage_regression_floor` against `last_coverage_score`) and the Reflector Phase 2g audit — distinguish direct-citation coverage from synthesis-mediated coverage.

The score is compared against `claim_coverage_threshold` from `reviews/classification.md`:

- **Score ≥ threshold.** Audit emits a CLEAN verdict. The Ph2 dispatch (when wired at S4) proceeds without an advisory.
- **Score < threshold.** Audit emits a BELOW_THRESHOLD verdict, names the uncovered claims with their locus and kind, and (from S4 onward) auto-dispatches SK-NEW-C `extend-snowball-incremental` per uncovered claim. At S3 (manually-invokable mode) the audit recommends manual extension and stops.

The score is **advisory, not gating**. A section can advance to Ph2 with a sub-threshold score if the user judges the uncovered claims are out-of-scope or coverable only via grey literature (per Risk R-3 in architecture §7).

## 4. Output artefact

Write the report to `reviews/claim_coverage_<YYYY-MM-DD>_<cycle_id>.md` in the following shape:

```markdown
# Claim Coverage Audit — <section heading_path>
Cycle: <cycle_id>
P-stage: <P0|P1|P2>
Threshold: <claim_coverage_threshold from classification.md>
Skill version: claim-coverage-audit@v1.0
Wiki access mode: <filesystem | mcp_fastpath | mcp_unreachable | NA-when-not-wiki-linked>
Synthesis-alignment threshold (active): <0.6 cosine | 0.3 Jaccard | NA>
Manuscript hash: <sha256 of manuscript/<section>.md at audit time>
References hash: <sha256 of references/REFERENCES.md at audit time>
Syntheses hash: <sha256 of alphabetised wiki/syntheses/*.md concatenation; empty when wiki/syntheses/ is absent>

## Coverage score: (<covered> + <synthesis-covered>) / <total> = <score> (<verdict>)
Verdict: CLEAN | BELOW_THRESHOLD
Direct coverage: <covered>/<total> = <direct_score>
Synthesis-mediated coverage: <synthesis-covered>/<total> = <synthesis_score>

## Covered (<count>) — direct citation / anchored metadata / lexical match
| claim_id | claim_kind | claim_text (load-bearing) | claim_locus | resolving_sources |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

## Synthesis-covered (<count>) — via wiki synthesis brief (v0.10.0-S4.5 R1)
| claim_id | claim_kind | claim_text (load-bearing) | claim_locus | aligning_synthesis | alignment_score | wiki_access_mode |
|---|---|---|---|---|---|---|
| ... | ... | ... | ... | [[syntheses/<key>]] | 0.741 | mcp_fastpath |

## Partially covered (<count>)
| claim_id | claim_kind | claim_text | claim_locus | resolved_aspects | unresolved_aspects | partial_sources |
|---|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... | ... |

## Uncovered (<count>)
| claim_id | claim_kind | claim_text | claim_locus | suggested_fix |
|---|---|---|---|---|
| ... | ... | ... | ... | Run /extend-snowball-incremental on this claim, OR cite an existing pool source explicitly, OR mark the claim out-of-scope per directives.md |

## Recurrence hint for Reflector Phase 2g
<list of uncovered claim_ids; compare against the prior round's emission set>
```

The report is appended to `reviews/consolidated_findings_report.md` by reference when the Evaluator runs at Ph2 (from S4 onward); at S3 the file stands alone for user inspection.

## 5. Determinism contract

The skill MUST be deterministic across two consecutive invocations on unchanged inputs. Sources of non-determinism to avoid:

- **Floating-point similarity scores.** Round to three decimal places before comparison against the 0.6 threshold. Use a fixed tokeniser; do not rely on system-locale-dependent splitters.
- **Iteration order over REFERENCES.md rows.** Sort sources by their canonical citation key (alphabetical) before mapping. Do not preserve file order.
- **Random tiebreaks.** When multiple sources resolve the same claim, list all of them in alphabetical order of citation key. Do not pick "best."
- **Timestamp leakage.** Only the report's `timestamp` field varies between runs. The findings tables, hashes, and verdict are identical.

The strategy §5.4 stage-close gate validates this by running the audit twice in succession and diffing the two outputs; the diff must be empty modulo the timestamp line.

## 6. What this skill does NOT do

- **Not a Class 1 verifier dispatch.** No Scholar Gateway calls, no Consensus calls. The skill only reads on-disk artefacts.
- **Not a manuscript editor.** It does not modify `manuscript/<section>.md` or `references/REFERENCES.md`.
- **Not a snowball extender.** When coverage falls below threshold, it surfaces the uncovered set; SK-NEW-C (S4) handles the extension.
- **Not a Ph2 gate.** The audit is advisory, not blocking. The user is the final arbiter on whether sub-threshold coverage permits Ph2 entry — per the long-standing Ph2 admission grammar in `references/PHASE_PROTOCOL.md §3.2`.
- **Not a substitute for the Evaluator's judgment.** The audit's lexical similarity threshold is conservative (0.6); a borderline claim-source pair that the lexical match misses but a domain expert would accept lands in `partially-covered` or `uncovered` and surfaces for the Evaluator to adjudicate at Ph2.

## 7. Manually-invokable status (v0.10.0-S3)

At v0.10.0-S3 this skill is invoked **only** via the slash command `/claim-coverage-audit <section>`. There is no automatic dispatch from any phase runner. The user runs it after Ph1 completion (or any time during Ph1 to gauge progress) and inspects the report.

At v0.10.0-S4 a new Step 0.5 in `run-phase-2` will auto-invoke this skill before Evaluator Step 0a. The auto-invocation will wire the Ph2 advisory and (when score is below threshold) dispatch SK-NEW-C `extend-snowball-incremental` per uncovered claim. The S4 amendment will edit `skills/run-phase-2/SKILL.md` and add a partial-failure halt-vs-continue clause; this skill itself is unchanged at S4.

At v0.10.0-S4.5 R1 this skill's procedure was amended to add the synthesis-alignment fast-path (architecture §5.5.3; documented at §3 Phase 2.5 above): a fourth set `synthesis-covered` is added to the output, conservatively annotated `[via-synthesis: <synthesis_key>]`. The headline coverage score now sums direct and synthesis-mediated coverage (`(covered + synthesis-covered) / total`); subscores `direct_coverage` and `synthesis_coverage` are reported separately so downstream consumers — the cross-round regression-detection consumer landing at S4.5 R2 (`coverage_regression_floor` against `last_coverage_score`); the Reflector Phase 2g audit — can distinguish the two. The fast-path silently no-ops on projects without a populated `wiki/syntheses/` layer, preserving backward compatibility with the S3..S4 three-set behaviour. The synthesis-alignment threshold parameters (`synthesis_alignment_threshold_cosine` default 0.6; `synthesis_alignment_threshold_jaccard` default 0.3) are surfaced in `reviews/classification.md` at v0.10.0-S4.5 R2.

---

*Normative status.* This skill is the named operationaliser of the Ph1 → Ph2 admission signal defined in architecture §4.4. It is bound to `references/EXTERNAL_VERIFIERS.md §3` (Planner clause for source-resolution discipline) and to `references/GROUNDING_PROTOCOL.md` Rule 6 (no gap-filling — uncovered claims are surfaced, not back-filled with weak sources). The skill is registered as **SK-34** in `references/SKILL_REGISTRY.md`. S3 shipped the manually-invokable three-set audit; S4 wired the auto-dispatch from `skills/run-phase-2/SKILL.md §4 Step 0.5` (with the S4 architectural decisions anchored at `agents/planner.md §Phase 3.8`); S4.5 R1 added the synthesis-alignment fast-path documented at §3 Phase 2.5; S4.5 R2 will surface the threshold parameters in `reviews/classification.md` and wire the cross-round regression-detection consumer. The S5 documentation amendments (named-executor lines in `references/EXTERNAL_VERIFIERS.md §1.5`; `references/AGENT_ORCHESTRATION.md §8.6` Coupling E.1 retirement) are out of scope for S4.5.
