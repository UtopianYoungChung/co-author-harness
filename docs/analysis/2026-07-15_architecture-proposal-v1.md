# Architecture Proposal — co-author-harness v1.0

**Date:** 2026-07-15
**Status:** proposal. No code moved. Supersedes nothing until approved.
**Companion:** `2026-07-15_harness-audit-accuracy-efficiency-staleness.md` (the evidence this rests on)
**Decisions taken (2026-07-15 session):** milestones govern · one routed `/paper` entry · lenses collapse to `/review --lens=X`

---

## 1. Problem statement

The package grew by accretion across 29 minors without a structural reconciliation. Every increment was locally defensible; the sum is not. Three symptoms, one cause:

- **42 skills, 22 commands, 6 agents, 61 reference files (13,380 lines).** Every peer plugin on this machine ships 1 or 0 commands. `unified-superkit` runs a 5-stage governed loop with **10 agents behind 1 skill**. co-author-harness inverts this — **6 agents behind 42 skills** — and puts the knowledge in a reference tree **2.3× larger than the entire executable surface**.
- **Two lifecycle vocabularies that the docs call orthogonal and the code treats as dependent.** Milestones gate phases at 3 of 4 boundaries.
- **10/10 green checks over a materially incoherent tree**, because every gate verifies *presence*, not *correspondence*.

**The cause is a missing distinction.** The package never separated three things that look alike and behave differently:

| | governs | shape | example |
|---|---|---|---|
| **Deliverable state** | what has been accepted and handed forward | monotone chain, human-approved | M1 memo accepted |
| **Readiness state** | how converged the *current* artifact is | loop with a fixpoint | §3 stable across 3 rounds |
| **Analysis** | what a lens says about prose right now | stateless, repeatable | Bacon sentence pass |

Milestones are #1. Phases were asked to be #2 **and** #1 at once. The lenses are #3 but were documented as pipeline stages. Every collision below follows from that conflation.

---

## 2. Finding: phases and milestones are not orthogonal — they are nearly collinear

The package states the mapping itself, in the same sentence that claims independence:

> `AGENT_ORCHESTRATION.md:659` — "Milestones and phases are orthogonal… **M1-M3 normally execute within Ph1; M4 spans Ph2-Ph3; M5 closes at Ph4.** Neither vocabulary supersedes the other."

Read that mapping as a function:

```
M1, M2, M3  →  Ph1
M4          →  Ph2, Ph3      ← the only place phase adds information
M5          →  Ph4
```

**Phase is derivable from milestone everywhere except inside M4.** Two axes are orthogonal when neither predicts the other. Here one nearly determines the other. They are not independent dimensions; they are one axis plus a *zoom level* that only engages for a single deliverable.

That is why they collide. The forensics found the collisions exactly where the collinearity is thickest:

| Collision | Evidence |
|---|---|
| Milestones gate phases **in code**, at 3 of 4 boundaries | `scripts/milestone_framework_validate.py:146` — `GATE_BOUNDARIES = ("ph1_to_ph2", "ph4_admission", "ph4_terminal_close")`; `"ph1_to_ph2": ("M1","M2","M3")`. **Every milestone gate is named after a phase transition.** |
| Explicit supersession, in the negative | `skills/run-phase-1/SKILL.md:55` — "**Ph1 maturity never authorizes a jump to M4.**" |
| An *optional* namespace gates the *mandatory* ladder | `phase_state_schema.md:50` — `milestone_framework` is "**Optional** additive"; `PHASE_PROTOCOL.md:567` — "Ph1→Ph2 **requires** M1, M2, and M3 to compute `READY`" |
| The guard's docstring denies what the guard does | `pre_phase_advance_check.py:260` — `"""…no milestone predicate lives here."""` in a function named `check_milestone_gate` that dispatches on `target_phase` |
| The milestone namespace embeds a phase enum | `milestone_framework.schema.json:162` — `"phase": {"enum": ["Ph2","Ph3","Ph4"]}` |
| M4's span contradicts across authorities | `PHASE_PROTOCOL.md:345` "Ph1 drafting through Ph3" vs `AGENT_ORCHESTRATION.md:659` + `MFHP:13` "Ph2-Ph3" |
| Seven milestone authorities; the *retired* one is the live one | `PHASE_PROTOCOL.md:29` retires `AGENT_ORCHESTRATION.md §10.1`, which remains the **only** artefact-path binding and is still cited as authority by `M1_M2_M3_PLANNING_PHASE_README.md:21,149` |
| M5 denied as a milestone in prose, treated as one in every executing surface | `ASSIGNMENT_MILESTONE_PROCESS.md:23` "not evidence that the assignment has a fifth milestone" vs `schema:178`, `validate:148`, `MFHP:112` |

