


# Milestone Feedback and Handoff Framework Implementation Plan

**Status:** Implemented for release `0.28.0`; post-review verification passed 2026-07-14
**Approval provenance:** User approval in session on 2026-07-13; implementation record refreshed 2026-07-14

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Add an enforceable M1-M5 deliverable, feedback, adjudication, and handoff contract to the co-author harness while preserving Ph1-Ph4 as the manuscript revision/readiness axis and binding reader-accessibility policy/evidence across M1, M3, M4, and M5.

**Architecture:** Extend `reviews/phase_state.json` with one Planner-owned `milestone_framework` namespace. Store accepted handoffs as hash-bound F9 JSON evidence, compute explicit gate outcomes, generate human lifecycle views, and migrate legacy projects through a dry-run/user-adjudication workflow. The RE essay supplies the positive design case; INF3130 supplies negative and migration fixtures.

**Tech Stack:** Markdown protocols, JSON/JSON Schema, Python 3 standard library, PowerShell project wrappers, Bash release gate.

## Global Constraints

- Grounding and root filesystem-integrity rules remain non-overridable.
- `reviews/phase_state.json` remains the only lifecycle state authority.
- Planner remains the sole state writer; every write uses the existing atomic/concurrency contract.
- M1-M5 and Ph1-Ph4 remain orthogonal.
- Plans, gates, checklists, reports, and derived views cannot satisfy milestone deliverable slots.
- Accepted M4/M5 state binds exact manuscript bytes.
- Legacy migration never fabricates feedback, approvals, or lineage.
- No INF3130 mutation or `/run-phase-4` occurs in this implementation until the migration task is separately approved.
- Reader accessibility must operate from a package-local semantic authority and one machine-consumed resolved profile; a dangling portfolio cross-reference cannot be a runtime dependency.
- The banded cadence architecture is user-approved; its profile-owned numeric calibration remains provisional and tunable.
- Do not assign the release version until the final release task.

---

## File structure

### New normative files

- `references/MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md` — canonical milestone semantics, precedence, feedback classes, reopening, and gate outcomes.
- `references/schemas/milestone_framework.schema.json` — schema for the `phase_state.json.milestone_framework` namespace.
- `references/schemas/f9_milestone_handoff.schema.json` — strict F9 evidence schema.
- `references/templates/f9_milestone_handoff.json` — bootstrap template.
- `references/milestone_exemplars.json` — externally governed exemplar registry, initially empty.
- `references/policies/reader_accessibility.v1.json` — machine-consumed thresholds, phase scope, aggregation, lexicon routing, and remediation order.
- `references/schemas/reader_accessibility_profile.schema.json` — schema for package and project-resolved accessibility profiles.

### New executable files

- `scripts/milestone_framework_validate.py` — deterministic state, lineage, hash, feedback, and handoff validator.
- `scripts/milestone_framework_smoketest.py` — generated temporary-project fixtures for positive and negative predicates.
- `scripts/render_lifecycle_state.py` — deterministic Markdown renderer from `phase_state.json`.
- `scripts/render_lifecycle_state_smoketest.py` — round-trip and drift tests.
- `scripts/migrate_legacy_milestones.py` — dry-run-first legacy inventory and migration writer.
- `scripts/migrate_legacy_milestones_smoketest.py` — ambiguity, idempotence, archive, and rollback tests.
- `scripts/reader_accessibility_policy.py` — profile loader, project override resolver, and provenance hasher.
- `scripts/reader_accessibility_contract_smoketest.py` — authority, threshold-parity, override, dispatch, and gate-wiring tests.

### Existing files to modify

- `references/MANIFEST.md`
- `references/general_research_project_guidelines.md`
- `references/AGENT_ORCHESTRATION.md`
- `references/M1_M2_M3_PLANNING_PHASE_README.md`
- `references/PROJECT_BOOTSTRAP.md`
- `references/PHASE_PROTOCOL.md`
- `references/phase_state_schema.md`
- `references/ARTEFACT_FRONTMATTER_SCHEMA.md`
- `references/AGENT_CONTRACTS.md`
- `references/phase_notifications.yaml`
- `references/READER_ACCESSIBILITY.md`
- `references/DETERMINISTIC_CHECKS.md`
- `references/SAFEGUARD_LAYER.md`
- `references/STYLE_COMMITMENTS.md`
- `references/lay_term_lexicons.md`
- `skills/accessibility-overlay/SKILL.md`
- `skills/accessibility-overlay/references/sub_checks.md`
- `agents/planner.md`
- `agents/evaluator.md`
- `agents/generator.md`
- `agents/reflector.md`
- `scripts/phase_state_validate.py`
- `scripts/pre_phase_advance_check.py`
- `scripts/sk20_preflight_gate.py`
- `scripts/audit/run_all.py`
- `scripts/check8_g_prefilter.py`
- `scripts/check8_h_prefilter.py`
- `scripts/release-gate.sh`
- `docs/agent-instructions/harness-discovery-lifecycle.md`

