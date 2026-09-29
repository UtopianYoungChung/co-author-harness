# Preparing and validating a centroid review

The binder identifies the manuscript, scope, policy, and capability state. The
sentence checker prepares source-bound review units. The assigned Evaluator
performs the semantic review. Each step has its own evidence; a prepared packet
or a successful structural validator does not establish scholarly correctness.

## Prepare the review

Run `scripts/centroid_service.py` on the exact manuscript and optional heading.
Then pass the resulting packet and the same manuscript to
`scripts/centroid_sentence_logic.py`. A requested heading must match the bound
heading and its bytes. Headings, references, tables, and code are excluded from
the sentence inventory. Each prose sentence retains its original byte and line
locations; pairs refer to sentence IDs rather than repeating the text.

For explicitly author-admitted excerpts, supply `--passages` JSON. Each entry
names its source, complete printed-page locator, exact quote, warrant layer,
and admitting person. These are recorded as human attestations. A supplied name
or quote hash is not independent verification that a source contains the quote.

For PDF evidence, supply `--admit-pdf`, `--pages`, `--extract-receipt`, and
`--evidence-root`, and `--wiki-root`. The PDF must match its policy member's pinned identity. The
checker consumes an existing canonical extraction receipt from
`scripts/source_extract.py`, validates the source, normalized text, page map,
extractor identity, and publication, and reuses the extracted text. It does not
re-extract the PDF. An alternate or unpinned version requires explicit source
admission; assigning the known source key to a different PDF is refused.

`--pages` and excerpt locators use printed pages. All pages in a range or list
must be admitted. A page identity/index, ambiguous folio, or numeric heading
does not establish printed pagination.

Use `--format review` for the compact review view. Keep the JSON preparation
receipt for validation. Existing prepared receipts must be regenerated after
changes to the manuscript, relevant context, sources, policy, or checker.

## Assign and perform the review

The strongest available model at its maximum supported effort performs planning,
orchestration, and review under [MODEL_ALLOCATION.md](../../references/MODEL_ALLOCATION.md).
Lower models may execute bounded extraction, indexing, formatting, and tests.

The orchestrator records a request with this shape, using the actual preparation
file hash and observed model/effort identifiers:

```json
{
  "schema_version": "1.0.0",
  "request_type": "centroid_review_request",
  "prepared_sha256": "<sha256 of prepared JSON bytes>",
  "reviewer": {
    "actor_id": "<assigned Evaluator execution>",
    "dispatch_id": "<dispatch identity>",
    "model": "<resolved model identifier>",
    "effort": "<maximum supported effort>"
  },
  "model_requirement": {
    "model": "<required strongest model identifier>",
    "effort": "<required maximum effort>"
  },
  "generation_actor_id": null
}
```

Set `generation_actor_id` when the reviewed text has a known Generator execution.
The Evaluator must be a distinct actor. For text supplied by the author, the field
may be null. The orchestrator's identity/model declarations are inputs to the
validator; authenticating native execution remains the host workflow's job.

The Evaluator produces a separate record conforming to
[centroid_completed_review.schema.json](../../references/schemas/centroid_completed_review.schema.json).
It binds the preparation and request file hashes and supplies exactly one verdict
for every prepared pair. Each verdict records the checks, attesting passage IDs,
paragraph purpose, derivation, and warrant limits. Read the pair in its paragraph
and relevant earlier context. A lexical `derivation_cue_present` signal alone
does not show that a derivation is sound.

If no admitted passage attests a pair, leave its passage IDs empty, mark
attestation as an issue and the verdict as BLOCKER, and record the source gap.
Never attach an unrelated passage merely to fill a required field.

## Validate the completed record

```text
python scripts/centroid_review.py validate --prepared <prepared.json> --review <completed.json> --request <request.json>
```

The command replays preparation and checks current source/manuscript/policy
bindings, complete pair coverage, passage references, reviewer allocation,
preparation-module hashes, check dispositions, and verdict counts. Missing pairs, unresolved verdicts,
stale context, a lower model/effort than assigned, or a CLEAN verdict containing
an issue are refused. A BLOCKER or unresolved source gap remains visible in the
returned `bound_scope_has_blockers` field.

`review_validated` means the supplied record is structurally complete and its
bindings replay. It does not authenticate host execution, verify the truth of
semantic judgments, grant research acceptance, or substitute for lifecycle gates.
Keep the JSON result with the review evidence in the authorized output lane.

## Measure quality and cost

Start from [centroid_calibration.json](../../references/templates/centroid_calibration.json).
It contains unlabelled synthetic prompts, not author judgments or source quotes.
Have the author label the cases before scoring author agreement. Preserve the
label record and its hash; do not derive expected labels from model predictions.

Predictions contain `cases`, with each row naming `id`, `text_sha256`, and
`verdict`. Optional `latency_ms`, `input_tokens`, and `output_tokens` fields
record observed measurements. Omitted measurements remain unmeasured.

```text
python scripts/centroid_review.py calibrate --labels <labelled-cases.json> --predictions <predictions.json>
```

The result separates false clearances, missed blockers, and false alarms, and
reports the confusion matrix, agreement, and available timing/token observations.
Synthetic labels can test the scoring code but do not measure author agreement.
Preserve changes in meaning and voice as explicit review findings; a lower token
count or cleaner mechanical score does not establish improved prose.
