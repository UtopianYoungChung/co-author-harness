---
document_type: harness_proposal
filed_by: harness_session_agent
filed_on: 2026-04-23
status: IMPLEMENTED on v0.7.2 canonical substrate (2026-04-23); ship target v0.8.1 confirmed; v0.8.1 unpacked tree packaging pending
decisions_applied:
  D-G-1: ship as v0.8.1 (patch release rebased on v0.8.0); do not amend v0.8.0 §7 non-goal
  D-G-2: option A (single accessibility-overlay skill with a G branch; no sibling skill)
  D-G-3: advisory-only under run-phase-3-stability (no full-Ph3 escalation on G under stability mode)
  D-G-4: option (c) — D-13 registered as Ph4 revision candidate for INF3006Y Co Author + Sub-check G advisory-until-next-manuscript
targets:
  primary: research-writing-harness-claude v0.8.1 (confirmed)
  consumer_manuscript: INF3006Y Co Author paper — directive D-13 (consolidation anchors) registered 2026-04-23
relates_to:
  - proposals/v0.8.0_upgrade_architecture.md §7 (non-goals — v0.8.1 resolves the conflict by landing G in the follow-on release)
  - references/READER_ACCESSIBILITY.md (policy)
  - references/SAFEGUARD_LAYER.md Check 8 (enforcement)
  - references/TIER_PROTOCOL.md §3.3.3 (gate — PHASE_PROTOCOL.md in v0.8.x surfaces)
  - skills/accessibility-overlay/SKILL.md (overlay v1.1)
grounding_basis:
  - Session architecture draft (Sub-check G — cumulative cognitive load / consolidation anchors at structural boundaries)
  - v0.7.2 canonical substrate contracts as of 2026-04-23: six Sub-checks A–F; §3.3.3 gate names A–F; `accessibility-overlay` at v1.0 with six flags; `SAFEGUARD_LAYER.md` Check 8 scope (T2 section / T3–T4 full manuscript)
