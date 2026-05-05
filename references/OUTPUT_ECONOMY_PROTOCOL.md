# OUTPUT_ECONOMY_PROTOCOL

**Purpose.** Keep the harness manuscript-first. Phase work should improve the paper, update minimal state, and preserve audit evidence without producing a report stack at every step.

**Authority.** This file is normative for output profiles, evidence packets, events log, cache files, final round report assembly, and compatibility pointers. It extends the Lifecycle-Phase Ladder; it does not replace `PHASE_PROTOCOL.md` phase semantics.

**Schema linkage.** Evidence packets are the **F7** artifact family. Final round reports are the **F8** artifact family. Both are validated by `scripts/artefact_frontmatter_validate.py` — F7 through the validator's **JSON lane**, F8 through **YAML frontmatter** on Markdown. F7/F8 do **not** use the legacy F1–F6 `COMMON_REQUIRED` field set (`cycle_id`, `model_used`, etc.).

**Normative machine contract.** The JSON shape for F7 is also captured for tools at `references/schemas/f7_evidence_packet.schema.json` (JSON Schema). The human-facing section order for F8 is defined by `references/templates/final_round_report.md`.

---

## 1. Output Classes

| Class | Human-facing by default | Purpose |
|---|---:|---|
| Manuscript delta | Yes | The actual paper change. |
| Decision checkpoint | Yes | User approval, blocker choice, scope change, or phase exit. |
| Evidence packet | No | Machine-readable proof that checks ran (F7). |
| Final round report | Yes, once | End-of-round synthesis for the user (F8). |
| Exception report | Yes, on failure | Blocker, failed verifier, stale state, or unresolved contradiction. |

---

## 2. Default Rule

During Ph1–Ph3, do not create a new human-facing report when a compact evidence packet and a short checkpoint can preserve the same information.

---

## 3. Evidence Packet Shape (F7)

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

### 3.1 Required fields (F7)

| Field | Type | Constraints |
|-------|------|-------------|
| `artifact_family` | string | Must be `F7`. |
| `document_type` | string | Must be `evidence_packet`. |
| `round_id` | string | Must match `round_YYYY-MM-DD_NNN`. |
| `event_id` | string | Must match `<round_id>__<kind>__NNN` and **must** begin with `<round_id>__`. |
| `phase` | string | One of `Ph1`, `Ph2`, `Ph3`, `Ph3_converged`, `Ph4`, `round_close`. |
| `target` | string | Manuscript or section path being evidenced (non-empty). |
| `evidence_status` | string | One of `complete`, `partial`, `incomplete`. |
| `created_at` | string | ISO-8601 timestamp (UTC `Z` preferred). |

### 3.2 Optional fields (F7)

All optional. Types are advisory for tooling; the validator enforces top-level presence and coarse types.

| Field | Expected type |
|-------|-----------------|
| `checks_run` | array (entries are strings or small objects with at least a `check_id` or `id` string when object-shaped) |
| `blockers` | array of strings or objects |
| `major_actions` | array of strings or objects |
| `minor_actions_count` | integer ≥ 0 |
| `manuscript_delta_summary` | string |
| `state_updates` | object |
| `source_reads` | array of strings (paths relative to project root) |
| `final_report_inputs` | object; may contain `checks_skipped` (array), `baseline_metrics` (object), `notes` (array) |

### 3.3 SAFEGUARD and checklist consumption

Routine gates (SAFEGUARD subset, deterministic counters, phase-state transitions) read **F7 evidence packets** plus `reviews/phase_state.json` and existing F1–F6 artefacts where still emitted. **Full Markdown F1 findings files** are **exception outputs** when a blocker requires user adjudication, a phase gate fails, the user requests the full report, or a verifier contract still mandates a prose artefact. Do not assume SAFEGUARD reads only Markdown; prefer the evidence packet path recorded in `events.jsonl` and the short action list the Evaluator returns to the Planner.

---

## 4. Escalation Rule

Write a human-facing exception report only when the user must decide, a phase gate blocks, a verifier fails, or the manuscript cannot be changed safely.

---

## 5. Final Report Rule

