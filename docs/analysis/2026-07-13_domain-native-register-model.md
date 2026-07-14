# Domain-Native Register Model — proposal for Codex (plain-English anchor)

*2026-07-13. Cowork second-opinion draft. Defines what "plain English" means operationally for the co-author-harness by anchoring it to the LLM-Wiki graphify view and an Eric-Yu-centroid exemplar set. Plugs into `references/policies/reader_accessibility.v1.json` (Task 4A) and the M1 reader record (milestone framework). Implementation is Codex's; this is the spec to build against.*

---

## 1. What "plain English" means here

Plain English for this portfolio is **domain-native register**, not lay simplification: prose whose terms, phrasings, sentence shapes, and argument-derivation moves have *warrant* in how insiders of Information Systems, Software Engineering, Systems Engineering, and Requirements Engineering actually write — so a reader in those fields does not feel the piece came from outside the domain. Plainness is a relation to a **specified reader** and an **empirical corpus**, not an abstract scalar. It is therefore two-sided:

- **Positive (emulate):** terms, connectives, sentence shapes, and argument moves attested in the *exemplar* set.
- **Negative (do not invent):** no construction lacking warrant in the *attestation* set — the "feels foreign" signal.

This target is deliberately **higher and narrower** than lay-plain; it optimizes insider fluency. It is recorded as `register_class: domain-native` so it is never confused with lay simplification (which would apply only to a genuinely public-facing passage, e.g. an Eubanks-style policy section).

## 2. Reader model (M1)

```json
"reader_model": {
  "audience_classes": ["IS scholar", "software engineer", "systems engineer", "requirements engineer"],
  "imported_theory_registers": ["sociology", "psychology", "philosophy"],
  "reading_task": "recover the argument's claims and their derivation on a single read, without leaving the page to look up a term",
  "register_class": "domain-native",
  "source": "M1 milestone reader declaration"
}
```

## 3. Corpus binding — one graphify index, two semantically pinned views

The anchor is the LLM-Wiki graphify **index** plus two derived views. The *pin* is semantic (view membership / exemplar tuples), not the raw `graph.json` file — a moving file must not redefine "plain" mid-cycle. The graph indexes sources; the actual register lives in the source material the views select.

