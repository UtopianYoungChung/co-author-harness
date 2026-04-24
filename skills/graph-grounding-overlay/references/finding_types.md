# Phase 3 — The three finding types (detailed spec)

> **Loaded by** `SKILL.md` at the Phase 3 dispatch step. Owns the full spec for Finding A (graph-stub citations), Finding B (section-location mismatches — including the three-tier matcher with Jaccard 0.25 / bigram / stemmed-Jaccard 0.30 thresholds), and Finding C (missing-citation candidates). The numeric thresholds here are v1 defaults; SKILL.md keeps the operational routing and hand-off.

---

## Phase 3 — Generate the three finding types

**Finding type A — Graph-stub citations.** For every source in `cited_sources_without_nodes`:

- Severity: `[MAJOR]` if the source is a P1-anchor (per SK-15 priority classification) or appears more than 3 times in the manuscript; `[MINOR]` otherwise.
- Source tag: `[source: graph-stub]`
- Message: `Citation to <author YYYY> (<pdf_path>) has no graphify nodes — graph has not ingested this source. Re-run graphify to resolve, or accept the grounding gap.`

**Finding type B — Section-location mismatches.** For each citation in `resolved_cites` that points at a specific section (e.g., "Suchman 2007, §3.4" or "Haslam et al. 2013, Table 2"):

Extract the citation's sentence-level context — the sentence containing the citation plus the preceding sentence if the citation is at the start of one. Call this `claim_text`.

Run the matcher against every node in `nodes_by_source_file[pdf_path]` where `node.confidence == EXTRACTED` (INFERRED nodes are excluded from Finding B by design — they carry their own extraction uncertainty and would produce false positives). The matcher is three-tiered and short-circuits on first success:

1. **Tier-1 exact lexical match.** After lowercasing and removing stopwords, compute Jaccard similarity between the token set of `claim_text` and the token set of `node.label` (or `node.norm_label`, whichever yields the higher score). A node matches at Tier-1 if Jaccard ≥ 0.25 AND at least one content-word token (non-stopword with length ≥ 5) appears in both sets. This threshold was chosen empirically: graphify's node labels average 4–8 tokens, and 0.25 Jaccard corresponds to roughly one shared content word plus partial overlap.
2. **Tier-2 n-gram match.** If no Tier-1 match, check whether `node.norm_label` appears as a contiguous bigram-or-longer substring of the lowercased `claim_text`. Example: `node.norm_label = "collaborator-assistant spectrum"` matches the claim text "they distinguish a collaborator-assistant spectrum across merge workflows."
3. **Tier-3 stem-overlap match.** If no Tier-2 match, Porter-stem both token sets and recompute Jaccard with threshold 0.30. Stemming compensates for graphify's preference for noun-phrase node labels when the manuscript uses verb forms.

Then compare `source_location` values:

- If a matching node's `source_location` **equals** (case-insensitive, whitespace-normalized) the manuscript's cited section → no finding, citation is corroborated.
- If a matching node's `source_location` **differs** from the cited section → emit Finding B.
- If **no node matches** at any tier → do NOT emit Finding B. The absence of a match means the graph cannot corroborate or refute the location claim, not that the location is wrong. This is Rule 6 (No Gap-Filling) applied to graph overlay.

Finding B output:

- Severity: `[MAJOR]` at `submission-bound` depth; `[MINOR]` at `standard` depth; N/A at `light` depth.
- Source tag: `[source: graph-extracted]` (carry the matching node's `confidence_score == 1.0` through; a Tier-1 match cites the node directly, Tier-2/Tier-3 matches append `(match-tier: 2)` or `(match-tier: 3)` to the finding so grounding-audit Category 8 can weight the match confidence).
- Message: `Manuscript cites <author YYYY> §X for "<claim_text excerpt>", but graphify's node <node.id> locates this claim at §Y in the same source (match tier <1|2|3>). Verify by reading §Y and either correct the section number or confirm the manuscript's framing is broader than graphify's extraction.`

**Matcher calibration note.** The thresholds above (0.25 / bigram / 0.30) are v1 defaults calibrated to graphify's 2026-04-13 corpus output. If the pilot produces excessive false positives, raise thresholds; if it misses known mismatches, lower them. Record the thresholds used in the overlay report's P-stage-adjustments section so grounding-audit Category 8 can verify the calibration was consistent across findings.

**Finding type C — Missing-citation candidates.** For every edge in `edges_by_source_pair` where one endpoint's `source_file` is cited by the manuscript and the other endpoint's `source_file` is **not** cited, AND the edge's `relation` is one of `supports`, `extends`, `semantically_similar_to`, or `contradicts`:

- Severity: `[MAJOR]` if `relation == contradicts` at any P-stage; `[MAJOR]` if `confidence == EXTRACTED` at P1/P2; `[MINOR]` otherwise.
- Source tag: `[source: graph-inferred]` if the edge is INFERRED (carry `confidence_score` in the finding); `[source: graph-extracted]` if EXTRACTED.
- Message: `Manuscript cites <cited_source> for <cited_claim>, but graphify shows this claim <relation> a claim in <uncited_source> with confidence <score>. Consider whether <uncited_source> should be cited here, OR whether the graph edge is a false positive.`

Do NOT auto-promote findings to BLOCKER. The overlay's function is to surface candidates; severity escalation beyond MAJOR requires the Evaluator's normal seven-step judgment in a subsequent pass.

