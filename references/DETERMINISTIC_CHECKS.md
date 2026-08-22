# DETERMINISTIC CHECKS — Mechanical Pre-flight for Academic Prose

> Reader-accessibility numerics are loaded from `references/policies/reader_accessibility.v1.json`; the named keys (`thresholds.cadence`, `thresholds.rhythm`, `thresholds.jargon`, `thresholds.consolidation`, `thresholds.register`) are authoritative. All Check 8 outputs below are **proxy candidate** signals for overlay/Evaluator judgment, never normative semantic predicates.

**Purpose.** This file collects every rule in the package that can be checked **mechanically** — by grep, count, or regex — rather than by judgment. Run these **first**, before any judgment-based review (Step 0a in `REVIEW_ORCHESTRATION.md`). They take minutes and catch the measurable tics that burn reviewer attention.

**When to run.**
- **Always**, as Step 0a of any review, regardless of depth.
- **Re-run after edits** (Step 9 of submission-bound review) to confirm fixes landed and no new tics slipped in.
- **Before committing** any AI-assisted draft or revision (humanness pass per MASTER §A.4.2).

**Scope.** These checks do **not** replace judgment-based review. They are a floor: if a piece fails these, the judgment-based review will also fail. Passing these is necessary but not sufficient.

**Release-history integration.** Qualification keeps separate evidence
for shipment-v2 membership, completeness diagnostics, static output-economy,
and versioned replay; it grants no downstream or research authority.

## 0. Mechanics pre-flight and governed product gate

`scripts/audit/run_all.py` is the mechanics/compatibility surface. Its output is
diagnostic and never satisfies a product or lifecycle gate, including when the
legacy `--semantic-receipt` option is supplied:

```powershell
python scripts/audit/run_all.py "<manuscript>" --project-root "<project-root>" --date "YYYY-MM-DD" --out "<authorized-shipment>/findings.json"
```

For lifecycle-eligible product evidence, validate the exact committed Evaluator
transaction through the governed adapter. Missing semantic or verifier evidence
fails closed; the marker-last run manifest records checks, hashes, runtime
versions, omissions, outputs, recovery command, and terminal state:

```powershell
python scripts/run_product_gate.py --mode governed-product --project-root "<project-root>" --artifact "<manuscript>" --out-dir "<authorized-run-lane>" --check semantic-product-verifier --wiki-root "<wiki-root>" --semantic-receipt "<evaluation-semantic-receipt>" --verifier-transaction "<evaluation-verifier-transaction>" --verifier-publication-manifest "<evaluation-publication-manifest>" --verifier-commit-marker "<evaluation-commit-marker>"
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

## 0a. Product-assurance checks

When `--semantic-receipt` is supplied to `run_all.py`, the compatibility path
runs the product-assurance kernel and merges its findings into `findings.json`
while preserving a separate exact-byte diagnostic report. These checks operate on the bound
member extracts, not on a generic dictionary:

| Check | Signal | Gate behavior |
|---|---|---|
| `QUOTE-NOT-IN-EXTRACT` | normalized verbatim quote absent from canonical extract | hard failure |
| `CITATION-SAME-YEAR` | quote-local suffix disagrees with source title/label mapping | hard failure |
| `TERM-COINAGE` | compound term absent from bound extracts after narrow lemma and hyphen/space sequence matching, and not owned by the sentence containing `[S]` | Evaluator candidate |
| `REGISTER-ABSENT` | high-frequency manuscript lemma absent from bound extracts | Evaluator candidate; separate from grounding |
| `INSIDER-NEGATION` | an explicit Markdown Abstract section negates a reader term before introduction | Evaluator candidate |
| `EMPIRICAL-UNSUPPORTED` | a sentence-level frequency/tendency generalization lacks a parenthetical or narrative author-year citation and lacks `[S]` ownership in that sentence | Evaluator candidate |

PDF evidence is canonical only when produced by `scripts/source_extract.py`
with `pdftotext`. Generation may surface semantic candidates; evaluation must
dispose each current code/locator pair with a rationale. Hard evidence failures
cannot be waived. Candidate fingerprints bind the detector version, exact span,
and candidate text, so an adjudication from an older detector remains stale.
This preserves human adjudication for contestable synthesis without allowing
silence to count as clearance.

## 0b. Qualification controller and planes

The shared environment policy refuses ambient routing, warning, UTF-8, and
optimization controls before spawn. The durable controller records intent,
process identity, binary output, exit capsule, atomic journal, and terminal
receipt; `status`, `wait`, `cancel`, and `recover` do not rerun the product.
Topology preflight requires isolated `source`, `build`, `archive`, `unpacked`,
and `installed_cache` planes before runtime suites. The controlled gate binds
clean `main` before its corpus and refuses source drift afterward. Missing
cache authority leaves topology pending.

```powershell
python scripts/release_qualification_controller_smoketest.py
python scripts/qualification_plane_topology_smoketest.py
python scripts/runtime_plane_probe_smoketest.py
python scripts/archive_runtime_probe_smoketest.py
```

`token_budget_smoketest.py` is retired (removed with `token_budget_check.py`).

Runtime receipts distinguish exact files, permitted CRLF transformations,
semantic differences, missing files, and foreign extras. Cache equality is
runtime evidence only, never startup or loaded-path attestation.

The package-root behavioral corpus is still
`python scripts/analysis/fixture_runner.py --no-write` (committed suite time
about 111.5 minutes). A changed area may run a `REGISTRY` subset with
`python scripts/analysis/fixture_runner.py --suite <key> --no-write`. `--suite`
is not release qualification. Path-to-check routing:
`docs/agent-instructions/change-to-check-map.md`.

## 0c. Release archive and evidence publication

The release helpers fail closed on unsafe archive members, noncanonical
checksums, stale evidence bindings, replacement of immutable indices, and
manual drift between the authoritative plugin manifest and packaged
marketplace parity:

```powershell
python scripts/archive_runtime_probe_smoketest.py
python scripts/write_release_checksum_smoketest.py
python scripts/release_evidence_index_smoketest.py
python scripts/update_version_manifests_smoketest.py
```

`archive_runtime_probe.py` inspects the complete central directory before
extracting into a new temporary root and runs the bundled runtime probe with
isolated imports. `write_release_checksum.py` publishes exactly one lowercase
SHA-256, two spaces, the final ZIP basename, and LF, then re-reads both files.
`release_evidence_index.py` binds repository-relative paths to live SHA-256
bytes and writes immutable package and release indices; the human shipment
report is rendered from the final index. `update_version_manifests.py` is the
command-driven path for advancing authoritative `version.json` and the
published root `plugin.json` identity mirror together.

## 0d. Synthetic protocol conformance

`scripts/protocol_conformance_smoketest.py` records a synthetic M1-to-FINAL
assignment through the production receipt, claim, verifier, mutation,
milestone, handoff, and terminal authorities. It uses the committed
self-authored miniature PDF and exercises quotation, conditioning, product
candidate adjudication, and targeted tamper refusals. Its
`protocol_conformance` result proves executable protocol coverage only: it does
not claim human-quality semantic judgment or host-attested separate agents.

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

**H-motivated em-dash insertion (named false-fix pattern).** When applying H's register-shift signposting marker, the Generator may default to an em-dash as the vehicle. This can satisfy the marker while opening an em-dash regression. Prefer semicolons for contrast bridges, colons for specification pivots, or explicit cue phrases. Verify the result against the em-dash rule in this document rather than restating its numeric threshold here. Cross-reference: `references/lay_term_lexicons.md` register-shift guidance and `skills/accessibility-overlay/references/sub_checks.md` H procedure.

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

## 4b. Register dispersion (B4–B7) — proxy candidates only (added 2026-08-21)

§4 above counts *patterns*; §6 below measures *central tendency*. Neither measures
**dispersion** — and a manuscript can sit dead-on every average while reading as
machine-generated because its sentences are all the same shape. `scripts/register_dispersion_check.py`
covers that gap. It is read-only (it writes no files, so it is not a census writer
under `destination-coverage-check.py`).

```bash
python scripts/register_dispersion_check.py <file> [--baseline <accepted-prose>] [--json]
```

| Rule | Signal | Status |
|---|---|---|
| **B4** | Coefficient of variation of sentence length ("burstiness") | Measurement; finding only vs. `--baseline` |
| **B5** | Rate of pre-predicate interrupting material (proxy for subject–verb distance) | Measurement; finding only vs. `--baseline` |
| **B6** | Content-word overlap between a paragraph's first and last sentence (circular closure) | MINOR at ≥ 0.35 |
| **B7** | "Nuanced"-family complexity claim the sentence never discharges | MINOR per instance |

### Calibration record (binding on how these may be cited)

The pattern inventory was prompted by a popular-audience video on AI writing tells
(*Nail It With AI*, "7 Hidden AI Writing Tells," 2026-02-12). **That source's numbers
are not in this package.** It attributes burstiness bands, detector accuracies, and
corpus percentages to unnamed or unverifiable studies; `GROUNDING_PROTOCOL.md` is
absolute, so none of them may be repeated as findings. What follows is local
measurement, run 2026-08-21, and is falsifiable by recalibration.

Corpus: 4 LLM-authored memos under `docs/analysis/` vs. 3 human-authored craft and
scholarly sources under `references/` (Abbott, Suchman, Bacon).

| | B4 rhythm CV | B5 interruption rate |
|---|---|---|
| LLM-authored | 0.602 – 0.683 | 0.304 – 0.615 |
| Human-authored | 0.437 – 0.623 | 0.382 – 0.541 |

**The ranges overlap and the direction is inverted.** The LLM sample scored *more*
varied, not less. The low-burstiness-implies-machine claim did not replicate. An
absolute low-CV threshold would have flagged Bacon's own published sentence-craft
guide (CV 0.437) as machine-generated.

Two consequences, both binding:

1. **B4 and B5 carry no absolute threshold.** They are reported as measurements and
   fire only as a within-author delta against `--baseline`. The current local
   sensitivity convention is explicit: a candidate fires when the draft statistic
   is below **0.75 ×** the corresponding author-baseline statistic (B4 CV or B5
   interruption rate). This is also what C-7 requires: the author's own prose is
   the yardstick, never a population constant. Do not change the `0.75` ratio or
   introduce a population band without rerunning this calibration on a larger
   corpus and recording the result here.
2. **B6 and B7 survive as detectors** because they measure a *local* property of the
   text rather than a population comparison. B6 separated cleanly — across 48
   qualifying paragraphs in both corpora the observed maximum overlap was 0.250 and
   the 90th percentile 0.067, while a constructed circular paragraph scored 0.444;
   0.35 sits in the empty band. A sweep across five human-authored reference works
   produced zero findings.

Two of the video's seven tells were **rejected outright** rather than implemented.
Its "low perplexity" remedy (take creative risks, use idioms and colloquialisms,
be surprising) is a register prescription that collides with C-7's prohibition on
imposing a borrowed register, and the source itself concedes the measure misfires on
formal prose. Its "synonym cycling" tell is already owned as judgment by C-6 and by
Baird's terminology rule; a mechanical detector would duplicate that jurisdiction.
The remaining tell, temporal vagueness, is not a style defect at all — an undated
"recent studies show" is a citation failure, and it belongs to §7 and
`CITATION_DISCIPLINE.md`, where it is now enforced.

All B4–B7 outputs are **proxy candidates for Evaluator judgment, never normative
semantic predicates** — the same status the reader-accessibility prefilters carry.

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
| **Temporal vagueness on an evidential claim** (added 2026-08-21) | `\b(recent(ly\|\s+(studies\|work\|research\|years))\|in\s+recent\s+years\|nowadays\|the\s+modern\s+era\|contemporary\s+approaches\|traditional\s+methods\|increasingly)\b` | per file | Each hit requires judgment | **MAJOR** when the sentence asserts an evidential claim (a study, trend, or finding) with no date, date range, or citation carrying one; MINOR otherwise | Supply the actual period or the citation that dates it. "Recent studies show" is not a style tic — it is an undated evidential claim, and the reader cannot ask *which* studies or *when*. Prefer a named year, a range, or a dated citation. If the date is unknown, look it up rather than hedging. |
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

**The package's operational axis convention and exact-source boundary live in `GROUND_TRUTH.md`.** The patterns below are candidate-producing package heuristics, not transcriptions of an external workbook and not evidence of exact EYgp conformance.

| Rule | Pattern | Stage where flagged | Severity | Fix hint | Package-convention basis |
|---|---|---|---|---|---|
| P2 vocabulary in a P0/P1 conclusion | `\b(resolution|resolves|answers|research question|RQ\d)\b` in conclusion section | P0 or P1 | MAJOR | Use "refined problem statement," "open questions," "candidate q-items." | The package convention reserves committed research problems/questions and answer claims for P2; tokens remain review candidates, not source-verified violations. |
| "Not X but Y" in P0/P1 positioning sentences | see §4 above | any stage | MAJOR if density | As §4. | Out of scope (prose-style rule, not an axis definition). |
| Premature numbered RQs in §1 | `\bRQ[\d]+\b` or `\bq[0-9]+\b` in §1 of a P0/P1 paper | P0 or P1 | **BLOCKER** if the piece is P0/P1 | Restate as problem phenomenon + characterization lenses. | The package convention uses numbered or q-labeled items as a P2 commitment signal. |

### 8a. Research-process vocabulary pre-filter (all axes)

This sub-section is a **pre-filter**, not a pass/fail check. It raises candidates for the package research-process review lane (formerly the `eygp-framework-checker` skill, SK-28 — retired at v0.7.0 with stubs removed; SK-10 `p-stage-checker` covers the P-axis subset). It cannot establish exact advisor-specific conformance without a lawfully supplied project-local source.

| Marker class | Pattern | What to emit |
|---|---|---|
| Any axis-stage label | `\b(P[012]|R[012]|K[012]|S[1-5]|T[1-5]|V[0-5])\b` | file:line + matched label + one sentence of surrounding context |
| Readiness tick | `[✓]{1,5}` (Unicode check marks) or `\b\d+%?\s*(ready|-tick)\b` | file:line + matched text |
| Artefact-genre phrase tied to a stage | `\b(technical\s+(sketch|outline|note)|working\s+paper|published\s+paper)\b` | file:line + matched phrase (candidate mapping under the package convention) |
| Thesis-chapter phrase tied to a stage | `\b(Bib|Motivation|Research\s+Objectives|Related\s+work|Contributions|Background\s+on\s+subject-matter\s+area|Solution\s+chapters|Tools\s+chapter|Validation\s+chapter)\b` | file:line + matched phrase (candidate context only) |

**Emission rule.** Every match adds one candidate location to the pre-filter's candidate queue (formerly the `eygp-framework-checker` work queue; skill retired at v0.7.0). A location may match multiple markers; aggregate them.

**Output stub:**

```
### Research-process axis pre-filter
- Axis-stage labels found: <n>
  - <file:line>: <P1 | S3 | ...>
