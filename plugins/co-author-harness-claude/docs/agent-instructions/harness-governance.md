# Precedence and cross-project rules

**When to read:** Two sources conflict, or you work across multiple research projects.

---

## Precedence rules (root level)

When sources disagree, this hierarchy applies (most authoritative first):

1. **User's explicit instruction in the current conversation.**
2. **Venue author guide / call for papers / publisher template.**
3. **Advisor or instructor instruction.**
4. **Project-specific CLAUDE.md or `research_notes/directives.md`** — wins within that project over the package's cross-venue rules.
5. **Package component files** (`references/*.md`, `agents/*.md`, `skills/*/SKILL.md`) — win over any high-level summary until reconciled.
6. **Package references/CLAUDE.md or equivalent roll-up** — wins over this root file when a package rule is in dispute.
7. **Harness root `CLAUDE.md`** — wins over default behaviour but loses to everything above.

This hierarchy is identical to the portfolio-root `Ph.D. Research/CLAUDE.md §5` with one addition: the harness root file explicitly positions itself at level 7.

`references/GROUNDING_PROTOCOL.md` sits *outside* this ladder — it is absolute. No level 1–7 override permits fabrication, uncited numerical claims, or unverified citations.

---

## Cross-project consistency rules

When the agent works on multiple projects in one session or across sessions:

| Rule | Rationale |
|------|-----------|
| **Do not bleed directives.** A directive recorded in Project A's `research_notes/directives.md` does not apply to Project B unless explicitly stated. | Projects may have conflicting venue requirements. |
| **Package-level lessons apply everywhere.** Lessons recorded in `research_notes/lessons_learned.md` at this harness root (if maintained) or in the Reflector's package-level outputs apply to all projects. | Package lessons are cross-project by definition. |
| **Skills are scoped by tier.** Package-level skills apply everywhere; project-level skills apply only to their project. The Reflector decides the tier at creation time. | See `references/SKILL_REGISTRY.md` for the three tiers. |
| **Grounding Protocol is universal.** `references/GROUNDING_PROTOCOL.md` applies to every project, every session, every agent, no exceptions. | Integrity is not project-specific. |
