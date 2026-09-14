# Project-independent harness workflow implementation work order

> For agentic workers: execute this order task by task using superpowers:subagent-driven-development or superpowers:executing-plans if available. The order is self-contained; a missing planning plugin is not a product prerequisite. Use actual subagents for bounded implementation review and the required live manuscript exercises. The producer must not commit or push, regardless of a skill's default commit instructions.

**Goal:** Make ordinary harness passes, new drafting, and existing-manuscript revision work without a pre-existing project, using actual rules and real subagent workflows, with an honest and reachable task-completion result.

**Architecture:** Keep reusable writing rules and task execution independent of project lifecycle state. Optional project bindings add context and governed operations retain their protections. Reuse existing substantive checks and role execution surfaces; replace the PIW stubs instead of building another receipt-only workflow.

**Tech stack:** Existing Python scripts, Markdown skills, JSON policies/schemas, and the executing host's real subagent tools. No new external model service or API credential requirement.

**Spec:** This work order contains Joseph's complete behavioral requirements and supersedes the narrower PIW proposal wherever it omitted them. Earlier Spec/Arch/ADV/IR packets are diagnostic evidence, not acceptance criteria that can reduce this order.

## 1. Assignment and boundaries

You are the implementing Codex session. Complete the implementation and producer verification on B:, then deliver a reproducible candidate to the original Codex review session. Do not stop after planning, scaffolding, documentation, or negative tests.

- Repository: `B:/Agents/platform/co-author-harness`.
- Expected origin: `https://github.com/UtopianYoungChung/co-author-harness.git`.
- Main is the only permitted branch. Do not create a branch. A detached verification checkout is permitted by repository instructions.
- The original Codex review session owns independent verification, commit, final release qualification and push. You must not commit, push, tag, release, or overwrite production plugin installations.
- Your internal reviewer helps validate producer work; it does not replace the original session's independent review.
- Do not alter model/provider pins or pass model overrides when dispatch inherits pinned profiles. An unavailable route is a capability failure, not permission to impersonate a subagent.
- Preserve unrelated work, governed research destinations, source authority, and user acceptance boundaries. Do not edit any real manuscript for the tests; use disposable synthetic fixtures.
- This order authorizes repair or replacement of the rejected PIW changes and the necessary shared harness surfaces. It does not authorize unrelated research/governance repairs.
- Use Windows-side reads and writes; explicit UTF-8 without BOM. Use `B:/Agents/governance/tools/safe_fs_update.py` for critical or long file writes. Verify exact bytes after writing.

Read workspace and package AGENTS instructions and `docs/agent-instructions/change-to-check-map.md`. During actual manuscript exercises, also load the required rule files, Grounding Protocol, orchestration, and applicable D-STYLE instructions. A mandatory file read does not authorize applying an explicitly excluded overlay.

## 2. Verified starting state and rejected implementation

Observed during work-order preparation; recheck before changing anything:

- HEAD: `ff13282105d1975fd287b0f234f4244500748cd9`. The old delivery names `d8e4ae487e4b306319c3b737c3baf5efab7cd68f`.
- Main was four commits ahead of the local origin/main reference. That is not a fresh remote attestation.
- Five tracked paths carry PIW edits: invocation_scope.py, full_run_contract_check.py, hooks/full_run_pretooluse_gate.py, full_run_enforcement_surfaces_smoketest.py, and skills/plugin-commands/SKILL.md.
- Untracked PIW code: piw_session.py, piw_coordinator.py, piw_completion_guard.py, piw_overlay_attach.py, piw_acceptance_smoketest.py; three run-*-piw skill directories; and _piw_acceptance_last_run.json.
- Old readiness marker: `releases/project-independent-workflow-2026-09-06/DELIVERY_READY.json`, SHA-256 `d1747fc1e578167e6aa585f8fafd2970460cd4da968bcffcc94f39ef972068bd`, 3173 bytes. Rejected.
- Old candidate ZIP SHA-256: `89243f82285c67832b33c02b72e6c2e086f986f82804ca6d457e4038ee21876b`.
- The old manifest declares full_run_contract_check.py hash `d0e2c2e9b3db75308e9a274b07296264f8e5bcd8f12beeae0aff6dbbeab0ae68`; the current file is `156bc1a73f49d5ea5cd993ff53f13cad00a358ed841c14ff7b0ceefdb97b4cc1`. HEAD ff132821 includes a separate locator-object validation change in that file. Preserve it; do not restore the old file wholesale.
- piw_coordinator.py:58 writes role receipts itself; :70 onwards writes fixed draft text; :142 writes "Revised staging bytes." No actual manuscript role execution is demonstrated.
- piw_completion_guard.py:56 has no successful task-completion path.
- Public run-draft/run-iterate still require project binding; their Reflector step says "may probe". New PIW aliases do not repair ordinary invocation.
- command_surface_check.py exits 1 with four blockers; skill-check.py exits 1 with two. New aliases are not consistently registered.
- piw_session.py hardcodes B:/Agents/outputs as its default. A globally installed plugin must resolve portable task-local output without depending on this machine.
- Existing centroid-sentence-logic already supports admitted passages when the graph is ineligible. Inspect and reuse that work; do not falsely report all graph-independent analysis absent.
- The old 10/10 matrix measures helpers and weak assertions. ADV/IR confirm soft acceptance tests and untested Hermes. Refusal probes are not proof that a useful task can finish.