- Readiness-tick claims found: <n>
- Artefact-genre phrases: <n>
- Thesis-chapter phrases: <n>
- Candidate locations (axis pre-filter): <total unique>
```

**Scope.** This pre-filter is run on any artefact under review (manuscript, classification record, project memo, revision plan). It does **not** modify §8 severities — those remain the package's prose-style rules. It only produces a queue for the cross-axis framework check.

**Rationale.** When a manuscript or plan mentions `S3` or a readiness tick, the verifier should locate the claim mechanically and decide whether it matches the package convention. Exact tick conversion or EYgp wording remains unavailable unless the project supplies the controlling source. See `GROUND_TRUTH.md` for this boundary.

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

This block is a **pre-filter**, not a pass/fail check. It produces candidate locations for judgment review under the reader-experience audit. Archived external-review evidence identified unowned sentence architecture, definition topology, prose cadence, and list-in-disguise patterns; the profile now owns their numeric predicates.

| Marker class | Pattern | What to emit |
|---|---|---|
| Long-subject / late-verb sentence | Any sentence where the first finite main-clause verb appears > 20 words from sentence start. Heuristic proxy: sentences with a subordinate clause (`,\s*(which\|that\|who)\b` or `,\s*including\b`) within the first 20 words **and** total length > 30 words | sentence locator + word-count-to-first-verb |
| Stranded definition block | In LaTeX: any `\textbf{[^}]+\.}` or `\noindent\\emph\{[^}]+\.\}` immediately preceded by `\end{abstract}` or preceded only by section scaffolding and not followed by the term's first substantive use within 3 paragraphs | block locator + defined term |
| Definition after first substantive use | For each formally defined term `\emph{X}` introduced by `By X, I mean` or similar, check whether an unitalicized occurrence of `X` appears earlier in the document. If so, the definition lags its first use | term + first-use line, definition line |
| Unrelieved long-sentence run | Three or more consecutive sentences each > 35 words within a single paragraph, with no sentence ≤ 20 words among them | paragraph locator + sentence-length sequence |
| Rhetorical-question stacking | A single paragraph containing ≥ 3 sentences ending in `?` | paragraph locator + question count |
| Triadic enumerator (mechanized) | `\bFirst,\b[\s\S]{20,400}?\bSecond,\b[\s\S]{20,400}?\bThird,\b` OR three semicolon-chained parallel clauses in a single sentence (see §4 existing pattern, elevated from manual to mechanized) | passage locator + enumerator spans |
| Overclaiming verbs, expanded scope | `\b(reveal\|reveals\|revealing\|expose\|exposes\|exposing\|prove\|proves\|demonstrate\|demonstrates)\b` applied to the paper's own analysis (subject = the materials, the analysis, this essay, the evidence) | per-hit line + subject |
| **Paragraph cadence candidate** (feeds Check 8 A) | Apply `thresholds.cadence`: emit word count and cue-lexicon hits for paragraphs entering a nonzero turn-point band. A cue is a candidate, never an automatic credit; the overlay functionally confirms it. | paragraph locator + word count + candidate cues + `overlay_confirmation_required` |
| **Section-transition preamble absence** (feeds Check 8 Sub-check D) | For every section or subsection heading, inspect the profile-bounded opening under `thresholds.section_signpost`. Flag if it lacks an orienting clause, a contribution clause, or the required opening geometry. A section that dives directly into dense theoretical prose with no signpost is the "cold-open" pattern | section heading locator + missing-clause types |
| **Jargon density per paragraph** (feeds Check 8 Sub-check E) | Count new domain terms and compare against the resolved profile's P-stage candidate cap. | paragraph locator + term count + listed new terms + resolved cap |

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
- Paragraph cadence candidates under `thresholds.cadence`: <count>
- Section-transition preamble absent: <count>                # new v0.7.2
- Jargon density exceeded under resolved P-stage predicate: <count>
- Candidate locations for Check 8 Sub-check A (cadence): <count>
- Candidate locations for Check 8 Sub-check D (signposting): <count>
- Candidate locations for Check 8 Sub-check E (jargon density): <count>
- Candidate locations for Check 8 (all sub-checks, total unique): <count>
  - §X, line Y: [markers matched, sub-check codes]
  - ...
```

