---
name: plugin-commands
description: 'Show the supported user-facing slash commands in the co-author-harness plugin, with a short purpose and best-use moment. Use for command help, first-time orientation, or ambiguous project routing.'
trigger: 'Catalog and routing for the package public command surface.'
version: 1.3
---

# Plugin commands

List only supported, user-facing commands. Native `skills/*/SKILL.md` files are
the command implementations; the retired `commands/*.md` redirect layer is not
an invocation surface.

Do not advertise hidden compatibility bodies, maintainer operations, or
fail-closed unavailable capabilities. Their skill contracts remain installed
for internal routing, compatibility, and truthful failure behavior.

## Quick routing

| Situation | Start here |
|---|---|
| New or unclassified project | `/classify-manuscript` |
| Start or continue M1→M4 drafting | `/run-draft` |
| Review and revise a draft | `/run-iterate --profile refine` |
| Structural, deep, or byte-stable iteration | `/run-iterate --profile structural|deep|stability` |
| Submission-bound close-out | `/run-finalize` |
| Apply decisions from the current chat to manuscript files | `/run-generator-session` |
| Fast mechanical pre-flight | `/quick-deterministic` |
| Inspect evidence integrity | `/grounding-audit` |
| Learn from a round | `/run-reflection lightweight|full` |

`/quick-deterministic` is mechanics-only. Governed product qualification is an
Evaluator lifecycle operation, exposed from a source checkout as:

`python scripts/run_product_gate.py --mode governed-product --project-root "<project-root>" --artifact "<manuscript>" --out-dir "<shipment>/product-gate" --wiki-root "<wiki-root>" --semantic-receipt "<evaluation-semantic-receipt>" --verifier-transaction "<evaluation-verifier-transaction>" --verifier-publication-manifest "<evaluation-verifier-publication-manifest>" --verifier-commit-marker "<evaluation-verifier-commit-marker>"`

Do not substitute `scripts/audit/run_all.py` output or a compatibility semantic
receipt for that governed evidence.

## Command catalog

| Command | Purpose | Best use |
|---|---|---|
| `/plugin-commands` | Show the supported command catalog and routing. | Orientation or quick recall. |
| `/classify-manuscript` | Establish paper type, P-stage, venue, and review requirements. | Before review or lifecycle work. |
| `/run-draft` | Run the public draft-stage M1→M4 workflow. | Start or continue drafting. |
| `/run-iterate` | Run post-draft review and revision with `refine`, `structural`, `deep`, or `stability` profile. | Improve an existing draft. |
| `/run-finalize` | Run submission-bound verification and close-out. | After convergence and MCR admission. |
| `/run-generator-session` | Apply the current chat's agreed revisions under real project state. | Turn decisions into manuscript edits. |
| `/run-reflection` | Run lightweight integrity learning or full close-out reflection. | Round close or final close-out. |
| `/quick-deterministic` | Run the canonical mechanical pre-flight. | Before deep review. |
| `/grounding-audit` | Audit citation, metric, path, and rule-citation integrity. | Evidence and hallucination checks. |
| `/check-abstract-body` | Verify abstract and title promises are delivered in the body. | Before submission. |
| `/check-contradictions` | Audit theoretical and terminological contradictions across sources. | Multi-theory manuscripts. |
| `/p-stage-checker` | Check manuscript claims and vocabulary against the declared P-stage. | Stage-drift diagnosis. |
| `/accessibility-overlay` | Run the governed reader-accessibility checks. | Review and sign-off passes. |
| `/centroid-pass` | Bind and execute governed centroid-conditioned generation, review, or revision. | Explicit centroid audits and projects whose authoritative reader binding enables governed semantic use; reader-profile v2 with `semantic_usage: not_invoked` does not dispatch it. |
| `/analytic-move-audit` | Audit Abbott-style analytic construction across seven moves. | Theory-building arguments. |
| `/definition-derivation-check` | Check whether load-bearing terms are derived, imported, or stipulated. | Definitions and construct formation. |
| `/dissolution-move-check` | Check charitable reconstruction, buried assumptions, and dissolution moves. | Rival-view engagement. |
| `/sentence-level-pass` | Run the Bacon sentence-craft pass. | Line editing. |
| `/grammar-mechanics-pass` | Run grammar and punctuation correctness checks. | Copyediting and proofreading. |
| `/narrative-structure-pass` | Run the Sexton narrative-arc pass. | Structure and flow. |
| `/IS-theory-pass` | Run the Baird IS-theory criteria pass. | IS theory manuscripts. |
| `/suchman-register-audit` | Audit Suchman register and asymmetric argument quality. | Suchman-grounded work. |
| `/public-interest-accountability-pass` | Run the optional policy-critical accountability pass. | Inequality and public-service sections. |
| `/citation-format-pass` | Check Turabian/Chicago citation form. | Notes, references, and bibliography. |
| `/turabian-format-pass` | Check Turabian/Chicago document structure and layout requirements. | Thesis or course-paper formatting. |
| `/response-letter-review` | Review rebuttal or response-letter quality and traceability. | Revise-and-resubmit work. |
| `/advisor-escalation` | Route a strategic question to the configured advisor MCP. | EP-1 or EP-2 external feedback. |
| `/seed-snowball-discovery` | Build a section's initial reference pool through bounded snowballing. | Fresh section research. |
| `/claim-coverage-audit` | Map claims to covered, partially covered, or uncovered sources. | Before post-draft iteration. |
| `/extend-snowball-incremental` | Extend the source pool for a specific uncovered claim. | Targeted evidence gaps. |
| `/inherit-snowball-from-wiki` | Inspect or apply eligible cross-project graph pre-seeds. | Wiki-linked fresh sections. |

## Output

Return the concise catalog above. When the user's situation is clear, lead with
one recommended command and one sentence explaining why.
