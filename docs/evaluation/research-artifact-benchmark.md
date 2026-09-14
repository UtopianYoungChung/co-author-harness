# Research artifact benchmark

The benchmark covers the six promised outputs: project memo, annotated synthesis,
argument/evidence outline, sourced draft, bounded revision and final review. Its
synthetic source packet includes conceptual reasoning, small pilot observations,
different outcome measures, missing evidence and a legitimate unresolved question.
The revision includes protected wording and sections. Source files live in
`scripts/fixtures/research_artifacts/`; they are test inputs, never source admission.

## Running and recording an assessment

1. Prepare a case with `python scripts/eval/research_artifact_eval.py prepare --case memo`.
   Save the returned packet and its digest in an authorized output directory.
   Dispatch only that packet and the applicable native workflow instructions to
   the producer. Withhold the manifest's checks and any adjudicated reference
   judgments from the producer. The investigator and reviewer receive the actual
   source packet; blinding must not hide evidence needed to assess the work.
2. Run the real native task workflow using the inherited host/model settings.
   Retain source/package identity, exact output bytes, the PIW completion proof,
   all role requests/results and original trace prefixes. Fixture-generated role
   logs are useful validator tests and never observed cognitive benchmark runs.
3. Record an independent human assessment against the six dimensions in the
   manifest. Every score needs a reason and an artifact locator. Read the whole
   artifact: explain its problem-to-contribution path and whether a reader can
   recover the argument. Mechanical citation and word counts cannot replace this.
   Keep the original assessment and its SHA-256 separately. A declared human name
   alone is not authentication; the caller must know who supplied the assessment.
4. Score the bound artifact and assessment with the read-only scoring command.
   A case meets its thresholds only if every dimension is at least 3/4 and there
   are no critical failures. Missing adjudication reports an unqualified
   measurement; it cannot produce a passed research-quality result.
5. Establish the initial human-adjudicated baseline, then repeat every case at
   least three times per advertised host. Compare the same case, source bytes,
   rubric, package and evaluator configuration. Report each run and variation;
   do not hide failures in an average. Human disagreements need a retained
   adjudication record. Qualification requires the complete case/host matrix;
   one passed case cannot qualify a host or the harness.

## Timing and stability

The score command is `python scripts/eval/research_artifact_eval.py score
--submission <submission.json> --adjudication <human-review.json>
--adjudication-sha256 <separately-retained-hash>`. A submission records `case`,
`packet_sha256`, `artifact: {path, sha256, bytes}`, `execution_kind` (`live_host`
or `synthetic_fixture`) and `host: {adapter, model, configuration}`. Retain the
actual native completion evidence alongside it; these declarations cannot
authenticate execution. The human review records `case`, `artifact_sha256`,
`reviewer: {kind: human, identity}`, `critical_failures` and one `scores` entry per
manifest dimension, each with `value`, `rationale` and `locators`. Its digest is of
the actual review file bytes. The scorer checks binding and reported thresholds;
it does not read prose as a human or confer overall qualification.

Run `python scripts/piw_metrics.py --piw-session <session>` for verified role
durations, time to first candidate, time to last reviewed role, correction cycles
and trace sizes. These measurements do not count unrecorded failures or infer
missing token usage. Record unavailable usage as null, and collect native host
usage separately when available. Compare repeated identical cases before claiming
an end-to-end latency improvement. The prefix-read regression test establishes
bounded I/O as later log history grows; it does not establish faster writing.

## Current evidence boundary

The manifest starts with no observed baseline and no research-quality qualification.
Installing the runner, passing synthetic tests or providing numeric ratings does
not fill that gap. A human-adjudicated reference set and repeated live runs remain
required. Benchmark results grant no research acceptance, publication, lifecycle
completion, distribution release or model-selection authority.
