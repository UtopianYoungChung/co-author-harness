# Work Order — Harness Audit Repair (inside-out slice)

**Opened:** 2026-08-21
**Scope:** hand contracts, DEST-PROTECTED write-law enforcement, hook/command surface wiring.
**Authority:** none of these items change thesis direction or governance policy. R-plane sign-off required only where marked **[R]**.
**Baseline commit:** `cb79151` — *chore: baseline before harness audit repair*. 26 files of pre-existing uncommitted work (academic-voice pass, contract kernel re-pin, d-style profile, draft governance, skills) committed unchanged so this order's repairs are legible in the diff. This is the revert point; `git revert cb79151` is NOT the undo for this order — reset repair commits made after it.

## Current status — reconciled 2026-08-22

This file is the work-order record for the destination/hook/command-surface audit;
it is not part of the later register-dispersion feature.

- **R-0 and R-1 landed** in `1de2f2e` (`fix: enforce and gate destination coverage`),
  with registry re-pins in `e960a76`. The destination coverage check currently
  reports 64 writers classified, 0 unclassified, and 0 drifted.
- **R-2's functional finding is closed.** Source inspection established that the
  shared hook already branches on `hook_event_name == "Stop"` and has dedicated
  Stop handling. Only the optional filename/docstring cleanup remains.
- **R-3, R-4, R-6, and R-7 remain open.** Nothing in the R-0/R-1 commits or in
  this record claims they landed.
- The whole-order release gate remains a terminal criterion, not evidence that
  every open row above has already passed.

---

## R-0 — Chokepoint bypass: writers that never consult `destination_capability`

