---
title: Forensic re-read of v0.11.0 architectural-cut session
status: FINDINGS — not blocking; for the resuming session's adjudication
date: 2026-04-27
author: Reviewer (forensic pass)
predecessor: .claude/handoffs/2026-04-27-210758-v0110-architectural-cut-execution.md
predecessor_audit: reviews/promise_delivery_review_2026-04-27.md
governing_plan: docs/superpowers/plans/2026-04-27-v0.11.0-definitive-architectural-plan.md
scope: independent forensic re-read of the five-commit landing zone on release/v0.11.0 against the plan, the audit, and the working-tree state at session close
---

# Forensic re-read of the v0.11.0 architectural-cut session

## 0. Premise and posture

The session-completion recap framed the landing zone as clean: five commits landed, audit's high-severity finding closed, all four maintainer scripts green, handoff scored 94/100 READY. This forensic pass treats that framing as a hypothesis, not a conclusion. The pass reads the commits, the working tree, the plan, the audit, and the validator outputs against each other, rather than against the recap's self-report. The pass is non-blocking — none of the findings imply the v0.11.0 work should not continue — but several material drifts surfaced that the next session must adjudicate before c1.

## 1. Verified-clean against the recap

Five items in the recap were independently confirmed:

The five landed commits (`3c458d0`, `99ab329`, `2016f85`, `28eca1c`, `326653e`) are present on `release/v0.11.0`, in chronological order, with conventional-commit subjects scoped under `v0.11.0-cN`. Each carries a body that names the plan section it closes, the files touched, and the validator-state assertion at commit time. Authorship is uniformly `Joseph Chung <young.jo.chung@gmail.com>`; no AI-attribution trailers, consistent with the project's authorship convention. The five bodies are exemplary in scope discipline; if the project later adds a commit-message linter, the existing five will pass it.

The deferral of c1 to a fresh session is justified by the recap and consistent with the plan's stated migration order. c1's surface is large (≈400–600 lines, ≈10 files; the SD/SR footprint grep returns 197 occurrences across 47 files, of which roughly 60 are exempt history surfaces), and the cognitive switching cost between the c1 surgery and the trailer-strip mechanics of c7 would have been high. The deferral choice is sound.

The c0 → c2 → c3 → c6 → c7 ordering deviates from the plan's listed sequence (which begins at c1) but the deviation is documented in the handoff and well-justified: the lighter mechanical commits land first to compress the surface that c1 must traverse. No commit landed out of order relative to its dependencies.

The four maintainer scripts return zero blockers, zero warnings — confirmed by re-running them at the working-tree HEAD with `PYTHONUTF8=1` and the absolute Python launcher path. (Note this confirmation is **conditional** on the working-tree state, which §2 below shows is materially different from the committed state.)

The c7 trailer-strip commit appears thorough. The version-trailer pattern grep returns 99 occurrences across 33 files, but the plan explicitly preserves inline `(vX.Y.Z)` and `(vX.Y, P-N)` citations as semantically load-bearing; the residual hits are dominated by these preserved inline citations rather than by missed trailers. A precise audit would require running c8's planned `check_no_version_trailers_in_prose` regex (`\*Last updated:`, `harness substrate at \*\*v\d+\.\d+\.\d+\*\*`, `(vX.Y.Z addendum)`) which is tighter than my grep — that script does not yet exist.

## 2. Latent issues — graded by severity

### 2.1 HIGH — working-tree regression on the README c3 commitment

The working tree carries an uncommitted edit to `README.md` line 32 that reverts the c3 plan-mandated change: `### Skill catalog` is rolled back to `### Skills (32)`. The c3 commit body asserts: *"Renamed `### Skills (32)` heading to `### Skill catalog`."* The plan §3.1 binds: *"the count is derived, not asserted."* The working tree re-asserts the count.

This is regression of a landed plan commitment. It will be re-introduced into the next commit unless the resuming session notices and reverts the working-tree edit.

The regression silently passes `catalog-check.py`. I ran the validator at HEAD and it reports:

```
- README skills count: 32
- Blockers: 0
- Warnings: 0
```

