# Assignment Auto-Walk, Wiki Grounding, and M4-Only Exemplar Gates

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the course-essay assignment process mechanically enforce M1→M2→M3 before M4 drafting, require wiki-first grounding evidence before M4, and restrict Yu/Dennett domain-native exemplar conditioning to M4 (and later final-paper) drafting only.

**Architecture:** Extend the existing fail-closed `assignment_process_gate.py` with a `target_milestone` argument and three new check families (sequence, wiki grounding, exemplar scope). Wire Planner auto-walk as an explicit dispatch loop with user acceptance checkpoints—not silent auto-accept. Keep Ph1–Ph4 orthogonal; reuse F9 handoffs and `milestone_framework_validate` rather than inventing a second ledger.

**Tech Stack:** Python 3 stdlib, existing JSON contracts (`assignment_contract.json`, `phase_state.json`), Planner/Generator agent prompts, `/run-draft` / `/run-finalize` skills, release-gate smoketests.

## Global Constraints

- Grounding Protocol remains absolute; no fabricated wiki pages, citations, or acceptance evidence.
- `reviews/phase_state.json` remains the sole milestone-state authority; Planner is sole writer.
- M1–M5 machine slots stay orthogonal to Ph1–Ph4.
- Professor-copy production remains author-controlled unless explicitly requested.
- FINAL continues to map to terminal framework slot M5 and is not renamed as a fifth assigned milestone.
- “Dennett” is the intentional-root (`argument-only`); “Yu” is the domain-native surface-register centroid. Never treat Dennett prose as a surface-emulation target (C-7 / J-in-H fence).
- Auto-walk never invents M1–M3 acceptance; each milestone still needs deliverable + feedback gate + approval + F9 where the handoff protocol requires them.
- Live RE-essay legacy migration remains a separate adjudication path; this plan must not silently promote `not_started` M1–M3 to `accepted`.

---

## Clarifying assumptions (confirm before coding)

| # | Assumption | Default in this plan |
|---|---|---|
| A1 | “Auto-walk” means Planner-orchestrated sequential dispatch with a user checkpoint after each of M1, M2, M3—not unattended acceptance. | **Yes** |
| A2 | “Denette” means **Dennett** intentional-root in the domain-native register. | **Yes** |
| A3 | Wiki grounding before M4 means: project is wiki-linked (or explicitly opted out with recorded reason), wiki-first discovery has run, and a hash-bound grounding evidence artifact exists. | **Yes** |
| A4 | Yu/Dennett exemplar *retrieval conditioning* is forbidden for M1–M3 Generator prose; M1–M3 may still *cite* Yu as a scholarly source in the ordinary bibliography sense. | **Yes** |
| A5 | Native projects only for auto-walk v1; legacy projects keep `LEGACY_READY` / migration-boundary rules and must not be auto-walked into fake acceptance. | **Yes** |

If any assumption is wrong, stop and revise this plan before Task 1.

---

## File structure

### Extend

- `scripts/assignment_process_gate.py` — add `--target-milestone {M1,M2,M3,M4,FINAL}` (FINAL aliases stage `final`); sequence + wiki + exemplar-scope checks.
- `scripts/assignment_process_gate_smoketest.py` — fixtures for the new blockers.
- `references/ASSIGNMENT_MILESTONE_PROCESS.md` — normative auto-walk + gate matrix.
- `references/policies/course_essay_milestones.v1.json` — optional machine fields: `autowalk`, `wiki_grounding_before`, `exemplar_conditioning_from`.
- `agents/planner.md` — auto-walk dispatch loop.
- `agents/generator.md` — exemplar-scope refusal for M1–M3; require wiki evidence before M4.
- `skills/run-phase-1/SKILL.md` / `skills/run-draft/SKILL.md` — pass target milestone into the gate.
- `skills/run-phase-4/SKILL.md` / `skills/run-finalize/SKILL.md` — unchanged final gate, plus note that exemplar conditioning remains allowed.
- `references/MANIFEST.md`, `references/AGENT_ORCHESTRATION.md` §10 — route the new behavior.
- `scripts/release-gate.sh` — already lists the smoketest; keep coverage green.

### Reuse (do not reimplement)

- F9 predecessor consumption (`MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md`, `milestone_framework_validate.py`).
- Ph1→Ph2 pre-advance already requires M1–M3 READY chain (`PHASE_PROTOCOL.md` §8).
- Wiki-first order + SK-33 `seed-snowball-discovery` / SK-36 inherit (`EXTERNAL_VERIFIERS.md` §1.5).
- Domain-native register + `/repin-register` (Yu centroid; Dennett intentional-root pending grounding).

### New evidence artifact (project-local)

- `reviews/.harness/assignment/wiki_grounding_<round>.json` — hash-bound record that wiki-first discovery completed for the active lineage before M4. Schema sketched in Task 2.

