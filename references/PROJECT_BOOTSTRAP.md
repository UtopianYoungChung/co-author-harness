# PROJECT BOOTSTRAP — New Project Setup Protocol

**Purpose.** This file defines the standard directory structure, seed files, and initialization procedure for every new research project under the Research root folder. It replaces the implicit "use the INF3006Y template" instruction in `AGENT_ORCHESTRATION.md §8a` with an explicit, executable specification.

**When to use.** The agent reads this file whenever:
- The user says "start a new project," "set up a folder for X," "bootstrap Y," or any equivalent.
- The Planner encounters a project path that does not yet exist.
- The Research-root CLAUDE.md §7 directs the agent here.

---

## 1. The Standard Project Directory

Every research project gets this structure. Files marked `[seed]` are created at bootstrap time with template content. Files marked `[runtime]` are created by agents during the lifecycle.

```
<project-name>/
│
├── CLAUDE.md                              [seed]   Project-specific configuration
├── round_program.md                       [seed]   User-authored round control file (see §2.10)
│
├── manuscript/
│   ├── main.md (or main.tex)              [seed]   Empty manuscript scaffold
│   ├── outline.md                         [seed]   Empty outline template
│   └── revision_log.md                    [seed]   Empty log with structured experiment format
│
├── reviews/
│   ├── phase_state.json                  [seed]   Single phase + milestone state authority
│   ├── .harness/
│   │   ├── milestones/                   [seed]   Empty; F9 packets appear only after approval
│   │   └── policies/
│   │       └── reader_accessibility.resolved.json [seed] Resolved policy binding
│   ├── classification.md                  [runtime] Planner creates at first classification
│   ├── revision_plan.md                   [runtime] Planner creates when planning
│   ├── round_checklist.md                 [seed]   Operator checklist for gate-first evaluator rounds
│   ├── step_0a_deterministic.md           [runtime] Evaluator creates at Step 0a
│   ├── step_findings/                     [seed]   Empty directory
│   ├── consolidated_findings_report.md    [runtime] Evaluator creates at Step 8
│   ├── safeguard_layer_results.md         [runtime] Evaluator creates at Step 8.5
│   ├── G4_signoff.md                      [runtime] Evaluator creates for submission-bound
│   ├── reflection_report.md               [runtime] Reflector creates after each round
│   └── DO_NOT_DISTURB.md                  [seed]   Empty with header (append-only)
│
├── research_notes/
│   ├── project_memo.md                    [seed]   M1 template
│   ├── annotated_references.md            [seed]   M2 template
│   ├── directives.md                      [seed]   Empty with header
│   └── lessons_learned.md                 [seed]   Empty with header
│
├── scripts/
│   └── run-evaluator-preflight.ps1        [seed]   Runs SK-20 gate + coupling health update before evaluator round
│
└── skills/                                [seed]   Empty directory for project-level skills
```

---

## 2. Seed File Templates

### 2.1 Project CLAUDE.md

```markdown
# CLAUDE.md — <PROJECT_NAME>

**Project:** <project-name>
**Created:** <date>
**Venue:** <venue or "TBD">
**Paper type:** <type or "TBD">
**P-stage:** <P0 | P1 | P2>
**Current milestone:** M1 (Project Memo)

---

## Package delegation

This project uses the Research and Academic Paper Writing Package at:
`.paper-package/` (relative to Research root)

All review, editing, and agent orchestration follows the package rules.
Read `.paper-package/CLAUDE.md` for invocation rules.
Read `.paper-package/AGENT_ORCHESTRATION.md` for the four-agent loop.
Read `.paper-package/REVIEW_ORCHESTRATION.md` for the review pipeline.

---

## Project-specific directives

<!-- Record venue-specific overrides, advisor instructions, or user decisions here.
     These override package defaults within this project (per precedence rule 4). -->

None yet.

---

## Venue constraints

<!-- If the venue has a template, word limit, or formatting requirement, record it here. -->

None yet.

---

*Last updated: <date>.*
```

### 2.2 manuscript/main.md

```markdown
# <PROJECT_TITLE>

**Milestone:** M4 (Paper Draft)
**Status:** Not started

<!-- File presence is not milestone completion or acceptance. Replace this
     scaffold only after the accepted M3 handoff is consumed. -->

## 1. Introduction

## 2. Background / Related Work

## 3. [Core Contribution Section — rename per argument]

## 4. Discussion

## 5. Conclusion

## References
```

