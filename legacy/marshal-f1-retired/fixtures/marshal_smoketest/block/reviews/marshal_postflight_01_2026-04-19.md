---
round: 1
tier_entered: T3
date: 2026-04-19
plugin_version: 0.5.5
marshal_schema_version: 1
---

# Marshal Postflight — Round 1 (T3)

STATUS: WARN

## Blocking checks

_(no blocking checks in scope for this tier)_

## Advisory checks

- **Q-1** — state_probe_<date>.md emitted (N/A at T3): N/A
- **Q-2** — tier_closeout_<round>_<date>.md emitted: WARN
  - Recommendation: [ADVISORY-ONLY mode: would BLOCK at F.2] T1+ rounds must emit reviews/tier_closeout_01_<date>.md (TIER_PROTOCOL §11.9 invariant 1). SAFEGUARD Check 5 structural violation if absent.
- **Q-3** — tier_closeout schema valid: WARN
  - Recommendation: [ADVISORY-ONLY mode: would BLOCK at F.2] closeout missing (see Q-2).
- **Q-4** — escalation_log has row(s) for round: WARN
  - Recommendation: [ADVISORY-ONLY mode: would BLOCK at F.2] reviews/escalation_log.md has no row for round 1. Every tier transition (including initial-dispatch) emits a row; see AGENT_ORCHESTRATION §8.2a.
- **Q-5** — tier_decisions_log has row for Phase 5.5: WARN
  - Recommendation: [ADVISORY-ONLY mode: would BLOCK at F.2] No row for round 1 in tier_decisions_log.md. Phase 5.5 is non-skippable at T1+ (TIER_PROTOCOL §11.9 invariant 1).
- **Q-6** — tier-scoped artefact present: WARN
  - Recommendation: [ADVISORY-ONLY mode: would BLOCK at F.2] No consolidated_findings_report_<date>.md under reviews/. The tier's Evaluator output is missing.
- **Q-7** — tier_entered_via consistent with escalation_log terminal (N/A): N/A
- **Q-8** — ascent_observed consistent with decisions-log header (N/A): N/A
- **Q-9** — orphan artefacts in reviews/ (1 file(s)): revision_log.md: WARN
  - Recommendation: Formalise as a new artefact type in TIER_PROTOCOL.md, rename to match an existing type, or delete after review. Always advisory; never a BLOCK.
- **Q-10** — G.4 sign-off emitted (N/A at T3): N/A
- **Q-11** — manuscript diff non-empty if any edit was made: WARN
  - Recommendation: No revision_log.md present; cannot verify edit non-emptiness.

## Override record

- Round program override-tags read: []
- Overrides applied this round: []

