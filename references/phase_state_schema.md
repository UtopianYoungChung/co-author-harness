# `phase_state.json` — Per-Section Phase-State Ledger



## Wiki write deferral (Research Truth Phase 0/1)

Coupling C/D canonical Wiki mutation is **unavailable**
(`reason_code: WIKI_WRITE_TRANSACTION_UNAVAILABLE`).

- Block only the Wiki mutation.
- Do **not** block Research completion, approval, or release.
- Project-local REFERENCES, lessons, reports, manuscripts, and reflection
  outputs continue normally.
- On deferral record: `status: deferred`,
  `reason_code: WIKI_WRITE_TRANSACTION_UNAVAILABLE`, `wiki_page_key: null`.
- Do **not** write `m5_wiki_ingest` as a success trigger and do **not**
  fabricate `wiki_page_key` or `lessons_promoted_to_wiki` success values.
- Automatic callers treat the deferred result as a visible non-blocking
  downstream deferral. Phase 4 / G.4 completion does not depend on Wiki write
  availability.

> **File-rename note (v0.7.4.1).** This file is the authoritative schema for `reviews/phase_state.json`. It was shipped at v0.7.4 under the legacy name `tier_state_schema.md`; the physical rename to `phase_state_schema.md` landed at v0.7.4.1 to close a rename-migration miss surfaced by the plugin-calibrator. The body was carried forward in v0.7.0-shape prose through v0.7.4.1 as a known residual and is **rewritten to v0.7.4 shape at v0.8.0 (R-P0-SCHEMA-3 closure)**. The two provenance carve-outs that survive the rewrite are this file-rename note and the v0.6.0 predecessor reference on the next line.

> **v0.6.0 predecessor.** The direct documentary ancestor of this file is the v0.6.0 `tier_state_schema.md`, which shipped a ten-field `SectionStateObject` and a six-field log row under the Progressive-Approval depth-of-review vocabulary. The v0.7.0 Lifecycle-Stage Ladder widened the section shape to fifteen fields; the v0.7.4 Tier → Phase rename + economic-efficiency bundle widened the log row to seven fields and extended the trigger enum 28 → 30. At v0.8.0 under β-P-9a (pre-MCR Ph3-deep safety-net pass), the section shape widens a further 15 → 16 fields with the addition of `pre_mcr_deep_pass_completed: bool`; the widening is additive and does not rename the `schema_version` string. **v0.10.0 RC is the vocabulary roll point:** `schema_version` stays `"0.7.4"` at the ledger surface across the entire v0.8.x line and the v0.9.x line (both v0.8.0 and v0.9.0 shipped without rolling the surface, despite the v0.8.0 β-P-9a P2.1a section-shape widening and the v0.9.0 maintenance bundle); the bump to `"0.10.0"` lands at the v0.10.0 RC gate via `scripts/migrate_v090_to_v100_snowball_fields.py`, in lockstep with the snowball-driven SectionStateObject extensions documented at §2 (`references_initialized` at S2; `last_coverage_score` at S4) and the trigger-enum extension at §3.1 (`seed_snowball_signed = 31`). The v0.7.4 migration path for projects carrying a v0.7.3 `tier_state.json` is `scripts/migrate_v073_to_v074_tier_to_phase.py [retired from tree]`; see §7.

*Normative schema for the per-section ledger under the v0.7.4 Lifecycle-Phase Ladder. This file binds (a) the Planner's writes (Phase 0 session bootstrap, Phase 5.5 post-approval log-write, Phase 6 MCR cycle-step append) and (b) every other agent's reads. Located at `reviews/phase_state.json` for each manuscript. Single writer: Planner.*

Grounding: `PHASE_PROTOCOL.md §§1–3` (lifecycle-phase-ladder semantics, per-phase specifications, `[Ph3-STALE]` dual-state semantics, stability sub-mode, Check 8 accessibility gate), `PHASE_PROTOCOL.md §§4–5` (milestone supersession, agent role matrix), `PHASE_PROTOCOL.md §6` (schema delta — the authoritative surface for the trigger enum and row shapes specified below), `PHASE_PROTOCOL.md §§7–9` (escalation gates, approval semantics, MCR admission), `scripts/phase_state_validate.py` (runtime validator at v0.7.4; `scripts/tier_state_validate.py` is a forwarding shim retained during the v0.7.4 minor and removed at v0.7.5 RC).

---

## 1. File shape

`reviews/phase_state.json` is a single JSON object with the shape:

```
{
  "schema_version":         "0.7.4",
  "manuscript_id":          "<project-slug>",
  "default_final_phase":    "Ph1" | "Ph2" | "Ph3" | "Ph4",
  "fingerprint_mode":       "strict" | "tolerant" | "off",
  "terminal_phase_reached": false | true,
  "terminal_round_id":      null | "round_YYYY-MM-DD_NNN",   // additive (v0.7.4)
  "last_updated":           "<ISO-8601 UTC timestamp>",
  "phase_vocabulary":       "lifecycle_v0.7.4",
  "sections": {
    "<heading-path-slug>": <SectionStateObject>,
    ...
  },
  "milestone_framework": <MilestoneFrameworkObject>  // optional additive namespace
}
```

**Top-level shape.** The established phase fields remain unchanged, with one optional additive `milestone_framework` namespace. The `sections` entry is a JSON **object** keyed by heading-path slug — not an array — to match the validator's `sections[path]` access pattern (`scripts/phase_state_validate.py` `_validate_doc`). A flat-map layout is also tolerated as a legacy read path (top-level keys whose values are objects are treated as sections when no `sections` key is present); new writes always use the `sections: {...}` form.

The Planner validates shape on every Phase 0 bootstrap via `scripts/phase_state_validate.py`; BLOCKER findings halt Phase 0.

### 1.1 Top-level metadata fields

| Field | Type | Legal values | Notes |
|---|---|---|---|
| `schema_version` | string | `"0.7.4"` (exact match) | Hard-coded at v0.7.4. Migration scripts read the string to decide how to parse. |
| `manuscript_id` | string | project slug (lower-kebab-case) | Stable identifier used in cross-project logs. |
| `default_final_phase` | enum | `"Ph1"` / `"Ph2"` / `"Ph3"` / `"Ph4"` | Manuscript-wide ceiling. Caps the MCR target per `PHASE_PROTOCOL.md §9`. Writable via `/raise-ceiling` without `--section` (raises manuscript-wide) or at classification time. Renamed at v0.7.4 from `default_final_tier`. |
| `fingerprint_mode` | enum | `"strict"` / `"tolerant"` / `"off"` | Controls canonicalization tolerance for `last_scope_fingerprint` drift detection (see §4). |
| `terminal_phase_reached` | boolean | `true` only after a Ph4 Finalize & Close approval | Flipping to `true` dispatches the Reflector-full for the round and closes the Ph4 cycle. Planner-only write. Renamed at v0.7.4 from `terminal_tier_reached`. |
| `terminal_round_id` | string \| null | `null`, or the round identifier `round_YYYY-MM-DD_NNN` (format owned by `scripts/round_identifier.py`; contract at `ARTEFACT_FRONTMATTER_SCHEMA.md` F6/F7/F8) | **Additive at v0.7.4** — `schema_version` stays `"0.7.4"`; a legacy **non-terminal** ledger may omit the key. The Planner-created round identifier for the round that reached terminal, persisted so a terminal claim NAMES its final round instead of leaving a reader to infer it. Written **atomically with `terminal_phase_reached: true`** in the same guarded transaction, and cleared to `null` atomically whenever terminal is cleared (reopen, `eg1_ph4_downgrade_to_ph3`, retraction, or starting another round). Planner-only write. Biconditional, enforced by `phase_state_validate` (`TERMINAL_ROUND_ID_INVALID`, BLOCKER): terminal true ⟺ well-formed id; terminal false ⟺ `null`/absent. A legacy **terminal** ledger lacking the key fails closed and requires explicit Planner/user-authorised terminal re-attestation with the id supplied — it is **never** inferred from filenames, mtimes, glob order, event order, `notes`, or historical reports, since inferring it from the artefacts it exists to select would be circular. Consumed by `full_run_contract_check.py::_f8_findings` to select `reviews/final_round_report_<terminal_round_id>.md`. |
| `last_updated` | string | ISO-8601 UTC timestamp with `Z` suffix | MUST be the wall-clock time of the last successful atomic write to the file, and MUST be ≥ all `phase_entry_log` rows' timestamps written in the same session. The Planner refuses to advance if the on-disk `last_updated` is newer than its in-memory copy (`[CONCURRENCY-DETECTED]`). |
| `phase_vocabulary` | string | `"lifecycle_v0.7.4"` (exact match) | Fixed string identifying that this ledger uses the v0.7.4 Lifecycle-Phase Ladder vocabulary. The value is reserved for future minor-version vocabulary rolls. Renamed at v0.7.4 from `tier_vocabulary: "lifecycle_v0.7"`. |
| `sections` | object | `{heading_path_slug: SectionStateObject, ...}` | Keys are heading-path slugs; order is manuscript heading order (JSON object key-order preserved). Elements are never deleted; retracted approvals mutate the object in place. Empty `sections` on a manuscript with at least one heading fails `DOC_NO_SECTIONS` (MAJOR). |
| `milestone_framework` | object | contract version `"1.0.0"` | Optional additive M1-M5 feedback/handoff namespace. Its strict shape is `references/schemas/milestone_framework.schema.json`; semantics are defined by `references/MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md`. |

