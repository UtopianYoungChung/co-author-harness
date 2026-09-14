# Hermes Desktop integration

The native integration is installed by `scripts/install_hermes.py`. It derives
Hermes's `plugin.yaml` identity from `version.json`, copies the current source
bytes, and records every installed member in `HERMES_INSTALLATION.json`.
This is an explicitly labelled local development snapshot, not release evidence.
Configurations and previous plugin trees are backed up before replacement.
Only the co-author-harness plugin enablement changes; model/provider and fallback
configuration are preserved. Run with Hermes's Python environment (PyYAML is
required):

```text
python scripts/install_hermes.py --hermes-home <Hermes home> --all-profiles
```

Restart Hermes Desktop after installation, then start a fresh session. A new
session in an already running backend does not reload the native plugin. It
registers the public skills plus hidden legacy/maintainer skills and a bounded
system-prompt catalog. Unavailable skills are deliberately not registered.
Use ordinary text such as `Use co-author-harness:grammar-mechanics-pass on ...`.
The model loads `skill_view(name="co-author-harness:grammar-mechanics-pass")`.
Plugin skills are not standalone Desktop UI extensions. Package support files
remain under the installed package root; use the host's file/terminal tools to
read them. Hermes's `skill_view(file_path=...)` is restricted to a skill directory.

## Drafting and revision

Follow `PROJECT_INDEPENDENT_WORKFLOW.md`. The system-prompt section supplies the
current native host binding using adapter `hermes-hooks-jsonl`. Original traces
live under the active Hermes home's `plugin-data/co-author-harness/host-traces`.
The plugin observes actual `subagent_start`, `on_session_end`, and `subagent_stop`
events. It does not dispatch agents, choose a model, or fabricate role outputs.

The prompt callback cannot inspect the session's effective tool surface, so its
`subagents_available` value starts as `null`. Before creating a run, the caller
must check whether `delegate_task` is actually callable and set that field to
the observed boolean. Unknown or false is refused. Tool availability does not
grant a standing seat permission to draft or expand its permitted write lanes.

For each request emitted by `piw_coordinator.py next`, the caller computes
`sha256(piw_session.json_bytes(request))`. Include the complete role request and
`COAUTHOR_REQUEST_SHA256=<digest>` in the goal passed to native `delegate_task`.
Do not supply a model or provider override. Request substantive result JSON as
defined by the coordinator, including the child's actual `agent_execution_id`;
each child can read its session ID from its own plugin system-prompt binding.
Wait for a successful native completion. A merely present summary or a
budget-exhausted child does not qualify.

Use the original child trace's session header and `turn_finished.turn_id` to
form evidence with `agent_execution_id`, `turn_id`, and `child_log`. The filename
is SHA-256 of the session ID plus `.jsonl`. Ingest through the existing
coordinator. The verifier checks parent-child linkage, request hash, chronological
order, successful native completion, exact returned JSON, and pinned log prefixes.
Follow-up appends do not invalidate pinned prefixes; editing their bytes does.
Distinct Generator, Evaluator and Reflector executions remain mandatory.

The integrity of original host logs is trusted, as it is for Codex JSONL.
Synthetic hook/trace fixtures demonstrate adapter mechanics only. Live Hermes
execution and Desktop startup loading require separate evidence. If hooks,
native children, or original logs are unavailable, drafting/revision fails closed;
read-only passes can continue. External verification connectors and governed
lifecycle prerequisites remain required where the selected skill demands them.
