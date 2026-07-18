# Release Notes — research-writing-harness-claude v0.8.2

**Released:** 2026-04-24

## Summary

v0.8.2 is a skill-body quality patch release. A skill-judge audit of v0.8.1 (27 skills against the Anthropic skill-design rubric) scored the plugin 97/120 (B, 81%) and flagged three systemic issues — boilerplate duplication, thin description-field activation surfaces, and absent progressive disclosure. v0.8.2 applies mechanical and surgical fixes to all three without touching capability, skill surfaces, agent contracts, or gate wiring. Every agent that was valid at v0.8.1 remains valid at v0.8.2; every frontend invocation pattern is unchanged. Expected post-patch score: ~106/120 (A−, 88%).

The release also fixes a v0.8.1 release-zip defect where two nested zips (`releases/research-writing-harness-claude-v0.7.4.1.zip` and `releases/research-writing-harness-claude-v0.8.0.zip`) were packaged inside the v0.8.1 zip, triggering the Claude Code plugin loader's "A zip file cannot have a nested zip file" refusal. The v0.8.2 zip is built against the canonical `scripts/build-release-zip.sh` exclusion list with added post-build verification for nested-zip entries.

## What changed

### Quality — boilerplate removal (13 SKILL.md files)

A ~500-character blockquote titled `> **File resolution (plugin context).**` was duplicated verbatim across 13 SKILL.md bodies. Its stated purpose — translate legacy absolute paths to `${CLAUDE_PLUGIN_ROOT}/references/` — is obsolete for any session that reaches a skill. The block is removed from: `IS-theory-pass`, `advisor-escalation`, `check-abstract-body`, `check-contradictions`, `classify-manuscript`, `narrative-structure-pass`, `p-stage-checker`, `quick-deterministic`, `response-letter-review`, `run-reflection`, `sentence-level-pass`, `suchman-register-audit`, `tool-contract-roundtrip`. All 13 pass frontmatter validation post-edit.

### Quality — description thickening (12 SKILL.md files)

12 SKILL.md `description:` fields sat below ~160 characters with weak trigger-keyword coverage. Each was rewritten to carry the capability statement plus an explicit `Use when: "..."` trigger-phrase block, pushing descriptions into the 275–337 char band (all at or below the 350-char plugin-manifest ceiling). Skills affected: `check-contradictions`, `plugin-commands`, `quick-deterministic`, `p-stage-checker`, `check-abstract-body`, `sentence-level-pass`, `IS-theory-pass`, `grounding-audit`, `public-interest-accountability-pass`, `narrative-structure-pass`, `suchman-register-audit`, `promote-lessons-to-wiki`. Each skill's `trigger:` field was already rich; the change propagates that richness to the activation surface (`description:`) which is the only pre-load field the Agent sees.

### Quality — progressive disclosure (4 SKILL.md files split into per-skill `references/`)

Four long skills had detail blocks extracted into per-skill `references/` subdirectories with `MANDATORY — READ ENTIRE FILE` triggers at the workflow points where detail is loaded:

| Skill | SKILL.md before | SKILL.md after | references/ file | Extracted content |
|---|---:|---:|---|---|
| `accessibility-overlay` | 214 | 157 | `sub_checks.md` (68) | Sub-checks A–G threshold + severity-floor specs |
| `grounding-audit` | 249 | 116 | `audit_categories.md` (147) | 8 audit-category rubrics with verification procedures |
| `advisor-escalation` | 298 | 223 | `external_reclassification.md` (89) | Step 4: 4 attribution-pattern regexes + 4a–4d procedure |
| `graph-grounding-overlay` | 232 | 198 | `finding_types.md` (46) | Phase 3 Finding A/B/C specs + three-tier matcher thresholds |

Combined: 993 → 694 lines in SKILL.md bodies (30% reduction), ~350 lines parked behind MANDATORY triggers. Each extracted file opens with a statement of what it owns versus what SKILL.md owns.

### Build hygiene

The v0.8.2 zip is built against the canonical `scripts/build-release-zip.sh` exclusion list: 0 nested zips, 0 `__pycache__`/`.pyc`, 0 `releases/` entries, 0 boilerplate instances, 27/27 SKILL.md frontmatters valid, 4 new `skills/*/references/` subdirectories, 206 files / 983 KB. Integrity PASS.

## What did not change

- No skill added, removed, or renamed.
- No slash-command behaviour changed.
- No `phase_state.json` field rename, no trigger-enum change, no `SectionStateObject` schema change.
- No severity-floor change, no agent-contract change, no gate-wiring change.
- Sub-check G `advisory_until: next_manuscript_at_ph3` transitional flag and stability-sub-mode advisory rule carry forward unchanged.
- Phase protocol, review orchestration, grounding protocol, safeguard layer — all untouched.

## Deferred / future work

### Skills still above the 200-line threshold

`tool-contract-roundtrip` (230 lines) and `response-letter-review` (212 lines) sit just above the progressive-disclosure threshold but lack an obvious natural split boundary. Marked as candidates for a future pass rather than force-splitting now.

### Source-of-truth layout

The harness root (`agents/`, `skills/`, `references/`, `scripts/`) is the canonical working tree. Optional local `unpacked/<version>/` mirrors (from a release `.zip`) are not required for development and are not kept under version control; release cuts use `scripts/build-release-zip.sh` from this root.

## Upgrade path

Drop-in. Uninstall v0.8.1, install v0.8.2, no state migration required. Existing `reviews/phase_state.json` records, `reviews/classification.md` records, and `reviews/safeguard_check8_*.md` findings continue to parse and advance through the ladder under v0.8.2's identical contracts.

## Related

- Audit that surfaced the three issues: `skill-judge` plugin (score 97/120 at v0.8.1; expected 106/120 at v0.8.2).
- CHANGELOG entry: `CHANGELOG.md §v0.8.2 — 2026-04-24`.
- Build: `scripts/build-release-zip.sh` (unchanged; reproduces under `build-release-zip.sh research-writing-harness 0.8.2`).
