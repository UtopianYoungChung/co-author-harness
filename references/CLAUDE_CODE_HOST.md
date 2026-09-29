# Claude Code / Claude Desktop host integration

Claude Code (CLI, Claude Desktop Code tab, Cowork, Agent SDK) loads this package
from `.claude-plugin/plugin.json` and exposes every public skill and the role
agents under the `co-author-harness:` namespace. The Planner is the exception:
it runs on the main thread (the session that runs `/run-draft`, `/run-iterate`
or `/run-finalize`), because a Claude Code subagent cannot dispatch
subagents. The Generator, Evaluator and Reflector are dispatched children, and
each child runs its own sub-passes inline. The adapter described here
is the native-host boundary those sessions use for ordinary drafting and
revision under `PROJECT_INDEPENDENT_WORKFLOW.md`. Read-only passes never need it.

## Installation and updates

Start with the [Claude Code installation commands](../README.md#claude-code) or
the [Desktop / Cowork download](../README.md#claude-desktop--cowork).

The package scripts and hook contract checks need Python 3 with PyYAML and
jsonschema. Claude Code hooks also launch through `bash -c`, so Bash must be on
`PATH`. On Windows, use Git Bash (`C:\Program Files\Git\bin\bash.exe`). Set
`CLAUDE_PLUGIN_PYTHON` if the interpreter the hooks find is not the one with the
required packages. A hook that finds no Python reports `HOOK-INTERPRETER`.

### Claude Code marketplace updates

The Claude manifests declare no version, so an install tracks `main`: every push
is an update. Claude Code does not auto-update third-party marketplaces by
default; turn it on once in `/plugin` → **Marketplaces** →
`joseph-chung-co-author-harness` → **Enable auto-update**. The settings can also be
declared in either of these files:

- **One workspace or project:** `<folder>/.claude/settings.json`, which applies to
  sessions opened in that folder. Create the directory and file if absent;
  Claude Code asks you to trust the folder the next time you open a session in it.
- **Every project:** `~/.claude/settings.json`
  (`%USERPROFILE%\.claude\settings.json` on Windows). Add the keys to any existing
  settings instead of replacing the file.

```json
{
  "extraKnownMarketplaces": {
    "joseph-chung-co-author-harness": {
      "source": { "source": "github", "repo": "UtopianYoungChung/co-author-harness" },
      "autoUpdate": true
    }
  },
  "enabledPlugins": { "co-author-harness@joseph-chung-co-author-harness": true }
}
```

Updates arrive in the background. A running session keeps the version it started
with until `/reload-plugins`; new sessions load the latest. To update at once:

```text
claude plugin marketplace update joseph-chung-co-author-harness
claude plugin update co-author-harness@joseph-chung-co-author-harness
```

### Desktop / Cowork uploads

Each version bump on `main` publishes `co-author-harness.plugin` and an identical
`.zip` on the [Releases page](https://github.com/UtopianYoungChung/co-author-harness/releases).
An uploaded file does not update itself: load the newer file after a release.

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
   The Evaluator and Reflector agent files set `model: inherit` and
   `effort: max`, so they run on the parent session's model at maximum effort;
   the Generator's `model:` frontmatter requests a family. `/tasks` shows each
   child's model and, for these four, its effort; a subagent's fallback when
   the model lacks `max` is not documented (`MODEL_ALLOCATION.md` §3). Verify the actual
   resolved model and highest supported effort under `MODEL_ALLOCATION.md`
   before relying on planning or review, including either Reflector mode.
   An active directive override may pass a family alias when the Agent tool
   supports it, but an alias alone does not prove the resolved release or
   effort. If the required selection cannot be verified or is unavailable,
   report that limitation and hold the affected planning/review. The request
   binds `role_prompt`, `skill_bodies`, and `package_root` so
   the child reads the same role file and skill bodies on every host.
4. Wait for the tool to return `completed`. The child's final message must be
   the substantive result JSON, including its own `agent_execution_id` (the
   `agentId` the host assigned; it is the suffix of its subagent log filename).
   A child cannot discover it by itself; the SubagentStart hook tells each
   harness child its `agentId` (see Session context below).
   **Asynchronous children.** Claude Code 2.1.283 in a non-interactive
   session launches every subagent asynchronously, even when the dispatch
   passes `run_in_background: false`. The Agent `tool_result` is then
   `{"isAsync": true, "status": "async_launched", "agentId": …}`, and the
   child's final message arrives later in a host-written `<task-notification>`
   row (`origin.kind: "task-notification"`, `promptSource: "system"`; a typed
   prompt carries neither). Wait for that notification before ingesting. The
   adapter accepts exactly one completed notice for the same `agentId` and
   dispatching `tool_use`, reads the identity fields only from the notice's
   header, requires its `<result>` to equal the child's final message, and
   refuses a child resumed after completing (two notices). The evidence
   object is the same in both modes; `finished_at` is the notice's time.
5. Ingest with the original evidence:
   `{"agent_execution_id": "<agentId>", "turn_id": "<toolu_... tool_use id>", "child_log": "<logs_root>/<session-id>/subagents/agent-<agentId>.jsonl"}`.
   The verifier checks parent-child linkage, the token in the dispatching
   `tool_use`, a `completed` `tool_result`, an `end_turn` final child message
   equal to what the parent received, chronological order after the request,
   the exact result JSON, and pins both log prefixes. Later appends to a live
   session do not invalidate a pin; editing pinned bytes does.

Distinct Generator, Evaluator, and Reflector executions remain mandatory (the
Reflector is omitted only under `review_depth: light`); the
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

### Session context

Claude Code does not load a plugin's `AGENTS.md`, so the grounding floor would
otherwise reach a session only when a model chose to read it. A SessionStart
hook (startup, resume, clear and compact) and a SubagentStart hook run
`scripts/hooks/session_context_hook.py`, which adds to the context:

- the package root, with the rule that `scripts/…` and `references/…` paths
  in the package's own files resolve against it, so a bare
  `python scripts/…` in a reference is run as `python "<root>/scripts/…"`;
- the quick reference card of `GROUNDING_PROTOCOL.md`, read from the file on
  every run;
- for a `co-author-harness:` subagent only, the `agentId` the host assigned,
  which step 4 above requires as the result's `agent_execution_id`;
- for the main session, the host object above filled in from the
  `transcript_path` the host reports at session start (`logs_root` is its
  directory, `parent_log` the file). Use it as `request.host` rather than
  searching for the session log; set `subagents_available` to false if the
  session has no Agent tool.

Other plugins' subagents and the host's own receive nothing. The hook never
blocks a session; if the protocol is unreadable it injects a pointer to the
file and reports the fault on stderr. `COAUTHOR_SESSION_CONTEXT_DISABLE=1`
turns it off.
