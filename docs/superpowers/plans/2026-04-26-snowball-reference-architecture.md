<!-- scholar-gateway-contract: v0.1 -->

# Architectural Plan — Snowball-Driven Reference Scaffolding for Ph1 / Ph2

> **Status.** Architectural plan (deliverable form: AS-IS evaluation + TO-BE architecture + refinement ladder). No skill files modified by this document; implementation lives in successor patches sequenced per §6.
>
> **Author:** Drafted under the v0.9.0 maintenance session, 2026-04-26.
> **Theoretical lens:** Goal-Oriented Requirements Engineering (GORE; Yu 1995, van Lamsweerde 2009) over the i\* Strategic Dependency / Strategic Rationale frame, with Agent-Oriented Requirements Engineering (AORE) decomposition into agent roles, dependencies, and softgoal contributions.
> **Locus:** Phase 1 (Plan & Draft) and Phase 2 (Review & Revise) of the v0.7.4 Lifecycle-Phase Ladder.
> **Substrate:** v0.9.0; `references/GROUNDING_PROTOCOL.md` (Rule 7a binding); `references/EXTERNAL_VERIFIERS.md` (Class 1/1.5/2/3 registry; §1.5 wiki-first discovery ordering).

---

## 1. Problem Statement

The harness's grounding apparatus is **resolution-complete and discovery-impoverished**. Rule 7a (`GROUNDING_PROTOCOL.md`) and the four-class verifier registry (`EXTERNAL_VERIFIERS.md` §2) furnish a binding chain-of-verification for citations *that already exist in the project's `references/REFERENCES.md`*. Class 1 verifiers (Scholar Gateway, Consensus, Zotero+Scite) close the `[UNVERIFIED]` → `[externally verified]` loop with a logged audit trail. The Reflector's Phase 2.5 grounding audit spot-checks the chain. SK-15 (`backfill-source-stubs-from-references`) materialises wiki-side source stubs from a curated REFERENCES.md, and SK-16 (`retrofit-concept-grounding`) closes Coupling B by retrofitting concept pages with wikilinks. The downstream pipeline assumes the inbound corpus is given.

**The corpus is not given.** No skill in the harness produces `references/REFERENCES.md` from the manuscript's intended claim set. The `core corpus + snowball + cited-via` table convention is *documented* (SK-15's input contract; the INF3006Y_AgencyDelegation pilot referenced by SK-15 §Preconditions) but no skill mechanises the procedure that fills those tables. The Generator at Ph1 drafts under the declared P-stage register and is bound by Rule 4 (quote-before-attribute) and Rule 6 (no gap-filling), but has no skill-level procedure for *constructing* the evidence pool a P0 / P1 / P2 register requires. The Evaluator does not engage at Ph1 (`run-phase-1` §2: "Not dispatched at Ph1"); the first reference-adequacy adjudication is therefore deferred to Ph2 Step 4 (`run-phase-2` §4 step 4), at which point the section's prose is already drafted against a corpus the harness never authoritatively assembled.

The structural consequence: **reference adequacy** — the softgoal that *every claim made in the manuscript is supported by a traceable, externally verifiable source* — is asserted as a hard requirement by `GROUNDING_PROTOCOL.md` Rule 4 and operationalised at *resolution* time, but is left to ad-hoc human curation at *discovery* time. The snowball method (Wohlin 2014; Greenhalgh & Peacock 2005) is the canonical answer to the discovery-time problem, and it is precisely what the harness currently delegates to the user and to the Generator's drafting intuition without procedural support.

This plan proposes the architectural refinement that closes the discovery-time gap without weakening any existing resolution-time guarantee.

---

## 2. Theoretical Framework — i\* SR Model of Reference Adequacy

The intentionality the system must operationalise is *every claim is grounded in a source the agent has read or has logged a Class 1 external verification for*. This is a softgoal in the strict GORE sense — its satisficing is graded, not binary, and depends on contributing tasks whose output can be measured.

### 2.1 Strategic Dependency (SD) shape

The agent network for reference work has four actors, three of which are software agents and one is the human author. The human author depends on the **Planner** for *evidence-coverage adequacy as a precondition for Ph2 admission*. The **Planner** depends on a (currently absent) snowball-discovery skill for *the saturated evidence pool that the Generator will draft against*. The **Generator** depends on the evidence pool for *attributable sources for every drafted claim* (Rule 4 compliance). The **Evaluator** at Ph2 depends on the evidence pool for *resolvable citations during Step 8 synthesis* (the only step at which Ph2 invokes external verifiers per `agents/evaluator.md`); when the pool is impoverished, the Evaluator's BLOCKER-citation findings cascade into Generator re-work that the snowball-discovery skill should have absorbed at Ph1.

The SD graph at Ph1 / Ph2 today carries a missing dependency: the Planner has no software dependee for the evidence-pool resource. The current implicit dependee is the human author, which transfers what should be a software-agent task to a human under unmonitored coverage criteria. The TO-BE plan introduces the missing dependee as a triad of new skills (§5).

### 2.2 Strategic Rationale (SR) decomposition of the softgoal

```
                  Softgoal: ReferenceAdequacy
                 (every claim → traceable source)
                        |
        +---------------+---------------+
        |               |               |
   Task: Seed     Task: Saturate    Task: Verify
   (assemble      (extend by         (each in-pool
    initial        snowball until    claim resolves
    references)    new-rate < ε)     under Rule 7a)
        |               |               |
        v               v               v
+----------+    +-------------+    +----------+
| §1.5     |    | Backward:   |    | Class 1  |
| wiki     |    | bibliogr.   |    | verifier |
| → Zotero |    | of seeds    |    | hit; log |
| → Class1 |    | + ancestors |    | row in   |
+----------+    +-------------+    | external_|
                | Forward:    |    | verifi-  |
                | citing      |    | cation_  |
                | papers from |    | log.md   |
                | seeds       |    +----------+
                +-------------+
```

Three contributing tasks operationalise the softgoal:

1. **Seed assembly** — produce an initial reference set covering the section's declared P-stage scope. Mechanism: the existing `EXTERNAL_VERIFIERS.md §1.5` wiki-first discovery order. The seed set is the union of (a) wiki sources resolving to the section's planned concepts, (b) Zotero library hits on the claim keywords, and (c) Scholar Gateway / Consensus hits when (a)+(b) are insufficient. The seed set is the input to snowball iteration, not the final corpus.

2. **Snowball saturation** — iteratively extend the seed set by backward and forward citation chasing until the new-paper rate per iteration falls below a stopping threshold ε. Backward snowball (Wohlin 2014 Step 2) reads the bibliography of each seed and admits cited papers whose title/abstract resolve a section claim. Forward snowball (Wohlin 2014 Step 3) finds papers that cite each seed and admits those whose title/abstract resolve a section claim. The saturation condition `new_admitted_per_iteration / total_admitted < ε` is the empirical stop rule (Greenhalgh & Peacock 2005 §Saturation; Wohlin 2014 §Stopping criteria).

3. **Per-claim verification** — for every claim the Generator drafts at Ph1, confirm at least one source in the saturated pool resolves the claim under Rule 7a. This is the *coverage check* that produces the Ph1 → Ph2 admission signal (§5.2).

### 2.3 Why snowball, and why not alternatives

The snowball method is preferred over keyword-only search (PubMed-style) for the harness's research register because (a) it surfaces the *citation neighbourhood* of seed papers, which captures the disciplinary conversation the manuscript participates in — Mashkoor et al. (2022) report, on the strength of Wohlin's methodology, that "the possibility of noise in snowballing is less than using a digital library approach, and, by deduction, snowballing is a better approach than a digital library search for extending literature studies" (`10.1002/smr.2457`, chunk 24, externally verified via Scholar Gateway in §3.4); (b) it preserves the logical structure of the literature — seeds anchor claims, snowball-1 anchors mechanism, snowball-2 anchors counter-arguments — which maps directly onto the P0/P1/P2 register the harness uses for claim-maturity (`reviews/classification.md`); (c) the procedure halts on a measurable saturation criterion rather than an arbitrary corpus cap, aligning with the falsifiable convergence rationale the v0.7.4 Ph3 ladder already operationalises elsewhere.

The trade-off — snowball is recall-biased and may admit citations that are not load-bearing — is mitigated by the per-claim verification step, which prunes admitted papers to the subset that resolves a section claim.

---

## 3. AS-IS Evaluation — Current Reference-Handling Surface

### 3.1 Skill-level audit at Ph1 / Ph2


