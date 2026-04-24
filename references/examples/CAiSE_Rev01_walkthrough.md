# Worked Walkthrough: CAiSE 2026 Revision — "Identity-Sensitive Requirements in Human-AI Collaboration"

**Piece:** `Year 2026/CAiSE_Rev01/manuscript/Identity-Sensitive_Requirements_in_Human-AI_Collaboration.tex`
**Author:** Young Jo(seph) Chung, Kun Eun (Karen) Bae, Eric Yu
**Venue:** CAiSE 2026 (38th International Conference on Advanced Information Systems Engineering, Verona, Italy)
**Publisher format:** Springer LNCS, 15-page limit (excluding references)
**Status at entry:** Conditionally accepted (3 conditions from meta-review)
**Reviewed:** 2026-02 through 2026-03 (eight revision iterations, Rev01–Rev08, plus camera-ready)
**Reviewer(s):** Author (self-critique), Claude (multiple sessions), Prof. Eric Yu (advisor, annotated manuscripts + transcripts)

**Purpose of this walkthrough.** This file documents the **full revision lifecycle** of a conditionally accepted conference paper, from initial reviewer feedback through camera-ready submission. Unlike the INF3001 walkthrough (which demonstrates a single-pass review of a course essay), this walkthrough illustrates:
- How the harness operates across **multiple revision rounds** with an advisor in the loop.
- How **reviewer conditions** map to the review pipeline's steps.
- How **lessons learned** feed back into the package itself.
- How the project reached submission-readiness (M5).

---

## Planning-Phase Context (Added 2026-04-13)

**Important note for future projects:** This walkthrough demonstrates the **revision-and-refinement** workflow for a paper already under review. The package has since been enhanced (as of 2026-04-13) to recommend starting with **M1–M3 planning phase** for new projects *before* submitting or drafting extensively.

### What Changed

The INF3001 review cycle revealed that **argumentative rigor gaps** (disciplinary placement claims, framework transfer justification, resolution of logical tensions, addressing alternative positions, epistemological transparency) cannot be caught by the internal review pipeline alone. These gaps are better addressed during the planning phase (M1–M3) before drafting begins.

### How This Walkthrough Relates

The CAiSE revision cycle shown here is a **post-submission revision** workflow, where papers are already drafted and reviewer conditions must be met. The planning-phase checklist (`M1_M2_M3_ARGUMENTATIVE_RIGOR_CHECKLIST.md`) is designed for *new* projects to prevent such revisions from being necessary in the first place.

For **future CAiSE submissions:** Use M1–M3 planning before drafting to ensure:
- Related-work positioning (M2 annotations) is robust before writing §3
- Novelty and contribution differentiation (M3 outline) are clear before drafting §5
- Framework transfers (M2) are justified before proposing the methodology (M4)
- Alternative positions (M3) are addressed before making placement claims (M4)

This walkthrough shows the *refinement loop* after submission; the planning phase prevents many refinements from being necessary.

---

---

## 1. Classification (per `REVIEW_ORCHESTRATION.md` §1)

| Input | Value | Reason |
|---|---|---|
| **Paper type** | `conference/design-science-lite` | A design contribution (identity-sensitive modeling approach) with an illustrative case, not a full empirical study. LNCS venue. |
| **P-stage** | `P2` (submission-bound) | The piece commits to a formal RQ ("How can professional identities be systematically represented and analyzed in requirements engineering for AI system adoption?") and proposes a concrete modeling approach. |
| **Venue** | CAiSE 2026 (Springer LNCS) | Engineering/IS-engineering audience. LNCS format constraints (15 pages + references). |
| **Review depth** | `submission-bound` | Conditional acceptance requires all three meta-review conditions to be met. G.4 sign-off applies. |

**Consequences of the classification.** Baird applies in full (this is an IS-venue paper with a theory-modeling contribution). Sexton applies for narrative structure and opening/closing. Bacon applies universally. The project writing style checklist applies at P2 (all items). The full SAFEGUARD_LAYER is required at submission-bound depth. DETERMINISTIC_CHECKS runs at entry and after every revision cycle. The response letter triggers `response-letter-review.md` from the skills registry.

