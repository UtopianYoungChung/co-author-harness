# Release Notes — research-writing-harness-claude v0.7.1

**Release date:** 2026-04-20
**Theme:** scope-respecting SD/SR — goal-modelling work is opt-in at the package level, gated by a new `sd_sr_required` field in `reviews/classification.md` (default `false`), with absent-means-false migration so existing v0.7.0 projects upgrade at zero cost.
**Verdict:** CLEARED (point release; no new agents, no new skills, no new audit phases; surface conditionalization only).

---

## One-paragraph summary

v0.7.1 is a scope-control point release over v0.7.0. v0.7.0 treated the Strategic Dependency / Strategic Rationale (i\*) artefacts as unconditional — the Planner authored `reviews/sd_model.md` and `reviews/sr_model.md` at T1 on every project, the Evaluator opened them as read-prerequisites on every T2 entry, and the pre-tier-advance Cold-Start defence (`pre_tier_advance_check.check_clause_e`) fired `E-IMODEL-STRUCTURALLY-INCOMPLETE` when the models were missing. That made sense for GORE/AORE-native projects but silently imposed goal-modelling work on every manuscript, including ones where the user never asked for i\* modelling. v0.7.1 introduces a new `sd_sr_required` field in `reviews/classification.md` (canonical spec at `references/TIER_PROTOCOL.md §3.1.2`; default `false`). When absent or `false`: the Planner does not author SD/SR at T1, the `imodel_structural_validation_signed` trigger does not emit, the Evaluator does not open the SD/SR models at T2 entry, the Generator does not read goal-model artefacts, the `E-T2-SD-UNGROUNDABLE` and `E-IMODEL-STRUCTURALLY-INCOMPLETE` failure codes do not raise, and the Cold-Start defence short-circuits. When `true`, all v0.7.0 SD/SR behaviour is preserved byte-for-byte. Migration is absent-means-false: existing v0.7.0 `reviews/classification.md` files without the new field continue to work unchanged as if they had written `sd_sr_required: false`. No migration script is required.

## Headline change — the SD/SR opt-in gate

```
  reviews/classification.md
  ┌──────────────────────────────────────────────────┐
  │  SD/SR required: true    ← v0.7.1 opt-in         │
  │                  false   ← v0.7.1 default        │
  │                  <absent> ← v0.7.0 projects      │
  │                              (treated as false)  │
  └──────────────────────────────────────────────────┘
           │
           ▼  read by Planner, Evaluator, Generator,
              and pre_tier_advance_check.check_clause_e
           │
   ┌───────┴───────────────────────────────────────────┐
   │                                                    │
   ▼ (true)                                             ▼ (false / absent)
   - Planner authors sd_model.md + sr_model.md at T1    - SD/SR authoring out of scope at T1
   - §3.1.1 i* structural validator runs                - §3.1.1 validator does not run
   - imodel_structural_validation_signed emits          - trigger does not emit
   - Evaluator reads SD/SR at T2 entry                  - Evaluator reads prose directly at T2
   - E-T2-SD-UNGROUNDABLE may fire                      - E-T2-SD-UNGROUNDABLE does not fire
   - E-IMODEL-STRUCTURALLY-INCOMPLETE may fire          - E-IMODEL-STRUCTURALLY-INCOMPLETE does not fire
   - Generator reads goal-model artefacts               - Generator skips goal-model reads
```

- The flag is **package-level opt-in** — it lives in the per-project `reviews/classification.md` file, not in a global setting. Each project decides whether it wants i\* modelling.
- The gate is **silent when off** — no warning, no advisory, no log noise. A project that opts out never sees SD/SR surfaces at all.
- The gate is **unconditional when on** — when `sd_sr_required: true`, every v0.7.0 SD/SR obligation applies. v0.7.1 does not soften any v0.7.0 behaviour; it only adds the scope gate.
- **No schema changes to `reviews/tier_state.json`.** The 15-field `SectionStateObject` and 27-trigger enum from v0.7.0 are preserved. The opt-in lives one layer above, in classification.

## What changes at the file level

### Canonical spec

