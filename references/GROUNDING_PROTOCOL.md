# GROUNDING PROTOCOL — Absolute No-Hallucination Rules

**Status.** This file is a **binding constraint** on all four agents (Planner, Evaluator, Generator, Reflector). It is not a guideline, a best practice, or an aspiration. Every rule in this file is a hard requirement. Violation of any rule is a **BLOCKER** that the Reflector must flag in the reflection report.

**Scope.** Applies to all projects governed by this package, across all sessions, with no exceptions. No user instruction, project directive, or venue rule can override the rules in this file. A user can instruct an agent to skip a review step or relax a style rule; a user cannot instruct an agent to fabricate a citation or claim a file contains something it doesn't.

**Principle.** Every factual claim an agent makes must be traceable to a verifiable source. If the source has not been verified in the current session, the claim must be marked as unverified. If the source cannot be found, the agent must say so rather than fill the gap.

**Stable anchors (v0.15.0-pre).** Every rule heading carries an HTML anchor of the form `<a id="gp-N"></a>` (or `gp-Na` for sub-rules like 7a) so external auditors can resolve `[GP §N]`-style citations deterministically against this file. The forthcoming `scripts/audit/audit_citations.py` (PR-4) uses these anchors to break the citation-grounding self-attestation loop: the script verifies an anchor exists at the cited rule, the LLM never self-verifies. Anchor IDs are stable across renames of the visible heading text; if you rename a rule, do not change its anchor.

---

<a id="gp-1"></a>
## Rule 1 — Read Before Cite

**No agent may cite a file, section, or passage without having read it in the current session.**

### What this means

- Before writing "MASTER §B.1 says X," the agent must have used the Read tool (or equivalent) on `MASTER_research_and_paper_guidelines.md` and confirmed that §B.1 exists and says X.
- Before writing "line 42 of the manuscript contains Y," the agent must have read line 42 and confirmed it contains Y.
- Before writing "the project AGENTS.md requires Z," the agent must have read the project AGENTS.md in this session and confirmed it requires Z.

### What this prohibits

- Citing a package rule from memory of a previous session without re-reading it.
- Citing a line number without having read the file at that line.
- Citing a section heading without having confirmed it exists in the current version of the file (files change between sessions).

### How to comply

Use the Read tool before every citation. If you have read the file earlier in the same session and the file has not been modified since, a re-read is not required for that session. If you are unsure whether the file has been modified, re-read.

### Enforcement

If an agent cites a rule, line, or passage it has not read in the current session, the Reflector flags it as:
```
[GROUNDING VIOLATION — Rule 1] Agent cited <file>#<section> without reading it.
```

### Tier-gated digest exception — RETIRED AT v0.7.0

**Status.** The tier-gated digest exception (v0.4.18 through v0.6.0) is **retired at v0.7.0**. Rule 1 now applies unconditionally at every rung of the v0.7.0 Lifecycle-Stage Ladder (T1 Plan & Draft, T2 Review & Revise, T3 Iterate & Converge, T4 Finalize & Close). Full-file reads are the audit floor at every tier; no digest substitute is a valid Rule 1 satisfier.

**Why this was retired.** The v0.6.0 narrowing to `{T1}` (from the v0.5.5 `{T1 reflex, T2 local}` surface) already signalled the direction of travel — each version of the exception was harder to audit than the prior version and covered fewer cases than it was once meant to. Three v0.6.0-era pressures made the surface untenable at v0.7.0:

1. **Audit overhead vs. coverage.** The exception's five conditions (scope, version binding, release verification, contestation trigger, tier-down on miss) each required a Reflector audit line per invocation. The Reflector work to audit a single T1 digest citation approached the cost of reading the source file directly.
2. **Lifecycle-Stage Ladder semantics (vocabulary since renamed to the Lifecycle-Phase Ladder).** At v0.7.0 the rungs are lifecycle stages, not review-depth modes. T1 Plan & Draft is the widest-scope rung because it is the drafting stage — a digest is not appropriate for drafting work where the author may need to actually re-examine a rule in context.
3. **Single-code-path grounding.** Retiring the exception collapses the audit logic into a single invariant: "every citation is a full-file read." The Reflector's Grounding Audit (§ below) becomes a single rule rather than a rule plus an exception surface; projects can reason about grounding without tier-conditioning.

**What retirement means for a running project.**

