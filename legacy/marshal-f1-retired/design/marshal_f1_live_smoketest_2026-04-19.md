---
doc_type: field-report
date: 2026-04-19
plugin_version: 0.5.5
phase: F.1 (advisory rollout)
scope: Tier Marshal live-project smoketest — pre-F.2 calibration
projects_tested: [INF3006Y_AgencyDelegation, milestone4_Darlington]
marshal_schema_version: 1
---

# Marshal F.1 Live-Project Smoketest — 2026-04-19

## 1. Intent

Capture the live-project verdicts of the new Tier Marshal under v0.5.5's Phase F.1 advisory rollout, so that the set of findings flipping BLOCK→WARN is known *before* v0.5.6 activates Phase F.2 (BLOCK-active). Both projects were mounted by the user after v0.5.5 shipped; neither was authored with the new tier: field or the v0.5.5 Marshal contract in mind, so each is an ecologically valid probe of how the advisory layer behaves on legacy material.

## 2. Method

Two identical invocations, one per project:

```
python3 scripts/marshal_preflight.py \
  --project-root <live-project> \
  --tier T3 --round 1 --date 2026-04-19 \
  --plugin-root . --advisory-only
```

The migration helper was dry-run first on each project:

```
python3 scripts/migrate_classification_to_tier.py \
  --project-root <live-project> --dry-run
```

All artefacts (`marshal_preflight_01_2026-04-19.md` + `.json` sidecar) are written under each project's `reviews/`.

## 3. Findings

### 3.1 INF3006Y_AgencyDelegation

| Check | Severity | Notes |
|---|---|---|
| P-1 classification.md exists | PASS | File is present. |
| P-2 tier: field in frontmatter | **WARN (→ F.2 BLOCK)** | classification.md uses a markdown-table format (`\| **Review depth** \| standard \|`) with no YAML frontmatter. The frontmatter parser finds no keys. |
| P-3 tier: matches requested tier | WARN (cascade) | Reports "empty or missing (see P-2)". |
| P-4..P-11 | N/A | Correctly skipped — P-4/P-5 N/A at T3, P-6..P-11 N/A under the first-run reduced set. |
| P-12, P-13 | PASS | No prior postflights; no override tags. |

Migration-helper verdict: **WARN exit 1** — "classification.md carries neither tier: nor review_depth:". The table-format record is unreachable by the YAML-lite regex. The helper correctly refrains from mangling the file and refuses to guess.

### 3.2 milestone4_Darlington

| Check | Severity | Notes |
|---|---|---|
| P-1 classification.md exists | **WARN (→ F.2 BLOCK)** | File is absent. Project contains only graph-overlay / advisor / SK20 artefacts. |
| P-2 tier: field | WARN (cascade) | Reports "classification.md missing (see P-1)". |
| P-3 tier: matches | WARN (cascade) | Same cascade path. |
| P-4..P-11 | N/A | Skipped correctly. |
| P-12, P-13 | PASS | No prior postflights; no override tags. |

Migration-helper verdict: **BLOCK exit 2** — "reviews/classification.md not found". The helper is refusing to synthesize a classification record from thin air, which is the correct defensive posture.

## 4. Interpretation

Both projects surface findings that would become BLOCKs under F.2 (v0.5.6). They are non-pathological findings — they are the *intended* Marshal catchment. Specifically:

1. **Legacy classification formats.** The INF3006Y record predates the tier: field and uses a prose-with-table form that was well-formed under v0.5.3's `review_depth` vocabulary. The Marshal correctly declines to blind-match across that boundary; the migration helper correctly declines to mutate the file. Together they surface the legacy boundary rather than pave over it.

2. **Unclassified project roots.** The milestone4_Darlington tree represents a "pre-classification" state — the project has review artefacts (SK20 overlays, advisor consultations) but no formally declared paper type or tier. Under F.2 the Marshal would refuse to run a review at all; under F.1 it surfaces the absence loudly but non-blockingly.

Neither finding is a false positive. Both findings are the F.2 rollout target.

