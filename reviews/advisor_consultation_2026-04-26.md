# Advisor Consultations — 2026-04-26

## Consultation — 14:00 — Prompt clarity 0.25 score: calibrator gap vs structural deficiency?

**Question asked:**
> Three remediation paths exist for the 0.25 clarity score: (A) extend the calibrator's recognised-section config with harness-specific patterns (## What you do, ## Step N, ## Phase N, ## Output); (B) add standardised alias section headers to all 24 failing skills — effectively prepending a generic Procedure or Inputs block to each; (C) accept this as a known false-negative baseline and document it in .plugin-efficiency.json, treating the calibrator's clarity check as not applicable to this plugin's documentation style. What are the long-term maintainability trade-offs of each path? Specifically: does the mismatch itself signal a structural issue — that the skills are formatted inconsistently enough that a reasonable recogniser should catch them — or is this purely a calibrator vocabulary gap that the harness should not adapt to?

**Task summary provided:**
> We ran a full plugin calibration loop on the co-author-harness plugin (v0.8.7) — a research-writing assistance plugin for Claude Code/Cowork that orchestrates Planner→Evaluator→Generator→Reflector agents through a Ph1–Ph4 lifecycle ladder for academic manuscript development (IS/HCI domain, venues such as CAiSE and ECIS). The session produced three findings: (1) Six dead markdown references were fixed by redirecting to existing files. (2) Quality audit scored prompt_clarity at 0.25/1.0 — 24 of 32 artefacts fail due to calibrator vocabulary mismatch, not structural deficiency. (3) Chain depth reported as 21 > threshold 15, driven by plugin-commands manifest skill; actual operational pipeline is 5 phases.

**Contract version:** v1.3.0
**Input tokens:** 2,264
**Output tokens:** 1,038
**Packer warnings:** 0
**Model reported by server footer:** claude-opus-4-6 ⚠️ (server code pins ADVISOR_MODEL = "claude-opus-4-7"; footer may reflect a running instance of an older build — discrepancy noted)

---

### Advisor response (post-reclassification)

# Advisory Response: Remediation Path for 0.25 Clarity Score

## Diagnosis First

The core question is whether the mismatch signals a real structural problem or a calibrator vocabulary gap. Based on the evidence provided, **this is clearly a calibrator vocabulary gap, not a structural deficiency in the harness.** Evidence:

- All 32 artefacts pass frontmatter, trigger fields, and fenced code blocks — the semantic infrastructure is sound.
- The 4 agents that use `Output Contract + Procedure` headers pass — proving the calibrator works when vocabulary aligns.
- The 24 failing skills use **consistent** domain-specific headers (`## What you do`, `## Step N —`, `## Phase N —`) — they follow a *different* convention that the calibrator doesn't recognize.
- A "reasonable recogniser" should absolutely catch `## Step N —` as procedural and `## What you do` as a role/scope block. The calibrator's pattern list is underspecified, not the harness.

## Trade-off Analysis

### Path A: Extend calibrator's recognised-section config
**Pros:** Fixes root cause. Calibrator becomes smarter for this and future domain-specific plugins. The 24 skills need zero changes. Accuracy of clarity metric improves globally.
**Cons:** Requires maintaining calibrator config alongside the harness. If the calibrator is upstream/shared infrastructure, config patches may be overwritten on updates.
**Maintainability:** Best long-term if you control or can contribute to the calibrator. Moderate risk if calibrator is external — requires a `.calibrator-overrides` mechanism that survives version bumps.

### Path B: Add standardised alias headers to 24 skills
**Pros:** Immediate score fix. Skills become legible to any tool using standard vocabulary.
**Cons:** **Worst option.** Retrofits 24 files to satisfy a tool limitation. Introduces dual-header structures (domain-specific + generic aliases) creating real maintenance burden. Risks confusing agents that consume these skills. Adapts the artifact to the measurement tool rather than the reverse.
**Maintainability:** Ongoing tax on every new skill. Drift risk as contributors forget to add aliases. Semantic noise in files.

### Path C: Document as known false-negative baseline
**Pros:** Zero code changes. Transparent. Honest about what the metric means for this plugin.
**Cons:** Future real clarity regressions invisible against baseline noise. Degrades the metric's utility as a regression gate.
**Maintainability:** Low effort but acceptable only as a temporary measure.

## Recommendation

**Path A is clearly correct, with Path C as an interim bridge.**

1. **Immediately:** Document the false-negative baseline in `.plugin-efficiency.json` with a clear explanation (Path C), so the score is interpretable now.
2. **Next sprint:** Extend the calibrator's recognised-section vocabulary (Path A). Specific additions: map `## What you do` → scope/role, `## Step N —` and `## Phase N —` → procedure, `## Output` → output contract. Small, testable change.
3. **Do not pursue Path B** under any circumstances. It inverts the correct dependency direction and creates permanent maintenance burden.

## On the Chain Depth Issue (Finding 3)

Same category of problem: the checker lacks a `PROTOCOL_STAGES` constant and falls back to graph traversal, picking up the manifest hub as a false positive. Analogous fix to Path A — declare the constant or configure the checker to exclude manifest-type nodes from depth calculation. Document the 5-phase operational truth alongside the reported 21.

## Risk Flag

If you don't control the calibrator codebase, Path A requires either (a) a contribution upstream, (b) a local override mechanism, or (c) a fork. Clarify ownership before committing to the timeline. If the calibrator is fully external with no override hooks, Path C becomes the permanent answer and advocate upstream for configurable section vocabularies.

---

### EXTERNAL tag summary

| # | Tag | Sentence fragment | Original | Final | Reclassified? |
|---|-----|-------------------|----------|-------|---------------|
| — | — | (none) | — | — | No EXTERNAL tags present |

### Reclassification log

None — advisor response contains no external literature attributions. All content is architectural reasoning grounded in the harness structure as described in the task summary.

### Grounding status

No `[EXTERNAL: fact]` items in this consultation. Advisor guidance is structural/architectural and does not introduce literature claims requiring independent verification before manuscript use.