### 2.3 manuscript/outline.md

```markdown
# Structured Outline — <PROJECT_NAME>

**Milestone:** M3 (Structured Outline)
**Status:** Not started

File presence is not milestone completion or acceptance.

---

## Abstract (2–3 sentence preview)

## 1. Introduction
- Phenomenon:
- Problem statement:
- Aim / contribution preview:

## 2. Background / Related Work
- Key tension:
- Track A sources:
- Track B sources:
- What is contested:

## 3. [Core Section]
- Central argument:
- Sub-arguments:
- Evidence plan:

## 4. Discussion
- Implications:
- Limitations (scope, not apology):
- Future directions:

## 5. Conclusion
- Restatement of contribution:
- Forward-pointing close:
```

### 2.4 manuscript/revision_log.md

Uses the **structured experiment log format** (inspired by autoresearch's hypothesis→change→result→verdict pattern). See `AGENT_CONTRACTS.md` §3 for the rationale.

```markdown
# Revision Log — <PROJECT_NAME>

This file is append-only. Each round of revision adds a new entry.
The Generator writes entries; no other agent modifies this file.

The structured format below ensures every change is treated as an experiment:
a hypothesis about why it will improve the manuscript, the change itself,
the self-check result, and a verdict (RETAIN / REVERT / PARTIAL).

---

<!-- Template for each round:

## Round <N> — <date>

**Round program focus:** <from round_program.md, or "none — full scope">
**Hypothesis:** <why we expect this set of changes to improve the manuscript;
                 ties to specific actions in revision_plan.md>
**Scope:** <which sections/paragraphs were modified>
**Changes:**
- [location] → [what changed] → [rule cited]
- ...
**Self-check result:** <Generator's deterministic check output — CLEAN or list of remaining hits>
**Verdict:** <RETAIN — improvement confirmed by Evaluator re-check |
              REVERT — regression detected (list which changes reverted) |
              PARTIAL — some retained, some reverted (itemize)>
**Carried forward:** <unresolved items deferred to next round, with reason>

-->
```

### 2.5 reviews/DO_NOT_DISTURB.md

```markdown
# DO NOT DISTURB — <PROJECT_NAME>

This file records rules, decisions, and constraints that must not be overridden
by any agent in any round. It is append-only. Only the Evaluator and the
Reflector may add entries. No agent may remove entries.

---

<!-- Template:

## DND-<N>: <short label>
- **Added by:** <Evaluator | Reflector>
- **Date:** <date>
- **Rule:** <what must not be changed>
- **Reason:** <why this was frozen>

-->
```

### 2.5a reviews/round_checklist.md

```markdown
# Round Checklist — <PROJECT_NAME>

1. Run `scripts/run-evaluator-preflight.ps1`.
   - Default env var: `AGENT_PLUGIN_ROOT` (fallback: `CLAUDE_PLUGIN_ROOT` or `CURSOR_PLUGIN_ROOT`).
   - If needed, pass `-PluginRoot <path-to-co-author-harness-plugin-root>`.
2. If gate fails, inspect `reviews/sk20_noop_YYYY-MM-DD.json` and fix failed checks.
3. Run Evaluator Step 0a deterministic checks.
4. Run full evaluator pass.
5. Confirm `reviews/coupling_health.md` has been refreshed at round close.
```

### 2.5b reviews/phase_state.json and F9 directory

`reviews/phase_state.json` is the **only writable authority** for both the phase ledger and the `milestone_framework` namespace. Generate its native seed with `scripts/native_project_bootstrap.py`; do not copy status claims out of the Markdown files. The seed records M1 as `in_progress`, M2–M5 as `not_started`, empty artifact and feedback arrays, pending approvals, and not-ready handoffs. It also records only the evidence-free `milestone_started` event for M1.

The native seed has a fresh-target contract: the requested project root must not exist, and its parent must already exist. The generator builds the entire milestone seed in a newly created sibling staging directory, resolves every output path against that staging root, and runs both canonical validators there. Only a fully valid seed is atomically renamed to the requested root. Failure removes staging and never merges with, overwrites, or repairs an existing project. Existing projects use the migration workflow instead.

`reviews/.harness/milestones/` starts empty. An F9 packet is created only after its source milestone has an accepted deliverable and real approval evidence. The mere presence of `project_memo.md`, `annotated_references.md`, `outline.md`, or `main.md` never changes milestone state.

### 2.6 research_notes/project_memo.md

```markdown
# Project Memo — <PROJECT_NAME>

**Milestone:** M1 (Project Memo)
**Status:** In progress

File presence starts work; it does not record review, approval, acceptance, or handoff readiness.

---

## 1. Focus & Framing
<!-- Define the exact phenomenon. Distance from buzzwords.
     Focus on the underlying problem. -->

## 2. Core Tension / What the Corpus Says
<!-- Identify the clash in the literature. Map disagreements. -->

## 3. Terms to Hold at Arm's Length
<!-- List concepts/jargon that smuggle hidden assumptions. -->

## 4. Research Questions (or Forward-Pointing Candidates)
<!-- P0/P1: candidate q-items (q-α, q-β, q-γ), NOT numbered RQs.
     P2: formal RQs with justification. -->

## 5. Snowball Strategy
<!-- Core literature → tracks for genealogy, debate, precedents. -->
```

### 2.7 research_notes/annotated_references.md

```markdown
# Annotated References — <PROJECT_NAME>

**Milestone:** M2 (Annotated References)
**Status:** Not started

File presence is not milestone completion or acceptance.

---

<!-- Template for each source:

## [Author(s) (Year)] — <Short title>

**Full citation:** <APA/venue format>
**Track:** <which snowball track — genealogy / debate / precedent / method>
**Summary:** <2–3 sentences: what the source argues>
**Contribution to tension:** <how this source informs the research questions>
**Key concepts borrowed:** <terms, frameworks, or constructs drawn from this source>
**Limitations / caveats:** <what the source does not cover or where it overreaches>

-->
```

### 2.8 research_notes/directives.md

```markdown
# Directives — <PROJECT_NAME>

This file records user overrides, advisor instructions, and venue-specific
constraints that modify how the package rules apply to this project.

Directives here override the package's cross-venue rules within this project
(per precedence rule 4 in Package CLAUDE.md §4).

> **On session start.** Before beginning work on this project, read the global style authority `B:\Agents\reference\turabian-author-date-quickref.md` (Turabian Author-Date; see `D-STYLE` in `B:\Agents\AGENTS.md`). In-conversation user instructions and venue/template requirements still take precedence over it.

---

# Manuscript register class (v0.10.1)
# Conditions Sub-check H (Register Appropriateness) of SAFEGUARD Check 8.
# Default: technical (peer-reviewed scholarly venue; H runs only on the
# five non-technical passage roles — signposts, framing, transitions,
# vignettes, anchors).
# Set: mixed (thesis chapter aimed partly at committee, partly at applied
# audience; H additionally runs on abstract / introduction / conclusion).
# Set: non-technical (public-interest write-up, policy memo, trade-press
# article; H runs manuscript-wide with technical paragraphs held to
# positive-marker construction at the sentence level).
# Field is orthogonal to P-stage: P-stage governs depth/scope of engagement;
# register_class governs target-audience register requirements.
# Silent absence inherits the default `technical` for back-compat safety.
register_class: technical

# D-STYLE profile (workspace research-writing architecture)
# This routing declaration narrows the global D-STYLE defaults for the project.
# Absent fields inherit D-STYLE. Use `tbd` only during orientation; replace it
# before claiming argument readiness.
d_style_profile:
  question_type: tbd
  citation_style: tbd
  source_role_policy: strict_role_classification
  evidence_display_policy: standard
  assistance_disclosure_policy: project_local
  harness_profile: standard_research_review

---

<!-- Template:

## D-<N>: <short label>
- **Source:** <user | advisor | venue guide>
- **Date:** <date>
- **Directive:** <what to do or not do>
- **Overrides:** <which package rule this modifies, if any>

-->
```

### 2.9 research_notes/lessons_learned.md

```markdown
# Lessons Learned — <PROJECT_NAME>

This file is maintained by the Reflector. It records patterns, errors,
and insights extracted from review rounds. Other agents read it;
only the Reflector appends to it.

---

<!-- Template:

## L-<N>: <short label> (<date>)
- **Round:** <which review round>
- **Pattern:** <what happened>
- **Lesson:** <what to do differently>
- **Applies to:** <this project only | package-wide>

-->
```

### 2.10 round_program.md

The round program is the user-authored control file for each round (see `AGENT_ORCHESTRATION.md` §8.2). It is inspired by autoresearch's `program.md` — a lightweight markdown file where the human declares the agent's focus for the next iteration.

```markdown
# Round Program — <PROJECT_NAME>

**Round:** <N>
**Date:** <date>
**Author:** <user name>

---

## Focus

<!-- What should this round accomplish? Be specific.
     Examples: "Fix the Introduction's opening hook (Sexton §1)"
               "Address all BLOCKER findings from Round 2"
               "Rewrite §3 to strengthen the theoretical framing" -->

## Scope constraints

<!-- What should agents NOT touch this round?
     Examples: "Do not edit §5 (Conclusion) — advisor is reviewing it"
               "Ignore MINOR findings — focus on BLOCKERs and MAJORs only" -->

## Success criteria

<!-- How will you know this round succeeded?
     Examples: "WFC drops below 10"
               "SIS reaches 4 on the Introduction-to-Methods arc"
               "Zero TODO markers remain in §3" -->

## Notes for agents

<!-- Any additional context the Planner should know.
     Examples: "The advisor said the theory section is too long"
               "I changed the venue from ICIS to ECIS — update formatting"
               "I manually edited §2.3 since last round — don't revert those changes" -->
```

**Lifecycle.** This file is overwritten by the user before each round. The Reflector archives the prior round's program content into the reflection report's round-context section. If the user does not create or update this file before a round, the Planner proceeds without it — the round program is optional but recommended.

### 2.11 scripts/run-evaluator-preflight.ps1

```powershell
param(
  [string]$Date = (Get-Date -Format "yyyy-MM-dd"),
  [string]$PluginRoot = $env:AGENT_PLUGIN_ROOT
)

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not $PluginRoot -or -not (Test-Path $PluginRoot)) {
  if ($env:CLAUDE_PLUGIN_ROOT -and (Test-Path $env:CLAUDE_PLUGIN_ROOT)) {
    $PluginRoot = $env:CLAUDE_PLUGIN_ROOT
  } elseif ($env:CURSOR_PLUGIN_ROOT -and (Test-Path $env:CURSOR_PLUGIN_ROOT)) {
    $PluginRoot = $env:CURSOR_PLUGIN_ROOT
  }
}
if (-not $PluginRoot -or -not (Test-Path $PluginRoot)) {
  $Fallback = Resolve-Path (Join-Path $PSScriptRoot "..\..\.paper-package") -ErrorAction SilentlyContinue
  if ($Fallback) { $PluginRoot = $Fallback }
}
if (-not $PluginRoot -or -not (Test-Path $PluginRoot)) {
  Write-Error "Plugin root not found. Set AGENT_PLUGIN_ROOT (or CLAUDE_PLUGIN_ROOT/CURSOR_PLUGIN_ROOT) or pass -PluginRoot."
  exit 2
}

$GateScript = Join-Path $PluginRoot "scripts/sk20_preflight_gate.py"
$HealthScript = Join-Path $PluginRoot "scripts/coupling_health_report.py"

python "$GateScript" --project-root "$ProjectRoot" --date "$Date" --strict-exit
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

python "$HealthScript" --project-root "$ProjectRoot"
```

Purpose: run this script before every evaluator round so Coupling E.2 readiness/no-op artifacts are always emitted and coupling health trends are refreshed without manual command composition.

---

## 3. Bootstrap Procedure

When the agent receives a bootstrap request, follow this exact sequence:

### Step 1: Gather inputs

Ask the user for:

| Input | Required | Default if not provided |
|---|---|---|
| Project name (folder/project ID) | Yes | ASCII slug matching `[A-Za-z0-9][A-Za-z0-9._-]*` |
| Working title | No | Same as project name; must be non-empty, single-line printable text |
| Venue | No | "TBD" |
| Paper type | No | "TBD" |
| P-stage | No | P0 |
| Intended reader(s) | Yes | — |
| Brief description / motivating tension | No | Empty (Planner will elicit during M1) |
| Advisor / collaborators | No | Empty |
| Wiki linkage (Coupling D) | No | Auto-detected — see Step 5 |

### Step 2: Create the directory skeleton

Do **not** pre-create the project root. Confirm that its parent exists, then run the deterministic native milestone seed once:

```powershell
python <package-root>/scripts/native_project_bootstrap.py `
  --project-root <project-path> `
  --project-name <project-name> `
  --title <working-title> `
  --intended-reader "<reader description>"
```

The command accepts only a project identifier matching `[A-Za-z0-9][A-Za-z0-9._-]*`, a non-empty single-line printable title, and a real UTC `--created-at` timestamp (when supplied). The identifier grammar is deliberately narrower than Markdown, YAML, and filesystem grammars: whitespace, CR/LF, colon, `#`, controls, and leading punctuation are rejected before staging, so interpolated project metadata cannot add directive keys or alter `register_class`. The full validated identifier is recorded as `project_id` and must equal the resolved policy binding's `project_identity`.

The command builds the four milestone working surfaces, project directives, empty F9 directory, resolved reader-accessibility policy, and `reviews/phase_state.json` in a fresh sibling staging directory, validates the staged result, and atomically publishes it. The policy binding therefore includes the exact seeded `research_notes/directives.md` hash. It rejects any existing target—including a target containing an F9 packet, resolved policy, symlink, or junction—and never emits `BOOTSTRAPPED` before both canonical validators pass. After successful publication, seed the remaining non-milestone support files from §2 without modifying these authoritative surfaces. Existing or legacy projects must not use this command; route them through migration.

Re-run the validators before classification as a host-side confirmation:

```powershell
python <package-root>/scripts/milestone_framework_validate.py --project-root <project-path>
python <package-root>/scripts/phase_state_validate.py --project-root <project-path>
```

Both commands must exit 0. A newly created Markdown file must not be added to `artifacts`, `feedback_records`, or `approval` until the corresponding evidence exists.

### Step 3: Write the project CLAUDE.md

Instantiate the template in §2.1 with the user's inputs. Record the delegation chain (Research root → Package → Project) explicitly.

### Step 4: Dispatch Planner for M1 classification

Once the skeleton exists, run the Planner in classification mode (see `AGENT_ORCHESTRATION.md §10 — Lifecycle Dispatch`) to produce `reviews/classification.md` with paper type, P-stage, venue, and depth locked in.

### Step 5: Register wiki linkage (Coupling D and E hooks)

**Purpose.** Codifies the project's forward-looking relationship with the peer `LLM wiki/` store and its `graphify-out/` knowledge-graph layer. This step does not move any content; it records whether the project is wiki-linked and, if so, how its eventual M5 artefact should be ingested as a wiki source and whether the graph-overlay pipeline should fire during review rounds. The ingestions themselves are **Coupling D** (M5, fires once) and **Coupling E.2** (Evaluator pre-flight, fires every review round) — neither fires at bootstrap — but the *intent* is registered here so later agents do not need to re-litigate it.

**Detection.**

1. Check whether an `LLM wiki/` folder is reachable peer to the Research root (look for `LLM wiki/CLAUDE.md` or `LLM wiki/wiki/sources/`).
2. If no wiki is reachable, record `wiki_linked: false` in the project CLAUDE.md frontmatter (or in a `Wiki linkage` section if the CLAUDE.md has no frontmatter) and skip the rest of this step.
3. If a wiki is reachable, set `wiki_linked: true` and proceed.

**What to record in project CLAUDE.md.** Add a `## Wiki linkage (Coupling D)` section to the project CLAUDE.md containing:

| Field | Value |
|---|---|
| `wiki_linked` | `true` / `false` |
| `wiki_path` | Absolute or Research-relative path to the `LLM wiki/` folder (only if `true`) |
| `projected_wiki_key` | Proposed source key for the M5 artefact, format `<first-author>-<year>-<keyword>` — see `LLM wiki/CLAUDE.md §Source Keys`. For early-stage projects without a settled author/year, use a provisional key with `-draft` suffix (e.g. `chung-2026-delegation-draft`) and finalize at M5. |
| `coupling_c_active` | `true` if the Reflector's Phase 3.5 should fire SK-14 at round close (default: same value as `wiki_linked`). User may set to `false` to suppress per-round promotion without severing the M5 ingestion hook. |
| `coupling_d_on_m5` | `true` if the final paper should be self-ingested into `LLM wiki/wiki/sources/` at M5 (default: same value as `wiki_linked`). |
| `coupling_e_on_review` | `true` if SK-20 `graph-grounding-overlay` should run in the Evaluator pre-flight when `graphify-out/` exists and is fresh (default: same value as `wiki_linked`). Can be set `false` to suppress graph-overlay findings per-project without severing other wiki couplings — useful if a project's citation format does not resolve cleanly to graphify's `source_file` paths. |
| `concept_targets` | Optional list of wiki concept pages that the paper will plausibly ground at M5, e.g. `[agency, delegation, governance]`. Helps the M5 ingestion agent choose wikilink targets. |
| `wiki_first_resources` | `true` (default when `wiki_linked: true`) / `false` | When `true`, Planner and Generator follow `EXTERNAL_VERIFIERS.md` §1.5: consult peer `LLM wiki/` (sources, concepts, syntheses, `GRAPH_REPORT.md`, optional `/llm-wiki-query`) **before** adding new Zotero PDFs or using external discovery tools (e.g. Consensus). Set `false` only to bypass for a project or round with a documented reason. |

**When Coupling D fires.** At M5 (submission-bound final paper) — *not* at bootstrap. The M5 drafting/revision loop should, as its closing action after G.4 sign-off, invoke **SK-17 `ingest-m5-to-wiki`** (`.paper-package/skills/ingest-m5-to-wiki.md`, formalized 2026-04-13). SK-17 creates `LLM wiki/wiki/sources/<projected_wiki_key>.md` with `grounding_status: full` (since the paper has been read directly by every agent in the loop), harvests wikilinks to grounded concepts/entities, and queues the concept-page follow-on batch for a subsequent SK-16 retrofit sweep. It also appends a closing line to this project CLAUDE.md's Wiki linkage section so the coupling fire is auditable.

**Authoritative asymmetry (reminder).** The project manuscript is the source of truth; the wiki source page is a searchable, cross-linkable view. If the manuscript is later revised (e.g. a camera-ready revision after conditional acceptance), re-fire Coupling D against the new version and update the wiki source page in place — do not create a second source entry unless the revision constitutes a distinct publication.

**When Coupling E.2 fires.** At every Evaluator pre-flight, at **Step 0 — the first Evaluator action, before Step 0a (deterministic checks) and before Step 1 (classification gating)**. The ordering is deliberate: the overlay is the gating probe that tells the Evaluator whether graph-grounding findings need to enter the manuscript read at all, and Step 0a's deterministic checks consume the overlay's source-tag output when grading citations. The pre-flight agent invokes **SK-20 `graph-grounding-overlay`** (`skills/graph-grounding-overlay/SKILL.md`, formalized 2026-04-16). SK-20 resolves `wiki_path` from project metadata (or explicit overrides), reads `${wiki_path}/graphify-out/graph.json` and `GRAPH_REPORT.md`, overlays them on the manuscript's citation set, and writes `reviews/graph_overlay_YYYY-MM-DD.md` containing up to three finding types (graph-stub citations, section-location mismatches, missing-citation candidates) — each tagged with confidence inherited from graphify's `EXTRACTED`/`INFERRED`/`AMBIGUOUS` labels. The overlay is **pre-flight input** to Step 0a and Step 1, not a replacement for any pipeline step; the Evaluator's subsequent seven-step judgment pass consumes the overlay's candidates alongside its own. If `coupling_e_on_review: false`, or if `graphify-out/` is missing, or if the graph is stale relative to the manuscript, SK-20 no-ops cleanly and the Evaluator proceeds without overlay findings. The `skills/run-phase-3/SKILL.md` and `agents/evaluator.md` Step-0 sections are the runtime authority for this order; any document that describes a different ordering is stale.

**No-wiki fallback.** If `wiki_linked: false`, the project proceeds normally. None of the couplings fire, no SK-14/15/17/20 invocations occur, and the Reflector's Phase 3.5 is a no-op. The project is free-standing; later migration to a wiki-linked configuration can be done by flipping `wiki_linked: true` and running a retroactive Coupling C (on accumulated lessons), Coupling D (on the final paper if M5 has been reached), and enabling Coupling E.2 (which will start firing on the next Evaluator round once the flag is set and graphify has been run over the project's sources).

