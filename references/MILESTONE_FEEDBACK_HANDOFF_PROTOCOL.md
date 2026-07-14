# Milestone Feedback and Handoff Protocol

## 1. Status and scope

**Status.** This protocol is the canonical package contract for M1-M5 deliverables, feedback, adjudication, approval, lineage, reopening, and handoff evidence. It applies to native projects and to legacy projects only after an explicit migration boundary has been approved.

**Scope.** The protocol governs project-level lifecycle records stored under `reviews/phase_state.json.milestone_framework`. It does not replace the section-level Lifecycle-Phase Ladder in `PHASE_PROTOCOL.md`. `reviews/phase_state.json` remains the only lifecycle state authority; no milestone ledger, generated Markdown file, F9 packet, plan, report, or checklist may become a second state authority.

Grounding, provenance integrity, and root filesystem-integrity rules are non-overridable. The Planner is the sole lifecycle-state writer and must use the atomic-write and concurrent-change checks already required for `reviews/phase_state.json`. Validators, renderers, the Evaluator, the Generator, and the Reflector are read-only with respect to milestone state.

## 2. Orthogonal milestone and phase axes

Milestones and phases are orthogonal. Milestones name project deliverables and accepted handoffs. Phases name the revision/readiness state of the active artifact or sections. M1-M3 normally execute within Ph1; M4 spans Ph2-Ph3; M5 closes at Ph4. Neither vocabulary supersedes the other.

The normal coordination is:

| Milestone | Project deliverable | Normal phase binding |
|---|---|---|
| M1 | Project Memo | Ph1 |
| M2 | Annotated References | Ph1 |
| M3 | Structured Outline | Ph1 |
| M4 | Paper Draft | Ph2-Ph3 |
| M5 | Final Paper | Ph4 |

Phase advancement never proves milestone acceptance by itself. Milestone acceptance never proves that a section satisfies a phase gate. Cross-axis gates must test both authorities without collapsing either axis.

## 3. Authority and precedence

Within the non-overridable boundaries above, milestone content and form follow this order:

1. Current user instruction.
2. Venue requirements.
3. Advisor, instructor, or committee requirements.
4. Project-local `AGENTS.md`, `CLAUDE.md`, `directives.md`, and the declared project profile.
5. This protocol and `PHASE_PROTOCOL.md` within their respective axes.
6. General package defaults.

A higher-authority specialization may change format, add exit criteria, map a venue-named artifact to an M1-M5 semantic role, narrow scope, or authorize `not_applicable` with a reason and substitute evidence. It may not relabel a control as a deliverable, change schema meanings, fabricate or reclassify provenance, erase history, bypass Grounding or filesystem-integrity rules, or waive a blocker without an append-only authorized override.

An authorized override records the rule, scope, authority, rationale, timestamp, affected milestones and handoffs, substitute evidence when applicable, and revalidation obligations.

## 4. Milestone deliverable contracts

Each M1-M5 record requires `purpose`, `status`, `applicability`, `required_inputs`, `exit_criteria`, `artifacts`, `feedback_records`, `approval`, `handoff`, and `dependency_state`. Exactly one project-level `primary_lineage` identifies the accepted chain.

Framework mode is `native | legacy`. Applicability is `applicable | not_applicable`.

Milestone status is one of:

`not_started | in_progress | feedback_pending | revision_required | accepted | reopened | superseded | not_applicable | legacy_unverified`

Approval status is `pending | approved | rejected | reopened | not_applicable`. Handoff status is `not_ready | ready | consumed | needs_revalidation | not_applicable`. Dependency state is `current | needs_revalidation | not_applicable`.

The normal contracts are:

| Milestone | Purpose | Required handoff output |
|---|---|---|
| M1 Project Memo | Freeze the problem, intended readers, thesis, scope, questions, and success criteria. | M1-to-M2 packet identifying fixed scope and source needs. |
| M2 Annotated References | Establish source roles, evidentiary licences, limits, gaps, and reserve material. | M2-to-M3 packet mapping claims and questions to licensed evidence. |
| M3 Structured Outline | Convert thesis and evidence into executable argument architecture. | M3-to-M4 packet fixing section purposes, moves, sources, guardrails, and open debts. |
| M4 Paper Draft | Execute the complete argument at review-ready depth. | M4-to-M5 packet binding the full draft and adjudicated review findings. |
| M5 Final Paper | Resolve final findings and certify current manuscript and released export bytes. | Terminal packet binding approval, manuscript identity, export provenance, and residual risks. |

