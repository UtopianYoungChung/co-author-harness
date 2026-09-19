# Project-independent task workflow

This is the shared execution route for ordinary named passes, new drafting and
existing-manuscript revision. Full lifecycle and governed laboratory operations
remain in `FULL_RUN_CONTRACT.md`. Native project assignment/publication machinery
is reused only for its actual governed operations; never invent project state to
make an ordinary task pass those gates.

## Routing and rules

- A bounded read-only named pass declares `adhoc_review`. Read the named skill,
  `GROUNDING_PROTOCOL.md` and the rule files that skill selects; resolve these
  paths from the installed package. Read actual pasted text or file bytes and
  execute the mechanical and judgment checks in the skill. Report input identity,
  requested scope, counts, check applicability, substantive locator-bound findings
  and bounded proposals. A clean result must explain the checks performed.
- Ordinary drafting/revision declares `project_independent` and follows the native
  child loop below. No pre-existing project, graph, repository or research
  governance installation is required. State created after invocation is task
  evidence, never reconstructed milestone history.
- Explicit full-lifecycle, milestone, finalization, acceptance or promotion intent
  retains its governed prerequisites. Never silently downgrade it. Optional venue
  or project context refines the rules under established precedence. An explicitly
  supplied invalid authoritative binding is a binding error.
- Bind rule paths, SHA-256, byte lengths and package version; identify files
  actually read separately from rules applied. User exclusions win over default
  fire tables. Chung voice is optional and is never activated by a mandatory read.
  For explicit Chung-only analysis, run its actual named skill without a project.

## Native host boundary

Python binds, sequences and verifies evidence. It does not generate cognitive
role execution. The host caller invokes its native child-agent tools, waits for
finished outcomes and retains original execution references. A script producing
role JSON or a coordinator echoing fixed prose is not a child agent.

Every host binds through one registered trace adapter in
`scripts/piw_native_host.py` (`ADAPTERS`): `codex-jsonl` (Codex native spawn,
followup/message, wait/status and returned final outputs), `hermes-hooks-jsonl`
(Hermes lifecycle hooks, `HERMES_DESKTOP.md`), and `claude-code-jsonl` (Claude
Code, Claude Desktop, Cowork and Agent SDK session logs, `CLAUDE_CODE_HOST.md`).
Pass the bound role request to a real child and wait for completion before ingest.
Never pass model/provider overrides where dispatch inherits a pin. A host lacking
real children, an inspectable original trace, or a registered adapter returns
`PIW-HOST-CAPABILITY-UNAVAILABLE` for drafting/revision. Independent read-only
passes continue. A new host requires its own adapter module and fixture suite;
source-path execution on one host is not installed-cache, startup, or live
qualification on another, and adapter fixtures never establish live-host proof.

Original host logs are the trust boundary, not a cryptographic attestation.
Verification must check parent-child linkage, execution/turn identity, finished
outcome, the exact returned result and freshness against those logs. Keep the
original trace references for independent inspection. An editable copied receipt,
role label, path-presence check or completion=true flag alone proves no execution.

## Role responsibilities and sequence

### planner

The caller may be Planner. Bind the conceptual brief or original file bytes,
requested section/span, source access, profile, exclusions, check applicability,
authorized output and a correction limit (three correction cycles by default).
For revision, wait for independent Evaluator diagnosis before writing the bounded
revision plan. Map each requested change and diagnosed defect to allowed edits.
Mark unavailable optional checks as limitations; required unavailable checks hold
completion. Pass the same bindings and exclusions in every child request.

### generator

A distinct native child reads the brief, selected rules and actual input. For a
new draft, write substantive prose answering the brief. For revision, repair only
the planned scope, preserving terminology, argument and citations unless the user
requested those changes. Preserve untouched input byte ranges exactly, including
line endings. Proposal-only work writes the candidate to task output, leaving the
input untouched. Return the output identity and a concrete change summary. Never
certify the prose or impersonate an Evaluator/Reflector.

### evaluator

A separate native child diagnoses existing text before any revision plan, with
locators, reasons and bounded remedies. After each generation it reads and reviews
the exact candidate bytes against the request, plan and applicable rules. Verify
scope preservation and exclusions. Report actual checks, findings and limitations;
an empty findings list is valid only with substantive successful checks. The
Generator cannot serve as Evaluator, even under another role label.

