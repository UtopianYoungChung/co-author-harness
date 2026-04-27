# SUCCESS METRICS — Measuring Manuscript Improvement

**Purpose.** This file defines formal metrics for assessing whether the harness is producing measurable improvement in manuscripts across review rounds. It moves beyond the informal "finding-count reduction" to a multi-dimensional quality framework with quantitative and qualitative indicators.

**When to use.** The Reflector reads this file at Phase 2 (Lesson Extraction) to assess round-over-round improvement. The Planner reads it when the user asks "Is the piece ready?" or "How much has it improved?" The Evaluator reads it when producing the submission-bound G.4 sign-off.

---

## 1. The Five Dimensions of Manuscript Quality

Each dimension captures a distinct aspect of improvement. No single dimension is sufficient; the harness tracks all five.

| Dimension | What it measures | Primary instruments |
|---|---|---|
| **D1 — Defect Density** | Count and severity of violations per unit of text | Evaluator findings; DETERMINISTIC_CHECKS.md counts |
| **D2 — Structural Integrity** | Coherence of argument arc, construct consistency, abstract-body alignment | SAFEGUARD Checks 3, 4; Sexton arc checks; red-thread assessment |
| **D3 — Prose Craft** | Sentence-level quality: focus, balance, variety, voice markers | Bacon checklist; deterministic sentence-length distribution; humanness voice audit |
| **D4 — Theoretical Adequacy** | Correct use of theory: framing, operationalization, contribution claims, draw-on vs. extend | Baird five-element model; Playbook §3; construct provenance |
| **D5 — Lifecycle Progress** | Movement through milestones: M1 → M2 → M3 → M4 → M5 | Planner classification; milestone artifact completion |

---

## 2. Defect Density (D1)

### 2.1 Metric: Weighted Finding Count (WFC)

```
WFC = (BLOCKER_count × 10) + (MAJOR_count × 3) + (MINOR_count × 1)
```

A lower WFC is better. Track WFC per round:

| Round | BLOCKERs | MAJORs | MINORs | WFC | Δ from prior |
|---|---|---|---|---|---|
| R1 | — | — | — | — | — |
| R2 | — | — | — | — | — |
| ... | | | | | |

### 2.2 Metric: Deterministic Check Score (DCS)

Count how many of the nine deterministic check categories are within threshold:

```
DCS = (categories_within_threshold / 9) × 100%
```

Target: DCS = 100% for submission-bound manuscripts.

### 2.3 Interpretation

- **WFC decreasing monotonically** across rounds → the harness is working.
- **WFC increases** in a round → regression detected (SAFEGUARD Check 1 should catch this).
- **DCS < 100% at submission-bound** → deterministic fixes are incomplete; do not sign off G.4.

---

## 3. Structural Integrity (D2)

### 3.1 Metric: Structural Integrity Score (SIS)

A five-point rubric applied by the Evaluator at Step 8 (Synthesis):

| Score | Meaning |
|---|---|
| **5 — Submission-ready** | Argument flows without breaks; all constructs introduced, deployed, and resolved; abstract and body aligned; no unacknowledged contradictions. |
| **4 — Near-ready** | Minor arc gaps (e.g., one construct underdeployed); no BLOCKERs. |
| **3 — Revisable** | One structural BLOCKER (e.g., surprise construct in Results, or abstract-body misalignment); recoverable with targeted edits. |
| **2 — Needs restructuring** | Multiple structural issues; argument arc is unclear; significant rewriting required in 2+ sections. |
| **1 — Pre-structural** | No discernible argument arc; piece reads as notes or disconnected sections. |

### 3.2 Sub-indicators

| Indicator | Source | Threshold for submission |
|---|---|---|
| Red-thread continuity | Sexton §3 + Baird §1 | Present and traceable through all sections |
| Abstract-body alignment | SAFEGUARD Check 3 | All abstract promises resolved in body |
| Contradiction-free | SAFEGUARD Check 4 | Zero unacknowledged contradictions |
| Construct introduced-then-deployed | Baird Step 5 | No surprise constructs in Results/Discussion |

---

## 4. Prose Craft (D3)

### 4.1 Metric: Prose Quality Profile (PQP)

A six-indicator profile, each scored YES/PARTIAL/NO:

