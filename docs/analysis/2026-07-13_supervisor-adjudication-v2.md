# Supervisor adjudication v2 — cadence + Sub-check J (Cowork second opinion on Codex's revisions)

*2026-07-13. Role: supervisory review and second opinion. This file records validated decisions and issues directives; the implementation (profile, prose edits, schema) is Codex's task. Supersedes the severity/ceiling/provenance/schema details in `2026-07-13_task4a-cadence-and-j-dropins.md`. It does not restate the banded-cadence model or the J-out-of-A–H disposition, both of which stand.*

---

## 0. Verification finding that changes the scope of point 7

Codex's point 7 is not merely "don't append a duplicate J block." **J already contributes to the Check 8 aggregate.** Verified live:

- `SAFEGUARD_LAYER.md:453` (aggregation rule): "two or more MAJORs … across the manuscript when Sub-check G, H, **or J** contributes = MAJOR aggregate."
- `SAFEGUARD_LAYER.md:410` (advisory scoping): the gate reads "only the **A–H** aggregate."

These contradict. J is kept out of the gate today only by its `advisory_until: J_two_revision_cycles` flag — a transitional gate, not a structural exclusion. On flag retirement, a verdict-overclaim would fire `E-Ph3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF`. This confirms the category error is **latent-live**, and the de-aggregation is a structural edit to the aggregation rule, the J severity floor (`:404–406`), and the output format (`:447–453`) — not a cosmetic retitle. Directive J below reflects this.

---

## 1. Validation of Codex's eight revisions

| # | Codex revision | Verdict | Supervisor note |
|---|---|---|---|
| 1 | ADR status → `Proposed` | **Accept** | Correct and important; artifact fixed in the sibling file. Still needs Joseph's explicit sign-off (see §4). |
| 2 | Split `current_severity` / `persistence_state`; persistence must not rewrite semantic severity | **Accept — this is better than my draft** | My "+1 level per round, cap BLOCKER" conflated two orthogonal axes. Reinforcement below: persistence keys on **current content hash**, not round count. |
| 3 | >300 = MAJOR floor + mandatory split; BLOCKER only with no meaningful turn-point/break structure; calibrate 300 before 350 | **Accept with one tightening** | More faithful to §13.1 than my unconditional BLOCKER. Requires a deterministic definition of "meaningful structure" so BLOCKER stays reproducible (below). |
| 4 | Remove categorical C-8 carve-outs | **Accept — and relocate, don't just delete** | Correct: anaphora/cadential verdicts are not auto-turn-points. But the C-8 *protection* still has to live somewhere — it belongs on Sub-check B / sentence-level-pass, not on A. Directive below. |
| 5 | No self-hashing profile | **Accept** | Store hash externally (phase_state + F9/M3 evidence); do not rely on field-exclusion canonicalization. Matches Task 4A Steps 4/7. |
| 6 | Separate phase enum from passage-role | **Accept** | `binds_at:["Ph3","Ph4"]` + `ph2_role_overrides.orienting_clause:"blocker_candidate"`. Clean. |
| 7 | Edit the existing J block in place; don't call it a "Sub-check" while excluding it | **Accept — larger than stated** | See §0: also edit the aggregation rule and resolve the 410-vs-453 contradiction. |
| 8 | Remove all stubs before treating JSON as drop-in | **Accept with sequencing note** | The stubs map to reqs 3/4/5, each a substantial subtask. Assemble the complete profile; do not mark it schema-valid or `1.0.0` until stub-free. |

I found nothing to reject. Points 2, 3, and 4 are genuine improvements on my draft; 5, 6, 7 are correctness/hygiene fixes; 1 and 8 are discipline.

---

## 2. Supervisor refinements (additive — implement alongside the accepted points)

**R-a — Persistence keys on content hash.** `persistence_state` counts consecutive review rounds in which the **same finding on unchanged paragraph text (same current hash)** remains unresolved. Any edit to the paragraph resets it to 0. This ties persistence to the milestone framework's current-hash evidence continuity (M4/M5) rather than to a bare round counter, and prevents a cosmetically-touched paragraph from carrying stale persistence.

**R-b — Persistence gates workflow, never severity.** A persistence threshold may raise remediation priority and, past a defined bound after an *approved* revision round, let the **Planner** escalate to workflow-blocking via a separate, logged trigger. It must not mutate the recorded `current_severity`. The audit trail shows a MINOR finding plus an explicit Planner escalation event — not a MINOR silently rewritten to BLOCKER.

**R-c — Turn-point detection is candidate-then-verdict, mirroring the >200 split.** The cue lexicon is deterministic **candidate generation**; the overlay confirms the cue **functionally** performs a transition, counter-move, worked example, or thematic refocus before it counts. This unifies points 3 and 4 under one principle already adopted for >200 paragraphs, and it is where point 4 lands: C-8 M-4/M-5 features count as turn-points only when they functionally do so.