- **v0.7.0 onward.** No rule-digest is a Rule 1 satisfier. Every citation, at every tier, must come from a read the agent performed in the current session (or earlier in the session, provided the file has not been edited since). The `scripts/verify_rule_digest.py [retired from tree]` and `scripts/build_rule_digest.py` utilities are retained in the package tree for archive purposes but are not invoked by any v0.7.0 skill, agent, or release-gate phase.
- **v0.6.0 → v0.7.0 migration.** Projects whose ledger carries T1 rows whose `notes` field records a digest-satisfied citation do not need to re-audit those rows retrospectively; the citations were valid under the contemporaneous protocol. Any *new* citation written at v0.7.0 must comply with the unconditional Rule 1, regardless of the section's prior tier history.
- **Reflector Phase 3a (digest integrity).** Retired in lockstep at v0.7.0 (see `agents/reflector.md` Phase 3a — retired note). The Reflector no longer runs `verify_rule_digest.py` at session close. The `[DIGEST INTEGRITY FAIL]` and `§9: digest integrity — verified` emission lines are no longer produced.
- **Enforcement residual.** The Reflector still emits `[GROUNDING VIOLATION — Rule 1]` for any citation without a traceable session read, but the sub-variant `[GROUNDING VIOLATION — Rule 1, digest exception]` is no longer producible because no digest path exists to violate.

**Retirement ledger cross-reference.** `references/TIER_PROTOCOL.md §11` (retirement ledger) records this retirement alongside Evaluator Confirmation Mode, Generator Self-T1 Verdict, and gate EG-2. `references/SKILL_REGISTRY.md` records the corresponding retirement of any skill that invoked the digest path.

**Forward compatibility.** The exception is retired, not suspended. Re-introducing a digest path at a future version requires an explicit protocol amendment with a named mechanism for keeping the digest honest across sessions and a worked cost-versus-audit-overhead analysis. The default answer is full-file reads.

---

<a id="gp-2"></a>
## Rule 2 — Compute Before Report

**No agent may report a count, metric, or pattern match without having actually computed it.**

### What this means

- Before writing "0 em-dashes in the file," the agent must have run a grep (or equivalent search) for `---` and counted the results.
- Before writing "average sentence length is 19.6 words," the agent must have run the computation (via Bash, script, or structured counting).
- Before writing "the file has 192 lines," the agent must have verified the line count.

### What this prohibits

- Reporting a count from memory of a previous session.
- Estimating a count ("probably around 5") and presenting it as exact.
- Copying a count from a prior review artifact without re-verifying (files change between rounds).

### How to comply

Use the Grep tool, Bash tool, or Read tool to produce every number. If a number appears in your output, you must be able to point to the tool call that produced it.

### Enforcement

If an agent reports a count it did not compute, the Reflector flags it as:
```
[GROUNDING VIOLATION — Rule 2] Agent reported <metric> = <value> without computing it.
```

---

<a id="gp-3"></a>
## Rule 3 — Verify Before Reference

**No agent may reference a file path without having verified it exists.**

### What this means

- Before writing "the PDF is at `D:\...\references\Holldack.pdf`," the agent must have used Glob, Bash `ls`, or Read to confirm the file exists at that path.
- Before writing "see `reviews/consolidated_findings_report.md`," the agent must have confirmed the file exists (if the file is supposed to already exist) or must be about to create it (if the reference is to a file the agent is creating in this session).

### What this prohibits

- Guessing a file path based on convention ("it's probably in references/").
- Referencing a path from a previous session without re-verifying (files may have moved or been renamed — the `Pacakage` → `Package` rename in this workspace is exactly this scenario).
- Constructing a path by analogy ("if Baird is at X, Bacon is probably at Y").

### How to comply

Use Glob or `ls` to verify paths. For paths you are about to create, no pre-verification is needed, but the path must resolve after creation.

### Enforcement

If an agent references a path that does not exist and is not being created in the same operation, the Reflector flags it as:
```
[GROUNDING VIOLATION — Rule 3] Agent referenced <path> which does not exist.
```

---

<a id="gp-4"></a>
## Rule 4 — Quote Before Attribute

**No agent may attribute a position to an author without being able to point to the specific passage in a source the agent (or a prior agent in the chain) has actually read.**

### What this means

- Before writing "Baumer et al. argue that human and algorithm are categories that only come into being through their mutual interconnections," the agent must have read the Baumer et al. source (or a text extract of it) and located the specific passage.
- If the agent has not read the source directly, it must say so: "Baumer et al. (2024), as cited by Holldack et al. (2026), argue X." This is the "Cited but not read directly" category from `REFERENCES.md`.

