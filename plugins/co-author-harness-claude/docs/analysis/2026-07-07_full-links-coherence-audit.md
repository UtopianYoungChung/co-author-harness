# Full-Links Coherence Audit — co-author-harness-claude

**Date:** 2026-07-07 · **Baseline:** v0.22.0 · **Ships as:** v0.23.0
**Method:** Four parallel read-only audit lanes over the complete dependency graph — Lane A (references ↔ MANIFEST ↔ consumers), Lane B (agent contracts ↔ everything they cite), Lane C (skills/commands/registries), Lane D (scripts inventory + gate/CI wiring) — followed by cross-lane conflict resolution, a mechanical remediation pass (~45 edits, every one anchor-verified before application), and a 21-check verification battery.
**Finding classes:** DANGLING (target missing) · STALE (contradicts current state) · DRIFT (two sources disagree) · ORPHAN (nothing consumes it).

---

## 1. The systemic diagnosis

Three growth patterns produced nearly all findings:

1. **The schema moved; the contracts didn't.** `phase_state_schema.md` is at 18 fields and 31 triggers; every agent file, `AGENT_CONTRACTS.md`, and the Ph1 skill asserted 16 (or 15) fields and 30 triggers — a three-way spread ({15: generator, run-phase-1}, {16: planner, evaluator, reflector-closeout, contracts}, {18: schema}). The v0.22.0 version-planes registry guarded version *strings* but not derived *counts*; counts are now candidates for the same registry treatment (§4).
2. **Retirement leaves residue.** ~15 dangling `scripts/*.py` citations in live protocol files are retired-to-legacy scripts still cited at live paths; the reflector split (PR-4c) left `AGENT_ORCHESTRATION.md` and `evaluator.md` pointing into the emptied router; `REVIEW_ORCHESTRATION.md` still speaks Tier vocabulary as current. The release-gate header's own deferred gap — a retirement-sweep check — is precisely the missing enforcement.
3. **The alarm covered a ninth of the gate.** CI ran 9 checks; the gate runs ~25. The workflow header claimed "same check set" — false, now retired and corrected with an honest-scope note.

## 2. Fixed this cycle (mechanical, anchor-verified)

**Counts and shapes (Lane B B1–B3, B11, B12; Lane C M-1).** 30→31 trigger enum (planner ×4, evaluator, reflector-probe, AGENT_ORCHESTRATION ×2); 15/16→18-field SectionStateObject (planner ×5, evaluator, generator — also §5→§2 locator fix, reflector-closeout, AGENT_CONTRACTS, run-phase-1 SKILL ×2, run-phase-1 command shim, plugin-commands catalog); planner Phase-0 row-shape 6→7 fields adding `model_used`.

**Retired-concept leakage (B4).** `planner.md:277` "Rule 1 digest exception applies at Ph1 only" → retired-at-v0.7.4 language, ending the planner-vs-generator/evaluator contradiction on Ph1 read discipline.

