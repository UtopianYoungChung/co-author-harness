# Assignment Gate Hardening — Self-Enforcing Preflight

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the assignment-process gate impossible to skip before academic drafting: no Generator manuscript/deliverable write without a current, hash-bound READY receipt for the derived active milestone target.

**Architecture:** Keep `assignment_process_gate.py` as the sole predicate engine. Add a Planner-owned **gate receipt** artifact and a **pre-dispatch / pre-write verifier** that fail closed if the receipt is missing, stale, or mismatched. Wire that verifier into `/run-draft`, Planner refuse-to-dispatch, and Generator refuse-to-write. Do not rely on prompt memory alone.

**Tech Stack:** Python 3 stdlib, existing `assignment_process_gate.py`, `reviews/phase_state.json`, F9 patterns, release-gate smoketests.

## Incident grounding (why this plan exists)

Fresh project `2026-07-14_first-principles-RE-essay-fresh` produced a complete ~1,568-word essay under Ph1 while:

- `reviews/assignment_contract.json` was **absent**
- `assignment_process_gate.py` was **never invoked** (no APG traces in the project)
- M1–M3 were **`reopened`**, M4 **`revision_required`**
- The session followed classic “Ph1 = draft the full essay,” not M1→M2→M3 checkpoints

Conclusion already verified: the gate is fail-closed **when run**, but live sessions can skip running it. Prompt/skill text alone is insufficient.

## Global Constraints

- Grounding Protocol absolute; no fabricated contracts, receipts, wiki evidence, or acceptance.
- `phase_state.json` remains sole milestone-state authority; Planner sole writer of ledger + receipts.
- Do not invent a second milestone ledger; receipts are evidence that the existing gate passed.
- Ph1–Ph4 stay orthogonal to M1–M5.
- Professor-copy policy unchanged.
- Do not silently repair the fresh project’s ledger or invent its missing contract as part of this harness change.
- Surgical diffs; extend existing gate rather than rewriting milestone_framework_validate.

---

## Clarifying assumptions (confirm before coding)

| # | Assumption | Default |
|---|---|---|
| H1 | Hardening applies to projects that declare / bind the course-essay assignment profile (or any project that has, or is required to have, `assignment_contract.json`). | **Yes** |
| H2 | Projects with no academic assignment (pure internal notes) may remain outside this gate via explicit `assignment_contract.status: not_applicable` with authorized reason—or by not using `/run-draft` for academic deliverables. Prefer fail-closed for `/run-draft` on research deliverable trees. | **Fail closed for `/run-draft`** |
| H3 | A READY receipt is single-use for one Planner→Generator dispatch of one target; a new draft round requires a fresh receipt. | **Yes** |
| H4 | Mechanical enforcement = scripts that return non-zero + agent refuse rules that cite those scripts. No OS file locks required in v1. | **Yes** |
| H5 | Package version bump is a separate release decision after hardening lands. | **Yes** |

---

## Target enforcement model

```
User: /run-draft (or equivalent academic draft request)
  → Planner derives active_target (first non-accepted M1–M4; else FINAL path)
  → Planner ensures assignment_contract.json is resolved (or halts)
  → Planner runs assignment_process_gate.py --stage draft --target-milestone <T>
  → On READY: Planner writes gate receipt (path + hashes + target + wall time)
  → Planner may dispatch Generator only with receipt path in the dispatch brief
  → Generator runs assignment_dispatch_preflight.py (or gate --verify-receipt)
       before any deliverable/manuscript write
  → On non-zero: Generator writes nothing; returns blocker to Planner
  → After Generator finishes OR dispatch aborted: Planner invalidates/consumes receipt
  → M1–M3 still stop for user approval before acceptance (unchanged auto-walk)
```

### Why receipts (not only re-running the gate)

Re-running the gate at Generator time is necessary but not sufficient for audit: the receipt binds **which** READY result authorized **this** dispatch (target, contract hash, phase_state hash, gate stdout digest, timestamp). That closes “I meant to run it” without evidence.

---

## File structure

### New

- `scripts/assignment_dispatch_preflight.py` — verifies receipt + re-validates gate predicates for the receipt’s target; exit 0 only when both match.
- `scripts/assignment_dispatch_preflight_smoketest.py` — missing contract, missing receipt, stale receipt, wrong target, READY happy path, consume/invalidate.
- `references/schemas/assignment_gate_receipt.schema.json` — strict receipt schema.
- `references/templates/assignment_gate_receipt.json` — bootstrap template.

### Extend

