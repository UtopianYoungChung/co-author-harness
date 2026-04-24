---
name: quick-deterministic
description: 'Run the mechanical pre-flight on a manuscript — em-dashes, absolutes (must/cannot/comprehensiv*/anticipat*), LLM tics, sentence-length distribution, [REF to be verified] — emits the DETERMINISTIC_CHECKS.md §10 count block with line locations and pass/fail. Use when: "quick check", "pre-flight", "mechanical pass", before deep review.'
trigger: when the user asks for a quick check, a mechanical pass, a deterministic scan, or a pre-flight
created_by: Reflector
created_from: Package workflow — the most common first action on any piece
pattern_source: DETERMINISTIC_CHECKS.md (full file)
version: 1.0
---
# Quick Deterministic Check

You are running a fast mechanical pre-flight on an academic manuscript. This is Step 0a of the review pipeline, isolated as a standalone skill for speed.

## What you do

1. **Read the file** the user specifies (or `manuscript/main.md` in the current project).

2. **Run every pattern in `DETERMINISTIC_CHECKS.md`** (in the package folder). Read that file first for the exact patterns, thresholds, and severity assignments.

3. **Emit the count block** in the exact format prescribed by `DETERMINISTIC_CHECKS.md` §10:

```
## Deterministic check results

**File:** <path>
**Lines:** <count>

### Counts
- em-dashes (--- or —): <n>               [threshold: ≤ 1 pair per paragraph]
- em-dashes nested: <n>                    [threshold: 0]
- "not X but Y": <n>                       [threshold: ≤ 2]
- absolutes (must|cannot|comprehensiv|anticipat): <n>
  - must: <n> at lines <...>
  - cannot: <n> at lines <...>
  - comprehensiv*: <n>
  - anticipat*: <n>
- there is / there are / there remain: <n>
- reveals / exposes / proves: <n>
- "standard <noun>": <n>
- "first-class": <n>
- hedged paragraph-start transitions: <n>/<total paragraph breaks>
- sentences > 60 words: <n>
- avg sentence length: <words>
- max sentence length: <words>
- [REF to be verified]: <n>

### Verdict
- BLOCKERs: <n>
- MAJORs: <n>
- MINORs: <n>
- Pass / Fail
```

4. **For each count above threshold**, include the line number(s) and a one-line description of the hit so the user can navigate directly to the problem.

5. **Do not proceed to judgment-based review.** This skill is mechanical only. If the user wants a full review, they should invoke the Evaluator agent or run the full pipeline.

## What you do NOT do

- **Do not propose fixes.** Report counts and locations. The Generator fixes.
- **Do not run the safeguard layer.** That is a post-review check (Step 8.5), not a pre-flight.
- **Do not read the package's judgment-based files** (playbook, Bacon, Sexton, Baird). This skill is mechanical; reading those files wastes time on a quick check.
- **Do not comment on the quality of the prose.** The only output is counts, locations, and the pass/fail verdict.

## Shortcuts

If the user asks for a **very** quick check (e.g. "just check em-dashes and absolutes"):
- Run only the specified patterns.
- Emit only those rows of the count block.
- Still emit the verdict line.
