# FULL_RUN_CONTRACT.md — run scope, authorization to write prose, and terminal claims

**Output and shipment authority.** `references/role_output_contract.json` 3.0.0 governs the six fixed roles and nine triggered F1-F9 classes. This full-run contract governs scope and terminal claims; it does not convert a readable F7/F8, legacy event, or file-presence observation into shipment-v2 transaction evidence or proof of consumer application. Each observed trigger occurrence still requires its contract-defined closure and any terminal consumer must verify the separately pinned receipt chain.

> **Canonical surface.** This file is the single normative home for: what a
> whole-lifecycle request means, what authorizes writing academic prose, what a
> child dispatch may be told, and what authorizes a terminal claim. Other files
> **route here**; they do not restate these rules. Duplicated policy prose
> drifts — that is the defect this file exists to close, not to reproduce.
>
> **Mechanical authority.** Every rule below that can be checked is checked by
> `scripts/full_run_contract_check.py`. Where this file and that script
> disagree, the script is the contract and the disagreement is a bug. Prose an
> agent may simply not read is not enforcement.

---

## 0. Why this file exists

A user asked (audit `local_7fe69519…/audit.jsonl:1`, 2026-07-17):

> "Harness full run: referring to the LLM wiki, draft me a short essay (soft
> 2000-word limit) on Actor vs. Agency or Actor and Agency."

What the session actually did, from the same audit — not from its own summary:

| Audit | Observed |
|---|---|
| `:112` | Dispatched the Evaluator with: *"This is a LIGHTWEIGHT run — no project scaffold, no phase_state.json. Do NOT attempt to write reviews/ artifacts or bootstrap state. Return findings in your response only."* |
| `:185` | Repeated the response-only pattern for the Ph4 subdispatch |
| `:278` | Response-only re-audit |
| `:333` | Ad hoc review record invented outside the artefact contract |
| `:342` | *"Ladder complete — Ph1 draft → Ph3 evaluator + revision → Ph4 grounding audit, **PASS** on re-audit."* |

A complete essay was written with no project root, no assignment contract, no
phase state, no milestone acceptance, no F7/F8/F9, and no G.4 — and was then
reported as a completed ladder. **Every individual agent file already forbade
this.** The package said so in prose and enforced none of it:

- `references/AGENT_ORCHESTRATION.md` — permissions are "not structurally
  enforced by the filesystem."
- The assignment gates are the real fail-closed mechanism, but every one is
  `--project-root`-parameterised: with **no project at all**, no gate can fire.
- `run_scope` did not exist anywhere in the package, so a parent's intent could
  not constrain a child's dispatch.
- No deterministic check stood between an agent and the sentence "ladder
  complete."

The lesson is the one this repository keeps relearning: **a rule that only
exists as prose is a rule the system does not have.**

---

## 1. Run scope

Every invocation of this package has exactly one **run scope**. It is declared,
not inferred.

| Scope | Meaning | May write prose? | May advance lifecycle? | May claim terminal? |
|---|---|---|---|---|
| `full_lifecycle` | The canonical draft lifecycle: milestones, state, evidence, handoffs | Yes — via Generator, once authorized (§2) | Yes | Yes — only via §4 |
| `lab_iteration` | Transient proposal work in a resolved governed staging/private-shipment destination | Proposal bytes only | **No** | **No** |
| `adhoc_review` | A one-off read/critique the user explicitly asked for | **No** | **No** | **No** |

### 1.1 Scope is DECLARED, never sniffed

**The mechanism is the declaration, not the phrasing.** A request whose intent
is to produce or advance an academic deliverable is `full_lifecycle`, and
`full_lifecycle` is the **default** for any prose-producing request.
`adhoc_review` and `lab_iteration` must be **explicitly** declared. Ambiguity resolves to
`full_lifecycle`: guessing `adhoc_review` silently skips the lifecycle, while
guessing `full_lifecycle` costs one bootstrap prompt the user can decline.
`lab_iteration` is never inferred from a request for a draft or full run; it is
an explicit proposal-only laboratory scope with its own governed destination.