### 1.2 Additive milestone namespace

`reviews/phase_state.json` is the one lifecycle-state authority for both orthogonal axes: `sections` records Ph1-Ph4 section state, while `milestone_framework` records M1-M5 project deliverables and handoffs. The namespace does not create a second ledger and does not allow milestone acceptance to stand in for phase advancement (or the reverse).

The namespace contract is `contract_version: "1.0.0"`. It declares exactly one `primary_lineage`, exactly M1-M5 under `milestones`, and an append-only `events[]` history whose event enum and exact-byte bindings are defined by `MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md §8` (authoring shape: `references/templates/milestone_event.json`). Accepted artifact and F9 state binds current project-relative paths, SHA-256 values, and byte counts. Simultaneous deliverable candidates use unique `lineage_id` values; distinct unsuperseded lineages may coexist before acceptance. An artifact that displaces another lineage names it explicitly with `supersedes_lineage_id`; the target must exist in the same milestone, self-links and cycles are invalid, and milestone-level `superseded` status alone is insufficient. Accepted state has exactly one unsuperseded primary-lineage deliverable. A released M5 export carries `source_sha256` for the accepted primary-lineage manuscript (`source_path` is optional diagnostic duplication), and the terminal F9 packet repeats the canonical export binding as `released_export`; non-terminal packets carry `released_export: null`. Package-level override rules resolve to anchored package references; `project_local_contract` rules resolve only to anchored files contained by the project root. Override authorization remains explicit through the authority/rule locator and the current `substitute_evidence` path plus `substitute_evidence_sha256` binding. F9 packets and generated views are evidence derived from this file, never state authorities.

**Reader-accessibility policy binding.** Native projects initialize `milestone_framework.policy_bindings.reader_accessibility` at bootstrap; legacy projects declare migration semantics explicitly. Every source binding uses one shape: `scope: package|project`, normalized root-relative `path`, `sha256`, constrained `role`, and profile-owned `polarity` when applicable. The resolver artifact and phase-state binding must match exactly. G/H/VE transition entries carry `state`, derived `observed_count`, and append-only Planner observation/approval `events`; retirement requires the profile count plus current evidence bindings. `classification.md`, dates, normative prose, and calibration reports are evidence/generated views, never live authorities. Evidence is progressive: M1 intent only once M1 starts; M3 resolved-profile binding only once M3 starts; M4/M5 current manuscript/profile/phase once started and canonical Check 8 JSON evidence once accepted/ready. Future milestones carry no fabricated evidence. Drift, forged content, or missing links emit `MF-POLICY`.

**Ownership.** The Planner is the sole writer and must use the same atomic-write, advisory-lock, and concurrent-change checks as every other `phase_state.json` update. `scripts/milestone_framework_validate.py`, `scripts/phase_state_validate.py`, renderers, and all non-Planner agents are read-only. When the namespace is present, `phase_state_validate.py` calls the shared semantic implementation in `milestone_framework_validate.py`; it does not duplicate milestone predicates. Absence remains tolerated by the phase validator for pre-framework projects, while the dedicated milestone validator reports absent state as `MISCONFIGURED`.

---

## 2. `SectionStateObject` schema

Every value of the `sections` map is an object with the following eighteen fields (no omissions tolerated for the two fields the validator enforces as required; other fields are contract-required but not per-field-enforced by `phase_state_validate.py` — see §6.1). The sixteenth field, `pre_mcr_deep_pass_completed`, is additive at v0.8.0 under β-P-9a; a ledger that omits it is tolerated at shape-validation time and treated as `false` by the MCR admission gate. The seventeenth field, `references_initialized`, is additive at v0.10.0 Stage S2 under the snowball-driven reference-scaffolding bundle; a ledger that omits it is tolerated at shape-validation time and treated as `false` by SK-NEW-A's idempotency guard. The eighteenth field, `last_coverage_score`, is additive at v0.10.0 Stage S4 under the same bundle; a ledger that omits it is tolerated at shape-validation time and treated as `null` by SK-NEW-B's cross-round regression-detection logic at `agents/planner.md §Phase 3.8`.

### 2.2 Optional `stage` / `profile` (v0.15.0-pre PR-3b.1)

Two **optional** shadow fields are accepted on every `SectionStateObject`:

| Field | Type | Legal values | Notes |
|---|---|---|---|
| `stage` | string \| null | `"draft"` / `"iterate"` / `"finalize"` | Lifecycle axis decoupled from `current_phase`. Backfilled by `scripts/migrate_v0150pre_add_stage_profile.py` from existing `current_phase` (`Ph1→draft`, `Ph2/Ph3/Ph3_converged→iterate`, `Ph4→finalize`). |
| `profile` | string \| null | `"refine"` / `"structural"` / `"deep"` / `"stability"` | Scope dial, meaningful only when `stage == "iterate"`. Backfilled from `check_profile` when present, else `"refine"`. |

**Status at PR-3b.1.** Purely additive. Absence is tolerated; presence is enum-type-checked by `scripts/phase_state_validate.py` (BLOCKER on bad enum value). No agent, skill, or readiness gate reads `stage` or `profile` yet — that wiring lands in PR-3b.2 (MCR convergence keying) and PR-3b.3 (skill aliases). `current_phase` remains the source of truth for behaviour at 3b.1. The migration helper is idempotent; existing ledgers continue to validate without re-write.

**Update at PR-3b.2 (MCR convergence evidence advisory).** `scripts/pre_phase_advance_check.py:check_clause_f` now emits a single non-blocking advisory `W-MCR-CONVERGENCE-EVIDENCE` per section when the last two matching rows of `reviews/convergence_log.md` carry (a) an explicit `profile:` field in `{deep, structural, stability}` on both rows, (b) `findings_count_delta: 0` on both rows, and (c) the same non-null `convergence_metric` on both rows. If rows include a section key (`section`, `Section`, `heading_path`, or `section_heading_path`), the advisory is computed only from rows matching the section under review; rows without a section key are treated as project-scoped for backward compatibility. The advisory is **evidence-only** — it does not authorize MCR admission, does not change `_is_mcr_cleared`, and does not alter the script's exit code (W-prefixed codes route to warnings per `main()`). The `TerminalSignoffRow` in `ph3_convergence_signoff.md` remains the sole authority for `Ph3 → Ph3_converged`. Missing or pre-PR-3b.2 `profile:` fields on convergence-log rows yield no advisory and no finding (graceful degradation for old-schema ledgers). Future convergence-log writers SHOULD include `profile:` per iteration row so the advisory fires when stability is genuine.

