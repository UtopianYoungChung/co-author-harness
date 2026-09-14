---
name: grounding-audit
description: 'Run a GROUNDING_PROTOCOL compliance audit on review artifacts, revision logs, or agent outputs — four categories: citation accuracy, computed-metric verification, path existence, rule-citation fidelity — flags hallucination and fabrication. Use when: "grounding audit", "hallucination check", "are these citations real", integrity check.'
trigger: when the user asks for grounding audit, hallucination check, verify the review, are these citations real, check the rule citations, or integrity check
created_by: Reflector
created_from: Tier 3 skill build, 2026-04-11 — GROUNDING_PROTOCOL.md grounding audit had no standalone entry point
pattern_source: GROUNDING_PROTOCOL.md §§1–7 + Grounding Audit procedure
version: 1.0
---

# Grounding Audit

You are running a standalone grounding-integrity audit on review artifacts, revision logs, or agent outputs. This skill implements the Reflector's grounding audit (from `GROUNDING_PROTOCOL.md`) as a standalone, user-invocable check.

**Prerequisite:** Read `GROUNDING_PROTOCOL.md` in full before proceeding. The seven rules and the audit procedure are binding.

**What this skill audits.** This skill audits the **review artifacts** (findings reports, deterministic check outputs, revision logs, reflection reports), NOT the manuscript itself. It checks whether the agents' claims about the manuscript and the rules are grounded — not whether the manuscript's claims are grounded.

---

## What you do

1. **Read the artifact** the user specifies (or a review/revision log the user points at). Read the full file in every case.

2. **Run every grounding rule across eight categories.** The category specs — what to check, how to verify, the severity levels — are in [`references/GROUNDING_PROTOCOL.md`](../../references/GROUNDING_PROTOCOL.md) under the **Grounding Audit** section.

   **MANDATORY — READ ENTIRE FILE.** Before producing findings, you MUST read [`references/GROUNDING_PROTOCOL.md`](../../references/GROUNDING_PROTOCOL.md) completely from start to finish. That file carries the eight category rubrics (Citation audit / Metric audit / Path audit / Rule-citation audit / Gap-fill audit / Marker audit / legacy advisor-sourced claims / Graph-sourced claims), each with its verification procedure and severity table. **NEVER set any range limits when reading this file.** The rule-to-category mapping (Rule 1 → Category 4, Rule 2 → Category 2, Rule 3 → Category 3, Rule 4 → Category 1, Rule 5 → Category 6, Rule 6 → Category 5, Rule 7a → Category 7, etc.) is load-bearing — do not approximate.

   If you already read `GROUNDING_PROTOCOL.md` as the prerequisite, re-read the **Grounding Audit** section specifically rather than reloading the full file.

3. **Emit the results** using the template in the Output section below, marking every category CLEAN or listing findings with locations and suggested remediation.

## Output

```markdown
## Grounding Audit Results

**Artifact audited:** <path or description>
**Date:** <date>
**Auditor:** <Reflector | standalone invocation>

### Category 1 — Citations (Rule 4)
- **Checked:** <n>
- **Verified:** <n>
- **Indirect (correctly marked):** <n>
- **Violations:** <n>
  - [details per violation]

### Category 2 — Metrics (Rule 2)
- **Checked:** <n>
- **Computed matches:** <n>
- **Violations:** <n>
  - [details per violation]

### Category 3 — Paths (Rule 3)
- **Checked:** <n>
- **Exist:** <n>
- **Violations:** <n>
  - [details per violation]

### Category 4 — Rule Citations (Rule 1)
- **Checked:** <n>
- **Verified:** <n>
- **Violations:** <n>
  - [details per violation]

### Category 5 — Gap-Fill (Rule 6)
- **Claims checked:** <n>
- **All grounded:** <n>
- **Violations:** <n>
  - [details per violation]

### Category 6 — Markers (Rule 5)
- **Markers in artifact:** <n>
- **Resolved by verification:** <n>
- **Correctly retained (unresolved):** <n>
- **Silently dropped:** <n>
  - [details per violation]

### Category 7 — Legacy advisor-sourced claims (Rules 4, 7a)
- **`[source: advisor]` items in artifact:** <n, or N/A if none>
- **Traced to consultation artifact:** <n>
- **Facts verified:** <n>
- **Facts unverified (not yet submission-bound):** <n> [MAJOR if > 0]
- **Facts unverified (submission-bound):** <n> [BLOCKER if > 0]
- **Untraced claims:** <n> [BLOCKER if > 0]
  - [details per violation]

### Category 8 — Graph-sourced claims (Rules 3, 4, 5)
- **Graph-sourced items in artifact:** <n, or N/A if none>
  - `[source: graph-extracted]`: <n>
  - `[source: graph-inferred]`: <n>
  - `[source: graph-stub]`: <n>
- **Traced to matching graph node/edge:** <n>
- **Confidence-score inheritance correct:** <n>
- **Uncertainty laundering (inflated confidence):** <n> [MAJOR if > 0]
- **Missing confidence_score on inferred finding:** <n> [MAJOR if > 0]
- **Fabricated node/edge references:** <n> [BLOCKER if > 0]
- **False stub (source actually has nodes):** <n> [BLOCKER if > 0]
- **Graph staleness at overlay time:** <not reported | reported | N/A> [MAJOR if not reported but graph was stale]
  - [details per violation]

### N/A Categories
<If a category has no instances (e.g., no uncertainty markers exist in the artifact, no [source: advisor] items), mark it N/A with a reason rather than omitting it silently.>

### Grounding Verdict: [CLEAN | N VIOLATIONS FOUND]
```

---

## What you do NOT do

- **Do not audit the manuscript's content.** This skill audits the agents' claims about the manuscript and the rules. For manuscript content review, use `/run-tier-standard` (T3) or `/run-tier-submission` (T4).
- **Do not fix violations.** Report them. The violating agent (or the Generator, for prose) fixes.
- **Do not skip categories.** If a category has no instances (no metrics reported, no uncertainty markers), mark it N/A — do not omit it. The absence of a category in the output could be mistaken for the absence of an audit.
- **Do not use training data as a verification source.** Every verification must use the Read, Grep, Glob, or Bash tools on actual files. Training data is not a verifiable source.
