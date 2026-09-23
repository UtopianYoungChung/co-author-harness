# Independent review: argument coherence in the co-author harness

You are the **independent reviewer** for a completed work order in the co-author
harness, a research-writing plugin. The implementation was written by an Anthropic
model (Claude). You were chosen because you are **not** one. If you are an Anthropic
model, stop and say so: this review would not be independent.

Your job has two parts, and they are reported separately:

1. **Source review** of the implementation.
2. **Held-out qualification**: curate your own test fixtures, run the harness's
   judgment layer on them blind, and score the result against thresholds that
   were fixed before any run was scored.

Treat every claim in this prompt as something to check. It was written by the
implementer. Where this prompt and the repository disagree, the repository wins,
and the disagreement is a finding.

---

## What the work order asked for

The harness reviews academic prose. It could not catch prose that is fluent,
grammatical, on topic and well cited, yet does no argumentative work: a sentence
that does not advance its paragraph, or a paragraph that does not advance the
document. Before the change, on a synthetic section carrying three such defects,
the full mechanical check set returned four passive-voice findings and **zero**
coherence findings. On the conversational route, no semantic check ran at all.

The work order required the fix to:

- **extend existing controls**, not add an overlapping optional skill;
- keep **factual support**, **argumentative relevance**, and **document-level
  continuity** distinct;
- change **no** model settings, providers, profiles, credentials, or subagent model
  assignments;
- stay on `main`, preserve unrelated work, and exclude installation, cache
  replacement, release, promotion, and workspace-wide governance changes;
- treat the research manuscript as read-only and copy no private manuscript text
  into distributable fixtures;
- leave final held-out qualification to you.

## Where the work is

- **Repository:** <https://github.com/UtopianYoungChung/co-author-harness> (public;
  `git clone https://github.com/UtopianYoungChung/co-author-harness.git`). If you
  are working on the owner's machine, the owner will point you to the local checkout.
- **The implementer's commits**, in order: `51e6349` `0ea1f69` `178c419` `c4e7f5c`
  `8f2a4f5` `fee200d` `69197b3` `e94d6f3` `35e1982` `3424638`.
- **Other commits are interleaved** in that range. A separate session committed work
  on `scripts/citation_gate/` and distribution snapshots under `.claude-plugin/`.
  Those are **out of scope**. The two sets touch disjoint paths, so this command
  shows exactly the implementer's change (54 files):

  ```
  git diff 51e6349~1 3424638 -- . ':(exclude)scripts/citation_gate' ':(exclude).claude-plugin'
  ```

  Verify that disjointness yourself before relying on it.

**Start with these files:**

| File | Role |
|---|---|
| `references/ARGUMENT_COHERENCE.md` | The single obligation: what is checked, what is not, defect classes AC-1 to AC-5, positive controls, the route table |
| `references/SAFEGUARD_LAYER.md` (Check 9), `references/DETERMINISTIC_CHECKS.md` (§9f) | The judgment check and its mechanical pre-filter |
| `scripts/coherence_prefilter.py` | Lists the prose units, sets the coverage denominator, flags lexical markers; must never emit a verdict |
| `scripts/coherence_review.py` | Validates review evidence; stable `COHERENCE-*` error codes |
| `scripts/piw_coordinator.py`, `scripts/piw_completion_guard.py` | The required-check gate and the completion gate |
| `scripts/scholarly_evaluation.py` | `PROFILE_MINIMUM["argument_coherence"]` on the governed route |
| `scripts/argument_coherence_smoketest.py` | 35 unit and route controls |
| `docs/evaluation/argument-coherence-baseline.md` | The reproduced baseline, the evaluation protocol, and the fixed thresholds (§4.3) |

## Part 1: source review

Try to break it rather than confirm it. At minimum:

1. **Bypass.** Can `argument_coherence` be dropped from the coordinator's required
   checks, narrowed away by scope (`prose_only`), excluded, or satisfied by a
   reviewer status of `not_applicable` or `unavailable`?
2. **Stale or replayed evidence.** Does a review of different bytes, a different
   run, or a changed neighbouring unit ever clear? Required coverage is every
   changed prose unit **and its immediate neighbours**, measured against the
   original bytes.
3. **Coverage gaming.** Can a review satisfy coverage while splitting or merging
   units differently from the inventory, or while leaving sentences unexamined?
