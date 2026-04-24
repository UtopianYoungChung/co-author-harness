# Handoff: v0.8.0 Plugin Build — Commence Phase 3

## Session Metadata
- Created: 2026-04-23 00:04:39
- Project: research-writing-harness (plugin: `research-writing-harness-claude`)
- Workspace roots: `Ph.D. Research/` (portfolio), `research-writing-harness/` (harness)
- Wip0 substrate: `research-writing-harness/unpacked/research-writing-harness-claude-v0.8.0/`
- Session duration: ~2 hours (architecture review + build plan + two rounds of advisor feedback)

## Handoff Chain

- **Continues from**: None (first build-plan session; architecture authored across r1–r20 in prior sessions)
- **Supersedes**: None

> This is the first handoff for the v0.8.0 build execution. Prior work is documented in the upgrade architecture at `proposals/v0.8.0_upgrade_architecture.md` (r20).

## Current State Summary

The `research-writing-harness-claude` plugin is being upgraded from v0.7.4.1 to v0.8.0 as a single composed release. Phases 0, 1, and the entire Phase 2 (P2.1a through P2.8, 14 sub-phases) are **closed** on the wip0 substrate. Phase 3.1 is **partially landed** (Ph-native pointer demotion on `agents/evaluator.md`, but three post-apply verification items remain open). A model-tiered build plan was authored, reviewed by two rounds of advisor feedback, and corrected to r3. The next session should commence Phase 3 execution starting with the P3.1 verification closure.

## Codebase Understanding

### Architecture Overview

The plugin implements a **four-agent AORE harness** (Planner / Evaluator / Generator / Reflector) over a **Lifecycle-Phase Ladder** (Ph1 Plan & Draft → Ph2 Review & Revise → Ph3 Iterate & Converge → Ph4 Finalize & Close). v0.8.0 adds: Ph3 refinement profiles (refine / structural / deep), diff-scoped Evaluator with context halo, paragraph-hash verdict carryover cache, multi-signal convergence vector, and a pre-MCR Ph3-deep safety net.

The upgrade architecture (`proposals/v0.8.0_upgrade_architecture.md` r20) defines an eight-phase authoring order. Five architectural layers compose into a single release:
- L0 Hygiene (γ, closed at v0.7.4.1)
- L1 Instrumentation (α Tiers A+B, closed at Phase 1)
- L3 Ph3/Ph4 redesign (β core, closed at Phase 2)
- L2 Token pruning (α Tiers C1+C2+D, **in progress** — Phase 3)
- L4 Pulled-forward (β P-14 cache, Phase 4)

### Critical Files

| File | Purpose | Relevance |
|------|---------|-----------|
| `proposals/v0.8.0_upgrade_architecture.md` | **Binding architecture** (r20). Read §9 for entry point, §9.2 for closure log, §3.2 for authoring order | The authoritative plan; every session reads this first |
| `proposals/v0.8.0_build_plan.md` | **Model-tiered build plan** (r3). Session structure, model assignments, cost projections | Execution guide for remaining sessions |
| `proposals/v0.8.0_architecture_review_findings.md` | Architecture review with 7 findings (F-1 through F-7) | Residuals and risks to track |
| `unpacked/research-writing-harness-claude-v0.8.0/` | **Wip0 authoring substrate** (D-8). All edits land here | The tree the release-gate runs against |
| `unpacked/.../agents/evaluator.md` | 254 lines; Phase 3.1 pointer demotion **partially landed** (r20) | Next: verify token reduction, Regression Guard, paired review |
| `unpacked/.../skills/run-phase-{3,3-stability,4}/SKILL.md` | Three Phase 3 target skills (549 lines combined) | Phase 3.2 envelope factorisation target |
| `unpacked/.../scripts/sk20_overlay_run.py` | 404 lines, CC=48 | Phase 3.3 refactoring target (CC→≤15) |
| `unpacked/.../scripts/release-gate.sh` | 746 lines; current verdict: **4 blockers, 8 warnings** | Verification oracle |
| `proposals/drafts/v0.7.6_hand_authored_route/` | Draft diff (129 lines) + README (98 lines) + plugin-efficiency.json.draft | P3.1 intent spec (diff not applied raw — Ph-native adaptation used instead) |

### Key Patterns Discovered

**Sub-phase closure pattern (from n=17 sample):** Every sub-phase follows: scope applied → verification evidence (grounded) → residuals surfaced (out-of-scope, flagged). Verification runs `skill-check.py` + `release-gate.sh` and confirms blocker count unchanged. This pattern should continue through Phase 3–5.