### What this prohibits

- Attributing a position to an author based on the agent's training data alone. Training data may be stale, misremembered, or inaccurate.
- Attributing a position to an author based on what another author says about them, without marking the indirection.
- Paraphrasing a source's position in a way that changes its meaning, then attributing the changed meaning to the original author.

### How to comply

Three tiers of attribution confidence:

| Tier | Condition | How to cite |
|---|---|---|
| **Verified** | Agent has read the source text (PDF, .txt extract, or full text) in the current session or a documented prior session | "Author argues X" (direct attribution) |
| **Inherited** | A prior agent in the chain read the source and recorded the attribution in a review artifact or lessons file | "Author argues X [verified in Round N]" — the agent must read the artifact to confirm |
| **Indirect** | Agent has NOT read the source; attribution comes through another source | "Author, as cited by Source B, argues X" — the indirection must be visible |

The Generator, when writing new prose, must use **Verified** or **Inherited** tier for every attribution. If a source has not been read and cannot be read (e.g. no PDF on disk), the Generator must use the **Indirect** tier and make the indirection visible in the manuscript text.

### Enforcement

If an agent attributes a position to an author without being able to name the tier and trace the source, the Reflector flags it as:
```
[GROUNDING VIOLATION — Rule 4] Agent attributed <claim> to <author> without verified source.
Tier: [unknown — no read, no artifact, no indirection marked]
```

---

<a id="gp-5"></a>
## Rule 5 — Mark Uncertainty

**When an agent is unsure about a factual claim, it must use an explicit uncertainty marker rather than presenting the claim as verified.**

### Uncertainty markers (use these exact strings)

| Marker | When to use |
|---|---|
| `[UNVERIFIED]` | The claim has not been checked against a source in this session. Must be verified before the claim is used in a manuscript or a review finding. |
| `[FROM MEMORY — re-read to confirm]` | The claim comes from the agent's training data or a previous session's context. May be stale or inaccurate. Must be re-read from the source before acting on it. |
| `[INFERRED — verify before using]` | The claim is a logical inference from verified facts but has not itself been directly verified. E.g. "if A and B are true, then C follows" — C is inferred. |
| `[APPROXIMATE]` | The number or metric is an estimate, not a computed value. Must be computed exactly before being used in a deterministic check report. |
| `[REF to be verified]` | The citation has not been confirmed to exist. (Existing convention from MASTER §A.2.) |

### What this prohibits

- Presenting an unverified claim without a marker. If you're not sure, say so.
- Removing an uncertainty marker without having performed the verification. A marker can only be removed by the agent (or a subsequent agent) that has verified the claim.
- Using hedging language ("probably," "likely," "I believe") as a substitute for a marker. Hedging is for epistemic modesty about the world; markers are for traceability of the claim's verification status. They are different things and both may be needed.

### How to comply

When writing any factual claim (a count, a file path, a rule citation, an attribution), ask: "Have I verified this in this session?" If yes, no marker needed. If no, add the appropriate marker.

### Enforcement

If the Reflector finds a factual claim without a marker that turns out to be wrong, it flags it as:
```
[GROUNDING VIOLATION — Rule 5] Agent presented unverified claim as verified:
  Claim: <claim>
  Actual: <what the source actually says, or "source not found">
  Marker that should have been used: [UNVERIFIED] / [FROM MEMORY] / etc.
```

---

<a id="gp-6"></a>
## Rule 6 — No Gap-Filling

**When information is missing, the agent must leave a marked gap rather than fill it with plausible-sounding content.**

### What this means

- If the agent needs to describe what a source argues but has not read the source, it must not invent a plausible-sounding summary. It must write: `[SOURCE NOT READ — attribution requires reading <reference>]`.
- If the agent needs a specific fact (a year, a page number, a definition) and does not have it, it must not guess. It must write: `[FACT NEEDED — verify <what> from <where>]`.
- If the agent is asked to write a paragraph on a topic it does not have enough information about, it must say so: "I do not have enough verified information to write this paragraph. The following sources would need to be read: [list]."

### What this prohibits

- **Plausible fabrication.** Inventing a reasonable-sounding claim to fill a gap. This is the most dangerous form of hallucination because it reads as correct and may not be caught until the piece is reviewed by a domain expert.
- **Confident uncertainty.** Writing a claim in confident language while privately uncertain. The uncertainty must be externalized via a marker (Rule 5) or a gap statement.
- **Analogy-based extension.** "Author A probably agrees with Author B because they are in the same field." This is an inference, not a fact. If it appears in a manuscript, it must be marked `[INFERRED]` and verified before submission.

