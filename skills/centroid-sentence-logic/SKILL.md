---
name: centroid-sentence-logic
user-invocable: true
description: 'Join consecutive manuscript sentences to admitted Yu 2011 and Dennett passages. A missing join-cadence is a miss, not only a missing attested hinge. Invoke-only while the centroid binder packet is GRAPH-SEMANTIC-INELIGIBLE. Does not retrieve from a structural-only graph and does not mint scholarly CLEAN.'
trigger: explicitly when Writer or Reviewer invokes /centroid-sentence-logic after a binding_resolved centroid packet. Auto-run after the binder only once a later packet is semantically eligible. Not dispatched by chat-to-manuscript apply.
version: 1.1
---

# centroid-sentence-logic

**Invoke-only / fail-closed.** Stays invoke-able. Does not auto-dispatch as scholarly CLEAN.

Own skill. Not the binder. `scripts/centroid_service.py` stays a binder.

Joseph is the only R-plane actor. SK-32 stays CLOSED. DEST-PROTECTED stays.

## When to run

After `centroid-pass` emits `status: binding_resolved`. While `reason_code` is `GRAPH-SEMANTIC-INELIGIBLE`, invoke this skill; do not wait for Wiki graph repair.

| Mode | Who | What |
|---|---|---|
| `write` | Writer / Generator | Name the Yu hinge (and Dennett warrant if the pair ascribes intention) before or while drafting the next sentence. Does not write the manuscript. |
| `review` | Reviewer / Evaluator | Mark each pair CLEAN / ADVISORY / BLOCKER with locators. Do not rewrite prose. |
| `revise` | Writer / Generator | Repair only Evaluator-authorized pairs plus F6 items. |

## Invoke

From the harness root:

```
uv run --python 3.11 scripts/centroid_sentence_logic.py --mode review --packet <binder.json> --manuscript <M4.md> --passages <joseph-passages.json>
uv run --python 3.11 scripts/centroid_sentence_logic.py --mode write --packet <binder.json> --manuscript <M4.md> --heading <exact-heading> --admit-pdf <yu-2011.pdf> --pages 3,7,12 --project-root <package> --shipment-id <id>
```

The script carries PEP 723 metadata that pins `pypdf==6.14.2`; `uv run` resolves it in an isolated script environment rather than mutating Hermes Agent's shared venv. `--passages` is Joseph-admitted verbatim excerpts. `--admit-pdf` reads hash-bound PDF pages in the 2011 window (pp. 3-10 and 11-52). Either satisfies the held 2026-08-19 default. Graph retrieval does not.

`--heading` is an exact, case-sensitive ATX Markdown heading and must match the heading scope already bound in the centroid packet. It cannot narrow a full-manuscript packet or retarget a differently bound heading. Before sentence pairing, the instrument removes YAML front matter, Markdown headings/tables/fences, and the full-manuscript References/Bibliography tail; receipts bind both raw scope and filtered prose hashes.

Receipts are JSON (machine) plus a markdown sibling. Default is stdout. Package writes go only to `reviews/.harness/shipments/<id>/` via `--shipment-id`.

## Fail closed

No CLEAN, no manuscript write, no promote, when any of these hold: packet is not `binding_resolved`; manuscript hash mismatch; graph ineligible and no admitted passages; Yu quote outside pp. 3-10 / 11-52; Dennett used as surface register; invented unlocated "Yu says"; `/run-generator-session`.

The instrument lists pairs with `verdict: not_run`. Roles fill verdicts. One BLOCKER pair fails the bound scope for qualification.

Empty binder `semantic_findings` is not a pass.

## Join-cadence

Not the hinge. Not the binder. Do not collapse this into `centroid_service.py`.

`S_{n+1}` must show how the idea was derived from `S_n`. A short unearned verdict (`thus` / `therefore` / `so` / `hence`) is a miss even when an attested Yu hinge is named.

The script may flag `unearned_verdict`, `derivation_shown`, `all_short_stack` (every sentence ≤12 words, at least three sentences), and `needed_backtrack_missing`. Those are mechanical signals. They are not scholarly CLEAN.

Do not require a backtrack on every pair. Flag a missing backtrack only when the next sentence retracts, qualifies, or abandons an open commitment without returning to it.

Keep: no Yu/Dennett voice imitation; Dennett argument-only; Yu 2011 window; C-7 author voice; no CLEAN mint; SK-32 CLOSED.
