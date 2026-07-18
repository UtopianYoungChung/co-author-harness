# Reader-Accessibility ("Plain English") Policy — Consolidated Map for Codex

*Prepared 2026-07-13 for the harness architecture pass. Read this before designing any change to the accessibility / register / "plain English" surface. Every file:line below was verified by direct read on 2026-07-13 against package v0.27.0 (`.claude-plugin/plugin.json:3`); the one exception (the external binding anchor) is flagged as UNVERIFIED and needs folder access to close.*

---

## 1. There is no "plain English policy." There is a Reader-Accessibility Constraint.

"Plain English" in this harness is exactly **one of eight sub-checks** (Sub-check H, register appropriateness). The umbrella policy is broader and is called **reader accessibility**. It has three identities that any architecture must keep aligned:

| Identity | Where | Role |
|---|---|---|
| Methodological stance | `references/STYLE_COMMITMENTS.md` **C-5** (`:17`, `:22`) | The meta-rule that operationalises C-1…C-4; the *only* commitment that cannot be suspended via the §4 relaxation procedure. |
| Policy prose | `references/READER_ACCESSIBILITY.md` §13.1–13.5 | Definition, two-scale (local/cumulative) model, eight operational criteria, enforcement mechanics. |
| Enforcement | SAFEGUARD **Check 8**, Sub-checks A–H | Run by the Evaluator at Ph2/Ph3/Ph4. |

Design consequence for Codex: **H governs register *construction* inside structurally non-technical passages only** (signposts, framing, transitions, vignette bodies, consolidation anchors) — not register *choice* across the manuscript. The policy explicitly refuses manuscript-wide plain register as *dilution* (`READER_ACCESSIBILITY.md:15`, §13.4; C-5 "commits against … dilution that collapses intrinsic load," `STYLE_COMMITMENTS.md:17`). If the new architecture frames "plain English" as a document-level readability target, it contradicts the load-bearing design commitment.

---

## 2. Enforcement wiring (verified hop chain)

```
Evaluator Step 8.5           agents/evaluator.md:216 ; phases :45,:242 ; SAFEGUARD_LAYER.md:505
  Ph2 = A–F + H passage-subset (advisory, section-scoped)
  Ph3 = A–H (manuscript-scoped, convergence-gating)
  Ph4 = A–H (strict superset, external verifiers required)
        │
        ▼
Deterministic pre-filter     references/DETERMINISTIC_CHECKS.md
  §9b  cadence/signpost/jargon (A/D/E/F)  → NO SCRIPT (Evaluator runs ripgrep patterns)
  §9d  cumulative load (G)                → scripts/check8_g_prefilter.py  [implemented]
  §9e  register (H)                       → scripts/check8_h_prefilter.py  [reference impl only —
                                              overlay does NOT invoke it at runtime, :13-17]
        │
        ▼
Judgment overlay             skills/accessibility-overlay/SKILL.md:163 (reads §9b/§9d/§9e stubs, runs A–H)
        │
        ▼
Aggregation (SKILL.md:89-92) CLEAN / BORDERLINE (1 MAJOR) / MAJOR (≥2 MAJOR) / BLOCKER (any BLOCKER)
  → written to reviews/safeguard_layer_results.md §Check 8
        │
        ▼
Planner gate                 agents/planner.md:466 ; PHASE_PROTOCOL.md §3.3.3 (:198-207)
  BLOCKER → refuse TerminalSignoffRow, error E-Ph3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF,
            log trigger 28 ph3_accessibility_blocker_surfaced (phase_state_schema.md:206,:235);
            refused write does NOT consume Ph3 budget
  BORDERLINE → signoff permitted, surface [CONVERGENCE-BORDERLINE-ACCESSIBILITY]
        │
        ▼
Reflector Phase 2g           agents/reflector-closeout.md:82,:101 (walks trigger-28 rows, recurrence audit)
```

Scale/binding: **A–F local** (section-scoped; Ph2 advisory, Ph3/Ph4 full). **G cumulative** (full-manuscript only; binds Ph3/Ph4; `advisory_until: next_manuscript_at_ph3`). **H register** (passage scope at Ph2 under `register_class: technical|mixed`; manuscript scope Ph3+ under `non-technical`; `advisory_until: H_two_revision_cycles`).