Plans, revision plans, gates, checklists, reviews, reports, and derived views may control or evidence progress but cannot satisfy a milestone deliverable slot. M4 and M5 may use the same canonical manuscript path at different maturity depths; each accepted state binds the exact current manuscript path, SHA-256, byte count, and verification time. Changed bytes make the prior approval historical and the current binding stale.

## 5. Artifact roles and lineages

Every registered artifact has exactly one role:

`deliverable | transition_control | evidence | derived_view | export`

- `deliverable` is the project artifact the milestone exists to produce.
- `transition_control` is a plan, gate, checklist, or other control over movement.
- `evidence` records review, feedback, adjudication, approval, or validation.
- `derived_view` is reproducible human-readable output from authoritative state or evidence.
- `export` is a rendered or packaged representation of an accepted deliverable.

Every artifact also has a `lineage_id`. Multiple active candidates within a milestone require distinct lineage identifiers; filenames, directories, timestamps, and apparent similarity do not establish ancestry. `supersedes` and predecessor bindings must be explicit. Archive and live artifacts never auto-merge. Exactly one project-level `primary_lineage` may supply the accepted M1-M5 chain.

For M4 and M5, the primary-lineage `deliverable` must be a manuscript artifact. A transition control, evidence artifact, derived view, or export cannot be the sole deliverable.

## 6. Feedback provenance and adjudication

Feedback records use exactly one evidence class:

`direct_milestone_feedback | retrospective_application | harness_review_evidence | cross_cutting_guidance`

`direct_milestone_feedback` is contemporaneous attributable feedback on the named milestone. `retrospective_application` applies later feedback or principles to earlier work without rewriting that evidence as contemporaneous. `harness_review_evidence` covers Planner, Evaluator, Reflector, deterministic, or external-verifier review evidence. `cross_cutting_guidance` applies across milestones or projects.

Every record binds `feedback_id`, evidence class, source path and SHA-256, source actor, source and target milestones, receipt time, lineage, blocking status, disposition, rationale, and successor effect. Disposition is one of:

`pending | accepted | partially_accepted | rejected | deferred | informational`

Every blocking record must be adjudicated before its handoff can become ready. Direct external feedback is not mandatory at every milestone; an explicit truthful gate is mandatory. The gate may record received and adjudicated feedback, feedback not requested, unavailable history under an approved legacy boundary, or authorized non-applicability. During Ph1 the Evaluator is dormant: Planner checks, user/advisor responses, and deterministic evidence must retain their real actor and evidence class and must never be labeled Evaluator feedback.

## 7. F9 handoff evidence

F9 is a machine-readable JSON evidence family stored under `reviews/.harness/milestones/`, normally as `M1_to_M2.json`, `M2_to_M3.json`, `M3_to_M4.json`, `M4_to_M5.json`, and a terminal M5 packet. F9 is evidence, not lifecycle state. `reviews/phase_state.json` binds each packet path and SHA-256.

An F9 packet records `artifact_family: F9`, contract version, project, lineage, from/to milestone, predecessor packet binding except at M1, deliverable path/hash/bytes/role, inputs consumed, decisions frozen, feedback dispositions, open debts, next-milestone instructions, and approval authority/evidence/time. Adjacent packets use `to_milestone: M2 | M3 | M4 | M5`; the terminal M5 packet uses `to_milestone: null`. A handoff cannot become `ready` without approval evidence. The successor must record consumption before dependent work can claim a ready chain.

An F9 Markdown rendering, if produced, is a `derived_view`; it carries its source binding, generation time, and a do-not-edit marker.

## 8. Reopening and downstream staleness

Reopening appends history; it never edits an old approval into a new one.

1. The Planner appends `milestone_reopened` with actor, reason, scope, lineage, and old/current content bindings.
2. Each dependent handoff becomes `needs_revalidation` and receives a `downstream_stale` event.
3. The Planner records an impact adjudication for each downstream milestone: `revalidated`, `reopened`, or `superseded` by an explicit lineage.
4. Revalidation records new evidence and bindings; reopening records required work; supersession preserves the displaced lineage.
5. M5 cannot be accepted while any upstream dependency is stale.