```json
"corpus_binding": {
  "path_roots": {"NOTE": "three distinct roots — a traversal already misfired once; resolve explicitly", "wiki_root": "B:/Agents/knowledge/LLM wiki (all raw/corpus/* and wiki/sources/* paths are wiki_root-relative)", "workspace_root": "B:/Agents (the graph path below is workspace_root-relative)", "harness_root": "B:/Agents/platform/co-author-harness (references/policies/* is harness_root-relative)"},
  "graph": {"path": "knowledge/LLM wiki/graphify-out/graph.json", "role": "index + provenance metadata only — NOT a gate target (raw-file hashing over-triggers: unrelated wiki growth would invalidate a file pin and induce re-pin fatigue)", "observed_sha256_at_review": "EDF94FA6121794915A8C9C221D41869333BA3E837DDD7F5B9138290042F3090F (2026-07-13 19:34 — mutated same-day via stub write-back)"},
  "pin": {
    "level": "semantic — pin the two derived views, not the raw graph file",
    "algorithm": "SHA-256 over UTF-8 bytes (hex lowercase)",
    "pinned_objects": {
      "attestation_view_pin": "sha256 of newline-joined sorted node id list (see hash_recipe)",
      "exemplar_view_pin": "sha256 of newline-joined sorted exemplar tuples (see hash_recipe)"
    },
    "mf_policy_binding_keys": {
      "NOTE": "distinct from D-4 profile-file hash — do not collapse failure modes",
      "profile_sha256": "phase_state.json.milestone_framework.policy_bindings.reader_accessibility.profile_sha256 (D-4; whole policy file)",
      "attestation_view_pin": "…policy_bindings.reader_accessibility.attestation_view_pin",
      "exemplar_view_pin": "…policy_bindings.reader_accessibility.exemplar_view_pin",
      "graph_sha256_provenance": "…policy_bindings.reader_accessibility.graph_sha256_provenance (record only; NEVER compared for MF-POLICY block)"
    },
    "recorded_provenance": "raw graph.json sha256 + timestamp + unresolved_seed_ids at each pin event (metadata only; never gates)",
    "repin_policy": "recompute at natural boundaries — milestone transitions, or after any snowball round that admits new grounded sources; also when MF-POLICY discovers a membership/exemplar delta at review even if no snowball ran (community reshuffle inside the RE predicate is a real delta); AUTO-ACCEPT when both view pins are unchanged; on any real delta, prompt for a deliberate, versioned one-line re-pin; never silent, never intra-cycle",
    "rationale": "keeps the measurement instrument fixed within a review cycle (convergence stays falsifiable; no circular self-attestation from in-loop stub write-back) while letting the wiki evolve organically — the register only 'changes' when RE-cluster membership or an exemplar actually changes"
  },
  "related_to_RE_predicate": {
    "seed_resolution": "two-step, deterministic, no fuzzy matching: (1) exact id — nodes[].id == source_key; (2) source-file join — nodes[].source_file == 'wiki/sources/{source_key}.md'. Step 2 often returns multiple nodes (document + extracted concepts sharing the wiki page). Disambiguate deterministically: prefer file_type in {document, source}; if still multiple, prefer id ending with '_source'; if still multiple, take UTF-8-lexicographically first id and record the discarded ids under seed_resolution_ties in provenance. Step 2 is verified against the live graph 2026-07-13: after disambiguation, yu-mylopoulos-1994-wits_source and yu-mylopoulos-1994-icse_source are the chosen seed nodes for the two 1994 papers. Record the resulting source_key→node_id map (exactly one node_id per resolved source_key) in pin provenance. Seeds resolving by NEITHER step are listed as unresolved_seed_ids; they do not fail the pin. NEVER invent nodes.",
    "measured_reality_2026-07-13": "1/12 seeds resolve by id (yu-1995-istar, community 5); 2 more by source-file join after disambiguation (the two 1994 papers → wits_source / icse_source, community 10); 9/12 unresolved (zave, nuseibeh, goncalves-2019, yu-1997, yu-2001, yu-2011, all three recent-yu). Degeneracy is the CURRENT NORMAL, not an edge case — 3 resolved seeds sits at the thin-base floor.",
    "degeneracy_guard": "the policy loader MUST emit a provenance WARNING (never a block) when resolved_seed_count <= 3 OR len(primary_communities) < 2 — inclusive floor on seed count so today's measured 3/12 does not certify silently green. The pin still computes; thinness must be visible in resolved provenance.",
    "primary_communities": "unique nodes[].community integers of resolved seeds (recomputed each pin; do not hard-code community numbers — graphify may renumber)",
    "import_neighbors": "1-hop via links[]: read source/target as canonical; assert _src/_tgt agree and fail loudly on divergence (both field sets present on every link object; verified 0/811 divergent 2026-07-13). Neighbor = any node adjacent to a primary-community member whose community is NOT in primary_communities",
    "membership": "UNION of (all nodes with community in primary_communities) and (import_neighbors); identity field = nodes[].id",
    "NOTE": "captures sanctioned cross-community borrowings (sociology/psychology/philosophy) as 1-hop imports without pinning the whole wiki"
  },
  "hash_recipe": {
    "attestation_view_pin": "members = sorted(membership ids, UTF-8 lexicographic); bytes = '\\n'.join(members).encode('utf-8'); pin = sha256(bytes).hexdigest()",
    "exemplar_view_pin": "for each admitted exemplar_member (deny-list already applied), emit one line: '{source_key}\\t{tier_class}\\t{pdf_sha256_or_dash}' where tier_class = normalize_tier(grounding) and pdf_sha256_or_dash = pdf_sha256 if present else '-'; sort lines UTF-8 lexicographic; sha256 as above",
    "normalize_tier": "strip trailing annotation after ' — ' (em/en/ASCII hyphen variants); map aliases full-text-pass→full-read, section-read-verified→section-read; otherwise keep the leading token. Hash the normalized class, not the free-text annotation — annotation edits must not flip the pin",
    "pdf_staging_rule": "missing pdf_sha256 encodes as '-'. Staging a PDF later (or changing its bytes) IS a real exemplar delta and requires a deliberate re-pin — surface warrant strengthened"
  },
  "views": {
    "attestation": {"role": "negative check — is this construction foreign?", "members": "ALL nodes satisfying related_to_RE_predicate (broad)", "confidence": "presence = strong warrant; ABSENCE = advisory candidate only, never an automatic violation (the wiki is a personal KB and under-covers the field)"},
    "exemplar":    {"role": "positive target — write toward this", "members": "curated Yu-centroid set below (narrow)", "admission": "DENY-LIST: grounding_status in {stub, unresolved} excluded; every other tier admissible, recorded as a confidence attribute. Parse must be prefix-tolerant — wiki tier values carry free-text annotations ('full-read — 201/201 pages…') and variants ('full-text-pass', 'section-read-verified'); an exact-match enum on {full-read, section-read, read} would wrongly reject grounded pages."}
  }
}
```