**Verdict:** "orthogonal" is false. The only true version is the narrow one at `phase_state_schema.md:54` — *neither substitutes for the other*. That is a non-substitution rule, not independence, and v1.0 keeps it.

**One conflict is worth isolating** because it will bite a real project: the assignment track is required *unconditionally* (`planner.md:40` "Before any academic Generator dispatch… resolve and verify `reviews/assignment_contract.json`"; `run-draft:16` "fails closed when… absent") but hardwired to a single course-essay profile (`assignment_process_gate.py:17`). **Read literally, a CAiSE journal paper cannot invoke `/run-draft`.** It has no assignment contract, and the fail-closed clause carries no course-essay predicate.

---

## 3. Target architecture

### 3.1 One ladder: the deliverable chain

**Milestones govern. Phases stop being a lifecycle and become an attribute of one milestone.**

```
M1 memo → M2 references → M3 outline → M4 manuscript → M5 final
 └──────────── one-shot: open → submitted → accepted ────────────┘
                                  │
                                  └─ M4 only, because M4 is the only
                                     deliverable with an unbounded
                                     internal loop:
                                       readiness: drafting → iterating → converged
```

Why this and not phases-govern: **the code already votes this way.** Milestones are the binding predicate at 3 of 4 boundaries; phases are the thing being gated. Milestones also map to artifacts a human accepts, which is what an approval checkpoint needs. Making phases govern would mean rewriting the gates to fight their own semantics.

What each ladder rung is:

| Milestone | Artifact | State | Loop? |
|---|---|---|---|
| M1 | `research_notes/project_memo.md` | open · submitted · accepted | no |
| M2 | `references/REFERENCES.md` | open · submitted · accepted | no |
| M3 | `manuscript/outline.md` | open · submitted · accepted | no |
| **M4** | `manuscript/*.md` | open · submitted · accepted **× readiness per section** | **yes — the convergence loop** |
| M5 | submission-bound final | open · signed | no (close transaction) |

`readiness ∈ {drafting, iterating, converged}` exists **only** under M4 and **only** per section. Ph1/Ph2/Ph3/Ph4 as project-level lifecycle labels are retired. `M5` keeps its name — the prose hedge at `ASSIGNMENT_MILESTONE_PROCESS.md:23` is deleted rather than maintained, because nothing executing has ever honored it.

### 3.2 One state file

`reviews/project_state.json` replaces `phase_state.json` + the `milestone_framework` namespace. **One writer (Planner), one schema, one authority.**

```jsonc
{
  "schema_version": "1.0.0",          // enforced; see G0
  "project": {
    "id": "...", "type": "research-paper|course-essay|response-letter",
    "venue": "...", "p_stage": "P0|P1|P2",
    "contract": null                   // required iff type == course-essay
  },
  "milestones": {
    "M1": { "status": "accepted", "artifact": "...", "sha256": "...",
            "accepted_at": "...", "accepted_by": "user", "evidence": "..." },
    "M2": { ... }, "M3": { ... },
    "M4": {
      "status": "open",
      "sections": {
        "1. Introduction": {
          "readiness": "iterating",
          "convergence_metric": 3, "stable_rounds": 1,
          "last_review": "...", "scope_fingerprint": "...", "drift_lines": 12
        }
      }
    },
    "M5": { "status": "open", "signoffs": [] }
  }
}
```

Collapses the 18-field SectionStateObject + 903-line milestone schema + 31-trigger enum into one shape. The section object keeps only what a gate actually reads. **Rule: no field exists unless a gate consumes it.** That rule alone removes most of the current ledger.

### 3.3 Four gates, and nothing else

Every transition in the system is one of four pure functions of state. **A gate is a function, not a document.** Same input → same verdict, always.

