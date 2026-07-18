<!-- scholar-gateway-contract: v0.1 -->

# Release Notes — co-author-harness-claude v0.10.2

**Release date:** 2026-04-27
**Theme:** **Mixed substrate / forward-looking-spec sweep** closing the four items declared in v0.10.1's "Deferred to v0.10.2+" list — DETERMINISTIC_CHECKS §9e H pre-filter substrate (slot corrected from "§9b"); Sub-check H telemetry/aggregator + flag-retirement-decision plan doc; quantitative-thresholds plan doc; v0.10.0 pilot integration replay protocol plan doc — plus a substantial mid-cycle policy tightening (S1.5) per user directive 2026-04-27 to refine the H lay-term policy across five tighten-points.
**Verdict:** CLEARED — 0 blockers, 0 warnings across all four validation scripts at RC gate.
**Status:** FINAL — seven commits on `patch/v0.10.2` off `9861762` (v0.10.1 merge tip); annotated tag `v0.10.2`.

---

## 1. One-paragraph summary

v0.10.2 is a doc-and-script-heavy hardening + setup patch — no new skills, no schema changes, no phase-runner Step edits, §6.0 coupling-checklist EXEMPT throughout. Five layers landed in seven commits across `patch/v0.10.2`. The strategy doc (commit `da8a046`) captures the four-item scope and single-branch decision per user adjudication; the slot-correction commit (`f9dc2ee`) catches a v0.10.1 narrative artefact (§9b was already taken by the v0.7.2 Reader cognitive load pre-filter, so the H pre-filter slot is §9e). S1 (commit `d44cbc2`) ships the §9e substrate — three counter probes for nominalisation, prepositional-phrase stacking, and hedging density, with literature-anchored thresholds and a reference Python implementation at `scripts/check8_h_prefilter.py`. S1.5 (commit `92ead00`) tightens the H lay-term policy across five surfaces in response to a user directive: a closed-by-default load-bearing-Latinate whitelist (six entries with semantic-function rationale per entry); a three-class concrete-referent operational definition with explicit construct exclusion; a signpost orienting/contribution clause split with orienting-clause Ph2 binding; worked examples in §13.4 plus a new canonical lexicon file `references/lay_term_lexicons.md`; and a new fourth positive marker (register-shift signposting) capturing the user's directive *"Being consistent is also important. And, a proper signpost at every tone shift."* The compliance frame raised from at-least-two-of-three to at-least-two-of-four positive markers; overlay version 1.3 → 1.5. S2 (commit `87ead3d`) ships the H telemetry/aggregator pipeline (`scripts/aggregate_h_calibration.py`) and the retirement-decision plan doc that captures the criterion table the eventual binding adjudication will resolve against; SAFEGUARD §H step 7 added naming the aggregator as canonical empirical-input consumer. S3 + S4 (commit `a8a53ec`) land two forward-looking plan docs — quantitative thresholds candidate enumeration and the v0.10.0 pilot integration replay protocol. The pilot manuscript candidate slot is left as TBD per Q3 adjudication. Three deferred-to-v0.10.3+ items: per-project lexicon override implementation; per-marker FPR telemetry extension; cross-project FPR roll-up.

## 2. Work items

### 2.1 Strategy doc + slot correction (commits `da8a046`, `f9dc2ee`)

**Strategy doc.** `docs/superpowers/plans/2026-04-27-v0.10.2-implementation-strategy.md` captures the v0.10.2 four-item scope and single-branch layout. Two-tier deliverable taxonomy (substrate vs. forward-looking specification) is the load-bearing concept; per-item §6.0 coupling-checklist applicability enumerated upfront (all EXEMPT); risk register adds R-15 (pre-filter / overlay coupling), R-16 (pilot replay scope creep), R-17 (aggregator on inherited findings). Status: PROPOSAL → ADOPTED (implicit on substrate-commit landing).

**Slot correction.** v0.10.1 RELEASE_NOTES and the Sub-check H amendment plan doc both referenced "§9b" for the H pre-filter; §9b was already taken by the v0.7.2 Reader cognitive load pre-filter (feeds Check 8 Sub-checks A/D/E/F). The correction lands the H pre-filter at §9e — parallel structure to §9d (single sub-check feed; scoped tier).

