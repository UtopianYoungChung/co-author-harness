# WP8 distribution-rights and H2 impact audit

**Scope:** current tree and future package artifacts only. Historical commits,
tags, and previously published archives are outside this forward-looking
remediation.

## Distribution change

The current package no longer distributes the three raw book extracts, the
EYgp workbook or its mechanical transcription, or the prior long-passage
accessibility corpus and the two planning documents that reproduced it.
`references/distribution_rights.json` records the deletion-time whole-file and
long-passage fingerprints. `scripts/distribution-rights-check.py` blocks their
return, binds the replacement files, and verifies its enforcement wiring.

The gate establishes absence of the registered byte identities and passage
fingerprints in the candidate population. It does not make a legal
determination, detect arbitrary paraphrase, or rewrite Git history.

## Capability impact

| Capability | Registry disposition | Replacement effect | H2 result |
|---|---|---|---|
| `accessibility-overlay` | `degraded`, `prompt-mediated` | Stable corpus path now contains package-authored synthetic A-H illustrations; the policy and judgment procedure remain authoritative. | No disposition change. |
| `p-stage-checker` | `degraded`, `prompt-mediated` | Uses the package's non-verbatim P-stage convention. Exact EYgp/advisor conformance now fails closed unless a project-local source is supplied. | No disposition change; prior exact-source overclaim removed. |
| `grammar-mechanics-pass` | `degraded`, `prompt-mediated` | Package-authored Blue Book synthesis remains; raw source extract is absent. | No disposition change. |
| `citation-format-pass` | `degraded`, `prompt-mediated` | Package-authored Turabian/Chicago synthesis remains; raw source extract is absent. | No disposition change. |
| `turabian-format-pass` | `degraded`, `prompt-mediated` | Uses the same synthesized guideline and continues to defer exact physical values to the manual and venue template. | No disposition change. |
| `seed-snowball-discovery` | `external-dependent`, `prompt-mediated` | Package-authored Abbott process synthesis remains; raw source extract is absent. | No disposition change. |

`references/capabilities.yaml` is unchanged. Therefore this repair does not
alter an approved H0 capability disposition and does not reopen H2 under the
repair programme's stated trigger. Focused capability, accessibility, skill,
and catalog checks must still pass before commit, followed by the authoritative
fixture registry after the deletion commit is census-visible.
