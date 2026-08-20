---
name: centroid-sentence-logic
user-invocable: true
description: 'Join consecutive manuscript sentences to admitted Yu 2011 and Dennett passages. Invoke-only while the centroid binder packet is GRAPH-SEMANTIC-INELIGIBLE. Does not retrieve from a structural-only graph and does not mint scholarly CLEAN.'
trigger: explicitly when Writer or Reviewer invokes /centroid-sentence-logic after a binding_resolved centroid packet. Auto-run after the binder only once a later packet is semantically eligible. Not dispatched by chat-to-manuscript apply.
version: 1.0
---

# centroid-sentence-logic

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
python scripts/centroid_sentence_logic.py --mode review --packet <binder.json> --manuscript <M4.md> --passages <joseph-passages.json>
python scripts/centroid_sentence_logic.py --mode write --packet <binder.json> --manuscript <M4.md> --admit-pdf <yu-2011.pdf> --pages 3,7,12 --project-root <package> --shipment-id <id>
```

`--passages` is Joseph-admitted verbatim excerpts. `--admit-pdf` reads hash-bound PDF pages in the 2011 window (pp. 3-10 and 11-52). Either satisfies the held 2026-08-19 default. Graph retrieval does not.

Receipts are JSON (machine) plus a markdown sibling. Default is stdout. Package writes go only to `reviews/.harness/shipments/<id>/` via `--shipment-id`.

## Fail closed

No CLEAN, no manuscript write, no promote, when any of these hold: packet is not `binding_resolved`; manuscript hash mismatch; graph ineligible and no admitted passages; Yu quote outside pp. 3-10 / 11-52; Dennett used as surface register; invented unlocated "Yu says"; `/run-generator-session`.

The instrument lists pairs with `verdict: not_run`. Roles fill verdicts. One BLOCKER pair fails the bound scope for qualification.

Empty binder `semantic_findings` is not a pass.
