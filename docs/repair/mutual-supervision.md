# Codex-Claude mutual supervision protocol

**Status:** Ratified by the researcher on 2026-07-19 and binding for the
Co-Author Harness repair programme. It does not govern academic manuscript
production.

## Roles

| Actor | Authority | Prohibited action |
|---|---|---|
| Researcher | Normative decisions and H0-H3 approvals | Approval inferred from silence |
| Codex | Repository edits, regressions, integration, green commits to `main` | Self-approval of normative choices |
| Claude | Read-only pre-change, diff, and exact-SHA audit | Repository mutation or shipment declaration |
| Deterministic gates | Mechanical conformance to committed contracts | Normative policy decisions |

## Work-package loop

1. Codex records the baseline SHA, authority files and hashes, in-scope paths,
   forbidden paths, acceptance criteria, commands, and recovery procedure.
2. Claude performs a read-only adversarial pre-review of that packet.
3. Codex writes the failing regression in the working tree and captures the
   expected failure. The red state is never committed.
4. Codex implements the smallest coherent repair and runs the targeted gate.
5. Claude reviews the exact diff, test evidence, contract drift, missing
   negative cases, and user-facing complexity.
6. Codex classifies each finding as `CONFIRMED`, `DISPUTED`, `MISSING_TEST`,
   `SCOPE_DRIFT`, or `NORMATIVE_DECISION`, reproducing every mechanical claim.
7. The challenger authors a minimal synthetic fixture for an unresolved
   mechanical dispute; the other party runs it unchanged.
8. Codex runs the root checks and all affected authoritative fixtures.
9. Codex stages only the work-package files, reviews the staged diff, and
   commits test plus repair together to `main` using a Conventional Commit.
10. Claude audits the exact committed SHA. Codex independently verifies
    Claude's claims; deterministic gates, not either agent, decide mechanics.

## Evidence packet

Every review packet contains:

- work-package identifier and baseline SHA;
- authority-file hashes and Contract Kernel identity;
- exact changed-file list and diff statistics;
- failing regression command and captured failure;
- targeted and root-gate command outputs;
- known limitations and unresolved decisions;
- interruption/recovery instructions.

Claude returns evidence-bound findings with file/line or command output and a
verdict of `PASS`, `PASS WITH CONDITIONS`, or `BLOCK`.

## Interrupted work

Partial work remains uncommitted in the `main` working tree. No branch, stash,
reset, or destructive cleanup is used. Codex records a handoff and resumes or
explicitly reverts only its own known changes after preserving the evidence.
No later work package starts until the interrupted package is resolved.

## Historical evidence

Changing a capability from active to unavailable does not retroactively void
accepted evidence. Historical evidence remains valid when it binds the
capability version, implementation or package hash, schema, and acceptance
event that governed its production. Incompatible or explicitly revoked
evidence requires human re-attestation; it is never inferred or silently
migrated.