Preflight during preparation returned exit 1: a Wiki grounding-note error, a QE containment-guard failure, and an R9 role/config check failure; one run also exposed a cp949 subprocess decoding error. Re-run in an explicit UTF-8 process and record exact results. Diagnose applicability; do not repair unrelated Wiki, governance or model configuration to make the dashboard green. An applicable unresolved gate holds the dependent operation, not all independent implementation work.

Evidence roots, for consultation only:
- `B:/Agents/outputs/measurement/as-is-lane/PIW-20260906-SPEC-ASIS/`
- `B:/Agents/outputs/architecture/proposal-lane/PIW-20260906-ARCH-TOBE/`
- `B:/Agents/outputs/measurement/PIW-20260906-ADV-FALSIFY/`
- `B:/Agents/outputs/measurement/PIW-20260906-IR-SCORE/`

## 3. Product contract

### R1. Ordinary standalone passes

A user can invoke an existing named pass on pasted text or a file in an empty folder. No Workbench, assignment contract, milestone history, semantic graph, repository, or research-governance installation is required for ordinary read-only analysis.

Use the packaged, predetermined rules. Identify the rule files actually read, their version/hash, input scope, performed checks, and substantive findings with locators. A clean result is allowed when the actual checks find no defects; a default empty list or binder packet is not a performed review. Do not force a four-role manuscript workflow onto a bounded read-only grammar audit.

Optional venue/project instructions refine the rules under the established precedence. Invalid supplied authoritative bindings must not silently disappear into a standalone fallback. An explicit governed lifecycle request must not be silently downgraded.

### R2. Public routing and portability

Fix existing public skills and natural-language routing, including sentence-level-pass, grammar-mechanics-pass, run-draft, run-iterate and run-reflection. Users must not discover special PIW names to obtain promised behavior.

Distinguish ordinary drafting/revision from explicit governed lifecycle/finalization intent. "Draft a short essay" alone must work without bootstrap; a named governed lifecycle operation retains its prerequisites.

A run may create minimal task-local working state after invocation. It must not require users to construct a project first. Resolve rules from the installed package and output from an explicit authorized directory or the host's task-local area. No hardcoded B: drive, username, Hermes home, or live research path in portable runtime behavior.

Keep host differences in a small documented dispatch boundary. Use the host's actual native subagent capability; do not build a general multi-provider framework or introduce API keys merely to obtain subagents.

### R3. New drafts

Planner/caller binds brief, scope, sources, output authority, required checks and exclusions. A real Generator subagent writes; a separate Evaluator subagent independently reviews the exact result. Findings return to Generator for correction and Evaluator rechecks changed bytes. A real Reflector performs a required closeout before task completion.

The caller may be Planner. Generator, Evaluator and Reflector must be real distinct execution contexts, with observable host execution identifiers and substantive outputs. A Python subprocess writing role JSON is not a cognitive subagent. The Generator must not certify its own prose.

### R4. Existing manuscripts

Bind the actual original bytes, SHA-256, byte length, encoding and requested section/scope. Read the manuscript itself; a pointer or seed receipt is insufficient.

Required sequence:
1. Independent Evaluator diagnoses the existing text within the requested scope.
2. Planner maps that diagnosis and the user request into a bounded revision plan.
3. Generator revises the specified material.
4. Independent Evaluator checks the revised bytes and scope preservation.
5. Corrections repeat when needed, with review of each new candidate.
6. Reflector closes the completed round; new material findings reopen correction/review.
7. Deliver exactly the final reviewed bytes, plus a concise change summary and limitations.