| Skill / Document | Reference-handling role at Ph1/Ph2 | Gap relative to snowball softgoal |
|---|---|---|
| `skills/run-phase-1/SKILL.md` | Steps 1–12 cover preflight, i\* SD/SR (conditional), P-stage declaration, diff scoping, Generator dispatch, deterministic checks, Rule 1 scope check, Reflector probe, exit artefact, advance check, user approval. | **No reference-construction step.** REFERENCES.md is assumed to exist; if absent, the Generator drafts under Rule 4 / Rule 6 markers without an evidence pool to discharge them against. |
| `skills/run-phase-2/SKILL.md` | Step 4 (Evaluator Steps 1–3 + checklist) runs grounding checks; §9 explicitly excludes "external-verifier probing (Zotero / Scholar Gateway / register-specific passes)" at Ph2 — deferred to Ph3 (optional) and Ph4 (required). | **Reference adequacy is not adjudicated at Ph2.** Ungrounded claims surface as Evaluator findings on prose, not as reference-pool gaps; the remediation is Generator prose edits, not pool extension. |
| `skills/backfill-source-stubs-from-references/SKILL.md` (SK-15) | Reads an existing `references/REFERENCES.md` (core/snowball/cited-via tables) and produces wiki source stubs. Coupling A-revised. | **Downstream of snowball, not the producer.** SK-15 §Preconditions requires REFERENCES.md "in the format established by INF3006Y_AgencyDelegation (source-root aliases + core corpus table + snowball table + cited-via table)." Nothing in the harness produces those tables. |
| `skills/retrofit-concept-grounding/SKILL.md` (SK-16) | Surgical wikilink retrofit on existing concept pages. Coupling B. | **Downstream of SK-15, doubly downstream of REFERENCES.md.** Operates on pages that already cite sources; does not discover. |
| `skills/grounding-audit/SKILL.md` (sub-of-Reflector) | Eight-category audit including citation audit (Cat 1), metric audit (Cat 2), path audit (Cat 3), rule-citation (Cat 4), gap-fill (Cat 5), marker (Cat 6), Rule 7a annotations (Cat 7), graph-grounding (Cat 8). | **Adversarial only.** Detects ungrounded claims after they are written. The audit is a backstop, not a corpus builder. |
| `skills/graph-grounding-overlay/SKILL.md` (SK-20) | Surfaces graph-extracted / graph-inferred / graph-stub finding categories from the `graph.json` corpus knowledge graph. | **Complementary, not substitutive.** §Closing of `EXTERNAL_VERIFIERS.md` §7 explicitly notes the graph is "not a Class 1 verifier"; it tells you what the graph *knows about*, not what the external bibliographic record contains. |
| `references/GROUNDING_PROTOCOL.md` Rule 4 | "No agent may attribute a position to an author without being able to point to the specific passage in a source the agent (or a prior agent in the chain) has actually read." | The rule is binding but presupposes the corpus exists. Rule 6 (no gap-filling) instructs the Generator to write `[FACT NEEDED]` markers when sources are absent — but this externalises the gap to a future round rather than driving the snowball that would close it. |
| `references/EXTERNAL_VERIFIERS.md` §1.5 | Wiki-first discovery ordering (wiki → Zotero → external Class 1) when `wiki_linked: true` and the round may introduce new references. | **The procedural skeleton for discovery exists, but no skill executes it.** §1.5 mandates the *order* in which discovery sources are consulted; it does not mandate *when* (which phase, on which trigger) the discovery occurs. The trigger is currently implicit in the Generator's drafting work and the Evaluator's Step 8. |
| `reviews/external_verification_log.md` | Append-only ledger of Class 1 / Class 3 verifier hits. Resolution-time audit trail. | The ledger captures *what was verified*; there is no companion ledger for *what was discovered* (which seed yielded which snowball-1 admittance, which iteration saturated, what the new-rate was at stop). Absence of this ledger means snowball provenance is unrecoverable from artefacts alone. |


### 3.2 Phase-contract audit

**Ph1.** The reference-related sub-steps inside `run-phase-1` are confined to:
- Step 4 (P-stage declaration) — reads `reviews/classification.md`; does not touch references.
- Step 6 (Generator dispatch) — the Generator drafts under Rule 4 / Rule 6 with whatever `references/REFERENCES.md` happens to be present; if absent, the Generator marks `[FACT NEEDED]` and proceeds.
- Step 8 (Rule 1 full-file scope check) — verifies *citations the Generator wrote* trace to read sources; does not survey *which sources should have been read*.

**Ph2.** The reference-related sub-steps inside `run-phase-2` are confined to:
- Step 4 (Evaluator Steps 1–3) — judgment-based, no external-verifier calls.
- Step 5a (SAFEGUARD subset) — Check 5 (Edit Traceability) verifies that edits cite rules; not sources.
- §9 (What this stage does NOT do) — explicit exclusion of external-verifier probing.

The Evaluator's Step 8 *does* invoke Class 1 verifiers for BLOCKER-severity citation findings (`agents/evaluator.md` §"How agents invoke verifiers"), but Step 8 is a **synthesis** step that runs *after* the local pass concludes. By that point the Generator has already drafted prose against an unbuilt corpus.

The phase contract is therefore consistent: at no point in the Ph1 → Ph2 trajectory does any agent accept the snowball-construction task as their own. It falls between agent boundaries.

### 3.3 Diagnosed gap

The gap is **not** a missing rule — Rule 4 and Rule 7a together are sufficient as an integrity floor. The gap is a missing **task contributing to the softgoal at the discovery layer**: no software agent is responsible for *producing the saturated evidence pool* before the Generator drafts Ph1 prose, and no software agent is responsible for *extending the pool* when the Evaluator's Ph2 pass surfaces an ungrounded claim. The Reflector's grounding audit detects the symptom (ungrounded claim) without the apparatus to drive the cure (extend the corpus).

This is the architectural problem the refinement plan addresses.

### 3.4 Scholar Gateway verified capability brief