**Rationale:** Archived INF3001H review evidence reached a readiness verdict while reader-ergonomics defects remained. The defects were unowned axes rather than tracked rule violations. This pre-filter nominates them for judgment without preserving the historical counts as policy.

**Relationship to §9a.** §9a targets *paragraph-internal logical connective integrity* (invisible to mechanical checks, caught by adversarial reading). §9b targets *reader working-memory load within a paragraph or a section opening* (invisible to analytical checks, caught by first-pass reading). The two pre-filters are orthogonal; both feed the safeguard layer. See §9d for the manuscript-scale counterpart that feeds Sub-check G.

---

## 9d. Cumulative cognitive load pre-filter (added 2026-04-23, feeds SAFEGUARD_LAYER Check 8 Sub-check G)

This block is a **pre-filter**, not a pass/fail check. It locates candidate structural boundaries for G at manuscript scope. Its phase eligibility comes from the resolved profile; this prose does not preserve a legacy phase subset.

| Marker class | Pattern | What to emit |
|---|---|---|
| **Boundary gap — word count since last major heading** | Compute the body-word span for each major Markdown or LaTeX heading and compare it with `thresholds.consolidation.candidate_gap_words` for the resolved P-stage. | boundary locator + preceding-span word count + resolved threshold |
| **Boundary gap — paragraphs since last major heading** | Count paragraphs in the span and apply `thresholds.consolidation.candidate_gap_paragraphs` together with the P-stage word envelope. | boundary locator + paragraph count |
| **Consolidation-cue density before a major heading** | Scan the pre-heading paragraph window owned by `thresholds.consolidation.pre_heading_scan_paragraphs` for the consolidation-cue lexicon. Record the match count without restating the window size here. | boundary locator + cue count |
| **Consolidation-cue density in the opening paragraph of a new major section** | For the opening paragraph of each major section, scan for the same consolidation-cue lexicon plus the backward-reference lexicon from §9b Sub-check D (`\b(having\|after\|so far\|in the preceding\|this section\|the previous section\|up to this point)\b`). A single match counts whether from either lexicon; the point is backward consolidation, not the form | boundary locator + cue count (0 or ≥ 1) |
| **G-candidate boundary** (synthesis marker) | A boundary qualifies as a Sub-check G candidate when the preceding-span word count exceeds the resolved P-stage envelope and consolidation cues are absent from both the profile-sized pre-heading window and the next section's opening paragraph. | boundary locator + preceding-span word count + cue-absence confirmation |

