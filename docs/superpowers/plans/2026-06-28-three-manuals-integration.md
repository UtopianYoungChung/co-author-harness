# Integration Plan — Turabian, Abbott (*Digital Paper*), and the Blue Book into the Co-Author-Harness

**Author:** Research-writing harness maintainer pass, 2026-06-28
**Status:** Plan + first implementation (Blue Book wired end-to-end; Turabian and Abbott specified for follow-on PRs)
**Scope governed by:** `CLAUDE.md` (root), `references/SKILL_REGISTRY.md`, `references/SAFEGUARD_LAYER.md`, `references/DETERMINISTIC_CHECKS.md`, `references/AGENT_CONTRACTS.md`, `references/MASTER_research_and_paper_guidelines.md`.

---

## 1. Problem statement

The harness already absorbs external writing authorities through a stable, repeated pattern: each named source becomes a distilled `references/<author>_<year>_guidelines.md` file, is registered in `SKILL_REGISTRY.md`, and — where it licenses a recurring operation — is paired with an invocable judgment skill (Bacon → `sentence-level-pass`, Sexton → `narrative-structure-pass`, Baird → `IS-theory-pass`, Suchman → `suchman-register-audit`, Eubanks → `public-interest-accountability-pass`). Three new manuals were supplied for absorption:

1. **Turabian, *A Manual for Writers of Research Papers, Theses, and Dissertations* (Chicago for students).** Three-part structure: Part I research-and-writing process; Part II source citation (notes-bibliography *and* author-date); Part III mechanical style (spelling, punctuation, names, numbers, abbreviations, quotations, tables/figures); Appendix paper format/submission.
2. **Abbott, *Digital Paper: A Manual for Research and Writing with Library and Internet Materials*.** A *process* manual: library ethnography, the preliminary/mid/endphase model, bibliography, scanning/browsing, reading, file organization, analysis, design.
3. **Kaufman & Straus, *The Blue Book of Grammar and Punctuation*.** A *mechanics* manual: grammar (subject–verb agreement, who/whom, that/which, modifiers), punctuation (commas incl. Oxford, semicolons, colons, apostrophes, hyphens, dashes), capitalization, number style, and a confusing-words/homonyms glossary.

The three do not collapse into one harness layer. Each lands in a *different* substrate, and treating them uniformly (e.g., as three more prose-craft passes) would mis-place two of the three. The design problem is therefore a **routing** problem: map each manual to the harness layer whose contract it actually extends, and wire it at full SAFEGUARD/agent depth without duplicating an existing surface.

## 2. Theoretical framing — the harness's source-absorption pattern as a fixed point

The existing five-source precedent fixes the integration template. Every absorbed source occupies a position on two axes:

- **Read-surface** — a `references/*_guidelines.md` distillation that agents read before acting (the universal floor; all five precedents have one).
- **Operation-surface** — *zero or one* invocable skill, *plus* a binding hook in one or more of: `DETERMINISTIC_CHECKS.md` (mechanical/regex-detectable), `SAFEGUARD_LAYER.md` Check 8 (judgment/reader-experience), `AGENT_CONTRACTS.md` (Generator read-before-write, Evaluator step reference), `MASTER_research_and_paper_guidelines.md` (precedence-bearing rule statement).

The trade-off the harness already encodes: a source becomes an *operation* only where it licenses a recurring, decidable check; otherwise it stays a read-surface to avoid surface bloat (cf. Sub-check H being "overlay-internal, no SKILL_REGISTRY entry" where a standalone skill was not warranted). The three manuals are placed against this template below.

## 3. Routing decision — which manual extends which layer