```json
{
  "heading_path": ["1. Introduction"],
  "current_phase": "Ph1",
  "last_approved_phase": null,
  "ceiling_locked": false,
  "section_ceiling_override": null,
  "iteration_count_at_current_phase": 0,
  "last_scope_fingerprint": "<sha256 hex>",
  "fingerprint_computed_at": "2026-04-22T14:05:22Z",
  "cumulative_drift_lines_since_approval": 0,
  "phase_goal_declared": "produce a complete first draft with classification and an advisory Evaluator note",
  "phase_deliverable_path": "reviews/ph1_draft_completion.md",
  "references_initialized": false,
  "last_coverage_score": null,
  "convergence_metric": null,
  "ph1_pstage_declaration": "P2",
  "ph3_last_activity_at": null,
  "pre_mcr_deep_pass_completed": false,
  "phase_entry_log": [ <PhaseEntryLogRow>, ... ]
}
```

**Validator-enforced required fields (BLOCKER on absence).** `current_phase`, `phase_entry_log`. All other fields are contract-required per this §2 but are not enforced by `phase_state_validate.py` — they are validated in context by `pre_phase_advance_check.py` clauses (a)–(h) and by the Reflector's Phase 2b lifecycle-coherence audit at Ph4. The v0.8.0 sixteenth field `pre_mcr_deep_pass_completed` is a soft type-check at `phase_state_validate.py` (MINOR finding `SECTION_BAD_PRE_MCR_DEEP_PASS_TYPE` if present and non-boolean); its MCR admission refusal `E-MCR-PRE-DEEP-PASS-REQUIRED` is authored at `pre_phase_advance_check.py` clause (f) — see §6.1 "Contracts enforced elsewhere" — and at the Planner's Phase 8 MCR-assembly logic. The v0.10.0 seventeenth field `references_initialized` is likewise a soft type-check at `phase_state_validate.py` (MINOR finding `SECTION_BAD_REFERENCES_INITIALIZED_TYPE` if present and non-boolean); its consumer-side contract (the SK-NEW-A `seed-snowball-discovery` idempotency guard) is enforced at the skill's preflight, not in this validator — see §6.1 "Contracts enforced elsewhere". The v0.10.0 eighteenth field `last_coverage_score` is a soft type-check at `phase_state_validate.py` (MINOR finding `SECTION_BAD_LAST_COVERAGE_SCORE_TYPE` if present and neither `null` nor a number in [0.0, 1.0]); its consumer-side contract (the SK-NEW-B `claim-coverage-audit` cross-round regression-detection at `agents/planner.md §Phase 3.8`) is enforced at the Planner's Ph2 dispatch, not in this validator — see §6.1 "Contracts enforced elsewhere".

### 2.1 Field semantics

**`heading_path`** — `array<string>`. Ordered list of heading tokens rooted at the manuscript's top-level heading. Uniqueness key for the section.

**`current_phase`** — `enum`. Legal values: `"Ph1"`, `"Ph2"`, `"Ph3"`, `"Ph3_converged"`, `"Ph4"`. `"Ph4_ready"` is retired. `"Ph3_converged"` is not a fifth phase; it is the readiness state between a terminal Ph3 convergence-signoff row and MCR admission to Ph4. Exact legal source/trigger/target triples, including recovery, are machine-authoritative in `lifecycle_transitions.v1.json` and enforced by `phase_state_validate.py`.

**`last_approved_phase`** — `enum | null`. Highest phase at which the user has approved this section. Legal: `null` (before first approval), `"Ph1"`, `"Ph2"`, `"Ph3"`, `"Ph4"`. `"Ph3_converged"` is not a legal `last_approved_phase` value. Never decreases except under `retraction`. Renamed at v0.7.4 from `last_approved_tier`.

**`ceiling_locked`** — `boolean`. `true` when the section has been approved at a ceiling below Ph4. Cleared to `false` only on `ceiling_raised` trigger. Ceiling-lock participates in the MCR disjunctive admission rule per `PHASE_PROTOCOL.md §9.4` — a ceiling-locked section with `last_approved_phase == applicable_ceiling` satisfies MCR at Ph4 admission time without needing a `Ph3_converged` state.

**`section_ceiling_override`** — `enum | null`. `null` inherits `default_final_phase`. When set, overrides per-section. Applicable ceiling is `min_by_phase(default_final_phase, section_ceiling_override)`. Writable via `/raise-ceiling --section <path> --to <phase>`.

**`iteration_count_at_current_phase`** — `non-negative integer`. Incremented on each review cycle at the same phase. Resets to `0` on advance or on rollback demotion via retraction. Under Ph3's unbounded loop, increments on every Generator re-dispatch and resets only when the terminal signoff row flips `current_phase` to `Ph3_converged`.

**`last_scope_fingerprint`** — `string (sha256 hex)`. Canonicalized sha256 of the section body under the tokenizer of `fingerprint_mode`. Canonicalization rules in §4.

**`fingerprint_computed_at`** — `string (ISO-8601 UTC)`. Timestamp of the last fingerprint computation.

**`cumulative_drift_lines_since_approval`** — `non-negative integer`. Line-delta between the current canonical body and the body at the time of `last_approved_phase`'s approval. Accumulates across Ph3 iterations and resets *only* on the terminal signoff row (`PHASE_PROTOCOL.md §8.6`). Exceeding `tolerant_drift_threshold` (default 40 lines) triggers `fingerprint_reset` at Ph1/Ph2; at Ph3 emits only `W-Ph3-DRIFT-EXCEEDED-TOLERANT` to avoid conflict with the unbounded-loop contract.

**`phase_goal_declared`** — `string`. Human-readable goal for this phase-section, populated on every phase advance from the lookup table below. Renamed at v0.7.4 from `tier_goal_declared`.

| `current_phase` | Canonical `phase_goal_declared` value |
|---|---|
| `Ph1` | "produce a complete first draft with classification and an advisory Evaluator note" |
| `Ph2` | "produce a reviewed and revised section with all CRITICAL findings cleared and a signed ph2_review_completion" |
| `Ph3` | "iterate to convergence under the 2-consecutive-round convergence-metric threshold and sign ph3_convergence_signoff" |
| `Ph3_converged` | "hold post-convergence staging pending MCR admission to Ph4" |
| `Ph4` | "compose the manuscript-wide submission-bound artefact and sign ph4_ship_signoff" |

**`phase_deliverable_path`** — `string (repo-relative path)`. Path to the user-signed exit artefact for the current phase. Renamed at v0.7.4 from `tier_deliverable_path`.

| `current_phase` | Canonical `phase_deliverable_path` value |
|---|---|
| `Ph1` | `reviews/ph1_draft_completion.md` |
| `Ph2` | `reviews/ph2_review_completion.md` |
| `Ph3` | `reviews/ph3_convergence_signoff.md` (terminal row) |
| `Ph3_converged` | `reviews/ph3_convergence_signoff.md` (terminal row, unchanged) |
| `Ph4` | `reviews/ph4_ship_signoff.md` |

**`references_initialized`** — `boolean`. Introduced at v0.10.0 Stage S2 under the snowball-driven reference-scaffolding bundle (architecture: `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §5.4`; strategy: `docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md §3.3`). `true` iff the section's reference corpus has been seeded by the SK-NEW-A `seed-snowball-discovery` skill — operationally, iff `references/REFERENCES.md` exists and carries at least one row in either the core corpus table or the snowball table (the heuristic is the same one used by the migration script's default-set). `false` on a freshly-initialised section and on every section whose `references/REFERENCES.md` is absent or contains only the empty table scaffolds. Default on a freshly-initialised section (or a v0.9.x ledger carried forward without snowball-bundle run): `false`. Writer: the Planner, on the Phase 5.5 log-write that closes the SK-NEW-A clean exit at `run-phase-1` Step 4.5; the same write appends a `seed_snowball_signed` row (trigger 31) to the section's `phase_entry_log`. **Idempotency anchor:** SK-NEW-A reads this field at preflight (`skills/seed-snowball-discovery/SKILL.md §4` precondition clause 4); on `true`, the skill emits `ALREADY_INITIALIZED` no-op and exits without re-running the snowball saturation loop. The user must explicitly clear the field to `false` (or invoke SK-NEW-C `extend-snowball-incremental` for incremental extension) to re-enter SK-NEW-A. **Migration:** `scripts/migrate_v090_to_v100_snowball_fields.py` defaults this field to `true` on sections whose `references/REFERENCES.md` already has a populated core or snowball table at migration time, and to `false` otherwise; once present, the field is left untouched on subsequent migration re-runs (per the script's idempotency contract). **Consumer skill:** SK-NEW-A `seed-snowball-discovery` (`skills/seed-snowball-discovery/SKILL.md`); the Planner is the sole writer.

