# Reader-profile v2 next-version integration note

Status: included in the v0.40.0 release candidate; package qualification pending.

## Decision

The 2026-07-27 reader-policy/Graphify gate decoupling is a public lifecycle-contract change. It must ship as part of the next co-author-harness plugin version and must not be treated as an unversioned local repair.

Do not bump `.claude-plugin/plugin.json` independently while the next version is still under development. If the pending release is already the next minor version, absorb this bundle into it. If the pending release was planned as a `0.39.x` patch, reclassify it as a minor release (normally `0.40.0`) because this bundle adds reader-profile binding v2, Check 8 v2, migration semantics, and capability-triggered centroid obligations.

## Shipped behavior required

- Every canonical native bootstrap writes `binding_version: 2.0.0`, `binding_kind: reader_profile`, and `semantic_usage: not_invoked`.
- A native ledger without a supported v2 binding or an explicitly supported legacy binding fails validation.
- Assignment dispatch and draft governance derive centroid applicability from the authoritative phase-state binding; v2 omits the unavailable centroid obligation but retains C6 scholarly evaluation and every non-graph control.
- M3-M5 propagate the v2 reader-profile hashes plus `semantic_usage`.
- Accepted M4/M5 v2 work uses `check8_evidence.v2`, which rejects semantic pins and remains deterministically recomputable.
- Direct graph-dependent behavior remains fail-closed with `GRAPH_GOVERNED_GENERATION_UNAVAILABLE`.
- Legacy `semantic_graph_unavailable` projects migrate only through the receipted, rollback-safe Planner transaction.

## Global-trigger coverage

The implementation is complete at source level. Future projects are covered
through these shared authorities rather than project-local convention:

- Canonical native bootstrap automatically installs reader-profile v2.
- Validation refuses native projects that omit or hand-build the required binding.
- Public `/run-draft`, Planner, Generator, and Evaluator routes derive centroid obligations from that binding.
- Legacy projects require the explicit receipted migration.
- The global regression runs through the shared fixture registry used by both CI and `release-gate.sh`.
- Migration ID `reader-profile-v2-decoupling` is registered on the seven affected contract-kernel components: phase state, assignment process, reader accessibility, assignment-process gate, assignment-milestone transaction, milestone-framework validator, and milestone-framework schema.

## Release integration checklist

This checklist is component-scoped. The complete version, committed-HEAD ZIP,
checksum readback, source/archive/unpacked/cache qualification, evidence-index,
rendered-report, reinstall, and independent-review gates are governed by
[C11 of the v0.40 execution charter](../../../releases/V0.40.0_SCHOLARLY_ASSURANCE_REPAIR_AND_VERSION_UP_PLAN.md#c11---version-documentation-and-package-evidence).

- [x] Reconcile this bundle with all other next-version work; preserve pre-existing changes.
- [x] Register `scripts/reader_profile_v2_global_smoketest.py` in the common fixture registry used by both CI and `release-gate.sh`; direct execution and fixture-infrastructure validation pass.
- [x] Remove stale operational claims that centroid conditioning is universal from public skills, agent contracts, lifecycle protocols, and the draft-governance policy.
- [x] Register the migration identifier `reader-profile-v2-decoupling` on seven affected contract-kernel components.
- [x] Refresh contract-kernel and verifier-semantics hashes only after all next-version source files are frozen.
- [x] Add the bundle to the v0.40 CHANGELOG release history; this note is its compatibility/migration record.
- [x] Perform the single version bump for the complete pending release.
- [ ] Verify clean-worktree release gate, built archive membership, packaged-source parity, and installed-plugin-cache parity.

## Evidence already obtained

- Native bootstrap and legacy migration smoke test: PASS.
- Reader-accessibility contract: 23 cases PASS; adversarial and semantics suites PASS.
- Assignment process and draft-governance suites: PASS.
- Public M1 to M4 transaction walk, including M4 Check 8 v2 acceptance and exact-byte rollback: PASS.
- Milestone/phase-state integration and structural graph-authority boundary: PASS.
- Global routing regression, fixture infrastructure, and scoped diff checks: PASS.

This note is release-planning evidence, not a release receipt. The original
source implementation session changed no version, tag, archive, installed
cache, or remote state. The coordinated release slice has since advanced the
source manifests to the v0.40 release candidate; committed-HEAD archive,
installed-cache, independent-clearance, and remote-shipment evidence remain
separate gates until their receipts exist.
