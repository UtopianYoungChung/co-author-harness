# v0.42.0 Capability Closure C0 Freeze

**Status:** committed C0 boundary; implementation has not begun.

**Charter SHA-256:** `742165e45856be3c59be88eb464e2008a717880294a9adeaab027219615eeaf9`

**Baseline commit/tree:** `9979bb59b9e1f4f41b7879c46f43813a34a80dc5` / `d429d6f5b228a8ac5d9c1a514a0ded0afc5eb2c5`

**Version boundary:** both manifests remain `0.41.0` through C8.
**Consumer state:** `CONSUMER_COMPATIBILITY_PENDING`; no v2 consumer receipt exists.

This tracked file commits the C0 decisions before the C1 red-only slice. Detailed
local evidence remains beneath the charter-required verification root and is
hash-bound here:

- `releases/verification/v0.42.0/C0/C0_REBASELINE_AND_FREEZE.md`: 15,649 bytes, SHA-256 `aaee84b67a61a010e4d67b3062468d0cff09a8ee9edadca0fe4bb5b0b7d54cf5`.
- `releases/verification/v0.42.0/C0/C0_PATH_LEDGER.md`: 12,985 bytes, SHA-256 `398033133e88737290e539e5d6401eb2e448807c3593e5295d501bdc102538fe`.

The second artifact enumerates every writable source, schema, test, fixture,
policy, runtime, compatibility-kit, version, package, and evidence path without
globs. Every source-owned path binds C0 Git mode, byte count, and SHA-256 or the
literal `ABSENT`. The Evidence Builder owns exactly five paths; the Authority
Builder owns exactly three and may not write before the qualified C1 commit;
the Qualification Reviewer owns none. A newly required path is a stop gate and
needs a reviewed, separately committed C0 addendum.

## Six-plane capability claim

`references/capabilities.yaml` remains the sole capability registry. Schema
`2.0.0` binds every row, directly or through one named profile, to exactly:
`policy`, `contract`, `producer`, `consumer`, `runtime`, and `evidence`.
`active` requires every applicable plane. `degraded`, `external-dependent`,
and `unavailable` enumerate missing planes and an applicable provider or stable
refusal code. Circular/self evidence, unregistered fixture IDs, unsafe paths,
stale hashes, status/behavior contradictions, and omitted packaged runtime
members fail closed.

## Role/output contract 3.0.0

`schema_version` becomes `3.0.0`; `path_contract_version` remains `2.0.0`.
Every applicable trigger occurrence closes once as `emitted`,
`not_applicable`, or `suppressed`. Suppression reasons are closed to
`TRIGGER_NOT_OBSERVED`, `SCOPE_NOT_APPLICABLE`, `POLICY_SUPPRESSED`,
`CARDINALITY_ALREADY_SATISFIED`, `DEPENDENCY_UNAVAILABLE`, and
`CONSUMER_AUTHORITY_PENDING`.

Context is exactly `round`, `milestone`, or `package`. Stable occurrence ID is
the lowercase SHA-256 of compact key-sorted UTF-8 JSON over contract
ID/version/hash, work ID, invocation scope, class ID, trigger ID, context,
ordinal, and triggering-evidence SHA-256.

### Fixed roles

| ID | Writer | Current path | Context | Operation | Payload authority | Authorization |
| --- | --- | --- | --- | --- | --- | --- |
| `M1` | `generator` | `milestones/M1_project_memo.md` | milestone | create/modify registered current | Markdown | resolved assignment contract plus explicit M1 approval for acceptance |
| `M2` | `generator` | `milestones/M2_annotated_references.md` | milestone | create/modify registered current | Markdown | resolved assignment contract plus explicit M2 approval for acceptance |
| `M3` | `generator` | `milestones/M3_argument_evidence_outline.md` | milestone | create/modify registered current | structured-outline Markdown | resolved assignment contract plus explicit M3 approval for acceptance |
| `M4` | `generator` | `milestones/M4_complete_paper_draft.md` | milestone or round | create/modify registered current | manuscript Markdown | resolved assignment contract; modification never implies acceptance |
| `M5` | `generator` | `milestones/M5_final_paper.md` | milestone | create/modify registered current | final manuscript Markdown | full-lifecycle Ph4 plus explicit M5 approval |
| `manuscript_revision_log` | `generator` | `manuscript/revision_log.md` | round or milestone | append | Markdown log | same authority as the manuscript mutation it records |

Fixed-role specialization is valid only through an explicit higher-authority
project contract; file presence never specializes a path.

### Triggered classes

