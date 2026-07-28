# Skill Registry — Package-Level Skills



## Wiki write deferral (Research Truth Phase 0/1)

Coupling C/D canonical Wiki mutation is **unavailable**
(`reason_code: WIKI_WRITE_TRANSACTION_UNAVAILABLE`).

- Block only the Wiki mutation.
- Do **not** block Research completion, approval, or release.
- Project-local REFERENCES, lessons, reports, manuscripts, and reflection
  outputs continue normally.
- On deferral record: `status: deferred`,
  `reason_code: WIKI_WRITE_TRANSACTION_UNAVAILABLE`, `wiki_page_key: null`.
- Do **not** write `m5_wiki_ingest` as a success trigger and do **not**
  fabricate `wiki_page_key` or `lessons_promoted_to_wiki` success values.
- Automatic callers treat the deferred result as a visible non-blocking
  downstream deferral. Phase 4 / G.4 completion does not depend on Wiki write
  availability.

**Purpose.** Index of all skills created by the Reflector agent or manually added to the package. Each entry records the skill's name, what pattern it encodes, when it was created, and whether it has been deployed to a project or to the global skills directory.

**How skills work in this package.** Skills are `.md` files with frontmatter (name, description, trigger) and a body (the prompt that executes when invoked). They are user-invocable shortcuts that encode a recurring workflow, check, or fix pattern discovered during review rounds. The Reflector proposes skills; the Planner filters (three-filter gate); the user approves; the skill file is written.

---

## v0.7.0 vocabulary and surface-retirement banner

At v0.7.0 the tier system was reframed from the **Progressive Approval Staircase** (v0.6.0) to the **Lifecycle-Stage Ladder** (since renamed the **Lifecycle-Phase Ladder** at v0.7.4). Skill entries below retain their SK-NN identifiers but have been updated in place where v0.6.0 vocabulary no longer applies. The following surfaces are **retired** at v0.7.0 and must not appear in new or edited skill descriptions:

| Retired v0.6.0 surface | Status at v0.7.0 | Replacement or reason |
|---|---|---|
| Evaluator **Confirmation Mode** | Retired | Full-file reads are the universal floor; diff-backed shortcut is no longer recognized |
| Generator **Self-T1 Verdict** (Phase 3.5) | Retired | Drift measurement migrates into Phase 4 completion signal |
| **EG-2** (Self-T1 verdict mismatch gate) | Retired | No corresponding Verdict artifact to mismatch |
| **T3R sibling ladder** | Retired | Response-letter review folds into T3 Iterate & Converge as a manuscript-class |
| **Rule 1 tier-gated digest exception** | Retired | Single-code-path full-file grounding at every rung |
| **Laggard Clearance Report (LCR)** | Renamed | → **Manuscript Convergence Report (MCR)** |
| **T4_ready** (staircase approval state) | Renamed | → **T3_converged** (ladder convergence state) |
| `laggard_clearance_approved` flag | Renamed | → `mcr_admission` |

**Repurposed surfaces:**
- **EG-1** — now the T4→T3 grounding-demotion gate (was: T1 approval-on-drift; monotonicity-exempt).
- **EG-6** — degraded to a non-blocking advisory warning (was: T2 promotion-ceiling gate).

**Net-new surfaces at v0.7.0:**
- **EG-7** (`eg7_mcr_readmission_after_class_change`) — re-admission after classification change; monotonicity-exempt.
- **Reflector dispatch split** — lightweight mode (T1/T2/T3 ad-hoc integrity probe) vs. full mode (T4 close-out, five-phase).
- **Planner gatekeeper role** — three-filter review (evidence-adequacy / non-duplication / tier-appropriateness) on `reviews/plugin_update_proposals.md` before user sees proposals.

Every SK-NN entry below whose `Pattern` or `Depends on` line historically referenced a retired surface has been rewritten in place. The SK-NN identifier is preserved across the v0.6.0 → v0.7.0 transition; only the description and dependency text change.

**Skill locations (three tiers):**

