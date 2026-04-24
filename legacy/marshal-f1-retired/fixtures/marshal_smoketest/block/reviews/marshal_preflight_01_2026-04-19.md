---
round: 1
tier_requested: T3
date: 2026-04-19
plugin_version: 0.5.5
marshal_schema_version: 1
---

# Marshal Preflight — Round 1 (T3 requested)

STATUS: WARN

## Blocking checks

- **P-12** — no unresolved prior-round BLOCK postflight (latest: marshal_postflight_01_2026-04-19.md → WARN): PASS
- **P-13** — round_program override-tags use legal enum (no tags present): PASS

## Advisory checks

- **P-1** — classification.md exists: WARN
  - Recommendation: [ADVISORY-ONLY mode: would BLOCK at F.2] Run /classify-manuscript and save the result to reviews/classification.md.
- **P-2** — classification.md has tier: field: WARN
  - Recommendation: [ADVISORY-ONLY mode: would BLOCK at F.2] classification.md missing (see P-1).
- **P-3** — classification.md tier: matches requested tier: WARN
  - Recommendation: [ADVISORY-ONLY mode: would BLOCK at F.2] classification.md missing (see P-1).
- **P-4** — rule digest present (N/A at T3): N/A
- **P-5** — digest plugin-version matches plugin.json (N/A at T3): N/A
- **P-6** — manuscript/revision_log.md readable: WARN
  - Recommendation: No revision_log.md yet; Generator will create on first append. Legitimate in first-run projects.
- **P-7** — tier-decisions log readable (or legitimately absent): WARN
  - Recommendation: No tier_decisions_log.md yet. First Phase 5.5 election will create the header (bootstrap exemption; see §8.3.11).
- **P-8** — requested tier legal under ratchet (first-round latitude): WARN
  - Recommendation: No ascent_observed ratchet yet; confirm the requested tier is intentional.
- **P-9** — T2 local-scope envelope computable (N/A at T3): N/A
- **P-10** — response_letter.md present (N/A at T3): N/A
- **P-11** — Class-1 verifier reachable (N/A at T3): N/A

## Override record

- Round program override-tags read: []
- Overrides applied this round: []

