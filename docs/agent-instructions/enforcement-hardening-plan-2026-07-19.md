# Enforcement Hardening Plan — closing the narrated-run bypass (2026-07-19)

**Status:** IMPLEMENTATION CANDIDATE (TDD repair in progress; not committed,
version-bumped, packaged, or shipped).
**Author context:** follows the root-cause audit of the 2026-07-18 "harness full run" that produced no milestone artefacts, and its 2026-07-17 twin recorded in `scripts/full_run_contract_check.py`.
**Companion:** the bypass-surface inventory (B1–B7).

---

## 1. The finding in one sentence

The harness's fail-closed logic is correct and already written; nothing forces it to run, because enforcement is entered only by an agent that has already decided to enter it — and in the Cowork host, the one mechanism that could force it (plugin PreToolUse hooks) does not execute at all.

## 2. Host-dependence matrix (the governing constraint)

| Capability | Claude Code CLI | Agent SDK | Cowork desktop |
|---|---|---|---|
| Plugin-scoped `PreToolUse` hook fires | Yes | Driver-registered equivalent | **Historically not observed** (`--setting-sources user` excluded plugin scope in Claude Code 2.1.49; re-verify the target Cowork build — anthropics/claude-code#27398) |
| User-scope hook installable & persistent | Yes (`~/.claude`) | Yes (programmatic) | **No** (VM `$HOME=/sessions/<id>` is ephemeral; the persistent host bridge `mnt/.claude` is read-only and carries no `settings.json`) |
| Post-hoc detection possible | Yes | Yes | **Yes** |

**Consequence.** Prevention is available only when the host loads the hooks and
the driver explicitly declares `FRC_PARENT_SCOPE`. The current evidence does
not establish Cowork prevention. Cowork therefore retains the post-hoc track,
and the issue report is a version-bound observation rather than a permanent
host contract.

## 3. Track A — Cowork: detection (ships in-plugin, works everywhere)

### A1. `scripts/full_run_completeness_report.py` (new)
A post-hoc validator the user runs against the exact location where a run
claimed to work:

```bash
python scripts/full_run_completeness_report.py --search-root <workbench-or-project-dir>
python scripts/full_run_completeness_report.py --search-root <workbench> \
  --expected-root <claimed-run-location>
```

It discovers candidate project roots (`reviews/phase_state.json`) and retains
any explicitly supplied expected roots. It grades each as `COMPLETE` (gate exit
0), `INCOMPLETE` (authoritative refusal, gate exit 4), `NO-PROJECT`, or
`UNVERIFIABLE` (the gate could not form a verdict). Exit 0/1/2/3 respectively.
It does not pretend to infer which arbitrary loose document in a mixed
Workbench came from a claimed run; the caller must name that location with
`--expected-root`. Gate output is preserved in both JSON and human modes.

*Suggested integration:* invoke it at the end of any Cowork lifecycle session, and surface a `NO-PROJECT`/`INCOMPLETE` verdict as a blocking notice before any "converged/complete" language is shown to the user.

### A2. `release-gate.sh` — wire the enforcement smoketests (audit B7)
`full_run_contract_smoketest.py` and `full_run_semantic_bypass_smoketest.py`
existed but were never gated. Phase 0.57 now runs both plus the synthetic
`full_run_enforcement_surfaces_smoketest.py`; Phase 0.57b runs the portability
contract. Expected non-zero exits are captured with `errexit` temporarily
disabled, so the gate can classify them instead of exiting before its verdict.
A `CorpusRootError` remains a host VOID warning pending the hermetic corpus
fixture; every other failure is a BLOCKER.

## 4. Track B — CLI/SDK: prevention (inert in Cowork, hard block elsewhere)

### B1. `hooks/hooks.json` + `scripts/hooks/full_run_pretooluse_gate.py` (new)

A scoped `PreToolUse` + `Stop` hook that composes
`full_run_contract_check.py`. It is inert unless the driver explicitly exports
`FRC_PARENT_SCOPE=full_lifecycle|adhoc_review`; a global plugin hook may not
assume ordinary coding agents belong to an academic lifecycle.

- **Write/Edit into a normalized `manuscript/` path** → `authorize` under the
  declared parent scope; a refusal returns `permissionDecision: "deny"`.
- **Task / Agent dispatch** → `scope --parent-scope <declared> --child-brief <prompt>`;
  downgrade, escalation, contradiction, or omission is denied.
- **Stop with terminal vocabulary** → `terminal --project-root <current>`; an
  unearned completion claim returns `decision: "block"`.
- With an active scope, missing-gate and internal-error states fail closed. With
  no active scope, ordinary coding calls remain unaffected.

This does **not** claim that every shell-mediated write is intercepted.
`Bash`/PowerShell is a structurally different surface; authorship-critical SDK
drivers should restrict available write tools or route writes through the
authorized writer. The Stop gate prevents a shell bypass from earning terminal
language, and Track A detects the missing lifecycle after the fact.

### B2. Agent SDK equivalent (for programmatic drivers)
```python
# Driver sketch — activate the scope, then register the same hook contract
async def full_run_gate(input, tool_use_id, context):
    import subprocess, sys, json, tempfile, os
    tool, ti = input["tool_name"], input.get("tool_input", {})
    gate = f"{os.environ['CLAUDE_PLUGIN_ROOT']}/scripts/full_run_contract_check.py"
    def deny(reason):
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                "permissionDecision": "deny", "permissionDecisionReason": reason}}
    if tool in ("Write", "Edit") and "/manuscript/" in (ti.get("file_path","")):
        root = ti["file_path"].split("/manuscript/")[0]
        r = subprocess.run([sys.executable, gate, "authorize",
              "--project-root", root, "--run-scope", "full_lifecycle"],
              capture_output=True, text=True)
        if r.returncode != 0:
            return deny(r.stdout.strip())
    return {}   # allow

os.environ["FRC_PARENT_SCOPE"] = "full_lifecycle"
options = ClaudeAgentOptions(hooks={"PreToolUse": [HookMatcher(
    matcher="Write|Edit|Task|Agent", hooks=[full_run_gate])]})
```

## 5. Corpus-portability sub-finding (surfaced by this work)

Two distinct states must remain separate:

1. A host without the declared Windows corpus raises `CorpusRootError` — a
   portability VOID until the suites receive a fixture-owned corpus snapshot.
2. The current Windows corpus host resolves the roots but reports
   `initial semantic pin mismatch for exemplar_view_pin; deliberate profile
   repin required` — a governed semantic-drift BLOCKER, not a VOID.

The second state must be resolved through `/repin-register`; it must never be
converted into a warning. After a hermetic fixture exists, tighten the
`CorpusRootError` branch to BLOCKER too.

## 6. Verification state

- Synthetic enforcement surfaces: PASS on the current Windows host (Task / Agent
  interface, scope activation, normalized path refusal, Stop gate, exit-code
  preservation, mixed-tree expected-root handling, and `errexit` capture).
- Claude Code 2.1.214 live host: PASS. The observed `Task` call was denied when
  its child brief omitted `run_scope`, then allowed after exact
  `full_lifecycle` inheritance; the Stop hook also executed successfully.
- Python compilation and `hooks/hooks.json` parsing: PASS.
- Current corpus-host lifecycle suites: PASS after the confirmed epoch-5
  exemplar-view re-pin; the attestation pin and register membership are
  unchanged.
- Full fixture runner, release gate, pristine package build, and commit-bound
  provenance: not yet run on this overlay.

## 7. Governance / remaining steps (owner: maintainer, host-side)

1. Ship `hooks/` as the explicitly activated CLI/SDK prevention surface.
2. Package enumeration already includes every tracked non-archive path. Verify
   exact membership after commit; do not add a second enumeration rule.
3. Replace the remaining corpus-host VOID allowance with a hermetic fixture,
   then tighten Phase 0.57 to BLOCKER on every host.
4. Run the full `scripts/release-gate.sh` on the corpus host, commit the exact
   overlay, and verify the commit-bound package provenance.
5. Push the release branch for maintainer integration; the marketplace serves
   GitHub, so a local commit alone does not distribute the plugin.

## 8. What this does and does not buy

- **CLI/SDK with an explicit driver scope:** editor writes into `manuscript/`,
  child scope inheritance, and terminal claims are mechanically guarded.
- **Shell writes:** not claimed as intercepted; constrain tools in the driver or
  use the authorized writer, then verify with Track A.
- **Cowork:** prevention remains unverified on the target build. Detection is
  available, but it is not automatic unless the host or workflow invokes it.