**Emission rule.** Every G-candidate boundary adds a row to the Check 8 Sub-check G work queue. The deterministic layer emits a candidate; the judgment layer applies the semantic criterion at `READER_ACCESSIBILITY.md §13.3 G` and the numeric predicates from `thresholds.consolidation`. Cue matches alone do not clear the boundary.

**Output stub:**

```
### Cumulative cognitive load pre-filter (Sub-check G)
- Major headings scanned: <count>
- Boundary gaps exceeding P-stage envelope (words): <count>
- Boundary gaps exceeding profile paragraph-gap predicate: <count>
- Pre-heading windows without cues: <count>
- Zero-cue section-opening paragraphs: <count>
- G-candidate boundaries (both gap-exceeded AND zero-cue): <count>
  - <boundary locator>: preceding-span wc=<n>, para count=<n>, pre-heading cues=<n>, opening cues=<n>
  - ...
- Manuscript word count total: <n>
- Manuscript envelope result under `thresholds.consolidation`: <resolved result>
```

**Rationale.** The archived INF3006Y calibration surfaced repeated major-section boundaries with no consolidation cues even though the new arguments depended on prior material. The local pre-filter saw nothing because each paragraph was individually clean. This probe elevates nomination from the paragraph to the section boundary, paralleling the scale shift from the local Sub-checks to G. The pre-filter remains intentionally coarse; the judgment pass may reclassify a candidate boundary when the span does not actually cross the profile-owned construct-accumulation predicate.