**Dangling instructions (B5, B6; Lane D #20).** `generator.md:185` no longer imperatively "Run"s a deleted script (manual canonicalization with historical note); `phase_state_schema.md:314` migrate instruction converted to historical record; `MODEL_ALLOCATION.md` phantom `migrate_v073_to_v074.py` annotated retired, and its `CLAUDE.md §5`→`§4` precedence citation corrected.

**Reflector-split fallout (B7–B9, B13).** `evaluator.md` Phase 2f/2g.3 anchors → `reflector-probe.md`/`reflector-closeout.md`; `AGENT_ORCHESTRATION.md` Phase 2b anchor and §Phase 3.5 pointer → `reflector-closeout.md`; flat `skills/promote-lessons-to-wiki.md` path → directory form; agent-registry row now names both split files.

**Vocabulary forks (C-1, C-3, C-4).** `run-iterate` shim rewritten to agree with its skill that run-iterate is the canonical surface (the description enrichment tripped the shim-prefix-of-catalog invariant and a YAML-colon parse error — both caught by `end_to_end_smoketest.py` and `catalog-check.py`, fixed, and the catalog row synchronized); v0.7.0 ladder assertions in run-phase-1/plugin-commands/classify-manuscript → v0.8.0 (matching PHASE_PROTOCOL's canonical claim; agent-file fork untouched per snapshot policy); the 0.15.0-pre↔0.15.1 stage×profile fork **recorded** in `version_planes.json` (allowed values widened, run-iterate assertion registered) rather than silently tolerated.

**SKILL_REGISTRY current-claim rows (R-1, R-2).** Eight tier-era dependency claims in SK-25/26/27/29 rows migrated: `tier_state.json`→`phase_state.json`, `TIER_PROTOCOL §3 (T-x)`→`PHASE_PROTOCOL §3 (Ph-x)`, 15→18-field. (Historical source notes under the §74 carve-out left untouched.)

**MANIFEST (Lane A #1–3).** False "every reference file" completeness claim softened to an honest index claim; rows added for `schemas/f7_evidence_packet.schema.json`, `VERDICT_CACHE_CONTRACT.md` (with unwired-status note), and `_snippets/reflection-grounding.md`.

**`terminology_register.md` created (Lane A dangling #2).** Three live files (two Check-8 sub-check sources) cited a file that never existed; it now exists as an explicit empty register with a fall-through contract ("register empty" = advisory, not error).

**Scripts hygiene (Lane D #5–8).** Four committed output dumps (`catalog_check_output.txt`, `path_hygiene_output.txt`, `skill_check_output.txt`, `scripts/audit/reviews/findings.json`) — two embedding stale maintainer-local paths from the *old* repo root — moved to gitignored `scratch/audit-dumps/`.

**CI expansion (Lane D #14–16, #2, #3).** CI grows from 9 to 21 checks: + grounding_anchors, manifest_links, manifest-coherence, ssot, alias_parity, stage-profile smoketest, MCR-evidence smoketest, token_budget (with tiktoken), reflector_split_parity, **d_style_profile_smoketest and end_to_end_smoketest (both previously orphaned — the latter caught two real regressions during this very cycle)**, and the three test suites. Header comment now states the honest CI ⊂ gate scope and names what stays gate-only (packaging + fixture-argument validators).

## 3. Verified clean (so future audits skip it)

All 22 command shims map to existing skills; all alias routing targets exist; every `scripts/*.py` named in CLAUDE.md/AGENTS.md/README/agents/skills exists (dangling citations were confined to `references/`); all agent-cited section anchors in PHASE_PROTOCOL/AGENT_ORCHESTRATION/phase_state_schema resolve; the reflection-grounding snippet is included by both split reflectors; `run_all.py`'s dispatch modules all exist and `--project-root` behavior matches the quick-deterministic SKILL; release-gate references no missing files; the precedence ladders of root and references CLAUDE.md are consistent. Cross-lane conflict resolved: `VERDICT_CACHE_CONTRACT.md` is consumed only by stale gitignored `.claude/worktrees/` leftovers — treated as unwired and MANIFEST-flagged, not deleted (P-14 design intent may still land).

## 4. Open items — judgment, not mechanics (priority order)

1. **`REVIEW_ORCHESTRATION.md` §§88–100 rewrite** (Lane A top finding): the always-read-first review runbook still speaks `tier:`/`tier_state.json`/T4 as current. Needs a full vocabulary migration or a SKILL_REGISTRY-style historical carve-out — content rewrite, not string swap.
2. **`AGENT_CONTRACTS.md §2` Evaluator contract** (B14, B15): pre-ladder pipeline (M1–M5 phases, quick/standard/submission-bound depths, F1-as-routine); needs reconciliation with the F7-native evaluator. §2 output list vs §Output-economy internal contradiction included.
3. **T3R ontology decision** (C-2): registry says retired-folded-into-Ph3; `run-phase-3` §184 and `response-letter-review` say live independent sibling. Owner call required; whichever loses gets the carve-out treatment.
4. **Retirement-sweep check** — the enforcement for pattern #2; remaining residue: `GROUNDING_PROTOCOL.md` digest-script mentions, `AGENT_ORCHESTRATION.md:516` marshal-script list + nonexistent `legacy/` redirect, remaining migrator citations in PHASE_PROTOCOL/phase_state_schema/tier_notifications, `check_citation_order.py` (never existed) in the CAiSE walkthrough.
5. **Count assertions into the registry**: field/trigger counts fixed today can drift again tomorrow; register "18-field"/"31-trigger" as version-plane-style assertions (schema file as authority).
6. **Truncated UUID namespaces** in `seed-snowball-discovery` (`mcp__70599628-...__semanticSearch`) and host-pinned UUIDs in `tool-contract-roundtrip` — replace with symbolic names + resolution instruction (T-1, T-2).
7. **Orphan disposition**: `protocol_constants.py` (documented-broken calibrator consumer), `M1_M2_M3_PLANNING_PHASE_README.md`, operationally-unreachable-but-"binding" `GROUND_TRUTH.md`, `fixtures/convergence_journal_smoketest/` (consumer retired), `extract_pdf_comments.py` (kept: user tooling); 8 stale `.claude/worktrees/` (gitignored; safe to prune).
8. **Two packaging code paths** (`release-gate.sh` inline zip vs `build-release-zip.sh`) can drift; pick one.
9. **PHASE_PROTOCOL §2.2 numbering gap**; "Lifecycle-Stage" vs "Lifecycle-Phase" naming split inside PHASE_PROTOCOL itself; `phase_notifications_loader.py` has no smoketest; quick-deterministic SKILL should state the citations-not-included coverage seam and the no-default-target behavior (Lane D #11, #12).

## 5. Verification

21/21 checks pass post-remediation (9 structural + registry, 9 coherence/contract incl. the two newly un-orphaned smoketests, 3 test suites). Two regressions introduced *during* remediation were caught by the machinery itself (end_to_end prefix invariant; YAML colon) — the audit's clearest evidence that wiring orphaned checks into CI pays.
