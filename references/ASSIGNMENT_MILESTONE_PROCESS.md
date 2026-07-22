# Assignment-Derived Milestone Process

## 0. Producer boundary (binding, 2026-07-22)

Milestone transactions are production bookkeeping, never research authority.
Every transaction verb (`begin`, `record`, `accept`, `rebind-reader-policy`,
`recover`) and every writer CLI resolves its project root through
`scripts/destination_capability.py` and refuses a destination under a governed
workspace root outside the harness package with `DEST-PROTECTED`. Work whose
consumer is the research tree runs in the governed staging lane
(`outputs/co-author-harness/staging/<work-id>/<run-id>/`) and reaches its
consumer only as a path-and-hash-bounded shipment adjudicated under
`research/10_Governance/HARNESS_SHIPMENT_BOUNDARY.md`. No milestone status,
gate PASS, or handoff written by the harness implies acceptance, registration,
promotion, or permission to mutate a consumer tree.

## 1. Binding rule

Before drafting any academic deliverable, the Planner must read the controlling assignment, advisor brief, venue call, or current user instruction in full and resolve `reviews/assignment_contract.json`. A filename, prior harness default, or existing milestone label is not a substitute for reading the source. If the source is unavailable or the contract is unresolved, drafting is blocked rather than guessed.

Run `python scripts/assignment_process_gate.py --project-root <project-root> --stage draft --target-milestone <M1|M2|M3|M4>`. Draft dispatch without an explicit target fails closed. After accepted M4 and Ph4 admission, begin public `FINAL` with `assignment_milestone_checkpoint.py begin --milestone FINAL`, then run the assignment gate with `--stage final`; final stage always resolves the public target to `FINAL` and ledger slot M5. The final gate requires accepted M1-M4, M5 `in_progress`, all in-scope sections at Ph4, and both terminal fields still open.

The source binding records the source path, exact SHA-256, and authority. The package profile binding records the profile path and exact SHA-256. The project contract maps assigned deliverables to harness slots without changing what the assignment calls them.

## 2. Four milestones and a separate final paper

For `references/policies/course_essay_milestones.v1.json`:

| Assigned item | Precise job | Harness slot |
|---|---|---|
| M1 short project memo | Explore the preliminary focus, emerging tension, questions or goals, and the author's intellectual interest. It does not freeze a thesis. | M1 |
| M2 annotated references | Assemble relevant course readings and additional sources, with a brief statement of what each contributes. | M2 |
| M3 structured outline | Design the context, central tension, and reciprocal application that will organize the final analysis. | M3 |
| M4 complete paper draft | Present the full argument for feedback, even where claims and wording remain provisional. | M4 |
| Final paper | Elaborate and revise the full argument after the four milestones and the M4 feedback stage. | Terminal framework slot M5 |

The terminal framework slot is named `M5` for backward-compatible machine state. It is not evidence that the assignment itself has a fifth milestone. Human-facing documents must call it the final paper when the controlling brief does.

## 3. Gate semantics

- `draft` verifies that the assignment contract is resolved, the source and profile hashes are current, the assigned sequence and framework mapping are complete, professor-copy authority remains with the author unless explicitly delegated, and the target's predecessors are accepted.
- `final` includes every `draft` check and requires M1, M2, M3, and M4 to be `accepted`.
- Native course-essay projects use the sequence gate below. A legacy contract fails with `APG-SEQUENCE-LEGACY` until the operator performs the named migration and acceptance work; file presence never implies acceptance and the gate never promotes status.
- Harness phases remain orthogonal. Ph1-Ph4 control drafting and review maturity; they do not redefine assignment deliverables.
- Assignment or instructor requirements override the package profile. A different assignment requires an appropriate versioned profile or explicit higher-authority specialization before drafting.

| Target | Required accepted predecessors | Sequence blocker |
|---|---|---|
| M1 | none | none |
| M2 | M1 | `APG-SEQUENCE-M2` |
| M3 | M1, M2 | `APG-SEQUENCE-M3` |
| M4 | M1, M2, M3 | `APG-SEQUENCE-M4` |
| FINAL | M1, M2, M3, M4 | `APG-SEQUENCE-FINAL` plus the retained per-milestone final prerequisite finding |

Missing `--target-milestone` at draft stage produces `APG-SEQUENCE-TARGET`. `reviews/phase_state.json.milestone_framework.milestones` is the sole source of milestone acceptance state, and only the Planner may write it.

### 3.1 Wiki grounding before M4

M4 and FINAL additionally require current wiki-first grounding evidence. After SK-33 `seed-snowball-discovery`, SK-36 inheritance, or an equivalent wiki-first pass, the Planner writes `reviews/.harness/assignment/wiki_grounding_<round>.json` and binds its project-relative path and exact SHA-256 at `milestone_framework.milestones.M3.policy_evidence.wiki_grounding`. The finalized M3→M4 F9 packet carries the same `policy_evidence`; this extends the existing F9 handoff and does not create a second ledger.