Phrases like "Harness full run", "draft the whole paper", or "run the ladder"
are **recognition aids only**. They are not the contract, and no gate keys off
them:

- `full_run_contract_check.py intent` is **advisory** — it always exits 0, it
  returns a `suggested_run_scope`, and it authorizes nothing. If it could
  authorize, a phrase list would be the contract, and a phrase list only
  catches the wordings someone already thought of. The next failure will be
  worded differently from the last one.
- `authorize` takes an **explicit** `--run-scope`. It never reads the request
  text. An unanticipated wording of "just have a look" cannot silently
  authorize the ad hoc path.
- `scope` compares **declared** parent and child scopes. A brief with no
  `run_scope:` line is refused (`FRC-SCOPE-UNDECLARED`) rather than guessed at.

This is why the repair generalises past the one sentence that triggered it: the
enforcement surface is the declaration and the project state, both of which are
structural facts, not turns of phrase.

### 1.2 Scope is inherited exactly

The exact diagnostic order is `adhoc_review < lab_iteration < full_lifecycle`.
A child declaration different from its parent is always refused: movement down
is `FRC-SCOPE-DOWNGRADE`, movement up is `FRC-SCOPE-ESCALATION`, and omission is
`FRC-SCOPE-UNDECLARED`. The order selects the diagnostic only; it never grants
conversion authority.

A parent dispatch **must** state its scope. A child dispatch **must carry its
own `run_scope:` declaration**, and it must match the parent's. Two independent
rules apply, in this order:

1. **Structural (primary).** Any child scope below its parent in the diagnostic
   order is `FRC-SCOPE-DOWNGRADE`; any child scope above its parent is
   `FRC-SCOPE-ESCALATION`, regardless of how politely the rest of the brief is
   worded. A brief with no declaration at all is
   `FRC-SCOPE-UNDECLARED`: a dispatch whose scope must be guessed is refused.
2. **Textual (secondary net).** A brief that declares `full_lifecycle` and then
   contradicts itself — `lightweight`, `response-only`, `no-artifacts`,
   `no-state`, "do not bootstrap", "return findings in your response only" — is
   also refused. This net can only **add** a refusal; it can never grant one, so
   the floor never depends on a phrase list.

This is the exact instruction at audit `:112`. Under this contract that dispatch
is not a judgement call — it is refused with `FRC-SCOPE-DOWNGRADE`.

> **Reflector-lightweight is not a run scope.** `agents/reflector-probe.md`
> defines a *mode* of one agent, chosen by the Planner within a lifecycle run,
> and it still writes its artefacts. "Lightweight" as a mode is legitimate;
> "lightweight" as a licence to skip the lifecycle is what this section forbids.

---

## 2. Authorization to write academic prose

**No project, no prose.** Before any academic prose is written, all of:

1. a **project root** exists and is a native project (`reviews/phase_state.json`
   present, `milestone_framework.mode == "native"`);
2. `reviews/assignment_contract.json` is present and **resolved**;
3. the active target milestone is derived from state — the first non-`accepted`
   of M1…M4 — never chosen by the agent;
4. `scripts/assignment_process_gate.py` emits an immutable READY receipt for that target and exact Generator output paths; after any committed control transition the receipt must bind and replay that exact transition and active target;
5. Planner `scripts/assignment_dispatch_preflight.py` exits 0 and atomically reserves that receipt for those paths and modes; Generator stages only beneath its receipt-scoped staging root, and `scripts/assignment_writer_commit.py` journals and publishes the exact set, emits a publication-result sidecar binding paths, modes, and hashes, then consumes the receipt.

If (1) or (2) is missing the run **fails closed** and the only permitted output
is an actionable bootstrap instruction (§2.1). Specifically:

- Do **not** write academic prose anywhere — including outside the project,
  including a "draft for the user to look at", including to a scratch path.
