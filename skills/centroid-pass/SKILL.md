---
name: centroid-pass
user-invocable: true
description: 'centroid-bind: bind live policy centroid-source plus graph eligibility plus named manuscript bytes. Catalog id stays /centroid-pass. This is not a centroid-check and does not move centroid-source yu-et-al-2011-social-modeling.'
trigger: invoke-only / fail-closed. Explicit /centroid-pass only. Do not auto-dispatch as scholarly CLEAN. Reader-profile v2 with semantic_usage not_invoked does not dispatch this skill. GRAPH-SEMANTIC-INELIGIBLE stays fail-closed.
version: 3.1
---

# centroid-pass (instrument: centroid-bind)

**Invoke-only / fail-closed.** Not a scholarly CLEAN mint and not an
auto-dispatch. Graph / centroid remain invoke-only. `GRAPH-SEMANTIC-INELIGIBLE`
is eligibility, not a pair verdict.

Three objects share the word centroid. Keep them separate:

| Name | What it is | What it is not |
|---|---|---|
| **centroid-source** | Live policy `references/policies/reader_accessibility.v1.json` member `yu-et-al-2011-social-modeling`, role `centroid`. Retrieval is the Yu-authored window only: book pp. 3-10 and 11-52. | Not a manuscript hash. Not this bind. Not a pair verdict. |
| **centroid-check** | Sentence-logic on named manuscript bytes against that source (`/centroid-sentence-logic`). | Not a redefinition of centroid-source. A check of live M4 is a check. |
| **centroid-bind** | This skill. `scripts/centroid_service.py` binds policy + graph eligibility + named bytes. | Not a scholarly CLEAN. Empty `semantic_findings` means no role judgment ran, not a pass. |

The script always runs. When reader-profile v2 sets `semantic_usage: not_invoked`,
it still emits a general binding packet (scope, hashes, metrics) and marks
`reason_code: SEMANTIC_USAGE_NOT_INVOKED`. That is not a graph-governed scholarly
pass and not a fabricated finding set.

## Contract

This pass is invoke-only. It is not mandatory auto-dispatch and does not mint
scholarly CLEAN. Reader-profile v2 with `semantic_usage: not_invoked` does not
invoke this pass. A missing governed semantic binding is fail-closed.
Use `write` before generation, `review` after generation, and `revise` before a
finding-driven rewrite. The pass is read-only: the Generator remains the sole
academic-prose writer and the Evaluator remains the independent reviewer.

The policy at `references/policies/reader_accessibility.v1.json` is authoritative
for centroid-source membership, warrant layers, derivations, semantic pins, and the C-7
identity fence. `references/GROUNDING_PROTOCOL.md` remains absolute. Never invent
a passage, quotation, attestation, locator, or member.

## Required execution

1. Resolve the project and exact target. Run:

   `python scripts/draft_governance.py prepare --project-root <project-root> --target <M1|M2|M3|M4|FINAL> --role <generator|evaluator> --phase <generation|evaluation> [--artifact <path>]`

   If the target file does not yet exist, omit `--artifact`. The returned
   `artifact_state: absent` is valid and does not relax any obligation.

2. Build the centroid-bind packet with
   `python scripts/centroid_service.py --mode <write|review|revise>
   --manuscript <input-or-draft> --project-root <project-root>`. For `write` when
   the target is absent, use the closest grounded controlling text that will
   actually condition the draft: accepted predecessor, structured outline, or
   assignment source. Do not create placeholder prose merely to satisfy this
   argument.
   A successful packet says `status: binding_resolved` and `instrument: centroid-bind`.
   This means only that policy, pins, members, scope, and input bytes were resolved.
   The retired word `ready` must not be used for this state. If the response is
   `PROJECT_BINDING_REBIND_AVAILABLE`, use only the exact Planner-owned command
   in its `recovery` object; a bare stale/conflict refusal is not permission to
   infer or perform a rebind.
   `GRAPH-SEMANTIC-INELIGIBLE` is eligibility, not a pair verdict.

