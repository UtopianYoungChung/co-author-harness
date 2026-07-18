# Snapshot-Acquisition Contract — v1.0

**Date:** 2026-07-15
**Status:** ⚠️ **PROPOSED.** Approved in principle as a *boundary* (review 2026-07-15); this document specifies it.
**Companion:** `2026-07-15_predicate-preservation-matrix.md` (what the gates test), `2026-07-15_gate-specs-v1.md` (⛔ DRAFT, errata §0)

---

## 1. Why the draft's snapshot was not implementable

The review's finding 5 is correct and specific. The illustrated snapshot could not evaluate the gates it was drawn for:

| Gap | Consequence |
|---|---|
| `state` shown already parsed | **G0 cannot test JSON parsing.** Its first predicate is unevaluable |
| `snapshot.reviews` lacked the fields G2 reads | G2's stability components have no inputs |
| `files` = `{exists, sha256, lines}` | **G3 cannot inspect anchored `status:` lines.** It needs parsed content, not a hash |
| no invocation identity | "approval **from this invocation**" is unevaluable — the predicate protecting acceptance (matrix B-20..B-23) cannot be checked |
| verifier rows had no claim binding | G3-VERIFY cannot ask "is *this claim* corroborated?" |

**The pattern:** the draft designed the *shape* of purity and skipped the *content*. A boundary that cannot carry the predicates across it is decoration.

**A second lesson, learned the hard way this session.** Acquisition read a file through a mount that silently returned a **truncated** 9,224-byte view of a 10,468-byte file. The script parsed, ran, exited 0, and produced nothing — a *successful* run over a corrupt read. Acquisition that cannot detect this will feed gates a snapshot that is well-formed and wrong. **§4 exists because of that, not in anticipation of it.**

---

## 2. Contract — three stages, not two

