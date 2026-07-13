# Harness Audit — Gaps, Drifts, Stales

*2026-07-13 · package v0.26.0 (tag `v0.26.0`, HEAD `f107694`) · report-only, no repo edits made.*
*Method: all 10 CLAUDE.md maintainer checks executed (all PASS), followed by a three-agent semantic sweep (vocabulary/version drift; cross-file contracts; docs/release staleness). Every finding below was verified against file content; line numbers are exact quotes.*

## Verdict

The deterministic layer is green and the version-string planes are clean — no unregistered version values anywhere. The drift that survives is exactly the kind the snapshot-mode checks cannot see: **stale counterclaims** (15/16-field, 30-trigger residue from before the v0.10.0 widenings), **one live reference file frozen two eras back** (`MODEL_ALLOCATION.md`), and **a cluster of citations to files that were moved or retired without re-pathing**. There is also uncommitted in-flight work on the pre-advance guardrail that introduces a trigger not in the canonical enum.

---

## S1 — BLOCKER: contradictions on live contract surfaces

Canonical facts (per `references/phase_state_schema.md` and the `version_planes.json` registry): **18-field** SectionStateObject, **31-trigger** enum, **7-field** log row, ledger `reviews/phase_state.json`.

| # | Surface | Evidence | Drift |
|---|---------|----------|-------|
| 1.1 | `references/CLAUDE.md:9` | "15-field `SectionStateObject`, 7-field log row, 30-trigger enum" | 15≠18, 30≠31 on the package invocation-rules line |
| 1.2 | `references/MODEL_ALLOCATION.md` (whole file) | `:3` "Lifecycle-**Stage** Ladder… At v0.7.4 the tier identifiers **will** rename to Ph1–Ph4" (future-tense, shipped long ago); `:55,:63,:69` instruct reads/writes of retired `reviews/tier_state.json` (`log[].notes` override logging) | File is frozen at v0.7.3 tier vocabulary yet is read by the Planner **at every dispatch** (`agents/planner.md:48`). Single most drifted live surface. |
| 1.3 | `agents/planner.md` (internal fork) | `:4` and `:59` say 18-field; `:35` and `:46` say "16-field"; `:132` says "30-trigger active enum"; `:528` "sixteen-field" | Self-contradicting sole-writer contract |
| 1.4 | `references/AGENT_ORCHESTRATION.md` | 16-field at `:23,:163,:438,:451` ("sixteen canonical fields… six v0.7.0+ additions" — omits the two v0.10.0 snowball fields `references_initialized`, `last_coverage_score`); 30-trigger at `:452` ("**30 legal values**") and `:521`; while `:419` correctly says 31 | The §-level ledger description never absorbed the v0.10.0 S2/S4 widenings |
| 1.5 | Reflector write target mis-pathed | `AGENT_CONTRACTS.md:216`, `AGENT_ORCHESTRATION.md:19` (Reflector-full **writes** column), `EVAL_METHODOLOGY.md:3`, `OPERATING_MANUAL.md:193` all cite `skills/SKILL_REGISTRY.md` | File lives at `references/SKILL_REGISTRY.md`; `skills/SKILL_REGISTRY.md` does not exist — the Reflector's append target is mis-addressed in its contract |

## S2 — MAJOR: in-flight and ghost code

