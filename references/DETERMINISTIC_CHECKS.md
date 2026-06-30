# DETERMINISTIC CHECKS — Mechanical Pre-flight for Academic Prose

**Purpose.** This file collects every rule in the package that can be checked **mechanically** — by grep, count, or regex — rather than by judgment. Run these **first**, before any judgment-based review (Step 0a in `REVIEW_ORCHESTRATION.md`). They take minutes and catch the measurable tics that burn reviewer attention.

**When to run.**
- **Always**, as Step 0a of any review, regardless of depth.
- **Re-run after edits** (Step 9 of submission-bound review) to confirm fixes landed and no new tics slipped in.
- **Before committing** any AI-assisted draft or revision (humanness pass per MASTER §A.4.2).

**Scope.** These checks do **not** replace judgment-based review. They are a floor: if a piece fails these, the judgment-based review will also fail. Passing these is necessary but not sufficient.

## 0. D-STYLE canonical pre-flight

Before Step 0a counters, run the canonical pre-flight:

```powershell
python scripts/audit/run_all.py "<manuscript>" --project-root "<project-root>" --date "YYYY-MM-DD" --out "reviews/findings.json"
```

This emits `reviews/findings.json` and `reviews/d_style_profile_YYYY-MM-DD.json`.
The lower-level helper is `scripts/d_style_profile_check.py`, but the canonical
pre-flight entrypoint is `scripts/audit/run_all.py --project-root ...`. The D-STYLE
portion validates the optional `research_notes/directives.md` `d_style_profile` enum
values, resolves inherit-by-absence defaults, lists active D-STYLE obligations for
the round, and checks the manuscript for the required reader-auditable surfaces.

The D-STYLE findings are surface validators, not quality judgments. They check
that the Evaluator has visible surfaces to judge:

- claim, reason, evidence, warrant/stakes, and objection/limit;
- visual-evidence source, scale/axis/unit, method/transformation, and display-limit
  cues when visual evidence is present or required; and
- assistance disclosure or assistance-log cues under the active disclosure policy.

Missing argument or visual-evidence surfaces are MAJOR. Missing assistance surfaces
are MAJOR under `project_local` and BLOCKER under `venue_required` or
`overseer_escalate`. Passing the surface validators does not prove the argument,
evidence display, or disclosure is adequate; it proves those issues are exposed for
Evaluator judgment.

**Output stub:**

```text
### D-STYLE canonical pre-flight
- profile_declared: <true|false>
- resolved_profile: <question_type>/<citation_style>/<harness_profile>
- active_obligations: <comma-separated obligation ids>
- findings: <n>  verdict: <CLEAN|ADVISORY|MAJOR|BLOCKER>
- surface_findings: <argument/visual/assistance finding ids>
- report: reviews/d_style_profile_YYYY-MM-DD.json
```

**Tool assumption.** The patterns below are written for ripgrep (`rg`) which is what Claude uses via the Grep tool. They translate cleanly to `grep -E`, editor find-in-files, or simple scripts. LaTeX-specific patterns assume `.tex` source; Markdown/plain-text patterns are noted where they differ.

---

## 1. How to read each check

Each entry has six fields:

| Field | Meaning |
|---|---|
| **Rule** | The content rule being enforced, with its authoritative location in the package. |
| **Pattern** | The regex or search string to run. |
| **Scope** | Per-file, per-paragraph, per-sentence, or per-section. |
| **Threshold** | The maximum count allowed before the check fails. |
| **Severity on failure** | The tag applied in the findings report (BLOCKER / MAJOR / MINOR). |
| **Fix hint** | Short note on the typical remediation. |

Thresholds are written as "≤ N" (pass if count is N or fewer). A pattern producing zero matches always passes unless the rule requires a minimum.

---

## 2. Absolute language (MAJOR)

| Rule | Pattern | Scope | Threshold | Severity | Fix hint |
|---|---|---|---|---|---|
| No unsupported "cannot" (MASTER §B.1, playbook §2.3) | `\bcannot\b` | per file | **Manual review required for each hit.** Many are legitimate (logical claims); flag each for human judgment. | MAJOR if the hit is a comparative claim about other approaches; MINOR otherwise | Rephrase as "did not aim to," "have not addressed," or "lie outside the analytical focus of." |
| No absolute "must" (MASTER §B.1) | `\bmust\b` | per file | Each hit requires judgment. If the "must" is prescriptive-to-reader, replace with "should." | MAJOR if prescribing behavior; MINOR if quoted or logical | "must" → "should" unless truly necessary. |
| No "comprehensively" (MASTER §B.1) | `\bcomprehensiv\w*` | per file | ≤ 0 (unless quoted) | MAJOR | Delete or replace with "systematically." |
| No "anticipate" in trajectory-prediction sense (MASTER §B.1) | `\banticipat\w*` | per file | Each hit requires judgment; flag if it implies predicting dynamics. | MAJOR if predicting trajectories; MINOR otherwise | Replace with "surface" or "reveal." |

**Single combined pattern for a fast first sweep:**
```
\b(cannot|must|comprehensiv\w*|anticipat\w*)\b
```

---

## 3. Em-dash and punctuation (MINOR)

| Rule | Pattern | Scope | Threshold | Severity | Fix hint |
|---|---|---|---|---|---|
| Em-dash sparingly (MASTER §E.2) | `---` in LaTeX; `—` in plain text | per paragraph | ≤ 1 pair per paragraph; 0 nested pairs | MINOR | Prefer colons, commas/parentheses, semicolons, or a sentence break. |
| No stacked em-dash pairs (MASTER §E.2) | `---.*?---.*?---` (three or more on one line or within a paragraph) | per paragraph | ≤ 0 | MINOR | Break the sentence; convert the outer pair. |
| No nested em-dash pairs (MASTER §E.2) | `---[^-]*?---[^-]*?---[^-]*?---` | per paragraph | ≤ 0 | MINOR | Replace inner pair with commas or parentheses. |

**Quick count sweep:**
```
rg --count '---' <file>         # total em-dash count
rg --count -- '—' <file>        # plain-text em-dashes (rare in LaTeX)
```

