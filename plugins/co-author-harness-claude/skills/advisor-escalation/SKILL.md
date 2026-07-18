---
name: advisor-escalation
description: 'Advisor MCP bridge: co-author-harness plugin skill calls the host-configured advisor MCP (`consult_advisor`) for external feedback—strategic questions plus EP-1 (post-Ph2 pre-Ph3) and EP-2 (post-Ph3_converged pre-MCR/Ph4). Re-classify EXTERNAL tags; file `reviews/advisor_consultation_*.md`. See `references/ADVISOR_MCP.md`.'
trigger: when the user or Planner needs strategic or fresh-eyes guidance via the advisor MCP—EP-1/EP-2 moments, P-stage boundaries, reframing, theory pivots, submission-readiness judgment, stuck value-judgment loops, or explicit /advisor-escalation
created_by: User + design session (C.1 → A.1 progression)
created_from: advisor_plugin_upgrade design, 2026-04-15 — context_contract.md v1.3.0
pattern_source: advisor output requires grounding-protocol integration that free-form consultation does not provide; EXTERNAL tags need audit-side re-classification; consultation artifacts need filing for traceability
version: 1.1
---
# Advisor MCP — `advisor-escalation` (plugin bridge)

You are running the **Advisor MCP** bridge skill shipped by the **co-author-harness** plugin. It connects the four-agent loop to the **advisor** MCP server the user has attached in the **host** (Cursor, Claude Code, etc.). The plugin **does not** bundle the server; it exposes this skill so agents invoke `mcp__advisor__consult_advisor` with the same guardrails every time.

It handles everything between "the Planner decides it needs external feedback" and "the requesting agent receives a grounded, auditable consultation result."

**Normative one-pager.** Read [`references/ADVISOR_MCP.md`](references/ADVISOR_MCP.md) for EP-1 / EP-2 definitions and plugin–MCP wiring.

---

## Lifecycle entry points (submission defensibility)

Use the same Steps 1–7 below. **Name the entry point in `task_summary`** so downstream artefacts show *why* this consultation ran.

| ID | When to run | What to ask |
|----|-------------|-------------|
| **EP-1** | After **Ph2** completion (first full Evaluator pass / Ph2 exit artefacts), **before** deep **Ph3** iteration | Macro questions: contribution clarity, narrative arc, venue fit, structural risks—*before* Ph3 optimizes locally. |
| **EP-2** | After all in-scope sections are **`Ph3_converged`**, **before** **MCR** and **Ph4** | Skeptical read: over-claiming, related-work fairness, "would a reviewer believe this" issues—*before* external-verifier and G.4 work. |

These are **recommended** consult moments; they do not replace user approval, MCR, or `EXTERNAL_VERIFIERS` checks.

---

## Procedural flow (Steps 1–7)

You are executing the advisor-escalation bridge. **Claude Fable 5** pricing applies to the advisor MCP server as configured (US$10 in / US$50 out per MTok, list pricing verified 2026-07-07); see Step 1.

**Prerequisite reads.** Before proceeding, read these files (skip if already read in this session):

1. `GROUNDING_PROTOCOL.md` — the seven rules are binding on advisor output too.
2. `context_contract.md` — at the advisor MCP runtime root (or project-local override). You need the current `CONTRACT_VERSION` and the EXTERNAL tag protocol (§§8–9).
3. The project's `reviews/classification.md` — you need the P-stage and depth to frame the question.
4. The project's `reviews/DO_NOT_DISTURB.md` — frozen rules the advisor must not override.

---

## When to invoke this skill

### Trigger conditions (any one is sufficient)

| Condition | Example |
|---|---|
| **P-stage boundary question** | "Is this paper still P0 or has it crossed into P1?" |
| **Theoretical reframing** | "Should we pivot from Leonardi's relational framing to Suchman's situated action?" |
| **Submission-readiness judgment** | "Is this ready for CAiSE or does it need another round?" |
| **Strategic dead-end** | The Evaluator keeps flagging the same BLOCKER and the Generator cannot resolve it — the problem may be structural, not editorial |
| **User explicitly requests advisor** | "Ask the advisor about X," "Escalate this to the advisor" (or a named advisor model), `/advisor-escalation` |
| **EP-1 (post-Ph2, pre-Ph3)** | Scheduled **Advisor MCP** read after Ph2 exit, before deep Ph3 — see `references/ADVISOR_MCP.md` |
| **EP-2 (pre-MCR/Ph4)** | Scheduled read after `Ph3_converged`, before MCR/Ph4 — see `references/ADVISOR_MCP.md` |
| **Cross-project strategic question** | "How does the INF3006Y framing relate to the CAiSE revision?" |