### Step 6: Confirm bootstrap to user

Present the completed skeleton, classification, and wiki-linkage decisions to the user for acknowledgment. From this point forward the project is governed by the full lifecycle in `AGENT_ORCHESTRATION.md §10`.

---

## 4. The Five Couplings — quick reference

This package codifies five synergy couplings between a `Research/<project>/`, a peer `LLM wiki/`, and the `graphify-out/` knowledge-graph layer beneath the wiki. They are listed here so the bootstrap agent has a single-page map of where each coupling is defined and when it fires.

| Coupling | Direction | Fires at | Codified in | Skill |
|---|---|---|---|---|
| A-revised | Research → Wiki (source stubs) | On demand / backlog burn-down | `skills/backfill-source-stubs-from-references/SKILL.md` | SK-15 |
| B | Internal to Wiki (concept grounding) | After SK-15 populates stubs | `skills/retrofit-concept-grounding/SKILL.md` | SK-16 |
| C | Research → Wiki (lessons → syntheses) | Reflector Phase 3.5, every round | `agents/reflector.md §Phase 3.5`, `AGENT_ORCHESTRATION.md §8.5`, `skills/promote-lessons-to-wiki/SKILL.md` | SK-14 |
| D | Research → Wiki (final paper → source) | M5 close-out, post-G.4 | This file §3 Step 5; `skills/ingest-m5-to-wiki/SKILL.md` | SK-17 |
| **E.2** | **Graphify → Evaluator (graph-overlay findings)** | **Evaluator pre-flight, between Step 0a and Step 1** | `AGENT_ORCHESTRATION.md §8.6`; `skills/graph-grounding-overlay/SKILL.md` | **SK-20** |

