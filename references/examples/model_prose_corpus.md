---
name: model_prose_corpus
version: 2.0
date: 2026-07-20
description: >
  Package-authored synthetic calibration examples for reader-accessibility
  Sub-checks A-H. No passage is copied from or attributed to an external work.
content_origin: synthetic
license: MIT
---

# Synthetic Model-Prose Corpus

## Purpose and limits

These examples illustrate the functions judged by reader-accessibility
Sub-checks A-H. They are synthetic package fixtures, not excerpts, quotations,
or imitations of a named author. They help a reviewer recognize a function;
they do not create thresholds, severity arithmetic, or an automatic CLEAN
verdict. Those decisions remain with the policy profile and the Evaluator.

Each example uses an invented research setting involving a municipal service
team and a fictional scheduling system called Harbor. The examples may be
reused, modified, and redistributed under the package's MIT license.

---

## Sub-check A — Paragraph Cadence

**Property being illustrated:** a visible internal turn changes the paragraph's
direction.

> The service team first treated late appointments as a forecasting problem.
> It added more historical data and recalculated demand each night. Yet the
> delays persisted because the schedule assumed every case followed the same
> path. The team therefore changed the question: instead of predicting a
> single queue, it mapped the points where staff had to wait for another unit.
> That shift exposed coordination delays that the forecast could not represent.

**Functional note.** “Yet” begins a counter-move, and “therefore” turns the
diagnosis into a new analytic action. The paragraph does not merely contain cue
words; its object of analysis changes from demand volume to coordination.

---

## Sub-check B — Sentence-Length Distribution

**Property being illustrated:** sentence shape varies for rhetorical function.

> Harbor grouped requests by urgency, location, staff availability, and the
> dependencies recorded by each participating unit. The first simulation
> looked convincing because its average waiting time fell across the full test
> set. One case broke it. A resident who needed both translation and an
> accessibility assessment moved between two queues until the day ended.

**Functional note.** The short sentence marks the reversal after two
explanatory sentences. Its brevity carries emphasis; variation is not inferred
from a raw average alone.

---

## Sub-check C — First-Use Definition

**Property being illustrated:** a construct is defined before it carries later
conceptual work.

> We call a **handoff gap** any interval in which one unit has finished its
> assigned action but the next unit lacks either the information or authority
> needed to begin. This definition separates handoff gaps from ordinary queue
> time. Later comparisons use the construct only for delays that meet both
> conditions.

**Functional note.** The first sentence supplies a bounded definition, the
second distinguishes a nearby concept, and the third tells the reader how the
term will be used.

---

## Sub-check D — Section-Transition Signposting

**Property being illustrated:** a section opening both locates the reader and
states the section's action.

> The previous section showed that most delays arose between units rather than
> within them. This section tests whether Harbor's dependency map makes those
> cross-unit waits visible before a schedule is approved.

**Functional note.** The first sentence is orienting; the second is the
contribution clause. Neither function substitutes for the other.

---

## Sub-check E — Jargon Discipline

**Property being illustrated:** new terms enter in a controlled sequence and
receive an immediate plain-language role.

> Harbor records a **dependency** when one team cannot act until another team
> provides something. A **dependency owner** is the team responsible for that
> item. Together, the two terms let the schedule show who is waiting, what is
> missing, and who can resolve the delay.

**Functional note.** The paragraph introduces two related terms, defines each
at entry, and consolidates them in ordinary language before adding more
vocabulary.

---

## Sub-check F — Worked Examples at Density Spikes

**Property being illustrated:** a concrete case carries a multi-part conceptual
claim.

> Consider a housing inspection that requires a translator and an electrical
> specialist. Harbor can assign both people, but the appointment still fails if
> the translator receives the address only after the specialist has arrived.
> The case shows why resource availability, information timing, and authority
> to reschedule must be evaluated together: satisfying any one condition does
> not complete the coordination task.

**Functional note.** The example instantiates three dependencies in one event
and shows their interaction. It is doing explanatory work, not decorating the
claim.

---

## Sub-check G — Cumulative Cognitive Load

**Property being illustrated:** a structural boundary names accumulated
material and signals the next move.

> The analysis has established three points: delays cluster at unit boundaries,
> ownership is often ambiguous, and timing information arrives too late for
> staff to adjust. The next section treats these findings as design constraints
> and asks which of them Harbor can enforce directly.

**Functional note.** The first sentence consolidates prior results; the second
states how the argument will use them. A local section signpost alone would not
perform this backward-looking consolidation.

---

## Sub-check H — Register Appropriateness

**Property being illustrated:** technically necessary terms remain, while
agents, actions, and transitions stay visible.

> When a supervisor approves the schedule, Harbor checks whether every recorded
> dependency has an owner. If an owner is missing, the system returns the case
> to the coordinating team and names the unresolved item. The rule does not
> guarantee a successful appointment; it makes responsibility visible before
> the resident begins another trip through the service process.

**Functional note.** “Dependency” retains its defined technical role, but the
sentences identify who acts, what the system checks, and what follows. The final
sentence states the boundary of the claim instead of hiding it in nominalized
prose.

---

## Extension rule

Add only package-authored synthetic examples or material whose redistribution
license is recorded in `references/distribution_rights.json`. Project prose may
inform an abstraction, but do not copy project text into this package without
the author's explicit redistribution permission and a registered disposition.