### How to comply

When you encounter a gap:
1. Stop writing.
2. Determine what information is needed to fill the gap.
3. Attempt to read the source (use Read tool on the PDF, .txt extract, or referenced file).
4. If the source is available, read it and fill the gap with verified content.
5. If the source is not available, leave the gap with a marker and report the gap to the Planner (who can decide whether to acquire the source or adjust the plan).

### Enforcement

If the Reflector finds fabricated content (a claim that does not trace to any source), it flags it as:
```
[GROUNDING VIOLATION — Rule 6] Agent filled a gap with unverified content:
  Content: <the fabricated claim>
  Source: [none found]
  Action: Remove or replace with verified content; add [FACT NEEDED] marker if source not available.
```

---

<a id="gp-7"></a>
## Rule 7 — Chain of Verification

**Every factual claim in the system must have a traceable verification chain: who verified it, when, and from what source.**

### What this means

The verification chain for a claim looks like:

```
Claim: "Baumer et al. (2024) argue that human and algorithm co-constitute one another"
  ↓
Verified by: Evaluator, Round 1, 2026-04-09
  ↓
Source: Baumer et al. (2024), read from PDF extract at
  $CORE_REFS\Baumer Brubaker McGee 24 TCHI algmc subjectivities 34p.pdf.txt
  ↓
Passage: [specific quote or page reference]
  ↓
Status: VERIFIED
```

### Where verification chains live

- **For citations in the manuscript:** `references/REFERENCES.md` records whether each source was read directly, via another source, or not yet read. This is the citation-level chain.
- **For counts and metrics:** The deterministic check output file records what was computed and how. This is the metric-level chain.
- **For rule citations:** The agent's own output (step findings, consolidated report) should name the file and section. The package's traceability matrix (MASTER §top) provides the rule-level chain.
- **For file references:** The tool-call history shows which files were accessed. This is the path-level chain.

### How agents contribute to the chain

| Agent | Verification responsibility |
|---|---|
| **Planner** | Verifies classification inputs (paper type, stage, venue) by reading the manuscript and project files. |
| **Evaluator** | Verifies every count (by running patterns), every rule citation (by reading the package file), and every attribution check (by reading the source or its extract). |
| **Generator** | Verifies every citation it adds (by checking REFERENCES.md and reading the source), every rule it cites for an edit (by reading the package file), and every claim it writes (by tracing it to a source). |
| **Reflector** | Audits the verification chains of all other agents. Flags breaks in the chain. |

### Enforcement

The Reflector's grounding audit (see below) checks the verification chain for every factual claim in the round's outputs. A broken chain is flagged as a grounding violation with the appropriate rule number (1–6).

---

<a id="gp-7a"></a>
## Rule 7a — External Verification (Scholar Gateway, Consensus, Zotero/Scite)

**An attribution may be marked `[externally verified]` and its `[UNVERIFIED]` marker removed only after bibliographic resolution AND inspection of a source passage that supports the actual claim, with its locator and the support judgment logged in the current session.** A Class 1 metadata match establishes bibliographic resolution alone. It does not establish that the source supports the attribution.

### What this means

- "Read before cite" (Rule 1) requires actual source text. Unread sources remain unread; a bibliography or retrieval hit cannot stand in for that read.
- A Class 1 verifier can resolve a paper and retrieve a passage. Record `bibliographic_resolution` separately from `attribution_support`. Metadata-only results leave attribution support `unavailable`; preserve `[UNVERIFIED]` on the claim.
- Class 1.5 (HuggingFace Papers for ML/AI venues) and Class 2 (local Zotero resolver, `.bib` resolver) provide *supporting* evidence only. They do not satisfy Rule 7a on their own. A Class 3 retraction hit (Scite) is binding and escalates to BLOCKER regardless.

### What this prohibits

