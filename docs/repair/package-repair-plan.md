# Co-Author Harness repair programme

**Status:** Approved architecture; implementation proceeds sequentially on the
sole branch `main`. A failing regression is written before its repair but the
test and repair are committed together only after the work package is green.

## Work packages

| WP | Scope | Exit gate |
|---|---|---|
| WP0 | Architecture, Contract Kernel manifest, capability truth registry, supervision protocol, and coherence checks | Root checks plus WP0 contract tests pass; Claude audits exact diff |
| WP1 | Canonical Ph1-Ph4 FSM, M1-M4 ownership, recovery transitions, role timing | Lifecycle, migration, recovery, ownership, and routing fixtures pass; H1 approval |
| WP2 | Receipt transaction and scoped writer authorization | Fresh positive dispatch passes; stale, copied, replayed, wrong-target, wrong-role, and wrong-path cases fail closed |
| WP3 | Public workflow and checkpointed M1-M4 progression | Synthetic M1-M4 walk succeeds without manual state repair |
| WP4 | Atomic M5/FINAL close | Exact G4, terminal round, F8/F9/M5, artifact hash, and terminal checker pass together |
| WP5 | Centroid and provider-aware graph/wiki services | Every capability has a truthful registry disposition: available capabilities are callable and tested; unavailable capabilities carry explicit reason, remediation, and evidence |
| WP6 | Simplified entrypoints, reflection modes, hooks, and shim deduplication | One discoverable name per capability; supported host mutations fail closed |
| WP7 | One fixture authority and Windows portability | Registry drives local/CI/release; native Windows and detached-clean checks pass |
| WP8 | License/catalog/version/package/install alignment | Source, archive, Claude, and Codex agree on version, hash, capability set, and enabled state; H3 approval |

## Cross-cutting invariants

1. `main` is the only branch; temporary clean verification uses a detached
   worktree that is removed afterward.
2. The Contract Kernel is versioned and each project binds a compatible kernel
   identity or completes an explicit migration/re-attestation.
3. Forward and recovery transitions are machine-readable rows in one FSM.
4. Planner alone writes authoritative lifecycle state.
5. Receipt emission to dispatch is free of bound-file mutation.
6. Every M1-M5 deliverable has one owner, path, acceptance rule, and evidence
   binding.
7. An active registry entry implies a callable implementation and registered
   evidence.
8. Hooks are idempotent defense in depth; explicit preflight is primary.
9. One fixture registry drives every verification surface.
10. Catalog, license, version, package provenance, and installed bytes agree at
    shipment.

## Approval gates

- **H0:** architecture, licensing intent, and capability disposition.
- **H1:** canonical lifecycle, recovery transitions, and M1-M4 ownership.
- **H2:** automatically reopens if a later change alters an H0 capability
  disposition.
- **H3:** exact immutable release artifact and installation receipts.

Changing an approved surface reopens its gate; approval is never inferred from
silence.