| # | Finding | Evidence |
|---|---------|----------|
| 2.1 | **Uncommitted migration of `scripts/pre_phase_advance_check.py`** (tier_state → phase_state). Committed version still reads retired `tier_state.json` with `SCHEMA_VERSION_EXPECTED = "0.7.0"`. Working copy: (a) hardcodes `"0.7.4"` inline, leaving the constant at `:93` dead; (b) *[corrected 2026-07-13]* trigger `ph3_iteration_round_manuscript` **is** canonical (trigger 29, v0.7.4 P-7) — the original finding here was wrong; the real gap is that `VALID_TRIGGERS` was still the tier-era enum and was missing canonical triggers 28 (`ph3_accessibility_blocker_surfaced`) and 30 (`stability_mode_escalated_to_full_ph3`); trigger 13 is deliberately excluded (retired v0.11.0 with the SD/SR cut, documented in-file). Resolved in fix commit C1. | `git status`; `git diff scripts/pre_phase_advance_check.py`; `phase_state_schema.md §3.1` |
| 2.2 | **Orphan smoketest.** `scripts/pre_phase_advance_phase_state_smoketest.py` is untracked and wired nowhere — not in `release-gate.sh`, not in CI, not in any doc. Every other smoketest is gate- or CI-wired. | `git status`; grep of `release-gate.sh`, `.github/workflows/` |
| 2.3 | *[withdrawn 2026-07-13]* `scripts/run-evaluator-preflight.ps1` is **not** a ghost: `PROJECT_BOOTSTRAP.md §2.11` defines it as a per-project seed script (marked `[seed]` in the bootstrap tree) materialized in the user's project at bootstrap — like `references/REFERENCES.md`, it is expected-absent from the plugin package. No fix needed. | `PROJECT_BOOTSTRAP.md:46,:404` |
| 2.4 | **Retired skill cited as live.** `eygp-framework-checker` (SK-28, retired v0.7.0 per `SKILL_REGISTRY.md:544`) still cited as active at `DETERMINISTIC_CHECKS.md:248` and `GROUND_TRUTH.md:196`; `GROUND_TRUTH.md:205` also uses defunct `skills/packaged/p-stage-checker.md` (actual: `skills/p-stage-checker/SKILL.md`). | paths absent |
| 2.5 | **Phantom `legacy/` archive.** No `legacy/` directory exists, but `AGENT_ORCHESTRATION.md:516` ("preserved under `legacy/marshal-f1-retired/`" + six named files) and `PHASE_PROTOCOL.md:766` ("archived under `legacy/rule-digest-v060-retired/`") claim it does. `phase_state_schema.md:249` claims `scripts/tier_state_canonicalize.py` is "retained… as a stable-import contract" — it is absent. | `ls legacy` fails |
| 2.6 | **Unannotated retired-script citations.** Retired migration scripts presented as runnable without the `[retired from tree]` tag used elsewhere: `PHASE_PROTOCOL.md:120,:234`, `PHASE3_PHASE4_COMMON_ENVELOPE.md:42`, `TIER_PROTOCOL.md:32`, `ARTEFACT_FRONTMATTER_SCHEMA.md:436`, `AGENT_ORCHESTRATION.md:29`. | scripts absent |

## S3 — MAJOR: documentation-tier stale counts

| # | Surface | Evidence |
|---|---------|----------|
| 3.1 | `docs/agent-instructions/harness-reference-index.md:36` | "15-field `SectionStateObject` + 30-trigger enum" |
| 3.2 | `docs/agent-instructions/harness-discovery-lifecycle.md:29,:66` | "15-field… 30-trigger"; bootstrap tree comment "15-field per-section ledger" |
| 3.3 | `docs/agent-instructions/harness-architecture.md` | `:7` stamped "v0.8.7"; `:14` pre-split four-agent list (no `reflector-probe`/`reflector-closeout`); `:16` pre-v0.16 skill surface; `:21` claims `releases/` is "tracked in git when committed" — `git check-ignore` shows the entire directory is gitignored, nothing committed |
| 3.4 | `references/SKILL_REGISTRY.md:297` | SK-25 "Depends on" still binds the **six-field `tier_entry_log`** row (`prev_tier`,`new_tier`,…) — triple drift: field count, retired log name, tier columns. The 2026-07-07 coherence audit migrated SK-25's field count but missed this clause |
| 3.5 | `references/templates/F3_reflector_lightweight_probe.md:39` | emitted-template comment "trigger outside the v0.7.4 **30-trigger** enum" |

Note: the v0.24.0 cycle's claim that count-drift was "healed everywhere" (`README.md:132`) is falsified by S1.1, S1.3–1.4, S3.1–3.2, S3.4–3.5 — the sweep covered agents/skills but not `references/CLAUDE.md`, `AGENT_ORCHESTRATION.md` deep sections, docs/agent-instructions, or templates.

## S4 — MINOR

