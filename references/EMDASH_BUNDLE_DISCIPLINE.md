# EMDASH BUNDLE DISCIPLINE — AI-Tell Removal Bundle

**Purpose.** This file defines a top-level discipline binding all manuscript-prose generation in the harness. The discipline is a **bundle treatment** of three humanizer-style AI-tell rules that recur together in LLM-authored prose: em-dash overuse (rule 13 / DETERMINISTIC_CHECKS §3), negative parallelism ("not just X but Y" stacks; rule 9 / DETERMINISTIC_CHECKS §4 row 1), and triadic-list / rule-of-three repetition (rule 11 / DETERMINISTIC_CHECKS §4 row 2). Each rule is independently auditable; the bundle treatment is the discipline of auditing all three together at every prose-action site, on the rationale that they are co-occurrent symptoms of a single AI-prose register.

**Status.** **MANDATORY at every Generator prose action — no exceptions.** Per user adjudication 2026-04-30 (v0.13.0): "this rule applies to every instance with no exception." A waiver requires an explicit user instruction in the current session; the Generator cannot self-waive, and inherited waivers from prior sessions are invalid. The discipline is parallel in binding force to `GROUNDING_PROTOCOL.md` — both are non-negotiable rules that override the §4 STYLE_COMMITMENTS.md relaxation procedure.

**Provenance.** Authored 2026-04-30 (v0.13.0) per `docs/superpowers/plans/2026-04-30-voice-and-h-lessons.md` cluster 3.6 (em-dash-bundle elevation per Q4 answer). The bundle treatment surfaced from the INF3006Y Overview restructure (2026-04-30) where a single em-dash-protocol audit caught not only the em-dash overuse but co-occurring negative parallelisms and a redundant restatement, on a single pass. The single-pass economy is what motivates the elevation: auditing rule 13 alone misses the co-occurrent rules 9 and 11 that almost always travel with it.

---

## 1. The bundle's three rules

| Bundle ID | DETERMINISTIC_CHECKS reference | Pattern | Bundle behavior |
|---|---|---|---|
| **B1 (em-dash)** | §3 line 63 (H-motivated em-dash insertion); §3 em-dash count | `---` (LaTeX) or `—` (plain text) used as M4 vehicle, parenthetical pair, or trailing-emphatic punctuation | Audit count; count must not increase across any prose action; preferred substitutions per §3 line 63 (semicolon, colon, explicit signpost cue) |
| **B2 (negative parallelism)** | §4 row 1: `\bnot (just \|only \|merely )?\S+ but\b` | "not just X but Y" / "not only X but Y" / "not merely X but Y" | Audit count; threshold ≤2 per file; rewrite excess as direct assertions |
| **B3 (triadic / rule-of-three)** | §4 row 2: triadic lists `A, B, and C` repeated across paragraphs | Three parallel items, especially when stacked across consecutive paragraphs | Reduce by half if obviously stacked; break at least half into asymmetric pairs or singletons |

The three rules are **co-audited**: when the Generator applies any prose action (drafting, revising, fix-applying), all three rules must be checked at the affected paragraph(s) before the action is committed. A finding under any one rule triggers an audit of the other two at the same site.

## 2. Why bundle treatment

Empirical observation across the INF3006Y manuscript polish: every site where rule 13 fired, at least one of rules 9 or 11 also fired (often both). The three rules are not independent symptoms — they are co-occurrent expressions of a single AI-prose register characterised by emphatic-punchy phrasing, parallelism-stacking, and triadic enumeration. A Generator that audits them separately catches each rule's instances but misses the *cluster*-level signal that the prose has drifted into AI-tell register at this paragraph.

Bundle treatment also provides a single audit pass with three-rule coverage, reducing the Generator's per-action overhead. The audit cost is sub-additive: counting em-dashes, "not X but Y" matches, and triadic structures across the same paragraph runs in roughly the same time as counting any one alone, since the bottleneck is paragraph-reading, not rule-matching.

## 3. The audit procedure

At every Generator prose action (Ph1 drafting, Ph2/Ph3 fix application, Ph4 fix-only-no-new-prose):

1. **Pre-action snapshot.** Before the action, capture the affected paragraph(s)' counts: B1 (em-dash count), B2 (negative-parallelism stack count), B3 (triadic structure count).
2. **Apply the action.** Draft, revise, or fix per the Planner/Evaluator directive.
3. **Post-action snapshot.** Recapture the same three counts on the affected paragraph(s).
4. **Bundle delta check.** For each of B1/B2/B3: post-count must be ≤ pre-count. If post-count exceeds pre-count, the action **introduced** an AI-tell — flag as a self-correction candidate, revise the action to use §3-neutral substitutes (B1 → semicolon/colon/signpost cue; B2 → direct assertion; B3 → asymmetric pair or singleton), and re-snapshot.
5. **Cross-rule co-audit.** If any of B1/B2/B3 fires (count > prior baseline OR ≥1 instance in a previously-zero paragraph), audit the other two at the same site for co-occurrent fires; rewrite to clear all three before committing.
6. **Commit.** Only commit the action when post-snapshot satisfies the bundle delta check across all three rules.

## 4. The fix procedure (when the bundle fires on existing prose, not on a new action)

When the Evaluator surfaces a finding under any of B1/B2/B3 in the existing manuscript, the Generator's fix must:

1. **Co-audit the other two rules at the same site.** If the finding is under B1, check B2 and B3 at the same paragraph. If under B2, check B1 and B3. If under B3, check B1 and B2. The co-audit is mandatory; the Generator does not fix one rule and leave the others.
2. **Fix all rules that fire at the site, in a single revision pass.** Multi-rule fixes are committed as a single revision-log entry with all three rule-references listed in the Rule-trace field. Splitting a multi-rule fix across multiple revision passes is prohibited because intermediate passes leave the prose in an unstable register state where some rules are fixed and others are not.
3. **Verify post-fix.** Re-run the audit procedure (§3 above) to confirm all three rules are clear at the fixed paragraph.

## 5. Waiver process

A waiver of the bundle discipline at a specific site requires an **explicit user instruction in the current session**. The waiver must:

- Name the specific paragraph or sentence where the waiver applies.
- Name the specific rule (B1, B2, or B3) being waived.
- Provide a rationale for the waiver (e.g., "the em-dash here is mid-quote and cannot be substituted without altering the source quote").

The Generator records the waiver in `manuscript/revision_log.md` with `waiver_user_session: <session_id>` and the user's verbatim instruction. **Inherited waivers from prior sessions are invalid** — a new session resets the binding, and the user must re-issue the waiver if it is still desired. The Generator cannot self-waive, and the Planner cannot waive on the user's behalf.

## 6. Versioning

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-04-30 (v0.13.0) | Initial authoring. Three-rule bundle (B1 em-dash, B2 negative parallelism, B3 triadic-list); mandatory at every prose action; waiver process defined; co-audit and bundle delta check procedures specified. Per `docs/superpowers/plans/2026-04-30-voice-and-h-lessons.md` cluster 3.6 (Q4 elevation). |

**Note.** This file is the canonical home for the AI-tell-bundle discipline. Cross-references in `agents/generator.md` Binding Constraints, `references/CLAUDE.md` precedence ladder, and `DETERMINISTIC_CHECKS.md §3 / §4` should resolve here rather than re-state the rules in prose.
