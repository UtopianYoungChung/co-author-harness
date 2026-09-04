# Handoff: Centroid advisory read-only contract fresh session

## Session Metadata

- Created: 2026-08-08T23:03:43-04:00
- Project: B:\Agents\platform\co-author-harness
- Branch: main
- Session duration: multi-turn architecture, migration audit, and release-state survey

## Current State Summary

The centroid redesign is planned but not implemented. The accepted direction is to preserve the existing governed semantic centroid and add a separate explicit `advisory_readonly` review contract for reader-profile v2 projects whose semantic usage is not invoked. The new route must use graph-independent reader-profile resolution plus explicit exact-file source bindings, produce no lifecycle evidence, and never mutate Paper 2. The fresh task has not been created or started.

## Codebase Understanding

## Architecture Overview

The current centroid packet builder is already read-only but calls the production semantic policy resolver. A valid reader-profile v2 project is deliberately refused before graph access. The harness already exposes a graph-independent reader-profile resolver, so the advisory route can be implemented without touching re-pin, Planner migration, or semantic-qualification code. Draft governance should remain the governed evidence boundary; advisory output must remain outside it.

## Critical Files

| File | Purpose | Relevance |
|------|---------|-----------|
| scripts/centroid_service.py | Deterministic centroid packet builder | Add the explicit advisory execution contract while preserving governed behavior |
| references/schemas/centroid_analysis.schema.json | Packet schema | Enforce a distinct advisory status and non-evidence semantics |
| scripts/centroid_service_smoketest.py | Public service behavioral contract | Lead the implementation with positive, negative, and no-write cases |
| skills/centroid-pass/SKILL.md | User-facing centroid workflow | Route explicit advisory review without restoring auto-dispatch |
| scripts/reader_profile_v2_global_smoketest.py | Global v2 routing regression | Prove semantic use remains dormant and automatic centroid remains off |
| docs/superpowers/plans/2026-08-08-centroid-advisory-readonly-contract.md | Approved planning artifact | Execute its tasks in order after the start gate clears |

## Key Patterns Discovered

- Reader-profile v2 intentionally records graph-independent policy state and `semantic_usage: not_invoked`.
- Governed centroid execution is receipt-backed and lifecycle-coupled; its failures must remain fail-closed.
- The clean separation point is the existing graph-independent profile resolver, not a relaxed semantic resolver.
- Exact source paths and hashes must be explicit inputs to advisory review; the system must not infer source admission from an unqualified graph.
- Advisory findings are proposals only and cannot be copied into governed evidence.

## Work Completed

## Tasks Finished

- [x] Diagnosed the architectural coupling that made a read-only centroid request trigger production semantic and lifecycle prerequisites.
- [x] Completed and independently audited the source implementation for fresh semantic qualification and v2-to-semantic migration; this is source-level only and remains unreleased/unactivated.
- [x] Surveyed the current v0.43.0 source, dirty paths, worktrees, qualification lock, and latest terminal controller receipt.
- [x] Drafted the implementation plan and allocated four bounded fresh-session lanes.
- [x] Preserved Paper 2 M4 and all protected project-state hashes.

## Files Modified

| File | Changes | Rationale |
|------|---------|-----------|
| docs/superpowers/plans/2026-08-08-centroid-advisory-readonly-contract.md | Added implementation and release-coordination plan | Give the fresh task an executable TDD sequence and exact authority boundaries |
| .claude/handoffs/2026-08-08-230343-centroid-advisory-readonly-fresh-session.md | Added this planning handoff | Allow a genuinely fresh task to rebaseline rather than inherit stale operational assumptions |

No centroid source, manuscript, lifecycle, F9, promotion, delivery, Wiki graph, version, release, cache, or host file was modified by this planning step.

## Decisions Made

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Add a separate advisory contract | Relax governed semantic qualification; qualify/re-pin every review; separate advisory plane | Separation preserves governed evidence while making an ordinary review proportionate |
| Use graph-independent profile resolution | Reuse semantic graph resolver; read archived artifacts; use current reader profile | The current profile API supplies declared members without fabricating semantic graph eligibility |
| Require explicit source files | Infer paths from graph; accept model memory; bind exact files | Exact paths and hashes preserve grounding without a production semantic transaction |
| Keep advisory Evaluator-only | Enable generation/revision; review only | The immediate need is independent review, not an automated solution or manuscript mutation |
| Exclude advisory output from lifecycle | Permit later promotion; treat as evidence; force fresh governed execution | Prevents a lightweight review from impersonating governed centroid evidence |