| # | Finding |
|---|---------|
| 4.1 | `reviews/plugin_update_proposals.md`: Summary table (`:122–125`) still says A6–A9 "ADVANCED — awaiting user sign-off" while the closure section above (`:11–18`) marks them IMPLEMENTED (v0.8.4). P-R-1 targets `agents/reflector.md §Phase 2g`, a surface since split; P-R-6's premise (`terminology_register.md` absent) no longer holds — it shipped at v0.23.0. |
| 4.2 | `README.md:110–117` maintainer list has 7 scripts; `CLAUDE.md`/`AGENTS.md` list 10 (missing the three registry checks added v0.22–0.24). |
| 4.3 | Committed stale generated state: `outputs/v013_validators_output.txt` + `outputs/run_v013_validators.bat` (v0.13.0-era, 32 skills/16 commands, old root path). |
| 4.4 | `releases/`: stray temp-named zip `ziJsZwBW` (1.7 MB); packaging format flip-flops (`v0.25.0.plugin` vs `v0.26.0.zip`). Local-only (dir gitignored). |
| 4.5 | Retired T-label residue on live command surfaces: `commands/run-phase-1.md:3` and `skills/plugin-commands/SKILL.md:45,:47` ("T1 Plan & Draft", "final tier (T1–T4 / T3R)"). Labels only; no misrouting. |
| 4.6 | `.claude/worktrees/`: 8 stale gitignored worktrees flagged for manual prune since 2026-07-07 (`docs/analysis/2026-07-07_deferred-register-closure.md:24`); still unpruned. |

## S5 — Tooling gap (why this survived ten green checks)

`version-planes-check.py` is **snapshot/presence-mode**: it verifies registered assertion strings are still present; it cannot detect *unregistered stale counterclaims*. `retirement-sweep-check.py` covers 15 retired names but evidently not the stale count strings or `tier_state.json`-as-live citations in `MODEL_ALLOCATION.md` (or that file is not in its live-surface scan set). Recommendation: add a **negative-assertion sweep** — register `"15-field"`, `"16-field"`, `"sixteen canonical fields"`, `"30-trigger"`, `"30 legal values"`, `"six-field row"`, and live-voice `tier_state.json` as retired strings in `references/schemas/retired_surfaces.json` (with the existing historical carve-outs for CHANGELOG/§-history), and wire the S2.2 orphan smoketest into `release-gate.sh`.

## S6 — Environment (not in-repo)

The **advisor plugin's** PostToolUse hook fails on this Windows host: `${CLAUDE_PLUGIN_ROOT}` is not expanded, so `python "${CLAUDE_PLUGIN_ROOT}/hooks/advisor_toolsearch_guard.py"` resolves to a literal nonexistent path (observed this session on every ToolSearch call). The guard is silently dead — its enforcement (whatever it gates) is not running.

## Healthy surfaces (verified, no action)

All 10 maintainer checks PASS on the working tree · version/README/CHANGELOG/marketplace all agree at 0.26.0 · no orphan skills (41 reachable) · full command↔skill parity (22/22) · agent read/write contract paths exist (except S1.5) · `catalog-check`'s `README skills count: <missing>` is the *intended* pass state (asserted counts are the BLOCKER, per `catalog-check.py:56–70`) · deferred register (`2026-07-07_deferred-register-closure.md §Still open`) is current: the planner-vs-evaluator ladder fork remains the only tolerated vocabulary fork, correctly registered · `hooks/` empty and undeclared, as designed.

## Remediation record (2026-07-13, same day)

All findings remediated in fix commits `e043dfd` (C1 guardrail migration + smoketest wiring), `1bae8ec` (C2 count sweep), `e0cec37` (C3 MODEL_ALLOCATION re-voice), `29ec28b` (C4 ghost/retired citations), `ef1bf4d` (C5 minors), `aa7dd18` (C6 retired_phrases negative assertions per S5 + residual vocabulary), released as **v0.27.0**. Two findings were corrected during remediation and are annotated in place above: S2.1(b) (trigger 29 is canonical) and S2.3 (the `.ps1` is a per-project seed script, withdrawn). Deliberately not changed: agent-file ladder fork (registered), subagent-dispatch model pins (v0.25.0 deferral, now recorded in `MODEL_ALLOCATION.md §8`), classification's T-coded `tier:` field (live surface by design), S4.6 worktree prune (host permissions, still manual).

## Suggested remediation order

1. `MODEL_ALLOCATION.md` full re-voice to phase vocabulary + `phase_state.json` (S1.2) — it is dispatch-critical.
2. Count-string sweep across S1.1/1.3/1.4/S3 in one commit; then register the negative assertions (S5) so it cannot recur.
3. Re-path `skills/SKILL_REGISTRY.md` → `references/SKILL_REGISTRY.md` (S1.5).
4. Resolve the in-flight `pre_phase_advance_check.py` work: either add `ph3_iteration_round_manuscript` to the canonical §3.1 enum (32 values, with registry + docs updates) or drop it; restore the constant; commit; wire the smoketest into the gate (S2.1–2.2).
5. Ghost/retired citations (S2.3–2.6), then the S4 minors.
