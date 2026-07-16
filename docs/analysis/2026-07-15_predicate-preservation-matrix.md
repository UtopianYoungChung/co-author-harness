# Predicate-Preservation Matrix — v0.29.0 → v1.0 (v2)

**Date:** 2026-07-15 · **Supersedes:** v1 of this file (rejected, review 2026-07-15 #2)
**Status:** ⚠️ **PROPOSED. Unsigned.**
**Rows:** generated — `docs/analysis/generated/predicate_rows.md`. This file is the *policy layer*; it contains no rows.
**Parity gate:** `python scripts/analysis/code_census.py --parity docs/analysis/generated/predicate_rows.md`

> **Every number in this file is a dated OBSERVATION, not an assertion.** Read `[obs 2026-07-15]` as "the script reported this on that date"; re-run to get the current value. Nothing here is authority.
>
> The previous revision announced "no prose asserts a count" and then asserted `65`, `242`, and `258` repeatedly — **in the same document, immediately after.** Two rounds before that, two reviewers quoted two different stale hashes (`9A24CAA0…`, `b9cf36c8…`) from prose while the script moved underneath. That is the `version_planes.json` snapshot-freeze antipattern reproduced by the document meant to replace it, twice.
>
> The rule that actually works is not "never write a number" — a design doc has to describe its subject. It is: **no number here is load-bearing.** Authority is `script_sha256` + counts stamped into the generated file's header at generation time. A gate reads the generated artifact; a human reads this and re-runs.

> **Rows are CANDIDATE predicates, not proven ones (review #4).** A site may be a diagnostic rather than a transition predicate, one branch of a helper whose real condition lives elsewhere, a code-table entry shared by several conditions, or a wrapper around another predicate. Site granularity is *safer* than label granularity; it is not *sufficient*. The generated rows are the **adjudication queue** — parity PASS proves **coverage**, never **preservation**.

---

## 0. What v1 got wrong

**v1 counted 70 code labels and called them predicates.** A label is not a predicate:

| Code | Emission sites |
|---|---|
| `MF-EXEMPLAR` | **37** |
| `MF-POLICY` | **30** |
| `MF-EVENT` | **22** |
| `APG-RECEIPT-INVALID` | **16** |
| `APG-WIKI-GROUNDING-STALE` | **14** |
| `MF-HANDOFF` | 13 |
| `E-ROW-SHAPE-VIOLATION` | 12 |
| `MF-PHASE` | 12 |

One row per label preserves the **name** while deleting most of the **judgment**. This is the census error one level up: v1 fixed *how many labels* and left *how many rules* uncounted.

`[obs 2026-07-15: 65 code labels → 242 production emission-site CANDIDATES.]` Not "242 predicates" — that phrasing (v3's) begs the question the adjudication exists to answer. A site is a candidate; whether it carries a predicate is §0's open question.

**v1's census scope was also wrong.** It hardcoded three emitters. Discovery finds **six**, including `assignment_dispatch_preflight.py` (the required dispatch preflight — emits `APG-RECEIPT-TARGET-MISMATCH` at `:63`, absent from all 70 v1 rows) and `phase_notifications_loader.py` and `render_lifecycle_state.py`, which no prior document mentions at all.

**Consequence, measured:** the v1 matrix scores **0 / 242** on parity. It covered none of the actual predicates.

---

## 1. Rows are generated, not written

A hand-written table cannot track 30 `MF-POLICY` branches, and v1 proved it. Rows come from the census:

```bash
python scripts/analysis/code_census.py --emit-matrix > docs/analysis/generated/predicate_rows.md
python scripts/analysis/code_census.py --parity docs/analysis/generated/predicate_rows.md
```

### 1.0 Row identity — deterministic, not durable

> **The scheme guarantees injectivity, not durability, and calling it "durable" was overclaiming.** Inserting an *identical sibling before* an existing site renumbers that site's ordinal — so the ID of an already-adjudicated row can change without that row's own predicate changing. Three honest options, none free:
>
> | Option | Cost |
> |---|---|
> | **Freeze emitters during adjudication** (recommended) | no upstream edits to the 6 emitter files until the queue is worked |
> | Call it deterministic and re-key on regeneration | overlay must be re-matched after any emitter edit |
> | Introduce explicit stable site keys | requires touching every emitter to add a key |
>
> The generated header now says **DETERMINISTIC, not durable**, and names the freeze requirement. This is a real constraint on scheduling: **adjudication and emitter edits cannot proceed in parallel.**


**Row identity is `code@module:function#asthash~ordinal`.** `file:line` is a **locator**, not identity.

Every component earns its place by a failure:

- **`~ordinal` — because `code@function#asthash` is not injective.** Two identical `_finding("MF-TEST", "same")` calls in one function hash identically and collapse to **one** ID. Parity compares *sets*, so the collision hides a predicate **and still reports PASS**. Verified: 2 sites → 1 unique ID. The ordinal counts prior identical `(code, module, fn, asthash)` tuples in source order; it shifts only when an identical sibling is inserted before it — which genuinely is a new predicate needing adjudication.
- **`module:` — because two files may share a function name.**
- **A hard uniqueness assertion at generation time**, because an ID change *after* adjudication invalidates every human overlay row. `_assert_injective()` raises rather than generating a collided set.

Two more reasons the locator cannot be identity, both learned by getting it wrong:

- **`file:line` collides.** A conditional emitter — `Finding(code="E-MISSING-T1-SIGNOFF" if prior == "T1" else "E-ARTEFACT-MISSING")` at `scripts/pre_phase_advance_check.py:431` — is **two predicates on one line**. v2's generated Row column keyed on `filename:line` and produced 242 rows with **241 unique IDs**; `pre_phase_advance_check:431` appeared twice. (The prose claimed `file:line:code` while the generator emitted `file:line` — the prose and the code disagreed, again.)
- **`file:line` is unstable.** Insert an unrelated line above a site and every row below it changes identity, so a no-op edit looks like a wholesale predicate turnover. An AST hash survives line moves and changes only when the expression changes — which is exactly when re-adjudication *should* be forced.

### 1.1 Fixture rows are generated too

### 1.1 Fixture coverage — NOT IMPLEMENTED, and no longer faked

Two false claims, in successive revisions:

- **v2:** asserted the 16 fixture sites were rows while `emit_matrix()` and `parity()` iterated production only. Coverage claimed, not implemented.
- **v3:** generated 16 "fixture cases" from AST code literals and parity-scored them **258 = 242 + 16**. Also false. **Those 16 are code-emission call sites — all `MF-EXEMPLAR` — not test cases.**

Why AST discovery cannot produce a regression corpus, at all:

| Defect | Consequence |
|---|---|
| **PASS cases carry no expected code** | `absent_claim_without_registration`, `ledger_analytical_scalar` are invisible to a literal scan — and PASS rows are exactly what makes the corpus falsifiable. *"Every old block still blocks"* is satisfiable by a gate that blocks everything; only PASS cases catch that. **v3's scan systematically omitted the cases that do the work.** |
| **Loops execute many cases from one static site** | one literal ≠ one case |
| **A literal carries no expected outcome** | the script cannot know PASS vs BLOCK |

### 1.2 The suite universe must not be derived from code literals

The deepest instance of this file's founding error, found at review round 5:

> `discover_emitters()` filtered on `STATIC_RE` **before** classifying fixtures. A suite became visible only if it happened to mention a finding code. `[obs 2026-07-15: 11 of 30 suites discovered.]` **A manifest covering "11/11" would have passed while 19 suites — migration, bootstrap, end-to-end, phase-notification, parity — were silently absent.**

A population defined by the thing you are looking for cannot tell you what you are missing. And the omission is not random: **PASS-case suites are exactly the ones with no code literal**, and exactly the ones that make a corpus falsifiable.

`discover_suite_universe()` is now content-blind — every file under `scripts/` matching a fixture marker, no filter, ever. `[obs 2026-07-15: 30 = 27 × *_smoketest.py + 3 × pytest-style test_*.py.]` `report["fixtures"]` survives as a **diagnostic only** and is explicitly marked never-use-as-universe.

### 1.3 Repair (specified, not built)

Each suite emits a manifest at `docs/analysis/generated/fixture_manifest.json`:

```jsonc
{ "cases": [ { "fixture_file": "scripts/milestone_framework_smoketest.py",
               "case_id": "absent_claim_without_registration",
               "expected_exit": 0, "expected_outcome": "READY",
               "expected_code": null } ] }
```

### 1.4 There is no global outcome vocabulary

**My deepest error in this workstream.** I read `MFHP §9` as universal law and applied one contract to 30 heterogeneous suites — then minted `USAGE_ERROR` and `IO_ERROR` as *outcome tokens* when the authority defines them only as **exit categories**. The authority scopes itself in the sentence I skipped:

> `MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md:124` — "Validators and **compatible preflight gates** use:"

Not universal. And the consequence is concrete: `scripts/pre_phase_advance_check.py:1367` is

```python
return 1 if errors else 0
```

**Exit 1 there is a genuine predicate failure**, not a usage error. A global map relabels every historical block in that component as `USAGE_ERROR` — the validator corrupting the corpus it exists to preserve. This is the third time I reconstructed a contract rather than reading it (`PASS iff exit 0`; `PASS`/`BLOCK` vs the real `READY`; now the scope).

**The separation:**

| Universal — every case, every suite | Component-specific — only under a declared contract |
|---|---|
| `fixture_file` · `case_id` | `outcome_contract` |
| `expected_exit` (**exact**, never inferred) | `expected_outcome` (**optional**, valid only under that contract) |
| `expected_code` (exact or null) | |

| Contract | Vocabulary | Exit constrained? |
|---|---|---|
| `MFHP-9` | `READY`·`LEGACY_READY`·`NOT_APPLICABLE`·`MISCONFIGURED` | yes — 0/0/0/4 (`MFHP:126-131`) |
| `PRE-PHASE` | `CLEAN`·`BLOCKED` | **no** — exit 1 = predicate failure, 2 = I/O. Record exactly |
| `EXIT-ONLY` | none | n/a — `expected_outcome` must be null |

### 1.5 The property is **suite-bound manifest consistency** — not case completeness

I named this check "case completeness" for two rounds. It was never that, and the tell is a tautology I shipped:

```
case_count (declared in the manifest)  ==  len(cases) (in the same manifest)
```

**Both sides come from the same file.** I was checking the document against itself and calling the result completeness. A fabricated one-case-per-suite file with correctly computed hashes and arbitrary run ids passes — the same loophole as round 6, with more fields.

**What it proves:** every discovered suite is represented (both directions) · suite bytes are **current** (`sha256` vs disk — a suite edited since its recorded run has not reported on the code being adjudicated) · declared counts match supplied rows · every **case path** is a discovered suite · ids unique, types right, outcomes valid **under their own contract**.

**What it does not prove:** that the rows **exhaust** a suite's cases · that any case ever **ran**. Neither is provable from a document describing itself. They become provable only when a **central runner is the authoritative writer** and its case registry drives execution — the manifest a *side effect of running*, not an artifact someone writes. Until then, completion is **asserted evidence** (trusted-base class *asserted judgment*, per the acquisition contract §3), not fact.

Escalation of one check across five rounds — each version named for something stronger than it proved:

| Round | Named | Actually satisfiable by |
|---|---|---|
| 4 | presence | the word `case_id` in prose |
| 4b | file exists | a 1-case file, 10 suites absent |
| 5 | suite parity | only 11 of 30 suites discoverable |
| 6 | "case completeness" | a manifest naming each suite once |
| 7 | "case completeness" | **still** — the manifest agreeing with itself |
| **now** | **suite-bound manifest consistency** | forging 30 current source hashes + a coherent run — and it still says nothing about execution |

**Verified rejections** (one probe, 34 problems where the prior version raised 2): phantom case for an undiscovered path · duplicate completion record (previously **silently overwrote**, last-write-wins) · empty `run_id` · `PRE-PHASE` `BLOCKED` with exit 0 · mixed `run_id`s · forged `suite_sha256` ×30 · `MFHP-9` `MISCONFIGURED` exit 1.
**Verified acceptance:** 30/30 hash-bound, one `run_id`, including a `PRE-PHASE` exit-1 `BLOCKED` case.
**Exit: 1 → 0 → 1**, measured.

`PRE-PHASE` is now constrained — `CLEAN → 0`, `BLOCKED → 1` (`pre_phase_advance_check.py:1367`). Leaving its table empty "because exit 2 exists" let `CLEAN`/exit-2 and `BLOCKED`/exit-0 through: **unconstrained is not the same as unknown.** Exit-2 paths are I/O and argument failures — not outcomes of that contract; they belong under `EXIT-ONLY`.

`run_id`: one nonempty id shared across the manifest, because **a manifest is the evidence of one run**. Independent per-suite runs would need `suite_run_id` and would reduce the artifact to unrelated receipts.

### 1.6 Bind to the code under test, not the test file

`suite_sha256` binds the run to the **suite**. It does not bind it to the **subject**. Verified hole:

| Step | | Result |
|---|---|---|
| 1–2 | run suites, record manifest | exit **0** |
| 3–4 | edit `milestone_framework_validate.py` (`e65541a4` → `4279d69d`); **suites untouched** | — |
| 5 | re-check | exit **0** ← evidence describing behaviour that no longer exists |

Manifests now carry a **`tested_inputs` snapshot** and parity recomputes it:

```jsonc
"tested_inputs": {
  "mode": "packaging-authority",
  "enumerator": "scripts/package_enumeration.py::enumerate_package_files",
  "pre_sha256":  "<digest BEFORE execution>",   // must equal post
  "post_sha256": "<digest AFTER execution>",    // must equal post == current
  "file_count":  "<derived count>",             // reconciled against current
  "exclude": ["scripts/analysis/"]
}
```

> **No `sha256` field.** An earlier draft carried one; the validator checks only `pre_sha256`/`post_sha256`, so a recorded `sha256` was **decoration that reads as proof** — the same defect as the unenforced `script_sha256` stamp and the unchecked `file_count`. The current digest is checker-local recomputation, not recorded evidence. Every field here is verified or absent.
>
> **`file_count` is `<derived count>`, not a literal.** Hardcoding `450` goes stale the moment any untracked path is committed, since the enumeration is tracked-at-HEAD. Derive it; never transcribe it.

Now: subject mutated → `tested_inputs.sha256 STALE: code under test changed since the recorded run (recorded 719a14b5…, current 8e735773…)`, exit **1**. Restored → exit **0**.

**A git rev would not do.** A dirty worktree carries uncommitted subject changes under a clean-looking commit id — and this entire workstream is uncommitted. The snapshot hashes **content**: sorted `path\0sha256` per file, digested. Sorted → stable across filesystem order; per-path → a rename is a change; content → immune to dirty worktrees.

**Do not author a population that already has an owner.**

Seven populations were invented in this workstream. Every one was an allowlist. Every one was wrong:

| Population | Mine | Truth |
|---|---|---|
| emitters | hand-listed 3 | **6** |
| suite universe | code-literal filtered 11 | **30** |
| tested inputs v1 | `*.py` + schema json = 99 — *"conservative"* | — |
| tested inputs v2 | six-root *"denylist"* = 365 — **still an allowlist** | **450** |

v2 was wrong in **both directions** against `scripts/build-plugin.py`, the authority that decides what ships: it **omitted 87 shipped files** (`README.md`, `CLAUDE.md`, `CHANGELOG.md`, `.github/**`, `docs/**`, `reviews/**`, root config) and **included 2 generated `.plugin` archives the builder explicitly excludes**. Editing an omitted shipped file left evidence "valid"; rebuilding an archive invalidated it. And `release-gate.sh:1127` defines a *third* population.

The lesson is not "write a better list." **The packaging path already owned this question.** The enumeration now lives in `scripts/package_enumeration.py` — a neutral, normally-importable module — and both `build-plugin.py` and the census `import` the same function. `mode: "packaging-authority"`. `[obs 2026-07-15, pre-commit: 450 = 450 against the builder.]`

> **The import must be a plain import.** An earlier revision did `try: from build_plugin_shim import ... except ImportError: <load build-plugin.py by path>` — putting the declared authority in the **except branch**. Creating a file named `build_plugin_shim.py` anywhere on the path would have silently replaced the source of truth, with no warning. **A checker whose authority can be swapped by adding a file is not a checker.** No fallback now: if the import fails, the census dies.

**Scope — stated, not overclaimed.** This closes the `.plugin` upload path only. **`release-gate.sh:1127` still enumerates its own population** for the full-release path, and root governance names release-gate as *the* release path. So **two package populations still exist**, and "drift is impossible by construction" is **false** until release-gate imports the same function. That convergence is an **open blocker**. This is not "the" repo-wide authority and must not be described as one.

**Enumeration from the authority; content from the working tree.** `git ls-tree -r HEAD` answers *which files ship*; it cannot answer *what they say now*. Hashing HEAD blobs would reinstate the dirty-worktree hole. *(No worktree count is quoted anywhere in this file: it moved 8 → 9 → 10 across three review rounds, and a count in prose is a fact with no owner. Run `git status --porcelain`.)*

One subtraction, stated as an exception rather than a filter: `scripts/analysis/**`, because **a subject cannot vouch for its own observer**; the checker is bound separately (§1.7). *Currently a no-op — the checker is untracked, so `ls-tree` never returns it. It goes live on commit, which will also change the derived count.*

### 1.8 ⛔ The extraction shipped a broken artifact

**The refactor that closed the six-root defect broke the bundle, and I called it verified.** Measured against the archive:

```
MEMBERS                            450
HAS_AUTHORITY_MODULE               False   <- scripts/package_enumeration.py absent
ARCHIVED_BUILDER_IMPORTS_AUTHORITY True    <- but build-plugin.py imports it
HEAD_TRACKS_AUTHORITY              False
```

`build-plugin.py` is tracked and now imports `package_enumeration.py`, which is untracked — so the HEAD-based enumeration ships the **importer without its import target**. Running the archived builder raises `ModuleNotFoundError`. **It "passed" only because I ran it from the worktree, where the import resolves.** I verified the wrong artifact: narrow probe, broad claim — the same shape as `head -20` and "worktree clean".

**Second, deeper consequence:** the tested-input digest hashes 450 files while **excluding the module that decides which 450**. The population definer sits outside the population it defines.

**Fix applied:** `scripts/package_enumeration.py` is now in `REQUIRED_FILES`, so the builder **refuses to build** until it is tracked at HEAD. Verified:

```
[ERROR] required files missing from tracked set: ['scripts/package_enumeration.py']
exit=1
```

A build tool must not be able to emit a bundle that cannot run itself.

**Resolved at `e4a23c7`** (branch `codex/assignment-gate-hardening`) — the atomic pair `package_enumeration.py` + `build-plugin.py` committed together. Committing the dependency alone would have made the dirty worktree pass while leaving the commit without its consumer.

Verified from the new HEAD, against the **artifact**:

| # | Check | Result |
|---|---|---|
| 1 | builder exits 0 | ✅ 451 tracked, 451 members |
| 2 | bundle contains `scripts/package_enumeration.py` | ✅ `HAS_AUTHORITY_MODULE True` |
| 3 | archived `build-plugin.py` imports it — *extracted and executed, not grepped* | ✅ imports OK |
| 4 | members == shared enumerator result | ✅ 451 = 451, set-equal, 0 either direction |
| 5 | regenerate + parity | ✅ exit `1`, **solely** the absent fixture manifest |

**The self-reference closed as a side effect:** `tested_inputs.file_count` 450 → **451**, and `scripts/package_enumeration.py` is now *inside its own population*. Before the commit the digest bound 450 files while excluding the module that picked the 450.

### 1.9 Membership is not provenance

**Checks 1–4 proved membership and dependency closure. They did not prove the bundle was an artifact of `e4a23c7`.** It wasn't:

```
reviews/plugin_update_proposals.md
  ARCHIVE_EQ_HEAD      False        HEAD_SHA     421eae8d6462
  ARCHIVE_EQ_WORKTREE  True         ARCHIVE_SHA  b566860d962d
```

The builder takes **paths from HEAD** (`git ls-tree`) and **bytes from disk** (`z.write` at `:174`). So a bundle built from a dirty tree carries uncommitted content under a clean commit's file list — and 451/451 membership passed the whole time, because membership says nothing about bytes.

Worse, I *documented this split as correct*. It **is** correct for the census, where detecting uncommitted subject changes is the entire point. For the builder it silently converts "built from `e4a23c7`" into a claim the artifact cannot support. **The same mechanism is right in one component and wrong in the other; only the claim differs.**

**Verified from a clean detached worktree at `e4a23c7`:**

| Check | Result |
|---|---|
| builder exit | 0 — 451 tracked, 451 members |
| members == enumerator | ✅ set-equal |
| every member byte == HEAD blob | 6 differ |
| …those 6 | **all** carry `<!-- include:` in HEAD, resolved in archive, grew — the builder's *declared* include-rendering |
| **archive == HEAD modulo declared rendering** | ✅ **0 unexplained diffs / 451** |

So `e4a23c7` **is** byte-reproducible; the shipped archive simply wasn't built from it.

**First fix attempt — a dirty guard — was deleted, not repaired.** Check-then-act, with three structural defects:

| Defect | Evidence |
|---|---|
| **fails open** | probe had no `check=True`; git failure → empty stdout → `dirty == []` → concludes CLEAN. Verified: `returncode 128, stdout empty` |
| **mis-parses porcelain** | staged rename `R  old.md -> new.md` → path `"old.md -> new.md"`, intersecting nothing → rename invisible |
| **races** | checks once, reads files later; a file edited between check and `z.write()` ships uncommitted bytes under a clean verdict |
| **provenance lost** | `--allow-dirty` printed to **stderr only** — once the terminal scrolls, a dirty archive is indistinguishable from a clean one |

No parser fixes the race. **The error was the component boundary, not the implementation:**

| | enumeration | bytes | because |
|---|---|---|---|
| **census** | HEAD | **worktree** | detecting dirty subject changes *is* its job |
| **builder** | HEAD | **HEAD** | producing a *commit artifact* is its job |

**Durable fix: the builder materializes HEAD** (`git archive` → temp tree) and reads only from that snapshot — including include targets, since `resolve_includes_in_text` reads them from disk (`resolve_includes.py:73`), so reading HEAD for the outer file alone would still have pulled worktree includes in. A dirty bundle is now **unrepresentable**: nothing to guard, nothing to race, nothing to fail open. `--allow-dirty` is gone — there is no dirty artifact class.

**Verified by building from a deliberately dirty tree:**

```
reviews/plugin_update_proposals.md
  ARCHIVE_EQ_HEAD      True   (was False)
  ARCHIVE_EQ_WORKTREE  False  (was True)
451 members / 0 unexplained diffs — from a DIRTY tree
```

**Automated coverage added** (`scripts/build_plugin_provenance_smoketest.py`, 6 cases, all pass) — the deleted guard shipped with none:

- clean build == HEAD modulo declared rendering (re-runs the rendering; never "6 diffs, probably fine")
- unstaged edit to a shipped file → member == HEAD, probe text absent
- staged edit → member == HEAD, **not index**
- staged rename → HEAD path shipped, renamed path absent
- git probe uses `check=True` (no silent empty result)
- no live `--allow-dirty` escape hatch

Tests restore all mutated state; verified repo-identical before/after.

`release-gate.sh` convergence is the next population blocker.

**A missing enumerated file now BLOCKS.** The prior version silently skipped absent roots and would have produced a smaller, perfectly "valid" snapshot.

### 1.7 Two more bindings the runner must carry

**Pre/post equality.** The runner digests tested inputs **before and after** execution and records both; parity requires `pre_sha256 == post_sha256 == current`. A post-run hash alone cannot detect code that changed *during* the run — the results would describe a mixture of two trees while looking perfectly bound. Verified: `pre != post` → *"the code under test changed DURING the run; results describe no single tree."*

**Checker provenance.** The generated header stamped `script_sha256` and **nothing enforced it** — a changed checker could evaluate a matrix generated by a previous one and report PASS. Since the checker is (correctly) excluded from `tested_inputs`, it must be bound here. Verified: tampered stamp → `CHECKER PROVENANCE: FAIL - matrix was generated by checker deadbeef1234, current is 63a688b00adf`, and production parity fails with it.

> The manifest check is a **file** check, not a text check. My first attempt tested `"case_id" in text and "expected_outcome" in text` and reported `MANIFEST PRESENT` — because the NOT-IMPLEMENTED prose *mentions those words*. A check satisfiable by prose describing the thing is the presence-not-correspondence defect this redesign exists to remove, and it reappeared inside the fix for it.

**Parity scores production only** `[obs 2026-07-15: 242/242]`. Fixture coverage is a declared, blocking gap.

### 1.1 Parity replaces the count check

Per review: **identity, not count.** A count is satisfiable by coincidence — retire one predicate, add another, total unchanged. Parity asserts four things:

| Assertion | Failure meaning |
|---|---|
| every discovered emitter is scanned | census scope gap (v1's bug) |
| every discovered **production** site has a row | **live predicate with no adjudication** |
| every discovered **fixture** case has a row | regression case with no preservation plan |
| every row cites a site that still exists | orphaned row — predicate deleted upstream |
| every discovered code appears | label dropped |

Additions and removals report **by identity**, listed individually. `--check N` is deleted.

**The gate runs under the documented environment.** v2's parity command crashed with `UnicodeEncodeError` on a cp949 console because the heading carried an em dash; every run shown in review was silently wrapped in `$env:PYTHONIOENCODING="utf-8"`. **A gate that passes only under an undeclared override does not pass.** The script now establishes UTF-8 in-process and emits ASCII only.

---

## 2. Dispositions

| Disp | Meaning | Approval |
|---|---|---|
| **KEEP** | same predicate, same semantics, new code name | no |
| **MOVE** | same predicate, different gate | **yes if the target gate runs earlier or more often** (§2.1) |
| **SPLIT** | one predicate → **n** predicates, jointly equivalent | **yes** |
| **CHANGE** | semantics differ on some input | **yes** — must name the input |
| **RETIRE** | deleted; nothing enforces it | **yes** — must name the replacement or declare abandonment |

`SPLIT` is now defined (v1 used it undefined — review #3).

### 2.1 MOVE is not free

Review is right: **moving a predicate to an earlier or more frequently invoked gate changes behavior.** A predicate at G3 fires once at ship; the same predicate at G0 fires every invocation. A project that previously worked for weeks and failed at ship now fails immediately. That may be desirable — it is not *neutral*. A MOVE crossing a frequency boundary is approval-bearing.

### 2.2 Default is KEEP

An unsigned row at implementation is a **BLOCKER**, not a silent retirement. This inverts v1's failure mode, where four live MF codes vanished because a `head -20` truncated the census and nobody had to sign.

---

## 3. Rulings applied

Per review's per-row recommendations.

| Row | Ruling | Action |
|---|---|---|
| **C-3** (findings-delta ≤1) | reclassify — no semantic approval | **KEEP** at P-12's `≤1`. v1's `== 0` was tighter and is deleted |
| **C-14** (`G2-BLOCKER`) | reclassify | not new — already implicit in the Evaluator envelope; **KEEP** |
| **D-3** (M4 re-hash at ship) | reclassify | not new — implied by hash-binding discipline; **KEEP** |
| **C-5** (exact metric equality ×3) | **DELETE** | rejected-draft invention. Not in P-12. Removed, no approval needed |
| **A-1** (contract scope) | approve in principle, **rewrite** | §4 |
| **C-10** (`[Ph3-STALE]`) | approve in principle, **rewrite** | §5 |
| **A-10** `E-ROW-SHAPE-VIOLATION` | **do not retire — translate** | 12 sites; v1 treated as one CHANGE. Each site adjudicated individually |
| **A-13** `TRIGGER_UNKNOWN` | **do not retire — translate** | trigger enum = write audit trail; v1 keeps an event log, so it translates |
| **B-3** `APG-SEQUENCE-LEGACY` | **do not retire — translate/split** | blocked on migrator no-framework rule (§6) |
| **B-30** `E-ARTEFACT-TIER-MISMATCH` | **do not retire — translate** | frontmatter-milestone match, not deletion |
| **B-35** `MF-PHASE` | **do not retire — SPLIT** | **12 sites carrying several consistency predicates.** v1 retired it as one indivisible row. Only the *collinearity artifact* (phase enum in milestone namespace) is a retirement candidate; the consistency predicates are not |
| **D-4** `G3-ESCALATION` | **user policy decision** | ✅ **ADOPTED 2026-07-16** — superseded by §9.1 |
| **D-5** `G3-VERIFY` | **user policy decision** — promoting Reflector sampling to a gate raises strictness | ✅ **ADOPTED 2026-07-16** — superseded by §9.1 |
| **D-6** `G3-GROUNDING` | **user policy decision** — same | ✅ **ADOPTED 2026-07-16** — superseded by §9.1 |
| **D-8** signoff → `SIGNED` | **REJECTED as written** | standardizing every signoff to `SIGNED` adds migration cost without preserving additional protection. **Three vocabularies retained**; `G3-SIGNOFF` keeps the exactly-one-anchored-status rule per `PHASE_PROTOCOL.md:567`, vocabulary-agnostic |

**v1 claimed "12 rows requiring approval" and enumerated 15** (review #3). Corrected: **3 rows require user policy decisions** — D-4, D-5, D-6. A-1 and C-10 are approve-in-principle-pending-rewrite (§4, §5). Everything else is KEEP/SPLIT/translate at the generated-row level.

### 3.1 Two distinctions v1 collapsed

| v1 error | Correction |
|---|---|
| `MF-EXEMPLAR` mapped with `APG-EXEMPLAR-SCOPE` | **Different rules.** `MF-EXEMPLAR` governs **external exemplar credentials** — registry entries, approval authority, evidence hash-binding, self-declaration detection (`MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md:159` ff.). `APG-EXEMPLAR-SCOPE` governs **exemplar conditioning** at M1–M3. Merging loses the credential layer entirely — 37 sites' worth |
| B-20..B-23 receipts → `G1-APPROVAL` | **Receipt validity is dispatch authorization, not user approval.** A receipt authorizes an agent to dispatch against a target milestone; approval is the human accepting a deliverable. Separate predicates: `G1-DISPATCH-AUTH` vs `G1-APPROVAL`. Collapsing them would let a valid receipt read as user acceptance — inverting the rule at `ASSIGNMENT_MILESTONE_PROCESS.md:77` |

### 3.2 Citation form

Review #3: most v1 citations gave only `:line`, violating its own R-3. All generated rows carry full `file:line`. Prose citations in this file carry `file:line`. **R-3 is now machine-enforced** — parity extracts `scripts/<path>.py:<line>` and fails on a row without one.

---

## 4. A-1 rewritten — contract scope

Review #6. **Two concepts, separated:**

| Predicate | Applies to | Code |
|---|---|---|
| **Controlling-source contract**, hash-bound, resolved | **every academic project** — assignment · advisor brief · venue call · captured user instruction | `G0-CONTRACT` |
| **Course-essay milestone profile** (id/path/hash/functions/mapping) | only `project.type == course-essay` | `G0-PROFILE` |

Preserves "read the controlling source; do not guess" (`ASSIGNMENT_MILESTONE_PROCESS.md:5` — universal) while unblocking the CAiSE case, which currently cannot invoke `/run-draft` at all (`assignment_process_gate.py:17` hardwires one profile; `run-draft:16` fails closed with no type predicate). v1's "make the whole contract conditional on course-essay" **would have weakened the rule** and is withdrawn.

---

## 5. C-10 rewritten — drift vs. re-engagement

Review #2. **Two predicates, not one. Neither subsumes the other:**

| Predicate | Asks | Gate |
|---|---|---|
| `G2-CONTENT-DRIFT` | reviewed hash ≠ current hash? | G2 |
| `G3-REENGAGEMENT` | convergence evidence older than budget without user re-engagement? | G3 |

`[Ph3-STALE]` protects **active acknowledgment that old evidence remains viable**, not byte-identity. v1 collapsed them and justified it with a false claim that the clock-based predicate was untestable — `_is_t3_stale(section, budget_days, now)` (`scripts/pre_phase_advance_check.py:861`) already takes `now` as a parameter; only the context default at `:241` reads ambient. **The justification is withdrawn; the split stands on the review's reasoning.** Cold-start clause (`ph3_last_activity_at: null` → not stale, `references/PHASE_PROTOCOL.md:150`) attaches to `G3-REENGAGEMENT`.

---

## 6. M-3 resolved — status machine

Review's resolution adopted. **Compact live machine; feedback substates derived:**

```
status:        open | submitted | accepted | reopened
applicability: applicable | not_applicable
```

| Old status | v1.0 |
|---|---|
| `not_started` | `open` |
| `in_progress` | `open` |
| `feedback_pending` | **derived** = `submitted` + unadjudicated feedback |
| `revision_required` | **derived** = `submitted` + adjudicated blocking feedback requiring revision |
| `accepted` | `accepted` |
| `reopened` | `reopened` — **distinct**: a previously *accepted* milestone was reopened |
| `superseded` | **lineage/history event**, not live status |
| `not_applicable` | `applicability: not_applicable` only |
| `legacy_unverified` | **migration-pending** state |

`revision_requested` and feedback adjudication persist as **events**; `G1-FEEDBACK` blocks acceptance until cleared. This also removes the current contradiction of storing `not_applicable` in **both** `status` and `applicability`.

**The migrator must map all nine old statuses explicitly** — not only `revision_required`. v1 named one and missed eight.

---

## 7. Fixture preservation

Review: *"'every old block still blocks' can be satisfied by a gate that blocks everything."*

**NOT IMPLEMENTED — blocking (§1.1).** No fixture rows are generated. `[obs 2026-07-15: 11 fixture files carry code literals; those literals are not cases.]`

Blocked on the smoketest manifest contract. Parity exits non-zero until `docs/analysis/generated/fixture_manifest.json` exists and parses.

| Outcome class | Requirement | ☐ |
|---|---|---|
| **BLOCK** | every historical blocking fixture blocks, **with the mapped code** | ☐ |
| **PASS** | every historical passing fixture **still passes** | ☐ |
| **LEGACY_READY** | preserved, or retired with an approved migrator rule (B-3) | ☐ |
| **NOT_APPLICABLE** | `applicability: not_applicable` still short-circuits | ☐ |
| **MISCONFIGURED** | always blocks (`references/PHASE_PROTOCOL.md:567`) | ☐ |
| **QE2026 replay** | 2 × `READY`; 1 × `MF-HANDOFF`; v3 × 2 `MF-EVENT`; reopened → 23 findings incl. `MF-POLICY`, `MF-POLICY-PROVENANCE`, `MF-STRUCTURE` | ☐ |

The QE2026 replay is the strongest fixture — drawn from a live project, not from the spec's own assumptions — and it exercises four predicates v1 merged or retired.

---

## 8. Still open

| # | Item | Blocks | Status |
|---|---|---|---|
| **O-1** | **Every generated row is `TBD`** `[obs 2026-07-15: 242 production candidates; fixture row population UNKNOWN and ABSENT]`. Generation is partial; adjudication has not started | all implementation | **OPEN** |
| **O-2** | Mention-only candidates: `APG-DISPATCH-REFUSED`, `W-DUAL-READ-LEGACY`, `W-SNOWBALL-PRECONDITION-UNMET`, `MF-POLICY-{ATTESTATION,EXEMPLAR}-PIN-STALE`. **Not auto-dead** — adjudicate by reading | parity completeness | OPEN |
| **O-3** | Two undocumented emitters | gate coverage | **RESOLVED** ↓ |
| **O-4** | D-4 / D-5 / D-6 user policy decisions | G3 spec | ✅ **CLOSED 2026-07-16** (all three adopted; §9.1) |
| **O-5** | Q-2/Q-3 trusted-vs-derived | G2 purity | **RESOLVED** — acquisition contract §2, §3 |

### 8.1 O-3 resolved — no fifth gate

Adjudicated at review: **emitting a code does not make a component a gate.**

| Component | Actually is | Layer |
|---|---|---|
| `phase_notifications_loader.py` | emits a **compatibility warning** | adapter / acquisition **diagnostic** |
| `render_lifecycle_state.py` | validates/regenerates a **non-authoritative derived view** | **projection / maintenance** |

Both need **preservation coverage** — their sites are matrix rows — but neither is a transition gate. The four-gate design stands. My §8 framing ("either a fifth gate exists…") wrongly inferred *gate* from *emits a code*; the correct question is whether the component **decides a transition**, and neither does.

---

## 9. Next milestone

Per review, in order — **not** implementation:

| # | Step | Status |
|---|---|---|
| 1 | Parity portability | ✅ runs under the documented environment, no override |
| 2 | **Fixture completeness** | ⛔ **OPEN** — manifest contract specified, **not built**. Parity blocks |
| 3 | Durable row identity | ✅ `code@module:function#asthash~ordinal`; injectivity asserted at generation |
| 4 | Acquisition consistency | ✅ raw/projected split; `ACQ-*` vs `PRJ-*`; `asserted_result` single-named |
| 5 | **Adjudicate the candidate queue** | ⛔ blocked on 2 |
| 6 | Present D-4 / D-5 / D-6 | ⛔ blocked on 5 |

**Adjudication should not start until step 2 lands.** Row IDs would otherwise change when the fixture matrix is added, invalidating overlay work already done — the same reason injectivity had to be fixed *before* generation rather than after.

Implementation remains unauthorized. Steps 1, 3, 4 removed obstacles to adjudication; they are not adjudication.

---

## 9.1 Addendum — 2026-07-16 (dated update; §9 statuses superseded)

| Item | Update |
|---|---|
| §9 step 2 (fixture completeness) | **LANDED** — `scripts/analysis/fixture_runner.py` is the authoritative manifest writer (suite granularity); census SUITE-BOUND MANIFEST CONSISTENCY: PASS, parity exit 0 |
| §9 step 5 (adjudication) | **COMPLETE** — queue regenerated 242 → **248** after a user-approved census extension (bare finding-call codes + `[BLOCKER]`-prose; the parity code check was prefix-allowlisted too and fixed); all 248 rows adjudicated and user-signed in `docs/analysis/predicate_adjudication_overlay.md`, emitters frozen throughout (`docs/analysis/generated/emitter_freeze.json`) |
| §9 step 6 (D-4/D-5/D-6) | **RESOLVED — all three ADOPTED** as blocking G3 predicates (user decision) |
| §3 B-35 | Executed: 12 sites split individually; the collinearity artifact (`milestone_framework_validate.py:1756`) **RETIRE approved** with named replacement (:1759 milestone-status readiness under §6) |
| §8 O-1 | **CLOSED** (see step 5) |
| §8 O-2 | Partially resolved by reading: `APG-DISPATCH-REFUSED` live (batch 1), `MF-POLICY-ATTESTATION/EXEMPLAR-PIN-STALE` live (batch 4); `W-DUAL-READ-LEGACY`, `W-SNOWBALL-PRECONDITION-UNMET` remain open |
| §8 O-4 | **CLOSED** (adopted) |
| §1.3 / §1.5 "not built" | Superseded — runner built; the checker's own epistemics unchanged (it still verifies only the document) |
| Two-population caveat (§1.9 tail) | **CLOSED** — release-gate.sh Phase 1 and build-release-zip.sh both converged onto the committed builder (commit `6ebc465`) |

## 10. Grounding note

Row generation and parity are mechanical and re-runnable; **provenance is stamped in the generated file, not asserted here** (§0). The emitter list is *discovered*, not declared — a declared list is what hid three emitters. The parity failure of matrix v1 (0/242) and the 241-unique-IDs-in-242-rows collision were both **measured**. QE2026 outcomes in §7 are quoted from the review's validation run and have **not** been independently reproduced in this session; they are the review's evidence, not mine. O-3's resolution is the review's adjudication, adopted.