| Class ID | Writer | Trigger ID / event type | Context | Invocation scopes | Path template | Cardinality and order | Persistence / human-facing | Payload schema | Authorization rule |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `F1_evaluator_findings` | evaluator | `evaluation_blocker_or_requested` / `evaluation_exception` | round | all three | `reviews/evaluator_findings_{occurrence_id}.md` | 0..n; occurrence ordinal ascending | immutable / yes | `ARTEFACT_FRONTMATTER_SCHEMA.md#family-f1` | only a blocker, failed gate, explicit report request, or verifier prose requirement; consumer controls create/application |
| `F2_evaluator_deterministic` | evaluator | `deterministic_report_required` / `deterministic_exception` | round | all three | `reviews/evaluator_deterministic_{occurrence_id}.md` | 0..n; ordinal ascending | immutable / yes | `ARTEFACT_FRONTMATTER_SCHEMA.md#family-f2` | only when a registered verifier requires prose; routine checks use F7 |
| `F3_reflector_lightweight_probe` | reflector | `reflector_probe_requested` / `reflection_probe` | round | all three | `reviews/reflector_probe_{occurrence_id}.md` | 0..n; ordinal ascending | immutable / yes | `ARTEFACT_FRONTMATTER_SCHEMA.md#family-f3` | explicit probe dispatch; consumer controls create/application |
| `F4_reflector_full_report` | reflector | `round_close_reflection` / `reflection_closeout` | round | `full_lifecycle` | `reviews/reflector_full_{round_id}.md` | 0..1 per round; after F1/F2/F3/F7 closures | immutable / yes | `ARTEFACT_FRONTMATTER_SCHEMA.md#family-f4` | full close-out dispatch only; consumer controls create/application |
| `F5_planner_consolidated_findings` | planner | `round_findings_consolidation` / `findings_consolidation` | round | `full_lifecycle` | `reviews/consolidated_findings_{round_id}.md` | 0..1 per round; after scheduled finding closures | immutable / yes | `ARTEFACT_FRONTMATTER_SCHEMA.md#family-f5` | aggregation trigger plus complete scheduled inputs; consumer controls create/application |
| `F6_planner_dispatch_plan` | planner | `round_open_dispatch` / `dispatch_plan` | round | `full_lifecycle` | `reviews/dispatch_plan_{round_id}.md` | exactly 1 when round-open trigger occurs; before downstream round output | immutable / yes | `ARTEFACT_FRONTMATTER_SCHEMA.md#family-f6` | user-approved dispatch under resolved assignment contract; never in lab iteration |
| `F7_evidence_packet` | role executing the registered check | `check_evidence_recorded` / `machine_evidence` | round, milestone, or package | all three | `reviews/.harness/evidence/{event_id}.json` | 0..n; event/ordinal ascending | immutable / no | `references/schemas/f7_evidence_packet.schema.json` | registered check or governing gate requires evidence; evidence does not grant authority |
| `F8_final_round_report` | planner | `round_close_report` / `final_round_report` | round | `full_lifecycle` | `reviews/final_round_report_{round_id}.md` | exactly 1 when close trigger occurs; after F4/F5/F7 closure | immutable / yes | `ARTEFACT_FRONTMATTER_SCHEMA.md#family-f8` plus `templates/final_round_report.md` | explicit round close or Ph4; consumer controls create/application |
| `F9_milestone_handoff` | planner | `milestone_approved` / `milestone_handoff` | milestone | `full_lifecycle` | `reviews/.harness/handoffs/{milestone_id}_to_{successor_milestone_id}.json` | exactly 1 after qualifying approval; milestone order | immutable / no | `references/schemas/f9_milestone_handoff.schema.json` | real approval provenance and lifecycle gate; forbidden in lab iteration |

`manuscript_delta` is explicitly classified under fixed role `M4` plus
`manuscript_revision_log`; it never creates another manuscript path.
`decision_checkpoint` is F7 when machine-readable and F1 when a human decision
requires an exception report. `blocker_exception` is F1. A consumer
application receipt is a closed shipment-control member, not an output class.
F7/F8 and legacy F1-F6/F9 remain readable, but a legacy artifact is not v2
transaction evidence merely because its class is recognized.

## Shipment v2 transaction

Shipment schema `2.0.0` is a discriminated union of `successful_shipment` and
`refused_shipment`. v1.0 and external v1.1 remain readable only and produce
`VERSION-LEGACY-NONAUTHORITATIVE` when offered as v2 authority.

