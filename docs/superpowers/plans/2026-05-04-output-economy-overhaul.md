# Output Economy Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorient co-author-harness so each phase optimizes manuscript drafting, revision, and finalization speed, while deferring most reporting until the full phase sequence or round is complete.

**Architecture:** Add an **Output Economy Layer** on top of the existing Lifecycle-Phase Ladder (see `docs/superpowers/specs/2026-05-04-output-economy-architecture.md`). Phase work stays manuscript-first: edits, minimal state deltas, and small decision checkpoints; audit evidence defaults to machine-readable packets; the human-facing final report is generated once at round close unless a blocker or exception path fires. Grounding and phase-state integrity are unchanged; verbose reporting becomes opt-in or failure-triggered rather than the default surface.

**Tech Stack:** Markdown skill and reference files, Claude plugin command shims, Python validators, JSON phase ledger, release-gate scripts.

---

## Audit Verdict

The plugin's stated identity is "PhD-level academic-writing review" with a four-agent phase ladder, but its operational center has drifted toward producing governance evidence. The manuscript-changing work is inside the loop, while the required artifacts around it have become the visible output surface.

Evidence from the current tree:

- The live efficiency report counts 50 runtime artifacts, about 164,620 prompt tokens, 481 dispatch references, and a projected invocation cost of 6.84921 USD.
- Speed telemetry reports an estimated 9.743 seconds of input processing, max chain depth 19, and parallelisable fraction 0.048.
- The operating manual already says Step 8 is the consolidated report the user actually reads, while per-step findings and checks are supporting evidence.
- The phase skills still require many per-phase reports: Ph1 lists deterministic, reflector, snowball, external verification, signoff, revision log, and ledger outputs; Ph2 lists deterministic, findings, recheck, reflector, signoff, revision log, and ledger outputs; Ph3 lists the largest set, including findings, overlays, safeguard files, convergence logs, signoffs, journal rows, probes, revision logs, and ledger rows.

The important architectural conclusion: do not merely trim prose in the current files. The harness needs a new output contract.

## Target Contract

### Primary Product

The primary output of Ph1-Ph4 is the paper:

- `manuscript/main.md` or the relevant manuscript section
- `manuscript/revision_log.md` as a compact edit ledger
- `reviews/phase_state.json` as the machine state ledger

### Runtime Evidence

Runtime checks should write compact evidence packets only when needed:

- `reviews/.harness/evidence/<event_id>.json`
- `reviews/.harness/events.jsonl`
- `reviews/.harness/cache/<content_hash>.json`

These are for recovery, audit, and final synthesis, not routine human reading.

### Human-Facing Reports

Human-facing reports should collapse to three moments:

- Before work: a short phase intent and success criterion.
- During work: only blockers, decisions, or user approvals.
- After the full round: one final report summarizing what changed, what was verified, what remains, and how manuscript quality moved.

## File Structure

- Modify: `README.md`
  State the plugin intention as manuscript-first co-authoring with deferred reporting.

- Modify: `.claude-plugin/plugin.json`
  Align the description and keywords with the new intent.

- Create: `docs/release-notes/RELEASE_NOTES_v0.14.0.md`
  Document the output-economy behavior change and keep version checks coherent.

- Modify: `references/ROUTING_SPINE.md`
  Add the manuscript-first output rule and redefine phase gates around paper movement, not report production.

- Modify: `references/OPERATING_MANUAL.md`
  Replace "each step writes findings" as the default with "each step records evidence, final report synthesizes."

- Modify: `references/REVIEW_ORCHESTRATION.md`
  Split evaluator outputs into `evidence_packet`, `action_list`, and `final_report`.

- Modify: `references/PHASE_PROTOCOL.md`
  Add an Output Economy clause that limits mandatory per-phase artifacts.

- Modify: `references/TOKEN_BUDGET_PROTOCOL.md`
  Extend segmentation logic into report deferral and evidence caching.

- Modify: `references/ARTEFACT_FRONTMATTER_SCHEMA.md`
  Register output-economy evidence and final-report artifact families so the new artifacts are schema-governed.

- Modify: `references/SUCCESS_METRICS.md`
  Add efficiency and paper-delta metrics: edits accepted, unresolved blocker count, time-to-next-draft, evidence-to-output ratio.

- Modify: `skills/run-phase-1/SKILL.md`
  Make the default output a draft delta plus compact state update; move deterministic and reflector details into evidence packets unless a blocker fires.

- Modify: `skills/run-phase-2/SKILL.md`
  Make the default output an approved action list and applied revision delta; defer findings detail to final report unless the user asks.

- Modify: `skills/run-phase-3/SKILL.md`
  Make each iteration produce a convergence delta, not a full report stack.

- Modify: `skills/run-phase-3-stability/SKILL.md`
  Preserve this as the model for reduced-envelope execution and make its "clean admission" pattern reusable.

- Modify: `skills/run-phase-4/SKILL.md`
  Make Ph4 the final report assembly point after G.4, rather than another multi-report phase.

- Modify: `agents/planner.md`
  Teach the Planner to choose output profiles: `silent_evidence`, `decision_checkpoint`, `final_report`.

- Modify: `agents/evaluator.md`
  Teach the Evaluator to emit machine evidence and short action lists by default.

- Modify: `agents/generator.md`
  Keep the Generator focused on manuscript edits and compact revision-log entries.

- Modify: `agents/reflector.md`
  Move routine reflection to round close; mid-phase reflection becomes blocker-triggered only.

- Create: `references/OUTPUT_ECONOMY_PROTOCOL.md`
  New authority for output profiles, evidence packets, final report assembly, and escalation rules.

- Create: `references/templates/final_round_report.md`
  Single human-facing round report template.

- Create: `scripts/output_economy_check.py`
  Validator that fails when a phase skill requires nonessential human-facing artifacts by default.

- Modify: `scripts/artefact_frontmatter_validate.py`
  Validate output-economy artifact families and evidence-packet required keys.

- Create: `scripts/output_economy_smoketest.py`
  Simulated live smoke test for evidence packet, events log, compatibility pointer, and final report assembly.

