---
name: response-letter-review
description: Review a response letter or rebuttal — opening strength, discipline provenance, tone audit, coverage completeness, scope hedging, and SAFEGUARD integrity checks. T3R entry point in the Incremental Tier Protocol (v0.5.0+).
trigger: when the user asks for response letter review, rebuttal check, reviewer response feedback, revise-and-resubmit help, or is my tone too defensive
created_by: Reflector
created_from: Tier 3 skill build, 2026-04-11 — research_paper_writing_guidelines.md §8 had no standalone review entry point
pattern_source: research_paper_writing_guidelines.md §8 + SAFEGUARD_LAYER.md Checks 1, 4, 5
tier_binding: >
  Response-letter manuscript-class within Ph3 (disposition settled 2026-07-07; the former independent T3R sibling ladder is retired — T3R survives as this entry point's historical label, v0.5.0 ancestry). Invoked by the Planner when the classification record carries paper_type=response-letter (legacy records carrying tier=T3R route here). Emits the three T3R artifacts (`reviews/response_letter_findings_<date>.md`, `reviews/response_letter_reframe_brief_<date>.md`, `manuscript/response_letter.md`) under `TIER_PROTOCOL.md §2.5` contract.
version: 1.1
---
# Response-Letter Review

You are reviewing a response letter (or rebuttal) for an academic venue submission. This skill implements the response-letter-specific rules from `research_paper_writing_guidelines.md §8` combined with targeted SAFEGUARD_LAYER integrity checks.

**Prerequisite:** Read `research_paper_writing_guidelines.md §8` and `SAFEGUARD_LAYER.md` (Checks 1, 4, 5) before proceeding.

## T3R dispatch contract (v0.5.0+)

At v0.5.0 this skill is the Evaluator-side entry point for the T3R mini-tier of the Incremental Tier Protocol. Under T3R the dispatch geometry is: Planner → Evaluator (this skill, seven checks) → Generator (reframe) → Evaluator (re-check) → Reflector. The dispatch is compressed relative to T3 and has three dedicated artifacts:

- **`reviews/response_letter_findings_<date>.md`** — the atomic seven-check output produced by this skill. Each check emits `PASS` / `FAIL` / `PARTIAL` with severity and a one-sentence rationale. The Evaluator writes this file.
- **`reviews/response_letter_reframe_brief_<date>.md`** — the Generator's binding instruction sheet. Produced by the Evaluator at the end of the seven checks; the Generator must consume it verbatim when rewriting the letter. Each entry in the brief names a finding, the proposed reframing, and the rule citation (Playbook §8 / SAFEGUARD Check N / Rule 7a).
- **`manuscript/response_letter.md`** — the letter itself, in the project manuscript folder. The Generator rewrites this file under the reframe brief; the Evaluator re-checks it on the second Evaluator hop.

**Escalation-out from T3R.** Three conditions escalate T3R to a higher tier and are recorded in `reviews/escalation_log.md`:

1. A contradiction between a concession in the letter and the revised manuscript's actual content → **T3 on the manuscript** (separate run). Under `SAFEGUARD_LAYER.md` Check 4 semantics; fires EG-4.
2. A render-contract failure on any Class 1 / 1.5 verifier citation in the letter → **T4 submission-bound re-audit** of the letter plus the manuscript passages that share the verifier output. Fires EG-6 if the submission deadline is within the venue's published minor-revision window.
3. An unaddressed reviewer point in the coverage report → **T3 on the manuscript** to recheck the passages the reviewer flagged.

These escalations are emitted by the Planner on signal from this skill, not by the skill itself. The skill's job is to emit the findings that trigger them.

---

## What you do

### Check 1 — Opening strength

Read the first two paragraphs of the response letter.

| Pattern | Verdict | Severity |
|---|---|---|
| Opens with **positive contribution** (what the paper adds, what was improved) | PASS | — |
| Opens with **limitations** (retrospective case, single site, narrow scope) | FAIL | [MAJOR] — "Do not open with limitations" (Playbook §8) |
| Opens with **defensive apology** ("we acknowledge the reviewers' concerns about…") | FAIL | [MAJOR] — reframe as constructive contribution |
| Opens with **generic gratitude** that occupies > 1 sentence before substance | PARTIAL | [MINOR] — keep gratitude to one sentence, then substance |

### Check 2 — Discipline provenance

For every imported theory or framework mentioned in the response letter:

| Check | What to look for | Severity if missing |
|---|---|---|
| **Parent discipline named** | Does the letter name the discipline the theory comes from (e.g., "from sociology of work," "from STS," "from organizational behavior")? | [MAJOR] — reviewers need provenance to evaluate fit |
| **Citation provided** | Is the foundational source cited? | [MINOR] — citations in response letters are helpful but not always required |

### Check 3 — Tone audit (defensive vs. constructive)

For each reviewer-by-reviewer response, classify the tone:

| Tone | Indicators | Verdict |
|---|---|---|
| **High-ground (constructive)** | Leads with what the revision contributes; reframes the reviewer's concern as an opportunity; uses "we strengthened" / "we clarified" / "we revised §X to" | PASS |
| **Neutral (compliant)** | Simply states what was changed without framing value | PARTIAL — acceptable but misses an opportunity |
| **Defensive** | Uses "we disagree" / "the reviewer misunderstood" / "we believe our original approach was correct" without softening or reframing | FAIL — [MAJOR] |
| **Submissive** | Accepts every criticism without judgment, including contradictory ones; strips the paper's contribution | FAIL — [MAJOR] — overcorrection |

For defensive responses, propose a **reframing**: show how the same substantive point can be made from the high ground.

### Check 4 — Coverage completeness

| Check | What to look for | Severity if missing |
|---|---|---|
| **Every reviewer point addressed** | Does the letter respond to every numbered or distinct concern from each reviewer? | [MAJOR] per unaddressed point |
| **Traceability to manuscript** | Does each response point to the specific section(s) in the revised manuscript where the change was made? | [MAJOR] — reviewers should not have to hunt for changes |
| **Prioritized ordering** | Are the most substantive changes addressed first, with minor formatting/typo fixes grouped at the end? | [MINOR] |

### Check 5 — Scope hedging

| Check | What to look for | Severity if missing |
|---|---|---|
| **Scrutiny-magnet words softened** | Does the letter avoid overclaiming? Words like "adequacy," "comprehensive," "complete" should be hedged if the evidence base is narrow | [MINOR] per instance |
| **Stage-appropriate claims** | If the revised paper is still exploratory, does the letter say so honestly rather than overclaiming generalizability? | [MAJOR] if overclaiming |

### Check 6 — SAFEGUARD integrity checks

Run three of the six SAFEGUARD_LAYER checks against the revised manuscript (not the response letter itself):

| SAFEGUARD Check | What it catches here | How to run |
|---|---|---|
| **Check 1 (Regression Guard)** | Did the revision introduce new problems while fixing the reviewer's concerns? Run deterministic checks on the revised draft; compare to the pre-revision state if available. | Quick deterministic scan + compare |
| **Check 4 (Contradiction Audit)** | Did the revision introduce or expose theoretical contradictions (e.g., accepting reviewer A's framing while also accepting reviewer B's, which may be incompatible)? | List all theoretical commitments in the revised draft; test pairs |
| **Check 5 (Edit Traceability)** | Does every change in the revised manuscript trace to either a reviewer comment or a self-identified improvement? Are there unexplained changes? | Compare revision log to reviewer comments |

### Check 7 — External-verifier render-contract audit (Category 9.a extended)

Response letters frequently cite external evidence to reply to reviewer challenges — "Baumer (2024) contests this framing," "Consensus rates this claim at 72% agreement across 14 papers," "HuggingFace reports model X at benchmark Y." When that evidence originates from Scholar Gateway, Consensus, or HuggingFace Papers, the render contracts declared in those verifiers' responses apply to the response letter just as they apply to the consolidated findings report (`EXTERNAL_VERIFIERS.md §3.1`; `REVIEW_ORCHESTRATION.md §7.5`). A response letter that cites Scholar Gateway evidence without rendering the contract is a Rule 7a violation in the rebuttal surface — reviewers reading the letter see the claim but not the provenance that the verifier's own terms require.

This check extends the Reflector's Category 9.a audit from the consolidated findings artifact to the response-letter artifact. Run it whenever the response letter draws on any Class 1 / 1.5 verifier.

**Scholar Gateway compliance (when any Scholar Gateway excerpt appears in the letter):**

| Item | Check | Severity if missing |
|---|---|---|
| **Contract marker** | Top of file: `<!-- scholar-gateway-contract: v0.1 -->` | [MAJOR] — reviewers cannot tell the letter is subject to the contract |
| **Per-search provenance line** | Before every paragraph that synthesizes Scholar Gateway output: `Scholar Gateway · <query> · <N> passages · <N> articles · <YYYY-MM-DD>–<YYYY-MM-DD>`, counts and date range copied verbatim from the response `provenance` object | [MAJOR] — Rule 7a violation specialized to rebuttal surface |
| **Gaps clause (conditional)** | If the Scholar Gateway result set was narrow (low count, short date range, or the author observed absence-of-evidence material to interpretation), a gaps-and-limitations sentence appears *before* the synthesis, not as a trailing caveat | [MAJOR] if narrow result set silently synthesized; [MINOR] if acknowledged only in a trailing caveat |
| **Inline citations** | Author-year format with DOI hyperlink (`https://doi.org/<doi>`), deduplicated across chunks — a paper that contributed two passages appears once in the citation list | [MAJOR] per undeduplicated cluster |
| **Session footer** | Rendered exactly once at end of letter: retrieval attribution, AI-summary caveat, corpus freshness date, content-coverage link, feedback link | [BLOCKER] if absent; [MINOR] if duplicated per-search ("over-rendering") |
| **Passage quoting (Rule 4)** | Quoted passages come from the `results[].text` field, not paraphrased from the paper's abstract | [MAJOR] — cross-reference Check 2 discipline provenance and Rule 4 quote-before-attribute |

**Consensus compliance (when any Consensus excerpt appears in the letter):**

| Item | Check | Severity if missing |
|---|---|---|
| **Journal-quartile tier surfaced** | If the Consensus result reports SJR quartile (Q1/Q2/Q3/Q4), the letter must state the quartile for the cited paper rather than paraphrasing Consensus's aggregate score without tier | [MINOR] — reviewers can recompute but the letter is less informative |
| **Sample-size disclosure** | If Consensus reports sample-size metadata for the cited study, the letter must name it when using Consensus evidence to defend a generalizability claim | [MAJOR] if generalizability is being defended and sample size is absent |
| **Aggregate-vs-paper disambiguation** | If the letter cites a Consensus aggregate ("72% agreement across 14 papers"), the letter must name whether the cited claim is an aggregate signal or a single-paper result. Reviewers conflate these; the letter should not | [MAJOR] — misattribution of aggregate authority to a single paper is a Rule 4 violation |

**HuggingFace Papers compliance (when any HuggingFace Papers excerpt appears in the letter):**

| Item | Check | Severity if missing |
|---|---|---|
| **Class-1.5 marker** | Any HuggingFace-sourced claim carries the tag `[verified: HuggingFace Papers — supporting]` or equivalent, reflecting that Class 1.5 is supporting evidence, not authoritative (`EXTERNAL_VERIFIERS.md §2` Class 1.5) | [MAJOR] — without the tag, the letter promotes Class 1.5 evidence to authoritative |
| **Cross-check to Class 1** | For any HuggingFace-sourced claim used to rebut a substantive reviewer concern, the letter must either cite a Class 1 verifier cross-check or tag the claim `[UNVERIFIED — Class 1.5 only]` | [MAJOR] — rebuttals anchored only on Class 1.5 are weak by the package's own tier rules |

**Advertised-but-unrendered detection.** If the response letter references Scholar Gateway / Consensus / HuggingFace Papers *by name* ("we ran a Scholar Gateway search," "Consensus rates this claim at…") but does not render the corresponding contract items listed above, the letter has a **rebuttal-side render-contract gap**. Severity is at least MAJOR; it escalates to BLOCKER if the same gap appears on a resubmission where the prior round already flagged it.

**Interaction with Checks 1–6.** Check 7 runs *after* Checks 1–6 so that tone and coverage are established first. A response letter that is otherwise compliant but fails Check 7 should not be submitted as-is; the Generator's fix is additive (insert provenance lines, add the session footer, deduplicate citations) and does not typically require reworking Checks 1–6.

### Output

```markdown
## Response-Letter Review Results

**File:** <path>
**Date:** <date>
**Venue:** <venue>
**Reviewers addressed:** <count>

### Check 1 — Opening Strength
- **Verdict:** PASS / PARTIAL / FAIL
- **Finding:** <what the opening does, and what it should do>
- **Severity:** — / [MAJOR] / [MINOR]

### Check 2 — Discipline Provenance
| Theory/Framework | Discipline named? | Citation? | Verdict |
|---|---|---|---|
| ... | ... | ... | ... |

### Check 3 — Tone Audit
| Reviewer | Response # | Tone | Verdict | Reframing (if defensive) |
|---|---|---|---|---|
| R1 | 1 | High-ground | PASS | — |
| R1 | 2 | Defensive | FAIL [MAJOR] | <proposed reframing> |
| ... | ... | ... | ... | ... |

### Check 4 — Coverage Completeness
- **Total reviewer points identified:** <n>
- **Addressed:** <n>
- **Unaddressed:** <n> → [list]
- **Traced to manuscript section:** <n>/<total>

### Check 5 — Scope Hedging
- **Scrutiny-magnet words:** <n instances> → [list with locations]
- **Stage-appropriate claims:** PASS / [MAJOR]

### Check 6 — SAFEGUARD Integrity
- **Regression guard:** PASS / <n> regressions found
- **Contradiction audit:** PASS / <n> contradictions found
- **Edit traceability:** PASS / <n> unexplained changes

### Check 7 — External-verifier render-contract audit
- **Verifiers invoked in letter:** [Scholar Gateway / Consensus / HuggingFace Papers / none]
- **Scholar Gateway compliance:**
  - Contract marker present: Y/N
  - Per-search provenance lines: <n present> of <n required>
  - Gaps clause (where applicable): PASS / FAIL
  - Inline citation dedup: PASS / <n undeduplicated clusters>
  - Session footer: PASS (once) / FAIL (absent) / over-rendered (<n>)
  - Passage quoting (Rule 4): PASS / <n> abstract-paraphrase instances
- **Consensus compliance:**
  - Quartile surfaced where applicable: PASS / <n> missing
  - Sample size disclosed for generalizability claims: PASS / <n> missing
  - Aggregate-vs-paper disambiguation: PASS / <n> misattributions
- **HuggingFace Papers compliance:**
  - Class-1.5 marker present: PASS / <n> missing
  - Class 1 cross-check for substantive rebuttals: PASS / <n> unchecked
- **Rebuttal-side render-contract gaps:** <n> findings, severity breakdown

### Summary
- BLOCKERs: <n>
- MAJORs: <n>
- MINORs: <n>
- Overall tone: <constructive / mixed / defensive>
- Single highest-priority fix: <one sentence>
```

---

## What you do NOT do

- **Do not rewrite the response letter.** Report findings and propose reframings. The Generator rewrites (under the T3R dispatch, consuming `reviews/response_letter_reframe_brief_<date>.md` as its binding instruction sheet).
- **Do not run a full review of the revised manuscript.** This skill checks the response letter and runs three targeted SAFEGUARD checks. For a full review of the revised manuscript, use `/run-tier-standard` (T3) or `/run-tier-submission` (T4). The legacy `/run-full-review` command was retired at v0.5.1.
- **Do not evaluate P-stage.** Response letters do not have P-stages.
- **Do not run the full six SAFEGUARD checks.** Only checks 1, 4, and 5 apply to response-letter context.
- **Do not run Check 7 when no external verifier was invoked by the letter.** If the response letter cites only the author's own Zotero-resolved sources and makes no reference to Scholar Gateway / Consensus / HuggingFace Papers searches, record `Check 7: not applicable — no Class 1/1.5 verifier invocation detected in letter`. The check is activation-gated, not universal.
- **Do not repair render-contract violations by paraphrasing them away.** If a Scholar Gateway passage must be removed to satisfy the reviewer's concern, remove the passage; do not paraphrase it to evade the provenance line. The Generator's fix is additive (insert provenance lines, session footer, dedup) or subtractive (remove the excerpt entirely) — never concealing.