### 2.2 S1 — DETERMINISTIC_CHECKS §9e H pre-filter substrate (commit `d44cbc2`)

**Three counter probes.** Per Q1 adjudication 2026-04-27 (adopt literature-anchored defaults):

- **Nominalisation density.** Suffix-pattern match (`-tion / -ment / -ance / -ence / -ity / -ness`) divided by passage word count; threshold 0.08 (above the 90th-percentile ~0.10 academic baseline reported in register-corpus studies); 20-term content-bearing exclusion list (`introduction`, `conclusion`, `methodology`, etc.) suppresses false positives on common copular nominals; `-ing` form intentionally excluded per pilot 30% FP-inflation observation on participial constructions.
- **Prepositional-phrase run length.** Longest consecutive PP chain in a single sentence over a 13-preposition cover set (`of`, `in`, `for`, `with`, `to`, `by`, `on`, `at`, `from`, `under`, `over`, `through`, `via`); fires when run length ≥3, anchored in Williams' *Style: Toward Clarity and Grace* §6 (two PPs is the comfortable upper bound; three or more imposes mental-stack demand).
- **Hedging density.** Hedge-marker hits per 100 words against built-in 15-marker default list (`may`, `might`, `could`, `perhaps`, `possibly`, `likely`, `suggests`, `indicates`, `appears`, `seems`, `somewhat`, `relatively`, `generally`, `typically`); fires when >2 per 100 words. Per-project override mechanism documented in §9e prose but not implemented at v0.10.2 per Q4 adjudication.

**Output contract per probe.** `(probe_name, raw_count, normalised_value, threshold, fired: bool)`. Per-passage bundle (three tuples) appended to overlay's input record under `prefilter_h_bundle`. H step 1 short-circuits to NULL/CLEAN when all three `fired` flags are false; if any probe fires, H runs the full classification and the bundle's raw signals enter per-finding rationale.

**Reference Python.** `scripts/check8_h_prefilter.py` (~210 lines) — CLI entry-point for development/testing; not invoked at runtime by the overlay (the overlay reads the bundle directly from `reviews/deterministic_<cycle_id>.md`).

**Files modified.**

- `references/DETERMINISTIC_CHECKS.md`: new §9e (45 lines including marker-class table, exclusion-list rationale, output contract, emission rule, output stub, rationale, orthogonality paragraph, advisory-until alignment, future-calibration deferred note).
- `skills/accessibility-overlay/SKILL.md`: frontmatter version 1.3 → 1.4; pattern_source extended with §9e + Williams + Biber-Conrad sources; entry-condition step 4 reads §9e bundle; Interaction-with-9b/9d/9e section updated; Normative status paragraph adds v0.10.2 entry; source_tag `accessibility-overlay@v1.3` → `@v1.4`.
- `skills/accessibility-overlay/references/sub_checks.md`: Pre-filter integration (§9e) paragraph + H step 1 procedure (with §9e short-circuit) paragraph added after Negative markers section.
- `scripts/check8_h_prefilter.py` (new).

### 2.3 S1.5 — H lay-term policy tightening (commit `92ead00`)

User-directed mid-cycle policy review 2026-04-27 surfaced five tighten-points where v0.10.1's H spec leaked toward over-aggressive lay-register pressure or relied on under-specified judgment calls. The Phase 2 vs. Phase 3 H-binding asymmetry was the load-bearing case (signposts had been held to a single lay-term standard regardless of clause type).

**Tightening A — Latinate exemption whitelist.** Six load-bearing-Latinate connectives permitted in non-technical passages with semantic-function rationale per entry: `whereby` (manner/mechanism — "by which" loses manner-specificity); `hence` (logical entailment — "so" is causally weaker); `notwithstanding` (acknowledged constraint — "even with" loses formal-acknowledgment register); `insofar as` (partial scope/qualification); `qua` (role-as-such); `mutatis mutandis` (analogous case with necessary changes). Whitelist closure rule defined (function specificity + economy + register-coherence three-part test). Edits `sub_checks.md` positive marker 3, `SAFEGUARD §H` step 3 marker (c), `READER_ACCESSIBILITY.md §13.3` criterion 8.