### reflector

A third distinct native child performs required task closeout on the final
reviewed candidate and the actual preceding evidence. Read the Grounding Protocol
and check source/claim traceability, computed metrics, rule references, scope,
exclusions and unresolved findings. It does not edit prose or grant acceptance.
Any new material finding reopens correction and independent evaluation, then a
fresh closeout. No-change completion needs substantive diagnosis, review and
reflection explaining why unchanged bytes satisfy the request.

### Correction and delivery

New drafts run Planner -> Generator -> Evaluator -> Reflector. Existing manuscripts
run Evaluator diagnosis -> Planner revision plan -> Generator -> Evaluator ->
Reflector. Findings return to Generator; each new candidate returns to Evaluator.
Exhausting the correction limit ends `needs_revision`, never task completion.
Execution errors and partial analysis are reported separately.

Only the completion verifier may derive task_complete from inspected evidence.
It binds input/final hashes and lengths, scope, rules/profile/exclusions, real
finished child references, revision diagnosis, plan/generation/evaluation/reflection,
applicable checks and exact delivery bytes. Missing/stale/replayed/wrong-run or
self-review evidence, failed dispatch and unresolved required findings refuse.
A successful task has `lifecycle_terminal=false` and `research_acceptance=false`.
Deliver exactly the reviewed bytes with a concise change summary and limitations.

## Sources and destinations

Keep centroid-source, centroid-bind and centroid-check distinct. The binder's
`GRAPH-SEMANTIC-INELIGIBLE` result describes graph capability, not prose quality.
Use `centroid-sentence-logic` with actual admitted source passages and locators
where requested, preserving its source-membership, page-window and warrant-layer
policies. Its script exposes sentence pairs and mechanical signals; the invoked
role must perform the substantive judgment. A binding packet is not a review.
Missing source access holds dependent checks only. Never invent excerpts or pass
an empty binder as a successful source judgment.

Resolve ordinary task output from an explicit authorized directory or the host's
task-local area. Input files are read-only unless an explicit apply transaction
separately authorizes them. Protected governed paths remain protected regardless
of scope labels; ordinary task state cannot authorize lifecycle terminal,
promotion, source admission or direct Workbench writes. Exact private shipments
and governed staging continue under destination capability policy.

## Coordinator commands for host callers

### Portable evidence and timing

After successful live verification, export an evidence closure with
`python scripts/piw_archive.py export --piw-session <session> --destination <new-authorized-directory>`.
Retain the returned manifest SHA-256 separately. Verify a relocated copy with
`python scripts/piw_archive.py verify --manifest <archive/manifest.json> --sha256 <retained-hash>`.
Verification reads only explicit source-to-archive mappings, preserves original
path identities, and replays shared role and trace checks. Missing mappings,
changed artifacts and incomplete trace prefixes fail. It reports
`archived_evidence_verified`, with live execution, host qualification and task
completion flags false. Export before original rules or evidence change; a stale
session cannot gain a valid archive through a copied completion flag.

`python scripts/piw_metrics.py --piw-session <session>` reports observed role timing
and prefix sizes. Missing context/usage data and unrecorded failures remain null.
The artifact benchmark and human-reference requirements are documented in
`docs/evaluation/research-artifact-benchmark.md` at the package root.

### Task execution

Resolve `scripts/` from the loaded package, not from the input directory.
The public skill's caller performs these steps without asking the user to build
state. Commands below are evidence plumbing; the native child performs the work.

```text
python scripts/piw_session.py bind-pass --pass-name grammar-mechanics-pass --text "<pasted text>"
python scripts/piw_session.py bind-pass --pass-name sentence-level-pass --input-path <file>
python scripts/piw_session.py open --outputs-root <authorized task area>
python scripts/piw_session.py open --ingress mss_revision --mss-path <file> --outputs-root <task area>
python scripts/piw_coordinator.py start --piw-session <session> --request-json <request.json>
python scripts/piw_coordinator.py next --piw-session <session>
python scripts/piw_coordinator.py plan --piw-session <session> --plan-json <plan.json>
python scripts/piw_coordinator.py ingest --piw-session <session> --result-json <child-final.json> --host-evidence <host.json>
python scripts/piw_coordinator.py deliver --piw-session <session> --destination <final.md>
python scripts/piw_completion_guard.py verify --piw-session <session>
```