- `references/TIER_PROTOCOL.md §3.1.2` — net-new subsection "SD/SR opt-in gate (v0.7.1 — `sd_sr_required`)". Documents motivation, flag location, absent-means-false migration, all downstream gates affected, what remains unconditional, and change-of-mind semantics.
- Cross-references added in `§2.1` (G1 goal), `§2.2` (AORE preamble and T1/T2 SD bullets), `§3.1` (primary deliverables and exit artefact), `§3.2` (T2 SD-contract row), `§4.2` (M1 row), `§5.1` (agent matrix), `§5.3` (Evaluator's T1-model read contract).

### Classification template

- `skills/classify-manuscript/SKILL.md` — classification template row for the new flag with a default-false recommendation; default-classification fallback now reads `essay/positioning · P1 · cross-venue · T3 · sd_sr_required: false`.

### Agent prompts

- `agents/planner.md` — T1 exit artefact conditional; T2 dispatch row conditional; validator instruction conditional.
- `agents/evaluator.md` — frontmatter description conditional; T2 scope budget conditional; T2 read-prerequisites heading conditional; T2 SD/SR read-prerequisites sub-step conditional with explicit skip clause.
- `agents/generator.md` — line-65 goal-model-artefact read rule conditional; line-204 T2 SD/SR-derived-constraint respect conditional.

### Tier entry skills

- `skills/run-tier-1/SKILL.md` — frontmatter description conditional; agent table Planner row split; dispatch sequence phases 2, 3, 6, 10, 11 conditional; artefacts conditional; `tier_state.json` write set reordered with conditional `imodel_structural_validation_signed`.
- `skills/run-tier-2/SKILL.md` — frontmatter description conditional; grounding basis extended to `§3.1.2`; preconditions rows 4 and 5 conditional; Evaluator row conditional; sub-phase 2 ("Planner: Evaluator read-contract staging") marked conditional.
- `skills/plugin-commands/SKILL.md` — `/run-tier-1` and `/run-tier-2` rows conditional.

### Orchestration and state references

- `references/AGENT_ORCHESTRATION.md` — §1 Planner row conditional; §3.0 T1 Planner cell conditional; §3.2 T1 truncated loop ASCII expanded with conditional SD/SR notes; §10.1 M3 row and §10.2 M3 deliverable block conditional.
- `references/REVIEW_ORCHESTRATION.md §3.3` — T1 and T2 tier-table rows conditional; `E-T2-SD-UNGROUNDABLE` and `E-IMODEL-STRUCTURALLY-INCOMPLETE` conditional.
- `references/SKILL_REGISTRY.md` — SK-29 (`run-tier-2`) pattern and source paragraphs conditional.
- `references/TIER_PROTOCOL_SR.mermaid` — Evaluator T2 node label conditional; Ladder T2 node label conditional.
- `references/tier_state_schema.md` — T1 canonical `tier_goal_declared` updated; three JSON example occurrences updated; trigger 13 (`imodel_structural_validation_signed`) description conditional; failure codes `E-IMODEL-STRUCTURALLY-INCOMPLETE` and `E-T2-SD-UNGROUNDABLE` conditional.
- `references/tier_notifications.yaml` — `imodel_validation_signed`, `imodel_structurally_incomplete`, `t2_sd_ungroundable` entries annotated with §3.1.2 and v0.7.1 opt-in YAML comments; `log_detail` strings carry `(sd_sr_required=true)` markers; `user_template` strings carry explanatory trailing notes.

### Scripts

- `scripts/migrate_v060_to_v070.py TIER_GOAL_TABLE["T1"]` — v0.7.1 default is `"produce a complete first draft with classification and an advisory Evaluator note"`; projects that set `sd_sr_required: true` may append `" and i* SD/SR"` downstream. Migration script unchanged otherwise.
- `scripts/pre_tier_advance_check.py` — net-new helper `_resolve_sd_sr_required(project_root: Path) -> bool` reads `reviews/classification.md` and returns `False` on absent/malformed/missing (absent-means-false migration). `check_clause_e` now early-returns when the helper returns `False`, so the Cold-Start defence no longer fires on opt-out projects.

## What is unchanged

- The **four-agent pipeline** (Planner, Evaluator, Generator, Reflector) is unchanged.
- The **Lifecycle-Stage Ladder** topology (T1 Plan & Draft → T2 Review & Revise → T3 Iterate & Converge → T4 Finalize & Close) is unchanged.
- The **15-field `SectionStateObject`** and **27-trigger enum** are unchanged. `sd_sr_required` lives in `reviews/classification.md`, not `tier_state.json`.
- **Full-file reads at every rung** remain the universal grounding floor.
- **MCR admission** (every section at `T3_converged`; +50% iteration reserve; climb target capped at `default_final_tier`) is unchanged.
- **Monotonicity invariants** (with the three documented exemptions: `retraction`, `eg1_t4_downgrade_to_t3`, `eg7_mcr_readmission_after_class_change`) are unchanged.
- **Reflector dispatch split** (lightweight for T1/T2/T3 integrity probes; full for T4 close-out) is unchanged.
- **Grounding Protocol** rules and the Coupling E.2 graph-grounding overlay are unchanged.
- **Release-gate phases** are unchanged. No new phases, no retired phases.
- **Skill count** is unchanged.

## Migration — v0.7.0 → v0.7.1

**Absent-means-false migration.** No migration script is required. Existing v0.7.0 projects whose `reviews/classification.md` file does not include an `SD/SR required:` field are treated as `sd_sr_required: false` by the Planner, Evaluator, Generator, and `pre_tier_advance_check.check_clause_e`. The resolver helper `_resolve_sd_sr_required(project_root)` in `scripts/pre_tier_advance_check.py` handles the absence defensively:

```python
def _resolve_sd_sr_required(project_root: Path) -> bool:
    """Read reviews/classification.md and resolve the v0.7.1 `sd_sr_required`
    flag. Default is False (absent-means-false migration semantics)."""
    cls_path = project_root / "reviews" / "classification.md"
    text = _read_text_or_none(cls_path)
    if not text:
        return False
    # ... parse case-insensitively, tolerant of bullet/asterisk/colon shapes
    return False
```

**Projects that want SD/SR to continue.** v0.7.0 projects that were actively using SD/SR at T1/T2 must add one line to `reviews/classification.md`:

```markdown
- SD/SR required: true
```

After adding the line, the project resumes full v0.7.0 SD/SR behaviour on the next T1 or T2 dispatch.

**Change of mind.** The flag is read on every Planner dispatch, so toggling the value mid-project is supported. Flipping `false → true` starts SD/SR authoring at the next T1 and starts SD/SR read-prerequisites at the next T2. Flipping `true → false` stops new SD/SR work but leaves any existing `sd_model.md` / `sr_model.md` in place as project history.

## Verification

- `scripts/release-gate.sh --probe-only` — clean (no regressions over the v0.7.0 probe-only baseline).
- Skill-count reconciliation — unchanged at v0.7.0 counts.
- Smoketest on `scripts/migrate_v060_to_v070.py` — clean; v0.6.0 → v0.7.1 migration path unaffected (v0.7.1 is an additive scope gate over v0.7.0; the migration script still emits v0.7.0 canonical goals, and projects that want SD/SR set `sd_sr_required: true` post-migration).
- Grep sweep for stragglers — zero outstanding unconditional SD/SR references in `agents/`, `skills/`, `references/`, `scripts/`.

## Lessons

**Default assumptions about modelling scope bleed into every surface.** The v0.7.0 assumption that SD/SR authoring was universal was encoded in ~18 files. Moving from unconditional to opt-in required edits across `references/`, `agents/`, `skills/`, and `scripts/`. When adding a new cross-cutting obligation in a future release, author the opt-in/opt-out gate in the same release — do not assume the default will stay correct.

**Absent-means-false migration semantics are cheaper than a migration script.** Rather than requiring existing v0.7.0 projects to write `sd_sr_required: false` into their classification files, the Planner and pre-flight check treat *absent* as *false*. This makes the v0.7.0 → v0.7.1 upgrade zero-cost for the vast majority of projects.

**Point releases can still touch many files.** v0.7.1 is a scope-control change, not an architectural one — but because the scope was unconditional in v0.7.0, conditionalizing it touched roughly the same file count as a minor-version rollout. Scope is cross-cutting even when architecture is not.