**Revised 2026-07-15 (review #2), resolving Q-2/Q-3.** The two-stage design was wrong: it forced acquisition to either *derive* policy inputs (making it gate logic in disguise) or *trust* journal rows (making the journal writer an unaudited part of the trusted base). Neither is acceptable. The resolution is a **third stage**:

```
acquire_raw()          pure_project()              gate()
  I/O only        →    parse + derive          →   policy verdict
  stable bytes         deterministic, no I/O       no I/O
```

| Stage | Does | Must not |
|---|---|---|
| **`acquire_raw()`** | read raw state, journal rows, findings, signoffs, immutable verifier records | derive, threshold, normalise, or call the network |
| **`pure_project()`** | compute findings deltas, churn ratios, session matching, normalised views; **check journal assertions against their source records** | I/O of any kind |
| **`gate()`** | apply policy predicates to the projected snapshot | I/O; derive |

Two consequences that matter:

- **Verifier calls happen *before* acquisition** and write immutable, claim/session-bound evidence containing the raw-response hash. **Acquisition never calls the network.** This kills Q-3: `verifiers[]` is read from an evidence store, not produced by an MCP call inside the reproducible component.
- **The journal is not trusted.** `pure_project()` re-checks journal assertions against their source records, so a mis-written journal row is caught rather than believed. This kills Q-2: the P-12 components are *derived in a pure, testable layer* from raw inputs, so G2 stays a policy predicate and the derivation is independently verifiable.

**Q-4 resolved by compare-and-swap.** Before any write, CAS against the acquired state hash **and** artifact hashes. If anything changed, **discard the verdict and reacquire.** A verdict computed over a superseded snapshot is void, not stale-but-usable.

```
acquire_raw -> pure_project -> gate -> [CAS: state.sha256 + artifact hashes unchanged?]
                                          ├─ yes -> Planner writes
                                          └─ no  -> discard verdict, reacquire
```

Everything downstream of `acquire_raw()` is a total function over its output.

### 2.0 Two types, not one

**Review #5:** the three-stage prose sat on a two-stage schema — `AcquisitionResult` still carried `raw_state.parse`, anchored signoff lines, `grounding_clean`, normalised Check 8 status, and churn ratio. All of those are *projections*. A stage boundary the schema doesn't express is a diagram, not an architecture.

**Parsing failures belong to projection. Read failures belong to acquisition.**

```jsonc
// ---------- STAGE 1 : acquire_raw() -> RawSnapshot ----------
// Bytes, hashes, identities, raw records. No parse. No derivation.
RawSnapshot = {
  "ok": true,                              // false => STOP. No projection, no gates.
  "errors": [ { "code": "ACQ-...", "path": "...", "detail": "..." } ],

  "identity": {
    "invocation_id": "uuid",               // one /paper invocation
    "session_id":    "uuid",               // one chat session
    "started_at":    "2026-07-15T14:22:00Z",
    "now":           "2026-07-15T14:22:03Z",   // injected, never read
    "actor":         "planner",
    "tool_versions": { "python": "3.10.12" }
  },

  "blobs": {                               // EVERY read file, uniformly
    "reviews/project_state.json": {
      "exists": true, "sha256": "...", "bytes": 4192,
      "bytes_utf8": "<raw>",               // NOT parsed here
      "fstat_pre":  { "size": 4192, "ino": "...", "mtime": "..." },
      "fstat_post": { "size": 4192, "ino": "...", "mtime": "..." },
      "path_identity_stable": true, "reparse": false
    },
    "manuscript/intro.md":     { "...": "..." },
    "reviews/G4_signoff.md":   { "...": "..." }
  },

  "records": {                             // raw, unparsed, ordered
    "journal_rows":     [ "<raw line>", "..." ],
    "finding_records":  [ "<raw>", "..." ],
    "approval_records": [ "<raw>", "..." ],   // §2.2
    "verifier_evidence":[ "<raw>", "..." ]    // immutable, written pre-acquisition
  },

  "provenance": { "reads": 47, "rejected_reads": 0, "clock_source": "injected" }
}

// ---------- STAGE 2 : pure_project(RawSnapshot) -> ProjectedSnapshot ----------
// Parses, derives, and CHECKS journal assertions against source records.
// Deterministic. No I/O. Parse failure is reported HERE, as data.
ProjectedSnapshot = {
  "state": { "ok": true, "error": null, "value": { /* parsed ledger */ } },

  "files": { "manuscript/intro.md": { "sha256": "...", "lines": 412 } },

  "signoffs": [
    { "path": "reviews/G4_signoff.md", "sha256": "...",
      "anchored_status_lines": [ { "line": 14, "value": "SIGNED" } ],
      "count": 1, "malformed": false }
  ],

  "reviews": [                             // P-12 components DERIVED here
    { "cycle_id": "...", "section": "1. Introduction", "at": "...", "profile": "deep",
      "grounding_clean": true,             // component 1  (derived + cross-checked)
      "check8_aggregate": "acceptable",    // component 2
      "findings_count": 3,                 // component 3
      "line_churn_ratio": 0.003,           // component 4
      "convergence_metric": { "legacy_scalar": 0.003 },
      "manuscript_hash": "...",
      "journal_assertion_verified": true } // row re-checked against source records
  ],

  "findings": [
    { "id": "F-12", "severity": "BLOCKER", "section": "3. Method",
      "open": true, "owner": "generator", "escalated": false }
  ],

  "approvals": [ /* §2.2 */ ],
  "verifiers": [ /* §2.3 */ ],

  "projection_errors": [ { "code": "PRJ-JOURNAL-UNVERIFIED", "row": "..." } ]
}
```

### 2.2 The approval record — the gap in v1

**Review #5:** `invocation_id` proves *invocation identity*, not *human approval*. Receipt codes are *dispatch authorization*, not approval. Neither is a human saying yes. The schema had no approval object at all, so the predicate protecting acceptance (`ASSIGNMENT_MILESTONE_PROCESS.md:77` — "No file, elapsed time, user silence, or phase advancement counts as milestone acceptance") had nothing to read.

```jsonc
ApprovalRecord = {
  "milestone":       "M2",
  "artifact_sha256": "...",        // binds approval to EXACT bytes approved
  "decision":        "approved",   // approved | rejected
  "invocation_id":   "uuid",       // must equal identity.invocation_id
  "session_id":      "uuid",
  "at":              "...",
  "prompt_shown":    "<verbatim text the user answered>",
  "response_raw":    "<verbatim user response>",
  "captured_by":     "planner"
}
```

Edit the artifact after approving and `artifact_sha256` breaks before any approval predicate is consulted. **But note §3:** that this record *exists* is mechanical; that it *reflects a real human decision* is not provable by any gate.

### 2.3 Verifier evidence

```jsonc
VerifierEvidence = {                 // written PRE-acquisition, immutable
  "claim_id": "C-7", "claim_text_sha256": "...",
  "verifier": "zotero", "class": 1,
  "query": "Suchman 2007 plans situated actions",
  "raw_response_sha256": "...",      // the actual bytes returned
  "returned_id": "urn:isbn:9780521675888",
  "returned_title": "Human-Machine Reconfigurations",
  "asserted_result": "corroborating",  // an ASSERTION, not a proof (§3)
  "at": "...", "session_id": "uuid"
}
```

---

## 3. The trusted base

**Review #6 is right and my "nothing is trusted" claim was false.** Pure projection can verify *structure* and derive *counters*. It cannot mechanically prove that an Evaluator's grounding judgment is substantively correct, that a verifier result truly corroborates a claim, or that a captured approval actually came from the user. Claiming otherwise would launder human and tool judgment as machine-verified fact — the failure this redesign exists to prevent, one layer deeper.

| Field | Authoritative writer | Class | What is actually guaranteed |
|---|---|---|---|
| `blobs[*].sha256`, `fstat_*` | acquisition | **mechanical** | bytes read == bytes on disk at read time (§5 caveat) |
| `state.value` | `pure_project()` | **mechanical** | parses; conforms to schema |
| `reviews[*].findings_count`, `line_churn_ratio` | `pure_project()` | **mechanical** | correctly derived from raw records |
| `reviews[*].journal_assertion_verified` | `pure_project()` | **mechanical** | journal row matches its source record |
| `reviews[*].grounding_clean` | **Evaluator** | **asserted judgment** | an Evaluator *said* the scope is grounded. Projection can confirm no open `R-Refl-GR-*` record exists — **not that the judgment was correct** |
| `reviews[*].check8_aggregate` | **Evaluator / overlay** | **asserted judgment** | aggregate computed per policy from asserted sub-check verdicts |
| `findings[*].severity` | **Evaluator** | **asserted judgment** | a severity was assigned; correctness is not machine-checkable |
| `verifiers[*].raw_response_sha256` | verifier bridge | **mechanical** | these bytes came back from that call |
| `verifiers[*].asserted_result` | **verifier + agent reading** | **asserted judgment** | that the returned source *corroborates the claim* is an interpretation. Rule 7a's audit trail records it; nothing proves it |
| `approvals[*].artifact_sha256` | **Planner** (`captured_by`) | **mechanical** | the recorded hash; **acquisition verifies the binding**, it does not author it |
| `approvals[*].decision` | **the user** | **human authority** | that this reflects a real human choice is **outside** the machine. `prompt_shown` / `response_raw` make it *auditable*, not *provable* |

**Three classes, and the boundary is load-bearing:**

| Class | Meaning | Falsifiable by |
|---|---|---|
| **mechanical** | derivable and re-checkable from bytes | re-running projection |
| **asserted judgment** | a competent component recorded a verdict; structure checkable, substance not | Reflector sampling, human review |
| **human authority** | only the user can supply it; machine records but cannot generate it | the user |

Gates enforce **structure over all three**. They must never present an asserted judgment as a mechanical fact. G3-GROUNDING does not verify grounding — **it verifies that an Evaluator asserted grounding and that no contradicting record exists.** That distinction is the whole difference between a gate and a rubber stamp, and D-5/D-6 are user policy decisions precisely because promoting Reflector *sampling* to a *gate* changes what the system claims to know.

---

### 2.1 What each field exists for

**No field without a consumer.** This is invariant I-7 from the gate draft, applied to acquisition itself.

| Field | Stage | Consumed by | Trust class (§3) |
|---|---|---|---|
| `blobs[*].sha256` | Raw | CAS (Q-4); G1-ARTIFACT; G2-CONTENT-DRIFT; G3-M4-DRIFT | mechanical |
| `blobs[*].fstat_pre/post` | Raw | R-3 read integrity | mechanical |
| `identity.invocation_id` | Raw | G1-APPROVAL, G3-APPROVAL — "this invocation" | mechanical |
| `identity.session_id` | Raw | G3-VERIFY — Rule 7a session scoping | mechanical |
| `identity.now` | Raw | G3-REENGAGEMENT — injected, never ambient | mechanical |
| `records.*` | Raw | inputs to projection | mechanical |
| `state.ok` / `state.error` | **Projected** | **G0-SCHEMA** (was `raw_state.parse`) | mechanical |
| `state.value` | Projected | every gate | mechanical |
| `signoffs[*].anchored_status_lines` | **Projected** | G3-SIGNOFF — needs count and values, not a hash | mechanical |
| `reviews[*].findings_count` | **Projected** | G2 component 3 (delta ≤1) | mechanical |
| `reviews[*].line_churn_ratio` | **Projected** | G2 component 4 (≤0.5%) | mechanical |
| `reviews[*].journal_assertion_verified` | **Projected** | G2 — row re-checked against source | mechanical |
| `reviews[*].grounding_clean` | **Projected** | G2 component 1 | **asserted judgment** |
| `reviews[*].check8_aggregate` | **Projected** | G2 component 2 | **asserted judgment** |
| `findings[*].severity` | Projected | G2-BLOCKER | **asserted judgment** |
| `findings[*].owner` / `escalated` | Projected | G0-ESCALATION-OWNER, G3-ESCALATION | mechanical (structure) |
| `verifiers[*].claim_id` + `asserted_result` | Projected | G3-VERIFY — "is *this claim* corroborated?" | **asserted judgment** |
| `approvals[*].artifact_sha256` | Projected | G1-APPROVAL binding | mechanical |
| `approvals[*].decision` | Projected | G1-APPROVAL, G3-APPROVAL | **human authority** |

> The field is `asserted_result`, **not** `result` — the two names appeared in the same document and reviewers were right to call it a contradiction. `result` implied a fact; the value is an interpretation. One name, and it is the one that tells the truth.

> **`reviews[*]` carries all four P-12 components** because the matrix (C-1..C-4) keeps all four. The draft's snapshot carried two, which is *how* the convergence rule got silently narrowed. **The snapshot shape and the predicate set must be designed together or the snapshot quietly amends the rules.**

---

## 3. Determinism

Acquisition is impure but must be **reproducible**: same tree + same `now` → byte-identical `RawSnapshot`. Projection, being pure, is trivially reproducible from a fixed `RawSnapshot`.

| # | Rule |
|---|---|
| **D-1** | All collections sorted by a declared key: `files` by path; `reviews` by `(section, at, cycle_id)`; `findings` by `id`; `verifiers` by `(claim_id, at)`; `errors` by `(code, path)`. No filesystem-iteration order. |
| **D-2** | `now` is **passed in**, never read. Acquisition has no clock. |
| **D-3** | No `mtime` in any predicate — carried for diagnostics only. Filesystem timestamps are not portable. |
| **D-4** | Hashes over raw bytes, before any decoding or normalisation. |
| **D-5** | Absent ≠ empty. A missing file is `{exists: false}`, never `{exists: true, bytes: 0}`. |
| **D-6** | Serialisation is canonical JSON (sorted keys, fixed separators) so results diff cleanly. |

**Test:** acquire twice over an unchanged tree with fixed `now` → identical bytes. This is the same determinism check the census now carries (verified: 8,521 chars, twice).

---

## 4. Read integrity — the mount-skew defence

This session, a 10,468-byte file read as 9,224 bytes through a mount, truncated mid-function. Nothing errored. **A corrupt read is indistinguishable from a valid read of a different file unless acquisition looks for it.**

> **Scope of this defence — stated honestly (review #7).** These rules protect against **races, replacement, and short reads**. They are **not** a complete defence against a consistently dishonest filesystem or mount. A layer that reports the same false size in `fstat` *and* returns the matching truncated bytes *every time* is internally consistent and undetectable from inside this process — `fstat` is the same untrusted layer that served the bytes. Detecting that requires an out-of-band check (a second reader, a host-side comparison, a signed manifest). **The session failure that motivated §4 was of the detectable kind — size disagreed with content. A stable liar would have passed.**

**Double-reading alone is insufficient, and the harness already knew that.** A mount returning the *same stable truncation twice* passes a double-read. The stronger pattern is already specified in this tree at `references/MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md:159`:

> "The registry and each evidence object are acquired as one stable binary snapshot: **raw path components are checked before opening; the open descriptor is bound to the pre-open path identity; descriptor size, identity, and modification time must remain stable through the read; and the path must still name the same non-reparse file afterward.**"

That rule was written for exemplar evidence and is adopted verbatim as the general acquisition rule. My §4 double-read was a weaker reinvention of a discipline sitting in the harness's own references.

| # | Rule |
|---|---|
| **R-1** | **Pre-open path check.** Validate raw path components before opening. Reject reparse points / symlink substitution. |
| **R-2** | **Descriptor identity binding.** Bind the open descriptor to the pre-open path identity. Read through the descriptor, never re-resolve the path mid-read. |
| **R-3** | **`fstat` before and after.** Descriptor size, identity, and mtime must be stable across the read. Any change → `ACQ-UNSTABLE-READ`. |
| **R-4** | **Post-read path identity.** The path must still name the same non-reparse regular file afterward. Replacement race → `ACQ-PATH-REPLACED`. |
| **R-5** | **Size cross-check.** Bytes read == `fstat` size. Mismatch → `ACQ-SHORT-READ`. **This is the check that catches a stable truncation, which R-6 alone cannot.** |
| **R-6** | **Double-read verify.** Read twice, hash both. Mismatch → `ACQ-UNSTABLE-READ`. *Necessary but not sufficient* — retained as a cheap catch for unstable mounts, not relied on. |
| **R-7** | **Fail closed, loudly.** Any read anomaly → `ok: false`, **projection does not run and gates do not run**. An unstable read is not a gate verdict — the snapshot is void. |
| **R-8** | **Record `rejected_reads`.** Nonzero with `ok: true` is a contradiction and fails the acquisition self-test. |

> **Structural sanity is NOT an acquisition rule (review #3).** A previous revision had R-7 run `ast.parse` / JSON parse / frontmatter checks *during acquisition* while the contract said parsing belongs to `pure_project()` — the boundary contradicted itself in adjacent sections. **Acquisition does not parse.** Structural validity moved to projection as `PRJ-STRUCTURAL` (§2.4).
>
> This costs nothing: the truncation that motivated these rules is caught by **R-5's size cross-check**, which needs no parse. Detecting truncation by "the Python won't compile" was always the weaker signal — a file can truncate at a statement boundary and still parse.

> **R-4's distinction matters.** "The state is malformed" is a finding about the project. "I could not reliably read the state" is a finding about the *reader*. Collapsing them lets infrastructure failure masquerade as project failure — precisely how this session's script "passed" with exit 0 while doing nothing.

### 4.1 Error codes

**Stage 1 — acquisition (read failures). All void the snapshot.**

| Code | Meaning | `ok` |
|---|---|---|
| `ACQ-UNSTABLE-READ` | fstat drift across read, or two reads disagree (R-3, R-6) | false |
| `ACQ-SHORT-READ` | bytes ≠ fstat size (R-5) | false |
| `ACQ-PATH-REPLACED` | path no longer names the same non-reparse file (R-1, R-4) | false |
| `ACQ-PERMISSION` | unreadable path | false |
| `ACQ-IDENTITY-MISSING` | no `invocation_id`/`session_id` supplied | false |
| `ACQ-CAS-CONFLICT` | state or artifact hash changed between acquire and write (Q-4) | verdict void; reacquire |

### 2.4 Stage 2 — projection (parse failures). These are DATA, not void.

| Code | Meaning | Consumed by |
|---|---|---|
| `PRJ-STATE-UNPARSEABLE` | `project_state.json` is not valid JSON | **G0** → `G0-SCHEMA` |
| `PRJ-STRUCTURAL` | known-type structure invalid (was the mis-placed `ACQ-STRUCTURAL`) | G0 |
| `PRJ-JOURNAL-UNVERIFIED` | a journal row does not match its source record | G2 |
| `PRJ-SIGNOFF-MALFORMED` | signoff parse failed / no anchored status line | G3 |

**The distinction is R-8's, drawn precisely.** *"I could not reliably read the bytes"* is a fact about the **reader** — the snapshot is void and no verdict may be rendered. *"The bytes are not valid JSON"* is a fact about the **project** — a legitimate state that G0 must report. Collapsing them lets infrastructure failure masquerade as project failure, which is how this session's script "passed" with exit 0 while executing nothing.

`raw_state.parse` is **removed** — it was the artifact of the two-stage schema and had no home once parsing moved to projection. Parse outcome now lives at `ProjectedSnapshot.state.{ok,error}`.

> **`ACQ-STATE-UNPARSEABLE` no longer exists.** It was a two-stage artifact: an `ACQ-*` code that did not void the snapshot, contradicting the rule that every acquisition error voids. Once parsing moved to projection the contradiction dissolved — it is now `PRJ-STATE-UNPARSEABLE` (§2.4), which never claimed to void anything. Every remaining `ACQ-*` code voids, without exception.

---

## 5. Testability

Acquisition is impure, so it gets an integration harness, not a purity shim.

| Class | Requirement |
|---|---|
| **Golden tree** | fixture project → expected `RawSnapshot` **and** `ProjectedSnapshot` byte-for-byte, fixed `now` |
| **Determinism** | acquire × 2 → identical (D-1..D-6) |
| **Short read** | mock returning n−k bytes → `ACQ-SHORT-READ`, `ok: false`. **Regression test for this session's failure** |
| **Stable truncation** | mock returning the **same** n−k bytes on **both** reads → must still fail via R-5 size cross-check. **Double-read alone passes this; that is why R-5 exists** |
| **Unstable read** | mock returning different bytes per call → `ACQ-UNSTABLE-READ` |
| **Path replacement** | swap the path for a reparse point mid-read → `ACQ-PATH-REPLACED` |
| **CAS conflict** | mutate state between acquire and write → verdict discarded, reacquire; **no write occurs** |
| **Unparseable state** | malformed JSON → `RawSnapshot.ok: true` (bytes read fine), `ProjectedSnapshot.state.ok: false` + `PRJ-STATE-UNPARSEABLE`, G0 emits `G0-SCHEMA` |
| **Absent vs empty** | missing file ≠ zero-byte file (D-5) |
| **Ordering** | shuffled filesystem order → identical output (D-1) |
| **No clock** | run under a shim raising on `datetime.now()` / `time.*`. **Any call = failure** (D-2) |
| **Identity** | absent `invocation_id` → `ACQ-IDENTITY-MISSING`, not a default |

The clock shim is the invariant most likely to decay silently — a `datetime.now()` added inside a helper months from now breaks D-2 with no visible symptom until a gate becomes irreproducible.

---

## 6. Open questions — not resolved here

| # | Question | Status |
|---|---|---|
| **Q-1** | **Cost.** Acquisition hashes every file a gate might touch. On a large manuscript, how expensive? A lazy/memoised variant reintroduces order-dependence and threatens D-1. | **OPEN — unmeasured** |
| **Q-2** | Who computes `reviews[*]` (the P-12 components)? | **RESOLVED** §2 — `pure_project()` derives them from raw inputs and re-checks journal assertions against source records. Neither acquisition-derives nor journal-trusts |
| **Q-3** | Does acquisition make verifier calls? | **RESOLVED** §2 — no. Verifier calls precede acquisition and write immutable claim/session-bound evidence carrying the raw-response hash. Acquisition reads the evidence store |
| **Q-4** | Snapshot staleness between acquire and write | **RESOLVED** §2 — compare-and-swap on state + artifact hashes; on conflict the verdict is **void** and the cycle reacquires |

Q-2/Q-3 were one question — *what is trusted input versus what is derived* — and the three-stage split answers the **mechanical** half. It does not abolish the trusted base. See §3.

---

## 7. Grounding note

§1's gaps are the review's finding 5, restated against the draft's illustrated snapshot. §4 is grounded in an observed failure in this session: host `get_file_info` reported 10,468 B / 259 lines; the sandbox read 9,224 B truncated mid-function; the script exited 0 having executed nothing. Field→consumer mappings in §2.1 cite matrix rows, which cite `file:line`. §6 is labelled open because it is; Q-2/Q-3 are known-unsolved, not overlooked.
