---
name: quick-deterministic
description: 'Run the canonical mechanical pre-flight on a manuscript via `python scripts/audit/run_all.py`, adding `--project-root` when available so D-STYLE profile routing and surface validation are emitted. Summarizes severity counts and top locators. Use when: "quick check", "pre-flight", "mechanical pass", before deep review.'
trigger: when the user asks for a quick check, a mechanical pass, a deterministic scan, or a pre-flight
created_by: Reflector
created_from: v0.15.0-pre — promoted from LLM-prosecuted regex counting to a scripts-first audit suite
pattern_source: scripts/audit/ (rule anchors in DETERMINISTIC_CHECKS.md)
version: 2.0
---
# Quick Deterministic Check (scripts-first)

You are running a fast mechanical pre-flight on an academic manuscript. As of v0.15.0-pre, **you do not count anything**. The `scripts/audit/` suite counts; you read its output and adjudicate severity in context.

## What you do

1. **Resolve the target.** If the user named a path, use it. Otherwise default to `manuscript/main.md` (or the active project's draft path).

2. **Invoke the audit suite:**
   ```
   python scripts/audit/run_all.py <target> --project-root <project-root> --date YYYY-MM-DD --out reviews/findings.json
   ```
   The script writes `reviews/findings.json`, writes `reviews/d_style_profile_YYYY-MM-DD.json` when `--project-root` is supplied, and prints a one-line summary. If no project root exists for the target, omit `--project-root` and state that D-STYLE profile routing and surface validation were skipped.

3. **Read `reviews/findings.json` and, when present, `reviews/d_style_profile_YYYY-MM-DD.json`.** Each mechanical finding carries `check_id`, `category`, `severity`, `locator (file:line)`, `evidence`, `rule_ref`, and `tentative`. The D-STYLE profile report carries the resolved routing obligations and surface findings for argument/warrant exposure, visual evidence, and assistance disclosure/logging.

4. **Emit a count block** with these sections:
   - **Total findings** by severity (`default` / `inviolable`) and category.
   - **D-STYLE verdict** plus any MAJOR/BLOCKER surface findings from `d_style_profile_YYYY-MM-DD.json`.
   - **Per-check-id counts** with at most three example locators each.
   - **Tentative findings** listed separately — they need human/LLM adjudication (e.g., absolutes `must`/`cannot` whose severity depends on whether they are prescriptive).
   - **Verdict.** Pass if zero `inviolable` findings; otherwise fail.

5. **Do not re-count anything.** If the script under-detected (false negative), file a bug against `scripts/audit/` — do not paper over it with manual counting.

## What you do NOT do

- **Do not run regexes yourself.** The patterns live in `scripts/audit/audit_style.py`; LLM-side regex counting is the anti-pattern this version retired.
- **Do not propose fixes.** Report findings. The Generator fixes.
- **Do not run the SAFEGUARD layer.** Post-review check, not pre-flight.
- **Do not promote `default` severity to `inviolable`.** Style is taste; only grounding/citation findings are inviolable.

## Adjudication of `tentative: true` findings

Some checks fire on patterns whose severity depends on context — `must` may be prescriptive or logical, `there is/are` may delay a real subject or be idiomatic. For each tentative finding:

- Read the surrounding sentence in the manuscript.
- Decide: confirm (raise to MAJOR/MINOR in the report) or dismiss (note "context-appropriate use").
- Do not silently drop. Every tentative finding earns a one-line disposition in your output.

## Shortcuts

If the user asks for a narrow check ("just em-dashes"):
- Run `run_all.py` anyway (it's cheap), but filter the count block to the requested `check_id` class.
- Still emit the verdict line.

## Where to learn more

- `scripts/audit/schema.py` — Finding/FindingsReport schema.
- `scripts/audit/audit_style.py` — pattern catalogue.
- `references/DETERMINISTIC_CHECKS.md` — rule rationale (now an explanation file, no longer the runtime source of patterns).