Changed accepted bytes trigger the same stale-dependency behavior. The validator reports the block; it does not auto-demote phase state. Planner and the authorized user decide the phase and milestone recovery path.

Milestone event types are:

`milestone_started | feedback_recorded | feedback_adjudicated | milestone_accepted | handoff_ready | handoff_consumed | milestone_reopened | downstream_stale | downstream_revalidated | milestone_superseded | authorized_override | migration_hold | migration_accepted`

The append-only `milestone_framework.events[]` array is part of the sole `phase_state.json` authority. Every event carries `sequence` (unique, contiguous from 1), a full RFC3339 UTC `timestamp` (`YYYY-MM-DDTHH:MM:SS[.fraction]Z` only), `event_type`, `milestone`, `lineage_id`, `actor`, `authority`, non-empty `reason`, optional exact-byte `evidence_path` + `evidence_sha256`, `caused_by_sequence`, and typed `bindings[]` (`artifact`, `feedback`, `approval`, `handoff_packet`, `override`, `migration`, `previous_content`, or `current_content`). `downstream_stale` causally references an earlier reopened milestone on the same lineage and strictly upstream of the affected milestone; `downstream_revalidated` references the stale event for the same affected milestone and lineage, preserving that root chain. Other events carry `caused_by_sequence: null`. Every status (`not_started`, `in_progress`, `not_applicable`, `accepted`, `reopened`, `superseded`) and every handoff projection is justified by its latest relevant event; an old acceptance or handoff cannot justify reset work without a later reopen/start/override/migration event. Acceptance binds the current deliverable and approval evidence; each feedback-recorded/adjudicated event binds the current feedback source path/hash; handoff events bind the current F9 hash. Full historical replay beyond current-state justification remains a future migration/replay extension; validators already enforce ordering, subject-aware causality, current-state consistency, and exact-byte bindings.

## 9. Gate outcomes and exit semantics

Applicability and readiness are separate. Validators and compatible preflight gates use:

| Outcome | Meaning | Exit |
|---|---|---:|
| `READY` | A native applicable contract satisfies every predicate. | 0 |
| `LEGACY_READY` | An explicit approved migration record grandfathers already-crossed work; warnings remain visible. | 0 |
| `NOT_APPLICABLE` | A higher-authority record supplies reason, scope, and substitute evidence. | 0 |
| `MISCONFIGURED` | State is missing, contradictory, stale, malformed, or only implicitly absent. | 4 |

Usage errors exit 1. I/O or parse failures exit 2. Authorized N/A and no-op outcomes succeed; absence never silently means legacy or N/A.

## 10. Native projects

A project bootstrapped under this contract uses `mode: native`, declares exactly M1-M5, begins M1 as `in_progress`, and begins M2-M5 as `not_started`. File presence never implies acceptance. Each milestone becomes accepted only after its deliverable, feedback gate, adjudication, approval, exact-byte binding, and F9 handoff satisfy this protocol.

The native milestone namespace lives only inside `reviews/phase_state.json`. Project `AGENTS.md`, status notes, and lifecycle summaries link to the authority or a generated view; they do not maintain parallel status.

## 11. Legacy migration

Legacy migration is discovery-first and dry-run-first. It inventories ledgers, candidate deliverables, controls, feedback, exports, paths, and lineages; emits an evidence matrix and proposed graph without writing canonical state; and creates a HOLD for every ambiguity. A user-authorized adjudication selects the primary lineage, applicability, completed-through boundary, and disposition of each hold before any atomic canonical write.

Migration preserves raw artifacts and archives the prior ledger with exact hashes. It must be idempotent and produce a rollback manifest. Divergent archive/live candidates never auto-merge. Missing historical feedback is recorded as `not captured under prior contract`; feedback, approvals, lineage, or completion are never fabricated. Already-crossed work receives `LEGACY_READY` only through an explicit approved migration record.

## 12. Derived views

Human lifecycle summaries are deterministic views of `reviews/phase_state.json` and accepted F9 evidence. A lifecycle view records `generated: true`, `derived_from`, `source_sha256`, and `generated_at`; its body begins `DO NOT EDIT: generated lifecycle view`.

Derived views never satisfy deliverable slots, own lifecycle status, or override source state. Source-hash mismatch is drift and requires regeneration after the authoritative state is corrected.

## 13. Exemplar governance

