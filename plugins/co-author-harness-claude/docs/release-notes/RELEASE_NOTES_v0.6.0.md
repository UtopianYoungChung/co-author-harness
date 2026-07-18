# Release Notes — research-writing-harness-claude v0.6.0

**Release date:** 2026-04-19
**Theme:** the Progressive Approval Staircase — per-section tier ledger + four-rung monotonic advancement.
**Verdict:** CLEARED-WITH-WARNINGS (pending the one description-length blocker; all invariant and smoketest gates clean).

---

## One-paragraph summary

v0.6.0 is a protocol redesign. The v0.5.5 Incremental Tier Protocol (six modes with heterogeneous preconditions, a whole-manuscript `tier:` field, and a fifth agent — the Tier Marshal — supervising a Phase 5.5 Down/Stay/Up/Done election) is replaced by a **four-rung Progressive Approval Staircase** (T1 Draft → T2 Review → T3 Verify → T4 Ship, with T3R as the response-letter sibling and `T4_ready` as the pre-T4 marker tier), a **per-section ledger** (`reviews/tier_state.json`, single writer = Planner), and a **monotonicity invariant** that makes most of the Marshal's 24 predicates architecturally impossible to violate. The Marshal is retired; its remaining obligations absorbed into Planner Phase 0 bootstrap and the Evaluator's entry/closeout checks. Grounding Rule 1's tier-gated digest exception narrows from `{T1, T2}` to `{T1}` only, recognising that full-file reads are mandatory the moment the Evaluator joins the loop.

## Headline change — the Progressive Approval Staircase

```
   T1 Draft → T2 Review → T3 Verify → T4 Ship
                                         ▲
                                         │ (T4_ready marker; admission gated by
                                         │  the Laggard Clearance Report)
                                         │
   T3R response-letter sibling ──────────┘ (independent ladder)
```

- Each rung runs **review → plan → generate → human approval**. User approval at tier N advances the section to tier N+1 (or ceiling-locks at N if `section_ceiling_override == N`).
- **T4 admission** is not sectional: every section must reach `current_tier: T4_ready` and the **Laggard Clearance Report** (LCR, `references/TIER_PROTOCOL.md §7`) must clear before the manuscript is admitted to T4 Ship. NEW-H-7 provides a +50% iteration reserve per tier to prevent LCR stalls.
- **Monotonicity is an invariant.** `from_tier ≤ to_tier` for every ledger row, with exactly one documented exception: `trigger: retraction` (human-initiated demotion). The Evaluator enforces this at every dispatch; the validator rejects any ledger that violates it (`MONOTONICITY_VIOLATION`, `tier_state_schema.md §6`).

## What retires

- **T0 state-probe.** Merged into the Planner's session-bootstrap routine (`agents/planner.md §Phase 0`). The validator refuses `T0` in `default_final_tier` at `SCHEMA_VERSION_UNKNOWN`-adjacent codes; the migration script coerces T0 seeds to T3 with a `T0_DEFAULT_COERCED` warning.
- **Phase 5.5 Tier Close-Out** with `Down / Stay / Up / Done` elections. Advancement is now a binary user Approve/Reject per section.
- **The asymmetric-Down ratchet** (`ascent_observed` array). Monotonicity removes its referent.
- **`reviews/tier_decisions_log.md`** with the `choice` column. Replaced by `reviews/tier_state.json`'s `tier_entry_log` array, which widens the audit surface from user-election-only to every state transition (12 triggers).
- **`reviews/tier_closeout_<round>_<date>.md`** benefit-delta artefact.
- **The fifth agent — Tier Marshal** (v0.5.5 Phase F.1). All 24 predicates bound to the retired machinery above; residual obligations absorbed into Planner Phase 0 (`agents/planner.md §§Phase 0.1, 0.2`) and Evaluator entry/closeout. Archived intact under `legacy/marshal-f1-retired/`.
- **Reflector Phase 2c — Tier-decision drift audit.** Its three metrics (Systematic down-drift, Premature completion, Ratchet-suppression frequency) lose their referent under monotonicity + LCR admission + retired `tier_closeout` artefacts. Covered by Phase 2b (confirmation-failure rate) + LCR iteration-reserve monitoring.
- **`run-tier-reflex`, `run-tier-standard`, `run-tier-submission`.** Replaced by the rung-explicit `run-tier-1/2/3/4` skills.

## What is net-new