- Do **not** substitute a task checklist, TODO list, or plan for milestone state.
  A checklist is not a milestone. Neither is a file that happens to exist.
- Do **not** treat the absence of a project as licence to proceed informally.
  Absence of a scaffold is the **strongest** blocker, not the weakest.

### 2.1 The required response when unbootstrapped

State plainly that a full run needs a project, and give the actual command:

```bash
python scripts/native_project_bootstrap.py --project-root <path> \
    --project-name <name> --title "<title>" --intended-reader "<readers>"
```

This creates a `1.1.0` native milestone framework with explicit
`handoff_policy: derived`. Use `--handoff-policy audited` only when the new
project explicitly requires mandatory F9 compatibility behavior. Existing
`1.0.0` projects remain implicit audited and are never rewritten by bootstrap
or validation.

then resolve `reviews/assignment_contract.json` from the controlling source
(`references/ASSIGNMENT_MILESTONE_PROCESS.md`). Ask for the project root if it
is genuinely ambiguous. **Asking one question is always cheaper than an
unauthorized deliverable.**

### 2.2 Gather, then circulate; M5 is the one-way door

First-start of M1-M4 is an earning order. M2 cannot *start* until M1 has a
current accepted hash; M3 until M1 and M2; M4 until M1-M3. "Draft the whole
paper" does not collapse that gather. **File presence never implies
acceptance or materials-in-play**: a `project_memo.md` on disk is not an
accepted M1.

After materials are in play, any of M1-M4 may be named for restage in any
order. Materials-in-play is Joseph's bound `materials_in_play` declaration
(`authority: user`) or four current accepted hashes, or the ledger proof that
each of M1-M4 has been accepted at least once. It is never inferred from
files on disk.

M5 / FINAL still requires four *current* accepted hashes. Revising M3 after
M4 was accepted does not open FINAL until the four current hashes are
accepted together. An accepted M5 is the one-way door: M1-M4 may not be
named past it.

Acceptance lives in `milestone_framework.milestones.M<n>.approval` and
nowhere else. Gather auto-walk still derives the first non-accepted
milestone when Joseph does not name one. After materials are in play, name
the target with `--target-milestone`.

### 2.3 Laboratory proposal authorization

`lab_iteration` does not use the lifecycle prose authorization above. It
requires an existing exact governed `research/60_Workbench/<work-id>` project,
a resolved assignment contract, and `--output-root` matching either that
work-id's governed staging run or its exact private shipment lane. Successful
authorization returns `result: PROPOSAL_ONLY` with
`lifecycle_authority: false`, `f9_authority: false`, and
`terminal_authority: false`; it does not return lifecycle `OK`.

The scope writes no authoritative research, lifecycle, approval, F9,
promotion, final-deliverable, release, or dissemination state. Direct write
hooks permit only destination-classified staging/private-shipment paths.
`DEST-MISROUTED`, `DEST-PROTECTED`, and `DEST-UNGOVERNED` remain independent
destination blockers.

---

## 3. Who may write what

Restated **by reference**, not re-legislated — the agent files remain
authoritative: `agents/generator.md` (sole writer of academic deliverables within the plugin; stages via `assignment_writer_commit.py`; Writer outside applies),
`agents/planner.md` (coordinates; writes lifecycle state; never manuscript),
`agents/evaluator.md` and the Reflector files (read-only for manuscript).

What this contract adds is the mechanical floor that
`references/AGENT_ORCHESTRATION.md` admits is otherwise missing: manuscript
movement in a `full_lifecycle` run must be **attributable** to a Generator round
— a `manuscript/revision_log.md` entry and a preflight receipt for the round.
Manuscript bytes that no Generator round accounts for are `FRC-AUTHORSHIP`.

---

## 4. Terminal claims

**Terminal vocabulary** — "Ph4", "G.4", "terminal PASS", "ladder complete",
"converged", "shipped", "complete" applied to the lifecycle — is **claim-bearing**.
It may be emitted only when `full_run_contract_check.py terminal` returns 0
against the authoritative project.

