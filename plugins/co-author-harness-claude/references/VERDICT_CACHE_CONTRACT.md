# VERDICT_CACHE_CONTRACT — Paragraph-Hash Verdict Carryover Cache (P-14)

**Status.** v0.8.0 Phase 4 (β P-14 pulled-forward). Evaluator-owned; the Planner does not read the cache.

**Grounding basis.** `proposals/v0.7.5_phase3_refinement_loop_proposal.md §P-14`; `PHASE_PROTOCOL.md §3.3.0 (check_profile, halo_scope)`; `DETERMINISTIC_CHECKS.md` and `SAFEGUARD_LAYER.md` (authoritative `halo_scope` per-check matrix); `scripts/paragraph_hash_map.py` (paragraph-id and hash format); `AGENT_CONTRACTS.md §2` (Evaluator); `phase_state_schema.md §2` (model_used field).

---

## 1. Purpose

When an Evaluator round runs under `check_profile: refine` or `structural`, many paragraphs are byte-identical to the prior iteration. Re-running every check on unchanged paragraphs is the paradigmatic cost-waste case at Ph3. The verdict cache allows the Evaluator to carry forward per-paragraph, per-check verdicts from prior iterations when the paragraph's content hash has not changed and the model family has not downgraded.

The cache is an **optimization layer**, not an authority source. A cache hit is a shortcut; a cache miss falls through to the live check. The Evaluator may always discard the cache and re-evaluate from scratch.

---

## 2. Cache location and ownership

- **Path:** `reviews/.evaluator_verdict_cache/<manuscript_id>.json`
- **Owner:** Evaluator (sole reader and writer). The Planner does not read the cache. The Reflector's Phase 2f audit may inspect the cache for integrity but does not modify it.
- **Lifecycle:** Created on the first cache-eligible Evaluator round; updated after each round; deleted on retraction to Ph2 or Ph1 (the cache does not survive phase demotion below Ph3).
- **Not a ledger artefact.** The cache is not tracked in `phase_state.json` and is not subject to monotonicity constraints. It may be deleted at any time without data loss — the next round simply runs without cache hits.

---

## 3. Cache-key specification

### 3.1 Paragraph-local checks (`halo_scope: paragraph`)

```
key = SHA-256( paragraph_hash || check_id )
```

Where:
- `paragraph_hash` — the SHA-256 hex digest from `paragraph_hash_map.py` for the paragraph at its `p-NNNN` id.
- `check_id` — the canonical check identifier (e.g., `deterministic_em_dash`, `safeguard_check_1`).

The `model_family` is stored in the entry (§4) but is NOT part of the key. Model-family filtering is applied at lookup time via the capability-inversion check (§5), allowing a verdict cached by a more-capable model to be reused by a less-capable consumer without a key miss.

### 3.2 Cross-paragraph checks (`halo_scope: immediate_neighbour` or `containing_section`)

```
key = SHA-256( paragraph_hash || check_id || diff_scope_fingerprint )
```

Where `diff_scope_fingerprint = SHA-256( sorted(changed_paragraph_id_set) )`. The changed-paragraph set comes from the Planner's Phase 0.6 dispatch plan (the diff between the current and prior `paragraph_hash_map`). Cross-paragraph verdicts are invalidated when any paragraph in the halo changes, even if the focal paragraph is byte-identical. As with §3.1, model-family filtering is at lookup time (§5), not in the key.

### 3.3 Check-class tagging

Each check's cache-class (`paragraph_local` or `cross_paragraph`) is derived from the `halo_scope` field published in the authoritative per-check matrix at `DETERMINISTIC_CHECKS.md` and `SAFEGUARD_LAYER.md`:

| `halo_scope` | Cache class | Key shape |
|---|---|---|
| `paragraph` | `paragraph_local` | §3.1 |
| `immediate_neighbour` | `cross_paragraph` | §3.2 |
| `containing_section` | `cross_paragraph` | §3.2 |