---

## 2. Entry State — Reviewer Feedback and Meta-Review Conditions

### 2.1 Acceptance context

331 full paper submissions to CAiSE 2026; 46 accepted (≈14% acceptance rate). This paper was **conditionally accepted** — the revision had to satisfy three explicit conditions to earn final acceptance.

### 2.2 The three conditions

| Condition | Requirement | Harness mapping |
|---|---|---|
| **C1** | Strengthen and complete the related work section to position the contribution within existing socio-technical and RE4AI research. | Steps 1–2 (project guidelines + playbook §3: related work), Step 3 (Baird §2.1: five areas, §5.1: literature positioning) |
| **C2** | Clarify the novelty of the proposal vs. other i*-based extensions and applications. | Step 2 (playbook §2.1: contribution framing), Step 5 (Sexton §4: cause-effect / earned climax) |
| **C3** | Provide stronger evidence or argumentation demonstrating added value over advanced baseline methods. | Step 7 (checklist Part 4 §11: theoretical tension, §15: earned solutions), Step 3 (Baird §2.5: contribution) |

### 2.3 Individual reviewer profiles

**Reviewer 1** — Constructive, detailed. Praised integration of identity tensions with i* and the Santander illustration. Raised: (a) no evidence RE hasn't recognized identity issues, (b) no explicit RQs, (c) missing Tropos/KAOS/STS-ml positioning, (d) professional identity definition needed earlier, (e) org. identity vs. professional identity distinction, (f) citation linkability issues.

**Reviewer 2** — Critical on novelty and evaluation. Three core objections: (a) contribution is primarily an application of i*, not a methodological advance; (b) no step-by-step methodology; (c) single retrospective case with outdated baseline, no comparison to i*-based extensions or RE4AI approaches.

**Reviewer 3** — Most positive. Praised problem framing ("perfectly introduced"), theoretical integration, and meso-level analysis. Minor issues only: [6] missing DOI, "AI Team Capability" missing verb.

---

## 3. Step 0a — Deterministic Pre-flight (applied to Rev01 draft)

Ran `DETERMINISTIC_CHECKS.md` patterns against the initial revision draft.

### Counts (Rev01)

- **em-dashes (`---`):** Low; LaTeX `---` rendering clean. Not flagged.
- **absolutes:**
  - `cannot`: 4 hits (§1 "current RE practice cannot capture," §2 "functional models cannot surface," §3 "existing frameworks cannot represent," §6 "traditional approaches cannot reveal"). **All four are comparative overclaims.** MAJOR per §A1 of lessons.
  - `must`: 2 hits (§1 "organizations must address," §7 "future work must validate"). Both prescriptive. MAJOR.
  - `comprehensiv*`: 1 hit ("comprehensively model"). MINOR — remove.
  - `anticipat*`: 1 hit ("anticipate identity dynamics"). MINOR per §A3 — replace with "surface" or "reveal."
- **reveals / exposes / proves:** 3 hits of "reveals" (§5 "the model reveals," §6 "identity-sensitive modeling reveals," §6 "analysis reveals"). **MAJOR** — models don't reveal; analysts use models to analyze. Per §C3 of lessons: "Models are instruments; people take action."
- **"not X but Y" stacking:** 2 hits. Moderate, within threshold.
- **glossary-dump opening:** No. Clean.
- **there is / there are:** 1 hit. Clean.

### Verdict from Step 0a
- **BLOCKERs:** 0 from mechanical scan (but judgment-based review will promote several).
- **MAJORs:** 6 absolute-language violations, 3 "reveals/exposes" attribution errors.
- **MINORs:** 2 (comprehensively, anticipate).

---

## 4. Steps 0b–2 — MASTER Skim + Playbook Review

After reading MASTER Parts A–D and `research_paper_writing_guidelines.md`:

### Blockers identified

