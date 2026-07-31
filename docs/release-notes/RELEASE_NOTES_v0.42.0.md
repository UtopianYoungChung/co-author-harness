# Release notes - v0.42.0

## Outcome

This release closes the capability-claim boundary across six explicit planes:
policy, machine contract, producer, independently governed consumer, packaged
runtime, and qualification evidence. Every positive closure claim must bind the
same versioned contract kernel and fail closed when a required plane is absent,
stale, contradicted, or outside scope.

## Typed outputs and governed shipment

Role/output contract 3.0.0 defines fixed and triggered F1-F9 outputs, including
their invocation scope, occurrence, naming, deduplication, and diagnostic
rules. A declared output is not inferred from prose or file presence, and F9
retains its existing lifecycle authority boundaries.

Shipment schema 2.0.0 makes delivery a typed transaction. Manifests bind work,
state, evidence, preimage and postimage hashes, seal identity, retry behavior,
and recovery state. The implementation refuses path traversal, destination
protection violations, stale hashes, incompatible schemas or output classes,
duplicate occurrences, concurrent claims, and unsupported recovery states.

## Bilateral compatibility

The producer publishes an immutable shipment-v2 compatibility kit containing
the contract kernel, schemas, policy projection, diagnostic map, and a frozen
40-fixture corpus. The research-governance consumer pins those exact bytes and
executes the corpus through its own guard, policy, configuration, and tests;
it does not import mutable harness checkout modules. Consumer receipts bind the
producer tuple and both sides' component hashes.

Compatibility is observational and proposal-only. A passing receipt does not
apply a shipment, accept research work, mutate lifecycle state, authorize F9,
promote material, deliver to an advisor, enter canon, or disseminate anything.

## Qualification and status boundary

The pre-version source passed C8 at `QUALIFIED B0/M0/m0` with 15/15 structural
checks and 95/95 registry cases (91 suites, 696 inputs) from execution with
cache off, plus an exact detached replay. The preliminary independent consumer
passed all 40 frozen fixtures and 10 controls.

At this version/history slice the repository is only a source candidate. Final
0.42 source replay (C10), a new final consumer receipt, package/archive/
unpacked/installed-cache qualification (C11), and independent evidence-index
review (C12) remain separate gates. This file does not claim
`CAPABILITY_CLOSED`, `PACKAGE_CLEARED`, `SHIPPED`, `HOST_QUALIFIED`, research
activation, push, tag, or upload.

`.claude-plugin/plugin.json` remains the authoritative current-version plane;
this release note is historical release metadata.
