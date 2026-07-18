# Gate Specifications — co-author-harness v1.0

**Date:** 2026-07-15
**Status:** ⛔ **DRAFT — NOT A CONTRACT. DO NOT IMPLEMENT AGAINST THIS FILE.**
Reviewed and rejected as a v1.0 contract 2026-07-15. The snapshot *boundary* (§2.2) is approved in principle; the *predicates* are not. Superseded for planning purposes by `2026-07-15_predicate-preservation-matrix.md` and `2026-07-15_snapshot-acquisition-contract.md`.
**Scope:** the four gates. Not the router, not the state migrator, not the lens registry.
**Rule for this document:** a gate is a pure function. Anything that is not a predicate over a snapshot does not belong here.

---

## 0. ERRATA — defects confirmed against the tree at HEAD `2e34218`

This file changed semantics while claiming to preserve them. Recorded here rather than silently patched, because the failure mode is the subject of the redesign.

| # | Defect | Where | Status |
|---|---|---|---|
| **E-1** | **§5.1 claims "the 3-round stability rule survives unchanged" and does not.** `PHASE_PROTOCOL.md:154` (P-12) specifies a **four-component stability signature** over three rounds: `grounding_clean`, Check 8 aggregate, findings-delta **≤1**, line churn **≤0.5%**. §5's predicates 2.1–2.2 test two components, use `findings_delta == 0` (tighter), and add exact `convergence_metric` equality (a different axis). **Grounding and accessibility were dropped out of the convergence test.** | §5, `:201` | **REJECTED — rewrite required** |
| **E-2** | **`G2-DRIFT` conflates two predicates.** `[Ph3-STALE]` protects *active acknowledgment that old convergence evidence remains viable*, not byte-identity. Content drift and review-age re-engagement are independent. Must split: `G2-CONTENT-DRIFT` (hash) + `G3-REENGAGEMENT` (age budget). | §5, §5.1 | **REJECTED — split required** |
| **E-3** | **The justification for E-2 was factually false.** §5.1 asserts the clock-based predicate "was not testable." `_is_t3_stale(section, budget_days, now)` at `pre_phase_advance_check.py:861` **already takes `now` as a parameter**; only the context default at `:241` reads the ambient clock. The defect was asserted without reading the function. The argument is withdrawn; any change to these semantics must stand on its own merits. | §5.1 | **WITHDRAWN** |
| **E-4** | **The 63→21 census is not reproducible and undercounts.** §7's MF census came from a pipeline ending in `\| head -20` — **the output was truncated at 20 and 20 was then reported as the count.** Real static census at HEAD: 24 MF tokens. `MF-STRUCTURE`, `MF-ROLE`, `MF-REOPEN`, `MF-STATUS` were dropped by truncation, not judgment. `MF-POLICY`, `MF-FEEDBACK`, `MF-EXPORT` were retired without warrant — `MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md:169` makes them validator predicates, including blocking-feedback adjudication. Dynamic APG families expand into further runtime identities not counted at all. | §7 | **VOID — recount required** |
| **E-5** | **§7.1's third open question is resolved: they are different.** `MF-GATE-M4` (`milestone_framework_validate.py:175`) tests `status == accepted` ∧ `approval` ∧ `handoff == consumed`. `E-MCR-NOT-CLEARED` (`pre_phase_advance_check.py:894`) loops `_is_mcr_cleared(s, ...)` per section. Mapping both to `G3-SECTIONS` erases a predicate. G3 must additionally **re-hash the accepted M4 artifact and its handoff** — `M4.status == accepted` does not detect edits after acceptance. | §7, §7.1 | **REJECTED — separate predicates** |
| **E-6** | **§3.1 took the narrow reading of the contract scope; the universal reading is correct.** The repair is to separate two concepts, not to condition the whole contract: a **generic hash-bound controlling-source contract** is required for *every* academic project (assignment, advisor brief, venue call, or captured user instruction), while the **course-essay milestone profile** is required only when `project.type == course-essay`. Conditioning the entire contract on course-essay would weaken the "read the controlling source; do not guess" rule. | §3, §3.1 | **REJECTED — restructure required** |
| **E-7** | **§8's regression corpus is block-only.** "Every historical BLOCK must still block" is satisfiable by a gate that blocks everything. Regression must equally preserve `PASS`, `LEGACY_READY`, and `NOT_APPLICABLE` outcomes. | §8 | **INSUFFICIENT** |