1. **[BLOCKER] No explicit research question (R1 objection).** The initial draft posed the problem compellingly but never stated a formal RQ. Playbook §2.2 requires at minimum one answerable question at P2. The meta-review (C2) implicitly requires this for novelty framing. → *Fixed in Rev02: Single RQ added to §1.*

2. **[BLOCKER] Comparative overclaiming — "cannot" pattern (C1/C2/C3).** Four instances of claiming other frameworks "cannot" do something without constructing models in those frameworks to demonstrate failure. Per lessons §A1: say "did not aim to" or "have not addressed," not "cannot." Per MASTER §B.2: every claim needs proportional evidence. → *Fixed across Rev02–Rev05: systematic softening with context-specific phrasing.*

3. **[BLOCKER] Related work gap (C1).** Original submission lacked positioning against Tropos, KAOS, STS-ml, and RE4AI survey literature. R1 and R2 both flagged this. Playbook §3.1 and Baird §2.1 require explicit positioning within the research conversation. → *Fixed in Rev02–Rev04: §3 expanded with complementarity framing, Ahmad et al. (2023) and Habiba et al. (2024) added as survey anchors.*

### Majors identified

4. **[MAJOR] Models attributed agency ("the model reveals").** Three instances where i* models are treated as actors. Per lessons §C3 and MASTER §B.4: attribute action to analysts, not instruments. → *Fixed Rev03–Rev05.*

5. **[MAJOR] IDEA methodology named as systematic but underspecified (R2 objection).** The four-phase IDEA procedure (Identify, Distinguish, Evaluate, Articulate) was presented as "systematic" without operational detail (interview protocol, softgoal derivation rules, exhaustiveness criteria). → *Fixed by strategic retreat: IDEA acronym removed per DIR-ACADEMIC-01 §Key Rule 6; three-step procedural guidance provided in §4.1 as "a starting point"; systematic methodology positioned as future work.*

6. **[MAJOR] Single case cannot validate methodology (R2 objection).** Retrospective analysis of the Santander case is descriptive reconstruction, not discovery. Self-critique identified circular reasoning risk. → *Fixed by reframing: "illustrative" not "validation"; added three supplementary examples in online repository; scoped as representational adequacy.*

7. **[MAJOR] External theories positioned as co-equal with home discipline.** Dynamic capabilities and organizational identity theory treated as peers to RE/modeling. Per lessons §B1–B2: "External theories support, don't found, the contribution." → *Fixed Rev03: asymmetric framing throughout ("we draw on X and use Y to...").*

8. **[MAJOR] Reference [6] (Brynjolfsson et al.) misused.** Cited as professional identity source but paper is about labor displacement. Self-critique flagged this as Critical Issue 3. → *Fixed Rev02: replaced with Herrmann & Pfeiffer (distributed agency) and Carter & Grover (IT Identity).*

### Minors identified

9. **[MINOR] Abstract lists 3 requirement themes; body and conclusion list 4.** Inconsistency between abstract and downstream sections. → *Fixed Rev03.*

10. **[MINOR] "AI Team Capability" missing verb (R3 minor).** Label in model is noun phrase without action verb. → *Fixed Rev04.*

11. **[MINOR] Citation order inconsistencies.** LNCS requires sequential first-appearance ordering. Per lessons §F3. → *Fixed Rev06; verified by `scripts/check_citation_order.py`.*

---

## 5. Step 3 — Baird (full application, IS-venue paper)

### Five-element model assessment

| Element | Status at Rev01 | Status at camera-ready |
|---|---|---|
| **Focus** | Present but blurred by multiple theoretical threads | Sharp: identity-sensitive requirements modeling, single RQ |
| **Background** | Thin; missing Tropos/KAOS/STS-ml; missing RE4AI surveys | Full: §3 expanded with 15+ new references, complementarity framing |
| **Tension** | Implicit (identity concerns unmodeled in RE) but never named as a "gap" in the literature | Explicit: grounded in Ahmad et al. (2023, 43 studies) and Habiba et al. (2024, 126 studies) documenting stakeholder-centric RE gaps |
| **Resolution** | i* mapping asserted but not demonstrated through a clear analytical path | Three-step procedural guidance in §4.1; Table 1 mapping; full illustrative analysis in §5; Table 2 with four requirement categories |
| **Guidelines** | Not present | §4.1 procedural guidance (steps a, b, c); §6 identity-sensitive analysis principles; future work scoped |

