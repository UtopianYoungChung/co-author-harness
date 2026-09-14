# Grounding Audit — Categories 1 through 8 (rubrics + severity)

> **Loaded by** `SKILL.md` at the audit-execution step. This file is the authoritative specification of each category: what to check, how to verify, and severity assignments. SKILL.md keeps the routing and the output template; this file defines the rubrics.

---

## Category 1 — Citation audit (Rule 4: Quote Before Attribute)

For every author attribution in the audited artifact:

1. Is the source referenced in `references/REFERENCES.md` or the manuscript bibliography?
2. Has the source been read in this session or a documented prior session?
3. Does the attributed claim match what the source actually says? (Spot-check at least 3 attributions.)

| Finding | Severity |
|---|---|
| Attribution matches source | PASS |
| Source exists but attribution is inaccurate or distorted | [BLOCKER] — Rule 4 violation |
| Source not read; attribution based on training data | [BLOCKER] — Rule 4 violation (must be marked Indirect tier) |
| Source does not exist (fabricated reference) | [BLOCKER] — Rule 6 violation (gap-filling) |

## Category 2 — Metrics audit (Rule 2: Compute Before Report)

For every count or metric in the audited artifact (em-dash counts, sentence counts, finding tallies):

1. Was a computation (grep, word count, script) run to produce the number?
2. Does the reported number match the computed number?

| Finding | Severity |
|---|---|
| Number matches computation | PASS |
| Number does not match (off by > 0 for exact counts) | [BLOCKER] — Rule 2 violation |
| No computation found for the reported number | [BLOCKER] — Rule 2 violation (number from memory) |

**How to verify:** Re-run the computation yourself. If the artifact says "3 em-dashes," grep for em-dashes and count. If the counts match, PASS. If not, report the discrepancy.

## Category 3 — Path audit (Rule 3: Verify Before Reference)

For every file path in the audited artifact:

1. Does the file exist at the referenced path?
2. If the path references a specific section or line number, does that section/line exist?

| Finding | Severity |
|---|---|
| Path exists and content matches | PASS |
| Path does not exist | [BLOCKER] — Rule 3 violation |
| Path exists but section/line does not | [MAJOR] — Rule 3 violation (partial) |

**How to verify:** Use Glob or Read to check each path.

## Category 4 — Rule-citation audit (Rule 1: Read Before Cite)

For every package-rule citation in the audited artifact (e.g., "MASTER §B.1," "Bacon §3.2," "SAFEGUARD Check 4"):

1. Does the cited section exist in the cited file?
2. Does the section say what the artifact claims it says? (Spot-check at least 3.)

| Finding | Severity |
|---|---|
| Citation exists and content matches | PASS |
| Section does not exist in the file | [BLOCKER] — Rule 1 violation (fabricated rule citation) |
| Section exists but says something different | [BLOCKER] — Rule 1 violation (misquoted rule) |

**How to verify:** Read the cited file at the cited section.

## Category 5 — Gap-fill audit (Rule 6: No Gap-Filling)

For every factual claim in the audited artifact that is NOT a rule citation or attribution:

1. Is the claim traceable to a verifiable source (a file read, a computation, a user statement)?
2. Are there claims that are "too smooth, too specific, or too convenient" without a source?

| Finding | Severity |
|---|---|
| Claim traceable to source | PASS |
| Claim plausible but untraceable | [BLOCKER] — Rule 6 violation (plausible fabrication) |

This is the hardest category. Look specifically for:
- Specific numbers without a computation
- Author positions without a source
- Historical claims without a citation
- "The manuscript says X on line Y" without evidence of reading line Y

## Category 6 — Marker audit (Rule 5: Mark Uncertainty)

For every uncertainty marker (`[UNVERIFIED]`, `[FROM MEMORY]`, `[INFERRED]`, `[APPROXIMATE]`, `[REF to be verified]`) in the audited artifact:

1. Was the marker resolved by verification? If so, confirm it was removed after verification.
2. If not resolved, is the marker still present in the final output?

| Finding | Severity |
|---|---|
| Marker resolved and removed after verification | PASS |
| Marker still present (unresolved) — correctly retained | PASS |
| Marker silently dropped without verification | [BLOCKER] — Rule 5 violation |
| Unverified claim with no marker at all | (Caught by Categories 1–5 above) |