```
        ┌─────────────────────────────────────────────────┐
        │  G0  ADMIT      may work start at all?          │
        │  G1  ACCEPT     may milestone M close?          │
        │  G2  CONVERGE   is section S done iterating?    │
        │  G3  SIGN       may M5 ship?                    │
        └─────────────────────────────────────────────────┘
```

**G0 — ADMIT** *(replaces: classification checks, contract fail-closed, schema checks)*

| Predicate | Blocks on |
|---|---|
| `project_state.json` parses; `schema_version == "1.0.0"` | `G0-SCHEMA` |
| `project.type` set; `p_stage` ∈ {P0,P1,P2}; `venue` set | `G0-UNCLASSIFIED` |
| **iff** `type == course-essay`: `contract` resolves + hash-verifies | `G0-CONTRACT` |

> Fixes the unconditional fail-closed bug: the contract predicate is **conditioned on project type**, so a journal paper admits without one. This is the one-line fix for the CAiSE case in §2.

**G1 — ACCEPT `M`** *(replaces: milestone_framework_validate, F9 packet, approval/handoff/dependency_state machines)*

| Predicate | Blocks on |
|---|---|
| all `M' < M` are `accepted` | `G1-SEQUENCE` |
| `M`'s artifact exists and hash matches recorded | `G1-ARTIFACT` |
| `M`'s exit criteria met (per type) | `G1-CRITERIA` |
| **explicit user approval this invocation** | `G1-APPROVAL` |
| no upstream `M'` reopened or stale | `G1-STALE` |

> Collapses four parallel status machines (`status` 10 values / `approval` 5 / `handoff` 5 / `dependency_state` 3 — `MFHP:50-52`) into one `status` + a sequence predicate. The four machines encoded the same fact four ways.
> **Retained invariant:** "No file, elapsed time, user silence, or phase advancement counts as milestone acceptance" (`ASSIGNMENT_MILESTONE_PROCESS.md:77`). This is the single most important rule in the package and G1 is its only home.

**G2 — CONVERGE `S`** *(M4 only; replaces: TerminalSignoffRow, check_profile, MCR admission, [Ph3-STALE])*

| Predicate | Blocks on |
|---|---|
| `stable_rounds >= 3` with `findings_delta == 0` and unchanged `convergence_metric` | `G2-UNSTABLE` |
| no open BLOCKER finding | `G2-BLOCKER` |
| a `deep`-profile review ran since last substantive edit | `G2-NO-DEEP` |
| `scope_fingerprint` current (no unreviewed drift) | `G2-DRIFT` |

> G2 is the *only* loop in the system, and it is scoped to one deliverable. The existing 3-round stability rule (`PHASE3_PHASE4_COMMON_ENVELOPE.md:48`) survives intact — it was always the right test, just wired to the wrong ladder. `[Ph3-STALE]` becomes `G2-DRIFT`.

**G3 — SIGN M5** *(replaces: G.4 sign-off, ph4_ship_signoff, terminal close preflight)*

| Predicate | Blocks on |
|---|---|
| M4 `accepted`; **all** sections `converged` or explicitly ceiling-locked | `G3-SECTIONS` |
| external verifiers ran and returned | `G3-VERIFY` |
| grounding audit clean | `G3-GROUNDING` |
| signoff carries exactly one anchored `status: SIGNED` | `G3-SIGNOFF` |
| explicit user approval | `G3-APPROVAL` |

**Invariant across all four:** a gate reads state and returns `PASS | BLOCK(code) | NOT_APPLICABLE`. It never writes. Only the Planner writes, only after a gate returns PASS **and** the user approves. This is the AORE point that the current design lost: the gates are the *protocol* between agents, and protocol must be separable from the agents that obey it. Today it is smeared across `pre_phase_advance_check.py`, `milestone_framework_validate.py`, `assignment_process_gate.py`, and prose in six reference files.

### 3.4 Three commands

| Command | Does | Replaces |
|---|---|---|
| **`/paper`** | Reads state → runs the next gate → dispatches the one action it authorizes → stops for approval | `run-phase-1/2/3/3-stability/4`, `run-draft`, `run-iterate`, `run-finalize`, `classify-manuscript`, `run-generator-session`, `plugin-commands` (11) |
| **`/review [--lens=X] [--deep]`** | One analysis pass. Lens optional; default = the wired Evaluator envelope | 14 scholar-lens skills + `quick-deterministic` + `check-*` (16) |
| **`/reflect`** | Learning loop; lessons + grounding audit | `run-reflection`, `grounding-audit`, reflector router (3) |

