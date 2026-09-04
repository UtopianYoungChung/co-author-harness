# Centroid Advisory Read-only Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make an explicitly requested centroid review available as a simple, read-only advisory operation when a project has reader-profile v2 with `semantic_usage: not_invoked`, without weakening or impersonating the existing governed semantic/lifecycle path.

**Architecture:** Preserve two non-interchangeable execution contracts. `governed_semantic` remains the existing graph-qualified, receipt-backed route used only when the authoritative binding enables it. `advisory_readonly` resolves the package reader profile without invoking Graphify, requires explicit exact-file source bindings, produces a deterministic non-authoritative packet, and dispatches only an Evaluator. An advisory packet can never satisfy draft governance, F9, milestone, product-gate, promotion, or delivery evidence.

**Tech Stack:** Python 3 standard library, JSON Schema draft 2020-12, existing `reader_accessibility_policy.resolve_reader_profile()`, deterministic smoke tests, co-author-harness fixture runner, PowerShell release qualification.

## Global Constraints

- Work directly from the current `main` checkout as required by repository governance. Do not create a feature branch or an implementation worktree. A detached clean worktree is permitted only for post-commit verification when separately authorized.
- The first fresh-session action is a read-only rebaseline. Do not mutate source while a release qualification is running or while ownership of the current failed qualification/lock remains unresolved.
- Do not amend, reuse, or overwrite the frozen v0.43.0 attempt-049 artifacts. That attempt is terminal `child_failed`, exit 1, because `scripts/token_budget_smoketest.py::default` failed; it wrote no fixture manifest.
- Do not remove `.git/coauthor-fixture-runner.lock`, retry worktrees, generated residue, or another session's files under this authority. A dead recorded PID is not cleanup authority.
- Treat all current modified and untracked harness paths as protected work from the semantic-qualification/reader-binding migration. This plan intentionally avoids `scripts/reader_accessibility_policy.py`, `scripts/assignment_milestone_transaction.py`, `scripts/assignment_milestone_checkpoint.py`, the reader-profile schema, and repin tests.
- Do not modify Paper 2 M4, `reviews/phase_state.json`, F9, lifecycle state, promotion, delivery, the live Wiki graph, or archived 290-page semantic artifacts.
- An advisory centroid run is explicit-user-request only. Reader-profile v2 must remain graph-independent and must not auto-dispatch centroid work.
- A failure in `governed_semantic` must never fall back to `advisory_readonly`. A successful advisory run must never be upgraded or copied into governed evidence. Governed adoption requires a fresh governed execution.
- No version bump, contract-kernel refresh, fixture-manifest regeneration, archive build, cache install, or host activation occurs until the active v0.43.0 upgrade owner assigns this bundle to a named release slice.

## Frozen Starting Evidence

- Harness checkout: `main` at `388ff6b5e5ebc7e4307cf6c948606088dfa59409`, manifest version `0.43.0`.
- v0.43.0 qualification attempt 049: terminal `child_failed`, return code 1, no validation capsule and no fixture manifest; the single reported case is the token-budget unchanged-baseline regression.
- Paper 2 M4 SHA-256: `cb2308e6c9598430684d8a3c42569f0e0095534b547ef11ef0616075fc7bb2c3`.
- Paper 2 phase-state SHA-256: `3fc35ae3060d0205075d69c41dae77f70fa903d905c276c21abef174cefbfa29`.
- Paper 2 work-package SHA-256: `2a955040a7520514b66e1ff75d767dcae0d76baabc2e0c5f635cf8a299930aff`.
- The semantic-qualification and v2-to-semantic migration implementation has an independent source-level PASS, but no live qualified graph, re-pin, Planner activation, installed-cache qualification, or host qualification exists.

## Task 0: Rebaseline and obtain the release integration gate

**Read only:** `.claude-plugin/plugin.json`, Git status/HEAD, release qualification receipts, fixture lock, active processes, current worktrees, and the files listed in this plan.

- [ ] Record exact `main` HEAD, tree, plugin version, tracked/index status, protected untracked paths, and hashes of every file this plan may touch.
- [ ] Inspect the latest v0.43 qualification receipt, exit capsule, validation capsule if any, and fixture-manifest state. Treat a missing or failed terminal artifact as closed-fail, not as permission to retry.
- [ ] Confirm whether the v0.43 release owner has dispositioned attempt 049 and assigned this centroid bundle to a named version slice. If no version identifier and source-integration authority exist, stop before editing.
- [ ] Confirm that none of the intended centroid files overlap another session's dirty paths. If overlap appears, stop and reconcile exact preimages with that owner.
- [ ] Re-hash M4 and its protected state files. Stop if any differs from the frozen starting evidence unless the user explicitly supersedes the target.

**Gate:** Source implementation starts only after the user starts the fresh task and the release owner supplies a non-conflicting integration point. Cleanup, retry, and release repair remain separate work.

## Task 1: Characterize the two execution contracts in tests

**Files:**

- Modify: `scripts/centroid_service_smoketest.py`
- Verify unchanged behavior: `scripts/reader_profile_v2_global_smoketest.py`

