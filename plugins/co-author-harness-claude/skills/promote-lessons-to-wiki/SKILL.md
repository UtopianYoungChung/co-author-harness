---
name: promote-lessons-to-wiki
description: 'Promote a project''s research_notes/lessons_learned.md entries into a generalizing synthesis page in the LLM wiki with bidirectional wikilinks and scope qualifiers (materializes Coupling C). Use when: "promote lessons to wiki", "close reflection round with wiki update", after appending an L-xx lesson.'
trigger: when the user asks to promote lessons to the wiki, close a reflection round with a wiki update, materialize Coupling C, or regenerate a lessons synthesis after L-xx append
created_by: Reflector (Coupling C pilot)
created_from: Research↔Wiki diagnostic audit, 2026-04-13 — Finding F4 (lessons terminate in-project, wiki syntheses is natural sink); pilot executed 2026-04-13 producing `lessons-agency-delegation-2026-04-13.md`
pattern_source: Research-root CLAUDE.md §6 (cross-project consistency), §11 (lessons compounding); AGENT_ORCHESTRATION.md Reflector Phase 4; GROUNDING_PROTOCOL.md (synthesis pages must be groundable)
version: 1.0
---

# Promote Lessons to Wiki

You are materializing **Coupling C** — the Reflector-to-Synthesis feedback loop connecting a project's `research_notes/lessons_learned.md` to the LLM wiki's `syntheses/` folder. This skill converts project-local feedback memories (L-xx entries) into a generalizing, wikilinked synthesis page, preserving the project file as the authoritative append-only store.

## Preconditions

Before invoking this skill, verify all of the following. Abort with a clear error if any fails.

