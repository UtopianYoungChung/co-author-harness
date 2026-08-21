---
name: plugin-commands
description: 'Show the supported user-facing slash commands in the co-author-harness plugin, with a short purpose, best-use moment, and honest runtime status. Use for command help, first-time orientation, or ambiguous project routing.'
trigger: 'Catalog and routing for the package public command surface.'
version: 1.4
---

# Plugin commands

The command catalog does not grant output authority. `references/role_output_contract.json` 3.0.0 governs the six fixed roles and nine triggered F1-F9 classes; readable legacy artifacts and file presence do not prove shipment-v2 application or acceptance.

List only supported, user-facing commands. Native `skills/*/SKILL.md` files are
the command implementations; the retired `commands/*.md` redirect layer is not
an invocation surface.

Status is the public runtime label. It must match `references/capabilities.yaml`
and `references/policies/command_surface.v1.json`:

- `active` — a local script is the implementation and has been proven callable, or a public staging coordinator that binds the four plugin hands with dest-safe publication.
- `degraded` — public prompt-mediated or incomplete orchestration; not a mechanical runner or staging coordinator.
- `external-dependent` — public only when the named provider is available.

Do not advertise hidden compatibility bodies, maintainer operations, or
fail-closed unavailable capabilities. Their skill contracts remain installed
for internal routing, compatibility, and truthful failure behavior.
`inherit-snowball-from-wiki` is hidden/unavailable (`GRAPH_GOVERNED_GENERATION_UNAVAILABLE`).

## Quick routing

| Situation | Start here |
|---|---|
| New or unclassified project | `/classify-manuscript` |
| Start or continue M1-M4 drafting | `/run-draft` |
| Review and revise a draft | `/run-iterate --profile refine` |
| Structural, deep, or byte-stable iteration | `/run-iterate --profile structural|deep|stability` |
| Submission-bound close-out | `/run-finalize` |
| Fast mechanical pre-flight | `/quick-deterministic` |
| Bind centroid / draft-governance packet | `/centroid-pass` |
| Inspect evidence integrity | `/grounding-audit` |
| Learn from a round | `/run-reflection lightweight|full` |

`/quick-deterministic` and `/centroid-pass` are active mechanical adapters
(`scripts/audit/run_all.py`, `scripts/d_style_profile_check.py`,
`scripts/draft_governance.py`, `scripts/centroid_service.py`) and stay
invoke-only / fail-closed. `/run-draft`, `/run-iterate`, `/run-finalize`,
and `/run-reflection` are active staging coordinators: they bind Planner,
Generator, Evaluator, and Reflector on staging. Generator publishes only
via `assignment_writer_commit.py`. Writer (outside the plugin) is the apply
step. Parked `run-phase-*` names are not public.

`/quick-deterministic` is mechanics-only. Governed product qualification is an
Evaluator lifecycle operation, exposed from a source checkout as:

`python scripts/run_product_gate.py --mode governed-product --project-root "<project-root>" --artifact "<manuscript>" --out-dir "<shipment>/product-gate" --wiki-root "<wiki-root>" --semantic-receipt "<evaluation-semantic-receipt>" --verifier-transaction "<evaluation-verifier-transaction>" --verifier-publication-manifest "<evaluation-verifier-publication-manifest>" --verifier-commit-marker "<evaluation-verifier-commit-marker>"`

Do not substitute `scripts/audit/run_all.py` output or a compatibility semantic
receipt for that governed evidence.

## Command catalog