That gate requires **all fifteen, unconditionally**:

> **`not_applicable` cannot reach terminal.** A milestone may be authorizedly
> waived (`applicability: not_applicable` with a valid `authorized_override`),
> and that waiver is legal and meaningful for **milestone-local and `adhoc_review`
> validation** — `milestone_framework_validate` validates such a record at its own
> target and returns `NOT_APPLICABLE`.
>
> It can **never** satisfy a `full_lifecycle` terminal claim. A `full_lifecycle`
> run is the user asking for the whole ladder, so every milestone is required
> *because they asked for it*; applicability describes one milestone's own
> validation, and does not get to redefine the request. §4 is unsatisfiable
> without M5 in any case — requirement 15 needs the FINAL/M5 packet and terminal
> state, so a terminal claim over a waived M5 asserts that the deliverable
> shipped without the deliverable. Any `not_applicable` M1–M5 record is refused
> directly with `FRC-NA-MILESTONE-IN-FULL-LIFECYCLE`.
>
> The earlier wording here was "as applicable to the project's own declared
> applicability", which read as a licence for exactly the waiver this paragraph
> forbids — and a waiver that turns "ladder complete" from false to true is not
> applicability, it is the audit failure of 2026-07-17 wearing the vocabulary of
> a legitimate feature.

| # | Requirement |
|---|---|
| 1 | resolved assignment contract |
| 2 | M1–M4 `accepted` with approval authority + evidence |
| 3 | exact-byte deliverable bindings (recorded sha256 == file on disk) |
| 4 | current-byte Generator and independent Evaluator draft-governance envelopes plus a separate qualified C6 scholarly evaluation for every M1-M4 and FINAL artifact; the C6 evidence reuses the consumed receipt/dispatch chain, binds the complete claim/criteria/profile/obligation read set, and has no unresolved `BLOCKER` or `MAJOR` |
| 5 | handoff-policy-correct predecessor state: effective `audited` requires exact ready/consumed F9 packets and the consumed predecessor chain; effective `derived` requires `not_applicable` by default and validates any optional exact F9 packet as non-gating, non-consumed evidence |
| 6 | F7 evidence packets and recorded events |
| 7 | `manuscript/revision_log.md` |
| 8 | deterministic-check evidence and Check 8 accessibility evidence |
| 9 | convergence journal/log and a signed `TerminalSignoffRow` |
| 10 | a completed deep iterate pass (`pre_mcr_deep_pass_completed`) |
| 11 | passing MCR |
| 12 | valid `reviews/G4_signoff.md` |
| 13 | Reflector-full close-out |
| 14 | F8 final-round report |
| 15 | accepted FINAL/M5 publication transaction: consumed immutable FINAL receipt + result, exact final/export bindings, complete structured terminal-evidence bindings, terminal state (`terminal_phase_reached`), and the policy-correct terminal handoff representation (mandatory exact F9 only under effective `audited`; optional, non-gating exact F9 or `not_applicable` under effective `derived`) |

An `adhoc_review` run **can never** satisfy this and must never imply it. Its
response is not evidence: it cannot stand in for F7, F8, or F9, and it cannot
be converted into one later by writing it into a file afterwards.

A `lab_iteration` also can never satisfy this. Its proposals and optional
analysis remain private scratch evidence and cannot be converted into
acceptance, promotion, terminal state, shipment, or dissemination. A terminal
gate proves lifecycle closure only; actual dissemination remains an external,
separately authorized action.

### 4.1 The two-file state is not a completed run

The observed artefacts — a manuscript and a review record, both outside any
project — satisfy **zero** of the fifteen. `full_run_contract_check.py terminal`
returns non-zero for that state, which is the mechanical form of the sentence
this contract exists to make unsayable.

---

## 5. Error codes