**Relationship to adjacent pre-filters.** The logical-connective, within-paragraph, and manuscript-scale consolidation probes operate at orthogonal scales and feed the safeguard layer.

**P-stage adjustment.** Read the current P-stage envelope from `thresholds.consolidation.candidate_gap_words`. This prose records rationale but owns no numeric threshold.

---

## 9e. Register pre-filter (added 2026-04-27, feeds SAFEGUARD_LAYER Check 8 Sub-check H)

This block is a **pre-filter**, not a pass/fail check. It nominates passage evidence for Sub-check H using the resolved reader-accessibility profile. Phase scope, thresholds, and severity are not owned here.

§9e operates at the resolved passage scope in `register_scope` and `sub_checks.H`. Its workflow effect comes from the bound H transition state, never a prose advisory flag.

| Marker class | Pattern | What to emit |
|---|---|---|
| **Nominalisation density** | Count profile-defined suffix candidates, apply domain-token exclusions, and compare the normalised result with `thresholds.register.nominalisation_density_candidate`. | passage locator + raw count + normalised value + resolved threshold + fired flag |
| **Prepositional-phrase run length** | Longest consecutive run under the resolved `lexicons.prepositions`; firing threshold comes only from `thresholds.register.prepositional_run_candidate`. | passage locator + run length + run span + profile threshold + fired flag |
| **Hedging density** | Resolve the hedge lexicon, override polarity, and threshold from the active profile. | passage locator + raw hedge count + words + normalised ratio + resolved threshold + fired flag |

