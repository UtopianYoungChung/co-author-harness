# Harness architecture and layout

**When to read:** You need the directory tree, canonical ownership, or consolidation context for `co-author-harness/`.

---

## Package substrate (version: see `.claude-plugin/plugin.json` — no prose version pin per the root rule)

The canonical harness substrate lives at the top level of this directory:

```
co-author-harness/
├── .claude-plugin/plugin.json   # plugin manifest — authoritative version
├── agents/                      # agent prompts (planner, evaluator, generator; reflector router + reflector-probe / reflector-closeout split)
├── skills/                      # slash-command skills (public ladder run-draft / run-iterate / run-finalize; canonical run-phase-1/3/4 + legacy routers; run-reflection, etc.)
├── references/                  # canonical governance references (AGENT_ORCHESTRATION, REVIEW_ORCHESTRATION, GROUNDING_PROTOCOL, PHASE_PROTOCOL, etc.)
├── scripts/                     # phase_state_validate.py, pre_phase_advance_check.py, release-gate.sh, migration scripts
├── research_notes/              # package-tier lessons_learned.md
├── reviews/                     # package-tier review artefacts (ground-truth verification)
├── legacy/                      # plugin-internal legacy (marshal-f1, rule-digest-v060, etc.)
├── releases/                    # build outputs from `scripts/build-release-zip.sh` (`.zip`) and `scripts/build-plugin.py` (`.plugin`); gitignored — local artefacts only
├── CHANGELOG.md, README.md
├── docs/                        # agent-instructions/, concepts/, release-notes/RELEASE_NOTES_v*.md, …
└── CLAUDE.md                    # harness root instructions (this repo)
```

(All paths are relative to this harness root. Any session mounted at `co-author-harness/` or any of its subfolders can reach the package substrate.)

All academic writing rules, review orchestration, agent prompts, skills, safeguard checks, and grounding constraints live inside the four canonical top-level directories named above. The root `CLAUDE.md` does **not** duplicate them.

**Canonical ownership note.** Under Option C″ (2026-04-21), `co-author-harness/` (v0.8.7+; formerly `research-writing-harness/`) is the canonical workspace-root harness. The former `paper-harness/` root has been retired; surviving material from that era is either in this tree or in git history. The legacy plugin-internal tree at `legacy/` (e.g., `research-writing-harness-v0.2.0/`) is retained for release-oracle reference and should be treated as a frozen mirror — never edit there unless a release task explicitly targets it.

For workspace-level ownership and mirror policy, use `../ROOT_ARCHITECTURE_INDEX.md` as the first routing hop.

**Release exports:** shipped `.zip` files under `releases/` unpack to a versioned tree; that tree can differ from this harness root (for example layout or file names). For canonical behaviour, use `agents/`, `skills/`, `references/`, and `scripts/` here — not a stale offline unpack.

---

## Consolidation reference

See [harness-history.md](harness-history.md) for the full consolidation footnote and changelog of this file’s ancestry.
