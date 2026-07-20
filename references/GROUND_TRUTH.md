# Operational Research-Process Vocabulary

## Status

This file is a package-authored, non-verbatim operational interpretation of the
P/R/K/S/T/V research-process labels used by the harness. It is self-contained
for package routing, but it is **not** an authoritative reproduction of Prof.
Eric Yu's group workbook and does not certify exact EYgp conformance.

The external workbook and its mechanical transcription are deliberately not
distributed. When a user, advisor, venue, or project requires fidelity to a
particular workbook revision, that lawfully supplied project-local source has
higher authority than this summary. Without that source, the agent may apply
the package convention below but must label any claim about exact EYgp wording
or readiness bands as unavailable for verification.

This boundary implements `GROUNDING_PROTOCOL.md`: the package may own its
operational vocabulary, but it may not attribute exact definitions or numbers
to an unavailable source.

## What the labels do

The labels separate kinds and maturities of research work. They are routing
devices, not the manuscript lifecycle state owned by `phase_state.json`, and
they are not percentages or automatic quality scores.

| Axis | Package interpretation |
|---|---|
| P — problem setting | Move from collecting phenomenon material, through structured characterization, to bounded research problems or questions. |
| R — related work | Move from collecting sources, through analysis of existing approaches, to comparison with the proposed contribution. |
| K — knowledge content | Move from collecting domain knowledge, through an organized conceptual account, to reusable encoded knowledge. |
| S — solution artifact | Move from an exploratory sketch toward progressively more complete internal and external research artifacts. |
| T — tool | Move from an experimental representation toward implementations suitable for progressively wider use. |
| V — validation | Move from illustrative material and toy cases toward larger cases, feedback, and empirical study. |

## Problem-setting convention

The public `p-stage-checker` uses the following package convention.

| Stage | Operational purpose | Typical evidence |
|---|---|---|
| P0 | Assemble and organize material about the phenomenon. | Source collection, tags, observations, and preliminary facets. |
| P1 | Characterize the phenomenon through explicit lenses or dimensions. | Synthesis, classifications, tensions, and candidate questions handed forward. |
| P2 | State bounded research problems, questions, or objectives that can guide solution work. | Explicit problem statements, alternatives, trade-offs, and boundary conditions. |

P0 and P1 should not present later-stage questions as already answered. P2
should do more than repeat a characterization: it commits to problems specific
enough to organize subsequent inquiry. These are harness review heuristics, not
quotations from the unavailable workbook.

## Other-axis convention

### Related work

- R0 collects and groups relevant sources.
- R1 analyzes or synthesizes existing approaches.
- R2 compares the proposed work with existing or alternative approaches.

### Knowledge content

- K0 collects domain-knowledge sources.
- K1 organizes the domain account using concepts, relations, or categories.
- K2 encodes selected knowledge in a reusable structure suitable for retrieval,
  application, or reasoning.

### Solution artifacts

- S1 is an exploratory sketch.
- S2 is a structured technical outline.
- S3 is a technical note suitable for focused internal review.
- S4 is a fuller working report for a knowledgeable, relatively friendly
  audience.
- S5 is a polished artifact prepared for external review or dissemination.

The stages can overlap. A later artifact should make its problem relation,
technical content, evidence, and audience expectations more explicit; the
package does not assign exact lengths, timing rules, or readiness percentages.

### Tools

- T1 represents exploratory mock-ups or experiments.
- T2 captures requirements or design specification.
- T3 is a functional research prototype or demonstration.
- T4 is prepared for limited use by other researchers or collaborators.
- T5 is prepared for broader use, subject to project-specific release gates.

### Validation

- V0 collects illustrative source material or candidate cases.
- V1 uses small or toy examples.
- V2 uses larger, literature-grounded, or comparative examples.
- V3 uses a real-world case study.
- V4 incorporates user or stakeholder feedback.
- V5 uses an empirical study or experiment.

These descriptions guide routing only. The evidence quality of a particular
case remains a grounding judgment.

## Readiness

The package does not distribute or reproduce the workbook's tick-to-percentage
table. Consequently it does not claim exact EYgp readiness scoring. If a
project uses advisor-specific readiness bands, the agent must read the
project-local source and record that source's identity with the resulting
assessment. When no such source is available, report readiness descriptively
and do not invent a numeric or tick conversion.

## Verification procedure

1. Decide whether the request asks for the package convention or exact
   advisor-specific conformance.
2. For the package convention, cite this file and apply the relevant routing
   surface, such as `skills/p-stage-checker/SKILL.md`.
3. For exact conformance, require a lawfully supplied project-local source.
   Record its path or attachment identity in the findings artifact; do not copy
   it into the package tree.
4. If the source is missing, report that exact verification is unavailable.
   Continue only with the package convention when that narrower result answers
   the user's request.
5. Keep inference explicit whenever project-specific terminology extends these
   operational meanings.

## Consumer boundaries

| Consumer | Permitted claim |
|---|---|
| `skills/p-stage-checker/SKILL.md` | The manuscript matches or conflicts with the package P-stage convention. |
| `project_writing_style_checklist.md` | P-stage vocabulary is a package review heuristic. |
| `DETERMINISTIC_CHECKS.md` | Stage-like tokens are candidates for human review, not source-verified violations. |
| Project-specific advisor audit | Exact conformance only after the local source is read and identified. |

## Distribution maintenance

Do not add the external workbook, a transcription, screenshots, or raw source
extracts to this repository. Lawfully acquired copies belong under the ignored
`references/resources/local/` path or in the project that owns them. Any new
redistributed source material requires an explicit disposition in
`references/distribution_rights.json` and must pass
`scripts/distribution-rights-check.py`.
