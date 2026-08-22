# EMDASH BUNDLE DISCIPLINE — AI-Tell Removal Bundle

**Purpose.** This file defines a top-level discipline binding all manuscript-prose generation in the harness. The discipline is a **bundle treatment** of humanizer-style AI-tell rules that recur together in LLM-authored prose. The founding three are em-dash overuse (rule 13 / DETERMINISTIC_CHECKS §3), negative parallelism ("not just X but Y" stacks; rule 9 / DETERMINISTIC_CHECKS §4 row 1), and triadic-list / rule-of-three repetition (rule 11 / DETERMINISTIC_CHECKS §4 row 2). Four dispersion-side rules were added 2026-08-21 (B4–B7; DETERMINISTIC_CHECKS §4b). Each rule is independently auditable; the bundle treatment is the discipline of auditing the paragraph-local rules together at every prose-action site, on the rationale that they are co-occurrent symptoms of a single AI-prose register.

**Two tiers (added 2026-08-21).** B1–B3 and B6–B7 are **paragraph-local**: they name a pattern visible in the affected paragraph, so they are co-audited at every prose action per §3. B4–B5 are **document-level statistics** over a whole draft; a single paragraph has no coefficient of variation, so they are *not* part of the per-action delta check and are run once per round against the full artifact. Where a procedure below says "the co-audited rules," it means B1–B3 and B6–B7.

**Status.** **MANDATORY at every Generator prose action — no exceptions.** Per user adjudication 2026-04-30 (v0.13.0): "this rule applies to every instance with no exception." A waiver requires an explicit user instruction in the current session; the Generator cannot self-waive, and inherited waivers from prior sessions are invalid. The discipline is parallel in binding force to `GROUNDING_PROTOCOL.md` — both are non-negotiable rules that override the §4 STYLE_COMMITMENTS.md relaxation procedure.

**Provenance.** Authored 2026-04-30 (v0.13.0) per `docs/superpowers/plans/2026-04-30-voice-and-h-lessons.md` cluster 3.6 (em-dash-bundle elevation per Q4 answer). The bundle treatment surfaced from the INF3006Y Overview restructure (2026-04-30) where a single em-dash-protocol audit caught not only the em-dash overuse but co-occurring negative parallelisms and a redundant restatement, on a single pass. The single-pass economy is what motivates the elevation: auditing rule 13 alone misses the co-occurrent rules 9 and 11 that almost always travel with it.

---

## 1. The bundle's rules

| Bundle ID | DETERMINISTIC_CHECKS reference | Pattern | Bundle behavior |
|---|---|---|---|
| **B1 (em-dash)** | §3 line 63 (H-motivated em-dash insertion); §3 em-dash count | `---` (LaTeX) or `—` (plain text) used as M4 vehicle, parenthetical pair, or trailing-emphatic punctuation | Audit count; count must not increase across any prose action; preferred substitutions per §3 line 63 (semicolon, colon, explicit signpost cue) |
| **B2 (negative parallelism)** | §4 row 1: `\bnot (just \|only \|merely )?\S+ but\b` | "not just X but Y" / "not only X but Y" / "not merely X but Y" | Audit count; threshold ≤2 per file; rewrite excess as direct assertions |
| **B3 (triadic / rule-of-three)** | §4 row 2: triadic lists `A, B, and C` repeated across paragraphs | Three parallel items, especially when stacked across consecutive paragraphs | Reduce by half if obviously stacked; break at least half into asymmetric pairs or singletons |
| **B4 (rhythm uniformity)** | §4b; `scripts/register_dispersion_check.py` | Coefficient of variation of sentence length. Metronomic pacing — every sentence the same shape | **Measure and report. Finding only as a within-author delta against a supplied baseline** (see §1a) |
| **B5 (clause-depth uniformity)** | §4b; `scripts/register_dispersion_check.py` | Rate of pre-predicate interrupting material; proxy for subject–verb distance. Subjects sitting adjacent to their predicates throughout | **Measure and report. Finding only as a within-author delta** (see §1a). Fix via Bacon §§5–8: appositives, relative clauses, absolutes |
| **B6 (circular closure)** | §4b; `scripts/register_dispersion_check.py` | A paragraph's last sentence restates its first in different words instead of advancing | Audit; MINOR at content overlap ≥ 0.35. End with forward momentum — an implication, a question, a transition |
| **B7 (deflected complexity)** | §4b; `scripts/register_dispersion_check.py` | "Nuanced," "more complex than it appears," "a range of factors" — naming complexity instead of discharging it | Audit; MINOR per instance. Replace with the actual complexity: *it depends on X, Y, and Z*, with the dependence stated |