Checks without a published `halo_scope` assignment default to `cross_paragraph` (conservative — the halo is unknown, so the cache key must include the diff fingerprint).

---

## 4. Cache entry format

```json
{
  "schema_version": "0.8.0",
  "entries": {
    "<cache_key_hex>": {
      "paragraph_id": "p-NNNN",
      "check_id": "...",
      "model_family": "opus",
      "verdict": "PASS | MINOR | MAJOR | BLOCKER",
      "finding_summary": "...",
      "source_iteration": "cycle_id",
      "cached_at": "ISO-8601",
      "paragraph_hash": "hex",
      "diff_scope_fingerprint": "hex | null"
    }
  }
}
```

---

## 5. Capability-inversion protection

The cache refuses hits across a model-family **downgrade** on the family ordering:

```
Haiku 4.5  ≺  Sonnet 4.6  ≺  Opus 4.7
```

**Rules:**
- A verdict cached by Opus is usable by Opus, Sonnet, or Haiku (the caching model is at least as capable as the consumer).
- A verdict cached by Sonnet is usable by Sonnet or Haiku, but **not by Opus** — the cache entry was produced by a less-capable model.
- A verdict cached by Haiku is usable only by Haiku.

**Implementation.** On cache lookup, compare `entry.model_family` against the current round's model family. If `entry.model_family ≺ current_model_family` (i.e., the entry was produced by a weaker model than the current consumer), the hit is refused and the check runs fresh. This prevents a low-capability verdict from suppressing a finding that a higher-capability model would have caught.

**Model-family change across rounds.** When the Planner's dispatch allocates a different model family for the Evaluator than the prior round used, the effective cache hit-rate drops because many entries fail the capability-inversion check. This is by design — model upgrades are not free; they earn their cost by re-evaluating with higher capability.

---

## 6. Cache lifecycle events

| Event | Cache action |
|---|---|
| Ph3 iteration closes (any `check_profile`) | Evaluator writes new/updated entries for checks run in this round |
| Paragraph hash changes | Entries keyed to the old hash are stale; lookup misses naturally |
| Model-family upgrade | Entries from weaker models refuse hits (§5); fresh verdicts replace them |
| Model-family downgrade | Not permitted at the Evaluator level (`E-MA-CAPABILITY-INVERSION` refused) |
| Retraction to Ph2 or Ph1 | Cache file deleted (phase demotion invalidates the review substrate) |
| Ph3 stability sub-mode | Cache is not consulted (stability runs grounding + Check 8 counters only; verdict cache is for judgment-pass checks) |
| Ph4 dispatch | Cache is consulted but all entries must pass the Ph4 severity-floor escalation; a cached MAJOR that is now BLOCKER at Ph4 is surfaced as a miss |

---

## 7. Instrumentation

Cache hit/miss statistics are reported in `reviews/reflection_report.md` on every post-cache-land round:

- `cache_hit_count` / `cache_miss_count` / `cache_refused_capability_inversion`
- `cache_hit_rate` = hits / (hits + misses + refused)
- Per-check-class breakdown (paragraph_local vs cross_paragraph)

The Reflector's Phase 2f audit may inspect the cache for integrity (e.g., entries whose `paragraph_hash` no longer matches the current `paragraph_hash_map` — a sign of stale entries that should have been evicted).

---

## 8. Threshold versioning

Cache entries carry the `threshold_version` from the F6 dispatch plan that governed their source iteration. When `threshold_version` changes between rounds (e.g., `v0.7.5-provisional` → `v0.8.0-provisional`), entries produced under the old version are treated as misses — the check must re-run under the new thresholds.

---

*Authored at v0.8.0 Phase 4 (β P-14 pulled-forward). The cache is an optimization layer; the live check is always authoritative. This contract is subordinate to `PHASE_PROTOCOL.md` and `AGENT_CONTRACTS.md`.*