The recap and the c3 commit body both promised that `catalog-check` would report `README skills count: <missing>` — that is now false. The validator does not BLOCKER on an asserted count; it merely reports it. This is exactly the validator gap the plan's c8 was scoped to close (`check_README_skill_count_is_derived_not_asserted`), and the regression-in-flight confirms the gap's load-bearing nature. Until c8 ships, README assertions are not enforced.

**Adjudication for resuming session.** Either revert the working-tree README change before c1, or fold it into a c2.5 / c3.1 patch commit with an explicit rationale (which would itself contradict the plan; the plan has no provision for a re-asserted count). The default disposition is *revert*.

### 2.2 HIGH — manifest description SSOT violation: "Ships 32 skills"

Both `.claude-plugin/plugin.json.description` and `.claude-plugin/marketplace.json.plugins[0].description` end with the clause *"Ships 32 skills: snowball references, accessibility audit, named-scholar style overlays."* The literal `32` is asserted twice. The plan §3.1 retires asserted counts in the README; the plan §3.4 SSOT registry names `skill_count`'s authority as `ls skills/ | wc -l` with consumers including `README.md` and `skills/plugin-commands/SKILL.md` — but **does not list** the two manifest descriptions as consumers.

This is a structural inconsistency *within the plan itself*. §2.2 authored the manifest descriptions with `Ships 32 skills` baked in (the verbatim drafted text appears at plan line 54). §3.4 then forgot to register the manifest descriptions as skill-count consumers. The c8 `manifest-coherence-check.py` is scoped to enforce description ≤ 300 chars and keyword-substrate parity, not skill-count parity inside the description prose.

The consequence: when the skill count moves (32 → 33), README will be silently consistent (catalog-derived, post-c8) and the manifests will silently drift. The drift class the plan exists to retire is reproduced inside the plan's own enforcement architecture.

**Adjudication for resuming session.** Two options. (a) Add `plugin.json.description` and `marketplace.json.plugins[0].description` to the §3.4 SSOT registry under `skill_count.consumers`, and extend `manifest-coherence-check.py` (or `ssot-check.py` at c9) to grep the description for `\b\d+ skills?\b` and assert the count matches the catalog. (b) Rewrite the descriptions to drop the count entirely (`Ships skills for snowball references, accessibility audit, named-scholar style overlays.`) and treat the count as marketplace-irrelevant. The plan's posture (Principle 4 — deletion preferred over documentation) favors (b); the structural-enforcement posture (Principle 5) favors (a). The two are not exclusive; the cleanest answer combines them: drop the count from the descriptions *and* add the descriptions to the SSOT registry as a defensive layer.

### 2.3 MEDIUM — handoff document is internally inconsistent on push state

Handoff line 9 asserts: *"`release/v0.11.0` has not been pushed."* The remote is in fact populated: `git ls-remote --heads origin release/v0.11.0` returns `326653e0eb4880367338475a4c2446093406a2ac`, identical to local HEAD. `git for-each-ref` reports the upstream as `origin/release/v0.11.0` and the branch is up-to-date with it. The push happened either before or after the handoff was written; the handoff's claim is false at the moment of forensic re-read.

The class of finding matters: the handoff is the artefact the resuming session reads first. If a single asserted fact in the handoff is false, the resuming session has reduced reason to trust the handoff's other asserted facts. The handoff scored 94/100 in the validation pass, but the validator does not check assertions against the repository state — and could not, without doing the work this forensic pass is doing.

**Adjudication for resuming session.** Patch the handoff line 9 to read *"`release/v0.11.0` is pushed to origin at `326653e`"* before resuming. This is a documentation correction, not a code change.

### 2.4 MEDIUM — manifest description unification not acknowledged in handoff

The working-tree diff shows `plugin.json.description` being edited to mirror the marketplace.json sharpened form, character-for-character. The two descriptions are now identical. The handoff (line 31) directs: *"Plugin.json description is the slightly longer 'climb a four-phase ladder' form; do not unify them in c12 unless the user requests it."*