---

## 3. What to preserve (do not "fix" these)

1. **Positive-marker compliance frame.** H passes on *presence of ≥2 of 4 positive register markers*, not on absence of negative markers (`READER_ACCESSIBILITY.md:15,:40`). This is the anti-dilution / anti-Flesch-Kincaid firewall. It is the single best decision in the policy. Keep it.
2. **Local vs. cumulative separation** (Sweller intrinsic/extraneous/germane; §13.2). A manuscript can pass every local check and still fail cumulative load; the two scales need distinct criteria.
3. **C-5 ⇄ C-7 ⇄ C-8 tension surfaced, not defaulted.** An accessibility pass may not flatten idiolect (C-7) or strip demonstrative anaphora / cadential verdicts (C-8 M-4/M-5) on taste alone; the burden of proof sits on the rule that would strip the feature (`STYLE_COMMITMENTS.md:22,:52,:72`). Preserve this arbitration.

---

## 4. Verified defect register (the actionable part)

Severity is my engineering judgment, not a harness verdict.

### D-1 — Binding authority points outside the package  [HIGH]
The policy's non-negotiable force is asserted via cross-reference to "Hard Constraint #8 in the Ph.D.-root `CLAUDE.md` §9" (`READER_ACCESSIBILITY.md:3`). **No enumerated hard-constraint list exists anywhere in the package** — every one of the ~18 in-package occurrences is a pointer, and even the shipped root-CLAUDE template `references/RESEARCH_ROOT_CLAUDE.md` has "Related files" at its §9, not a constraint list. The real definition lives in `B:\Agents\research\Ph.D. Research\CLAUDE.md` — **outside the mounted folder, UNVERIFIED** (could not be read this session). Also an internal attribution split: `READER_ACCESSIBILITY.md:3` says the rule is §9; `phase_notifications.yaml:505` and the v0.7.2 release notes say §13.
*Fix direction:* internalize the constraint text in the package (a package-owned non-negotiable register), have project CLAUDE.md *inherit* it, and reconcile the §9-vs-§13 citation. Confirm the live project file first.

### D-2 — Numeric single-source-of-truth drift  [HIGH]
The thresholds are restated in prose across `READER_ACCESSIBILITY.md §13.3`, `sub_checks.md`, and `SAFEGUARD_LAYER.md`, and re-implemented independently in scripts. Confirmed divergences:

| Threshold | Prose says | Reality / gap |
|---|---|---|
| G "needs an anchor" trigger | ≥3 load-bearing constructs (`READER_ACCESSIBILITY.md:39`, `sub_checks.md:67`, `SAFEGUARD_LAYER.md:346`) | Script measures **`para_count > 6`** (`check8_g_prefilter.py:169`) — a different, unrelated proxy. **Highest-divergence item.** |
| E jargon P-stage adjust (P0=3 / P2=1) | only `sub_checks.md:45` | Absent from policy doc and SAFEGUARD procedure — an Evaluator working from either applies a flat "two." |
| B rhythm μ>28, σ<6; 20-word warning | `READER_ACCESSIBILITY.md:34`, `sub_checks.md:19` | **Absent from `DETERMINISTIC_CHECKS.md §9b`**; the 20-word warning is also absent from SAFEGUARD and the policy doc. |
| A cadence 150/200 | all three prose files agree | Prose-only; not in any script (§9b pre-filter is ripgrep-by-hand). |
| G 3,000-word CLEAN floor | `READER_ACCESSIBILITY.md:39`, `sub_checks.md:70` | Unmechanized; absent from SAFEGUARD. Only the **5,000** upper bound is consistent end-to-end (the one fully-aligned number). |

*Fix direction:* one machine-readable thresholds table (in `sub_checks.md` or the lexicon file); policy prose and scripts reference it; retire the `para_count>6` proxy or reconcile it to the construct-count definition.

