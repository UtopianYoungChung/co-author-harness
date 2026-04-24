# Tier Close-Out Artifact Schema (v0.5.4)

**Status.** Normative schema for `reviews/tier_closeout_<round>_<YYYY-MM-DD>.md`. Binding on the Planner's Phase 5.5 step (b) emission and on the Reflector's Phase 2c read-path.

**Paired with.** `TIER_PROTOCOL.md §11` (Tier Close-Out Protocol) and `AGENT_ORCHESTRATION.md §8.2b` (Tier Decisions Log). Read those first; this file carries only the schema.

---

## 1. File naming

```
reviews/tier_closeout_<round>_<YYYY-MM-DD>.md
```

Where `<round>` is the integer round identifier matching `manuscript/revision_log.md` and `reviews/escalation_log.md`'s `round_id`, and `<YYYY-MM-DD>` is the local date at Phase 5.5 emission.

Example: `reviews/tier_closeout_07_2026-04-19.md`.

---

## 2. Canonical template

```markdown
---
round: 7
tier_entered: T3
tier_entered_via: initial-dispatch
ascent_observed: [T3]
classification_tier: T4
advisories: []
---

# Tier Close-Out — Round 7 (T3, standard)

## Delta (deterministic)

- BLOCKER: 4 → 0
- MAJOR:   11 → 3
- MINOR:   28 → 14
- Paragraphs touched: 17
- Escalation gates fired this round: [EG-4]
- Wall-clock (min): 18.2

## Narrative (Evaluator-authored, ≤ 120 words)

The round closed four BLOCKERs tied to Baumer-style contradictions in §3
and reduced MAJOR count by 73%. Residual MAJORs concentrate in §5
(operationalization) and §7 (discussion). Grounding integrity held:
zero Rule 4 violations; two Rule 7a deferrals against the LLM wiki
remain open and are tracked separately. Remaining risk is thematic,
not fabrication-class; a T1 polish pass is likely sufficient barring
new contradictions introduced on rewrite.

## Close-out choice

**Available:** Down (T2, T1), Stay (T3), Up (T4), Done
**Present tier:** T3
**Planner note:** Residual MAJORs are local to §5 and §7; a targeted T2 run could close them without a second full pass.
```

---

## 3. Frontmatter fields

Every field below is **required**. A missing field fails `scripts/tier-closeout-schema-check.py` and is surfaced as a SAFEGUARD Check 5 (Edit Traceability) structural violation at the next Reflector audit.

- **`round: <int>`** — matches the round identifier across the round's artifacts. Not a string; write `7`, not `"7"` or `"round-07"`.

- **`tier_entered: T1 | T2 | T3 | T3R | T4`** — the tier at which this round executed, after any in-round escalations settled. T0 never appears (T0 rounds do not emit this artifact).

- **`tier_entered_via: initial-dispatch | user-up | user-stay | user-down | auto-escalation-EG-<n>`** — the provenance of how the round landed at its present tier. `initial-dispatch` is first round of session; `user-up / user-stay / user-down` are Phase 5.5 elections from a prior round; `auto-escalation-EG-<n>` is a mid-round gate firing (EG-1 through EG-7 are legal).

- **`ascent_observed: [<list of tiers>]`** — the ratchet state at round-close, copied from `reviews/tier_decisions_log.md`'s session header as updated by this round. Used by Phase 2c to compute the ratchet-suppression metric.

- **`classification_tier: T0 | T1 | T2 | T3 | T3R | T4`** — copied verbatim from `reviews/classification.md`'s `tier:` field. The Phase 5.5 handler compares this against `tier_entered` to decide whether `[DECLARED-COMPLETION-BELOW-TIER]` fires on a `Done` election.

- **`advisories: [<list of advisory tags>]`** — list of advisory tags active at emission, or `[]`. Legal values: `[DECLARED-COMPLETION-BELOW-TIER]`, `[USER-OVERRIDE]`, `[RATCHET-VIOLATION-ATTEMPTED]`, `[NARRATIVE-TRUNCATED]`. The `[DECLARED-COMPLETION-BELOW-TIER]` tag is written only when a `Done` election actually occurs and `tier_entered < classification_tier`; it is not pre-populated.

---

## 4. Body sections

### 4.1 Title (required)

```
# Tier Close-Out — Round <n> (<tier>, <tier label>)
```

Tier labels: `T1 = reflex`, `T2 = local`, `T3 = standard`, `T3R = response-letter`, `T4 = submission-bound`.

### 4.2 Delta block (required)

Six lines exactly, each required:

- BLOCKER: `<pre>` → `<post>` (integer counts from the consolidated findings report, pre-round and post-round)
- MAJOR: `<pre>` → `<post>`
- MINOR: `<pre>` → `<post>`
- Paragraphs touched: `<int>` (distinct paragraph count in this round's revision_log entry; a single paragraph touched three times counts as one)
- Escalation gates fired this round: `[<list of EG-n>, …]` or `[]`
- Wall-clock (min): `<float>` (time between first Evaluator dispatch and Phase 5.5 emission, to one decimal)

Any line that cannot be computed from round artifacts is written as `[UNVERIFIED: <reason>]`. Fabricated numbers are a Rule 6 gap-fill violation; Rule 7a does not apply here because no external verifier is in scope.

### 4.3 Narrative block (required)

A single paragraph, ≤ 120 words. Evaluator-authored. No recommendations. Covers: what substantively changed; where residual risk lives; whether risk is fabrication-class or thematic-class; grounding-rule deferrals still open.

The 120-word bound is enforced at write time. If the Evaluator's draft exceeds the budget, the Planner truncates at the nearest sentence boundary below 120 words, appends `[NARRATIVE-TRUNCATED]` to `advisories`, and surfaces the truncation advisory in the user notification.

### 4.4 Close-out choice block (required)

Three lines:

- **Available:** `<subset of {Down, Stay, Up, Done}>` — the offered-choice set after the ratchet has suppressed unreachable Down affordances. Write `Down (T<a>, T<b>)` with explicit destinations; `Stay (T<n>)`; `Up (T<a>, T<b>, T<c>)`; `Done`.
- **Present tier:** `T<n>`
- **Planner note:** `≤ 1 sentence` — the Planner's situational signpost. This is not a recommendation. Phrases like "likely sufficient" are legal only if strictly scoped ("... barring new contradictions on rewrite"); unconditioned recommendations ("you should pick Down") are not.

---

## 5. Validation

`scripts/tier-closeout-schema-check.py` (to land with v0.5.4) validates every field and section in this schema. A release-gate run checks every `reviews/tier_closeout_*.md` in the project tree. Schema failures fail the gate.

Minimum validation surface:

1. Frontmatter has all six required keys; no unknown keys.
2. `tier_entered`, `tier_entered_via`, `classification_tier` use legal enum values.
3. `round` is an integer; `ascent_observed` is a YAML list; `advisories` is a YAML list.
4. Delta block has all six lines; counts are non-negative integers; wall-clock is a float with one decimal.
5. Narrative paragraph is ≤ 120 words; `[NARRATIVE-TRUNCATED]` advisory is present iff the narrative was clipped.
6. Close-out choice block has all three lines; offered set is a subset of `{Down, Stay, Up, Done}`; Down destinations are all strictly less than the present tier.

---

*Last updated: 2026-04-19. Introduced at v0.5.4 Phase E.1.*
