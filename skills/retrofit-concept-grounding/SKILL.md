---
name: retrofit-concept-grounding
description: >-
  Retrofit wiki concept pages with grounding citations to existing source pages. Converts
  in-prose author-year references into wikilinks to `sources/` pages, updates frontmatter
  `sources` and `grounding_status`, and appends a grounding footer. Performs surgical edits
  only — does not rewrite page content.
trigger: when the user asks to ground concept pages, retrofit wikilinks after a batch source-stub run, materialize Coupling B, or close the grounding loop after SK-15
created_by: Reflector (Coupling B codification)
created_from: Research↔Wiki diagnostic audit 2026-04-13 — Finding F3 (concept pages assert claims without grounding citations); pilot on `concepts/humanness.md` 2026-04-13 demonstrated that retrofit works when (a) source stubs exist (SK-15) and (b) the retrofit is surgical (preserves existing prose) rather than a rewrite
pattern_source: GROUNDING_PROTOCOL.md Rule 4 (every theoretical claim must be citable); LLM wiki CLAUDE.md §Wikilinks ("link to existing concept/entity pages when mentioning key terms")
version: 1.0
---

# Retrofit Concept Grounding

You are executing **Coupling B** — the concept-page grounding retrofit that closes the loop between the wiki's external-source layer (populated by SK-15) and the concept pages that cite those sources in prose without wikilinks. The retrofit is **surgical**: you convert in-prose citations into wikilinks, update frontmatter, and append a grounding footer. You do NOT rewrite the page's argument, reorder its sections, or alter its claims.

## Preconditions

1. **Target concept page exists** at `LLM wiki/wiki/concepts/<name>.md` with existing prose content.
2. **Relevant source stubs exist** in `LLM wiki/wiki/sources/` — if the page cites sources that have no wiki page, the retrofit reports them as **red-link candidates** and does not fabricate links.
3. **Source pages' `source_key` frontmatter resolves** — the skill uses the `source_key` field to construct wikilinks, not the filename (though they should match).
4. **The page is not currently under live edit** — check for a conflicting modification timestamp; if the page was updated in the last hour by another agent, ask the user whether to proceed.

## What you do

### Phase 1 — Inventory citations

1. Read the target concept page.
2. Enumerate every in-prose author-year citation. Use the pattern: `Author (YYYY)`, `Author et al. (YYYY)`, `(Author YYYY)`, `(Author et al. YYYY)`, or in-table cells like `(Bandura 2001)`.
3. For each citation, attempt to resolve it to a `wiki/sources/<key>.md` page by matching author + year against the source pages' frontmatter (`source_key`) and first-line author field.
4. Produce two lists:
   - **Resolvable citations** — (author, year, target source_key)
   - **Red-link citations** — (author, year, *no source page exists yet*)

### Phase 2 — Plan edits

For each resolvable citation, plan a wikilink replacement:
- In-prose: `Suchman (2006)` → `[[sources/suchman-2006-reconfigurations|Suchman 2006]]`
- Parenthetical: `(Haslam et al. 2013)` → `([[sources/haslam-2013-humanness|Haslam et al. 2013]])`
- In-table: `(Bandura 2001)` → leave if no source page exists; retrofit if it does

Do NOT replace a citation that is already a wikilink. Do NOT replace citations inside code blocks or frontmatter.

### Phase 3 — Execute edits

1. **Update frontmatter `sources:`** to include every resolved `source_key` not already listed.
2. **Add `grounding_status: retrofit <YYYY-MM-DD>`** to frontmatter (or update the date if the field exists).
3. **Replace in-prose citations with wikilinks** using the plan from Phase 2. Preserve surrounding punctuation and capitalization exactly.
4. **Append a "Grounding sources" footer section** if one does not exist, or update it if it does:
   ```markdown
   ## Grounding sources

   | Source | Role on this page |
   |---|---|
   | [[sources/<key>]] | <one-line role — e.g., "foundational two-sense model (§1)", "Position A anchor (§3)"> |
   | ... | ... |

   *Grounding retrofit: <YYYY-MM-DD>. Status of each source (stub vs. direct-read) can be checked on its page.*
   ```
5. **Do NOT touch** existing sections (Core, Three Dimensions, etc.) except to convert citations within them to wikilinks.

### Phase 4 — Report red-links

Any citation that could not be resolved becomes a **red-link candidate** in the report. Common cases:

- The source is cited-but-not-read-directly in the project REFERENCES (per the Agency convention) and was correctly skipped by SK-15. Propose no action; note that the retrofit cannot ground it until it is read directly.
- The source is an external work not yet in any project's REFERENCES. Propose an ad-hoc stub or flag for user attention.
- The author-year string is ambiguous (e.g., "Leonardi (2023)" could map to one of several Leonardi papers). Report ambiguity; do not guess.

