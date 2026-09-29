---
name: centroid-sentence-logic
user-invocable: true
disable-model-invocation: true
description: 'centroid-check: prepare scoped sentence pairs against admitted Yu 2011 and Dennett evidence, then validate a separately produced review. Binds exact manuscript and source bytes. No automatic scholarly CLEAN.'
trigger: Explicit /centroid-sentence-logic after a binding_resolved centroid-bind packet. Requires admitted evidence and a valid capability state. Dormant bindings never become eligible through an override. Not dispatched by chat-to-manuscript apply.
version: 2.0
---

# centroid-sentence-logic (instrument: centroid-check)

> **Package paths.** `${CLAUDE_PLUGIN_ROOT}` is the installed package root; Claude Code fills it in. On other hosts use the directory containing `version.json`. Resolve the paths below against that package root.

This invoke-only skill prepares a scoped review and checks its completed record.
The **centroid-source** remains policy member `yu-et-al-2011-social-modeling`,
limited to Yu-authored book pp. 3-10 and 11-52. **centroid-bind** remains the
packet from `/centroid-pass`. **centroid-check** evaluates named manuscript
bytes against admitted evidence; changing the manuscript never moves the source.

## Preconditions

Read the [Grounding Protocol](../../references/GROUNDING_PROTOCOL.md) and the
[review procedure](../../docs/specs/centroid-check-review.md). The packet must
bind the exact manuscript and scope. A requested heading must equal the bound
heading; missing, ambiguous, or stale scopes refuse.

`GRAPH-SEMANTIC-INELIGIBLE` permits preparation only with explicitly admitted
excerpts or validated canonical extraction evidence. A dormant
`SEMANTIC_USAGE_NOT_INVOKED` packet refuses this semantic check. `--allow-eligible`
only permits a packet whose eligible policy and provenance can be revalidated;
it does not make dormant, unknown, or unavailable states eligible.

## Prepare

For person-admitted passages:

```text
python "${CLAUDE_PLUGIN_ROOT}/scripts/centroid_sentence_logic.py" --mode review --packet <binder.json> --manuscript <named.md> --passages <admitted-passages.json> --format review
```

Each passage names its source key, complete printed-page locator, quote, warrant
layer, and admitting person. `--admitted-by` can supply the person when a row
omits that field. These are recorded as human attestations; a name or a quote
hash does not independently verify the quotation. Every page in a range or list
must be allowed. Unknown sources and malformed entries refuse.

For already extracted PDF evidence:

```text
python "${CLAUDE_PLUGIN_ROOT}/scripts/centroid_sentence_logic.py" --mode review --packet <binder.json> --manuscript <named.md> --admit-pdf <yu-2011.pdf> --pages 3,7,12 --extract-receipt <canonical-extract.json> --evidence-root <extraction-project-root> --wiki-root <wiki-root> --format review
```

The PDF must match the live policy's pinned source identity. The checker consumes
and validates an existing `scripts/source_extract.py` receipt, normalized text,
and page map; it never re-extracts the PDF. `--pages` names printed book pages,
not PDF indices. Ambiguous or absent folios refuse. An unpinned source or an
alternate edition needs explicit source admission; it cannot acquire the known
identity by supplying a source key.

Use default JSON output to save preparation evidence. `--format review` is a
compact view for the reviewing model. Artifact output remains restricted by
`destination_capability.py`: use `--project-root` and `--shipment-id` for the
exact authorized `reviews/harness/shipments/<id>/` lane. A write returns a
summary and artifact paths rather than repeating the whole receipt.

## Review

The strongest available model at maximum supported effort performs planning,
orchestration, and semantic review under
[MODEL_ALLOCATION.md](../../references/MODEL_ALLOCATION.md). Lower models may
execute bounded extraction, indexing, formatting, and tests. Keep the required
Generator/Evaluator role separation.

| Mode | Role | Work |
| --- | --- | --- |
| `write` | Generator | Identify the attested Yu join and any Dennett argument warrant before drafting. |
| `review` | Evaluator | Judge every prepared pair in its paragraph and relevant earlier context. |
| `revise` | Generator | Repair only Evaluator-authorized pairs and applicable F6 items. |

Prepared pairs have `verdict: not_run`. The Evaluator supplies carry, hinge,
attestation, scope, voice, role-split, and join-cadence judgments with rationales,
passage IDs, paragraph purpose, derivation, and warrant limits. A lexical
`derivation_cue_present` is only a signal. `unearned_verdict`, short-stack, and
backtrack signals also require judgment. A backtrack is not required on every
pair. Preserve the author's voice; Dennett is argument-only, never a surface
register or imitation target.

## Validate and calibrate

The orchestrator records the actual reviewer assignment and preparation hash.
The Evaluator returns a separate completed-review JSON record. Then run:

```text
python "${CLAUDE_PLUGIN_ROOT}/scripts/centroid_review.py" validate --prepared <prepared.json> --review <completed.json> --request <request.json>
```

The validator replays preparation, checks complete pair coverage, current
bindings, passage references, verdict counts, and the assigned reviewer identity,
model, and effort. One BLOCKER remains a blocker for the bound scope. The result
checks structure and freshness; it neither authenticates a host execution nor
proves semantic correctness or research acceptance. No scholarly CLEAN is minted
by preparation, empty binder findings, or this structural validation.

Use the [calibration template](../../references/templates/centroid_calibration.json)
and `centroid_review.py calibrate` to measure author-labelled judgments and
observed timing/token costs. The supplied cases are unlabelled synthetic prompts;
never present model-generated labels as author judgments.

SK-32 remains CLOSED. This skill does not write manuscript prose, mutate the
Wiki, promote artifacts, or bypass protected destinations. Binding/source/role
failures remain refusals, and governed lifecycle requirements remain separate.
