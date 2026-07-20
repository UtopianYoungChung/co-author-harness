---
name: reflector
description: |
  Reflector compatibility router (v0.15.0-pre PR-4c). The Reflector was split into two mode-specific agent files: `agents/reflector-probe.md` for ad-hoc mid-round lightweight integrity probes (Ph1/Ph2/Ph3) and `agents/reflector-closeout.md` for the full five-phase reflection at Ph4 Finalize & Close. This file is retained as a routing surface so legacy dispatch paths that name "reflector" continue to resolve; retirement condition (recorded 2026-07-06): delete only when the host dispatch surface no longer names `reflector` as an agent type. New dispatch flows should target `reflector-probe` or `reflector-closeout` directly by name. Shared epistemics — binding constraint, dispatch modes, output contract, invariants, read/write boundary — live in `references/_snippets/reflection-grounding.md` and are included verbatim by both split files.
  <example>
  Context: mid-round Ph3 integrity probe.
  user: "Run a lightweight reflector pass on this round to check grounding."
  assistant: Dispatch reflector-probe (Phase 2f tier-row audit + Phase 2.5 grounding audit, no proposals).
  </example>
  <example>
  Context: Ph4 close-out after G.4 PASS.
  user: "Close this section at Ph4. Run the full reflector."
  assistant: Dispatch reflector-closeout (Phases 1–6 inclusive, plugin-proposal filing through the Planner gatekeeper).
  </example>
---

# Reflector — Compatibility Router (v0.15.0-pre PR-4c)

> **Retirement condition (2026-07-06, supersedes "retained for one minor"):** this router is deleted only when the host dispatch surface no longer lists `reflector` as an agent type. Until then it is load-bearing. See `docs/analysis/2026-07-06_systematic-improvement-plan.md` §3.

This file is a thin router. The substantive Reflector prompt was split into two mode-specific files at v0.15.0-pre PR-4c to reduce the 20,113-token always-loaded surface that fired warn-only at PR-4d. Both halves share an epistemic preamble that lives in a single snippet.

## How to resolve a Reflector dispatch

| Planner-issued mode | Read this file as the agent prompt |
|---|---|
| **Reflector-lightweight** (Ph1/Ph2/Ph3, on demand) | `agents/reflector-probe.md` |
| **Reflector-full** (Ph4 close-out, scheduled after G.4 PASS) | `agents/reflector-closeout.md` |
| Mode not declared | **Halt and ask the Planner.** Do not guess. The split is mode-significant; running the wrong half violates the dispatch contract and may emit out-of-scope artefacts (e.g. plugin proposals from a lightweight probe). |

The Planner declares the mode in the dispatch message per `AGENT_ORCHESTRATION.md §3`. If you were invoked under the legacy name `reflector` without a declared mode, ask the Planner to re-issue with `reflector-probe` or `reflector-closeout` named explicitly.

## What this file does NOT contain

- **Procedure.** All phases (1, 2, 2b, 2c, 2d, 2e, 2f, 2g, 2.5, 2.5.1, 2.6, 3, 3a, 4, 5, 6) live in the split files, scoped to the mode they apply to.
- **Output contract.** Lives in `_snippets/reflection-grounding.md`; included verbatim by both split files.
- **Invariants.** Same — in the shared snippet.
- **Vocabulary notes.** Same — in the shared snippet.

This file's only job is to route the dispatch. It carries no rules of its own.

## Output economy (mirrored from snippet for the static guard)

Both split files honour the v0.14.0 output-economy contract: they treat the F7 **evidence packet** paths and the Planner-assembled **final report** (F8) as read-only inputs for grounding and contract audits unless an exception profile requires Markdown step artefacts. The normative wording lives in `references/_snippets/reflection-grounding.md`; this paragraph is a router-side mirror so the static guard at `scripts/output_economy_check.py` can verify policy-vocabulary presence without resolving includes.

## Retirement condition

This router remains until the host dispatch surface no longer lists
`reflector` as an agent type. There is no calendar- or version-based removal
date. New dispatches use the explicit mode implementations; legacy dispatches
continue to route here until the host condition is verified.

## See also

- `agents/reflector-probe.md` — lightweight integrity probe
- `agents/reflector-closeout.md` — full Ph4 reflection
- `references/_snippets/reflection-grounding.md` — shared preamble (binding constraint, dispatch modes, output contract, invariants, what-you-read, v0.7.4 vocabulary)
- `references/AGENT_CONTRACTS.md §4 (Reflector)` — normative output contract details
- `references/AGENT_ORCHESTRATION.md §3` — dispatch protocol
