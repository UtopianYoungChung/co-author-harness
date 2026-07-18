# Harness Audit — Accuracy, Efficiency, Staleness

**Date:** 2026-07-15
**Target:** `co-author-harness` @ manifest `0.29.0` (`.claude-plugin/plugin.json:3`), HEAD `2e34218`
**Method:** full maintainer suite (10 scripts) + semantic read-through of `agents/`, `skills/`, `references/`, `commands/`, `scripts/`, root docs. Three parallel auditors (staleness / accuracy / efficiency); every finding below independently spot-verified against the file.
**Deliverable:** findings only. No files modified.

---

## 0. Headline

**The check suite is 10/10 green and the package is materially incoherent.** This is the same result as the 2026-07-13 audit (L: "green checks ≠ coherence"), but the mechanism is now sharper and worth naming precisely:

> Every gate in this tree verifies *presence*, not *correspondence*. `version-planes-check` verifies that the stale version strings are **still there**. `retirement-sweep-check` verifies that retired names carry a **marker**, not that the surrounding sentence is true. `alias_parity_smoketest` verifies a description **starts with** "Alias for /X" — and thereby pins a claim that three other files contradict. `path-hygiene-check` resolves markdown links **in README.md only**.

The gates have become a ratchet that freezes drift rather than resolving it. The single largest concentration of damage is **one incomplete refactor**: the v0.15.0-pre PR-4c Reflector split updated `agents/` and left every consumer pointing into the file it hollowed out.

**Severity counts:** 3 BLOCKER, 6 MAJOR, 8 MINOR, 1 structural (efficiency).

---

## 1. BLOCKER

### B1 — `skills/run-reflection/SKILL.md` resolves to nothing

`agents/reflector.md` was reduced to a router at PR-4c. It contains **zero** Phase sections (`grep -cE "^#+ .*Phase" agents/reflector.md` → `0`) and says so at `:40`: "This file's only job is to route the dispatch. **It carries no rules of its own.**"

`run-reflection` — a shipped, user-invocable skill with a `commands/` shim — still treats it as the manual:

| Line | Claim | Reality |
|---|---|---|
| `:13` | "Read `agents/reflector.md` **in full** … It is the **complete Reflector operating manual**." | 4,761 B router, no rules |
| `:41` | "Work through all **five phases** as defined in `agents/reflector.md`." | no phases in file |
| `:51` | "the nine-point audit defined in `agents/reflector.md §Phase 2.5`" | anchor dead |
| `:60` | "Per `agents/reflector.md §Phase 2.5 item 8a`" | anchor dead |
| `:68` | "the gating table in `agents/reflector.md §Phase 2.5.1`" | anchor dead |
| `:70` | "per `agents/reflector.md §Phase 2.6`" | anchor dead |
| `:77` | "the four criteria from `agents/reflector.md §Phase 4`" | anchor dead |
| `:81` | "the ten-section template in `agents/reflector.md §Phase 5`" | anchor dead |

An agent invoking `/run-reflection` reads a router, finds no Phase 2.5, and must **improvise the mandatory grounding audit** — the one procedure the package treats as absolute. This is the highest-value fix in the repo: rewrite the skill to dispatch `reflector-probe` / `reflector-closeout` by name.

**Why no check caught it:** nothing validates `§`-anchors across files.

### B2 — `classify-manuscript`, the "mandatory first step," emits a record its consumers cannot read

- `skills/classify-manuscript/SKILL.md:60` emits `- Tier: [T0 / T1 / T2 / T3 / T3R / T4 — default T3; …]`. The ledger field is **`default_final_phase`** with legal values `Ph1`–`Ph4` (`references/phase_state_schema.md:44`, "Renamed at v0.7.4 from `default_final_tier`"). The template emits **no phase value at all**.
- Template (`:49–84`) writes only Paper type / P-stage / Venue / Tier. Consumers read fields it never writes:
  - `skills/seed-snowball-discovery/SKILL.md:28` — reads `claim_coverage_threshold`, `inherit_snowball`, `pre_seed_cap`; "If absent or unparseable: no-op with `CLASSIFICATION_MISSING`. **The user must run `/classify-manuscript` first.**" — running it does not help.
  - `skills/claim-coverage-audit/SKILL.md:34`, `skills/inherit-snowball-from-wiki/SKILL.md:38` — same class.