---

### Task 1: Author the canonical milestone protocol

**Files:**
- Create: `references/MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md`
- Modify: `references/general_research_project_guidelines.md`
- Modify: `references/AGENT_ORCHESTRATION.md`
- Modify: `references/M1_M2_M3_PLANNING_PHASE_README.md`
- Modify: `references/MANIFEST.md`

**Interfaces:**
- Consumes: architecture decisions in `docs/superpowers/specs/2026-07-13-milestone-feedback-framework-architecture.md`.
- Produces: named normative sections referenced by schemas, agents, and validators.

- [x] **Step 1: Write the protocol with fixed headings**

Required headings, in order:

```markdown
# Milestone Feedback and Handoff Protocol
## 1. Status and scope
## 2. Orthogonal milestone and phase axes
## 3. Authority and precedence
## 4. Milestone deliverable contracts
## 5. Artifact roles and lineages
## 6. Feedback provenance and adjudication
## 7. F9 handoff evidence
## 8. Reopening and downstream staleness
## 9. Gate outcomes and exit semantics
## 10. Native projects
## 11. Legacy migration
## 12. Derived views
## 13. Exemplar governance
## 14. Validator codes
```

- [x] **Step 2: Replace supersession language**

In `AGENT_ORCHESTRATION.md §10`, replace the claim that phases supersede milestones with:

```markdown
Milestones and phases are orthogonal. Milestones name project deliverables and accepted handoffs. Phases name the revision/readiness state of the active artifact or sections. M1-M3 normally execute within Ph1; M4 spans Ph2-Ph3; M5 closes at Ph4. Neither vocabulary supersedes the other.
```

- [x] **Step 3: Reconcile historical M1-M3 instructions**

Update `M1_M2_M3_PLANNING_PHASE_README.md` so Planner/user feedback is not mislabeled Evaluator feedback while Evaluator remains dormant at Ph1.

- [x] **Step 4: Route the protocol through MANIFEST**

Add one routing row for project lifecycle/milestone work and one component inventory row naming the new protocol.

- [x] **Step 5: Verify terminology coherence**

Run:

```powershell
rg -n "milestones.*supersed|superseded.*milestone|handoff to Evaluator" references/AGENT_ORCHESTRATION.md references/M1_M2_M3_PLANNING_PHASE_README.md
```

Expected: zero live-contract hits; historical discussion is explicitly labeled historical.

- [x] **Step 6: Commit**

```powershell
git add references/MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md references/general_research_project_guidelines.md references/AGENT_ORCHESTRATION.md references/M1_M2_M3_PLANNING_PHASE_README.md references/MANIFEST.md
git commit -m "docs: define milestone feedback and handoff protocol"
```

---

### Task 2: Define milestone and F9 schemas test-first

**Files:**
- Create: `references/schemas/milestone_framework.schema.json`
- Create: `references/schemas/f9_milestone_handoff.schema.json`
- Create: `references/templates/f9_milestone_handoff.json`
- Create: `scripts/milestone_framework_smoketest.py`

**Interfaces:**
- Consumes: exact enums and fields from Task 1.
- Produces: `validate_milestone_namespace(value)` and F9 fixture shapes consumed by Task 3.

- [x] **Step 1: Write failing schema tests**

The smoke test creates temporary ledgers and asserts these cases:

```python
CASES = {
    "valid_native_chain": 0,
    "missing_milestone_purpose": 4,
    "m4_plan_as_deliverable": 4,
    "m5_checklist_as_deliverable": 4,
    "missing_feedback_provenance": 4,
    "two_primary_lineages": 4,
    "handoff_without_approval": 4,
    "not_applicable_without_authority": 4,
}
```

Run:

```powershell
python scripts/milestone_framework_smoketest.py
```

Expected before implementation: failure because schemas and validator do not exist.

- [x] **Step 2: Write `milestone_framework.schema.json`**