- **`reviews/tier_state.json`** — per-section ledger. Ten `SectionStateObject` fields plus `tier_entry_log` array (12-trigger enum). Single writer = Planner. Canonical schema in `references/tier_state_schema.md §§2–4`; 17 failure codes in §6.
- **Three Phase-7 scripts:**
  - `scripts/tier_state_validate.py` — read-only validator for the 17 failure codes. Exit codes map: 0 valid, 1 schema error, 2 consistency error, 3 version/migration gate, 4 bad invocation.
  - `scripts/tier_state_canonicalize.py` — three-mode LaTeX canonicalizer (`strict` / `tolerant` / `off`) with sentinel-tagged carve/uncarve for opaque environments (`verbatim`, `lstlisting`, `minted`, etc.). Public API: `canonicalize()` and `fingerprint()`.
  - `scripts/migrate_v055_to_v060.py` — one-way migrator from v0.5.5 state artefacts to the v0.6.0 ledger. Produces a three-section `reviews/migration_report_v055_to_v060.md` (Mapped rows / Warnings / User hold-point) per `tier_state_schema.md §7.3`. Integrity-gated: the Planner refuses `/review` until the user appends `user_confirmed_migration_report_at: <ISO-8601>` to `reviews/classification.md`.
- **The Laggard Clearance Report (LCR)** — pre-T4 admission gate; `TIER_PROTOCOL.md §7`. NEW-H-7 +50% iteration reserve per tier. Climb target capped at `default_final_tier` (R-02).
- **Four rung-explicit skills:** `run-tier-1`, `run-tier-2`, `run-tier-3`, `run-tier-4`. `run-tier-2` is net-new (v0.5.5 had no standalone T2 entry point).
- **Evaluator Confirmation Mode** relocates to T2 entry (was part of the retired `run-tier-reflex` mid-round check). Triggered by a prior-cycle `CLEAN` Self-T1 Verdict; otherwise the T2 pass runs full Evaluator local-scope.
- **EG-2 / EG-3 gate-semantics deltas:** EG-2 (Self-T1 verdict mismatch) is **relocated to T2 entry** (T1 has no Evaluator). EG-3 (Cross-scope reference mismatch) is **redefined** to fire when a T2 finding cites a `location:` outside the containing section.
- **`scripts/fixtures/tier_state_smoketest/`** — PASS/BLOCK fixtures exercised by `scripts/release-gate.sh` Phase 0.67.
- **`references/TIER_PROTOCOL_SR.mermaid`** — i\*-style Strategic Rationale diagram of the staircase.
- **`references/tier_notifications.yaml`** `config_version` 2.0 block.

## Breaking changes

- `plugin.json.version` → `0.6.0`; `description` rewritten for the staircase.
- `references/tier_notifications.yaml` `config_version` 1.2 → 2.0.
- `classify-manuscript` skill's `tier:` frontmatter → `default_final_tier:`, legal values `{T1, T2, T3, T4}` (plus T3R sibling). T0 seeds coerced at migration.
- Grounding Rule 1 tier-gated digest exception narrows from `{T1, T2}` to `{T1}` only (`references/GROUNDING_PROTOCOL.md §Rule 1`).
- `run-tier-reflex`, `run-tier-standard`, `run-tier-submission` slash commands removed; use `run-tier-1/2/3/4`.
- Monotonicity invariant: ledger consumers MUST treat `trigger: retraction` as the sole legal downward transition.
- Single-writer invariant on `tier_state.json`: Generator, Evaluator, and Reflector read-only. Any non-Planner write is a Reflector Category 6 violation.

## Migration

The migration is one-way (rollback requires the preserved `research-writing-harness-claude-v0.5.4/` tree). Recommended sequence:

```bash
# 1. Dry-run to inspect warnings and mapped rows without writing.
python3 scripts/migrate_v055_to_v060.py \
    --project-root <project> \
    --dry-run

# 2. Real run.
python3 scripts/migrate_v055_to_v060.py \
    --project-root <project>

# 3. Review reviews/migration_report_v055_to_v060.md (§§1–2).
# 4. Append the confirmation line to reviews/classification.md frontmatter:
#      user_confirmed_migration_report_at: 2026-04-19T00:00:00Z
# 5. Invoke /review or /review --section <path>; Planner Phase 0 clears the hold.
```

The migrator handles: T0 → T3 coercion with warning; `tier_decisions_log.md` → `tier_entry_log` replay against every discovered section; heading-path duplicate disambiguation; `choice=Up/Done` → `user_approval`, `choice=Stay` → `user_rejection`, `choice=Down` → `retraction`; retraction-lossy last-approved reset (with warning); T4 arrival migrated as `T4_ready` pending LCR clearance.