- Modify: `CLAUDE.md`
  Add `output_economy_check.py` and `output_economy_smoketest.py` to the maintainer check block.

## Dependency Order

Implementation order is binding:

1. Task 1 defines the vocabulary and evidence-packet contract.
2. Task 2 updates public intent surfaces.
3. Task 3 registers schema, round identifiers, and event identifiers before any artifact-producing behavior changes.
4. Task 4 updates the core protocol consumers that every later task references.
5. Task 9 Step 1 captures the pre-overhaul output-economy baseline before any behavior-changing edits in Tasks 5-8.
6. Task 5 updates phase skills to use the new contract.
7. Task 6 updates agent contracts after the phase skill vocabulary is stable.
8. Task 7 adds final-report and backward-compatibility behavior.
9. Task 8 adds validation and smoke-test tooling.
10. Task 9 recalibrates efficiency telemetry after the baseline is captured.
11. Task 10 runs static and simulated live verification.

Do not start Tasks 5-9 before Tasks 1-4 pass validation and Task 9 Step 1 has recorded the pre-overhaul baseline. If implementation is split across workers, Task 5 and Task 6 may run in parallel only after both workers confirm they are using the exact `OUTPUT_ECONOMY_PROTOCOL.md`, `round_id`, `event_id`, and artifact-family vocabulary from Tasks 1 and 3.

## Task 1: Define Output Economy Protocol

**Files:**
- Create: `references/OUTPUT_ECONOMY_PROTOCOL.md`
- Modify: `references/CLAUDE.md`
- Modify: `docs/agent-instructions/harness-reference-index.md`

- [ ] **Step 1: Create the protocol**

Add `references/OUTPUT_ECONOMY_PROTOCOL.md` with these sections:

````markdown
# OUTPUT_ECONOMY_PROTOCOL

**Purpose.** Keep the harness manuscript-first. Phase work should improve the paper, update minimal state, and preserve audit evidence without producing a report stack at every step.

## 1. Output Classes

| Class | Human-facing by default | Purpose |
|---|---:|---|
| Manuscript delta | Yes | The actual paper change. |
| Decision checkpoint | Yes | User approval, blocker choice, scope change, or phase exit. |
| Evidence packet | No | Machine-readable proof that checks ran. |
| Final round report | Yes, once | End-of-round synthesis for the user. |
| Exception report | Yes, on failure | Blocker, failed verifier, stale state, or unresolved contradiction. |

## 2. Default Rule

During Ph1-Ph3, do not create a new human-facing report when a compact evidence packet and a short checkpoint can preserve the same information.

## 3. Evidence Packet Shape

Evidence packets live at `reviews/.harness/evidence/<event_id>.json` and contain:

```json
{
  "artifact_family": "F7",
  "document_type": "evidence_packet",
  "round_id": "round_2026-05-04_001",
  "event_id": "round_2026-05-04_001__ph2__001",
  "phase": "Ph2",
  "target": "manuscript/main.md#section",
  "evidence_status": "complete",
  "created_at": "2026-05-04T00:00:00Z",
  "checks_run": [],
  "blockers": [],
  "major_actions": [],
  "minor_actions_count": 0,
  "manuscript_delta_summary": "",
  "state_updates": {},
  "source_reads": [],
  "final_report_inputs": {
    "checks_skipped": [],
    "baseline_metrics": {},
    "notes": []
  }
}
```

## 4. Escalation Rule

Write a human-facing exception report only when the user must decide, a phase gate blocks, a verifier fails, or the manuscript cannot be changed safely.

## 5. Final Report Rule

The final round report is assembled at Ph4 or explicit round close from evidence packets, revision logs, and phase state.

## 6. Events And Cache Files

`reviews/.harness/events.jsonl` is append-only. Each line records one event with:

```json
{"round_id":"round_2026-05-04_001","event_id":"round_2026-05-04_001__ph2__001","timestamp":"2026-05-04T00:00:00Z","phase":"Ph2","event":"evidence_packet_written","path":"reviews/.harness/evidence/round_2026-05-04_001__ph2__001.json"}
```

`reviews/.harness/cache/<content_hash>.json` stores reusable deterministic-check results keyed by manuscript or source content hash:

```json
{"content_hash":"sha256:abc","kind":"deterministic_checks","computed_at":"2026-05-04T00:00:00Z","result":{"clean":true,"counts":{}}}
```

## 7. Final Report Assembly

At Ph4 or explicit round close, the Planner reads `events.jsonl`, resolves every `evidence_packet_written` event for the round, loads those evidence packets, then merges them with `manuscript/revision_log.md` and `reviews/phase_state.json`.

Assembly order:

1. Sort evidence packets by `timestamp` or event order.
2. Summarize `manuscript_delta_summary` into Paper Delta.
3. Merge `blockers`, `major_actions`, and `minor_actions_count` into Quality Movement.
4. List `checks_run`, `source_reads`, skipped checks, and verifier failures in Evidence Summary.
5. Derive Next Actions from unresolved blockers first, then unresolved major actions, then phase-gate residue.

If an evidence packet listed in `events.jsonl` is missing, write an exception report and mark the final report `evidence_status: incomplete`; do not fabricate the missing result.

## 8. Identifier Contract

Use two identifiers:

- `round_id`: names the whole multi-phase round and the final report.
- `event_id`: names one phase event, check event, exception event, or evidence packet inside that round.

Format:

```text
round_id = round_YYYY-MM-DD_NNN
event_id = <round_id>__<phase-or-event-kind>__NNN
```

Examples:

```text
round_2026-05-04_001
round_2026-05-04_001__ph1__001
round_2026-05-04_001__ph2__002
round_2026-05-04_001__ph3__003
round_2026-05-04_001__exception__004
```

Incrementing rule:

1. The Planner creates the `round_id` at round open.
2. `NNN` is the next unused integer for that date in the project.
3. The Planner checks existing `reviews/.harness/events.jsonl`, `reviews/final_round_report_*.md`, and `reviews/.harness/evidence/*.json` before choosing a new ID.
4. Event IDs increment monotonically within a round by event-write order.
5. The final report path is `reviews/final_round_report_<round_id>.md`, never a phase event ID.

Uniqueness guarantee:

The Planner refuses to write if the chosen `round_id` or `event_id` already exists in events, evidence filenames, final report filenames, or `phase_state.json` notes for the active project.
````

- [ ] **Step 2: Register the protocol**

Add `OUTPUT_ECONOMY_PROTOCOL.md` to `references/CLAUDE.md` and `docs/agent-instructions/harness-reference-index.md` as a package authority file.

- [ ] **Step 3: Add compatibility clause**

Add this clause to `OUTPUT_ECONOMY_PROTOCOL.md`:

````markdown
## 9. Backward Compatibility

Existing projects may still contain `reviews/consolidated_findings_report.md`, `reviews/safeguard_layer_results.md`, `reviews/ph2_findings_*.md`, and other pre-overhaul report paths. These remain readable inputs. New rounds default to evidence packets and final reports, but loaders must treat old report paths as legacy evidence sources.

When a project is mid-round and expects an old path, the Planner writes a compatibility pointer instead of silently dropping the artifact:

```markdown
# Compatibility Pointer

This round now uses output economy evidence packets.

Legacy path: `reviews/consolidated_findings_report.md`
Replacement evidence: `reviews/.harness/evidence/<event_id>.json`
Final synthesis: `reviews/final_round_report_<round_id>.md`
```
````

- [ ] **Step 4: Verify references resolve and identifiers are named**

Run:

```powershell
Select-String -Path references\OUTPUT_ECONOMY_PROTOCOL.md -Pattern "round_id|event_id|final_round_report_<round_id>"
python scripts/path-hygiene-check.py
```

Expected: identifier terms appear and no new broken path references.

## Task 2: Rewrite Intent Surfaces

**Files:**
- Modify: `README.md`
- Modify: `.claude-plugin/plugin.json`
- Create: `docs/release-notes/RELEASE_NOTES_v0.14.0.md`
- Modify: `references/ROUTING_SPINE.md`

- [ ] **Step 1: Update plugin description**

Change `.claude-plugin/plugin.json` description from a phase-led review identity to:

```json
"description": "Manuscript-first academic co-authoring for Claude Code. Planner, Evaluator, Generator, and Reflector improve drafts through compact phase checkpoints, machine-readable evidence, and one final round report after drafting, revision, and finalization are complete."
```

- [ ] **Step 2: Bump plugin version**

Because this overhaul adds new artifact families, a new protocol authority, new validators, and changed default runtime behavior, bump `.claude-plugin/plugin.json` from `0.13.0` to `0.14.0`.

Create `docs/release-notes/RELEASE_NOTES_v0.14.0.md` with:

```markdown
# Release Notes v0.14.0

## Output Economy Overhaul

- Makes manuscript movement the default phase product.
- Defers routine human-facing findings reports until round close.
- Adds F7 JSON evidence packets and F8 final round reports.
- Adds output-economy validation and smoke-test coverage.
- Preserves legacy report paths through compatibility pointers for in-progress projects.
```

- [ ] **Step 3: Update README opening**

Revise the README "Why this project" section to state:

```markdown
The harness optimizes for the paper, not for report volume. Each phase should leave the manuscript better than it found it, preserve only the evidence needed for audit and recovery, and defer human-facing synthesis until round close unless a blocker needs the user's decision.
```

- [ ] **Step 4: Add routing spine output rule**

Add a short rule to `references/ROUTING_SPINE.md` after the phase table:

```markdown
**Output economy rule.** Phase exit is certified by manuscript movement, state correctness, and evidence availability. Per-step reports are evidence, not the product. The default human-facing synthesis is the final round report.
```

- [ ] **Step 5: Verify manifest parity**

Run:

```powershell
python scripts/version-check.py
python scripts/manifest-coherence-check.py
```

Expected: both pass; if the manifest check expects description parity with marketplace metadata, update `.claude-plugin/marketplace.json` in the same task.

## Task 3: Register Artifact Schema And Identifier Validation

**Files:**
- Modify: `references/ARTEFACT_FRONTMATTER_SCHEMA.md`
- Modify: `scripts/artefact_frontmatter_validate.py`
- Modify: `references/OUTPUT_ECONOMY_PROTOCOL.md`

- [ ] **Step 1: Add output-economy artifact families**

Add two artifact families to `references/ARTEFACT_FRONTMATTER_SCHEMA.md`:

````markdown
## F7 evidence_packet

Machine-readable evidence for one output-economy event.

Required fields:

```yaml
artifact_family: F7
document_type: evidence_packet
round_id: round_YYYY-MM-DD_NNN
event_id: round_YYYY-MM-DD_NNN__<kind>__NNN
phase: Ph1|Ph2|Ph3|Ph4|round_close
target: manuscript/main.md
evidence_status: complete|partial|incomplete
created_at: ISO-8601
```

Allowed payload fields:

```yaml
checks_run: []
blockers: []
major_actions: []
minor_actions_count: 0
manuscript_delta_summary: ""
state_updates: {}
source_reads: []
final_report_inputs:
  checks_skipped: []
  baseline_metrics: {}
  notes: []
```

## F8 final_round_report

Human-facing round synthesis assembled from F7 evidence packets.

Required fields:

```yaml
artifact_family: F8
document_type: final_round_report
round_id: round_YYYY-MM-DD_NNN
evidence_status: complete|partial|incomplete
created_at: ISO-8601
```
````

- [ ] **Step 2: Add JSON validation lane for F7 and narrow Markdown validation for F8**

Update `scripts/artefact_frontmatter_validate.py` as an architectural extension, not a simple family-table addition:

- `collect_paths` must collect both `*.md` and `*.json` when `--dir` is used.
- `validate_path` must dispatch by suffix:
  - `.md` keeps the existing YAML-frontmatter path.
  - `.json` uses a new JSON reader and validates the JSON root object directly.
