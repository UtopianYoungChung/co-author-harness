# Shipment v2 compatibility kit

This directory is the vendorable, immutable producer/consumer interface for
shipment manifest 2.0.0 and role/output contract 3.0.0. Consumers must copy or
pin these exact bytes; importing a mutable harness checkout is not conformance.

`shipment_manifest.schema.json` and `role_output_contract.json` are byte-for-byte
copies of their package authorities. `contract_kernel_projection.json` binds the
relevant machine components without granting lifecycle authority.
`canonicalization.json`, `diagnostic_map.json`, and
`shared_fixture_corpus.json` freeze cross-implementation behavior.
`compatibility_profile.json` is the producer candidate tuple; only a separately
governed consumer observation receipt can change its pending status.

## Consumer binding is never shipped

The profile carries `binding_state: "template"` and, in that state,
`consumer: null` and `external_snapshot: []` -- enforced by
`consumer_compatibility_profile.schema.json`, not merely by convention. A
package template that named one workspace's guard, policy, config, tests, or
absolute file paths would make the reusable plugin a mutable mirror of that one
consumer.

The resolved tuple still exists and still requires both fields; it just belongs
to the consumer's own plane. A consumer produces it inside a
`consumer_observation_receipt.schema.json` receipt, which pins the embedded
profile to `binding_state: "resolved"`.

Workspace-specific paths and hashes reach this package only through
`consumer_integration_adapter.schema.json`: a versioned, consumer-supplied
interface belonging to a separately authorized integration project. It takes
immutable core and consumer identities as inputs, is `authority:
"integration-input-only"`, and declares every lifecycle, approval, promotion,
delivery, release, installation, activation, and source-mutation grant as
`false`. Schema validation rejects malformed or authority-claiming adapters.
Absence is inert because the reusable core neither discovers nor applies an
adapter. Stale identities are detectable but must be refused by the integration
project before application; none of the adapter is stored here. Falsifiable
coverage: CORE-DECOUPLING D1-D5 in `scripts/contract_kernel_coherence_smoketest.py`.

This kit grants no research mutation, application, promotion, release,
shipment, host-qualification, or downstream-activation authority.