---

## Gate matrix (target behavior)

| Target | Contract/hash checks | Predecessor accepted | Wiki grounding evidence | Yu/Dennett exemplar conditioning |
|---|---|---|---|---|
| M1 | required | n/a | not required | **forbidden** |
| M2 | required | M1 `accepted` (native) | not required | **forbidden** |
| M3 | required | M1+M2 `accepted` | not required | **forbidden** |
| M4 | required | M1+M2+M3 `accepted` | **required** (or authorized opt-out) | **allowed** |
| FINAL | current `final` checks | M1–M4 `accepted` | must remain current / non-stale | **allowed** |

New blocker codes (proposed):

- `APG-SEQUENCE-Mn` — drafting target `n` while required predecessors are not `accepted`.
- `APG-WIKI-GROUNDING-MISSING` — M4/FINAL without current wiki-grounding evidence.
- `APG-WIKI-GROUNDING-STALE` — evidence hash/path drift vs declared sources.
- `APG-WIKI-OPT-OUT-INVALID` — opt-out missing authority/reason/evidence.
- `APG-EXEMPLAR-SCOPE` — M1–M3 dispatch requested exemplar-conditioned drafting.

---

## Task 1: Sequence gate (auto-walk prerequisite)

**Deliverable:** `--target-milestone` sequence enforcement in `assignment_process_gate.py`.

- [ ] Extend smoketest: temp project with only M1 accepted → M2 draft READY; M3/M4 blocked with `APG-SEQUENCE-*`.
- [ ] Extend smoketest: all of M1–M3 accepted → M4 draft READY on sequence (wiki check stubbed/skipped until Task 2, or temporarily marked not-applicable in fixture).
- [ ] Implement predecessor lookup from `phase_state.json` → `milestone_framework.milestones[Mn].status == "accepted"`.
- [ ] Native-only for v1: if `mode == "legacy"`, emit `APG-SEQUENCE-LEGACY` advisory-or-blocker per confirmed assumption A5 (default: **blocker** that names migration/acceptance work required—do not invent acceptance).
- [ ] Keep `--stage draft|final` working: `final` implies target FINAL; `draft` without `--target-milestone` defaults to **reject** (fail-closed) or to reading `assignment_contract.active_target`—prefer explicit `--target-milestone` (fail-closed if absent).
- [ ] Update `ASSIGNMENT_MILESTONE_PROCESS.md` gate semantics table.
- [ ] Run `python scripts/assignment_process_gate_smoketest.py`.

**Verify:** M4 cannot pass sequence checks while any of M1–M3 is `not_started` / `in_progress` / non-accepted.

---

## Task 2: Wiki grounding evidence + M4 gate

**Deliverable:** Fail-closed wiki grounding before M4.

### Evidence schema (minimum)

```json
{
  "schema_version": "1.0.0",
  "lineage_id": "live",
  "produced_at": "RFC3339",
  "wiki_path": "...",
  "wiki_first_resources": true,
  "skills_invoked": ["seed-snowball-discovery"],
  "references_path": "references/REFERENCES.md",
  "references_sha256": "...",
  "graph_path": ".../graphify-out/graph.json",
  "graph_sha256_provenance": "...",
  "sources_consulted": [{"path": "...", "sha256": "..."}],
  "authority": "planner",
  "notes": "non-empty"
}
```

- [ ] Add writer helper or Planner obligation: after SK-33/SK-36 (or equivalent wiki-first pass), write the evidence file and bind its path+sha256 on the M3→M4 F9 packet or under `milestone_framework` policy_evidence (prefer F9 / harness evidence path already used by MF-POLICY).
- [ ] Gate M4: require evidence file present, hashes match, `wiki_first_resources: true` OR a separate authorized opt-out object with `authority ∈ {user, advisor, instructor}` and non-empty reason.
- [ ] Smoketest: M1–M3 accepted, no wiki evidence → M4 `APG-WIKI-GROUNDING-MISSING`.
- [ ] Smoketest: stale references hash → `APG-WIKI-GROUNDING-STALE`.
- [ ] Smoketest: valid evidence → sequence+wiki READY for M4 (exemplar scope still open until Task 3).
- [ ] Document that Coupling D (ingest M5 → wiki) remains **after** final, not a substitute for pre-M4 grounding.

**Verify:** Live RE-essay M4 remains blocked until either real wiki-grounding evidence is filed or an explicit opt-out is approved—**do not** fabricate evidence in the live project during harness work.

---

## Task 3: Yu/Dennett exemplar conditioning only from M4

**Deliverable:** Exemplar write-discipline is milestone-scoped.

