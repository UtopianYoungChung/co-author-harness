# ARGUMENT COHERENCE — the shared review obligation

**Status.** Binding. One obligation, reused by every route that reviews or produces
prose in this package. It is not a new optional pass and has no slash command of its
own: `SAFEGUARD_LAYER.md` Check 9 is where a reviewer executes it, the
`argument_coherence` required check is where `PROJECT_INDEPENDENT_WORKFLOW.md`
enforces it, and `scholarly_evaluation.py` `PROFILE_MINIMUM` is where the governed
route enforces it. Those three surfaces cite this file; they do not restate it.

**Inputs.** `DETERMINISTIC_CHECKS.md` §9f (`scripts/coherence_prefilter.py`) supplies
the prose-unit inventory and the coverage denominator; `scripts/coherence_review.py`
validates the resulting evidence.

**What it catches.** Prose that is fluent, grammatical, and topically relevant, but
does not advance the argument of its paragraph or of the document. Every mechanical
control in this package is blind to this defect by construction: the
`DETERMINISTIC_CHECKS.md` §9a pre-filter keys on named-author application phrases
and descriptive-to-normative jumps; §9b–§9d key on sentence length, definition
topology, and cognitive load. A well-formed sentence that simply does no
argumentative work matches none of those patterns.

**What it is not.** It is not source-support verification. A valid citation cannot
clear irrelevant placement, and a coherent bridge cannot clear an unsupported claim.
Keep the two verdicts on separate lines; `GROUNDING_PROTOCOL.md` remains absolute
and is not softened, satisfied, or overridden by anything in this file.

---

## 1. The obligation

For the reviewed span, determine and report all four of the following.

1. **Paragraph purpose.** What argumentative work this paragraph does in this
   section. Determine it **from the actual text and its context**. A plausible role
   label ("this is the motivation paragraph") asserted without textual warrant is
   not a determination and does not satisfy this item. If the purpose cannot be
   recovered from the text, that is itself the finding.
2. **Sentence contribution.** For each substantive sentence, how it serves that
   purpose. The permitted dispositions are `advances`, `supports`, `qualifies`,
   `background`, `transition`, and `none`. Only `none` is a defect, and it requires
   a finding.
3. **Transitions between concepts.** Whether each move from one concept to the next
   is recoverable by the reader from what is on the page.
4. **Connection to the document's research commitments.** Whether what this passage
   promises, defines, asks, or commits to is carried by the document's stated
   method, deliverables, and evaluation — and whether the passage still agrees with
   the occurrences of those commitments elsewhere.

Item 4 is the document-level obligation and is distinct from items 1–3. A paragraph
can be internally coherent and still break the document.

## 2. Finding shape

A finding that does not carry all four of these is not a finding under this file:

- **The exact passage** — quoted verbatim from the reviewed bytes, with a locator.
- **The failed relationship** — which of the four relations above broke, named:
  `purpose_unrecoverable`, `no_contribution`, `answers_other_question`,
  `unexplained_meaning_change`, `promise_without_payoff`, `broken_bridge`, or
  `disconnected_neighbour`.
- **Its effect on the argument** — what the reader can no longer follow or is
  licensed to conclude wrongly. Not a restatement of the rule.
- **A bounded remedy** — the smallest change that restores the relationship, within
  the passage or its paragraph.

**Reject explanations that require the reviewer to invent an unstated premise.** If
the only way to describe the defect, or to justify the remedy, is to supply a claim
the author never made, the reviewer has written the author's argument rather than
reviewed it. Say the relationship is unrecoverable and stop there.

## 3. Defect classes

| Code | Class | What it looks like |
|---|---|---|
| **AC-1** | Source-status aside without argumentative consequence | A true, relevant remark about the state of the literature, the corpus, or the method that is never used — and whose insertion breaks the bridge between the sentences it separates. |
| **AC-2** | Sentence answers a different question from its paragraph | Fluent, on-topic, and addressed to a question the paragraph is not asking. |
| **AC-3** | Unexplained change of meaning | A term is used in a sense that differs from its established sense elsewhere in the document, with no marked revision. |
| **AC-4** | Research promise without a corresponding method or evaluation | The document commits to producing, showing, or evaluating something that no later method or evaluation section carries. |
| **AC-5** | Revision that disconnects an unchanged neighbouring sentence | The edited sentence is sound in isolation; the sentence beside it, untouched, now refers to something that is no longer there. |

AC-5 is the class that ordinary scope discipline hides: the reviewer inspects the
changed bytes, the changed bytes are fine, and the damage is one sentence away.

## 4. Positive controls — what is not a defect