**`last_coverage_score`** — `float | null`. Introduced at v0.10.0 Stage S4 under the snowball-driven reference-scaffolding bundle (architecture: `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §§4.4, 5.4, 6.5`; strategy: `docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md §5.5`). The most recent claim-coverage score (in `[0.0, 1.0]`) emitted by SK-NEW-B `claim-coverage-audit` at the section's most recent Ph2 entry — operationally, the `covered / total` ratio computed from the section's `claim_coverage_<YYYY-MM-DD>_<cycle_id>.md` audit, recorded with three-decimal-place precision per SK-NEW-B's determinism contract (`skills/claim-coverage-audit/SKILL.md §5`). `null` on a freshly-initialised section, on every section that has not yet entered Ph2, and on every section whose most-recent Ph2 audit returned `E-COVERAGE-AUDIT-FAILED` per `phase_notifications.yaml §4` (the audit-failure outcome does not update the field; the prior value is preserved or the field stays `null`). **Persistence semantics:** the field persists across rounds and across phase movements — a Ph3 retraction → Ph2 re-entry path preserves the most recent `last_coverage_score` so the Planner's Phase 3.8 dispatch can compare the current round's audit verdict against the prior round's score for cross-round regression detection (architecture §5.4 stated consumer; threshold parameter `coverage_regression_floor` default 0.05 surfaceable in `classification.md` at S4.5 calibration). **Writer:** the Planner, on the Phase 3.8 outcome (i) clean-exit and outcome (ii) below-threshold paths, in the same atomic write that appends the cycle's notification rows; outcome (iii) audit-failure paths do NOT update this field. **Migration:** `scripts/migrate_v090_to_v100_snowball_fields.py` defaults this field to `null` on every migrated section (no historical coverage data exists at migration time); once present, the field is left untouched on subsequent migration re-runs. **Consumer skill:** SK-NEW-B `claim-coverage-audit` (`skills/claim-coverage-audit/SKILL.md`) reads via the Planner; SK-NEW-C `extend-snowball-incremental` (`skills/extend-snowball-incremental/SKILL.md`) does NOT read this field directly (the SK-NEW-C dispatch decision is made by the Planner's Phase 3.8 outcome handler from the audit's per-cycle verdict, not from the persisted `last_coverage_score`); the Planner is the sole writer.

**`convergence_metric`** — `float | null`. Most recent Ph3 convergence metric, computed as `diff_lines_vs_previous_round / total_section_lines` (`PHASE_PROTOCOL.md §3.3`). `null` when not at Ph3 or when no Ph3 iteration has yet completed. At v0.8.0, the multi-signal 4-vector shape specified in the v0.8.0 β core P-9/P-10 redesign supersedes this scalar; migration at v0.8.0 via `scripts/migrate_convergence_journal_v075.py [retired from tree]` (see `proposals/v0.8.0_upgrade_architecture.md §3.2 Phase 2.1`).

**`ph1_pstage_declaration`** — `enum | null`. P-stage declared at Ph1 sign-off, from EYgp vocabulary (`"P0"`, `"P1"`, `"P2"`). `null` before Ph1 sign-off. Renamed at v0.7.4 from `t1_pstage_declaration`.

**`ph3_last_activity_at`** — `string (ISO-8601 UTC) | null`. Timestamp of the most recent Planner-observed Ph3 activity. Drives computed `[Ph3-STALE]` per `PHASE_PROTOCOL.md §3.3.1`: `is_stale := (current_phase == "Ph3") AND (ph3_last_activity_at IS NOT NULL) AND (now - ph3_last_activity_at > ph3_staleness_budget)`. A `null` value short-circuits to `[Ph3-STALE] = false`. Default budget: 14 days. Renamed at v0.7.4 from `t3_last_activity_at`.

**`pre_mcr_deep_pass_completed`** — `boolean`. Introduced at v0.8.0 under β-P-9a (pre-MCR Ph3-deep safety-net pass, reframed per Advisor Action A-GK-5 in `proposals/v0.7.5_phase3_refinement_loop_proposal.md §3.P-9a`). `true` iff the section has completed **exactly one** Ph3-deep pass (not Ph3-refine, not Ph3-structural) at any point after the first `user_approval` to Ph3; `false` on every section that has not yet run a Ph3-deep pass or has only run Ph3-refine / Ph3-structural passes. Default on a freshly-initialised section (or a v0.7.4 ledger carried forward without P-9a run): `false`. Writer: the Planner, on the Phase 5.5 log-write that closes a Ph3 iteration whose F6 dispatch plan had `check_profile: deep`. The pre-MCR pass counts as a single iteration against the section's Ph3 budget; the +50% MCR iteration reserve absorbs its cost (§3.P-9a). **MCR admission contract:** `pre_phase_advance_check.py` clause (f) refuses admission with `E-MCR-PRE-DEEP-PASS-REQUIRED` on any section whose value is `false` at MCR-assembly time; the Planner's Phase 8 MCR-assembly surfaces the refusal as a blocking condition. **Role:** safety net for residual misclassifications that the per-check falsification at §3.P-9.1 missed — not the primary correctness guarantee for the Ph3 convergence contract. **Ledger interaction:** the field survives a `ceiling_raised` or `fingerprint_reset` trigger (the completed deep pass is an audit record, not a staging state); it is cleared back to `false` only on a `retraction` trigger that retracts the Ph3 approval under which the deep pass was run. Absent-tolerance: a ledger that omits this field is shape-valid and treated as `false` by the MCR admission gate (see §6.1).

**`phase_entry_log`** — `array<PhaseEntryLogRow>`. Append-only audit trail. Never truncated. Every write to any other field MUST append one row. Row schema in §3 and §3a. Renamed at v0.7.4 from `tier_entry_log`.

---

## 3. `PhaseEntryLogRow` schema (v0.7.4 seven-field shape)

Each row in `phase_entry_log` is an object with the following seven fields. The row widens from v0.7.3's six fields by adding `model_used`, which carries absent-means-null semantics for the Reflector's capability-inversion audit.

```json
{
  "timestamp":   "2026-04-22T14:05:22Z",
  "trigger":     "<one of the enum values below>",
  "prev_phase":  "Ph1" | "Ph2" | "Ph3" | "Ph3_converged" | "Ph4" | null,
  "new_phase":   "Ph1" | "Ph2" | "Ph3" | "Ph3_converged" | "Ph4",
  "actor":       "planner" | "evaluator" | "generator" | "reflector" | "user",
  "notes":       "<freeform string, ≤ 280 chars, optional>",
  "model_used":  "<model slug string>" | null
}
```

The validator `phase_state_validate.py` enforces the set of required field names exactly (missing → `LOG_ROW_MISSING_FIELD` BLOCKER; extra → `LOG_ROW_UNKNOWN_FIELD` MAJOR). `model_used: null` is legal (explicit absence).

### 3.1 The v0.7.4 trigger enum (31 values)

The authoritative enum lives in `PHASE_PROTOCOL.md §6.3` (original 28 values) and `§6.3` additions (triggers 29 and 30 at v0.7.4; trigger 31 added at v0.10.0 Stage S2 under the snowball-driven reference-scaffolding bundle). Summarised here for cross-reference.