**Exclusion-list rationale for nominalisation suffix `-ing`.** The `-ing` form is doubly ambiguous in academic prose: it serves as participial verb (an active form), gerund-noun (a content-bearing nominal), and progressive aspect (still verb-anchored). Including `-ing` in the suffix probe inflates false-positive rates by ~30% in pilot probing on the v0.10.0 INF3001H Round 7 corpus, mostly on participial constructions ("having traced the dependencies", "applying the framework"). The five remaining suffixes (-tion / -ment / -ance / -ence / -ity / -ness) are unambiguously nominal. Future v0.10.3 calibration may re-introduce `-ing` with a participial-form filter; the current probe ships without it.

**Output contract per probe.** Each probe emits a tuple `(probe_name, raw_count, normalised_value, threshold, fired: bool)`. The pre-filter bundle is appended to the passage's overlay-input record under field `prefilter_h_bundle`. A clear negative pre-filter may skip negative-marker elaboration, but it never implies `NULL/CLEAN`: the overlay always performs the positive-marker audit required by `runtime_modes.stability.negative_prefilter_short_circuit` and Sub-check H.

**Emission rule.** Each passage in scope emits a bundle regardless of whether a negative-marker probe fires. The aggregate `fired` boolean is telemetry for elaboration only; it cannot suppress positive-marker evaluation or rewrite a semantic verdict.

**Output stub:**

```
### Register pre-filter (Sub-check H)
- Passages in scope: <count>          # pre-filter scope under resolved register_class
- register_class_resolved: domain-native
- passage_scope_class_resolved: <technical | mixed | non-technical>
- Bundles emitted: <count>
- Negative pre-filter clear (positive-marker audit still required): <count> / <passages>
- Probe firings:
  - Nominalisation density: <count fired>
  - Prepositional-phrase run length: <count fired>
  - Hedging density: <count fired>
- Per-passage detail (fired-only):
  - <passage role + heading_path>: <profile-keyed probe values, resolved thresholds, and fired booleans>
  - ...
```

**Rationale.** Sub-check H's full register adjudication is a judgment pass. §9e supplies permissive candidates; the overlay remains the functional judge.

**Relationship to §9a, §9b, §9d.** These pre-filters cover orthogonal sentence-pair, paragraph, manuscript, and passage scales; all feed the safeguard layer. The passage scale remains distinct because H's profile-owned roles can be sub-paragraph or paragraph-set units rather than full paragraphs.

**Transition alignment.** §9e reads `transitions.H` and the matching policy-binding event stream. Probe thresholds are profile keys; retirement requires the profile count and Planner approval evidence.

**Calibration.** Proposed threshold or lexicon changes must update the profile and its tests. Operational prose cannot activate future values.

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
- B4 rhythm CV: <value | not computed>          [finding only vs. author baseline]
- B5 interruption rate: <value | not computed>  [finding only vs. author baseline]
- B6 circular paragraphs: <n; paragraph locations>
- B7 undischarged complexity claims: <n; sentence locations>
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