Require exactly M1-M5 under `milestones`, the enums from the architecture, one `primary_lineage`, milestone `purpose`, `required_inputs`, `exit_criteria`, `artifacts`, `feedback_records`, `approval`, `handoff`, and `dependency_state`.

- [x] **Step 3: Write `f9_milestone_handoff.schema.json`**

Require:

```json
{
  "artifact_family": "F9",
  "contract_version": "1.0.0",
  "project": "project-id",
  "lineage_id": "main",
  "from_milestone": "M1",
  "to_milestone": "M2",
  "predecessor_packet": null,
  "deliverable": {
    "role": "deliverable",
    "path": "research_notes/project_memo.md",
    "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
    "bytes": 1
  },
  "inputs_consumed": [],
  "decisions_frozen": [],
  "feedback_dispositions": [],
  "open_debts": [],
  "next_milestone_instructions": [],
  "approval": {
    "authority": "user",
    "evidence_path": "reviews/approval.md",
    "approved_at": "2026-07-13T18:00:00Z"
  }
}
```

- [x] **Step 4: Write a syntactically valid template**

Use explicit empty arrays and `null` only where the schema permits it. Every required example value must satisfy its schema; instructional sentinel strings are forbidden.

- [x] **Step 5: Compile JSON and Python**

```powershell
Get-Content -Raw references/schemas/milestone_framework.schema.json | ConvertFrom-Json | Out-Null
Get-Content -Raw references/schemas/f9_milestone_handoff.schema.json | ConvertFrom-Json | Out-Null
python -m py_compile scripts/milestone_framework_smoketest.py
```

Expected: exit 0.

- [x] **Step 6: Commit**

```powershell
git add references/schemas/milestone_framework.schema.json references/schemas/f9_milestone_handoff.schema.json references/templates/f9_milestone_handoff.json scripts/milestone_framework_smoketest.py
git commit -m "test: define milestone and handoff schema cases"
```

---

### Task 3: Implement deterministic milestone validation

**Files:**
- Create: `scripts/milestone_framework_validate.py`
- Modify: `scripts/phase_state_validate.py`
- Modify: `references/phase_state_schema.md`

**Interfaces:**
- Consumes: `phase_state.json.milestone_framework` and F9 packets.
- Produces: outcome JSON and exit codes `0`, `1`, `2`, or `4`.

- [x] **Step 1: Implement stable finding and outcome types**

```python
class Outcome(str, Enum):
    READY = "READY"
    LEGACY_READY = "LEGACY_READY"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    MISCONFIGURED = "MISCONFIGURED"

@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    path: str
    message: str
```

- [x] **Step 2: Implement the required predicates**

Implement one function per code:

```python
CHECKS = (
    "MF-STRUCTURE", "MF-ROLE", "MF-CANON", "MF-BINDING",
    "MF-HANDOFF", "MF-FEEDBACK", "MF-LINEAGE", "MF-REOPEN",
    "MF-PHASE", "MF-EXPORT", "MF-DERIVED", "MF-OVERRIDE",
    "MF-STATUS", "MF-EXEMPLAR",
)
```

Every malformed but parseable shape returns findings; no `.values()` or field access occurs before type checking.

- [x] **Step 3: Bind current bytes**

Use `hashlib.sha256(path.read_bytes()).hexdigest()` and `path.stat().st_size`. Accepted state fails when either differs from the ledger or F9 packet.

- [x] **Step 4: Extend phase-state validation**

When `milestone_framework` exists, validate it. When absent:

- native project under the new contract: `MF-STRUCTURE` BLOCKER;
- explicit approved legacy migration boundary: `LEGACY_READY` warning;
- project with authorized N/A: `NOT_APPLICABLE`;
- implicit absence: `MISCONFIGURED`.

- [x] **Step 5: Run the smoke test**

```powershell
python scripts/milestone_framework_smoketest.py
```

Expected: all named cases pass; process exit 0.

- [x] **Step 6: Run existing phase-state tests**

```powershell
python scripts/pre_phase_advance_phase_state_smoketest.py
python scripts/migrate_v0150pre_stage_profile_smoketest.py
```

Expected: both exit 0.

- [x] **Step 7: Commit**

```powershell
git add scripts/milestone_framework_validate.py scripts/phase_state_validate.py references/phase_state_schema.md scripts/milestone_framework_smoketest.py
git commit -m "feat: validate milestone feedback and handoff state"
```

