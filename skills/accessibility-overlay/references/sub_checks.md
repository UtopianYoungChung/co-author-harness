# Sub-checks A–G — threshold values, severity floors, detection procedures

> **Loaded by** `SKILL.md` at the Sub-check dispatch step. This file is the authoritative specification of the seven Sub-checks; the SKILL.md body routes and aggregates, this file defines. All threshold numerics (word counts, σ cut-offs, term caps, accumulation thresholds) and severity floors live here to keep the SKILL.md body routing-focused.

---

Each Sub-check maps to one finding class. The Evaluator's native finding shape is preserved: every finding carries `id`, `sub_check` (A–G), `severity` (MINOR / MAJOR / BLOCKER), `location` (heading_path + line range for A–F; structural-boundary locator such as `end_of_§3` or `pivot_§5.2` for G), `rule_citation` (`SAFEGUARD_LAYER.md §Check 8 Sub-check X` plus `Ph.D.-root CLAUDE.md §13.3 (criterion)`), `evidence` (the offending span, the measured value, or — for G — the named structural boundary with its accumulated-construct count), `suggested_fix` (a one-to-two-sentence action the Generator can act on), and `source_tag: accessibility-overlay@v1.1` so Reflector Phase 2g can trace recurrence.

## Sub-check A — Paragraph cadence (Cadence-Flag)

Scan every paragraph in the section. A paragraph is **flagged** if it exceeds 150 words **and** contains no internal turn-point (transition cue, worked example, counter-claim, or thematic refocus). Turn-points are detected via a small cue lexicon: `however`, `but`, `yet`, `still`, `by contrast`, `conversely`, `suppose`, `for example`, `to illustrate`, `consider`, `take the case of`, `reframing`, `which is to say`, `put differently`. A paragraph that spans a single argumentative move and exceeds 200 words is flagged independently of turn-point presence.

Severity floors: MINOR if 151–200 words without turn-point; MAJOR if >200 words with or without turn-point; BLOCKER if >300 words with no turn-point and no sentence break signals (em-dash, colon, semicolon) — this pattern is the "wall of prose" that the constraint most directly targets.

## Sub-check B — Sentence-length distribution (Rhythm-Flag)

Compute per-paragraph sentence-length mean (μ) and standard deviation (σ). A paragraph is **flagged** if μ > 28 and σ < 6 — the monotone-dense pattern. Paragraphs of three sentences or fewer are exempt (insufficient sample for σ). The flag also surfaces a "no short sentences" warning when the paragraph's shortest sentence exceeds 20 words — rhythm depends on contrast, not merely on average length.

Severity floors: MINOR on any single flagged paragraph; MAJOR if two or more adjacent paragraphs trip the same flag (a monotone-dense stretch); never BLOCKER alone (rhythm is a diffuse property; BLOCKER is reserved for A, D, F).

## Sub-check C — First-use definition (First-Use-Flag)