| Indicator | Rule source | What "YES" means |
|---|---|---|
| Sentence-length variety | MASTER §F.5; Bacon §9.5 | Distribution spans 8–40 words; no sentence > 60; mean within venue target |
| First-person navigation | MASTER §A.4.2 | Author voice present; not exclusively passive or impersonal |
| Asymmetric rhythm | MASTER §I; Bacon §3 | Sentences vary in structure; no three consecutive parallel constructions |
| Concrete anchors | Sexton §2; MASTER §D.2 | Abstract claims grounded by example within 2 paragraphs |
| LLM-tic absence | MASTER §A.4.2; DETERMINISTIC_CHECKS | Zero "not X but Y," zero triadic lists, zero glossary dumps |
| Lived-in detail | MASTER §J; Bacon §3.1 | At least one domain-specific, non-generic detail per major section |

### 4.2 Scoring

```
PQP = (YES_count × 2 + PARTIAL_count × 1) / 12 × 100%
```

Target: PQP ≥ 83% (at least 5 YES and 1 PARTIAL) for submission-bound manuscripts.

---

## 5. Theoretical Adequacy (D4)

### 5.1 Metric: Theory Deployment Checklist (TDC)

Applicable to theory and empirical papers (gated by paper type). Six binary checks:

| Check | Rule source | Pass condition |
|---|---|---|
| Theory is "drawn on," not extended (unless explicitly extending) | Playbook §3.1 | Correct framing verb used |
| Constructs have provenance (cited to origin) | Checklist Part 4 §15 | Every named construct traceable to a source |
| Five-element model satisfied (IS venue) | Baird §3 | All five elements present and connected |
| No agency attribution to models | MASTER §B.4 | Models described as instruments, not actors |
| External theory limitations acknowledged | Playbook §3.2 | At least one limitation noted per borrowed framework |
| Contribution claim matches actual contribution | Baird §4 Step 6 | No over-claim; no under-claim |

### 5.2 Scoring

```
TDC = applicable_passes / applicable_checks × 100%
```

Target: TDC = 100% for submission-bound IS papers. For non-IS papers, only applicable checks count.

---

## 6. Lifecycle Progress (D5)

### 6.1 Metric: Milestone Completion Index (MCI)

Track which milestones have been completed and the quality of their artifacts:

| Milestone | Artifact | Status | Quality |
|---|---|---|---|
| M1 — Project Memo | `research_notes/project_memo.md` | Not started / Draft / Complete | — / Reviewed / Approved |
| M2 — Annotated References | `research_notes/annotated_references.md` | Not started / Draft / Complete | — / Reviewed / Approved |
| M3 — Structured Outline | `manuscript/outline.md` | Not started / Draft / Complete | — / Reviewed / Approved |
| M4 — Paper Draft | `manuscript/main.md` | Not started / Draft / Complete | — / Reviewed / Approved |
| M5 — Final Paper | `manuscript/main.md` | Not started / Draft / Complete | — / G.4 signed / Submitted |

### 6.2 Scoring

```
MCI = completed_milestones / total_milestones × 100%
```

A milestone is "complete" when its artifact exists and has been reviewed at least once by the Evaluator. "Approved" means the user has accepted the review findings and the Reflector has run.

---

## 7. The Composite Quality Dashboard

For round-over-round tracking, the Reflector produces a dashboard in the reflection report:

```markdown
## Quality Dashboard — Round <N>

| Dimension | Metric | This round | Prior round | Δ | Target |
|---|---|---|---|---|---|
| D1 — Defect Density | WFC | — | — | — | 0 (no BLOCKERs) |
| D1 — Defect Density | DCS | —% | —% | — | 100% |
| D2 — Structural Integrity | SIS | —/5 | —/5 | — | ≥ 4 |
| D3 — Prose Craft | PQP | —% | —% | — | ≥ 83% |
| D4 — Theoretical Adequacy | TDC | —% | —% | — | 100% (IS) |
| D5 — Lifecycle Progress | MCI | —% | —% | — | 100% |

**Overall trajectory:** [Improving / Stable / Regressing]
**Submission readiness:** [Ready / Near-ready / Not ready]
```

### 7.1 Submission-readiness criteria

A manuscript is **submission-ready** when:
- WFC BLOCKER count = 0
- DCS = 100%
- SIS ≥ 4
- PQP ≥ 83%
- TDC = 100% (for applicable paper types)
- G.4 sign-off completed (for submission-bound depth)

---

## 8. When Metrics Conflict with Judgment

Metrics are instruments, not verdicts. If the Evaluator's judgment says the piece is not ready but the metrics say it is (e.g., WFC = 0 but the argument is conceptually weak in a way no rule captures), the Evaluator's judgment wins. The Reflector should flag the gap and consider whether a new check or rule is needed.

Conversely, if metrics flag issues but the user and Evaluator agree the piece is ready (e.g., a MINOR that the venue does not care about), the user's decision wins (precedence rule 1).

