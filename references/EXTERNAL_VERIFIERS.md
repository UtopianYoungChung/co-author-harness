# EXTERNAL VERIFIERS — Ground-Truth Validity Tools for the Harness



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

**Status.** This file is a **binding component** of the Grounding Protocol. It enumerates the external Model-Context-Protocol (MCP) servers that the four agents (Planner, Evaluator, Generator, Reflector) may invoke as **ground-truth validity layers** when verifying citations, attributions, factual claims, or retraction status. It also defines **§1.5** (peer `LLM wiki/` paths and optional `/llm-wiki-query` — not MCP) for **discovery** ordering. Every verification tier in §2 onward participates in the Chain of Verification (`GROUNDING_PROTOCOL.md` Rule 7) and in Rule 7a (the external-verifier rule introduced below).

**Scope.** Applies to all projects governed by this package. A project's `CLAUDE.md` may declare which verifier tiers it permits (e.g. `external_verifiers: [class_1, class_1_5]`) but may not declare a verifier that is not registered here. Adding a new verifier requires editing this file and bumping the package version.

**Precedence.** This file sits **below** `GROUNDING_PROTOCOL.md` (which is binding and non-overridable) and **above** the component style files. It is read by the Evaluator (Step 8 synthesis), the Generator (before adding any citation), and the Reflector (Phase 2.5 grounding audit, Categories 1, 7, 8). It is not consulted during the deterministic pass (Step 0a) or the pre-flight graph overlay (Step 0.5).

---

## 1. Why external verifiers exist

The Grounding Protocol's Rules 1–6 ensure that agents do not fabricate citations, metrics, paths, or attributions **within** the project's own files. But the protocol alone cannot answer four questions that require external ground truth:

1. **Does a cited paper exist?** The project's `REFERENCES.md` may carry a row the agents have never actually retrieved. A live bibliographic lookup settles this.
2. **Is the cited paper retracted?** The project's `REFERENCES.md` has no retraction field; an external retraction index does.
3. **Does the attributed claim appear in the cited source?** A semantic-passage search against the source can surface or refute the passage.
4. **Is the claim supported by the broader literature, or is it idiosyncratic?** A multi-paper consensus search situates the claim.

Each of these questions is a **Category 1 citation audit** (Rule 4) question that the Reflector's spot-check would otherwise answer from memory — itself a Rule 5 violation. External verifiers convert the audit from a memory check into an evidentiary check.

**The bootstrapping paradox.** Before this file existed, an agent could only verify a citation against files the user had already curated. If the citation was never in the project, verification was impossible. External verifiers close this loop: Rule 7a allows an agent to treat a claim as `[externally verified]` only if at least one Class 1 verifier returned a corroborating result in the current session.

---

## 1.5 Wiki-first resource order (discovery and gap-filling)

**Purpose.** Closes the read loop with the peer `LLM wiki/`: *reuse curated knowledge before* opening new PDFs from Zotero or running broad external search (e.g. Scholar Gateway, **Consensus**). This section governs **where to look first** when the task is to **find, justify, or add** literature — not the **Rule 7a** resolution order for a citation already under audit (see §3 — Evaluator/Generator/Reflector steps for 7a are unchanged).

**When it applies.** The project’s `CLAUDE.md` has `wiki_linked: true` **and** `wiki_first_resources` is not `false` (see `PROJECT_BOOTSTRAP.md` §3 Step 5). If `wiki_linked: false` or the user has set `wiki_first_resources: false`, skip straight to the Zotero → external flow below.

**Order (strict):**

1. **Peer LLM wiki (first line).** At `wiki_path` from the project’s Wiki linkage section, consult at least: relevant `wiki/sources/*.md`, `wiki/concepts/`, `wiki/syntheses/`, and `graphify-out/GRAPH_REPORT.md` (communities, hubs, suggested questions). If the workspace installs the `llm-wiki` plugin, you may use `/llm-wiki-query` for a contract-bound pass; otherwise use Read/semantic search over those paths. **Log a traceable line** in `reviews/revision_plan.md` (Planner) or `manuscript/revision_log.md` (Generator discretionary note), e.g. `Wiki-first: read <paths or query summary> — <sufficient / gap remains because …>`. Rule 1 still applies: do not treat wiki *stubs* as full evidence for new claims at submission depth.