## 4. Exemplar set (verified grounded 2026-07-13)

Centroid = Eric Yu / i\* conceptual-modeling lineage; halo = close-derived lineage + RE canon. Surface-register warrant is extracted from the **corpus PDF / verbatim extracts** (the wiki page is an LLM summary, not the author's prose); argument-architecture warrant uses the **wiki source page + graph topology**.

```json
"exemplar_members": [
  {"source_key": "yu-1995-istar",                                 "role": "centroid",      "grounding": "full-read",    "pdf": "raw/corpus/yu-1995-istar.pdf", "pdf_sha256": "C5F6472EE3348DBDF1D1D239BBF1FF9003B231953AC2C72266DA63A4381E0199"},
  {"source_key": "yu-mylopoulos-1994-modelling-strategic-actor-relationships-bpr-8p", "role": "classic-halo", "grounding": "full-read"},
  {"source_key": "yu-mylopoulos-1994-understanding-why-software-process-modelling",   "role": "classic-halo", "grounding": "full-read"},
  {"source_key": "yu-1997-early-phase-re",                        "role": "classic-halo",  "grounding": "full-read"},
  {"source_key": "yu-e-agent-orientation-as-a-modeling-paradigm-2001", "role": "classic-halo", "grounding": "full-read"},
  {"source_key": "yu-et-al-2011-social-modeling",                 "role": "classic-halo",  "grounding": "section-read"},
  {"source_key": "yu-2024-nine-pivots",                           "role": "recent-yu",     "grounding": "read"},
  {"source_key": "yu-2025-social-agentics-crosstalk",             "role": "recent-yu",     "grounding": "read"},
  {"source_key": "yu-lapouchnian-2025-social-agentics-bdi-star",  "role": "recent-yu",     "grounding": "read"},
  {"source_key": "zave-1997-four-dark-corners-re",               "role": "re-canon",      "grounding": "full-read"},
  {"source_key": "nuseibeh-2000-re-a-roadmap",                   "role": "re-canon",      "grounding": "full-read"},
  {"source_key": "goncalves-2019-istar-extension",               "role": "istar-extension-halo", "grounding": "section-read", "note": "promoted from stub 2026-07-13 (abstract+intro read-through; mid/end guideline set not exhaustively mapped — lower-confidence surface warrant; optional deepening to full-read)"}
],
"exemplar_pending_grounding": []
```

## 5. Two warrant layers (do not conflate — this is the J-in-H lesson again)

```json
"warrant_layers": {
  "surface":  {"question": "is this term / phrase / connective / sentence shape attested?", "source": "exemplar PDFs + verbatim extracts; attestation graph for vocabulary", "hosts_on_check": ["Sub-check H", "humanizer/lexicon layer"]},
  "argument": {"question": "is this derivation / logic-connection an insider move?",         "source": "exemplar wiki source pages + graph topology",                     "hosts_on_check": ["C-8 analytic moves", "C-3 narrative arc", "IS-theory pass (Baird C-4)"]}
}
```

## 6. C-7 identity-layer fence (non-negotiable)

The exemplar set informs the **discipline layer** — domain conventions and argument-derivation architecture — and **must not** overwrite the author's **identity layer** (sentence-length signature, cadence, repetition tolerance, humor, evaluative stance). The harness writes *domain-native per Yu's conventions, in the author's voice*. Where the exemplar register and the author's fingerprint conflict, surface for adjudication (C-5/C-7 arbitration); never default to Yu-pastiche.

```json
"c7_fence": {"anchor_scope": ["domain_conventions", "argument_derivation"], "protected_identity_layer": ["sentence_length_signature","cadence","repetition_tolerance","point_of_view","humor","evaluative_stance","characteristic_metaphor"], "conflict_resolution": "surface_for_adjudication"}
```

## 7. Write / review / revise derivations (all from this one object)

- **Write (generative):** condition drafting on retrieved near-neighbor exemplar passages for the current argument move; do not draft from generic priors.
- **Review (discriminative):** flag surface constructions with no attestation warrant and argument moves with no exemplar warrant — a grounding-shaped check. Absence of warrant = advisory candidate (§3), not automatic finding.
- **Revise (operational):** substitute an unwarranted construction with an *attested* one drawn from the corpus (never a fresh invention), preserving propositional content (dilution guard) and the C-7 fence.

## 8. Provenance & drift — two-level pin

The pin is **semantic, not file-level** (§3 `pin` + `hash_recipe`). Two objects gate; one is recorded but never gates:

- **Gates (MF-POLICY semantic-pin block):** `attestation_view_pin` and `exemplar_view_pin` only. Block when the manuscript's / binding's recorded pins differ from the current recomputed views — i.e., when the *register itself* changed under the manuscript.
- **Gates separately (D-4):** `profile_sha256` over the whole `reader_accessibility.v1.json` file. Do **not** fold semantic pins into the profile-file hash failure mode — emit distinct MF-POLICY reasons (`MF-POLICY-PROFILE-STALE` vs `MF-POLICY-ATTESTATION-PIN-STALE` / `MF-POLICY-EXEMPLAR-PIN-STALE`).
- **Never gates:** `graph_sha256_provenance`. Unrelated wiki growth (new pages, community reshuffles **outside** the RE predicate) must not block. Reshuffles **inside** the RE predicate change attestation membership → real delta → deliberate re-pin (even if no snowball ran).

Re-pin cadence is organic but explicit: recompute at milestone transitions and after any snowball round that admits new grounded sources; auto-accept on no-delta; a real delta (including MF-POLICY-discovered membership change at review, or newly staged exemplar PDFs) requires a deliberate one-line versioned re-pin. The yardstick never moves silently or mid-cycle — that keeps Ph3 convergence falsifiable and prevents in-loop stub write-back from becoming circular self-attestation. Run the existing drift-detection cadence when exemplar source phrases are used.

## 9. Resolved / residual items (updated at review, 2026-07-13)

- **Resolved:** `goncalves-2019-istar-extension` was promoted stub → **section-read** on 2026-07-13 (pypdf read-through, abstract + introduction; grounding_note on the source page). It is now admitted to the exemplar core (§4) under the deny-list rule. Residual: mid/end guideline set not exhaustively mapped — its surface warrant carries lower confidence; deepen to full-read if its register is leaned on heavily.
- **Resolved (post second-opinion):** pin byte recipe, RE-predicate membership rule, PDF-staging delta rule, and distinct MF-POLICY binding keys vs D-4 `profile_sha256` are now specified in §3 (`hash_recipe`, `related_to_RE_predicate`, `mf_policy_binding_keys`) and restated in §8. Policy remains closed; Codex implements the recipe as written.
- **Note for Codex:** `references/policies/reader_accessibility.v1.json` does **not exist yet** — it is the Task 4A deliverable this object plugs into (see `docs/analysis/2026-07-13_task4a-cadence-and-j-dropins.md` and the milestone-framework plan). Treat it as create-target, not read-target.
- **Verified at review:** all 5 exemplar PDFs staged in `raw/corpus/`; `yu-1995-istar.pdf` SHA-256 matches the §4 pin exactly; all 12 source pages exist with the grounding tiers stated in §4; graph.json present (hash at review recorded in §3).
- **Seed-resolution reality (measured 2026-07-13, graph @ 559 nodes / 811 links):** only 3/12 exemplar seeds resolve — 1 by id, 2 by the source-file join after document/`_source` disambiguation (§3 `seed_resolution`); 9/12 are `unresolved_seed_ids` today. The attestation view is currently built from communities {5, 10} only. This is why §3 carries a `degeneracy_guard` with an **inclusive** seed floor (`resolved_seed_count <= 3`): today's measured base must emit WARNING, not certify silently green. Backfilling the missing sources into the graph (graphify re-run over the newer wiki pages) is the organic fix and is a real membership delta → deliberate re-pin when it lands. Out of Codex scope.
