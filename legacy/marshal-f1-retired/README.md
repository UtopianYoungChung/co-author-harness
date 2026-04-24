# Tier Marshal F.1 — Retired Surface

*This folder archives the 5th-agent "Tier Marshal" contract that shipped at v0.5.5 (F.1 advisory-tier rollout on 2026-04-19) and was retired at v0.6.0. Contents are preserved for audit-trail discipline — they are NOT read by any live v0.6.0 code path.*

## Why the Marshal was retired

The v0.6.0 redesign replaced the v0.5.5 ladder (tiers as disjoint review modes with heterogeneous preconditions) with a **progressive approval staircase** (T1 Draft → T2 Review → T3 Verify → T4 Ship), where each tier runs review→plan→generate→human approval and approval auto-advances to the next tier. Every Marshal predicate — P-1 through P-13 (preflight) and Q-1 through Q-11 (postflight) — was bound to retired v0.5.5 machinery:

- Phase 5.5 Close-Out elections (`Down / Stay / Up / Done`) — retired; v0.6.0 has no elections, only per-section approvals.
- The `choice` column in `reviews/tier_decisions_log.md` — retired; v0.6.0 replaces the decisions log with `tier_state.json` per-section ledgers.
- The asymmetric-Down ratchet (`ascent_observed` array) — retired; v0.6.0 uses `ceiling_locked` and `applicable_ceiling` instead.
- The `tier_closeout_<round>_<date>.md` benefit-delta artefact — retired; v0.6.0 emits approval diffs into `tier_state.json` directly.

Since none of these artefacts survive the v0.6.0 migration, the Marshal's hard-gate and coordinator roles collapsed into the Planner's new session-bootstrap routine (Phase 0 of v0.6.0). The 5th agent retires; the package returns to a four-agent contract (Planner, Evaluator, Generator, Reflector).

## What is archived here

| Path | Origin | Purpose in v0.5.5 |
|---|---|---|
| `TIER_MARSHAL_CONTRACT.md` | `references/` | The 5th-agent contract and 24-predicate ledger. |
| `tier_closeout_schema.md` | `references/` | Normative schema for the Phase 5.5 close-out artefact (bound on Q-3). |
| `scripts/marshal_preflight.py` | `scripts/` | Stdlib runner implementing predicates P-1…P-13. |
| `scripts/marshal_postflight.py` | `scripts/` | Stdlib runner for predicates Q-1…Q-11. |
| `scripts/_marshal_common.py` | `scripts/` | Shared helpers for the two runners. |
| `scripts/migrate_classification_to_tier.py` | `scripts/` | v0.4 → v0.5 transitional migration (historical). |
| `fixtures/marshal_smoketest/` | `scripts/fixtures/` | F.1 live-smoketest fixtures (pass/block variants). |
| `design/tier_marshal_design_v1.md` | `research_notes/` | Fourteen-section Marshal design spec (GORE + i* SD/SR). |
| `design/marshal_f1_live_smoketest_2026-04-19.md` | `research_notes/` | Live smoketest findings from the F.1 rollout. |

## Grounding discipline for readers

A v0.6.0 agent that encounters a reference to any of these files in older reviews, reflection reports, or research notes should:

1. Mark the reference as `[LEGACY — Marshal surface retired at v0.6.0]`.
2. Do not treat any retired-artefact field (`choice`, `ratchet_respected`, `ascent_observed`, `tier_closeout_<round>`) as authoritative.
3. If a migration is required (e.g., porting a v0.5.5 project's residual state into v0.6.0), use `scripts/migrate_v055_to_v060.py` (created in Phase 7 of the v0.6.0 rollout), not the files archived here.

## See also

- `research-writing-harness-claude-v0.5.4/CHANGELOG.md` v0.5.5 entry — original Marshal rollout notes.
- `TIER_REDESIGN_v0.6-draft-3.md §9.4` — Marshal retirement surface and rationale.
- `TIER_REDESIGN_v0.6_phase_2_audit.md §3` — the nine-file archive list that this folder realizes.