2. **Zotero (second).** Search the user’s library, resolve attachments, and add PDFs the project will actually read per `REFERENCES.md` / stub workflow — only after step 1 fails to cover the information need or the gap is explicitly *net-new* vs. the wiki’s coverage.

3. **External Class 1 / discovery tools (third).** Scholar Gateway, **Consensus**, and other Class 1 verifiers in §2 — for net-new external discovery, contested claims, or 7a verification. Do not use these *instead of* step 1 when the wiki is linked and a reasonable wiki pass could answer the question.

**Skill executors.** At Ph1, **SK-33 `seed-snowball-discovery`** is the package's named executor of this three-step order: its seed and iterate phases walk steps 1–3 in sequence (wiki-first graph traversal → Zotero → Scholar Gateway fall-through), logging a traceable `Wiki-first:` line per step 1's requirement. At Ph2 in-loop, **SK-35 `extend-snowball-incremental`** re-executes steps 1–3 narrowed to a single uncovered claim from SK-34's `## Uncovered` table. When `wiki_linked: false` or `wiki_first_resources: false`, both skills skip step 1 and begin at step 2 (Zotero).

**Non-overlap with Rule 7a.** The Zotero row in §2 still names library-first **for citation resolution** where the user likely holds the item. **Discovery** is wiki → Zotero → external; **7a** Step 1 in `GROUNDING_PROTOCOL.md` remains Zotero first *among Class 1 tools* for removing `[UNVERIFIED]` on a specific attribution, unless the project’s verification log already established coverage via wiki *full* reads.

---

## 2. Verifier tiers

Four tiers are defined. A project inherits all four unless its `CLAUDE.md` narrows the list.

### Class 1 — Scholarly search with provenance (authoritative for Rule 7a)

A Class 1 verifier must (a) return a resolvable identifier (DOI, arXiv ID, ACL anthology key, or persistent URL), (b) return source-level metadata (title, authors, venue, year), and (c) cover a corpus of at least 50M papers. Claims verified against Class 1 receive the `[externally verified]` annotation and may remove upstream `[UNVERIFIED]` markers **provided** the annotation records the verifier name, the query used, and the returned identifier.

Active Class 1 verifiers in this deployment:

| Verifier | MCP tool (runtime namespace) | Registry UUID | Corpus | When to invoke |
|---|---|---|---|---|
| **Scholar Gateway** | `mcp__70599628-0640-490e-bb1b-450b0e8248a9__semanticSearch` | `ff091334-0f12-4d0e-a973-c00467dd3818` | ~200M peer-reviewed papers (Semantic Scholar, PubMed, Scopus, arXiv) with passage-level provenance | **Primary Rule 7a verifier.** Use for any attribution the agent has not read directly. Returns passage-level provenance with citations, suitable for Rule 4 quoting. |
| **Consensus** | `mcp__a28b93ab-2ce7-493f-b02d-f03a8ebe522f__search` | `65247229-f0c7-49df-9044-fcbb8b3894c6` | Peer-reviewed scientific literature with journal-quartile (SJR) ranking, sample-size, and study-type metadata | Use when the finding requires not just "the paper exists" but "what the field thinks of the claim." Especially valuable for Category 1 spot-checks where the attribution is contested, and for filtering by SJR / study type / sample size. |
| **Zotero (+ Scite)** | `mcp__zotero__*` (stable namespace; includes `scite_check_retractions`, `scite_enrich_item`, `scite_enrich_search`, `zotero_semantic_search`) | (local MCP — no registry UUID) | User's personal library with Scite citation-intent enrichment | Use as the **first Class 1 verifier** for *citation resolution* when the user likely has the item. For *new literature discovery* when `wiki_linked: true`, follow **§1.5** first (peer wiki), then Zotero, then other Class 1 tools. Library-first minimizes external calls, preserves user-curated metadata, and surfaces retraction flags automatically. |