### D-3 — Per-project lexicon override documented but never implemented  [HIGH for portability]
Override via `research_notes/{hedge_terms,connective_terms,latinate_whitelist}.md` is documented in ≥6 places and deferred to "v0.10.3" (`lay_term_lexicons.md:5,:9,:36,:77`; `DETERMINISTIC_CHECKS.md:426,:457`; `sub_checks.md:115`). Package is now **v0.27.0 — 17 minor versions past target — and no code reads those files**; `check8_h_prefilter.py:25-27,:64-65` hardcodes the built-in lists and disclaims override. The `research_notes/` override pattern *is* implemented for model-dispatch directives, so the gap is specific to the lexicons.
*Compounding:* the domain-token exclusion list (`lay_term_lexicons.md:98-100`) is calibrated only to **i\*/GORE/AORE/HCI** vocabulary. A non-i\* project gets zero built-in domain-token coverage under H marker 1 and no override path — only manual `terminology_register.md`/`glossary.md` population. This is the primary barrier to using the policy as a portable *harness* rather than a project asset.

### D-4 — Claimed-implemented probe does not exist in code  [MEDIUM, grounding integrity]
`lay_term_lexicons.md:149` states the drift-detection cadence is "implemented as a deterministic probe in `DETERMINISTIC_CHECKS.md §9e` (suffix `_corpus_drift`)." **No `_corpus_drift` probe exists anywhere in `scripts/`.** Relatedly, `scripts/check8_h_prefilter.py` is a reference implementation the runtime overlay does not call (`:13-17`), and `scripts/audit/run_all.py` (the canonical D-STYLE preflight) does **not** invoke the check8 pre-filters — so the deterministic→overlay hop for Check 8 is not routed through the canonical preflight. Prose claims runtime enforcement that the code does not provide.
*Fix direction:* either implement the probes and wire them into `run_all.py`, or downgrade the prose from "implemented" to "specified." Given the project's own "green checks ≠ coherence" lesson, close the claim-vs-reality gap explicitly.

### D-5 — Cross-check conflict: H's M4 marker vs. §3 em-dash penalty  [MEDIUM]
H marker 4 (register-shift signposting) most naturally lands on an em-dash, while `DETERMINISTIC_CHECKS.md:94` penalizes em-dashes (≤1 pair/paragraph). The conflict is named ("H-motivated em-dash insertion false-fix pattern," `:104`), documented on both sides, and worked around by a prescribed semicolon/colon substitution (`READER_ACCESSIBILITY.md:100`, `lay_term_lexicons.md:139`), with a dedicated file `references/EMDASH_BUNDLE_DISCIPLINE.md:15`. It works, but it is two checks pulling opposite directions reconciled by a manual revision step.
*Fix direction:* resolve at the contract level — make the M4 marker vehicle-agnostic (semicolon/colon/cue as first-class M4 vehicles) so the deterministic and judgment checks cannot disagree.

### D-6 — Project-specific transition state fossilized into policy text  [MEDIUM]
§13.5 embeds `advisory_until: next_manuscript_at_ph3` (G), `advisory_until: H_two_revision_cycles` (H), `inherited_from_pre_h` grace, and hard-coded April-2026 / INF3006Y dates *inside the normative policy statement*. Transition scaffolding masquerading as timeless policy (the same "second authority" anti-pattern flagged in the milestone-upgrade review).
*Fix direction:* move advisory-until / cycle-counting state into machine-readable classification state; keep §13 timeless.

---

## 5. One-line brief for the architecture

The core (positive-marker frame, local/cumulative split, C-5/C-7/C-8 arbitration) is intellectually strong and should survive intact. The gap between *good project policy* and *clean harness policy* is four fixable defects: external binding authority (D-1), numeric drift with a script proxy that contradicts the prose (D-2), an unimplemented-but-documented override that breaks portability (D-3), and prose that claims runtime enforcement the code does not deliver (D-4). Fix those and the accessibility policy becomes portable.

*Open item requiring folder access: read `B:\Agents\research\Ph.D. Research\CLAUDE.md` §9/§13 to confirm the exact Hard Constraint #8 text and resolve the §9-vs-§13 citation split (D-1).*