- `scripts/assignment_process_gate.py` — optional `--emit-receipt <path>` on READY; optional `--verify-receipt <path>`.
- `scripts/assignment_process_gate_smoketest.py` — receipt emit/verify cases (or keep solely in preflight smoketest).
- `references/ASSIGNMENT_MILESTONE_PROCESS.md` — § Hardening / receipt lifecycle.
- `agents/planner.md` — refuse Generator dispatch without writing a fresh READY receipt; consume after round.
- `agents/generator.md` — refuse all academic deliverable/manuscript writes until preflight exit 0; cite receipt path.
- `skills/run-phase-1/SKILL.md`, `skills/run-draft/SKILL.md` — Step 0 becomes: contract → derive target → gate → emit receipt → only then dispatch; no parallel “draft the essay” shortcut.
- `skills/run-phase-4/SKILL.md`, `skills/run-finalize/SKILL.md` — final path emits/verifies FINAL receipt.
- `references/AGENT_ORCHESTRATION.md` §10 — self-enforcing preflight paragraph.
- `references/PROJECT_BOOTSTRAP.md` (or course-essay bootstrap note) — creating a course-essay project requires resolving `assignment_contract.json` before first `/run-draft`.
- `scripts/release-gate.sh` — add preflight smoketest next to assignment gate smoketest.
- `references/MANIFEST.md` — route hardening docs.

### Reuse

- Existing `assignment_process_gate.py` predicates (sequence, wiki, exemplar, legacy).
- F9 / milestone acceptance still owned by Planner after user checkpoint.

---

## Receipt schema (minimum)

Path: `reviews/.harness/assignment/gate_receipt_<target>_<utc>.json`

```json
{
  "schema_version": "1.0.0",
  "receipt_id": "uuid-or-ulid",
  "status": "ready",
  "stage": "draft",
  "target_milestone": "M1",
  "project_root_name": "2026-07-14_first-principles-RE-essay-fresh",
  "produced_at": "RFC3339",
  "consumed_at": null,
  "authority": "planner",
  "gate_command": ["python", "scripts/assignment_process_gate.py", "..."],
  "gate_exit_code": 0,
  "gate_stdout_sha256": "...",
  "assignment_contract_sha256": "...",
  "phase_state_sha256": "...",
  "profile_sha256": "...",
  "exemplar_conditioning": false,
  "active_lineage_id": "main"
}
```

Rules:

- `status` is `ready` | `consumed` | `invalidated`.
- Generator accepts only `ready` with matching live hashes.
- Planner sets `consumed_at` and `status: consumed` after the dispatch round ends (success or abort).
- Hash drift on contract or phase_state → preflight fails with `APG-RECEIPT-STALE`.

New codes (proposed):

- `APG-RECEIPT-MISSING`
- `APG-RECEIPT-STALE`
- `APG-RECEIPT-TARGET-MISMATCH`
- `APG-RECEIPT-CONSUMED`
- `APG-RECEIPT-INVALID`
- `APG-DISPATCH-REFUSED` (Planner-facing aggregate when preflight blocks dispatch)

---

## Task 1: Receipt emit + verify in the gate

**Deliverable:** Gate can emit and verify receipts.

- [ ] Add schema + template files.
- [ ] On READY, support `--emit-receipt PATH` writing the receipt object (Planner normally supplies path under `reviews/.harness/assignment/`).
- [ ] Support `--verify-receipt PATH` that: loads receipt; recomputes contract/phase_state/profile hashes; re-runs validate() for receipt target; fails on mismatch/consumed/invalid.
- [ ] Smoketest: emit on M1 READY; verify passes; mutate phase_state → verify fails `APG-RECEIPT-STALE`; mark consumed → `APG-RECEIPT-CONSUMED`.
- [ ] Document in `ASSIGNMENT_MILESTONE_PROCESS.md`.

**Verify:** Without a valid receipt path, `--verify-receipt` cannot pass.

---

## Task 2: `assignment_dispatch_preflight.py`

**Deliverable:** Single entrypoint Generator/Planner must call before writes/dispatch.

```text
python scripts/assignment_dispatch_preflight.py \
  --project-root <root> \
  --receipt <receipt.json> \
  --expected-target <M1|M2|M3|M4|FINAL>
```

- [ ] Exit 0 only if receipt verifies and `target_milestone == expected-target`.
- [ ] Exit 4 with blocker codes otherwise (never write project files).
- [ ] Smoketest covers: missing contract (via verify), missing receipt, wrong target, happy path.
- [ ] Wire into `release-gate.sh`.

**Verify:** A temp project shaped like the fresh failure (no contract, no receipt) cannot get exit 0.

---

## Task 3: Planner refuse-to-dispatch (hard instruction + checklist artifact)

**Deliverable:** Planner cannot claim a Generator dispatch without a receipt.