---

### Task 4: Integrate milestone gates with Planner and phases

**Files:**
- Modify: `agents/planner.md`
- Modify: `agents/generator.md`
- Modify: `agents/reflector.md`
- Modify: `references/AGENT_CONTRACTS.md`
- Modify: `references/PHASE_PROTOCOL.md`
- Modify: `scripts/pre_phase_advance_check.py`
- Modify: `references/phase_notifications.yaml`

**Interfaces:**
- Consumes: validator outcomes from Task 3.
- Produces: milestone start, accept, reopen, handoff, and stale-dependency events.

- [x] **Step 1: Add Planner sole-writer workflow**

Planner sequence:

```text
read state -> verify mtime/hash -> classify feedback -> write F9 -> obtain approval
-> atomically append milestone event and hashes -> rerun validator -> render view
```

- [x] **Step 2: Add Generator and Reflector boundaries**

Generator reads the consumed predecessor packet and writes manuscript/revision-log changes only. Reflector audits provenance, hash continuity, and derived-view state. Neither writes milestone state.

- [x] **Step 3: Add phase gate clauses**

`pre_phase_advance_check.py` must enforce:

- Ph1→Ph2: M1-M3 each produce `READY`, `LEGACY_READY`, or authorized `NOT_APPLICABLE` and form one consumed chain.
- Ph4 admission: M4 handoff accepted plus existing MCR conditions.
- Ph4 terminal close: M5 current-hash approval, no stale upstream handoff, G.4 and terminal evidence present.

While editing the gate, replace the stale `t3_convergence_signoff.md` lookup with the canonical Ph3 convergence-signoff filename already used by the current phase protocol. Add a fixture proving the canonical file is recognized and the stale name is rejected.

- [x] **Step 4: Add reopening behavior**

Upstream reopening emits stale dependency findings. The script does not auto-demote phases; it blocks and routes the decision to Planner/user authority.

- [x] **Step 5: Add controlled malformed-input tests**

Extend the smoke test with a list-shaped `sections` value and assert a stable BLOCKER, not an exception traceback.

- [x] **Step 6: Verify**

```powershell
python scripts/milestone_framework_smoketest.py
python scripts/pre_phase_advance_phase_state_smoketest.py
```

Expected: exit 0.

- [x] **Step 7: Commit**

```powershell
git add agents/planner.md agents/generator.md agents/reflector.md references/AGENT_CONTRACTS.md references/PHASE_PROTOCOL.md scripts/pre_phase_advance_check.py references/phase_notifications.yaml
git commit -m "feat: gate phase advancement on milestone handoffs"
```

---

### Task 4A: Consolidate reader-accessibility authority and enforcement

**Files:**
- Create: `references/policies/reader_accessibility.v1.json`
- Create: `references/schemas/reader_accessibility_profile.schema.json`
- Create: `scripts/reader_accessibility_policy.py`
- Create: `scripts/reader_accessibility_contract_smoketest.py`
- Modify: `references/READER_ACCESSIBILITY.md`
- Modify: `references/DETERMINISTIC_CHECKS.md`
- Modify: `references/SAFEGUARD_LAYER.md`
- Modify: `references/STYLE_COMMITMENTS.md`
- Modify: `references/lay_term_lexicons.md`
- Modify: `skills/accessibility-overlay/SKILL.md`
- Modify: `skills/accessibility-overlay/references/sub_checks.md`
- Modify: `agents/evaluator.md`
- Modify: `agents/planner.md`
- Modify: `agents/reflector-closeout.md`
- Modify: `scripts/audit/run_all.py`
- Modify: `scripts/check8_g_prefilter.py`
- Modify: `scripts/check8_h_prefilter.py`

**Interfaces:**
- Consumes: `docs/analysis/2026-07-13_plain-english-policy-map.md`, package policy, project `directives.md`, terminology/glossary files, and optional lexicon overrides.
- Produces: one schema-valid resolved profile with source paths/hashes, deterministic probes, A–H aggregate evidence, and milestone/phase bindings.

- [x] **Step 1: Freeze the current failures as tests**

The smoke test must fail on:

```python
ACCESSIBILITY_CASES = (
    "dangling_external_hard_constraint_authority",
    "threshold_repeated_outside_profile",
    "cadence_over_200_semantics_disagree",
    "documented_override_is_not_loaded",
    "h_prefilter_not_dispatched_by_canonical_runner",
    "g_proxy_mislabeled_as_construct_threshold",
    "claimed_corpus_drift_probe_missing",
    "transition_state_owned_by_normative_prose",
    "planner_trigger_28_names_only_a_to_f",
    "subcheck_set_disagrees_a_to_h_vs_j",
    "m4_em_dash_fix_violates_resolved_style_profile",
    "m4_or_m5_evidence_missing_policy_hash",
)
```

The authority fixture must prove that the package remains operational when no portfolio `CLAUDE.md` or `AGENTS.md` is readable.

- [x] **Step 2: Obtain the cadence adjudication**

Present the live conflict to the user before coding: `DETERMINISTIC_CHECKS.md` and `sub_checks.md` flag every paragraph above 200 words, while `SAFEGUARD_LAYER.md` permits a paragraph above 200 words when it carries two turn-points. Record the chosen meaning in the architecture decision log and profile fixture. Do not infer the choice from file age.

- [x] **Step 3: Establish package-local authority**

Make `READER_ACCESSIBILITY.md` the normative semantic source. Replace claims that a missing external §9/§13 definition is the binding package authority with historical provenance language. Keep C-5 non-suspendable and preserve the intrinsic-load anti-dilution rule.

- [x] **Step 4: Define and load the policy profile**

The JSON profile must contain:

- the adjudicated active Sub-check set, scope, phase applicability, and gate contribution, including an explicit disposition for the safeguard layer's current advisory Sub-check J;
- cadence, rhythm, jargon, and consolidation thresholds;
- aggregate-verdict rules and transitional/advisory flags;
- built-in lexicon and domain-token source paths;
- project override filenames and polarity;
- remediation ordering for Sub-check H register shifts versus em-dash discipline;
- profile version and canonical SHA-256.

The package profile defines transition semantics, but live grace flags, counters, and retirement events are stored under `phase_state.json.milestone_framework.policy_bindings.reader_accessibility`. Migrate any authoritative value currently inferred from dates or `classification.md`; retain old documents as evidence or generated views.

`reader_accessibility_policy.py` validates the package profile, resolves project directives, and emits a resolved JSON object with every contributing path/hash. Hedge and plain-connective project files replace defaults; the Latinate whitelist supplements defaults. Project terminology/glossary sources extend domain-token exclusions.

- [x] **Step 5: Remove independent numeric authority**

Convert `DETERMINISTIC_CHECKS.md`, `SAFEGUARD_LAYER.md`, `sub_checks.md`, and overlay instructions into named references to profile keys. Human-readable values may be rendered for explanation, but `reader_accessibility_contract_smoketest.py` must compare them to the profile and fail on drift. Python probes import the loader/constants rather than hard-coding 5,000 or the H thresholds.

- [x] **Step 6: Complete the runtime wiring**

Make `scripts/audit/run_all.py` dispatch applicable A–F, G, and H prefilters from the resolved profile. Preserve the distinction between deterministic candidate generation and Evaluator judgment: G's word/paragraph-gap logic is a labeled proxy candidate, never the three-construct predicate. Implement and dispatch `_corpus_drift` or remove every claim that it is implemented. Update Planner trigger 28 to name every profile-active failing Sub-check, keep Reflector Phase 2g aggregation-only, and remove obsolete roadmap/status claims.

- [x] **Step 7: Bind policy evidence into milestones**

Extend the milestone and F9 schemas so M1 records intended readers, M3 records the resolved profile path/hash, and M4/M5 record manuscript hash, policy hash, Check 8 evidence path/hash, aggregate verdict, and phase. `MF-POLICY` blocks stale, differently configured, or missing evidence.

- [x] **Step 8: Verify**

```powershell
python scripts/reader_accessibility_contract_smoketest.py
python scripts/milestone_framework_smoketest.py
python scripts/audit/test_audit.py
python scripts/pre_phase_advance_phase_state_smoketest.py
```

Expected: exit 0 for every command, with temporary projects covering technical, mixed, and non-technical registers plus one non-i*/GORE domain glossary.

- [x] **Step 9: Commit**

```powershell
git add references/policies/reader_accessibility.v1.json references/schemas/reader_accessibility_profile.schema.json scripts/reader_accessibility_policy.py scripts/reader_accessibility_contract_smoketest.py references/READER_ACCESSIBILITY.md references/DETERMINISTIC_CHECKS.md references/SAFEGUARD_LAYER.md references/STYLE_COMMITMENTS.md references/lay_term_lexicons.md skills/accessibility-overlay/SKILL.md skills/accessibility-overlay/references/sub_checks.md agents/evaluator.md agents/planner.md agents/reflector-closeout.md scripts/audit/run_all.py scripts/check8_g_prefilter.py scripts/check8_h_prefilter.py
git commit -m "feat: consolidate reader accessibility policy wiring"
```

