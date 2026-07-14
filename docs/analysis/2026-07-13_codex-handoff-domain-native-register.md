# Handoff to Codex — wire the Domain-Native Register Model into Task 4A + M1

*2026-07-13. From the Cowork second-opinion session. Spec reviewed and corrected same day; every factual claim below was re-verified against the live wiki, corpus, and harness tree at review time. Authoritative spec: `docs/analysis/2026-07-13_domain-native-register-model.md` (read it in full first — this handoff scopes the work, the spec defines the object).*

---

## 1. What you are building

Operationalize "plain English" for the harness as **domain-native register** (`register_class: domain-native`) — a register model anchored to one pinned graphify view and a Yu-centroid exemplar set — and wire it into two implementation targets you already own in the milestone-feedback-framework plan:

1. **Task 4A profile** (`references/policies/reader_accessibility.v1.json`, plan §Task 4A, lines ~396–402): embed the register-model object (spec §§2–8) alongside the cadence/sub-check keys already drafted in `docs/analysis/2026-07-13_task4a-cadence-and-j-dropins.md`. The register model supplies the Sub-check H (register appropriateness) semantics and the humanizer/lexicon routing layer.
2. **M1 reader record** (plan Step 7, line ~478): M1 records intended readers — use the spec §2 `reader_model` object verbatim as that record's shape. M3 then records the resolved profile path/hash; `MF-POLICY` blocks stale or mismatched evidence, extended per spec §8 to cover the **semantic pin** (attestation-view membership + exemplar-view hashes), never the raw graph hash.

## 2. Non-negotiables (do not re-derive; already adjudicated)

- **Domain-native ≠ lay simplification.** The bar is insider fluency for the four M1 reader classes. Lay-plain applies only to genuinely public-facing passages (Eubanks-style policy sections).
- **Two node-selections, one pinned graph** (spec §3): broad *attestation* view for the negative "is this foreign?" check; narrow *exemplar* view for the positive target. **Absence of attestation is advisory-only** — the wiki under-covers the field; never auto-fail on absence.
- **Two warrant layers, never conflated** (spec §5): surface warrant from exemplar PDFs/verbatim extracts; argument-architecture warrant from wiki source pages + graph topology. Conflating them repeats the J-in-H category error.
- **C-7 fence** (spec §6): exemplars inform the discipline layer only. Identity-layer conflicts surface for adjudication; never default to Yu-pastiche.
- **Exemplar admission is a DENY-LIST**: `grounding_status ∈ {stub, unresolved}` excluded, everything else admitted with tier as confidence attribute, **prefix-tolerant parse** — wiki tier values carry free-text annotations (`full-read — 201/201 pages…`, `full-text-pass`, `section-read-verified`). An exact-match enum will wrongly reject grounded pages; this was caught at review.
- **The pin is SEMANTIC, two-level** (spec §3 `pin` + `hash_recipe`, §8 — adjudicated 2026-07-13 after review): gate on (a) `attestation_view_pin` and (b) `exemplar_view_pin` only. Raw `graph.json` sha256 is `graph_sha256_provenance` and **never gates**. Store these as **distinct** MF-POLICY binding keys from D-4 `profile_sha256` — do not collapse "policy file stale" and "register view stale." Re-pin cadence: recompute at milestone transitions and after grounded-source-admitting snowball rounds; also when review discovers an in-predicate membership delta without a snowball; auto-accept on no-delta; real delta (including newly staged exemplar PDFs) requires a deliberate versioned re-pin. Never silent, never intra-cycle. **Implement the byte recipe in spec §3 `hash_recipe` as written** — that is implementation under settled policy, not a re-opening of the pin scheme.

## 3. Path roots — resolve explicitly (a traversal already misfired once today)

| Root | Path | Governs |
|---|---|---|
| `wiki_root` | `B:/Agents/knowledge/LLM wiki` | `raw/corpus/*` PDFs, `wiki/sources/*` pages |
| `workspace_root` | `B:/Agents` | `knowledge/LLM wiki/graphify-out/graph.json` |
| `harness_root` | `B:/Agents/platform/co-author-harness` | `references/policies/*`, `scripts/*`, everything you write |

`reader_accessibility.v1.json` **does not exist yet** — it is your Task 4A create-target, not a read-target.

## 4. Verified inputs (state as of 2026-07-13 evening)