Either the user authorized the unification post-handoff (likely — the recap acknowledges only the marketplace.json edit, but the same person could have unified plugin.json in the same editing pass and the recap simply didn't notice the second file), or the unification was an unintended side-effect of the marketplace.json edit (less likely; the descriptions are character-identical, which suggests deliberate copy-paste).

The handoff's guidance is now either stale (if intentional) or actively wrong (if unintentional). The resuming session needs to know which.

**Adjudication for resuming session.** Confirm with the user whether the unification is intentional. If yes, patch handoff line 31 to read *"Plugin.json and marketplace.json descriptions are unified to the user-sharpened form (working tree, uncommitted as of session close); fold into a c2.5 patch commit before c1, or as a leading hunk of c12."* If no, revert plugin.json to the c2-landed form before c1.

### 2.5 LOW — untracked artefacts will leak into commits if anyone runs `git add -A`

`releases/.write_test`, `releases/newtest.txt`, `releases/ziyJnSzo` are untracked test artefacts (likely from a bash write-access probe). `tmp/diff_sample.txt`, `tmp/diff_stat.txt`, `tmp/get_diff.bat` are session-scratch files. `.gitignore` ignores `releases/*.zip` and the named artefact-output trees, but does **not** ignore `releases/*` (non-zip) or `tmp/` as a whole. A future `git add -A`, `git add releases/`, or `git add tmp/` would commit the noise.

The class of finding: latent foot-gun, not active drift. Path-hygiene-check.py does not detect untracked-files-in-tracked-or-loose directories.

**Adjudication for resuming session.** Either delete the seven untracked files (preferred — they are scratch, not artefacts), or extend `.gitignore` with `releases/*` (and re-allow `releases/*.plugin` if the build convention is to land releases there, though `*.plugin` is already ignored globally) and `tmp/`. Default disposition is *delete*.

### 2.6 LOW — c0 commit not enumerated in the plan's "13 commits" target

The plan's Step 2 begins at "Commit 1" (SD/SR deletion). c0 — landing the audit + plan as in-tree governing documents — is not listed in §4. The actual chain on `release/v0.11.0` is now c0 + c1..c13 = 14 commits, but the plan promises ≈13. This is accounting drift, not substantive drift. CHANGELOG and RELEASE_NOTES at c12 should reference the actual chain length.

## 3. Plan-vs-implementation skew summary

| Class | Direction | Severity |
|---|---|---|
| §3.1 README count derived | Working tree → re-asserted | HIGH (§2.1) |
| §3.4 SSOT registry vs §2.2 description authoring | Plan internal | HIGH (§2.2) |
| Handoff push state | Handoff → repo | MEDIUM (§2.3) |
| Handoff unification guidance vs working tree | Handoff → repo | MEDIUM (§2.4) |
| Plan commit-count target vs actual chain | Plan → repo | LOW (§2.6) |
| Plan ordering vs actual ordering | (none — documented; deferral justified) | clean |

The skew pattern: the plan is internally rigorous, the commits are internally rigorous, but the *interface* between session-end and session-resume — the handoff document and the working-tree state — is where the drift accumulates. This is unsurprising; that interface has no validator gate, only narrative discipline.

## 4. Validator gaps surfaced by this pass

The four current scripts plus the seven planned extensions (c8: four scripts gain rules + manifest-coherence-check; c9: ssot-check.py; c10: end-to-end smoketest) cover most of the substrate's drift surface. This forensic pass surfaced four gaps not yet covered by the plan:

**Gap 1 — Asserted counts in manifest descriptions.** The c8 `manifest-coherence-check.py` enforces description length and keyword-substrate parity but not asserted counts inside description prose. Candidate rule: grep `description` for `\b\d+\s+(skills?|commands?|agents?|phases?)\b` and BLOCKER on match unless the digit equals the SSOT count for that surface. Adds ≈5 lines to manifest-coherence-check.py.

**Gap 2 — Description parity between plugin.json and marketplace.json.** Neither c8 nor c9 explicitly checks that plugin.json.description and marketplace.json.plugins[0].description agree (or are intentionally different per a flag). Candidate rule: ssot-check.py asserts equality unless an explicit `descriptions_diverge: true` flag is set in `ssot.yaml`. Adds ≈10 lines to ssot-check.py and a one-line entry to ssot.yaml.

**Gap 3 — Untracked-files-in-tracked-directories drift.** `path-hygiene-check.py` checks for orphan directory references in README (post-c8) but does not check for untracked artefacts inside a tracked directory that would be picked up by `git add -A`. Candidate rule: shell out to `git ls-files --others --exclude-standard` and BLOCKER on any path under a tracked directory whose extension is not in an explicit allowlist (e.g., `*.plugin`, `*.zip` are allowed in `releases/` but only if matched by a corresponding manifest version). Adds ≈15 lines to path-hygiene-check.py.

**Gap 4 — Handoff-vs-repo coherence.** No validator checks the handoff's asserted facts against the repository state. Candidate rule: a new `handoff-check.py` or extension to `session-handoff` skill that, on handoff write, runs a self-test against a small set of repo invariants (branch push state, working-tree clean state, named commit SHAs exist, named files exist) and refuses to write the handoff if any invariant fails. The §2.3 finding would have been caught by such a validator. Adds ≈80 lines and a new script. This is heavier than the other three; it could be deferred to v0.11.x or v0.12.0.

## 5. Recommendations for the resuming session

The resuming session should execute these adjudications, in order, before beginning c1:

1. **Patch the handoff** — line 9 (push state) and line 31 (unification guidance). If the user confirms the unification is intentional, also note it in the handoff's Decisions Made table. (No code; one Edit per line.)

2. **Adjudicate the working-tree README regression** — default disposition is revert. If revert, run `git checkout README.md` and re-run the four maintainer scripts to confirm `catalog-check` reports `<missing>` again. If not revert, fold into a c2.5 patch commit with explicit rationale and a TODO to update the plan §3.1.

3. **Adjudicate the manifest description state** — confirm with the user whether the unification is intentional. If yes, fold the unified description (and the c2.5 README disposition) into a single c2.5 commit before c1, or as the leading hunk of c12. If no, revert plugin.json to the c2-landed form. Either way, add a §2.2 finding to the plan acknowledging the SSOT-vs-§2.2 internal inconsistency, and decide whether to drop `Ships 32 skills` from both descriptions (Principle-4 disposition) or to register the descriptions as `skill_count` consumers in §3.4 (Principle-5 disposition). The combined disposition (drop *and* register) is cheapest and most defensible.

4. **Clean the untracked artefacts** — `del /Q releases\.write_test releases\newtest.txt releases\ziyJnSzo` and remove `tmp/` (or its contents). Optionally extend `.gitignore` with `tmp/` and `releases/*` (whitelisting `*.plugin` and `*.zip`).

5. **Re-run the four maintainer scripts** after each of the above to preserve the invariant.

6. **Add the four validator gaps** (§4) to the plan's c8/c9 scope, with explicit rules. The first three are small additions to existing scripts; the fourth is a deferral candidate.

7. **Begin c1** as scheduled, with the SD/SR machinery deletion targeting the 197-occurrence footprint (≈137 after subtracting CHANGELOG, RELEASE_NOTES, plan, and predecessor-audit history). The plan's specification is precise; the surgery itself is mechanical once the pre-c1 working-tree dirt is resolved.

## 6. Closing posture

The recap's "clean" framing was overstated, but only at the seams — the handoff/working-tree interface, not the substrate. None of the §2 findings are catastrophic; all are recoverable in under one focused hour before c1. The plan itself is rigorous and the commit chain is sound; the gaps that surfaced are gaps the plan would have closed at c8/c9 if those commits had landed before this session ended. The forensic pass therefore does not invalidate the recap's claim of progress, but it does replace the recap's "READY to resume" framing with "READY to resume *after* the §5 punch list is cleared."

The deeper observation — and this is the meta-finding the plan implicitly predicts — is that the only validator that could have caught these drifts before the handoff was written is the one the plan has not yet built. Section 3.5 of the plan promises *"the substrate's worry-of-being-out-of-date is itself the substrate's job to make impossible."* This forensic pass is evidence that, until c8/c9 land, the substrate cannot yet keep that promise, and the maintainer (or a successor session) must do the work the validators will eventually do automatically. That is a known cost the plan accepts; the forensic pass merely names it.

---

*Forensic author: Reviewer (forensic pass), 2026-04-27. Method: independent re-read of plan, audit, handoff, commit bodies, working-tree diff, validator outputs, and repo grep state. All asserted facts in this document were verified against direct evidence; line numbers and commit SHAs are quoted from primary sources.*