- Key-form mismatch on top: template writes `- Paper type:` / `- P-stage:`; consumers read `paper_type` / `p_stage`.
- `:13` hard-codes a retired root: "The canonical Windows path is `B:\Agents\Paper\Package`" — `CLAUDE.md:11` declares `paper-harness/` retired and this tree canonical.

The mandatory first step produces a classification record in a vocabulary the rest of the package abandoned at v0.7.4, ~22 minors ago.

### B3 — The full-file-read floor costs ~141,500 tokens per `/run-iterate`, per agent hop

`skills/run-phase-3/SKILL.md:10` (Grounding basis) names 10 files; the round dispatches 3 agent contracts on top. Measured:

| File | bytes |
|---|---|
| `references/PHASE_PROTOCOL.md` | 119,935 |
| `agents/planner.md` | 101,922 |
| `references/phase_state_schema.md` | 57,596 |
| `references/SAFEGUARD_LAYER.md` | 45,775 |
| `references/DETERMINISTIC_CHECKS.md` | 41,384 |
| `agents/generator.md` | 36,584 |
| `agents/evaluator.md` | 34,601 |
| `references/ARTEFACT_FRONTMATTER_SCHEMA.md` | 33,437 |
| `references/GROUNDING_PROTOCOL.md` | 29,200 |
| `references/REVIEW_ORCHESTRATION.md` | 28,728 |
| `references/PHASE3_PHASE4_COMMON_ENVELOPE.md` | 8,549 |
| `run-phase-3` + `run-iterate` SKILL.md | 28,366 |
| **Total** | **566,077 B ≈ 141,500 tok** |

The Rule 1 digest exception was retired at v0.7.4, making this non-negotiable and restated as invariant in five places (`agents/evaluator.md:274` "Digest reads are no longer a valid grounding basis at any phase."; `:46`; `:183`; `agents/generator.md:4`; `skills/run-phase-1/SKILL.md:22`). Dispatch is 2 skill hops + 4 agent hops, and **the read set is re-paid per agent context** — `PHASE_PROTOCOL.md` (~30K tok) alone is read by Planner and Evaluator both.

Classified BLOCKER because it is a *rule*, not a file: no digest, no §-scoped read, no caching escape hatch exists. It cannot be fixed by trimming prose.

---

## 2. MAJOR

### M1 — `agents/reflector.md` ships a self-contradiction

- `:19` — "**Retirement condition (2026-07-06, supersedes 'retained for one minor'):** this router is deleted only when the host dispatch surface no longer lists `reflector` as an agent type."
- `:48` — "The router is retained for **one minor version** … After that window (no earlier than the next minor following the v0.15.0 release), this file is removed"

Line 19 announces it supersedes line 48; line 48 was never deleted. The plan prescribed exactly this: `docs/analysis/2026-07-06_systematic-improvement-plan.md:36` — "**replace the open-ended promise** with a dated header note". The note was *added*; the promise was not *replaced*. Line 48's window (v0.16.0) expired **thirteen minors ago**.

### M2 — That retirement condition is unsatisfiable by construction

`:19` gates deletion on "the host dispatch surface no longer lists `reflector` as an agent type." The host derives agent types **from `agents/*.md` in this plugin** — this session's dispatch surface lists `co-author-harness-claude:reflector`, sourced from that very file. The file's own existence is the sole cause of the condition forbidding its deletion. No external event can satisfy it. Needs rewriting to a condition about *in-tree callers* — which, per B1/M3, are still live and would block deletion honestly.

### M3 — Four more dead `§Phase` anchors into the gutted router

- `skills/run-phase-4/SKILL.md:10` — "`agents/reflector.md §§Phase 2b, 3, 4, 5`"
- `skills/run-phase-4/SKILL.md:115` — "§§Phase 2b, 2.5, 2.5.1, 3, 4, 5"
- `skills/run-phase-1/SKILL.md:54` — "§Phase 2.5.1"
- `references/PROJECT_BOOTSTRAP.md:625` — "`agents/reflector.md §Phase 3.5`" — **worse: Phase 3.5 exists in neither the router nor either split file.** `grep -rn "Phase 3.5" agents/` returns only `planner.md:305` (a different agent) and `generator.md:37,103,194` (retired-at-v0.7.0 notices). Coupling C's normative pointer has been wrong since before the split.

### M4 — `run-iterate` alias direction is inverted, and the smoketest pins the inversion

Four files say run-iterate is canonical; its own frontmatter says it's an alias, and a gate enforces that:

- `skills/run-iterate/SKILL.md:3` — "**Alias for /run-phase-3** … /run-iterate **is the canonical public surface**" (both, in one sentence)
- `commands/run-iterate.md:3` — "canonical post-draft iteration surface"
- `skills/run-phase-3/SKILL.md:14` — "The public stage surface is now `/run-iterate`. This file remains the compatibility body."
- `references/SKILL_REGISTRY.md:408` — "Public iterate stage/profile router"; `:412` — "**Depends on:** `skills/run-phase-3/SKILL.md` (**canonical body**)" — same entry, both readings
- `scripts/alias_parity_smoketest.py:34` `ALIAS_PAIRS = [… ("run-phase-3", "run-iterate")]`; `:118` `assert desc.startswith(f"Alias for /{canonical}")`

**run-iterate's frontmatter cannot be corrected without failing a currently-passing gate (8/8).** `run-draft`/`run-finalize` don't have this problem — both cleanly declare run-phase-1/run-phase-4 canonical. This is the sharpest instance of the headline pattern: the gate actively defends the wrong claim.

### M5 — `schema_version` roll never landed; the schema contradicts itself, and nothing adjudicates

- `references/phase_state_schema.md:41` — "`schema_version` | string | `"0.7.4"` (**exact match**)"
- `:7` — "the bump to `"0.10.0"` lands at the v0.10.0 RC gate via `scripts/migrate_v090_to_v100_snowball_fields.py`"
- `scripts/migrate_v090_to_v100_snowball_fields.py:114` — `SCHEMA_FROM = "0.7.4"` / `SCHEMA_TO = "0.10.0"`

At v0.29.0 a ledger is either `0.7.4` (contradicting the announced roll) or `0.10.0` (contradicting the exact-match rule). **`SUPPORTED_SCHEMA_VERSION = "0.7.4"` at `scripts/phase_state_validate.py:88` is never referenced anywhere else in that file** — the validator does not check `schema_version` at all. §1.1's "exact match" is unenforced prose.

### M6 — `plugin-commands` catalog asserts retired vocabulary and a corrupted row

`/plugin-commands` is the orientation surface — the first thing a new user or unclassified project reads.

- `:75` — "Check 8's **six** … Sub-checks (**A–F**) … Dormant at T1, T2 severity-floored, full severity at T3/T4" vs `skills/accessibility-overlay/SKILL.md:35,37` — "the **eight** Sub-checks A–H"; "**Check 8 is exactly A–H.**"; `:39` — "it does **not** create tier-specific membership or severity exceptions." (G added v0.8.1, H at v0.10.1.)
- `:53` — "`[T3-STALE]` computed from `t3_last_activity_at` … the default `default_final_tier: T3` dispatch" vs real names `[Ph3-STALE]` / `ph3_last_activity_at` (`PHASE3_PHASE4_COMMON_ENVELOPE.md:58`) / `default_final_phase`.
- `:47` — "no Self-T1 Verdict (retired at v0.7.0)" — the construct is `Self-Ph1`.
- `:57` — corrupted 4-cell row in a 3-column table (`/run-iterate`).

**Why the sweep passes:** `retired_surfaces.json` `retired_phrases` registers only count-claims (`15-field`, `30-trigger`, `six-field row`) and `Lifecycle-Stage Ladder`. **No tier-vocabulary strings are registered** — `T3-STALE`, `default_final_tier`, `Self-T1`, `t3_last_activity_at` are invisible to the gate.

---

## 3. MINOR