**Root cause, stated plainly.** E-1, E-3, and E-4 share one mechanism: a claim about existing behavior was asserted from reconstruction rather than read from the source, and then load-bearing design was built on it. E-4 is the sharpest — the measuring pipeline truncated its own input and the artifact of that truncation was reported as a finding. This is the failure class the audit named ("green checks ≠ coherence"), reproduced by the document meant to cure it. The corrective is mechanical, not attitudinal: **§7's census is replaced by a re-runnable script (`scripts/analysis/code_census.py`), and no predicate migrates without a row in the preservation matrix citing its source.**

**Resolved open decisions** (from §7.1, adjudicated at review):
- *Escalation ownership* — not a fifth gate, not Planner-internal. Ownership/transfer validity becomes a **G0 state-integrity predicate**; unresolved escalations become a **G3 ship predicate**.
- *`legacy_unverified` / `superseded`* — removed from live v1 status **only if retained as migration/history concepts**. `legacy_unverified` → explicit migration-pending state. `superseded` → lineage/history event.
- *QE2026* — no current milestone record uses either enum, but several ledgers carry **no milestone framework at all**, and active ledgers use `reopened` and `revision_required`. The migrator needs no-framework, reopen, and historical-supersession rules.

---

---

## 1. Why gates are separable

Today the gate logic lives in four scripts and prose across six reference files, and it does not agree with itself:

```python
# scripts/pre_phase_advance_check.py:254-260
def check_milestone_gate(project_root, document, target_phase, terminal_close=False):
    """Select a shared pre-transition gate; no milestone predicate lives here."""
    boundary = ("ph1_to_ph2" if target_phase == "Ph2" ...)
    result = milestone_validator.validate_gate(project_root, document, boundary)
```

A function named `check_milestone_gate`, dispatching on `target_phase`, returning blocking findings, whose docstring denies it holds a milestone predicate. That is not a bug in a comment — it is what happens when protocol has no home of its own and gets smeared across the agents that obey it.

**The AORE point:** the gates *are* the protocol between agents. Protocol must be specified separately from the parties bound by it, or each party re-interprets it. Four agents × prose substrate = four interpretations, which is the drift the audit measured.

---

## 2. The purity contract

### 2.1 Signature

```
gate(snapshot: ProjectSnapshot, args: GateArgs) -> Verdict
```

```jsonc
Verdict = {
  "gate":     "G0|G1|G2|G3",
  "result":   "PASS | BLOCK | NOT_APPLICABLE",
  "codes":    ["G1-SEQUENCE", ...],        // empty iff PASS
  "advisories": ["G2-BORDERLINE", ...],    // never affect result
  "evidence": [ { "code": "...", "predicate": "...", "observed": "...", "expected": "...", "locator": "path:line" } ]
}
```

**Every BLOCK carries evidence with an observed and an expected value.** A gate that says "blocked" without saying what it read and what it wanted is a gate that cannot be debugged — and, per the audit's central lesson, cannot be checked for correspondence either.

### 2.2 The snapshot boundary — the load-bearing design decision

Gates cannot read the filesystem, the clock, the network, or `git`. All impurity is hoisted into **snapshot acquisition**, performed by the Planner *before* any gate runs:

```
Planner  ──acquire()──>  ProjectSnapshot  ──> G0/G1/G2/G3  ──> Verdict
         (impure: fs,                        (pure: total
          hashes, clock,                      function, no I/O)
          verifier results)
```