**Read loop (not a separate coupling).** `EXTERNAL_VERIFIERS.md` §1.5 — when `wiki_linked: true` and `wiki_first_resources` is not `false`, agents consult peer `LLM wiki/` *before* new Zotero PDFs and external tools (e.g. Consensus) for **discovery** of literature. Pairs with Couplings C/D (writing into the wiki) by reusing what the portfolio already ingested.

*Recorded in Coupling D registration (Step 5): `wiki_linked`, `projected_wiki_key`, and the per-coupling activation flags become the project's wiki-facing interface. The bootstrap agent does not decide the couplings' outcomes; it only records intent.*

**Research-process readiness (Abbott, added 2026-06-28).** Bootstrapping a project directory is necessary but not sufficient for Ph1 drafting. `references/abbott_2014_research_process_guidelines.md` gives the Planner an explicit account of the **preliminary→midphase→endphase** work that is *upstream* of drafting: a stabilized design/question (≈5 iterations), an orienting preliminary bibliography, filing discipline, and a phase-appropriate search regime (browsing/bibliography in the preliminary phase; brute-force snowball only once claims are narrowed — the regime `seed-snowball-discovery` operationalizes). The Planner reads that file before dispatching Ph1 drafting or a snowball run on a fresh section and records any readiness gap rather than drafting an unstabilized argument (Abbott guideline §6 checklist).