No invented M1-M3 history, accepts, F9 records, or bootstrap-as-history. Preserve terminology, argument and citations unless the user explicitly requests the relevant change. Preserve untouched sections byte-for-byte for bounded file revisions. Proposal-only requests produce proposed changes in an output artifact/chat without altering the input. Protected Workbench application remains a separate authorized transaction.

Bound correction attempts by an explicit run limit, with a default of three correction cycles after initial review. Exhaustion produces needs_revision with unresolved findings, never a pass. A no-change result is valid only after substantive diagnosis, review and reflection explain why no edit is required.

### R5. Task completion with positive and negative paths

Define task completion independently of scholarly CLEAN, milestone acceptance, lifecycle terminal status, release, installation and promotion. Task completion means the requested deliverable has been produced and all required work for that scope has finished with acceptable results.

Reuse existing schemas where adequate; extend them minimally. A completion record must bind:
- input and final output hashes/lengths and requested scope;
- selected rule/profile/exclusion identities;
- actual child execution references and their finished outcomes;
- initial diagnosis for revision, generation, independent evaluation and reflection evidence;
- check applicability, results and unresolved blocking findings;
- the exact final reviewed bytes and delivery location.

The verifier must inspect the bound evidence, not trust flags such as completion=true or a list of role names. Validate run identity, target, role separation, evidence freshness and hashes. Role labels alone are not independent execution evidence; retain host trace references for independent inspection.

A completed scoped task may still have lifecycle_terminal=false and research_acceptance=false. This must be a tested successful state. Required missing evidence, failed dispatch, missing reviewer/reflection, stale final bytes, unresolved blockers, wrong-run/replayed receipts, or role impersonation must prevent task completion.

Report execution errors, needs_revision and partial analysis distinctly. An optional unavailable check is an explicit limitation; a required unavailable check cannot be marked passed. If the host cannot execute subagents, return a precise capability failure for drafting/revision and keep unrelated standalone checks usable.

### R6. Centroid, sources and excluded overlays

Keep centroid-source, centroid-bind and centroid-check distinct. Preserve graph-semantic ineligibility as an honest graph capability result. Route an ordinary requested substantive check to predetermined rules or admitted source passages without requiring a completed project semantic corpus.

Reuse the existing centroid-sentence-logic/source-admission path where sufficient. Do not relabel a binding packet as prose judgment or replace source membership/warrant policies. Source-based claims require actual admitted passages and their locators/hashes. Missing source access holds only dependent checks; available independent checks continue with precise limits.

When the user excludes Chung voice, exclude it in Planner, Generator, Evaluator fire tables, corrections and Reflector closeout. Required file reads may still occur but must be recorded separately from applied rules. Do not silently re-enable it through a default evaluation table. Test both explicit invocation and exclusion.

### R7. Protect governed operations

Preserve protected destinations, source discipline, model pins, author acceptance, full-lifecycle validation, native project handling and publication provenance. Test ordinary authorized output outside a governed workspace and forbidden protected writes separately. Absence of governance must not block an ordinary read-only pass; presence of governance must not be bypassed by changing a scope label.

Do not rename unrelated scientific authorities or weaken the existing source/evidence publication repairs in ff132821.

## 4. Implementation sequence and file ownership

Paths below are relative to the repository. Each step finishes with a demonstrated behavior and reviewable diff. Extend an existing component when it covers the need; new files require a concrete missing responsibility.

### Task 1. Establish exact ownership and reproduce failures
- [ ] Record HEAD, origin, index/worktree/untracked inventory, and hashes before editing. Save the rejected PIW diff and distinguish it from unrelated committed/uncommitted changes.
- [ ] Read current routing, source rules and execution surfaces. Compare the existing graph-independent path with R6.
- [ ] Run the current structural checks and a bounded baseline probe. Record expected failures without accepting the old matrix as authority.
- [ ] Inspect which host tools can actually dispatch/wait/read subagents. Record capability evidence without changing pins.
- [ ] Create the new behavioral test fixtures specified below, with initially failing positive tests.

Read/repair candidates: scripts/piw_*.py, scripts/invocation_scope.py, scripts/full_run_contract_check.py, scripts/hooks/full_run_pretooluse_gate.py. Shared-file edits must preserve ff132821 changes.

