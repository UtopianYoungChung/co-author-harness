# references/templates/ — v0.7.4 artefact emit-by-example contract

*Authoring stubs for the five P-3 artefact families (F1–F5). The Evaluator, Reflector, and Planner copy the relevant template, replace placeholder values with round-specific data, and emit under `reviews/` with the conventional filename. Every template validates clean through `scripts/artefact_frontmatter_validate.py` as-shipped; a template regression is a release-gate blocker.*

## 0. Why this folder exists

Proposal P-3 in the v0.7.4 economic-efficiency package shifted artefact authoring from prose-first to frontmatter-first. The YAML block at the top of each artefact is now the machine-readable substrate read by the Planner (consolidated-findings aggregation), by the P-2 stability sub-mode (hash-checkable inheritance), and by the Reflector's Phase 2f contract audit. The prose body after the frontmatter narrates *new signal* only — carry-forward state is cited by reference.

Without a canonical template per family, the Evaluator and Reflector would re-invent frontmatter shape each round; the hash-check inheritance under P-2 compares inconsistent surfaces and stability-mode silently diverges. The templates close that gap: authors emit-by-example, and the validator enforces conformance.

## 1. File index

| Template | Family | Produced by | Canonical filename under `reviews/` |
|---|---|---|---|
| `F1_evaluator_findings.md` | F1 | Evaluator (Step 7 / Step 8 / Step 8.5) | `ph{1,2,3,4}_findings_<YYYY-MM-DD>_iter<N>.md` |
| `F2_evaluator_deterministic.md` | F2 | Evaluator (Step 0a) | `ph{1,2,3,4}_deterministic_<YYYY-MM-DD>_iter<N>.md` |
| `F3_reflector_lightweight_probe.md` | F3 | Reflector (lightweight at Ph1/Ph2/Ph3) | `reflector_lightweight_<YYYY-MM-DD>_iter<N>.md` |
| `F4_reflector_full_report.md` | F4 | Reflector (full at Ph4 close-out only) | `reflector_full_<YYYY-MM-DD>.md` |
| `F5_planner_consolidated_findings.md` | F5 | Planner (per-round aggregation) | `consolidated_findings_report_<YYYY-MM-DD>_iter<N>.md` |

## 2. How to use a template

1. Copy the relevant template into `reviews/` under the filename above.
2. Replace every `<placeholder>` token with the round-specific value. Placeholders follow the convention `<type-hint:description>` (e.g. `<int:blocker_count_for_this_iteration>`) so the type expected at each slot is visible inline.
3. Replace the template's date-stamp (`2026-04-21`) with the round's actual `produced_at`.
4. Replace `cycle_id: "TEMPLATE-PLACEHOLDER"` with the cycle identifier from `reviews/phase_state.json`.
5. Populate the prose body below the frontmatter with the *new signal* for this iteration. Carry-forward findings are cited by reference (e.g., "see ph3_findings_2026-04-18_iter6.md F-3, F-7") rather than re-stated.
6. Run the validator before committing the artefact:

   ```bash
   python <plugin-root>/scripts/artefact_frontmatter_validate.py reviews/<filename>
   ```

   The validator exits 0 on PASS, 3 on non-blocker findings, 4 on any BLOCKER.

## 3. What the templates do NOT cover

- **Prose conventions.** The templates give you an empty narrative shell. For the actual review/audit prose the Evaluator should consult `REVIEW_ORCHESTRATION.md` (seven-step pass), `SAFEGUARD_LAYER.md` (the eight SAFEGUARD checks), `DETERMINISTIC_CHECKS.md` (the §9a/§9b counters), and — for accessibility — `skills/accessibility-overlay` and `STYLE_COMMITMENTS.md` (C-5). The Reflector should consult `AGENT_CONTRACTS.md §Reflector` for the Phase 1–6 structure and Phase 2d/2e/2f/2g audit mechanics.
- **F4 extensibility.** Family F4 (reflector-full) is the only non-strict family — the validator permits unknown fields for forward-compatibility with historical audits. If you extend F4 with a new field under an audit phase that is not yet schema-registered, prefer adding it under `historical_audits.<audit_name>` rather than at top level.
- **Legacy artefacts.** v0.7.3 artefacts live on their original reduced-shape frontmatter. The validator emits `R-Refl-FM-6-legacy` (ADVISORY) but does not block; the migration from v0.7.3 → v0.7.4 (`scripts/migrate_v073_to_v074_tier_to_phase.py`) does not rewrite existing artefact frontmatter — by design. New artefacts written under v0.7.4+ carry the full schema.

## 4. Validation parity

Every template in this folder is validated as part of the release-gate in `scripts/release-gate.sh`:

```bash
python scripts/artefact_frontmatter_validate.py \
  references/templates/F1_evaluator_findings.md \
  references/templates/F2_evaluator_deterministic.md \
  references/templates/F3_reflector_lightweight_probe.md \
  references/templates/F4_reflector_full_report.md \
  references/templates/F5_planner_consolidated_findings.md \
  --quiet
```

(This README itself is documentation, not an artefact; it carries no frontmatter and is excluded from validation by name.) A non-zero exit from the command above blocks the release. When extending a family (e.g., adding an optional field in v0.7.5), update the corresponding template here and re-run the validator before committing.

## 5. Relationship to `skills/accessibility-overlay`

The F1 template's `check_8_aggregate` and `check_8_subcheck_counters` fields are populated by the `accessibility-overlay` skill. At v0.7.4 the overlay emits flag counts (not per-sub-check severity verdicts); the Check 8 aggregate verdict comes from the overlay skill's scoring rule (`one MAJOR → BORDERLINE; two MAJORs → MAJOR; any BLOCKER → BLOCKER`) and is written into the frontmatter by the Evaluator at Step 8.5. A future v0.7.5 minor may lift per-sub-check severity verdicts to first-class fields; the templates are forward-compatible by design (the validator tolerates added optional fields under the `1.x` `schema_version` window).

---

*Normative status.* Authoring stubs for P-3 artefact families. Referenced by `ARTEFACT_FRONTMATTER_SCHEMA.md §1` and by the release-gate script. Any new artefact family added after v0.7.4 must land its template here before the validator dispatch is wired.

*Last updated: 2026-04-21 (v0.7.4 initial authorship).*
