# ADVISOR_MCP — External feedback via the plugin–MCP bridge

**Status.** Advisory **companion** to `PHASE_PROTOCOL.md` and `skills/advisor-escalation/SKILL.md`. It names the **Advisor MCP** surface, how the **co-author-harness plugin** exposes it, and the two **recommended lifecycle entry points** for fresh-eyes / strategic feedback before costly iteration or before MCR/Ph4 certification.

**Binding vs non-binding.** Phase gates, MCR, and G.4 remain defined in `PHASE_PROTOCOL.md`. This file does **not** add new mandatory ledger fields; it **names** optional, auditable consultation moments that improve **submission defensibility** when the user enables the advisor MCP.

---

## 1. What “Advisor MCP” means

| Term | Meaning |
|------|---------|
| **Advisor MCP** | The connected **Model Context Protocol** server that exposes advisor tools (see `skills/advisor-escalation/SKILL.md` — canonical call: `mcp__advisor__consult_advisor`). |
| **co-author-harness plugin** | The published package (this repo) whose manifest lives at `.claude-plugin/plugin.json`. It ships the **`/advisor-escalation`** skill so agents and users can invoke the bridge without ad hoc prompts. |
| **Connection** | The **host** (e.g. Claude Code, Cursor) must install both the **plugin** and the **advisor** MCP server; the skill describes the tool invocation and post-processing. The plugin **does not** embed the MCP server — it **calls out** to whatever advisor MCP the host has configured. |
| **External feedback** | Structured consultation output (strategic, positioning, or read-through questions) with **EXTERNAL** tag discipline and a filed artefact at `reviews/advisor_consultation_YYYY-MM-DD.md`. It is **not** a replacement for `EXTERNAL_VERIFIERS.md` Class 1–3 citation verification. |

---

## 2. Two recommended entry points (EP)

These are the **highest-leverage** moments discussed for submission defensibility: macro steering **before** deep Ph3 spend, and skeptical read **before** MCR/Ph4 binding.

| ID | When | Rationale |
|----|------|-----------|
| **EP-1** | After **Ph2** exit (user-approved `ph2`-equivalent / first full Evaluator pass complete), **before** committing to long **Ph3** iteration. | Catches contribution, structure, and positioning issues the internal stack may not question again once Ph3 optimizes line-by-line. |
| **EP-2** | After every in-scope section is **`Ph3_converged`**, **before** **MCR** clearance and **Ph4** admission. | Catches “normalization” blind spots before external-verifier and G.4 work locks the manuscript narrative. |

**Agent procedure.** When invoking the bridge at **EP-1** or **EP-2**, set `task_summary` to state the entry point explicitly (e.g. `Advisor entry point: EP-1 (post-Ph2, pre-Ph3)` or `EP-2 (post-Ph3_converged, pre-MCR/Ph4)`), then the single `specific_question` for that consultation. Follow `advisor-escalation` Steps 1–7 unchanged.

**User procedure.** Approve the cost gate in Step 1; file human notes in the same consultation file if a **human** reader also supplied feedback in the same window (label `[source: human]` in the project’s own appendix — not governed by the advisor EXTERNAL protocol).

---

## 3. Downstream on the ladder

- Consultation **actionable items** flow to the **Planner** revision plan and may appear as `[source: advisor]` (see the skill) until independently verified for manuscript text at submission depth.
- **EP-1** typically feeds the **next** `/run-phase-3` (or section-scoped Ph3) with clearer targets.
- **EP-2** typically feeds a **targeted** revision round **before** re-checking MCR preconditions; it does **not** replace `pre_mcr_deep_pass_completed` or other β gates in `PHASE_PROTOCOL.md` §3.4 when those apply.

---

## 4. Related files

- `skills/advisor-escalation/SKILL.md` — executable bridge (cost gate, `consult_advisor`, reclassification, artifact template, Category 7).
- `references/EXTERNAL_VERIFIERS.md` — citation / claim **verification** (Rule 7a), orthogonal to advisor strategic feedback.
- `references/GROUNDING_PROTOCOL.md` — binding rules; advisor output remains **Indirect** until verified for prose.

*Last updated: 2026-04-25 — EP-1/EP-2 entry points and plugin–MCP wiring.*