Projects do not self-declare exemplar status. The sole credential authority is the project-external package registry at `references/milestone_exemplars.json`; its empty state is exactly `{"schema_version":"1.0.0","entries":[]}`. Absence from the registry is normal and does not affect ordinary `READY` or `LEGACY_READY` outcomes. A project-local claim never substitutes for registration, even when the project has a valid registry entry.

Each registry entry is strict and closed. It records one canonical absolute `project_path`, one allowed `exemplar_class`, explicit `approval_authority`, approval evidence path and SHA-256, current package `validator_version`, class-appropriate `validator_outcome`, a role-typed array of validator/evidence path and SHA-256 bindings, a strict RFC3339 UTC `registered_at`, and the current `reviews/phase_state.json` SHA-256. Duplicate registrations for one canonical identity and registrations that assign both classes to one identity are invalid. All registered evidence paths are project-relative, contained, current-byte hash-bound, regular non-reparse files. A custom registry may be injected by the validator CLI for maintenance and tests, but the registry file itself must also be a regular non-reparse file.

`clean_lifecycle_exemplar` requires `mode: native`; accepted, approved, dependency-current M1-M5 records; consumed M1-M4 handoffs; a ready or consumed terminal M5 packet; current milestone- and phase-validator evidence; a generated lifecycle view whose source hash is the current ledger; a full release-gate pass; and an independent replay. `legacy_migration_exemplar` requires `mode: legacy`, an approved migration boundary, current milestone and phase validation with `LEGACY_READY`, and separately hash-bound migration approval, report, commit, and rollback manifest evidence. Registration records evidence; it does not rewrite ledger outcome or historical provenance.

Self-declaration detection is deliberately bounded. The validator inspects the machine ledger and only the declared project authority/status surfaces `AGENTS.md`, `CLAUDE.md`, and `reviews/lifecycle_state.md`. It recognizes exact lifecycle credential keys/values, exact credential headings or status fields, and normative project-is/designated/registered-as claims for `portfolio exemplar`, `reference implementation`, `clean_lifecycle_exemplar`, or `legacy_migration_exemplar`. It does not scan manuscripts or arbitrary reviews, where ordinary disciplinary uses of “exemplar” or “reference implementation” are not lifecycle claims.

For a registered clean exemplar, the lifecycle-view evidence hash is also the exact-byte derived-view binding. Any manual edit therefore emits both `MF-EXEMPLAR` and `MF-DERIVED`; editing or deleting the local claim cannot create or restore the external credential.

## 14. Validator codes

| Code | Predicate | Failure |
|---|---|---|
| `MF-STRUCTURE` | M1-M5 records contain the required contract fields. | BLOCKER |
| `MF-ROLE` | M4/M5 primary deliverables are manuscripts, never plans, checklists, or gates. | BLOCKER |
| `MF-CANON` | Canonical paths exist and obey project canonical-source rules. | BLOCKER |
| `MF-BINDING` | Accepted artifact and packet hashes and byte counts match current bytes. | BLOCKER |
| `MF-HANDOFF` | Successor work consumes an approved or authorized predecessor handoff. | BLOCKER |
| `MF-FEEDBACK` | Feedback is typed, attributable, hash-bound, and blocking items are adjudicated. | BLOCKER |
| `MF-LINEAGE` | Active candidates have distinct lineages and exactly one primary lineage. | BLOCKER |
| `MF-REOPEN` | Drift or reopening creates append-only history and downstream staleness. | BLOCKER |
| `MF-PHASE` | M4/M5 state agrees with phase, MCR, G.4, and terminal conditions. | BLOCKER |
| `MF-POLICY` | Reader intent, resolved policy, and current-hash accessibility evidence form one chain. | BLOCKER |
| `MF-EXPORT` | A released export exists and binds the accepted manuscript. | BLOCKER |
| `MF-DERIVED` | Generated lifecycle views match the current ledger hash. | MAJOR |
| `MF-OVERRIDE` | N/A or waiver has authority, reason, scope, evidence, and an event. | BLOCKER |
| `MF-STATUS` | Maintained prose does not claim authority or contradict the ledger. | MAJOR |
| `MF-EXEMPLAR` | Exemplar registration satisfies class-specific external evidence. | BLOCKER |

Malformed but parseable state must produce controlled findings, never an uncaught exception.
