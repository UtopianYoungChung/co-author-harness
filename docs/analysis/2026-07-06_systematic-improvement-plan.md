# Systematic Improvement Plan — co-author-harness-claude

**Date:** 2026-07-06
**Baseline:** v0.21.0 (manifest), all seven structural checks passing, 0 blockers / 0 warnings.
**Method:** Evidence-first audit (deterministic check run + repo-wide staleness/redundancy/version survey + quantitative size inventory) → plan draft → adversarial review by a clean-context reviewer agent (13 findings: 2 BLOCKER, 6 MAJOR, 5 MINOR — all integrated below, marked `[AR-n]`) → implementation.
**Status legend:** `PLANNED` → flipped to `IMPLEMENTED` / `SCAFFOLDED` per workstream only after the work verifiably lands `[AR-1]`.

---

## 1. Problem statement

The harness is structurally sound at the deterministic layer — the seven maintainer checks pass cleanly — but its growth pattern creates four systemic risks that no current check owns:

1. **Version-plane sprawl.** Prose in `agents/` asserts at least fourteen distinct version identifiers (`v0.5.5` … `v0.15.0-pre`, plus `schema_version` values and β-proposal IDs). `agents/planner.md` alone carries ten. Worse than sprawl, the *current-value assertions themselves are forked*: `planner.md:4` asserts the "v0.8.0 Lifecycle-Phase Ladder" while `evaluator.md` and `generator.md` assert "v0.7.4" and `reflector.md` asserts "v0.15.0-pre PR-4c" `[AR-4]`. `version-check.py` validates five surfaces of the package-version plane only (manifest, README version entry, README badge, CHANGELOG top heading, marketplace self-reference, plus a prose version-trailer sweep) `[AR-10]`; the ladder, schema, and envelope planes are unguarded — exactly the surface the agents themselves must quote correctly at dispatch time.
2. **Untested judgment layer.** `scripts/fixtures/` covers structural and contract fixtures (frontmatter, convergence journal, output economy), but there is **no golden manuscript with seeded defects**. When a skill prompt is edited (as happened three times in the C-7/C-8 cycle), nothing measures whether detection recall regressed. The deterministic layer is regression-tested; the layer that does the actual reviewing is not.
3. **Quadratic commitment-interaction space.** Eight style commitments imply 28 pairwise interactions; six are declared in `STYLE_COMMITMENTS.md` prose (§3 table and §6 open fronts). The C-6↔C-8/M-1 collision was discovered by live-run failure, not design review. Each new commitment adds N−1 undeclared pairs silently.
4. **No CI.** The repo is git-backed with a live GitHub remote and `.github/CODEOWNERS` but no workflows. Structural checks run only when a maintainer remembers. CI checks pushed commits, not working trees `[AR-12]` — its value here is catching drift between sessions and partial commits that split parity-coupled files (see §8 hazard note).

A fifth, lower-grade concern: **context economy** — `references/` is ~2.3 MB (67% of content bytes) and 41 skill descriptions load into every session. Measured, not yet actioned (§7).

## 2. Design principles

- **Registry over prose, check over registry.** Every fact asserted in more than one file gets one machine-readable source of truth plus a check script — the pattern `plugin.json` + `version-check.py` already establishes. Prose cites; it does not assert.
- **Deterministic scoring of non-deterministic work.** The judgment layer cannot be unit-tested, but its *outputs* can be scored deterministically against a seeded-defect manifest — provided the findings format and matching rule are themselves specified `[AR-8]`.
- **Declare-or-fail for combinatorial spaces.** Where a space grows quadratically (commitment pairs), require an explicit entry — including explicit "no known tension" — for every element, so silence becomes a check failure rather than a latent collision.
- **Additive, reversible increments — with disclosed exceptions.** No agent-contract changes, no skill retirement without a reference sweep. One disclosed non-reversible action: moving `pdf_comments_dump.txt` to gitignored `scratch/` untracks it — a `git rm` in effect, accepted deliberately `[AR-3]`.
- **New checks join every enforcement surface at once.** A check added to CI but not to `release-gate.sh`, root `CLAUDE.md`, and `AGENTS.md` inverts the declared authority relationship between gate and alarm `[AR-7]`.

## 3. WS-1 — Hygiene and staleness — IMPLEMENTED