| Command | Status | Purpose | Best use |
|---|---|---|---|
| `/plugin-commands` | degraded | Show the supported command catalog and routing. | Orientation or quick recall. |
| `/classify-manuscript` | degraded | Establish paper type, P-stage, venue, and review requirements. | Before review or lifecycle work. |
| `/run-draft` | active | Coordinate Planner/Generator/Evaluator/Reflector on staging for draft. | Start or continue drafting on staging. |
| `/run-iterate` | active | Coordinate the four hands on staging for refine/structural/deep/stability. | Improve an existing draft on staging. |
| `/run-finalize` | active | Coordinate the four hands on staging; Evaluator certifies shipment bytes. | After a certified draft, before Writer apply. |
| `/run-reflection` | active | Coordinate reflection on a certified staging shipment (lightweight or full). | After a certified shipment. |
| `/quick-deterministic` | active | Run the canonical mechanical pre-flight. | Before deep review. |
| `/grounding-audit` | degraded | Audit citation, metric, path, and rule-citation integrity. | Evidence and hallucination checks. |
| `/check-abstract-body` | degraded | Verify abstract and title promises are delivered in the body. | Before submission. |
| `/check-contradictions` | degraded | Audit theoretical and terminological contradictions across sources. | Multi-theory manuscripts. |
| `/p-stage-checker` | degraded | Check manuscript claims and vocabulary against the declared P-stage. | Stage-drift diagnosis. |
| `/accessibility-overlay` | degraded | Run the governed reader-accessibility checks. | Review and sign-off passes. |
| `/centroid-pass` | active | Bind and execute governed centroid-conditioned generation, review, or revision. | Explicit centroid audits and projects whose authoritative reader binding enables governed semantic use; reader-profile v2 with `semantic_usage: not_invoked` does not dispatch it. |
| `/centroid-sentence-logic` | active | Join consecutive sentences to admitted Yu 2011 / Dennett passages after a binder packet. Invoke-only while GRAPH-SEMANTIC-INELIGIBLE. | After `/centroid-pass` on the same manuscript bytes. |
| `/analytic-move-audit` | degraded | Audit Abbott-style analytic construction across seven moves. | Theory-building arguments. |
| `/definition-derivation-check` | degraded | Check whether load-bearing terms are derived, imported, or stipulated. | Definitions and construct formation. |
| `/dissolution-move-check` | degraded | Check charitable reconstruction, buried assumptions, and dissolution moves. | Rival-view engagement. |
| `/sentence-level-pass` | degraded | Run the Bacon sentence-craft pass. | Line editing. |
| `/grammar-mechanics-pass` | degraded | Run grammar and punctuation correctness checks. | Copyediting and proofreading. |
| `/narrative-structure-pass` | degraded | Run the Sexton narrative-arc pass. | Structure and flow. |
| `/IS-theory-pass` | degraded | Run the Baird IS-theory criteria pass. | IS theory manuscripts. |
| `/suchman-register-audit` | degraded | Audit Suchman register and asymmetric argument quality. | Suchman-grounded work. |
| `/public-interest-accountability-pass` | degraded | Run the optional policy-critical accountability pass. | Inequality and public-service sections. |
| `/chung-academic-voice-pass` | degraded | Run the optional Chung academic-voice register pass. | On-demand authorial-voice audit or draft. |
| `/citation-format-pass` | degraded | Check Turabian/Chicago citation form. | Notes, references, and bibliography. |
| `/turabian-format-pass` | degraded | Check Turabian/Chicago document structure and layout requirements. | Thesis or course-paper formatting. |
| `/response-letter-review` | degraded | Review rebuttal or response-letter quality and traceability. | Revise-and-resubmit work. |
| `/advisor-escalation` | external-dependent | Route a strategic question to the configured advisor MCP. | EP-1 or EP-2 external feedback. |
| `/seed-snowball-discovery` | external-dependent | Build a section's initial reference pool through bounded snowballing. | Fresh section research. |
| `/claim-coverage-audit` | degraded | Map claims to covered, partially covered, or uncovered sources. | Before post-draft iteration. |
| `/extend-snowball-incremental` | external-dependent | Extend the source pool for a specific uncovered claim. | Targeted evidence gaps. |

## Output

Return the concise catalog above. When the user's situation is clear, lead with
one recommended command and one sentence explaining why. State status honestly:
do not present a degraded or external-dependent command as a live mechanical runner.
