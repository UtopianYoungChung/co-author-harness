# Package Integration Summary — 2026-04-13 Root Cause Analysis Response

**Date:** 2026-04-13
**Source:** Root cause analysis of INF3001H "Whose Humanness Is Encoded?" review (five substantive logical gaps persisted through 8 internal rounds; external review caught all five on 1 pass)
**Outcome:** Package comprehensively updated to address gaps at planning (M1–M3) and review phases

---

## Executive Summary

The internal review pipeline is optimized for **consistency and well-formedness** checks. External review catches **argumentative rigor** gaps. These are orthogonal dimensions. The INF3001H review exposed five structural blind spots in the package where argumentative gaps went undetected because the package had no mechanism to catch them.

**Solution:** Push argumentative rigor checking upstream into the planning phase (M1–M3), so that by the time drafting begins (M4), the argumentative skeleton is solid. This reduces rework at M4–M5 and makes the manuscript more robust to external review.

---

## Five Blind Spots Identified

### 1. Asserted vs. Demonstrated Premises
**Gap:** Claims are present in the paper but not *supported with evidence*; they are merely *asserted*.
- **Example (INF3001H):** "Information is the right home" for studying identity-sensitive requirements. Asserted but without naming existing research programs that perform the claimed integration.
- **Prevention mechanism:** M1 & M2 planning phase checks now explicitly require enumeration of exemplar research programs.

### 2. Unresolved Logical Tensions
**Gap:** Two premises are individually consistent but create a logical consequence the paper doesn't resolve.
- **Example (INF3001H):** "Actors are provisional stabilizations" + "we model actors with i*" → What does the model capture? When does it become stale? Paper didn't resolve.
- **Prevention mechanism:** M1 planning now requires identifying premises that might create tensions and explicitly marking them as resolved-within-paper or deferred-to-future-work.

### 3. Epistemological Transparency (Illustration vs. Evidence)
**Gap:** Illustrations are doing evidential work without being flagged as constructed; readers mistake the case for data.
- **Example (INF3001H):** Loan-officer case presented without being explicitly flagged as illustrative; empirical grounding sparse.
- **Prevention mechanism:** M2 planning now requires epistemological clarity for every source (evidence, framing, or illustration) and M3 outline must flag illustrations as "constructed scenario."

### 4. Argumentative Completeness Against Objections
**Gap:** A claim is present but not differentiated from alternative positions or objections.
- **Example (INF3001H):** "Why Information, not STS or organizational studies?" — alternative positions not addressed in outline.
- **Prevention mechanism:** M3 planning now requires explicit enumeration of alternative positions and verification that the outline shows differentiation for each.

### 5. Justified Framework Transfer
**Gap:** A framework developed in Domain A is transferred to Problem B without justifying the transfer.
- **Example (INF3001H):** Haslam's interpersonal humanness perception framework applied to technical specifications without explaining why the transfer is valid.
- **Prevention mechanism:** M2 planning now requires documenting framework origin domain and transfer justification for every borrowed framework.

---

## Package Integration: Files Changed and Created

### 1. **AGENT_ORCHESTRATION.md §10 (M1–M3 Criteria Enhanced)**

**Changes:**
- **M1 (Project Memo):** Added two argumentative rigor checks:
  - "Argumentative framing (NEW)" — disciplinary placement claims must name existing exemplars
  - "Premise mapping (NEW)" — identify potential internal tensions; mark as resolved or deferred
  
- **M2 (Annotated References):** Added two epistemological clarity checks:
  - "Framework origin & transfer (NEW)" — every framework must state origin domain and transfer justification
  - "Epistemological clarity (NEW)" — every source must be classified as evidence, framing, or illustration
  
- **M3 (Structured Outline):** Added three argumentative completeness checks:
  - "Alternative positions addressed (NEW)" — placement claims must show comparison to alternatives
  - "Tension resolution (NEW)" — M1 tensions must appear in outline with resolution strategy
  - "Illustration vs. evidence separation (NEW)" — illustrations must be flagged as constructed and paired with empirical grounding

**Impact:** M1–M3 now check argumentative rigor, not just structure. The planning phase surfaces gaps before drafting begins.

---

### 2. **M1_M2_M3_ARGUMENTATIVE_RIGOR_CHECKLIST.md (NEW)**

**Purpose:** Operationalize the M1–M3 checks into concrete prompts and decision trees for Planners and Generators.

**Contents:**
- M1 Check 1a: Disciplinary placement claims must enumerate exemplars (2–4 research programs demonstrating the integration)
- M1 Check 1b: Identify logical tensions between premises; mark as resolved or deferred
- M2 Check 2a: Framework transfer justification (origin domain + mechanism of transfer)
- M2 Check 2b: Epistemological clarity (evidence vs. framing vs. illustration)
- M3 Check 3a: Alternative positions must be named and addressed in outline
- M3 Check 3b: M1 tensions must appear in outline with explicit resolution
- M3 Check 3c: Illustrations must be flagged as constructed and paired with empirical support