- Removing an `[UNVERIFIED]` marker based on "I recall this paper exists" — that is training-data memory, not verification.
- Removing an `[UNVERIFIED]` marker based only on the paper appearing in the project's `references/REFERENCES.md` — that is a circular check; REFERENCES.md can itself be wrong.
- Logging an external verification that the agent did not actually invoke in this session.
- Treating a Class 1.5 hit as if it were Class 1 (e.g. "HuggingFace has it, so it's verified" — HuggingFace's corpus is too narrow).

### How to comply

Before removing an `[UNVERIFIED]` marker on a Rule 4 attribution:

1. Choose a Class 1 verifier per `EXTERNAL_VERIFIERS.md` §3 (Zotero library first; Scholar Gateway for external; Consensus if the claim is contested).
2. Invoke the verifier's MCP tool (e.g. `mcp__zotero__zotero_search_by_citation_key`, then fall through to `semanticSearch` if absent from library).
3. Confirm the verifier returns a matching identifier AND matching source metadata (title/authors/year). Title-only matches are insufficient when multiple papers share a title.
4. Read the retrieved passage and context; identify its source locator and the manuscript claim locator. Judge whether it supports the precise attribution, including its qualifications. A matching phrase alone does not establish support.
5. Append a row to the authorized `reviews/external_verification_log.md` with date, agent, exact claim and locator, verifier/query, identifier/title, bibliographic resolution, quoted passage and source locator, attribution support (`supported`, `unsupported`, `contested`, or `unavailable`) and rationale. Retain conflicting evidence and retraction findings.
6. Remove `[UNVERIFIED]` only when attribution support is `supported` and no unresolved conflicting or retraction evidence defeats it. Metadata-only MATCH, missing passages and unresolved contested findings cannot clear the marker.

If the verifier returns NOT FOUND, the `[UNVERIFIED]` marker **stays** and the Evaluator escalates the finding to `[BLOCKER] citation does not resolve via any Class 1 verifier`.

If the verifier returns UNREACHABLE (MCP timeout, auth failure), annotate `[VERIFIER UNREACHABLE — <verifier>]` at the point of use and leave `[UNVERIFIED]` in place. Do not silently fall back to memory.

**Discovery vs. resolution.** Rule 7a’s Class 1 ordering (Zotero among verifiers, then Scholar Gateway, etc.) applies to **removing `[UNVERIFIED]` on a specific attribution**. When **choosing** new literature or PDFs, wiki-linked projects follow **`EXTERNAL_VERIFIERS.md` §1.5 (wiki-first)** before Zotero and before external search — the two orderings are complementary, not identical.

### Enforcement

The Reflector's Phase 2.5 grounding audit (Category 1) spot-checks Rule 7a annotations:

```
[GROUNDING VIOLATION — Rule 7a] Agent removed [UNVERIFIED] marker without external verifier log entry.
  Claim: <claim>
  Expected log entry: reviews/external_verification_log.md row with verifier/query/id/timestamp
  Found: <none or partial>
```

A logged verification that does not reproduce on spot-check is flagged as the fabrication subtype:

```
[GROUNDING VIOLATION — Rule 7a.fabrication] Logged external verification does not reproduce on spot-check.
  Logged: <verifier, query, identifier>
  Re-checked: <identifier or not-found>
  Action: Restore [UNVERIFIED] marker and re-verify.
```

---

## Grounding Audit (Reflector responsibility)

The Reflector runs a **grounding audit** as part of every reflection round. This is a new sub-phase within the Reflector's Phase 2 (Extract Lessons), specifically focused on hallucination detection.

### Audit procedure

1. **Citation audit.** For every citation the Generator added or the Evaluator referenced in this round:
   - Does the reference exist in `references/REFERENCES.md` or the manuscript bibliography?
   - Has the source been read (directly or via extract) in this session or a documented prior session?
   - Is the attributed claim actually present in the source? (Spot-check at least 3 attributions per round.)
   - Flag any citation that fails as `[GROUNDING VIOLATION — Rule 4]`.

2. **Metric audit.** For every count or metric the Evaluator reported:
   - Was the grep/computation actually run? (Check tool-call history or the deterministic output file for the computation.)
   - Does the reported number match the computed number?
   - Flag any discrepancy as `[GROUNDING VIOLATION — Rule 2]`.

3. **Path audit.** For every file path referenced by any agent:
   - Does the path exist on disk?
   - Flag any broken path as `[GROUNDING VIOLATION — Rule 3]`.

4. **Rule-citation audit.** For every package rule cited in the findings or revision log:
   - Does the cited section exist in the cited file?
   - Does the section say what the agent claims it says? (Spot-check at least 3 rule citations per round.)
   - Flag any fabricated or misquoted rule as `[GROUNDING VIOLATION — Rule 1]`.

5. **Gap-fill audit.** For every new paragraph the Generator wrote:
   - Is every factual claim in the paragraph traceable to a source?
   - Are there any claims that read as confident but have no source? (These are the hardest to catch: plausible fabrication. The Reflector must actively look for claims that are too smooth, too specific, or too convenient without a citation.)
   - Flag any ungrounded claim as `[GROUNDING VIOLATION — Rule 6]`.

6. **Marker audit.** For every uncertainty marker in the round's outputs:
   - Was the marker resolved by verification? If so, confirm the marker was removed after verification.
   - If not resolved, is the marker still present in the final output? It should be — unresolved markers must not be silently dropped.
   - Flag any silently dropped marker as `[GROUNDING VIOLATION — Rule 5]`.

### Audit output format

```markdown
### Grounding Audit — Round [N]

**Citations checked:** [n]
- Verified: [n]
- Indirect (marked): [n]
- Violations: [n] → [details]

**Metrics checked:** [n]
- Computed: [n]
- Violations: [n] → [details]

**Paths checked:** [n]
- Exist: [n]
- Violations: [n] → [details]

**Rule citations checked:** [n]
- Verified: [n]
- Violations: [n] → [details]

**Gap-fill check:** [n paragraphs checked]
- All claims grounded: [n]
- Violations: [n] → [details]

**Markers:** [n markers in output]
- Resolved by verification: [n]
- Still open (correctly retained): [n]
- Silently dropped: [n] → [details]

**Grounding verdict:** [CLEAN / n violations found]
```

---

## How this integrates with the package

### Binding chain

```
GROUNDING_PROTOCOL.md (this file)
    ↓ referenced by
agents/planner.md, agents/evaluator.md, agents/generator.md, agents/reflector.md
    ↓ enforced by
Reflector → Grounding Audit (every round)
    ↓ reported in
reviews/reflection_report.md → Grounding Audit section
```

### Precedence

This file's rules **cannot be overridden** by:
- User instructions ("just make something up for now")
- Project directives ("we don't need to verify citations in this project")
- Venue rules (no venue requires fabrication)
- Other package files (no package rule authorizes hallucination)

If a user instructs an agent to fabricate content, the agent must refuse and explain why: "The Grounding Protocol prohibits fabricating content. I can mark the gap with `[FACT NEEDED]` and identify what source would be needed to fill it."

### Relationship to existing files

| File | How grounding interacts |
|---|---|
| `DETERMINISTIC_CHECKS.md` §7 | Already checks for `[REF to be verified]` placeholders. Grounding Protocol extends this to all seven hallucination types. |
| `SAFEGUARD_LAYER.md` Check 5 | Edit Traceability requires rule citations for every edit. Grounding Protocol Rule 1 requires that the cited rule was actually read. |
| `SAFEGUARD_LAYER.md` Check 3 | Abstract-Body Consistency checks whether promises are delivered. Grounding Protocol Rule 4 checks whether the delivered content is actually sourced. |
| `REFERENCES.md` (project) | Already categorizes sources as "read directly," "snowball," or "cited via." Grounding Protocol Rule 4 uses this categorization to determine the attribution tier. |
| `EXTERNAL_VERIFIERS.md` (package) | Enumerates external verifier tiers. Rule 7a requires bibliographic resolution plus inspected passage support, with source/claim locators and a logged judgment, before clearing an attribution's `[UNVERIFIED]` marker. |
| `skills/graph-grounding-overlay/SKILL.md` (SK-20) | Materializes Coupling E.2. Produces findings tagged `[source: graph-extracted]` / `[source: graph-inferred]` / `[source: graph-stub]`. Grounding-audit Category 8 traces every such finding back to `graph.json`. The graph is NOT a Class 1 verifier under Rule 7a; the two layers are complementary. |

---

## Quick reference card (for agent prompts)

Every agent should internalize these six commands:

1. **Read it before you cite it.**
2. **Compute it before you report it.**
3. **Verify the path before you reference it.**
4. **Find the passage before you attribute it.**
5. **Mark what you're unsure about.**
6. **Leave the gap rather than fill it with plausible fiction.**

And two meta-commands:

7. **Audit every round for violations of 1–6.** (Reflector's Phase 2.5)
7a. **If you didn't read it, verify externally and log it.** (Scholar Gateway / Consensus / Zotero+Scite per `EXTERNAL_VERIFIERS.md` §3; log in `reviews/external_verification_log.md`.)

---

*This file is the integrity floor of the package. It does not make the writing better; it makes the writing honest. Everything else in the package — the style rules, the severity tiers, the narrative craft, the voice register — is worthless if the underlying claims are fabricated. Grounding comes first.*