| Code | Meaning |
|---|---|
| `FRC-NO-PROJECT` | prose-producing intent with no native project root |
| `FRC-CONTRACT-MISSING` | no resolved `reviews/assignment_contract.json` |
| `FRC-SCOPE-UNDECLARED` | dispatch carries no run scope |
| `FRC-SCOPE-DOWNGRADE` | child declares a lower scope than its parent, or contradicts a `full_lifecycle` declaration with lightweight/response-only/no-artifacts/no-state instructions |
| `FRC-LAB-PROJECT-REQUIRED` | no exact governed Workbench project is resolved for `lab_iteration` |
| `FRC-LAB-CONTRACT-REQUIRED` | the laboratory project's assignment contract or its live bindings are unresolved |
| `FRC-LAB-DESTINATION-REQUIRED` | no laboratory proposal output root was supplied |
| `FRC-LAB-DESTINATION-MISMATCH` | output root does not match the project's governed staging work-id or exact private shipment lane |
| `FRC-LAB-LIFECYCLE-FORBIDDEN` | laboratory brief or write attempts lifecycle/authoritative-state mutation |
| `FRC-LAB-F9-FORBIDDEN` | laboratory brief requests F9 authority |
| `FRC-LAB-TERMINAL-FORBIDDEN` | laboratory brief or response claims terminal, shipment, or lifecycle completion |
| `FRC-SCOPE-ESCALATION` | child declares a higher scope than its parent; a child may not confer on itself authority its parent does not hold |
| `FRC-NO-ACTIVE-MILESTONE` | `authorize` on a project whose applicable milestones are all `accepted`: no target exists to author against. Validate a finished run with `terminal`; to continue, reopen or derive a milestone first |
| `FRC-PROSE-FORBIDDEN` | `authorize --run-scope adhoc_review`: prose is forbidden, so prose authorization is REFUSED. The ad hoc review itself is legal — validate its dispatch with `scope`, and never read an authorization exit code out of it |
| `FRC-TERMINAL-ROUND-UNBOUND` | a terminal claim whose `phase_state.terminal_round_id` is absent, null or malformed. No authoritative terminal round means no F8 can be selected — and selecting one anyway (newest, last, only) is the heuristic the binding abolishes. Fails closed BEFORE any selection is attempted |
| `FRC-ARTEFACT-ROUND-MISMATCH` | the F8 at the bound canonical path claims a different `round_id` than `terminal_round_id`: the filename agrees with the binding and the document does not |
| `FRC-NA-MILESTONE-IN-FULL-LIFECYCLE` | a terminal claim over an authorizedly `not_applicable` M1–M5. The waiver is legal milestone-locally and for `adhoc_review`; it cannot produce "ladder complete", "terminal PASS", or shipment |
| `FRC-MILESTONE-ORDER` | target milestone runs ahead of an unaccepted predecessor |
| `FRC-PRESENCE-NOT-ACCEPTANCE` | acceptance inferred from a file's existence |
| `FRC-AUTHORSHIP` | manuscript movement not attributable to a Generator round |
| `FRC-SCHOLARLY-EVALUATION-MISSING` | an accepted milestone lacks the required C6 scholarly-evaluation binding |
| `FRC-SCHOLARLY-EVALUATION-STALE` | a present C6 binding, authority chain, artifact, obligation, or transitive dependency is stale or unqualified |
| `FRC-TERMINAL-UNPROVEN` | terminal claim without the §4 evidence |

---

## 6. Routing

| Surface | Points here for |
|---|---|
| `AGENTS.md` | whole-lifecycle intent trigger; unbootstrapped fail-closed |
| `references/AGENTS.md` | package invocation on prose-producing intent |
| `skills/run-draft/SKILL.md`, `skills/run-phase-1/SKILL.md` | run scope + §2 authorization |
| `skills/run-finalize/SKILL.md`, `skills/run-phase-4/SKILL.md` | §4 terminal gate |
| `agents/planner.md` | scope declaration + child-dispatch refusal |
| `agents/evaluator.md`, `agents/reflector-*.md` | may not accept a scope-downgrading dispatch |

Grounding: `references/GROUNDING_PROTOCOL.md` remains absolute and is unchanged
by this file.
