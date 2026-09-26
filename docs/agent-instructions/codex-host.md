# Codex skills, roles, and hooks

The Codex overlay `.codex-plugin/plugin.json` exposes `skills/` and explicitly
selects `hooks/codex.json`. Keep the Claude hook configuration in `hooks/hooks.json`.
Do not add an unsupported `agents` manifest field to try to register Claude role
Markdown files as Codex agents.

## Skills and the six roles

Codex initially exposes skill names, descriptions, and paths. The agent reads a
selected `SKILL.md` when needed; catalog visibility does not mean every body was
read. `skills/plugin-commands/SKILL.md` distinguishes supported public commands
from internal/compatibility skills. Do not unhide unavailable commands merely
to increase the visible command count.

The canonical role files are `agents/planner.md`, `evaluator.md`, `generator.md`,
`reflector.md`, `reflector-probe.md`, and `reflector-closeout.md`. These implement
four functional roles with split Reflector modes and a compatibility router.
The project-independent coordinator already binds the selected `role_prompt`,
`skill_bodies`, and `package_root` into each native-child request. It does not
require Codex to auto-register the Markdown files.

For named native Codex agents, generate TOML configuration pointing to the
canonical files in a stable source checkout or installed package:

```powershell
python scripts/codex_agent_setup.py --agent-dir "$env:USERPROFILE/.codex/agents" --config-output "$env:USERPROFILE/.codex/coauthor-harness.config.toml"
python scripts/codex_agent_setup.py --agent-dir "$env:USERPROFILE/.codex/agents" --config-output "$env:USERPROFILE/.codex/coauthor-harness.config.toml" --write
```

The first command previews the six destinations. The second creates them;
different existing files are refused before any write. For project-only roles,
pass that project's `.codex/agents` directory instead. Names use `coauthor_`
followed by the role, with underscores replacing hyphens. The setup changes no
model, reasoning effort, permissions, or hook trust. Refresh/reopen Codex and
verify discovery in a new chat. Rerun from the desired package after its root
changes; existing pointers are not automatically migrated. The optional config
output supplies explicit `[agents.<name>]` declarations for hosts that have not
adopted standalone agent discovery. Activate the generated profile with
`codex -p coauthor-harness`; creating files alone does not activate that profile.
Do not replace an existing user configuration with this generated fragment.

## The two hook events

`PreToolUse` adapts Codex `apply_patch` (`tool_input.command`) and `spawn_agent`
(`tool_input.message`) to the existing scope and destination checks. Every
add/update/delete target and both sides of a move are checked before a patch is
allowed. `Stop` uses the existing terminal-claim check and always emits JSON.
No separate lifecycle policy is implemented in the adapter.

The Unix and Windows launchers need a Python 3 interpreter with the package's
dependencies (including PyYAML and jsonschema). Set `COAUTHOR_HOOK_PYTHON` to an
absolute executable path when interpreter discovery is insufficient.
`CLAUDE_PLUGIN_PYTHON` remains a fallback. Codex supplies `PLUGIN_ROOT`.
Windows uses a native command launcher via `commandWindows` and tries `py -3`
when no interpreter override is set; it does not change PowerShell execution
policy. The default command uses a POSIX shell.

Installing a plugin does **not** trust its hooks. Review and trust the selected
definitions in Codex's `/hooks` interface before relying on them. Do not bypass
trust or edit persisted trust records as part of setup. Bind `FRC_PARENT_SCOPE`
for the run and, for project-independent writes, the actual `FRC_PIW_SESSION`.
Unscoped ordinary edits remain allowed outside harness territory; unscoped
argument-bearing edits inside a native project or governed workspace remain
refused. Folder names alone do not establish harness territory. An absent scope
does not activate full-lifecycle checks.

If the intended host's hook inventory does not discover plugin hooks, add
`--include-hooks` when generating a **new** config output above. This binds the
same two adapters by absolute path in that explicit profile. Verify the profile's
hook inventory before use and trust those definitions through the host. Use this
fallback only while plugin discovery is absent, to avoid registering duplicate
hook handlers. The setup never trusts hooks on the user's behalf.

These hooks do not intercept shell writes, arbitrary MCP file writers, or host
paths that skip tool hooks. A synthetic adapter test proves the decision logic,
not live installation, trust, or full-lifecycle qualification. The existing
trace verification and lifecycle gates remain required.

## Verify each layer separately

1. Run `python scripts/skill-check.py` and
   `python scripts/loader_compat_portability_smoketest.py` against the source.
2. Inspect `codex plugin list --json` in the intended host environment. A CLI
   inventory may differ from a running desktop chat's loaded plugin catalog.
3. Capture `codex debug prompt-input` once to a file and compare the skill names
   with the source inventory; inspect custom-role discovery in a fresh session.
4. Check installed file hashes and review current hook trust. Exercise a denied
   synthetic manuscript patch and a benign code patch in a disposable directory
   before claiming the native hooks enforce decisions. Never use live research
   files as a loading probe.

Official host contracts: [plugin packaging](https://developers.openai.com/plugins/build/plugins),
[hooks](https://learn.chatgpt.com/docs/hooks), and
[custom agents](https://learn.chatgpt.com/docs/agent-configuration/subagents).