**Target users:** Planners creating M1–M3 artifacts; Evaluators reviewing them; Generators drafting against the plans.

**Integration point:** This checklist is referenced from AGENT_ORCHESTRATION.md §10 and serves as the runbook for pre-drafting argumentative rigor.

---

### 3. **.paper-package/research_notes/lessons_learned.md (NEW — Package-Level)**

**Purpose:** Cross-project lessons extracted from root cause analysis. These bind all future projects.

**Lessons added:**

**L-P1: External Review Addresses Argumentative Rigor; Internal Pipeline Addresses Consistency**
- Internal review (automated checks, safeguard layer) catches mechanical errors and consistency failures
- External review catches argumentative rigor (demonstrated vs. asserted, completeness, transparency, differentiation)
- **They are orthogonal.** Neither alone is sufficient; both are necessary at submission-bound depth
- **Action:** Use M1–M3 argumentative rigor checklist to move some external-review-type checks into planning phase

**L-P2: Disciplinary Placement Claims Require Named Exemplars**
- When arguing "Problem X belongs in Discipline Y," support with 2–4 research programs that already perform the claimed integration
- "Research program" = named scholar/group with sustained body of work demonstrating the integration
- Not just individual papers, not aspirational language, not single components
- **Action:** Add exemplar enumeration requirement at M1; annotate programs in M2; reference in M3 outline; introduce in M4 §1

**L-P3: Unresolved Logical Tensions Become Reviewer Questions**
- When holding two premises simultaneously, check if they create a logical consequence the paper doesn't resolve
- Tension = A + B → (unresolved Q) ... different from contradiction (A AND NOT-A)
- Unaddressed tensions make reviewers question author's rigor even when both premises are individually sound
- **Action:** Identify tensions at M1; track resolution strategy in M3 outline; resolve or scope explicitly in M4 draft

**Impact:** These lessons are binding on all projects. They operationalize the root cause analysis findings.

---

### 4. **agents/reflector.md §Phase 2.8 (Check-Ownership Audit)**

**Status:** Already implemented in prior conversation (2026-04-13).

**Purpose:** Before accepting READY verdict at submission-bound depth, Reflector must enumerate which dimensions the check topology owns and which it does not.

**Why it matters:** An external reviewer caught defects on dimensions the internal pipeline had reported PASS on. The dimensions were unowned — no check was defined to audit them.

**Action:** Reflector lists all active checks and their dimensions. For any dimension not owned that is load-bearing for submission, flag as residual risk in G.4 sign-off.

---

### 5. **SAFEGUARD_LAYER.md Check 3 (Citation Attribution & Abstract Specificity)**

**Status:** Already implemented in prior conversation (2026-04-13).

**Additions (submission-bound depth):**
- **Step 4:** Citation attribution epistemological honesty audit (L-16) — verify primary vs. secondary source attribution
- **Step 5:** Abstract closing specificity check (L-17) — avoid generic "disciplinary and analytical" closings; require specific contribution statement

**Why needed:** These are high-leverage checks for submission readiness. They were identified as lessons (L-16, L-17) from INF3001H round 8 and promoted to the package.

---

## How the System Works: Prevention Logic

### **The Loop: M1 → M2 → M3 → M4 → M5**

```
M1: PLANNER + GENERATOR draft Project Memo
    ↓
    EVALUATOR checks:
    • Disciplinary placement claims named with exemplars? ✓
    • Logical tensions identified and tracked? ✓
    
M2: PLANNER + GENERATOR draft Annotated References
    ↓
    EVALUATOR checks:
    • Framework transfers justified (origin + mechanism)? ✓
    • Every source epistemologically classified? ✓
    
M3: PLANNER + GENERATOR draft Structured Outline
    ↓
    EVALUATOR checks:
    • Alternative positions enumerated and addressed? ✓
    • M1 tensions appear in outline with resolution? ✓
    • Illustrations flagged and grounded empirically? ✓
    
M4: GENERATOR drafts paper against the explicit argumentative skeleton
    • By now, argumentative rigor is baked in
    • DETERMINISTIC_CHECKS + SAFEGUARD_LAYER catch consistency/well-formedness
    • REVIEW_ORCHESTRATION Steps 1–8 run judgment
    ↓
    
M5: Submission-bound depth review
    • Full eight SAFEGUARD_LAYER checks including citation attribution and abstract specificity
    • Check-Ownership Audit (Reflector Phase 2.8) surfaces any residual risks
    • External review addresses any *remaining* argumentative gaps
```

**Key insight:** By M4, the argumentative skeleton is solid. M4–M5 drafting and review are execution against an explicit plan, not discovery of argumentative gaps.

---

## Scope of Coverage: What Each Prevention Mechanism Addresses

