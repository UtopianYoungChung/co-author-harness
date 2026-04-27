<!-- scholar-gateway-contract: v0.1 -->

# Release Notes — co-author-harness-claude v0.10.1

**Release date:** 2026-04-27
**Theme:** **Hardening patch** closing the two work items declared in v0.10.0's "Deferred to v0.10.1+" list — architecture- and strategy-doc mirrors for the four S4 binding decisions, plus the accessibility Sub-check H (Register Appropriateness) amendment — with one hot-fix for the v0.10.0 RC marketplace.json version-skew that was rejecting the `.plugin` loader install.
**Verdict:** CLEARED — 0 blockers, 0 warnings across all four validation scripts at RC gate.
**Status:** FINAL — five commits on `patch/v0.10.1` off `4a02b66` (v0.10.0 RC tip); annotated tag `v0.10.1`.

---

## 1. One-paragraph summary

v0.10.1 is a doc-only-plus-one-hot-fix hardening patch — no new skills, no schema changes, no phase-runner Step edits, §6.0 coupling-checklist EXEMPT throughout. Three layers landed in five commits. The hot-fix (commit `103faf4`) syncs `.claude-plugin/marketplace.json` to plugin.json (both at `0.10.0` mid-patch; both at `0.10.1` after RC) and extends `scripts/version-check.py` with a marketplace-self-referencing-version check that hard-gates future RCs on the same class of skew. The arch/strategy mirrors (commit `f614b34`) backport the four S4 binding decisions anchored at `agents/planner.md §Phase 3.8` into the architecture and strategy plan docs as cross-references, not duplications — the IDEMPOTENT_HIT outcome class missing from the architecture doc since S4 is now enumerated; the inline parallel-fanout cap of 8 is registered as Risk R-14; the cross-round coverage-regression hook is named at §5.2 Edit-2 closing prose with `agents/planner.md §Phase 3.8` as SOT; and the Phase 3.7-vs-3.8 halt-vs-continue asymmetry is anchored as the canonical example in §6.0 closing paragraph. The accessibility Sub-check H amendment (commits `0c408dc` + `2d5ea2e` + `edfe0a9`) operationalises the user's daily-language directive at three integration points: a passage-scoped variant covering the five non-technical passage roles (signpost orienting/contribution clauses, section framing, inter-section transitions, worked-example vignette bodies, consolidation anchor sentences); a manuscript-scoped variant under the new `register_class: technical | mixed | non-technical` field in `research_notes/directives.md`; and a presence-of-positive-markers compliance frame (concrete-referent anchoring, agent-verb-object default, plain-English connectives) inverted from the usual absence-of-negative-markers grammar to close the dilution back-door. H ships under `advisory_until: H_two_revision_cycles` with cycle-counting retirement via `h_advisory_cycles_observed` in `reviews/classification.md`. The plan doc's five Open Questions were adjudicated to the Default proposed answers per user direction 2026-04-27. The 32-skill invariant holds (H is overlay-internal per the plan doc's recommended path); SAFEGUARD Check 8's sub-check count expands from seven (A–G) to eight (A–H).

## 2. Work items

### 2.1 Hot-fix — marketplace.json version-skew (commit `103faf4`)

**Problem.** v0.10.0 RC shipped with `.claude-plugin/marketplace.json` line 13 declaring `"version": "0.9.0"` while `.claude-plugin/plugin.json` had been bumped to `"0.10.0"` at the RC gate. The `.plugin` ZIP install path carries both files; the loader saw two disagreeing version assertions for the same plugin and rejected the install (user-reported symptom: "the .plugin file fails validation").

**Root cause.** `scripts/version-check.py` validated manifest ↔ README ↔ CHANGELOG agreement during the v0.10.0 RC gate but did not read `marketplace.json` plugin-entry versions. The skew was not surfaced at the gate and shipped.

**Fix.**

- `.claude-plugin/marketplace.json` line 13 synced to `0.10.0` (at v0.10.1 RC: `0.10.1` everywhere in lockstep).
- `scripts/version-check.py` extended with `extract_marketplace_self_referencing_versions(plugin_root)` — reads `marketplace.json`, identifies `plugins[]` entries whose `source` field resolves to `plugin_root` (honouring both interpretations: relative-to-marketplace.json-directory and relative-to-plugin-root), and emits `BLOCKER` for any version disagreement with `plugin.json`. Absent `marketplace.json` is silent (not every plugin ships a co-located marketplace); present-but-no-self-referencing-entries is silent; mismatch hard-gates the gate.

**Verification.** Validator output at v0.10.1 RC: `Marketplace self-referencing entries: co-author-harness-claude=0.10.1; Blockers: 0`. The hot-fix prevents recurrence — any future RC where the four version surfaces (manifest, README, CHANGELOG, marketplace) drift apart will fail the gate before tagging.

### 2.2 Arch/strategy doc mirrors for the four S4 binding decisions (commit `f614b34`)

**Problem.** During v0.10.0 S4 implementation, four Planner-side binding decisions were anchored at `agents/planner.md §Phase 3.8` per the §6.0 row 4 single-source-of-truth principle (the agent file is canonical for partial-failure semantics; consumed SKILL.md and plan docs reference rather than restate). The architecture- and strategy-doc mirrors were deferred to RC-scope and then deferred again to v0.10.1.

**The four decisions (with terminology corrections from the v0.10.1 audit).** (a) Four-outcome handler for SK-NEW-B `claim-coverage-audit` dispatch (CLEAN / BELOW_THRESHOLD / AUDIT_FAILED / IDEMPOTENT_HIT) — the IDEMPOTENT_HIT outcome class is the load-bearing addition; its asymmetric notification treatment vs. AUDIT_FAILED is the rationale for four outcomes rather than three. (b) Inline parallel-fanout cap of 8 SK-NEW-C invocations per Ph2 cycle, sourced from `max_parallel_extend_snowball` in `reviews/classification.md` (default 8 per S4.5 R2 surfacing). (c) Cross-round coverage-regression hook consuming `last_coverage_score`, gated on `coverage_regression_floor` (default 0.05); consumer wiring lands at S4.5 R2; emits non-blocking `W-COVERAGE-REGRESSION-OBSERVED`. (d) Halt-vs-continue asymmetry between Phase 3.7 outcome (iii) HALT (SK-NEW-A substrate failure — REFERENCES.md is the substrate the Generator drafts against) and Phase 3.8 outcome (iii) CONTINUE (SK-NEW-B advisory failure — the audit signal informs but does not gate downstream reads).

**Audit findings vs. handoff.** The v0.10.1-open audit identified two terminology slips in the handoff doc's enumeration: decision (a) was rendered as "four-outcome handler for `extend-snowball-incremental`" when planner.md §Phase 3.8 anchors it on `claim-coverage-audit` (SK-34) — extend-snowball-incremental (SK-35) is the *consequence* of outcome (ii), not the subject of the four-outcome enumeration. Decision (d) was rendered as "halt-vs-continue asymmetry rationale for partial snowball failures" when the asymmetry is between Phase 3.7's SK-NEW-A snowball-population partial failure (HALT) and Phase 3.8's SK-NEW-B audit partial failure (CONTINUE) — calling both "snowball failures" elides the substrate-vs-advisory distinction the rationale rests on. Both corrections are baked into the v0.10.1 amendment prose.

**Architecture amendments** (`docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md`):

- §5.2 Edit-2 — replace "Two outcomes:" with the four-outcome class enumeration (CLEAN / BELOW_THRESHOLD / AUDIT_FAILED / IDEMPOTENT_HIT). Closing prose names the inline parallel-fanout cap and the cross-round regression hook as load-bearing details whose authoritative spec lives at planner.md §Phase 3.8.
- §6.0 closing paragraph — add v0.10.1-marked paragraph naming the Phase 3.7 (HALT — substrate failure) vs Phase 3.8 (CONTINUE — advisory failure) asymmetry as the canonical example of row-4 partial-failure halt-vs-continue semantics. Future contributors evaluating row 4 should ask: is this Step's output substrate (HALT) or advisory (CONTINUE)? The answer determines the row-4 polarity and the corresponding `phase_notifications.yaml` code class.
- §7 Risk Register — add R-14: outcome (ii) BELOW_THRESHOLD on a long-tail uncovered list could blow the verifier budget unboundedly (e.g., 30 uncovered × max_iter=2 × per_seed_cap=5 = 300 probes from a single Ph2 entry). Distinct from R-1 (per-iteration single-run cost) and R-12 (SK-16 red-link queue surface). Mitigation: inline parallel-fanout cap of 8 with Rule-7a-criticality ranking and `W-COVERAGE-FANOUT-CAPPED` for deferred claims.

**Strategy amendments** (`docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md`):

- §5.5 Stage S4 — added "Binding decisions" paragraph enumerating the four S4 surfaces. Each decision lists its architecture mirror point.
- §5.6 Stage S4.5 — added "S4 carry-overs (R2)" paragraph naming the two parameters (`max_parallel_extend_snowball`, `coverage_regression_floor`) that materialise S4 binding decisions (b) and (c), plus the regression-hook consumer wiring landing here.

**Discipline preserved.** All amendments are cross-references, not duplications. Future edits that touch any of the four decisions must edit `agents/planner.md §Phase 3.8` first (the SOT) and propagate to the mirrors second; the §6.0 closing paragraph carries the meta-rule for future contributors.

### 2.3 Sub-check H — Register Appropriateness (commits `0c408dc` + `2d5ea2e` + `edfe0a9`)

**Problem.** SAFEGUARD Check 8 measured seven dimensions of reader-accessibility surface quality (Sub-checks A–G) but **none governed register tone**. A paragraph could be A–G-CLEAN at the structural level (E-compliant, F-compliant, G-anchored) and still register-inappropriate for its passage role: a signposting paragraph in a manuscript's introduction could use no domain jargon and still read as cold, abstraction-stacked academic prose where the user's reader-accessibility intent calls for daily, agent-verb-object construction.

**Provenance.** User-initiated consultation with `advisor:advisor` (Opus 4.6) on 2026-04-27 surfaced the gap and proposed a structured amendment (1817 output tokens). The amendment was captured in `docs/superpowers/plans/2026-04-27-accessibility-subcheck-h-amendment.md` mid-S3, deliberately deferred from the v0.10.0 snowball rollout per the user's "do not bundle" directive, and adjudicated at v0.10.1 open with all five plan-doc Open Questions resolved to Default proposed answers.

**Sub-check H specification.** SAFEGUARD Check 8 expands from seven Sub-checks (A–G) to eight (A–H). Sub-check H operates at three integration points:

- **Passage scope (within-manuscript).** H runs over the five non-technical passage roles already named by the protocol: section signpost orienting/contribution clauses (D enforces structural presence; H enforces register construction); section framing/introduction prose; inter-section transitions; worked-example vignette bodies (F locates the spike, H audits the vignette); consolidation anchor sentences (G locates the boundary, H audits the anchor).
- **Manuscript scope (audience-conditioned).** A new field `register_class: technical | mixed | non-technical` is added to `research_notes/directives.md`. Default `technical` runs H on the five passage roles only. `mixed` extends scope to abstract / introduction / conclusion (the four-section list per the plan doc §10.3 Default proposed). `non-technical` runs H manuscript-wide, with technical paragraphs (those failing the functional removability test) retaining their domain terms but held to positive-marker construction at the sentence level. The field is **orthogonal to P-stage** (P-stage governs depth/scope of engagement; register_class governs target-audience register requirements).
- **Compliance frame.** Three positive markers (concrete-referent anchoring, agent-verb-object default, plain-English discourse connectives) and three negative markers (unnecessary nominalisation, stacked prepositional phrases, hedging pile-up) are tracked. The compliance frame is **presence of positive markers**, not absence of negative markers — a deliberate inversion that closes the dilution back-door and rewards register craft rather than punishing register lapses. A passage with one negative marker but two positive markers is CLEAN; a passage with zero positive markers and zero negative markers is MINOR.

**Functional removability test (passage-scope eligibility).** A passage is classified as non-technical and subject to H iff removing every domain-term token (italicised terms; terms in `references/terminology_register.md`; project-glossary entries — same scope as Sub-check C's "construct" definition per plan doc §10.1 Default proposed) and substituting plain-language glosses preserves the paragraph's propositional content. The test is **fuzzy by design** — the alternative is hard scoring (forbidden by the anti-dilution stance).

**Severity floors.** MINOR / MAJOR / BLOCKER mirroring A–G grammar; BLOCKER reserved for `register_class: non-technical` manuscript-wide variant when >50% of non-technical passages emit MAJOR. BLOCKER is gated by the `advisory_until: H_two_revision_cycles` flag — even on a `register_class: non-technical` manuscript, the BLOCKER does not gate the §3.3.3 TerminalSignoffRow until the advisory period clears.

**Advisory-until flag (cycle-counting).** H ships under `advisory_until: H_two_revision_cycles`, distinct from G's manuscript-scoped `advisory_until: next_manuscript_at_ph3` flag. Retirement state is recorded in `reviews/classification.md` as `h_advisory_cycles_observed: <integer>`, incremented at every Ph3 close where the overlay ran with H in scope. After two complete cycles, H findings join the aggregate identically to A–G.

**Per-finding telemetry.** Each H finding emits `false_positive_candidate: true|false` (default `false` at emission; user-settable during review per plan doc §10.4 Default proposed). The flag feeds a project-side calibration log (`reviews/h_calibration_<cycle_id>.md`, append-only) that informs the v0.10.2 retirement adjudication — provisional retirement criterion is false-positive rate <30% across two revision cycles.

**Back-compat grace period.** First H run on a previously-non-H manuscript records `inherited_from_pre_h: true` and runs MINOR-only regardless of detected severity for that one iteration (per plan doc §10.5 Default proposed). The grace gives the author a one-round signal of where H would otherwise fire MAJOR/BLOCKER without the punitive verdict.

**Stability sub-mode.** Under `run-phase-3-stability`, H runs **advisory-only** mirroring G's stability-sub-mode treatment. Findings are logged with `stability_advisory: true` and do not contribute to the aggregate.

**Recommended path adopted.** H ships **overlay-internal** per the plan doc's recommended path — no sibling skill, no `references/SKILL_REGISTRY.md` entry, no new skill folder. Skill count invariant 32 holds. The accessibility-overlay frontmatter version bumps from 1.2 → 1.3 and the description / trigger fields are extended to enumerate A–H.

**Files modified across the patch (12 total).**

| Layer | Files |
|---|---|
| Spec foundation | `skills/accessibility-overlay/references/sub_checks.md`, `references/READER_ACCESSIBILITY.md` |
| Skill body + protocol | `skills/accessibility-overlay/SKILL.md`, `references/SAFEGUARD_LAYER.md`, `references/PHASE_PROTOCOL.md` (§3.3.3 only) |
| Phase wiring | `skills/run-phase-3/SKILL.md`, `agents/evaluator.md` (§Step 8.5 only), `references/PROJECT_BOOTSTRAP.md` (§2.8 directives template only) |
| Arch/strategy mirrors | `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md`, `docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md` |
| RC ceremony | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md`, `CHANGELOG.md` |
| Hot-fix | `scripts/version-check.py` |

**Files NOT modified (intentional, with rationale).**

- `agents/planner.md` — plan doc §6 file-edit table named "planner.md §3.3.3" but §3.3.3 lives in PHASE_PROTOCOL.md (already amended). Planner.md cross-references PHASE_PROTOCOL §3.3.3 for the gate logic; no Planner-side aggregate-reading code needs separate H awareness because the Planner reads the overlay's pre-computed aggregate verdict directly.
- `references/SKILL_REGISTRY.md` — H is overlay-internal per the plan doc's recommended path. No SK-NN entry; no skill-count change.
- `references/DETERMINISTIC_CHECKS.md §9b` — optional H pre-filter (cheap counter probes for nominalisation, prepositional-phrase stacking, hedging) deferred per plan doc "not required for v1" guidance. Cheap to add; not required for the v0.10.1 binding contract.

## 3. RC gate evidence

**Validation gate (run with `PYTHONUTF8=1` via `py.exe` launcher in DC cmd.exe + `B:\Agents\run-validators.bat`).**

```
==== skill-check.py ====
SKILL INTEGRITY CHECK
- Plugin root: B:\Agents\co-author-harness
- Shipped skills discovered: 32
- Blockers: 0
- Warnings: 0
==== version-check.py ====
VERSION CONSISTENCY CHECK
- Plugin root: B:\Agents\co-author-harness
- Manifest version: 0.10.1
- README latest version: 0.10.1
- CHANGELOG top version: 0.10.1
- Marketplace self-referencing entries: co-author-harness-claude=0.10.1
- Blockers: 0
- Warnings: 0
==== catalog-check.py ====
CATALOG PARITY CHECK
- Plugin root: B:\Agents\co-author-harness
- Discovered skills: 32
- Discovered commands: 16
- README skills count: 32
- Blockers: 0
- Warnings: 0
==== path-hygiene-check.py ====
PATH HYGIENE CHECK
- Plugin root: B:\Agents\co-author-harness
- Blockers: 0
==== DONE ====
```

All four scripts pass with 0 blockers and 0 warnings. The newly-extended marketplace-version check now hard-gates RCs: any future v0.10.2 / v0.11.0 RC where manifest, README, CHANGELOG, or marketplace.json drift apart will fail the gate before tagging.

**Skill count invariant (32) holds** — Sub-check H is overlay-internal per the plan doc's recommended path; no new skill folder, no SKILL_REGISTRY entry.

**§6.0 coupling-checklist EXEMPT** — v0.10.1 is doc-only-plus-one-hot-fix; no phase-runner Step edits, no new dispatch edges, no Step number changes. Per the architecture doc's §6.0 closing-paragraph rule, doc-only stages do not trigger the four-row coupling-mutation requirement.

## 4. Commit ordering

Five commits on `patch/v0.10.1` off `4a02b66` (v0.10.0 RC tip):

| Commit | Subject | Layer |
|---|---|---|
| `103faf4` | v0.10.1 hot-fix: marketplace.json version skew + version-check.py guard | Hot-fix |
| `f614b34` | v0.10.1 docs: arch/strategy mirror points for 4 S4 binding decisions | Mirrors |
| `0c408dc` | v0.10.1: Sub-check H spec foundation — sub_checks.md + READER_ACCESSIBILITY.md | H spec |
| `2d5ea2e` | v0.10.1: Sub-check H — wire into overlay SKILL + SAFEGUARD + PHASE_PROTOCOL | H wire |
| `edfe0a9` | v0.10.1: Sub-check H — phase wiring (run-phase-3, evaluator, bootstrap) | H wire |
| (this) | v0.10.1 RC: version bumps + RELEASE_NOTES + CHANGELOG dated | RC gate |

Each commit passes the four-script gate independently; the cumulative state at RC tip is the verdict above.

## 5. Deferred to v0.10.2+

- **DETERMINISTIC_CHECKS §9b H pre-filter** — optional; cheap counter probes for nominalisation, prepositional-phrase stacking, hedging. Plan doc §6 file-edit table marks this as "optional pre-filter ... cheap to add but not required for v1." Defer to v0.10.2 hardening if observed false-positive patterns make a deterministic feed materially helpful.
- **Sub-check H `advisory_until` flag retirement** — scheduled for the first patch / minor release after `h_advisory_cycles_observed >= 2` is reached on at least one project. Provisional retirement criterion: false-positive rate <30% across two revision cycles, anchored at plan doc §10.4 Default proposed answer. The calibration log (`reviews/h_calibration_<cycle_id>.md`) is the empirical input for the binding decision.
- **Quantitative thresholds for H positive markers** — e.g., "≥1 concrete noun per 100 words"; "≥60% agent-subject sentences." Plan doc §10.2 Default proposed defers these to post-flag-retirement based on observed false-positive patterns. The advisory period is the calibration window.
- **Pilot integration replay** — clean-room replay on a fresh project (deferred from v0.10.0 RC per `RELEASE_NOTES_v0.10.0.md §4`). Still pending; not a v0.10.1 blocker.

## 6. Risk and back-compatibility

**Risk register additions.** Architecture §7 R-14 (added v0.10.1) — outcome (ii) BELOW_THRESHOLD on a long-tail uncovered list could blow the verifier budget; mitigation `max_parallel_extend_snowball` cap. The R-H1..R-H6 risks documented in the plan doc §7 are folded into the SAFEGUARD_LAYER §Sub-check H stability-sub-mode advisory, the `false_positive_candidate` per-finding telemetry, and the `advisory_until: H_two_revision_cycles` flag — no new risk register rows in the architecture doc are needed because H's risks are managed through the overlay's existing severity/aggregate machinery.

**Back-compatibility.**

- **`register_class` field default `technical`.** Existing `directives.md` files that do not declare the field inherit `register_class: technical` by silent absence. H still fires on the five non-technical passage roles common to all academic manuscripts. New projects' `PROJECT_BOOTSTRAP.md` template adds the field at v0.10.1.
- **First H run grace period.** Manuscripts whose `reviews/classification.md` lacks `h_advisory_cycles_observed` get a one-iteration MINOR-only grace. After that round, H runs at full severity (still under `advisory_until: H_two_revision_cycles`).
- **Skill count invariant 32 holds.** No new skills, no skill renames, no SKILL_REGISTRY changes. Existing projects mid-Ph3 inherit H on their next iteration with the back-compat grace period active.
- **`accessibility-overlay` frontmatter version bumps 1.2 → 1.3.** Source-tag references in the overlay's existing artefacts (`source_tag: accessibility-overlay@v1.1`) remain readable; new artefacts emit `@v1.3`. Reflector Phase 2g recurrence audits across the v1.1/v1.2 → v1.3 boundary preserve continuity via the `sub_check` field, not the source tag.

## 7. Provenance

- **Plan doc** (`docs/superpowers/plans/2026-04-27-accessibility-subcheck-h-amendment.md`) authored 2026-04-27 mid-S3, captured the user's clarified daily-language directive (dual scope: within-manuscript non-technical passages + audience-conditioned whole-manuscript register) and the advisor's structured 1817-token amendment proposal. Status: PROPOSAL → ADOPTED (implicit at v0.10.1 implementation).
- **User adjudication 2026-04-27.** All five plan-doc §10 Open Questions resolved to Default proposed answers per user direction.
- **Audit at v0.10.1 open.** Two terminology slips in the handoff doc's enumeration of the four S4 binding decisions identified and corrected at the source rather than propagated into the doc-mirror prose.
- **Tooling discipline.** Memory-captured constraints honoured throughout — GitKraken MCP for git ops; DC cmd.exe + .bat with `set PYTHONUTF8=1` on its own line for harness scripts; `py.exe` launcher with absolute paths; bash sandbox skipped for harness validation due to CIFS mount staleness.

---

**End of release notes.** Tag `v0.10.1` (annotated) pushed to https://github.com/UtopianYoungChung/co-author-harness.git.
