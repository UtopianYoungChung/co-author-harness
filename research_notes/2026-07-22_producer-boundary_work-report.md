# Work Report — Producer-Boundary Workstream (for supervisory review)

**Date:** 2026-07-22 · **Repository:** `platform/co-author-harness`, branch `main`, HEAD `90c39fd`, working tree clean · **Plugin version:** v0.36.0 (authority: `.claude-plugin/plugin.json`)
**Prepared for:** the reviewing authority adjudicating the final closeout shipment
**Decision requested:** Accept / Reject / Revise of the closeout shipment at
`outputs/co-author-harness/staging/producer-boundary-closeout/run-20260722T185523Z-6f0fd411/`

This report is self-contained: a reviewer without the working-session context should be able to reach a decision from this document plus the closeout shipment it describes.

---

## 1. What is being decided — and what is not

**Being decided:** whether the harness-engineering workstream summarized below is accepted as complete production evidence. Acceptance records that the co-author harness now structurally enforces the producer boundary and that the staging lane is the sole research-facing production path going forward.

**Not being decided, and not implied by acceptance:**
- No research decision, milestone acceptance, registration, promotion, advisor delivery, or manuscript shipment. Everything the harness produced remains `effect_scope: proposal_only`.
- No change to any byte under `B:\Agents\research`, the canonical Wiki, or workspace governance. The closeout's proposed-operations list is empty ("none — harness-only closeout").
- Rejection does not undo the `main` commits; any rollback would be a separately scoped decision.

## 2. Why the work was needed

The binding constitutional boundary (`research/10_Governance/HARNESS_SHIPMENT_BOUNDARY.md`, effective 2026-07-22) declares the harness a **producer, not a decision maker**: zero direct-write authority under the research root; shipments are proposals; the user decides; research governance applies. Before this workstream, the code did not enforce what the constitution declared:

1. **No write guard existed.** Any harness writer (21 distinct mutator entry points were inventoried) could write into the research tree if pointed there.
2. **M4 stranding defect (reproduced):** after all sections reached `Ph3_converged`, a pre-acceptance edit had no legal re-record verb (exit 4, `AMC-ORDER`).
3. **M5 non-re-recordable defect:** after its first recording, the final paper's derived action became `close`, which `record()` never permitted — a recorded final candidate could not be revised.
4. **Authority-bundling risk:** milestone labels (`accepted`), F9 handoffs, and terminal PASSes written by the harness could be misread as research authority.
5. **Stale governance descriptions:** the workspace index still described direct harness writes into `research/<project>/` and a canonical-Wiki write-back that the skill contract had already deleted.

An external review (Codex) and an in-session verification pass converged on the corrected authority model: **the user is primary authority; the research master adjudicates, registers, promotes, and owns live state; root/Overseer governance owns routing and capabilities; the harness produces.**

## 3. What was done

All work on `main` (single-branch policy), TDD per defect (every regression observed red before its fix), no intentionally red commits.

| Phase | Content | Commit |
|---|---|---|
| A | Baseline receipt (full battery recorded; one pre-existing environment-sensitive test failure documented, explicitly not treated as green) + mechanical inventory of all 21 writer entry points and agent/skill write surfaces | `3c9e9c4` |
| Side fix (separately authorized) | Root-caused and fixed the flaky provenance smoketest (one-shot `git clean` vs. transient external file handles; misclassified environment failure). Deterministic Windows handle-injection regression added | `d11cd4c`, manifest `31dc941` |
| B (governance; **applied by root governance after explicit user acceptance**) | Staging-lane route into the `WS_OUTPUTS` zone (`outputs/co-author-harness/staging/<work-id>/<run-id>/`), routing-contract enum extensions, prose meaning paragraph, workspace-index reconciliation of both stale claims, change record `2026-07-22_harness-staging-route.yaml` → `installed`. Byte-exact hash verification; routing gate exit 0; containment guard 0 errors | applied outside this repo |
| C | `destination_capability.py` — single write-destination chokepoint: harness package and staging lane writable; anything else under a governed root refuses `DEST-PROTECTED`; installs without discoverable workspace governance fail closed (`DEST-UNGOVERNED`). Wired through 5 transaction verbs, 3 receipt-transaction entries, 13 writer CLIs. Alias-resistant (case-folding, forward slashes, `..`, junctions). Binding producer-duty declarations in `CLAUDE.md`, `AGENTS.md`, `AGENT_ORCHESTRATION.md`, `ASSIGNMENT_MILESTONE_PROCESS.md` §0 | `8e95abb` |
| D | `staging_run.py` + `shipment_manifest.schema.json` — run lifecycle: immutable input snapshots (bytes + source path + SHA-256), exclusive byte-verified shipment emission, tamper detection, application-receipt recognition (no receipt = not applied) | `8e95abb` |
| E | Authority mode `shipment_only` (orthogonal to assignment profile and run scope; "operating mode" stays reserved-empty). `derive` reports the mode; staging events, bootstrap genesis events, and F9 handoffs carry `effect_scope: proposal_only`. Direct-local output byte-identical to before | `8e95abb` |
| F | Staging revisability: post-convergence M4 and recorded M5 candidates re-record freely **in staging only**; the superseding event carries a `previous_content` binding, names `candidate_superseded`, and discloses the research-master revalidation advisory the harness never applies. M5 staging deliverables became content-addressed snapshots so historical event bindings stay byte-valid. Direct-local projects keep the historical refusals (regression-pinned) | `8e95abb` |
| G | Schema compatibility: additive optional `effect_scope` on milestone events and F9; contract kernel re-pinned for every changed pinned component; historical 1.0.0 evidence remains valid with no dual validators | `8e95abb` |
| H | Automatic canonical-Wiki / lessons-promotion attempt wiring removed across skills, agents, and references; canonical Wiki changes are separately adjudicated shipments to Wiki governance; a persistent `wiki_writes` flag is configuration, not promotion authority | `8e95abb` |
| I | Full verification + fixture-manifest regeneration after a fully green run, immediately re-verified | `90c39fd` |

