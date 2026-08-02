# v0.43 C2 destination-registry kernel-binding C0 addendum

Date: 2026-08-02
Scope: C0 authority only; no package, shipment, cache, host, activation, release,
promotion, acceptance, or canon claim.

## Observed blocker

The already-authorized destination-coverage pin updated
`references/destination_coverage_registry.json` to SHA-256
`0113fe84aa5aaf621b2e2e592a6922082a0c4ea57a4be80f3e7614c2b5194fcb`.
The contract-kernel coherence validator therefore reports exactly:

`destination-coverage-registry: content hash drift`

The preceding C0 addendum authorized only the `fixture-runner` component update
inside `references/contract_kernel.v1.json`; it did not authorize this derived
registry binding update.

## Narrow authority

Authorize exactly one additional source change:

- In `references/contract_kernel.v1.json`, update only the SHA-256 value of the
  component whose id is `destination-coverage-registry`, from
  `6179e140a11426d2ce1376303245a1c6605d7f01b7abe6e876d9b9e107f8d018` to
  `0113fe84aa5aaf621b2e2e592a6922082a0c4ea57a4be80f3e7614c2b5194fcb`.

No other component, migration, policy, fixture, manifest, package, cache, or
research byte is authorized to change under this addendum.

## Closure gates

Before the repair can be committed, require:

1. `python -B scripts/contract_kernel_coherence_smoketest.py` exits zero.
2. `python -B scripts/destination-coverage-check.py` exits zero.
3. `python -B scripts/analysis/fixture_infrastructure_check.py` exits zero.
4. The repository-wide tracked Python-bytecode census remains stable.
5. Independent exact-diff review reports B0/M0/m0.

The voided generated fixture manifest remains excluded from this repair and
must be regenerated only by a successful governed full-registry transaction.
