# Mutation-Surface Inventory — Producer-Boundary Phase A

**Date:** 2026-07-22. **HEAD:** `32bf9d4` (`main`, clean).
**Purpose:** mechanical enumeration of every harness component that writes to a
filesystem destination or directs an agent to write, as the pre-implementation
input to the producer-only boundary work (destination-capability guard, Phase C;
shipment-producer conversion, Phase E). No behavior is changed by this document.

**Method.** Host-side enumeration on clean `main`:

- Python writers: `Select-String` over `scripts/*.py`, `scripts/analysis/*.py`,
  `scripts/audit/*.py` (smoketests, checks, validators, and test files
  excluded) for `write_text | write_bytes | open(..,"w") | os.replace |
  shutil.{move,copy,rmtree} | .rename( | .unlink( | .mkdir(`.
- Skill-directed writes: pattern sweep over `skills/*/SKILL.md`.
- Agent-directed writes: pattern sweep over `agents/*.md`.
- Public command surface: read directly from
  `scripts/assignment_milestone_checkpoint.py`.

Match counts are write-*operation* sites, not distinct destinations.
Classifications marked (prelim) are name/context-based and must be confirmed
file-by-file during Phase C guard wiring before any enforcement decision relies
on them.

## A. Public CLI mutation surface

`scripts/assignment_milestone_checkpoint.py` (line 19) exposes exactly:
`derive`, `begin`, `record`, `accept`, `rebind-reader-policy`, `recover`.

- `derive` is read-only; the other five mutate project state via
  `assignment_milestone_transaction.py`.
- There are **no** public `register`, `release`, `ship`, or `close` commands.
  `close` exists only as a derived internal action
  (`assignment_milestone_transaction.py` line 497).

## B. Production writer scripts — project-state writers (prelim)

These write into a `--project-root` (which, for research-rooted packages,
resolves under `B:\Agents\research`). Primary Phase C guard targets; primary
Phase E shipment-producer conversions.

| Script | Write-op sites | Role (prelim) |
|---|---|---|
| `assignment_milestone_transaction.py` | 14 | milestone framework events, approvals binding, F9 handoff, checkpoint state |
| `assignment_receipt_transaction.py` | 17 | single-use dispatch receipts |
| `assignment_receipt_recover.py` | 1 | receipt recovery |
| `assignment_process_gate.py` | 2 | gate receipts |
| `native_project_bootstrap.py` | 5 | project-root creation/population |
| `migrate_legacy_milestones.py` | 25 | project migration |
| `migrate_milestone_paths.py` | 13 | project migration (path contract 2.0.0) |
| `migrate_v090_to_v100_snowball_fields.py` | 8 | project migration |
| `migrate_v0100_to_v0110_drop_sd_sr.py` | 1 | project migration |
| `migrate_v0150pre_add_stage_profile.py` | 1 | project migration |
| `render_lifecycle_state.py` | 3 | rendered lifecycle view |
| `reader_accessibility_policy.py` | 25 | accessibility profile/register writes |
| `sk20_overlay_run.py` | 7 | overlay run artifacts under project reviews |
| `sk20_preflight_gate.py` | 10 | preflight gate artifacts |
| `check8_g_prefilter.py` | 2 | review prefilter artifacts |

## C. Production writer scripts — package/tooling-local writers (prelim)

Expected to write only inside the harness package or its build/test sandboxes.
Phase C must still route them through the guard (classification `package`), not
exempt them.

| Script | Write-op sites | Role (prelim) |
|---|---|---|
| `build-plugin.py` | 4 | plugin ZIP build |
| `install_preflight_assets.py` | 2 | packaged asset install |
| `aggregate_h_calibration.py` | 1 | calibration aggregate |
| `gate_threshold_tuner.py` | 2 | tuning output |
| `coupling_health_report.py` | 4 | report output |
| `worktree_paths.py` | 1 | path helper |
| `assignment_fixture_support.py` | 15 | test-fixture scaffolding |
| `semantic_graph_fixture_support.py` | 7 | test-fixture scaffolding |
| `scripts/analysis/fixture_runner.py` | 4 | fixture manifest (write suppressed by `--no-write`) |
| `scripts/audit/run_all.py` | 4 | audit report emission |
| `scripts/audit/schema.py` | 2 | audit schema support |

## D. Skill-directed writes

Pattern sweep found write directives in 13 `SKILL.md` files:
`advisor-escalation`, `centroid-pass`, `accessibility-overlay`,
`extend-snowball-incremental`, `inherit-snowball-from-wiki`,
`graph-grounding-overlay`, `response-letter-review`, `run-generator-session`,
`run-phase-4`, `turabian-format-pass`, `run-phase-3`, `run-phase-1`,
`seed-snowball-discovery`.

**Canonical Wiki status (verified, not prelim):** every canonical-Wiki mutation
path is already fail-closed. `seed-snowball-discovery` §4 declares write-back
**deleted**; `ingest-m5-to-wiki`, `promote-lessons-to-wiki`,
`backfill-source-stubs-from-references`, and `retrofit-concept-grounding` all
return `status: deferred` / `reason_code: WIKI_WRITE_TRANSACTION_UNAVAILABLE`;
`graph-grounding-overlay` and `inherit-snowball-from-wiki` are fail-closed on
graph authority. What remains live is the **automatic attempt wiring** — e.g.
`run-phase-4` SKILL.md step 4 auto-attempts SK-17 at Ph4 close — which Phase H
converts to separately adjudicated shipments to Wiki governance.

Remaining live skill-directed writes target project-root surfaces
(`references/REFERENCES.md`, `reviews/*`, manuscript files) and are covered by
the same Phase C/E boundary as section B.

## E. Agent-directed writes

Write-role declarations found in all five agent files (114 pattern hits):

- `planner.md` — sole writer of `reviews/phase_state.json` (project root).
- `generator.md` — manuscript prose and revision-log writes (project root).
- `evaluator.md` — findings/convergence-log artifacts (project root).
- `reflector-probe.md` / `reflector-closeout.md` — lessons/memory notes
  (package `research_notes/`) and close-out artifacts (project root).

Agent-directed writes use general file tools, so they cannot be constrained by
the Python chokepoint alone; the binding producer-only duty instructions
(landing with the Phase C guard) are the enforcement surface for this class.

## F. Consequence for Phase C

Every section-B script, the live skill-directed writes (D), and the
agent-directed writes (E) must resolve destinations through the single
destination-capability chokepoint: harness-owned staging = writable;
harness package per repo rules = writable; protected consumer roots =
shipment-only, refuse; unknown = refuse. Section-C scripts route through the
same chokepoint with `package` classification.