### Nine-step empirical process

Not directly applicable (this is an illustrative case, not a full empirical study). However, Baird's "data and analysis" standards informed the critique of the Santander retrospective: the case illustrates representational adequacy but cannot claim predictive or explanatory validity. This scoping was made explicit in the camera-ready revision.

### Rookie mistakes check (Baird §5)

- **Laundry-list lit review:** Not present. §3 organizes literature by four tracks (human-AI collaboration, RE4AI, agent-oriented modeling, i* extensions) with complementarity framing.
- **Surprise constructs:** Initial draft had four governance checks appearing ex nihilo (§5). Addressed by removing the overspecified IDEA framing and providing lighter procedural steps grounded in the theoretical framework.
- **Disconnected future research:** Initial closing was vague ("future work should validate"). Camera-ready names three concrete directions: (1) systematic methodology development, (2) prospective validation across organizational contexts, (3) broader social modeling agenda.

---

## 6. Step 4 — Bacon (sentence craft)

Applied Bacon §10 checklist across the camera-ready text:

- **Sentence length:** Controlled. Longest sentence identified was ~50 words in §4. No 60+ word sentences surviving from earlier drafts (the 142-word sentence flagged in INF3001 work was from a different paper; this manuscript stayed within bounds).
- **Subject-verb focus:** Strong. The Santander case provides concrete actors (Sarah the recruiter, junior analysts, AI screening system) as grammatical subjects throughout §5.
- **Attribution clarity:** Improved across revisions. "Models reveal" → "analysts can identify through modeling." Per lessons §C3.
- **Parallelism:** Table 1 and Table 2 maintain parallel structure across rows.
- **Variety:** Good mix of sentence types. No monotony clusters detected.

**Verdict:** Clean at the sentence level. No BLOCKERs or MAJORs from Bacon.

---

## 7. Step 5 — Sexton (narrative craft)

- **[STRONG] Opening with impact (Sexton §1).** §1 moves quickly to the phenomenon: "As AI systems assume increasingly agentic roles... they emerge as new organizational members and partners to employees, fundamentally altering workplace relationships and professional identities." Concrete before abstract.
- **[STRONG] Show-then-tell (Sexton §2).** §2 Motivation provides four real-world accounts (Santander, call center, journalism, manufacturing) before theorizing. The reader sees the pattern before the claim.
- **[STRONG] Cause-effect / earned climax (Sexton §4).** The modeling proposal in §4 follows from §2 (motivation) and §3 (gap in existing work). The i* choice is earned through the incremental introduction: agent-oriented family → survey of Tropos/KAOS/STS-ml → narrow to i* for the Position construct. Per lessons §E1.
- **[MINOR] Forward drive (Sexton §3).** The transition from §3 (Related Work) to §4 (Theoretical Foundations) could be sharper. The gap statement at the end of §3 carries the burden but a single bridging sentence would strengthen the narrative arc.
- **[STRONG] Title and roadmap.** Title is descriptive and accurate. Roadmap at end of §1 is present.

---

## 8. Step 6 — Precedence and Conflict Check

### Venue constraints applied

- Springer LNCS format, 15 pages (+ references). Camera-ready at 15 pages. Compliant.
- 3–5 keywords required. Five provided. Compliant.
- Citations linkable: Improved in camera-ready (hyperlinked). Per R1 minor request.

### Advisor instructions applied (precedence level 3)

Prof. Yu's annotated feedback generated 30+ specific directives across three meeting transcripts (03.12, 03.19, audio1111262520) and two annotated manuscript PDFs. Key advisor overrides recorded in `lessons_caise_revision.md`:

- **§A1:** Never claim "cannot" without evidence. (Override: stronger than MASTER §B.2's general rule; applied as absolute prohibition.)
- **§B3:** Select theory on its own merit, not because it maps to a modeling language. (Override: reorders the theory-before-tool presentation.)
- **§C2:** Avoid social-science vocabulary for an engineering audience. (Override: applies venue-specific vocabulary filtering beyond MASTER §B.5.)
- **§D3:** Don't be defensive in the response letter; take the high ground. (Override: response letter craft, applied at precedence level 3.)
- **§E2:** Track what each additional case tests. (Override: extends package's evaluation guidance.)
- **§F4:** Single answerable RQ is sufficient; don't over-commit. (Override: RQ2 dropped on advisor instruction.)
- **§G3:** Keep distance from "agentic AI" hype framing. (Override: conceptual-level language throughout.)

### Project-specific directives

- `DIR-ACADEMIC-01.md`: Two-layer framing (identity/agency in RE [broad] vs. professional identity in AI adoption [specific]). Key Rule 6: Do not mention IDEA acronym.
- `DIR-ISTAR-01.md`: iStar 2.0 compliance, JSON output format, modeling standards.
- `DIR-OPS-001.md`: Operational governance.
- `DIR-ROOT-001.md`: Root-level project configuration.

### Conflicts noted

No conflicts between package rules and advisor instructions. The advisor's directives are **stricter than** the package defaults in every case (e.g., "never claim cannot" is stricter than "avoid absolutes"). Per precedence rule 3, advisor instructions win.

---

## 9. Step 7 — Integrated Checklist Pass (P2, submission-bound)

Walking `project_writing_style_checklist.md` at P2:

| Checklist item | Status | Notes |
|---|---|---|
| Part 1 §1 Clear Central Need | PASS | Identity concerns in RE are unmodeled; grounded in two systematic reviews. |
| Part 1 §1 Forward Drive | PASS | Problem → gap → RQ → approach → illustrative analysis → discussion. |
| Part 1 §1 Hidden-Assumptions Audit | PASS | "Agentic" marked as contested framing (per §G3). Intentional stance applied symmetrically to human and AI actors. |
| Part 1 §3 Earned Solutions | PASS | i* earned through incremental introduction (§E1). |
| Part 4 §11 Theoretical Tension | PASS | Identity theory (social psychology) × agent-oriented modeling (CS/IS) × dynamic capabilities (strategic management): cross-disciplinary tension is made productive, not dissolved. |
| Part 4 §11 Resolution / Guidelines | PASS | Three-step guidance in §4.1; Table 1 mapping; Table 2 requirements. Systematic methodology deferred to future work. |
| Part 4 §15 No Surprise Constructs | PASS | All constructs (person-based, role-based, relational identity; Position construct; softgoals) introduced with provenance before use. |
| Part 4 §15 Construct Provenance | PASS | Sluss & Ashforth → identity dimensions; Carter & Grover → IT Identity; Herrmann & Pfeiffer → distributed agency; Horkoff & Yu → goal evaluation. All cited and deployed. |

**No items failed at the final checklist pass.**

---

## 10. Step 8 — Consolidated Findings Report (camera-ready state)

### Summary

The paper underwent eight revision iterations (Rev01–Rev08) over approximately four weeks, driven by three meta-review conditions and detailed advisor feedback. The revision addressed all three conditions through: (1) a substantially expanded §3 with complementarity framing and two survey anchors, (2) explicit novelty framing as "bringing identity and agency into RE" rather than merely demonstrating i*'s adaptability, and (3) representational comparison via Table 2, three supplementary examples, and explicit scoping as illustrative rather than comparative.

### Final defect state

- **BLOCKERs remaining:** 0
- **MAJORs remaining:** 0
- **MINORs remaining:** 1 (§3→§4 transition could be sharper; accepted as within tolerance for 15-page limit)
- **Deterministic check violations:** 0 (`cannot` eliminated; `must` softened; `reveals` re-attributed; citation order verified by script)

### What the revision changed

| Area | Before (Rev01) | After (camera-ready) |
|---|---|---|
| Research questions | None stated | 1 explicit RQ in §1 |
| Related work | Thin; no Tropos/KAOS/STS-ml; no RE4AI surveys | Full §3 with 4 tracks, 15+ new references, complementarity framing |
| Methodology framing | "IDEA" presented as systematic procedure | IDEA removed; three-step guidance in §4.1; systematic methodology as future work |
| Comparative language | 4× "cannot," 2× "must," 3× "reveals" | Context-specific softening: "have not addressed," "were not aimed at," "lie outside the analytical focus of" |
| External theories | Co-equal with RE | Asymmetric: "we draw on X and use Y to..." |
| Case framing | Implied validation | Explicitly illustrative; representational adequacy |
| References | ~22 | 38 (added Tropos, KAOS, STS-ml, Ahmad 2023, Habiba 2024, Carter & Grover, Herrmann & Pfeiffer, and others) |
| Page count | ~13 pages | 15 pages (at limit) |

---

## 11. Step 8.5 — SAFEGUARD_LAYER (post-review integrity checks)

### Check 1: Regression guard
No previously fixed issues were reintroduced. The `cannot` pattern was systematically eliminated and stayed eliminated across all subsequent revisions. The `DO_NOT_DISTURB.md` mechanism (had it existed at the time) would have frozen the "no cannot claims" rule after Rev02.

### Check 2: Drift detection
The contribution claim remained stable: "bringing identity and agency concepts into RE." The two-layer framing (broad contribution + specific instance) was maintained per DIR-ACADEMIC-01. No scope creep detected.

### Check 3: Abstract-body consistency
Abstract lists three identity dimensions (person-based, role-based, relational) and four requirement categories (transparency, authority preservation, competence development, experience-differentiated design). Both confirmed present in body (§4 and Table 2 respectively). The earlier 3-vs-4 requirement theme misalignment was fixed.

### Check 4: Contradiction audit
No internal contradictions detected in the camera-ready version. The earlier Baumer-vs-i* style tension (provisional subjects vs. fixed agent nodes) is not present in this paper because this paper does not cite Baumer. The theoretical apparatus is internally consistent: identity theory → mapping → i* constructs → illustrative analysis.

### Check 5: Edit traceability
Full traceability maintained through: `revision_traceability_matrix.md` (reviewer comments → revision artifacts → completion status), `revision_log_rev06.md` (50+ line-level changes with reasons and transcript references), `changelog.md` (infrastructure evolution), and eight dated manuscript PDFs (Rev01–Rev08).

### Check 6: Humanness voice audit
Prose reads as authored, not generated. Specific indicators: the Santander case uses domain-specific detail (Sarah the recruiter, junior analyst rotation, talent-pool screening) that reflects close reading of the source material. Softening phrases vary by context (six different constructions across sections). Sentence rhythm varies. No "Furthermore, it is important to note that" or other LLM-tic patterns detected.

---

## 12. Response Letter Assessment

The response letter (`manuscript/response_letter.tex`) was assessed against `skills/packaged/response-letter-review.md`:

### Check 1: Opening strength
Opens with the contribution positively: what the paper does, not what it doesn't do. Per lessons §D1: no weakness words in the opening paragraph. **PASS.**

### Check 2: Discipline provenance
Parent disciplines named: "social psychology" for identity theory, "strategic management" for dynamic capabilities. Per lessons §D2. **PASS.**

### Check 3: Tone audit
High-ground framing throughout. Addresses conditions by reframing rather than counter-arguing. Per lessons §D3: "We can take the high ground." **PASS.**

### Check 4: Coverage completeness
All three conditions explicitly addressed with section references. Individual reviewer comments mapped to specific revisions. R1's eight points, R2's three points, R3's two points all traceable. **PASS.**

### Check 5: Scope hedging
Illustrative scope stated clearly: "representational adequacy," not "validation." Future work explicitly names systematic methodology development. **PASS.**

---

## 13. Revision Timeline and Round Summary

| Rev | Date | Trigger | Key changes |
|---|---|---|---|
| Rev01 | 2026-02-10 | Conditional acceptance received | Initial revision planning; self-critique drafted |
| Rev02 | 2026-02-27 | Self-critique + R1/R2/R3 mapping | RQ added; reference [6] replaced; related work expansion begun |
| Rev03 | 2026-03-02 | Continued revision | §3 complementarity framing; Tropos/KAOS/STS-ml positioning; asymmetric theory framing |
| Rev04 | 2026-03-10 | Advisor feedback (03.12 transcript) | Incremental i* introduction; "cannot"→"have not addressed"; theory-before-tool ordering |
| Rev05 | 2026-03-18 | Advisor annotated manuscript | Context-specific softening; attribution corrections ("models reveal"→"analysts identify"); response letter v1 |
| Rev06 | 2026-03-19 | Advisor meeting (03.19 transcript) | 50+ line-level changes; RQ2 dropped; organizational identity heading clarified; citation order fixed |
| Rev07 | 2026-03-21 | Final QA | Figures inserted; page count verified; response letter finalized |
| Rev08 | 2026-03-23 | Camera-ready submission | Final PDF compiled; copyright form signed; camera-ready package assembled |

---

## 14. Final State and Submission-Readiness Assessment

Using `SUCCESS_METRICS.md` dimensions (retrospective application):

| Dimension | Metric | Value | Threshold | Status |
|---|---|---|---|---|
| D1 Defect Density | WFC | 0 | BLOCKER=0 | **PASS** |
| D1 Defect Density | DCS | 100% | 100% | **PASS** (all 9 deterministic categories within threshold) |
| D2 Structural Integrity | SIS | 5/5 | ≥4 | **PASS** (all sections present, correctly ordered, argument flows) |
| D3 Prose Craft | PQP | ≈92% | ≥83% | **PASS** (sentence variety: YES, first-person navigation: YES, asymmetric rhythm: YES, concrete anchors: YES, LLM-tic absence: YES, lived-in detail: PARTIAL — case is retrospective, not firsthand) |
| D4 Theoretical Adequacy | TDC | 6/6 | 100% | **PASS** (all binary checks: theory deployed, constructs grounded, provenance cited, tension productive, resolution offered, guidelines scoped) |
| D5 Lifecycle Progress | MCI | 100% | — | M5 complete: camera-ready submitted, accepted |

**Submission-readiness verdict: READY.** All thresholds met. Paper accepted at CAiSE 2026.

---

## 15. Lessons Extracted (back into the package)

This revision cycle generated the richest set of lessons of any project to date. They were captured in `research_notes/review/lessons_caise_revision.md` (7 sections, A–G, 30+ rules) and have been treated as **cross-project lessons** (applied to INF3001 and future work by author directive). Key package-level takeaways:

### L1. Comparative language requires a lesson, not just a rule
The package's MASTER §B.2 says "every claim needs proportional evidence." This was insufficient — the CAiSE revision needed the stronger lesson §A1 ("Never claim 'cannot' without evidence; say 'did not aim to'"). The lesson is now in the package as a project-specific supplement that the author has elected to apply cross-project. **Recommendation:** Promote §A1 to a DETERMINISTIC_CHECKS pattern (grep for `cannot`, `unable to`, `fails to` in comparative contexts).

### L2. Theory selection justification must precede tool selection
Prof. Yu's directive (§B3) — "adapt the modeling language to suit a good theory, not narrow yourself because there is a modeling language" — is a package-level principle. The package's current guidance (Baird §2.3: "locate your work") does not explicitly sequence theory-before-tool. **Recommendation:** Add to MASTER §B.4 or to the IS-theory-pass skill.

### L3. Audience vocabulary filtering is venue-critical
Lessons §C1–C2 (know the technical meaning of terms; avoid social-science vocabulary for engineering audiences) exposed a gap: the package's cross-venue playbook does not have a venue-specific vocabulary gate. **Recommendation:** Add a vocabulary-awareness step to the review pipeline, triggered by venue classification.

### L4. Response letter craft deserves its own pass
The response letter required five specific checks (opening strength, discipline provenance, tone audit, coverage completeness, scope hedging) that were not part of the manuscript review. The `response-letter-review.md` skill was created partially in response to this need. **Confirmed:** The skill covers all five checks.

### L5. Advisor feedback generates project-specific lessons that outlast the project
The 30+ rules in `lessons_caise_revision.md` are too detailed for the package's general rules but too valuable to discard. The harness's three-tier skill system (package → project → global) handles this: the author elevated the CAiSE lessons to cross-project status by explicit instruction, and several rules (§A1, §B3, §C3, §D3) are candidates for package-level promotion. **Pattern:** Advisor feedback produces "candidate package rules" that should be evaluated by the Reflector.

### L6. Self-critique before external review is high-value
The self-critique documents (`self_critique.md`, `self_critique_expanded.md`) identified the three most critical issues (circular validation, IDEA underspecification, reference [6] misuse) before any external reviewer or advisor saw them. This compressed the revision timeline. **Recommendation:** Add self-critique as a recommended pre-step in `AGENT_ORCHESTRATION.md` §3 (before dispatching the Evaluator).

### L7. Traceability artifacts prevent drift across long revision cycles
With eight revisions over four weeks, the traceability matrix (`revision_traceability_matrix.md`) and revision log (`revision_log_rev06.md`) were essential for ensuring no reviewer comment was lost. The harness's `manuscript/revision_log.md` seed file (from `PROJECT_BOOTSTRAP.md`) was designed with this need in mind, but this project predated the bootstrap template. **Confirmed:** The template is sufficient; the pattern works.

### L8. Governance simplification improves focus
The project's early 3-agent architecture (RE + Academic + UX Research) was streamlined to a 2-agent dyad (RE + Academic) when the UX layer was found to add no value. This mirrors the harness principle of minimal viable process. **Recommendation:** When bootstrapping, start with the minimum agent configuration and add agents only when the project demands it.

---

## 16. Relationship to the Harness

This project predates the formalized harness (the package was finalized in April 2026; this paper was submitted in March 2026). Nevertheless, the revision process **implicitly followed** many of the harness's patterns:

| Harness component | CAiSE_Rev01 equivalent |
|---|---|
| `REVIEW_ORCHESTRATION.md` (seven-step pipeline) | Informal but present: deterministic checks → content review → sentence craft → integration pass |
| `DETERMINISTIC_CHECKS.md` | `lessons_caise_revision.md` §A1–A3 (absolute language), `scripts/check_citation_order.py` (citation verification) |
| `SAFEGUARD_LAYER.md` | `self_critique.md` (internal adversarial review), `revision_traceability_matrix.md` (traceability), `section_by_section_review_for_external_feedback.md` (external QA) |
| `AGENT_ORCHESTRATION.md` (four agents) | Informal: Planner (revision plan v2), Evaluator (self-critique), Generator (8 revision iterations), Reflector (lessons learned) |
| `PROJECT_BOOTSTRAP.md` (directory template) | Partially matches: `manuscript/`, `research_notes/`, `research_notes/review/` all present. Missing: `reviews/` directory (findings scattered across research_notes), `skills/` directory, `CLAUDE.md` project file (directives served this function). |
| `SUCCESS_METRICS.md` (five dimensions) | Retrospectively applied in this walkthrough (§14). Not available during the actual revision. |
| `GROUNDING_PROTOCOL.md` (no-hallucination rules) | Implicitly followed: all citations verified against source PDFs; all claims traced to literature; no gap-filling detected. |

This walkthrough serves as **evidence that the harness's patterns work** — they were discovered independently through the pressure of a real conditional acceptance, then formalized into the package. The CAiSE_Rev01 project is both a successful outcome and a primary source for the harness's design.

---

*This walkthrough is saved as `examples/CAiSE_Rev01_walkthrough.md` in the `.paper-package/` deployment. The camera-ready manuscript is at `Year 2026/CAiSE_Rev01/manuscript/camera_ready_package_IdentitySensitive/Identity-Sensitive_Requirements_in_Human-AI_Collaboration.pdf`. The lessons learned file is at `Year 2026/CAiSE_Rev01/research_notes/review/lessons_caise_revision.md`.*