Scholar Gateway is the primary Class 1 verifier under `EXTERNAL_VERIFIERS.md` §2 and is the load-bearing infrastructure for SK-NEW-A (seed phase, when the wiki and Zotero do not cover the section's claim register) and SK-NEW-C (per-claim micro-iteration). The plan rests on Scholar Gateway's reachability and on its response shape; both were probed in the drafting session and the findings recorded here so SK-NEW-A's implementation can build against observed behaviour rather than assumed behaviour.

**Probe verdict.** Reachable. The runtime tool name is `mcp__70599628-0640-490e-bb1b-450b0e8248a9__semanticSearch`. The directory UUID is `ff091334-0f12-4d0e-a973-c00467dd3818` (per `EXTERNAL_VERIFIERS.md` §7). A representative query (`snowball sampling method for systematic literature review in software engineering, including stopping criteria and saturation`, top-5) returned five passages from three unique articles in the 2021-03-19 to 2022-05-26 date window, with the corpus content-freshness disclosure dated February 2026.

**Response payload schema (verified at probe time).** `scholar_gateway.response_payload` v0.1. Top-level keys observed:

```
{
  "schema": "scholar_gateway.response_payload",
  "version": "0.1",
  "tool": "semanticSearch",
  "type": "results",
  "provenance": { source, retrieved_at, query_as_executed,
                  result_count, unique_articles, pub_date_range,
                  disclosures[] },
  "render_contract": { schema, version, per_search_disclosure,
                       gaps_and_limitations, citation_presentation,
                       session_footer },
  "results": [ { chunk_index, metadata{ journal_code, article_type,
                                        pub_type, journal_issn,
                                        additionalMetadata{ volume, citationLine,
                                                            issue, link, isRetracted,
                                                            publisher, abstract, title,
                                                            isOpenAccess, publicationDate,
                                                            journalTitle },
                                        total_chunks },
                 rrf_score, rerank_score, id, text, doi } ]
}
```

The `text` field carries the passage prose verbatim from the source document; under Rule 4 (quote-before-attribute), this text — not the abstract — is the legitimate source of an attribution to a specific claim. The `metadata.additionalMetadata.isRetracted` flag exposes the Scite retraction signal at the chunk level (Class 3 verifier integration; binding under Rule 7a per `EXTERNAL_VERIFIERS.md` §2 Class 3). The `id` field is `<doi>_<chunk_index>` and is stable across queries; SK-NEW-A's snowball admission record should key on `doi` rather than on `id` to deduplicate across chunks.

**Render contract (binding per `EXTERNAL_VERIFIERS.md` §3.1).** Every artifact that incorporates Scholar Gateway results must:

1. Carry the top-of-file marker `<!-- scholar-gateway-contract: v0.1 -->` (this plan does, line 1).
2. Render a per-search provenance line at the point of synthesis: `Scholar Gateway · <query_as_executed verbatim> · <N> passages · <N> articles · <YYYY-MM-DD>–<YYYY-MM-DD>`. Counts and date range are copied from `provenance.{result_count, unique_articles, pub_date_range.earliest, pub_date_range.latest}`.
3. Cite substantive claims drawn from results inline with author-year + DOI hyperlinks, deduplicated across chunks.
4. Render the static session footer **once per response**, not per search, at the end of any response that consumed Scholar Gateway results. The footer's `Last corpus update` date is copied from `provenance.disclosures[type=content_freshness]`.

The Reflector's Phase 2.5 audit spot-checks compliance: a missing per-search provenance line is a Category 9 MAJOR finding; a missing session footer is a Category 9 BLOCKER (`EXTERNAL_VERIFIERS.md` §3 Reflector clause).

**Parameter shape (binding for SK-NEW-A and SK-NEW-C).** The `semanticSearch` tool requires three parameters and accepts five optional. SK-NEW-A and SK-NEW-C must set them as follows:

- `query` (required, string) — natural-language claim or seed-paper-relation phrasing; do **not** reduce to keywords. Acronyms and short / polysemous terms must be expanded.
- `interaction_id` (required, UUID) — generated **once per snowball iteration**, reused across all `semanticSearch` calls within that iteration. *Not* per seed paper, *not* per claim. The reuse-across-an-iteration convention coalesces backward and forward sub-queries under a single billable interaction and aligns with the tool's contract for "parallel/follow-up searches in the same episode" (`EXTERNAL_VERIFIERS.md` §2 Scholar Gateway parameter note).
- `inferred_intent` (required, free-text) — the *underlying information need* (e.g., "extending backward snowball from seed Wohlin 2014 to identify the methodological basis of saturation criteria"), not the query itself.
- `start_year` / `end_year` (optional) — set when the section's classification implies a relevance window (e.g., post-2020 ML literature for an ML survey).
- `includeRetractedContent` (optional, default `false`) — keep `false` for snowball admission; flip only when retraction history is itself the section's subject.
- `topN` (optional, default 15; max 20) — SK-NEW-A's seed phase uses `topN=15`; SK-NEW-C's micro-iteration uses `topN=5` to control token cost on the per-claim path.

**Observed result quality on the probe.** All five returned passages were on-topic; `rrf_score` and `rerank_score` for the top result were 0.00819 and 0 respectively (the rerank-score-zero pattern across all results suggests the rerank stage was not engaged for this query — possibly a token-cost optimisation by the gateway when relevance is unambiguous; SK-NEW-A should not rely on `rerank_score` magnitude as a quality signal). The top hits include Mashkoor et al. 2022 (`10.1002/smr.2457`) and the Wohlin et al. 2021 follow-on (`10.1002/smr.2345`), both citing Wohlin's snowballing guidelines as their methodological basis. Barros-Justo et al. 2021 (`10.1002/smr.2370`) reports an empirical forward-snowball iteration trace — three iterations yielding 3039 → 601 → 26 candidate papers, a per-iteration admission decay of 0.197 → 0.043 — which is the saturation evidence that replaces the training-memory figures originally proposed in §4.3.

**Verification log entry that this probe would write** (in a project context, against `reviews/external_verification_log.md`):

```markdown
| 2026-04-26 | Architecture-plan author | Scholar Gateway availability + snowball-method anchor | Scholar Gateway | "snowball sampling method for systematic literature review in software engineering, including stopping criteria and saturation" | 10.1002/smr.2457 ; 10.1002/smr.2345 ; 10.1002/smr.2370 | Mashkoor 2022 ; Wohlin 2021 ; Barros-Justo 2021 | MATCH (3 unique articles) |
```

This row format is the canonical Rule 7a artefact; SK-NEW-A's implementation must emit one row per snowball admission, and SK-NEW-C must emit one row per micro-iteration that admitted at least one paper.

---

### 3.5 LLM Wiki collaboration: AS-IS surface and the discovery-layer asymmetry

The harness ships five wiki couplings, registered in `references/PROJECT_BOOTSTRAP.md §4` and `references/AGENT_ORCHESTRATION.md §8.5–§8.6`. Their *direction* and *timing* together expose a structural asymmetry that the snowball-driven reference architecture must address.


| Coupling | Skill | Direction | Timing in pipeline | Stage |
| --- | --- | --- | --- | --- |
| A-revised | SK-15 `backfill-source-stubs-from-references` | harness → wiki (push) | post-REFERENCES curation | downstream of citation work |
| B | SK-16 `retrofit-concept-grounding` | wiki ↔ wiki (in-place) | post-SK-15 | downstream |
| C | SK-14 `promote-lessons-to-wiki` | harness → wiki (push) | post-round | downstream |
| D | SK-17 `ingest-m5-to-wiki` | harness → wiki (push) | M5 close-out | terminal |
| E.2 | SK-20 `graph-grounding-overlay` | wiki → harness (read) | Evaluator pre-flight | post-draft |


Two further E-series couplings are roadmapped but **unimplemented**, per SK-20 §Dependencies and §Planned successors: **E.1 `graph-read-at-planner`** (Planner-timed input from god-nodes and suggested questions) and **E.3 `graph-contradiction-sweep`** (extends `check-contradictions` with cross-corpus edges). Both are flagged "not part of the v0.3.0 pilot" and have no implementing SKILL.md.

**The diagnosed asymmetry.** The harness reads from the wiki only **once** (SK-20, post-draft, against the Evaluator's pre-flight). Every other coupling pushes harness state into the wiki. The new snowball pipeline (SK-NEW-A/B/C of §5) is entirely a *discovery-layer* construct that runs **before** drafting — it occupies exactly the slot Coupling E.1 was meant to fill but never has. Without wiki-side reads at Ph1 entry, SK-NEW-A is forced to rebuild from external Class 1 verifiers what the wiki's graph layer often already contains. The wiki's investment in extracted citation edges (graphify `EXTRACTED` / `INFERRED` / `AMBIGUOUS` confidence-tagged from full-text reads) is unavailable to the discovery layer.

The plan's wiki-collaboration deepenings, formalised at §5.5, address this asymmetry along five axes: graph-as-snowball-substrate (materialises Coupling E.1); incremental wiki write-back during snowball (promotes SK-15 from terminal to in-loop); wiki syntheses as claim-coverage anchors (gives SK-NEW-B a fast-path); concept-page red-links as snowball triggers (closes the SK-16 ↔ SK-NEW-C loop); and cross-project seed inheritance (consumer-side counterpart to wiki write-back). The result is a coupling surface where the wiki is read at every phase of the discovery-and-resolution loop, not just at SK-20's post-draft pre-flight.

---

## 4. Methodology — Snowball Mechanisation

The TO-BE plan treats snowball not as a heuristic but as a *bounded procedure* with declared inputs, declared outputs, declared termination, and declared audit artefacts. The decomposition follows Wohlin (2014) with adaptations for the harness's tool inventory.

### 4.1 Inputs

- **Seed claim set.** Extracted from the section's Ph1 outline (the Planner's deliverable plan in `reviews/revision_plan.md`) plus the section's declared P-stage register from `reviews/classification.md`. A claim is a proposition that requires evidence (an existential, a comparison, a mechanism, a result, a theoretical commitment).
- **Existing wiki corpus.** When `wiki_linked: true`, the project's peer LLM wiki under `wiki_path` (`EXTERNAL_VERIFIERS.md` §1.5).
- **Zotero library.** The user's curated personal library (`mcp__zotero__zotero_search_items`, `zotero_semantic_search`, `zotero_search_by_citation_key`).
- **Class 1 external verifiers.** Scholar Gateway (`mcp__70599628-0640-490e-bb1b-450b0e8248a9__semanticSearch`; reachability and response shape verified at §3.4), Consensus (`mcp__a28b93ab-2ce7-493f-b02d-f03a8ebe522f__search`; documented as connected at `EXTERNAL_VERIFIERS.md` §7), Zotero+Scite (`mcp__zotero__*` namespace; 43 tools registered per `EXTERNAL_VERIFIERS.md` §7 including `scite_check_retractions` for Class 3 retraction probes and `zotero_semantic_search` for embedding-based library search).
- **Saturation parameters.** ε (new-admittance ratio threshold below which iteration halts), max_iterations (hard cap to prevent runaway), per_seed_cap (cap on backward+forward admissions per seed per iteration).

### 4.2 Procedure (mechanised)

```
INIT:
  S0 = ∅                                      # accumulated seed set
  I = 0                                       # iteration counter

SEED PHASE (procedure: SEED_FROM_CLAIMS):
  for each claim c in seed_claim_set:
    candidates = WIKI(c) ∪ ZOTERO_SEM(c)      # §1.5 step 1+2
    if |candidates| < min_seed_per_claim:
      candidates += SCHOLAR_GATEWAY(c) ∪ CONSENSUS(c)   # §1.5 step 3
    S0 = S0 ∪ admit(candidates, c)             # admission criterion: title/abstract resolves c
  log(SEED, S0)

SNOWBALL ITERATION (procedure: ITERATE):
  while True:
    I = I + 1
    backward_admits = ⋃_{s ∈ S_{I-1}} BACKWARD(s)        # bibliography of s; admit if resolves an open claim
    forward_admits  = ⋃_{s ∈ S_{I-1}} FORWARD(s)         # papers citing s; admit if resolves an open claim
    new_admits = (backward_admits ∪ forward_admits) \ S_{I-1}
    rate = |new_admits| / max(1, |S_{I-1}|)
    log(ITERATE, I, |new_admits|, rate)
    if rate < ε or I >= max_iterations:
      break
    S_I = S_{I-1} ∪ new_admits

VERIFY PHASE (procedure: VERIFY_AND_LOG):
  for each s ∈ S_I:
    log_external_verification(s)              # writes external_verification_log.md row per s
  produce REFERENCES.md with three tables:
    - core corpus      = seeds whose source was read directly
    - snowball         = admitted papers from iterations 1..I, grouped by iteration depth
    - cited-via        = papers referenced from inside read sources but not read directly

OUTPUT:
  references/REFERENCES.md (populated)
  reviews/snowball_log.md (procedure trace: per-iteration admits, rates, claim coverage)
  reviews/external_verification_log.md (extended with rows for every Class 1 verification)
```

### 4.3 Saturation criterion

The stop rule `rate < ε` is parameterised. The default is anchored by an empirical iteration trace observed in Barros-Justo et al. (2021), retrieved via Scholar Gateway (§3.4): a forward-snowball update of an earlier systematic literature review on global software development risks ran three iterations on a 38-paper seed and admitted 3039 → 601 → 26 candidate papers (`10.1002/smr.2370`, chunk 22). Treating admission decay as a proxy for saturation, the per-iteration admission ratio (admits at iteration *i* divided by admits at *i−1*) is 601/3039 = 0.198 from iteration 1 to 2, and 26/601 = 0.043 from iteration 2 to 3. The third-iteration ratio falls below the 0.05 threshold the plan adopts as ε. SK-NEW-A's saturation default is therefore ε = 0.05 with `max_iterations = 4`, calibrated against this single observed trace; the parameter is surfaced in the project's `classification.md` for override when the field's citation churn warrants tightening (ε = 0.02 for theoretical-stable subfields) or loosening (ε = 0.1 for fast-moving ML/HCI subfields). The two iteration-cap and ε-loosening defaults remain `[INFERRED — verify before using]` against an additional Class 1 hit; the load-bearing default for the architecture (the ε = 0.05 stop rule) is now grounded in a verified observation.

### 4.4 Per-claim coverage as the Ph1 → Ph2 admission signal

The output of the procedure is not the snowball pool itself but the **claim-coverage map**: for each claim in the seed_claim_set, the subset of the snowball pool that resolves the claim. The map is the Ph1 → Ph2 admission artefact; it is read by the Evaluator at Ph2 entry as a precondition (analogous to the existing `E-PSTAGE-REQUIRED-AT-Ph2` check).

A coverage *score* (covered / total) is recorded alongside the map. The score is a softgoal-satisficing metric, not a binary gate; the user is the final arbiter (per `pre_phase_advance_check.py` clause architecture). A typical threshold is 0.8 (80% of claims covered) but the threshold belongs in `classification.md` as a project parameter, not in the harness substrate.

### 4.5 Incremental extension trigger at Ph2

When the Evaluator at Ph2 surfaces an ungrounded claim during Steps 1–3 (a new claim introduced by the Generator's draft, or a previously-marked `[FACT NEEDED]` that was not resolved by the seed-and-saturate run), the finding does not escalate as a prose BLOCKER. It triggers an **incremental snowball micro-iteration** anchored on the new claim's keywords and on the closest existing references in the pool. The micro-iteration runs the seed-and-saturate procedure with `max_iterations = 2` and a narrowed admission criterion (the new claim alone, not the full claim set). The output is a delta to REFERENCES.md and a new row in `snowball_log.md`. Only if the micro-iteration fails to produce a resolving source does the finding escalate to BLOCKER under the existing `[BLOCKER] citation does not resolve via any Class 1 verifier` rubric.

This integrates the discovery layer with the existing resolution layer without rewriting the resolution layer.

---

## 5. TO-BE Architecture

### 5.1 New skills (three)

#### SK-NEW-A. `seed-snowball-discovery` (Ph1 entry skill)

| Field | Value |
|---|---|
| **Tier** | Executor (Sonnet — Generator-class structured output, per `MODEL_ALLOCATION.md` §2 row 3 analogue) |
| **Trigger** | Auto-invoked by `run-phase-1` Step 4.5 (new) when `references/REFERENCES.md` is absent OR `classification.md` carries `references_initialized: false`. Manually: `/seed-snowball-discovery <section>`. |
| **Inputs** | `reviews/classification.md` (P-stage, claim register); `reviews/revision_plan.md` (section claim outline); `wiki_path` (when `wiki_linked: true`); Class 1 verifier handles. |
| **Outputs** | `references/REFERENCES.md` (populated three-table format); `reviews/snowball_log.md` (procedure trace); rows appended to `reviews/external_verification_log.md`. |
| **Rule 7a wiring** | Every admitted paper triggers a `log_external_verification` call; the skill cannot exit cleanly without the log rows. |
| **Saturation contract** | Stops on `rate < ε` (default 0.05) OR `iterations >= 4`. Reports both trigger reason and final rate. |

#### SK-NEW-B. `claim-coverage-audit` (Ph2 pre-engagement skill)

| Field | Value |
|---|---|
| **Tier** | Executor (Sonnet — structured audit) |
| **Trigger** | Auto-invoked by `run-phase-2` Step 0.5 (new) before the Evaluator's Step 0a. Manually: `/claim-coverage-audit <section>`. |
| **Inputs** | `manuscript/<section>.md` (Ph1 draft); `references/REFERENCES.md`. |
| **Outputs** | `reviews/claim_coverage_<YYYY-MM-DD>_<cycle_id>.md` with three sets: covered (claim ↔ source mapping), partially-covered (claim has a source for some aspects), uncovered (no resolving source). |
| **Coverage score** | `covered / total`; below `claim_coverage_threshold` (project parameter, default 0.8) the audit emits a Ph2-blocking warning and dispatches SK-NEW-C. |
| **Reflector audit hook** | Every uncovered-claim row is spot-checked by the Reflector's Phase 2.5 Category 5 (gap-fill audit) at round close. |

#### SK-NEW-C. `extend-snowball-incremental` (Ph2 in-loop skill)

| Field | Value |
|---|---|
| **Tier** | Executor (Sonnet) |
| **Trigger** | Dispatched by SK-NEW-B when coverage score falls below threshold OR by the Evaluator at Step 4 when a new claim surfaces in the Generator's Ph1 draft that has no resolving source. Manually: `/extend-snowball-incremental <claim>`. |
| **Inputs** | A single uncovered claim (or short claim list); the existing REFERENCES.md (full pool for anchor selection). |
| **Outputs** | Delta to REFERENCES.md (new rows under the `snowball` table only — the `core corpus` table is not extended at Ph2); new entry in `snowball_log.md` recording the micro-iteration. |
| **Saturation contract** | `max_iterations = 2`; `per_seed_cap = 5` (narrower than SK-NEW-A's per-seed_cap to prevent Ph2 token blow-out). |
| **Failure mode** | If 2 iterations admit zero papers resolving the claim, the skill writes `[BLOCKER] claim does not resolve via Class 1 snowball` to the Evaluator's findings; Generator must downgrade the claim to Indirect tier or remove it. |

### 5.2 Edits to existing skills (two)

#### Edit-1. `run-phase-1/SKILL.md` — insert seed-snowball gate after Step 4

Insert a new Step **4.5** between the existing Step 4 (P-stage declaration) and Step 5 (diff scoping):

> **4.5 Planner: seed-snowball gate (conditional).** Read the section's `references_initialized: bool` field from `reviews/phase_state.json` (`phase_state_schema.md §2`; new field at v0.10.0 S2; defaults to `false` on fresh sections). **OR-conjunctive outer guard:** if `references_initialized` is `false` or absent OR `references/REFERENCES.md` does not exist, dispatch SK-NEW-A `seed-snowball-discovery` for this section. The OR-conjunction (NOT AND) is load-bearing: it catches both inconsistent-state windows (state-flag-false + REFERENCES populated; state-flag-true + REFERENCES absent) that a conjunctive AND-guard would silently skip. The skill produces the populated REFERENCES.md and the snowball log. **Three-outcome-branch handling** (authoritative in `agents/planner.md`; this clause references that contract): *(i) Clean exit* — Planner sets `references_initialized: true` in `phase_state.json` (NOT `classification.md`; the field lives in the SectionStateObject) and appends a `seed_snowball_signed` row (trigger 31, `phase_state_schema.md §3.1`) to `phase_entry_log`. *(ii) Precondition no-op* — when SK-NEW-A's preconditions are unmet beyond the idempotency clause (per `seed-snowball-discovery/SKILL.md §2` reason codes), Planner emits non-blocking `W-SNOWBALL-PRECONDITION-UNMET` (declared at `phase_notifications.yaml §4`); Ph1 proceeds without trigger-31 write; Ph2's Step 0.5 placeholder (added at S2 per §6.3 enumeration row 7) re-tests. *(iii) Partial-failure mid-run* — when SK-NEW-A's preconditions PASS but execution fails per its §8 failure modes, Planner emits `E-SNOWBALL-MID-RUN-FAILURE` (declared at `phase_notifications.yaml §4`); Ph1 cycle HALTS pending user adjudication; partial REFERENCES.md preserved on disk.

(Note: the `W-CORPUS-BOOTSTRAP-DEFERRED` code referenced in the v0.10.0 pre-S2 draft of this paragraph was renamed to `W-SNOWBALL-PRECONDITION-UNMET` at S2 close to align with the operational notification registry; the older name is not declared anywhere and should be considered deprecated terminology.)

The `phase_entry_log` row addition is consistent with the row-shape contract at `phase_state_schema.md §3a.1`. The new trigger enum value (`seed_snowball_signed = 31`) extends the 30-trigger enum at `phase_state_schema.md §3.1` to 31; the trigger is not retroactively applied to migrated rows.

The Generator dispatch at Step 6 is augmented: when `references_initialized: true`, the Generator's revision plan handoff includes the path to REFERENCES.md and is instructed to draft against the saturated pool, with Rule 4 attribution preferred over `[UNVERIFIED]` markers when a resolving source exists in the pool.

#### Edit-2. `run-phase-2/SKILL.md` — insert claim-coverage gate before Step 0a

Insert a new Step **0.5** between the existing Step 1 (Planner Phase 0 preflight) and Step 3 (Evaluator Step 0a deterministic):

> **0.5 Planner: claim-coverage audit dispatch (auto).** Dispatch SK-NEW-B `claim-coverage-audit` for the section. The skill reads `manuscript/<section>.md` and `references/REFERENCES.md` and produces `reviews/claim_coverage_<date>_<cycle_id>.md`. Two outcomes:
>
> - **Coverage score ≥ `claim_coverage_threshold`** (default 0.8) — audit passes; Ph2 dispatch proceeds to Step 0a. The Evaluator's Step 8 synthesis still invokes Class 1 verifiers for BLOCKER citations as today.
> - **Coverage score < `claim_coverage_threshold`** — audit emits a non-blocking Ph2 advisory and auto-dispatches SK-NEW-C `extend-snowball-incremental` per uncovered claim. The Ph2 Evaluator pass proceeds in parallel; if SK-NEW-C lands new sources before the Evaluator's Step 4 reaches the affected claim, the Evaluator reads against the extended pool. Otherwise the claim surfaces as a MAJOR finding in the Evaluator's report with `propose_extend_snowball` as the remediation hint.

Step 0.5 does not block Ph2 admission — the existing eight `pre_phase_advance_check.py` clauses are unchanged. The new clause is *advisory* and feeds the Evaluator's Step 4 / Step 8 reads. This preserves the v0.7.4 admission-rule semantics while adding a discovery-layer signal.

The `What this stage does NOT do` list at `run-phase-2` §9 is amended: the line "No external-verifier probing (Zotero / Scholar Gateway / register-specific passes)" is qualified — *Ph2 still does not invoke external verifiers during Steps 1–7*; SK-NEW-B and SK-NEW-C invoke them at the **discovery** layer (pre-pass and on-uncovered-claim), not at the **judgment** layer where the §9 prohibition applies. The two layers are distinct under the framing introduced in `EXTERNAL_VERIFIERS.md` §1.5.

### 5.3 New ledger artefacts

- `reviews/snowball_log.md` — append-only procedure trace. Per-iteration rows record: seed_set_size, backward_admits, forward_admits, new_admits, rate, saturation_signal (ε-met / max-met / verifier-unreachable). Read by SK-NEW-C to anchor incremental iterations. Read by the Reflector at Phase 2.5 Category 7 (Rule 7a annotations) for spot-check sampling. Append-only and never edited, by analogy with `external_verification_log.md`.
- New `claim_coverage_*.md` files under `reviews/` — produced by SK-NEW-B per Ph2 cycle. Time-stamped and cycle-id-stamped per the existing `reviews/<phase>_<date>_<cycle_id>.md` convention (`run-phase-2` §7 row "Artefacts produced").

### 5.4 SectionStateObject schema additions

Two new fields are appended to the 16-field SectionStateObject (currently `phase_state_schema.md §2` at v0.8.0):

- `references_initialized: bool` (default `false`) — set `true` after SK-NEW-A's clean exit at Ph1 Step 4.5. Read by SK-NEW-A's idempotency guard (skill exits no-op when `true` AND `REFERENCES.md` is populated; partial-state windows are caught by the OR-conjunctive outer guard at Step 4.5). Field lives in the SectionStateObject (`phase_state.json`), NOT in `classification.md` (the v0.10.0 pre-S2 architecture draft incorrectly named the latter).
- `last_coverage_score: float` (default `null`) — set by SK-NEW-B at Ph2 Step 0.5. Persisted across rounds so the Planner can detect score regressions when Ph2 re-enters after a Ph3 retraction.

The 16-field invariant becomes 18-field at the next minor version bump. The migration script at `scripts/migrate_v090_to_v0X0_*.py` (to be authored at implementation time) handles the field addition.

### 5.5 Wiki-collaboration extensions to the new skills

Per the §3.5 diagnosis, the discovery-layer asymmetry is closed by five concrete extensions to the new skills, plus one new skill (SK-NEW-D) for cross-project seed inheritance. Each extension is contractual: inputs, outputs, and integration points are named so the implementing skills can build against the existing wiki coupling pattern (`wiki_path` resolution; `wiki_linked: true` gating; graceful no-op when wiki is absent or stale, identical to SK-20's precondition discipline).

#### 5.5.1 Extension to SK-NEW-A — wiki-graph as snowball substrate (materialises Coupling E.1)

SK-NEW-A's iteration step (§4.2 `ITERATE`) is rewritten so that backward and forward admissions are computed *first against the graphify graph*, then through Class 1 external verifiers only for graph-stub citations. The iteration pseudocode becomes:

```
SNOWBALL ITERATION (graph-substrate variant):
  while True:
    I = I + 1

    # Step 1: graph-local traversal (zero external API cost)
    for s in S_{I-1}:
      graph_node = lookup_node_by_doi_or_pdf_path(s, graph.json)
      if graph_node:
        backward_local += traverse_edges(graph_node, direction="backward",
                                         confidence_floor="EXTRACTED")
        forward_local  += traverse_edges(graph_node, direction="forward",
                                         confidence_floor="EXTRACTED")

    # Step 2: external fall-through ONLY for seeds the graph does not cover
    for s in S_{I-1} \ graph_covered_seeds:
      backward_external += SCHOLAR_GATEWAY_BACKWARD(s)
      forward_external  += SCHOLAR_GATEWAY_FORWARD(s)

    new_admits = (backward_local ∪ forward_local ∪
                  backward_external ∪ forward_external) \ S_{I-1}
    rate = |new_admits| / max(1, |S_{I-1}|)
    log(ITERATE, I, |new_admits|, rate,
        graph_local_admits=|backward_local|+|forward_local|,
        external_admits=|backward_external|+|forward_external|)
    if rate < ε or I >= max_iterations: break
    S_I = S_{I-1} ∪ new_admits
```

**Behavioural contract.** Per SK-20 Phase 1 (`graph-grounding-overlay/SKILL.md`), `graph.json` carries node fields `id, label, source_file, source_location, author, captured_at, community, norm_label` and edge fields `relation, confidence, confidence_score, source_file, source_location, weight, source, target`. SK-NEW-A's `lookup_node_by_doi_or_pdf_path` keys on `source_file` (resolved against REFERENCES.md's `pdf_path` column) primarily and on `(author, year)` heuristics secondarily; its `traverse_edges` admits papers whose corresponding node carries `confidence: EXTRACTED` by default, with `confidence: INFERRED` admitted only when the iteration's external-cost budget warrants the lower-confidence path. AMBIGUOUS edges are never auto-admitted; they surface as `[graph-ambiguous]` candidates in the snowball log for user review.

**Cost projection.** For a project with N seed papers of which k are wiki-resident, the graph-substrate variant reduces external Scholar Gateway calls from O(N × max_iterations) to O((N − k) × max_iterations). For projects where the wiki has accumulated meaningful coverage (k/N → 1), external API cost drops by an order of magnitude. This is the load-bearing efficiency benefit of the deepening.

**Coupling E.1 materialised.** SK-20 §Dependencies registers Coupling E.1 (`graph-read-at-planner`, M1-timed) as a planned successor that has never shipped. SK-NEW-A's graph-substrate variant **is** Coupling E.1 — Planner-timed graph read at Ph1 entry, feeding the snowball pipeline rather than the Evaluator's pre-flight. The plan recommends retiring the unused E.1 placeholder in `references/AGENT_ORCHESTRATION.md §8.6` and registering SK-NEW-A's graph-substrate variant under the same identifier.

#### 5.5.2 Extension to SK-NEW-A — incremental wiki write-back during snowball

Every paper SK-NEW-A admits triggers an immediate `wiki/sources/<key>.md` stub creation, calling SK-15's stub-template logic *inline* rather than batching the writes for a post-snowball SK-15 invocation. The wiki therefore appreciates as an asset across project runs: the next project's seed phase finds more wiki-resident sources, which (via §5.5.1) reduces its external API cost, which (via the same §5.5.1) further increases the speed of subsequent snowball passes.

**Atomic-write contract.** Per the existing `wiki/wiki/log.md` and `wiki/wiki/index.md` append-only conventions (SK-15 §Phase 4), the in-loop write-back uses the same `<wiki_path>/wiki/sources/<key>.md.tmp` → atomic-rename pattern that SK-15 already implements. Concurrent SK-NEW-A invocations across sections in the same project serialise on the wiki index file via OS-level file locking; cross-project concurrency (rare in practice) falls back to user adjudication on conflicting `index.md` rows.

**Provenance preservation.** Each in-loop stub carries `grounding_status: stub — created by SK-NEW-A iteration <i> from snowball seed <seed_doi>` in frontmatter. The Reflector's Phase 2.5 Category 7 audit can therefore distinguish wiki entries created proactively (stubs from snowball admissions) from wiki entries created reactively (stubs from terminal SK-15 backfill). The two populations have different verification debt profiles and the audit treats them differently.

#### 5.5.3 Extension to SK-NEW-B — wiki syntheses as claim-coverage anchors

SK-NEW-B's coverage check gains a fast-path: before any per-claim Scholar Gateway probe, the audit attempts to align each drafted claim against `<wiki_path>/wiki/syntheses/*.md`. A claim is *transitively covered* if it aligns with a synthesis page and the synthesis's source set resolves under Rule 7a.

**Alignment criterion.** A drafted claim aligns with a synthesis page when (a) the synthesis page's load-bearing thesis (typically the first paragraph after frontmatter, by SK-14's emission convention) is semantically similar to the claim above a similarity threshold, and (b) the synthesis page's `Inbound references (Research/)` frontmatter lists at least one source in the claim's section topic register. The similarity threshold is 0.6 (cosine similarity over an embedding model when MCP fast-path is available; Jaccard 0.3 over normalized claim+synthesis tokens otherwise; thresholds parameterised in `classification.md`). The threshold is conservative — false positives degrade to per-claim probes (no harm done); false negatives (failing to find an alignment) cost an extra Scholar Gateway call.

**Coverage-score impact.** A claim covered via synthesis alignment counts toward the coverage score with a `[via-synthesis: <synthesis_key>]` annotation. SK-NEW-B's output `reviews/claim_coverage_*.md` carries a fourth set alongside covered/partially-covered/uncovered: **synthesis-covered**, with a row count and a per-row synthesis pointer. This makes the curated synthesis logic visible to the Reflector and to the user.

#### 5.5.4 Extension to SK-NEW-C — concept-page red-links as snowball triggers (closes the SK-16 ↔ SK-NEW-C loop)

SK-16 Phase 4 (`retrofit-concept-grounding/SKILL.md`) currently produces "red-link candidates" — citations on concept pages with no resolving wiki source page — as a passive log entry. With this extension, every red-link auto-triggers SK-NEW-C `extend-snowball-incremental` against the cited author-year *as if it had been an Evaluator-surfaced uncovered claim*. The trigger fires only when (a) `wiki_linked: true`, (b) the project's `classification.md` has `auto_redlink_snowball: true` (new opt-in field), and (c) SK-16 has run in the same round.

**Audit-loop closure.** The current backlog of unresolved red-links is, in effect, a backlog of discovery work the harness should have been doing but wasn't. This extension converts the backlog from a passive ledger into an active queue that SK-NEW-C drains. The cost ceiling is `red_link_cap_per_round` (default 5; surfaced in `classification.md`) so a concept-page sweep with a long red-link list cannot blow the round's external-API budget.

#### 5.5.5 New skill: SK-NEW-D `inherit-snowball-from-wiki` (cross-project seed inheritance)

When a fresh project's section is bootstrapped under SK-NEW-A and the wiki holds graphify communities adjacent to the section's classification, SK-NEW-D pre-seeds SK-NEW-A's seed_set from the adjacent communities' source membership. This is the consumer-side of §5.5.2 — the wiki write-back's compounding return.

| Field | Value |
| --- | --- |
| **Tier** | Executor (Sonnet — structured graph traversal) |
| **Trigger** | Auto-invoked by SK-NEW-A's seed phase when (a) `wiki_linked: true`, (b) `${wiki_path}/graphify-out/graph.json` exists and is fresh per SK-20 Precondition 3, and (c) `classification.md` has `inherit_snowball: true` (new opt-in, default `true` for wiki-linked projects). |
| **Inputs** | The section's `classification.md` (P-stage, paper-type, claim register); `${wiki_path}/graphify-out/graph.json` (community membership); `${wiki_path}/graphify-out/GRAPH_REPORT.md` (community labels and god-nodes). |
| **Outputs** | A pre-seed list `pre_seed.json` consumed by SK-NEW-A as the input to its `SEED_FROM_CLAIMS` procedure (the pre-seed is unioned with, not substitutive of, the claim-derived seeds). One row in `reviews/snowball_log.md` recording the pre-seed source. |
| **Adjacency criterion** | Two graphify communities are *adjacent* to the section if (a) their community label (per GRAPH_REPORT.md) overlaps with the section's claim register tokens above the synthesis-alignment threshold of §5.5.3, OR (b) at least one god-node in the community is cited in the section's classification.md as a P-stage anchor. |
| **Pre-seed cap** | `pre_seed_cap` (default 10 papers; surfaced in `classification.md`). The pre-seed cannot dominate SK-NEW-A's iteration: claim-derived seeds remain the load-bearing input. |

**Strategic benefit.** Across a portfolio of projects sharing a research domain, the wiki accumulates community structure. SK-NEW-D lets a new project enter at iteration k of an effective shared snowball rather than at iteration 0. Empirical leverage scales with `wiki_corpus_size × overlap(section_domain, wiki_communities)`; the architecture promises the leverage exists and surfaces it as a parameter rather than asserting a specific magnitude (a magnitude claim would be `[INFERRED]` until measured against a real wiki).

#### 5.5.6 Dual-path access contract (filesystem default + MCP fast-path)

All five wiki-collaboration extensions resolve `wiki_path` and access wiki resources through a **dual-path contract** that lets the implementation behave identically whether the optional `llm-wiki` plugin is connected or not. The contract is:

**Default path — filesystem reads.** The skill uses `Read`, `Glob`, and `Grep` over `${wiki_path}/wiki/{sources,concepts,syntheses}/*.md`, `${wiki_path}/wiki/{index,log}.md`, and `${wiki_path}/graphify-out/{graph.json,GRAPH_REPORT.md}`. Semantic queries fall back to lexical/Jaccard matching. This is the default; it requires no MCP and matches SK-20's existing access pattern verbatim.

**Fast-path — `mcp__llm-wiki__*` when available.** At skill entry, the implementation probes for the `llm-wiki` MCP namespace via the available toolset. If detected, semantic queries route through `/llm-wiki-query` (per `EXTERNAL_VERIFIERS.md §1.5`'s "contract-bound pass" provision); the read-side becomes embedding-driven rather than lexical. The user-facing behaviour is identical: same outputs, same artefacts, same logs; only the internal query mechanism differs.

**Detection rule.** Tool-namespace detection runs once per skill invocation and is logged in the snowball-log row as `wiki_access_mode: filesystem | mcp_fastpath | mcp_unreachable`. The third value indicates the MCP was detected but errored mid-call; in that case the skill falls back to filesystem reads silently for the remainder of the round. The Reflector's Phase 2.5 audit can compare admission rates across access modes to detect false-negative cases (filesystem-only mode failing to admit papers the MCP fast-path would have admitted).

**Per-skill access-mode field.** Each new skill (SK-NEW-A/B/C/D) carries an `access_mode` parameter in its frontmatter — `auto` (default; detect-and-prefer-fast-path), `filesystem` (force filesystem reads even if MCP detected), `mcp_fastpath` (require MCP; refuse to run if absent). The default `auto` matches §1.5's portability contract; the explicit modes are for testing and for projects that want deterministic behaviour.

### 5.6 GROUNDING_PROTOCOL and EXTERNAL_VERIFIERS interactions

No new rule is required. The existing apparatus is sufficient when interpreted under the discovery / resolution split:

- **Rule 4** (quote-before-attribute) is *enforced* at resolution (Ph2 Step 4 / Step 8) and *prepared for* at discovery (Ph1 Step 4.5 produces the pool the Generator quotes from).
- **Rule 6** (no gap-filling) is *enforced* by the Generator's `[FACT NEEDED]` markers and *prevented from arising* by the snowball pool's claim coverage.
- **Rule 7a** (external verification) is *applied* on every snowball admission at Ph1 (the seed-and-saturate output is itself a Rule 7a logging exercise) and on every micro-iteration admission at Ph2.
- **§1.5** (wiki-first discovery ordering) is *operationalised* — SK-NEW-A executes the wiki → Zotero → Class 1 ladder as its seed phase. The §1.5 prose currently mandates the order without naming an executor; SK-NEW-A becomes the named executor.

A documentation amendment to `EXTERNAL_VERIFIERS.md` §1.5 is therefore the only protocol-level change: the section header is annotated *Operationalised by SK-NEW-A `seed-snowball-discovery` at Ph1 entry; by SK-NEW-C `extend-snowball-incremental` at Ph2 incremental extension*. The substance of §1.5 is unchanged.

---

## 6. Refinement Ladder (Sequenced Implementation)

The implementation is staged in eight increments to keep each step independently shippable and reversible. Each increment passes `release-gate.sh` before the next begins. Stages S1 / S2 / S3 / S4 / S5 are the discovery-and-resolution backbone; stages S1.5 / S4.5 / S6 are the wiki-collaboration deepenings of §5.5 and are sequenced to land alongside the backbone stages whose behaviour they modify.

### 6.0 Coupling Checklist for Phase-Runner Step Edits (added v0.10.0 S2)

Any stage that **inserts or edits a Step in any `run-phase-N` skill** must concurrently amend the four orchestration co-mutation surfaces below — they are not implicit consequences of the SKILL.md edit. This checklist surfaced empirically at v0.10.0 Stage S2 close, when semantic-review caught the gap between Sub-A's faithful Step 4.5 insertion and the four downstream surfaces it left untouched. Codifying the checklist here prevents S3, S4, S4.5, and S6 from rediscovering the same coupling sequentially.

| # | Surface | What to update | Failure mode if skipped |
|---|---|---|---|
| 1 | `agents/planner.md` (canonical Planner spec) | Register the dispatch responsibility at the correct Planner phase. The Planner subagent reads `agents/planner.md` as authoritative; consumed `run-phase-N/SKILL.md` is *not* authoritative over the Planner's behaviour. Phase placement must mirror the SKILL.md Step's position relative to other Planner activities. For a Step inserted between P-stage declaration and diff scoping in `run-phase-1`, the Planner-side phase lives in the **pre-revision-plan region (Phase 3.5 / 3.7 / pre-Phase 4)** — diff scoping happens during Phase 4's revision plan production via the template's `Where:` field. Do **NOT** place such a dispatch in Phase 4.5 / 4.6 (these are model-dispatch and SubAgent-delegation invariants, downstream of the revision plan) or Phase 5 (post-user-approval). The v0.10.0 S2 implementation places the SK-NEW-A dispatch at Phase 3.7 specifically. | Planner subagent has no instruction to dispatch; the Step never fires at runtime; downstream ledger writes (e.g., new trigger rows) never happen. |
| 2 | `references/phase_notifications.yaml` | Declare every new W-* / E-* code emitted by the new Step. Mirror the shape of an existing entry in the same severity class (e.g., `W-PSTAGE-UNAVAILABLE` for warnings, `E-IMODEL-STRUCTURALLY-INCOMPLETE` for errors). | The harness's own validation rejects emission of unregistered codes; md-reviewer flags broken-contract MAJOR. |
| 3 | `scripts/pre_phase_advance_check.py` (or its phase-named successor) | Add any new trigger to `VALID_TRIGGERS`; add a clause for any new field that gates phase advance. Without this, clause (g) row-shape conformance refuses every section's exit on the new trigger; or, if the field is non-blocking, the section silently rides through Ph1→Ph4 without the field ever being enforced. | New trigger rows hard-block phase advance OR new fields have no enforcement at all. |
| 4 | Partial-failure halt-vs-continue semantics, reconciled across `agents/planner.md` AND `skills/run-phase-N/SKILL.md` | When two specs (Planner agent file vs. consumed skill) both describe the failure-handling for the new Step, they must agree on whether mid-run failure halts the cycle or skips ledger writes and continues. Single source of truth: the Planner agent file (the dispatcher); the SKILL.md references it. Inner/outer guard conjunction must also have a single source of truth. | Planner subagent non-deterministically chooses one contract; downstream cycles depend on which doc the subagent attended to. |

The checklist applies to S2, S4, and any post-v0.10.0 stage that touches a phase-runner. S1, S3, S4.5, S5, and S6 are exempt by realised scope: S1/S3/S6 ship new manually-invokable skills (no `run-phase-N` Step edit), S5 is documentation-only, and S4.5 amends two existing SKILL.md bodies (`claim-coverage-audit`, `retrofit-concept-grounding`) without editing any phase-runner Step. The two surfaces named at S4.5 close — `W-REDLINK-CAP-SATURATED` declared in `phase_notifications.yaml` (row-2-shaped) and the skip-and-continue partial-failure contract written into `retrofit-concept-grounding/SKILL.md §8` (row-4-shaped) — are required by the baseline code-registration contract and the partial-failure single-source-of-truth principle, **not** §6.0 coupling: the SKILL.md amendment authors them in the SKILL.md itself rather than across phase-runner / Planner / `pre_phase_advance_check.py`. The §6.0 closing-sentence enumeration was empirically revised at S4.5 entry; the original "applies to … S4.5" text reflected pre-S4 scope expectations (the predecessor architecture-plan author anticipated that the synthesis fast-path would reshape Step 0.5 logic) which the realised S4.5 design did not require.

### 6.1 Stage S1 — Discovery layer skill (SK-NEW-A only, no harness wiring)

Ship `skills/seed-snowball-discovery/SKILL.md` as a manually-invokable skill (`/seed-snowball-discovery`). No `run-phase-1` edit; users invoke it deliberately on a fresh project. Validates the procedure end-to-end against the wiki-first ordering and Class 1 verifier handles; produces the first instances of `references/REFERENCES.md` populated by the skill rather than by hand. Risk: low (additive, no existing behaviour changed). Validation: end-to-end run against an empty project; `external_verification_log.md` rows match the snowball admissions; Reflector audit passes.

### 6.2 Stage S1.5 — Wiki-graph substrate + write-back inside SK-NEW-A (§5.5.1 + §5.5.2)

Extend SK-NEW-A's iteration step to traverse `${wiki_path}/graphify-out/graph.json` first and fall through to Scholar Gateway only for graph-stub seeds. Implement the in-loop `wiki/sources/<key>.md` stub creation (calling SK-15's stub-template logic inline). Implement the dual-path access contract (§5.5.6) with `auto`/`filesystem`/`mcp_fastpath` parameters. Risk: medium (read-side coupling to graphify schema; relies on SK-20's existing graph-staleness precondition pattern; concurrent write-back needs atomic-rename). Validation: the snowball log shows `graph_local_admits` ≥ `external_admits` for any seed paper resolvable in the graph; `wiki/sources/` count grows by exactly the snowball-admission count; `wiki_access_mode` is logged correctly across all three explicit settings.

### 6.3 Stage S2 — Phase-1 wiring (Edit-1) — full enumeration per §6.0 coupling checklist

S2 is a phase-runner-Step-editing stage and therefore must touch all four §6.0 surfaces in addition to the document-layer deliverables. The full enumeration:

**Document-layer deliverables (the original §6.3 scope):**
1. **`skills/run-phase-1/SKILL.md`** — insert Step 4.5 per §5.2 Edit-1 (OR-conjunctive outer guard; three-outcome-branch Planner handling).
2. **`references/phase_state_schema.md`** — add `references_initialized: bool` field (default `false`) to SectionStateObject §2; add trigger 31 (`seed_snowball_signed`) to §3.1 enum; update §1.1 schema_version commentary.
3. **`scripts/migrate_v090_to_v100_snowball_fields.py`** — flesh out the S0 skeleton with the four S2-scoped functions; smoketest fixtures under `scripts/fixtures/phase_state_smoketest/v090_to_v100/`.

**Orchestration co-mutations (per §6.0 checklist; surfaced at S2 close v0.10.0):**

4. **`agents/planner.md`** — register the SK-NEW-A dispatch responsibility at the Planner phase that mirrors `run-phase-1` §3 Step 4.5's placement (between P-stage declaration and diff scoping; this is the **pre-revision-plan region (Phase 3.5 / 3.7 / pre-Phase 4)** since diff scoping happens during Phase 4's revision plan production via the template's `Where:` field). The v0.10.0 S2 implementation places this at **Phase 3.7** specifically (between Phase 3.5 wiki synthesis brief and Phase 4 revision plan). Do **NOT** place in Phase 4.5 / 4.6 (model-dispatch / SubAgent-delegation invariants, downstream of the revision plan) or Phase 5 (post-user-approval); see §6.0 row 1 for the general rule. Three-outcome-branch handling (clean / precondition no-op / partial-failure mid-run) authoritative here; the SKILL.md references this contract rather than duplicating it.
5. **`references/phase_notifications.yaml`** — declare `W-SNOWBALL-PRECONDITION-UNMET` (warning, non-blocking, emitted on SK-NEW-A precondition no-op beyond the idempotency clause) and `E-SNOWBALL-MID-RUN-FAILURE` (error, blocks Ph1 completion until user adjudication, emitted on SK-NEW-A's §8 mid-run failure modes — `WRITE_FAILURE`, `GRAPH_VS_EXTERNAL_DISAGREEMENT`, lock-contention). Mirror the shapes of `W-PSTAGE-UNAVAILABLE` and `E-IMODEL-STRUCTURALLY-INCOMPLETE` respectively.
6. **`scripts/pre_phase_advance_check.py`** — add `seed_snowball_signed` to `VALID_TRIGGERS` so trigger 31 rows pass clause (g) row-shape conformance at every Ph1→Ph2 advance check; add a clause that surfaces a non-blocking advisory when `references_initialized: false` is observed at Ph1→Ph2 advance (does not refuse the advance; matches Step 0.5's non-blocking re-test semantics).
7. **`skills/run-phase-2/SKILL.md`** — insert a non-blocking Step 0.5 placeholder that re-tests the gate at Ph2 entry and re-emits `W-SNOWBALL-PRECONDITION-UNMET` if `references_initialized: false`. Full Ph2-side dispatch of SK-NEW-A / SK-NEW-B lands at S3 (§6.4) / S4 (§6.5); this Step 0.5 is the placeholder that substantiates Step 4.5's "Ph2 entry will re-test the gate" claim at S2.

**Risk:** medium (modifies the Ph1 dispatch sequence; ledger schema bump; orchestration coordination across four surfaces).

**Validation:** existing Ph1 sections do not break (idempotency guard fires); new sections trigger SK-NEW-A and the entry log shows the new row; semantic-review (binding at S2) returns CLEAR — md-reviewer reads run-phase-1, run-phase-2, AND this architecture document; promise-reviewer reads run-phase-1 + run-phase-2 frontmatter; orchestrator-critic reviews the dispatch graph including the four co-mutations.

### 6.4 Stage S3 — Coverage audit skill (SK-NEW-B only, no Ph2 wiring)

Ship `skills/claim-coverage-audit/SKILL.md` as a manually-invokable skill (`/claim-coverage-audit`). Validates the claim-extraction → source-mapping → coverage-score logic on real Ph1 drafts. Risk: low (additive). Validation: hand-curated coverage maps for two pilot sections agree with the skill's output to within ±5 percentage points.

### 6.5 Stage S4 — Phase-2 wiring + incremental skill (Edit-2 + SK-NEW-C)

Insert Step 0.5 into `run-phase-2`. Ship SK-NEW-C. Add `last_coverage_score` to SectionStateObject. Risk: medium (modifies the Ph2 dispatch; introduces auto-dispatch chain SK-NEW-B → SK-NEW-C). Validation: the Ph2 advisory does not block admission; the Evaluator's Step 4 reads against the extended pool when SK-NEW-C lands sources in time; the MAJOR-finding fallback is exercised when it does not.

### 6.6 Stage S4.5 — Wiki synthesis fast-path + red-link triggers (§5.5.3 + §5.5.4)

Extend SK-NEW-B with the synthesis-alignment fast-path; extend SK-16 with the red-link auto-trigger to SK-NEW-C (gated on `auto_redlink_snowball: true` and capped by `red_link_cap_per_round`). Risk: medium (introduces an SK-16 → SK-NEW-C dispatch edge; alignment threshold may need calibration). Validation: synthesis-covered count is non-zero on a project with a populated `wiki/syntheses/` layer; per-claim Scholar Gateway probe count drops materially (target: ≥30% reduction vs. S4 baseline on a wiki-resident corpus); red-link auto-trigger is rate-limited as configured.

S4.5 ships in two rounds:

**R1 — primary deliverables.** The two SKILL.md amendments above. Plus one new warning code `W-REDLINK-CAP-SATURATED` declared in `references/phase_notifications.yaml`, emitted by SK-16 when the round's red-link queue exceeds `red_link_cap_per_round` (baseline code-registration contract, not §6.0 coupling — see §6.0 closing-sentence revision). Plus the skip-and-continue partial-failure contract for SK-NEW-C dispatch failures inside SK-16's red-link queue, documented in `skills/retrofit-concept-grounding/SKILL.md §8 Failure modes` (single-source-of-truth — no phase-runner reads the contract). Calibrator advisory; semantic-review advisory at S4.5 (per strategy §4.4).

**R2 — S4 carry-overs.** `reviews/classification.md` template additions for the five new fields surfaced across S4 + S4.5: `coverage_regression_floor` (default 0.05; surfaces the `last_coverage_score` cross-round regression-detection consumer landing in this round), `max_parallel_extend_snowball` (default 8; surfaces the inline cap currently encoded in `agents/planner.md §Phase 3.8`), synthesis-alignment threshold (0.6 cosine / 0.3 Jaccard, conditioned on `wiki_access_mode`), `auto_redlink_snowball` (default `false`), `red_link_cap_per_round` (default 5). Plus the cross-round regression-detection consumer wiring at `agents/planner.md §Phase 3.8` (delivers the S4 round-2 fix's "S4.5-deferred consumer" promise; introduces a second new code `W-COVERAGE-REGRESSION-OBSERVED` per the same baseline code-registration contract). Plus `CHANGELOG.md` + `docs/release-notes/RELEASE_NOTES_v0.10.0.md §2.S4` + `§2.S4.5` catch-up (one-shot at R2 close per the S4 close-notes' deferral rationale).

### 6.7 Stage S5 — Documentation amendment (`EXTERNAL_VERIFIERS.md` §1.5; `AGENT_ORCHESTRATION.md §8.6`)

Annotate `EXTERNAL_VERIFIERS.md §1.5` with the named executor lines (SK-NEW-A and SK-NEW-C as operationalisers of the wiki-first ladder). Annotate `AGENT_ORCHESTRATION.md §8.6` to register SK-NEW-A's graph-substrate variant under the Coupling E.1 identifier (retiring the unused `graph-read-at-planner` placeholder). Bump `references/SKILL_REGISTRY.md` to register SK-NEW-A / -B / -C / -D. Risk: zero (documentation-only). Validation: `python scripts/skill-check.py` and `python scripts/catalog-check.py` pass.

### 6.8 Stage S6 — Cross-project seed inheritance (SK-NEW-D, §5.5.5)

Ship `skills/inherit-snowball-from-wiki/SKILL.md` (SK-NEW-D). Wire it as an auto-invoked pre-seed step inside SK-NEW-A. Surface `inherit_snowball: true` (default for wiki-linked projects) and `pre_seed_cap` (default 10) in the `classification.md` template. Risk: low (additive; only runs when wiki has accumulated cross-project content; bounded by `pre_seed_cap`). Validation: on a wiki with ≥2 prior projects in adjacent communities, SK-NEW-D pre-seed yields at least 1 admission; on a wiki with no adjacent communities, SK-NEW-D no-ops cleanly without modifying SK-NEW-A's seed_set.

---

## 7. Risk Register


| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-1 | Class 1 verifier rate-limit / cost blow-out during a max-iteration snowball run | Medium | Medium (token / quota cost; potential session abort) | `per_seed_cap` parameter; `interaction_id` reuse per `EXTERNAL_VERIFIERS.md` §2 Scholar Gateway contract; coalesce Scholar Gateway batch via single `interaction_id` per snowball iteration (one UUID per iteration, not per seed). |
| R-2 | Snowball admits irrelevant papers; pool inflates without resolving more claims | Medium | Low (signal-to-noise drops; downstream SK-15 stub count grows) | Per-claim verification step prunes admissions to claim-resolving subset; SK-NEW-B's coverage score detects pool-inflation-without-coverage-gain. |
| R-3 | Snowball fails to find a source for a niche claim that genuinely has no Class 1 hit | Low | High (R-2 manifests as an apparent uncovered claim that is actually coverable only via grey literature or unindexed venues) | SK-NEW-C escalates to MAJOR finding, not BLOCKER, on first failure; user is the final arbiter; the ladder allows graceful downgrade to Indirect tier per Rule 4 with explicit indirection. |
| R-4 | Coverage score is gameable (low-quality sources padding the count) | Medium | Medium (false confidence at Ph1 → Ph2 admission) | Reflector Phase 2.5 Category 7 (Rule 7a) spot-check applies to snowball admissions; sample-of-3 per round; mismatches escalate to BLOCKER. Coverage score is advisory, not a hard gate. |
| R-5 | Saturation never reaches `rate < ε` for niche fields | Low | Medium (max-iteration cap fires; user sees premature stop) | Cap is 4 iterations (Wohlin 2014 norm); skill reports "max-iter-reached" in the snowball log so the user can decide whether to extend manually. |
| R-6 | Concurrent Ph2 dispatch of SK-NEW-C and the Evaluator pass races on REFERENCES.md | Medium | Low | Single-writer convention: SK-NEW-C writes `references/REFERENCES.md.tmp` then atomic-renames per the existing `phase_state_schema.md §5` pattern; Evaluator reads only the canonical path. |
| R-7 | SectionStateObject schema bump breaks existing tooling | Low | Medium | Migration script per Stage S2 / S4; `scripts/phase_state_validate.py` updated in lockstep; existing 16-field validators tolerate the additional fields by design (extension-tolerant readers). |
| R-8 | Graphify graph stale relative to manuscript / REFERENCES.md (SK-NEW-A reads outdated edges) | Medium | Medium (false-negative admissions; SK-NEW-A passes work that the graph would have caught) | Reuse SK-20 Precondition 3 verbatim (`captured_at` vs. most recent `Last updated:`); on stale-graph detection, SK-NEW-A's graph-substrate step emits `[graph-stale]` warnings and falls through to Scholar Gateway for full coverage rather than no-op'ing the iteration. |
| R-9 | Wiki MCP fast-path errors mid-call; admission count diverges from filesystem-only mode | Low | Medium (silent recall regression if undetected) | Detection rule (§5.5.6): `wiki_access_mode: mcp_unreachable` is logged in the snowball-log row; Reflector's Phase 2.5 audit compares admission rates across access modes on the same seed_set when both modes are exercised in the same project. Discrepancies above a 10% threshold escalate to MAJOR. |
| R-10 | In-loop wiki write-back races on `wiki/index.md` between concurrent SK-NEW-A invocations | Low (single-user harness; rare cross-section parallelism) | Low | OS-level file-locking on `wiki/index.md` per the SK-15 atomic-rename pattern; cross-project concurrency falls back to user adjudication on conflicting rows. |
| R-11 | Synthesis-alignment false positives (SK-NEW-B marks claim covered when synthesis is only superficially related) | Medium | Medium (coverage score inflated; uncovered claim slips past Ph2 advisory) | Conservative similarity threshold (0.6 cosine / 0.3 Jaccard); explicit `[via-synthesis: <key>]` annotation in coverage report; Reflector Phase 2.5 Category 7 spot-checks synthesis alignments on sample-of-3 per round; threshold parameter surfaced in `classification.md` for project-side calibration. |
| R-12 | Red-link auto-trigger floods Scholar Gateway (SK-16 surfaces a long red-link list, all triggering SK-NEW-C) | Medium | Medium (cost blow-out; round may abort) | `red_link_cap_per_round` parameter (default 5); excess red-links logged as deferred-discovery candidates rather than triggering immediately; rate-limit visible in the snowball-log and surfaced to the user at round close for explicit re-prioritisation. |
| R-13 | SK-NEW-D pre-seed dominates SK-NEW-A's iteration (wiki-inherited papers crowd out claim-derived seeds) | Low | Low (signal-to-noise drop on SK-NEW-A's first iteration) | `pre_seed_cap` (default 10); the union with claim-derived seeds is bounded; SK-NEW-A's per-claim verification (§4.4) prunes pre-seeded papers that do not resolve any of the section's actual claims, so over-seeding self-corrects across iterations. |


---

## 8. Validation Criteria (per stage `release-gate.sh` pass)

- **Skill manifest.** `python scripts/skill-check.py` passes with new SK-NEW-A/B/C/D entries discovered. SK-NEW-A description ≤ 500 chars (per `skill-check.py REQUIRED_FRONTMATTER_KEYS`).
- **Catalog parity.** `python scripts/catalog-check.py` passes with new `commands/<name>.md` shims (one per new skill, following the v0.9.0 UI loadability convention).
- **Version bump.** `python scripts/version-check.py` passes; version bumped to v0.10.0 (minor — additive).
- **Path hygiene.** `python scripts/path-hygiene-check.py` passes.
- **Phase state.** `python scripts/phase_state_validate.py` passes against the 18-field SectionStateObject; the migration test fixture under `scripts/fixtures/phase_state_smoketest/` is extended with a v0.9.0 → v0.10.0 case.
- **End-to-end probe.** A pilot section is taken through Ph1 → Ph2 with the new dispatch chain. Audit artefacts:
  - `references/REFERENCES.md` populated with three tables.
  - `reviews/snowball_log.md` shows ≥1 iteration and a saturation signal; per-iteration rows record `graph_local_admits`, `external_admits`, and `wiki_access_mode`.
  - `reviews/external_verification_log.md` has rows for every snowball admission that fell through to a Class 1 verifier (graph-local admissions log to `snowball_log.md` only).
  - `reviews/claim_coverage_*.md` shows a coverage score with four sets (covered / partially-covered / synthesis-covered / uncovered); the score is `≥ claim_coverage_threshold` for a claim register that is by construction coverable.
  - When `wiki_linked: true`: `${wiki_path}/wiki/sources/` count grows by exactly the snowball-admission count, with each new stub carrying `grounding_status: stub — created by SK-NEW-A iteration <i>`; `${wiki_path}/wiki/log.md` carries the corresponding ingest entries.
  - Reflector grounding audit at round close shows zero new violations attributable to the new skills, including the new Category-9 audit lines for synthesis-alignment annotations and `wiki_access_mode` consistency.

---

## 9. Out of Scope (deliberate exclusions)

- **Ph3 / Ph4 reference work.** Ph3 already invokes external verifiers optionally and Ph4 mandatorily; the snowball machinery interacts cleanly at those rungs but the v0.10.0 cut is Ph1 / Ph2 only.
- **Wiki source-page promotion-to-`full` from snowball admissions.** §5.5.2 covers in-loop *stub* creation only; promotion of a stub to `grounding_status: full` requires a direct read pass and is SK-17's terminal-stage job, not the snowball pipeline's. No change to SK-17 is in scope.
- **Concept-page retrofit on snowballed sources.** §5.5.4 wires SK-16's red-link output as an SK-NEW-C trigger but does not edit SK-16's retrofit logic itself. The retrofit pass remains SK-16's responsibility, invoked manually after SK-NEW-A has populated the wiki source layer.
- **Coupling E.3 (`graph-contradiction-sweep`).** SK-20's planned successor that extends `check-contradictions` with cross-corpus edges is unimplemented and remains so; the snowball architecture is orthogonal to it.
- **Tri-tier calibrator schema** (Haiku / Sonnet / Opus per `MODEL_ALLOCATION.md` §2). The new skills are all Sonnet-class executors and fit cleanly inside the current binary calibrator schema; the F4/F8 schema-fidelity question (open from `RELEASE_NOTES_v0.9.0_addendum.md`) is unrelated.
- **Snowball over grey literature, theses, technical reports.** Class 1 verifiers cover peer-reviewed; grey literature snowball is a separate operationalisation problem deferred to a later cut.

---

## 10. Open Questions (for user adjudication before Stage S1 begins)

1. **Coverage threshold.** Default proposed: `claim_coverage_threshold: 0.8`. Should the threshold be discipline-conditioned (e.g., 0.9 for IS empirical, 0.7 for HCI design)? Lives in `classification.md` either way; the question is what default the harness ships with.
2. **Saturation parameter ε.** Default proposed: 0.05. ML/HCI fields with high citation churn may need 0.1; theoretical-stable fields may saturate at 0.02. Same question — default vs. project override.
3. **Class 1 verifier ordering inside the snowball iteration.** §1.5 specifies wiki → Zotero → external; inside the *external* tier, is the order Scholar Gateway → Consensus, or Consensus → Scholar Gateway? The `EXTERNAL_VERIFIERS.md` §2 table privileges Scholar Gateway as "primary Rule 7a verifier" so I propose Scholar Gateway → Consensus, with Consensus reserved for contested-claim cross-check. Confirmation requested.
4. **Backward / forward asymmetry.** Wohlin (2014) reports that backward snowball typically yields more admissions than forward at iteration 1 but the asymmetry inverts at iteration 2+. Should the skill record per-direction admit counts separately? Cheap to add; only justified if the user wants the methodological audit trail.
5. **Per-section vs. per-manuscript scope.** The plan as drafted is per-section (each Ph1 entry runs SK-NEW-A on its own claim register). An alternative is per-manuscript (one snowball pool shared across sections, extended incrementally per section). Per-section is simpler and aligns with the Lifecycle-Phase Ladder's section-scoped semantics; per-manuscript is more efficient for cross-section evidence reuse. Tabled for user input.

---

## 11. Authorship and Provenance

Drafted under the v0.9.0 maintenance session, 2026-04-26. The architectural framing follows the GORE / AORE conventions declared in the user's session-level preferences and operationalised in the harness via `references/PHASE_PROTOCOL.md §3.1` (i\* SD/SR opt-in) and `agents/planner.md` (i\* structural-completeness validator). The integration with `Rule 7a` and `EXTERNAL_VERIFIERS.md` §1.5 / §2 is the architectural contribution; the existing rule and registry text are cited verbatim against files read in the current session and are unmodified.

The §3.5 / §5.5 / §6.2 / §6.6 / §6.8 wiki-collaboration deepening was added in a same-session amendment after the user requested formalisation of the LLM Wiki collaboration. The amendment is grounded in direct reads of `skills/graph-grounding-overlay/SKILL.md` (SK-20; Coupling E.2 contract and graph-staleness precondition pattern), `skills/ingest-m5-to-wiki/SKILL.md` (SK-17; Coupling D and the `grounding_status: stub | full` discipline), `skills/backfill-source-stubs-from-references/SKILL.md` (SK-15; the in-loop write-back's atomic-rename pattern is borrowed from this skill), and `skills/retrofit-concept-grounding/SKILL.md` (SK-16; the red-link auto-trigger consumes SK-16's existing red-link output). The unimplemented Coupling E.1 is materialised by SK-NEW-A's graph-substrate variant per §5.5.1.

**Citation-provenance disclosure (per `GROUNDING_PROTOCOL.md` Rule 5).** Three classes of citation appear in this plan; their verification status differs and is logged here for traceability.

1. *Verified at §3.4 via Scholar Gateway probe (this session).* Mashkoor et al. 2022 (`10.1002/smr.2457`), Wohlin et al. 2021 (`10.1002/smr.2345`), Barros-Justo et al. 2021 (`10.1002/smr.2370`). All three were retrieved with passage-level provenance via `mcp__70599628-0640-490e-bb1b-450b0e8248a9__semanticSearch` on 2026-04-26. The §4.3 saturation-criterion default rests on the Barros-Justo iteration trace and is now Class 1-grounded; the §2.3 noise-vs-digital-library claim quotes Mashkoor et al. 2022 verbatim from the Scholar Gateway `text` field.

2. *Cited indirectly via the Scholar Gateway hits.* Wohlin 2014 ("Guidelines for snowballing in systematic literature studies and a replication in software engineering") is the methodological anchor referenced (as "Wohlin 14" / "Wohlin 43" / "Wohlin 4") in all three Scholar-Gateway-returned papers. The plan's reliance on Wohlin's procedure is therefore *inherited-tier* under Rule 4 — the methodology itself is what the verified papers cite as their basis. The original Wohlin 2014 paper has not been read directly in this session; before Stage S1 ships, SK-NEW-A's documentation should resolve Wohlin 2014 directly via `zotero_add_by_doi` or a follow-on Scholar Gateway query and log the verification row.

3. *Carry residual `[INFERRED]` markers.* The ε = 0.02 / ε = 0.1 field-conditioned ε defaults (§4.3) and Greenhalgh & Peacock 2005 (§2.3 retired in this revision) remain inferred from training memory. The architectural argument does not depend on them; the load-bearing default for the architecture (ε = 0.05 with the Barros-Justo trace as anchor) is now Class 1-grounded.

The verification debt that remains is therefore **bounded** — Wohlin 2014 direct read at S1, plus optional cross-field ε defaults at the user's discretion — and is materially smaller than at the prior plan revision. The implementing project will run a single seed-and-saturate pass against this plan's own claim register as a self-test before Stage S1 closes.