### 1a. B4/B5 are measurements, not thresholds (binding)

B1–B3 and B6–B7 are **detectors**: each names a pattern present in the text, and the
Generator can clear it by rewriting that pattern. B4 and B5 are **statistics about a
distribution**, and local calibration (recorded in `DETERMINISTIC_CHECKS.md` §4b)
found no population threshold that separates human from machine prose — the LLM and
human corpora overlapped, and the LLM sample scored *more* varied, not less. A
population band would have flagged Bacon's own published sentence-craft guide as
machine-generated.

Therefore B4 and B5 fire **only** as a within-author delta against the author's
accepted prose. With no baseline they are reported and nothing is asserted. This is
not a weaker form of the same rule; it is what C-7 requires, since the author's own
dispersion is the only defensible yardstick and a population constant is precisely
the borrowed register C-7 forbids importing. **No agent may treat a bare B4/B5
number as a defect, and none may reintroduce an absolute band without rerunning the
§4b calibration and recording the result there.**

### 1b. What was considered and rejected

Two further patterns from the same source were examined and deliberately **not**
added to the bundle. A *low-perplexity* rule (prescribing surprising word choices,
idioms, and colloquialisms) is a register prescription that collides head-on with
C-7's prohibition on imposing a borrowed voice, and the measure is known to misfire
on formal prose. A *synonym-cycling* detector would duplicate jurisdiction already
held as judgment by C-6 (one term, one concept) and Baird's terminology rule;
per `analytic_construction_guidelines.md` §6, an unowned feature invites
mis-handling, but a **doubly**-owned one invites contradictory findings. Temporal
vagueness was routed to `DETERMINISTIC_CHECKS.md` §7 rather than into this bundle,
because an undated "recent studies show" is a citation-integrity failure, not a
register tic.

The paragraph-local rules (B1–B3, B6, B7) are **co-audited**: when the Generator applies any prose action (drafting, revising, fix-applying), all five must be checked at the affected paragraph(s) before the action is committed. A finding under any one rule triggers an audit of the others at the same site. B4–B5 are document-level and run once per round per §3a.

## 2. Why bundle treatment

Empirical observation across the INF3006Y manuscript polish: every site where rule 13 fired, at least one of rules 9 or 11 also fired (often both). The three rules are not independent symptoms — they are co-occurrent expressions of a single AI-prose register characterised by emphatic-punchy phrasing, parallelism-stacking, and triadic enumeration. A Generator that audits them separately catches each rule's instances but misses the *cluster*-level signal that the prose has drifted into AI-tell register at this paragraph.

Bundle treatment also provides a single audit pass with three-rule coverage, reducing the Generator's per-action overhead. The audit cost is sub-additive: counting em-dashes, "not X but Y" matches, and triadic structures across the same paragraph runs in roughly the same time as counting any one alone, since the bottleneck is paragraph-reading, not rule-matching.

## 3. The audit procedure

At every Generator prose action (Ph1 drafting, Ph2/Ph3 fix application, Ph4 fix-only-no-new-prose):

1. **Pre-action snapshot.** Before the action, capture the affected paragraph(s)' counts for every co-audited rule: B1 (em-dash count), B2 (negative-parallelism stack count), B3 (triadic structure count), B6 (first/last-sentence restatement), B7 (undischarged complexity claims).
2. **Apply the action.** Draft, revise, or fix per the Planner/Evaluator directive.
3. **Post-action snapshot.** Recapture the same counts on the affected paragraph(s).
4. **Bundle delta check.** For each co-audited rule: post-count must be ≤ pre-count. If post-count exceeds pre-count, the action **introduced** an AI-tell — flag as a self-correction candidate, revise the action to use §3-neutral substitutes (B1 → semicolon/colon/signpost cue; B2 → direct assertion; B3 → asymmetric pair or singleton; B6 → close on an implication, question, or transition instead of a restatement; B7 → state the dependence rather than naming the complexity), and re-snapshot.
5. **Cross-rule co-audit.** If any co-audited rule fires (count > prior baseline OR ≥1 instance in a previously-zero paragraph), audit the others at the same site for co-occurrent fires; rewrite to clear them all before committing.
6. **Commit.** Only commit the action when post-snapshot satisfies the bundle delta check across every co-audited rule.