| # | Finding | Evidence |
|---|---|---|
| m1 | 5 broken relative links, all on lines marked "**MANDATORY — READ ENTIRE FILE**". Resolve against `skills/<name>/`, not plugin root. | `skills/advisor-escalation/SKILL.md:16,134`; `skills/grounding-audit/SKILL.md:25,27`; `skills/graph-grounding-overlay/SKILL.md:84`. `path-hygiene-check.py:86` resolves links **in README.md only**. |
| m2 | Stale absolute paths to the retired root | `skills/run-reflection/SKILL.md:15`, `skills/classify-manuscript/SKILL.md:13` — "`B:\Agents\Paper\Package`". `BLOCKED_PATTERNS` (`:33-36`) blocks only `C:\Users\young\` / `/Users/young/`. |
| m3 | Retired shim described in **live voice** at v0.29.0 | `references/phase_state_schema.md:274` — "The legacy `scripts/tier_state_validate.py` **is** a forwarding shim" (removed at v0.7.5). Sweep clears it on the "legacy" marker. |
| m4 | `scripts/` escapes the retirement sweep | `scripts/phase_state_validate.py:103` — "`# Required SectionStateObject top-level fields (v0.7.4 15-field schema).`" — `15-field` is a registered retired phrase; sweep scans `.md` only. |
| m5 | Command shim advertises the legacy rule as current | `commands/run-phase-3.md:3` "**two-round** stability test" vs `skills/run-phase-3/SKILL.md:3` "**three stable rows**"; authority `PHASE3_PHASE4_COMMON_ENVELOPE.md:48` — three consecutive for v0.8.0 object rows; two-round is legacy scalar only. |
| m6 | Internally contradictory command shim | `commands/classify-manuscript.md:3` — "default final **tier (T1–T4 / T3R)** of the **v0.8.0 Lifecycle-Phase Ladder**". The phase ladder has no tiers. |
| m7 | Trigger enum: 31 is cardinality, not active count | `agents/planner.md:146` — "the **31-trigger active enum**" vs `phase_state_schema.md:196` — trigger 13 "**RETIRED at v0.11.0** … v0.11.0 ledgers do not emit this trigger." Active = 30. (The `31` figure itself is correctly pinned; the word "active" is the error.) |
| m8 | Reflector phase count fork | `agents/reflector.md:4` "**five-phase** reflection" vs `agents/reflector-closeout.md:8` "**Phases 1–6 inclusive**". Also `AGENT_ORCHESTRATION.md:61,781`, `SKILL_REGISTRY.md:30`, and `references/templates/F4_reflector_full_report.md:90` say five — while `:7` of that same template says 1–6. |

**Honest negative — orphaned docs are NOT a problem.** 8 of 143 docs have zero inbound refs: 5 archival release-notes, 1 transient handoff, 2 dated today (in-flight). `references/` and `research_notes/` are fully reachable.

**Honest negative — several accuracy claims check out clean.** Planner's `18-field` / `31-trigger` / `7-field row` all match `phase_state_schema.md:66,78-97,167-176,184-215`. 22 commands all route to existing skills; 42 skills all appear in the catalog. README derives its skill count rather than hard-coding it (`README.md:34`). `quick-deterministic`'s "seven style/craft auditors" matches `scripts/audit/run_all.py:40-48`. All 18 cited scripts exist.

---

## 4. Efficiency (measured)

| # | Sev | Finding | Cost |
|---|---|---|---|
| S1 | BLOCKER | Full-file-read floor (= **B3**) | 566,077 B ≈ 141,500 tok × 4 agent hops |
| S2 | HIGH | `PHASE_PROTOCOL.md` 119,935 B = **9.5% of the 1.26 MB `references/` corpus in one file**; `agents/planner.md` 101,922 B = **48% of all six agent files**, 21× the median. Both mandatory reads under S1. | ~55,500 tok, unavoidable |
| S3 | HIGH | Agent descriptions mean **1,223 chars** vs 329 for skills — 6 agents burn 35% of the budget 42 skills use. **20% (1,453 chars) is version narration; 36% (2,611 chars) is `<example>` blocks.** | 1,834 tok/session; ~1,015 removable |
| S4 | MEDIUM | `AGENTS.md` is a **19-line diff** from `CLAUDE.md`. Repo-wide: 9 duplicated blocks ≥180 chars, 5,201 redundant chars. The 10-script bash block is verbatim in **3 files**. | ~1,734 + ~1,300 tok |
| S5 | MEDIUM | `skill-check.py` and `catalog-check.py` **independently re-implement** `discover_skills()`, `parse_plugin_commands()`, `parse_registry_names()` and assert the same 2 invariants twice (`skill-check:168-184,192-202` ≡ `catalog-check:232-239,246-251`). Two parsers of the same two files that can drift apart. | maintainer-time |
| S6 | LOW | `CHANGELOG.md` 352,373 B ≈ 88,000 tok ships in every install (`scripts/build-plugin.py:80` `REQUIRED_FILES`); **zero runtime reads** — all 5 mentions are pointer prose. Hazard: `skills/run-phase-3/SKILL.md:10` names it *inside* the Grounding basis list that S1 governs. | 88,000 tok payload |

**The irony worth naming:** `agents/reflector.md:21` records that the Reflector was split precisely to "reduce the 20,113-token always-loaded surface." `planner.md` (~25,500 tok) and `PHASE_PROTOCOL.md` (~30,000 tok) are each **larger than the surface that justified that split**. The precedent exists; it was not applied to the two biggest files. Meanwhile the router left behind burns ~330 tok/session — including a 476-char `<example>` block — to announce its own obsolescence.