- [ ] Add a failing test proving the current default governed invocation still returns `GRAPH_GOVERNED_GENERATION_UNAVAILABLE` for a valid v2 `semantic_usage: not_invoked` project.
- [ ] Add a failing test for an explicit `--execution-contract advisory_readonly` invocation that is expected to succeed without reading a structural-only graph.
- [ ] Make the advisory test provide every selected member as an explicit `source_key=absolute_path` binding and assert exact path, SHA-256, byte length, role, warrant scope, and retrieval scope in the packet.
- [ ] Add negative cases for a missing primary centroid source, an undeclared source key, duplicate keys, stale profile hash, unreadable source, a source changed during packet construction, and graph-root arguments supplied to advisory mode.
- [ ] Add mode-separation cases: advisory refuses `write` and `revise`; governed refuses advisory source-binding arguments; neither mode falls back to the other.
- [ ] Snapshot project, manuscript, source, Wiki, and workspace trees before and after every advisory call and assert byte-for-byte neutrality.
- [ ] Run `python -B scripts/centroid_service_smoketest.py` and retain the expected red output before implementation.

## Task 2: Define a machine-enforced advisory packet

**Files:**

- Modify: `references/schemas/centroid_analysis.schema.json`
- Modify: `scripts/centroid_service_smoketest.py`

- [ ] Add `execution_contract` with exactly `governed_semantic` and `advisory_readonly`.
- [ ] Add a distinct success state such as `advisory_binding_resolved`; do not reuse `binding_resolved`.
- [ ] Require `evidence_eligibility: advisory_only`, `authority_effect: none`, `semantic_usage: not_invoked`, explicit source bindings, and a closed list of prohibited uses on the advisory branch.
- [ ] Require the advisory branch to bind the project reader-profile declaration, exact manuscript/scope bytes, selected member metadata, and every source input byte.
- [ ] Keep `semantic_findings` empty in deterministic service output. The Evaluator, not the packet builder, performs the semantic judgment.
- [ ] Preserve the existing governed schema branch so current governed packets remain compatible.
- [ ] Add schema-negative tests showing an advisory packet cannot claim `binding_resolved`, lifecycle eligibility, governed provenance, graph pins, or a semantic execution receipt.

## Task 3: Implement the minimal graph-independent advisory resolver

**Files:**

- Modify: `scripts/centroid_service.py`
- Test: `scripts/centroid_service_smoketest.py`

- [ ] Add `--execution-contract`, defaulting to `governed_semantic` for backward compatibility.
- [ ] Add repeatable `--source-binding source_key=path`, accepted only for `advisory_readonly`.
- [ ] For advisory mode, require `--project-root`, read the exact manuscript, and validate the project binding as reader-profile v2 with `semantic_usage: not_invoked` and the current profile SHA-256.
- [ ] Call `reader_accessibility_policy.resolve_reader_profile()` only. Do not call `resolve_policy()`, `resolve_domain_native_register()`, Graphify, repin, Planner, draft governance, or lifecycle code.
- [ ] Derive primary and selected member keys from the resolved profile, then require one explicit source binding for each. Reject extras, duplicates, aliases, and missing members.
- [ ] Resolve each source once, capture a pre-read file identity, read bytes, capture the post-read identity, and fail closed if the file changed. Record exact path, SHA-256, byte length, declared role, grounding, warrant scope, and retrieval scope.
- [ ] Emit the advisory-only prohibitions: no draft-governance evidence, no semantic execution receipt, no F9 or milestone evidence, no product-gate evidence, no promotion/delivery claim, no graph qualification, and no source admission beyond the explicit packet.
- [ ] Keep the governed code path byte-semantically unchanged except for the new explicit contract label and argument validation.
- [ ] Run the focused smoke test until all cases pass, then inspect the diff for accidental imports or calls into mutation/lifecycle surfaces.

## Task 4: Route explicit advisory review without restoring automatic centroid dispatch

**Files:**

- Modify: `skills/centroid-pass/SKILL.md`
- Modify: `agents/evaluator.md`
- Modify: `references/SKILL_REGISTRY.md`
- Modify: `references/MANIFEST.md`
- Modify only if required by existing routing assertions: `references/ROUTING_SPINE.md`, `references/AGENT_ORCHESTRATION.md`, `skills/plugin-commands/SKILL.md`
- Test: `scripts/reader_profile_v2_global_smoketest.py`

- [ ] Document a decision table: governed semantic binding uses the existing governed route; v2 `not_invoked` plus an explicit user request uses advisory review; v2 without an explicit request does nothing; malformed or stale binding refuses.
- [ ] Keep advisory mode Evaluator-only. It reviews exact bytes and returns findings in conversation or an already-authorized private shipment surface; it does not generate or revise manuscript prose.
- [ ] Require exact explicit source paths and prohibit invented retrieval, inferred graph eligibility, re-pin, activation, or receipt creation.
- [ ] State that advisory findings are proposals and that adoption requires ordinary user-authorized manuscript revision plus fresh milestone review; they cannot be promoted as governed centroid evidence.
- [ ] Extend the global v2 routing regression to prove auto-dispatch remains absent while explicit advisory invocation is documented and callable.
- [ ] Run `python -B scripts/reader_profile_v2_global_smoketest.py` and the focused centroid smoke test.

