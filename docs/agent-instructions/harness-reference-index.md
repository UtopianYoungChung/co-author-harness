# What the harness root AGENTS.md is not — and where to read rules

**When to read:** You need the canonical file index or a reminder not to treat this repo’s root `AGENTS.md` as the full rule source.

---

## What the harness root AGENTS.md is NOT

- **Not** a rule source. Rules live in the package component files under `agents/`, `references/`, and `skills/`.
- **Not** a substitute for reading the package orchestration files. The root file delegates; it does not replicate.
- **Not** project-specific. Project-specific guidance lives in each project's own AGENTS.md and `research_notes/` folder.
- **Not** a Claude-specific instruction file. This package has no `CLAUDE.md`.

---

## Related files (index)

Entries below use paths **under this harness** unless noted. Rows that point to `../Ph.D. Research/` or `../ROOT_ARCHITECTURE_INDEX.md` assume a **workspace sibling** layout (multi-root checkout). Those files are not inside `co-author-harness/` when this repo is cloned alone.

| File | Location | Role |
|------|----------|------|
| AI harness concept (workspace) | `docs/concepts/ai-harness.md` | Prompt vs harness engineering explainer; not part of the shipped plugin bundle |
| Release notes (per version) | `docs/release-notes/RELEASE_NOTES_v*.md` | Point-in-time ship notes; lean release zips exclude historical files (see `scripts/build-release-zip.sh`) |
| Package identity | `version.json` | Authoritative current name, version, and license |
| Host metadata | `plugin.json` | Published metadata; identity fields mirror `version.json` |
| Claude host pack | `.claude-plugin/plugin.json` | Claude Desktop / Cowork loader identity; name and license mirror `version.json`, no version (installs track commits) |
| Claude marketplace | `.claude-plugin/marketplace.json` | Marketplace-add entry; self-referencing name and license mirror `version.json`, no version |
| Output economy protocol | `references/OUTPUT_ECONOMY_PROTOCOL.md` | F7/F8 artefacts, events log, final report assembly, compatibility pointers (v0.14.0+) |
| AGENT_ORCHESTRATION.md | `references/AGENT_ORCHESTRATION.md` | Four-agent architecture + lifecycle dispatch |
| REVIEW_ORCHESTRATION.md | `references/REVIEW_ORCHESTRATION.md` | Review pipeline runbook (Steps 0a–8.5) |
| PHASE_PROTOCOL.md | `references/PHASE_PROTOCOL.md` | Lifecycle-Phase Ladder canonical spec (v0.7.4; §3.3.3 for Check 8 gate) |
| GROUNDING_PROTOCOL.md | `references/GROUNDING_PROTOCOL.md` | Binding no-hallucination rules |
| SAFEGUARD_LAYER.md | `references/SAFEGUARD_LAYER.md` | Eight SAFEGUARD checks (Check 8 = Reader-Experience / Prose Architecture) |
| DETERMINISTIC_CHECKS.md | `references/DETERMINISTIC_CHECKS.md` | Mechanical pre-flight (Step 0a) |
| AGENT_CONTRACTS.md | `references/AGENT_CONTRACTS.md` | Per-agent preconditions, inputs, outputs, invariants |
| STYLE_COMMITMENTS.md | `references/STYLE_COMMITMENTS.md` | Package-tier commitments (C-5 = accessibility) |
| PROJECT_BOOTSTRAP.md | `references/PROJECT_BOOTSTRAP.md` | New project setup protocol |
| SKILL_REGISTRY.md | `references/SKILL_REGISTRY.md` | Three-tier skill registry |
| phase_state_schema.md | `references/phase_state_schema.md` | 18-field `SectionStateObject` + 31-trigger enum |
| phase_state_validate.py | `scripts/phase_state_validate.py` | Validator (monotonicity with 3 documented exemptions) |
| release-gate.sh | `scripts/release-gate.sh` | Release-gate probe |
| Portfolio CLAUDE.md | `../Ph.D. Research/CLAUDE.md` | Peer root governing papers-in-flight |
| ROOT_ARCHITECTURE_INDEX.md | `../ROOT_ARCHITECTURE_INDEX.md` | Workspace-level canonical-ownership contract |