4. **Misleading completion.** Can a run report `review_complete` while carrying a
   blocking finding, or claim semantic correctness? The completion guard's
   `coherence` block is supposed to carry `semantic_correctness_established: false`
   on every run (`scripts/piw_completion_guard.py`).
5. **Scope of the obligation.** Does `ARGUMENT_COHERENCE.md` keep factual support,
   argumentative relevance, and document-level continuity separate? Do its positive
   controls (implicit transitions, legitimate background, qualifications,
   counterarguments, authorial voice) stop it turning into a signposting rule?
6. **Honest routing.** Conversational manuscript application is declared
   **unsupported**, with no coherence enforcement. Check that no document claims a
   gate there.
7. **The two maintenance commits.** `178c419` cut a shared Reflector snippet from
   1578 to 1463 tokens to meet its budget: check that no doctrine was lost.
   `c4e7f5c` rebound a detector freeze after re-scoring both splits: check that
   held-out discipline was preserved and that scores were identical before the
   rebind.
8. **Constraints.** Confirm from the diff that no model, provider, profile,
   credential, or subagent-assignment setting changed, and that nothing was
   installed, versioned for release, or promoted.

## Part 2: held-out qualification

### The fixtures must be yours

The package ships four coherence fixtures (`golden_coherence_*`, `heldout_coherence_*`).
**All four were written by the implementer** and carry `independently_curated: false`.
They do not count toward qualification. **Disclosure:** on 2026-09-23, while
preparing this handoff, the implementer's tooling printed the manifest entry of
`heldout_coherence_defects.md` (its defect lines and classes). That is a further
reason those files cannot qualify anything.

Write your own defect fixture and control fixture:

- Use a domain and prose of your own. **Do not use text from the owner's research
  manuscripts.**
- **Defects:** seed at least one instance of each class, AC-1 to AC-5, as defined in
  `references/ARGUMENT_COHERENCE.md` §3. Mark each defect with an HTML comment on
  or near its line.
- **Controls:** well-formed prose of the kinds the obligation lists as positive
  controls (§4). A coherence flag on any of it is a false positive.
- Place both files in `scripts/fixtures/golden/`. The scorer only accepts registered
  files in that directory. Register them in `scripts/fixtures/golden/manifest.json`
  under `fixtures`, following an existing coherence entry's shape, with
  `"split": "held_out"` and `"independently_curated": true`. A defects fixture's
  entry has `"role": "detection"` and a `defects` list; each defect carries
  `defect_id`, `expected_code_family`, `expected_severity`, and a one-based `line`
  in the comment-stripped file. A controls fixture's entry has
  `"role": "false-positive-control"`, `gated_families`, and a `controls` list whose
  items carry `control_id`, `description`, `location_hint`, and `must_not_fire`.
  Copy the shape of `heldout_coherence_controls.md`'s entry
  rather than trusting this summary.

**Keep your fixtures away from the implementer.** Work in your own clone or a
detached worktree, and do not push them to `main` or show them to any Claude
session before qualification is complete. A future implementer session that reads
them would contaminate the held-out set. **The repository is public**, so anything
pushed to it, on any branch or fork, is readable by anyone, including any model
that can browse. Keep the fixtures local until the owner decides where they go.

### Running the judgment layer

There is **no automated runner**, and no scored run has ever been recorded
(`baseline_runs` in the manifest is empty). A scored run is produced by hand:

1. **Blind the fixture:**
   `python scripts/eval/golden_eval_score.py --blind-fixture <your_fixture>.md`
   prints the file with every HTML comment removed and line numbers preserved.
   Show the evaluator **only** these bytes. Telling it to ignore comments is not
   enough; the markers must be gone.
2. **Run the harness's Evaluator executing SAFEGUARD Check 9** on the blinded text.
   This is the subject under test, and in normal operation it runs on Claude. That
   is expected: you are independent as the curator, operator and scorer, and the
   harness's judgment is what is being measured. Run it from the **source at the
   commit you reviewed**. If your host can only run an installed copy of the
   plugin, **stop and ask the owner**. Installation was excluded from this work
   order and needs separate authorization, and an installed copy must first be
   shown byte-identical to the reviewed source.