```jsonc
ProjectSnapshot = {
  "state":     { /* reviews/project_state.json, parsed */ },
  "files":     { "manuscript/intro.md": { "exists": true, "sha256": "...", "lines": 412 } },
  "now":       "2026-07-15T14:22:00Z",     // injected, never ambient
  "verifiers": [ { "class": 1, "name": "zotero", "query": "...", "returned_id": "10.1000/x", "at": "..." } ],
  "findings":  [ { "id": "F-12", "severity": "BLOCKER", "section": "3. Method", "open": true } ],
  "reviews":   [ { "cycle_id": "...", "profile": "deep", "section": "...", "findings_count": 3, "at": "..." } ]
}
```

Three consequences, each of which fixes a named audit finding:

1. **Gates are unit-testable against fixtures.** No project, no filesystem. This is what makes §6's correspondence checks possible at all.
2. **`now` is an argument.** The old `[Ph3-STALE]` read wall-clock ambiently ("Option A"), making staleness untestable and time-dependent. Injecting `now` makes it a predicate like any other.
3. **Verifier results are inputs, not calls.** Rule 7a's "at least one Class 1 verifier returned a corroborating result **in the current session**" (`EXTERNAL_VERIFIERS.md:22`) becomes a snapshot field. The gate checks the record; it does not make the call. Preserves the rule, removes the I/O.

### 2.3 Invariants

