---
name: claim-coverage-audit
description: Manually-invokable Ph1 → Ph2 admission audit — read manuscript/<section>.md and references/REFERENCES.md, deterministically extract claims, map each to resolving sources, emit a three-set coverage map (covered / partially-covered / uncovered) with score = covered/total at reviews/claim_coverage_<date>_<cycle_id>.md
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/claim-coverage-audit/SKILL.md` and follow it as the binding instruction set for this invocation. Treat that file as the authority for trigger conditions, preconditions, claim-extraction procedure, source-mapping rules, scoring contract, output artefact format, and the determinism guarantee.

If `${CLAUDE_PLUGIN_ROOT}` does not resolve in this host, fall back to `skills/claim-coverage-audit/SKILL.md` from the workspace root the user opened.
