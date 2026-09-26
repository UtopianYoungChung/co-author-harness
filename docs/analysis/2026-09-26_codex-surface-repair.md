# Codex surface repair — verification record

Date: 2026-09-26. Source baseline: `9622346` on `main`.
Host probe: Codex CLI `0.158.0-alpha.2` on Windows. Package identity remains
governed by `version.json`. Master Governance resolver: valid `1.0.13`.

## Findings and repairs

Claude's pasted report concerned another commit and package version. Its
skills-only conclusion is too broad: current official Codex documentation
describes plugin hooks, including default discovery without an explicit
manifest field. The existing coordinator also already passes canonical role
prompts and required skill bodies to real Codex children.

The confirmed source defect was the hook protocol mismatch. The existing
Claude gate did not handle Codex `apply_patch` or `spawn_agent` payloads.
`hooks/codex.json` now selects native launchers and a dedicated adapter through
the Codex manifest. Patches check every affected path, including both sides of
moves; child messages reach the existing scope gate; Stop emits valid JSON.
Launcher failures return the host's blocking exit code. The original Claude
hook and its policy logic were preserved.

`scripts/codex_agent_setup.py` creates six native role configurations pointing
to the canonical Markdown prompts and skill directory. It can also generate
explicit role declarations and, when requested, the two hook bindings in a
new config fragment/profile. It refuses different existing files before
writing and changes no model, permissions, or hook trust.

## Observed verification

| Layer | Observation |
| --- | --- |
| Source skill inventory | 44 skill bodies; six canonical agent files |
| Isolated native plugin installation | Local marketplace add and plugin add succeeded |
| Native model-visible skill catalog | All 44 names present; none missing |
| Standalone role files / plugin-hook discovery | Not established by this CLI probe; plugin-only `hooks/list` returned zero hooks |
| Explicit generated configuration | Native `config/read` recognized six role declarations; `hooks/list` recognized PreToolUse and Stop, both untrusted, with zero errors/warnings |
| Profile parsing | `codex -p coauthor-harness debug prompt-input` succeeded against the generated disposable profile |
| Native child execution | Not exercised; configuration discovery is not role execution |
| Hook behavior | Direct adapter tests and actual Windows/POSIX launcher tests passed; no live host tool interception claimed |
| Existing user changes | Both pre-existing modified files were preserved exactly |

The passing focused checks were loader compatibility/adapter/role setup,
full-run enforcement surfaces, skill integrity, command surface, version,
version policy, manifest coherence, SSOT, schema runtime, path hygiene,
manifest links, and retirement sweep. Regression coverage includes benign
code edits, protected multi-file patches, add/update/delete/move targets,
normalized paths, malformed input, missing PIW session, child dispatch,
terminal claims, interpreter failure, dry-run behavior, and refusal to
overwrite a user-edited role.

On the initial working tree, `contract-kernel-check.py` was blocked by the pre-existing
`review-orchestration: content hash drift`. Its file still matches the
pre-repair snapshot. The workspace-wide preflight produced no output during
its prolonged scan and was interrupted; the canonical governance resolver was
run separately and validated the bound version above. No release qualification
or full fixture-corpus claim is made.

The initial standalone CLI inventory was empty even though this desktop chat
advertised harness skills. Those are different observed host contexts; neither
was used as evidence that the other's runtime was repaired.

## Integration with GitHub main

Before publishing, GitHub main at `50d42a7` was merged with the pre-existing local
enforcement commit. Two generated compatibility hash conflicts were resolved
from the merged kernel. Kernel validation, schema runtime validation, the
argument-coherence suite, and the kernel-coherence suite on a clean staged-file
snapshot passed. The earlier review-orchestration edit remains separately saved
and is not part of the publication candidate.

The newer upstream write guard scopes unscoped protection to native projects
and governed workspaces. The Codex regression fixtures now establish that
territory explicitly and also check that a similarly named ordinary directory
remains writable. Review dispatch tests bind the parent review scope rather than
depending on the separately saved local read-only exemption.

## Activation boundary

The repairs are in source and were installed only into a disposable test home.
The user's desktop plugin caches and trust records were not changed. Follow
the [Codex host setup](../agent-instructions/codex-host.md) for the intended
environment, refresh the host, and review/trust the exact hook definitions.
Use the explicit hook configuration fallback only when plugin discovery is
absent, avoiding duplicate handlers. Scope and PIW session bindings remain
required. Shell/MCP writes are outside these adapters' coverage.

Local logs, the pre-edit snapshots, native discovery responses, and source
hashes are retained in `.harness-test-scratch/codex-surface-repair/`, including
`verified-facts.json`. These development receipts are private and untracked.

Host references: [plugin packaging](https://developers.openai.com/plugins/build/plugins),
[hook protocol and trust](https://learn.chatgpt.com/docs/hooks), and
[custom agents](https://learn.chatgpt.com/docs/agent-configuration/subagents).