**Severity:** high (this is the write law's whole point)

`scripts/destination_capability.py` is the single producer-boundary chokepoint. 62 of 66 writing modules route through it (directly via `assert_writable`, or via the `guard_project_root` / `guard_repin_project_root` / `guard_instrument_lane` wrappers, all of which delegate to `assert_writable`). Four do not:

| File | Write call | Notes |
|---|---|---|
| `scripts/evidence_publication.py` | `path.open("xb")` ×2, `path.open("a+b")` | publishes evidence — the highest-value bypass |
| `scripts/contract-kernel-check.py` | `kernel_path.write_text(...)` (L216) | a *check* script that mutates the kernel |
| `scripts/audit/schema.py` | write | |
| `scripts/audit/test_audit.py` | write | test-local; confirm sandbox-only, then exempt explicitly |

**Repair:** add `assert_writable(path, purpose=...)` immediately before each byte-landing call. `x`-mode does not substitute for the guard: exclusive-create still lands bytes in a protected lane if the file is absent.
**Verify:** extend `destination_capability_smoketest.py` with a negative case per file — point each writer at a governed `research/` path and assert `DestinationRefused(DEST-PROTECTED)`. Then re-run the bypass scan; expected residual = 0 (or 1, explicitly annotated, for the test file).

## R-1 — Enforce the chokepoint mechanically, not by convention

**Severity:** high (R-0 recurs without this)

Nothing prevents the next writer from being added unguarded.

**Repair:** new `scripts/producer_boundary_coverage_check.py` — walks `scripts/**.py`, flags any module containing `write_text|write_bytes|open(...,'w'|'a'|'x')` that lacks a `destination_capability` import, against an explicit allowlist with a reason string per entry. Wire into `release-gate.sh`.
**Verify:** check fails on a deliberately unguarded scratch file; passes on a clean tree.

## R-2 — Hook surface: Stop hook runs a PreToolUse gate

**Severity:** medium — **[R]** decision needed

`hooks/hooks.json` binds *both* `PreToolUse` (matcher `Write|Edit|MultiEdit|NotebookEdit|Task|Agent`) and `Stop` to the same entrypoint: `scripts/hooks/full_run_pretooluse_gate.py`. A Stop event has no tool payload, so either the gate silently no-ops on Stop (dead wiring — the full-run contract is not actually enforced at turn end), or it re-runs pre-tool logic against absent input.

**Repair:** determine intent, then either split into `full_run_stop_gate.py` with Stop-appropriate semantics, or drop the Stop binding and document why.
**[R] question:** is end-of-turn full-run enforcement *supposed* to exist? That is a contract-scope call, not a bug fix.

## R-3 — Hook interpreter is a bare `python3`

**Severity:** medium (portability; latent on this host)

`hooks.json` invokes `"command": "python3"`. On this Windows host that resolves to the Microsoft Store shim (`AppData/Local/Microsoft/WindowsApps/python3`, Python 3.14.2) — it works, but the shim is user-profile-scoped and can resolve to an install prompt on a fresh machine. A hook that silently fails to launch is an unenforced gate.

**Repair:** resolve via `sys.executable`/`CLAUDE_PLUGIN_PYTHON` with a documented fallback chain, and make launch failure loud rather than silent.
**Verify:** existing `loader_compat_portability_smoketest.py` extended with a hook-launch case.

## R-4 — Empty command surface passes its own check

**Severity:** medium

`commands/` contains no entries, yet `command_surface_check.py` reports `Blockers: 0` and a `plugin-commands` skill documents a command surface. Either the commands moved and the docs drifted, or the check has no emptiness assertion.

**Repair:** `commands/` is empty on disk — confirmed by the structural slice — so this is a single defect seen from two directions, and it splits cleanly: the **Orchestrator** owns the doc side (prune the `plugin-commands` skill reference and the README/AGENTS.md command-surface sections, plus the `releases/` residual below), the **Generator** owns the tooling side (`command_surface_check.py` must fail on an empty-but-documented surface rather than reporting `Blockers: 0`).

**Residual (Orchestrator):** `releases/` tops out at v0.42.0 with no 0.50.0 artifact. Doc drift, not a version conflict — the version plane itself is coherent (R-5 closed).

## R-2 — Hook surface: dual binding — **REFRAMED, no longer authority-gated**

**Severity:** low (cosmetic)

Original finding assumed the `Stop` binding was dead wiring because both events point at `scripts/hooks/full_run_pretooluse_gate.py`. Reading the source refutes this: the gate branches on `hook_event_name == "Stop"` (L250, L254, L268), has a dedicated `_handle_stop()` (L217) that tests the final response against `full_run_contract_check.py terminal --project-root`, and a fail-closed `_block_stop()`. The dual binding is intentional and end-of-turn enforcement is real.

Residual defect is the filename: `pretooluse_gate` describes half of what it does, and that mis-naming is what produced this false finding in the first place.
**Repair:** rename to `full_run_gate.py` (updating `hooks/hooks.json` both bindings) or correct the docstring in place. **[R]** cosmetic preference only — not a blocker.

## R-6 — Unset `FRC_PARENT_SCOPE` makes the whole gate inert, silently

**Severity:** high

The gate's error paths are well built: with a scope set, an unreadable payload or internal error **denies** (L246, L270) and `_block_stop`s on Stop (L251, L269). But every one of those paths is preceded by `if _active_parent_scope() is None: return _allow()` (L220, L243, L265). An unset or unknown `FRC_PARENT_SCOPE` therefore does not degrade enforcement — it disables it entirely, Stop included, with no signal. One environment variable separates full enforcement from none.

This is deliberate in part (the docstring's stated intent is not freezing ordinary coding sessions for a user-scoped plugin), so the repair is not simply to fail closed.

**Repair:** keep the permissive *decision*, remove the silence — emit a stderr notice on every scope-unset passthrough naming the variable and the fact that the full-run contract is unenforced for this event. Consider a `FRC_REQUIRE_SCOPE=1` opt-in that converts inertness to denial for lifecycle hosts.
**Verify:** smoketest asserting the notice appears on a scope-unset Write/Stop payload, and that `FRC_REQUIRE_SCOPE=1` denies.

## R-7 — End-of-turn enforcement is keyed to phrasing

**Severity:** high

`_handle_stop` engages only when the final assistant message contains a `TERMINAL_MARKERS` substring ("ladder complete", "terminal pass", "converged", "shipped", …); otherwise L223 returns `_allow()`. Terminal-state enforcement is therefore conditioned on the agent *announcing* terminality in specific words. An agent that completes a run and describes it any other way passes unchecked — the same defect class as R-0: not failing, not looking.

**Repair:** derive terminality from state, not prose — consult `phase_state` / the lifecycle record for the enclosing project and let `TERMINAL_MARKERS` remain only an additional trigger, never the sole one.
**Verify:** smoketest with a terminal-state project and a final message containing no marker; the gate must engage.

## R-5 — Version-plane coherence — **CLOSED**

`plugin.json` and `version.json` both read `0.50.0` and agree. Confirming that against `CHANGELOG.md` head, `.plugin-calibrator.json`, and `releases/` belongs to the structural slice — not repeated here.

---

## Sequencing

Closed: R-0 → R-1. Remaining mechanical sequence: R-3 → R-6 → R-7 → R-4.
R-2's functional concern is closed; its optional naming cleanup does not block
that sequence.

## Success criteria (binary, verifiable)

| Item | Done when |
|---|---|
| R-0 | Bypass scan returns 0 unguarded writers outside the annotated allowlist, AND one negative smoketest case per repaired file raises `DestinationRefused(DEST-PROTECTED)` when aimed at a governed `research/` path. |
| R-1 | **CLOSED:** `destination-coverage-check.py` scans `scripts/**/*.py`, refuses unclassified writers or pinned-class drift, checks maintainer/runbook parity, and is invoked by `release-gate.sh`. Current result: 64 writers classified, 0 unclassified, 0 drifted. |
| R-2 | **CLOSED (functional):** the shared hook branches on `hook_event_name == "Stop"`, invokes dedicated Stop handling, and fails closed when terminal enforcement engages. Optional file renaming is cosmetic only. |
| R-3 | Hook launches from a resolved interpreter on a profile without the Store shim; a launch failure surfaces an error rather than a silent skip. |
| R-4 | `command_surface_check.py` fails on an empty-but-documented surface; docs and disk agree either way. |
| R-6 | A scope-unset passthrough emits a stderr notice naming `FRC_PARENT_SCOPE`; `FRC_REQUIRE_SCOPE=1` denies instead of allowing; both covered by smoketest. |
| R-7 | A terminal-state project whose final message contains no `TERMINAL_MARKERS` substring still engages `_handle_stop`. |

Whole-order gate: `release-gate.sh` green, and no file outside the authorization table below is modified.

## Write authorization (pre-cleared against DEST-PROTECTED)

Every path below is inside the harness package root — classification `package`, writable under repo rules. **No item in this order touches a governed root**: nothing under `research/`, no manuscript, no `phase_state`, no `outputs/co-author-harness/` inside the package (that lane is `misrouted` and must stay refused).

| Hand | Authorized to modify | Explicitly NOT authorized |
|---|---|---|
| Generator | `scripts/evidence_publication.py`, `scripts/contract-kernel-check.py`, `scripts/audit/schema.py`, `scripts/audit/test_audit.py`, new `scripts/producer_boundary_coverage_check.py`, `scripts/release-gate.sh`, `scripts/command_surface_check.py` (emptiness assertion only), `scripts/full_run_contract_check.py` (R-7 state-derived terminality), `scripts/catalog-check.py`, `scripts/skill-check.py`, `scripts/version-planes-check.py` (inventory floor only), `hooks/hooks.json`, `scripts/hooks/full_run_pretooluse_gate.py`, `references/semantics_manifest.v1.json` (re-pin ONLY of members whose bytes changed under this order, via the `repin-register` skill, as a separate commit) | `scripts/destination_capability.py` — the chokepoint itself is frozen for this order; changing the law while repairing its enforcement destroys the evidence. Also `README.md` / `AGENTS.md` — doc drift is Orchestrator-owned |
| Evaluator | `scripts/destination_capability_smoketest.py`, `scripts/loader_compat_portability_smoketest.py`, `scripts/command_surface_smoketest.py` | production writers (tests only) |
| Orchestrator | `README.md`, `AGENTS.md` (R-4 doc drift + `releases/` residual) | anything under `scripts/` |
| Planner | `docs/work-orders/` | `scripts/`, `README.md`, `AGENTS.md` |
| Reflector | `research_notes/` work report at close | all of the above |

R-2 no longer carries an authority gate: source inspection closed the functional
question. The optional file rename/docstring cleanup is cosmetic and remains
non-blocking.

## Non-findings (checked, clean)

- The 23 modules that import `destination_capability` without a literal `assert_writable` token are **not** bypasses — they call the `guard_*` wrappers. Any coverage tooling must count the wrappers, or it will produce this same false positive.
- Alias handling in the chokepoint is sound: `realpath` + `normcase` before comparison, so junctions, case variants, and `..` traversals classify identically.
- `COAUTHOR_EXTRA_GOVERNED_ROOTS` is additive-only and cannot un-protect the real workspace.
- `classify()` fails closed on `ungoverned`.