---

### Task 5: Bootstrap native projects with the full chain

**Files:**
- Modify: `references/PROJECT_BOOTSTRAP.md`
- Modify: `docs/agent-instructions/harness-discovery-lifecycle.md`
- Modify: `references/ARTEFACT_FRONTMATTER_SCHEMA.md`

**Interfaces:**
- Consumes: schemas and templates from Task 2.
- Produces: fresh projects with native pending M1-M5 state and F9 directories.

- [x] **Step 1: Extend the seed tree**

Add:

```text
reviews/
  phase_state.json
  .harness/
    milestones/
research_notes/
  project_memo.md
  annotated_references.md
manuscript/
  outline.md
  main.md
```

- [x] **Step 2: Seed milestone state**

M1 starts `in_progress`; M2-M5 start `not_started`; no milestone is inferred accepted from file presence.

- [x] **Step 3: Register F9**

Document F9 as JSON evidence rather than Markdown frontmatter and route its JSON Schema validator.

- [x] **Step 4: Verify bootstrap references**

```powershell
python scripts/manifest_links_check.py
python scripts/path-hygiene-check.py
```

Expected: exit 0.

- [x] **Step 5: Commit**

```powershell
git add references/PROJECT_BOOTSTRAP.md docs/agent-instructions/harness-discovery-lifecycle.md references/ARTEFACT_FRONTMATTER_SCHEMA.md
git commit -m "feat: bootstrap native milestone handoff state"
```

---

### Task 6: Generate lifecycle views and detect drift

**Files:**
- Create: `scripts/render_lifecycle_state.py`
- Create: `scripts/render_lifecycle_state_smoketest.py`

**Interfaces:**
- Consumes: authoritative ledger and accepted F9 packets.
- Produces: `reviews/lifecycle_state.md` with source binding.

- [x] **Step 1: Write the failing drift test**

The test must:

1. render a valid ledger;
2. assert `generated: true`, `derived_from`, and `source_sha256`;
3. modify the generated status manually;
4. assert validator code `MF-DERIVED`;
5. rerender and assert byte-identical deterministic output when `generated_at` is injected as a fixed argument.

- [x] **Step 2: Implement the renderer**

CLI:

```text
python scripts/render_lifecycle_state.py --project-root scripts/fixtures/native-milestone-project --generated-at 2026-07-13T18:00:00Z --check
```

`--check` writes nothing and exits 4 on drift.

- [x] **Step 3: Verify**

```powershell
python scripts/render_lifecycle_state_smoketest.py
```

Expected: exit 0.

- [x] **Step 4: Commit**

```powershell
git add scripts/render_lifecycle_state.py scripts/render_lifecycle_state_smoketest.py
git commit -m "feat: generate lifecycle views from unified state"
```

---

### Task 7: Implement guarded legacy migration

**Files:**
- Create: `scripts/migrate_legacy_milestones.py`
- Create: `scripts/migrate_legacy_milestones_smoketest.py`

**Interfaces:**
- Consumes: legacy phase/tier ledgers and artifact inventory.
- Produces: dry-run evidence matrix, HOLD records, approved atomic migration, archive manifest, and report.

- [x] **Step 1: Write migration tests**

Required cases:

```python
MIGRATION_CASES = (
    "dry_run_writes_nothing",
    "archive_live_ambiguity_creates_hold",
    "missing_feedback_is_not_captured_not_invented",
    "array_sections_migrate_to_object",
    "mixed_tier_phase_state_requires_adjudication",
    "approved_migration_is_idempotent",
    "rollback_manifest_restores_original_hash",
)
```

- [x] **Step 2: Implement dry-run output**

Emit JSON containing unclassified artifact and feedback candidates, non-authoritative filename/location hints, lineage hints, path failures, ledger-shape findings, and HOLDs. Default invocation never writes canonical state and never infers a milestone or feedback class from a filename.

- [x] **Step 3: Implement authorized write mode**

Require both:

```text
--apply --adjudication scripts/fixtures/approved-legacy-adjudication.json
```

