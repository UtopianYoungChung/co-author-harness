# Advisory-until scoping (A7)

**When to read:** You are the Planner or Reflector, and a Check 8 Sub-check, SAFEGUARD gate, or new protocol row is in **advisory-only** or **advisory-until** mode for a specific manuscript, phase, or revision.

**Purpose.** One place to record the **machine- and human-readable** condition that limits advisory behaviour so the manuscript does not suffer split-brain gate behaviour. Pair every advisory-until with a single `directives.md` or `SAFEGUARD_LAYER.md` cross-reference and the plugin version in force when the flag was set.

**Pattern (minimal)**

1. **Scope** — name the checker and its profile transition key; never encode live state in prose.
2. **Condition** — the exact disjunction that retires the flag (e.g. “next Ph1 classification file dated after 2026-04-23” or “user-published `G_binding: full` in `directives.md`”).
3. **Artefact** — one file carries the author-facing sentence; the other file carries the machine mirror (`advisory_scope_key` in frontmatter, if your project uses it).

**Cross-refs**

- `references/PHASE_PROTOCOL.md` §3.3.3 (Check 8 gate).
- `references/SAFEGUARD_LAYER.md` Check 8 Sub-check G (stability and advisory-until interaction).
- `proposals/check8_subcheck_g_consolidation_anchors_proposal.md` (implementation log, if present in your tree).

*Package addition v0.8.4 (A7-advisory-until-template).*