## Task 5: Prove lifecycle and product-gate non-interference

**Files:**

- Modify tests only unless a current validator incorrectly accepts advisory evidence: `scripts/draft_governance_smoketest.py`, `scripts/run_product_gate_smoketest.py`, `scripts/milestone_framework_smoketest.py`
- Runtime files may change only if a failing negative test proves they are too permissive: `scripts/draft_governance.py`, `scripts/run_product_gate.py`, `scripts/milestone_framework_validate.py`

- [ ] Add a negative test showing an advisory packet cannot satisfy a centroid-generation or centroid-evaluation obligation.
- [ ] Add a negative test showing an advisory packet cannot be supplied as `centroid_semantic_execution` evidence.
- [ ] Add a negative test showing the governed product gate rejects an advisory packet or advisory finding report.
- [ ] Add a negative test showing milestone/F9 validation gains no status, evidence, or acceptance from advisory output.
- [ ] Assert that failed tests are fixed by type/status separation, not by weakening existing governed requirements.
- [ ] Run the three focused suites and inspect all touched runtime diffs. If no runtime change is needed, keep them unchanged.

## Task 6: Run targeted and full source verification

**Files:**

- Modify registry only if a new test file was created: `scripts/analysis/fixture_runner.py`
- Later release integration only: `references/contract_kernel.v1.json`, `docs/analysis/generated/fixture_manifest.json`

- [ ] Run syntax compilation and focused centroid, v2 routing, draft-governance, milestone, and product-gate tests.
- [ ] Run version check and package completeness checks without changing the version.
- [ ] Run the full fixture suite only from a release-owner-approved clean verification context. Do not reuse attempt 049 or its worktree.
- [ ] Diagnose any token-budget failure independently from centroid behavior; do not expand this task into the v0.43 qualification repair.
- [ ] Refresh contract-kernel hashes and the fixture manifest only after the entire assigned release slice is frozen and separately authorized.

## Task 7: Perform the Paper 2 read-only consumer pilot

**Read only:** Paper 2 M4, the advisory packet's explicitly bound centroid sources, and project directives.

- [ ] Reconfirm M4 SHA-256 `cb2308e6c9598430684d8a3c42569f0e0095534b547ef11ef0616075fc7bb2c3` immediately before the pilot.
- [ ] Resolve the declared centroid/member set from the current reader profile and bind exact existing source files. Do not create a live semantic qualification or use the archived 290-page artifacts.
- [ ] Run `advisory_readonly` in review mode and have an independent Evaluator assess M4's first-principles engineering argument, outward-to-inward convergence, actor/agency treatment, and source-warrant limits.
- [ ] Return the findings as proposal-only review. Do not edit M4, phase state, F9, promotion, or delivery state.
- [ ] Re-hash all protected Paper 2 files and report equality with the pre-run hashes.

## Task 8: Integrate with the harness upgrade as a separate release slice

**Files are release-owner selected after source freeze. Typical surfaces:** `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `CHANGELOG.md`, release notes, compatibility profiles, contract kernel, fixture manifest, release evidence.

- [ ] Use only the version identifier explicitly supplied by the release owner. If none is supplied, stop before version files.
- [ ] Reconcile the centroid bundle with the independently owned semantic-migration bundle and any v0.43 token-budget repair by exact preimage/postimage review.
- [ ] Obtain independent BLOCKER/MAJOR/MINOR review of the frozen source bytes.
- [ ] Run source qualification, independent consumer conformance, package/archive parity, installed-cache parity, catalog/startup qualification, and fresh-host qualification as separate gates.
- [ ] Do not call the feature shipped, installed, or active until the corresponding terminal receipts exist and exact loaded paths match.

## Task 9: Close with exact-byte evidence and a fresh handoff

- [ ] Report every modified file with preimage/postimage SHA-256 and the complete test matrix.
- [ ] Report protected Paper 2 hashes and confirm no M4/lifecycle/F9/promotion/delivery mutation.
- [ ] Report source, release, installed-cache, and host status as separate typed claims.
- [ ] Request a final independent boundary audit. Internal subagent review is useful but is not an external consumer receipt.
- [ ] Create and validate a new session handoff if implementation spans another task; do not reuse this planning handoff as completion evidence.

## Fresh-session Resource Allocation

The fresh task may use four concurrent lanes after the user explicitly starts it:

1. **Primary/Planner lane:** owns rebaseline, change boundaries, TDD integration, exact hashes, and release coordination.
2. **Adversarial test lane:** independently designs negative tests for graph access, fallback, stale bindings, time-of-check/time-of-use source changes, and lifecycle misuse.
3. **Contract audit lane:** reviews exact frozen bytes against this plan and reports BLOCKER/MAJOR/MINOR without editing.
4. **Research-consumer lane:** performs the final read-only M4 pilot and protected-state rehash; it does not certify release or external consumer independence.

Only the Primary lane edits. The other lanes are read-only unless the user separately reallocates authority. No lane is started by this plan; the fresh task begins only on the user's explicit command.