### When NOT to invoke

- **Mechanical checks.** Use `/quick-deterministic`, `/check-contradictions`, `/grounding-audit` instead.
- **Sentence-level craft.** Use `/sentence-level-pass` or `/narrative-structure-pass`.
- **Classification.** Use `/classify-manuscript` — the advisor does not classify.
- **Routine review rounds.** The four-agent loop handles these. Escalate only when the loop is stuck or the question is genuinely strategic.

---

## Step 1 — Cost confirmation (mandatory)

Before calling the advisor, present the user with:

```
Advisor escalation: estimated ~<N> input tokens (manuscript + framing files + question).
Claude Fable 5 pricing applies (US$10/MTok in, US$50/MTok out). Proceed? [y/n]
```

To estimate input tokens:
- Read the project's canonical files (per context_contract.md §3) and sum character counts.
- Divide by 4 (the contract's heuristic).
- Add ~500 tokens for the system prompt and EXTERNAL_TAG_CONSTRAINT block.
- Add the user's question length / 4.

**Do not call the advisor if the user declines.** Offer to rephrase the question to reduce context, or suggest which canonical files to exclude via `context_files` override.

---

## Step 2 — Compose the question

Structure the advisor call as:

```python
consult_advisor(
    task_summary="<one-paragraph framing: project name, P-stage, venue, what round we're in, what the loop is stuck on>",
    specific_question="<the actual strategic question — one question only; if multiple, split into separate calls>",
    project_root="<path to the project root>"
)
```

**Rules for composing the question:**

1. **One question per call.** Multiple questions dilute the advisor's focus and make tag-attribution harder.
2. **If EP-1 or EP-2:** the first line of `task_summary` MUST be `Advisor entry point: EP-1 (post-Ph2, pre-Ph3)` or `Advisor entry point: EP-2 (post-Ph3_converged, pre-MCR/Ph4)` (exact choice matching `ADVISOR_MCP.md`).
3. **Include what the loop already tried.** If the Evaluator flagged a BLOCKER and the Generator attempted a fix, say so. The advisor needs to know what failed.
4. **Name the tension explicitly.** "The tension is between X and Y; the loop cannot resolve it because Z."
5. **Do not ask the advisor to line-edit every sentence.** The advisor gives strategic / fresh-eyes guidance; the Evaluator reviews prose. If you need both, run the advisor first, incorporate its guidance, then run the Evaluator.

---

## Step 3 — Call the advisor

Use the advisor MCP tool directly:

```
mcp__advisor__consult_advisor(
    task_summary=<composed task summary>,
    specific_question=<composed question>,
    project_root=<project root path>
)
```

Capture the full response text. The response will contain:
- The advisor's substantive answer
- `[EXTERNAL: gap]` and `[EXTERNAL: fact]` tags on any external literature references
- A footer with model, contract version, input/output token counts, and packer warnings

---

## Step 4 — Audit-side re-classification of EXTERNAL tags

The advisor's output carries `[source: external]` tags on claims the advisor attributes to named authorities. Those tags must be re-classified defensively before the content enters the manuscript pipeline — some will resolve to verifiable citations in your REFERENCES.md, some will remain unverified and must stay `[REF to be verified]`, and a few will be ungrounded rhetorical attributions that must be removed entirely.

**MANDATORY — READ ENTIRE FILE.** Before running re-classification, you MUST read [`references/GROUNDING_PROTOCOL.md`](references/GROUNDING_PROTOCOL.md) completely from start to finish. That file carries the attribution-confidence tiers (Verified / Inherited / Indirect), the Rule 4 attribution procedure, and the four-pattern framework (Name+verb, Author's-term, Per-X/According-to-X, X-who-argues) plus the extract → heuristic-reclassify → force-reclassify → validate procedure. **NEVER set any range limits when reading this file.** The tier definitions and pattern numbering are load-bearing for the reclassification log the Step 5 artifact template consumes.

If you already read `GROUNDING_PROTOCOL.md` at Step 0, re-read the **Rule 4** and **Attribution-confidence tiers** sections specifically rather than reloading the full file.

## Step 5 — File the consultation artifact

Create (or append to) `reviews/advisor_consultation_YYYY-MM-DD.md` in the project root. Use today's date.

### Artifact template

```markdown
## Consultation — <HH:MM> — <one-line question summary>

**Question asked:**
> <the specific_question verbatim>

**Task summary provided:**
> <the task_summary verbatim>

**Contract version:** <from footer>
**Input tokens:** <from footer>
**Output tokens:** <from footer>
**Packer warnings:** <count from footer, or 0>

### Advisor response (post-reclassification)

<full advisor response with any reclassified tags updated in-place>

### EXTERNAL tag summary

| # | Tag | Sentence fragment | Original | Final | Reclassified? |
|---|-----|-------------------|----------|-------|---------------|
| 1 | fact | "Bratman distinguishes..." | fact | fact | no |
| 2 | gap→fact | "Coeckelbergh argues..." | gap | fact | yes (P1) |
| 3 | gap | "the manuscript does not cite X" | gap | gap | no |

### Reclassification log

<list of all [RECLASSIFIED] entries from Step 4c, or "None — all tags accepted as-is">

### Grounding status

Every `[EXTERNAL: fact]` item in this consultation is an **unverified hypothesis** (Indirect tier per GROUNDING_PROTOCOL Rule 4). These items:

- **MAY** be used by the Planner to inform revision strategy.
- **MAY** be cited in `consolidated_findings_report.md` with `[source: advisor]` cross-references.
- **MUST NOT** be written into the manuscript as verified claims without independent verification.
- **MUST** be externally verified (Zotero MCP, CrossRef, or human reader) before surviving to submission-bound depth (Rule 7a).
```

If the file already exists (multiple consultations in one day), **append** a new `## Consultation` section. Do not overwrite prior consultations.

---

## Step 6 — Hand back to the requesting agent

Return a structured summary to the agent that requested the escalation (typically the Planner):

```markdown
### Advisor consultation result

**Question:** <one-line summary>
**Key recommendation:** <1–2 sentence distillation of the advisor's answer>
**Actionable items for revision plan:**
1. <item 1> [source: advisor]
2. <item 2> [source: advisor]
...

**EXTERNAL facts requiring verification before use in manuscript:**
- <fact 1> — verify via Zotero/CrossRef before incorporating
- <fact 2> — verify via Zotero/CrossRef before incorporating

**EXTERNAL gaps (investigation candidates):**
- <gap 1> — search Zotero; add to reference list if relevant
- <gap 2> — search Zotero; add to reference list if relevant

**Consultation artifact filed at:** `reviews/advisor_consultation_YYYY-MM-DD.md`
```

The Planner incorporates the actionable items into its revision plan. The `[source: advisor]` tags flow through to `consolidated_findings_report.md` so the Reflector can audit provenance.

---

## Step 7 — Grounding-audit extension

When the grounding-audit skill (`/grounding-audit`) encounters `[source: advisor]` cross-references in any review artifact, it applies an additional check:

### Category 7 — Advisor-sourced claims (new)

For every `[source: advisor]` item in the audited artifact:

1. Does a corresponding entry exist in `reviews/advisor_consultation_YYYY-MM-DD.md`?
2. Is the claim an `[EXTERNAL: fact]` (requires verification) or an `[EXTERNAL: gap]` (investigation candidate)?
3. If `[EXTERNAL: fact]`: has the claim been independently verified since the consultation? Check for:
   - A Zotero entry added after the consultation date
   - A `[verified]` annotation added to the consultation artifact
   - A manuscript citation that post-dates the consultation

| Finding | Severity |
|---|---|
| Advisor-sourced claim traced to consultation artifact, fact verified | PASS |
| Advisor-sourced claim traced to consultation artifact, gap (no verification needed) | PASS |
| Advisor-sourced claim traced to consultation artifact, fact NOT verified but not yet at submission-bound depth | [MAJOR] — schedule verification |
| Advisor-sourced claim traced to consultation artifact, fact NOT verified at submission-bound depth | [BLOCKER] — Rule 7a violation |
| Advisor-sourced claim NOT traced to any consultation artifact | [BLOCKER] — Rule 4 violation (unattributed advisor claim) |

---

## What you do NOT do

- **Do not let the advisor override DO_NOT_DISTURB rules.** If the advisor recommends something that conflicts with a DND entry, flag the conflict to the user but do not apply the recommendation.
- **Do not write advisor recommendations directly into the manuscript.** The advisor informs the Planner's strategy; the Generator writes prose. The advisor's words are not manuscript text.
- **Do not skip the re-classification step.** Even if the advisor's tagging looks correct, run the heuristic. The regex catches what the model misses; the model catches what the regex can't represent. Both layers are needed.
- **Do not call the advisor without cost confirmation.** No silent Fable 5 spend.
- **Do not treat advisor output as verified.** Every factual claim from the advisor is Indirect tier until independently verified. The advisor is a hypothesis generator, not a fact source.
- **Do not call the advisor for mechanical checks.** The harness's own tools are faster, cheaper, and deterministic.