| # | `trigger` | When it fires | Typical `prev_phase` → `new_phase` |
|---|---|---|---|
| 1 | `initial_dispatch` | Section created fresh; first row. | `null → Ph1` |
| 2 | `user_approval` | Explicit milestone approval in Ph1 leaves phase unchanged; explicit phase-exit approval advances Ph1 or Ph2. | `Ph1 → Ph1` (milestone-only), `Ph1 → Ph2`, `Ph2 → Ph3`; never Ph3 → Ph4 |
| 3 | `user_rejection` | User rejects; iteration_count increments. | `Ph_n → Ph_n` |
| 4 | `user_defer` | Explicit pause; no ledger movement. | `Ph_n → Ph_n` |
| 5 | `fingerprint_reset` | `cumulative_drift_lines` exceeded `tolerant_drift_threshold` (tolerant) or fingerprint mismatch (strict); at Ph3 emits warning instead. | `Ph_n → Ph_n` |
| 6 | `mcr_admission` | MCR cleared; Ph4 admission manuscript-wide. | `Ph3_converged → Ph4` |
| 7 | `laggard_clearance_cancelled` | User invoked `/cancel-climb` during MCR (name preserved for audit continuity across the LCR→MCR rename). | No movement |
| 8 | `ceiling_locked` | Section reached applicable ceiling. | `Ph_n → Ph_n` |
| 9 | `ceiling_raised` | `/raise-ceiling` invoked or classification updated. | No phase movement |
| 10 | `override_applied` | `section_ceiling_override` written. | No phase movement |
| 11 | `retraction` | User explicitly retracts an approval (one of the three monotonicity-exempt triggers). Exact targets are enumerated; arbitrary deep rollback is illegal. | `Ph2 → Ph1`; `Ph3 → Ph2`; `Ph3_converged → Ph3`; `Ph4 → Ph3` |
| 12 | `ph1_draft_completion_signed` | User signs `ph1_draft_completion.md`. Prerequisite for Ph1→Ph2 advance. | `Ph1 → Ph1` |
| 13 | `imodel_structural_validation_signed` | RETIRED at v0.11.0 with the SD/SR machinery cut. Migrated rows are read-only via `scripts/migrate_v0100_to_v0110_drop_sd_sr.py`; v0.11.0 ledgers do not emit this trigger. | No phase movement |
| 14 | `ph2_review_completion_signed` | User signs `ph2_review_completion.md`. Prerequisite for Ph2→Ph3 advance. | `Ph2 → Ph2` |
| 15 | `escalation_owner_transferred` | `convergence_log.md` records a `transferred_to` event. | No phase movement |
| 16 | `escalation_named_owner_assigned` | ESCALATED-finding owner assignment at Ph2 or Ph3. | No phase movement |
| 17 | `ph3_iteration_round` | One section-scoped iteration within the Ph3 unbounded loop. | `Ph3 → Ph3` |
| 18 | `ph3_convergence_signoff_row` | One appended row in cumulative `ph3_convergence_signoff.md` (not necessarily terminal). | No phase movement |
| 19 | `ph3_stale_reengagement_signoff` | Re-engagement row that clears `[Ph3-STALE]`. | No phase movement; `ph3_last_activity_at` updated |
| 20 | `ph3_convergence_signoff_terminal` | Terminal row bearing `is_terminal: true`; flips `current_phase: Ph3 → Ph3_converged`. | `Ph3 → Ph3_converged` |
| 21 | `mcr_blocked_ph3_stale` | MCR pause due to stale sections (`E-MCR-BLOCKED-Ph3-STALE`). | No movement |
| 22 | `eg7_mcr_readmission_after_class_change` | EG-7 fire at Ph4 forcing Ph3-iteration-then-MCR-replay. One of the three monotonicity-exempt triggers. | `Ph4 → Ph3` |
| 23 | `eg1_ph4_downgrade_to_ph3` | Rule 1–7 grounding violation at Ph4 forcing section back to Ph3. One of the three monotonicity-exempt triggers. Renamed at v0.7.4 from `eg1_t4_downgrade_to_t3`. | `Ph4 → Ph3` |
| 24 | `eg6_override_inconsistency_warning` | Planner warning on an inconsistent override target. Non-blocking. | No phase movement |
| 25 | `m5_wiki_ingest` | Coupling D ingestion at Ph4 close — emit **only** after a governed Wiki ingestion transaction succeeds. On `WIKI_WRITE_TRANSACTION_UNAVAILABLE` do **not** write this success trigger; record deferred status in the reflection report instead. | No phase movement |
| 26 | `plugin_update_proposed_by_planner` | Planner-formalised plugin proposal. | No phase movement |
| 27 | `v0_7_state_rename` | Migration-only rename `Ph4_ready → Ph3_converged`. | Recorded in `notes` |
| 28 | `ph3_accessibility_blocker_surfaced` | Planner refused a `TerminalSignoffRow` write because a Check 8 BLOCKER is open at signoff (`PHASE_PROTOCOL.md §3.3.3`). Introduced at v0.7.2. | No phase movement |
| 29 | `ph3_iteration_round_manuscript` | One manuscript-level Ph3 iteration that touches N≥2 sections under a single revision directive. Emits N rows sharing one `cycle_id`. Introduced at v0.7.4 per P-7 (`PHASE_PROTOCOL.md §3.3.5`). | `Ph3 → Ph3` |
| 30 | `stability_mode_escalated_to_full_ph3` | Automatic escalation from Ph3 stability sub-mode back to full Ph3 when the reduced envelope surfaces a finding. Introduced at v0.7.4 per P-2 (`PHASE_PROTOCOL.md §3.3.2`). | `Ph3 → Ph3` (escalation row only; the full-Ph3 round that follows uses trigger 17 or 29) |
| 31 | `seed_snowball_signed` | SK-NEW-A `seed-snowball-discovery` returned a clean exit at `run-phase-1` Step 4.5: the section's `references/REFERENCES.md` has been seeded by the snowball saturation loop. Within-phase artefact-completion row (analogous to trigger 12 `ph1_draft_completion_signed`); not a phase-advance trigger. The Planner is the actor — it writes the row immediately after SK-NEW-A's clean exit, in the same Phase 5.5 atomic write that flips `references_initialized: true` on the section. **Notes contract:** `notes` SHOULD identify the SK-NEW-A run id (timestamp suffix) and the count of references admitted, broken down by table — e.g., `"SK-NEW-A run 2026-04-27T14:05:22Z — admitted 14 sources (12 core, 2 snowball)"`. ≤ 280 chars per §3a.1. Introduced at v0.10.0 Stage S2 per the snowball-driven reference-scaffolding bundle (`docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §5.4`). | `Ph1 → Ph1` |

**Retired at v0.7.0.** The v0.6.0 trigger `confirmation_failed` is retired; migrated rows are preserved but no v0.7.0+ write path emits this trigger.

**Monotonicity-exempt triggers (enforced by the validator).** The three triggers that license a downward `prev_phase → new_phase` transition are: `retraction`, `eg1_ph4_downgrade_to_ph3`, `eg7_mcr_readmission_after_class_change`. Any other downward transition emits `MONOTONICITY_VIOLATION` (BLOCKER). Source of truth: `scripts/phase_state_validate.py` `MONOTONICITY_EXEMPTIONS`.

---

## 3a. Structured row schemas

Three structured row shapes are consumed by tooling across v0.7.4. Their contracts are specified authoritatively in `PHASE_PROTOCOL.md §6.3a`; this section summarises them for cross-reference. Field counts and semantics are binding.

### 3a.1 `PhaseEntryLogRow` (element of `SectionStateObject.phase_entry_log`)

