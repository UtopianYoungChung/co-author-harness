---
name: ingest-m5-to-wiki
description: Ingest an M5 (submission-bound final) paper into the LLM wiki as a full source page, materializing Coupling D — the project's final artefact becomes a first-class, wikilinked entry in the research knowledge graph.
trigger: when the user asks to ingest an M5 paper into the wiki, close out a project with a wiki source entry, materialize Coupling D, or finalize the wiki record for a completed manuscript after G.4 sign-off
created_by: Reflector (Coupling D formalization)
created_from: Research↔Wiki diagnostic audit, 2026-04-13 — Finding F6 (M5 final paper is a natural wiki source, not just a review artefact); Coupling D registered at bootstrap in PROJECT_BOOTSTRAP.md §3 Step 5; skill formalized 2026-04-13 following completion of SK-14/15/16 chain
pattern_source: PROJECT_BOOTSTRAP.md §3 Step 5 + §4 Four Couplings table; LLM wiki/CLAUDE.md §Operations/Ingest; AGENT_ORCHESTRATION.md §8.5 (Coupling C) — SK-17 is the M5-timed analogue
version: 1.0
---

# Ingest M5 to Wiki

You are materializing **Coupling D** — the final Research→Wiki hook in the four-coupling synergy program. This skill converts a project's submission-bound M5 manuscript into a complete (non-stub) source page in the peer `LLM wiki/wiki/sources/` directory, with full bibliographic metadata, a structured claim summary, and inbound wikilinks from every concept the paper grounds.

Unlike SK-15, which populates *stub* source pages from a REFERENCES table (where the agent has not read the paper), this skill assumes the paper has been read directly and repeatedly by every agent in the M5 loop. The resulting page therefore carries `grounding_status: full` from creation.

## Preconditions

Before invoking this skill, verify all of the following. Abort with a clear error if any fails.

1. **Project is at M5.** The project has `reviews/G4_signoff.md` present and marked complete, OR the user has explicitly confirmed the manuscript is submission-bound.
2. **Wiki exists.** The path `LLM wiki/wiki/` is reachable, with subfolders `sources/`, `concepts/`, `entities/`, `syntheses/`, and files `index.md` + `log.md`.
3. **Project CLAUDE.md declares wiki linkage.** The project CLAUDE.md contains a `## Wiki linkage (Coupling D)` section (per PROJECT_BOOTSTRAP.md §3 Step 5) with `wiki_linked: true` and `coupling_d_on_m5: true`. If absent, ask the user whether to proceed anyway and retroactively record the linkage.
4. **Projected wiki-key is resolvable.** Either the project's CLAUDE.md carries a `projected_wiki_key` field, or the manuscript has final author/year/keyword information from which a key can be constructed per `LLM wiki/CLAUDE.md §Source Keys` (`<first-author>-<year>-<keyword>`). If the projected key has a `-draft` suffix, finalize it by dropping the suffix — the M5 version is no longer a draft.
5. **No prior non-stub ingestion.** Check `LLM wiki/wiki/sources/<key>.md`. If a page exists with `grounding_status: full`, stop and ask the user whether this is a revision (update in place) or a different paper (new key).

## What you do

### Phase 1 — Read the final manuscript

1. Read `manuscript/main.md` (or `main.tex`) in full — every section, every table, every figure caption. You are producing a source summary that downstream agents will treat as authoritative; partial reads produce stub-quality pages.
2. Read `reviews/G4_signoff.md` for the final classification: paper type, venue, P-stage-at-submission, depth.
3. Read `research_notes/project_memo.md` (M1 artefact) for the original intentionality and tension framing — this gives the "Why this source matters" paragraph its seed.
4. Read `research_notes/annotated_references.md` (M2 artefact) to identify which entities, prior works, and concepts the paper engages. These become the wikilink targets.
5. Read any existing `LLM wiki/wiki/sources/<key>.md` (if the user is overwriting a stub or draft) so you preserve fields the stub got right and only replace what the full read changes.

### Phase 2 — Resolve bibliographic fields

Construct the source page frontmatter and bibliographic table using **only** information present in the manuscript, G4_signoff, or project CLAUDE.md. Never invent. Fields required:

| Field | Source | Notes |
|---|---|---|
| `source_key` | `projected_wiki_key` in project CLAUDE.md, drop any `-draft` suffix | If absent, derive from manuscript title page |
| Authors | Manuscript title page | Preserve order; use "et al." only if the author line does |
| Year | Submission year from G4_signoff, else manuscript front matter | |
| Venue | G4_signoff classification | If still TBD, mark `(under submission — venue TBD)` and flag for later patch |
| DOI | Manuscript or submission receipt | Absent-is-fine; do not fabricate |
| PDF / source path | Research-relative path to `manuscript/main.md` (or compiled PDF if available) | |

### Phase 3 — Structured claim summary

Write a source summary with these sections, in this order:

1. **Why this source matters** (1–2 paragraphs, scholar-cartographer register per suchman_writing_style.md — not promotional, not self-congratulatory; state the tension the paper addresses and the move it makes). Derived from M1 project memo and the manuscript's introduction.
2. **Key claims** (numbered list, 3–7 items). Each claim is a load-bearing thesis the paper actually argues, with a brief `— §X.Y` section reference. No inferred claims; no "the authors probably mean" — only what the manuscript states.
3. **Method / apparatus** (short paragraph). What instruments the paper uses (i* modeling, process mining, case study, argument analysis, etc.). This lets future concept-grounding retrofits cite the paper on methodological grounds.
4. **Relationship to the research program** (short paragraph). How this paper connects to other sources already in the wiki — which concepts it anchors, which prior sources it extends, which tensions it inherits from earlier work.
5. **Limitations & open threads** (bullet list). Taken from the manuscript's own discussion/conclusion, not imposed. If the manuscript flags a scope limitation or a "future work" item, record it verbatim-or-paraphrased here. This is what makes the page useful to the *next* project.

### Phase 4 — Wikilink harvesting

1. List every concept page in `LLM wiki/wiki/concepts/` and decide which ones the paper actively grounds. A page is "actively grounded" if the paper makes a claim the concept page should cite, not merely touches the topic. Err on the side of under-linking — every wikilink is a commitment the concept page must honor.
2. List every entity page the paper invokes (authors, organizations, systems, venues). Create new entity pages only if the entity is invoked in a load-bearing way and has no existing page. Do not create entity pages for every co-author.
3. For each concept/entity, add a row to the page's "Inbound references (wiki)" section at the bottom of the source page. Format: `- [[concepts/<name>]] — <one-line role>`.
4. **Do not edit the concept pages themselves inside this skill.** Concept-page retrofits are SK-16's job. Record the concept-page edits that *should* happen as a follow-on batch and present them to the user at the end.

### Phase 5 — Write the source page

Create `LLM wiki/wiki/sources/<key>.md` with this frontmatter:

```yaml
---
type: source
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [<from manuscript's domain — re, istar, haic, etc.>]
source_key: <key>
grounding_status: full — ingested from M5 manuscript on YYYY-MM-DD via SK-17 (Coupling D)
---
```

Body follows the section order specified in Phase 3, followed by the bibliographic table, followed by the Inbound references (wiki) and Inbound references (Research/) sections. Mirror the style of existing full-read source pages (e.g. `sources/chung-2026-identity-req.md`), not the stub pages from SK-15.

### Phase 6 — Update index and log

1. Append a row to `LLM wiki/wiki/index.md` under `## Sources`, placed alphabetically by key. Mark as non-stub (no "(stub)" suffix).
2. Append a log entry to `LLM wiki/wiki/log.md` under the current date with operation `ingest | M5 — <short project name>`. Record: the source key, the projected concept-grounding follow-ons (for SK-16), the wiki corpus size pre/post.

### Phase 7 — Update project CLAUDE.md

Append a dated line to the project CLAUDE.md `## Wiki linkage (Coupling D)` section recording that ingestion fired: `- YYYY-MM-DD: Coupling D fired. Source page [[sources/<key>]] created. grounding_status: full.` This closes the project-side record of the coupling.

### Phase 8 — Verify and report

1. Open the created source page and verify: frontmatter parses, all wikilinks resolve (or are marked red-link explicitly), no TODO markers remain except intentional limitation flags.
2. Verify the index and log entries are in place.
3. Verify the project CLAUDE.md received the closing line.
4. Produce a final report listing: the source page path, the corpus-size delta, the concept-page follow-on batch (pages that should be retrofitted via SK-16 to cite the new source), and any red-link candidates the new page invokes.