Enumerate theoretical and domain constructs introduced in the section (a construct is any italicized term, any term tagged in the project's `research_notes/glossary.md` if present, or any term appearing in `references/terminology_register.md`). For each construct, locate its first occurrence in the section and verify a definition or worked illustration appears within the same paragraph or the immediately preceding paragraph. This is binding even for terms the author considers field-standard: `affordance`, `operationalization`, `socio-technical`, `intentionality`, `delegation`, `situated action`, `contradiction-mapping`.

Severity floors: MINOR per undefined construct (author can argue field-standardness); MAJOR if two or more undefined constructs appear in the same paragraph; BLOCKER if an undefined construct does conceptual work (is cited, contrasted, or built upon) in a subsequent paragraph without ever being defined.

## Sub-check D — Section-transition signposting (Signpost-Flag)

Every section in the manuscript opens with a one-to-three-sentence preamble that (a) tells the reader where they have arrived in the argument and (b) tells the reader what the section will contribute. This is not a chapter summary and not a prose abstract; it is a map fragment. The overlay checks the section's opening paragraph against a minimal signpost schema: an orienting clause (claim about position in the argument) AND a contribution clause (claim about what follows). A section lacking either clause is flagged.

Severity floors: MINOR if one of the two clauses is present but weak; MAJOR if the opening paragraph is substantive prose with no orienting or contribution clauses at all; BLOCKER if the section dives directly into a dense theoretical move without any orienting sentence — this pattern is the "cold-open" the constraint most directly forbids.

## Sub-check E — Jargon discipline within paragraphs (Jargon-Density-Flag)

Count new domain terms introduced per paragraph. A paragraph may introduce at most two new domain terms (a term is "new" if it has not been introduced earlier in the section or in a preceding section marked as its entry point in `references/terminology_register.md`). P-stage adjustment: P0 permits three (exploratory register); P2 permits one only (resolution register tolerates no ambiguity).

Severity floors: MINOR on any paragraph that exceeds the P-stage cap by one term; MAJOR on any paragraph that exceeds the cap by two or more terms; never BLOCKER alone.

## Sub-check F — Worked examples at density spikes (Worked-Example-Flag)

Detect density spikes: a tri-part decomposition, a multi-criteria evaluation, a contested-claim cluster (three or more cited positions with conflicting commitments), or an extended theoretical derivation. For each density spike, verify that the prose turns to a worked example, a vignette, or a concrete instantiation within the same or immediately following paragraph. The INF3001H loan-officer vignette is the canonical model; the INF3006Y three-positions map (Decomposition / Dissolution / Reframing) expects its own instantiation per position.

Severity floors: MINOR if a density spike is followed by a gestural example (a phrase, not a vignette); MAJOR if a density spike is followed by further abstract prose; BLOCKER if a density spike exceeds one full page of abstract prose with no instantiation — this is the pattern the constraint names as "density without cadence."

## Sub-check G — Cumulative cognitive load / consolidation anchors (Consolidation-Anchor-Flag)

**Scope.** Full manuscript only. If the overlay is invoked with a section `heading_path` rather than a `scope: full_manuscript` directive, Sub-check G does not run and the overlay emits the `G_REQUIRES_FULL_MANUSCRIPT` noop reason code (per Precondition 2).

**Procedure.**

1. **Enumerate structural boundaries.** Read the manuscript outline (major sections, labelled subsections, and argumentative pivots) and build a boundary inventory. A boundary is any of: (i) the closing paragraph of a major section followed by a new major section; (ii) a labelled pivot within a section (e.g., a subsection that relocates the argument from description to stance); (iii) the opening of any section whose argument depends on constructs from two or more prior sections. If the project carries a `research_notes/directives.md` entry naming explicit structural boundaries (e.g., INF3006Y D-13 names the end of Sec. 3, the Sec. 5 pivot, and the Sec. 6 opening), use the project list and extend only if the Evaluator detects additional argument-dependency boundaries the project list does not cover.
2. **Measure construct accumulation between boundaries.** For each span between consecutive boundaries (or between the manuscript opening and the first boundary), count distinct load-bearing constructs, positions, or tensions introduced — where load-bearing is defined as in `SAFEGUARD_LAYER.md` Check 8 Sub-check G procedure step 2.
3. **Apply the construct-accumulation threshold.** A boundary crosses the threshold when the prior spans have introduced three or more load-bearing constructs, or when the next section's argument depends on two or more prior sections' material.
4. **Check for consolidation anchors.** For each threshold-crossing boundary, read the paragraph preceding the boundary, the paragraph opening the next section, and any labelled transition between them. Verify a one-sentence consolidation anchor exists. The canonical anchor form is "At this point in the paper, [the reader holds X, Y, Z]; the next movement [does W with them]," but any sentence performing both the naming-of-accumulated-material and the signalling-of-next-move functions qualifies.
5. **Flag missed boundaries.** For each threshold-crossing boundary lacking an anchor, emit a Sub-check G finding with a structural-boundary locator (e.g., `end_§3`, `pivot_§5.2`, `opening_§6`), the construct count at that point, and the absence description. The `suggested_fix` field names the canonical anchor form and points to any adjacent paragraphs where insertion would least disrupt the surrounding register (per project directives, e.g., D-06's Vidal-cartographer register for INF3006Y).
6. **Word-count envelope.** On a manuscript under ~3,000 words, emit CLEAN by default unless an explicit construct-dependency boundary is still unserved. On a manuscript over ~5,000 words with no consolidation anchors at any threshold-crossing boundary, emit the absence-of-anchors BLOCKER regardless of per-boundary construct counts.

**Severity floors:**

- **MINOR** — exactly one threshold-crossing boundary lacks an anchor and the manuscript word count is under 5,000.
- **MAJOR** — two or more threshold-crossing boundaries lack anchors, or a single missed boundary is located at the transition into the manuscript's closing argumentative move (where cumulative load is highest).
- **BLOCKER** — a manuscript beyond ~5,000 words contains no consolidation anchors at any threshold-crossing boundary, or a missed boundary directly precedes a section whose argument is specified in the abstract and depends on three or more prior-section constructs.

**Interaction with Sub-check D.** D and G are orthogonal and additive. D audits local section-opening preambles; G audits cumulative anchor placement at structural boundaries. A section opening can satisfy D while omitting the G anchor, and vice versa. When a Generator is applying a fix, D-targeting preambles and G-targeting anchors can co-locate in the same paragraph, but the two sentences should do distinct work.

**Advisory-until transitional flag.** Sub-check G carries an `advisory_until: next_manuscript_at_ph3` flag per `READER_ACCESSIBILITY.md §13.5`. Under the flag, G findings are emitted with severity and locators recorded, but the aggregate-verdict computation in the next section treats G findings as advisory: the `advisory_until_flag_active: true` output field tells the Planner to compute the TerminalSignoffRow decision on the A–F aggregate alone. The flag retires automatically on the first Ph3 entry of a manuscript whose Ph1 classification postdates 2026-04-23.

**Stability sub-mode.** Under `run-phase-3-stability` (v0.8.0+ byte-stable inheritance pass), Sub-check G runs advisory-only regardless of the `advisory_until` flag. A G finding under stability mode is logged with `stability_advisory: true` and does not force escalation to a full Ph3 pass. The rationale is that G is judgment-heavy and its findings are not cheaply re-derivable from a byte-stable snapshot; a stability pass that fired a G BLOCKER would either require a full-Ph3 escalation on every round (expensive) or would need a hash-summary caching layer not yet specified. The advisory path lets the reduced stability pass run cheaply while preserving G's recurrence trail through Reflector Phase 2g.