## 5. Recommended user actions before v0.5.6 (F.2 activation)

For **INF3006Y_AgencyDelegation**:
- Add a YAML-lite frontmatter block at the top of `reviews/classification.md`:
  ```
  ---
  paper_type: essay/positioning
  p_stage: P0-P1
  venue: INF3006Y (PhD coursework, iSchool, University of Toronto)
  tier: T3
  last_confirmed: 2026-04-09
  ---
  ```
- Leave the existing prose-and-table body intact; it is still the authoritative narrative. The frontmatter is Marshal-readable metadata, not a replacement.

For **milestone4_Darlington**:
- Run `/classify-manuscript` to produce a fresh classification record, or author `reviews/classification.md` by hand with the frontmatter block above. Either route satisfies P-1 and P-2 together.

## 6. F.2 rollout criteria implication

Both findings are clean, non-pathological hits — they should not delay the F.1→F.2 transition. However, the migration helper's original regex-based frontmatter assumption left a gap at the legacy-table boundary (see §3.1). Two options were considered for v0.5.6:

- **(a)** Ship F.2 with the helper unchanged; document the table-format case as a known migration skip and have users add the frontmatter block manually. *Low effort; relies on the F.2 BLOCK message being legible.*
- **(b)** Teach the helper to parse the "| Review depth | standard |" cell form as a fallback. *Wider coverage; adds a second regex and a table-walker. Defers the ecological complexity into the tool.*

**Decision (2026-04-19, post-smoketest).** User elected (a) in philosophical frame — the Marshal's job is to surface the boundary, not to silently rewrite — with (b) layered on as a conservative extension. The helper now carries a table-cell fallback that:

1. Triggers only when YAML-lite frontmatter carries neither `tier:` nor `review_depth:` (or when no frontmatter exists at all).
2. Requires exactly one `| Review depth | <value> |` row; two or more rows return WARN ("refusing to guess which is authoritative") rather than rewriting.
3. *Prepends* a minimal frontmatter block carrying the derived `tier:`; it does not mutate the original table row. The narrative evidence that motivated the classification stays intact and visible.
4. Emits a provenance comment inside the new frontmatter — `# [migrated via table-cell fallback at v0.5.5 — derived from "Review depth | <value>" row; table row preserved below]` — so the migration path is auditable in-file.

This is (a)'s frame preserved (surface the boundary, don't rewrite the narrative) with (b)'s coverage added (the helper now sees the table form). The failure modes (a) worried about — silent corruption on multi-cell or translated tables — are addressed by the "exactly one row" guard. Translated labels (non-English) still fall through to the "no frontmatter, no table-cell" BLOCK path.

### Edge-case validation (2026-04-19)

Four synthetic fixtures exercised during the late-add. All pass:

| Fixture | Expected | Observed |
|---|---|---|
| `Review depth | \`standard\`` (backticks, emphasis) | PASS, tier:T3 | PASS |
| `Review depth | submission-bound` (no backticks) | PASS, tier:T4 | PASS |
| Two `Review depth` rows with different values | WARN, no rewrite | WARN |
| No frontmatter, no table row | BLOCK | BLOCK |

Idempotency: second invocation against an already-migrated file returns PASS no-op (the new frontmatter is visible to the primary path; the fallback never fires).

## 7. Evidence trail

Artefacts written during this smoketest:

- `INF3006Y_AgencyDelegation/reviews/marshal_preflight_01_2026-04-19.md` + `.json`
- `milestone4_Darlington/reviews/marshal_preflight_01_2026-04-19.md` + `.json`

Both sidecars validate against `marshal_schema_version: 1`. No package-side code was modified during the smoketest — this is a pure observational run.

## 8. Verdict

F.1 advisory rollout behaves as designed on both live projects. No false-positive BLOCKs were generated; both WARN findings are F.2-intended catchments with legible remediation paths. The package is cleared to ship v0.5.5; v0.5.6 (F.2 activation) can proceed once the user has taken the §5 actions on the two live projects, or explicitly declares them out of scope.