| Field | Type | Required | Notes |
|---|---|---|---|
| `timestamp` | string (ISO-8601 UTC, `Z`-suffixed) | yes | Monotonically non-decreasing across rows in the same array. |
| `trigger` | enum | yes | One of the 31 values in §3.1. |
| `prev_phase` | enum \| null | yes | One of `"Ph1"` / `"Ph2"` / `"Ph3"` / `"Ph3_converged"` / `"Ph4"`, or `null` for initial rows. |
| `new_phase` | enum | yes | Same enum as `prev_phase` but `null` is **not** legal (the validator fires `LOG_ROW_BAD_NEW_PHASE` BLOCKER on `null`). Non-phase-changing triggers repeat the prior phase in `new_phase` (e.g., `user_rejection` with `prev_phase: Ph2, new_phase: Ph2`) to satisfy the monotonicity check as a no-movement row. |
| `actor` | enum | yes | One of `"planner"` / `"evaluator"` / `"generator"` / `"reflector"` / `"user"`. |
| `notes` | string | optional | ≤ 280 chars. Validator emits `LOG_ROW_NOTES_OVER_280` (MINOR) on exceedance. |
| `model_used` | string \| null | yes | Model slug used to emit this row; absent-means-null semantics. Feeds the Reflector's capability-inversion audit. |

### 3a.2 `TerminalSignoffRow` (row in `reviews/ph3_convergence_signoff.md`)

A cumulative signoff file; the **terminal** row carries `is_terminal: true`. Full contract in `PHASE_PROTOCOL.md §6.3a`. Key invariant: a terminal row with `convergence_metric_value == null` fails with `E-Ph3-CONVERGENCE-NULL-AT-SIGNOFF`; a terminal row attempted while Check 8 carries BLOCKER fails with `E-Ph3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF` (the Reader-Experience defence, `PHASE_PROTOCOL.md §3.3.3`).

**Effect of appending a terminal row:** (i) flips `current_phase: Ph3 → Ph3_converged`; (ii) writes a `ph3_convergence_signoff_terminal` trigger into `phase_entry_log`; (iii) freezes `convergence_log.md` against further appends; (iv) resets `cumulative_drift_lines_since_approval` and `iteration_count_at_current_phase` to `0`.

### 3a.3 `ReengagementSignoffRow` (row in `reviews/ph3_convergence_signoff.md`)

Clears a `[Ph3-STALE]` flag. Does **not** advance the phase. Full contract in `PHASE_PROTOCOL.md §6.3a`.

**Effect of appending a re-engagement row:** (i) updates `ph3_last_activity_at` to `row_timestamp`; (ii) writes a `ph3_stale_reengagement_signoff` trigger into `phase_entry_log`; (iii) does not flip `current_phase`; (iv) does not reset `iteration_count_at_current_phase` or `cumulative_drift_lines_since_approval`.

---

## 4. Fingerprint policy

Three modes (preserved from v0.6.0): `strict`, `tolerant` (default), `off`. Tolerant canonicalization rules (percent escapes, inline/display math preservation, verbatim-environment passthrough, whitespace collapse, `--`/`---` normalization to `U+2013`/`U+2014`, `\label`/`\ref` preservation, comment stripping) are unchanged from v0.6.0; implementation formerly in `scripts/tier_state_canonicalize.py` *[retired from tree]* (it had been retained under the legacy file name during the v0.7.4 minor as a stable-import contract for consumers). Drift thresholds: `per_edit_drift_threshold` (strict → any diff triggers `fingerprint_reset`); `tolerant_drift_threshold` (default 40 lines; exceedance at Ph3 emits `W-Ph3-DRIFT-EXCEEDED-TOLERANT` rather than forcing re-review); `fingerprint_staleness_budget` (24 hours default); `ph3_staleness_budget` (14 days default, drives `[Ph3-STALE]` per `PHASE_PROTOCOL.md §3.3.1`).

---

## 5. Writer discipline

**Single writer: the Planner.** Evaluator, Generator, and Reflector read `phase_state.json` but never write. The Planner writes in three phases:

- **Phase 0 session bootstrap** — validates shape via `phase_state_validate.py`, verifies the `last_updated` invariant, checks fingerprint staleness, recomputes fingerprints for stale sections, computes `[Ph3-STALE]` for every Ph3 section.
- **Phase 5.5 post-approval log-write** — on every approval / rejection / defer / retraction / signed-artefact trigger, updates the affected section's fields and appends a `phase_entry_log` row. `phase_goal_declared` and `phase_deliverable_path` are rewritten from the §2.1 lookup tables on every phase change; `ph1_pstage_declaration` is populated on the Ph1→Ph2 advance; `ph3_last_activity_at` is refreshed on every Ph3-iteration or re-engagement row.
- **Phase 6 MCR cycle-step append** — during an MCR climbing cycle, appends `phase_entry_log` rows for each section as they climb.

**Concurrency contract.** Writes are atomic via `.tmp → rename` with advisory lockfile `reviews/phase_state.json.lock` and mtime-sha256 re-check before the final rename; any drift between pre-read snapshot and pre-rename re-read aborts with `[CONCURRENCY-DETECTED]`. Pre-rename backup to `reviews/phase_state.json.bak.<timestamp>` (retention: last 10). `[STATE-CORRUPT]` recovery uses these backups.

---

## 6. Validation

The runtime validator is `scripts/phase_state_validate.py` (v0.7.4). The legacy `scripts/tier_state_validate.py` is a forwarding shim that re-execs `phase_state_validate.py` with identical argv and emits `W-DUAL-READ-LEGACY` to stderr; the shim is removed at v0.7.5 RC. Dual-read behaviour: if `phase_state.json` exists, validate at v0.7.4 shape; else if `tier_state.json` exists, emit `DEPRECATION_WARNING` (MINOR) and translate field names in-memory (`current_tier → current_phase`, `T1..T4 → Ph1..Ph4`, etc.) before validation; if both exist, prefer `phase_state.json` and emit `MIXED_STATE` (MAJOR).

### 6.1 Validator finding codes

Codes emitted by `scripts/phase_state_validate.py` at v0.7.4. Codes are grounded to the validator source; this table is the source of truth for finding-code semantics in CI surfaces. Codes named in `PHASE_PROTOCOL.md` and in `pre_phase_advance_check.py` but not emitted by this validator are tracked under "Contracts enforced elsewhere" below.