1. **Wiki exists.** The path `knowledge/LLM wiki/wiki/` (relative to the workspace root the user has mounted, or absolute per the user's CLAUDE.md) is present with subfolders `sources/`, `concepts/`, `entities/`, `syntheses/`, and files `index.md` + `log.md`.
2. **Project has lessons.** The target project has `research_notes/lessons_learned.md` with at least one `L-xx` entry.
3. **Project has a source page in the wiki** (or the manuscript has been ingested). The generalizing synthesis must cite the project's own manuscript via `[[sources/<key>]]`. If the source page does not exist, stop and ask the user whether to (a) ingest the manuscript first (Coupling D), or (b) proceed with a stub placeholder marked `TODO-ground`.
4. **No uncommitted review round in flight.** Check `reviews/` for a report whose date is newer than the latest L-xx entry. If a review has produced findings that have not yet been appended as a lesson, ask the user whether to wait.

## What you do

### Phase 1 — Read and map

1. Read `research_notes/lessons_learned.md` in full. Enumerate L-01, L-02, …, L-N.
2. Read `research_notes/directives.md` if present. Note any P-stage, venue, voice register, or audience commitments that qualify the scope of the lessons.
3. Read the project's source page at `knowledge/LLM wiki/wiki/sources/<key>.md`. Extract the source key, the paper's P-stage (if recorded), and the concepts it already wikilinks to.
4. Read `knowledge/LLM wiki/wiki/index.md` to see which `concepts/` and `syntheses/` pages already exist. Do not invent wikilinks to nonexistent pages without marking them as red-link candidates.

### Phase 2 — Classify each lesson for generalizability

For each L-xx, decide its **promotion class**:

| Class | Meaning | Promotion action |
|---|---|---|
| **G — Generalizable** | The rule applies across multiple projects with no or minor qualifier | Promote with a **Generalization** paragraph stating the scope condition |
| **P — Project-conditional** | Applies only under specific conditions (P-stage, venue, voice register, co-authorship structure) | Promote with explicit **Scope:** qualifiers in the Generalization paragraph |
| **L — Local** | Specific to this manuscript's constructs (e.g. "line 133 of this draft") | Do NOT promote. Note in the synthesis page's §1 that L-xx was assessed local |
| **D — Deferred** | Generalizable in principle but the wiki lacks grounding infrastructure (e.g. concept page is empty) | Promote with a `TODO-ground` marker naming the missing concept page |

Produce the classification table explicitly before drafting.

### Phase 3 — Draft the synthesis page

Write to `knowledge/LLM wiki/wiki/syntheses/lessons-<project-slug>-<YYYY-MM-DD>.md`. Use this structure:

```markdown
---
type: synthesis
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
tags: [<from lessons + domain>]
sources: [<project source key>]
inbound_projects: [<project path from workspace root>]
---

# <Title — name the generalizing thread, not the project>

> Promoted from `<project path>/research_notes/lessons_learned.md` (<L-range>) on <date> as
> <"the pilot of" | "a further materialization of"> **Coupling C** — the Reflector→Synthesis feedback loop.
> Each lesson was originally a project-local feedback memory about <source key>. Promoted here,
> they become candidate **package-tier commitments** available to any future project whose problem
> shape they fit.

## 1. Problem Statement

<Why this promotion, what the lessons collectively articulate, what is NOT promoted (L-class entries).>

## 2. The Lessons (one subsection per promoted L-xx)

### L-xx — <One-line rule statement>

<Restatement in generalizing prose. Then:>
**Generalization.** <The scope condition. If class P, state it explicitly: "Applies when P-stage = P0/P1 and voice register = cartographer.">

<Wikilinks to concepts: [[concepts/agency]], [[concepts/humanness]], etc. Wikilinks to source: [[sources/<key>]].>

<Repeat for each promoted L-xx.>

## 3. Cross-Lesson Synthesis

<PhD-level reading: do the lessons compose? What stance do they articulate together? This is the value-add over the project file — the connective tissue.>

## 4. Trade-offs in Promoting These Lessons

<Three risks at minimum. Register capture, voice inheritance, concept-page feedback obligations, etc.>

## 5. Operational Consequences

<Is this a falsifiable commitment? What would disconfirm the coupling? Name the test.>

## 6. Back-references

- Source project: `<project path>/research_notes/lessons_learned.md` (authoritative — append-only there; this page is a view)
- Source manuscript: [[sources/<key>]]
- Related synthesis: [[syntheses/...]] (if any)
- Concept pages implicated: [[concepts/...]], [[concepts/...]]

---

*<Skill-version attribution and regeneration note.>*
```

### Phase 4 — Update the wiki index and log

1. Append a new row to the Syntheses table in `knowledge/LLM wiki/wiki/index.md`:
   `| <Title> | <YYYY-MM-DD> | [[syntheses/<filename-without-ext>]] |`
2. Append a new entry to `knowledge/LLM wiki/wiki/log.md`:
   ```
   ## [<YYYY-MM-DD>] promote | Coupling C — <project> lessons → synthesis

   Promoted <L-range> from `<project path>/research_notes/lessons_learned.md` into
   `wiki/syntheses/<filename>` with bidirectional wikilinks to [[sources/<key>]] and
   concept pages (<list>). The project's lessons file remains authoritative; this
   page is the generalizing view. <Regeneration or first-run note.>
   ```

### Phase 5 — Insert the back-pointer in the project file

Add a **non-destructive** header note to `<project path>/research_notes/lessons_learned.md` — immediately after the "**How to add entries.**" paragraph in the preamble, before L-01. Do NOT modify any L-xx entry. The note reads:

```
**Cross-project view (<YYYY-MM-DD>).** L-<range> have been promoted to the LLM wiki as a generalizing synthesis page: `knowledge/LLM wiki/wiki/syntheses/<filename>`. That page is a *view* into cross-project relevance (Coupling C of the Research↔Wiki synergy architecture, <audit date>). This file remains the **authoritative, append-only store**; edits to lessons happen here, and the synthesis page is regenerated when L-<range> change or when L-<next>+ is appended.
```

If the header note already exists from a prior run, **update its date and L-range** rather than adding a second note.

### Phase 6 — Verify

Perform these checks and report results:

1. **File count.** `ls knowledge/LLM wiki/wiki/syntheses/` — the new file is listed.
2. **Link resolution.** Every `[[sources/...]]`, `[[concepts/...]]`, `[[syntheses/...]]`, `[[entities/...]]` in the new page resolves to an existing file. Report any red links as **red-link candidates** — do not fabricate content for them.
3. **Index registration.** `grep` the new filename in `index.md`: expect exactly one hit.
4. **Log registration.** `grep` the new filename in `log.md`: expect exactly one hit.
5. **Back-pointer.** `grep` the synthesis filename in the project's `lessons_learned.md`: expect exactly one hit.
6. **Authoritative asymmetry.** Confirm that no L-xx entry was edited — diff the project file against its prior state and show only the preamble note as changed.

## What you output

```markdown
## Coupling C Promotion — <project> → wiki

**Project:** <path>
**Date:** <YYYY-MM-DD>
**Lessons assessed:** <count>

### Classification table
| L-xx | Class (G/P/L/D) | Scope qualifier |
|---|---|---|
| L-01 | <G/P/L/D> | <one-line qualifier or "none"> |
| ... | ... | ... |

### Files written / edited
- `knowledge/LLM wiki/wiki/syntheses/lessons-<slug>-<date>.md` — created (<word count>)
- `knowledge/LLM wiki/wiki/index.md` — Syntheses row appended
- `knowledge/LLM wiki/wiki/log.md` — promote entry appended
- `<project>/research_notes/lessons_learned.md` — preamble back-pointer inserted (no L-xx edits)

### Red-link candidates (if any)
<List wikilinks to pages that do not yet exist, with a short note on whether each should be created as its own follow-on task.>

### Verification
- [ ] Synthesis file exists
- [ ] All non-red wikilinks resolve
- [ ] Index registration: 1 hit
- [ ] Log registration: 1 hit
- [ ] Back-pointer in project file: 1 hit
- [ ] No L-xx edited (diff shows preamble only)

### Falsifiability note
<One sentence naming what would disconfirm this coupling — typically: "If no future project cites this page via `sources:` or inline wikilinks, Coupling C is degenerate and should be redesigned.">
```

## What you do NOT do

- **Do NOT edit any L-xx entry.** The project file is append-only by the Reflector. Edits to lesson text happen in the project file by the user or by a Reflector run, never by this skill.
- **Do NOT copy L-xx verbatim into the synthesis.** Verbatim promotion violates Research-root CLAUDE.md §6 ("do not bleed directives"). Always restate with a scope qualifier.
- **Do NOT invent concept pages or source pages.** If a wikilink would be red, emit a **red-link candidate** entry in the output. Creating new concept pages is Coupling B's job, not this skill's.
- **Do NOT promote L-class lessons** (manuscript-specific). Note them in §1 of the synthesis page as assessed-and-held-local.
- **Do NOT delete or move the project's lessons file.** Only insert the non-destructive preamble note.
- **Do NOT run this skill while a review round is producing new findings.** If the latest `reviews/` artifact is newer than the latest L-xx, ask the user whether to wait or proceed with a stale promotion.
- **Do NOT promote if the project's source page does not exist in the wiki.** Stop and ask; the synthesis must be groundable to [[sources/<key>]] under the Grounding Protocol.

## Regeneration behavior

If this skill is invoked a second time on the same project and the L-range has not changed, the skill **no-ops** and reports "already promoted at <filename>." If the L-range has grown (new L-xx appended), the skill **regenerates** the synthesis page in place (overwrite), re-classifies all lessons, and updates the back-pointer date. The old synthesis file is not preserved — the wiki log is the history.

## Notes on tier and scope

This is a **package-tier** skill: it applies to any project under `Research/` that maintains a `lessons_learned.md` under the standard structure (Research-root CLAUDE.md §7). It does not apply to non-academic projects and should not be promoted to the global tier.
