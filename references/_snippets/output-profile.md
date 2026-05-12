Default profile: `silent_evidence`.

Human-facing output during this phase is limited to:

- the manuscript delta or action list the user must approve;
- phase gate decisions;
- exception reports for blockers, verifier failures, stale state, or unsafe edits.

All routine check details are written to `reviews/.harness/evidence/<event_id>.json` (append `reviews/.harness/events.jsonl`) and summarized only in the final round report. Use `round_id` / `event_id` per `references/OUTPUT_ECONOMY_PROTOCOL.md`.
