# Release notes — v0.14.0 (2026-05-04)

## Output economy

This release lands the **output economy** architecture: default outputs are **F7** JSON evidence packets (under `reviews/.harness/evidence/`) plus an append-only **`reviews/.harness/events.jsonl`** log. The **Planner** assembles **F8** `final_round_report_<round_id>.md` for the consolidated human read. Full contract: `references/OUTPUT_ECONOMY_PROTOCOL.md`.

## Tooling

- `scripts/output_economy_check.py` — static guard on phase skills and agent contracts.
- `scripts/output_economy_smoketest.py` — fixture-backed F7/F8 validation via `artefact_frontmatter_validate.py`.
- Both run from `scripts/release-gate.sh` (Phase 0.61) and are listed in repo-root `CLAUDE.md` maintainer checks.

## Efficiency baseline (Task 9)

Post-implementation scan of `skills/run-phase-*/SKILL.md`, `agents/*.md`, and top-level `references/*.md` (same regexes as `docs/superpowers/plans/2026-05-04-output-economy-overhaul.md` Task 9 Step 1), recorded in `.plugin-efficiency.json` under `output_economy_baseline`: **human-facing default phrasing** 14 hits, **legacy consolidated path** 28 hits, **evidence packet / harness path** 52 hits. Targets under `output_economy_targets` include token and dispatch reduction goals plus `human_facing_reports_per_phase_default_max: 1` and `final_report_default: true`.

## References

- JSON schema: `references/schemas/f7_evidence_packet.schema.json`
- F8 template: `references/templates/final_round_report.md`
- Architecture spec: `docs/superpowers/specs/2026-05-04-output-economy-architecture.md`