### Task 2. Make public standalone routing execute the real rules
- [ ] Implement R1/R2 using existing skill rule bodies and package-relative rule resolution.
- [ ] Reconcile AGENTS.md, references/AGENTS.md, references/FULL_RUN_CONTRACT.md, references/AGENT_ORCHESTRATION.md, MANIFEST.md and affected public skills so startup instructions agree with runtime behavior.
- [ ] Remove or route the rejected PIW aliases consistently; do not expose a second incomplete product.
- [ ] Run AT01-AT03 and AT09-AT10 below.

Primary skills: skills/sentence-level-pass/SKILL.md, skills/grammar-mechanics-pass/SKILL.md, skills/run-draft/SKILL.md, skills/run-iterate/SKILL.md, skills/run-reflection/SKILL.md.
Rule reuse: references/bacon_2009_well_crafted_sentence_guidelines.md and the exact files routed by other invoked skills.

### Task 3. Implement real drafting/revision execution
- [ ] Replace fixed-prose and self-certification stubs. Wire actual host child execution and wait for completion; propagate failures.
- [ ] Implement R3/R4 sequencing, source/input binding, scoped output protection and correction loop.
- [ ] Keep Generator, Evaluator and Reflector responsibilities separate in agents/planner.md, agents/generator.md, agents/evaluator.md and agents/reflector.md.
- [ ] Run actual live AT04-AT06 and record host traces, including a real revision of the supplied fixture.
- [ ] Have a fresh internal reviewer inspect the produced text and dispatch evidence, not merely the filenames.

Inspect reuse before changing: scripts/assignment_dispatch_preflight.py, scripts/assignment_dispatch_claim.py, scripts/assignment_writer_commit.py, references/role_output_contract.json. Do not feed invented native project state into these components to make them accept standalone work.

### Task 4. Implement evidence-bound completion and source/overlay handling
- [ ] Replace unconditional refusal with R5's evidence-verified positive completion path.
- [ ] Implement missing/stale/replayed evidence checks and reject a Generator acting as its own Evaluator.
- [ ] Connect R6 to skills/centroid-pass/SKILL.md, skills/centroid-sentence-logic/SKILL.md, scripts/centroid_service.py, scripts/centroid_sentence_logic.py and affected fire tables only where needed.
- [ ] Ensure explicit Chung exclusion wins throughout every child brief and result.
- [ ] Run AT07-AT13. Include a real successful task completion and independently tampered copies that fail.

Do not create cryptographic claims that a self-written receipt authenticates a host execution. State the evidence/trust boundary and verify against actual host logs where available.

### Task 5. Integrate and qualify the candidate
- [ ] Reconcile references/policies/command_surface.v1.json, references/SKILL_REGISTRY.md, skills/plugin-commands/SKILL.md, catalog/manifest surfaces and affected hooks.
- [ ] Register new tests in the existing authoritative fixture mechanism. Replace weak PIW assertions; no new parallel acceptance authority.
- [ ] Run structural census, the full fixture corpus and applicable release qualification checks. Capture real exit status and final results.
- [ ] Exercise the candidate in a fresh Codex context with actual subagents and no project. Distinguish direct source use from isolated installed-candidate use and startup loading.
- [ ] Test supported additional hosts where available; record Hermes accurately if unavailable. No universal-host or full-installation claim from a Codex-only run.
- [ ] Produce the final delivery in section 7. Stop editing before writing readiness.

## 5. Acceptance matrix: fixed requirements, not a remappable rollup

Every row needs a fixture/request, command or host invocation, observed output, exit/completion status, evidence path/hash and verdict. Report unit, integration, live-host and independent-review evidence separately. Do not replace these rows with easier helper tests.