The evidence object records `schema_version: 1.0.0`, active `lineage_id`, RFC3339 `produced_at`, `wiki_path`, `wiki_first_resources: true`, non-empty `skills_invoked`, `references_path` plus exact hash, `graph_path` plus provenance hash, at least one exact-byte `sources_consulted` binding, `authority: planner`, and non-empty notes. The gate re-hashes the evidence file and every declared file at M4 and FINAL. Missing evidence emits `APG-WIKI-GROUNDING-MISSING`; path, lineage, schema, or hash drift emits `APG-WIKI-GROUNDING-STALE`.

An opt-out is valid only when `M3.policy_evidence.wiki_grounding_opt_out` records authority `user`, `advisor`, or `instructor`, a non-empty reason, and a current project-local approval-evidence path/hash. Anything weaker emits `APG-WIKI-OPT-OUT-INVALID`. The Planner must never infer an opt-out.

This pre-M4 read-side grounding is distinct from Coupling D. M5-to-wiki ingestion remains a post-final write-side action and cannot satisfy this gate.

### 3.2 Exemplar-conditioning scope

The Planner passes `--exemplar-conditioning` only when the dispatch will retrieve and condition prose on domain-native exemplar passages. The gate blocks that flag, or an equivalent `exemplar_conditioning: true` contract/dispatch field, at M1-M3 with `APG-EXEMPLAR-SCOPE`. This restriction concerns conditioning, not ordinary scholarship: M2 may read, annotate, and cite Yu or Dennett when the Grounding Protocol is satisfied.

At M4 and FINAL, Yu is the domain-native surface centroid. Dennett is the intentional-root and is admissible only for argument architecture with `warrant_scope: argument-only`; it is never a surface-register emulation target. When Dennett is pending rather than admitted, the gate emits `APG-EXEMPLAR-DENNETT-PENDING` as an advisory while Yu-conditioned drafting remains available.

| Target | Accepted predecessors | Wiki grounding | Exemplar conditioning |
|---|---|---|---|
| M1 | none | not required | forbidden |
| M2 | M1 | not required | forbidden; scholarly citation allowed |
| M3 | M1, M2 | not required | forbidden |
| M4 | M1, M2, M3 | current evidence or authorized opt-out | allowed under Yu/Dennett role split |
| FINAL | M1-M4 | current evidence or authorized opt-out | allowed under Yu/Dennett role split |

### 3.3 READY receipt lifecycle

The Planner records a successful gate result with `--emit-receipt <path>`. The path must match `reviews/.harness/assignment/ready/gate_receipt_<target>_<utc>.json`; the gate refuses the basename if it already exists in any receipt-state directory. A receipt is immutable evidence for one Planner-to-Generator transaction, not a milestone ledger or an acceptance record. Its strict schema is `references/schemas/assignment_gate_receipt.schema.json`, and its non-authoritative bootstrap example is `references/templates/assignment_gate_receipt.json`.

Each receipt binds the project name, stage, target, active lineage, exemplar-conditioning decision, exact assignment-contract, phase-state, and package-profile hashes, plus a digest of the gate's READY output, a reservation token, the Generator role, and exact authorized output paths. `python scripts/assignment_process_gate.py --project-root <project-root> --verify-receipt <receipt>` re-hashes all bound files and re-runs the sole `validate()` predicate engine. Verification never updates milestone state.

Receipt state is its directory: `ready`, `reserved`, `consumed`, or `invalidated`. Receipt bytes never change. Immediately before dispatch, the Planner runs `assignment_dispatch_preflight.py` with `--consumer planner` and every intended `--write-path`; the command validates the live bindings and atomically moves `ready` to `reserved`. A second reservation fails closed.

The Generator writes only beneath `reviews/.harness/assignment/staged/<receipt_id>/`, then supplies a strict write plan to `assignment_writer_commit.py`. The commit revalidates the receipt, live role contract, exact reserved path/mode set, reservation token, target preimages, staged paths, and hashes. It prepares recoverable copies, journals and publishes the complete target set, writes the publication-result sidecar, and only then atomically moves `reserved` to `consumed`. A handled partial failure rolls back; an unclean interruption remains journaled and resumable with the exact plan. `append` targets must be staged as strict extensions of their reserved preimages. Cancellation uses `assignment_receipt_invalidate.py`, which atomically moves a `ready` or `reserved` receipt to `invalidated`.