| Tier | Path | Scope | When to use |
|---|---|---|---|
| **Package** | `.paper-package/skills/` | Any project using this package | Patterns that recur across multiple projects |
| **Project** | `<project>/.claude/skills/` or `<project>/skills/` | One specific project | Patterns specific to one project's domain or conventions |
| **Global** | `~/.claude/skills/` (i.e. `C:\Users\young\.claude\skills\`) | All Claude Code sessions | Patterns useful beyond academic writing |

The Reflector defaults to package-level. It escalates to global only when the pattern is clearly not academic-writing-specific. It narrows to project-level when the pattern depends on project-specific constructs.

**Protocol surface (not an SK-NN skill).** **Wiki-first resource order** — `EXTERNAL_VERIFIERS.md` §1.5; project field `wiki_first_resources` in `PROJECT_BOOTSTRAP.md` §3 Step 5; Generator invariant I-Gen-8 in `AGENT_CONTRACTS.md` §3. Closes the read loop: consult peer `LLM wiki/` before new Zotero PDFs and external search (e.g. Consensus) when choosing literature.

---

## Skill template

Every skill created by the Reflector follows this template:

```markdown
---
name: <skill-name>
description: <one-line description of what the skill does>
trigger: <when to invoke — e.g. "when the user asks to check contradictions">
created_by: Reflector
created_from: <reflection report reference — e.g. "Round 2 reflection, INF3006Y, 2026-04-09">
pattern_source: <the recurring pattern that motivated this skill>
version: 1.0
---

# <Skill Name>

<Full prompt that executes when the skill is invoked. Should be self-contained:
include what to read, what to check, what to output, and what NOT to do.>
```

---

## Active skills

**Current surface note (v0.14.0).** Active skills ship as `skills/<name>/SKILL.md` directories. The current ladder uses Ph1/Ph2/Ph3/Ph4 terminology, `reviews/phase_state.json`, `current_phase`, and `phase_entry_log`. Tier-era names such as `T1`, `T2`, `T3`, `T4`, `run-tier-*`, and `reviews/tier_state.json` appear below only in historical source notes, retired-skill migration notes, or ancestry descriptions.

### SK-01. `check-contradictions`
- **File:** `skills/check-contradictions/SKILL.md`
- **Pattern:** Theoretical contradiction between co-invoked sources (SAFEGUARD_LAYER Check 4)
- **Created:** 2026-04-09
- **Source:** INF3001 review — Baumer/i* contradiction was the highest-value BLOCKER found
- **Tier:** Package
- **Status:** Active

### SK-02. `check-abstract-body`
- **File:** `skills/check-abstract-body/SKILL.md`
- **Pattern:** Abstract promises not paid off in the body (SAFEGUARD_LAYER Check 3)
- **Created:** 2026-04-09
- **Source:** INF3001 review — Haslam taxonomy defined but not operationalized
- **Tier:** Package
- **Status:** Active

### SK-03. `quick-deterministic`
- **File:** `skills/quick-deterministic/SKILL.md`
- **Pattern:** Running the mechanical pre-flight without a full review
- **Created:** 2026-04-09
- **Source:** Package workflow — most common first action on any piece
- **Tier:** Package
- **Status:** Active

### SK-04. `classify-manuscript`
- **File:** `skills/classify-manuscript/SKILL.md`
- **Pattern:** Mandatory first-step classification before any review — gathers paper type, P-stage, venue, and default final phase, applies the gating table, and produces `reviews/classification.md`
- **Created:** 2026-04-11
- **Source:** Tier 1 skill build — REVIEW_ORCHESTRATION.md §1 and §3 had no standalone entry point; users had to manually know to classify before reviewing
- **Tier:** Package
- **Status:** Active

### SK-06. `run-reflection`
- **File:** `skills/run-reflection/SKILL.md`
- **Pattern:** Single-command entry point for the Reflector agent. The Reflector dispatches in two modes: (a) **lightweight** — evidence gathering, integrity probes, and memory-only learning during Ph1/Ph2/Ph3 rounds, with no skill proposals or plugin-update filings; (b) **full** — round-close evidence gathering, lesson extraction, grounding audit, memory update, skill development, convergence trajectory audit, `[Ph3-STALE]` / MCR volatility audit, and phase-row contract audit at Ph4 close-out. Skill proposals and plugin-update proposals (`reviews/plugin_update_proposals.md`) are **full-mode-only** and route through the Planner three-filter gate (evidence-adequacy / non-duplication / phase-appropriateness) before the user sees them.
- **Created:** 2026-04-11; mode-split rewritten 2026-04-20 for v0.7.0
- **Source:** Early package skill build — the Reflector had no standalone entry point; lessons were consistently lost between sessions because reflection was never triggered. The mode-split was added at v0.7.0 to support the Lifecycle-Phase Ladder's unbounded Ph3 iteration: lightweight passes catch ledger-integrity drift mid-iteration without forcing a full close-out cycle.
- **Tier:** Package
- **Status:** Active
- **Depends on:** `skills/run-reflection/SKILL.md` (public mode router), `agents/reflector-probe.md` (lightweight procedure), `agents/reflector-closeout.md` (full procedure), `references/PHASE_PROTOCOL.md §11`, and `agents/planner.md` (proposal gatekeeper)

### SK-07. `sentence-level-pass`
- **File:** `skills/sentence-level-pass/SKILL.md`
- **Pattern:** Targeted Bacon sentence-craft pass — 9-point checklist covering focus, balance, modification, variety, and rhythm; runs independently of the full pipeline
- **Created:** 2026-04-11
- **Source:** Tier 2 skill build — `bacon_2009_well_crafted_sentence_guidelines.md` had no standalone entry point; users had to invoke the full review to get sentence-level feedback
- **Tier:** Package
- **Eval benchmark:** [ICI — see EVAL_METHODOLOGY.md] with_skill 95.2% vs without_skill 42.8% (Δ +0.52)
- **Status:** Active

### SK-08. `narrative-structure-pass`
- **File:** `skills/narrative-structure-pass/SKILL.md`
- **Pattern:** Targeted Sexton narrative-structure pass — 10-item arc check covering central need, forward drive, show-then-tell, cause-and-effect, voice, and structural theme
- **Created:** 2026-04-11
- **Source:** Tier 2 skill build — `Sexton_Fiction_to_Academic_Writing_Guide.md` had no standalone entry point; arc checks were bundled into the full pipeline and never run in isolation
- **Tier:** Package
- **Eval benchmark:** [ICI — see EVAL_METHODOLOGY.md] with_skill 95.2% vs without_skill 42.8% (Δ +0.52)
- **Status:** Active

### SK-09. `IS-theory-pass`
- **File:** `skills/IS-theory-pass/SKILL.md`
- **Pattern:** Targeted Baird IS-theory pass — five-element model, nine-step compliance table, six reviewer lenses, five rookie mistakes; IS-venue applicability gate included
- **Created:** 2026-04-11
- **Source:** Tier 2 skill build — `baird_2021_writing_guidelines.md` had no standalone entry point; IS-theory checks were embedded in Step 3 of the full review with no way to run them independently for quick venue-fit assessment
- **Tier:** Package
- **Eval benchmark:** [ICI — see EVAL_METHODOLOGY.md] with_skill 95.2% vs without_skill 42.8% (Δ +0.52)
- **Status:** Active

### SK-10. `p-stage-checker`
- **File:** `skills/p-stage-checker/SKILL.md`
- **Pattern:** Targeted P-stage verification — checks vocabulary drift, argument arc, five anti-patterns (premature RQs, missing forward handoff, P2 vocabulary in P1 conclusion), and contribution framing against declared P0/P1/P2 stage
- **Created:** 2026-04-11
- **Source:** Tier 3 skill build — P-stage verification was buried inside the full pipeline with no standalone entry point; without the skill, agents unilaterally reclassify manuscripts and miss the q-α/β/γ forward-handoff pattern
- **Tier:** Package
- **Eval benchmark:** [ICI — see EVAL_METHODOLOGY.md] with_skill 100.0% vs without_skill 41.1% (Δ +0.59)
- **Status:** Active

### SK-11. `response-letter-review`
- **File:** `skills/response-letter-review/SKILL.md`
- **Pattern:** Six-part response letter review — opening strength, discipline provenance, tone audit (defensive vs. constructive matrix), coverage completeness, scope hedging, and SAFEGUARD integrity checks. Response letters are treated as a manuscript class under the Lifecycle-Phase Ladder rather than a sibling ladder: the Planner classifies the response-letter document, routes the appropriate phase work, and preserves traceability between reviewer points, manuscript changes, and response prose. Invoke directly as `/response-letter-review`; a natural-language review-letter request may route here through the Planner.
- **Created:** 2026-04-11; reframed 2026-04-20 for v0.7.0 (T3R sibling ladder retired)
- **Source:** Tier 3 skill build — `research_paper_writing_guidelines.md §8` response letter rules had no standalone review entry point; without the skill, agents miss edit traceability checks and structured priority-fix ranking
- **Tier:** Package
- **Eval benchmark:** [ICI — see EVAL_METHODOLOGY.md] with_skill 100.0% vs without_skill 41.1% (Δ +0.59)
- **Status:** Active
- **Lifecycle-Phase Ladder placement:** Response-letter review is no longer a sibling ladder. When paired with a Ph4 manuscript pass (e.g., a resubmission), G.4 sign-off is required on the Ph4 manuscript per `REVIEW_ORCHESTRATION.md §3.3`; the response letter itself is reviewed under its declared phase and manuscript class. Historical T3R/T4R labels are preserved only in older release notes and migration history.

### SK-12. `grounding-audit`
- **File:** `skills/grounding-audit/SKILL.md`
- **Pattern:** Six-category GROUNDING_PROTOCOL compliance audit — citations (Rule 4), metrics (Rule 2), file paths (Rule 3), rule citations (Rule 1), gap-fill/fabrication (Rule 6), uncertainty markers (Rule 5); produces CLEAN or N VIOLATIONS verdict
- **Created:** 2026-04-11
- **Source:** Tier 3 skill build — `GROUNDING_PROTOCOL.md` grounding audit had no standalone entry point; without the skill, agents produce narrative audits that miss the formal category structure and N/A reporting for absent categories
- **Tier:** Package
- **Eval benchmark:** [ICI — see EVAL_METHODOLOGY.md] with_skill 100.0% vs without_skill 41.1% (Δ +0.59)
- **Status:** Active

### SK-13. `suchman-register-audit`
- **File:** `skills/suchman-register-audit/SKILL.md`
- **Pattern:** Two-layer Suchman register compliance audit — seven-move inventory (from `suchman_writing_style.md §5`) plus theoretical adequacy check for plans/situated action distinction (Check A) and asymmetric design argument (Check B)
- **Created:** 2026-04-11
- **Source:** INF3001H Round 4 — Suchman was cited without the plans/situated action distinction being deployed; the voice audit did not catch it because it checked move presence but not theoretical adequacy
- **Tier:** Package
- **Status:** Active

### SK-17. `ingest-m5-to-wiki`
- **File:** `skills/ingest-m5-to-wiki/SKILL.md`
- **Pattern:** Materializes **Coupling D** — ingests a project's M5 (submission-bound final) manuscript into `LLM wiki/wiki/sources/<key>.md` as a complete, non-stub source page with `grounding_status: full-read (deferred Wiki page; do not write until governed ingestion)`. Fires after G.4 sign-off. Produces: bibliographic table, structured claim summary, method/apparatus note, relationship-to-program paragraph, limitations list, harvested wikilinks to concepts/entities the paper grounds, and a concept-page follow-on batch queued for SK-16. Closes the coupling by appending a dated line to the project CLAUDE.md's Wiki linkage section. Preserves the manuscript as source of truth; the wiki source page is a searchable view.
- **Created:** 2026-04-13
- **Source:** Research↔Wiki diagnostic audit 2026-04-13 — Finding F6 (M5 final paper is a natural wiki source, not just a review artefact). Coupling D was registered as a bootstrap-time intent in PROJECT_BOOTSTRAP.md §3 Step 5 on 2026-04-13; SK-17 formalizes the ingestion protocol itself so the coupling becomes executable rather than aspirational.
- **Tier:** Package
- **Status:** Active
- **Depends on:** Project at M5 with G4_signoff; wiki reachable; project CLAUDE.md declares `wiki_linked: true` and `coupling_d_on_m5: true` (per PROJECT_BOOTSTRAP.md §3 Step 5)
- **Sibling:** SK-14 (independent, both can fire at round close); SK-16 (downstream consumer — SK-17 queues concept-page follow-ons that SK-16 executes); SK-15 (inverse relationship — SK-17 produces full source pages, SK-15 produces stubs)
- **One-time trigger on first deployment:** SK-17 Phase 9 surfaces a recommendation to upgrade `QUICKSTART.md` and `OPERATING_MANUAL.md` from the lighter patch (applied 2026-04-13) to full integration, based on actual-use experience. Scheduled 2026-04-13 against the first SK-17 invocation in the workspace.

### SK-16. `retrofit-concept-grounding`
- **File:** `skills/retrofit-concept-grounding/SKILL.md`
- **Pattern:** Materializes **Coupling B** — retrofits wiki concept pages with grounding citations to existing source pages. Converts in-prose author-year references into wikilinks, updates frontmatter (`sources:` + `grounding_status:`), appends a grounding footer. Surgical: does not rewrite page content, does not fabricate citations or source pages, reports unresolved citations as red-link candidates.
- **Created:** 2026-04-13
- **Source:** Research↔Wiki diagnostic audit 2026-04-13 — Finding F3 (concept pages assert claims without grounding citations, violating Grounding Protocol Rule 4). Pilot retrofit of `concepts/humanness.md` 2026-04-13 established the stub-then-cite pattern.
- **Tier:** Package
- **Status:** Active
- **Depends on:** SK-15 (external-source stubs must exist before retrofit); SK-17 (for M5-triggered batch retrofits against a newly ingested paper)
- **Sibling:** SK-15 upstream for stub corpus; SK-17 upstream for M5-triggered concept-page follow-ons

### SK-15. `backfill-source-stubs-from-references`
- **File:** `skills/backfill-source-stubs-from-references/SKILL.md`
- **Pattern:** Materializes **Coupling A-revised** — generates `wiki/sources/<key>.md` stubs in batch from a project's `references/REFERENCES.md`, populating the external-source layer the wiki currently lacks. Each stub carries `grounding_status: stub` in frontmatter until replaced by a direct-read summary. Enumerates core + snowball rows only (skips "cited but not read directly"), classifies P1/P2/P3 priority by whether the source anchors an existing concept page, writes new files without touching existing ones, updates `index.md` and `log.md`.
- **Created:** 2026-04-13
- **Source:** Research↔Wiki diagnostic audit 2026-04-13 — Finding F1 (wiki holds zero external scholarly sources; the wiki and the pipeline are complementary, not redundant). Humanness retrofit (2026-04-13) demonstrated that stub-first grounding works if `grounding_status` frontmatter carries the audit trail; this skill codifies the stub-generation half as a repeatable batch operation.
- **Tier:** Package
- **Status:** Active
- **Depends on:** Project has a REFERENCES file in the INF3006Y_AgencyDelegation format (source-root aliases + core + snowball + cited-via tables); wiki exists at the path declared in workspace CLAUDE.md
- **Sibling:** SK-14 `promote-lessons-to-wiki` — downstream consumer. Together SK-15 → SK-14 forms the batch pathway "populate external sources, then promote project lessons into syntheses that can cite them without red links."

### SK-14. `promote-lessons-to-wiki`
- **File:** `skills/promote-lessons-to-wiki/SKILL.md`
- **Pattern:** Materializes **Coupling C** — promotes a project's `research_notes/lessons_learned.md` (L-xx entries) into a generalizing synthesis page in `LLM wiki/wiki/syntheses/` with bidirectional wikilinks, scope-qualified generalizations (G/P/L/D classification), non-destructive back-pointer in the project file, and index + log registration. Preserves the project file as authoritative/append-only; the synthesis page is a regenerable view.
- **Created:** 2026-04-13
- **Source:** Research↔Wiki diagnostic audit 2026-04-13 — Finding F4 (lessons terminate in-project; `wiki/syntheses/` is the natural sink but no protocol connected the two); pilot executed ad hoc on INF3006Y_AgencyDelegation L-01..L-05 producing `lessons-agency-delegation-2026-04-13.md`. This skill codifies the pilot as a repeatable protocol so the Reflector can trigger it at review-round close.
- **Tier:** Package
- **Status:** Active
- **Depends on:** A functioning LLM wiki at the path the workspace CLAUDE.md declares; the project's source page must exist in `wiki/sources/` (else skill stops and asks)
- **Related couplings:** Coupling B (concept-page grounding retrofit) is a likely follow-on when red-link candidates accumulate; Coupling D (manuscript self-ingestion on M5) is this skill's upstream prerequisite

### SK-18. `advisor-escalation`
- **File:** `skills/advisor-escalation/SKILL.md` (executable prompt)
- **Pattern:** **Advisor MCP** — the co-author-harness **plugin** ships this skill; the **host** must connect the **advisor** MCP server so `consult_advisor` is available. Escalation from the four-agent loop to frontier-class advisor output (Claude Fable 5 as of advisor plugin v0.4.0, 2026-07-07), with EXTERNAL-tag re-classification, `reviews/advisor_consultation_*.md` filing, and grounding-protocol integration. **EP-1** (post-Ph2, pre-Ph3) and **EP-2** (post-`Ph3_converged`, pre-MCR/Ph4) are the recommended **submission-defensibility** entry points; normative text in `references/ADVISOR_MCP.md` and `PHASE_PROTOCOL.md` §1.
- **Created:** 2026-04-15
- **Source:** C.1 → A.1 design session — advisor MCP server (v1.3.0) produces EXTERNAL-tagged output, but without a bridge skill the tags are not audited, the consultation is not filed, and advisor-sourced claims enter the pipeline as unverified-but-unmarked hypotheses. EP-1/EP-2 entry points added 2026-04-25.
- **Tier:** Package
- **Status:** Active
- **Dependencies:** `advisor` MCP server in the **host** (contract v1.3.0+ runtime; `ADVISOR_MCP.md` documents wiring); consultation uses `project_root` canonical context packing where possible
- **Contract version gate:** v1.3.0+ — treat earlier versions' tag output as untrusted and always re-classify; v1.3.0+ improves prompt-side discipline but re-classification remains mandatory
- **Grounding-audit extension:** Adds Category 7 (advisor-sourced claims) to the grounding-audit skill's six existing categories
- **Sibling:** SK-12 `grounding-audit` (downstream consumer — Category 7 extension); SK-25/29/26/27 `run-phase-1/2/3/4` (advisor-escalation is an optional **lateral** at EP-1/EP-2, not a substitute for phase skills)

### SK-22. `tool-contract-roundtrip`
- **File:** `skills/tool-contract-roundtrip/SKILL.md`
- **Pattern:** Pre-release round-trip probe of every external-verifier MCP — invokes each advertised tool, inspects the response payload for undocumented contract fields (render_contract, session_footer, disclosures, usage_terms), surfaces placeholder namespaces, stale UUIDs, and referenced-but-unexercised tools. Reflexively applies GROUNDING_PROTOCOL Rules 1 (read-before-cite) and 4 (verify-before-reference) to the plugin's own tool surface. Emits an append-only `reviews/tool_contract_probe_<date>.md` with BLOCKER / MAJOR / MINOR findings and a release-gate verdict (CLEARED / BLOCKED / CLEARED-WITH-DEFERRALS).
- **Created:** 2026-04-16
- **Source:** v0.3.3 integration analysis addendum — the v0.3.2 placeholder-namespace defect (Defect 1) and the missing-render-contract defect (Defect 2) were both instances of the same pattern: `EXTERNAL_VERIFIERS.md` referenced a tool without invoking it. A single round-trip probe on every referenced tool would have surfaced both before release. SK-22 makes the round-trip the release gate.
- **Tier:** Package
- **Status:** Active (v0.4.0 release-gate skill)
- **Depends on:** `EXTERNAL_VERIFIERS.md` (§2 verifier tier tables, §3.1 Scholar Gateway render contract); `mcp__mcp-registry__search_mcp_registry` for connectivity probing; each declared verifier's minimal-invocation path (see skill Phase 4 for per-verifier probe specs)
- **Governance role:** Release gate. Running the plugin through a version bump that touches `EXTERNAL_VERIFIERS.md` without a SK-22 probe is itself a package-governance violation. The probe report is append-only so drift between releases is auditable.
- **Sibling:** SK-12 `grounding-audit` (structural analog — applies Rule 1/4 to manuscripts; SK-22 applies Rule 1/4 to the plugin itself); SK-18 `advisor-escalation` (both concern external-source contract management; SK-18 at runtime, SK-22 at release time)
- **Reflexive claim.** The harness must pass the rules it imposes. SK-22 is the mechanism by which the plugin demonstrates Rule 1 / Rule 4 compliance on its own advertised tool surface before asking manuscripts to do the same.

### SK-20. `graph-grounding-overlay`
- **File:** `skills/graph-grounding-overlay/SKILL.md`
- **Pattern:** Unavailable Coupling E.2 overlay. The unconditional graph-authority gate returns `GRAPH_GOVERNED_GENERATION_UNAVAILABLE`; structurally valid graph files do not grant authority and the skill produces no overlay findings.
- **Created:** 2026-04-16
- **Source:** Synergy analysis 2026-04-16 — graphify produces 43 nodes / 53 edges / 7 communities / 81% EXTRACTED 19% INFERRED / section-level provenance at `LLM wiki/graphify-out/`, but zero file in `.paper-package/` references it (grep confirmed). SK-20 is the v0.3.0 minimum-viable pilot: a single Evaluator pre-flight hook that converts graph topology into findings in the pipeline's native output format, preserving uncertainty inheritance through graph-specific source tags.
- **Tier:** Package
- **Status:** Unavailable (`GRAPH_GOVERNED_GENERATION_UNAVAILABLE`); a separate governed graph-generation contract is required before promotion.
- **Depends on:** graphify toolchain (runs externally; produces `graph.json` and `GRAPH_REPORT.md` under `LLM wiki/graphify-out/`); SK-15 `backfill-source-stubs-from-references` (provides citation-key ↔ pdf-path mapping Phase 2 relies on); project CLAUDE.md declares `wiki_linked: true`; `reviews/classification.md` exists for P-stage adjustment
- **Contract version gate:** Graphify output schema as observed 2026-04-13 (top-level keys: `directed`, `multigraph`, `graph`, `nodes`, `links`, `hyperedges`; node fields: `id`, `label`, `source_file`, `source_location`, `author`, `captured_at`, `community`, `norm_label`; edge fields: `relation`, `confidence`, `confidence_score`, `source_file`, `source_location`, `weight`, `source`, `target`). If graphify's output schema changes, update this skill before running against a new graph.
- **Grounding-audit extension:** Adds Category 8 (graph-sourced claims) to grounding-audit, paralleling SK-18's Category 7 extension. Category 8 audits three tag classes (extracted, inferred, stub), enforces confidence-score inheritance, and blocks on fabricated node/edge references or false stubs. As of v0.4.0, Category 8 gains sub-item 8a (confidence-echo detector) — every `[GRAPH-OVERLAY][CAT-8]` finding whose severity matches the mechanical confidence-to-severity mapping (EXTRACTED→BLOCKER, INFERRED→MAJOR, AMBIGUOUS→MINOR) must carry an independent-reasoning note citing a passage, directive, P-stage rule, or Class 1 verifier cross-check. Echo findings (matching severity + missing note) are MAJOR at standard depth and BLOCKER at submission-bound depth; shallow findings (matching severity + confidence-only note) are one tier below. Round-level ECHO+SHALLOW rate ≥ 30% triggers a `[COUPLING-E.2 DEGRADED]` flag.
- **Sibling:** SK-18 `advisor-escalation` (structurally analogous — both bridge an external source of claims into the pipeline with tag-preserved uncertainty; SK-18 → Category 7, SK-20 → Category 8); SK-15 `backfill-source-stubs-from-references` (upstream dependency); SK-16 `retrofit-concept-grounding` (shares citation-parsing patterns); SK-17 `ingest-m5-to-wiki` (downstream — M5 ingestion triggers graphify re-run, which in turn refreshes SK-20's substrate)
- **Coupling family:** Coupling E has two active sub-couplings at v0.11.0: E.1 (snowball-seeding) is materialised via **SK-33 `seed-snowball-discovery`**'s graph-substrate iterate phase (previously roadmapped as `SK-19 graph-read-at-planner`, now retired; implemented at v0.10.0-S1.5); E.2 (overlay-this-skill) is this skill. The originally roadmapped E.3 contradiction-sweep extension was retired at v0.11.0 with the c4 phantom-roadmap cleanup; if a contradiction-sweep need re-emerges it is reachable via the existing `check-contradictions` skill rather than a graph-specific successor.

### SK-30. `accessibility-overlay`
- **File:** `skills/accessibility-overlay/SKILL.md`
- **Pattern:** Materializes the **Reader-Experience defence** — exactly eight profile-bound Sub-checks A–H. A–F audit local prose, G cumulative consolidation, and H passage/manuscript register. The A–H aggregate is the Planner's accessibility gate value. Verdict-Edge (VE) is a separate adjacent advisory routed only to Reflector recurrence and never contributes to the aggregate.
- **Created:** 2026-04-20 (v0.7.2 Reader-Experience defence pilot)
- **Source:** the architectural-gap audit preserved in the release notes. SK-30 is the judgment layer that converts deterministic pre-filter output into Evaluator-native findings and is grounded in `READER_ACCESSIBILITY.md §13.3`.
- **Tier:** Package
- **Status:** Active (v0.7.2 pilot — validation target is per-section Check 8 corpus aggregation at Reflector-full Phase 2g close-out)
- **Depends on:** resolved `references/policies/reader_accessibility.v1.json` plus its source hashes; `DETERMINISTIC_CHECKS §9b/§9d/§9e` candidate output; `SAFEGUARD_LAYER.md` Check 8; `phase_state.json.milestone_framework.policy_bindings.reader_accessibility` for live transition state; `milestones/M4_complete_paper_draft.md`.
- **Grounding-audit extension:** Contributes its `source_tag: accessibility-overlay@v1.0` on every finding so the Reflector's grounding audit (`GROUNDING_PROTOCOL.md §Grounding Audit`) can trace Check 8 findings back to the overlay that produced them. Severity floors mirror the SAFEGUARD Check 8 aggregation rule exactly.
- **Sibling:** SK-20 `graph-grounding-overlay` (structural analog — additive, non-manuscript-mutating overlay that converts an external signal into Evaluator-native findings); SK-03 `quick-deterministic` (upstream — §9b pre-filter feeder); SK-12 `grounding-audit` (sibling audit); SK-06 `run-reflection` (downstream consumer at Phase 2g recurrence audit).
- **Non-suspendable commitment:** Check 8 operationalises **commitment C-5** of `STYLE_COMMITMENTS.md`; the overlay therefore cannot be disabled wholesale via the §4 relaxation procedure. Project-scoped severity-floor overrides are permitted via `research_notes/directives.md`.

### SK-23. `plugin-commands`
- **File:** `skills/plugin-commands/SKILL.md`
- **Pattern:** Built-in slash-command catalog. Returns the complete list of shipped commands with one-line purpose and best-use moment so users can discover and invoke commands directly after installation.
- **Created:** 2026-04-16
- **Source:** Plugin usability request — command list was not conveniently accessible from a single slash command in installed sessions.
- **Tier:** Package
- **Status:** Active
- **Depends on:** Current `skills/*/SKILL.md` set in the package. Command list should be updated whenever skills are added or retired.
- **Sibling:** SK-04 `classify-manuscript` (recommended first command after `/plugin-commands` for review workflows); public lifecycle routers SK-37 `run-draft`, SK-38 `run-iterate`, and SK-39 `run-finalize`; hidden compatibility bodies SK-25 `run-phase-1`, SK-29 `run-phase-2`, SK-26 `run-phase-3`, and SK-27 `run-phase-4`.

### SK-24. `public-interest-accountability-pass`
- **File:** `skills/public-interest-accountability-pass/SKILL.md`
- **Pattern:** Optional Eubanks-style overlay for policy-critical writing. Audits whether major claims pair human-impact anchoring with explicit mechanism tracing (rules, workflows, metrics, legal/procedural constraints), and whether normative framing remains evidence-disciplined.
- **Created:** 2026-04-16
- **Source:** Comparative style audit request — evaluate `Automating Inequality` against existing Baird/Sexton/Bacon stack and capture additive strengths without replacing core controls.
- **Tier:** Package
- **Status:** Active
- **Depends on:** `references/eubanks_2018_automating_inequality_style_guidelines.md`; manuscript scope includes policy/inequality/public-service accountability framing.
- **Sibling:** SK-08 `narrative-structure-pass` (macro narrative drive), SK-07 `sentence-level-pass` (micro craft), SK-04 `classify-manuscript` (decides whether overlay is in scope)

### SK-25. `run-phase-1`
- **File:** `skills/run-phase-1/SKILL.md` (renamed at v0.7.4 from `skills/run-tier-1/SKILL.md` as part of the tier→phase vocabulary sweep; earlier rename at v0.6.0 from `skills/run-tier-reflex/SKILL.md`; rewritten in place at v0.7.0)
- **Pattern:** Compatibility implementation body for the public `/run-draft` entrypoint. It preserves the **Ph1 Plan & Draft** rung of the Lifecycle-Phase Ladder — the planning-and-drafting rung covering scoping, problem framing, and initial prose generation (absorbed activities from milestones M1, M2, and M3). Engagement delegates to `references/policies/phase_engagement.v1.json`: Generator-led drafting is followed by the bounded independent Evaluator pass. The retired Generator Self-T1 Verdict is no longer emitted; drift-measurement signals migrate into the Generator's Phase 4 completion message. The retired Confirmation Mode is no longer entered at any rung. The retired Rule 1 tier-gated digest exception is no longer applied; full-file reads are the universal floor at every rung. On user approval, the Planner advances the section to T2 (`prev_tier: T1`, `new_tier: T2`, `trigger: user_approval`, `actor: planner`).
- **Created:** 2026-04-19 (as `run-tier-reflex` under v0.4.19); renamed 2026-04-19 (v0.6.0); rewritten 2026-04-20 (v0.7.0).
- **Source:** Phase B of the Incremental Tier Protocol (v0.4.19) seeded the skill; Phase 6 of the v0.6.0 rollout renamed and rewrote it to carry the staircase semantics; the v0.7.0 rewrite removes the Self-T1 Verdict, Confirmation Mode, and digest-exception couplings to align with the Lifecycle-Stage Ladder's full-file-read floor and tier-conditioned agent engagement.
- **Tier:** Package
- **Status:** Legacy compatibility body (active; public guidance should prefer `/run-draft`)
- **Depends on:** `references/PHASE_PROTOCOL.md §3 (Ph1 Plan & Draft)`, `references/GROUNDING_PROTOCOL.md` (full-file reads at every rung — no digest exception at v0.7.0), the per-section ledger `reviews/phase_state.json` (18-field SectionStateObject including `ph1_pstage_declaration`), and the Planner's `phase_entry_log` seven-field row contract per `AGENT_ORCHESTRATION.md §8.2a` (`prev_phase`, `new_phase`, `trigger`, `actor`, `notes`, `timestamp`, `model_used`).
- **Sibling:** SK-03 `quick-deterministic` (mechanical-only ancestor); SK-29 `run-phase-2` (Review & Revise — advance target on approval); SK-26 `run-phase-3` and SK-27 `run-phase-4` (further rungs); SK-04 `classify-manuscript` (writes the `tier:` field this skill dispatches on, legal values `{T1, T2, T3, T4}` at v0.7.0).

### SK-26. `run-phase-3`
- **File:** `skills/run-phase-3/SKILL.md` (renamed at v0.7.4 from `skills/run-tier-3/SKILL.md` as part of the tier→phase vocabulary sweep; earlier rename at v0.6.0 from `skills/run-tier-standard/SKILL.md`; rewritten in place at v0.7.0)
- **Pattern:** Compatibility implementation body for the public `/run-iterate` entrypoint's full **Ph3 Iterate & Converge** envelope. It preserves the unbounded-iteration convergence rung, including pre-flight deterministic checks, the judgment pass, SAFEGUARD integrity audit, convergence logging, terminal sign-off, MCR admission, and re-engagement semantics.
- **Created:** 2026-04-19 (as `run-tier-standard` under v0.5.0); renamed 2026-04-19 (v0.6.0); rewritten 2026-04-20 (v0.7.0).
- **Source:** Phase C of the Incremental Tier Protocol (v0.5.0) seeded the skill; Phase 6 of the v0.6.0 rollout renamed it for staircase-position clarity; the v0.7.0 rewrite reframes T3 from a single-pass Verify rung to an unbounded Iterate & Converge rung with explicit convergence-log and MCR semantics.
- **Tier:** Package (Cowork-installable .skill file)
- **Status:** Legacy compatibility body (active; public guidance should prefer `/run-iterate`)
- **Depends on:** `references/PHASE_PROTOCOL.md §3 (Ph3 Iterate & Converge)` and `§6 (Manuscript Convergence Report)`, `references/REVIEW_ORCHESTRATION.md §3.3` (tier table), the full seven-step review references, the `reviews/phase_state.json` ledger (18-field SectionStateObject including `convergence_metric`, `ph3_last_activity_at`), `reviews/convergence_log.md`, and `reviews/classification.md` declaring `tier: T3` (or the section's `current_phase` reaching Ph3 through ladder advance).
- **Sibling:** SK-25 `run-phase-1` (Plan & Draft — two rungs below); SK-29 `run-phase-2` (Review & Revise — one rung below, the ladder predecessor); SK-27 `run-phase-4` (Finalize & Close — one rung above, the MCR-gated advance target); SK-04 `classify-manuscript` (writes the `tier:` field). SK-05 `run-full-review` (retired at v0.5.1; see Retired Skills) was the v0.4.x entry point this skill replaced.

### SK-31. `run-phase-3-stability`
- **File:** `skills/run-phase-3-stability/SKILL.md` (net-new at v0.7.4; no prior surface)
- **Pattern:** **Compatibility router** for the former Ph3 stability sub-mode. The public surface is now `/run-iterate --profile stability`; this legacy command preserves old slash histories while routing to the iterate-stage profile. The underlying envelope remains the S-0 byte-stability gate, grounding audit, deterministic Check 8 counter comparison, trigger-30 escalation on any finding, and the rule that stability cannot satisfy the pre-MCR deep-pass requirement.
- **Created:** 2026-04-21 (v0.7.4, P-2 substantive landing)
- **Source:** v0.7.4 economic-efficiency package P-2 — the Ph3 round on a byte-stable manuscript is the paradigmatic cost-waste case (seven-step judgment pass produces no new signal because the signal substrate has not changed). Motivating observation: INF3006Y iter-7 stability pass produced ~80% of a full-round's cost with zero new findings (n=1 diagnostic; ship-on-iter-7-only deliberate user override per CHANGELOG caveat). P-2 closes the waste envelope without compromising audit integrity — the gate is *all-families-match-or-drop-through*, stricter than strictly necessary but defensible on provenance grounds. The sub-mode defers to full `run-phase-3` on any surfaced finding, treats escalation as bookkeeping rather than a findings event, and preserves the Ph4 admission contract intact.
- **Tier:** Package
- **Status:** Legacy compatibility router (active; public guidance should prefer `/run-iterate --profile stability`)
- **Depends on:** `references/PHASE_PROTOCOL.md §3.3.2` (stability sub-mode normative spec), `§3.3.4` (convergence_journal.jsonl `manuscript_hash`), `§3.3.5` (P-7 exclusion note), `§6.3` (trigger 30 declaration); `references/ARTEFACT_FRONTMATTER_SCHEMA.md §7a` (F6 `stability_sub_mode_anticipated` flag, F6-not-inherited rule); `references/AGENT_CONTRACTS.md §2` (I-Planner-10 round dispatch plan); `references/DETERMINISTIC_CHECKS.md §9b` (Check 8 pre-filter counters); `references/GROUNDING_PROTOCOL.md §Rule 1` (full-file read floor); `agents/planner.md` Phase 0.6 and Phase 5.5 Ph3 iteration boundary; `agents/evaluator.md §Step 8.5` (SAFEGUARD Check 8 sub-filter); `reviews/convergence_journal.jsonl` (per-iteration manuscript_hash ledger); `skills/run-phase-3/SKILL.md` (the full Ph3 envelope this sub-mode reduces from).
- **Sibling:** SK-38 `run-iterate` (public stage/profile router); SK-26 `run-phase-3` (legacy full-iterate compatibility body); SK-30 `accessibility-overlay` (downstream-excluded under stability); SK-12 `grounding-audit`; SK-06 `run-reflection` lightweight-mode.
- **Contract version gate:** v0.7.4+ — the stability sub-mode requires `manuscript_hash` on journal rows, which v0.7.4 `migrate_convergence_log_v074.py` backfills (P-4). Pre-v0.7.4 projects without backfilled hashes drop through to full `run-phase-3` on every invocation via S-0 clause `hash_missing_prior_iteration`; no retroactive harm.
- **Non-ceiling-locked constraint.** A section at `current_phase: Ph3_converged` does not invoke stability mode — stability is a Ph3-active construct. A Ph4-demoted section that returned to Ph3 via EG-1 may run stability mode once the re-admission row is written and a full-Ph3 pass has re-established the hash baseline.

### SK-27. `run-phase-4`
- **File:** `skills/run-phase-4/SKILL.md` (renamed at v0.7.4 from `skills/run-tier-4/SKILL.md` as part of the tier→phase vocabulary sweep; earlier rename at v0.6.0 from `skills/run-tier-submission/SKILL.md`; rewritten in place at v0.7.0)
- **Pattern:** Compatibility implementation body for the public `/run-finalize` entrypoint. It preserves the **Ph4 Finalize & Close** terminal envelope: M5, MCR admission, required G.4 sign-off, external verification, the full-mode Reflector close-out, and terminal sign-off semantics.
- **Created:** 2026-04-19 (as `run-tier-submission` under v0.5.0); renamed 2026-04-19 (v0.6.0); rewritten 2026-04-20 (v0.7.0).
- **Source:** Phase C of the Incremental Tier Protocol (v0.5.0) seeded the skill; Phase 6 of the v0.6.0 rollout renamed it and wired in the Laggard Clearance Report precondition; the v0.7.0 rewrite replaces the LCR with the MCR, wires in the monotonicity-exempt EG-1 (T4→T3 demotion) and the net-new EG-7 (MCR re-admission after classification change), and couples T4 approval to the Reflector's full-mode five-phase close-out including audit phases 2d/2e/2f.
- **Tier:** Package (Cowork-installable .skill file)
- **Status:** Legacy compatibility body (active; public guidance should prefer `/run-finalize`)
- **Depends on:** `references/PHASE_PROTOCOL.md §3 (Ph4 Finalize & Close)` and `§6 (Manuscript Convergence Report)`, `references/REVIEW_ORCHESTRATION.md §3.3` and `§6` (G.4 sign-off template), all T3 dependencies, the per-section `reviews/phase_state.json` ledger (18-field SectionStateObject, `mcr_admission` flag), `reviews/convergence_log.md`, and `reviews/classification.md` declaring `tier: T4` (or the ladder having advanced every section to `T3_converged`).
- **Sibling:** SK-25 `run-phase-1` (Plan & Draft — three rungs below); SK-29 `run-phase-2` (Review & Revise — two rungs below); SK-26 `run-phase-3` (Iterate & Converge — one rung below, the ladder predecessor); SK-04 `classify-manuscript` (auto-recommends T4 on the submission-bound triggers listed in its Step 2); SK-06 `run-reflection` (full-mode Reflector dispatch at T4 close-out); SK-17 `ingest-m5-to-wiki` (downstream handoff after G.4 sign-off closes). SK-05 `run-full-review` (retired at v0.5.1; see Retired Skills) dispatched here when classification was T4 during the v0.5.0 transitional window.

### SK-29. `run-phase-2`
- **File:** `skills/run-phase-2/SKILL.md` (renamed at v0.7.4 from `skills/run-tier-2/SKILL.md` as part of the tier→phase vocabulary sweep; net-new at v0.6.0; rewritten in place at v0.7.0)
- **Pattern:** **Compatibility router** for the former T2/Ph2 Review & Revise rung. The public surface is now `/run-iterate --profile refine`; this legacy command preserves old slash histories while routing the first full revision-maturity Evaluator engagement into iterate. Historical Ph2 artefacts remain valid evidence.
- **Created:** 2026-04-19 (v0.6.0 Phase 6 skill build); rewritten 2026-04-20 (v0.7.0).
- **Source:** The v0.5.5 T2 "local" tier had no standalone skill entry point — it was dispatched implicitly by the Planner from the `tier:` field. The v0.6.0 staircase promoted T2 to a first-class approval rung between Draft and Verify; the v0.7.0 Lifecycle-Stage Ladder (since renamed Lifecycle-Phase) retains T2 as a first-class rung but retires Confirmation Mode entirely and removes the Self-T1 Verdict coupling.
- **Tier:** Package (Cowork-installable .skill file)
- **Status:** Legacy compatibility router (active; public guidance should prefer `/run-iterate --profile refine`)
- **Depends on:** `references/PHASE_PROTOCOL.md §3 (Ph2 Review & Revise)`, `references/REVIEW_ORCHESTRATION.md §3.3` (tier table), the per-section `reviews/phase_state.json` ledger (18-field SectionStateObject), `reviews/classification.md`, and `references/GROUNDING_PROTOCOL.md` (full-file reads at every rung — no digest exception at v0.7.0).
- **Sibling:** SK-38 `run-iterate` (public stage/profile router); SK-25 `run-phase-1` / SK-37 `run-draft` (draft stage); SK-27 `run-phase-4` / SK-39 `run-finalize` (finalize stage); SK-04 `classify-manuscript`.

### SK-32. `run-generator-session`
- **File:** `skills/run-generator-session/SKILL.md`
- **Pattern:** **Session-sourced Generator** pass — the current chat supplies revision *instructions*; `reviews/classification.md` and `reviews/phase_state.json` supply *authority* (phase, P-stage, ceiling). No new `reviews/` session artefacts in v1. Aligned with `docs/superpowers/specs/2026-04-25-generator-session-revision-design.md` and `agents/generator.md` (manuscript + `manuscript/revision_log.md` only; no `reviews` writes by the Generator).
- **Created:** 2026-04-25
- **Source:** Brainstorming + approved design spec `docs/superpowers/specs/2026-04-25-generator-session-revision-design.md`
- **Tier:** Package
- **Status:** Active
- **Depends on:** `agents/generator.md`, `references/GROUNDING_PROTOCOL.md`, `reviews/classification.md`, `reviews/phase_state.json`, optional project-local style path via `CLAUDE.md` / `directives.md`
- **Sibling:** SK-25 `run-phase-1` … SK-27 `run-phase-4` (full ladder entry points with Planner/Evaluator packaging); SK-23 `plugin-commands` (discovery); SK-07 `sentence-level-pass` / SK-08 `narrative-structure-pass` (craft overlays, not the Generator role file)
- **Not a replacement for:** full `/run-phase-2+` with Evaluator when the project’s governance still requires that round; does not create Planner artefacts

### SK-33. `seed-snowball-discovery`
- **File:** `skills/seed-snowball-discovery/SKILL.md`
- **Pattern:** **Ph1 entry reference scaffolding** — assemble `references/REFERENCES.md` from a section's claim register via Wohlin-style snowball saturation (Wohlin 2014, `10.1145/2601248.2601268`; Zotero `FXJ6M8ED`). Three-phase mechanised procedure: seed (wiki-first per `EXTERNAL_VERIFIERS.md §1.5`; Zotero second; Class 1 fall-through), iterate (graph-substrate variant — traverse `${wiki_path}/graphify-out/graph.json` first, fall through to Scholar Gateway only for graph-stub seeds), verify (every Class 1 admission emits a Rule 7a verification log row). In-loop wiki/sources/ stub write-back when `wiki_linked: true`. Dual-path access (filesystem / mcp_fastpath / auto). Stops on `rate < ε` (default 0.05) or `iterations >= 4`. Materialises Coupling E.1 — previously roadmapped as the `graph-read-at-planner` placeholder in SK-20 §Dependencies (now retired; E.1 implemented via this skill's graph-substrate iterate phase at v0.10.0-S1.5). Pre-seed step: when `inherit_snowball: true` in `reviews/classification.md`, SK-33 auto-invokes SK-36 `inherit-snowball-from-wiki` at Phase 0 before its seed phase.
- **Created:** 2026-04-26
- **Source:** v0.10.0 Stage S1 implementation per `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §5.1, §5.5.1, §5.5.2, §5.5.6`
- **Tier:** Package (executor — Sonnet)
- **Status:** Active (v0.10.0+)
- **Depends on:** `references/GROUNDING_PROTOCOL.md` (Rule 4, Rule 6, Rule 7a), `references/EXTERNAL_VERIFIERS.md §§1.5, 2, 3.1` (Scholar Gateway render contract), `reviews/classification.md` (claim register + the new v0.10.0 fields `claim_coverage_threshold`, `inherit_snowball`, `pre_seed_cap`), `reviews/revision_plan.md` (claim outline), Class 1 verifiers (Scholar Gateway primary; Consensus for contested cross-check; Zotero+Scite for Class 2 resolution + Class 3 retraction), graphify graph at `${wiki_path}/graphify-out/graph.json` (when `wiki_linked: true`)
- **Sibling:** SK-15 `backfill-source-stubs-from-references` (downstream consumer; SK-33's deferred Wiki write-back (`WIKI_WRITE_TRANSACTION_UNAVAILABLE`) inherits SK-15's stub-template logic); SK-16 `retrofit-concept-grounding` (downstream consumer; consumes the populated `wiki/sources/` layer); SK-20 `graph-grounding-overlay` (upstream contract — SK-33 reads the same `graph.json` schema SK-20 reads); SK-34 `claim-coverage-audit` (Ph2 successor); SK-35 `extend-snowball-incremental` (Ph2 in-loop successor); SK-36 `inherit-snowball-from-wiki` (pre-seed dependency)
- **Not a replacement for:** SK-15 (which converts a curated REFERENCES.md to wiki stubs at terminal stage; SK-33 operates inline at Ph1); SK-16 (which retrofits concept pages with wikilinks; SK-33 only writes to `wiki/sources/`); manual literature review (SK-33 is recall-biased and prunes via per-claim verification — it surfaces candidates, not commitments)

### SK-34. `claim-coverage-audit`
- **File:** `skills/claim-coverage-audit/SKILL.md`
- **Pattern:** **Per-claim source mapping for Ph1 → Ph2 admission** — read `manuscript/<section>.md` and `references/REFERENCES.md`, deterministically extract the section's claims (five-kind taxonomy per architecture §4.1: existential, comparison, mechanism, result, theoretical-commitment), map each claim to resolving sources via three categories (explicit citation, anchored metadata, lexical-match similarity ≥ 0.6), and emit a three-set coverage map (covered / partially-covered / uncovered) with a coverage score = `covered / total`. The score is compared against `claim_coverage_threshold` (default 0.8 from `reviews/classification.md`) to surface a CLEAN or BELOW_THRESHOLD verdict. Manually-invokable at v0.10.0-S3 via `/claim-coverage-audit`; auto-invoked by `run-phase-2` Step 0.5 from S4 onward; synthesis-covered fourth set added at S4.5 per architecture §5.5.3. Deterministic — two consecutive runs against the same inputs produce byte-identical findings modulo the timestamp (strategy §5.4 stage-close gate).
- **Created:** 2026-04-27
- **Source:** v0.10.0 Stage S3 implementation per `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §§4.4, 5.1 SK-NEW-B, 6.4` and `docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md §5.4`
- **Tier:** Package (executor — Sonnet; structured audit, on-disk reads only)
- **Status:** Active (v0.10.0+)
- **Depends on:** `references/GROUNDING_PROTOCOL.md` (Rule 6 — no gap-filling; uncovered claims surface, are not back-filled), `references/EXTERNAL_VERIFIERS.md §3` (Planner clause for source-resolution discipline), `references/PHASE_PROTOCOL.md §3.2` (Ph2 admission preconditions), `reviews/classification.md` (`claim_coverage_threshold` parameter, `paper_type`, `p_stage`), `manuscript/<section>.md` (Ph1 draft body), `references/REFERENCES.md` (the pool SK-33 produces)
- **Sibling:** SK-33 `seed-snowball-discovery` (upstream — SK-34 audits the pool SK-33 produces); SK-35 `extend-snowball-incremental` (downstream — SK-34's BELOW_THRESHOLD verdict surfaces uncovered claims that SK-35 resolves at Ph2 from S4 onward); SK-12 `grounding-audit` (adjacent, not equivalent — SK-12 audits claim-source coupling at the rhetorical level; SK-34 audits the existence of resolving sources at the pool-membership level)
- **Not a replacement for:** SK-12 `grounding-audit` (SK-34 reads the pool to ask "is there a source that COULD resolve this claim?"; SK-12 reads the manuscript to ask "is the claim CITED to a source?"); the Evaluator's Step 4 in `run-phase-2` (which makes binding judgements on claim-source resolution; SK-34 produces an advisory map the Evaluator consumes as one input among many); a Class 1 verifier dispatch (SK-34 reads on-disk artefacts only — no Scholar Gateway probes, no Consensus probes; extension is SK-35's job)

### SK-35. `extend-snowball-incremental`
- **File:** `skills/extend-snowball-incremental/SKILL.md`
- **Pattern:** **Ph2 in-loop snowball micro-iteration anchored on a single uncovered claim** — read the target claim text + locus, the existing `references/REFERENCES.md` (anchor seed pool), and `reviews/classification.md` (`per_seed_cap_extend_snowball`, `max_iterations_extend_snowball` parameters; defaults 5 / 2). Select up to `per_seed_cap` anchor papers via lexical / claim-kind match (mirrors SK-34's source-mapping logic), run the SK-33 iteration body verbatim with narrowed admission criterion (target claim only, not the section claim register), and break on first non-zero admit. Fall back to a direct-claim Scholar Gateway probe when the anchor seed set is empty or both iterations zero-admit. Atomic-rename writes to REFERENCES.md `snowball` table only (NOT core corpus); appends one row to `reviews/snowball_log.md` and one Rule 7a row per admit to `reviews/external_verification_log.md`. Failure mode (zero admits across all sub-phases): writes a `[BLOCKER]` finding to the Evaluator's `ph2_findings_<date>_<cycle_id>.md` per architecture §5.1 row 3; Generator must downgrade the claim to Indirect tier or remove it. Auto-dispatched by `run-phase-2` Step 0.5 (per uncovered claim from SK-34's BELOW_THRESHOLD verdict) and by the Evaluator at Step 4 (per claim newly surfaced in the Generator's Ph1 draft); manually invokable via `/extend-snowball-incremental <claim>`.
- **Created:** 2026-04-27
- **Source:** v0.10.0 Stage S4 implementation per `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §§4.5, 5.1 SK-NEW-C, 5.2 Edit-2, 6.5` and `docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md §5.5`
- **Tier:** Package (executor — Sonnet; structured per-claim micro-iteration; bounded token budget via `max_iterations=2` + `per_seed_cap=5`)
- **Status:** Active (v0.10.0+)
- **Depends on:** `references/GROUNDING_PROTOCOL.md` (Rule 4 quote-before-attribute, Rule 6 no gap-filling, Rule 7a chain-of-verification per admit), `references/EXTERNAL_VERIFIERS.md §§1.5, 2, 3` (named Ph2 operationaliser of the wiki-first ladder per architecture §5.6), `references/PHASE_PROTOCOL.md §3.2` (Ph2 charter; admission grammar — SK-35 is advisory, not gating), `references/phase_state_schema.md §5` (atomic-write convention for REFERENCES.md), `reviews/classification.md` (`per_seed_cap_extend_snowball`, `max_iterations_extend_snowball` parameters), `references/REFERENCES.md` (anchor seed pool — must be non-empty), Class 1 verifiers (Scholar Gateway primary; Zotero+Scite for Class 2/3 resolution; Consensus when registered), `agents/planner.md §Phase 3.8` (canonical Ph2 dispatch contract; halt-vs-continue authoritative)
- **Sibling:** SK-33 `seed-snowball-discovery` (upstream — SK-35 extends the pool SK-33 produced); SK-34 `claim-coverage-audit` (upstream trigger — SK-34's BELOW_THRESHOLD verdict surfaces the uncovered claims SK-35 resolves; the audit's `## Uncovered` table is SK-35's input queue when auto-dispatched from `run-phase-2` Step 0.5); SK-12 `grounding-audit` (adjacent, not equivalent — SK-12 audits claim-source coupling at the rhetorical level after the pool is curated; SK-35 extends the pool itself); SK-36 `inherit-snowball-from-wiki` (orthogonal, S6 deliverable — operates at Ph1 pre-seed time, not Ph2 in-loop)
- **Not a replacement for:** SK-33 `seed-snowball-discovery` (SK-33 is saturation-focused with `rate < ε` stop rule across the section claim register; SK-35 is resolution-focused with single-claim early-break — different stop rules by construction); SK-34 `claim-coverage-audit` (SK-34 measures the coverage gap; SK-35 closes individual gaps one claim at a time); the Evaluator's Step 4 judgment (SK-35 surfaces *candidate* sources via lexical / claim-kind resolution; the Evaluator adjudicates whether each candidate resolves the claim under domain judgment per Rule 7a); a Class 2 / 3 verifier (SK-35 invokes Class 1 verifiers only; Class 2/3 fallback is at the Evaluator's discretion when a `[BLOCKER]` finding lands and the user accepts grey literature per architecture §7 R-3 mitigation)

### SK-36. `inherit-snowball-from-wiki`
- **File:** `skills/inherit-snowball-from-wiki/SKILL.md`
- **Pattern:** **Pre-seed inheritance from wiki graphify communities (Coupling E.3)** — at Ph1 pre-seed time, auto-invoked by SK-33 when `wiki_linked: true`, `inherit_snowball: true` (default for wiki-linked projects), and `graphify-out/graph.json` is fresh per SK-20 Precondition 3. Traverses `${wiki_path}/graphify-out/graph.json` (community membership) and `GRAPH_REPORT.md` (community labels and god-nodes) to identify graphify communities adjacent to the section's classification — adjacent if (a) community label overlaps with claim-register tokens above the synthesis-alignment threshold of architecture §5.5.3, OR (b) at least one god-node is a P-stage anchor in `classification.md`. Emits a `pre_seed.json` list (capped at `pre_seed_cap`, default 10) that SK-33 unions with its claim-derived seeds as the input to `SEED_FROM_CLAIMS`. One row written to `reviews/snowball_log.md` recording the pre-seed source. Pre-seed cannot dominate claim-derived seeds; SK-33's per-claim verification prunes pre-seeded papers that do not resolve actual claims, so over-seeding self-corrects across iterations.
- **Created:** 2026-04-27
- **Source:** v0.10.0 Stage S6 implementation per `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §§5.5.5, 6.8` and `docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md §5.6`
- **Tier:** Package (executor — Sonnet; on-disk reads only, no external API calls)
- **Status:** Active (v0.10.0+)
- **Depends on:** `references/EXTERNAL_VERIFIERS.md §1.5` (wiki-first ordering; SK-36 is the pre-seed predecessor in that chain); `reviews/classification.md` (`inherit_snowball` — wiki_linked-conditional opt-in, default true; `pre_seed_cap` — default 10); `${wiki_path}/graphify-out/graph.json` + `GRAPH_REPORT.md` (community structure and labels from a prior project's graphify run); `skills/graph-grounding-overlay/SKILL.md` SK-20 Precondition 3 (graph-staleness check — reused verbatim)
- **Sibling:** SK-33 `seed-snowball-discovery` (SK-36 is the pre-seed predecessor — SK-33 auto-invokes SK-36 when opt-in conditions hold; SK-36 pre-seeds the pool SK-33 then saturates); SK-35 `extend-snowball-incremental` (orthogonal — SK-36 operates at Ph1 pre-seed time; SK-35 operates at Ph2 in-loop for single-claim gap-closing)
- **Not a replacement for:** SK-33 `seed-snowball-discovery` (SK-36 pre-seeds; SK-33 saturates — when `inherit_snowball: true`, SK-36 runs first and SK-33 resumes from the pre-seeded pool, not from zero; SK-36 cannot replace the saturation iteration); manual cross-project curation (SK-36 uses graphify communities as a proxy for relevance — the proxy is useful but not equivalent to an expert selection of prior project sources)

### SK-37. `run-draft`
- **File:** `skills/run-draft/SKILL.md` (new at v0.15.0-pre PR-3b.3)
- **Pattern:** Public **draft** stage entrypoint (`stage=draft`). It routes to SK-25 `run-phase-1`, retained as the compatibility implementation body so old project scripts and slash history continue to resolve without creating a second public name.
- **Created:** 2026-05-12 (v0.15.0-pre PR-3b.3)
- **Tier:** Package
- **Status:** Active (public stage router)
- **Depends on:** `skills/run-phase-1/SKILL.md` (compatibility implementation body); `references/phase_state_schema.md §2.2` (the `stage` / `profile` shadow fields).
- **Sibling:** SK-25 `run-phase-1` (compatibility body); SK-38 `run-iterate`; SK-39 `run-finalize`. `/run-phase-2` is retained only as a compatibility route to `/run-iterate --profile refine`.

### SK-38. `run-iterate`
- **File:** `skills/run-iterate/SKILL.md` (new at v0.15.0-pre PR-3b.3)
- **Pattern:** Public **iterate** stage/profile router. Profiles are `refine`, `structural`, `deep`, and `stability`; legacy `/run-phase-2` routes here with `profile=refine`, legacy `/run-phase-3` routes here for the full iterate body, and legacy `/run-phase-3-stability` routes here with `profile=stability`. `skills/run-phase-3/SKILL.md` remains the compatibility body for full iterate semantics.
- **Created:** 2026-05-12 (v0.15.0-pre PR-3b.3)
- **Tier:** Package
- **Status:** Active (public stage/profile router)
- **Depends on:** `skills/run-phase-3/SKILL.md` (compatibility implementation body); `references/phase_state_schema.md §2.2`; `scripts/pre_phase_advance_check.py` (PR-3b.2 `W-MCR-CONVERGENCE-EVIDENCE` advisory reads the `profile:` field this vocabulary aligns with).
- **Sibling:** SK-26 `run-phase-3` (legacy full-iterate compatibility body); SK-29 `run-phase-2` (legacy refine compatibility router); SK-31 `run-phase-3-stability` (legacy stability compatibility router); SK-37 `run-draft`; SK-39 `run-finalize`.

### SK-39. `run-finalize`
- **File:** `skills/run-finalize/SKILL.md` (new at v0.15.0-pre PR-3b.3)
- **Pattern:** Public **finalize** stage entrypoint (`stage=finalize`). It routes to SK-27 `run-phase-4`, retained as the compatibility implementation body. MCR admission, G.4 sign-off, external-verifier requirements, and Reflector-full close-out remain binding.
- **Created:** 2026-05-12 (v0.15.0-pre PR-3b.3)
- **Tier:** Package
- **Status:** Active (public stage router)
- **Depends on:** `skills/run-phase-4/SKILL.md` (compatibility implementation body); `references/phase_state_schema.md §2.2`; `scripts/pre_phase_advance_check.py` (PR-3b.2 advisory at MCR boundary).
- **Sibling:** SK-27 `run-phase-4` (compatibility body); SK-37 `run-draft`; SK-38 `run-iterate`.

### SK-40. `grammar-mechanics-pass`
- **File:** `skills/grammar-mechanics-pass/SKILL.md` (new at 2026-06-28)
- **Pattern:** Blue Book grammar-and-punctuation **correctness** pass — mechanical scan (it's/its, comma splices, that/which, Oxford comma, compound-modifier hyphenation, number style) plus a judgment pass on subject–verb agreement and restrictiveness. Closes the gap where the harness owned sentence *craft* (SK via `sentence-level-pass`) and em-dash *discipline* (DETERMINISTIC §3) but had no standalone correctness/copyedit surface.
- **Created:** 2026-06-28 (three-manuals integration — `docs/superpowers/plans/2026-06-28-three-manuals-integration.md`)
- **Tier:** Package
- **Status:** Active
- **Pattern source:** `references/blue_book_grammar_guidelines.md §§1–7`
- **Depends on:** `references/blue_book_grammar_guidelines.md` (read-before-act prerequisite); `references/DETERMINISTIC_CHECKS.md` grammar-mechanics work queue (Phase-1 pre-filter); `research_notes/directives.md` `citation_style` (venue-sensitive precedence).
- **Non-overlap (deliberate):** defers em-dash policy to `EMDASH_BUNDLE_DISCIPLINE.md` / `DETERMINISTIC_CHECKS.md §3`; defers sentence craft to `sentence-level-pass` (Bacon); defers citation form to `turabian_chicago_guidelines.md` and citation *judgment* to `CITATION_DISCIPLINE.md`.
- **Sibling:** SK for `sentence-level-pass` (Bacon, craft) — this is the correctness counterpart.

### SK-41. `citation-format-pass`
- **File:** `skills/citation-format-pass/SKILL.md` (new at 2026-06-28)
- **Pattern:** Turabian/Chicago citation-**form** conformance — single-style consistency (notes-bibliography vs. author-date), note/bibliography/reference-list form, shortened-note discipline, parenthetical and block-quote citation placement, parenthetical↔reference-list orphan check. Closes the gap where the harness owned the *whether-to-cite* judgment (`CITATION_DISCIPLINE.md`) but had no *how-the-cite-is-rendered* surface.
- **Created:** 2026-06-28 (three-manuals integration PR-2 — `docs/superpowers/plans/2026-06-28-three-manuals-integration.md`)
- **Tier:** Package
- **Status:** Active
- **Pattern source:** `references/turabian_chicago_guidelines.md §§1–6`
- **Depends on:** `references/turabian_chicago_guidelines.md` (read-before-act prerequisite); `research_notes/directives.md` `citation_style` (selects NB vs. AD); declared-style precedence for shared mechanics (`turabian_chicago_guidelines.md §5`).
- **Non-overlap (deliberate):** orthogonal to `CITATION_DISCIPLINE.md` (form, not whether-to-cite); does not verify source existence (`EXTERNAL_VERIFIERS.md` / `GROUNDING_PROTOCOL.md`); defers shared mechanics conflicts to declared style via `[CONFLICT]`.
- **Sibling:** SK-40 `grammar-mechanics-pass` (shares the declared-style `[CONFLICT]` discipline on mechanics).

### SK-42. `analytic-move-audit`
- **File:** `skills/analytic-move-audit/SKILL.md` (new at 2026-07-01)
- **Pattern:** Targeted Abbott analytic-construction pass — audits the seven M-moves that assemble a claim (M-1 definitional deferral, M-2 reconstruct-then-dissolve, M-3 counterexample-as-demolition, M-4 anaphoric demonstration, M-5 cadential verdict, M-6 calibrated confidence, M-7 meta-reflexivity). Implements commitment **C-8**. Occupies the previously unclaimed **analytic-move layer** between `sentence-level-pass` (C-2, clause craft) and `IS-theory-pass` (C-4, static theory anatomy): C-4 audits whether the theory *has* the right parts; SK-42 audits whether those parts were *earned*.
- **Created:** 2026-07-01 (v0.20.0 — `docs/analysis/2026-07-01_abbott-system-of-professions-analytic-construction-and-C8-rationale.md`)
- **Tier:** Package
- **Status:** Active
- **Pattern source:** `references/analytic_construction_guidelines.md §2` (M-1…M-7 operational tests) + `§5` (P-stage gating, severity); Abbott, *The System of Professions* (1988).
- **Depends on:** `references/analytic_construction_guidelines.md` (read-before-act prerequisite); `reviews/classification.md` P-stage (gates the move set — P0/P1 restricts to M-3/M-5/M-6; P2 admits all seven).
- **Non-overlap (deliberate):** orthogonal to `IS-theory-pass` (SK-09, theory *anatomy* not move *dynamics*), `sentence-level-pass` (SK-07, clause craft not argument), and `narrative-structure-pass` (SK-08, whole-piece arc not the single move). Carries M-4/M-5 carve-outs that overturn a `sentence-level-pass` monotony/concision flag on demonstrative anaphora and cadential verdicts.
- **Sibling:** SK-13 `suchman-register-audit` (C-1 register) and the C-7 idiolect carve-out in SK-07/SK-08 — SK-42 is the convergent analytic-move counterpart to those voice-layer surfaces.

### SK-43. `definition-derivation-check`
- **File:** `skills/definition-derivation-check/SKILL.md` (new at 2026-07-01, v0.21.0)
- **Pattern:** Focused single-move pass on **C-8 / M-1 (definitional deferral)** — classifies each load-bearing term as *derived* (from the theory's questions), *imported* (cited, acceptable if motivated), or *stipulated* (fiat → finding), and applies the **C-6 upfront-glossary carve-in** (keys-only glossaries pass; a glossary that pre-states a *derived* construct's payoff is a `[MINOR — C-6↔C-8/M-1]` interaction note). The narrow, near-deterministic complement to SK-42's full pass.
- **Created:** 2026-07-01 (surfaced by the two-run live validation — the QE2026 reciprocity draft's upfront glossary sat exactly on the C-6↔M-1 seam).
- **Tier:** Package
- **Status:** Active
- **Pattern source:** `references/analytic_construction_guidelines.md §2 M-1` + `§5`; Abbott 1988.
- **Depends on:** `references/analytic_construction_guidelines.md` (read-before-act); `reviews/classification.md` P-stage — **P2-gated** (M-1 is a P2 move; reports out-of-scope at P0/P1).
- **Sibling:** SK-42 `analytic-move-audit` (bundled seven-move pass); SK-44 `dissolution-move-check` (the M-2 companion).

### SK-44. `dissolution-move-check`
- **File:** `skills/dissolution-move-check/SKILL.md` (new at 2026-07-01, v0.21.0)
- **Pattern:** Focused single-move pass on **C-8 / M-2 (reconstruct → locate buried assumption → dissolve)** — scores each rival-engagement site on three components (charitable reconstruction / named buried assumption / dissolution vs. mere contradiction) and flags strawman (`[MAJOR]`) and contradiction-without-dissolution (`[MINOR]`/`[MAJOR]` by centrality). Rewards the Abbott shape of relocating a dispute one level up.
- **Created:** 2026-07-01.
- **Tier:** Package
- **Status:** Active
- **Pattern source:** `references/analytic_construction_guidelines.md §2 M-2` + `§5`; Abbott 1988.
- **Depends on:** `references/analytic_construction_guidelines.md` (read-before-act); `reviews/classification.md` P-stage — **P2-gated** (a P1 piece that holds rival positions open is doing correct non-convergence, not failing M-2; reports out-of-scope at P0/P1).
- **Sibling:** SK-42 `analytic-move-audit`; SK-43 `definition-derivation-check`.

### SK-45. `turabian-format-pass`
- **File:** `skills/turabian-format-pass/SKILL.md` (new at 2026-07-01)
- **Pattern:** Turabian/Chicago **document-format** conformance pass against **Appendix A (Paper Format and Submission)** — heading-level hierarchy and per-level consistency, front-matter presence and order, title-page elements, table/figure numbering + caption + in-text-callout + source placement, and a deferred physical-layout checklist (margins, spacing, pagination, submission format). Closes the coverage gap identified in the 2026-07-01 D-STYLE/Turabian presentation audit, where `turabian_chicago_guidelines.md §6` demoted the entire Appendix to "pointers" with no enforcing skill. Deliberately **structure-and-consistency only**: it defers absolute physical values to the manual and any venue template rather than asserting measurements the Markdown source cannot carry.
- **Created:** 2026-07-01.
- **Tier:** Package
- **Status:** Active
- **Pattern source:** `turabian_chicago_guidelines.md §6`; Turabian, *A Manual for Writers*, Appendix §§A.1–A.3.
- **Applicability gate:** `d_style_profile.harness_profile` — in scope for `thesis_qe` and Chicago/Turabian course papers; under `venue_submission` the `venue_template_precedence` obligation (`scripts/d_style_profile_check.py`) reduces the pass to venue-independent structure. Reads `citation_style` (now including `turabian_notes_bibliography`, added 2026-07-01) to confirm the declared style.
- **Orthogonality:** citation *form* is SK-05-lineage `citation-format-pass`; grammar mechanics is `grammar-mechanics-pass`; heading *signposting* (C-5) is `accessibility-overlay`. This pass owns heading *structural well-formedness* and table/figure *placement*, and hands off anything outside that boundary.
- **Sibling:** `citation-format-pass` (the form/format split within the Turabian authority); `grammar-mechanics-pass`; `accessibility-overlay`.

### SK-46. `repin-register`
- **File:** `skills/repin-register/SKILL.md` (new at 2026-07-14, exemplar ingestion extended at v0.29.0)
- **Pattern:** Orchestrates the single authoritative semantic-pin compute path in `scripts/reader_accessibility_policy.py --repin`: lock and scoped-dirt preflight, one-snapshot graph/wiki resolution, first-class delta report, no-delta audit event or explicitly confirmed atomic profile patch, package ledger/derived view, and optional project rebind request. It never hashes independently, never writes `phase_state.json`, and never moves the yardstick inside an open cycle.
- **Created:** 2026-07-14 from the accepted `/repin-register` architecture and the v0.28.0 domain-native register pin contract. v0.29.0 adds exact-key exemplar admission/drop, singleton-role locks, scope-aware surface/argument routing, and criterion-9 fixtures without touching live corpora.
- **Tier:** Package
- **Status:** Active
- **Depends on:** `references/policies/reader_accessibility.v1.json`, `references/schemas/reader_accessibility_profile.schema.json`, `scripts/reader_accessibility_policy.py`, and Planner sole-writer enforcement.
- **Trigger:** Milestone transition, grounded-source-admitting snowball round, MF-POLICY semantic-pin discovery, or explicit manual package maintenance.
- **Sibling:** SK-20 `graph-grounding-overlay` (may surface corpus changes); SK-25/26/27 phase skills (consume Planner-applied bindings, never the pending request directly).

### SK-47. `centroid-pass`
- **File:** `skills/centroid-pass/SKILL.md` (new 2026-07-19)
- **Pattern:** Public, read-only orchestration. A deterministic packet binds the live policy, pins, members, warrant views, exact text scope, hashes, and derivation; the Generator or Evaluator then performs the grounded semantic generation, review, or revision pass.
- **Created:** 2026-07-19; promoted after the deterministic packet, all-drafts governance contract, and behavioral integration evidence were installed.
- **Tier:** Package
- **Status:** Active; mandatory within academic draft generation, evaluation, and revision orchestration.
- **Depends on:** `references/policies/reader_accessibility.v1.json`, `references/policies/draft_governance.v1.json`, `scripts/centroid_service.py`, `scripts/draft_governance.py`, and `references/GROUNDING_PROTOCOL.md`.
- **Trigger:** Every M1-M4/FINAL draft or revision, or explicit `/centroid-pass`.
- **Sibling:** SK-46 `repin-register` (the only pin-motion path); `accessibility-overlay` Sub-check H (the existing governed review surface).

---

## Planner intents (not slash commands)

These natural-language intents appear in the Planner dispatch contract but have
no skill file and are not advertised by `/plugin-commands`. They are retained
here only so Planner and Evaluator prose can name the behavior without implying
an installed command surface.

### INTENT-1. Review
- **Dispatch target:** Planner Phase 2.5 command table.
- **Pattern:** Default phase-agnostic review command. The Planner resolves scope precedence (1. `--section <heading-path>`, 2. `--subsection <heading-path>`, 3. most recent change per heading-path lookup, 4. first unlocked section below the applicable ceiling, 5. all-at-ceiling report) and then dispatches the matching `run-phase-N` skill per the section's `current_phase` in `reviews/phase_state.json`. The retired Confirmation Mode shortcut path is no longer attempted.
- **Sibling:** `/run-draft`, `/run-iterate`, and `/run-finalize` are the explicit public lifecycle commands.

### INTENT-2. Review letter
- **Dispatch target:** Planner Phase 2.5 command table; resolves to SK-11 `response-letter-review`.
- **Pattern:** Entry point for response-letter review. The retired T3R sibling ladder is no longer invoked; instead, response letters classify as manuscript-class artifacts under the Lifecycle-Phase Ladder per `paper_type` and phase declarations in `reviews/classification.md`. Escalation-out rules per `PHASE_PROTOCOL.md` apply when the response letter triggers a Ph4 Finalize & Close manuscript pass.

### INTENT-3. Cancel climb
- **Dispatch target:** Planner Phase 5.5 post-approval and Phase 6 Manuscript Convergence Report cycles.
- **Pattern:** User-initiated cancellation of an in-flight climbing cycle (MCR section-by-section advance, Ph4 admission sequence, or multi-section ladder advance). Updates `reviews/phase_state.json` with `trigger: mcr_climbing_cancelled` in `phase_entry_log` (renamed from `laggard_clearance_cancelled`); preserves `last_approved_phase` so no work is lost. Grounding: `PHASE_PROTOCOL.md`.

### INTENT-4. Raise ceiling
- **Dispatch target:** Planner Phase 2.5 command table; writes to `reviews/phase_state.json`.
- **Pattern:** User-initiated upward revision of the applicable ceiling on a section, either by raising `section_ceiling_override` (per-section) or by raising `default_final_phase` (manuscript-wide). Emits `trigger: ceiling_raised` in `phase_entry_log`. The converse operation — locking a section at a lower ceiling — happens automatically on approval at that phase; cancel-climb intent cannot lower the ceiling.

---

## Skill Retirement Criteria

A skill should be retired (moved to the Retired Skills section below) when **any** of the following conditions is met:

| Criterion | Description | Who decides |
|---|---|---|
| **R1 — Superseded** | A newer skill covers the same pattern with equal or greater coverage. The older skill adds no unique value. | Reflector proposes; user approves |
| **R2 — Absorbed into pipeline** | The check or workflow encoded by the skill has been incorporated into the core review pipeline (REVIEW_ORCHESTRATION.md or SAFEGUARD_LAYER.md) and the standalone skill is redundant. | Reflector proposes; user approves |
| **R3 — Pattern extinct** | The recurring error the skill was built to catch no longer appears in reviews (zero hits across 5+ consecutive rounds or 3+ projects). The pattern has been internalized. | Reflector detects; user confirms |
| **R4 — Eval regression** | The skill's eval benchmark score drops below 60% accuracy, indicating the skill prompt has drifted out of alignment with the current package rules. | Reflector detects during eval; user decides whether to fix or retire |
| **R5 — User directive** | The user explicitly retires the skill. | User decides |

**Retirement procedure:**

1. The Reflector moves the skill's registry entry from "Active skills" to "Retired skills" below.
2. The Reflector adds the retirement date, the criterion triggered (R1–R5), and a brief reason.
3. The skill file is **not deleted** — it is moved to `skills/retired/` (or `skills/packaged/retired/` for .skill files) for reference.
4. If the skill is later needed again, it can be restored by reversing these steps.

---

## Retired skills

### SK-05. `run-full-review` — retired 2026-04-19 (v0.5.1)
- **Criterion triggered:** R1 — Superseded. SK-26 `run-tier-standard` (T3) and SK-27 `run-tier-submission` (T4) together cover the same behaviour with explicit tier binding. SK-05's only role at v0.5.0 was a transitional alias that dispatched to SK-26 or SK-27 based on the classification record's `tier:` field.
- **Original file:** `skills/run-full-review/SKILL.md` (removed from the v0.5.1 tree; deprecation preserved in v0.5.0's release artifact).
- **Reason:** The old name was ambiguous across T3 and T4 once the six-tier Incremental Tier Protocol replaced the three-value `review_depth` vocabulary. Visible aliasing at v0.5.0 surfaced the deprecation on every invocation; v0.5.1 completes the rename by removing the alias.
- **Migration path:** Use `run-tier-standard` for the T3 procedure and `run-tier-submission` for the T4 procedure. `classify-manuscript` writes the `tier:` field directly; no depth translation is required in new projects. Legacy `review_depth` values in archived v0.4.x classification records still read under the v0.5.0 transitional read-path; at v0.5.1 the read-path is also retired (see `TIER_PROTOCOL.md §10`).

### SK-28. `eygp-framework-checker` — retired 2026-04-20 (v0.7.0)
- **Criterion triggered:** R5 — User directive (release-gate WARN on 2026-04-20 flagged the skill for pruning during the v0.6.0 → v0.7.0 transition).
- **Original file:** `skills/packaged/packaged/eygp-framework-checker.md` (plus the `.skill` sibling). Both stubs were **removed** at the v0.7.0 sweep, following the v0.5.2 precedent for retired packaged-only stubs (see the v0.5.2 README Version block where `skills/packaged/run-full-review.skill` was removed for the same reason — packaged-only stubs with no canonical-directory counterpart are pruned rather than moved, to keep the shipped bundle free of dead surfaces). The Retired-Skill Procedure's default move-to-`retired/` path applies to skills with a canonical `skills/<name>/` directory; packaged-only stubs are removed.
- **Reason:** The EYgp six-axis cross-check coverage goal has not manifested as a recurring reviewer need across projects, and the skill's dependency on the non-distributed workbook (`references/EYgp_Research_process_and_artifacts.xlsx`) created a brittle contract that did not justify its maintenance cost. SK-10 `p-stage-checker` retains the P-axis coverage that projects actually invoke.
- **Migration path:** Use SK-10 `p-stage-checker` for the P-axis (P0 / P1 / P2) subset. Cross-axis auditing is not currently an active requirement; if a future project needs the removed stub's prose, recover from git history at tag `v0.6.0` (the stub was live through v0.6.0 and retired at v0.7.0) and re-register under a new SK-NN identifier rather than un-retiring SK-28.

<!-- Template for retired entries:

### SK-XX. `skill-name` (RETIRED)
- **File:** `skills/retired/skill-name.md`
- **Original creation:** <date>
- **Retired:** <date>
- **Criterion:** <R1–R5>
- **Reason:** <why retired>

-->

---

## How the Reflector creates new skills

See `agents/reflector-closeout.md` Phase 4 (Skill Development). Summary:

1. **Identify the pattern.** A recurring error, check, or workflow that appeared in 2+ rounds or 2+ projects.
2. **Determine the tier.** Package, project, or global?
3. **Draft the skill file** using the template in §Skill template above. Include frontmatter (`name`, `description`, `trigger`, `created_by: Reflector`, `created_from`, `pattern_source`, `version`) and a self-contained body that specifies what to read, what to check, what to output, and what NOT to do.
4. **File a plugin-update proposal** in `reviews/plugin_update_proposals.md` (net-new at v0.7.0; full-mode Reflector only). The proposal is routed through the Planner's three-filter gatekeeper (evidence-adequacy / non-duplication / tier-appropriateness) before the user sees it. The Reflector proposes raw; the Planner filters; the user decides.
5. **Register the approved skill** in the §Active skills section above, assigning the next available SK-NN identifier. SK-NN identifiers are stable across version transitions — when a skill is rewritten in place (as with the v0.7.0 rewrites of SK-25/SK-26/SK-27/SK-29), the identifier is preserved and only the description text changes.
6. **Retirement path** is symmetric: see the §Skill Retirement Criteria table for R1–R5 triggers and the retirement procedure below the table. Retired entries move to §Retired skills with a dated retirement note; the skill file moves to `skills/retired/` (or `skills/packaged/retired/`) rather than being deleted.