| Manual | Primary layer | Operation-surface | Rationale (and what it must *not* duplicate) |
|---|---|---|---|
| **Blue Book** | `DETERMINISTIC_CHECKS.md` (mechanical) **+** new judgment skill | `grammar-mechanics-pass` skill; new `DETERMINISTIC_CHECKS` mechanical subsection; Generator/Evaluator hooks | Grammar/punctuation correctness is decidable and partly regex-detectable — the deterministic home. The judgment residue (subject–verb agreement across intervening phrases, that/which restrictiveness, comma-splice vs. intended semicolon) needs a craft pass. Must **not** duplicate `sentence-level-pass` (Bacon = rhetoric/rhythm, not correctness) nor `EMDASH_BUNDLE_DISCIPLINE.md` (already owns em-dash policy — the new pass defers to it). |
| **Turabian** | `CITATION_DISCIPLINE.md` + `STYLE_COMMITMENTS.md` + paper-format reference | `citation-format-pass` skill (style-conformance, not the *when-to-cite* judgment); new `references/turabian_chicago_guidelines.md`; hook into Evaluator Step 4 (citation precision) | Turabian Part II is the **format** of citations; `CITATION_DISCIPLINE.md` already owns the **engagement-vs-demarcation judgment**. The two are orthogonal and must stay so. Part III mechanics overlap the Blue Book — reconciled in §6. |
| **Abbott** | Research-*process* docs: `PROJECT_BOOTSTRAP.md`, `seed-snowball-discovery`, Planner contract, file-organization conventions | **No new prose skill.** New `references/abbott_2014_research_process_guidelines.md`; hooks into Planner pre-draft checklist and the snowball/bibliography phase | *Digital Paper* governs the pre-writing research lifecycle, not sentence or citation surface. Forcing it into a prose pass would mis-file it. It extends the Planner's discovery/organization contract — the phase the harness currently under-documents relative to drafting. |

## 4. First implementation (this PR) — Blue Book end-to-end

Chosen as the worked exemplar because it is the cleanest full-wiring case: a decidable domain, a natural deterministic home, a non-overlapping judgment skill, and a clear severity story. Files created/edited:

1. **`references/blue_book_grammar_guidelines.md`** (new) — distilled, grounded guideline mirroring `bacon_2009_*`. Sections: grammar (subject/verb finding, S–V agreement, who/whom, that/which restrictive/nonrestrictive, adjective/adverb, prepositions), punctuation (Oxford comma, comma with coordinate adjectives, semicolon three rules, colon, apostrophe/possessive, hyphenated compound modifiers + suspended hyphens, dashes deferring to em-dash discipline), capitalization, number style, confusing-words pointer. Carries a "Raw extraction" pointer to `references/resources/blue_book_grammar_extract.txt` and an academic-register scoping note (what to enforce in scholarly prose vs. what is venue-deferred).
2. **`references/resources/blue_book_grammar_extract.txt`** (new) — raw text extraction of the rule chapters (grounding substrate).
3. **`skills/grammar-mechanics-pass/SKILL.md`** (new, SK-40) — Phase 1 mechanical scan (regex-detectable: it's/its, comma-splice candidates, that/which, missing Oxford comma in series, compound-modifier hyphenation, number-style); Phase 2 judgment pass (agreement across intervening phrases, restrictiveness, colon/semicolon licensing); Phase 3 findings block. Explicit non-overlap clauses with `sentence-level-pass`, `EMDASH_BUNDLE_DISCIPLINE.md`, and DETERMINISTIC_CHECKS.
4. **`skills/plugin-commands/SKILL.md`** (edit) — add `/grammar-mechanics-pass` catalog row (required by `skill-check.py` /plugin-commands parity).
5. **`references/SKILL_REGISTRY.md`** (edit) — add `### SK-40. \`grammar-mechanics-pass\`` (required by `skill-check.py` registry parity).
6. **`references/DETERMINISTIC_CHECKS.md`** (edit) — add a mechanical-grammar subsection feeding the pass's Phase-1 work queue (the deterministic wiring).
7. **`references/AGENT_CONTRACTS.md`** (edit) — Generator invariant: read the Blue Book guideline before any mechanical/copyedit fix; Evaluator: reference the guideline at the copyedit step.

**Deliberately deferred to the gated release step (not in this PR):** the `plugin.json` version bump (0.16.0 → 0.17.0), the `CHANGELOG.md` entry, `README.md` skill-count, and `marketplace.json`/`ssot.yaml` updates. These are governed by `scripts/release-gate.sh` and `version-check.py`/`catalog-check.py`, which require coordinated, single-commit edits. Bumping the manifest mid-implementation would red the version-coherence checks. The additive content above keeps all five structural checks green at the current version; the version ceremony is the explicit final gate (§7).

## 5. Follow-on PRs — Turabian and Abbott

**PR-2 (Turabian).** Create `references/turabian_chicago_guidelines.md` distilling Parts II–III + Appendix; add `citation-format-pass` skill (SK-41) for author-date/notes-bibliography *form* conformance, reference-list ordering, and ibid./short-form discipline; wire into Evaluator Step 4 alongside `CITATION_DISCIPLINE.md` with an explicit boundary note (`CITATION_DISCIPLINE` = whether to cite; `turabian` = how the cite is formatted). Add a paper-format checklist to `STYLE_COMMITMENTS.md`. Resolve the Part III ↔ Blue Book mechanics overlap per §6.

**PR-3 (Abbott).** Create `references/abbott_2014_research_process_guidelines.md` distilling the preliminary/mid/endphase model, bibliography-building, scanning/browsing/brute-force search, reading-for-engagement, and file organization; wire into `PROJECT_BOOTSTRAP.md` (a pre-draft research-readiness checklist) and the `seed-snowball-discovery` / Planner contract (Abbott's bibliography and brute-force-search heuristics complement the Wohlin snowball). No new skill — process guidance is read-surface for the Planner.

## 6. Conflict reconciliation — Blue Book ↔ Turabian Part III

Both manuals legislate mechanical style (punctuation, numbers, hyphenation), and they occasionally differ (e.g., serial-comma framing, number-spelling thresholds). The harness needs one authority per decidable item to avoid an arbitrary surface (the same discipline-coherence rationale `CITATION_DISCIPLINE.md §3` invokes). Resolution: **Turabian/Chicago is the precedence authority for any item where the target venue is Chicago/Turabian-styled; the Blue Book is the default authority for general academic mechanics and the source of the *judgment* heuristics (agreement, restrictiveness) that Turabian states more tersely.** The `grammar-mechanics-pass` reads both guideline files and defers to the project's declared style (`directives.md` `citation_style` field) on any conflict, flagging the conflict rather than silently picking. This is documented in both guideline files' "Precedence and conflicts" section when PR-2 lands.

## 7. Sequencing, gating, and verification

1. **This PR (done):** create files 1–7 of §4; run `skill-check.py`, `version-check.py`, `catalog-check.py`, `path-hygiene-check.py`, `snippet-check.py` — all must stay at 0 blockers.
2. **PR-2 / PR-3:** repeat the §4 pattern for Turabian and Abbott; each keeps the five checks green at the unchanged version.
3. **Release gate (final, single commit):** bump `plugin.json` to 0.17.0; add the CHANGELOG entry enumerating SK-40 (and SK-41 if Turabian lands together); update README skill count and `marketplace.json`/`ssot.yaml`; run `bash scripts/release-gate.sh --build`. Only here does the version surface move.
4. **Reflection:** run `/run-reflection` to record the integration as a lesson and let the Reflector audit grounding on the new guideline files (every quoted rule must trace to the raw extract).

## 8. Risks and trade-offs

- **Surface bloat.** Three manuals could add three skills + multiple hooks. Mitigation: Abbott gets *no* skill (read-surface only); Turabian gets one format skill, not a second citation-judgment skill. Net new invocable skills ≤ 2.
- **Mechanics double-authority (Blue Book vs. Turabian Part III).** Mitigated by the precedence rule in §6 (declared-style defers; conflicts are flagged, not silently resolved).
- **Grounding integrity.** Guideline files must not paraphrase rules into inaccuracy. Mitigation: raw extract committed alongside; Reflector grounding audit in §7.4; guideline files carry the "not a substitute for the source" disclaimer the Bacon file uses.
- **Version-coherence breakage.** Mitigated by deferring the manifest bump to the single gated release commit (§4 deferred list, §7.3).