> **Runtime vs. registry UUIDs.** The `directoryUuid` (Registry UUID column) is the Cowork MCP registry's catalog entry — it is what `suggest_connectors` expects. The runtime namespace (MCP tool column) is the UUID the MCP server exposes once connected in this session; it is what prefixes every tool name. These are not the same UUID and must not be confused. If the runtime UUID appears to drift between sessions, re-probe via `mcp__mcp-registry__search_mcp_registry(keywords=["scholar-gateway"])` and re-read the tool list to recover the current runtime prefix.

> **Scholar Gateway `semanticSearch` required parameters.** The tool requires `query` (natural-language, do not reduce to keywords), `interaction_id` (a UUID generated once per user prompt and reused across parallel/follow-up searches in that episode), and `inferred_intent` (a free-text description of the *underlying information need*, not the query itself — e.g. "checking whether Baumer 2024 advances algorithmic co-constitution or merely surveys it"). Optional: `start_year`, `end_year`, `includeRetractedContent` (default `false`; set `true` only when retraction history is itself the subject), `topN` (1–20, default 15).

**Rule 7a wiring.** An agent may remove an `[UNVERIFIED]` marker after a Class 1 hit only if the audit log records: verifier name, exact query, returned DOI/ID, returned title (for disambiguation), and the session timestamp. The Reflector's Category 1 audit re-checks a sample of these removals.

### Class 1.5 — Domain-specific scholarly search (supporting, not authoritative)

A Class 1.5 verifier covers a narrower corpus (single-publisher, single-platform, or single-community) and is **supporting evidence** rather than authoritative. Claims verified against Class 1.5 alone remain `[UNVERIFIED — supporting only]`; they must be cross-checked against Class 1 before the marker is removed.

Active Class 1.5 verifiers:

| Verifier | MCP tool | Corpus | When to invoke |
|---|---|---|---|
| **HuggingFace Papers** | `mcp__ab9ac1e8-8aca-4de3-afba-92c86249d5aa__paper_search`, `mcp__ab9ac1e8-8aca-4de3-afba-92c86249d5aa__hf_doc_search`, `mcp__ab9ac1e8-8aca-4de3-afba-92c86249d5aa__hub_repo_search` | arXiv (ML/AI subset) + HuggingFace Hub | Primary for ML/AI method-paper lookups, model-card citations, benchmark references. Weaker for IS/HCI venues. |

### Class 2 — Local bibliography resolver (citation-key to path)

A Class 2 verifier resolves a citation key (e.g. `baumer2024tchi`) against a local BibTeX or Zotero export to a filesystem path (e.g. `raw/papers/Baumer24.pdf`). It does not verify the claim; it verifies that the project's own citation graph is internally consistent. This is the verifier the Evaluator uses to decide whether a citation is readable by the Generator before attribution.

Active Class 2 verifiers:

| Verifier | Tool | Corpus | When to invoke |
|---|---|---|---|
| **Zotero library resolver** | `mcp__zotero__zotero_search_by_citation_key`, `zotero_get_item_metadata`, `zotero_get_item_fulltext` | User's Zotero library | Invoked before every attribution by the Generator; invoked during Category 3 path audit by the Reflector. |
| **Local `.bib` resolver** | Filesystem read of project's `references.bib` if present | Project-scoped | Fallback when Zotero MCP is not reachable or when the project maintains a BibTeX export. |

### Class 3 — Retraction and integrity index

A Class 3 verifier returns a binary retraction signal and (where available) a retraction reason. It is invoked at submission-bound depth on every cited paper that appears in the Evaluator's consolidated findings report. A `retracted: true` result is an automatic **BLOCKER** regardless of the cited claim's quality.

Active Class 3 verifiers:

| Verifier | Tool | Corpus | When to invoke |
|---|---|---|---|
| **Scite retraction check** | `mcp__zotero__scite_check_retractions` | Scite's retraction registry | Mandatory at submission-bound depth; optional at standard depth; skipped at quick depth. |

---

## 3. How agents invoke verifiers

### Planner