| ID | Exercise | Required observation |
|---|---|---|
| AT01 | Empty non-project folder; grammar pass on pasted text: "The results shows a difference. Each participant have a code." | Identifies both agreement errors with locators/rules; no bootstrap/graph requirement; does not invent sources. |
| AT02 | File with "The model records requests. Therefore, every user has institutional authority." Run sentence-level pass. | Substantive unsupported-inference/derivation finding, with reason and bounded proposal; binding packet alone fails. |
| AT03 | Same pass with no project, then optional venue context, then invalid explicitly supplied governed binding. | Default works; venue override affects the relevant rule; invalid authoritative binding is diagnosed instead of silently discarded. |
| AT04 | Request a 150-200 word explanatory draft about the distinction between a queue recording requests and a policy granting approval, using only that supplied conceptual brief. | Real Generator/Evaluator/Reflector; relevant complete prose without invented studies or citations; independent review; required reflection; successful task completion. |
| AT05 | Revise only the Scope section of the exact fixture below, requesting grammar correction while preserving the argument and terminology. | Independent diagnosis precedes plan and revision; actual errors repaired; Anchor section unchanged; exact final review hash equals delivered bytes; no fabricated milestone history. |
| AT06 | Proposal-only revision of AT05; repeat with a justified no-change request. | Original file untouched; useful proposed changes for the first run; substantive evidence explains no-change completion for the second. |
| AT07 | Evaluator finds a planted issue in the first draft; Generator corrects it. Also exercise an unresolved issue through the correction limit. | Trace proves finding-driven correction and new independent review; unresolved case ends needs_revision, not completion. |
| AT08 | Delete required reflection/review evidence; fail/timeout a reviewer; substitute Generator as Evaluator; replay another run's receipt. | Each case fails completion for its specific defect. Test actual coordinator/verifier entry points, not only a deny-list helper. |
| AT09 | Graph absent/ineligible; run a rule-based pass and source-based centroid check with admitted excerpts; repeat without needed excerpts. | Rule-based analysis runs; admitted-source check performs real judgment; missing-source check is limited/blocked precisely; empty binder is never a pass. |
| AT10 | "Exclude Chung voice" in both AT04 and AT05, and a separate explicit Chung-only audit. | Exclusion persists across all role briefs/fire tables/corrections; read-only file access is not activation; explicit audit works without project prerequisites. |
| AT11 | Change the input after pinning; remove revision pin; change final prose after evaluation; forge completion=true; supply file-presence-only evidence. | Each fails with the appropriate input/evidence/staleness error. A missing pin cannot silently bypass validation. |
| AT12 | Complete AT04/AT05, then request lifecycle terminal/promotion or a direct protected Workbench write using PIW state. Also write to an authorized disposable output directory. | Task completion succeeds; lifecycle/promotion/protected bypass fails; ordinary permitted output works. Exact required refusal, not "expected code OR generic no-project". |
| AT13 | Fresh candidate-loaded Codex context in an empty workspace; exercise AT01, AT04, AT05. Remove subagent capability in a separate controlled integration test. | Real fresh-host positive evidence; absent capability blocks drafting/revision honestly but leaves independent read-only passes usable. |
| AT14 | Structural census, affected regressions, complete fixture registry and candidate qualification. | Actual terminal outcomes recorded; failed/untested counts accurate. Untested required host behavior keeps full qualification pending. |

AT05 fixture, UTF-8 without BOM:
~~~markdown
# Example manuscript

## Anchor
The term "request" denotes a submitted item, not an approval. [Anchor-A]

## Scope
Each reviewer examine one request. The queue record the decision after the review.
~~~

AT04 is synthetic conceptual prose, not evidence of an empirical result. Do not import live paper content or invent scholarly citations to satisfy the demonstration.

A minimal evidence check to run against the delivered AT05 artifacts (the producer creates these files from actual host execution; this script alone does not prove agent independence):
~~~python
from pathlib import Path
import hashlib, json

case = Path("AT05")
before = (case / "input.md").read_bytes()
after = (case / "final.md").read_bytes()
review = json.loads((case / "evaluation.json").read_text(encoding="utf-8"))
completion = json.loads((case / "completion.json").read_text(encoding="utf-8"))

anchor = b'## Anchor\nThe term "request" denotes a submitted item, not an approval. [Anchor-A]\n'
assert anchor in before and anchor in after
assert after != before
assert b"Each reviewer examines one request." in after
assert b"The queue records the decision after the review." in after
assert review["artifact_sha256"] == hashlib.sha256(after).hexdigest()
assert completion["artifact_sha256"] == review["artifact_sha256"]
assert completion["task_complete"] is True
assert completion["lifecycle_terminal"] is False
assert completion["research_acceptance"] is False
assert review["agent_execution_id"] != completion["generator_execution_id"]
~~~

Use these field names in the AT05 exported evidence view; it may adapt an existing internal schema. The view must trace back to original host execution and verifier outputs. Forged strings satisfying this script are not acceptance.

## 6. Verification commands and release boundary

