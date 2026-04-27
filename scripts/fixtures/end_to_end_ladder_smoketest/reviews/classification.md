# Classification Record

**Piece:** end-to-end ladder smoketest fixture
**Date:** 2026-04-27
**Classified by:** smoketest harness (synthetic)

## Inputs
- Paper type: theory
- P-stage: P2
- Venue: cross-venue
- Tier: T3
- default_final_phase: Ph3

## Component file applicability

| File | Applies | Notes |
|---|---|---|
| general_research_project_guidelines.md | Y | |
| research_paper_writing_guidelines.md | Y | |
| project_writing_style_checklist.md | Y | P2 register active |
| GROUNDING_PROTOCOL.md | Y | full-file reads at every phase |

## Notes

Smoketest fixture authored at v0.11.0 c10 per the
definitive-architectural-plan §3.5. Represents a single-section
manuscript at Ph1 entry; the assertion harness exercises the
seven-clause pre_phase_advance_check.py guardrail against this fixture
without dispatching agents.

The v0.7.1 `sd_sr_required` field is intentionally absent: v0.11.0 c1
retired the SD/SR opt-in machinery (see RELEASE_NOTES_v0.11.0.md);
fresh classification.md files at v0.11.0 do not declare it.