- F7 evidence packets live at `reviews/.harness/evidence/<event_id>.json`; they must never be sent through `extract_frontmatter`.
- F8 final round reports stay Markdown and use YAML frontmatter.
- Existing `validate_common` remains required for legacy F1-F6 Markdown families only.
- F7 and F8 must use their own common-field checks because they deliberately replace legacy `cycle_id` with `round_id` / `event_id` and omit legacy fields such as `model_used`, `iteration`, `section_heading_path`, and `grounding_basis`.

Add:

```python
ROUND_ID_RE = re.compile(r"^round_\d{4}-\d{2}-\d{2}_\d{3}$")
EVENT_ID_RE = re.compile(r"^round_\d{4}-\d{2}-\d{2}_\d{3}__[a-z0-9_]+__\d{3}$")
OUTPUT_ECONOMY_FAMILIES = {"evidence_packet", "final_round_report"}
```

Validation rules:

- F7 JSON requires `artifact_family: "F7"`, `document_type: "evidence_packet"`, `round_id`, `event_id`, `phase`, `target`, `evidence_status`, and `created_at`.
- F7 JSON allows `checks_run`, `blockers`, `major_actions`, `minor_actions_count`, `manuscript_delta_summary`, `state_updates`, `source_reads`, and `final_report_inputs`.
- F8 Markdown frontmatter requires `artifact_family: "F8"`, `document_type: "final_round_report"`, `round_id`, `evidence_status`, and `created_at`.
- F7 `event_id` must begin with its `round_id`.
- `evidence_status` must be one of `complete`, `partial`, or `incomplete`.
- JSON parse failure, non-object JSON roots, and missing F7 fields should emit `R-Refl-FM-7` or `R-Refl-FM-1` consistently with existing finding classes.
- Unknown-field rejection for F7/F8 must use their own allowed-field sets, not `COMMON_REQUIRED`.

- [ ] **Step 3: Add schema pointer to output protocol**

Add to `OUTPUT_ECONOMY_PROTOCOL.md`:

```markdown
Evidence packets are the F7 artifact family. Final round reports are the F8 artifact family. Both are validated by `scripts/artefact_frontmatter_validate.py`.

F7 is a JSON artifact validated through the validator's JSON lane. F8 is a Markdown artifact validated through YAML frontmatter. F7/F8 do not use the legacy F1-F6 `COMMON_REQUIRED` field set.
```

- [ ] **Step 4: Verify schema validator**

Run:

```powershell
python scripts/artefact_frontmatter_validate.py --help
$fixture = New-Item -ItemType Directory -Force -Path "$env:TEMP\coauthor-f7-f8-validator"
@'
{
  "artifact_family": "F7",
  "document_type": "evidence_packet",
  "round_id": "round_2026-05-04_001",
  "event_id": "round_2026-05-04_001__ph2__001",
  "phase": "Ph2",
  "target": "manuscript/main.md",
  "evidence_status": "complete",
  "created_at": "2026-05-04T00:00:00Z",
  "checks_run": [],
  "blockers": [],
  "major_actions": [],
  "minor_actions_count": 0,
  "manuscript_delta_summary": "",
  "state_updates": {},
  "source_reads": [],
  "final_report_inputs": {
    "checks_skipped": [],
    "baseline_metrics": {},
    "notes": []
  }
}
'@ | Set-Content -Encoding utf8 "$fixture\round_2026-05-04_001__ph2__001.json"
@'
---
artifact_family: F8
document_type: final_round_report
round_id: round_2026-05-04_001
evidence_status: complete
created_at: 2026-05-04T00:00:00Z
---

# Final Round Report
'@ | Set-Content -Encoding utf8 "$fixture\final_round_report_round_2026-05-04_001.md"
python scripts/artefact_frontmatter_validate.py "$fixture\round_2026-05-04_001__ph2__001.json" "$fixture\final_round_report_round_2026-05-04_001.md"
python scripts/path-hygiene-check.py
```

Expected: validator loads without syntax errors, both F7 and F8 fixtures exit 0, and path hygiene passes. If either fixture fails, fix the JSON dispatch, F8 frontmatter path, or F7/F8 common-field bypass before starting Task 4.

## Task 4: Align Core Protocol Consumers

**Files:**
- Modify: `references/PHASE_PROTOCOL.md`
- Modify: `references/TOKEN_BUDGET_PROTOCOL.md`
- Modify: `references/REVIEW_ORCHESTRATION.md`

- [ ] **Step 1: Add Output Economy clause to PHASE_PROTOCOL**

Add a clause near the phase overview:

```markdown
## Output Economy Clause

The Lifecycle-Phase Ladder certifies paper movement, not report volume. Ph1-Ph3 default to compact evidence packets plus decision checkpoints. Human-facing per-phase reports are required only when a phase gate blocks, a verifier fails, an unsafe edit condition appears, or the user explicitly requests the report. Ph4 or explicit round close assembles the final human-facing report from evidence packets, revision logs, and `phase_state.json`.
```

- [ ] **Step 2: Extend TOKEN_BUDGET_PROTOCOL**

Add this subsection after consolidated report assembly:

```markdown
### Report Deferral For Long Manuscripts

For Long and Extended manuscripts, per-segment findings are stored as evidence packets by default. The Evaluator emits only segment-local action lists during the round. The final round report assembles the human-facing cross-segment synthesis after all in-scope segments finish or when the user explicitly closes the round.

If context limits interrupt a segment, write an evidence packet with `evidence_status: "partial"`, include the completed checks in `checks_run`, and add the skipped work to `final_report_inputs.checks_skipped`. The final report must show the partial status instead of treating the segment as clean.
```

- [ ] **Step 3: Split REVIEW_ORCHESTRATION outputs**

Replace the default "what to emit at each step" wording with:

```markdown
## Output Modes

Evaluator outputs are split into three forms:

1. `evidence_packet`: machine-readable check evidence stored under `reviews/.harness/evidence/`.
2. `action_list`: short human-facing list of BLOCKER and MAJOR actions needed for manuscript movement.
3. `final_report`: end-of-round synthesis assembled from evidence packets and revision logs.

Routine per-step findings are written as evidence packets. A Markdown findings report is an exception output, used when a blocker requires user adjudication, a phase gate fails, or the user requests the full report.
```

- [ ] **Step 4: Verify core protocol vocabulary**

Run:

```powershell
Select-String -Path references\PHASE_PROTOCOL.md,references\TOKEN_BUDGET_PROTOCOL.md,references\REVIEW_ORCHESTRATION.md -Pattern "OUTPUT_ECONOMY_PROTOCOL|evidence_packet|final_report|action_list"
python scripts/path-hygiene-check.py
```

Expected: the terms appear in all three files and path hygiene passes.

## Task 5: Convert Phase Skills To Output Profiles

**Files:**
- Modify: `skills/run-phase-1/SKILL.md`
- Modify: `skills/run-phase-2/SKILL.md`
- Modify: `skills/run-phase-3/SKILL.md`
- Modify: `skills/run-phase-3-stability/SKILL.md`
- Modify: `skills/run-phase-4/SKILL.md`

- [ ] **Step 1: Add output profile block to each phase skill**

Insert near the top of each phase skill:

```markdown
## Output Profile

Default profile: `silent_evidence`.

Human-facing output during this phase is limited to:
- the manuscript delta or action list the user must approve;
- phase gate decisions;
- exception reports for blockers, verifier failures, stale state, or unsafe edits.

All routine check details are written to `reviews/.harness/evidence/<event_id>.json` and summarized only in the final round report.
```

For `run-phase-4`, set:

```markdown
Default profile: `final_report`.
```

- [ ] **Step 2: Replace mandatory report lists with required evidence**

For Ph1-Ph3, change `Artefacts produced` from many human-facing Markdown reports to:

```markdown
## Required Outputs

- Manuscript delta or approved no-change rationale.
- Compact entry in `manuscript/revision_log.md`.
- State update in `reviews/phase_state.json` when the phase gate changes.
- Evidence packet at `reviews/.harness/evidence/<event_id>.json`.
- Human-facing exception report only when an escalation rule fires.
```

- [ ] **Step 3: Keep Ph3 stability as the reference fast path**

In `skills/run-phase-3-stability/SKILL.md`, add:

```markdown
This sub-mode is the exemplar for output economy: inherit prior findings when the substrate is byte-stable, run only drift-sensitive checks, and emit a compact clean-admission event instead of a new full report.
```

- [ ] **Step 4: Verify skill frontmatter and catalog**

Run:

```powershell
python scripts/skill-check.py
python scripts/catalog-check.py
```

Expected: both pass.

## Task 6: Refactor Agent Contracts Around Paper Movement

**Files:**
- Modify: `agents/planner.md`
- Modify: `agents/evaluator.md`
- Modify: `agents/generator.md`
- Modify: `agents/reflector.md`
- Modify: `references/AGENT_CONTRACTS.md`

- [ ] **Step 1: Add Planner output-profile routing**

In `agents/planner.md`, add `### Output Profile Routing` under the existing Procedure section immediately after the session-state cache initialization step. This block owns profile selection only; final report assembly is added later in Task 7.

Teach Planner to choose:

```markdown
`silent_evidence`: default for routine checks.
`decision_checkpoint`: when the user must approve, reject, defer, or choose scope.
`final_report`: at Ph4 or explicit round close.
`exception_report`: when a blocker or unsafe condition halts manuscript movement.
```

- [ ] **Step 2: Make Evaluator action-list first**

Evaluator default output should be:

```markdown
1. BLOCKER actions that must be resolved before progress.
2. MAJOR actions that materially improve the paper.
3. Count of MINOR polish findings, with details deferred unless requested.
4. Evidence packet path.
```

- [ ] **Step 3: Preserve Generator focus**

Generator completion should remain compact:

```markdown
- What changed in the manuscript.
- Which approved actions were completed.
- Any skipped action and why.
- Self-check status.
- Evidence packet path if checks ran.
```

- [ ] **Step 4: Defer Reflector by default**

Reflector-lightweight should run mid-phase only for blocker-triggered integrity checks. Reflector-full remains the final report and learning engine.

- [ ] **Step 5: Update AGENT_CONTRACTS.md**

Add this contract amendment to `references/AGENT_CONTRACTS.md`:

```markdown
## Output Economy Contract

All agents preserve auditability without defaulting to report proliferation.

- Planner owns output-profile selection and final report assembly.
- Evaluator owns evidence packets and short action lists; full Markdown findings are exception outputs.
- Generator owns manuscript deltas and compact revision-log entries.
- Reflector-lightweight is blocker-triggered during Ph1-Ph3; Reflector-full runs at Ph4 or explicit round close.

No agent may require a routine human-facing report when an evidence packet satisfies the audit need and no escalation rule has fired.
```

- [ ] **Step 6: Verify Planner routing placement before final assembly**

Run:

```powershell
Select-String -Path agents\planner.md -Pattern "Output Profile Routing|Final Report Assembly" -Context 2,2
```

Expected: `Output Profile Routing` appears once under Procedure, and `Final Report Assembly` is absent until Task 7.

- [ ] **Step 7: Verify no role writes outside contract**

Run:

```powershell
python scripts/skill-check.py
python scripts/path-hygiene-check.py
```

Expected: no contract drift warnings introduced by the new output profile language.

## Task 7: Add Final Round Report Template And Compatibility Shims

**Files:**
- Create: `references/templates/final_round_report.md`
- Modify: `references/SUCCESS_METRICS.md`
- Modify: `references/OPERATING_MANUAL.md`
- Modify: `agents/planner.md`

- [ ] **Step 1: Create template**

Add:

```markdown
---
artifact_family: F8
document_type: final_round_report
round_id: <round_id>
evidence_status: <complete|partial|incomplete>
created_at: <ISO-8601>
---

# Final Round Report

**Manuscript:** <path>
**Round:** <round_id>
**Phases completed:** <Ph1/Ph2/Ph3/Ph4>

## Paper Delta

- Sections changed:
- Main improvements:
- Remaining author decisions:

## Quality Movement

| Metric | Before | After | Direction |
|---|---:|---:|---|
| BLOCKER count | | | |
| MAJOR count | | | |
| Deterministic clean categories | | | |
| Submission readiness | | | |

## Evidence Summary

- Evidence packets read:
- Verifiers used:
- Checks skipped with reason:

## Next Actions

1. <highest-value next action>
2. <second action>
3. <third action>
```

- [ ] **Step 2: Add efficiency metrics**

In `references/SUCCESS_METRICS.md`, add:

```markdown
## Output Economy Metrics

- Time-to-next-draft: elapsed time from phase start to manuscript delta.
- Evidence-to-output ratio: evidence packets divided by human-facing reports.
- Accepted-action yield: approved actions completed divided by actions proposed.
- Report deferral compliance: routine reports deferred until round close unless escalation fired.
```

- [ ] **Step 3: Update operating manual artifact priority**

In `references/OPERATING_MANUAL.md`, find the artifact guidance that names `reviews/consolidated_findings_report.md` as the normal reader-facing review artifact and replace it with:

```markdown
Routine review evidence is recorded in `reviews/.harness/evidence/<event_id>.json` and indexed by `reviews/.harness/events.jsonl`. The normal reader-facing artifact is the round-close report at `reviews/final_round_report_<round_id>.md`.

Do not write `reviews/consolidated_findings_report.md` as a routine per-review output for new rounds. Use that path only as a backward-compatibility pointer for in-progress projects that already expect it, or as an exception report when a blocker, unsafe edit condition, verifier failure, or explicit user request requires a human-facing report before round close.
```

Verify with:

```powershell
Select-String -Path references\OPERATING_MANUAL.md -Pattern "final_round_report_<round_id>|consolidated_findings_report.md|backward-compatibility pointer"
```

- [ ] **Step 4: Specify final report assembly in Planner**

In `agents/planner.md`, add `### Final Report Assembly` immediately after the `### Output Profile Routing` block created in Task 6. Do not edit the routing block when adding assembly behavior.

Add:

```markdown
### Final Report Assembly

At Ph4 or explicit round close, read `reviews/.harness/events.jsonl`, load each evidence packet for the active `round_id`, merge with `manuscript/revision_log.md` and `reviews/phase_state.json`, and write `reviews/final_round_report_<round_id>.md` from `references/templates/final_round_report.md`.

If legacy reports exist and no evidence packet exists for that round, treat the legacy report as a legacy evidence source and add `legacy_source: true` to the final report Evidence Summary.
```

- [ ] **Step 5: Add legacy compatibility pointers without duplicating protocol text**

Task 1 already defines the protocol-level backward-compatibility pointer in `OUTPUT_ECONOMY_PROTOCOL.md` section 9. Do not append a second compatibility section. Add only the Planner execution instruction:

```markdown
When a legacy report path is expected by an in-progress project, write a small compatibility pointer at the legacy path instead of producing a full duplicate report. The pointer must name the replacement evidence packet and final report path.
```

- [ ] **Step 6: Verify Planner block coherence**

Run:

```powershell
Select-String -Path agents\planner.md -Pattern "Output Profile Routing|Final Report Assembly|Compatibility Pointer" -Context 2,2
```

Expected: each block appears once, final report assembly follows output-profile routing, and compatibility behavior sits under final-report or backward-compatibility instructions.

## Task 8: Add Output Economy Validator And Smoke-Test Script

**Files:**
- Create: `scripts/output_economy_check.py`
- Create: `scripts/output_economy_smoketest.py`
- Modify: `scripts/release-gate.sh`
- Modify: `README.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Create validator**

Implement a small validator that fails when phase skills, agent contracts, or agent files contain default mandatory human-facing artifact language for routine reports.

Core checks:

```python
PHASE_FILES = [
    "skills/run-phase-1/SKILL.md",
    "skills/run-phase-2/SKILL.md",
    "skills/run-phase-3/SKILL.md",
    "skills/run-phase-3-stability/SKILL.md",
    "skills/run-phase-4/SKILL.md",
]

AGENT_AND_CONTRACT_FILES = [
    "agents/planner.md",
    "agents/evaluator.md",
    "agents/generator.md",
    "agents/reflector.md",
    "references/AGENT_CONTRACTS.md",
]

PHASE_REQUIRED_PHRASES = [
    "Output Profile",
    "reviews/.harness/evidence/<event_id>.json",
    "round_id",
    "event_id",
]

PLANNER_REQUIRED_PHRASES = [
    "Output Profile Routing",
    "evidence packet",
    "final report",
]

AGENT_REQUIRED_PHRASES = [
    "evidence packet",
    "final report",
]

CONTRACT_REQUIRED_PHRASES = [
    "Output Economy Contract",
    "evidence packet",
    "final report",
]

DISCOURAGED_DEFAULTS = [
    "per-step findings",
    "writes its findings",
    "full report per iteration",
    "routine Markdown findings report",
]
```

Exception-section detection must be deterministic:

```python
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ALLOWED_DISCOURAGED_SECTION_RE = re.compile(
    r"\b(exception output|exception report|legacy compatibility|backward compatibility)\b",
    re.IGNORECASE,
)
```

A discouraged phrase is allowed only between a matching heading and the next Markdown heading of the same or higher level. Implement this with heading-depth traversal, not a single-line regex state:

```python
def allowed_discouraged_lines(lines):
    allowed = set()
    active_depth = None
    for lineno, line in enumerate(lines, start=1):
        match = HEADING_RE.match(line)
        if match:
            depth = len(match.group(1))
            title = match.group(2)
            if active_depth is not None and depth <= active_depth:
                active_depth = None
            if ALLOWED_DISCOURAGED_SECTION_RE.search(title):
                active_depth = depth
        if active_depth is not None:
            allowed.add(lineno)
    return allowed