Start from the actual repository root in a UTF-8 Python environment. These commands already exist:
~~~powershell
python -X utf8 scripts/skill-check.py
python -X utf8 scripts/command_surface_check.py
python -X utf8 scripts/schema_runtime_check.py
python -X utf8 scripts/contract-kernel-check.py
python -X utf8 scripts/contract_kernel_coherence_smoketest.py
python -X utf8 scripts/destination-coverage-check.py
python -X utf8 scripts/destination_capability_smoketest.py
python -X utf8 scripts/analysis/fixture_infrastructure_check.py
python -X utf8 scripts/analysis/fixture_runner.py --list
python -X utf8 scripts/analysis/fixture_runner.py --no-write
~~~

Also run the remaining package-root maintainer checks and affected suites required by change-to-check-map.md. Do not claim a partial suite is the full corpus. Preserve final exit/session metadata; an idle process or intermediate JSON file is not a completed run.

Read scripts/release-gate.sh before invoking the applicable non-publishing qualification path. Commit-bound release building cannot certify uncommitted candidate bytes: deliver a hash-bound source snapshot/patch for review and mark final commit-bound build pending. The original reviewer performs the authorized commit, final build/install/startup verification and push after the necessary gates pass.

Do not overwrite production caches for testing. Use supported isolated candidate loading/install paths. If the host cannot load the candidate separately, document that limitation; source-path execution is not installed-host qualification. A production reinstall requires a fresh task for startup-time loading.

## 7. Delivery to the original Codex reviewer

Use:
`B:/Agents/platform/co-author-harness/releases/project-independent-workflow-2026-09-06/codex-v2/`

Preserve the rejected delivery artifacts as historical evidence. Before replacing the old top-level readiness marker, preserve its exact bytes inside codex-v2/prior-delivery/DELIVERY_READY.json. Do not relabel the old artifacts as passing.

Deliver:
1. HANDOFF.md: final behavior, requirement-to-change mapping, limitations, tested hosts, exact reproduction commands, and explicit no commit/push.
2. BASELINE.json: actual starting/final HEAD, branch/origin, pre-existing changes, intended ownership, and final worktree hashes. Explain every shared-file overlap.
3. CHANGED_FILES.json: all intended additions/modifications/deletions, SHA-256/bytes where applicable; exclude unrelated changes and generated scratch.
4. A reproducible patch including tracked and untracked intended content, plus a complete candidate source artifact and file inventory. Verify reconstruction from the declared base. Do not ship a ZIP containing only new scripts while implying it contains the whole product.
5. ACCEPTANCE_MATRIX.md covering AT01-AT14 unchanged, with actual pass/fail/untested values and evidence links.
6. TEST_LOGS/ and HOST_EVIDENCE/: commands, exits, relevant original host execution references, role outputs, input/final hashes, successful completion and adversarial cases. Keep secrets out of logs.
7. REVIEW.md: fresh internal review findings and their resolution; clearly identified as producer review.
8. PENDING_INTEGRATION.md: exact remaining commit-bound release, production installation and startup checks for the original reviewer.

Write the top-level marker LAST:
`B:/Agents/platform/co-author-harness/releases/project-independent-workflow-2026-09-06/DELIVERY_READY.json`

Preserve the readiness protocol: work_id=project-independent-workflow; status=ready_for_codex_verification; new package_id; actual base_commit; candidate path/hash; changed-files and test-report path/hashes; all delivery artifact hashes/lengths; host outcomes and limitations; git_commit_performed=false; git_push_performed=false. Paths may point into codex-v2. Distinguish producer verification from pending independent verification and final shipment.

Only emit readiness when implementation and producer checks are finished. If blocked, report the precise dependency and unfinished acceptance rows; do not replace the readiness marker with another "ready" claim. After writing readiness, stop modifying the candidate. A later edit requires updated evidence and a new marker.

## 8. Definition of done

The producer is done when ordinary public passes produce substantive results without a project; real drafting and existing-manuscript workflows satisfy R1-R7; AT01-AT14 are honestly accounted for; required producer checks pass; and a reproducible, stationary candidate is delivered with precise pending integration steps.

The product is fully shipped only after the original Codex session independently verifies that candidate, commits the verified intended changes, completes applicable commit-bound release and fresh-host checks, and pushes the verified commit. Neither the producer nor this work order declares that outcome in advance.

Do not reduce this work to relabeling receipts, strengthening only refusal tests, or rewriting the work order. Implement the requested behavior.
