# Assurance Provenance Closure: C4 Interface Freeze

**Status:** frozen activation boundary; implementation and independent red
qualification pending
**Parent:** `2026-07-24-assurance-provenance-closure-c0.md`
**Red specification:** `2026-07-24-assurance-provenance-c1-red-spec.md`
**Frozen against:** commit `682030496c0a451f7802c1cd996446c02b6ae1fc`

## 1. Activation rule

C4 begins with a narrow, uncommitted activation seam because a valid attack
cannot execute before a genuine issuer and consumer exist. The seam may:

1. issue and marker-commit benign dispatch claims through the assignment
   transaction kernel;
2. consume the benign claims once;
3. enable a deterministic adapter only inside synthetic temporary fixtures;
4. issue fresh-project genesis and validate a synthetic externally authorized
   legacy anchor; and
5. deliberately omit the attack-specific checks long enough for the frozen
   one-fact attacks to succeed unexpectedly.

The builder stops at that point. The Qualification Reviewer must confirm the
benign controls, attacked fact, unexpected success, and full-tree unchanged
oracle before defensive implementation begins. Missing files, schemas,
functions, or CLIs remain `INTERFACE_BLOCKED`, not red evidence. No vulnerable
activation bytes may be committed.

## 2. Dispatch claim and consumption

`assignment_dispatch_claim` `1.0.0` is kernel-issued, immutable, canonical
JSON. The Planner requests issuance but is not the authority. Every claim
binds its ID/kind, role, issued-at value, nonce, kernel issuer/version and
issuer transaction, assignment receipt and reservation paths/IDs/hashes,
milestone and target, exact authorized paths/modes/preimages, policy digest,
and committed canonical-corpus digest.

A generation claim has no artifact postimage. An evaluation claim additionally
binds the consumed generation claim, exact artifact, and a replay-validated,
marker-committed generation verifier transaction whose phase is `generation`
and disposition is `evaluation_ready`.

`assignment_dispatch_consumption` `1.0.0` separately binds the exact claim,
consumer role/transaction, generated artifact or postimages, mutation rows and
head, consumed-at value, nonce, publication manifest, and last-written marker.
Claim issue, target publication, claim consumption, and mutation append share
the existing assignment transaction serialization. There is no parallel claim
or mutation lock.

Duplicate issue is a second issuance for the same logical issuer transaction,
role, and nonce, regardless of consumption state. Replay is a second
consumption of an already consumed claim.

## 3. Host attestation and independence

`assignment_host_attestation` `1.0.0` binds an allowlisted issuer/tool identity
and version, opaque task and session IDs, role, dispatch claim, target,
artifact, issued-at value, nonce, and a verifiable authenticator or immutable
tool receipt. A generation attestation omits a generation verifier
transaction; an evaluation attestation binds it.

The shipped production adapter allowlist is empty at C4. The deterministic
adapter is fixture-only and cannot be selected by a production CLI. Standard
mode can achieve `dispatch_separation`. Strict mode achieves
`host_attested_independence` only when both authenticated task IDs and both
authenticated session IDs differ. With no trusted adapter, strict mode returns
`INDEPENDENCE_UNVERIFIED`. An invalid supplied attestation is a hard refusal
and never downgrades.

No attestation proves a human reviewer, attentive reading, a different model,
causal independence, or qualitative judgment beyond its authenticated facts.

## 4. Mutation genesis, anchor, prefix, and head

Fresh projects receive transaction-issued genesis before the first mutation.
Genesis binds project identity, ledger path, zero-row state, initial live
target snapshots, policy/corpus context, issuer transaction, timestamp, and
nonce.

Existing projects require an authenticated, non-retroactive external anchor
binding project identity; ledger path/bytes/hash/row count/head; exact live
target snapshots; authorization path/hash/authority; adapter identity/version,
freshness, replay key, and authenticator; and
`historical_provenance_asserted: false`. The harness may propose but never
apply an anchor to protected research state. Existing rows are not rewritten,
and `migration_boundary` is not an anchor.

Milestone-style `accepted_prefix` validation binds canonical prefix bytes,
row count, and prefix head while allowing later legitimate appends.
Terminal/shipment-style `live_head` validation binds the current row count,
head, every latest target postimage, and absence of incomplete append state.
These are separate validators.

Mutation append uses the assignment transaction journal and records prior
head, prospective rows/head, targets, and marker-last completion. An internally
consistent marker omission is `APG-MUTATION-APPEND-INCOMPLETE`; divergent or
ambiguous state is `APG-MUTATION-RECOVERY-REQUIRED`.

## 5. Refusal precedence

Consumers apply this order so one-fact tests reach stable oracles:

1. missing object;
2. strict schema/canonicalization invalid;
3. missing publication marker or otherwise uncommitted object;
4. issuer/authenticator/replay authority;
5. expected-context binding.

For anchors, unknown issuer, bad authenticator, or replay is
`APG-MUTATION-ANCHOR-UNAUTHORIZED`; an authenticated malformed or
binding-invalid anchor is `APG-MUTATION-ANCHOR-INVALID`; an authenticated true
historical-provenance assertion is
`APG-MUTATION-LEGACY-PROVENANCE-OVERCLAIM`.

The exact dispatch, host, and mutation refusal codes are those frozen in the
C0 and C1 documents; no alias code may replace them.

## 6. State oracle and compatibility

Every ordinary refusal snapshots the complete synthetic project immediately
before the future consumer call and requires identical post-refusal paths,
object kinds, file bytes, and link targets, including all control, claim,
nonce, lease, reservation, journal, prepared, marker, ledger, recovery, and
target state. A crash test snapshots the already-partial state before the
refusing consumer. Successful recovery may add only its specified immutable
recovery receipt and must otherwise match the clean benign twin.

Semantic receipt `3.0.0` changes from the C2/C3
`legacy_compatibility` activation shape to mandatory dispatch-claim authority
for governed generation and evaluation. Its diagnostic legacy view remains
non-authoritative. Verifier transactions bind the exact claim and consumption,
and evaluation binds the generation transaction. `evaluation_ready` authorizes
only evaluation dispatch; only a later committed `product_qualified`
evaluation transaction can become C5 lifecycle evidence.

Legacy receipts, legacy semantic evidence, and an unanchored mutation ledger
remain diagnostic only. C4 performs no implicit migration and invents no
historical provenance.