`/paper` sub-verbs, all optional: `/paper status` (read-only — what gate am I at, what blocks), `/paper next` (dry-run — what would happen), `/paper apply` (session-sourced revision, today's `run-generator-session`).

**22 → 3.** The user types `/paper` repeatedly until the paper ships. The routing table *is* the gate cascade:

```
/paper
  ├─ G0 BLOCK  → classify / request contract → stop
  ├─ G0 PASS   → active = first non-accepted milestone
  │    ├─ M1|M2|M3 → draft it → G1 → stop for approval
  │    ├─ M4       → per section: readiness?
  │    │     ├─ drafting  → Generator draft   → readiness = iterating
  │    │     ├─ iterating → Evaluator + Generator → G2
  │    │     └─ converged → all sections done? → G1(M4) → stop for approval
  │    └─ M5       → G3 → stop for approval
  └─ every stop is a user checkpoint; no auto-advance past a gate
```

> This is not a new idea — it is the one the plugin already proved. `/run-iterate` collapsed Ph2 + Ph3 + stability into one surface with a `profile` argument. **The collapse pattern worked; it just was never applied to the other 19 commands or the 14 lenses.**

### 3.5 Lenses: 14 skills → 1 parameterized skill

Today: 14 skills, 1,435 lines, **0 wired into the Evaluator**. `PHASE_PROTOCOL.md:91,124` lists Bacon/Sexton/Baird/Suchman/Eubanks in "Skills invoked" tables. `agents/evaluator.md:275` names its actual delegation whitelist:

> "an `accessibility-overlay` run, a `graph-grounding-overlay` run (Step 0.2), or a `quick-deterministic` counter refresh"

Three. **The reference tree documents a pipeline that does not exist.**

The 14 share one shape — read a pattern source in `references/`, apply an N-point checklist, emit per-finding rewrites. The variable is *which reference file* and *which checklist*. Three of them are literally sub-moves of one scholar (Abbott → `analytic-move-audit` / `definition-derivation-check` / `dissolution-move-check`, where M-1 and M-2 are two of seven moves). And `EVAL_METHODOLOGY.md:32-34` reports **identical eval figures for SK-07/SK-08/SK-09** (`95.2% / 42.8% / Δ +0.52`), self-annotated "likely shared eval set" — there is no measured evidence those three lenses differ at all.

```
/review --lens={bacon|sexton|baird|suchman|eubanks|abbott|bluebook|turabian}
        [--move=M1..M7]     # Abbott sub-move filter
        [--deep]            # full envelope
```

One skill (~120 lines) + a lens registry mapping name → reference file + checklist. **~1,435 → ~120 lines, losing nothing** — the knowledge lives in `references/`, not in the skills. Then either wire the registry into the Evaluator so `PHASE_PROTOCOL`'s tables become true, or delete the tables. **Not both, and not neither, which is today's state.**

### 3.6 Agents: 6 → 4, honestly

Planner (sole writer, gate runner, dispatcher) · Evaluator (finds, never writes prose) · Generator (writes prose, never evaluates) · Reflector (learns, never gates). The split is sound and survives. Changes:

- Delete `agents/reflector.md` — the router. Its retirement condition is unsatisfiable by construction (audit M2), it contradicts itself (M1), and its consumers point into the hollow (B1). Update the callers to name `reflector-probe` / `reflector-closeout` directly.
- Split `agents/planner.md` — 101,922 B, **48% of all agent bytes**, 21× the median. Extract the gate logic to the four gate specs; what remains is dispatch.
- Trim frontmatter descriptions: 20% is version narration, 36% is `<example>` blocks. Dispatch never turns on whether the digest exception was retired at v0.7.4. **~1,015 tok/session, free.**

---

## 4. What this fixes, mapped to the audit

| Audit finding | Fixed by | How |
|---|---|---|
| B1 `/run-reflection` resolves to nothing | §3.4 | `/reflect` names `reflector-probe`/`reflector-closeout`; router deleted |
| B2 `classify-manuscript` emits unreadable record | §3.2 + G0 | Classification *is* `project_state.project`; one shape, one reader |
| B3/S1 141K-tok read floor | §3.3 | Gates are functions over a small ledger. An agent reads the gate spec (~1 page) + its own contract, not 10 reference files. Full-file-read floor stays for *prose review*, where it belongs |
| M1/M2 reflector router | §3.6 | Deleted |
| M3 dead `§Phase` anchors | §3.1 | The phases they point at no longer exist as a lifecycle |
| M4 alias inversion pinned by smoketest | §3.4 | No aliases. One command. `alias_parity_smoketest.py` deleted |
| M5 `schema_version` unenforced | G0 | First predicate of the first gate |
| M6 stale tier vocabulary in catalog | §3.4 | `plugin-commands` deleted — 3 commands don't need a catalog |
| m5/m6 command-shim drift | §3.4 | 22 shims → 3 |
| S2 `PHASE_PROTOCOL.md` 119,935 B | §3.1 | Most of it specifies a ladder that stops existing |
| S3 description bloat | §3.6 | Trim |
| S5 duplicate check parsers | §5 | Fewer surfaces to check |
| S6 352KB CHANGELOG shipped | §5 | Drop from `REQUIRED_FILES` |

**The version-plane fork resolves by deletion, not harmonization.** 16 distinct version strings in `agents/` (none of them 0.29.0) exist because four vocabularies drifted independently. One vocabulary can't fork. `version_planes.json` and its snapshot-freeze go away — they were scar tissue over the fork, and the audit showed they *ratify* drift rather than resolve it.

---

## 5. The gate-scope principle

The deepest lesson from the audit is not any single finding. It is:

> **Every check in the current tree verifies presence. None verifies correspondence.**

`version-planes-check` confirms stale strings are *still there*. `retirement-sweep-check` confirms a marker is *present*, not that the sentence is true. `alias_parity_smoketest` asserts a description *starts with* "Alias for /X" — and thereby defends a claim four files contradict. `path-hygiene-check` resolves links **in README only**.

v1.0's check suite must invert this. Every check answers *does X match Y?*, never *does X exist?*:

| Check | Asserts |
|---|---|
| `gate-parity` | every gate code in prose exists in code, and vice versa |
| `state-schema` | every field in `project_state.json` is read by ≥1 gate — **unread field = BLOCKER** |
| `anchor-resolve` | every `§`-reference resolves to a real heading (would have caught B1) |
| `link-resolve` | every relative link resolves — **all files, not just README** (would have caught m1) |
| `lens-registry` | every lens in `/review --lens` has a reference file and a checklist |
| `contract-parity` | every frontmatter description matches its body's actual behavior |

**Six checks that verify correspondence, replacing ten that verify presence.** No snapshot mode. No marker loophole. A check that can be satisfied by adding a word to a comment is not a check.

---

## 6. Migration

Sequenced so each step is independently shippable and reversible. **Steps 1–3 are strictly repairs to 0.29.0 and carry no v1.0 commitment** — worth doing even if v1.0 is deferred.

| # | Step | Ships as | Risk |
|---|---|---|---|
| 1 | Fix B1 — `/run-reflection` dispatches the split agents by name | 0.29.1 | none |
| 2 | Fix the unconditional contract gate (§2) — condition on `project.type` | 0.29.1 | none — unblocks non-essay projects |
| 3 | Fix M3 dead anchors; delete the reflector router (M1/M2) | 0.29.2 | low |
| 4 | **Write the four gate specs.** Pure functions, no prose. The contract v1.0 is built against | 0.30.0-pre | design |
| 5 | Collapse 14 lenses → `/review --lens=X`; wire the registry into the Evaluator | 0.30.0 | medium — behavior change |
| 6 | `project_state.json` + migrator from `phase_state.json`. Both readable one minor | 0.31.0 | **highest — real project state** |
| 7 | `/paper` router; 22 commands → 3. Old commands warn-and-route one minor, then delete | 0.32.0 | medium |
| 8 | Retire the phase ladder as lifecycle; readiness becomes an M4 attribute | 0.33.0 | high — the point of the exercise |
| 9 | Rebuild the check suite on §5's correspondence principle; delete `version_planes.json` | **1.0.0** | low by then |

**Sequencing rationale.** Gates (4) precede everything because they are the contract. State (6) precedes routing (7) because the router reads state. Ladder retirement (8) is last because it is irreversible and everything else de-risks it. **Step 6 is where a live manuscript can be damaged** — it needs a dry-run mode, a backup, and verification against a real project before it runs on QE2026.

**One dependency worth naming:** step 6 touches `phase_state.json` in live projects. The known mount skew on uncommitted files means the migrator must be verified host-side, not through the sandbox.

---

## 7. Honest counter-arguments

Presented because a proposal that only argues its own side is advocacy, not design.

**"Milestones govern" is not obviously right.** Phases carry the convergence loop, which is where the intellectual work happens; milestones are bureaucratic checkpoints. A reasonable architect would say: govern by the thing that does the work. The counter — and why the recommendation stands — is that the loop is *scoped to one deliverable*. A lifecycle whose middle rung is 90% of the project isn't a lifecycle. But if M1–M3 are ever dropped for research papers (they're assignment-derived), the M-chain degenerates to `M4 → M5` and the phase ladder is doing the real work again. **This proposal is right for course essays and for research papers that keep the memo/references/outline discipline. It is wrong for a project that starts at "draft the manuscript."** Guard: keep `applicability: not_applicable` per milestone (already in `MFHP`), so the chain can legitimately collapse to M4→M5 without lying.