implementation_log:
  - 2026-04-23 — D-13 registered in `Ph.D. Research/INF3006Y_AgencyDelegation/research_notes/directives.md` (Ph4 revision candidate paired with advisory-only Sub-check G for this manuscript's Ph4 pass; D-G-4 option c).
  - 2026-04-23 — `references/READER_ACCESSIBILITY.md` §13.1 and §13.2 expanded to name the local/cumulative distinction; §13.3 criterion 7 added (Consolidation anchors at structural boundaries); §13.5 remapped six→seven criteria and A–F→A–G, with the `advisory_until: next_manuscript_at_ph3` transitional scoping paragraph appended.
  - 2026-04-23 — `references/SAFEGUARD_LAYER.md` Check 8 expanded: preamble updated from six→seven Sub-checks; two-scale architecture paragraph added; Sub-check G procedure, severity floors, output format, and dispatch-table rows added; Stability-sub-mode interaction subsection added per D-G-3; Provenance line amended; "How the output is used" bullet updated to name the advisory-until exception.
  - 2026-04-23 — `references/TIER_PROTOCOL.md` §3.3.3 updated: gate trigger enumeration amended A–F → A–G with the Sub-check G transitional exception; logging text updated to log G findings and mark advisory-under-flag status.
  - 2026-04-23 — `skills/accessibility-overlay/SKILL.md` bumped to v1.1 per D-G-2: frontmatter description and version updated; Preconditions extended with scope-resolution check and stability-sub-mode interaction; new `G_REQUIRES_FULL_MANUSCRIPT` noop reason code; Sub-check G section added with procedure, severity floors, Sub-check D interaction note, advisory-until and stability-advisory paths; Aggregate-verdict block updated to note G contribution conditions; Output template extended with G block and two new output fields; Tier-conditioning block updated to distinguish A–F at T2 from A–G at T3/T4; closing normative status updated to v0.8.1.
  - 2026-04-23 — `CHANGELOG.md` prepended with v0.8.1 Unreleased section capturing Sub-check G ship scope, decisions applied, and three lessons (L-v0.8.1-01 through L-v0.8.1-03).
  - 2026-04-23 — `references/DETERMINISTIC_CHECKS.md §9d` added (Cumulative cognitive load pre-filter feeding Sub-check G): boundary-gap word counts, paragraph counts since last major heading, consolidation-cue density in pre- and post-heading windows, G-candidate boundary synthesis marker, P-stage-adjusted gap envelope (P0 ≥ 800 / P1 ≥ 700 / P2 ≥ 600 words). §9d slot chosen over §9c because §9c is already in use for the INF3001H artifact-organization block. `accessibility-overlay/SKILL.md` frontmatter and Integration-with-§9b paragraph updated to reflect §9d as G's pre-filter feeder; SAFEGUARD_LAYER.md Sub-check G procedure step 0 added to consume §9d output as the Evaluator's enumeration seed. Decision upgrades the proposal §4.4 "optional" tag to shipped-with-v0.8.1.
  - 2026-04-23 — DEFERRED (for v0.8.1 unpacked-tree packaging): `unpacked/research-writing-harness-claude-v0.8.1/` substrate to be cut from v0.8.0 + these v0.7.2 edits merged forward; `skills/run-phase-3-stability/SKILL.md §3.2` G-advisory language applied at that point (SAFEGUARD_LAYER.md paragraph is canonical until then); `Ph.D. Research/CLAUDE.md §13` root-level summary update from "six criteria" to "seven" (deferred per §4.7 out-of-scope note to avoid precedence-7 drift until v0.8.1 unpacked tree is validated).
---

# Proposal: SAFEGUARD Check 8 — Sub-check G (Consolidation Anchors / Cumulative Load)

## 1. Problem statement

Check 8 Sub-checks **A–F** operationalize **local** reader-accessibility: paragraph cadence, sentence rhythm, first-use definitions, section-open signposting, jargon density per paragraph, worked examples at density spikes. A manuscript can pass every local check while still imposing a **cumulative** working-memory tax: the reader reaches a late section holding multiple framings, positions, or tensions **without** a deliberate **consolidation anchor** (short accumulation summary or equivalent move) at **structural boundaries** agreed in project policy.

`READER_ACCESSIBILITY.md` §13.2 already names Sweller’s taxonomy, including **germane** load across the reading experience; §13.3’s six criteria do not yet name a **manuscript-scale** consolidation obligation. External meta-feedback (round three) asked the harness to own a **distance scale**, not only local signals.

**Intent:** Add **Sub-check G** as the seventh operational criterion, enforced through the same Check 8 aggregate and (when binding) `PHASE_PROTOCOL.md §3.3.3` terminal gate — with explicit **phase- and project-scoped** binding and an optional **deterministic hint** layer.

## 2. Conflict with `v0.8.0_upgrade_architecture.md` §7

The binding architecture **r20** lists as a **non-goal**:

> Any change to `PHASE_PROTOCOL.md §3.3.3` (the Check 8 accessibility gate at Ph3 TerminalSignoffRow).

Sub-check G **requires** edits to §3.3.3 (at minimum: Sub-check enumeration **A–G**, trigger 28 / Planner logging text, and any new **advisory-only** semantics if adopted). Therefore:

- **Recommended:** Treat this proposal as **v0.8.1** (or later) scope, **after** v0.8.0 ship, **or**
- **Alternative:** Record an explicit **user decision** that amends §7 for a **late v0.8.0** slot (re-run paired review on gate semantics).

This proposal does **not** assume v0.8.0 Phase 3–5 work is blocked; it assumes G lands in a **follow-on** release unless the non-goal is formally lifted.

## 3. Review of the session draft (satisfied / gaps)

**Satisfied**

- **Three coordinated surfaces** (manuscript directive, policy, enforcement) match the separation of concerns already used for D-10/11/12 vs harness files.
- **Local vs cumulative** distinction is the right conceptual handle; it aligns with §13.2’s germane-load framing.
- **Full-manuscript scope for G** matches `SAFEGUARD_LAYER.md` Check 8 text that T3/T4 run on the **full manuscript** while explaining why the current `accessibility-overlay` **section** dispatch is insufficient for G alone.
- **Ph2 advisory / Ph3–Ph4 binding** is consistent with `READER_ACCESSIBILITY.md §13.5` phasing language (to be made explicit for G).
- **Aggregation** (one MAJOR → BORDERLINE; any BLOCKER → BLOCKER) should **extend to seven** Sub-checks unless a project explicitly exempts G from aggregate (not recommended for default harness behavior).

**Gaps to close in implementation**

1. **Stability sub-mode (`run-phase-3-stability`):** Today the reduced pass re-runs §9b **counters** and inherits A–F from the prior F1. G is **judgment-heavy**; inheritance rules need a **single** chosen pattern: full-Ph3 escalation when G-relevant manuscript state changes, a **stored G-summary hash** in F1, or **G advisory-only** under stability until a full pass.
2. **`advisory_until` / one-off Ph4:** If a project uses **advisory-only G** for the current manuscript, the **exact** machine- and human-readable condition (project id, plugin version, directive key) must live in **one** place (`SAFEGUARD_LAYER.md` + `directives.md` cross-ref) to avoid split-brain gate behavior.
3. **Overlay skill:** Option A (extend `accessibility-overlay` with a G branch + `scope: full_manuscript`) vs Option B (thin sibling skill) should be decided before large edits; either way, **noop reason** `G_REQUIRES_FULL_MANUSCRIPT` (or equivalent) when only a section path is provided.
4. **Deterministic layer:** Optional §9b extension or new **§9c** “G candidates” (e.g. distance since last boundary-anchored paragraph) — **hints only**, not pass/fail, to stay aligned with §9b’s pre-filter pattern.

## 4. Architecture (binding design)

### 4.1 Policy (`references/READER_ACCESSIBILITY.md`)

- Add **§13.3** bullet (or numbered criterion) **7 — Consolidation anchors at structural boundaries**: one-sentence (or short) **accumulation summaries** (or equivalent consolidation moves) at **nominated** structural boundaries so the reader can **rebase** working memory before new argumentative load.
- Expand **§13.1–13.2** with one explicit sentence: local criteria (1–6 / A–F) vs **cumulative** criterion (7 / G).
- Update **§13.5**: map **seven** criteria to Sub-checks **A–G**; name G (e.g. **Consolidation-Flag** or **Cumulative-Load-Flag**) parallel to existing flag names.

### 4.2 Enforcement (`references/SAFEGUARD_LAYER.md` Check 8)

- Add **Sub-check G** with: **scope = full manuscript only**; procedure (outline → boundary list from project `directives` or default schema → read for consolidation moves); **severity floors** (calibrated to “missing anchor at required boundary” vs “reader cannot reconstruct thread”); **output template** line `- G. …`.
- Remap **Procedure** header from six → **seven** sub-checks; **Output format** and **Severity aggregation** include G.
- Preserve existing A–F aggregation rule and **extend** to include G in the same **MAJOR/BLOCKER** counting (unless a **project directive** explicitly sets G to advisory-only — then document the exception in aggregation for that project only).

### 4.3 Phase gate (`references/PHASE_PROTOCOL.md` §3.3.3, `agents/planner.md`, `references/phase_state_schema.md` as needed)

- Replace **A–F** with **A–G** everywhere the Check 8 gate names sub-checks (gate trigger, logging, trigger 28 `notes`).
- If **advisory-only** G is adopted for a closed project: §3.3.3 must state that **G does not emit a terminal BLOCKER** under that directive (while still appearing in `safeguard_layer_results` for audit).

### 4.4 Deterministic pre-filter (`references/DETERMINISTIC_CHECKS.md`)

- Optional **§9c** (or §9b extension): emit **candidate boundary gaps** for Evaluator judgment — **not** a standalone pass/fail.

### 4.5 Skill (`skills/accessibility-overlay/SKILL.md` or sibling)

- Implement G per §3 **Option A or B**; bump **overlay version**; extend aggregate verdict to **seven** Sub-checks; document **full-manuscript** dispatch in Evaluator Step 8.5.

### 4.6 Ph3 stability and run-phase skills

- Update `skills/run-phase-3-stability/SKILL.md` **§3.2** text: either G **excluded** from counter-only stability pass (forces escalation when G binding) or **inheritance** rule for G as per §3.1 above.

### 4.7 Project manuscript (out of plugin zip)

- Register **D-13** in `INF3006Y_AgencyDelegation/research_notes/directives.md` (or equivalent): **scope-fenced** consolidation anchors at **2–3** boundaries; **Ph4 revision candidate** so the Generator lands anchors before G.4 sign-off when that project uses the harness for the Co Author paper.

**Out of scope for the first implementation pass (unless user directs):** root `Ph.D. Research/CLAUDE.md` §13 edit — update **after** `references/READER_ACCESSIBILITY.md` is stable to avoid precedence-7 drift.

## 5. Verification (when implemented)

- `scripts/skill-check.py` — SKILL metadata and triggers consistent.
- `scripts/release-gate.sh` — no new blockers from description-length or manifest drift (expect touch of multiple references).
- Spot grep: **A–F** remaining only where historical narrative requires; **A–G** in gate paths.
- One **golden-path** Evaluator notes: full manuscript, G CLEAN vs G BLOCKER, Planner gate behavior matches §3.3.3.

## 6. Release packaging

- Ship as **v0.8.1** patch release with **CHANGELOG** entry: “Check 8 Sub-check G (consolidation anchors); §3.3.3 enumeration A–G; READER_ACCESSIBILITY §13.3 seventh criterion.”
- If combined with other small reference-only changes, keep the same minor bump once.

## 7. Decisions required from user

| ID | Question | Default recommendation |
|----|----------|-------------------------|
| D-G-1 | **Release:** v0.8.1 follow-on vs amend v0.8.0 §7 non-goal? | **v0.8.1** |
| D-G-2 | **Overlay:** Option A (single skill) vs B (sibling skill)? | **A** unless G exceeds ~40% of skill size — then B |
| D-G-3 | **Stability mode** for G? | **Escalate to full Ph3** when manuscript bytes change and G is binding; document |
| D-G-4 | **INF3006Y** one-off: Ph4 revision candidate + **G advisory** for that manuscript’s Ph3 close-out? | **Yes (c)** — matches prior session recommendation; must be written into `directives` + SAFEGUARD |

---

*End of proposal.*