| Item | Evidence | Action |
|---|---|---|
| `RELEASE_v0.16.0_runbook.md` at repo root | Five minors stale; zero inbound references | Relocate to `docs/release-notes/` — **not** `releases/`, which is gitignored and excluded from release bundles; the file would have silently left version control `[AR-2]` |
| `extract_pdf_comments.py` at root | Tooling at governed root; zero inbound references | Relocate to `scripts/` |
| `pdf_comments_dump.txt` at root | Scratch output at governed root; zero inbound references | Relocate to `scratch/` (disclosed untracking, §2) `[AR-3]` |
| `agents/reflector.md` router "retained for one minor" (v0.15.0-pre) | Now several minors past | Re-scope: replace the open-ended promise with a dated header note stating the explicit retirement condition (host dispatch surface no longer names `reflector`). Recorded in the file itself, not in the version-planes registry — deprecation is a dispatch-lifecycle fact, not a version plane `[AR-13]`. Deletion deferred; the routing surface is still load-bearing. |
| *(Withdrawn)* README skills-count marker | catalog-check.py:74–88 treats any numeric README count as a drift hazard by design | No action. Recorded because the initial audit mis-read `<missing>` as a defect — the class of error external review exists to catch. |

## 4. WS-2 — Version-plane registry — IMPLEMENTED (snapshot mode)

**Reviewer-forced redesign `[AR-4, AR-5]`.** The original single-`current`-per-plane design would fire blockers on day one clearable only by editing agent frontmatter — the dispatch-surface contract this cycle does not touch. And the assertion phrasing across files is not stable enough to anchor a narrow regex with real coverage ("under the vX ladder", "on the vX ladder", "(vX Lifecycle-Phase Ladder)", "spec (vX)", composite forms). Therefore v1 of the registry runs in **snapshot mode**:

**Deliverables.** `references/schemas/version_planes.json` `[AR-6: placed in schemas/ per existing practice; MANIFEST.md row added]` — one entry per plane (`package`, `lifecycle_ladder`, `phase_state_schema`, `evaluator_envelope`, `stage_profile_vocabulary`), each recording the `authority` file and the **observed per-file assertions** (file, quoted assertion, value) as of this snapshot. Plus `scripts/version-planes-check.py`:

1. `package` plane must equal `.claude-plugin/plugin.json` (delegates prose surfaces to `version-check.py`; no duplication).
2. For every snapshotted assertion: the quoted string must still be present in the named file. Drift = a file changed its version assertion without updating the registry → blocker. This catches *silent* divergence while tolerating the *known, recorded* fork.
3. A file in `asserted_in` that disappears, or a known-forked plane whose fork *widens* (new distinct value appears in a registered file), is a blocker.

**Deferred to its own cycle (§9):** defining the canonical assertion syntax, harmonizing the agent files to it, and tightening the check from snapshot mode to current-value mode. That sweep edits agent descriptions and must ride with a dispatch-surface test, not a structural cycle.

## 5. WS-3 — Commitment-interaction registry — IMPLEMENTED

**Deliverables.** `references/schemas/commitment_interactions.json` `[AR-6]` — all 8 commitments and **all 28 pairs**, each classified `declared-tension` (with resolution rule + finding code), `protective-overlap`, or `no-known-tension` (explicit default; produces no blockers `[AR-9]`). Plus `scripts/commitment-interactions-check.py`:

1. Commitment IDs in the registry must exactly match the §1 table rows of `STYLE_COMMITMENTS.md`.
2. Pair coverage must be complete: C(n,2) entries. Adding C-9 without 8 new pair entries is a blocker.
3. Every `declared-tension` entry must name a resolution locus, verified as file-exists **plus anchor-string-present** — not §-resolution, which prose anchors cannot support mechanically `[AR-9a]`.

**Scope note `[AR-9b]`.** The registry *asserts pair classifications*; STYLE_COMMITMENTS.md prose remains authoritative for the *content* of each tension and its resolution. Demoting the §3/§6 prose lists to registry citations is deferred (§9) — it edits a core reference and deserves its own reviewed change.

## 6. WS-4 — Golden-manuscript judgment evals — SCAFFOLDED

**Deliverables.** `scripts/fixtures/golden/` starter suite (trailer-sweep-exempt placement verified `[AR-8]`):

