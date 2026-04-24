# Discovery, lifecycle, and project bootstrap

**When to read:** Finding research projects, phase ladder context, or standard project folder layout.

---

## Project discovery

Research projects live under the portfolio root (`Ph.D. Research/` in this workspace). Projects may also appear as immediate children of this harness root in test or demo scenarios. The agent should recognize a research project by the presence of any of these markers:

| Marker | Meaning |
|--------|---------|
| `CLAUDE.md` in the project folder | Project-specific configuration exists |
| `manuscript/` directory | A draft is in progress |
| `reviews/` directory | A review round has been run |
| `research_notes/` directory | Project memory exists |
| A `.tex` or `.md` or `.docx` file matching a paper title | A manuscript exists even without full structure |

When a user names a project (e.g., "the agency delegation paper"), the agent should search for it under the portfolio root `Ph.D. Research/`. If ambiguous, ask.

---

## Lifecycle governance (harness v0.8.2)

Every research project under this root follows the **Lifecycle-Phase Ladder** defined in the v0.7.4 package substrate:

**Ph1 Plan & Draft → Ph2 Review & Revise → Ph3 Iterate & Converge → Ph4 Finalize & Close**

The ladder is climb-only, user-gated, and arbitrated by a per-section ledger at `reviews/phase_state.json` with a 15-field `SectionStateObject` and a 30-trigger enum. Agent engagement is phase-conditioned: the Evaluator is dormant at Ph1, joins at Ph2, and the full four-agent loop runs at Ph3/Ph4. Full-file reads are the universal grounding floor at every rung.

Admission to Ph4 is gated by the **Manuscript Convergence Report (MCR)**: every section must reach `current_phase: Ph3_converged`, and no section may carry a computed `[Ph3-STALE]` flag.

The canonical spec lives at `references/PHASE_PROTOCOL.md`. For the full phase-by-phase runbook, the skill dispatch table, and the milestone-to-rung mapping, see `Ph.D. Research/CLAUDE.md §12` and `PLUGIN_SPEC_v074.md` (the portfolio-root v0.7.4 spec).

### Milestone-to-rung mapping (quick reference)

Governed by `references/AGENT_ORCHESTRATION.md §10` (Lifecycle Dispatch) and `references/REVIEW_ORCHESTRATION.md`.

| Milestone | Artifact | Primary rung(s) |
|-----------|----------|-------------------|
| M1 — Project Memo | `research_notes/project_memo.md` | Ph1 (classify + draft memo) |
| M2 — Annotated References | `research_notes/annotated_references.md` | Ph1–Ph2 |
| M3 — Structured Outline | `manuscript/outline.md` | Ph1–Ph2 |
| M4 — Paper Draft | `manuscript/main.md` (or `main.tex`) | Ph2 → Ph3 (iterate-until-stable) |
| M5 — Final Paper | `manuscript/main.md` (submission-bound) | Ph4 with G.4 sign-off + Reflector-full close-out |

The Planner determines the current milestone and rung by reading the project state (`reviews/classification.md` and `reviews/phase_state.json`). The user can override via explicit instruction.

---

## Bootstrapping a new project

When the user asks to start a new research project, the agent reads `references/PROJECT_BOOTSTRAP.md` and follows its protocol. The bootstrapping protocol creates the standard directory structure, seeds the project CLAUDE.md, and dispatches the Planner for initial classification (which under v0.8.2 includes the `default_final_phase` declaration and the opt-in `sd_sr_required` flag in `reviews/classification.md`).

**Quick reference — the standard project structure:**

```
<project-name>/
├── CLAUDE.md                     # Project-specific config
├── manuscript/
│   ├── main.md (or main.tex)     # The manuscript
│   ├── outline.md                # Structural outline (M3)
│   └── revision_log.md           # Append-only change log
├── reviews/
│   ├── classification.md         # Paper type, P-stage, venue, default_final_phase, sd_sr_required
│   ├── phase_state.json          # 15-field per-section ledger (Planner-owned)
│   ├── revision_plan.md          # Current action list
│   ├── ph1_draft_completion.md   # Ph1 exit artefact
│   ├── ph2_review_completion.md  # Ph2 exit artefact
│   ├── ph3_convergence_signoff.md # Ph3 TerminalSignoffRow / ReengagementSignoffRow
│   ├── convergence_log.md        # Per-iteration Ph3 rows (Trajectory-synthesis prose)
│   ├── safeguard_layer_results.md
│   ├── safeguard_check8_*.md     # Reader-Experience findings (v0.7.2)
│   ├── G4_signoff.md             # Ph4 (submission-bound) only
│   ├── reflection_report.md      # Reflector output
│   ├── sd_model.md, sr_model.md  # Only if sd_sr_required: true
│   └── DO_NOT_DISTURB.md         # Frozen rules (append-only)
├── research_notes/
│   ├── project_memo.md           # M1 artifact
│   ├── annotated_references.md   # M2 artifact
│   ├── directives.md             # User overrides + advisor instructions
│   └── lessons_learned.md        # Reflector-maintained project memory
└── skills/                       # Project-level skills (if any)
```