- At bootstrap (M1), the Planner confirms which verifier tiers are reachable by probing each MCP with a whoami-class call (`mcp__zotero__zotero_list_libraries`, `mcp__*__hf_whoami`). It records the result in the project's `CLAUDE.md` under a `Verifier availability` section. The Evaluator reads this section at the start of each round.
- If a Class 1 verifier is unreachable and the project is at submission-bound depth, the Planner escalates: either the user connects the MCP, or the project proceeds with `[UNVERIFIED]` citations that cannot be cleared at submission time.
- When a round’s scope may introduce **new** references or PDFs, and the project is wiki-linked with `wiki_first_resources` not `false`, the Planner’s `reviews/revision_plan.md` must include a **Wiki-first** line per **§1.5** (what was read under `wiki_path`, or an explicit `N/A` with reason).

### Evaluator

- During Steps 1–7, the Evaluator does **not** invoke external verifiers. Those steps are judgment-based against the manuscript and the rule files; pulling external sources mid-judgment would fragment attention and exceed the token budget for the step.
- During Step 8 synthesis, for each BLOCKER-severity citation finding, the Evaluator invokes Class 1 (Scholar Gateway preferred; Consensus as second opinion when the claim is contested) to confirm the citation resolves to a real paper. If the citation cannot be resolved, the finding escalates from "citation may be wrong" to "**[BLOCKER] citation does not resolve — possible fabrication**."
- **When Scholar Gateway results enter the consolidated findings report**, the Evaluator must honour the Scholar Gateway render contract (see §3.1 below). This is a compliance obligation declared by the tool itself in every response payload, not a stylistic choice.
- At submission-bound depth, the Evaluator additionally invokes Class 3 (`scite_check_retractions`) against every cited paper. Any hit appends a line to the G.4 sign-off table.

### Generator

- When **adding** a citation or proposing **new** literature, if `wiki_linked: true` and `wiki_first_resources` is not `false`, the Generator consults the peer `LLM wiki/` per **§1.5** before relying on Zotero-only or external search, and records the same one-line **Wiki-first** trace in `manuscript/revision_log.md` for that round.
- Before adding any new citation, the Generator invokes Class 2 (Zotero library resolver) to confirm the citation key maps to a readable source in the user's library. If Class 2 fails, the Generator invokes Class 1 (Scholar Gateway) to confirm the paper exists externally and proposes a `zotero_add_by_doi` action for user approval before citing.
- Before attributing a specific claim to a specific passage, the Generator invokes Class 1 (Scholar Gateway `mcp__70599628-0640-490e-bb1b-450b0e8248a9__semanticSearch`) with the passage's claim text. The call must include `query` (the claim in natural language), `interaction_id` (a UUID generated once per user prompt and reused across sibling/follow-up searches), and `inferred_intent` (a description of why the Generator is verifying — e.g. "confirming attributed passage is actually present in Baumer 2024 before promoting from [UNVERIFIED] to attributed"). If Scholar Gateway returns a matching passage, the Generator may attribute; if not, the Generator downgrades to **Indirect tier** per Rule 4 or leaves a `[FACT NEEDED]` marker per Rule 6.

### Reflector

- In Phase 2.5 (Grounding Audit), the Reflector **spot-checks** at least 3 Rule 7a annotations per round — re-runs the query against the declared Class 1 verifier and confirms the returned identifier matches the logged one. A mismatch is a Category 1 BLOCKER under the new enforcement subtype `[GROUNDING VIOLATION — Rule 7a]`.
- At submission-bound depth, the Reflector additionally spot-checks at least 1 Class 3 retraction result per round.
- The Reflector also audits **Scholar Gateway render-contract compliance** (see §3.1): every section of the consolidated findings report that cited a Scholar Gateway result must carry the per-search provenance line, and the report as a whole must carry the session footer exactly once. Missing provenance line → Category 9 MAJOR; missing session footer → Category 9 BLOCKER.

---

## 3.1. Scholar Gateway render contract (binding)

The Scholar Gateway `semanticSearch` response includes a `render_contract` (schema `scholar_gateway.render_contract`, v0.1) that declares how Scholar Gateway wants its results presented. The contract is not optional — it ships in every successful response and constitutes the usage terms under which Scholar Gateway results may appear in downstream artifacts. The plugin treats render-contract compliance as a Rule 7a obligation.

The contract mandates four presentation rules:

**1. Per-search provenance line.** Every time Scholar Gateway output is synthesized into a finding, a revision note, or a paragraph of prose, the synthesis must be preceded by an inline provenance line:

```
Scholar Gateway · <query> · <N> passages · <N> articles · <YYYY-MM-DD>–<YYYY-MM-DD>
```

The counts and date range come from the response payload's `provenance` object (`result_count`, `unique_articles`, `pub_date_range.earliest`, `pub_date_range.latest`). The query is copied verbatim from `provenance.query_as_executed` — not the agent's internal paraphrase.

**2. Gaps-and-limitations clause (conditional).** When Scholar Gateway returned a narrow date range, a low result count, or when the agent observes absence-of-evidence that would materially change interpretation, the agent must state the gap plainly *before* the synthesis begins, not as a trailing caveat. Format is free-text but must name what the evidence does not cover — generic phrasings ("results may be limited") do not satisfy this rule.

**3. Inline citations.** Substantive claims drawn from Scholar Gateway results must be cited author-year with DOI hyperlinks where available. Deduplicate across chunks: a paper that contributed two passages must appear once in the citation list, not twice. DOI hyperlinks use the form `https://doi.org/<doi>`.

**4. Session footer (once per response, not per search).** At the end of any response that consumed one or more Scholar Gateway searches, the agent must render the static disclosure block exactly once:

```
---
Results retrieved by Scholar Gateway · Summary generated by AI — verify claims against source documents · Last corpus update: <date from `provenance.disclosures[content_freshness]`> · [Content coverage details](https://support.scholargateway.ai/s/article/Available-Content)

📋 **We're testing a new response format** — did the search context, source counts, and any evidence notes change your opinion about this response? [Share your feedback](https://wiley.qualtrics.com/jfe/form/SV_1HRCBDWSjlaTk58) (takes about a minute)
```

The footer is rendered regardless of how many individual `semanticSearch` calls were made. Repeating it per-search is a contract violation (Category 9 MINOR: "render-contract over-rendering").

**Interaction with the Grounding Protocol.** Rule 4 (quote-before-attribute) requires that direct attributions cite a specific passage. When the passage came from Scholar Gateway, Rule 4 compliance is satisfied by the passage text in the `results[].text` field, not by the abstract. The agent must quote the chunk's `text`, not paraphrase the paper's abstract, to preserve provenance. The Reflector's Category 1 (citation audit) checks this alignment.

**Artifact flagging.** Any review artifact (consolidated findings report, revision log, reflection report) that incorporated Scholar Gateway results must carry a top-of-file marker:

```
<!-- scholar-gateway-contract: v0.1 -->
```

This marker signals to downstream agents and to the Reflector that the file is subject to render-contract audit. Its absence on a file that cites Scholar Gateway is itself a Category 9 violation.

---

## 4. Rule 7a — External verification as Chain-of-Verification evidence

**Text of Rule 7a** (appended to `GROUNDING_PROTOCOL.md` after Rule 7 in package version 0.3.2):

> **Rule 7a — External Verification.** A claim whose source has not been read in the current session may be treated as `[externally verified]` (and any upstream `[UNVERIFIED]` marker removed) only if a Class 1 verifier (per `EXTERNAL_VERIFIERS.md`) returned a corroborating result in the current session AND the verification was logged in `reviews/external_verification_log.md` with: verifier name, query, returned identifier, returned title, and timestamp. A Class 1.5 or Class 2 hit is supporting evidence and does not satisfy Rule 7a on its own. A Class 3 retraction hit is binding: a `retracted: true` result overrides any prior verification and escalates the finding to BLOCKER regardless of the cited claim's quality.

**Enforcement.** The Reflector's Phase 2.5 Category 1 audit spot-checks Rule 7a annotations. A removed `[UNVERIFIED]` marker without a corresponding log entry is flagged:

```
[GROUNDING VIOLATION — Rule 7a] Agent removed [UNVERIFIED] marker without external verifier log entry.
  Claim: <claim>
  Expected log: reviews/external_verification_log.md entry with verifier/query/id/timestamp
  Found: <none or partial>
```

A mismatch between the logged identifier and the re-checked identifier (same claim, different DOI) is flagged as a Rule 7a *fabrication* subtype:

```
[GROUNDING VIOLATION — Rule 7a.fabrication] Logged external verification does not reproduce.
  Logged: <verifier, query, identifier>
  Re-checked: <identifier or not-found>
  Action: Restore [UNVERIFIED] marker and re-verify.
```

---

## 5. External verification log format

Every agent that invokes a Class 1 or Class 3 verifier appends a row to `reviews/external_verification_log.md`:

```markdown
| Date | Agent | Claim (short) | Verifier | Query | Returned ID | Returned title | Result |
|---|---|---|---|---|---|---|---|
| 2026-04-16 | Evaluator | Baumer 2024 argues algorithmic co-constitution | Scholar Gateway | "algorithmic subjectivities Baumer 2024" | 10.1145/3610094 | Algorithmic Subjectivities: ... | MATCH |
| 2026-04-16 | Evaluator | Retraction check — Holldack 2026 | Scite | Holldack 2026 | n/a | n/a | NOT RETRACTED |
```

The log file is append-only — rows are never edited after write so the Reflector can diff for fabricated additions. The Evaluator and the Reflector both write to this file; the Planner reads it at round start to inventory prior verifications.

---

## 6. When verifiers disagree

Class 1 verifiers can disagree (Scholar Gateway returns a matching paper; Consensus returns "claim contested by [paper X]"). The disagreement is itself evidence:

- **Both return MATCH:** claim is corroborated; log both, annotate `[externally verified, n=2]`.
- **One MATCH, one UNKNOWN:** claim is corroborated on the weaker ground of single-verifier match; annotate `[externally verified, n=1, single-verifier]`.
- **MATCH and CONTESTED:** the finding is preserved, but the contested status is appended to the manuscript's attribution: "Baumer et al. (2024) argue X [contested by Y (Consensus)]." At submission-bound depth, a CONTESTED result escalates the Category 1 audit to MAJOR until the contradiction is resolved in-text.
- **Both UNKNOWN / NOT FOUND:** the `[UNVERIFIED]` marker may not be removed; the Evaluator flags the citation as **[BLOCKER] citation does not resolve via any Class 1 verifier**.

---

## 7. Operational addendum — live verifier registry (as of package version 0.3.2)

As of the 2026-04-16 customization round, the following verifiers are **operational and confirmed reachable** in the user's deployment (probed via `search_mcp_registry` at customization time):

- **Scholar Gateway** — `connected: true`, `enabledInChat: true` (directoryUuid `ff091334-0f12-4d0e-a973-c00467dd3818`)
- **Consensus** — `connected: true`, `enabledInChat: true` (directoryUuid `65247229-f0c7-49df-9044-fcbb8b3894c6`)
- **Zotero + Scite** — `connected: true`, 43 tools registered under `mcp__zotero__*`
- **HuggingFace Papers** — `connected: true` (UUID `ab9ac1e8-8aca-4de3-afba-92c86249d5aa`)

Rule 7a is therefore **operationally satisfiable** at submission-bound depth in this deployment. Projects that were previously unable to clear `[UNVERIFIED]` markers because no Class 1 verifier was reachable should re-run the Evaluator's Step 8 citation pass on the next round; the Rule 7a column of the Category 1 audit should now close cleanly.

**Failure-mode contract.** If a verifier is unreachable mid-session (MCP timeout, auth failure), the agent does NOT silently fall back to memory. It writes `[VERIFIER UNREACHABLE — <verifier>]` into the artifact at the point of use and continues with `[UNVERIFIED]` preserved. The Reflector's Category 1 audit distinguishes unreachable-verifier cases (not a violation) from bypassed-verifier cases (a Rule 7a violation).

---

*Relationship to SK-20 (graph-grounding-overlay).* The graphify graph is **not** a Class 1 verifier. It is a pre-flight input that surfaces overlay candidates; its findings carry `[source: graph-extracted]` / `[source: graph-inferred]` / `[source: graph-stub]` tags and are audited under Category 8 of grounding-audit. A graphify hit does not satisfy Rule 7a; a Scholar Gateway hit does. The two layers are complementary: graphify tells you which cited sources the corpus graph knows about; Scholar Gateway tells you whether the cited paper exists in the external bibliographic record and what passage supports the claim.