- `golden_p2_theory.md` — a short P2 theory section seeding ≥6 defects: stipulated contested definition (M-1/C-8), strawmanned rival (M-2), payoff-pre-stating glossary entry (C-6↔C-8/M-1), unscoped load-bearing metaphor (C-6), >150-word monotone paragraph without turn-point (C-5/Check 8-A), construct used before first-use definition (C-5/Check 8-C).
- `golden_p1_brief.md` — a P1 control whose open definitions and unresolved positions the P2-gated checks (M-1, M-2, M-7) must **not** flag. Measures false-positive discipline — the harder half, per the C-8 live-runs.
- `manifest.json` — per-fixture defect inventory: `defect_id`, `location_hint`, `expected_finding_code`, `expected_severity`, `p_stage_gate`.
- **Findings-file schema + matching rule `[AR-8]`** (in `manifest.json` header block): a scored run is a JSON list of `{finding_code, severity, location_hint}`; matching is **code-family-first** (finding code must match the expected code's family, e.g. any `C-6↔C-8/M-1` variant), location used only as a tiebreaker when one code family has multiple seeded instances. Recall numbers are therefore a property of the declared matcher, not an artifact of an unstated one.
- `scripts/eval/golden_eval_score.py` — deterministic scorer over that schema: per-code recall, false positives on the P1 control, comparison to prior run.

**Protocol (recorded, not automated).** After any edit to a judgment skill or agent contract: run the relevant pass over both fixtures, transcribe findings into the schema, score. Recall drop or new P1 false positive = release blocker. Wiring into `release-gate.sh` waits for two baselines (§9) — a gate with no baseline is noise.

**Known limitation.** N=2 measures regression, not capability. The manifest + findings schema is the contribution; fixtures are cheap once it exists.

## 7. WS-5 — CI — IMPLEMENTED; context economy — DEFERRED (design recorded)

**CI.** `.github/workflows/structural-checks.yml`: on push/PR — Python 3.11, PyYAML, run the seven structural checks **plus the two new registry checks**, which are simultaneously wired into `release-gate.sh`, root `CLAUDE.md`, and `AGENTS.md` so gate and alarm enforce the same set `[AR-7]`. Local `release-gate.sh` remains the release authority; CI is the drift alarm for pushed commits.

**Context economy (deferred).** Hotspots: `references/` ≈ 2.3 MB (67% of content); 41 skill descriptions per session. Deferred because trimming 41 descriptions is a routing-risk change that needs the golden-eval suite in place first: trim, then verify routing didn't regress. Target: ≤ 500 chars where routing evidence permits; measure via the superkit economics probe before/after.

## 8. Sequencing and verification

WS-1 → WS-2 → WS-3 → WS-4 → WS-5 → full check re-run (nine checks) → CHANGELOG + bump to 0.22.0 (manifest is sole authority; README `## Version` entry, README badge, CHANGELOG top heading, and `marketplace.json` self-referencing entries follow — the complete five-surface set `version-check.py` enforces `[AR-10]`) → final verification, 0 blockers → flip §3–§7 status labels `[AR-1]`.

**Working-tree hazard `[AR-12]`.** The tree carries 8 pre-existing modified files plus 2 untracked (including an entire uncommitted skill, `skills/turabian-format-pass/`, whose catalog and registry rows live in two of the *modified* files). These are left untouched; but any future commit must include the turabian skill and its parity rows **atomically**, or catalog-check fails on CI's first run. Committing remains the maintainer's call.

## 9. Deferred register

- **Version-plane harmonization sweep** — canonical assertion syntax; agent-file sweep; snapshot→current-value check tightening (§4). Rides with a dispatch-surface test.
- **Context-economy trim** (§7) — after golden-eval baselines.
- **Golden-eval gate in release-gate.sh** — after two baselines.
- **STYLE_COMMITMENTS §3/§6 demotion to registry citations** (§5) — own reviewed change.
- **`agents/reflector.md` deletion** — condition recorded in its header note (§3).
- **Convergence-metric calibration** — thresholds never validated against human judgment; needs a labeled converged/not-converged section-pair set. Largest open scientific question in the harness.
- **release-gate.sh self-declared gaps `[AR-11]`** — retirement-sweep check (natural substrate: the version-planes pattern), **tier-table sweep audit**, and **description-length gate sourcing from README**; the latter two are further instances of registry-over-prose.
