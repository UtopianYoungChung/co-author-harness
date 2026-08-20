---
name: run-generator-session
user-invocable: false
description: CLOSED public bypass (CLOSED_PUBLIC_BYPASS). Do not write manuscript from chat without Evaluator findings and F6 approval.
trigger: refuse /run-generator-session and chat-apply requests unless Evaluator findings and F6 are on disk
version: 1.1
---

# run-generator-session -- closed as a chat-to-manuscript bypass

This skill is not a public write path. Chat is not authority. Classification plus phase_state.json presence is not enough.

Do not write manuscript files unless every hard stop below passes.

## Hard stops all required

If any check fails: no writes. Route to /run-draft or /run-iterate so Planner can collect F6 and Evaluator can publish findings.

1. reviews/classification.md exists.
2. reviews/phase_state.json exists and has a section entry for the named target.
3. Evaluator findings for that section exist on disk: F7 packet or reviews/step_findings covering the target. A chat summary is not findings.
4. F6 is approved: reviews/dispatch_plan_<cycle_id>.md exists and user_approval_signature is populated, not empty and not null. I-Planner-10.
5. Generator may apply only Evaluator-authorized fixes plus F6-listed items that do not add argument beyond those findings. Chat cannot introduce new claims.

## If all hard stops pass

Obey agents/generator.md for the declared current_phase. Write only manuscript files and manuscript/revision_log.md. Do not write reviews. Chat is not evidence for facts.

## You must not

- Rewrite manuscript from session chat alone.
- Skip Evaluator or F6 because the user asked to apply what was agreed.
- Treat this skill as a public slash command. Use /run-draft, /run-iterate, or /run-finalize.