**R-d — Relocate the C-8 protection to Sub-check B / sentence-level-pass.** Per `STYLE_COMMITMENTS.md:72`, the C-8 carve-out protects M-4 anaphora and M-5 cadential verdicts from being flagged as *monotony/rhythm* defects. Its correct home is Sub-check B (rhythm) and `sentence-level-pass` as a do-not-flag guard, not Sub-check A as a turn-point credit. Remove `thresholds.cadence.carve_outs`; add the guard under B's spec.

---

## 3. Revised directives for Codex (implement; I will review, not author)

**D-1 (cadence severity model).** Replace `base_severity` + `recurrence_escalation` with two orthogonal fields:
- `current_severity` from the present paragraph only:
  - 151–200 with fewer than 1 functional turn-point → MINOR
  - 201–300 with fewer than 2 functional turn-points → MAJOR
  - > `hard_ceiling_words` (default 300) → MAJOR **and** `mandatory_split: true` (always at least MAJOR)
  - > `hard_ceiling_words` **and** no meaningful structure → BLOCKER, where **"no meaningful structure" is operationalized deterministically as: zero functional turn-points AND zero internal sentence-break signals (em-dash / colon / semicolon)**. This keeps the wall-of-prose BLOCKER reproducible.
- `persistence_state` per R-a/R-b (content-hash round count; workflow escalation only).

**D-2 (turn-points).** Encode the lexicon as `candidate` semantics and require overlay functional confirmation for the verdict (R-c). Do not auto-credit any construct type.

**D-3 (C-8).** Remove `carve_outs` from cadence; add the M-4/M-5 do-not-flag guard to Sub-check B and `sentence-level-pass` (R-d).

**D-4 (hash).** Remove `canonical_sha256` from the profile body. Compute over the whole file; store in `phase_state.json.milestone_framework.policy_bindings.reader_accessibility` and in M3/F9 evidence; `MF-POLICY` compares stored vs recomputed.

**D-5 (phase/role).** `sub_checks.H`: `binds_at:["Ph3","Ph4"]`, `advisory_at:["Ph2"]`, `ph2_role_overrides:{"orienting_clause":"blocker_candidate"}`. No role tokens in any phase enum.

**D-6 (J de-aggregation — structural).** (a) Retitle the existing `SAFEGUARD_LAYER.md:384` block from "Sub-check J" to an adjacent-advisory id that carries no letter-series membership (e.g., **"Check-8-Adjacent — Verdict-Edge Discipline (VE)"**). (b) Edit the aggregation rule at `:453` to remove "or J." (c) Resolve the `:410`↔`:453` contradiction so both say VE is outside the A–H aggregate and outside the gate regardless of advisory state. (d) Fix the severity floor (`:404–406`) and output format (`:447–453`) accordingly. (e) Overlay + `evaluator.md` state "Check 8 = A–H; VE is an adjacent advisory." (f) Profile: `adjacent_advisory_checks.VE` with `gate_contribution:"none"`; route findings to Reflector Phase 2g only. (g) Keep the follow-up to relocate VE to a C-8/M-6 verdict-calibration home.

**D-7 (no stubs).** Populate lexicons / domain-token / remediation-ordering (reqs 3/4/5) into the profile before it is schema-valid; version stays `1.0.0-draft` until stub-free.

**D-8 (single-source parity).** Every prose surface cites profile keys; `reader_accessibility_contract_smoketest.py` fails on any numeric restated outside the profile (Task 4A Step 5).

---

## 4. Sequencing and the one open human decision

Codex's ask is right: **schema and profile should be reviewed together** because points 2, 3, 5, 6 are structural. Proposed order:

1. Codex implements D-1…D-8 in the profile + prose surfaces and drafts `reader_accessibility_profile.schema.json` to match.
2. Cowork (me) reviews the assembled schema + profile jointly as second opinion, and drafts any schema-fragment corrections at that point — not before, so I'm reviewing the real shape rather than a scaffold.
3. `MF-POLICY` + contract-parity + the Step-1 case list must pass before release.

**Open decision that only Joseph can make** (this is what keeps ADR-ACCESS-01 from repeating the provenance error): explicit endorsement of the banded cadence rule and the `hard_ceiling_words: 300` provisional default. My recommendation is to accept the bands and keep 300 as a *provisional* default flagged for calibration against real manuscripts before any move to 350. On your word, ADR-ACCESS-01 moves Proposed → Accepted with real provenance; until then it stays Proposed and Codex implements against it as provisional.
