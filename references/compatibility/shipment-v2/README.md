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

This kit grants no research mutation, application, promotion, release,
shipment, host-qualification, or downstream-activation authority.
