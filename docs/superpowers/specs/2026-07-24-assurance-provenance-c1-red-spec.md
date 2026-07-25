# Assurance Provenance Closure: C1 Red Specification

**Status:** C1 exit candidate under the authorized addendum; intended-red files are uncommitted
**Parent freeze:** commit `43c3b4471b66b0b27e4714161f525b3f64743f75`
**C0 document SHA-256:** `2d89e6f4057beb95cde59bc7b3ec117b7ff64d5721f989ec4156a5b03b80010b`

## 1. Evidence rule

A C1 vulnerability reproduction is valid only when it:

1. establishes a passing benign control on the current executable;
2. changes only the missing trust-boundary fact;
3. demonstrates that the current executable still returns success;
4. asserts the frozen future refusal code and unchanged state where state exists;
5. aggregates every intended-red result after the existing positive controls;
   and
6. remains uncommitted until production behavior makes the test green.

A missing future module, schema, CLI, or field is labelled
`INTERFACE_BLOCKED`; it is not evidence that an attack reproduced.

## 2. Reproduced product and evidence attacks

| Attack | Current executable | Future oracle | Observed v0.38 result |
|---|---|---|---|
| Duplicate JSON key | `product_assurance.py` | `EVIDENCE-SCHEMA-INVALID` | accepted, exit 0 |
| Unknown receipt field | `product_assurance.py` | `EVIDENCE-SCHEMA-INVALID` | accepted, exit 0 |
| Non-finite JSON value | `product_assurance.py` | `EVIDENCE-SCHEMA-INVALID` | accepted, exit 0 |
| Non-canonical JSON serialization | `product_assurance.py` | `EVIDENCE-CANONICALIZATION-INVALID` | accepted, exit 0 |
| Schema-valid assurance bytes copied outside verifier authority | `draft_governance.py verify` | `ASSURANCE-FORGED` | verified, exit 0 |
| Halo-only surface passage omits the centroid-role passage | `draft_governance.py verify` | `CENTROID-COVERAGE-INCOMPLETE` | verified, exit 0 |

Owned test files:

- `scripts/product_assurance_smoketest.py`
- `scripts/draft_governance_smoketest.py`

## 3. Reproduced authority and lifecycle attacks

No authority or lifecycle attack currently qualifies as reproduced red under
Section 1. The legacy evidence-version attack is `INTERFACE_BLOCKED` until C5
can establish eligible v2 checkpoint, milestone-framework, and F9 envelopes
bound to a committed `product_qualified` verifier transaction as its benign
control. It is specified in Section 5 and is not counted as reproduced red.

For every stateful attack activated later, the fixture must compare pre/post
trees or authoritative state bytes. The benign control may make its expected
state changes; the future refusal must leave the attack pre-state unchanged.

## 4. Preserved controls

The two modified suites still execute their own pre-existing positive and
negative controls before raising the aggregate C1 failure. Those controls
include valid product assurance, exact source/extract bindings, correct
locator/citation cases, current adjudication, and draft generation/evaluation
verification.

Separately, the unmodified receipt transaction smoke and the restored milestone
and terminal smokes remain green. They cover M1-to-M4 milestone walking,
successful terminal close, ordinary receipt replay refusal, broken-chain
refusal, live-byte mutation refusal, and recovery behavior.

## 5. Interface-blocked attacks

The following charter attacks cannot yet satisfy the C1 evidence rule because
their authority-bearing interface does not exist. They are not counted as
reproduced red:

| Attack family | Concrete fixture requirement | Responsible role and activation test | Checkpoint and frozen oracle |
|---|---|---|---|
| Missing extraction receipt | Semantic receipt `3.0.0` plus a benign committed canonical-extract `2.0.0` receipt/output transaction over an admitted source; remove only the passage's extraction-receipt binding | Evidence Builder; `source_extract_smoketest.py` and `product_assurance_smoketest.py` | C2 first red; `EXTRACT-RECEIPT-MISSING` |
| Invalid or uncommitted extraction receipt | The benign committed extraction transaction; replace only the receipt with a malformed object or a publication lacking its commit marker | Evidence Builder; `source_extract_smoketest.py` and `product_assurance_smoketest.py` | C2 first red; `EXTRACT-RECEIPT-INVALID` |
| Extractor unavailable | Self-authored three-page PDF and the benign qualified extraction transaction; make only the qualified executable unavailable | Evidence Builder; `source_extract_smoketest.py` | C2 first red; `EXTRACTOR-UNAVAILABLE` |
| Unsupported extractor version | The benign qualified extraction transaction; substitute only an unqualified executable version | Evidence Builder; `source_extract_smoketest.py` | C2 first red; `EXTRACTOR-UNSUPPORTED` |
| Extractor executable identity mismatch | The benign qualified extraction transaction; retain the claimed executable and version but substitute executable bytes with a different SHA-256 | Evidence Builder; `source_extract_smoketest.py` | C2 first red; `EXTRACTOR-IDENTITY-MISMATCH` |
| Extraction argv, layout, normalization, source, or extract binding mismatch | The benign committed extraction transaction; change exactly one bound argv, layout-mode, normalization-version, source-hash, or extract-hash fact, including coordinated source/extract substitution | Evidence Builder; `source_extract_smoketest.py` and `product_assurance_smoketest.py` | C2 first red; `EXTRACT-BINDING-STALE` |
| Locator, page, or span mismatch | Self-authored three-page PDF with repeated text, ligatures, and a cross-page phrase plus its benign replayable page/span map; alter only the locator, selected occurrence, page, or span mapping | Evidence Builder; `source_extract_smoketest.py` | C2 first red; `EXTRACT-LOCATOR-MISMATCH` |
| Extraction path escape | The benign admitted-source transaction; replace only a root-relative source, extract, or receipt path with a symlink, junction, alias, or traversal that resolves outside its governing root | Evidence Builder; `source_extract_smoketest.py` | C2 first red; `EXTRACT-PATH-ESCAPE` |
| Conditioning passage versus direct quotation, quotation relabelling, manuscript-span mismatch, and incomplete centroid/member coverage | Semantic receipt `3.0.0` with typed passage use, exact manuscript span, reviewed influence statement, a centroid-role surface passage, and an included/omitted rationale for each applicable argument member | Evidence Builder; `product_assurance_smoketest.py` and `draft_governance_smoketest.py` | C2 first red; quotation/use relabelling: `PASSAGE-CLASSIFICATION-MISMATCH`; manuscript span mismatch: `MANUSCRIPT-SPAN-MISMATCH`; missing centroid-role surface passage or applicable argument-member rationale: `CENTROID-COVERAGE-INCOMPLETE` |
| Bibliography metadata, redirect, alias, snapshot, root, identity, and cited-subset suffix attacks | Synthetic governed Wiki root containing canonical pages, explicit redirects, exact source bytes, a benign committed metadata transaction, and a manuscript citing a controlled subset | Evidence Builder owns initial implementation and attacks; Integration Steward owns schema/policy integration; new `canonical_bibliography_smoketest.py` | C2 first red; missing metadata: `CITATION-METADATA-MISSING`; redirect cycle or escape: `CITATION-REDIRECT-INVALID`; alias collision or ambiguous bibliography: `CITATION-BIBLIOGRAPHY-AMBIGUOUS`; malformed or internally rebuilt snapshot: `CITATION-SNAPSHOT-INVALID`; changed bound page/source bytes: `CITATION-SNAPSHOT-STALE`; substituted Wiki root: `CITATION-ROOT-MISMATCH`; canonical identity/title or cited-subset same-year suffix mismatch: `CITATION-IDENTITY-MISMATCH` |
| Governing-root substitution | Two typed root descriptors with the same relative path/bytes but distinct identities and manifests; benign binding uses the declared root | Integration Steward; `draft_evidence_verifier_smoketest.py` | C2/C3 boundary red before verifier implementation; `EVIDENCE-ROOT-MISMATCH` |
| Changed candidate and stale adjudication | Product assurance 2.0 benign candidate with stored fingerprint and matching adjudication; change only candidate text at the same code/locator | Evidence Builder; `product_assurance_smoketest.py` | C3 first red; `ADJUDICATION-STALE` |
| Semantics-manifest omission/addition/import redirection | Committed manifest containing the complete benign dependency inventory; remove, add, or redirect one dependency | Integration Steward; `draft_evidence_verifier_smoketest.py` | C3 first red; `SEMANTICS-DIGEST-MISMATCH` |
| Verifier lookalike, pre-marker publication, and lifecycle propagation | Valid verifier-transaction `1.0.0` prepared publication plus checkpoint/framework/F9 `2.0.0` bindings; substitute a role-authored lookalike or stop the genuine publication before its commit marker | Integration Steward and Authority Builder; `draft_evidence_verifier_smoketest.py`, milestone and terminal smokes | C3 then C5 consumer red; role-authored lookalike: `ASSURANCE-FORGED`; genuine publication before commit marker: `VERIFIER-TRANSACTION-INCOMPLETE`; terminal outer refusal: `FRC-TERMINAL-UNPROVEN`, delegating the verifier refusal |
| Dispatch claim manufacture, mismatch, replay, and interrupted consumption | Genuine committed generation and evaluation claims from a deterministic test issuer plus live expected contexts differing in one fact | Authority Builder; new `assignment_dispatch_claim_smoketest.py` | C4 first red; malformed claim: `APG-DISPATCH-CLAIM-INVALID`; role-authored or untrusted-issuer claim: `APG-DISPATCH-CLAIM-AUTHORITY`; missing: `APG-DISPATCH-CLAIM-MISSING`; pre-marker/uncommitted: `APG-DISPATCH-CLAIM-UNCOMMITTED`; role: `APG-DISPATCH-CLAIM-ROLE-MISMATCH`; target: `APG-DISPATCH-CLAIM-TARGET-MISMATCH`; receipt: `APG-DISPATCH-CLAIM-RECEIPT-MISMATCH`; preimage: `APG-DISPATCH-CLAIM-PREIMAGE-MISMATCH`; policy: `APG-DISPATCH-CLAIM-POLICY-MISMATCH`; corpus: `APG-DISPATCH-CLAIM-CORPUS-MISMATCH`; artifact: `APG-DISPATCH-CLAIM-ARTIFACT-MISMATCH`; generation: `APG-DISPATCH-CLAIM-GENERATION-MISMATCH`; duplicate issue: `APG-DISPATCH-CLAIM-DUPLICATE`; replay: `APG-DISPATCH-CLAIM-REPLAY`; interruption or recovery-required state: `APG-DISPATCH-CLAIM-RECOVERY-REQUIRED` |
| Invalid, mismatched, replayed, or unavailable host attestation | Genuine dispatch-separated control plus a frozen test adapter; change only one attestation or adapter fact | Authority Builder; `assignment_dispatch_claim_smoketest.py` | C4 first red; untrusted issuer: `HOST-ATTESTATION-ISSUER-UNTRUSTED`; malformed object, bad signature/tool receipt, or failed issued-at freshness: `HOST-ATTESTATION-INVALID`; session, claim, role, target, artifact, generation, or nonce binding mismatch: `HOST-ATTESTATION-BINDING-MISMATCH`; replay: `HOST-ATTESTATION-REPLAY`; no trusted adapter in strict mode: `INDEPENDENCE_UNVERIFIED` |
| Mutation anchor, prefix/head, interrupted append, and recovery attacks | Transaction-issued genesis or allowlisted deterministic governance-adapter anchor, accepted prefix binding, and later append committed through the real mutation transaction | Authority Builder; new `assignment_mutation_anchor_smoketest.py` plus receipt and terminal smokes | C4 first red; required legacy anchor absent: `APG-MUTATION-ANCHOR-MISSING`; malformed or binding-invalid anchor: `APG-MUTATION-ANCHOR-INVALID`; forged or replayed external authority: `APG-MUTATION-ANCHOR-UNAUTHORIZED`; historical provenance overclaim: `APG-MUTATION-LEGACY-PROVENANCE-OVERCLAIM`; truncation, row rewrite, or recomputed accepted-prefix substitution: `APG-MUTATION-PREFIX-MISMATCH`; stale live head: `APG-MUTATION-HEAD-STALE`; interrupted append: `APG-MUTATION-APPEND-INCOMPLETE`; recovery-required state: `APG-MUTATION-RECOVERY-REQUIRED` |
| Governed-product evidence, mode, publication, and recovery attacks | Typed mechanics manifest, `evaluation_ready` transaction, and `product_qualified` evaluation transaction from shared fixture builders plus a benign committed governed-run publication | Authority Builder; new `run_product_gate_smoketest.py` | C5 first red; governed mode without evidence: `PRODUCT-GATE-EVIDENCE-REQUIRED`; mechanics-as-product: `PRODUCT-GATE-MODE-MISMATCH`; publication before commit marker: `PRODUCT-GATE-TRANSACTION-INCOMPLETE`; recovery-required publication: `PRODUCT-GATE-RECOVERY-REQUIRED` |
| Legacy v1 lifecycle evidence substituted for eligible v2 evidence | Eligible assignment milestone checkpoint `2.0.0`, milestone framework `2.0.0`, and F9 handoff `2.0.0` envelopes bound to exact current bytes and a committed `product_qualified` verifier transaction; first prove the benign milestone and terminal paths, then replace only the relevant lifecycle envelope with v1 | Integration Steward and Authority Builder; `assignment_milestone_checkpoint_smoketest.py` and `assignment_terminal_close_smoketest.py` | C5 first red; milestone refusal `EVIDENCE-VERSION-INELIGIBLE`; terminal outer refusal `FRC-TERMINAL-UNPROVEN`, delegating `EVIDENCE-VERSION-INELIGIBLE` |

The v0.38 observations that motivated these rows remain contextual evidence,
not interface-specific red proof. Each activation test must establish its own
valid future-format benign control before changing the single attacked fact.

## 6. Authorized checkpoint disposition

The user authorized the following narrow execution clarification on
2026-07-24. It is an addendum to C1 only; it does not alter the original
fresh-session charter bytes or SHA-256.

C1 exits when:

1. every attack executable against the v0.38 surface has valid intended-red
   evidence under Section 1;
2. every interface-blocked attack has an exact owner, owning checkpoint,
   fixture requirement, and frozen refusal oracle; and
3. each owning checkpoint C2-C5 treats activation of its blocked attack as its
   first red gate, before any production implementation for that interface.

An `INTERFACE_BLOCKED` row is specification-complete at C1 but is not reported
as `RED-VULNERABILITY-REPRODUCED`. Its owning checkpoint cannot implement or
exit until the independent Qualification Reviewer confirms that the newly
executable test fails for the frozen intended reason. Missing modules, schemas,
fields, and CLIs remain non-evidence.

The currently failing C1 files remain uncommitted. They are committed only with
the production changes that make their vertical slice green. This preserves
the charter's prohibition on commits containing intentionally failing tests.
