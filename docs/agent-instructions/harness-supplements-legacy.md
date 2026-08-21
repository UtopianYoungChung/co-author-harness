# Supplements, domain rules, and legacy project index

**When to read:** Project-specific supplements, i* / SD-SR modeling, or Year 2026 workspace project locations.

---

## Project-specific supplements

Some projects carry **binding supplements** — files that add rules within that project's scope but do not override the package. When entering a project, check for these markers:

| Marker | Meaning |
|--------|---------|
| `research_notes/directives.md` | Author decisions that reviewers must treat as fixed (already in bootstrap template) |
| `research_notes/lessons_learned.md` | Accumulated feedback from review rounds |
| Venue-specific lesson files (e.g., `lessons_caise_revision.md`) | Advisor or reviewer feedback specific to a venue submission |

**Known supplements (update as projects migrate to this tree):**

- **CAiSE_Rev01** (if/when migrated from Year 2026): `CAiSE_Rev01/research_notes/review/lessons_caise_revision.md` (Prof. Eric Yu's revision feedback); `CAiSE_Rev01/research_notes/writing_style_checklist.md` (CAiSE style baseline — now one component of the master package).
- **INF3006Y_AgencyDelegation:** `research_notes/directives.md` (eight directives, D-01 through D-08); `research_notes/lessons_learned.md` (five lessons, L-01 through L-05).
- **INF3001H_Research:** Vidal-dominant hybrid voice; em-dash functional test; three anti-patterns A/B/C caught at Step 0a; DO-NOT-DISTURB on loan-officer vignette and §5 closing question.

**Scope rule:** Supplements are binding *within their project only*. They do not bleed across projects (see [harness-governance.md](harness-governance.md), "Do not bleed directives").

---

## Domain-specific modeling rules

When a project involves a specific modeling notation, the project AGENTS.md should record the notation rules. Known domain rules from the Year 2026 workspace:

- **i\* modeling (CAiSE_Rev01):** When generating or reviewing i\* model content (in projects whose manuscripts are *about* i\*), consult the i\* Construct Vocabulary table in the project's memory. Key rule: agents are specific actors, roles are abstract expectations — do not confuse them.

(The harness itself no longer authors SD/SR models as part of its own pipeline; the v0.7.1 `sd_sr_required` opt-in was retired at v0.11.0 along with the Cold-Start defence and the `E-IMODEL-STRUCTURALLY-INCOMPLETE` / `E-Ph2-SD-UNGROUNDABLE` finding classes. Projects that author manuscripts *about* i*/GORE/AORE remain fully supported through the Reader-Experience and Argumentative-Rigor surfaces.)

These rules are recorded here as a cross-reference so the agent knows they exist even if the project has not yet migrated to the Research tree. Once a project migrates, the modeling rules should live in that project's own AGENTS.md.

---

## Legacy projects (Year 2026 workspace)

The following projects were still tracked under an **external Year 2026 portfolio workspace** (path varies by machine; not part of this harness repo). They are governed by that tree’s `AGENTS.md` where it still applies. They may migrate to the portfolio root (`Ph.D. Research/`) in the future; when they do, each should get the standard project structure (see [harness-discovery-lifecycle.md](harness-discovery-lifecycle.md) § Bootstrapping) and a project AGENTS.md.

| Project | Venue / Context | Status |
|---------|-----------------|--------|
| CAiSE_Rev01 | CAiSE 2026 paper | Active (revision) |
| RE 2026 | RE conference | Active |
| INF3001H_Research | PhD research course | Active (migrated to `Ph.D. Research/INF3001H_Research/`) |
| INF2205_MLOps | MLOps course | Course |
| INF2404_EXPnFAIR4ML | Explainability & Fairness in ML | Course |
| INF3130_HCI | HCI course | Course |
| AIWare | AIWare conference | Active |
| TA | Teaching assistant work | Ongoing |

The Year 2026 instruction file and this harness root `AGENTS.md` share the same package rules. The two files should be kept in sync on shared rules; project-specific rules live only in the relevant workspace. There is no package `CLAUDE.md`.
