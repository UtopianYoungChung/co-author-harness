---
name: centroid-pass
user-invocable: false
description: 'Unavailable public centroid-analysis entrypoint. Returns a deterministic read-only envelope with reason code IMPLEMENTATION_MISSING; it never edits a manuscript, bypasses a milestone fence, mutates lifecycle state, or writes to the canonical Wiki.'
trigger: when the user invokes /centroid-pass or asks for the package centroid pass.
version: 1.1
---

# centroid-pass — unavailable public entrypoint

## Capability disposition

`/centroid-pass` is **unavailable**. Its registry reason code is
`IMPLEMENTATION_MISSING`: the package does not yet expose a promoted public
centroid-analysis workflow.

Return this machine-readable envelope and stop:

```json
{
  "schema_version": "1.0.0",
  "capability": "centroid-pass",
  "status": "unavailable",
  "reason_code": "IMPLEMENTATION_MISSING",
  "read_only": true,
  "writes_performed": false
}
```

Do not create a review artefact merely to record the refusal. Do not edit the
manuscript, `phase_state.json`, assignment receipts, milestone evidence, or any
Wiki path.

## What is not promised

- There is no public `write`, `revise`, `all`, or `--apply` mode.
- This entrypoint does not bypass the Generator's M1–M3 exemplar fence.
- It does not retrieve or invent exemplar passages, attestations, quotations,
  corpus locators, or semantic findings.
- It does not re-pin the reader-accessibility policy or promote a capability.
- It cannot make graph generation or Wiki mutation available.

## Maintainer-only candidate

The repository may contain `scripts/centroid_service.py`, a read-only candidate
that prepares a hash-bound analysis packet from an explicitly named manuscript
and the resolved reader-accessibility policy. That script is testable substrate,
not public activation. It writes JSON to stdout only, reports deterministic
unavailability when inputs cannot be resolved, and emits no semantic verdict.

Changing this skill or `references/capabilities.yaml` from unavailable to an
active posture requires the separately governed H2 promotion decision and
evidence for the exact promoted interface.

## Inherited authority

The policy object at `references/policies/reader_accessibility.v1.json` remains
the authority for centroid membership, warrant layers, the C-7 identity fence,
derivations, and semantic pins. `references/GROUNDING_PROTOCOL.md` remains
absolute. This skill creates no new corpus membership, lifecycle authority,
write authority, or warrant claim.