The adjudication must explicitly admit or exclude every discovered candidate. Admitted feedback binds class, source actor/authority, source/target milestone, receipt time, lineage, disposition, and contemporaneity evidence path/hash. Excluded or unavailable candidates require a rationale and create no lifecycle records or events. Archive original state, write atomically, emit a migration report that distinguishes admitted/excluded/unavailable/missing evidence plus a rollback manifest, then run both validators.

- [x] **Step 4: Verify**

```powershell
python scripts/migrate_legacy_milestones_smoketest.py
```

Expected: exit 0.

- [x] **Step 5: Commit**

```powershell
git add scripts/migrate_legacy_milestones.py scripts/migrate_legacy_milestones_smoketest.py
git commit -m "feat: migrate legacy milestone projects safely"
```

---

### Task 8: Promote gate outcome semantics and repair SK-20 no-op behavior

**Files:**
- Modify: `scripts/sk20_preflight_gate.py`
- Modify: `references/PROJECT_BOOTSTRAP.md`
- Modify: `scripts/milestone_framework_smoketest.py`

**Interfaces:**
- Consumes: shared outcome meanings from Task 1.
- Produces: successful N/A/no-op and blocking misconfiguration behavior.

- [x] **Step 1: Add failing SK-20 cases**

Assert:

- enabled and ready → exit 0, `READY`;
- explicitly disabled with reason → exit 0, `NOT_APPLICABLE`;
- missing required project configuration → exit 4, `MISCONFIGURED`.

- [x] **Step 2: Change strict-exit behavior**

Do not return nonzero merely because SK-20 should no-op. Return 4 only when readiness failure represents misconfiguration.

- [x] **Step 3: Verify**

```powershell
python scripts/milestone_framework_smoketest.py
python scripts/end_to_end_smoketest.py
```

Expected: exit 0.

- [x] **Step 4: Commit**

```powershell
git add scripts/sk20_preflight_gate.py references/PROJECT_BOOTSTRAP.md scripts/milestone_framework_smoketest.py
git commit -m "fix: distinguish preflight no-op from misconfiguration"
```

---

### Task 9: Add exemplar governance

**Files:**
- Create: `references/milestone_exemplars.json`
- Modify: `scripts/milestone_framework_validate.py`
- Modify: `references/MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md`

**Interfaces:**
- Consumes: validator evidence.
- Produces: externally granted `clean_lifecycle_exemplar` and `legacy_migration_exemplar` entries.

- [x] **Step 1: Seed an empty registry**

```json
{
  "schema_version": "1.0.0",
  "entries": []
}
```

- [x] **Step 2: Add registration predicates**

Reject self-declaration in project files. A registry entry requires project path, exemplar class, approval authority, validator version, evidence paths, registration time, and current ledger hash.

- [x] **Step 3: Add negative test**

An INF3130 fixture that merely says “portfolio exemplar” in Markdown must fail `MF-EXEMPLAR` until migration and registry evidence pass.

- [x] **Step 4: Verify and commit**

```powershell
python scripts/milestone_framework_smoketest.py
git add references/milestone_exemplars.json scripts/milestone_framework_validate.py references/MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md
git commit -m "feat: gate milestone exemplar registration"
```

---

### Task 10: Pilot the design case and migration case without mutating them

**Files:**
- Modify: `scripts/milestone_framework_smoketest.py`
- Modify: `scripts/migrate_legacy_milestones_smoketest.py`

**Interfaces:**
- Consumes: read-only snapshots or synthetic equivalents of the RE essay and INF3130 structures.
- Produces: regression fixtures proving the architecture addresses the observed failures.

- [x] **Step 1: Add the RE essay positive case**

Assert:

- M4/M5 bind the manuscript, not plan/checklist;
- all M1→M5 handoffs resolve;
- changed M5 manuscript hash creates `MF-BINDING` and stale approval;
- reopening M2 blocks M5 until downstream revalidation.

- [x] **Step 2: Add the INF3130 negative case**

Assert:

- divergent archive/live M1 and M3 create lineage HOLDs;
- array-shaped sections produce controlled findings, not traceback;
- simultaneous tier/phase state blocks migration apply;
- direct M3 plus retrospective M1 evidence cannot be reported as direct feedback for all milestones;
- unlocked Ph3 sibling blocks Ph4/MCR admission.

- [x] **Step 3: Verify**

```powershell
python scripts/milestone_framework_smoketest.py
python scripts/migrate_legacy_milestones_smoketest.py
```

