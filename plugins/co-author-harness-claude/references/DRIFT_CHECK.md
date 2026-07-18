# DRIFT CHECK — MASTER / Component Reconciliation Gate

**Purpose.** This file defines the procedure that detects when `MASTER_research_and_paper_guidelines.md` has fallen out of sync with the component files it claims to summarise. The package's own precedence rule ("component file wins over MASTER until reconciled") *documents* drift rather than *preventing* it; this gate prevents drift from accumulating silently across rounds.

**Status.** Run by the Reflector at Phase 2.6 of every reflection round, and as a hard gate before any submission-bound G.4 sign-off.

---

## 1. The drift problem

The MASTER carries a traceability matrix mapping its consolidated claims back to the component files. Every edit to a component file may invalidate a portion of that matrix. Without an automated gate:

- Authors who consult the MASTER may follow rules that no component file actually carries.
- Component-file edits accumulate without a reconciliation pass, expanding the surface area of unacknowledged contradiction.
- SAFEGUARD Check 4 (contradiction audit) is *aimed at the manuscript* but the same pattern operates *inside the package itself* — and is currently unaudited.

The drift gate closes this loop.

---

## 2. What "drift" means precisely

Three drift categories must be distinguished:

| Category | Definition | Severity |
|---|---|---|
| **D-A — Quote drift** | The MASTER reproduces a passage that no longer appears verbatim in the cited component file | MAJOR |
| **D-B — Claim drift** | The MASTER asserts a rule (e.g., "Bacon §10 requires X") that the cited section does not assert | BLOCKER |
| **D-C — Structural drift** | The MASTER references a section number (e.g., "Sexton §6.3") that does not exist in the cited file | BLOCKER |

A round that introduces any D-B or D-C drift cannot pass G.4 sign-off.

---

## 3. Procedure (Reflector Phase 2.6)

### Inputs
- `MASTER_research_and_paper_guidelines.md`
- All component files referenced in the MASTER's traceability matrix
- The diff of any component-file edits made in the current session (from version control or file mtime)

### Steps

1. **Enumerate the citations in MASTER.** Use Grep to find every reference of the form `<file>` `§<section>` or "see <file>". Build a list `(file, section_anchor, claim_text)`.

2. **For each citation, perform three checks:**
   - **Existence check (D-C):** Does the file exist? Does the section anchor (heading or section number) resolve in the file? If not → BLOCKER.
   - **Quote check (D-A):** If the MASTER quotes the component file, does the quoted passage appear verbatim in the source? Use Grep on the source; allow whitespace normalisation. If not → MAJOR.
   - **Claim check (D-B):** Does the cited section actually assert what the MASTER claims it asserts? This requires reading the section. The Reflector spot-checks **at minimum 5 citations per round** at standard depth, **all citations** at submission-bound. If a sampled citation fails → BLOCKER, escalate to full audit.

3. **Diff-aware acceleration.** If a component file was edited in this session, every MASTER citation pointing into that file is mandatory to re-check (not just spot-checked).

4. **Emit `reviews/drift_check.md`** with the format below.

5. **Update the trajectory log** at `.paper-package/DRIFT_LOG.md` (append-only; created by this gate on first run): one line per round with date, citations checked, drift items found by category.

### Output format

```markdown
# Drift Check — Round <N>
**Date:** <ISO date>
**Files in scope:** MASTER + <list of component files cited>

## Summary
| Category | Count |
|---|---|
| D-A Quote drift (MAJOR) | <n> |
| D-B Claim drift (BLOCKER) | <n> |
| D-C Structural drift (BLOCKER) | <n> |
| Citations checked | <n> / <total> |

## Findings
| ID | Category | MASTER citation | Component file says | Resolution required |
|---|---|---|---|---|
| DR-01 | D-B | "Sexton §6.3 requires show-then-tell in openings" | §6.3 does not exist; show-then-tell is in §3.2 | Update MASTER citation to §3.2 |
| ... | | | | |

## Verdict
- **Drift status:** [CLEAN / DRIFT DETECTED]
- **Submission-bound G.4 eligibility:** [ELIGIBLE / BLOCKED — fix BLOCKERs first]
```

---

## 4. Resolution procedure

When drift is found, the Reflector does **not** silently fix the MASTER (which would propagate the same single-agent paradox the Grounding Protocol guards against). Instead:

1. Reflector emits the drift findings as part of the reflection report.
2. Reflector marks the affected MASTER passages with `[DRIFT — see reviews/drift_check.md DR-NN]` inline.
3. The user (or an explicitly Generator-roled agent, with user approval) reconciles the MASTER and the component file.
4. The next reflection round confirms the drift is resolved before clearing the marker.

This preserves the Generator/Evaluator separation that makes the harness trustworthy.

---

## 5. Hard gate before G.4

`SUCCESS_METRICS.md` §7.1 lists the submission-readiness criteria. As of 2026-04-13 the following criterion is added:

> **Drift Check status = CLEAN** — no D-B or D-C findings open in `reviews/drift_check.md` for the current round.

A G.4 sign-off attempted while drift is open returns:

```
[BLOCKER — DRIFT_CHECK] Submission-bound sign-off blocked.
  D-B Claim drift items open: <n>
  D-C Structural drift items open: <n>
  See: reviews/drift_check.md
```

---

## 6. Why this matters

A package that flags unacknowledged contradictions in manuscripts but tolerates them in its own constitution loses its standing to make the demand. The drift gate is therefore a *coherence* requirement, not an optimisation. It also has a methodological pay-off: every drift item the gate catches is a recorded instance of the failure mode the harness is trying to address — drift between formal model and instantiated practice — and is itself usable as material for the program's research.

---

*Created 2026-04-13 as part of the package-tightening pass. Addresses recommendation #3 of `wiki/syntheses/paper-package-evaluation-2026-04-13.md`.*