`bind-pass` emits `bound_not_reviewed`. The caller must then read the named skill
and rules and perform the actual review. This command alone cannot satisfy a pass.
Use `--help` for input, venue, explicit authoritative-binding and exclusion options.

For `start`, request JSON binds `brief`, `requested_scope` (a description, plus
`section` for a bounded Markdown section), selected `passes`, `profile`,
`exclusions`, `required_checks`, optional source excerpts/venue/project context,
`proposal_only` and `max_corrections`. Each required check has an `id` and
`required` boolean; a source-dependent check also declares `source_required`.
With bound sources, the default grounding check is source-dependent. Its default
`verification_level` is `attribution`; a check explicitly limited to citation
identity may use `bibliographic` and cannot clear attribution support. An
attribution `pass` requires nonempty `source_support` rows containing `source_id`,
`source_locator`, `quote`, `claim` and `status: supported`. IDs and locators must
match the bound excerpts; quotations must occur in those excerpts and claims in
the reviewed target. The native Evaluator/Reflector judges actual support and
qualifications; substring validation establishes provenance, not entailment.
Contested, unsupported or unavailable passages cannot clear the check.
Substantive review of a manuscript containing citations or a bibliography also
requires the automatic `bibliography` check and a complete `bibliography_review`
object in both Evaluator and Reflector results, following
`CITATION_DISCIPLINE.md` §6. This applies even if callers supply narrower
`required_checks`; a single attribution row cannot clear the bibliography.
Set `review_scope: prose_only` only for an explicitly prose-only task; completion
then reports `bibliography_status: not_assessed_prose_only`. New references or
changed citation contexts reopen coverage. Numeric renumbering can reuse
unchanged identities and attachments, while native final-byte review remains
required. Unresolved evidence permits planning and draft correction but blocks
satisfactory completion of dependent substantive checks.
The default correction limit is three. No-change revision still follows the full
revision sequence and produces separately reviewed unchanged candidate bytes.

The host object names the registered `adapter`, `subagents_available: true`,
`logs_root` and `parent_log` from the actual running host (Codex: `codex-jsonl`;
Hermes: `hermes-hooks-jsonl`; Claude Code and Claude Desktop: `claude-code-jsonl`).
These declarations do not prove execution. `ingest` requires the child's original
`child_log`, actual `agent_execution_id` and `turn_id` (on Claude Code the
`agentId` and the dispatching `tool_use` id); the verifier inspects that
parent/child trace. Every emitted request also binds `role_prompt`
(`agents/<role>.md`), `skill_bodies` (the applied `skills/*/SKILL.md`) and
`package_root`, so a child on any host reads the same role file and skill
bodies. Never point this boundary at synthetic integration logs for live
qualification.

When `next` returns `awaiting_native_child`, read the returned `request_path` and
validate `python scripts/full_run_contract_check.py scope --parent-scope
project_independent --child-brief <request_path>`, then invoke the host's native
child tools with that exact request. The JSON request declares its top-level
`run_scope`; plain-text dispatch wrappers also declare
`run_scope: project_independent`. Wait until the child finishes. The
child's final response is the substantive result JSON described in the request,
including its actual session identity, request hash, inspected target, actual rule
reads, applied passes and exclusions. Copy the exact final result from the original
host completion event; do not replace it with the caller's summary. Ingest it,
then obey the next state. The caller supplies the revision plan only after
`diagnosis`; it does not manufacture the diagnostic result.

`ready_to_deliver` permits delivery verification, not a terminal claim. Delivery
writes only the final reviewed candidate and exports `completion.json` plus the
Evaluator view. `needs_revision` preserves unresolved findings. Required missing
work stays incomplete, and native dispatch/trace failures remain execution errors.
For hooks, `FRC_PARENT_SCOPE=project_independent` and `FRC_PIW_SESSION` identify
the validated task; direct tool writes stay confined to its task area. Exact
final delivery uses the coordinator's destination validation.