- 12/12 exemplar source pages exist with the grounding tiers stated in spec §4; all 5 exemplar-core PDFs staged in `raw/corpus/`.
- `yu-1995-istar.pdf` SHA-256 = `C5F6472EE3348DBDF1D1D239BBF1FF9003B231953AC2C72266DA63A4381E0199` (matches spec pin exactly).
- `goncalves-2019-istar-extension` was promoted stub → `section-read` today and is **admitted** (role `istar-extension-halo`, lower-confidence surface warrant — abstract+intro read; deepen to full-read only if its register is leaned on heavily). No open decision remains here.
- `graph.json` observed at review: SHA-256 `EDF94FA6121794915A8C9C221D41869333BA3E837DDD7F5B9138290042F3090F` (modified 2026-07-13 19:34 by same-day stub write-back). Under the two-level scheme this is **provenance metadata only** — record it at each pin event as `graph_sha256_provenance`, but the gating pins you compute at build are the two view hashes (spec §3 `pin.pinned_objects` + `hash_recipe`).
- **Seed resolution, measured (graph @ 559 nodes / 811 links, 2026-07-13): 3/12 exemplar seeds resolve — 1 by exact id, 2 by the `source_file` join after document/`_source` disambiguation (spec §3 `seed_resolution`); 9/12 are `unresolved_seed_ids` today.** Degeneracy is the current normal, not an edge case: the attestation view spans communities {5, 10} only. Implement the two-step resolution rule (incl. multi-hit disambiguation) and the `degeneracy_guard` WARNING (`resolved_seed_count <= 3` OR `len(primary_communities) < 2`) exactly as specified — today's 3 resolved seeds **must** emit the WARNING. Do not invent nodes, do not fail the pin, do not let a thin view pass silently. Link fields: `source`/`target` is canonical; `_src`/`_tgt` are duplicates (0/811 divergent at review) — assert agreement, fail loudly on divergence.

## 5. Acceptance criteria

1. Profile validates against `references/schemas/reader_accessibility_profile.schema.json` and carries the register-model object with concrete `attestation_view_pin` and `exemplar_view_pin` (raw graph hash recorded only as `graph_sha256_provenance`).
2. `reader_accessibility_policy.py` resolves the register model with every contributing path/hash in its provenance output; binding keys keep `profile_sha256` (D-4) separate from the two view pins; `reader_accessibility_contract_smoketest.py` fails on semantic-pin drift (MF-POLICY staleness, spec §8) with distinct reason codes.
3. **Pin-scope test:** smoketest proves the asymmetry both ways — mutating `graph.json` *without* changing view membership does NOT block; changing view membership or an exemplar tuple (including staging a previously missing `pdf_sha256`) DOES. This is the whole point of the two-level scheme; test it explicitly against the §3 `hash_recipe`.
4. Admission-rule unit test includes annotated tier values and variants — proves the prefix-tolerant deny-list admits `full-read — 201/201…` and rejects `stub` and `unresolved`; proves `normalize_tier` keeps annotation edits from flipping `exemplar_view_pin`.
5. M1 record schema accepts the §2 `reader_model` shape; Sub-check H and the review/revise derivations (spec §7) reference profile keys, not hard-coded values (plan Step 5 discipline).
6. No identity-layer key appears in any auto-remediation path (C-7 fence test).
7. **Seed-resolution visibility test:** smoketest asserts the resolved provenance output records the `source_key`→`node_id` map (exactly one node per resolved key after disambiguation), populates `unresolved_seed_ids` (expect 9 against today's graph), and emits the `degeneracy_guard` WARNING under `resolved_seed_count <= 3` OR `len(primary_communities) < 2` (today's 3/12 resolved **must** fire it). A degenerate attestation view must never certify silently green.

## 6. Honesty constraints (carry into implementation notes, not just code)

"Condition drafting on retrieved exemplar passages" and "flag constructions with no corpus warrant" are disciplines, not guarantees: retrieval conditions generation without determining it, and warrant-absence is advisory by design. Do not present the register model as a determinism guarantee anywhere in prose surfaces. The residual judgment — "does this read native to Yu's tradition?" — remains with the Evaluator, now calibrated against grounded exemplars.

## 7. Out of scope for this handoff

- Grounding-tier promotion of any wiki page (Gonçalves deepening is optional and user-triggered).
- Re-pinning **policy** beyond spec §8 — the two-level scheme and its cadence are settled; do not re-open. Implementing `hash_recipe` / `related_to_RE_predicate` as specified is required work, not a policy re-open.
- The cadence/J-disposition drop-ins — already drafted in `2026-07-13_task4a-cadence-and-j-dropins.md`; where that file and `2026-07-13_supervisor-adjudication-v2.md` differ, the adjudication file is authoritative.