## Pending Work

## Immediate Next Steps

1. Wait for the user's explicit command to start the fresh task; do not create or dispatch it from this session.
2. In the fresh task, perform Task 0 of the implementation plan as a read-only rebaseline and confirm release-owner disposition of v0.43.0 attempt 049.
3. Start source edits only after a named, non-conflicting release integration point exists and current protected dirty work is reconciled.
4. Implement Tasks 1 through 6 with tests first; perform the M4 pilot only after source verification.

## Blockers/Open Questions

- [ ] Blocker: v0.43.0 attempt 049 is terminal `child_failed` on the token-budget unchanged-baseline case and produced no fixture manifest. Needs: separate release-owner disposition and a new governed qualification authority; the centroid task must not repair or retry it implicitly.
- [ ] Blocker: the main checkout contains protected modified and untracked semantic-migration work. Needs: exact ownership/integration reconciliation before any overlapping release-manifest or contract-kernel changes.
- [ ] Release decision: the centroid bundle has no assigned version identifier. Needs: release owner must explicitly assign a patch/minor slice before any version files change.
- [ ] Operational caution: the fixture lock names PID 77148, which is not live, but lock removal and retry-worktree cleanup are not authorized by this plan.

## Deferred Items

- Live semantic qualification, re-pin, Planner activation, installed-cache update, and host activation are deferred because the advisory design intentionally does not require them.
- M4 revision is deferred until the advisory centroid produces findings and the user separately authorizes manuscript changes.
- Governed adoption of any advisory finding is deferred to a fresh governed semantic execution; advisory output itself is never promotable evidence.

## Context for Resuming Agent

## Important Context

Current harness HEAD is `388ff6b5e5ebc7e4307cf6c948606088dfa59409` on `main`, with plugin version `0.43.0`. Qualification attempt 049 reached a terminal `child_failed` receipt with return code 1; its sole reported failing fixture was the token-budget unchanged-baseline test, and no new fixture manifest was written. Do not describe the release as qualified.

Paper 2 M4 remains SHA-256 `cb2308e6c9598430684d8a3c42569f0e0095534b547ef11ef0616075fc7bb2c3`. Its phase-state hash is `3fc35ae3060d0205075d69c41dae77f70fa903d905c276c21abef174cefbfa29`, and its work-package hash is `2a955040a7520514b66e1ff75d767dcae0d76baabc2e0c5f635cf8a299930aff`. The future consumer pilot is read-only and must recheck these bytes before and after.

The semantic-migration source implementation passed independent audit, but there is no live production qualified graph, re-pin, Planner activation, installed-cache qualification, or host qualification. Do not turn source-level success into an activation claim.

## Assumptions Made

- The user wants a simple advisory review first and governed adoption only if later warranted.
- The current public graph-independent profile resolver remains the intended stable seam in the assigned release slice.
- The release owner, not the fresh centroid task, will decide the version and disposition attempt 049.

## Potential Gotchas

- `centroid_service.py` currently refuses dormant v2 before semantic graph resolution; changing that refusal globally would accidentally restore universal centroid coupling.
- The current source tree is not globally clean. Preserve all unrelated modified and untracked paths.
- A dead lock PID does not make cleanup safe or authorized.
- A passing focused suite does not prove the archive, installed cache, startup catalog, or loaded host uses the new bytes.
- Internal multi-agent review is useful but is not an independently governed external consumer receipt.

## Environment State

## Tools/Services Used

- PowerShell and Git for exact live-state inspection.
- Python 3 standard-library harness scripts and smoke-test contracts.
- Independent read-only semantic-migration audit completed with no remaining source blockers.

## Active Processes

- No live process with PID 77148 was observed at handoff creation.
- The fixture lock remains present and names retry-34. It was not removed.

## Environment Variables

- `PYTHONDONTWRITEBYTECODE` may be set for verification runs.
- `PYTHONUTF8` may be set for Unicode-safe Windows probes.

## Related Resources

- docs/superpowers/plans/2026-08-08-centroid-advisory-readonly-contract.md
- skills/centroid-pass/SKILL.md
- scripts/centroid_service.py
- scripts/reader_profile_v2_global_smoketest.py
- references/GROUNDING_PROTOCOL.md
