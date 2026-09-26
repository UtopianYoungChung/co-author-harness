# Claude Code / Claude Desktop host integration

Claude Code (CLI, Claude Desktop Code tab, Cowork, Agent SDK) loads this package
from `.claude-plugin/plugin.json` and exposes every public skill and the four
role agents under the `co-author-harness:` namespace. The adapter described here
is the native-host boundary those sessions use for ordinary drafting and
revision under `PROJECT_INDEPENDENT_WORKFLOW.md`. Read-only passes never need it.

## Where the original traces live

Claude Code keeps one JSONL per session in its project log root
(`~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`) and one JSONL per native
subagent at `<session-id>/subagents/agent-<agentId>.jsonl` beside it, with an
`agent-<agentId>.meta.json` naming the dispatching `toolUseId`. The parent log
records the `Agent` (or legacy `Task`) `tool_use` block that dispatched the child
and the `tool_result` row whose `toolUseResult` carries `status`, `agentId`, and
the child's final message. Those files are the trust boundary; the plugin never
writes them and never accepts a self-written receipt in their place.

## Host object

```json
{"adapter": "claude-code-jsonl", "subagents_available": true,
 "logs_root": "<project log root>", "parent_log": "<logs_root>/<session-id>.jsonl"}
```

`parent_execution_id` is derived from the log's single `sessionId`; a declared
value must match it. `subagents_available` must be the observed boolean: the
session actually has the Agent tool. Unknown or false is refused with
`PIW-HOST-CAPABILITY-UNAVAILABLE`; read-only passes continue.

## Drafting and revision

1. `python scripts/piw_session.py open --outputs-root <task area>` then
   `python scripts/piw_coordinator.py start --piw-session <session> --request-json <request.json>`
   with the host object above in `request.host`.
2. On `awaiting_native_child`, validate the request with
   `python scripts/full_run_contract_check.py scope --parent-scope project_independent --child-brief <request_path>`.
3. Compute `COAUTHOR_REQUEST_SHA256=<sha256 of the request file bytes>` (the
   coordinator prints it as `request_sha256`). Invoke the native Agent tool with
   the matching role (`co-author-harness:generator`, `:evaluator`, or
   `:reflector`), passing the complete request JSON and that token in the prompt.
   Do not pass a `model` override where dispatch inherits a pin. The request
   binds `role_prompt`, `skill_bodies`, and `package_root` so the child reads the
   same role file and skill bodies on every host.
4. Wait for the tool to return `completed`. The child's final message must be
   the substantive result JSON, including its own `agent_execution_id` (the
   `agentId` the host assigned; it is the suffix of its subagent log filename).
5. Ingest with the original evidence:
   `{"agent_execution_id": "<agentId>", "turn_id": "<toolu_... tool_use id>", "child_log": "<logs_root>/<session-id>/subagents/agent-<agentId>.jsonl"}`.
   The verifier checks parent-child linkage, the token in the dispatching
   `tool_use`, a `completed` `tool_result`, an `end_turn` final child message
   equal to what the parent received, chronological order after the request,
   the exact result JSON, and pins both log prefixes. Later appends to a live
   session do not invalidate a pin; editing pinned bytes does.

Distinct Generator, Evaluator, and Reflector executions remain mandatory; the
caller (Planner) cannot present itself as a child. Task completion via
`piw_completion_guard.py verify` grants no lifecycle, scholarly CLEAN, or
research acceptance authority. Synthetic fixtures in
`scripts/claude_host_smoketest.py` prove adapter mechanics only; live
qualification requires a real session's own logs.

## Hooks

`hooks/hooks.json` registers the PreToolUse and Stop gate for Claude Code
sessions where the host sets `CLAUDE_PLUGIN_ROOT`. It enforces
`FULL_RUN_CONTRACT.md` scope declarations; it is not part of the trace boundary.

Plugin hooks run in every session once the plugin is enabled, so the gate is
scoped by territory, not by folder name:

- **No scope declared (the default).** Writes proceed, each with one
  `[FRC-SCOPE-PASSTHROUGH]` stderr notice. The gate denies only
  argument-bearing paths (`manuscript/`, `milestones/`, `submission_bundle/`,
  `research/`, `60_Workbench/`) that lie inside harness territory: a native
  project (an ancestor holding `reviews/phase_state.json` or
  `reviews/assignment_contract.json`) or a governed workspace root. A folder
  called `research` elsewhere on disk is ordinary. Agent/Task briefs naming
  `run-generator-session` are refused, and briefs naming a manuscript are
  refused when the session's working directory is inside harness territory.
- **A declared scope.** Writes to lifecycle artefacts (`manuscript/`,
  `milestones/`, `submission_bundle/`) route through
  `full_run_contract_check.py authorize`; `adhoc_review` is read-only and
  always refuses. Argument-bearing paths inside a governed root but outside
  the staging and private-shipment lanes are `DEST-PROTECTED` under every
  scope.

The hook reads the scope from its own process environment, which it inherits
from the host at launch; a model cannot declare it mid-session. Ordinary
`/run-draft` and `/run-iterate` work needs no scope. To drive a governed run
from a dedicated session, set it before starting Claude Code, either in the
launching shell or in the project's `.claude/settings.json`:

```json
{"env": {"FRC_PARENT_SCOPE": "full_lifecycle"}}
```

`FRC_REQUIRE_SCOPE=1` refuses every event without a valid scope, and
`FRC_GATE_HOOK_DISABLE=1` turns the gate off.