### Phase 4.5 — Red-link auto-trigger (v0.10.0-S4.5 R1)

After Phase 4's red-link report is produced, optionally auto-dispatch SK-NEW-C `extend-snowball-incremental` (SK-35) on each red-link candidate to extend the project's source pool. This phase implements the wiki-collaboration accelerant specified in architecture §5.5.4: red-links surfaced during a SK-16 round can be resolved in-loop rather than waiting for a manual `/extend-snowball-incremental` invocation.

The phase is **gated, capped, and skip-and-continue.** Procedure:

1. **Gate check.** Read `reviews/classification.md`. If the file does not exist, fails YAML parse, declares `wiki_linked: false`, OR declares `auto_redlink_snowball: false` (default `false` at S4.5 R2 surfacing — opt-in by design), skip Phase 4.5 entirely. The Phase 4 red-link report stands unchanged. If `auto_redlink_snowball: true` AND `wiki_linked: true`, proceed.

2. **Cap selection.** Read `red_link_cap_per_round` from classification.md (default 5; surfaces in classification.md template at S4.5 R2). The first `red_link_cap_per_round` red-link candidates in **document order** (the order they appear during the Phase 1 inventory sweep) are selected for SK-NEW-C dispatch. Remaining candidates are deferred. The document-order rule is the deterministic default; future v0.10.x extension may add a criticality-ranked selection per Rule 7a.