**Substrate inconsistency pattern:** Twice during Phase 2 (R-P0-SCHEMA-3, R-P2-VALIDATOR-F6), a pre-existing v0.7.4 inconsistency surfaced during a sub-phase pre-flight audit. The remedy was to nest a dedicated reconciliation sub-phase (P0.1a, P2.1a.1) before the additive work touched the same surface. Be alert for this pattern recurring at Phase 3 entry.

**Model assignment taxonomy:** Three profiles — Mechanical (Haiku 4.5), Schema/Script/Doc-alignment (Sonnet 4.6), Prompt engineering/Governance rewrite (Opus 4.7). Decision tree in build plan §5.

## Work Completed

### Tasks Finished

- [x] Architecture review of v0.8.0 upgrade architecture (r18 → found 7 findings, filed at `proposals/v0.8.0_architecture_review_findings.md`)
- [x] Effort estimate for remaining work (8–12 sessions → optimized to 6 sessions via model tiering)
- [x] Model-tiered build plan authored (`proposals/v0.8.0_build_plan.md` r1)
- [x] First advisor feedback applied (7 issues: rebase on r20, n-count, P3.1 Ph-native rewrite, 5.H1 scoping, P2.8b model, calendar risk, fixture finding)
- [x] Second advisor feedback applied (4 copy-edits: §3.2 cost reconciliation, §6 "12"→"17", Sonnet n=7→8, fixture repro steps)

### Files Created

| File | Purpose |
|------|---------|
| `proposals/v0.8.0_architecture_review_findings.md` | 7 findings from architecture review |
| `proposals/v0.8.0_build_plan.md` (r3) | Model-tiered build plan, advisor-reviewed |

### Decisions Made

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Model tiering for remaining work | All-Opus (~$20) vs tiered (~$4.70) | n=17 taxonomy shows only 6/17 sub-phases needed Opus; 70% cost savings |
| P3.1 is verify+sign-off, not re-apply | Re-apply diff vs verify existing Ph-native land | r20 already landed a Ph-native adaptation; the Tier-targeted diff cannot be applied raw |
| 5.H1 is rename-only | Rename + clause (f) implementation vs rename-only | Clause (f) implementation is separate scope; Planner prompt-level enforcement is the binding gate |
| Fixture repair is Session D first item | Repair immediately vs defer to Phase 5 | Release-gate is lying (4 blockers, should be 2); all verification depends on honest gate output |
| Separate days for Sessions A and B | Same-day vs separate days | Both carry paired-review gates; context-window pressure + cognitive fatigue risk |

## Pending Work

### Immediate Next Steps

1. **Repair truncated fixtures** — Both `scripts/fixtures/phase_state_smoketest/{pass,block}/reviews/phase_state.json` on wip0 are truncated at line 50 (`model_used` has no value, JSON unclosed). Complete with `null` per absent-means-null semantics, close the JSON structure. Verify release-gate drops from 4 to 2 blockers. **Model: Haiku 4.5.**

2. **Close P3.1 verification (Session A)** — Three items remain per r20:
   - V1: Run `audit-package-economics` on wip0; confirm ~3.2–3.4k token reduction on `agents/evaluator.md` (Haiku)
   - V2: Capture SAFEGUARD Check 1 (Regression Guard) CLEAN on a post-demotion Evaluator round (Sonnet)
   - V3: Paired review — confirm Ph-native pointer table + four call-outs preserve draft README's 14 binding rules (Opus 4.7)

3. **Execute Phase 3.2 (Session B)** — Author `references/PHASE3_PHASE4_COMMON_ENVELOPE.md` (~120 lines); rewrite three SKILL files to pointer + differentiators; paired review of envelope in isolation. **Model: Opus 4.7 (lead) + Sonnet 4.6.**

### Blockers/Open Questions

- [ ] Fixture truncation (blocks honest release-gate verification)
- [ ] `audit-package-speed` invocation fails with rc=2 in this environment (WARN-degradation, not blocking — but Phase 5.4 calibrator probe needs a working calibrator)
- [ ] P3.1 paired review requires user availability

### Deferred Items

- Phase 4 (P-14 verdict cache) — independent of Phase 3; can run in parallel with Sessions A/B
- Phase 5 hygiene items: `pre_tier_advance_check.py` rename, `AGENT_ORCHESTRATION.md` vocab sweep (~40 strings), SKILL description trimming, `halo_scope` matrix pinning, `TIER_PROTOCOL_SR.mermaid` fix
- Clause (f) `E-MCR-PRE-DEEP-PASS-REQUIRED` implementation in `pre_phase_advance_check.py` — v0.8.1 scope unless pulled in
- INF3001H replication for empirical falsification (D-5) — post-ship, v0.8.1

## Context for Resuming Agent

### Important Context