**Tightening B — Concrete-referent operational definition.** Three explicit referent classes: (i) physical/material entity; (ii) named individual or group; (iii) specific scenario or worked vignette. Defined constructs (Sub-check C terms; project-glossary entries; italicised tokens; i\* / GORE / AORE / HCI construct families) explicitly excluded from the count to close the dilution back-door on referentially-precise-but-abstract terms. Edits `sub_checks.md` positive marker 1, `SAFEGUARD §H` step 3 marker (a), `READER_ACCESSIBILITY.md §13.3` criterion 8.

**Tightening C — Signpost orienting/contribution clause split with Ph2/Ph3 binding.** Orienting clause (where-am-I; reader-orientation work) binding at Ph2 with BLOCKER-CANDIDATE on zero positive markers, full severity at Ph3; contribution clause (what-this-section-does; technical-content work) advisory at Ph2, binding at Ph3 with technical density permitted. Detection rule: backward-reference grammatical subject for orienting (`having`, `after`, `so far`, etc.); forward-reference subject + verb-of-action for contribution (`this section does`, `I now turn to`, etc.). Severity floor refined to weight orienting clauses alongside consolidation anchors and section transitions. Edits `sub_checks.md` scope paragraph, `READER_ACCESSIBILITY.md §13.5` Ph2/Ph3 binding paragraph, `SAFEGUARD §H` scope + severity floor.