| # | Invariant |
|---|---|
| **I-1** | A gate never writes. Not state, not artifacts, not logs. |
| **I-2** | A gate is total: every snapshot yields a Verdict. No exceptions, no partial evaluation. |
| **I-3** | A gate is deterministic: same snapshot → byte-identical Verdict. |
| **I-4** | A gate evaluates **all** predicates and returns **all** failing codes. No short-circuit — the user sees every blocker at once, not one per round-trip. |
| **I-5** | `PASS` authorizes; it does not act. Only the Planner writes, only after `PASS` **and** explicit user approval. |
| **I-6** | Advisories never change `result`. (Preserves `W-MCR-CONVERGENCE-EVIDENCE`'s evidence-only semantics — `phase_state_schema.md` PR-3b.2.) |
| **I-7** | Every field in `project_state.json` is read by ≥1 gate. An unread field is a BLOCKER in the check suite, not a harmless leftover. |

I-7 is how the 18-field/903-line schema sprawl is prevented from recurring. State exists to be gated on; state that gates nothing is drift waiting to happen.

---

## 3. G0 — ADMIT

> **May work start at all?** Runs first, every invocation. Nothing else runs on `BLOCK`.

`G0(snapshot) -> Verdict`

| # | Predicate | Code | Notes |
|---|---|---|---|
| 0.1 | `state` parses as JSON | `G0-SCHEMA` | |
| 0.2 | `state.schema_version == "1.0.0"` | `G0-SCHEMA` | **Fixes audit M5** — today `SUPPORTED_SCHEMA_VERSION` at `phase_state_validate.py:88` is never referenced in its own file; the schema version is unenforced prose. Here it is predicate #2. |
| 0.3 | `project.type ∈ {research-paper, course-essay, response-letter}` | `G0-UNCLASSIFIED` | |
| 0.4 | `project.p_stage ∈ {P0, P1, P2}` | `G0-UNCLASSIFIED` | |
| 0.5 | `project.venue` non-empty | `G0-UNCLASSIFIED` | |
| 0.6 | **iff** `project.type == "course-essay"`: `project.contract` resolves, and `files[contract].sha256` matches `contract.sha256` | `G0-CONTRACT` | **The conditioning is the fix.** |
| 0.7 | **iff** `project.type == "course-essay"`: contract profile id/path/hash resolve | `G0-CONTRACT` | absorbs `APG-PROFILE-{ID,PATH,HASH,FUNCTIONS,MISSING}` |
| 0.8 | **iff** contract carries policy pins: pins current vs. snapshot | `G0-PIN-STALE` | absorbs `MF-POLICY-*-STALE` (4 codes) |

**Advisory:** `G0-PSTAGE-PROVISIONAL` when `p_stage` is declared but unbacked by a P-stage check (was `W-PSTAGE-UNAVAILABLE`).

### 3.1 The bug this fixes, stated precisely

Current behavior — the contract predicate has **no type condition**:

- `agents/planner.md:40` — "**Before any academic Generator dispatch**, read `references/ASSIGNMENT_MILESTONE_PROCESS.md`, read the controlling brief in full, and **resolve and verify** `reviews/assignment_contract.json`."
- `skills/run-draft/SKILL.md:16` — "`/run-draft` **fails closed** when `reviews/assignment_contract.json` is absent or unresolved."
- `scripts/assignment_process_gate.py:17` — `PROFILE_REL = Path("references/policies/course_essay_milestones.v1.json")` — one hardwired profile.
- `:387` returns `APG-CONTRACT-MISSING` when absent; `:485` defaults `mode` to `"legacy"`.

There is **no `not_applicable` escape**. A CAiSE journal paper has no assignment contract and cannot pass. Predicate 0.6's `iff` is the whole fix.

**Note the ambiguity, and that I am not silently resolving it:** `ASSIGNMENT_MILESTONE_PROCESS.md:5` widens the contract's scope to "assignment, advisor brief, venue call, or current user instruction" — which reads as *universal*, making the course-essay hardwiring at `:17` the bug rather than the fail-closed clause. **If that reading is intended, predicate 0.6 becomes unconditional and `contract` gains a `venue-call` / `user-instruction` variant instead of a type condition.** This is a decision for you, not for me. Predicate 0.6 as written takes the narrow reading because it is the one that unblocks a real project today.

---

## 4. G1 — ACCEPT `M`

> **May milestone M close?** The human checkpoint. The most important gate in the system.

`G1(snapshot, { milestone: "M1".."M5", approval: ApprovalRecord|null }) -> Verdict`

| # | Predicate | Code |
|---|---|---|
| 1.1 | every `M' < M` with `applicability == applicable` has `status == accepted` | `G1-SEQUENCE` |
| 1.2 | `M.applicability == applicable` — else `NOT_APPLICABLE` | — |
| 1.3 | `M.artifact` exists in `files` | `G1-ARTIFACT` |
| 1.4 | `files[M.artifact].sha256 == M.sha256` | `G1-ARTIFACT` |
| 1.5 | `M`'s exit criteria met (§4.2) | `G1-CRITERIA` |
| 1.6 | `approval` present, references `M`, references `M.sha256`, `approval.at` within this invocation | `G1-APPROVAL` |
| 1.7 | no `M' < M` has `status ∈ {reopened, revision_required}` | `G1-STALE` |
| 1.8 | exactly one `primary_lineage` chain resolves through `M` | `G1-LINEAGE` |

### 4.1 The rule G1 exists to protect

> `ASSIGNMENT_MILESTONE_PROCESS.md:77` — "**No file, elapsed time, user silence, or phase advancement counts as milestone acceptance.**"

This is the single most important sentence in the package. Predicate 1.6 is its only home in v1.0. `approval` is an *argument*, not a state field — the gate cannot infer it, cannot find it on disk, and cannot age into it. It is passed by the Planner only after the user says so, this invocation, bound to this artifact hash. That binding is what makes "I approved it" unfalsifiable-by-drift: approve §3 at hash `abc`, edit §3, and 1.4 breaks before 1.6 is even consulted.

### 4.2 Exit criteria per milestone

Predicate 1.5 delegates here. These are the *only* per-milestone special cases in the entire gate system.

| M | Artifact | Exit criteria | Absorbs |
|---|---|---|---|
| M1 | `research_notes/project_memo.md` | non-empty; declares focus/tension/questions; **does not freeze a thesis** (`ASSIGNMENT_MILESTONE_PROCESS.md:17`) | |
| M2 | `references/REFERENCES.md` | ≥1 admitted source; every admit has a Rule 7a row with verifier name + query + returned id (`EXTERNAL_VERIFIERS.md:66`) | `APG-SOURCE-{MISSING,HASH,AUTHORITY}` |
| M3 | `manuscript/outline.md` | every outline node maps to ≥1 M2 source | |
| M4 | `manuscript/*.md` | **all sections `converged` or `ceiling_locked`** (§5.3) | `MF-GATE-M4`, `E-MCR-NOT-CLEARED` |
| M5 | final | delegated to **G3** — G1(M5) is `NOT_APPLICABLE` | `MF-GATE-M5` |

**Conditioned criteria (course-essay only, from the contract profile):**

| Predicate | Code | Source |
|---|---|---|
| exemplar conditioning forbidden at M1–M3 | `G1-EXEMPLAR-SCOPE` | `ASSIGNMENT_MILESTONE_PROCESS.md:55,61-63` — "blocks that flag… at M1-M3". Note the carve-in preserved verbatim: *this restricts conditioning, not scholarship* — M2 may read, annotate, and cite Yu or Dennett under the Grounding Protocol. |
| wiki grounding current or authorized opt-out at M4 | `G1-WIKI-GROUNDING` | `ASSIGNMENT_MILESTONE_PROCESS.md:51,64` — "M5-to-wiki ingestion remains a post-final write-side action and **cannot satisfy this gate**" |

### 4.3 Four status machines → one

Today (`MFHP:44-52`) every milestone record carries four parallel state machines:

```
status           : not_started | in_progress | feedback_pending | revision_required |
                   accepted | reopened | superseded | not_applicable | legacy_unverified   (9)
approval         : pending | approved | rejected | reopened | not_applicable              (5)
handoff          : not_ready | ready | consumed | needs_revalidation | not_applicable      (5)
dependency_state : current | needs_revalidation | not_applicable                           (3)
```

**They encode the same fact four ways**, and can disagree — a record can be `status: accepted` / `approval: rejected` / `handoff: not_ready`, and nothing adjudicates. v1.0:

```
status        : open | submitted | accepted | reopened | not_applicable   (5)
applicability : applicable | not_applicable                              (2)
```

`approval` → predicate 1.6 (an argument, not state). `handoff` → predicate 1.1 (derived: M is "consumed" iff a successor is accepted — a *computation*, not a stored fact). `dependency_state` → predicate 1.7 (derived from upstream `status`). **Three stored machines become three predicates.** Stored state that can contradict other stored state is the drift surface; derived state cannot drift from its source.

`legacy_unverified` and `superseded` are dropped — flag for decision in §7.

---

## 5. G2 — CONVERGE `S`

> **Is section S done iterating?** M4 only. The only loop in the system.

`G2(snapshot, { section: string }) -> Verdict`

| # | Predicate | Code |
|---|---|---|
| 2.1 | last 3 review rows for `S` carry `findings_delta == 0` | `G2-UNSTABLE` |
| 2.2 | last 3 rows carry identical non-null `convergence_metric` | `G2-UNSTABLE` |
| 2.3 | no open finding for `S` with `severity == BLOCKER` | `G2-BLOCKER` |
| 2.4 | ≥1 row with `profile == "deep"` at or after `S.last_substantive_edit` | `G2-NO-DEEP` |
| 2.5 | `files[S.path].sha256 == S.scope_fingerprint` | `G2-DRIFT` |

**Advisory:** `G2-BORDERLINE` — `S` is in the tension band (§5.2). Never blocks (I-6).

### 5.1 What is preserved verbatim

The 3-round stability rule survives unchanged. It was always the right test — it was wired to the wrong ladder, not wrong in itself.

> `PHASE3_PHASE4_COMMON_ENVELOPE.md:48` — object-shaped v0.8.0 rows require **three consecutive** stable rows.

Predicates 2.1–2.2 are that rule, restated as a function. Note this also silently fixes audit **m5**: `commands/run-phase-3.md:3` advertises the *legacy scalar* "two-round" rule as current. There is one rule now, in one place, and it is three.

`G2-DRIFT` replaces `[Ph3-STALE]`. **The semantics change and this is deliberate:** `[Ph3-STALE]` measured *elapsed wall-clock since last activity* (`ph3_last_activity_at`, "Option A"). `G2-DRIFT` measures *whether the reviewed text is the current text*. Elapsed time is not a property of the artifact; a section untouched for six months is not stale, it is finished. A section edited after its last review **is** stale, however recently. This is a better predicate, and it is testable — which the clock-based one was not.

### 5.2 Ceiling-lock — preserved, with its judgment intact

`PHASE_PROTOCOL.md:259-270` (P-8) records a real finding: ~7% of an observed cost overrun (n=1) came from sections iterating inside a narrow band of the stability threshold while one BORDERLINE advisory persisted. The response was a **termination-ranking proposal**, explicitly *not* an admission-rule change:

> `:261` — "The contract does **not** change the §9.4 admission rule (the disjunction is unchanged) and does **not** add a new monotonicity-exempt trigger."

v1.0 keeps the separation exactly:

- **G2** emits `G2-BORDERLINE` when `distance_to_ceiling(S) = abs(line_diff_scalar(S) − stability_threshold)` falls in the tension band `[0, 0.01]`. Advisory only.
- **The Planner** ranks borderline sections (lowest distance first; ties by iterations consumed, descending) and writes the proposal artifact.
- **The user** chooses Option C (ceiling-lock) or Option I (iterate).
- **G3** honors `ceiling_locked` via 5.3's disjunction.

The gate detects. The Planner proposes. The user decides. Ranking logic does **not** enter the gate — it is a heuristic over a scalar, not a predicate, and heuristics in gates are how gates become unfalsifiable.

### 5.3 The §9.4 disjunction

Preserved verbatim as the definition consumed by G1(M4) predicate 1.5 and G3 predicate 3.1:

```
cleared(S)  ≡  S.readiness == "converged"
            ∨  (S.ceiling_locked == true ∧ S.last_approved_readiness == S.applicable_ceiling)
```

> `PHASE_PROTOCOL.md:259` — "a section is MCR-cleared if either `current_phase == Ph3_converged` or (`ceiling_locked == true` AND `last_approved_phase == applicable_ceiling`)."

This is the one place phase vocabulary survives translation rather than deletion, because the disjunction is doing real work: it distinguishes *converged* from *deliberately stopped short*, and a system that cannot say "good enough, on purpose, on the record" will either lie or never ship.

---

## 6. G3 — SIGN M5

> **May the paper ship?** Terminal. Irreversible.

`G3(snapshot, { approval: ApprovalRecord|null }) -> Verdict`

| # | Predicate | Code |
|---|---|---|
| 3.1 | `M4.status == accepted` ∧ ∀S ∈ M4.sections: `cleared(S)` (§5.3) | `G3-SECTIONS` |
| 3.2 | ∀ claim requiring Rule 7a: ≥1 Class 1 verifier row in `snapshot.verifiers` with name + query + returned id | `G3-VERIFY` |
| 3.3 | grounding audit clean — no fabricated citation, no uncited number, no unresolved path | `G3-GROUNDING` |
| 3.4 | signoff artifact carries **exactly one** anchored `status: SIGNED` | `G3-SIGNOFF` |
| 3.5 | no `M' ∈ M1..M4` has `status ∈ {reopened, revision_required}` | `G3-STALE` |
| 3.6 | `approval` present, bound to the M5 artifact hash, this invocation | `G3-APPROVAL` |

Predicate 3.4 preserves a rule the current package got right and should keep the sharp edge on:

> `PHASE_PROTOCOL.md:567` — "Each signoff file carries exactly one anchored line `status: PASS`, `status: APPROVED`, or `status: SIGNED`; **missing, negative, negated, duplicate, or contradictory statuses block.**"

Three signoff vocabularies collapse to one (`SIGNED`). Duplicate-and-contradictory still block — that clause exists because a file with two status lines is a file someone edited without reading, and it is exactly the failure this whole redesign is about.

**G3 is the only gate that consumes `snapshot.verifiers`.** Rule 7a's session-scoping (`EXTERNAL_VERIFIERS.md:22`) is preserved by snapshot construction: the Planner populates `verifiers` from *this session's* calls, so a stale row cannot satisfy 3.2. The rule is unchanged; only its enforcement point moves.

---

## 7. Code migration — 63 → 21

Current: 27 `APG-*` + 20 `MF-*` + 16 `E-*/W-*` across three scripts that do not share a namespace, a severity model, or a caller.

| v1.0 code | Absorbs |
|---|---|
| `G0-SCHEMA` | `APG-PHASE-STATE-MISSING`, `E-ROW-SHAPE-VIOLATION` |
| `G0-UNCLASSIFIED` | `E-CLASSIFICATION-MISSING-AT-T2`, `E-PSTAGE-REQUIRED-AT-T2` |
| `G0-CONTRACT` | `APG-CONTRACT-{MISSING,UNRESOLVED}`, `APG-PROFILE-{ID,PATH,HASH,FUNCTIONS,MISSING}`, `APG-MAPPING` |
| `G0-PIN-STALE` | `MF-POLICY-{PROFILE,PIN-EPOCH,EXEMPLAR-PIN,ATTESTATION-PIN}-STALE`, `MF-POLICY-PROVENANCE` |
| `G1-SEQUENCE` | `APG-SEQUENCE`, `APG-SEQUENCE-{M2,M3,M4,FINAL,TARGET,LEGACY}`, `MF-GATE-CHAIN`, `MF-HANDOFF` |
| `G1-ARTIFACT` | `E-ARTEFACT-{MISSING,MALFORMED}`, `APG-SOURCE-{MISSING,HASH}` |
| `G1-CRITERIA` | `MF-DERIVED`, `MF-CANON`, `MF-BINDING` |
| `G1-APPROVAL` | `APG-RECEIPT-{MISSING,INVALID,STALE,CONSUMED}`, `E-MISSING-T1-SIGNOFF`, `APG-PROFESSOR-COPY-AUTHORITY`, `APG-SOURCE-AUTHORITY` |
| `G1-STALE` | `MF-OVERRIDE` |
| `G1-LINEAGE` | `MF-LINEAGE` |
| `G1-EXEMPLAR-SCOPE` | `APG-EXEMPLAR-SCOPE`, `APG-EXEMPLAR-DENNETT-PENDING`, `MF-EXEMPLAR` |
| `G1-WIKI-GROUNDING` | `APG-WIKI-GROUNDING-{MISSING,STALE}`, `APG-WIKI-OPT-OUT-INVALID` |
| `G2-UNSTABLE` | `E-T3-CONVERGENCE-NULL-AT-SIGNOFF`, `E-T3-TERMINAL-ROW-MISSING` |
| `G2-BLOCKER` | (new — was implicit in the Evaluator envelope) |
| `G2-NO-DEEP` | `E-MCR-PRE-DEEP-PASS-REQUIRED` |
| `G2-DRIFT` | `E-MCR-BLOCKED-T3-STALE` |
| `G2-BORDERLINE` *(advisory)* | `W-MCR-CONVERGENCE-EVIDENCE` |
| `G3-SECTIONS` | `E-MCR-NOT-CLEARED`, `MF-GATE-M4` |
| `G3-VERIFY` | (new — Rule 7a was enforced by Reflector sampling, never gated) |
| `G3-GROUNDING` | (new — same) |
| `G3-SIGNOFF` | `MF-GATE-M5` |
| `G3-APPROVAL` | `MF-EVENT` |
| `G0-PSTAGE-PROVISIONAL` *(advisory)* | `W-PSTAGE-UNAVAILABLE` |

**Retired outright:** `E-ARTEFACT-TIER-MISMATCH` (tier vocabulary — audit M6), `MF-PHASE` (the phase enum embedded in the milestone namespace — the collinearity artifact), `MF-EXPORT`, `MF-FEEDBACK` (feedback-record shape is not a gate predicate; it is a Reflector concern).

### 7.1 Three codes I could not place — decisions for you

Flagged rather than silently resolved, because each encodes judgment I can see but cannot reconstruct:

1. **`E-ESCALATION-WITHOUT-OWNER` / `E-OWNERSHIP-TRANSFER-WITHOUT-RATIONALE`.** These gate *escalation ownership* — who owns a finding when it moves between agents. That is real, and it is not a milestone, readiness, or ship predicate. Either it belongs to a fifth gate (G4 ESCALATE), or it is a Planner-internal rule that was never a gate. I lean Planner-internal; I have no evidence for that lean.
2. **`legacy_unverified` / `superseded` milestone statuses.** Dropped in §4.3's 5-value machine. `legacy_unverified` exists for pre-contract projects; `superseded` for replaced milestones. If any live project carries either, the migrator needs a rule. **This must be checked against QE2026 before step 6.**
3. **`MF-GATE-M4` vs. `E-MCR-NOT-CLEARED`.** Both map to `G3-SECTIONS` above, but they may not be the same assertion — one is a milestone-framework gate, the other an MCR admission check, and the audit found these two subsystems disagreeing elsewhere. If they differ, `G1(M4).1.5` and `G3.3.1` need distinct definitions rather than the shared `cleared(S)`.

---

## 8. Test contract

Purity is only worth what it is tested for. Each gate ships with fixtures **before** any migration step consumes it:

| Class | Requirement |
|---|---|
| **PASS** | one minimal snapshot per gate that passes — the existence proof |
| **BLOCK** | one snapshot per code, asserting exactly that code and no other |
| **Multi-block** | one snapshot per gate failing ≥3 predicates, asserting **all** codes returned (I-4) |
| **Determinism** | each fixture evaluated twice → byte-identical Verdict (I-3) |
| **Totality** | property test: malformed/adversarial snapshots never raise, always return a Verdict (I-2) |
| **Purity** | run under a filesystem/clock/network shim that raises on access. **Any I/O = test failure.** This is the invariant that decays first and is invisible without a shim. |
| **Advisory** | advisories present, `result` unchanged (I-6) |

**Regression corpus:** replay the ~63 current codes against v1.0 gates via the §7 mapping. Every historical BLOCK must still block, or the delta must be an explicit, named decision. This is the guard against §7's collapse quietly dropping a rule someone learned the hard way — 29 minors of accumulated judgment is in those codes, and the audit only proved the *stale* parts stale.

---

## 9. What this does not specify

Named so the boundary is auditable, and so no one mistakes silence for a decision:

- **The router.** `/paper`'s cascade calls these gates; it is not one. Step 7.
- **The migrator.** `phase_state.json` → `project_state.json`. Step 6 — the dangerous one.
- **The lens registry.** `/review --lens=X`. Step 5, independent of gates.
- **Snapshot acquisition.** Impure by design. Needs its own contract — it is where hashes, verifier calls, and `now` enter, and therefore where the purity of everything downstream is actually won or lost.
- **SAFEGUARD couplings.** Check 8 / accessibility feed `G2-BLOCKER` via `snapshot.findings`, but their *internal* logic is untouched here. Per the proposal's §7 caveat, they need an explicit keep/drop decision before step 8 — not a sweep.

---

## 10. Grounding note

Every quoted rule was read from the tree at HEAD `2e34218` and is cited to file:line. The 63 codes in §7 were extracted mechanically (`grep -oE` over the three gate scripts), not recalled. Where a current rule's intent was ambiguous (§3.1, §7.1) the ambiguity is surfaced as a decision rather than resolved by assumption. §5.1's change to `G2-DRIFT` semantics is a deliberate departure from `[Ph3-STALE]`, argued rather than asserted — it is the only predicate in this spec that changes meaning rather than location.