```

It is not allowed merely because the sentence contains the word "exception".

The script should print one line per failure and exit nonzero if any phase file lacks `PHASE_REQUIRED_PHRASES`, `agents/planner.md` lacks `PLANNER_REQUIRED_PHRASES`, any non-Planner agent file lacks `AGENT_REQUIRED_PHRASES`, `references/AGENT_CONTRACTS.md` lacks `CONTRACT_REQUIRED_PHRASES`, or any file contains discouraged defaults outside the deterministic allowed sections.

It must also check `references/OUTPUT_ECONOMY_PROTOCOL.md` for the identifier contract strings `round_id`, `event_id`, and `final_round_report_<round_id>.md`.

- [ ] **Step 2: Wire release gate**

Add `python scripts/output_economy_check.py` to `scripts/release-gate.sh` after existing static documentation checks.

- [ ] **Step 3: Update maintainer check block**

Add these checks to the maintainer block in root `CLAUDE.md`:

```powershell
python scripts/output_economy_check.py
python scripts/output_economy_smoketest.py
```

- [ ] **Step 4: Add simulated live smoke test as primary behavioral check**

Create `scripts/output_economy_smoketest.py`. It should create or reset a tiny fixture under `scripts/fixtures/output_economy_smoketest/`, seed:

```text
manuscript/main.md
manuscript/revision_log.md
reviews/classification.md
reviews/phase_state.json
reviews/.harness/events.jsonl
reviews/.harness/evidence/round_2026-05-04_001__ph2__001.json
```

The script should simulate a Ph2-style event, assemble `reviews/final_round_report_round_2026-05-04_001.md`, and assert:

- the evidence packet matches the F7 schema shape;
- `python scripts/artefact_frontmatter_validate.py <fixture evidence JSON> <fixture final report Markdown>` exits 0, so smoke-test structure and schema-validator structure cannot drift apart;
- `events.jsonl` references the same `round_id` and `event_id`;
- no routine `reviews/ph2_findings_round_2026-05-04_001__ph2__001.md` or `reviews/consolidated_findings_report.md` is produced;
- a compatibility pointer can be generated at the legacy path without duplicating the final report.

- [ ] **Step 5: Verify**

Run:

```powershell
python scripts/output_economy_check.py
python scripts/output_economy_smoketest.py
python scripts/skill-check.py
python scripts/catalog-check.py
python scripts/path-hygiene-check.py
```

Expected: all pass.

## Task 9: Capture Baseline And Recalibrate Efficiency

**Files:**
- Modify: `.plugin-efficiency.json`
- Modify: `artifacts/efficiency/latest.json` only if regenerated by the existing audit script
- Modify: `docs/release-notes/RELEASE_NOTES_v0.14.0.md`

- [ ] **Step 1: Capture pre-overhaul output-economy baseline**

Execute this step immediately after Tasks 1-4 pass validation and before Tasks 5-8 change phase or agent behavior. Record a deterministic pre-overhaul baseline in `.plugin-efficiency.json`:

```json
{
  "output_economy_baseline": {
    "measured_at": "<ISO-8601 timestamp>",
    "human_facing_report_defaults_count": 0,
    "legacy_report_path_mentions_count": 0,
    "evidence_packet_mentions_count": 0,
    "scan_scope": [
      "skills/run-phase-*/SKILL.md",
      "agents/*.md",
      "references/*.md"
    ]
  }
}
```

Populate the counts from the current tree before editing those files. Use the same scan logic before and after the overhaul:

```powershell
$files = @()
$files += Get-ChildItem skills -Recurse -Filter 'SKILL.md' -File |
  Where-Object { $_.DirectoryName -match 'run-phase' }
$files += Get-ChildItem agents -Filter '*.md' -File
$files += Get-ChildItem references -Filter '*.md' -File

$humanFacingDefaultPattern = '(?i)(must|shall|required|write|produce|emit).{0,80}(findings report|consolidated findings|human-facing report|markdown findings)'
$legacyReportPattern = 'reviews/consolidated_findings_report\.md|consolidated_findings_report\.md'
$evidencePacketPattern = 'evidence_packet|reviews/\.harness/evidence|<event_id>\.json'