These are legitimate and must not be flagged. A control list is part of the
obligation, not a courtesy.

- **Implicit transitions recoverable from the text.** A connective is not required.
  If the relationship is available to the reader without one, the transition passes.
- **Legitimate background.** Orientation that the argument needs is `background`, a
  passing disposition.
- **Qualifications and counterarguments.** Material that limits or complicates the
  claim is `qualifies`. Flagging it as inert inverts the point: a paper that only
  states what supports it is the weaker paper.
- **Connections established earlier in the section.** A sentence may rely on a
  relation the section already built. Re-establishing it is not required.
- **Authorial voice.** The `C-7` idiolect carve-out applies here in full. A
  characteristic rhythm, a flat affect, a deliberate repetition is voice.

**No fixed paragraph formula and no mandatory signposting.** This file never
requires a topic sentence in a given position, a stated transition word, a
three-part paragraph, or a roadmap. A remedy that imposes one is out of scope.

## 5. When the obligation runs

- **Before substantive revision.** Diagnose the relevant passage. The diagnosis is
  independent of the revision plan and precedes it.
- **After revision.** Review the **whole changed paragraph**, not the changed
  sentences, plus the declared neighbouring units. AC-5 is unreachable otherwise.
- **On commitment-bearing changes.** A change to a definition, a research question,
  a deliverable, or an evaluation commitment additionally requires examining that
  commitment's affected occurrences elsewhere in the document, and reporting them.

**Inspection may extend beyond authorized write scope.** Reading a neighbouring
paragraph to judge AC-5 is required; editing it is not authorized by having read it.
Defects found outside the write scope are **findings**, reported with locators, and
they confer no write authority. Widening the edit on the strength of an inspection
is a scope violation.

## 6. Evidence and invalidation

A review under this file is bound to: the candidate bytes, the context actually
relied on, the covered scope, the applicable rules, the findings, their
dispositions, and the actual execution that produced it. **Any change to those
inputs invalidates the review**; a review of earlier bytes is stale and cannot be
carried forward. Applying a repair preserves intervening author edits through
guarded application and read-back verification.

Missing, partial, failed, stale, replayed, or improperly self-issued evidence
prevents a reviewed-completion claim.

**Mechanical validation establishes evidence integrity and coverage. It does not
establish semantic correctness.** `scripts/coherence_review.py` can confirm that
every changed unit was covered, that every quoted passage occurs in the candidate,
and that no review was replayed from other bytes. It cannot confirm that the
purpose was read correctly or that the finding is right. Nothing in this package
may report a passing `argument_coherence` check as evidence that the prose is
coherent — only that the obligation was executed against these bytes and its
findings were dispositioned.

## 7. Outcomes

Use exactly these:

- **Review incomplete** — required execution, context, or current evidence is
  missing.
- **Changes required** — a substantiated argumentative defect remains unresolved.
- **Review complete** — required checks ran on the identified version and findings
  received justified dispositions.

A recorded user exception remains an exception. It does not convert to a semantic
pass, and it is reported as an exception in every downstream summary.

---

## 8. Where this obligation is enforced

| Route | Scope label | Enforcement point | Kind |
|---|---|---|---|
| Named read-only pass | `adhoc_review` | the named skill's reporting contract | report-only; there is no completion to gate |
| Ordinary drafting / revision | `project_independent` | `piw_coordinator.effective_checks` → `validate_result` → `advance` → `piw_completion_guard.verify_completion` | blocking |
| Governed staging / lifecycle | `lab_iteration`, `full_lifecycle` | `scholarly_evaluation.PROFILE_MINIMUM['argument_coherence']` | blocking |
| Conversational manuscript application | — | **none** | see below |

**Conversational application is not a reviewed route.** When an agent edits a
manuscript directly from chat, this package's only control is the
`hooks/hooks.json` PreToolUse gate, which is a *routing* gate: it asks whether a
scope was declared and whether the destination is permitted. It does not and cannot
require a coherence review, and it is honoured only where plugin-scoped PreToolUse
hooks run (the Claude Code CLI and the Claude Agent SDK; Cowork and Cursor coverage
are not claimed). `SK-32` remains `CLOSED_PUBLIC_BYPASS` and chat-apply remains
unsupported for manuscript bytes. Do not describe the package as protecting prose
edited outside its enforcement points.

## 9. Provenance

Written 2026-09-21 under a work order to enforce argument coherence, after a
conversational manuscript application where a style-lint pass returned clean on an
edited line and no independent semantic evaluator ran on those bytes at all. The
reproduced baseline, the route-and-control matrix, and the defect corpus are in
`docs/evaluation/argument-coherence-baseline.md`.