- [ ] Update `agents/planner.md`: before any Generator dispatch for academic deliverables, mandatory sequence is derive target → run gate → `--emit-receipt` → include receipt path in dispatch brief → only then Agent-tool dispatch.
- [ ] Require dispatch brief to contain an exact line: `assignment_gate_receipt: <path>` and `assignment_gate_target: <T>`.
- [ ] After round: mark receipt consumed in the same Planner transaction style (atomic write); never leave a reusable READY receipt lying around across sessions.
- [ ] Update `AGENT_ORCHESTRATION.md` §10 auto-walk with the receipt lifecycle.
- [ ] Update `/run-draft` / `run-phase-1` Step 0 to name the preflight scripts explicitly; state that writing `ph1_draft_completion.md` for a full essay while M1–M3 are non-accepted is a protocol violation.

**Verify:** Doc/agent text makes “draft complete essay at Ph1 without M1 acceptance” an explicit refuse condition for course-essay profile.

---

## Task 4: Generator refuse-to-write

**Deliverable:** Generator invariant is mechanical, not advisory.

- [ ] Update `agents/generator.md`: first action on academic write requests is run `assignment_dispatch_preflight.py`; on non-zero, write **zero bytes** to manuscript/deliverable paths and return the blocker block verbatim.
- [ ] Clarify deliverable paths in scope: `manuscript/**`, `milestones/**`, `research_notes/project_memo.md`, `research_notes/annotated_references.md`, outline deliverables bound as milestone artifacts—not only `main.md`.
- [ ] Smoketest or agent-contract note: optional lightweight test that preflight is listed in Generator invariants (catalog/contract check if one exists); do not fake an LLM test.

**Verify:** Generator prompt states refuse-to-write with script citation; no “best effort draft anyway” escape hatch.

---

## Task 5: Bootstrap / contract resolution fail-closed

**Deliverable:** Course-essay projects cannot start `/run-draft` without a contract.

- [ ] Bootstrap / PROJECT_BOOTSTRAP (or assignment process §): first `/run-draft` on a course-essay tree must create/resolve `assignment_contract.json` (source path + sha256 + profile pin) or halt with `APG-CONTRACT-MISSING`.
- [ ] Optional helper: `scripts/assignment_contract_init.py` that refuses to invent source hashes—requires user-supplied assignment path and computes sha256. (Only if it stays thin; otherwise document manual resolution.)
- [ ] Document operator steps for the fresh project: resolve contract, then M1 receipt-gated memo—not another full-essay Ph1.

**Verify:** Documented path from empty reviews/ → contract → M1 receipt → memo only.

---

## Task 6: Regression against the fresh-failure shape

**Deliverable:** Fixture that encodes the incident class.

- [ ] Add fixture dir `scripts/fixtures/assignment_dispatch_preflight/fresh_skip_gate/` (or generate in smoketest):
  - phase_state with native mode, M1–M3 reopened, manuscript present
  - **no** assignment_contract.json
  - **no** receipt
- [ ] Assert preflight exit 4 with `APG-CONTRACT-MISSING` or `APG-RECEIPT-MISSING` (contract missing may surface first).
- [ ] Second fixture: contract present, M1 not accepted, receipt claims M4 → `APG-RECEIPT-TARGET-MISMATCH` or gate sequence failure on verify.
- [ ] Keep live fresh project untouched by the harness change set.

**Verify:** Incident class is a permanent regression, not only narrative in this plan.

---

## Out of scope (v1)

- OS-level hooks that intercept every filesystem write.
- Auto-creating assignment PDFs or wiki evidence.
- Auto-accepting M1–M3 on the fresh or legacy RE-essay projects.
- Replacing F9 / milestone_framework_validate.
- Package version bump (decide at release).

---

## Suggested order

1. Task 1 — receipt emit/verify  
2. Task 2 — preflight entrypoint + release-gate wire  
3. Task 6 — fresh-failure fixture (lock the incident)  
4. Task 3 — Planner refuse-to-dispatch  
5. Task 4 — Generator refuse-to-write  
6. Task 5 — bootstrap / contract resolution docs (+ optional init helper)

---

## Done criteria

- A project without `assignment_contract.json` cannot obtain a READY receipt or preflight exit 0.
- Generator instructions require preflight exit 0 before any academic deliverable write.
- Planner instructions forbid Generator dispatch without a fresh READY receipt for the derived target.
- Fresh-failure fixture is regression-covered.
- Existing assignment_process_gate smoketest still passes.
- No silent mutation of live RE-essay trees in this change set.

---

## Codex handoff note

Implement Tasks 1→2→6 first (mechanical), then 3→4→5 (agent/bootstrap wiring). Prefer TDD on receipt/preflight scripts. Report files changed, new codes, tests run, and any deviation from this plan.