| Blind Spot | Mechanism | Phase | File |
|---|---|---|---|
| **Asserted vs. Demonstrated** | Exemplar enumeration requirement | M1 + M2 | AGENT_ORCH §10 M1; CHECKLIST §M1 1a |
| **Unresolved Tensions** | Tension identification + tracking | M1 + M3 | AGENT_ORCH §10 M1, M3; CHECKLIST §M1 1b, M3 3b |
| **Epistemological Transparency** | Source classification + illustration flagging | M2 + M3 | AGENT_ORCH §10 M2, M3; CHECKLIST §M2 2b, M3 3c |
| **Argumentative Completeness** | Alternative position enumeration | M3 | AGENT_ORCH §10 M3; CHECKLIST §M3 3a |
| **Framework Transfer** | Transfer justification documentation | M2 | AGENT_ORCH §10 M2; CHECKLIST §M2 2a |
| **Citation Attribution** | Epistemological honesty audit (L-16) | M5 | SAFEGUARD_LAYER Check 3 Step 4 |
| **Abstract Specificity** | Concrete contribution naming (L-17) | M5 | SAFEGUARD_LAYER Check 3 Step 5 |

---

## Integration Points: How to Use This System

### **For future projects:**

1. **At M1 kickoff:** Planner uses `M1_M2_M3_ARGUMENTATIVE_RIGOR_CHECKLIST.md` §M1 to guide the Generator. Check 1a (exemplar enumeration) and Check 1b (tension identification) are mandatory.

2. **At M2 annotation stage:** Generator annotates sources and classifies each as evidence/framing/illustration. Evaluator checks framework transfer justifications (Check 2a) and epistemological clarity (Check 2b).

3. **At M3 outline stage:** Generator maps alternative positions and shows outline addresses each. Evaluator verifies M1 tensions appear in outline with resolution strategy. Illustrations are flagged as constructed.

4. **At M4 drafting:** Generator follows the explicit argumentative skeleton from M3. No major argumentative rework should be needed; the plan is solid.

5. **At M5 submission-bound review:** SAFEGUARD_LAYER Check 3 Steps 4–5 (citation attribution, abstract specificity) run. Check-Ownership Audit (Reflector Phase 2.8) surfaces residual risks before G.4 sign-off.

---

## Cross-Project Applicability

All of the mechanisms introduced here apply to **any Faculty of Information research project** at submission-bound depth or higher. They are not INF3001H-specific.

**Projects with disciplinary placement or framework transfer arguments** (most research) should run the M1–M3 argumentative rigor checklist as a matter of course. This includes:
- Thesis papers (MS/PhD)
- Conference submissions with positioning arguments
- Grant proposals with interdisciplinary claims
- Course papers arguing for a novel framing

---

## Backward Integration: Existing Projects

**INF3001H:** All five gaps have been closed in the manuscript. The root cause analysis and gap closure logs are documented in `draft/reviews/`.

**INF3006Y (if revisited):** Apply the M1–M3 argumentative rigor checklist at the start of the next revision cycle to prevent similar gaps.

**Future projects:** The checklist and updated AGENT_ORCHESTRATION.md are now the standard for all projects.

---

## Verification: Completeness Check

This integration addresses all five blind spots identified in the root cause analysis:

✓ **Gap 1 (Asserted vs. Demonstrated)** — Exemplar enumeration requirement at M1 + M2
✓ **Gap 2 (Unresolved Tensions)** — Tension identification at M1; tracking through M3 outline
✓ **Gap 3 (Epistemological Transparency)** — Source classification at M2; illustration flagging at M3
✓ **Gap 4 (Argumentative Completeness)** — Alternative position enumeration at M3
✓ **Gap 5 (Framework Transfer)** — Transfer justification documentation at M2

Plus two lesson-driven package improvements:
✓ **L-16 (Citation Attribution)** — Epistemological honesty audit in SAFEGUARD_LAYER Check 3 Step 4
✓ **L-17 (Abstract Specificity)** — Concrete contribution check in SAFEGUARD_LAYER Check 3 Step 5

Plus one post-integration addition (2026-04-13, late addendum):
✓ **L-P4 (Conjunct-Level Citation Verification)** — Compound-claim check in GROUNDING_PROTOCOL Rule 1; regex-based flag in DETERMINISTIC_CHECKS §7; lesson recorded in package `research_notes/lessons_learned.md` §L-P4. Triggered by silent Braverman/Star \& Strauss attribution conflation in INF3001H §1 ¶5.

**Package architecture is now coherent:** Pre-drafting planning (M1–M3) catches argumentative gaps; review phase (M4–M5) ensures consistency and well-formedness; citation grounding is audited at conjunct granularity rather than sentence granularity. Neither internal review alone substitutes for external review, but the combination is robust.

---

*Created 2026-04-13 as comprehensive integration summary of root cause analysis response. All referenced files and sections exist and are cross-linked.*
