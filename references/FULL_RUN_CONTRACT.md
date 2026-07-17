# FULL_RUN_CONTRACT.md — run scope, authorization to write prose, and terminal claims

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
| `adhoc_review` | A one-off read/critique the user explicitly asked for | **No** | **No** | **No** |

### 1.1 Scope is DECLARED, never sniffed

**The mechanism is the declaration, not the phrasing.** A request whose intent
is to produce or advance an academic deliverable is `full_lifecycle`, and
`full_lifecycle` is the **default** for any prose-producing request.
`adhoc_review` must be **explicitly** declared. Ambiguity resolves to
`full_lifecycle`: guessing `adhoc_review` silently skips the lifecycle, while
guessing `full_lifecycle` costs one bootstrap prompt the user can decline.

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

### 1.2 Scope is inherited, and a child may only narrow what does not matter

A parent dispatch **must** state its scope. A child dispatch **must carry its
own `run_scope:` declaration**, and it must match the parent's. Two independent
rules apply, in this order:

1. **Structural (primary).** `run_scope: adhoc_review` under a `full_lifecycle`
   parent is `FRC-SCOPE-DOWNGRADE` — regardless of how politely the rest of the
   brief is worded. A brief with no declaration at all is
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
4. `scripts/assignment_process_gate.py` emits a READY receipt for that target;
5. `scripts/assignment_dispatch_preflight.py` exits 0 against that receipt.

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

```
python scripts/native_project_bootstrap.py --project-root <path> \
    --project-name <name> --title "<title>" --intended-reader "<readers>"
```

then resolve `reviews/assignment_contract.json` from the controlling source
(`references/ASSIGNMENT_MILESTONE_PROCESS.md`). Ask for the project root if it
is genuinely ambiguous. **Asking one question is always cheaper than an
unauthorized deliverable.**

### 2.2 Milestone order is not negotiable

M4 (deliverable) requires M1, M2, M3 `accepted` with real approval evidence.
"Draft the whole paper" does not collapse them. **File presence never implies
acceptance**: a `project_memo.md` on disk is not an accepted M1. Acceptance
lives in `milestone_framework.milestones.M<n>.approval` and nowhere else.

---

## 3. Who may write what

Restated **by reference**, not re-legislated — the agent files remain
authoritative: `agents/generator.md` (sole writer of manuscript prose),
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

That gate requires, as applicable to the project's own declared applicability:

| # | Requirement |
|---|---|
| 1 | resolved assignment contract |
| 2 | M1–M4 `accepted` with approval authority + evidence |
| 3 | exact-byte deliverable bindings (recorded sha256 == file on disk) |
| 4 | consumed predecessor handoffs (F9 packets, `status: consumed`) |
| 5 | valid F9 packets with `packet_sha256` matching bytes |
| 6 | F7 evidence packets and recorded events |
| 7 | `manuscript/revision_log.md` |
| 8 | deterministic-check evidence and Check 8 accessibility evidence |
| 9 | convergence journal/log and a signed `TerminalSignoffRow` |
| 10 | a completed deep iterate pass (`pre_mcr_deep_pass_completed`) |
| 11 | passing MCR |
| 12 | valid `reviews/G4_signoff.md` |
| 13 | Reflector-full close-out |
| 14 | F8 final-round report |
| 15 | terminal state (`terminal_phase_reached`) and final F9 packet |

An `adhoc_review` run **can never** satisfy this and must never imply it. Its
response is not evidence: it cannot stand in for F7, F8, or F9, and it cannot
be converted into one later by writing it into a file afterwards.

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
| `FRC-SCOPE-DOWNGRADE` | child dispatch narrows a `full_lifecycle` parent to lightweight/response-only/no-artifacts/no-state |
| `FRC-MILESTONE-ORDER` | target milestone runs ahead of an unaccepted predecessor |
| `FRC-PRESENCE-NOT-ACCEPTANCE` | acceptance inferred from a file's existence |
| `FRC-AUTHORSHIP` | manuscript movement not attributable to a Generator round |
| `FRC-TERMINAL-UNPROVEN` | terminal claim without the §4 evidence |

---

## 6. Routing

| Surface | Points here for |
|---|---|
| `AGENTS.md` | whole-lifecycle intent trigger; unbootstrapped fail-closed |
| `references/CLAUDE.md` | package invocation on prose-producing intent |
| `skills/run-draft/SKILL.md`, `skills/run-phase-1/SKILL.md` | run scope + §2 authorization |
| `skills/run-finalize/SKILL.md`, `skills/run-phase-4/SKILL.md` | §4 terminal gate |
| `agents/planner.md` | scope declaration + child-dispatch refusal |
| `agents/evaluator.md`, `agents/reflector-*.md` | may not accept a scope-downgrading dispatch |

Grounding: `references/GROUNDING_PROTOCOL.md` remains absolute and is unchanged
by this file.