**Snippet mechanism is barely used:** `references/_snippets/` holds 2 files pulled by 6 sites. None of the 9 duplicated blocks is snippeted, despite `resolve_includes.py` + `snippet-check.py` existing for exactly that. `agents/reflector.md:42` even documents a *deliberate* copy — "mirrored from snippet for the static guard" — because `output_economy_check.py` can't resolve includes.

**Mandatory per-session floor before any work:** ~5,293 tok (48 descriptions) + ~1,722 tok (`CLAUDE.md`) ≈ **7,015 tok**, or ~8,749 if `AGENTS.md` also loads. That's the cheap part. S1 is the expensive part.

---

## 5. The gate-scope map (why 10/10 green means little)

| Gate | Verifies | Blind to |
|---|---|---|
| `version-planes-check` | registered strings are **still present** (snapshot mode, `snapshot_date: 2026-07-07`) | whether they're **right**. `fork_note`: "Recorded, **tolerated**, scheduled for harmonization." Pins 0.7.4/0.8.0/0.15.0-pre at package 0.29.0. |
| `retirement-sweep-check` | retired names carry a marker; registered count-phrases absent | tier vocabulary (unregistered); `scripts/` (scans `.md` only); truth of the marked sentence |
| `alias_parity_smoketest` | `desc.startswith("Alias for /X")` | whether X is actually canonical — **pins the M4 inversion** |
| `path-hygiene-check` | `C:\Users\young\` patterns; links **in README.md only** | `B:\Agents\Paper\Package`; all links in `skills/` (m1, m2) |
| `skill-check` / `catalog-check` | frontmatter, counts, name parity | `§`-anchor resolution (B1, M3); producer/consumer field contracts (B2) |
| all | presence | **correspondence** |

`CLAUDE.md:7` (verbatim in `AGENTS.md:7`): "**No prose document in this tree asserts a version number; consult the manifest.**" `agents/` asserts **16 distinct version strings** — `v0.5.0 v0.5.4 v0.5.5 v0.6.0 v0.7.0 v0.7.3 v0.7.4 v0.7.5 v0.8.0 v0.8.4 v0.9.0 v0.10.0 v0.13.0 v0.14.0 v0.15.0 v0.15.0-pre`. **None is 0.29.0.** `version_planes.json` does not resolve this; it *ratifies* it. Harmonization has been deferred since 2026-07-07 (`docs/analysis/2026-07-06_systematic-improvement-plan.md:93` §9).

---

## 6. Recommended sequence

1. **B1** — rewrite `skills/run-reflection/SKILL.md` to dispatch `reflector-probe` / `reflector-closeout` by name. Only shipped skill whose core procedure resolves to nothing.
2. **M3** — fix the 4 remaining dead anchors; decide what `PROJECT_BOOTSTRAP.md:625`'s "Phase 3.5" was meant to name.
3. **B2** — rebuild the `classify-manuscript` template around `default_final_phase` + the `paper_type`/`p_stage`/`claim_coverage_threshold`/`inherit_snowball`/`pre_seed_cap` keys consumers actually read.
4. **M4** — decide the canonical direction once, then make `alias_parity_smoketest` express it (the gate must follow the decision, not precede it).
5. **M6** + m5/m6 — refresh `plugin-commands` and the command shims; **register the tier vocabulary in `retired_phrases`** so this class can't recur.
6. **M1/M2** — delete the superseded promise; restate the retirement condition in terms of in-tree callers.
7. **M5** — make `phase_state_validate.py` actually check `schema_version`, or delete the exact-match prose.
8. **Ladder harmonization** (deferred since 2026-07-07) — the 16-version fork in `agents/`. Gates the whole staleness class.
9. **Efficiency**: S3 is free (trim version narration + examples from agent descriptions, ~1,015 tok/session). S6 is nearly free. S2/S1 are a design decision about whether the full-file floor survives contact with a 566 KB read set.

---

## 7. Grounding note

Every finding cites path + line + verbatim quote and was verified against the file, not inferred. Findings B1, B2, M4, M6 and the `retired_phrases` scope claim were independently re-verified in the primary session after subagent report. `reviews/plugin_update_proposals.md` was uncommitted (`M`) at audit time and was not relied upon. No claim here rests on `CHANGELOG.md` narrative.