## 4. Evidence

Final-tree verification (none waived):

| Surface | Result |
|---|---|
| Maintainer battery (12 structural checks) | 12/12 exit 0 |
| Fixture corpus, `--no-write` | exit 0 — **58 suites, 58 cases green** (55 pre-existing + 3 new) |
| New: destination-capability refusals | 15 mutators refuse `DEST-PROTECTED` writing nothing; alias/junction cases; ungoverned fail-closed |
| New: staging authority/revisability walk | full public-command M1→FINAL walk in a hermetic fake governed lane; M4 post-convergence and FINAL re-records succeed with supersession records; direct-local refusals unchanged |
| New: shipment contract | round-trip validation, tamper-a-byte detection, exclusive emission, receipt semantics |
| Contract-kernel coherence | exit 0 (all pins current) |
| Routing gate (workspace) | exit 0 — 13 zones, 15 routes |
| Research containment guard | exit 0, 0 errors |
| Fixture manifest | regenerated only after fully green runs; re-verified; committed |

Safety property of the test design worth noting: red-phase runs mutate a **fake** governed root supplied through an additive-only environment hook — a failing guard during development wrote into a disposable tree, never into `B:\Agents\research` (and one red run demonstrably would have).

## 5. Practical consequences for day-to-day work

1. **Research-rooted direct milestone commands now refuse** (`DEST-PROTECTED`) — including against the existing Paper 1 package under `research/60_Workbench/`. This is the accepted C→E adoption gap: the correct workflow is a staging-lane run; the transition shipment for the Paper 1 package is research-master work not performed here.
2. **Research-facing production runs in the lane** (`shipment_only` derives automatically), and its output reaches the research tree only as a path-and-hash shipment adjudicated by the user with research governance.
3. **Nothing the harness writes reads as authority.** `accepted` in staging is a production marker; F9 is a proposed handoff; a shipment is applied only when a consumer-side receipt exists.
4. **Wiki mutation happens only on explicit instruction** and only as a proposal to Wiki governance.

## 6. Limitations, deviations, open items

1. **C→E adoption gap** (accepted in-session): see §5.1. Follow-up owner: research master.
2. **Schema versioning deviation (disclosed):** additive-optional fields instead of the plan's "2.0.0 parallel schema" default — chosen because it preserves all historical evidence without dual validators; recorded in the CHANGELOG.
3. **Staging `accept:FINAL` walk not separately exercised.** The verification floor named M5 *re-record* (verified); terminal close remains corpus-green in direct-local form. If staging terminal acceptance is wanted as pinned behavior, that is a small follow-up test.
4. **Provenance smoketest history:** fixed and 6/6 consecutive green; its historical environment-sensitive flake window is documented in the Phase A baseline receipt.
5. **Operating mode** remains reserved-empty by design (no phantom values).

## 7. Decision options

| Option | Effect |
|---|---|
| **Accept** | The closeout becomes recorded harness-production evidence; the staging lane is confirmed as the sole research-facing production path. Nothing is applied anywhere; no research status changes. |
| **Reject** | The shipment stays in the lane as evidence. `main` retains the commits; rollback, if wanted, is a separately scoped decision. |
| **Revise** | Name the items (e.g., add the staging `accept:FINAL` walk; different schema-versioning form); the workstream reopens for exactly those. |

**Recommendation:** Accept, with two named follow-ups routed to their proper owners — (a) the Paper 1 staging-transition shipment (research master, with user authorization), and (b) optionally the staging `accept:FINAL` regression (harness, small).

## 8. Where everything lives

- Closeout shipment (human + machine + evidence): `B:\Agents\outputs\co-author-harness\staging\producer-boundary-closeout\run-20260722T185523Z-6f0fd411\`
- Workstream commits: `3c9e9c4`, `d11cd4c`, `31dc941`, `8e95abb`, `90c39fd` (all on `main`)
- Phase A baseline receipt: `research_notes/2026-07-22_producer-boundary_phase-a_baseline.md`
- Mutation-surface inventory: `docs/analysis/2026-07-22_mutation-surface-inventory.md`
- Applied Phase B change record: `governance/output-routing/changes/2026-07-22_harness-staging-route.yaml`
- Version narrative: `CHANGELOG.md` v0.36.0 entry