3. Retrieve only passages admitted by the packet's member and warrant views.
   `surface` members condition register; `argument` members condition argument
   architecture; a member without the relevant warrant is not silently promoted.
   Record every passage actually used in a role-produced semantic execution
   receipt conforming to
   `references/schemas/centroid_semantic_execution.schema.json`. Bind the source
   bytes, a non-empty canonical extracted-passage file, the verbatim quote
   actually used, citation identity, its corpus/page locator, its `surface` or
   `argument` use, and the exact deterministic centroid-bind packet. Produce PDF
   extracts with `python scripts/source_extract.py`; a lone `pypdf` extraction
   is not canonical evidence.
   `references/templates/centroid_semantic_execution.json` is the authoring
   shape. A policy/member packet or generic path/hash evidence is not this
   receipt.

4. In `write`, the Generator conditions the draft on the retrieved passages but
   does not imitate a source's identity-layer voice. In `review`, the Evaluator
   independently compares the produced draft with the resolved centroid-source and
   records strengths, deviations, warrant limits, and actionable findings. In
   `revise`, preserve propositional content and C-7 identity features while
   substituting only grounded, attested constructions.

5. Complete every applicable obligation in the returned draft-governance
   contract, including D-STYLE, grammar/mechanics, citation and em-dash policy,
   deterministic checks, Grounding, SAFEGUARD, and project/venue overlays. An
   always-on obligation may not be marked `not_applicable`.
   Invoke the mechanics suite for diagnostics only:

   `python scripts/audit/run_all.py <artifact> --project-root <project-root> --out <shipment-findings-path>`

   This command never produces lifecycle evidence. Hard evidence failures cannot
   be adjudicated away. Generation may surface semantic candidates for the
   Evaluator; evaluation must record exact code/locator dispositions and reach
   a passing product-assurance report through the shared verifier.

6. Run `draft_governance.py verify` against the exact generated bytes and the
   completed obligation receipt, publish the shared generation and evaluation
   verifier transactions, and preserve their marker-last lifecycle locators in
   the authorized run's private evidence lane. Then run
   `scripts/run_product_gate.py --mode governed-product` with the exact committed
   evaluation transaction, its publication manifest and marker, the evaluation
   semantic receipt, and the resolved Wiki root. A milestone record, terminal
   claim, or product qualification without both consumed role claims and both
   current-byte verifier transactions fails closed. Mechanics-mode output is
   diagnostic and cannot substitute. Evaluation preparation and the `review`
   centroid-bind packet must bind the exact bytes that the Evaluator reviewed;
   unresolved candidates prevent product qualification.

## Semantic output

The deterministic service deliberately emits no semantic verdict. Its job is to
prove which policy, members, warrants, scope, and bytes the role received. The
Generator or Evaluator must perform and document the semantic judgment; empty
`semantic_findings` from the service is not evidence that the prose passed.

## Prohibitions

- When the authoritative binding enables the pass, do not skip it because an M1-M3 artefact exists, is missing, or was
  migrated from an older run.
- Do not treat centroid conformity as citation grounding, grammatical
  correctness, D-STYLE compliance, or user acceptance; each has separate
  evidence.
- Do not label the deterministic service packet a generation/evaluation
  envelope or copy its discipline string into manuscript metadata as proof of
  retrieval. Only a verified role-produced semantic execution receipt supports
  a conditioning claim.
- Do not let the Generator self-certify the evaluation receipt.
- Do not verify PDF quotes with a single non-canonical library extractor or
  assign same-year suffixes without checking the title/label mapping in the
  manuscript bibliography.
- Do not mutate lifecycle state, the canonical Wiki, or a protected consumer
  path from this skill.
- Do not treat a manuscript hash as centroid-source. Do not mint CLEAN from this binder.
