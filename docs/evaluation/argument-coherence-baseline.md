# Argument coherence — baseline, route matrix, and evaluation protocol

**Date.** 2026-09-21. **Package version at measurement.** `version.json` (0.50.2).
**Obligation.** `references/ARGUMENT_COHERENCE.md`. **Reviewer procedure.**
`SAFEGUARD_LAYER.md` Check 9. **Pre-filter.** `DETERMINISTIC_CHECKS.md` §9f.

This file records what the package could and could not catch **before** the
obligation existed, where the obligation is now enforced, and what the evaluation
evidence does and does not establish. It is not a qualification record.

---

## 1. Route-and-control matrix

Each route is classified by what the harness actually controls, not by what it
documents. "Implemented" means an enforcement point exists in code and is tested.

| Route | Scope label | Entry point | Reviewer execution | Application point | Completion reporter | Evidence validator | Coherence enforcement | Status |
|---|---|---|---|---|---|---|---|---|
| Named read-only pass | `adhoc_review` | `piw_session.py bind-pass`, `/sentence-level-pass`, `/narrative-structure-pass`, `/grammar-mechanics-pass`, … | the invoking agent reads the named SKILL and reports | **none** — the pass never writes prose | none (`bound_not_reviewed`) | none | **report-only.** The two closest skills now state that a clean craft or arc result is not a coherence result and route the observation to Check 9. | implemented (as a reporting duty; there is no completion to gate) |
| Ordinary drafting | `project_independent` | `/run-draft` → `piw_coordinator.start` | distinct native Generator / Evaluator / Reflector children | `piw_coordinator.deliver` to an authorized task output | `piw_completion_guard.verify_completion` | `piw_coordinator.validate_result`, `replay_records` | **blocking.** `argument_coherence` is appended by `effective_checks` and cannot be removed by a caller. | implemented + tested |
| Ordinary revision | `project_independent` | `/run-iterate` → `piw_coordinator.start` with an `mss_revision` ingress | same, with Evaluator diagnosis first | same; input bytes stay read-only unless a separate apply transaction authorizes them | same | same | **blocking**, with changed-unit + neighbour coverage measured against the author's original bytes | implemented + tested |
| Governed staging / lifecycle | `lab_iteration`, `full_lifecycle` | `/run-finalize`, `assignment_writer_commit.py` | Evaluator fire table on certified staging bytes | `assignment_writer_commit.py` (staging only) | `scholarly_evaluation.py` C6 verify | `scholarly_evaluation.validate_scholarly_evaluation_binding` | **blocking.** `argument_coherence` is in `PROFILE_MINIMUM`; a profile omitting it is `SET_COVERAGE_INCOMPLETE`. | implemented + tested (coverage-level; no finding-code floor is pinned) |
| Conversational manuscript application | *(none declared)* | an agent calling `Write`/`Edit` on manuscript bytes from chat | whatever the agent chooses | the file itself | none | none | **none.** See §1.1. | **unsupported** |

### 1.1 The route the harness does not control

When an agent edits a manuscript directly from chat, the package's only mechanical
control is the `hooks/hooks.json` PreToolUse gate. That gate is a **routing** gate:
it asks whether a scope was declared and whether the destination is permitted. With
no `FRC_PARENT_SCOPE` it denies writes to paths containing `manuscript`, `research`,
`60_workbench`, or `milestones`; under `project_independent` it additionally
confines writes to the bound PIW staging root. It never asks whether a review ran,
and it cannot: a semantic obligation is not expressible as a path predicate.

Three limits are stated rather than papered over:

1. The gate is honoured by the **Claude Code CLI and the Claude Agent SDK**. Cowork
   and Cursor coverage are not claimed (`scripts/hooks/full_run_pretooluse_gate.py`
   module docstring). Where plugin-scoped PreToolUse hooks do not run, there is no
   control at all.
2. `FRC_GATE_HOOK_DISABLE` remains an explicit off switch, and a session without
   `CLAUDE_PLUGIN_ROOT` never loads the gate.
3. `SK-32` is `CLOSED_PUBLIC_BYPASS` and chat-apply of manuscript bytes remains
   unsupported. That is a policy statement, not an enforcement point.

**Do not describe this package as protecting prose edited outside its enforcement
points.** Acceptance condition 1 of the work order is met by *naming* this route as
unsupported, not by claiming a gate it does not have.

---

## 2. Reproduced baseline

Reproduced with synthetic prose. No manuscript excerpt from the investigation
record was copied into any distributable fixture.

**Measurement A — work-order reproduction.** `scratch/argument-coherence-20260921/repro.md`,
a four-paragraph synthetic Method section carrying an unused source-status aside
between a premise and its `therefore`, an unpaid research promise, and an
unmarked re-specification of a defined term:

| Layer | Result |
|---|---|
| `scripts/audit/run_all.py` (full deterministic set) | **4 findings, all `PAS-001` passive voice. 0 coherence findings.** |
| `DETERMINISTIC_CHECKS.md` §9a (Check 7 queue) | **0 candidates** across all four marker classes |
| §9b proxies (long-sentence runs, question stacking) | 0 |
| new §9f pre-filter | 4 prose units inventoried, 4 carrying candidate markers |

**Measurement B — seeded golden fixture.** `scripts/fixtures/golden/golden_coherence_defects.md`,
blinded, five seeded defects (one per AC class):

| Layer | Result |
|---|---|
| `scripts/audit/run_all.py` | **4 findings, all `PAS-001` passive voice. 0 coherence findings.** |
| §9a | **0 candidates** |
| §9b proxies | 0 |
| new §9f pre-filter | 11 prose units (the coverage denominator), 4 carrying candidate markers at the D1, D2, D4, and D5 locations |

### 2.1 Per-check disposition of the existing layer

| Existing check | Disposition on this defect class | Why |
|---|---|---|
| `DETERMINISTIC_CHECKS.md` §§2–8 (absolutes, em-dash, LLM tics, sentence focus, length, citation, scope traps) | **misses** | keys on surface tokens and counts; the defective sentences are mechanically clean |
| §9a → SAFEGUARD Check 7 | **misses** | keys on named-author application phrases, If-Then/template co-presence, and `, so X should`; none present |
| §9b/§9d/§9e → SAFEGUARD Check 8 | **misses** | keys on sentence length, definition topology, cognitive load, and register; the fixture is short-sentenced and register-consistent |
| SAFEGUARD Check 3 (abstract ↔ body) | **partially reachable, not invoked** | would reach AC-4 only for promises made in the abstract, and only at `standard`+ depth |
| SAFEGUARD Check 4 (contradiction audit) | **misses** | targets conflicts *between co-invoked sources*, not a term's drift within the document |
| `/sentence-level-pass` (Bacon) | **misses** | judges how a sentence is built; Check 10 semantic-predication is about predication truth, not argumentative contribution |
| `/narrative-structure-pass` (Sexton) | **partially reachable, not invoked** | items 2 and 6 operate at section scale with a ten-item verdict, not paragraph-by-paragraph with a denominator; it is also opt-in |
| `piw_coordinator` required checks | **never invoked** | before this change the defaults were `brief_and_scope`, `grammar`, `grounding`, plus automatic `bibliography` |

### 2.2 Routing defects vs. weak semantic judgment

Separated as the work order requires:

- **Routing defect.** On the conversational route, no independent semantic
  evaluator was invoked on the edited bytes at all. The style-lint probes recorded
  in the investigation record returned `PASS` with empty `review`, `warnings`, and
  `prompts` arrays, and that record itself states the limit: *"Style-lint behavior
  only; this is not a semantic-coherence verdict."* Nothing was judged weakly;
  nothing was judged.
- **Routing defect.** On the `project_independent` route, a coherence obligation
  was not in the required-check set, so a complete, valid run could deliver without
  one. Fixed by `effective_checks`.
- **Weak-judgment risk.** Whether a reviewer that *is* invoked reliably finds these
  defects is a separate question, unresolved here, and the subject of §4.

---

## 3. What the mechanical layer now establishes

`scripts/coherence_review.py` validates that a coherence review:

- is bound to the exact candidate bytes (`candidate_sha256`) and to each covered
  unit's own hash — a replayed or copied review is refused;
- covers every changed prose unit **and its immediate neighbours**, measured
  against the author's original bytes rather than the previous correction;
- covers the whole requested scope when nothing changed, so a no-change run cannot
  discharge the obligation with an empty review;
- partitions each covered unit's text **exactly** into the sentences it reports —
  nothing omitted, reordered, or invented;
- quotes only passages that occur in the candidate, inside covered units;
- states a purpose per unit that is more than a role label;
- carries no finding whose explanation or remedy needs a premise the author never
  made;
- reports an outcome consistent with its blocking findings;
- reports out-of-scope observations without write authority;
- records a user exception as an exception, never as a semantic pass.

**It establishes evidence integrity and coverage. It does not establish semantic
correctness.** `verify_completion` reports
`coherence.semantic_correctness_established: false` on every successful run, and
`coherence_review.validate` returns the same disclaimer in its summary. No surface
in this package may report a passing `argument_coherence` check as evidence that
the prose is coherent.

---

## 4. Evaluation protocol and current status

### 4.1 Mechanical enforcement — measured

`python scripts/argument_coherence_smoketest.py` — **35 cases, 35 pass, 0 fail**
(2026-09-21). It covers the six negative-control classes the work order names:
missing review and incomplete coverage; changed candidate and changed relied-on
context; wrong-run and replayed evidence; reviewer failure (`fail` status,
`not_applicable`, `unavailable`); attempted bypass (narrowed `required_checks`,
`prose_only` scope, explicit exclusion); and misleading completion reports (a
blocking finding reported as `review_complete`, a completion claiming semantic
correctness). It also asserts the positive direction: a valid review clears, a
clean run completes, and completion stays non-terminal.