3. **Transcribe the findings** into a JSON file:

   ```json
   {
     "fixture": "<your_fixture>.md",
     "pass": "<the evaluator and pass that produced these findings>",
     "evaluator": {"host": "...", "model": "...", "configuration": "..."},
     "findings": [
       {"finding_code": "AC-2", "severity": "MAJOR", "line": 28, "location_hint": "..."}
     ]
   }
   ```

   `severity` is `BLOCKER`, `MAJOR`, or `MINOR`. `line` must point at a non-empty
   line of the blinded text. Record the real model, host, and settings in
   `evaluator`, and do not change the harness's model assignments to get a
   different one.
4. **Score:** `python scripts/eval/golden_eval_score.py findings.json`. A finding
   counts only with the **exact AC class on the exact line**. There is no credit for
   a neighbouring line or a near class, and duplicates count as extra findings.

Do this **three times per fixture**, each run fresh.

### The thresholds are fixed

The review owner fixed these on 2026-09-23, before any semantic run was scored, in
commits `35e1982` and `3424638` (see `docs/evaluation/argument-coherence-baseline.md`
§4.3). **Do not change them, and do not re-grade after seeing numbers.** If you
think they are wrong, say so in a separate section; the verdict still uses them.

Qualification passes only if **all three** hold:

1. the **median** pooled recall across the three runs on your defects fixture is
   **≥ 0.80**;
2. **every** AC class (AC-1 to AC-5) is detected in **at least 2 of the 3 runs**;
3. the **median** number of false positives on your controls fixture is **≤ 1**.

If a second independent reviewer also scores the runs, report both judgments and
the disagreement rate. **Do not adjudicate** between them.

## Known conditions: do not spend time rediscovering these

- **Run the test registry in a tree nothing else writes to.** Another session commits
  to this repository. Use a detached worktree at the commit under review:
  `git worktree add --detach <path> <commit>`, then
  `python scripts/analysis/fixture_runner.py --no-write` inside it. A result of
  `REGISTRY_EXIT=2` with 0 failures means the files changed during the run, not
  that a test failed. See `docs/evaluation/fixture-runner-tree-mutation.md`.
- **The implementer's last full run:** at `a4272dd` on 2026-09-23, **114 of 114 cases
  passed** (`REGISTRY_EXIT=0`), with the tested-inputs hash `cf67dad97154` over 846
  files identical before and after the run. That commit contains the whole work
  order, including the thresholds and an earlier version of this prompt.
- **One known intermittent failure:**
  `release_qualification_controller_smoketest::fixture-owner` hits a Windows file lock
  (WinError 32). It failed in 2 of 5 full runs, both at `e94d6f3`, where the result was
  113 of 114. It passed 6 of 6 in isolation and passed in the `a4272dd` run. No
  implementer commit touches that suite or its subject. Confirm or refute that
  attribution; do not assume it.
- **The full registry takes about 2 hours** (1 h 44 min to 2 h 7 min across the last
  four runs). `scholarly_evaluation_smoketest` alone takes about 15 minutes.
- The repository requires **LF** line endings (`.gitattributes`). Do not rewrite line
  endings by hand.

## What you may not do

- Modify the implementation, push to `main`, or open changes against it. Report
  defects; do not fix them.
- Install, version, package, release, or promote anything.
- Read, copy from, or modify the owner's research manuscripts, or any file outside
  this repository.
- Show your fixtures or intermediate scores to any Claude session before you finish.

## Your report

Report each of these on its own line. Never fold one into another:

| Line | Values |
|---|---|
| Source review | `approved` / `changes required` / `not completed` |
| Held-out qualification | `pass` / `fail` / `not run` (and why) |
| Installed-byte identity | `not established` unless you established it |
| Fresh-task execution | `not established` unless you ran one |
| Release | `not performed` |

Then give:

1. **Source findings**, most severe first. For each: severity (`BLOCKER`, `MAJOR`,
   `MINOR`), `file:line`, what is wrong, a concrete input or state that shows it, and
   what it would take to fix. Say which of the eight Part 1 checks you completed,
   and which you did not.
2. **Qualification figures**, for every run, not only the median:
   - per-defect caught / missed, and pooled recall;
   - per-class detection counts across the three runs;
   - false positives on the controls, by line;
   - the min, median, and max of each quantity;
   - the evaluator identity (host, model, configuration) and the execution route
     (source path or installed copy).
3. **Your fixtures:** file names and their sha256, so the owner can later confirm the
   runs used exactly these bytes.
4. **Anything in this prompt that the repository contradicts.**
5. **What you did not check**, stated plainly.
