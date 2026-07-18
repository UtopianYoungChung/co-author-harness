# QUICKSTART — One-Page Operational Primer



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

*For the reader who wants to invoke the package today. Full runbook: `OPERATING_MANUAL.md`.*

---

## The one rule

**Always begin a session by asking Claude to read `ROUTING_SPINE.md` and name the phase it is dispatching into. Never let a round close without a Reflector pass.** These two habits exercise nearly all of the machinery.

---

## Session opening (every time)

Open Claude inside the Research folder. If Claude does not volunteer it, prompt: *"Read `Research/CLAUDE.md`, then `.paper-package/CLAUDE.md`, then `ROUTING_SPINE.md`, then `Research/conductor.md`. Tell me which project we are on and what phase it is in."*

If no `conductor.md` exists at the Research root, say *"Seed the conductor per `PARALLEL_CONDUCTOR.md §8`"* and approve the draft.

---

## The seven phases and how to invoke each

| To do this | Say this | Lands on | First artifact you will see |
|---|---|---|---|
| Start a new project | *"Bootstrap a new project on X, targeting venue V, paper type T"* | **Think (M1)** | `research_notes/project_memo.md` |
| Build the bibliography | *"Build annotated references for the memo"* | **Plan (M2)** | `research_notes/annotated_references.md` |
| Structure the argument | *"Outline the paper"* | **Plan (M3)** | `manuscript/outline.md` |
| Draft prose | *"Co-author §N on topic T"* | **Build (M4)** | Edits to `manuscript/main.md` + revision-log entry |
| Get a review | *"Run a full review"* or *"Critique §N"* | **Review** | `scripts/run-evaluator-preflight.ps1` then `reviews/consolidated_findings_report.md` |
| Run only checks | *"Run the deterministic pass"* / *"Run the safeguard layer"* | **Test** | Per-check results under `reviews/` |
| Sign off for submission | *"Is it ready?"* then *"Do the G.4 sign-off"* | **Ship (M5)** | `reviews/G4_signoff.md` |
| Learn from the round | *"Retro this round"* | **Reflect** | `reviews/reflection_report.md` |

Ambiguous utterances: Claude should ask which phase. If it doesn't, push back — *"Name the phase before dispatching."*

---

## User checkpoints (do not skip them)

Every arrow in `AGENT_ORCHESTRATION.md §3`'s loop is a mandatory stop. You see either a plan, findings, proposed edits, a re-check, or a reflection, and you either **approve**, **modify**, **dispute**, or **reject**. Approvals are what let the round advance. Silence is not approval.

---

## Three failure modes and their corrective utterances

| Symptom | Corrective |
|---|---|
| Claude starts editing prose without showing a plan | *"Show me the revision plan first."* |
| A phase advances without certifying its exit gate | *"Run the exit gate for the current phase per `ROUTING_SPINE.md §3`."* |
| A directive from Project A is being applied to Project B | *"Check directive scope per `RESEARCH_ROOT_CLAUDE.md §6`."* |

---

## Submission-bound depth — what must be green

Before G.4 sign-off, every item below must read CLEAN or RESOLVED:

- `reviews/step_0a_deterministic.md` — mechanical patterns
- `reviews/safeguard_layer_results.md` — six integrity checks
- `reviews/drift_check.md` — MASTER / component reconciliation
- `reviews/reflexivity_check.md` — substitution-vs-augmentation audit
- External verification per `GROUNDING_PROTOCOL.md` Rule 7a (Zotero MCP or registered verifier)

If any is open, G.4 returns a BLOCKER and names the remediation.

---

## Power-user shortcuts

- `/quick-deterministic` — mechanical checks only, no judgment-based review
- `/check-contradictions` — SAFEGUARD Check 4 in isolation
- `/check-abstract-body` — abstract-vs-body promise audit
- `/suchman-register-audit` — C-1 register-consistency check

Skills are shortcuts, not substitutes. A BLOCKER from any skill should escalate to a full Evaluator round.

## Wiki-facing couplings (if you maintain a peer `LLM wiki/`)

Four skills link Research projects to a peer wiki — see `wiki/syntheses/synergy-program-m0-completion-2026-04-13.md` for the full picture.

- **SK-14** `promote-lessons-to-wiki` — Reflector may invoke it automatically; currently returns deferred (`WIKI_WRITE_TRANSACTION_UNAVAILABLE`) and must not write a Wiki synthesis page.
- **SK-15** `backfill-source-stubs-from-references` — on-demand. Burns a project's REFERENCES.md into `wiki/sources/` stubs.
- **SK-16** `retrofit-concept-grounding` — on-demand. Cites existing sources on wiki concept pages; flags red-links.
- **SK-17** `ingest-m5-to-wiki` — may be invoked at M5 close-out after G.4 sign-off but currently returns `status: deferred` / `WIKI_WRITE_TRANSACTION_UNAVAILABLE` without writing a Wiki source page; G.4 / Phase 4 completion does not depend on Wiki write availability.

At bootstrap, `PROJECT_BOOTSTRAP.md §3 Step 5` records wiki-linkage intent in the project CLAUDE.md. Set `wiki_linked: false` to opt out entirely.

Before each evaluator round in a wiki-linked project, run:

`scripts/run-evaluator-preflight.ps1`

This emits deterministic coupling artifacts (`coupling_readiness_*.json`, optional `sk20_noop_*.json`, and `coupling_health.*`) before Step 0a.

---

## Multi-project rhythm

One project per utterance. Name the project when you switch (*"Switching to RE2026…"*). The conductor records phase, round, and resume-note for each active project; Claude reads it on session entry and updates it at session close. Cross-project directive bleed is the most common avoidable error — if it happens once, it will happen again unless the conductor is kept current.

---

## When something feels wrong

Ask Claude to *"Run the contract audit per `AGENT_CONTRACTS.md §6`"*. It will report any invariant violations from the round (wrong agent writing wrong file, bypassed checkpoint, ungrounded claim, over-scope edits) and either correct them or file them as a Reflector-level lesson for the next round.

---

*Created 2026-04-13. Paired with `OPERATING_MANUAL.md` (comprehensive runbook). If something here contradicts the operating manual, the operating manual wins; if the manual contradicts a component file, the component file wins (per `CLAUDE.md §4` precedence).*