**H-motivated em-dash insertion (named false-fix pattern).** When applying Sub-check H marker 4 (register-shift signposting), the Generator defaults to em-dash as the signposting vehicle — e.g. "not a political stance — it is a question of method." This satisfies M4 but adds to the §3 em-dash count. **Preferred M4 vehicles (§3-neutral):** semicolon for contrast bridges ("not a political stance; it is a question of method"), colon for specification pivots, explicit cue phrases (`consider concretely:`, `in plain terms:`, `to put this technically:`). On any H-motivated revision pass, verify that em-dash counts did not increase. If they did, flag the delta as a §3 regression even if the individual paragraph count is still ≤1 pair — the *pattern* is the tell. Cross-reference: `references/lay_term_lexicons.md §4` generalisation note 5; `skills/accessibility-overlay/references/sub_checks.md §H marker 4`; MASTER §E.2 ("do not let em-dash count go up when applying edits; models often add `---` or `—` when restructuring to satisfy a finding").

---

## 3b. Grammar mechanics (Blue Book) — work queue for `grammar-mechanics-pass` (added 2026-06-28)

Regex-detectable correctness candidates from `blue_book_grammar_guidelines.md`. These are **candidates**, not violations — most require the judgment pass to confirm (the same two-layer pattern §9a/§9b use). The pre-filter surfaces them cheaply; `skills/grammar-mechanics-pass/SKILL.md` Phase 2 judges them. Em-dashes are **out of scope here** — they are owned by §3 above.