Additionally: are there claims that **should** have markers but don't? Look for hedging language ("probably," "likely," "I believe") that masks an unverified claim without using the formal marker system.

## Category 7 — Legacy advisor-sourced claims (Rules 4, 7a)

**Applies when:** the audited artifact contains `[source: advisor]` cross-references. If no `[source: advisor]` items exist, mark this category N/A.

For every `[source: advisor]` item in the audited artifact:

1. Does a corresponding entry exist in `reviews/advisor_consultation_YYYY-MM-DD.md`?
2. Is the underlying claim an `[EXTERNAL: fact]` (requires independent verification) or an `[EXTERNAL: gap]` (investigation candidate, no verification needed)?
3. If `[EXTERNAL: fact]`: has the claim been independently verified since the consultation? Check for:
   - A Zotero entry added after the consultation date
   - A `[verified]` annotation added to the consultation artifact
   - A manuscript citation that post-dates the consultation

| Finding | Severity |
|---|---|
| Advisor-sourced claim traced to consultation artifact, fact verified | PASS |
| Advisor-sourced claim traced to consultation artifact, gap (no verification needed) | PASS |
| Advisor-sourced claim traced to consultation artifact, fact NOT verified but not yet at submission-bound depth | [MAJOR] — schedule verification |
| Advisor-sourced claim traced to consultation artifact, fact NOT verified at submission-bound depth | [BLOCKER] — Rule 7a violation |
| Advisor-sourced claim NOT traced to any consultation artifact | [BLOCKER] — Rule 4 violation (unattributed advisor claim) |

**How to verify:** Read the consultation artifact at the expected path (`reviews/advisor_consultation_*.md`). Match the claim text against the advisor's response. Check the EXTERNAL tag summary table for the tag classification. For verification status, search Zotero (if MCP available) or check the manuscript's reference list for post-consultation additions.

## Category 8 — Graph-sourced claims (Rules 3, 4, 5)

**Applies when:** the audited artifact contains `[source: graph-extracted]`, `[source: graph-inferred]`, or `[source: graph-stub]` tags (produced by SK-20 `graph-grounding-overlay`). If no graph tags exist, mark this category N/A.

For every graph-sourced item in the audited artifact:

1. Does a corresponding entry exist in `${wiki_path}/graphify-out/graph.json` (for extracted/inferred; resolve `wiki_path` from project AGENTS.md or CLI overrides) or in the manuscript's citation set (for stub)?
2. For `[source: graph-extracted]`: does the node's `source_file` + `source_location` match the finding's claim location? The node must carry `confidence: EXTRACTED` and `confidence_score == 1.0`.
3. For `[source: graph-inferred]`: does the edge's endpoints, `relation`, and `confidence: INFERRED` (or `AMBIGUOUS`) match the finding's claim? The finding MUST carry the edge's `confidence_score` through.
4. For `[source: graph-stub]`: is the cited source genuinely absent from graph.json (zero nodes with matching `source_file`)?

| Finding | Severity |
|---|---|
| Graph-sourced finding traces to matching graph node/edge with matching confidence | PASS |
| Graph-stub finding traces to a cited source genuinely absent from graph.json | PASS |
| Graph-extracted finding attributed a higher confidence than the node carries (e.g., confidence_score inflated) | [MAJOR] — Rule 5 violation (uncertainty laundering) |
| Graph-inferred finding missing its confidence_score | [MAJOR] — Rule 5 violation |
| Graph-sourced finding references a node or edge that does NOT exist in graph.json | [BLOCKER] — Rule 4 violation (fabricated graph claim) |
| Graph-stub finding referenced a source that DOES have nodes in graph.json | [BLOCKER] — Rule 3 violation (false stub claim) |
| Overlay report emitted but graph is stale relative to manuscript/references | [MAJOR] — staleness not reported in overlay header |

**How to verify:** Read `${wiki_path}/graphify-out/graph.json` and match each graph-sourced finding against its source node or edge. For extracted claims, verify `source_location` matches. For inferred claims, verify the edge exists with the claimed endpoints and relation. For stub claims, grep `graph.json` for the absent source and confirm zero matches. Compare `captured_at` in `graph.json` against the overlay report's declared graph-capture date.

---