- [ ] Add profile fields, e.g. `"exemplar_conditioning_from": "M4"` and `"exemplar_roles": ["yu-centroid-surface", "dennett-intentional-root-argument-only"]`.
- [ ] Generator invariant: for target M1–M3, do **not** retrieve/condition on `domain_native_register.exemplar_members` / near-neighbor passages; ordinary citation of Yu (or others) in M2 annotations remains allowed.
- [ ] Generator invariant: for target M4/FINAL, condition drafting on retrieved Yu near-neighbors for surface register; Dennett only if admitted past deny-list and only with `warrant_scope: argument-only` (never surface pastiche).
- [ ] Gate check `APG-EXEMPLAR-SCOPE`: if contract or dispatch plan sets `exemplar_conditioning: true` for M1–M3, block.
- [ ] Evaluator/Check-8 / accessibility overlay: when reviewing M1–M3 artifacts, treat missing exemplar warrant as **out of scope** (not advisory findings); enable warrant checks from M4 onward.
- [ ] Smoketest: dispatch flag `exemplar_conditioning=true` at M2 → blocker; at M4 → allowed.
- [ ] Note Dennett pending-grounding status: if still not admitted, M4 may use Yu surface exemplars while Dennett remains blocked/absent without failing the whole M4 gate—record as `APG-EXEMPLAR-DENNETT-PENDING` **advisory**, not blocker, until the wiki source is grounded.

**Verify:** M1–M3 prose path cannot require Yu/Dennett register retrieval; M4 can.

---

## Task 4: Planner auto-walk loop (orchestration)

**Deliverable:** Documented + agent-enforced walk, not a daemon.

Pseudo-loop for `/run-draft` on a native course-essay project:

```
run assignment_process_gate --stage draft --target-milestone <active>
if MISCONFIGURED: halt and report blockers
if active in {M1,M2,M3}:
    dispatch Generator for that deliverable only (no exemplar conditioning)
    run feedback/adjudication path per MILESTONE_FEEDBACK_HANDOFF_PROTOCOL
    STOP for user approval / acceptance
    on acceptance: write F9 packet; advance active_target to next
if active == M4:
    require wiki grounding evidence (Task 2)
    allow exemplar conditioning (Task 3)
    dispatch Generator for complete draft
    STOP for feedback iteration with user
if active == FINAL:
    require --stage final READY
    dispatch under Ph4 / finalize rules
```

- [ ] Add `assignment_contract.active_target` (or read from milestone statuses: first non-accepted in sequence).
- [ ] Update `agents/planner.md` with the loop and halt-for-approval rule.
- [ ] Update `AGENT_ORCHESTRATION.md` §10 with the assignment auto-walk paragraph.
- [ ] Update `run-phase-1` / `run-draft` step 0 to pass `--target-milestone`.
- [ ] Explicitly forbid “draft the whole paper” shortcuts that jump to M4 while earlier milestones are open.

**Verify:** A fresh native fixture walks M1→M2→M3 with three approval stops before M4 becomes reachable.

---

## Task 5: Regression + release wiring

- [ ] Expand `assignment_process_gate_smoketest.py` for Tasks 1–3 cases.
- [ ] Add one adversarial fixture directory if needed under `scripts/fixtures/` (mirror milestone-framework style).
- [ ] Run: assignment gate smoketest, milestone_framework smoketest (no regressions), skill-check, catalog-check, path-hygiene, version planes as needed.
- [ ] Confirm release-gate still invokes the expanded smoketest.
- [ ] Do **not** mutate live professor-facing DOCX/Google Docs.
- [ ] For the live RE-essay: document operator path to reach M4 legally (accept/promote M1–M3 under migration rules **or** complete native acceptance)—no silent status rewrite in this task.

---

## Out of scope (v1)

- Unattended overnight auto-accept of milestones.
- Auto-creating Dennett wiki source pages.
- Changing professor-copy export behavior.
- Replacing F9 / `milestone_framework_validate` with the assignment gate.
- Forcing wiki grounding for non-course-essay profiles (gate remains profile-bound until a second profile exists).

---

## Suggested implementation order

1. Task 1 (sequence) — unlocks honest fail-closed M4 blocking beyond today’s contract-only draft READY.
2. Task 2 (wiki) — matches “ground truth before M4.”
3. Task 3 (exemplar scope) — matches “Yu/Dennett only at M4.”
4. Task 4 (Planner loop) — makes the auto-walk operable in sessions.
5. Task 5 (release) — freeze the contract.

---

## Done criteria

- Native fixture: cannot start M4 until M1–M3 are `accepted` **and** wiki grounding evidence is current.
- Native fixture: M1–M3 Generator path refuses exemplar conditioning; M4 allows Yu (and Dennett argument-only when admitted).
- Planner `/run-draft` walks M1→M3 with user checkpoints.
- Existing assignment draft/final contract checks remain green.
- Live RE-essay final gate still blocks until real acceptance work is done; no fabricated evidence.