### Phase 9 — First-deployment manual-upgrade trigger (one-time)

**This phase fires only on the *first* invocation of SK-17 in the workspace.** Check `DRIFT_LOG.md` or `LLM wiki/wiki/log.md`: if no prior `skill | SK-17` or `ingest | M5` entry exists for SK-17, this is the first run. On first run:

1. After Phase 8 completes cleanly, surface a recommendation to the user: **"SK-17 has now been exercised once. Per the deferred scheduling recorded on 2026-04-13, this is the trigger for the heavier manual-upgrade pass — folding the synergy program into QUICKSTART.md and OPERATING_MANUAL.md proper, with actual-use experience replacing protocol speculation."**
2. Provide a concrete checklist the user can approve or defer:
   - Update OPERATING_MANUAL.md §7.5 to reflect observed behavior (timings, edge cases encountered, any deviations from protocol the skill exhibited under real load).
   - Update QUICKSTART.md's "Wiki-facing couplings" section if the flag semantics or invocation triggers differ from what was specified pre-deployment.
   - Add a new §4.8 "M5 wiki ingestion" subsection to OPERATING_MANUAL.md alongside the existing phase subsections, if SK-17 proves heavyweight enough to warrant first-class operational treatment.
   - Consider promoting SK-17's regeneration-behavior rules into the Ship (M5) phase description in §4.6.
3. Record the trigger-fire in `DRIFT_LOG.md` (so the first-run trigger is not re-fired on subsequent SK-17 invocations) and in the completion-report synthesis (update the §"Next work" item).

This phase is a one-time affordance, not a recurring check. After first deployment, Phase 9 collapses into a no-op and SK-17 terminates at Phase 8.

## What you do NOT do

1. **Do not rewrite the manuscript's claims.** The source page reports what the paper argues; it does not improve it, extend it, or second-guess it. Editorial intervention belongs in the Evaluator, not here.
2. **Do not edit concept pages.** Concept-page grounding retrofits are SK-16's responsibility. Even if a concept page obviously needs the new source, queue the edit — don't execute it.
3. **Do not edit the manuscript itself.** The manuscript is the source of truth. If Phase 1 reveals an error in the manuscript, flag it in the final report as a post-submission correction candidate; do not touch `manuscript/main.md`.
4. **Do not fabricate bibliographic fields.** If the venue is TBD, say TBD. If the DOI is absent, leave it absent. Stub-like gaps in a `grounding_status: full` page are acceptable; invention is not.
5. **Do not create duplicate source entries.** Re-ingestion is an update-in-place operation, not a new page.
6. **Do not fire Coupling C (SK-14) as a side-effect.** If the user wants a lessons synthesis at the same time, they invoke SK-14 separately. Keep the scope of SK-17 bounded.
7. **Do not run Coupling B (SK-16) as a side-effect.** Same rationale — SK-17 produces the source and queues the concept-page updates; the user decides when to burn the queue.

## Regeneration behavior

If `LLM wiki/wiki/sources/<key>.md` already exists:

- If it has `grounding_status: stub` — **overwrite**. SK-17 replaces stubs with full reads by design.
- If it has `grounding_status: full` and the manuscript has been revised (per project CLAUDE.md revision log) — **update in place**. Preserve the `created:` date, update the `updated:` date, revise the body to reflect the new version, and append a line to the Inbound references section noting the revision.
- If it has `grounding_status: full` and no revision is recorded — **ask the user** before overwriting. Something is unusual and the user should confirm the intent.

## Relationship to SK-14, SK-15, SK-16

SK-17 is the M5-timed closer of the four-coupling chain. Its outputs feed the other three skills in future rounds:

- **→ SK-16:** The concept-page follow-on batch produced in Phase 4 is the direct input to a subsequent SK-16 retrofit sweep that cites the new paper.
- **← SK-15:** If the new paper's references include sources absent from the wiki corpus, SK-17 flags them; the user runs SK-15 later against the paper's REFERENCES to backfill.
- **⊥ SK-14:** Independent. SK-14 promotes lessons; SK-17 promotes the paper itself. Both can fire in the same close-out round but neither depends on the other.