1. **Read order for every session:** `Ph.D. Research/CLAUDE.md` → `research-writing-harness/CLAUDE.md` → `proposals/v0.8.0_upgrade_architecture.md` §9 (entry point) → `proposals/v0.8.0_build_plan.md` (model assignments).

2. **The architecture doc (r20) is binding; the build plan (r3) is advisory.** If they conflict, the architecture wins. The build plan adds model-tier assignments and session structure that the architecture does not specify.

3. **The draft diff at `proposals/drafts/v0.7.6_hand_authored_route/evaluator.md.pointer-demotion.diff` was NOT applied as a raw patch.** The r20 session authored a Ph-native adaptation because the diff targets Tier/`TIER_PROTOCOL` vocabulary incompatible with wip0's Ph/`PHASE_PROTOCOL` surface. The diff serves as intent specification only. The README's 14-binding checklist IS still the verification baseline for the paired review.

4. **P2.8 falsification table dispositions:** All 11 rows `retained in Ph4-deep`. Row 11 carries a confessed coverage gap with a v0.7.6 lightweight-proxy milestone. This means the Ph3-refine check surface is NOT widened by P2.8 — all deferred checks stay in Ph4-deep.

5. **Release-gate state on wip0 (as of this session):** 4 blockers (2 fixture truncation + 1 description length + 1 version-check), 8 warnings (7 SKILL description lengths + 1 audit-package-speed failure). Target at ship: 0 blockers.

6. **Model assignment decision tree:** (a) Verifiable by grep/validator → Haiku 4.5; (b) Target fully specified by existing schema/proposal/diff → Sonnet 4.6; (c) Requires holding 2+ contract surfaces + semantic judgment → Opus 4.7.

### Assumptions Made

- The wip0 substrate at `unpacked/research-writing-harness-claude-v0.8.0/` is the canonical build surface (per D-8)
- The workspace-root `research-writing-harness/` tree is NOT the build surface (it is stale at `plugin.json` v0.7.2)
- Model cost rates: Opus $15/$75 per Mtok in/out; Sonnet $3/$15; Haiku $1/$5
- The calibrator plugin (`plugin-calibrator`) is available for Phase 5.4 but may not be wired correctly in all environments

### Potential Gotchas

- **Fixture truncation is a file-write artifact, not an architectural issue.** The JSON files were likely truncated by a prior session that hit a context or timeout limit mid-write. The fix is mechanical (complete the `model_used: null` value, close the JSON structure), but the release-gate will report false positives until it's done.
- **`AGENT_ORCHESTRATION.md` has ~40 stale Tier-vocabulary strings.** This file was NOT a Phase 2 target. An agent reading it at runtime will encounter `current_tier` and `tier_state.json` as if they are live. Phase 5 hygiene item.
- **`pre_tier_advance_check.py` is the only advance-check script on wip0.** Multiple governance docs reference `pre_phase_advance_check.py`. Phase 5 rename.
- **The `evaluator.md.pointer-demotion.diff` targets v0.7.0 Tier vocabulary.** Do NOT apply it to the post-β wip0 evaluator. The Ph-native adaptation is already landed.
- **Session A's Opus portion is read-only verification** (lower cognitive load than Session B's multi-file extraction). If scheduling both on the same day, do A first with a cooldown before B.

## Environment State

### Tools/Services Used

- Plugin-forge skill (invoked for this session)
- Advisor MCP (`advisor:advisor`) — used for two rounds of feedback on the build plan
- `scripts/release-gate.sh` — verification oracle (runs on wip0 via bash)
- `scripts/skill-check.py` — SKILL integrity check (0 blockers, 27 skills)
- Plugin-calibrator (`audit-package-economics`, `audit-package-speed`, `audit-package-quality`) — available but `audit-package-speed` fails with rc=2 in this environment

### Active Processes

- None (all verification was run ad-hoc)

### Environment Variables

- None relevant (no API keys or secrets involved in the build process)

## Related Resources

- `proposals/v0.8.0_upgrade_architecture.md` (r20) — binding architecture
- `proposals/v0.8.0_build_plan.md` (r3) — model-tiered execution guide
- `proposals/v0.8.0_architecture_review_findings.md` — 7 findings (F-1 through F-7)
- `proposals/v0.7.5_phase3_refinement_loop_proposal.md` §3.P-9.1 — falsification table (all 11 rows disposed)
- `proposals/v0.7.6_calibrator_audit_optimization_proposal.md` — α track source
- `proposals/drafts/v0.7.6_hand_authored_route/README.md` — binding-rule checklist for P3.1 paired review
- `Ph.D. Research/CLAUDE.md` — portfolio-root governance (read every session)
- `research-writing-harness/CLAUDE.md` — harness-root governance (read every session)

---

**Security Reminder**: No secrets, API keys, or credentials are present in this handoff.