The final round report is assembled at Ph4 or explicit round close from evidence packets, revision logs, and phase state. The body **must** follow the section order in `references/templates/final_round_report.md` (Paper Delta → Quality Movement → Evidence Summary → Next Actions).

---

## 6. Events And Cache Files

`reviews/.harness/events.jsonl` is append-only. Each line records one event with:

```json
{"round_id":"round_2026-05-04_001","event_id":"round_2026-05-04_001__ph2__001","timestamp":"2026-05-04T00:00:00Z","phase":"Ph2","event":"evidence_packet_written","path":"reviews/.harness/evidence/round_2026-05-04_001__ph2__001.json"}
```

**Operational risk (non-goal for v0.14.0).** A single project-wide `events.jsonl` may grow without bound and assumes a single writer appends lines. Rotation, per-round shards, or multi-process append are **out of scope** for this release; do not introduce parallel appenders without a follow-up locking design.

`reviews/.harness/cache/<content_hash>.json` stores reusable deterministic-check results keyed by manuscript or source content hash:

```json
{"content_hash":"sha256:abc","kind":"deterministic_checks","computed_at":"2026-05-04T00:00:00Z","result":{"clean":true,"counts":{}}}
```

---

## 7. Final Report Assembly

At Ph4 or explicit round close, the Planner reads `events.jsonl`, resolves every `evidence_packet_written` event for the round, loads those evidence packets, then merges them with `manuscript/revision_log.md` and `reviews/phase_state.json`.

Assembly order:

1. Sort evidence packets by `timestamp` or event order.
2. Summarize `manuscript_delta_summary` into Paper Delta.
3. Merge `blockers`, `major_actions`, and `minor_actions_count` into Quality Movement.
4. List `checks_run`, `source_reads`, skipped checks, and verifier failures in Evidence Summary.
5. Derive Next Actions from unresolved blockers first, then unresolved major actions, then phase-gate residue.

If an evidence packet listed in `events.jsonl` is missing, write an exception report and mark the final report `evidence_status: incomplete`; do not fabricate the missing result.

---

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
2. `NNN` is the next unused three-digit integer for that date in the project.
3. The Planner checks existing `reviews/.harness/events.jsonl`, `reviews/final_round_report_*.md`, and `reviews/.harness/evidence/*.json` before choosing a new ID.
4. Event IDs increment monotonically within a round by event-write order.
5. The final report path is `reviews/final_round_report_<round_id>.md`, never a phase event ID.

Uniqueness guarantee:

The Planner refuses to write if the chosen `round_id` or `event_id` already exists in events, evidence filenames, final report filenames, or `phase_state.json` notes for the active project.

---

## 9. Backward Compatibility

Existing projects may still contain `reviews/consolidated_findings_report.md`, `reviews/safeguard_layer_results.md`, `reviews/ph2_findings_*.md`, and other pre-overhaul report paths. These remain readable inputs. New rounds default to evidence packets and final reports, but loaders must treat old report paths as legacy evidence sources.

When a project is mid-round and expects an old path, the Planner writes a **compatibility pointer** instead of silently dropping the artifact:

```markdown
# Compatibility Pointer

This round now uses output economy evidence packets.

Legacy path: `reviews/consolidated_findings_report.md`
Replacement evidence: `reviews/.harness/evidence/<event_id>.json`
Final synthesis: `reviews/final_round_report_<round_id>.md`
```

### 9.1 Which `event_id` to cite when several packets exist

When the pointer must reference **one** replacement evidence file:

1. Prefer the **latest** `evidence_packet_written` line in `reviews/.harness/events.jsonl` for the active `round_id` (last matching line in file order).
2. If no event line exists but one or more F7 files exist on disk for that `round_id`, use the lexicographically greatest `event_id` under `reviews/.harness/evidence/` whose filename starts with `<round_id>__`.
3. If neither exists, omit the back-ticked evidence path and state `evidence_status: incomplete` in the pointer prose; still cite the final report path if already known.

---

## 10. Implementation operational defaults

The architecture freezes F7/F8 shapes and identifier formats. **Implementation** may add operational limits not duplicated here: maximum recommended F7 file size, maximum `events.jsonl` tail read for assembly, and retention policies — provided they do not delete evidence required for an incomplete final report without user direction.