A success binds package/kernel/output-contract identity, scope and context,
work/run/shipment IDs, every trigger closure, complete regular-file inventories
for `inputs/`, `work/`, `state/`, and `evidence/`, the closed `shipment/`
control set, one-to-one operation/artifact correspondence, and a state-last
journal seal. `create` requires absent-preimage evidence; `modify` requires the
expected preimage and exact postimage. `move`, `rename`, and `delete` require a
separate governing vocabulary and recoverable preimage. Exclusive writes,
idempotent retry, concurrency refusal, interrupted-seal recovery, and rollback
are mandatory. Receipt presence never means `applied`.

Receipts are distinct validation-only, consumer-observation,
consumer-authored application, refusal, and recovery variants. Application
recognition validates exact consumer identity, current authority, manifest
hash, accepted operations, preimages, postimages, and successful outcome.

Path comparison uses `/`, Unicode NFC, and Windows case-folding; absolute,
drive, UNC, device, traversal, collision, escape, symlink, junction, and any
reparse path is refused.

Stable diagnostic codes are:

`CAP-PLANE-MISSING`, `CAP-STATUS-CONTRADICTION`, `CONTRACT-HASH-STALE`,
`RUNTIME-PLANE-MISSING`, `VERSION-LEGACY-NONAUTHORITATIVE`,
`OUTPUT-POPULATION-MISMATCH`, `TRIGGER-UNKNOWN`, `CLASS-UNKNOWN`,
`OCCURRENCE-DUPLICATE`, `OCCURRENCE-CLOSURE-MISSING`,
`OCCURRENCE-STATE-CONTRADICTORY`, `CONTEXT-SCOPE-MISMATCH`,
`CARDINALITY-VIOLATION`, `ORDER-VIOLATION`, `PATH-TRAVERSAL`,
`PATH-COLLISION`, `PATH-REPARSE`, `PATH-ESCAPE`, `MEMBER-DUPLICATE`,
`MEMBER-UNLISTED`, `OPERATION-INVENTORY-MISMATCH`, `PREIMAGE-PRESENT`,
`PREIMAGE-STALE`, `POSTIMAGE-TAMPERED`, `TX-RETRY-CONFLICT`,
`TX-CONCURRENT`, `TX-UNSEALED`, `TX-RECOVERY-REQUIRED`,
`TX-ROLLBACK-FAILED`, `RECEIPT-INVALID`, and `APPLICATION-UNPROVEN`.

## Compatibility tuple

C5 preliminary and C10 final receipts use the same tuple: producer version,
commit, tree, kernel version/hash, shipment schema version/hash, output
registry version/hash, compatibility-kit hash, fixture corpus hash and exact
IDs, consumer guard/policy/config/test versions and hashes, work ID,
activation-baseline hash, canonical-role-registry hash, invocation scope,
occurrence/deduplication rules, results, and diagnostic mapping. C10 also binds
the exact final `0.42.0` package and cannot reuse C5 evidence. The consumer must
vendor immutable bytes; importing the mutable harness checkout is invalid.

The C0 external snapshot is the exact eight-file hash table in the hash-bound
rebaseline artifact. It confirms only the current v1.1 fixed-path/round
consumer. No harness role may edit it.

## C1 red IDs

The Evidence Builder's five exact paths must produce these expected failures
against unchanged production, with passing false-positive controls:

`cap-plane-policy-missing`, `cap-plane-contract-missing`,
`cap-plane-producer-missing`, `cap-plane-consumer-missing`,
`cap-plane-runtime-missing`, `cap-plane-evidence-missing`,
`cap-status-behavior-contradiction`, `cap-kernel-stale`,
`cap-runtime-stale`, `legacy-v1-not-v2`, `legacy-v1_1-not-v2`,
`population-fixed-triggered-confusion`, `trigger-unknown`, `class-unknown`,
`occurrence-duplicate`, `occurrence-closure-missing`,
`occurrence-state-contradictory`, `context-scope-mismatch`,
`cardinality-violation`, `order-violation`, `path-traversal`,
`path-case-collision`, `path-unicode-collision`, `path-reparse`,
`path-destination-escape`, `member-duplicate`, `member-unlisted`,
`operation-inventory-mismatch`, `create-present-preimage`,
`modify-stale-preimage`, `postimage-tampered`, `retry-conflict`,
`concurrent-writer`, `interrupted-seal`, `recovery-required`,
`rollback-exact`, `receipt-presence-not-applied`, `receipt-forged`,
`runtime-archive-suite-missing`, and `runtime-cache-suite-missing`.

C1 changes only the five Evidence Builder paths. It does not register the new
suites or update the committed fixture manifest. Root commits that red slice
alone and the read-only reviewer must qualify its exact expected failures,
controls, ownership, and production non-change before C2 opens.

No statement here grants research mutation, application, lifecycle, F9,
promotion, dissemination, shipment, or host authority.