**Three commands may be too few.** `/paper` becomes a large router, and routers accrete — which is exactly how the current mess started. The mitigation is that the gates are the router's whole logic and they're specified separately; if `/paper` grows prose of its own, that's the smell to act on.

**The lens collapse loses discoverability.** 14 skill descriptions in the host's skill list are 14 chances for the model to match a user's phrasing. One `/review` is one chance. Mitigation: the lens registry lives in the description (`--lens=bacon|sexton|…`) — but this is a real cost, not a free win.

**Step 8 is irreversible and the ladder has 29 minors of accumulated judgment in it.** Some of that judgment is load-bearing and not written down anywhere but the ladder's structure. The audit found the *stale* parts; it did not prove the rest is inert. Before step 8, the convergence rules, the SAFEGUARD couplings, and the ceiling-lock semantics each need an explicit keep/drop decision — not a sweep.

**The trade-off this whole design makes:** agent autonomy for system predictability. The current package lets agents interpret a large prose substrate; v1.0 gives them small contracts and hard gates. That buys reproducibility and costs adaptability — a gate can only block what someone anticipated. The bet is that for a system whose failure mode is *silent incoherence*, predictability is worth more. That bet is not self-evidently correct.

---

## 8. What v1.0 looks like, in one screen

```
COMMANDS   /paper [status|next|apply]   /review [--lens=X] [--deep]   /reflect
AGENTS     planner · evaluator · generator · reflector-{probe,closeout}
STATE      reviews/project_state.json          ← one file, one writer
GATES      G0 ADMIT · G1 ACCEPT · G2 CONVERGE · G3 SIGN   ← pure functions
LADDER     M1 → M2 → M3 → M4 → M5              ← one chain
           M4.sections[*].readiness: drafting → iterating → converged
CHECKS     6 correspondence checks             ← no presence checks, no snapshots
```

| | 0.29.0 | 1.0.0 |
|---|---|---|
| Commands | 22 | 3 |
| Skills | 42 | ~12 |
| Lifecycle vocabularies | 2 (+1 assignment track) | 1 |
| State authorities | `phase_state.json` + 903-line milestone schema | 1 file |
| Milestone authorities | 7, mutually inconsistent | 1 |
| Gate logic locations | 4 scripts + prose in 6 reference files | 4 specs |
| Version planes | 5 forked, 16 strings in `agents/` | 1 (the manifest) |
| Checks | 10, presence-verifying | 6, correspondence-verifying |

---

## 9. Grounding note

Every file:line citation was verified against the tree at HEAD `2e34218`. §2's collinearity argument is a reading of `AGENT_ORCHESTRATION.md:659` and `PHASE_PROTOCOL.md:345` as quoted — the inference is mine, the mapping is theirs. Peer figures are measured from `/sessions/kind-vibrant-pascal/mnt/.remote-plugins/`. Line counts are `wc -l`. No claim rests on `CHANGELOG.md`. §7 is argument, not evidence, and is labeled as such.
