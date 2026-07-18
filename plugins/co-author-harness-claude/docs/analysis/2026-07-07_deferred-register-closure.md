# Deferred-Register Closure — the nine §4 items, linked

**Date:** 2026-07-07 · **Baseline:** v0.23.0 · **Ships as:** v0.24.0
**Charter:** close every item in `2026-07-07_full-links-coherence-audit.md §4`, linked by the package's core promise: *one phase ladder, one vocabulary, one authority per fact, every authority checked*.

## The linkage

The nine items are one program in four movements. **Complete the migration** (items 1–3): the last three surfaces still speaking tier-as-current — the review runbook, the Evaluator contract, and the T3R fork — are now phase-native, so no reader can enter the package through a door that leads to the retired building. **Enforce it** (items 4–5): the retirement-sweep check makes the *next* incomplete migration a blocker instead of an audit finding, and the count planes make the *next* schema advance that outruns its contracts a blocker instead of a three-way drift. **Make contracts portable** (item 6): host-specific UUID namespaces are now explicitly non-contract. **Remove what feeds nothing** (items 7–9): every remaining orphan is either wired, honestly labeled, or quarantined. Each movement feeds the next: migration makes enforcement possible (a sweep over half-migrated vocabulary would drown), enforcement keeps migration complete, and the orphan pass is what enforcement finds when there's nothing left to catch.

## Item-by-item disposition

**1. REVIEW_ORCHESTRATION.md §3.3 — REWRITTEN.** Phase-native throughout: `phase_state.json`, `current_phase` legal set `{Ph1, Ph2, Ph3, Ph3_converged, Ph4, ceiling_locked}`, 18-field invariant, `PHASE_PROTOCOL.md` authority, schema-verified trigger/field spellings (`ph1_draft_completion_signed`, `eg1_ph4_downgrade_to_ph3`, `terminal_phase_reached`, `[Ph3-STALE]`). Stable identifiers (`E-PSTAGE-REQUIRED-AT-T2`, `W-T3-DRIFT-EXCEEDED-TOLERANT`, `/t3-reengage`) deliberately keep historical spellings — they are codes, not vocabulary — each annotated. The stale Ph1 digest-exception claim (same leak as planner.md's) replaced with retired-at-v0.7.4 language; the v0.6→v0.7 migration paragraph reframed as historical record.

**2. AGENT_CONTRACTS.md §2 — RECONCILED.** Preconditions now phase-gated (Ph2+ engagement, dormant Ph1) with the milestone formulation explicitly marked retired; outputs F7-evidence-packet-default / F1-exception (resolving the §2-vs-§Output-economy internal contradiction); depth names (`quick`/`standard`/`submission-bound`) mapped to the F6 `check_profile` envelopes with `submission-bound ≙ Ph4`; I-Refl-3 renumbered to the split reflectors' actual Phase 2.5/2.6.

**3. T3R — DECIDED: retired as an independent sibling.** Ruling authority: the SKILL_REGISTRY v0.14.0 retirement banner (newest declaration). Response-letter review is a **manuscript-class within Ph3**; `T3R` survives only as the entry point's historical label. Encoded in `run-phase-3/SKILL.md §11`, `response-letter-review` frontmatter (legacy `tier=T3R` records still route), and REVIEW_ORCHESTRATION's table row.

**4. Retirement sweep — BUILT AND WIRED.** `references/schemas/retired_surfaces.json` (15 retired scripts with provenance: retirement version, successor) + `scripts/retirement-sweep-check.py`: on live surfaces, every `scripts/*` citation must resolve or carry a historical marker; unregistered missing names are unknown danglers and always block. First run found 24 violations, zero unknown; all annotated `[retired from tree]` in place (YAML catalogs re-validated post-edit). Wired into release-gate Phase 0.55, CI, both maintainer blocks, MANIFEST. The release-gate header's oldest deferred gap is closed.

**5. Count planes — REGISTERED.** `section_state_field_count` (18; authority `phase_state_schema.md`) and `trigger_enum_count` (31) added to `version_planes.json` with widening patterns over `\d+-field` / `\d+-trigger` forms. The class of drift that dominated the coherence audit is now a check failure at introduction time.

**6. MCP namespaces — MADE SYMBOLIC.** `seed-snowball-discovery`'s truncated-UUID literals replaced with symbolic tool identities + resolve-at-session-start instruction; `tool-contract-roundtrip`'s recorded UUIDs relabeled as observed per-host examples with an explicit do-not-copy warning — the skill no longer exhibits the defect it detects.

**7. Orphans — DISPOSED.** `GROUND_TRUTH.md`: now operationally reachable — classify-manuscript's P-stage row routes to it as the binding stage-vocabulary source (it was "binding" but unrouted). `M1_M2_M3_PLANNING_PHASE_README.md`: MANIFEST row marked historical/ancestry. `protocol_constants.py`: header now documents the known calibrator pickup failure. `fixtures/convergence_journal_smoketest/`: quarantined to `scratch/` (consumer retired). `.claude/worktrees/` (8 stale, gitignored): host file permissions block programmatic deletion — **manual prune recommended**. `extract_pdf_comments.py`: retained deliberately (user tooling).

**8. Packaging — CANONICALIZED.** `release-gate.sh` Phase 1 declared the canonical packaging path in `build-release-zip.sh`'s own header; the wrapper is ad-hoc-only and the gate wins on disagreement.

**9. Smalls — CLOSED.** PHASE_PROTOCOL §2.2 gap marked reserved (numbering stability preserved — no renumber, so §2.3+ citations stay valid); its one current-tense "Lifecycle-Stage" → "Lifecycle-Phase"; `phase_notifications_smoketest.py` created (37 entries validated, deprecated `tier_notifications.yaml` validated *as a forwarding stub*, loader import-checked) and wired into gate Phase 0.56 + CI; quick-deterministic SKILL now states its coverage seam (no citation audits; no default target).

## Still open, deliberately

The **agent-file ladder fork** (planner v0.8.0 vs evaluator/generator v0.7.4) remains recorded-not-harmonized in `version_planes.json` — unchanged from the v0.22.0 decision, because harmonizing edits dispatch-surface descriptions and needs a dispatch test to ride with. It is now the *only* known vocabulary fork left in the package. Also open: golden-eval baselines (two runs needed before the gate can consume them) and the context-economy trim (gated on those baselines).

## Verification

23/23 checks green (10 structural/registry including the new retirement sweep, 10 coherence/contract including the new notifications smoketest, 3 test suites). Gate bash syntax validated; both notification YAMLs re-parsed after annotation edits; CI workflow YAML validated.