| Code | Severity | Condition | Source |
|---|---|---|---|
| `DOC_NOT_OBJECT` | BLOCKER | Top-level JSON is not an object. | `_validate_doc` |
| `DOC_SECTIONS_NOT_OBJECT` | BLOCKER | `sections` present but not an object (e.g., a v0.7.0 array shape). | `_validate_doc` |
| `DOC_NO_SECTIONS` | MAJOR | No sections found at top-level or under `sections` key. | `_validate_doc` |
| `SECTION_NOT_OBJECT` | BLOCKER | A section value is not an object. | `_validate_section` |
| `SECTION_MISSING_FIELD` | BLOCKER | A section lacks `current_phase` or `phase_entry_log`. | `_validate_section` |
| `SECTION_BAD_CURRENT_PHASE` | BLOCKER | `current_phase` outside `{Ph1, Ph2, Ph3, Ph3_converged, Ph4}`. | `_validate_section` |
| `SECTION_LOG_NOT_LIST` | BLOCKER | `phase_entry_log` is present but not a list. | `_validate_section` |
| `SECTION_LOG_EMPTY` | MAJOR | `phase_entry_log` is empty on a bootstrapped section. | `_validate_section` |
| `SECTION_CURRENT_PHASE_DIVERGENT` | MAJOR | `current_phase` does not match the last log row's `new_phase`. | `_validate_section` |
| `SECTION_BAD_PRE_MCR_DEEP_PASS_TYPE` | MINOR | `pre_mcr_deep_pass_completed` is present on a section but is neither `true` nor `false` (introduced v0.8.0 under β-P-9a; absence is tolerated and treated as `false` by the MCR admission gate). | `_validate_section` |
| `SECTION_BAD_REFERENCES_INITIALIZED_TYPE` | MINOR | `references_initialized` is present on a section but is neither `true` nor `false` (introduced v0.10.0 Stage S2 under the snowball-driven reference-scaffolding bundle; absence is tolerated and treated as `false` by SK-NEW-A's preflight idempotency guard). | `_validate_section` |
| `SECTION_BAD_LAST_COVERAGE_SCORE_TYPE` | MINOR | `last_coverage_score` is present on a section but is neither `null` nor a number in `[0.0, 1.0]` (introduced v0.10.0 Stage S4 under the same bundle; absence is tolerated and treated as `null` by SK-NEW-B's cross-round regression-detection logic). | `_validate_section` |
| `LOG_ROW_NOT_OBJECT` | BLOCKER | A log row is not an object. | `_validate_log_row` |
| `LOG_ROW_MISSING_FIELD` | BLOCKER | A log row is missing any of the seven required fields. | `_validate_log_row` |
| `TERMINAL_ROUND_ID_INVALID` | BLOCKER | `terminal_round_id` violates the biconditional with `terminal_phase_reached`: terminal true with the field absent, null, non-string, or not matching `round_YYYY-MM-DD_NNN`; or terminal false with a non-null id. A legacy terminal ledger lacking the field lands here and requires explicit re-attestation — never inference. |
| `LOG_ROW_UNKNOWN_FIELD` | MAJOR | A log row carries an unknown field (e.g., v0.6.0 `from_tier`, `to_tier`, `scope`, `cycle_id`, `detail`). | `_validate_log_row` |
| `LOG_ROW_BAD_PREV_PHASE` | MAJOR | `prev_phase` is non-null and not a legal phase code. | `_validate_log_row` |
| `LOG_ROW_BAD_NEW_PHASE` | BLOCKER | `new_phase` is not a legal phase code. | `_validate_log_row` |
| `LOG_ROW_EMPTY_TRIGGER` | MAJOR | `trigger` is not a non-empty string. | `_validate_log_row` |
| `LOG_ROW_BAD_ACTOR` | MAJOR | `actor` outside `{planner, evaluator, generator, reflector, user}`. | `_validate_log_row` |
| `LOG_ROW_NOTES_OVER_280` | MINOR | `notes` exceeds the 280-char ceiling. | `_validate_log_row` |
| `LOG_ROW_BAD_MODEL_USED` | MINOR | `model_used` is neither string nor null. | `_validate_log_row` |
| `MONOTONICITY_VIOLATION` | BLOCKER | Downward `prev_phase → new_phase` transition under a non-exempt trigger. | `_validate_monotonicity` |
| `DEPRECATION_WARNING` | MINOR | Dual-read of legacy `tier_state.json` under the v0.7.4 shim. | `_xlate_legacy` |
| `MIXED_STATE` | MAJOR | Both `phase_state.json` and `tier_state.json` present; preferring `phase_state.json`. | `main` |

**Exit codes.** `0` PASS; `1` usage error; `2` file I/O or parse error; `3` validation findings (MINOR or MAJOR only); `4` BLOCKER findings present.

**Contracts enforced elsewhere.** The following contracts named in `PHASE_PROTOCOL.md §§6.1, 7, 8, 9` are enforced by `scripts/pre_phase_advance_check.py` (clauses (a)–(h); clause (e) retired at v0.11.0) at advance time, not by this validator: required `SectionStateObject` fields beyond the two validator-required ones; signed exit artefacts gating advances (`E-MISSING-PH1-SIGNOFF`, `E-MISSING-PH2-SIGNOFF`); convergence-metric null-at-terminal (`E-Ph3-CONVERGENCE-NULL-AT-SIGNOFF`); Check 8 accessibility gate at terminal signoff (`E-Ph3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF`, introduced v0.7.2); escalation-ownership (`E-ESCALATION-WITHOUT-OWNER`, `E-OWNERSHIP-TRANSFER-WITHOUT-RATIONALE`); MCR `[Ph3-STALE]` admission block (`E-MCR-BLOCKED-Ph3-STALE`); pre-MCR Ph3-deep safety-net pass (`E-MCR-PRE-DEEP-PASS-REQUIRED`, introduced v0.8.0 under β-P-9a; clause (f) extension authored at P2.6 — refuses MCR admission on any section whose `pre_mcr_deep_pass_completed` is `false` or absent); SK-NEW-A `seed-snowball-discovery` preflight idempotency guard (`ALREADY_INITIALIZED` no-op, introduced v0.10.0 Stage S2 — refuses re-entry to the snowball saturation loop on any section whose `references_initialized` is `true` and whose `references/REFERENCES.md` carries non-empty core or snowball tables; authored at `skills/seed-snowball-discovery/SKILL.md §4` precondition clause 4, not in this validator); SK-NEW-B `claim-coverage-audit` cross-round regression-detection (introduced v0.10.0 Stage S4 — the Planner's Phase 3.8 outcome handler at `agents/planner.md` reads `last_coverage_score` before dispatch and compares the post-audit score against the prior value; regression beyond `coverage_regression_floor` parameter (default 0.05; surfaceable in `classification.md` at S4.5) emits a non-blocking advisory line in the cycle log; the field's per-round write is also at the Planner, not in this validator). These are not duplicated here — they are authored where they run.

### 6.2 Pre-advance check

Before any phase-changing `user_approval` write, the Planner invokes `scripts/pre_phase_advance_check.py`, which runs the seven-clause guardrail from `PHASE_PROTOCOL.md §7.3` (clause (e) retired at v0.11.0 with the SD/SR machinery cut): (a) exit-artefact presence and well-formedness, (b) required `SectionStateObject` fields populated for the target phase, (c) ESCALATED-finding owner presence plus non-empty `transfer_rationale`, (d) `ph1_pstage_declaration` set before Ph2 admission, (f) MCR clearance before Ph4 admission including the ceiling-lock disjunction and `[Ph3-STALE] = false` on every section, (g) row-shape conformance against §3a, (h) Check 8 accessibility gate at any attempted `TerminalSignoffRow` write. Clause (h) is the Reader-Experience defence; its refused write does not consume Ph3 iteration budget.

---

## 7. Migration

### 7.1 v0.7.3 → v0.7.4 (primary path)

Projects carrying `reviews/tier_state.json` at `schema_version: "0.7.3"` were historically upgraded via `migrate_v073_to_v074_tier_to_phase.py` (script since retired from the tree; semantics preserved here for the record). The script performs a single-pass idempotent migration: renames `tier_state.json → phase_state.json`, applies the field renames enumerated in §1.1 and §2.1, widens every log row from six to seven fields (adding `model_used: null`), renames the `eg1_t4_downgrade_to_t3` trigger to `eg1_ph4_downgrade_to_ph3`, renames companion exit-artefact files `reviews/t{1,2,3}_*_completion.md → reviews/ph{1,2,3}_*_completion.md`, and produces `reviews/migration_report_v073_to_v074.md` for user review. The Planner enforces user review of the migration report as a blocking Phase 0 hold.

**Idempotency.** If `reviews/phase_state.json` already exists, the script treats the migration as complete and re-emits the report (with a note). If any log row already has seven fields, it is left untouched. If `default_final_phase` is already set in classification frontmatter, no rename is attempted.

**Companion migration.** `scripts/migrate_convergence_log_v074.py [retired from tree]` splits the v0.7.3 convergence log per the P-4 contract (`PHASE_PROTOCOL.md §3.3.4`) and backfills `manuscript_hash` on every journal row. Run after the primary migration.

### 7.2 v0.6.0 → v0.7.0 (archival)

`scripts/migrate_v060_to_v070.py [retired from tree]` historically introduced the now-retired `milestone_assignment` split. Current migration treats that field only as archival input, removes it from the live projection, and requires explicit unsplit M1–M5 adjudication under `milestone_framework`. Projects still on v0.5.5 or earlier run `migrate_v055_to_v060.py` first.

### 7.3 Archive and idempotency

Before rewriting any ledger, the migration script archives the pre-migration file at `reviews/<pre>.v0.7.3.json` (retained indefinitely). Re-runs detect target schema on read and exit no-op.

---

## 8. Appendix — canonical seed template

Freshly-bootstrapped `phase_state.json` for a new v0.7.4 manuscript with two sections:

```json
{
  "schema_version": "0.7.4",
  "manuscript_id": "example-project",
  "default_final_phase": "Ph3",
  "fingerprint_mode": "tolerant",
  "terminal_phase_reached": false,
  "last_updated": "2026-04-22T14:05:22Z",
  "phase_vocabulary": "lifecycle_v0.7.4",
  "sections": {
    "1. Introduction": {
      "heading_path": ["1. Introduction"],
      "current_phase": "Ph1",
      "last_approved_phase": null,
      "ceiling_locked": false,
      "section_ceiling_override": null,
      "iteration_count_at_current_phase": 0,
      "last_scope_fingerprint": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "fingerprint_computed_at": "2026-04-22T14:05:22Z",
      "cumulative_drift_lines_since_approval": 0,
      "phase_goal_declared": "produce a complete first draft with classification and an advisory Evaluator note",
      "phase_deliverable_path": "reviews/ph1_draft_completion.md",
      "references_initialized": false,
      "last_coverage_score": null,
      "convergence_metric": null,
      "ph1_pstage_declaration": null,
      "ph3_last_activity_at": null,
      "pre_mcr_deep_pass_completed": false,
      "phase_entry_log": [
        {
          "timestamp": "2026-04-22T14:05:22Z",
          "trigger": "initial_dispatch",
          "prev_phase": null,
          "new_phase": "Ph1",
          "actor": "planner",
          "notes": "Section initialised on fresh v0.7.4 project.",
          "model_used": null
        }
      ]
    },
    "2. Background": {
      "heading_path": ["2. Background"],
      "current_phase": "Ph1",
      "last_approved_phase": null,
      "ceiling_locked": false,
      "section_ceiling_override": null,
      "iteration_count_at_current_phase": 0,
      "last_scope_fingerprint": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
      "fingerprint_computed_at": "2026-04-22T14:05:22Z",
      "cumulative_drift_lines_since_approval": 0,
      "phase_goal_declared": "produce a complete first draft with classification and an advisory Evaluator note",
      "phase_deliverable_path": "reviews/ph1_draft_completion.md",
      "references_initialized": false,
      "last_coverage_score": null,
      "convergence_metric": null,
      "ph1_pstage_declaration": null,
      "ph3_last_activity_at": null,
      "pre_mcr_deep_pass_completed": false,
      "phase_entry_log": [
        {
          "timestamp": "2026-04-22T14:05:22Z",
          "trigger": "initial_dispatch",
          "prev_phase": null,
          "new_phase": "Ph1",
          "actor": "planner",
          "notes": "Section initialised on fresh v0.7.4 project.",
          "model_used": null
        }
      ]
    }
  }
}
```

---

## 9. Cross-reference index

- `PHASE_PROTOCOL.md §1` — ladder overview (Ph1 Plan & Draft / Ph2 Review & Revise / Ph3 Iterate & Converge / Ph4 Finalize & Close).
- `PHASE_PROTOCOL.md §2` — P-stage theoretical framing.
- `PHASE_PROTOCOL.md §3` — per-phase specification, including §3.2.1 (ownership carryforward), §3.3.1 (`[Ph3-STALE]` dual-state semantics), §3.3.2 (Ph3 stability sub-mode), §3.3.3 (Check 8 accessibility convergence gate), §3.3.4 (P-4 convergence-log contract split), §3.3.5 (manuscript-level Ph3 iteration batching — trigger 29), §3.3.6 (ceiling-lock termination ranking — P-8), §3.5 (Ph4R sibling), §3.6 (Ph4 terminal-phase composition). (§3.1.1 i\* structural-completeness contract and §3.1.2 SD/SR opt-in gate retired at v0.11.0.)
- `PHASE_PROTOCOL.md §4` — milestone supersession (M1–M5 → Ph1–Ph4).
- `PHASE_PROTOCOL.md §5` — agent role matrix (Reflector re-expansion, Planner gatekeeper, Evaluator read contract, proposal/retirement criteria).
- `PHASE_PROTOCOL.md §6` — authoritative schema delta (§6.0 invariant lift, §6.1 top-level additions, §6.2 section-level additions, §6.3 trigger-enum additions including triggers 29 and 30, §6.3a row schemas, §6.4 migration semantics).
- `PHASE_PROTOCOL.md §7` — Escalation Gates EG-1 … EG-7.
- `PHASE_PROTOCOL.md §8` — approval semantics, including §8.1 advance rule, §8.5 explicit phase-down, §8.7 persistence contract.
- `PHASE_PROTOCOL.md §9` — MCR Ph4 admission gate, including §9.3 `[Ph3-STALE]` admission pause, §9.4 ceiling-lock disjunction, §9.5 EG-7 re-admission.
- `PHASE_PROTOCOL.md §10` — Rule 1 full-file reads at every phase (phase-gated digest exception retired at v0.7.4).
- `PHASE_PROTOCOL.md §11` — retired constructs ledger.
- `PHASE_PROTOCOL.md §12` — migration from v0.6.0.
- `PHASE_PROTOCOL.md §13` — success metrics.
- `AGENT_ORCHESTRATION.md §§8.2a–8.2b` — Escalation Log and phase-state ledger integration.
- `agents/planner.md` §§Phase 0 / Phase 5.5 / Phase 6 — writer entry points for this schema.
- `phase_notifications.yaml` — notification templates keyed on the v0.7.4 trigger enum.
- `scripts/phase_state_validate.py` — authoritative v0.7.4 validator (see §6.1).
- `scripts/tier_state_validate.py` — deprecated forwarding shim; removed at v0.7.5 RC.
- `scripts/migrate_v073_to_v074_tier_to_phase.py [retired from tree]` — v0.7.3 → v0.7.4 migration (see §7.1).
- `scripts/migrate_convergence_log_v074.py [retired from tree]` — companion P-4 convergence-log split.
- `scripts/migrate_v060_to_v070.py [retired from tree]` — archival v0.6.0 → v0.7.0 migration.
- `scripts/pre_phase_advance_check.py` — pre-advance guardrail (clauses (a)–(h); see §6.2). Canonical entry point; a legacy duplicate `pre_tier_advance_check.py` was removed from the harness tree (identical bytes to this file through v0.8.2).
- `scripts/tier_state_canonicalize.py` — fingerprint canonicalizer (unchanged from v0.6.0; retained under the legacy filename during the v0.7.4 minor as a stable-import contract).

---

*2026-04-26 (v0.10.0 Stage S2 — snowball-driven reference-scaffolding bundle): `SectionStateObject` 16 → 17 fields via `references_initialized: bool` (S4 will land the 18th field `last_coverage_score: float | null`); §3.1 trigger enum 30 → 31 via `seed_snowball_signed` (within-phase artefact-completion row, Planner actor, `Ph1 → Ph1`); §1.1 schema_version commentary updated to identify v0.10.0 RC as the vocabulary roll point (the bump from `"0.7.4"` to `"0.10.0"` lands via `scripts/migrate_v090_to_v100_snowball_fields.py`); validator type-check `SECTION_BAD_REFERENCES_INITIALIZED_TYPE` (MINOR) added to §6.1; SK-NEW-A `seed-snowball-discovery` preflight `ALREADY_INITIALIZED` no-op cross-referenced under "Contracts enforced elsewhere"; seed template bumped. See `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §5.4` and `docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md §3.3`.*

*2026-04-26 (v0.10.0 Stage S4 — same bundle, Ph2-side wiring): `SectionStateObject` 17 → 18 fields via `last_coverage_score: float | null` (final v0.10.0 shape); validator type-check `SECTION_BAD_LAST_COVERAGE_SCORE_TYPE` (MINOR; non-null values must be a number in `[0.0, 1.0]`) added to §6.1; SK-NEW-B `claim-coverage-audit` cross-round regression-detection at `agents/planner.md §Phase 3.8` cross-referenced under "Contracts enforced elsewhere"; §2 sample JSON and §8 seed template both bumped to include the field at `null`. The trigger enum is unchanged at 31 values (S4 introduces no new trigger); `last_coverage_score` is a state field written at every Ph2 audit clean-exit / below-threshold path, not a phase-advance gate. See `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §§4.4, 5.4, 6.5` and `docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md §5.5`.*