Registered in `scripts/analysis/fixture_runner.py` `REGISTRY`.

### 4.2 Semantic judgment — **not measured; no baseline recorded**

The fixtures and the scorer are in place; **no detector run has been scored.**
Nothing in this work order establishes that a reviewer executing Check 9 finds
these defects at any rate.

- **Fixtures.** `golden_coherence_defects.md` (5 seeded defects, one per AC class)
  and `golden_coherence_controls.md` (6 positive controls) on the `development`
  split; `heldout_coherence_defects.md` and `heldout_coherence_controls.md` on the
  `held_out` split, in a different domain.
- **Scoring.** `scripts/eval/golden_eval_score.py` accepts the `AC-1`…`AC-5`
  family, requires an exact class **and** an exact blinded source line (no
  substring credit, no credit at a neighbouring paragraph), counts duplicates and
  wrong locations as extra findings, and scores control fixtures against their own
  `gated_families` rather than the P2 list.
- **Splits.** A baseline comparison across splits is refused. The `held_out`
  fixtures have not been scored, and must not be scored during tuning.
- **Verified.** The scoring machinery itself was round-tripped on the development
  split: a perfect finding set scores recall 1.0 with 0 extras; a finding moved two
  lines scores 0.8 with 1 extra; an empty set scores 0.0; a coherence flag on a
  control counts as 1 false positive; a P2-family flag on a coherence control
  counts as 0. Those numbers describe the **scorer**, not any reviewer.

**Contamination limit, stated plainly.** Every fixture here carries
`independently_curated: false`. They were authored in the same session as the
obligation they test, by the same agent. "Held out" therefore means held out from
*tuning*, not from *authorship*. These files bound nothing about generalization to
real manuscripts. **Final held-out qualification requires fixtures curated by the
independent reviewer.**

### 4.3 Thresholds — fixed prospectively, 2026-09-23

Fixed by the review owner, Joseph, on 2026-09-23, **before any semantic run has been
scored** on either split. They are recorded here, and committed, so that the commit
that fixes them predates any number they will judge. Changing them after a scored
run exists makes them a description of that run, and must be reported as such.

| Decision | Fixed value |
|---|---|
| Detection on the held-out defects fixture | Pooled recall **≥ 0.80**, and **every AC class** (AC-1…AC-5) detected |
| False positives on the held-out controls fixture | **At most 1** coherence flag on well-formed prose per run |
| Repeats and how the threshold applies | **n = 3** runs per fixture; each threshold is judged on the **median** of the three runs |
| Inter-rater disagreement | **Report both judgments and the disagreement rate; do not adjudicate** |
| Denominator reporting | Per-defect booleans for every run, plus pooled recall (the earlier proposal, adopted) |

**How the values compose.** With the median rule applied to each threshold separately:

1. the median of the three pooled-recall values is ≥ 0.80;
2. each AC class is detected in **at least 2 of the 3 runs** (the median of that
   class's per-run caught / not-caught outcome);
3. the median false-positive count on the controls fixture is ≤ 1.

Qualification passes only if all three hold. Item 2 is the implementer's reading of
"every class detected" under the median rule, and is marked as a derivation rather
than a decision until the review owner confirms it.

**What every scored report must still give,** whatever the verdict: the missed
defects and the false alarms by name; the denominators; each run's figures and the
min–median–max spread, not only the median; and, where a second reviewer scored the
same runs, both judgments and the disagreement rate.

**Which fixtures these apply to.** The thresholds judge **held-out fixtures curated
by the independent reviewer**. The `heldout_coherence_*` files in this package were
authored by the implementer and carry `independently_curated: false`; a score on
them is not qualification, whatever it is.

**Status.** Thresholds are no longer an open decision. Semantic qualification stays
**held** until an independent reviewer curates held-out fixtures and runs the
scored evaluation against these values.

---

## 5. Outcomes vocabulary

`references/ARGUMENT_COHERENCE.md` §7 fixes three outcomes — *Review incomplete*,
*Changes required*, *Review complete* — and `coherence_review.py` enforces the
consistency between them and the findings. A recorded user exception remains an
exception in every downstream summary.

## 6. Status of this change

| Dimension | Status |
|---|---|
| Source validation | repository structural checks and the affected suites pass; see the return report |
| Independent review | **not performed** — returned for a separately authorized non-Anthropic reviewer |
| Installed-byte identity | **not established** — source-path only; no installed cache was replaced |
| Fresh-task / live-host execution | **not established** — synthetic host traces only (`claude_host_smoketest.py` proves adapter mechanics, not live qualification) |
| Release | **not performed** — no version bump, no packaging, no promotion |
| Semantic qualification | **held** pending independently curated held-out fixtures and an independent scored run; thresholds fixed prospectively 2026-09-23 (section 4.3) |
