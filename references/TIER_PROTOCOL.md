# TIER_PROTOCOL — DEPRECATED at v0.7.4

> **Deprecation banner (v0.7.4).** This file has been renamed `PHASE_PROTOCOL.md` as part of the cross-cutting Tier → Phase terminology rename. All authoritative content now lives at [`PHASE_PROTOCOL.md`](./PHASE_PROTOCOL.md). This forwarding stub ships during the v0.7.4 minor for back-compatibility and is **removed at v0.7.5 RC**.

## Why it was renamed

v0.7.4 retires the ambiguous *Tier* vocabulary that overloaded two unrelated surfaces — review depth (retired at v0.6.0) and the lifecycle ladder. The remaining ladder is now the **Lifecycle-Phase Ladder**, with rungs **Ph1 Plan & Draft → Ph2 Review & Revise → Ph3 Iterate & Converge → Ph4 Finalize & Close**. The rename eliminates the clash and re-grounds the ladder in manuscript-lifecycle semantics rather than review-effort semantics.

## Where to look now

| Old path                                     | New path                                                   |
| -------------------------------------------- | ---------------------------------------------------------- |
| `references/TIER_PROTOCOL.md`                | [`references/PHASE_PROTOCOL.md`](./PHASE_PROTOCOL.md)      |
| `reviews/tier_state.json`                    | `reviews/phase_state.json`                                 |
| `scripts/tier_state_validate.py [retired from tree]`             | `scripts/phase_state_validate.py`                          |
| `reviews/t1_draft_completion.md`             | `reviews/ph1_draft_completion.md`                          |
| `reviews/t2_review_completion.md`            | `reviews/ph2_review_completion.md`                         |
| `reviews/t3_convergence_signoff.md`          | `reviews/ph3_convergence_signoff.md`                       |
| `skills/run-tier-{1..4}`                     | `skills/run-phase-{1..4}`                                  |
| vocabulary `T1`–`T4`                         | vocabulary `Ph1`–`Ph4`                                     |
| field `current_tier`                         | field `current_phase`                                      |
| value `T3_converged`                         | value `Ph3_converged`                                      |
| flag `[T3-STALE]`                            | flag `[Ph3-STALE]`                                         |
| field `default_final_tier` (classification)  | field `default_final_phase`                                |
| trigger `eg1_t4_downgrade_to_t3`             | trigger `eg1_ph4_downgrade_to_ph3`                         |
| "Lifecycle-Stage Ladder" *(renamed)*         | "Lifecycle-Phase Ladder"                                   |

> **Note.** The response-letter sibling ladder `T4R` is **preserved, not renamed** — it does not participate in the main Ph1–Ph4 advancement.

## Migration

Run `scripts/migrate_v073_to_v074_tier_to_phase.py` *[retired from tree — recover from git history if needed]* against any project carrying legacy tier-named artefacts; the script is idempotent and emits `reviews/migration_report_v073_to_v074.md`. During the v0.7.4 minor the validator retains a **dual-read path** — `scripts/phase_state_validate.py` accepts a legacy `tier_state.json` with a `DEPRECATION_WARNING` finding — which is removed at v0.7.5 RC.

