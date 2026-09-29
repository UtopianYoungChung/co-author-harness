---
name: run-fast
description: 'Fast lane for a short deliverable (a course memo, an outline, a bounded section): one Generator child, one distinct Evaluator child, a two-file reading list, a mechanical citation gate at delivery, and an uncertified receipt. Not for governed milestones.'
trigger: 'when the user says "/run-fast," "fast draft," "quick memo," or "draft the M1 memo quickly"'
version: 0.51.0
user-invocable: true
---

# run-fast

> **Package paths.** `${CLAUDE_PLUGIN_ROOT}` is the installed package root; Claude Code fills it in. The `references/…` and `scripts/…` paths in this skill resolve against that root, not against this skill's own directory. On hosts that do not fill it in (Codex, a source checkout), use the package directory that contains `version.json`.

`/run-fast` drafts or revises a short deliverable in two child dispatches and a few
minutes. The output is an **uncertified working draft with a review record**. It grants
no lifecycle, acceptance or scholarly CLEAN authority. M4, the final paper and any
governed milestone go through `/run-draft`, `/run-iterate` and `/run-finalize`.

What stays fixed: no fabrication (gaps are marked `[FACT NEEDED]` or
`[CONCRETE EXAMPLE NEEDED]`), every citation resolves (checked by the script at
delivery), the writer and the reviewer are distinct child contexts, and the delivered
bytes are exactly the reviewed candidate bytes. The children read only
`GROUNDING_PROTOCOL.md`, `CITATION_DISCIPLINE.md` and the rule files of a pass the user
asked for. Shared runbook: `references/PROJECT_INDEPENDENT_WORKFLOW.md` (Fast lane).

Run `python "${CLAUDE_PLUGIN_ROOT}/scripts/fast_lane.py" <command>`. Each command prints one
JSON object and exits 0, or 4 with a `code`. Report a refusal code as it is; never edit
`binding.json`, `state.json`, a request or the receipt, and never write the candidate or
the findings yourself.

1. `open --task-root <task area> --brief <brief.md> [--input <manuscript>] [--pass <name> ...] [--exclude <name> ...] [--max-corrections N]`.
   Keep the `session_path` it prints as `<session>`. A brief or flag that claims lifecycle,
   promotion, acceptance or `full_lifecycle` is refused with `FAST-NON-TERMINAL`.
2. `request --session <session> --role generator`. Keep its `request_path`.
3. Dispatch ONE general-purpose subagent (model sonnet). Its prompt is `run_scope: project_independent`
   on its own line, then "Read the request at <request_path> and follow it exactly", and nothing
   else. Wait for it to finish and keep the agent id the host reports.
4. `record --session <session> --role generator --child-id <agent id> --child-model sonnet`.
5. `request --session <session> --role evaluator`. Keep its `request_path`.
6. Dispatch a DIFFERENT general-purpose subagent (model sonnet) with the same kind of prompt for the
   evaluator request, wait, and keep its agent id. Reusing the Generator's agent id is refused
   (`FAST-ROLE-DISTINCT`).
7. `record --session <session> --role evaluator --child-id <agent id> --child-model sonnet`. If the
   status is `awaiting_generator` (a blocking verdict with a correction left), repeat from step 2.
   If it is `needs_revision`, report the blocking lines and stop; do not deliver.
8. `deliver --session <session> --destination <new output file>`. Report the destination, the
   verdict, the corrections used, the advisory lines and the limits in the receipt.

Delivery is refused unless the last Evaluator record is later than the last Generator record
and its verdict is clear, and the candidate passes the citation inventory. Unsupported citation
syntax (LaTeX, Pandoc, footnotes) passes only when the author's input holds at least as much of
it; the bibliography is then unverified, not cleared. The destination may not be the input file
or a file in the session folder.

When the host sets `FRC_PARENT_SCOPE=project_independent` without `FRC_PIW_SESSION`, also set
`FRC_FAST_SESSION=<session>` so the children may write their candidate and findings under
`<session folder>/draft/` and `<session folder>/review/`.

Child ids are recorded as the host declares them and are not verified against host logs. A
run that needs verified execution evidence, a reflection, or a completion record uses
`/run-draft` or `/run-iterate`.