**Tightening D1 — Worked examples in §13.4 anti-dilution paragraph.** Three operational examples: PASSES H (signpost orienting clause with four positive markers — concrete referents, agent-verb-object, plain-English connectives, register-shift signpost via colon); **FAILS H** (the user's option-1 case 2026-04-27 — methods-section label dropped into narrative prose; preferred fix *"This is not a speculative argument."* flowing into the contrastive move; alternatives 2 and 3 noted with rationale per option); EDGE CASE (referentially-precise-but-abstract i\* paragraph that fails marker 1 under construct exclusion; demonstrates why the construct-exclusion rule matters).

**Tightening D2 — New canonical lexicon file.** `references/lay_term_lexicons.md` (165 lines) consolidates hedge list (15 markers with class + rationale per entry; Hyland 2005 + Biber et al. 1999 source attribution), discourse-connective list (plain-English preferred + Latinate-flagged-outside-whitelist + load-bearing-Latinate whitelist), and domain-term-token exclusion list (content-bearing nominals + i\* / GORE / AORE / HCI construct families). Per-project override semantics documented; implementation deferred to v0.10.3 per Q4.

**Tightening F — Register-shift signposting (new fourth positive marker).** Captures user directive 2026-04-27: *"Being consistent is also important. And, a proper signpost at every tone shift."* Within-passage register shifts must be announced via signposting cue (`consider concretely:`, `in plain terms:`, `to put this technically:` etc.); cross-passage register consistency enforced implicitly (unannounced shifts between adjacent same-role passages flagged at the per-passage level). Compliance frame raised from at-least-two-of-three to at-least-two-of-four positive markers; rationale captured in `sub_checks.md` compliance-frame paragraph. Overlay version 1.4 → 1.5; source_tag `@v1.4` → `@v1.5`.

### 2.4 S2 — H telemetry/aggregator + retirement-decision plan doc (commit `87ead3d`)

**Substrate — `scripts/aggregate_h_calibration.py`** (~330 lines). Reads `reviews/h_calibration_<cycle_id>.md` per project; the calibration-log format is documented in the script's docstring (Markdown table with required columns `id` / `locator` / `severity` / `false_positive_candidate` / `inherited_from_pre_h` plus optional `reviewer_note`). Computes per-cycle FPR (`false_positive_count / eligible_findings`, where eligible excludes inherited-from-pre-h findings per the v0.10.1 grace rule — closes R-17 in strategy doc risk register). Computes cumulative-eligible aggregate FPR. Emits `reviews/h_calibration_aggregate.md` with per-cycle table + cumulative metrics + retirement-criterion comparison (default per Q1: cycles ≥2 AND aggregate_fpr <0.30) + parse diagnostics. Tolerant boolean parsing (true/yes/1 vs false/no/0); name-keyed column matching tolerates header reorder. Per Q2 adjudication, per-project only; cross-project deferred to v0.10.3.

**Forward-looking — `docs/superpowers/plans/2026-04-27-h-flag-retirement-decision.md`.** §1 problem statement (deferred from v0.10.1; empirically gated). §2 provisional retirement criterion (cycles ≥2 + aggregate_fpr <0.30 per Q1 default; combined verdict). §3 alternative criteria considered (5 options: stricter FPR <0.20; per-marker FPR; cycle count >2; reviewer-agreement criterion; combined criterion) with trade-offs and substrate-impact assessment per option. §4 adjudication template — the rows the user fills in once aggregator output materialises. §5 binding-decision-is-FUTURE. §6 governance note (SOT pattern preserved; cross-references resolve here rather than restate).

**Cross-reference.** SAFEGUARD `§H` procedure step 7 added naming the aggregator as canonical empirical-input consumer; documents FPR-computation rule + inherited-finding exclusion; cross-references the retirement-decision plan doc as SOT.

### 2.5 S3 — H quantitative-thresholds plan doc (part of commit `a8a53ec`)

**Forward-looking — `docs/superpowers/plans/2026-04-27-h-quantitative-thresholds.md`.** Captures candidate quantitative thresholds for the four H positive markers per Q1 adjudication (qualitative thresholds for advisory period; quantitative deferred to post-flag-retirement based on observed FPR patterns). §2 candidate enumerations per marker (concrete-referent: per-50/100/150-words with provisional ≥1-per-100 recommendation; agent-verb-object: 40/50/60% with provisional ≥60% recommendation; discourse-connective: 3/5 per page or ratio>0.5 with provisional ratio recommendation; register-shift signposting: strict/tolerant/hybrid with provisional hybrid recommendation). §3 FPR-vs-FNR trade-offs with 30% per-marker FPR cap as adjudication anchor. §4 three binding-preconditions: flag retirement closes; per-marker telemetry available; ≥3 projects observed. §5 adjudication template. §6 binding-decision-is-FUTURE.

### 2.6 S4 — v0.10.0 pilot integration replay protocol (part of commit `a8a53ec`)

**Forward-looking — `docs/superpowers/plans/2026-04-27-v0.10.0-pilot-replay-protocol.md`.** §1 problem statement (integration validation, not unit testing; first full H advisory cycle on real project feeds aggregator). §2 pilot manuscript candidate slot left as TBD per Q3 adjudication (named at replay-session open). §3 clean-room workspace setup (`B:\Agents\<pilot-project>`; install via `/plugin marketplace add` now WORKING after v0.10.1 source-format fix). §4 protocol — Ph1 (SK-33 + SK-36 if wiki-linked); Ph2 (SK-34 + SK-35 with four-outcome handler + parallel cap); Ph3 (run-phase-3 + accessibility-overlay with v0.10.2 H tightenings active). §5 metric set (skill-trigger cost; coverage score deltas; H sub-check firing rates per passage role; §9e probe firing distribution; gate-blocker counts; H FPR estimate). §6 exit criteria. §7 known-deferred (SK-32 `run-generator-session`; `run-phase-3-stability`; Phase 4 reflector pass; cross-project pre-seed at scale). §8 binding-decision-is-FUTURE; §9 governance note.

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
- Manifest version: 0.10.2
- README latest version: 0.10.2
- CHANGELOG top version: 0.10.2
- Marketplace self-referencing entries: co-author-harness-claude=0.10.2
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

All four scripts pass with 0 blockers and 0 warnings.

**Skill count invariant 32 holds** — v0.10.2 added no new skill folders; the two new scripts (`check8_h_prefilter.py`, `aggregate_h_calibration.py`) are reference implementations / aggregator tools, not skills. `commands/` count remains 16. `phase_state.json` schema unchanged (no new fields).

**§6.0 coupling-checklist EXEMPT** throughout — no phase-runner Step edits; no new dispatch edges; no Step number changes. Per the architecture doc's §6.0 closing-paragraph rule, doc-and-script-only stages do not trigger the four-row coupling-mutation requirement.

**Marketplace.json source-format check** (added v0.10.1) and version-skew check both pass — `"source": "./"` preserved; all four version surfaces (manifest, README, CHANGELOG, marketplace) at `0.10.2` in lockstep.

## 4. Commit ordering

Seven commits on `patch/v0.10.2` off `9861762` (v0.10.1 merge tip):

| Commit | Subject | Layer |
|---|---|---|
| `da8a046` | docs(v0.10.2): implementation strategy doc | Strategy |
| `f9dc2ee` | docs(v0.10.2-strategy): correct H pre-filter slot reference — 9b → 9e | Slot fix |
| `d44cbc2` | feat(v0.10.2-S1): add DETERMINISTIC_CHECKS §9e — H pre-filter substrate | S1 substrate |
| `92ead00` | feat(v0.10.2-S1.5): tighten H lay-term policy — A/B/C/D/F refinements + lay_term_lexicons.md | S1.5 tightening |
| `87ead3d` | feat(v0.10.2-S2): H telemetry/aggregator setup + retirement-decision plan doc | S2 |
| `a8a53ec` | feat(v0.10.2-S3+S4): forward-looking plan docs — H quantitative thresholds + v0.10.0 pilot replay protocol | S3 + S4 |
| (this) | RC gate: v0.10.2 version bumps + RELEASE_NOTES + CHANGELOG dated | RC gate |

Each commit passes the four-script gate independently; the cumulative state at RC tip is the verdict above.

## 5. Deferred to v0.10.3+

- **Per-project lexicon override implementation.** v0.10.2 ships `references/lay_term_lexicons.md` as canonical lexicon source with per-project override semantics documented but not implemented per Q4 adjudication. v0.10.3 implements the override mechanism (project files at `research_notes/hedge_terms.md`, `research_notes/connective_terms.md`, `research_notes/latinate_whitelist.md` replace or supplement built-in defaults).
- **Per-marker FPR telemetry extension.** Current per-finding telemetry tracks `false_positive_candidate` overall, not per-marker. v0.10.3 extends the calibration-log format to track which marker(s) fired the finding; precondition for adopting quantitative thresholds beyond qualitative judgment per the quantitative-thresholds plan doc §4.
- **Cross-project FPR roll-up in `aggregate_h_calibration.py`.** v0.10.2 ships per-project only per Q2 adjudication. v0.10.3 adds an opt-in `--cross-project` flag that scans a workspace root for sibling projects' calibration logs and emits a workspace-level aggregate.
- **Pilot integration replay execution.** v0.10.2 ships the protocol; the run is a separate session triggered when a pilot manuscript candidate is named. The replay itself yields the first H advisory cycle data on a real project, which feeds the v0.10.2 aggregator for the eventual flag-retirement adjudication.
- **Sub-check H `advisory_until: H_two_revision_cycles` flag retirement adjudication.** Gated on `aggregate.md` showing both criteria met (cycles ≥2 + aggregate_fpr <0.30) on at least one project. The retirement-decision plan doc's §4 template is the adjudication surface; binding decision lands in whichever patch first applies the template.
- **Quantitative thresholds adoption.** Gated on flag retirement closing + per-marker telemetry available + ≥3 projects observed. The quantitative-thresholds plan doc captures the candidate enumerations; binding decision lands in whichever patch first applies the §5 template.

## 6. Risk and back-compatibility

**Risk register additions (from strategy doc §7).**

- **R-15 — Pre-filter / overlay coupling.** §9e ships counter probes consumed by the overlay's Sub-check H step 1. If a future overlay revision (post-v0.10.2) changes H's negative markers, §9e's three probes must move in lockstep. Mitigation: SAFEGUARD §H step 3 marker (d) names §9e explicitly; the §6.0 coupling-checklist row 4 (substrate-vs-advisory asymmetry) covers this if a future stage edits the overlay's Sub-check H sub-procedure.
- **R-16 — Pilot replay scope creep.** The pilot replay protocol (§4.4) names a metric set and exit criteria, but the actual run is a separate session. Risk: the replay session could expand beyond v0.10.0 snowball validation. Mitigation: protocol §7 explicitly enumerates known-deferred surfaces.
- **R-17 — Aggregator on inherited findings.** `aggregate_h_calibration.py` skips findings flagged `inherited_from_pre_h: true` per v0.10.1 grace-period spec. Mitigation: aggregator's `eligible_findings` property is the canonical denominator; `total_findings - inherited_findings` arithmetic is documented in the script's docstring.

**Back-compatibility.**

- **Sub-check H positive-marker count change (3 → 4).** Existing manuscripts mid-Ph3 inherit the four-marker compliance frame on their next iteration. Manuscripts whose `reviews/classification.md` lacks `h_advisory_cycles_observed` get the v0.10.1 back-compat grace period (first H run records `inherited_from_pre_h: true` and runs MINOR-only); the v0.10.2 marker-4 addition does not change the grace mechanism. Manuscripts that previously cleared H under the three-marker frame may surface marker-4 findings on next run; this is expected and the advisory-period framing covers it.
- **Overlay frontmatter version bumps 1.3 → 1.5.** Source-tag references in the overlay's existing artefacts (`source_tag: accessibility-overlay@v1.1` from v0.8.1, `@v1.3` from v0.10.1, `@v1.4` from v0.10.2 S1) remain readable; new artefacts emit `@v1.5`. Reflector Phase 2g recurrence audits across the version boundary preserve continuity via the `sub_check` field, not the source tag.
- **Skill count invariant 32 holds.** No new skills, no skill renames, no SKILL_REGISTRY changes. The two new scripts are reference implementations / aggregator tools.
- **Calibration-log format canonicalised.** v0.10.2 documents the `reviews/h_calibration_<cycle_id>.md` format in the aggregator script's docstring. The format is stable for v0.10.2 and v0.10.3+ extensions are additive (e.g., the per-marker telemetry extension adds columns; existing logs remain parseable).

## 7. Provenance

- **Strategy doc** (`docs/superpowers/plans/2026-04-27-v0.10.2-implementation-strategy.md`) authored 2026-04-27 with all 9 sections (problem statement; two-tier deliverable taxonomy; methodology; per-item deliverables; stage layout; RC gate criteria; risk register R-15/R-16/R-17; Open Questions Q1–Q4; governance note). Status: PROPOSAL → ADOPTED (implicit at v0.10.2 substrate-commit landing).
- **User adjudication 2026-04-27 of strategy doc Open Questions.** All four (Q1 §9e thresholds; Q2 aggregator output format; Q3 pilot manuscript candidate; Q4 hedge override) resolved to Recommended defaults.
- **User adjudication 2026-04-27 of S1.5 tightenings.** All four tighten-points (A Latinate whitelist; B concrete-referent operationalisation; C signpost orienting/contribution split; D worked examples + lexicon file) selected, plus a sixth axis the user contributed in their note: register consistency / tone-shift signposting (operationalised at v0.10.2 as the new fourth positive marker).
- **User-supplied worked example.** The §13.4 FAILS H example anchors on the user's option-1 case ("methods-section label dropped into narrative prose"; preferred fix *"This is not a speculative argument."*) per their adjudication note 2026-04-27. The user's two-principle distillation ("Being consistent is also important. And, a proper signpost at every tone shift.") became the rationale for marker 4.
- **Audit at v0.10.2 open.** The §9b → §9e slot correction (commit `f9dc2ee`) caught a v0.10.1 narrative artefact pre-substrate landing.
- **Tooling discipline.** Memory-captured constraints honoured throughout — GitKraken MCP for git status/branch/checkout; DC cmd.exe + .bat for commits and version-bump sequences; `py.exe` launcher with absolute paths for harness scripts; `PYTHONUTF8=1` set in every .bat that runs Python validators.

---

**End of release notes.** Tag `v0.10.2` (annotated) pushed to https://github.com/UtopianYoungChung/co-author-harness.git.