$baseline = [ordered]@{
  measured_at = (Get-Date).ToUniversalTime().ToString('o')
  human_facing_report_defaults_count = (@($files | Select-String -Pattern $humanFacingDefaultPattern).Count)
  legacy_report_path_mentions_count = (@($files | Select-String -Pattern $legacyReportPattern).Count)
  evidence_packet_mentions_count = (@($files | Select-String -Pattern $evidencePacketPattern).Count)
  scan_scope = @('skills/run-phase-*/SKILL.md', 'agents/*.md', 'references/*.md')
  count_method = 'Select-String line hits using the three regex patterns documented in the output-economy plan Task 9 Step 1'
}
```

Merge strategy is mandatory: read the existing `.plugin-efficiency.json` root object, add or replace only the top-level `output_economy_baseline` key, and write the root object back. Do not replace the file with the snippet. The existing rebase history, false-positive notes, model tiers, thresholds, and role overrides must remain byte-for-byte equivalent except for JSON formatting if the writer normalizes whitespace.

```powershell
$json = Get-Content .plugin-efficiency.json -Raw | ConvertFrom-Json
$json | Add-Member -NotePropertyName 'output_economy_baseline' -NotePropertyValue $baseline -Force
$json | ConvertTo-Json -Depth 20 | Set-Content -Encoding utf8 .plugin-efficiency.json
```

These baseline values feed the `Before / After / Direction` columns in the final report Quality Movement table.

- [ ] **Step 2: Run existing efficiency audit**

Identify the current efficiency audit command from the repo scripts, then run it from the plugin root. If the script writes a timestamped report, update `artifacts/efficiency/latest.json`.

- [ ] **Step 3: Record target deltas**

Record these targets in `.plugin-efficiency.json` using the same merge strategy: add or replace only the top-level `output_economy_targets` key on the existing root object.

```json
{
  "output_economy_targets": {
    "prompt_tokens_estimate_reduction_pct": 20,
    "dispatch_reference_hits_reduction_pct": 25,
    "human_facing_reports_per_phase_default_max": 1,
    "final_report_default": true
  }
}
```

- [ ] **Step 4: Release-note the behavioral change**

Extend `docs/release-notes/RELEASE_NOTES_v0.14.0.md` with the final measured baseline and target deltas. Document that the harness now defers routine reports until round close and preserves evidence as machine-readable packets.

## Task 10: Release Verification And Smoke Test

**Files:**
- No planned source edits unless checks fail.

- [ ] **Step 1: Run static checks**

Run:

```powershell
python scripts/skill-check.py
python scripts/version-check.py
python scripts/catalog-check.py
python scripts/path-hygiene-check.py
python scripts/output_economy_check.py
python scripts/output_economy_smoketest.py
```

Expected: all pass.

- [ ] **Step 2: Run release gate carefully on Windows**

Because this workspace has had CRLF-sensitive bash failures, check line endings before using the shell release gate. If line endings are safe, run:

```powershell
bash scripts/release-gate.sh
```

Expected: release gate passes without CRLF errors.

- [ ] **Step 3: Run simulated live smoke test**

Run:

```powershell
python scripts/output_economy_smoketest.py
```

The smoke test passes only if the fixture contains:

```text
manuscript/main.md
manuscript/revision_log.md
reviews/classification.md
reviews/phase_state.json
reviews/.harness/events.jsonl
reviews/.harness/evidence/round_2026-05-04_001__ph2__001.json
reviews/final_round_report_round_2026-05-04_001.md
```

Expected: the evidence packet and event log share the same `round_id` and `event_id`, no routine Ph2 findings or consolidated findings report is produced, and the compatibility pointer names both the replacement evidence packet and final round report.

- [ ] **Step 4: Confirm working tree**

Run:

```powershell
git status --short
```

Expected: only intentional overhaul files are changed; existing unrelated `README.md` and `scripts/release-gate.sh` edits should be reviewed before staging because they predated this plan.

## Self-Review

Spec coverage:

- Efficiency: covered by output profiles, evidence packets, validator, and efficiency targets.
- Accuracy: preserved through grounding, state ledger, evidence packets, exception reports, and final synthesis.
- Too many outputs: directly addressed by replacing per-phase reports with compact evidence and one final report.
- Intention and goal clarity: addressed in manifest, README, routing spine, and output protocol.
- Architecture evolution: addressed through a new protocol, phase skill changes, agent contract changes, and release validation.
- Orphaned file-structure entries: covered by Task 4.
- Agent contract surface: covered by Task 6 Step 5.
- Backward compatibility: covered by Task 1 section 9 and Task 7 Step 5, with Task 7 explicitly forbidden from appending duplicate protocol text.
- Evidence-packet consumers: covered by Task 1 section 7 and Task 7 Step 4.
- `round_id` and `event_id` ambiguity: resolved by Task 1 section 8 and enforced by Task 3.
- Artifact schema coverage: evidence packets are F7 JSON artifacts and final reports are F8 Markdown-frontmatter artifacts in Task 3.
- Validator architecture: Task 3 adds a JSON validation lane, keeps F7 out of `extract_frontmatter`, keeps F8 in Markdown frontmatter, and prevents F7/F8 from reusing the legacy F1-F6 `COMMON_REQUIRED` fields.
- Vocabulary consistency: Task 4 uses `evidence_status` and `final_report_inputs.checks_skipped`, matching the F7 schema.
- F7 example consistency: Task 1 and Task 3 now use the same nested `final_report_inputs` object and `state_updates` object.
- Validator fixture coverage: Task 3 verifies both an F7 JSON fixture and an F8 Markdown-frontmatter fixture against `artefact_frontmatter_validate.py`.
- Smoke/schema integration: Task 8 requires the smoke test to invoke the schema validator against generated F7 and F8 fixture artifacts.
- Validator scope: Task 8 checks phase skills, Planner, non-Planner agent files, and `references/AGENT_CONTRACTS.md` with separate required-phrase sets.
- Exception-section heuristic: Task 8 defines exact Markdown heading-depth traversal rules for allowed discouraged-default sections.
- Operating manual wording: Task 7 Step 3 supplies concrete replacement text and verification.
- Version bump: Task 2 bumps the plugin to v0.14.0 and creates matching release notes before version checks run.
- Efficiency merge safety: Task 9 requires merging new baseline and target keys into the existing `.plugin-efficiency.json` root object without replacing existing history.
- Baseline reproducibility: Task 9 supplies the exact scan scope and regex patterns used for output-economy counts, including recursive `skills/run-phase-*/SKILL.md` discovery.
- Windows compatibility: Task 9 uses PowerShell 5.1-compatible `ConvertFrom-Json` plus `Add-Member` instead of `ConvertFrom-Json -AsHashtable`.
- Planner merge safety: Task 6 and Task 7 add placement-specific checks for routing, assembly, and compatibility blocks.
- Output-economy baselines: Task 9 Step 1 captures deterministic pre-overhaul values before behavior-changing edits.
- Maintainer daily checks: Task 8 Step 3 updates root `CLAUDE.md`.
- Behavioral verification: covered by Task 8 Step 4 and Task 10 Step 3.

Risk:

- The largest risk is over-trimming audit evidence. The plan avoids that by preserving evidence packets and exception reports.
- The second risk is breaking existing project expectations around named report paths. The migration should keep old paths readable and only change defaults for new rounds.
- The third risk is schema bypass for the new primary evidence artifact. Task 3 makes schema registration a prerequisite before phase behavior changes.
- The fourth risk is vocabulary skew between phase skills and agent contracts. The binding dependency order requires Tasks 1-4 before Tasks 5-7 and adds core vocabulary verification.

Recommended first implementation slice:

Start with Tasks 1-4 only. They define the architectural contract, public intent, artifact schema, identifier rules, and core protocol consumers without touching phase-skill runtime behavior. Then run the validators and review the wording before changing phase skills or agent contracts.
