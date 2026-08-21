---
name: run-generator-session
user-invocable: false
description: CLOSED public bypass (CLOSED_PUBLIC_BYPASS). Do not write manuscript from chat. Route to /run-draft or /run-iterate.
trigger: refuse /run-generator-session and chat-apply requests. Zero manuscript bytes from this skill.
version: 1.2
---

# run-generator-session -- closed as a chat-to-manuscript bypass

This skill is not a public write path. Chat is not authority. Classification plus phase_state.json presence is not enough. Evaluator findings and F6 are not enough. CLOSED_PUBLIC_BYPASS.

Closed output economy: this skill does not emit `role_output_contract.json` or shipment-v2 receipts. It produces **zero** manuscript bytes and **zero** revision-log bytes. It does not call `assignment_writer_commit.py`.

## Unconditional refuse

Do not write, stage, or apply manuscript files. Do not write `manuscript/revision_log.md`. Route to `/run-draft` or `/run-iterate` so Planner can collect F6 and Evaluator can publish findings. Generator publication, if any, happens only under those coordinators via `assignment_writer_commit.py`.

## You must not

- Rewrite manuscript from session chat, with or without findings on disk.
- Treat Evaluator findings or an F6 signature as a license for this skill to write.
- Skip `/run-draft` or `/run-iterate` because the user asked to apply what was agreed.
- Treat this skill as a public slash command.