| Rule | Pattern | Scope | Threshold | Severity | Fix hint |
|---|---|---|---|---|---|
| its / it's confusion (BB §2.4) | `\bit's\b` (verify "it is"/"it has"); `\bits'\b` (always wrong) | per occurrence | each `it's` verified | MAJOR if possessive intent | `it's`→`its` when possessive; `its'` is never valid. |
| Comma splice candidate (BB §2.1) | independent clause `, ` + independent clause, no coordinating conjunction | per sentence | 0 confirmed | MAJOR | Semicolon, conjunction, or period. |
| Nonrestrictive `which` without comma / restrictive `that` with comma (BB §1.4) | `\w+\s+which\b` not preceded by comma; `, that\b` | per occurrence | judgment | MAJOR if meaning changes | Essential→`that` no commas; nonessential→`which` commas. |
| `-ly` adverb hyphenated to adjective (BB §2.5) | `\b\w+ly-\w+` | per occurrence | 0 | MINOR | Drop the hyphen ("highly regarded"). |
| Decade/possessive apostrophe error (BB §2.4) | `\b\d{4}'s\b` | per occurrence | 0 | MINOR | `1990s`, not `1990's`. |
| Sentence-initial digit (BB §4 Rule 1) | line/sentence starting `^\d` | per sentence | 0 | MINOR | Spell out or recast. |
| 4+ digit figure without grouping comma (BB §4 Rule 3a) | `\b\d{4,}\b` (non-year, non-citation) | per occurrence | venue-dependent | MINOR | Group by threes per declared style. |

**Venue note.** Oxford-comma and number-spell-out thresholds are **declared-style-dependent** (`research_notes/directives.md` `citation_style`). The pre-filter flags **inconsistency within the manuscript** and sentence-initial digits unconditionally; it does **not** impose a single threshold. A declared-style conflict is emitted as `[CONFLICT]`, not silently resolved (`blue_book_grammar_guidelines.md §6`).

**Quick sweep:**
```
rg --count -- "\bit's\b" <file>
rg -n -- "\b\w+ly-\w+" <file>
rg -n -- "\b[0-9]{4}'s\b" <file>
```

---

## 4. LLM tics (MAJOR on cluster, MINOR individually)

From MASTER §A.4.2. The "humanness pass." Each pattern is a tell; multiple hits compound.

| Rule | Pattern | Scope | Threshold | Severity | Fix hint |
|---|---|---|---|---|---|
| "Not X but Y" / "not just X but Y" stacked | `\bnot (just |only |merely )?\S+ but\b` | per file | ≤ 2 | MAJOR if > 2 | Allow ≤ 2 per paper; rewrite the rest as direct assertions. |
| Triadic lists (three parallel items) | Manual: look for `A, B, and C` structures repeated across paragraphs | per file | Reduce by half if clearly stacked | MAJOR if stacking is obvious | Break at least half into asymmetric pairs or singletons; vary length. |
| Trailing one-sentence add-ons | Manual: short sentence at paragraph end that could be cut without loss | per paragraph | 0 | MINOR | Fold into the paragraph or cut. |
| Hedged transitions at every paragraph break | `^(Accordingly|Likewise|Therefore|In practical terms|Moreover|Furthermore|Additionally),` | per file | ≤ 40% of paragraph breaks | MAJOR if density > 50% | Drop ~40%; logic survives. |
| Abstract-noun stacking | Manual: look for three or more abstract nouns in one sentence without a concrete verb or image | per sentence | Manual flag | MINOR per instance | Insert a concrete verb or image every few sentences. |
| Glossary-dump opening | 4+ consecutive italicized term definitions in opening section | per opening | ≤ 3 | MAJOR | Defer each term to the paragraph where it first does analytical work. |
| Semicolon-chained triads | `\w+[^;]*;\s*\w+[^;]*;\s*\w+[^;]*[.!?]` with parallel grammar | per sentence | Each hit is a tell | MINOR | Recompose as cause-and-effect prose. |
| Taxonomic parenthetical glosses after `\emph{}` terms | `\\emph\{[^}]+\}\s*\([^)]{10,}\)` | per file | Each hit requires judgment; flag when the parenthetical provides a comma-separated gloss list for a technical construct (e.g., `\emph{person-based} (the loan officer's years…)`) | MINOR | Absorb the gloss as an appositive, relative clause, or separate sentence; let the term emerge from the argument rather than being annotated over it. |
| Abstract demonstrative pivots ("This X illustrates/supports/strengthens") | `\b[Tt]his\s+\w+\s+(illustrates?\|supports?\|strengthens?\|confirms?\|sharpens?)\b` | per file | ≤ 0 | MINOR | Replace with a construction that advances the argument directly; the evidence should carry the claim, not announce that it does. |
| Third-person self-reference in a first-person paper | `\b[Tt]he\s+(essay\|paper\|article\|argument)\s+(draws\|asks\|argues\|develops\|shows\|claims\|examines\|grounds\|considers\|notes\|suggests\|proposes\|identifies\|traces)\b` | per file | Each hit requires judgment; flag when first-person is the established voice register | MINOR | Replace with first-person ("I develop…") or restructure as a direct assertion with no meta-commentary subject. |
| Forward-pointer sentences before section headers ("The next section specifies…") | `\b[Tt]he (next\|following) section\b` | per file | ≤ 0 unless the section header cannot carry the navigation alone | MINOR | Cut the sentence; the section header does the navigational work. If a load-bearing observation is present, absorb it into the closing sentence of the preceding paragraph via colon construction. |

**Combined sweep pattern for a fast §4 first pass:**
```
\b(not (just |only |merely )?\S+ but)\b
\\emph\{[^}]+\}\s*\([^)]{10,}\)
\b[Tt]his\s+\w+\s+(illustrates?|supports?|strengthens?|confirms?|sharpens?)\b
\b[Tt]he\s+(essay|paper|article|argument)\s+(draws|asks|argues|develops|shows|claims|examines|grounds|considers|notes|suggests|proposes|identifies|traces)\b
\b[Tt]he (next|following) section\b
```

---

## 5. Sentence focus and voice (Bacon §10; MASTER §F.2)

| Rule | Pattern | Scope | Threshold | Severity | Fix hint |
|---|---|---|---|---|---|
| No "there is / there are / there remain" as subject delayer | `\b[Tt]here (is|are|remain\w*)\b` | per file | Each hit requires judgment; many are fine | MINOR | If delaying a real subject, invert. |
| Overclaiming verbs | `\b(reveal\w*|expose\w*|prove\w*)\b` | per file | Each hit requires judgment | MAJOR if applied to one's own contribution; MINOR if to prior work | Prefer "shows," "demonstrates," "makes visible." |
| "Standard" implies consensus | `\bstandard\s+(approach\w*\|method\w*\|practice\w*)\b` | per file | Flag each hit | MINOR | Prefer "existing," "established," or name the specific approaches. |
| "First-class" used rhetorically | `\bfirst[\s-]class\b` | per file | Flag if paper does not introduce a metamodel change | MAJOR if misleading | Remove or rewrite; the term carries metamodel semantics in engineering venues. |

---

## 6. Sentence length distribution (Bacon §9.5; MASTER §F.5)

**Rule.** Technical prose ~15–20 words average; academic / long-form prose ~25. Avoid 60+-word sentences without relief.

**Pattern.** No simple regex; run a script or editor macro. A quick Bash sketch for LaTeX (strip commands then count):

```bash
# Rough sentence-length distribution (LaTeX-aware-ish)
cat file.tex \
  | sed 's/\\[a-zA-Z]*\({[^}]*}\)\?//g' \
  | tr -d '{}' \
  | tr '.?!' '\n' \
  | awk 'NF{wc=NF; print wc}' \
  | awk '{
      total+=$1; count++;
      if ($1 > max) max = $1;
      if ($1 > 60) over60++;
    } END {
      print "sentences:", count;
      print "avg words:", total/count;
      print "max words:", max;
      print "sentences > 60 words:", over60+0;
    }'
```

| Threshold | Severity | Fix hint |
|---|---|---|
| avg > 30 words | MINOR | Break long sentences; prefer early verb. |
| max > 60 words | MINOR each instance | Restructure into two sentences. |
| avg < 12 words | MINOR | Prose may feel choppy; add a cumulative sentence or two. |

---

## 7. Citation and integrity (BLOCKER on failure)

| Rule | Pattern | Scope | Threshold | Severity | Fix hint |
|---|---|---|---|---|---|
| Fabrication guard (MASTER §A.2) | `\[REF to be verified\]` | per file | Warn if present at submission time | **BLOCKER** if submission-bound | Verify each placeholder before submission. |
| Citation order (Springer/numeric venues) | Manual: walk `\cite{...}` / `\bibitem` in appearance order | per file | Strict ordering if venue requires | MAJOR | Renumber. |
| Unused bib entries | `grep -v '\cite{' mainfile.tex` against `\bibitem` keys | per file | Warn | MINOR | Remove unused bibitems. |
| Undefined citations | Check LaTeX build log for `Citation 'X' undefined` | build log | ≤ 0 | **BLOCKER** if building for submission | Add the missing bib entry. |
| Citation format consistency in `\hyperlink{}{}` documents | `\([A-Z][^)]+, [0-9]{4}\)` patterns not preceded by `\hyperlink` | per file | 0 | MINOR | Wrap plain `(Author, Year)` in `\hyperlink{key}{Author, Year}`. |
| Compound-claim citation flag (L-P4) | Sentence ending in `\hyperlink{...}{...}\)` that contains any of `\s(and\|or\|as well as)\s` between a finite verb and the citation, or lists separated by commas terminated by a single citation | per file | Flag all matches as candidates for manual conjunct-level check | MAJOR if unverified | For each flagged sentence, verify the cited source supports *every* conjunct, not just the first. See GROUNDING_PROTOCOL.md §Audit Procedure, Rule 1 (conjunct-level attribution check). Remediate by splitting the citation, narrowing the claim, or replacing with a source that covers the full compound. |

**Detection regex for compound-citation candidates (Step 0a):**

```regex
# Matches sentences containing " and " or " or " inside a compound structure
# that terminates with a \hyperlink{...}{...} citation.
[A-Z][^.!?]*?(\s+(and|or|as well as|,)\s+[^.!?]*?)+\s*\(\\hyperlink\{[^}]+\}\{[^}]+\}\)\s*\.
```

The regex is intentionally over-inclusive: it flags any compound sentence with a trailing hyperlinked citation. The manual step is to ask, for each conjunct: *does the source support this specific conjunct*? Over-flagging is preferable because silent conjunct failures are the hardest grounding violation to catch — the citation exists, the source was read, the most prominent conjunct is supported, and the reader's priors fill the gap on the rest.

**Severity ladder:**
- Flagged, reviewer confirms source supports all conjuncts → MINOR (no action; record verification).
- Flagged, source supports only some conjuncts → MAJOR (remediate per GROUNDING_PROTOCOL).
- Flagged, source supports none of the conjuncts → **BLOCKER** (fabrication-adjacent; escalate to Rule 4 violation).

---

## 8. Scope-keyword traps (stage-dependent)

From `project_writing_style_checklist.md` Part 0. Each pattern is a P-stage warning.

**Authoritative axis definitions live in `GROUND_TRUTH.md` (registered to the EYgp workbook `references/EYgp_Research_process_and_artifacts.xlsx`).** The patterns below are package-level *reader-convention* tells, not direct transcriptions of the workbook. Items marked `[INFERRED]` in the provenance column extend the workbook definitions; see `reviews/ground_truth_verification_2026-04-17.md` §2 for the paraphrase audit.

| Rule | Pattern | Stage where flagged | Severity | Fix hint | Workbook provenance |
|---|---|---|---|---|---|
| P2 vocabulary in a P0/P1 conclusion | `\b(resolution|resolves|answers|research question|RQ\d)\b` in conclusion section | P0 or P1 | MAJOR | Use "refined problem statement," "open questions," "candidate q-items." | `Sheet2!D3` supplies "research problems/questions/objectives" directly; `resolution`/`resolves`/`answers`/`RQ\d` are **package-recognised tells** `[INFERRED]` (not in workbook). |
| "Not X but Y" in P0/P1 positioning sentences | see §4 above | any stage | MAJOR if density | As §4. | Out of scope (prose-style rule, not an axis definition). |
| Premature numbered RQs in §1 | `\bRQ[\d]+\b` or `\bq[0-9]+\b` in §1 of a P0/P1 paper | P0 or P1 | **BLOCKER** if the piece is P0/P1 | Restate as problem phenomenon + characterization lenses. | Workbook labels P2 problems as `q1 q11 q21 ...` (`Sheet2!D5`); `RQ\d` is a reader-convention proxy for `q#` `[INFERRED]`. |

### 8a. EYgp ground-truth verification (all axes)

This sub-section is a **pre-filter**, not a pass/fail check; it raises candidates for the `eygp-framework-checker` skill (see `skills/packaged/eygp-framework-checker.md`). The patterns detect stage-label usage on any of the six EYgp axes so the framework checker can verify them against `GROUND_TRUTH.md`.

| Marker class | Pattern | What to emit |
|---|---|---|
| Any axis-stage label | `\b(P[012]|R[012]|K[012]|S[1-5]|T[1-5]|V[0-5])\b` | file:line + matched label + one sentence of surrounding context |
| Readiness tick | `[✓]{1,5}` (Unicode check marks) or `\b\d+%?\s*(ready|-tick)\b` | file:line + matched text |
| Artefact-genre phrase tied to a stage | `\b(technical\s+(sketch|outline|note)|working\s+paper|published\s+paper)\b` | file:line + matched phrase (these map 1-to-1 to S1/S2/S3/S4/S5 in `Sheet1`) |
| Thesis-chapter phrase tied to a stage | `\b(Bib|Motivation|Research\s+Objectives|Related\s+work|Contributions|Background\s+on\s+subject-matter\s+area|Solution\s+chapters|Tools\s+chapter|Validation\s+chapter)\b` | file:line + matched phrase (maps to workbook thesis-chapter cells) |

**Emission rule.** Every match adds one candidate location to the `eygp-framework-checker` work queue. A location may match multiple markers; aggregate them.

**Output stub:**

```
### EYgp axis pre-filter
- Axis-stage labels found: <n>
  - <file:line>: <P1 | S3 | ...>
- Readiness-tick claims found: <n>
- Artefact-genre phrases: <n>
- Thesis-chapter phrases: <n>
- Candidate locations for eygp-framework-checker: <total unique>
```

**Scope.** This pre-filter is run on any artefact under review (manuscript, classification record, project memo, revision plan). It does **not** modify §8 severities — those remain the package's prose-style rules. It only produces a queue for the cross-axis framework check.

**Rationale.** Axis stages were previously only referenced informally in the package. The EYgp workbook is the authoritative source; when a manuscript or plan mentions `S3` or `✓✓✓`, the verifier should be able to find every such mention mechanically and decide whether it survives the workbook comparison. See `GROUND_TRUTH.md` for the canonical definitions.

---

## 9. LaTeX hygiene

| Rule | Pattern | Scope | Threshold | Severity | Fix hint |
|---|---|---|---|---|---|
| Preserve `\label`, `\ref`, `\cite` (MASTER §E.3) | Diff-based: any removed `\label` should be intentional | per edit | — | **BLOCKER** if accidental | Restore; cross-check with `\ref`. |
| Math mode balance | `\\\(|\\\)|\$` count parity | per file | even count | BLOCKER | Fix unmatched `$` or `\(\)`. |
| Invasive package changes | Diff against `\documentclass`, `\usepackage` | per edit | ≤ 0 unless instructed | MAJOR if accidental | Revert unless the user asked for it. |
| `\end{document}` presence | `grep -c '\\end{document}'` | per file | exactly 1 | BLOCKER if 0; MAJOR if > 1 | Add `\end{document}` at file end (if 0); remove duplicate (if > 1). |
| Word-count compliance (when a target is specified) | `pdftotext <file.pdf> - \| head -[N lines before References] \| wc -w` | compiled PDF body (excl. references) | within declared target range | MINOR if > 100 words above target; flag to user if > 100-word divergence from source-based count | Use pdftotext body-only as the submission-facing figure; report alongside any source-based estimate. (L-20, approved 2026-04-16) |

---

## 9c. Artifact organization (INF3001H_Research project standard)

| Rule | Pattern | Scope | Threshold | Severity | Fix hint |
|---|---|---|---|---|---|
| Diff files in draft/ (sanity check) | Any `*_diff.tex` file under the project's `draft/` directory | per project | ≤ 0 | **MAJOR** | Move all `*_diff.tex` files to the `diffs/` subfolder. Diffs are review artifacts and should not be mixed with submission-ready versions. See `INF3001H_Research/diffs/README.md` for organization guidelines. |

**Detection command:**
```bash
find <project>/draft -name '*_diff.tex' -type f
```

**Rationale.** Diff files (produced by `latexdiff` or similar tools) contain markup that changes the document structure and semantics. They are invaluable for review (showing change tracking between revisions) but must not appear in the submission artifact folder (`draft/`). Keeping them in a separate `diffs/` subfolder preserves their utility while preventing confusion about which file is the "official" version. This rule catches accidental diffs left in the draft folder after regeneration.

---

## 9a. Inter-sentential connective pre-filter (triggers SAFEGUARD_LAYER Check 7)

This block is a **pre-filter**, not a pass/fail check. It produces a list of candidate paragraphs for judgment review under `SAFEGUARD_LAYER §Check 7` (Inter-Sentential Logical Connective Audit). No severity is emitted here; severity is assigned by Check 7.

| Marker class | Pattern | What to emit |
|---|---|---|
| Explicit application phrase | `\bI\s+(apply|extend|draw\s+on|follow|use|adopt)\b[^.]*\b[A-Z][a-z]+'s\b` | paragraph locator + matched string |
| Template invocation | `\b[A-Z][a-z]+'s\s+(analytic\s+template|framework|lens|apparatus|template)\b` | paragraph locator + matched string |
| Attributional inversion candidate | conditional (`\bIf\b[^.]+\bthen\b`) in sentence `S_n` followed within two sentences by any explicit application phrase | paragraph locator + both sentences |
| Following-X pivot | `\b[Ff]ollowing\s+[A-Z][a-z]+` or `\b[Ii]n\s+[A-Z][a-z]+'s\s+terms\b` | paragraph locator + matched string |
| Descriptive-to-normative jump candidate | `,\s+so\s+\w+\s+(should|must|ought\s+to)\b` within a single sentence | paragraph locator + matched string |

**Emission rule:** Every match adds one candidate paragraph to the Check 7 work queue. A paragraph may match multiple markers; list it once with all matches aggregated.

**Output stub:**

```
### Inter-sentential connective pre-filter
- Candidate paragraphs for Check 7: <count>
  - §X, line Y: [markers matched]
  - ...
```

**Rationale:** The Khovanskaya paragraph in INF3001H "Whose Humanness Is Encoded?" passed five review rounds with three of these markers co-present (If-Then conditional, "I apply Khovanskaya's analytic template," descriptive→normative "so…should" close). No regex caught it because none treats the co-presence as a flag. This pre-filter does.

---

## 9b. Reader cognitive load pre-filter (added 2026-04-13)

This block is a **pre-filter**, not a pass/fail check. It produces a list of candidate locations for judgment review under `SAFEGUARD_LAYER §Check 8` (Reader-Experience / Prose Architecture Audit). The block is motivated by the Round 7 external readability review (see `INF3001H_Research/draft/reviews/analysis_external_reviewer_gap_2026-04-13.md`), which identified four axes the prior pipeline did not own: sentence architecture (subject-verb distance), definition topology, prose cadence, and list-in-disguise patterns.

| Marker class | Pattern | What to emit |
|---|---|---|
| Long-subject / late-verb sentence | Any sentence where the first finite main-clause verb appears > 20 words from sentence start. Heuristic proxy: sentences with a subordinate clause (`,\s*(which\|that\|who)\b` or `,\s*including\b`) within the first 20 words **and** total length > 30 words | sentence locator + word-count-to-first-verb |
| Stranded definition block | In LaTeX: any `\textbf{[^}]+\.}` or `\noindent\\emph\{[^}]+\.\}` immediately preceded by `\end{abstract}` or preceded only by section scaffolding and not followed by the term's first substantive use within 3 paragraphs | block locator + defined term |
| Definition after first substantive use | For each formally defined term `\emph{X}` introduced by `By X, I mean` or similar, check whether an unitalicized occurrence of `X` appears earlier in the document. If so, the definition lags its first use | term + first-use line, definition line |
| Unrelieved long-sentence run | Three or more consecutive sentences each > 35 words within a single paragraph, with no sentence ≤ 20 words among them | paragraph locator + sentence-length sequence |
| Rhetorical-question stacking | A single paragraph containing ≥ 3 sentences ending in `?` | paragraph locator + question count |
| Triadic enumerator (mechanized) | `\bFirst,\b[\s\S]{20,400}?\bSecond,\b[\s\S]{20,400}?\bThird,\b` OR three semicolon-chained parallel clauses in a single sentence (see §4 existing pattern, elevated from manual to mechanized) | passage locator + enumerator spans |
| Overclaiming verbs, expanded scope | `\b(reveal\|reveals\|revealing\|expose\|exposes\|exposing\|prove\|proves\|demonstrate\|demonstrates)\b` applied to the paper's own analysis (subject = the materials, the analysis, this essay, the evidence) | per-hit line + subject |
| **Paragraph cadence: turn-point absence** (new at v0.7.2; feeds Check 8 Sub-check A) | Paragraph with word count > 150 AND containing no turn-point cue from the lexicon `\b(however\|but\|yet\|still\|by contrast\|conversely\|suppose\|for example\|to illustrate\|consider\|take the case of\|reframing\|which is to say\|put differently)\b`. Paragraphs > 200 words are flagged independently of cue presence | paragraph locator + word count + cue-absence flag |
| **Section-transition preamble absence** (new at v0.7.2; feeds Check 8 Sub-check D) | For every section or subsection heading, inspect the first paragraph. Flag if the paragraph lacks **both** an orienting clause (pattern: `\b(having\|after\|so far\|in the preceding\|this section\|the previous section\|up to this point)\b` or equivalent backward-reference) **and** a contribution clause (pattern: `\b(this section\|what follows\|I now\|I turn to\|the next move\|we will\|I will show\|the contribution here)\b` or equivalent forward-reference). A section that dives directly into dense theoretical prose with no signpost is the "cold-open" pattern | section heading locator + missing-clause types |
| **Jargon density per paragraph** (new at v0.7.2; feeds Check 8 Sub-check E) | Count new domain terms introduced in each paragraph. A term is "new" if it is either italicized (`\emph{X}` / `*X*`) for the first time in the section, present in `references/terminology_register.md` and not cited earlier in the section, or tagged in `research_notes/glossary.md` as a first-use marker. Flag any paragraph whose count exceeds the P-stage cap: **P0 ≥ 4, P1 ≥ 3, P2 ≥ 2** (one above the Sub-check E strict cap, to surface candidates for judgment rather than to enforce) | paragraph locator + term count + listed new terms |

**Emission rule:** Every match adds one candidate location to the Check 8 work queue. A location may match multiple markers; list it once with all matches aggregated.

**Output stub:**

```
### Reader cognitive load pre-filter
- Long-subject / late-verb sentences: <count>
- Stranded definition blocks: <count>
- Definition-after-first-use: <count>
- Unrelieved long-sentence runs: <count>
- Rhetorical-question stacking paragraphs: <count>
- Triadic enumerators: <count>
- Overclaiming verbs (expanded): <count>
- Paragraph cadence (turn-point absent, >150w): <count>     # new v0.7.2
- Section-transition preamble absent: <count>                # new v0.7.2
- Jargon density exceeded (P-stage cap +1): <count>          # new v0.7.2
- Candidate locations for Check 8 Sub-check A (cadence): <count>
- Candidate locations for Check 8 Sub-check D (signposting): <count>
- Candidate locations for Check 8 Sub-check E (jargon density): <count>
- Candidate locations for Check 8 (all sub-checks, total unique): <count>
  - §X, line Y: [markers matched, sub-check codes]
  - ...
```

**Rationale:** On INF3001H, the six internal review rounds produced a READY verdict while seven reader-ergonomics defects remained. An external reader caught them on a single readability pass. The defects shared one property: none was a rule violation the pipeline tracked. They were unowned axes. This pre-filter mechanizes the axes so future projects surface them automatically.

**Relationship to §9a.** §9a targets *paragraph-internal logical connective integrity* (invisible to mechanical checks, caught by adversarial reading). §9b targets *reader working-memory load within a paragraph or a section opening* (invisible to analytical checks, caught by first-pass reading). The two pre-filters are orthogonal; both feed the safeguard layer. See §9d for the manuscript-scale counterpart that feeds Sub-check G.

---

## 9d. Cumulative cognitive load pre-filter (added 2026-04-23, feeds SAFEGUARD_LAYER Check 8 Sub-check G)

This block is a **pre-filter**, not a pass/fail check. It produces deterministic signals that locate *candidate* structural boundaries where a Sub-check G judgment pass should verify consolidation-anchor placement. Unlike §9b, §9d operates at **manuscript scope**: its measurements span the whole file, not a single paragraph or section opening. The block runs at Ph3 and Ph4 (the tiers where Sub-check G is active at full-manuscript scope) and is skipped at Ph2 (where Check 8 runs section-scoped Sub-checks A–F only).

| Marker class | Pattern | What to emit |
|---|---|---|
| **Boundary gap — word count since last major heading** | For every major heading (`^## ` or `^# ` in Markdown; `\section{` or `\chapter{` in LaTeX), compute the word count of body prose between that heading and the previous major heading (or the manuscript start, for the first major heading). Flag boundaries where the span's body word count exceeds the P-stage gap envelope: **P0 ≥ 800 words, P1 ≥ 700 words, P2 ≥ 600 words**. Paragraphs inside the span that open with a major subheading (`^### ` or `\subsection{`) are counted as body prose, not boundary breaks | boundary locator + preceding-span word count |
| **Boundary gap — paragraphs since last major heading** | For the same major-heading set, count paragraphs in the span. Flag boundaries where the span contains more than six paragraphs AND the preceding-span word count exceeds the P-stage envelope above. Six is the working-memory reliable-recall ceiling documented in the Ph.D.-root §13.2 Sweller reference set; paragraph counts above it imply construct accumulation without consolidation opportunity | boundary locator + paragraph count |
| **Consolidation-cue density in the two paragraphs before a major heading** | For the two paragraphs immediately preceding each major heading, scan for a consolidation-cue lexicon: `\b(at this point\|so far\|to this point\|up to now\|taking stock\|we have seen\|we have established\|the reader now\|at this stage\|with (this|these) in place\|having (mapped\|traced\|identified\|set out)\|with the (foregoing\|preceding)\|what the (preceding\|foregoing) (pages\|sections))\b`. Record the count of matches in those two paragraphs | boundary locator + cue count (0, 1, 2+) |
| **Consolidation-cue density in the opening paragraph of a new major section** | For the opening paragraph of each major section, scan for the same consolidation-cue lexicon plus the backward-reference lexicon from §9b Sub-check D (`\b(having\|after\|so far\|in the preceding\|this section\|the previous section\|up to this point)\b`). A single match counts whether from either lexicon; the point is backward consolidation, not the form | boundary locator + cue count (0 or ≥ 1) |
| **G-candidate boundary** (synthesis marker) | A boundary qualifies as a Sub-check G candidate when BOTH (i) the preceding-span word count exceeds the P-stage gap envelope AND (ii) the consolidation-cue density is zero in both the two-paragraph pre-heading window and the opening paragraph of the next section. These are the boundaries the judgment pass should audit first | boundary locator + preceding-span word count + zero-cue confirmation |

**Emission rule.** Every G-candidate boundary adds one row to the Check 8 Sub-check G work queue. The deterministic layer emits a candidate; the judgment layer (the Evaluator running Sub-check G via the `accessibility-overlay` skill) confirms whether the boundary actually crosses the construct-accumulation threshold of §13.3 criterion 7 and whether any cue match (if present) is doing the consolidation work the criterion requires. Cue matches alone do not clear the boundary — a sentence saying "at this point" that fails to name what the reader holds and where the argument is going still fails G.

**Output stub:**

```
### Cumulative cognitive load pre-filter (Sub-check G)
- Major headings scanned: <count>
- Boundary gaps exceeding P-stage envelope (words): <count>
- Boundary gaps exceeding six-paragraph ceiling: <count>
- Zero-cue pre-heading windows: <count>
- Zero-cue section-opening paragraphs: <count>
- G-candidate boundaries (both gap-exceeded AND zero-cue): <count>
  - <boundary locator>: preceding-span wc=<n>, para count=<n>, pre-heading cues=<n>, opening cues=<n>
  - ...
- Manuscript word count total: <n>
- Manuscript over 5,000-word envelope (per Sub-check G BLOCKER rule): <yes/no>
```

**Rationale.** The INF3006Y Co Author Ph4 test variant surfaced the pattern §9d catches: eight major sections, roughly 6,200 body words, zero consolidation cues in the critical pre-heading windows before Sections 4, 5, and 6 despite each of those sections introducing an argument dependent on prior material. §9b's local pre-filter saw nothing because each paragraph's cadence, density, and first-use compliance was individually clean. §9d elevates the probe from the paragraph to the section boundary, parallelling the scale shift from Sub-checks A–F to Sub-check G. The pre-filter is intentionally coarse — the judgment pass can re-classify any G-candidate boundary as not actually threshold-crossing (e.g., if the span is a short illustrative interlude rather than a construct-accumulation span).

**Relationship to §9a and §9b.** §9a = paragraph-internal logical connective integrity. §9b = within-paragraph / section-opening reader working-memory load. §9d = manuscript-scale consolidation at structural boundaries. The three pre-filters are orthogonal scales (sentence-pair, paragraph, manuscript); all feed the safeguard layer. §9c is reserved for the pre-existing INF3001H artifact-organization block and is unrelated.

**P-stage adjustment.** The P-stage gap envelope (P0 ≥ 800 / P1 ≥ 700 / P2 ≥ 600) reflects the empirical observation that P0 manuscripts can carry slightly longer sections before consolidation is required (exploratory register tolerates construct-accumulation spans) while P2 manuscripts require earlier consolidation (resolution register must hold the mental model tighter). The envelope is calibrated from the INF3001H (P1) and INF3006Y (P0) review corpora as of 2026-04-23; it is a starting point, not a fixed rule, and should be re-calibrated when a P2 manuscript completes a Ph3 round under v0.8.1.

---

## 9e. Register pre-filter (added 2026-04-27, feeds SAFEGUARD_LAYER Check 8 Sub-check H)

This block is a **pre-filter**, not a pass/fail check. It produces deterministic counter probes for the three negative markers Sub-check H audits at the passage level (unnecessary nominalisation, stacked prepositional phrases, hedging pile-up; see SAFEGUARD_LAYER §Check 8 Sub-check H §4). The block runs at Ph3 (the tier where Sub-check H is active under `register_class: technical` and `register_class: mixed`; manuscript-wide under `register_class: non-technical`) and is skipped at Ph2 (where Check 8 runs section-scoped Sub-checks A–F only). v0.10.1's RELEASE_NOTES enumerated this pre-filter under the slot label "§9b" — the actual slot is §9e because §9b was already taken by the v0.7.2 reader-cognitive-load pre-filter.

§9e operates at **passage scope** by default (mirroring Sub-check H's passage-scope variant covering signpost orienting/contribution clauses, section framing, inter-section transitions, worked-example vignette bodies, and consolidation anchor sentences). Under `register_class: non-technical`, the pre-filter extends to manuscript-wide non-technical passages identified by Sub-check H's functional removability test. The pre-filter is intentionally **advisory-only** under the v0.10.1 `advisory_until: H_two_revision_cycles` flag — its findings inform Sub-check H but do not gate the §3.3.3 TerminalSignoffRow during the advisory period.

| Marker class | Pattern | What to emit |
|---|---|---|
| **Nominalisation density** | Token-level count of suffix-pattern matches `\w+(tion\|ment\|ance\|ence\|ity\|ness)\b` (excluding `-ing` form: see exclusion-list rationale below) within the passage, normalised to passage word count. Fires when `nominalisation_count / passage_word_count > 0.08`. The 0.08 threshold sits above the 90th-percentile academic baseline of ~0.10 reported in register-corpus studies, surfacing passages whose nominalisation density exceeds the median academic register. Exclusion list (proper nouns, established domain terms, common copular nominals): `\b(introduction\|conclusion\|abstract\|methodology\|discussion\|reference\|definition\|condition\|relation\|application\|operation\|representation\|description\|interpretation\|specification\|implementation\|verification\|evaluation\|presentation\|generation\|orientation)\b` — these are content-bearing nominals whose removal would lose meaning, not register inflation. Italicised constructs and project-glossary entries are excluded by the same delegation as Sub-check C's "construct" definition. | passage locator + raw count + normalised value + threshold + fired flag |
| **Prepositional-phrase run length** | Longest consecutive run of prepositional phrases within a single sentence, via the simplifier pattern `\b(of\|in\|for\|with\|to\|by\|on\|at\|from\|under\|over\|through\|via)\s+\w+`. The probe identifies stretches like "*the analysis of the structure of the relationship between the constructs in the framework*" — three or more `of`-phrases (or any preposition-phrase mix) consecutively. Fires when run length ≥ 3. The threshold of three is anchored in Williams' *Style: Toward Clarity and Grace* (2014) §6 documentation that two prepositional phrases is the comfortable upper bound; three or more imposes mental-stack demand the reader cannot sustain across the sentence. | passage locator + run length + run span (start-end token indices) + threshold + fired flag |
| **Hedging density** | Count of hedging-marker matches against the hedge list, normalised to per-100-words. Default built-in hedge list: `\b(may\|might\|could\|perhaps\|possibly\|likely\|suggests\|indicates\|appears\|seems\|somewhat\|relatively\|generally\|typically)\b` (15 markers). Per-project override mechanism (the project's `research_notes/hedge_terms.md` overrides the built-in default if present) is **mentioned but not implemented in v0.10.2**; v0.10.3 implements when a project requires the override. Fires when `hedge_count / passage_word_count * 100 > 2` (more than two hedges per 100 words). Two-per-100 reflects the observation that genuine epistemic care typically ships ≤ 1 hedge per 100 words; pile-up at 3+ per 100 dilutes the modal claim and reads as register-soft. | passage locator + raw hedge count + words + per-100 ratio + threshold + fired flag |

**Exclusion-list rationale for nominalisation suffix `-ing`.** The `-ing` form is doubly ambiguous in academic prose: it serves as participial verb (an active form), gerund-noun (a content-bearing nominal), and progressive aspect (still verb-anchored). Including `-ing` in the suffix probe inflates false-positive rates by ~30% in pilot probing on the v0.10.0 INF3001H Round 7 corpus, mostly on participial constructions ("having traced the dependencies", "applying the framework"). The five remaining suffixes (-tion / -ment / -ance / -ence / -ity / -ness) are unambiguously nominal. Future v0.10.3 calibration may re-introduce `-ing` with a participial-form filter; the current probe ships without it.

**Output contract per probe.** Each probe emits a tuple `(probe_name, raw_count, normalised_value, threshold, fired: bool)`. The pre-filter bundle (three tuples per passage) is appended to the passage's overlay-input record under field `prefilter_h_bundle`. The overlay's Sub-check H step 1, on receiving the bundle, can short-circuit to `NULL/CLEAN` for that passage if all three `fired` values are `false` — saving the full register classification pass. If any probe fires, the overlay runs the full Sub-check H procedure and the bundle's raw signals enter the per-finding rationale.

**Emission rule.** Every passage in scope emits one bundle, regardless of whether any probe fires. The bundle's `fired` aggregate (logical OR across the three probes) is the short-circuit signal. Passages with `fired: false (all three)` add a row to the §3.3.3 telemetry log under category `H_PREFILTER_SHORT_CIRCUIT` for ongoing calibration of probe sensitivity.

**Output stub:**

```
### Register pre-filter (Sub-check H)
- Passages in scope: <count>          # pre-filter scope under resolved register_class
- register_class_resolved: <technical | mixed | non-technical>
- Bundles emitted: <count>
- Short-circuit (no probe fired): <count> / <passages>
- Probe firings:
  - Nominalisation density: <count fired>
  - Prepositional-phrase run length: <count fired>
  - Hedging density: <count fired>
- Per-passage detail (fired-only):
  - <passage role + heading_path>: nom=<n>/<wc>=<r> [thr 0.08] fired=<bool>; prep_run=<n> [thr 3] fired=<bool>; hedge=<n>/<per100> [thr 2] fired=<bool>
  - ...
```

**Rationale.** Sub-check H's full register classification is a judgment pass; running it on every passage when most passages are register-clean is expensive in tokens. §9e mechanises three cheap counter probes so the overlay can short-circuit on passages where no negative-marker signal is detectable. The probes are deliberately permissive (high recall, moderate precision) — false positives at the pre-filter level cost only a downstream judgment pass; false negatives at the pre-filter level cost a missed Sub-check H finding, which is the worse failure mode. This polarity choice is consistent with §9b's coarse-grained-pre-filter precedent.

**Relationship to §9a, §9b, §9d.** §9a = paragraph-internal logical connective integrity (Check 7). §9b = within-paragraph / section-opening reader working-memory load (Check 8 Sub-checks A/D/E + F). §9d = manuscript-scale consolidation at structural boundaries (Check 8 Sub-check G). §9e = passage-scale register quality (Check 8 Sub-check H). The four pre-filters are orthogonal scales (sentence-pair, paragraph, manuscript, passage); all feed the safeguard layer. The passage scale is distinct from the paragraph scale because Sub-check H's passage roles (signposts, framing prose, inter-section transitions, vignette bodies, consolidation anchors) are sub-paragraph or paragraph-set units rather than full paragraphs.

**v0.10.1 advisory-until alignment.** Per v0.10.1 spec, Sub-check H ships under `advisory_until: H_two_revision_cycles`. §9e inherits the same advisory framing — its bundle is recorded but does not gate §3.3.3 verdicts during the advisory period. Once H retires the flag (per the v0.10.2 retirement-decision plan doc), §9e's findings join the aggregate identically. The probes themselves do not need a flag-retirement event; their thresholds are static defaults documented above.

**Future calibration (deferred to v0.10.3+).** Three calibration paths are open after the first H advisory cycle yields aggregator data: (i) re-tune nominalisation threshold from 0.08 to a corpus-empirical value; (ii) re-introduce `-ing` suffix with participial-form filter; (iii) implement per-project hedge-list override mechanism. None is required for v0.10.2 substrate; all are flagged in `docs/superpowers/plans/2026-04-27-h-quantitative-thresholds.md` for forward-looking adjudication.

---

## 10. Output format (what Step 0a emits)

After running the checks above, emit this block into the findings report:

```
## Deterministic check results

**File:** <path>
**Lines:** <count>
**Paragraphs:** <count>

### Counts
- em-dashes (`---`): <n>                      [threshold: ≤ 1 pair per paragraph]
- em-dashes nested: <n>                       [threshold: 0]
- "not X but Y": <n>                          [threshold: ≤ 2]
- absolutes (must|cannot|comprehensiv|anticipat): <n>
  - `must`: <n> at lines <...>
  - `cannot`: <n> at lines <...>
  - `comprehensiv*`: <n> at lines <...>
  - `anticipat*`: <n> at lines <...>
- there is / there are / there remain: <n>
- reveals / exposes / proves: <n>
- "standard <noun>": <n>
- "first-class" used: <n>
- hedged paragraph-start transitions: <n>/<total paragraph breaks>
- sentences > 60 words: <n>
- avg sentence length: <words>
- [REF to be verified] placeholders: <n>

### Stage-specific flags (if P0 or P1)
- P2 vocabulary in conclusion: <y/n; locations>
- Numbered RQs in §1: <y/n; locations>

### Verdict
- BLOCKERs from this pass: <n>
- MAJORs: <n>
- MINORs: <n>
- Pass / Fail (pass = 0 BLOCKERs; judgment pass can proceed)
```

---

## 11. Relationship to judgment-based review

A piece that **passes** all checks in this file may still fail the judgment-based review — these checks catch measurable tics, not structural problems. A piece that **fails** these checks almost certainly has structural issues as well, because writers who tolerate em-dash sprawl and absolute language often also tolerate defensive framing and deficit comparisons.

**Rule of thumb.** If a piece fails §2 (absolutes) or §4 (LLM tics) at high density, do not proceed to judgment-based review until those are fixed. They pollute the reviewer's attention budget.

---

## 12. Maintenance

When a new mechanical rule is added to any component file (MASTER, playbook, Bacon, etc.), record it here with its pattern, threshold, and severity. Without this, joint reviewers re-derive the same regex each time. The overlap map in `REVIEW_ORCHESTRATION.md` §5 should also be updated to point at this file as the authoritative location for the new check.

---

*This file is the mechanical counterpart to `REVIEW_ORCHESTRATION.md`. Run it first; trust but verify.*