### Coupling E — Graph-to-Pipeline family

Coupling E has two active sub-couplings at v0.11.0. (The originally roadmapped E.3 contradiction-sweep extension and the SK-19 graph-read-at-planner roadmap entry were retired at v0.11.0 with the c4 phantom-roadmap cleanup; E.1 is now materialised inside SK-33 `seed-snowball-discovery` rather than as a separate skill.)

| Sub-coupling | Direction | Fires at | Skill | Status |
|---|---|---|---|---|
| E.1 | Graphify → Planner (god-nodes, suggested questions, community hubs) | Ph1 seed-snowball | SK-33 `seed-snowball-discovery` graph-substrate iterate phase | **Active** — v0.10.0 |
| E.2 | Graphify → Evaluator (graph-overlay findings A/B/C) | Evaluator pre-flight | SK-20 `graph-grounding-overlay` | **Active** |

**Activation flag.** A project that wants Coupling E to fire must include `coupling_e_on_review: true` in its CLAUDE.md Wiki linkage section (see §3 Step 5). Without this flag, SK-20 no-ops even if `wiki_linked: true`. This is a deliberate opt-in because the graph overlay changes how the Evaluator's findings are weighted, and a project should declare the expectation rather than inherit it silently. Bootstrap-time default for new wiki-linked projects is `true`; retrofit for existing projects is manual.