One project-wide transition claim serializes receipt and target leases. A second live receipt cannot reserve the same target, and a completed target cannot be republished from the same phase-state snapshot. Transition claims have no implicit timeout: residue from an unclean termination fails closed. Inspect it with `assignment_receipt_recover.py`; clearing it requires the explicit `inspected-receipt-states-and-journal` acknowledgement and archives the stale claim as evidence.

The role field is an orchestration assertion enforced by the wrapper, not cryptographic identity. Hosts must still dispatch the Generator role named by the receipt. Verification reports stable `APG-*` blockers for missing, stale, copied, reserved, replayed, consumed, invalidated, wrong-target, wrong-role, wrong-token, and wrong-path cases. Hash drift requires a new gate run and a new receipt; an old receipt is never refreshed or copied in place.

## 4. Native auto-walk and approval stops

`/run-draft` derives one active target by running `python scripts/assignment_milestone_checkpoint.py derive --project-root <project-root>`. It gates and dispatches only the returned deliverable. The Planner does not reimplement the first-non-accepted predicate in prose. After accepted M5, derive returns `{"status":"COMPLETE","milestone":null,"action":null}`; the lifecycle has no active authoring target, and the operator validates or reports the completed run rather than dispatching another write.

The same public command owns the lifecycle transaction:

1. `begin --milestone M2|M3|M4|FINAL` consumes the ready predecessor F9 and starts the successor atomically. M3, M4, and FINAL bind the five stable reader-policy/profile pins at this boundary.
2. After `assignment_writer_commit.py` publishes the scoped Generator result, `record --milestone <M1-M4|FINAL> --receipt <consumed-receipt> --checkpoint <structured-checkpoint>` validates the receipt/result/live bytes and records the deliverable plus adjudicated feedback in one state-last write. Public FINAL requires both `milestones/M5_final_paper.md` and `submission_bundle/final_manuscript.md`; its checkpoint says ledger milestone `M5`. The checkpoint schema and authoring shape are `schemas/assignment_milestone_checkpoint.schema.json` and `templates/assignment_milestone_checkpoint.json`.
3. `accept --milestone <M1-M4|FINAL> --checkpoint <same-checkpoint> --approval-evidence <structured-approval>` requires a current-byte, project-local explicit approval. M4 additionally requires `--policy-evidence <current-policy>` after convergence. FINAL instead requires `--terminal-evidence <structured-M5-evidence>` per `schemas/assignment_terminal_evidence.schema.json`; it binds the terminal round, Check 8, F7/F8, G.4, ship signoff, reflection, deterministic findings, convergence, consumed FINAL receipt/result, and export provenance. The command publishes F9 first and `phase_state.json` last; FINAL uses `M5_terminal.json` with `to_milestone: null` and sets both terminal fields only after the prospective full-run terminal check passes. Authoring shapes are under `schemas/` and `templates/` with matching assignment names.

M4 has one intentional timing distinction. `begin M4` records only `profile_path`, `profile_sha256`, `resolved_sha256`, `attestation_view_pin`, and `exemplar_view_pin`, because no scoped manuscript bytes exist yet. The first successful `record M4` transaction must add the deliverable and `manuscript_sha256`, `phase`, and `cycle_id` atomically. An initial assembly uses `phase: Ph1`; this does not authorize acceptance. `accept M4` remains blocked until every in-scope section is `Ph3_converged` and the retained Check 8/phase gates pass.

At M1, M2, and M3, the Planner stops for explicit user approval after the record checkpoint. Only that approval permits the acceptance/F9 transaction. The invocation ends after the transaction; a later invocation derives and begins the next target. No file, elapsed time, user silence, or phase advancement counts as milestone acceptance.

Before the M3→M4 transaction, the Planner creates and binds current wiki-grounding evidence or records an authorized opt-out. M4 therefore becomes reachable only after three distinct acceptance checkpoints and the grounding gate. Legacy projects do not enter this walk until their migration boundary and acceptance evidence have been adjudicated.

Milestone transactions use a separate no-TTL claim at `reviews/.harness/milestones/claims/transaction.lock`; they never reuse the assignment receipt lock. An unclean claim requires inspection of `phase_state.json` and the lifecycle journal, followed by `assignment_milestone_checkpoint.py recover --acknowledgement inspected-milestone-state-and-journal`. Recovery refuses a live local process and fails closed on a foreign-host claim pending separately verified administrative coordination. For a proven-dead local claim it writes collision-resistant, exclusive archives for the claim and any canonical F9 packet not bound as ready/consumed by authoritative state; it does not silently delete or overwrite crash residue.

## 5. Format and export authority

Canonical drafting remains in the project's declared source format, normally Markdown. Formatting or exporting a professor copy is a separate action. The harness must not create, upload, or edit a professor-facing DOCX, PDF, or Google Doc unless the user explicitly requests that action.