3. **Per-red-link dispatch.** For each selected red-link candidate `(author, year, claim_locus, concept_page_path)`, dispatch SK-NEW-C with anchor synthesised from the citation context:

   ```
   anchor: "<author> <year> — cited at <claim_locus> in <concept_page_path>; surrounding sentence: <one-line excerpt>"
   ```

   SK-NEW-C runs its standard Phase 1 anchor selection / Phase 2 micro-iteration / Phase 3 atomic write. On clean dispatch, the new source row lands in `references/REFERENCES.md` and the source stub `wiki/sources/<key>.md` is created in-loop per architecture §5.5.2. The newly-grounded source becomes resolvable for any **subsequent** SK-16 invocation in a future round (the round's red-link queue is computed once at Phase 1 and is not re-walked after each dispatch — SK-NEW-C-resolved sources affect the next round, not the current one).

4. **Skip-and-continue partial-failure semantics.** A SK-NEW-C dispatch that errors mid-call (per SK-NEW-C §8 failure modes — `WRITE_FAILURE`, `EXTERNAL_VERIFIER_UNREACHABLE`, anchor selection no-op, `INSUFFICIENT_SEEDS_AFTER_PHASE`, etc.) does **NOT** halt Phase 4.5. The failed red-link is logged with the failure reason; processing advances to the next red-link in the queue. Per-failure `W-` / `E-` codes are not emitted; the audit trail in `reviews/snowball_log.md` is the canonical failure record. Aggregate failure counts surface in the Phase 4.5 closing summary appended to the SK-16 report. The skip-and-continue contract is documented authoritatively in §Failure modes below; this is the single-source-of-truth (no phase-runner reads the contract — Phase 4.5 is invoked inline as part of SK-16's procedure, and SK-16 itself is not a phase-runner).

5. **Cap saturation handling.** If the queue size exceeds `red_link_cap_per_round`, the excess red-links are written to the SK-16 round's `snowball_log` row as deferred-discovery candidates with structure:

   ```yaml
   - type: deferred_redlink_at_sk16
     round_id: <round_id>
     red_link_total: <n>
     red_link_cap: <cap>
     deferred:
       - author: <author>
         year: <year>
         claim_locus: <locus>
         cited_at: <concept_page_path>
   ```

   The `W-REDLINK-CAP-SATURATED` warning code is emitted (per `references/phase_notifications.yaml redlink_cap_saturated` block) with fields `{round_id, redlink_total, cap, deferred_count, snowball_log_path}`. The user adjudicates deferred candidates at round close per the warning's recommended-action ladder.

6. **Logging.** Each red-link auto-trigger event (whether successful, failed, or deferred at the cap) appends one row to `reviews/snowball_log.md` with the standard SK-NEW-C log shape extended with `triggered_by: redlink_auto_trigger_at_sk16` and `triggering_red_link: (author, year, claim_locus, concept_page_path)`. The log is the audit trail; the Reflector's Phase 2.5 Category 7 spot-check (sample-of-3 per round per architecture R-11) verifies a sample of red-link auto-triggered admissions to detect false positives.

**No-op condition.** If the gate check at step 1 fails, OR the red-link queue is empty after Phase 4, Phase 4.5 silently no-ops. The Phase 4 red-link report is unchanged in either case; no `W-` code is emitted on no-op.

**Determinism.** Process red-links in document order (Phase 1's enumeration order). On cap saturation, the first `red_link_cap_per_round` are processed; the remainder are deferred. Two consecutive runs against the same concept-page state and the same `red_link_cap_per_round` parameter produce identical Phase 4.5 dispatch sequences.

**Cross-references for the auto-trigger contract:** architecture §5.5.4 (red-link auto-trigger design); architecture R-12 (rate-limit mitigation); `references/phase_notifications.yaml redlink_cap_saturated` block (W-REDLINK-CAP-SATURATED user-template); `skills/extend-snowball-incremental/SKILL.md §3` (SK-NEW-C dispatch contract); §Failure modes below (skip-and-continue partial-failure contract).

### Phase 5 — Verify

1. **Frontmatter integrity.** The `sources:` list is valid YAML; `grounding_status` is present.
2. **Wikilink resolution.** `grep` each new wikilink in the page; confirm each points to an existing `sources/*.md` file.
3. **Prose preservation.** Diff the page against its prior state; confirm that no sentence was deleted or reordered. Only citation-span substitutions and frontmatter additions should appear.
4. **Footer consistency.** The grounding footer matches the `sources:` frontmatter exactly (no source in footer but not in frontmatter, or vice versa).

## What you output

```markdown
## Coupling B Retrofit — <concept page>

**Page:** `wiki/concepts/<name>.md`
**Date:** <YYYY-MM-DD>

### Citations inventory
- In-prose: <n>
- In-table: <n>
- Already-linked (skipped): <n>

### Resolution
| Citation | Resolution | Source page |
|---|---|---|
| Suchman (2006) | resolved | [[sources/suchman-2006-reconfigurations]] |
| Bandura (2001) | red-link | (no source page — cited-via in REFERENCES) |
| ... | ... | ... |

### Edits applied
- Frontmatter: `sources:` list grew from <a> to <b>; `grounding_status: retrofit <date>` added
- Wikilinks inserted: <n>
- Grounding footer appended (<n> rows)

### Red-link candidates
<list with proposed disposition: "read-directly needed", "ad-hoc stub", "ambiguous — ask user">

### Verification
- [ ] Frontmatter valid
- [ ] All new wikilinks resolve
- [ ] No prose deleted or reordered (diff shows citation-span substitutions only)
- [ ] Footer matches frontmatter
```

## What you do NOT do

- **Do NOT rewrite the page.** No reordering sections, no consolidating paragraphs, no "improving" prose. The skill is surgical.
- **Do NOT invent source pages.** Red-links are reported, not created. Creating source pages is SK-15's job.
- **Do NOT fabricate claims.** If the page asserts a claim without a citation nearby, do not invent one. Flag it as `ungrounded-claim` in the report and leave the prose untouched.
- **Do NOT replace already-wikilinked citations.** A citation like `[[sources/chung-2026-redistributing|chung-2026-redistributing]]` is already grounded; skip it.
- **Do NOT propagate edits to other concept pages.** Each invocation handles one page; cross-page consistency is a separate audit.
- **Do NOT upgrade `grounding_status: stub` to `full`.** Only a direct-read pass does that; this skill only touches the concept page's status, not the source page's.

## Regeneration behavior

If invoked a second time on the same page after SK-15 has added more source stubs, the skill re-inventories and retrofits only the *new* resolvable citations. Existing wikilinks are preserved. The `grounding_status` date is updated.

## Notes on tier and scope

Package-tier skill. Applies to any concept page in `LLM wiki/wiki/concepts/` following the wiki's standard schema. The G/P/L/D classification used by SK-14 does not apply here; concept grounding is uniformly surgical.

## Failure modes (v0.10.0-S4.5 R1)

This section documents Phase 4.5's partial-failure semantics. The contract is **single-source-of-truth here** — no phase-runner Step reads it; no Planner phase dispatches Phase 4.5 (it is invoked inline as part of SK-16's own procedure).

**FM-1 — SK-NEW-C dispatch failure on individual red-link.**
*Cause:* SK-NEW-C errors during its Phase 1/2/3 (e.g., `WRITE_FAILURE`, `EXTERNAL_VERIFIER_UNREACHABLE`, anchor selection no-op, `INSUFFICIENT_SEEDS_AFTER_PHASE`).
*Semantics:* **skip-and-continue.** The failed red-link is logged in `reviews/snowball_log.md` with the failure reason; processing advances to the next red-link in the queue. No `W-` or `E-` code is emitted per failure (the snowball log is the audit trail; aggregate failures surface in the Phase 4.5 closing summary appended to the SK-16 report).
*Rationale:* red-link auto-trigger is a wiki-collaboration accelerant per architecture §5.5.4, not a gating signal. Halting on individual failures would be inconsistent with the bounded-batch nature of SK-16's round and would penalise concept-page grounding for unrelated SK-NEW-C errors. The skip-and-continue contract was adopted at S4.5 R1 as the formal halt-vs-continue resolution for the §6.0 row-4 surface (per `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §6.0` closing-sentence revision and §6.6 R1 deliverable enumeration).

**FM-2 — Cap saturation.**
*Cause:* The red-link queue size exceeds `red_link_cap_per_round`.
*Semantics:* the first `red_link_cap_per_round` red-links are dispatched in document order; the remainder are deferred (logged as `deferred_redlink_at_sk16` candidates in the round's snowball-log row) and a `W-REDLINK-CAP-SATURATED` warning is emitted per `references/phase_notifications.yaml redlink_cap_saturated`.
*Rationale:* per architecture R-12 (rate-limit mitigation), the cap prevents Scholar Gateway flood from a single concept-page sweep that produces a long red-link list. Excess candidates are not lost — they are explicitly recorded and surfaced for user re-prioritisation at round close.

**FM-3 — Classification.md missing or unparseable at gate-check.**
*Cause:* `reviews/classification.md` does not exist or fails YAML parse.
*Semantics:* Phase 4.5 silently no-ops (treated as `auto_redlink_snowball: false`). The Phase 4 red-link report stands unchanged; no `W-` code is emitted on no-op.
*Rationale:* projects without a parseable classification.md are incompletely bootstrapped; auto-trigger gates default to off in this state to avoid surprise behaviour for users who have not yet adopted the v0.10.0 wiki-collaboration features.

**FM-4 — `wiki_linked: false` project.**
*Cause:* The project's `classification.md` declares `wiki_linked: false` (no LLM wiki integration).
*Semantics:* Phase 4.5 silently no-ops. The Phase 4 red-link report stands.
*Rationale:* wiki-collaboration accelerants apply only to wiki-linked projects; the gate prevents misuse on projects that have no wiki to write back to. Red-links from non-wiki-linked projects cannot resolve via SK-NEW-C extend (no `wiki/sources/` to populate), so the auto-trigger has no productive use.

**FM-5 — Concurrent SK-NEW-C dispatch over shared `references/REFERENCES.md`.**
*Cause:* SK-16's Phase 4.5 invoked concurrently with another skill that writes REFERENCES.md (e.g., a parallel `run-phase-2 Step 0.5` → SK-NEW-C dispatch under the S4-landed auto-dispatch graph).
*Semantics:* SK-NEW-C's existing atomic-rename contract (per architecture §5.5.2 / the existing SK-15 lock pattern) handles serialisation. Phase 4.5 inherits this contract — no separate locking is required at the SK-16 layer.
*Rationale:* SK-NEW-C is the canonical writer for snowball-driven REFERENCES.md extensions; SK-16's Phase 4.5 is a dispatch caller, not a direct writer. Layering writers would violate the single-writer convention encoded at `references/phase_state_schema.md §5`.

**FM-6 — Empty red-link queue after Phase 4.**
*Cause:* Phase 4 produced no red-link candidates (every cited author-year resolved to an existing `wiki/sources/<key>.md` page).
*Semantics:* Phase 4.5 silently no-ops. The Phase 4 report is unchanged.
*Rationale:* this is the desired terminal state — full grounding coverage. No `W-` code or log entry is needed.

## Sibling skills

- **Upstream:** SK-15 `backfill-source-stubs-from-references` — populates the source layer this skill depends on.
- **Downstream (added v0.10.0-S4.5 R1):** SK-NEW-C `extend-snowball-incremental` (SK-35) — auto-dispatched from Phase 4.5 on red-link candidates when `auto_redlink_snowball: true` AND `wiki_linked: true` in `reviews/classification.md`. Capped at `red_link_cap_per_round` (default 5) per round; excess red-links logged as deferred-discovery candidates and surfaced via `W-REDLINK-CAP-SATURATED` warning. See §3 Phase 4.5 and §Failure modes above.
- **Downstream (still TBD):** synthesis-level audit (cross-page consistency); SK-17 candidate, TBD per the original v0.7.0 sibling-skill register.
