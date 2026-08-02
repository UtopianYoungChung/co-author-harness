# v0.43 C2 destination-registry normalized-hash C0 correction

Date: 2026-08-02

## Correction

The preceding destination-registry kernel-binding addendum recorded the raw
working-tree SHA-256 of `references/destination_coverage_registry.json` as
`0113fe84aa5aaf621b2e2e592a6922082a0c4ea57a4be80f3e7614c2b5194fcb`.
That value is valid for the current CRLF working-tree bytes, but
`scripts/contract-kernel-check.py` deliberately binds text contracts after
normalizing CRLF to LF. The correct normalized SHA-256 is
`c1a082f902d01975b34457adbebf5c7cac802f8d2109275b194a8737d38e7552`.

## Narrow authority

Supersede only the destination-registry target hash named by the preceding
addendum. In `references/contract_kernel.v1.json`, the
`destination-coverage-registry` component SHA-256 may be changed from its
original value to the normalized value
`c1a082f902d01975b34457adbebf5c7cac802f8d2109275b194a8737d38e7552`.

All prior exclusions and closure gates remain binding. This correction grants
no package, shipment, cache, host, activation, release, promotion, acceptance,
research, or canon authority.