Three script exit codes to know: 1 missing inputs, 2 schema validation failure post-write, 3 output collision without `--force`, 4 bad invocation.

## Files changed (summary)

**Normative (rewritten):**
- `references/TIER_PROTOCOL.md` — full rewrite for the staircase + LCR + monotonicity.
- `references/tier_state_schema.md` — net-new canonical schema.
- `references/AGENT_ORCHESTRATION.md §§8.2a, 8.2b, 8.3` — escalation log revised, ledger section net-new, Marshal retirement recorded.
- `references/REVIEW_ORCHESTRATION.md §3` — tier-table rewritten.
- `references/GROUNDING_PROTOCOL.md §Rule 1` — digest exception narrowed.
- `references/SKILL_REGISTRY.md` — swept for v0.6.0; SK-05 `run-full-review` alias retirement preserved.
- `references/tier_notifications.yaml` — net-new v0.6.0 config block.

**Agents:**
- `agents/planner.md` — Phase 0 bootstrap expanded to absorb Marshal preflight; LCR authoring; single-writer responsibility.
- `agents/evaluator.md` — Confirmation Mode relocated to T2 entry; Step 8.5 tier-gated depth table refreshed.
- `agents/reflector.md` — Phase 2b retained; Phase 2c retired; ledger-read contract.

**Skills (new / renamed):**
- `skills/run-tier-1/SKILL.md` — net-new body; renamed from `run-tier-reflex`.
- `skills/run-tier-2/SKILL.md` — net-new skill.
- `skills/run-tier-3/SKILL.md` — net-new body; renamed from `run-tier-standard`.
- `skills/run-tier-4/SKILL.md` — net-new body; renamed from `run-tier-submission`.
- `skills/classify-manuscript/SKILL.md` — `default_final_tier:` dispatch; retired-depth read-path dropped.
- `skills/plugin-commands/SKILL.md` — command table refreshed for the four rungs.

**Scripts (new):**
- `scripts/tier_state_validate.py`
- `scripts/tier_state_canonicalize.py`
- `scripts/migrate_v055_to_v060.py`
- `scripts/fixtures/tier_state_smoketest/{pass,block}/reviews/tier_state.json`

**Scripts (retired → legacy/):**
- `scripts/marshal_preflight.py`, `marshal_postflight.py`, `_marshal_common.py`, `migrate_classification_to_tier.py`
- `scripts/fixtures/marshal_smoketest/`

**Release-gate changes:**
- `scripts/release-gate.sh` Phase 0.67 now runs `tier_state_validate.py` against the v0.6.0 smoketest fixtures (PASS exit 0 / BLOCK exit 2 = `MONOTONICITY_VIOLATION`).
- Phase 0.7 `py_compile` list updated to the three v0.6.0 scripts; Marshal entries removed.

## Known gaps (deferred)

- **README.md rewrite** — the v0.5.5 DRAFT banner remains; the full v0.6.0-oriented rewrite ships alongside these notes in this release but is listed here as a deferred-drift candidate for the next minor version.
- **Description-length blocker.** `plugin.json.description` is 397 chars vs peer-plugin max 365. Trim or request a cross-registry peer-max recompute in a follow-up.
- **Cross-project migration test sweep.** The migrator passes both smoke fixtures (`/tmp/migration_smoke*`); live-project migrations are user-initiated and reviewed against the migration report.

## Lessons (for the reflection ledger)

- L-2026-04-19-30: keep the description out of `trigger:` — the YAML frontmatter check parses colons in backticked literals strictly; a `description:` string containing `current_tier: T4_ready` breaks the skill-check gate. Prefer prose phrasing.
- L-2026-04-19-31: cross-reference integrity is a release gate. The `/tmp/xref_check.py` probe caught two forward-references to a design-phase document (`TIER_PROTOCOL_ARCHITECTURAL_PLAN.md`) that never became a real file; both were rewritten to point at the normative v0.6.0 registers.
- L-2026-04-19-32: when a validator assigns a specific exit code to a failure category (`MONOTONICITY_VIOLATION` → 2 for consistency errors, not 1 for schema errors), release-gate smoketests must assert the exact code, not a default "non-zero."

---

*Populated in Phase 9; see `CHANGELOG.md` for the per-phase rollout notes.*