Expected: exit 0 with zero fixture mutations outside temporary directories.

- [x] **Step 4: Commit**

```powershell
git add scripts/milestone_framework_smoketest.py scripts/migrate_legacy_milestones_smoketest.py
git commit -m "test: cover RE handoff and INF legacy failures"
```

---

### Task 11: Wire the release gate and perform full verification

**Files:**
- Modify: `scripts/release-gate.sh`
- Modify at release only: `.claude-plugin/plugin.json`
- Modify at release only: `.claude-plugin/marketplace.json`
- Modify at release only: `CHANGELOG.md`
- Modify at release only: `README.md`

**Interfaces:**
- Consumes: every implementation and smoke test.
- Produces: one release-gated harness minor version.

- [x] **Step 1: Add blocking release phases**

`release-gate.sh` must run:

```bash
python scripts/milestone_framework_smoketest.py
python scripts/reader_accessibility_contract_smoketest.py
python scripts/render_lifecycle_state_smoketest.py
python scripts/migrate_legacy_milestones_smoketest.py
python -m py_compile scripts/milestone_framework_validate.py scripts/render_lifecycle_state.py scripts/migrate_legacy_milestones.py
```

Missing runner or fixture is a BLOCKER, never a skip warning.

- [x] **Step 2: Run structural checks before version changes**

```powershell
python scripts/skill-check.py
python scripts/version-check.py
python scripts/catalog-check.py
python scripts/path-hygiene-check.py
python scripts/snippet-check.py
python scripts/manifest_links_check.py
python scripts/manifest-coherence-check.py
python scripts/phase_state_validate.py --project-root scripts/fixtures/phase_state_smoketest/pass
```

Expected: every applicable command exits 0. `phase_state_validate.py` validates an actual phase ledger and therefore uses the canonical PASS fixture here; a missing ledger is an input error for that validator. READY / NOT_APPLICABLE / MISCONFIGURED tri-state behavior belongs to the SK-20 milestone preflight and is exercised by `milestone_framework_smoketest.py`.

- [x] **Step 3: Run the complete test set**

```powershell
python scripts/milestone_framework_smoketest.py
python scripts/reader_accessibility_contract_smoketest.py
python scripts/render_lifecycle_state_smoketest.py
python scripts/migrate_legacy_milestones_smoketest.py
python scripts/pre_phase_advance_phase_state_smoketest.py
python scripts/end_to_end_smoketest.py
python scripts/output_economy_smoketest.py
```

Expected: exit 0 for every command.

- [x] **Step 4: Assign the release version**

Update manifest, marketplace, changelog, and README together. Do not invent the number earlier in the implementation.

- [x] **Step 5: Run the release gate**

```powershell
bash scripts/release-gate.sh --build
```

Expected: exit 0 with milestone, migration, derived-view, version, catalog, and package checks reported clean.

- [x] **Step 6: Commit the release**

```powershell
git add scripts/release-gate.sh .claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md README.md
git commit -m "release: ship milestone feedback and handoff framework"
```

---

## Post-release project work kept outside this plan

After the harness release and explicit user approval:

1. Run INF3130 migration in dry-run mode.
2. Have the user adjudicate M1/M3 lineages, MCR scope, legacy feedback classes, stale paths, and legacy ledger retirement.
3. Apply the migration atomically and validate.
4. Register INF3130 only as `legacy_migration_exemplar` if it meets every criterion.
5. Bootstrap a clean M1 project and complete an independent replay before registering any `clean_lifecycle_exemplar`.
6. Decide separately whether and when to resume INF3130 `/run-phase-4`.

## Self-review

- [x] The plan derives the feature from the RE essay failure.
- [x] INF3130 is used only as a negative/migration case.
- [x] Milestone and phase axes remain distinct.
- [x] One ledger remains authoritative.
- [x] Validator predicates, outcomes, and exit codes are explicit.
- [x] Reader accessibility has package-local authority, a single machine profile, override semantics, and end-to-end enforcement tests.
- [x] Accessibility intent and current-hash evidence feed from M1/M3 into M4/M5 rather than appearing only at finalization.
- [x] Precedence and override boundaries are implemented, not assumed.
- [x] Migration is dry-run-first, idempotent, and reversible.
- [x] Derived-view drift and exemplar self-designation are tested.
- [x] No INF3130 mutation is included in the harness implementation.
- [x] Release verification commands and expected outcomes are specified.