## 3a. Document-level pass (B4–B5)

B4 and B5 are statistics over a whole draft and cannot be evaluated on a single
paragraph, so they sit outside the per-action delta check. Run them once per review
round against the full artifact:

```bash
python scripts/register_dispersion_check.py <manuscript> --baseline <author's accepted prose>
```

Without `--baseline` the script reports the measurements and asserts nothing; that is
the calibrated behaviour, not a degraded mode (§1a). A B4/B5 finding is a **candidate
for Evaluator judgment**, and because it reports on the author's own rhythm it must
be dispositioned against C-7 before any rewrite: a flatter draft may be a defect, or
may be this author writing in a register the baseline does not yet cover.

## 4. The fix procedure (when the bundle fires on existing prose, not on a new action)

When the Evaluator surfaces a finding under any co-audited rule in the existing manuscript, the Generator's fix must:

1. **Co-audit the other rules at the same site.** If the finding is under B1, check B2, B3, B6, and B7 at the same paragraph; likewise for a finding under any other co-audited rule. The co-audit is mandatory; the Generator does not fix one rule and leave the others.
2. **Fix all rules that fire at the site, in a single revision pass.** Multi-rule fixes are committed as a single revision-log entry with every rule-reference listed in the Rule-trace field. Splitting a multi-rule fix across multiple revision passes is prohibited because intermediate passes leave the prose in an unstable register state where some rules are fixed and others are not.
3. **Verify post-fix.** Re-run the audit procedure (§3 above) to confirm every co-audited rule is clear at the fixed paragraph.

**B6/B7 carve-outs (binding).** A B6 restatement flag does **not** override C-8/M-5: a
cadential verdict that lands a long qualifying period is doing argumentative work
even when it echoes the paragraph's opening terms, and per `STYLE_COMMITMENTS.md` §5
it may not be deleted on a mechanical flag alone. Likewise a B6 flag on demonstrative
anaphora (C-8/M-4) is overturned. And a B7 hit is cleared, not rewritten, when the
sentence is *introducing* a complexity the following sentences actually discharge —
B7 targets complexity claimed and abandoned, never complexity claimed and then paid.

## 5. Waiver process

A waiver of the bundle discipline at a specific site requires an **explicit user instruction in the current session**. The waiver must:

- Name the specific paragraph or sentence where the waiver applies.
- Name the specific rule (B1–B7) being waived.
- Provide a rationale for the waiver (e.g., "the em-dash here is mid-quote and cannot be substituted without altering the source quote").

The Generator records the waiver in `manuscript/revision_log.md` with `waiver_user_session: <session_id>` and the user's verbatim instruction. **Inherited waivers from prior sessions are invalid** — a new session resets the binding, and the user must re-issue the waiver if it is still desired. The Generator cannot self-waive, and the Planner cannot waive on the user's behalf.

## 6. Versioning

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-04-30 (v0.13.0) | Initial authoring. Three-rule bundle (B1 em-dash, B2 negative parallelism, B3 triadic-list); mandatory at every prose action; waiver process defined; co-audit and bundle delta check procedures specified. Per `docs/superpowers/plans/2026-04-30-voice-and-h-lessons.md` cluster 3.6 (Q4 elevation). |
| 1.1 | 2026-08-21 | Extended to seven rules with the dispersion-side set: B4 rhythm uniformity, B5 clause-depth uniformity, B6 circular closure, B7 deflected complexity (`DETERMINISTIC_CHECKS.md` §4b; `scripts/register_dispersion_check.py`). Introduced the paragraph-local / document-level two-tier split: B1–B3 and B6–B7 are co-audited per prose action, B4–B5 run once per round (§3a). Recorded §1a — B4/B5 carry no absolute threshold because local calibration found no population separation — and §1b, the rejected candidates (low-perplexity register prescription, synonym-cycling duplicate jurisdiction). Added the B6/B7 carve-outs protecting C-8/M-4 anaphora and M-5 cadential verdicts. |

**Note.** This file is the canonical home for the AI-tell-bundle discipline. Cross-references in `agents/generator.md` Binding Constraints, `references/AGENTS.md` precedence ladder, and `DETERMINISTIC_CHECKS.md §3 / §4` should resolve here rather than re-state the rules in prose.
