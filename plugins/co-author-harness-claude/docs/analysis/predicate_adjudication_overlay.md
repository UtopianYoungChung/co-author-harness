# Predicate Adjudication Overlay — v0.29.0 → v1.0

**Status:** ✅ QUEUE COMPLETE — 248/248 rows adjudicated and user-signed across
4 batches (2026-07-16). D-4/D-5/D-6 presented after queue close per matrix §9
and **all three ADOPTED** (user decision 2026-07-16): `G3-ESCALATION` (ship
blocks on unresolved escalations), `G3-VERIFY` (external verifiers ran and
returned; results remain asserted-judgment class per the acquisition
contract), `G3-GROUNDING` (grounding-audit BLOCKER floor enforced at ship).

**Consolidated follow-ups owed (post-freeze / implementation round):**
census shape gaps — table-driven dynamic codes (B4 S-2), default-argument
`_file_binding` (B4 S-3), `_schema_findings` fan-out (B4 S-4); fixture gaps —
engine-present (B1-N2), clause c escalation/transfer (B2-N2), `MF-CANON`
(B4 S-6), 30/56 batch-3 rows; branch-level fixture attribution everywhere
(B2-N4 — the fixture_runner per-suite case-emission upgrade makes this
mechanical); O-2: `APG-DISPATCH-REFUSED` and both `MF-POLICY-*-PIN-STALE`
resolved LIVE, `W-DUAL-READ-LEGACY` and `W-SNOWBALL-PRECONDITION-UNMET`
still open; MF-EXEMPLAR gate placement to re-verify at implementation
(B4 S-9); v0.29.0 legacy-hash carve-out sunset decision (B4 S-10); §6
migrator no-framework rule still owed (blocks B-3's final split).
**Keyed by:** generated row ID (`code@module:function#asthash~ordinal`) from
`docs/analysis/generated/predicate_rows.md`. `file:line` is a locator only.
**Freeze:** emitters frozen at adjudication start — hashes in
`docs/analysis/generated/emitter_freeze.json` (2026-07-16). Verify before each
batch; any drift voids row IDs adjudicated after the drifted file changed.
**Policy layer:** `docs/analysis/2026-07-15_predicate-preservation-matrix.md`
(dispositions §2, standing rulings §3). Default is KEEP; an unsigned row at
implementation time is a BLOCKER, never a silent retirement.

**Post-freeze v0.30.0 addition:** the original 248/248 queue remains the
historical signed baseline. The implementation adds one new predicate row,
adjudicated below as KEEP; the live total is therefore 249/249. This addition
does not rewrite the 2026-07-16 freeze record. Current
`milestone_framework_validate.py` emitter hash: `9e0ce29a1be7`.

| Row ID | Outcome | Predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `MF-EVENT@milestone_framework_validate:_validate_events#073bff9fe25d~0` (:361) | BLOCKER finding | A current primary-lineage deliverable in an active pre-acceptance state (`in_progress`, `feedback_pending`, `revision_required`, or `reopened`) requires a `deliverable_recorded` event binding its exact path and hash | `milestone_framework_smoketest.py`: `missing_deliverable_recorded_event` and `deliverable_record_binding_mismatch` reject; `valid_deliverable_recorded_event` accepts | KEEP | none |

Dispositions: KEEP (no approval) · MOVE (approval if it crosses a gate-frequency
boundary) · SPLIT (approval) · CHANGE (approval; must name the differing input)
· RETIRE (approval; must name replacement or declare abandonment).

---

## Batch 1 — scripts/assignment_dispatch_preflight.py (5 rows) — ✅ SIGNED (user checkpoint 2026-07-16)

Emitter hash at adjudication: `58159da5cfaf` (verified against freeze record).

Component reading: fail-closed pre-dispatch receipt verifier. Every refusal
prints `MISCONFIGURED`, the specific `[BLOCKER]` code, the companion
`APG-DISPATCH-REFUSED` banner, and exits 4. Per matrix §3.1: receipt validity
is **dispatch authorization**, not user approval — target family is
`G1-DISPATCH-AUTH`, never `G1-APPROVAL`.

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `APG-RECEIPT-INVALID@assignment_dispatch_preflight:main#b57a7cef1e00~0` (:42) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / engine-present: the predicate engine (`assignment_process_gate.py`) must exist before any dispatch | **none** — no fixture exercises a missing engine (would require relocating the gate file; see B1-N2) | KEEP | none |
| `APG-RECEIPT-MISSING@assignment_dispatch_preflight:main#6cc3f0bf54f0~0` (:45) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / receipt-present: a dispatch requires an existing receipt file | `assignment_dispatch_preflight_smoketest.py` (asserts code, :194, :228) | KEEP | none |
| `APG-RECEIPT-INVALID@assignment_dispatch_preflight:main#181180e8d2b3~0` (:51) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / receipt-parseable: receipt must read as valid JSON | suite asserts `APG-RECEIPT-INVALID` (:244, :275); branch-level attribution (parse-fail vs shape-fail) unverified | KEEP | none |
| `APG-RECEIPT-INVALID@assignment_dispatch_preflight:main#887e247b442b~0` (:58) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / receipt-well-formed: receipt must be an object with string `target_milestone` | same as :51 — code asserted, branch attribution unverified | KEEP | none |
| `APG-RECEIPT-TARGET-MISMATCH@assignment_dispatch_preflight:main#65be49d55a5a~0` (:63) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / receipt-target-match: receipt's `target_milestone` must equal the dispatch target (the §3.1 core: authorization ≠ approval) | suite asserts code (:217, :249) | KEEP | none |

All five: same predicate, same trigger point (per-dispatch), same frequency —
new code family name only. KEEP requires no approval; recorded for checkpoint
review regardless.

### Batch 1 supplementary findings

- **B1-N1 — uncensused emission site (census shape-catalog gap).**
  `assignment_dispatch_preflight.py:84-89`: delegated verification
  (`assignment_process_gate.py --verify-receipt`) exits nonzero → refuse with
  `APG-DISPATCH-REFUSED`, exit 4. This is a genuine predicate
  (receipt-verified) with **no generated row**: the emission is a bare
  `print()` of a `[BLOCKER]`-prefixed string, a shape `collect_sites()` does
  not cover (it catches `[ADVISORY]`-prose but not `[BLOCKER]`-prose).
  Adjudicated here as: KEEP → `G1-DISPATCH-AUTH` / receipt-verified.
  **Census follow-up owed:** either extend the shape catalog to
  `[BLOCKER]`-prose emissions or record this as a standing manual row —
  extending the catalog renumbers nothing (new sites append new IDs) but must
  wait until the freeze lifts.
- **B1-N2 — fixture gap.** The engine-present branch (:42) has no fixture in
  any suite. Fixture requirement recorded for the v1.0 corpus: a case that
  relocates/renames the gate path and asserts refusal.
- **B1-N3 — O-2 partial resolution.** `APG-DISPATCH-REFUSED` (mention-only
  candidate in matrix §8 O-2) is **live**, emitted at :22 (inside `_refuse`,
  so on every refusal) and :86. It is not an independent predicate — it is the
  uniform refusal banner accompanying whichever predicate fired. Disposition:
  KEEP as the `G1-DISPATCH-AUTH` refusal marker. Not dead; O-2 should strike
  it from the candidate list when this batch is signed.
- **B1-N1/N3 resolved by census extension (2026-07-16, user-approved):** the
  collector now catches `[BLOCKER]`-prose and bare finding-call codes; queue
  regenerated 242 → 248, batch-1 row IDs verified unchanged. The two sites
  above now carry rows, adjudicated per B1-N1/B1-N3:

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `APG-DISPATCH-REFUSED@assignment_dispatch_preflight:_refuse#f9a3fbe992d3~0` (:22) | accompanies every refusal (exit 4) | `G1-DISPATCH-AUTH` / refusal marker (banner, fires with whichever predicate refused) | suite asserts banner on refusals (:195, :218, :229 ...) | KEEP | none |
| `APG-DISPATCH-REFUSED@assignment_dispatch_preflight:main#f9a3fbe992d3~0` (:86) | exit 4 after delegated gate nonzero | `G1-DISPATCH-AUTH` / receipt-verified: delegated `--verify-receipt` must exit 0 | suite exercises delegated refusals (stale/consumed receipt paths, :259-275) | KEEP | none |

---

## Batch 2 — scripts/pre_phase_advance_check.py (32 rows) — ✅ SIGNED (user checkpoint 2026-07-16)

Emitter hash at adjudication: `3975987cba16` (frozen; census extension touched
only the observer). Contract: PRE-PHASE (`CLEAN → 0`, `BLOCKED → 1`;
exit 2 = I/O and argument failures, outside the contract). `W-*` findings
route to warnings (CLEAN exit); all other codes are errors (BLOCKED).

Component reading: the mandatory pre-advance guardrail over
`reviews/phase_state.json`, clauses a–d, f, g. In v1.0 the Ph-advance event
disappears; its predicates translate to gate checks — per-transition
readiness → **G2**, dispatch readiness → **G1**, ship/MCR admission →
**G3**, signoff-row shape → **G3-SIGNOFF** (D-8: vocabulary retained,
exactly-one-anchored-status per PHASE_PROTOCOL.md:567). All MOVEs preserve
trigger cardinality **by design intent** — v1.0 gate invocation frequencies
are unimplemented, so "no frequency change" is a design claim, not a
measurement; re-verify at implementation.

### Clause a — prior-stage exit artefact (per-advance → G2)

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `E-ARTEFACT-MISSING@pre_phase_advance_check:check_clause_a#9c1ba06e7705~0` (:431) | BLOCKED | G2 / artefact-present: prior-stage exit artefact exists, non-empty | `pre_phase_advance_phase_state_smoketest.py` (branch attribution unverified) | MOVE → G2 | none (cardinality preserved) |
| `E-MISSING-T1-SIGNOFF@pre_phase_advance_check:check_clause_a#9c1ba06e7705~0` (:431) | BLOCKED | G2 / artefact-present, draft-stage specialization (same site, conditional code — the canonical two-predicates-one-line case) | same | MOVE → G2 | none |
| `E-ARTEFACT-MALFORMED@pre_phase_advance_check:check_clause_a#fc2b232076a8~0` (:442) | BLOCKED | G2 / artefact-frontmatter-present (YAML block parseable) | same | MOVE → G2 | none |
| `E-ARTEFACT-TIER-MISMATCH@pre_phase_advance_check:check_clause_a#486adc0d4da3~0` (:457) | BLOCKED | G2 / artefact-declares-stage — **matrix B-30: translate to frontmatter-milestone match, not deletion** | same | MOVE → G2 (B-30) | none (matrix-directed) |
| `E-T3-TERMINAL-ROW-MISSING@pre_phase_advance_check:check_clause_a#1728b84d99b9~0` (:472) | BLOCKED (ship admission only) | G3 / terminal-signoff-present: convergence signoff carries `is_terminal: true` before ship | same (T4-path branch) | MOVE → G3 | none |

### Clause b — state-object completeness (per-advance → G2; schema tracks §6)

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `SECTION_MISSING_FIELD@pre_phase_advance_check:check_clause_b#a23bbe10cef2~0` (:519) | BLOCKED | G2 / state-schema-complete: state object carries every schema-required field. **Field set changes under the adopted §6 status machine** — predicate is schema-parameterized | `phase_state_validate` fixtures (gate Phase 0.67); branch attribution unverified | CHANGE (input: required-field set, 15 → v1.0 §6 set) | **covered by adopted matrix §6**; re-sign only if §6 reopens |
| `SECTION_FIELD_EMPTY@pre_phase_advance_check:check_clause_b#5f879665f7f0~0` (:531) | BLOCKED | G2 / stage-goal-declared non-empty | same | CHANGE (field renames per §6) | covered by §6 |
| `SECTION_FIELD_EMPTY@pre_phase_advance_check:check_clause_b#ba6c6281ebcf~0` (:540) | BLOCKED | G2 / stage-deliverable-path non-empty | same | CHANGE (field renames per §6) | covered by §6 |
| `E-T3-CONVERGENCE-NULL-AT-SIGNOFF@pre_phase_advance_check:check_clause_b#7d9b22b618a0~0` (:550) | BLOCKED (ship admission) | G3 / convergence-metric-nonnull at ship admission (metric machinery kept per C-3/D-8) | same | MOVE → G3 | none |

### Clause c — escalation ownership (per-advance when log exists → G2)

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `E-ESCALATION-WITHOUT-OWNER@pre_phase_advance_check:check_clause_c#281e39074dc9~0` (:618) | BLOCKED | G2 / escalation-owner-present (Linear-Accountability defence; event log survives per A-13 rationale) | **none found** — fixture-gap, recorded B2-N2 | MOVE → G2 | none |
| `E-OWNERSHIP-TRANSFER-WITHOUT-RATIONALE@pre_phase_advance_check:check_clause_c#d955f1395242~0` (:631) | BLOCKED | G2 / transfer-rationale-present | **none found** — B2-N2 | MOVE → G2 | none |

### Clause d — review-dispatch readiness (first review admission → G1)

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `E-CLASSIFICATION-MISSING-AT-T2@pre_phase_advance_check:check_clause_d#cf6142f44ff7~0` (:674) | BLOCKED | G1 / classification-present before first review dispatch | suite (branch unverified) | MOVE → G1 | none |
| `W-PSTAGE-UNAVAILABLE@pre_phase_advance_check:check_clause_d#f920bcc137c0~0` (:694) | CLEAN + warning | G1 advisory / pstage-declared-or-warn (first admission tolerated) | suite (branch unverified) | KEEP (advisory) | none |
| `E-PSTAGE-REQUIRED-AT-T2@pre_phase_advance_check:check_clause_d#9703a6677188~0` (:706) | BLOCKED | G1 / pstage-required-on-reentry (prior approval history ⇒ pstage mandatory) | suite (branch unverified) | MOVE → G1 | none |

### Clause f — MCR / ship admission (→ G3)

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `E-MCR-NOT-CLEARED@pre_phase_advance_check:check_clause_f#49d2e9af4e52~0` (:905) | BLOCKED | G3 / all-sections-converged-or-ceiling-terminal before ship | `mcr_convergence_evidence_smoketest.py` + suite (branch unverified) | MOVE → G3 | none |
| `E-MCR-BLOCKED-T3-STALE@pre_phase_advance_check:check_clause_f#d76cd6b23e2f~0` (:917) | BLOCKED | **`G3-REENGAGEMENT`** per matrix §5 (C-10 rewrite): evidence older than budget without signed re-engagement; cold-start clause (null activity → not stale) attaches | same | MOVE → G3-REENGAGEMENT (§5) | none (ruled) |
| `E-MCR-PRE-DEEP-PASS-REQUIRED@pre_phase_advance_check:check_clause_f#8edfc2de29b9~0` (:931) | BLOCKED | G3 / pre-ship-deep-pass-completed (D-3: KEEP, implied by hash-binding discipline) | same | MOVE → G3 (D-3) | none |
| `W-MCR-CONVERGENCE-EVIDENCE@pre_phase_advance_check:check_clause_f#3c3df785bd76~0` (:951) | CLEAN + advisory | G3 advisory / convergence-evidence (explicitly non-authorizing; terminal signoff remains the authority) | `mcr_convergence_evidence_smoketest.py` | KEEP (advisory diagnostic) | none |

### Clause g — event-log row shape (per-advance → G2)

Per A-10: `E-ROW-SHAPE-VIOLATION`'s 12 sites adjudicated individually, never
as one row. Event log survives as events (matrix §6).

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `E-ROW-SHAPE-VIOLATION@pre_phase_advance_check:_check_tier_entry_log_row#5dc78041445b~0` (:1014) | BLOCKED | G2 / event-row-required-fields (timestamp, trigger, prev, new, actor) | suite (branch unverified) | MOVE → G2 | none |
| `TRIGGER_UNKNOWN@pre_phase_advance_check:_check_tier_entry_log_row#c8763159fe43~0` (:1024) | BLOCKED | G2 / event-trigger-known — **matrix A-13: translate; trigger enum = write audit trail** | suite (branch unverified) | MOVE → G2 (A-13) | none (ruled) |
| `E-ROW-SHAPE-VIOLATION@pre_phase_advance_check:_check_tier_entry_log_row#8c848994ade4~0` (:1034) | BLOCKED | G2 / event-actor-enum | suite | MOVE → G2 | none |
| `E-ROW-SHAPE-VIOLATION@pre_phase_advance_check:_check_tier_entry_log_row#680ce6585765~0` (:1045) | BLOCKED | G2 / event-stage-enum — **enum values change under §6** (phase enum retired) | suite | CHANGE (input: `TIER_ENUM_CURRENT` → §6 status values) | covered by adopted §6 |
| `E-ROW-SHAPE-VIOLATION@pre_phase_advance_check:_check_tier_entry_log_row#6cb121f68792~0` (:1057) | BLOCKED | G2 / event-notes-bound (≤280) | suite | MOVE → G2 | none |

### Clause g — signoff-row shape (→ `G3-SIGNOFF`, D-8 vocabulary retained)

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `E-ROW-SHAPE-VIOLATION@pre_phase_advance_check:_check_signoff_row#a852971860cd~0` (:1079) | BLOCKED | G3-SIGNOFF / row-kind-exclusive (terminal ∧ re-engagement forbidden) | suite (branch unverified) | MOVE → G3-SIGNOFF | none |
| `E-ROW-SHAPE-VIOLATION@pre_phase_advance_check:_check_signoff_row#133686f58c64~0` (:1091) | BLOCKED | G3-SIGNOFF / row-kind-required — the D-8 exactly-one-anchored-status rule (PHASE_PROTOCOL.md:567) | suite | MOVE → G3-SIGNOFF (D-8) | none (ruled) |
| `E-ROW-SHAPE-VIOLATION@pre_phase_advance_check:_check_signoff_row#9b54de382f11~0` (:1106) | BLOCKED | G3-SIGNOFF / common-row-fields (timestamp, iteration, signature, signed-at) | suite | MOVE → G3-SIGNOFF | none |
| `E-ROW-SHAPE-VIOLATION@pre_phase_advance_check:_check_signoff_row#38d27c2e10fe~0` (:1120) | BLOCKED | G3-SIGNOFF / terminal-row-fields (metric, verdict, owner-state) | suite | MOVE → G3-SIGNOFF | none |
| `E-T3-CONVERGENCE-NULL-AT-SIGNOFF@pre_phase_advance_check:_check_signoff_row#dae74c812218~0` (:1134) | BLOCKED | G3-SIGNOFF / terminal-metric-nonnull | suite | MOVE → G3-SIGNOFF | none |
| `E-ROW-SHAPE-VIOLATION@pre_phase_advance_check:_check_signoff_row#25de4a2a7af9~0` (:1147) | BLOCKED | G3-SIGNOFF / verdict-enum (CONVERGING·CONTESTED·DIVERGING; kept per C-3/D-8) | suite | MOVE → G3-SIGNOFF | none |
| `E-ROW-SHAPE-VIOLATION@pre_phase_advance_check:_check_signoff_row#96a58c924658~0` (:1160) | BLOCKED | G3-SIGNOFF / reengagement-cleared-at-required (pairs with G3-REENGAGEMENT) | suite | MOVE → G3-SIGNOFF | none |
| `E-ROW-SHAPE-VIOLATION@pre_phase_advance_check:_check_signoff_row#465528877ab6~0` (:1173) | BLOCKED | G3-SIGNOFF / verdict-terminal-only (forbidden on re-engagement rows) | suite | MOVE → G3-SIGNOFF | none |
| `E-ROW-SHAPE-VIOLATION@pre_phase_advance_check:_check_signoff_row#09d80714e8d1~0` (:1186) | BLOCKED | G3-SIGNOFF / notes-bound (≤560) | suite | MOVE → G3-SIGNOFF | none |

### Batch 2 supplementary findings

- **B2-N1 — census + parity extension (user-approved mid-batch).** Collector
  now accepts vouched bare finding-call codes and `[BLOCKER]`-prose; the
  parity code-presence check was itself prefix-allowlisted and fixed the same
  way. Queue 242 → 248; parity 248/248 exit 0; batch-1 IDs unchanged.
- **B2-N2 — fixture gaps.** No suite exercises clause c (escalation-owner /
  transfer-rationale). Recorded as v1.0 corpus requirements alongside B1-N2.
- **B2-N3 — 6 CHANGE rows all track the adopted §6 status machine** (field
  set, field renames, stage enum). They carry no independent approval need
  unless §6 reopens; listed so the dependency is explicit.
- **B2-N4 — fixture attribution debt.** "Suite (branch unverified)" appears
  throughout: the suites exist and pass, but per-branch assertion mapping was
  not verified row-by-row in this batch. That mapping is exactly what the
  future per-suite native case emission (fixture_runner granularity upgrade)
  should make mechanical.

---

## Batch 3 — scripts/assignment_process_gate.py (56 rows) — ✅ SIGNED (user checkpoint 2026-07-16)

Emitter hash at adjudication: `a9cab0033902` (verified against freeze record; sha256 recomputed 2026-07-16 in-session, full digest matches `emitter_freeze.json` byte-for-byte).

Component reading: the fail-closed predicate engine for assignment-derived
drafting, with three surfaces sharing one findings pipeline. (1) `validate()`
— the per-dispatch rule engine over `reviews/assignment_contract.json`,
the hardwired course-essay profile (`PROFILE_REL` at **:17** — the known
CAiSE bug, matrix §4), and `reviews/phase_state.json`. (2) Receipt emission
(`--emit-receipt`) — a single-use dispatch-authorization artifact hash-bound
to contract, phase state, profile, and the gate's own READY stdout. (3)
Receipt verification (`--verify-receipt`) — shape/path/status/staleness
checks that then **re-run `validate()` in full** (:404), so every
`validate()` row fires on both the emit path and every subsequent
verification. Outcome contract: any finding → `MISCONFIGURED` +
`[BLOCKER] <code>: <message>` lines, exit 4 (MFHP-9-compatible); pass →
`READY …` / `VERIFIED …` / `RECEIPT …`, exit 0; argparse usage errors exit 2
(EXIT-ONLY class, no codes). Per matrix §3.1, everything receipt-shaped here
is **`G1-DISPATCH-AUTH`, never `G1-APPROVAL`** — a valid receipt authorizes a
dispatch; it is not human acceptance of a deliverable. Also per §3.1,
`APG-EXEMPLAR-SCOPE` is conditioning scope, not `MF-EXEMPLAR` credentialing.
Per matrix §4 (A-1, adopted in principle), the contract clause universalizes
to `G0-CONTRACT` and the profile clause becomes `G0-PROFILE`, conditional on
`project.type == course-essay`. Suites: `assignment_process_gate_smoketest.py`
(direct) and `assignment_dispatch_preflight_smoketest.py` (delegated
`--verify-receipt` paths); no other suite in `scripts/` asserts APG codes
(grep-verified).

MOVE frequency note (as in batch 2): v1.0 gate invocation frequencies are
unimplemented, so "cardinality preserved" below is a design claim, not a
measurement; re-verify at implementation. For the G0 moves specifically, G0
runs at bootstrap (earlier than the current per-dispatch firing — §2.1 makes
that approval-bearing on its face), but per-dispatch protection is preserved
by the receipt hash re-binding (`assignment_contract_sha256` /
`profile_sha256` staleness at G1-DISPATCH-AUTH). That preservation argument
is part of what the A-1 in-principle approval covers; it is restated here so
the checkpoint can reject it.

### validate() — contract clause (→ G0-CONTRACT, A-1)

Old outcome for all five: MISCONFIGURED + `[BLOCKER]`, exit 4 (on emit and on every receipt verification via :404).

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `APG-CONTRACT-MISSING@assignment_process_gate:validate#0e4ee5e555eb~0` (:428) | MISCONFIGURED, exit 4; short-circuits all later clauses | `G0-CONTRACT` / contract-present-and-parseable: the hash-bound controlling-source contract exists and reads as JSON | `assignment_process_gate_smoketest.py` :303-312 (verified: project without contract; also asserts no receipt is emitted) | MOVE → G0-CONTRACT (A-1: universalized to every project) | covered by adopted A-1 rewrite (§4); re-sign only if A-1 reopens |
| `APG-CONTRACT-UNRESOLVED@assignment_process_gate:validate#598a8cf55ad0~0` (:432) | MISCONFIGURED, exit 4 | `G0-CONTRACT` / contract-resolved: version 1.0.0 with `status == resolved` — "read the controlling source; do not guess" | **none found** — no suite asserts this code (grep) | MOVE → G0-CONTRACT (A-1) | covered by A-1 (§4) |
| `APG-SOURCE-AUTHORITY@assignment_process_gate:validate#e4bfa8ca0e87~0` (:449) | MISCONFIGURED, exit 4 | `G0-CONTRACT` / source-authority-recognized: controlling source carries authority ∈ {user, advisor, instructor, committee, venue} | **none found** (grep) | MOVE → G0-CONTRACT (A-1) | covered by A-1 (§4) |
| `APG-SOURCE-MISSING@assignment_process_gate:validate#77b152aca146~0` (:456) | MISCONFIGURED, exit 4 | `G0-CONTRACT` / source-file-present: the controlling source file exists on disk | **none found** (grep) | MOVE → G0-CONTRACT (A-1) | covered by A-1 (§4) |
| `APG-SOURCE-HASH@assignment_process_gate:validate#1da46b286cf2~0` (:458) | MISCONFIGURED, exit 4 | `G0-CONTRACT` / source-hash-current: contract's `sha256` matches the source's current bytes | **none found** (grep) | MOVE → G0-CONTRACT (A-1) | covered by A-1 (§4) |

### validate() — profile / mapping / copy-policy clause (→ G0-PROFILE, A-1 CHANGE)

All eight fire unconditionally today because :17 hardwires
`course_essay_milestones.v1.json` for every project (the CAiSE bug). Under
adopted A-1 they become conditional: enforced iff
`project.type == course-essay`, not-applicable otherwise. That is a semantic
change on a named input (`project.type`), so the whole clause is CHANGE, with
approval already carried by the adopted §4 rewrite.

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `APG-PROFILE-MISSING@assignment_process_gate:validate#c511faba3d85~0` (:435) | MISCONFIGURED, exit 4 | `G0-PROFILE` / profile-present-and-parseable (package profile file) | **none found** (grep; would require mutilating the package profile) | CHANGE (input: `project.type` ≠ course-essay → not applicable) | covered by adopted A-1 rewrite (§4) |
| `APG-PROFILE-ID@assignment_process_gate:validate#b23e5df4afa6~0` (:438) | MISCONFIGURED, exit 4 | `G0-PROFILE` / profile-id-match: contract `profile_id` == package profile's | **none found** (grep) | CHANGE (A-1) | covered by §4 |
| `APG-PROFILE-PATH@assignment_process_gate:validate#85c622622824~0` (:440) | MISCONFIGURED, exit 4 | `G0-PROFILE` / profile-path-canonical: contract names the package profile path | **none found** (grep) | CHANGE (A-1) | covered by §4 |
| `APG-PROFILE-HASH@assignment_process_gate:validate#46c991c3eae4~0` (:442) | MISCONFIGURED, exit 4 | `G0-PROFILE` / profile-hash-current: contract `profile_sha256` matches the profile's current bytes | **none found** (grep) | CHANGE (A-1) | covered by §4 |
| `APG-PROFILE-FUNCTIONS@assignment_process_gate:validate#95d07b0f4c80~0` (:445) | MISCONFIGURED, exit 4 | `G0-PROFILE` / profile-deliverables-complete: profile defines exactly M1–M4 + separate FINAL | **none found** (grep) | CHANGE (A-1) | covered by §4 |
| `APG-SEQUENCE@assignment_process_gate:validate#761fe3f75bec~0` (:461) | MISCONFIGURED, exit 4 | `G0-PROFILE` / assigned-sequence-canonical: contract `assigned_sequence` == [M1, M2, M3, M4, FINAL] | **none found** — suites assert only the suffixed runtime forms `APG-SEQUENCE-M*` from :505, a **different predicate** (see B3-N3) | CHANGE (A-1) | covered by §4 |
| `APG-MAPPING@assignment_process_gate:validate#7dbeb3b9a066~0` (:463) | MISCONFIGURED, exit 4 | `G0-PROFILE` / framework-mapping-canonical: FINAL kept separate, bound to terminal slot M5 | **none found** (grep) | CHANGE (A-1) | covered by §4 |
| `APG-PROFESSOR-COPY-AUTHORITY@assignment_process_gate:validate#b329314e9c82~0` (:465) | MISCONFIGURED, exit 4 | `G0-PROFILE` / professor-copy-author-controlled: copy production stays author-controlled unless explicitly requested (course-essay policy field) | `assignment_process_gate_smoketest.py` :369-375 (verified: policy mutated to `harness_generates_professor_copy`) | CHANGE (A-1) | covered by §4 |

### validate() — dispatch-target coherence and exemplar scope (→ G1-DISPATCH-AUTH)

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `APG-SEQUENCE-TARGET@assignment_process_gate:validate#3d2bc271a882~0` (:469) | MISCONFIGURED, exit 4; short-circuits | `G1-DISPATCH-AUTH` / final-via-final-stage: FINAL is unreachable as a draft target (must use `--stage final`). In v1.0, if targets are computed from milestone state rather than passed, this survives as "requested transition must be unambiguous" | `assignment_process_gate_smoketest.py` :321-324 (verified: `draft FINAL`) | KEEP | none |
| `APG-SEQUENCE-TARGET@assignment_process_gate:validate#eb458d227e74~0` (:472) | MISCONFIGURED, exit 4; short-circuits | `G1-DISPATCH-AUTH` / draft-target-explicit: draft dispatch requires an explicit target milestone | `assignment_process_gate_smoketest.py` :223-227 (verified: `draft` with no target) | KEEP | none |
| `APG-EXEMPLAR-SCOPE@assignment_process_gate:validate#edca686f5dbf~0` (:478) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / exemplar-conditioning-scope: M1–M3 forbid domain-native exemplar retrieval conditioning (ordinary citation stays allowed). §3.1: this is conditioning scope, **not** `MF-EXEMPLAR` credentialing — do not merge | `assignment_process_gate_smoketest.py` :271-275 (verified: M2 + `--exemplar-conditioning`) | KEEP | none |

### validate() — state and milestone sequence (→ G2, per-transition readiness)

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `APG-PHASE-STATE-MISSING@assignment_process_gate:validate#a2e72b96d0b2~0` (:483) | MISCONFIGURED, exit 4 | G2 / state-present-and-parseable: `reviews/phase_state.json` exists and reads as JSON before any sequence judgment | **none found** — no suite asserts this code (grep) | MOVE → G2 | none (cardinality preserved by design intent) |
| `APG-SEQUENCE-LEGACY@assignment_process_gate:validate#98acd4bf7c5d~0` (:489) | MISCONFIGURED, exit 4; short-circuits sequence checks | G2 / state-native: non-native (`mode != "native"`) milestone state requires explicit migration + acceptance work before sequence dispatch. **Matrix B-3: translate/split, never retire** — final shape blocked on the §6 migrator no-framework rule (§6 maps `legacy_unverified` → migration-pending) | `assignment_process_gate_smoketest.py` :353-363 (verified: mode flipped to `legacy`; message words asserted) | MOVE → G2 (B-3; final split pending §6 migrator rule) | none (ruled B-3); reopens if §6 migrator rule changes |
| `APG-SEQUENCE@assignment_process_gate:validate#dd9e9054364b~0` (:505) | MISCONFIGURED, exit 4; runtime code is f-string `APG-SEQUENCE-{target}` (M2/M3/M4/FINAL; never M1 — empty predecessor set) | G2 / predecessors-accepted: every predecessor of the target milestone has `status == "accepted"`. Survives the §6 machine unchanged (`accepted` is a live §6 status; derived substates are all non-accepted) | `assignment_process_gate_smoketest.py` :218-221 (`APG-SEQUENCE-M2`), :243-244 (`-M3`), :246-249 (`-M4`) — verified | MOVE → G2 | none |
| `APG-PREREQUISITE@assignment_process_gate:validate#2f4e9d20da2a~0` (:518) | MISCONFIGURED, exit 4; runtime code is f-string `APG-PREREQUISITE-{key}` (M1–M4) | G2 / final-predecessors-accepted: `--stage final` requires accepted M1–M4, reported per-milestone. Kept at G2 (FINAL *drafting* readiness), not G3 — ship admission remains G3's job downstream | `assignment_process_gate_smoketest.py` :314-315 (verified: M4 `feedback_pending` → `APG-PREREQUISITE-M4`) | MOVE → G2 | none |

### _wiki_grounding_findings() — M4/FINAL grounding evidence (→ G2)

Fires only when target ∈ {M4, FINAL} (:510-511) — per-transition readiness
evidence for the late milestones, hash-bound end to end. All 17 rows: old
outcome MISCONFIGURED + `[BLOCKER]`, exit 4 (helper returns at most one
finding per invocation; branches are mutually exclusive in one run). The
suite asserts `APG-WIKI-GROUNDING-STALE` once (:293) but that case drifts
`references/REFERENCES.md`, exercising **only the :191 branch**; the other
13 STALE branches have no fixture (recorded B3-N6).

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `APG-WIKI-GROUNDING-MISSING@assignment_process_gate:_wiki_grounding_findings#422c7a4caa20~0` (:123) | MISCONFIGURED, exit 4 | G2 / wiki-evidence-or-opt-out-present: M4/FINAL requires a wiki-grounding binding or an authorized opt-out | `assignment_process_gate_smoketest.py` :261-265 (verified: M3 has no `policy_evidence`) | MOVE → G2 | none |
| `APG-WIKI-OPT-OUT-INVALID@assignment_process_gate:_wiki_grounding_findings#6bff11759961~0` (:125) | MISCONFIGURED, exit 4 | G2 / opt-out-is-object: opt-out must be an evidence-bound object | **none found for this branch** — :344 asserts the code but that case is a dict failing authority (→ :140) | MOVE → G2 | none |
| `APG-WIKI-OPT-OUT-INVALID@assignment_process_gate:_wiki_grounding_findings#2f36685c3ec6~0` (:140) | MISCONFIGURED, exit 4 | G2 / opt-out-authorized-and-bound: authority ∈ {user, advisor, instructor} (note: **planner excluded** — narrower than the G0-CONTRACT authority set, deliberately), nonempty reason, evidence file present with current hash | `assignment_process_gate_smoketest.py` :341-345 (verified: authority `planner` rejected, then `user` accepted at :346-351) | MOVE → G2 | none |
| `APG-WIKI-GROUNDING-STALE@assignment_process_gate:_wiki_grounding_findings#db258ee02536~0` (:146) | MISCONFIGURED, exit 4 | G2 / evidence-path-resolves: bound evidence path exists and stays inside the project | none found for this branch (see clause note) | MOVE → G2 | none |
| `APG-WIKI-GROUNDING-STALE@assignment_process_gate:_wiki_grounding_findings#c003267ccca4~0` (:148) | MISCONFIGURED, exit 4 | G2 / evidence-binding-hash-current: `evidence_sha256` in phase state matches the evidence file | none found for this branch | MOVE → G2 | none |
| `APG-WIKI-GROUNDING-STALE@assignment_process_gate:_wiki_grounding_findings#817a71366269~0` (:152) | MISCONFIGURED, exit 4 | G2 / evidence-parseable: evidence file reads as JSON | none found for this branch | MOVE → G2 | none |
| `APG-WIKI-GROUNDING-STALE@assignment_process_gate:_wiki_grounding_findings#ec1d5617fcd0~0` (:154) | MISCONFIGURED, exit 4 | G2 / evidence-is-object | none found for this branch | MOVE → G2 | none |
| `APG-WIKI-GROUNDING-STALE@assignment_process_gate:_wiki_grounding_findings#e38cf74c6bc1~0` (:161) | MISCONFIGURED, exit 4 | G2 / evidence-schema-complete: schema_version 1.0.0 + nine required nonempty string fields | none found for this branch | MOVE → G2 | none |
| `APG-WIKI-GROUNDING-STALE@assignment_process_gate:_wiki_grounding_findings#fc02675a4117~0` (:165) | MISCONFIGURED, exit 4 | G2 / evidence-produced-at-rfc3339 | none found for this branch | MOVE → G2 | none |
| `APG-WIKI-GROUNDING-STALE@assignment_process_gate:_wiki_grounding_findings#9575ae748b36~0` (:168) | MISCONFIGURED, exit 4 | G2 / evidence-binds-active-lineage: `lineage_id` == framework `primary_lineage_id` (default `live`) | none found for this branch | MOVE → G2 | none |
| `APG-WIKI-GROUNDING-STALE@assignment_process_gate:_wiki_grounding_findings#640b64acb4f9~0` (:180) | MISCONFIGURED, exit 4 | G2 / wiki-first-execution-recorded: `wiki_first_resources == true`, Planner authority, nonempty `skills_invoked` and `sources_consulted` | none found for this branch | MOVE → G2 | none |
| `APG-WIKI-GROUNDING-STALE@assignment_process_gate:_wiki_grounding_findings#32135c73212a~0` (:183) | MISCONFIGURED, exit 4 | G2 / wiki-path-present: declared `wiki_path` is an existing directory (may be outside the project — `_source_path`, not `_project_path`) | none found for this branch | MOVE → G2 | none |
| `APG-WIKI-GROUNDING-STALE@assignment_process_gate:_wiki_grounding_findings#7ba043447b9d~0` (:191) | MISCONFIGURED, exit 4 | G2 / references-bound-current: `references_path` inside the project, present, hash-current against `references_sha256` | `assignment_process_gate_smoketest.py` :289-294 (**verified branch**: REFERENCES.md drifted → hash mismatch) | MOVE → G2 | none |
| `APG-WIKI-GROUNDING-STALE@assignment_process_gate:_wiki_grounding_findings#cab5faa0558d~0` (:199) | MISCONFIGURED, exit 4 | G2 / graph-path-inside-wiki: `graph_path` resolves and does not escape `wiki_path` | none found for this branch | MOVE → G2 | none |
| `APG-WIKI-GROUNDING-STALE@assignment_process_gate:_wiki_grounding_findings#e43e408ca362~0` (:201) | MISCONFIGURED, exit 4 | G2 / graph-hash-current: graph file present, matches `graph_sha256_provenance` | none found for this branch | MOVE → G2 | none |
| `APG-WIKI-GROUNDING-STALE@assignment_process_gate:_wiki_grounding_findings#545ad5d8966f~0` (:211) | MISCONFIGURED, exit 4 | G2 / consulted-source-inside-wiki: each `sources_consulted[i]` resolves inside `wiki_path` | none found for this branch | MOVE → G2 | none |
| `APG-WIKI-GROUNDING-STALE@assignment_process_gate:_wiki_grounding_findings#d4b5a7e0310b~0` (:213) | MISCONFIGURED, exit 4 | G2 / consulted-source-hash-current: each consulted source present with current per-file hash | none found for this branch | MOVE → G2 | none |

### _ready_lines() — advisory (READY path)

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `APG-EXEMPLAR-DENNETT-PENDING@assignment_process_gate:_ready_lines#9b90d8bce1af~0` (:245) | READY, exit 0, with `[ADVISORY]` line (fires when target ∈ {M4, FINAL} ∧ exemplar requested ∧ contract `dennett_exemplar_status == "pending"`) | `G1-DISPATCH-AUTH` advisory / exemplar-source-pending: a contract-flagged exemplar source stays unavailable until grounded; conditioning on the grounded surface may proceed. **Hash-load-bearing**: this line participates in `gate_stdout_sha256`, so it is bound into receipts and checked at :411 (see B3-N7) | `assignment_process_gate_smoketest.py` :279-287 (verified: exit 0 + exact advisory prefix asserted) | KEEP (advisory) | none |

### Receipt path/shape helpers (→ G1-DISPATCH-AUTH; §3.1: never G1-APPROVAL)

`_receipt_path_finding` serves both the emit path (main:568) and the verify
path (verify_receipt:373); `_receipt_shape_finding` serves the verify path.
Old outcome for all six: MISCONFIGURED + `[BLOCKER]`, exit 4.

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `APG-RECEIPT-INVALID@assignment_process_gate:_receipt_path_finding#9767fd18534d~0` (:262) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / receipt-path-canonical: `reviews/.harness/assignment/gate_receipt_<target>_*.json` only | `assignment_dispatch_preflight_smoketest.py` :240-245 (verified: valid receipt copied outside the canonical dir; shape passes, path check fires via delegated `--verify-receipt`) | KEEP | none |
| `APG-RECEIPT-INVALID@assignment_process_gate:_receipt_shape_finding#c350756d5e5b~0` (:319) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / receipt-field-set-exact: field set == schema 1.0.0, no more, no less | **none found** — no suite constructs a wrong-field-set receipt | KEEP | none |
| `APG-RECEIPT-INVALID@assignment_process_gate:_receipt_shape_finding#71399188ee5a~0` (:323) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / receipt-id-uuid | **none found** | KEEP | none |
| `APG-RECEIPT-INVALID@assignment_process_gate:_receipt_shape_finding#9ec53067a95a~0` (:355) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / receipt-values-valid: the conjunctive value predicate (schema version, status enum, stage/target coherence incl. final→FINAL, planner authority, exit 0, four 64-hex digests, bool conditioning, lineage) | **none found** | KEEP — note: this single site carries a large conjunction; candidate for SPLIT **at implementation** if v1.0 wants per-field diagnostics, but as a predicate it is one validity rule | none |
| `APG-RECEIPT-INVALID@assignment_process_gate:_receipt_shape_finding#2b3225876932~0` (:357) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / ready-receipt-unconsumed: READY ⇒ `consumed_at` null | **none found** | KEEP | none |
| `APG-RECEIPT-INVALID@assignment_process_gate:_receipt_shape_finding#86151e6707e9~0` (:359) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / lifecycle-timestamp-required: non-READY ⇒ valid `consumed_at` | **none found** | KEEP | none |

### verify_receipt() (→ G1-DISPATCH-AUTH)

Old outcome for all ten: MISCONFIGURED + `[BLOCKER]`, exit 4 (the caller,
either `main --verify-receipt` or the dispatch preflight's delegation,
refuses the dispatch).

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `APG-RECEIPT-MISSING@assignment_process_gate:verify_receipt#d86ef67bd6e8~0` (:365) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / receipt-present | `assignment_process_gate_smoketest.py` :170-174 (verified). (The preflight's own missing-receipt check fires before delegation, so preflight cases do not reach this site) | KEEP | none |
| `APG-RECEIPT-INVALID@assignment_process_gate:verify_receipt#03ca8d828dcf~0` (:369) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / receipt-parseable (gate-side; preflight parses first, so this branch is reachable only via direct `--verify-receipt`) | **none found** — no suite feeds the gate a corrupt receipt directly | KEEP | none |
| `APG-RECEIPT-CONSUMED@assignment_process_gate:verify_receipt#c2de144df30f~0` (:379) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / receipt-single-use: a consumed receipt authorizes nothing further | `assignment_process_gate_smoketest.py` :209-216 (verified); also delegated via `assignment_dispatch_preflight_smoketest.py` :263-269 | KEEP | none |
| `APG-RECEIPT-INVALID@assignment_process_gate:verify_receipt#35270c5af0b0~0` (:381) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / receipt-not-invalidated | `assignment_dispatch_preflight_smoketest.py` :271-275 (verified: status flipped to `invalidated`, delegated verify) | KEEP | none |
| `APG-RECEIPT-INVALID@assignment_process_gate:verify_receipt#fa32c441b087~0` (:383) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / receipt-project-bound: `project_root_name` matches the invoking project | **none found** | KEEP | none |
| `APG-CONTRACT-MISSING@assignment_process_gate:verify_receipt#199d3f044549~0` (:387) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / bound-contract-present: the receipt-bound contract file must still exist at authorization time (re-verification instance of the G0-CONTRACT presence predicate; stays at G1 because it protects the authorization, not the bootstrap) | `assignment_dispatch_preflight_smoketest.py` :277-288 (verified: contract unlinked after emit, delegated verify refuses) | KEEP | none |
| `APG-RECEIPT-STALE@assignment_process_gate:verify_receipt#0c7ccb809d0e~0` (:397) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / bound-file-readable: a receipt-bound file (contract / phase state / profile) vanished or is unreadable | **none found for this branch** — suites drift content (→ :399); the deleted-contract case hits :387 first | KEEP | none |
| `APG-RECEIPT-STALE@assignment_process_gate:verify_receipt#01edf8151961~0` (:399) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / receipt-hashes-current: every bound digest (contract, phase state, profile) matches live bytes — the per-dispatch re-binding that lets the contract/profile predicates move to G0 without losing protection | `assignment_process_gate_smoketest.py` :196-206 (**verified branch**: phase_state drift); also delegated via preflight suite :252-260 | KEEP | none |
| `APG-RECEIPT-INVALID@assignment_process_gate:verify_receipt#059f7a8fc71b~0` (:411) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / stdout-digest-match: recomputed READY stdout (incl. any advisory line) equals `gate_stdout_sha256` | **none found** | KEEP | none |
| `APG-RECEIPT-INVALID@assignment_process_gate:main#c1b17ceabe89~0` (:539) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / verify-invocation-pure: `--verify-receipt` derives stage/target/conditioning from the receipt; supplying them is refused. Borderline usage-guard rather than transition predicate, but it protects against a verifier silently overriding receipt-bound parameters — kept as a predicate | **none found** | KEEP | none |

### main() — receipt emission guards (→ G1-DISPATCH-AUTH)

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `APG-RECEIPT-INVALID@assignment_process_gate:main#a9924732f31c~0` (:574) | MISCONFIGURED, exit 4 (after READY validation passed; no receipt written) | `G1-DISPATCH-AUTH` / receipt-no-overwrite: emission refuses an existing receipt path (single-use also at birth) | **none found** | KEEP | none |
| `APG-RECEIPT-INVALID@assignment_process_gate:main#278ac81e5a64~0` (:590) | MISCONFIGURED, exit 4 | `G1-DISPATCH-AUTH` / receipt-emittable: I/O or encoding failure while atomically writing the receipt refuses the dispatch rather than half-writing authorization | **none found** | KEEP | none |

### Batch 3 supplementary findings

- **B3-N1 — outcome-line emissions with no generated rows (all shapes: bare
  prints of outcome words, not codes).** `_print_findings` prints the bare
  `MISCONFIGURED` outcome word (:416); `_ready_lines` yields
  `READY assignment-process stage=… target=…` (:248); `main` prints
  `VERIFIED assignment-process receipt …` (:551-554) and
  `RECEIPT assignment-process path=…` (:593). None carries a finding code, so
  none has a row — correct at row granularity, but these are exactly the
  PASS-side surfaces the matrix §1.1 fixture manifest must preserve
  (`READY`/`VERIFIED` are asserted by both suites). Note the READY line at
  :248 is hash-load-bearing: it is digested into `gate_stdout_sha256`.
- **B3-N2 — `[BLOCKER] {code}` formatter (:418).** Pass-through f-string over
  findings; not an independent predicate; no row owed.
- **B3-N3 — f-string code families vs row labels.** :505 emits runtime codes
  `APG-SEQUENCE-{M2,M3,M4,FINAL}` under a row labeled `APG-SEQUENCE`, which
  textually collides with the *different* predicate at :461 (also labeled
  `APG-SEQUENCE`). :518 emits `APG-PREREQUISITE-{M1..M4}` under label
  `APG-PREREQUISITE`. Site-granularity keeps the rows distinct, but suites
  assert only the suffixed runtime forms — parity's code-presence check and
  the future fixture manifest `expected_code` fields must match the runtime
  suffixed codes, not the row labels.
- **B3-N4 — EXIT-ONLY paths, no rows owed.** `parser.error` at :558 (missing
  `--stage`) and argparse's own choice/mutual-exclusion validation exit 2
  with no code; `assert target is not None` (:564) is an internal invariant.
  All belong to the EXIT-ONLY contract class.
- **B3-N5 — O-2 mention-only candidates: none resolvable from this file.**
  The full source contains no occurrence of `W-DUAL-READ-LEGACY`,
  `W-SNOWBALL-PRECONDITION-UNMET`, `MF-POLICY-ATTESTATION-PIN-STALE`, or
  `MF-POLICY-EXEMPLAR-PIN-STALE` (read + grep). `APG-DISPATCH-REFUSED` was
  already resolved live in batch 1 (B1-N3). The four remaining O-2 candidates
  must be adjudicated against other components.
- **B3-N6 — fixture gaps (v1.0 corpus requirements).** No suite exercises:
  contract-unresolved (:432), source authority/presence/hash (:449/:456/:458),
  all five profile branches (:435-:445), assigned-sequence literal (:461),
  mapping (:463), phase-state-missing (:483), receipt shape branches
  (:319/:323/:355/:357/:359), gate-side receipt parse (:369), project-name
  mismatch (:383), bound-file-unreadable (:397), stdout-digest mismatch
  (:411), verify-args purity (:539), no-overwrite (:574), emit-I/O (:590),
  opt-out shape (:125), and 13 of 14 wiki-STALE branches (all except :191).
  That is 30 of 56 rows with no branch-attributable fixture.
- **B3-N7 — advisory text is welded into receipt authorization.** The
  `[ADVISORY] APG-EXEMPLAR-DENNETT-PENDING` line participates in
  `gate_stdout_sha256` (:296) and is re-derived at verification (:407-411),
  so *editing the advisory prose invalidates every live receipt* whose
  conditions included it. Design note for v1.0: either exclude advisory lines
  from the authorization digest or accept receipt churn on advisory edits.
  Also note the advisory is project-register-specific (Dennett/Yu, QE2026);
  its condition is contract-driven (`dennett_exemplar_status`), so the
  predicate generalizes to "contract-flagged exemplar source pending", which
  is how the New-predicate column states it.
- **B3-N8 — double trigger surface for validate() rows.** `verify_receipt`
  re-runs `validate()` in full (:404), so every G0/G2 row above currently
  fires on emission *and* on every verification. The G0 MOVEs rely on the
  hash re-binding rows (:399 family) to preserve the per-dispatch protection;
  if v1.0 drops the re-run without keeping the hash binding, the A-1
  preservation argument fails — flagged for the implementation-time re-check
  promised in the batch-2 frequency caveat.

---

## Batch 4 — scripts/milestone_framework_validate.py (153 rows) — ✅ SIGNED incl. :1756 RETIRE (user checkpoint 2026-07-16)

Emitter hash at adjudication: `e65541a44f76` (recomputed 2026-07-16; matches
`docs/analysis/generated/emitter_freeze.json` entry
`e65541a44f76d098424389f77a7461d7441b41019a1fa1a6232a1c62f35861af`).

Component reading: the read-only milestone validator — the canonical MFHP
semantics implementation. `validate_document()` is the shared integration
surface (docstring: used by `phase_state_validate.py`); `validate_gate()`
wraps it for the three pre-transition boundaries and is consumed by
`pre_phase_advance_check.py:269`. Contract: **MFHP-9**
(`references/MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md:124-131`):
READY | LEGACY_READY | NOT_APPLICABLE | MISCONFIGURED with exits 0/0/0/4;
usage errors exit 1, I/O exit 2 (MFHP:133, outside the outcome vocabulary).
Outcome computation (`_result`, :1850-1882): **any finding of any severity —
BLOCKER or MAJOR — forces MISCONFIGURED/exit 4**; severity never softens the
outcome. So "Old outcome" below is `MISCONFIGURED, exit 4` for every
`validate_document`-family row; `validate_gate`-only rows surface instead as
a gate finding (`GateValidationResult.exit_permitted=False`), which the
PRE-PHASE consumer reports as BLOCKED/exit 1
(`pre_phase_advance_phase_state_smoketest.py:220` asserts exactly that).

Routing rule used throughout (per the target vocabulary): milestone
**feedback** semantics → `G1-FEEDBACK`; **acceptance/approval/override
authority and evidence** → `G1-APPROVAL`; **structural/schema/lineage/event/
policy-binding consistency and per-transition readiness** → `G2`;
**Ph4-admission / terminal-close / export / MCR proof surfaces** → `G3`
(`G3-SIGNOFF` for anchored-signoff-status rows, per D-8). MF-EXEMPLAR rows
route to `G2` as credential-consistency predicates, kept as a **named,
unmerged family** per matrix §3.1 (external exemplar credentials — registry,
approval authority, evidence hash-binding, self-declaration detection —
never merged with `APG-EXEMPLAR-SCOPE`); the G2-vs-dedicated-credential-
surface placement question is flagged at S-9 for the checkpoint. All MOVEs
preserve trigger cardinality **by design intent** (validator already runs at
every boundary/preflight; v1.0 gate frequencies are unimplemented) — a design
claim, not a measurement; re-verify at implementation, as in Batch 2.
No site in this file naturally targets `G3-ESCALATION`/`G3-VERIFY`/
`G3-GROUNDING`, so this batch carries **zero** `PENDING-D4/5/6` rows.

Fixture abbreviations (all verified by grep to assert the code):
**MFS** = `scripts/milestone_framework_smoketest.py` (per-case table at
:66-:157 binds case_id → outcome/exit/target/code; exemplar cases
:1449-:1610); **PPS** = `scripts/pre_phase_advance_phase_state_smoketest.py`;
**DNR** = `scripts/domain_native_register_smoketest.py`;
**RRS** = `scripts/repin_register_smoketest.py`;
**RLS** = `scripts/render_lifecycle_state_smoketest.py` (+ its adversarial
twin). "Branch attribution unverified" = the suite asserts the code but the
case→site mapping was not proven row-by-row (B2-N4 debt applies here too).
Matrix §7 QE2026 replay context (2×READY; 1×MF-HANDOFF; 2×MF-EVENT;
reopened → 23 findings incl. MF-POLICY, MF-POLICY-PROVENANCE, MF-STRUCTURE)
is quoted from the review's run, not independently reproduced.

### validate_gate() — pre-transition boundary checks (6 rows)

Old outcome for this group: gate finding, `exit_permitted=False` → PRE-PHASE
BLOCKED exit 1 via `pre_phase_advance_check.py:269` (MFHP-9 exit 4 does not
apply to these six sites; they exist only on the gate path).

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `MF-GATE-CHAIN@milestone_framework_validate:validate_gate#63ef9cbf6028~0` (:172) | gate finding, BLOCKED exit 1 | G2 / predecessors-consumed: Ph1→Ph2 requires each applicable M1-M3 handoff consumed | PPS :105 | MOVE → G2 | none (cardinality preserved) |
| `MF-GATE-M4@milestone_framework_validate:validate_gate#c97b21e452a9~0` (:188) | gate finding, BLOCKED exit 1 | G3 / m4-admission: Ph4 admission requires accepted+approved M4 with ready/consumed F9 | PPS :110 | MOVE → G3 | none |
| `MF-PHASE@milestone_framework_validate:validate_gate#9b4fce32a2d3~0` (:193) | gate finding, BLOCKED exit 1 | G3 / convergence-signoff-present: canonical `ph3_convergence_signoff.md` exists at Ph4 admission (consistency predicate, not the collinearity artifact) | PPS :215, :220 (CLI path) | SPLIT → G3 (B-35) | none (B-35 ruled) |
| `MF-GATE-M5@milestone_framework_validate:validate_gate#b3ea04dec77a~0` (:210) | gate finding, BLOCKED exit 1 | G3 / m5-terminal-ready: terminal close requires accepted, dependency-current, approved M5 with ready/consumed F9 | PPS :132 | MOVE → G3 | none |
| `MF-GATE-M5@milestone_framework_validate:validate_gate#e58e0ea170c8~0` (:224) | gate finding, BLOCKED exit 1 | G3 / upstream-not-reopened: terminal close blocked while any M1-M4 is reopened or needs revalidation | PPS :151 | MOVE → G3 | none |
| `MF-GATE-M5@milestone_framework_validate:validate_gate#cb0b1bd150e0~0` (:231) | gate finding, BLOCKED exit 1 | G3-SIGNOFF / ship-signoffs-anchored: G4 + ph4 ship signoffs each carry exactly one `status: PASS\|APPROVED\|SIGNED` (D-8 exactly-one-anchored-status) | PPS :161, :170 (per-file/per-bad-status loop) | MOVE → G3-SIGNOFF (D-8) | none (ruled) |

### _validate_events() — event-ledger integrity (22 rows)

Event log survives in v1.0 (matrix A-13 rationale; §6 keeps feedback
adjudication and supersession as events). Status-conditioned rows are
CHANGE tracking the adopted §6 status machine (not_started/in_progress →
`open`; superseded → lineage event; feedback substates derived).

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `MF-EVENT@milestone_framework_validate:_validate_events#8b638aa433b7~0` (:253) | MISCONFIGURED, exit 4 | G2 / event-sequence-contiguous (append-only, unique, from 1) | MFS `unordered_events` (:130); branch attribution unverified | MOVE → G2 | none |
| `MF-EVENT@milestone_framework_validate:_validate_events#becd02c62ede~0` (:262) | MISCONFIGURED, exit 4 | G2 / event-timestamp-strict-utc (ISO-8601 Z only) | MFS `invalid_event_timestamp`/`_date_z`/`_offset`/`_naive`/`_malformed` (:136-:140) | MOVE → G2 | none |
| `MF-EVENT@milestone_framework_validate:_validate_events#c95c15c7ab67~0` (:266) | MISCONFIGURED, exit 4 | G2 / event-times-monotone (nondecreasing in sequence order) | MFS `unordered_events` (:130); branch attribution unverified | MOVE → G2 | none |
| `MF-EVENT@milestone_framework_validate:_validate_events#8ab08df6115b~0` (:276) | MISCONFIGURED, exit 4 | G2 / event-lineage-current (matches primary_lineage except supersession) | MFS MF-EVENT family (:129-:144); branch unverified | MOVE → G2 | none |
| `MF-EVENT@milestone_framework_validate:_validate_events#f0b9bb8f15ef~0` (:281) | MISCONFIGURED, exit 4 | G2 / event-evidence-hash-bound (via `_file_binding`; carries MF-CANON sub-branches) | MFS `event_artifact_binding_mismatch` (:134); branch unverified | MOVE → G2 | none |
| `MF-EVENT@milestone_framework_validate:_validate_events#c666e5c4bbdc~0` (:288) | MISCONFIGURED, exit 4 | G2 / event-bindings-hash-bound (each typed binding exact-byte) | same; branch unverified | MOVE → G2 | none |
| `MF-EVENT@milestone_framework_validate:_validate_events#a25ece83af41~0` (:295) | MISCONFIGURED, exit 4 | G2 / stale-causality-typed (downstream_stale/revalidated reference an earlier event of the required type) | MFS `stale_bad_cause` (:132) | MOVE → G2 | none |
| `MF-EVENT@milestone_framework_validate:_validate_events#f0dc58f1f194~0` (:297) | MISCONFIGURED, exit 4 | G2 / stale-causality-lineage (cause shares the affected lineage) | MFS MF-EVENT family; branch unverified | MOVE → G2 | none |
| `MF-EVENT@milestone_framework_validate:_validate_events#19d031f563ad~0` (:303) | MISCONFIGURED, exit 4 | G2 / stale-cause-upstream (genuinely upstream reopened milestone) | MFS MF-EVENT family; branch unverified | MOVE → G2 | none |
| `MF-EVENT@milestone_framework_validate:_validate_events#08d3d07b1b6b~0` (:305) | MISCONFIGURED, exit 4 | G2 / revalidation-cause-same-subject (references the stale event for the same milestone+lineage) | MFS `cross_subject_revalidation` (:144) | MOVE → G2 | none |
| `MF-EVENT@milestone_framework_validate:_validate_events#89621c67db4d~0` (:307) | MISCONFIGURED, exit 4 | G2 / causality-field-reserved (caused_by_sequence only on stale/revalidated) | none identified by case name; MFS asserts code family — branch unverified | MOVE → G2 | none |
| `MF-EVENT@milestone_framework_validate:_validate_events#fd44d24ba74d~0` (:337) | MISCONFIGURED, exit 4 | G1-FEEDBACK / feedback-event-evidence-bound (recorded/adjudicated events bind current feedback path+hash) | MFS `feedback_wrong_milestone_binding` (:143) | MOVE → G1-FEEDBACK | none |
| `MF-EVENT@milestone_framework_validate:_validate_events#b92e7f66f478~0` (:352) | MISCONFIGURED, exit 4 | G2 / state-event-correspondence (each ledger state justified by its required append-only event) — required set is status-derived | MFS `missing_accepted_event` (:129), `stale_without_event` (:131) | CHANGE (input: status enum per §6) | covered by adopted §6 |
| `MF-EVENT@milestone_framework_validate:_validate_events#027fcb66a59f~0` (:363) | MISCONFIGURED, exit 4 | G2 / override-event-evidence-bound (current override event binds authority + substitute evidence) | MFS MF-EVENT family; branch unverified | MOVE → G2 | none |
| `MF-EVENT@milestone_framework_validate:_validate_events#86d72495ce20~0` (:375) | MISCONFIGURED, exit 4 | G2 / no-phantom-lifecycle-events (not-started cannot retain unexplained lifecycle events) — conditions on a status §6 collapses into `open` | MFS `accepted_to_in_progress_old_events` (:141); branch unverified | CHANGE (input: status enum per §6) | covered by adopted §6 |
| `MF-EVENT@milestone_framework_validate:_validate_events#4164fc21890e~0` (:377) | MISCONFIGURED, exit 4 | G2 / latest-lifecycle-matches-status (allowed-latest map keyed by status) | MFS `obsolete_acceptance_event` (:133); branch unverified | CHANGE (input: allowed-latest map per §6) | covered by adopted §6 |
| `MF-EVENT@milestone_framework_validate:_validate_events#dac6a3ef6bc8~0` (:386) | MISCONFIGURED, exit 4 | G1-APPROVAL / acceptance-event-binds-deliverable (current acceptance binds accepted deliverable hash) | MFS `event_artifact_binding_mismatch` (:134); branch unverified | MOVE → G1-APPROVAL | none |
| `MF-EVENT@milestone_framework_validate:_validate_events#5a4ed5c71ce0~0` (:388) | MISCONFIGURED, exit 4 | G1-APPROVAL / acceptance-event-binds-approval (evidence_path equals approval evidence) | MFS MF-EVENT family; branch unverified | MOVE → G1-APPROVAL | none |
| `MF-EVENT@milestone_framework_validate:_validate_events#1332bfea46a9~0` (:394) | MISCONFIGURED, exit 4 | G2 / handoff-event-current (latest handoff event matches handoff status) | MFS `event_f9_binding_mismatch` (:135); branch unverified | MOVE → G2 | none |
| `MF-EVENT@milestone_framework_validate:_validate_events#033752279520~0` (:396) | MISCONFIGURED, exit 4 | G2 / handoff-event-binds-packet (binds the current F9 hash) | MFS `event_f9_binding_mismatch` (:135) | MOVE → G2 | none |
| `MF-EVENT@milestone_framework_validate:_validate_events#89e239e59cca~0` (:404) | MISCONFIGURED, exit 4 | G2 / handoff-reset-authorized (not_ready/not_applicable after prior handoff events requires a later reset-authorizing lifecycle event) | none identified by case name — branch unverified within MFS family | MOVE → G2 | none |
| `MF-EVENT@milestone_framework_validate:_validate_events#91a01a7cb81e~0` (:407) | MISCONFIGURED, exit 4 | G2 / dependency-state-event-consistent (cannot be current while latest dependency event is downstream_stale) | MFS `stale_without_event` (:131); branch unverified | MOVE → G2 | none |

### _file_binding() — canonical-path guard (2 rows)

Fixed-code MF-CANON emissions inside the shared binding helper; every
`call:_file_binding` row in this batch inherits these two sub-branches plus
the caller-coded read-failure/hash-mismatch branches (:625, :634).

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `MF-CANON@milestone_framework_validate:_file_binding#a39a5d545244~0` (:617) | MISCONFIGURED, exit 4 | G2 / path-canonical-contained (non-empty, resolves inside project root) | **none found** — no suite asserts `MF-CANON` (grep over scripts/); recorded S-6 | MOVE → G2 | none |
| `MF-CANON@milestone_framework_validate:_file_binding#90b35c1754e2~0` (:620) | MISCONFIGURED, exit 4 | G2 / bound-path-exists (canonical path is a file) | **none found** — S-6 | MOVE → G2 | none |

### _validate_feedback() (4 rows)

The G1-FEEDBACK core lives here (matrix §6: G1-FEEDBACK blocks acceptance
until feedback cleared; adjudication persists as events).

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `MF-FEEDBACK@milestone_framework_validate:_validate_feedback#a7ea40ac9a25~0` (:657) | MISCONFIGURED, exit 4 | G1-FEEDBACK / feedback-source-hash-bound | MFS `missing_feedback_provenance_real` (:81); branch unverified | MOVE → G1-FEEDBACK | none |
| `MF-FEEDBACK@milestone_framework_validate:_validate_feedback#91f58436c6ad~0` (:667) | MISCONFIGURED, exit 4 | G1-FEEDBACK / feedback-contemporaneity-bound | MFS `stale_feedback_contemporaneity_evidence` (:82) | MOVE → G1-FEEDBACK | none |
| `MF-LINEAGE@milestone_framework_validate:_validate_feedback#166943c3517d~0` (:677) | MISCONFIGURED, exit 4 | G1-FEEDBACK / feedback-lineage-matches-deliverable (feedback counts only against the milestone's primary deliverable line) | MFS MF-LINEAGE family (:83, :84); branch unverified | MOVE → G1-FEEDBACK | none |
| `MF-FEEDBACK@milestone_framework_validate:_validate_feedback#921229f190a0~0` (:679) | MISCONFIGURED, exit 4 | G1-FEEDBACK / blocking-feedback-adjudicated-before-handoff (the flagship §6 predicate) | MFS MF-FEEDBACK cases (:81, :82); branch unverified | MOVE → G1-FEEDBACK | none |

### _validate_artifacts() (9 rows)

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `MF-LINEAGE@milestone_framework_validate:_validate_artifacts#0274267fed0b~0` (:701) | MISCONFIGURED, exit 4 | G2 / deliverable-lineages-distinct | MFS `active_duplicate_lineage` (:107) | MOVE → G2 | none |
| `MF-LINEAGE@milestone_framework_validate:_validate_artifacts#baaab6043b0c~0` (:713) | MISCONFIGURED, exit 4 | G2 / supersession-target-valid (different, known lineage in same milestone) | MFS MF-LINEAGE family; branch unverified | MOVE → G2 | none |
| `MF-LINEAGE@milestone_framework_validate:_validate_artifacts#e20c0a31b091~0` (:725) | MISCONFIGURED, exit 4 | G2 / supersession-acyclic | MFS `cyclic_supersession` (:110) | MOVE → G2 | none |
| `MF-LINEAGE@milestone_framework_validate:_validate_artifacts#149ef4ee045a~0` (:733) | MISCONFIGURED, exit 4 | G2 / supersession-explicit — conditions on `status == "superseded"`, which §6 remaps to a lineage/history event | MFS `implicit_supersession` (:108) | CHANGE (input: superseded status → lineage event per §6) | covered by adopted §6 |
| `MF-LINEAGE@milestone_framework_validate:_validate_artifacts#7df0c1847469~0` (:743) | MISCONFIGURED, exit 4 | G1-APPROVAL / accepted-single-unsuperseded-primary (exactly one unsuperseded deliverable, on primary lineage) | MFS `accepted_unsuperseded_nonprimary` (:112) | MOVE → G1-APPROVAL | none |
| `MF-LINEAGE@milestone_framework_validate:_validate_artifacts#1a8d54caf4d5~0` (:747) | MISCONFIGURED, exit 4 | G1-APPROVAL / accepted-single-primary-deliverable (near-duplicate of :743; overlap noted for the v1.0 rewrite — jointly one invariant) | MFS `two_primary_lineages_real` (:83); branch unverified | MOVE → G1-APPROVAL | none |
| `MF-ROLE@milestone_framework_validate:_validate_artifacts#dbda705c9550~0` (:751) | MISCONFIGURED, exit 4 | G1-APPROVAL / accepted-deliverable-is-manuscript (M4/M5) | MFS `m4_plan_only_real` (:79), `m5_checklist_only_real` (:80) | MOVE → G1-APPROVAL | none |
| `MF-DERIVED@milestone_framework_validate:_validate_artifacts#af3788a9e0e2~0` (:766) | MISCONFIGURED, exit 4 (severity MAJOR — still blocks) | G2 / derived-view-marked (do-not-edit + derived_from + source_sha256) | MFS `malformed_derived_claim` (:90); RLS asserts MF-DERIVED | MOVE → G2 | none |
| `MF-STATUS@milestone_framework_validate:_validate_artifacts#a610b318b43c~0` (:774) | MISCONFIGURED, exit 4 (severity MAJOR — still blocks) | G2 / no-rival-status-authority (manual status doc cannot claim lifecycle authority — the "one authority" doctrine) | MFS `manual_status_claims_authority` (:91) | MOVE → G2 | none |

### _validate_packet() — F9 handoff packet (11 rows)

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `MF-HANDOFF@milestone_framework_validate:_validate_packet#3e22703895aa~0` (:799) | MISCONFIGURED, exit 4 | G1-APPROVAL / handoff-requires-approval (ready/consumed handoff only after approved evidence) | MFS `handoff_without_approval` (:47 area) / `ready_with_null_approval_evidence`; branch unverified | MOVE → G1-APPROVAL | none |
| `MF-HANDOFF@milestone_framework_validate:_validate_packet#3b218db55dc9~0` (:809) | MISCONFIGURED, exit 4 | G2 / packet-parseable (F9 is valid UTF-8 JSON) | MFS MF-HANDOFF family; branch unverified | MOVE → G2 | none |
| `MF-LINEAGE@milestone_framework_validate:_validate_packet#a864329fbc0f~0` (:815) | MISCONFIGURED, exit 4 | G2 / packet-lineage-current | MFS `artifact_lineage_mismatch` (:84); branch unverified | MOVE → G2 | none |
| `MF-HANDOFF@milestone_framework_validate:_validate_packet#50b8b3ef0367~0` (:819) | MISCONFIGURED, exit 4 | G2 / packet-source-matches-ledger (from_milestone) | MFS `forged_f9_from_milestone` (:98) | MOVE → G2 | none |
| `MF-HANDOFF@milestone_framework_validate:_validate_packet#c9e82b0602d4~0` (:824) | MISCONFIGURED, exit 4 | G2 / packet-successor-adjacent (to_milestone) | MFS `forged_f9_to_milestone` (:99) | MOVE → G2 | none |
| `MF-HANDOFF@milestone_framework_validate:_validate_packet#ea4f5307835c~0` (:829) | MISCONFIGURED, exit 4 | G2 / packet-project-identity-matches | MFS `forged_f9_project_identity` (:97) | MOVE → G2 | none |
| `MF-HANDOFF@milestone_framework_validate:_validate_packet#cda1338becfe~0` (:833) | MISCONFIGURED, exit 4 | G2 / packet-predecessor-chain (binds the prior packet exactly) | MFS MF-HANDOFF family; branch unverified | MOVE → G2 | none |
| `MF-BINDING@milestone_framework_validate:_validate_packet#3cb14496a586~0` (:838) | MISCONFIGURED, exit 4 | G2 / packet-deliverable-binding (role/path/sha256/bytes equal the ledger deliverable) | MFS MF-BINDING cases (:66, :87, :88); branch unverified | MOVE → G2 | none |
| `MF-EXPORT@milestone_framework_validate:_validate_packet#5e6d2f8ccf38~0` (:855) | MISCONFIGURED, exit 4 | G3 / terminal-export-binding (M5 packet released_export equals canonical export record) | MFS `terminal_f9_export_mismatch` (:121) | MOVE → G3 | none |
| `MF-HANDOFF@milestone_framework_validate:_validate_packet#a6b8ece9d1e4~0` (:867) | MISCONFIGURED, exit 4 | G1-APPROVAL / packet-approval-identity (authority, evidence path, time exactly match milestone approval) | MFS `mismatched_f9_approval_evidence` (:96), `fabricated_f9_authority` (:93) | MOVE → G1-APPROVAL | none |
| `MF-POLICY@milestone_framework_validate:_validate_packet#fe84c01d1cf7~0` (:873) | MISCONFIGURED, exit 4 | G2 / packet-policy-evidence-match | MFS MF-POLICY cases (:146-:157); branch unverified | MOVE → G2 | none |

### reader_policy_staleness_codes() (1 row)

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `MF-POLICY-PIN-EPOCH-STALE@milestone_framework_validate:reader_policy_staleness_codes#39056244c920~0` (:888) | contributes code to caller; production reachability caveat at S-2 (surfaces as MISCONFIGURED, exit 4 when emitted) | G2 / pin-epoch-current-at-cycle-open (binding epoch must not predate profile epoch when opening a new cycle) | RRS :241 (unit, both cycle modes), RRS :178-:189 (validator-level: continuing tolerated, opening blocked, rebound clears) | MOVE → G2 | none |

### _validate_reader_accessibility_policy() (31 rows)

All policy-binding consistency → G2. The `started()` helper (:1044-1046)
distinguishes `not_started`/`legacy_unverified` from `in_progress` — a
distinction §6 collapses — so `started()`-conditioned rows are CHANGE.
The epoch-gap / continuing-semantic-compatibility carve-outs (:936-:948,
LEGACY_READER_PROFILE_HASHES, v0.29.0 bounded migration) soften :978, :986,
:998 and the :957 staleness loop; that carve-out is itself version-scoped and
should sunset in v1.0 (noted S-10).

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#98541f8863fc~0` (:911) | MISCONFIGURED, exit 4 | G2 / native-binding-initialized (native mode requires the reader-accessibility binding) | MFS `policy_native_binding_omitted` (:150) | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#c423ce8dc8a8~0` (:916) | MISCONFIGURED, exit 4 | G2 / binding-is-object | MFS MF-POLICY family; branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#b3c048fed926~0` (:921) | MISCONFIGURED, exit 4 | G2 / policy-rederivable (resolver must succeed) | reader_accessibility_contract/semantics smoketests assert MF-POLICY; branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#84b5db259ebe~0` (:925) | MISCONFIGURED, exit 4 | G2 / source-binding-shape (scope ∈ {package, project}, path string) | same; branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#d977fbe01125~0` (:930) | MISCONFIGURED, exit 4 | G2 / source-binding-contained (no escape from declared root) | same; branch unverified | MOVE → G2 | none |
| `MF-POLICY-PROFILE-STALE@milestone_framework_validate:_validate_reader_accessibility_policy#30ddf1324d1d~0` (:950) | MISCONFIGURED, exit 4 | G2 / profile-path-canonical (binds the canonical package profile path) | RRS :225, :228; DNR :254; branch (path vs hash) unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#a950560bee45~0` (:970) | MISCONFIGURED, exit 4 | G2 / resolved-artifact-hash-bound | MFS `policy_hash_drift` (:146); branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#7f7b9282e802~0` (:974) | MISCONFIGURED, exit 4 | G2 / resolved-artifact-json | MFS/contract suites; branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#1679474e789a~0` (:978) | MISCONFIGURED, exit 4 | G2 / resolved-projection-current (stable keys equal fresh resolver output) | contract/semantics suites; branch unverified | MOVE → G2 | none |
| `MF-POLICY-PROVENANCE@milestone_framework_validate:_validate_reader_accessibility_policy#7be3f0780d98~0` (:986) | MISCONFIGURED, exit 4 | G2 / register-provenance-consistent (invariant keys + provenance paths match fresh resolver) | DNR :231, :236, :242 (per-key and per-field loops) | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#df1b082203a1~0` (:996) | MISCONFIGURED, exit 4 | G2 / package-source-contained | contract suites; branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#fd5c15932cfe~0` (:999) | MISCONFIGURED, exit 4 | G2 / package-source-current (present and hash-matching) | contract suites; branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#3476ff7c11bc~0` (:1001) | MISCONFIGURED, exit 4 | G2 / project-source-hash-bound | contract suites; branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#fa50f5512de7~0` (:1003) | MISCONFIGURED, exit 4 | G2 / source-scope-declared | contract suites; branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#e8ee5ff7a4f0~0` (:1014) | MISCONFIGURED, exit 4 | G2 / transition-evidence-hash-bound | MFS `policy_retired_without_events` (:154); branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#8adb7ddcfbc7~0` (:1017) | MISCONFIGURED, exit 4 | G2 / transition-sequence-monotone (append-only, unique increasing) | MFS MF-POLICY family; branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#a283bdd13309~0` (:1030) | MISCONFIGURED, exit 4 | G2 / observation-distinctness (one count per distinct cycle, distinct bound evidence) | MFS MF-POLICY family; branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#6c664e7aba18~0` (:1033) | MISCONFIGURED, exit 4 | G2 / observed-count-derived (counter equals approved observation events) | MFS MF-POLICY family; branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#9ae088940ea8~0` (:1036) | MISCONFIGURED, exit 4 | G2 / last-sequence-projection | MFS MF-POLICY family; branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#183e2a3dadda~0` (:1041) | MISCONFIGURED, exit 4 | G2 / retirement-earned (profile count reached + Planner-owned approval, last event) | MFS `policy_retired_without_events` (:154) | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#aa90ac96cb9c~0` (:1043) | MISCONFIGURED, exit 4 | G2 / no-premature-retirement-approval (active transition cannot carry one) | MFS MF-POLICY family; branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#a58b28d415dd~0` (:1050) | MISCONFIGURED, exit 4 | G2 / m1-reader-model-recorded (native M1 records canonical reader_model) — `started()`-conditioned | MFS `policy_missing_m1_intent` (:147) | CHANGE (input: started() status set per §6) | covered by adopted §6 |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#0b4411ae6cff~0` (:1053) | MISCONFIGURED, exit 4 | G2 / m3-policy-binding-complete (profile, resolved config, both semantic pins) — `started()`-conditioned | MFS `policy_missing_m3_profile` (:148) | CHANGE (input: started() status set per §6) | covered by adopted §6 |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#4a35b8377fac~0` (:1058) | MISCONFIGURED, exit 4 | G2 / no-fabricated-policy-evidence (not-started M4/M5 must carry none) — status-conditioned | MFS MF-POLICY family; branch unverified | CHANGE (input: status set per §6) | covered by adopted §6 |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#4ebfb3b66fcf~0` (:1067) | MISCONFIGURED, exit 4 | G2 / milestone-check8-evidence-complete (required field set widens at accepted) — `accepted` test includes `superseded`, which §6 remaps | MFS `policy_missing_m4_current_hash` (:149); branch unverified | CHANGE (input: accepted-set {accepted, superseded} per §6) | covered by adopted §6 |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#1a2b6c76f8e1~0` (:1070) | MISCONFIGURED, exit 4 | G2 / milestone-policy-binding-current (matches the ledger binding on all five identity fields) | MFS MF-POLICY family; branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#3aa024c1002e~0` (:1072) | MISCONFIGURED, exit 4 | G2 / check8-bound-to-current-manuscript | MFS `policy_missing_m4_current_hash` (:149); branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#9136d9777e66~0` (:1074) | MISCONFIGURED, exit 4 | G2 / check8-sidecar-hash-bound | MFS `policy_forged_check8_content` (:156); branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#5018426d1f46~0` (:1078) | MISCONFIGURED, exit 4 | G2 / check8-sidecar-json | MFS MF-POLICY family; branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#9371e38a28ec~0` (:1086) | MISCONFIGURED, exit 4 | G2 / check8-evidence-structurally-valid (PolicyError on validate/recompute) | MFS MF-POLICY family; branch unverified | MOVE → G2 | none |
| `MF-POLICY@milestone_framework_validate:_validate_reader_accessibility_policy#43ea1fa9593f~0` (:1090) | MISCONFIGURED, exit 4 | G2 / check8-recompute-match (fields + recomputed A-H aggregate + transition snapshot) | MFS `policy_forged_check8_content` (:156), `policy_forged_other_round` (:157) | MOVE → G2 | none |

### _project_evidence() — exemplar evidence acquisition (4 rows)

MF-EXEMPLAR family — kept distinct per matrix §3.1 and MFHP §13 (:159:
stable-snapshot acquisition rule).

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `MF-EXEMPLAR@milestone_framework_validate:_project_evidence#07c2d65c1bfc~0` (:1229) | MISCONFIGURED, exit 4 | G2 / exemplar-evidence-path-relative-contained | MFS exemplar cases (:1449-:1610); branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_project_evidence#4f260d208b27~0` (:1234) | MISCONFIGURED, exit 4 | G2 / exemplar-evidence-regular-nonreparse-file | same; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_project_evidence#fbbb9ffb2e24~0` (:1239) | MISCONFIGURED, exit 4 | G2 / exemplar-evidence-stable-read (snapshot capture refusal) | MFS race probes (:1591, :1610 assert MF-EXEMPLAR under racing) | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_project_evidence#e83256d7129a~0` (:1243) | MISCONFIGURED, exit 4 | G2 / exemplar-evidence-hash-current | MFS `stale_evidence_hash` (:1508) | MOVE → G2 | none |

### _project_prose_exemplar_claims() (2 rows)

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `MF-EXEMPLAR@milestone_framework_validate:_project_prose_exemplar_claims#5d9548438cfa~0` (:1309) | MISCONFIGURED, exit 4 | G2 / status-surface-readable (declared authority surfaces must be inspectable) | none identified by case name — MFS asserts family; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_project_prose_exemplar_claims#61672a1b6458~0` (:1312) | MISCONFIGURED, exit 4 | G2 / no-prose-self-declared-exemplar (AGENTS.md / CLAUDE.md / lifecycle_state.md) | MFS `agents_self_declaration` (:1471), `lifecycle_self_declaration` (:1474), `inf_prose_self_declaration` (:1486), claim-evasion loop (:1449, :1455) | MOVE → G2 | none |

### _validate_exemplar_registry() (32 rows)

External credential layer (MFHP §13, :153-:167). Registry is the sole
credential authority; project-local claims never substitute.

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#1627234a5090~0` (:1329) | MISCONFIGURED, exit 4 | G2 / no-ledger-self-declared-exemplar | MFS `ledger_self_declaration` (:1479) | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#9e9ea7890bf2~0` (:1338) | MISCONFIGURED, exit 4 | G2 / registry-parseable (stable snapshot + UTF-8 JSON) | MFS `malformed_registry` (:1569); branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#4ac69c08d88a~0` (:1341) | MISCONFIGURED, exit 4 | G2 / registry-shape (exactly schema_version 1.0.0 + entries array) | MFS `malformed_registry` (:1569); branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#0c64d832896d~0` (:1356) | MISCONFIGURED, exit 4 | G2 / entry-fields-exact (closed field set) | MFS exemplar cases; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#d564bf394908~0` (:1361) | MISCONFIGURED, exit 4 | G2 / entry-project-path-canonical-absolute | MFS exemplar cases; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#959f999e343a~0` (:1364) | MISCONFIGURED, exit 4 | G2 / entry-class-known (two classes only) | MFS exemplar cases; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#2bf4d960c770~0` (:1367) | MISCONFIGURED, exit 4 | G2 / entry-authority-permitted (credential-grant whitelist — §3.1 credential layer, distinct from G1-APPROVAL) | MFS exemplar cases; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#8ced60e8f804~0` (:1371) | MISCONFIGURED, exit 4 | G2 / entry-outcome-class-consistent (READY for clean, LEGACY_READY for legacy; strict UTC timestamp) — hard-codes MFHP-9 vocabulary, see S-7 | MFS exemplar cases; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#865e0bd1490e~0` (:1374) | MISCONFIGURED, exit 4 | G2 / entry-validator-version-explicit | MFS exemplar cases; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#f712f37ab1d1~0` (:1378) | MISCONFIGURED, exit 4 | G2 / entry-evidence-nonempty | MFS exemplar cases; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#67d6c016898d~0` (:1384) | MISCONFIGURED, exit 4 | G2 / evidence-item-shape (exactly role, path, sha256) | MFS exemplar cases; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#5dd15ac3a08d~0` (:1390) | MISCONFIGURED, exit 4 | G2 / evidence-roles-exact (unique, class-exact set) | MFS `unknown_evidence_role` (:1499) | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#6c469393b83d~0` (:1401) | MISCONFIGURED, exit 4 | G2 / registration-identity-unique (no duplicate/conflicting registrations per canonical identity) | MFS `duplicate_registration` (:1560), `conflicting_registration` (:1565) | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#40b7a40156d8~0` (:1416) | MISCONFIGURED, exit 4 | G2 / registration-validator-version-current (equals package manifest version) | MFS exemplar cases; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#cad76e121663~0` (:1421) | MISCONFIGURED, exit 4 | G2 / registered-snapshot-matches-document | MFS `stale_ledger_hash` (:1513); branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#cf204e5aa974~0` (:1423) | MISCONFIGURED, exit 4 | G2 / registered-snapshot-parseable | MFS exemplar cases; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#aca8b77a6757~0` (:1432) | MISCONFIGURED, exit 4 | G2 / approval-evidence-attested (explicit APPROVED + registered authority) | MFS exemplar cases; branch unverified | MOVE → G2 | none |
| `MF-DERIVED@milestone_framework_validate:_validate_exemplar_registry#fe53b2c7b677~0` (:1442) | MISCONFIGURED, exit 4 (severity MAJOR — still blocks) | G2 / lifecycle-view-bytes-current (registered derived view equals generated bytes; MFHP :167 dual MF-EXEMPLAR/MF-DERIVED on manual edit) | MFS `edited_generated_self_claim` (:1503); RLS suites assert MF-DERIVED | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#f29e52f5dcec~0` (:1449) | MISCONFIGURED, exit 4 | G2 / evidence-roles-complete-after-binding | MFS exemplar cases; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#a026845a8bd1~0` (:1456) | MISCONFIGURED, exit 4 | G2 / validator-evidence-attests-version-and-outcome | MFS exemplar cases; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#a64dbd6425fb~0` (:1463) | MISCONFIGURED, exit 4 | G2 / phase-validator-evidence-attests-pass | MFS exemplar cases; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#36ff360329a4~0` (:1477) | MISCONFIGURED, exit 4 | G2 / clean-exemplar-chain (native, accepted+approved+current M1-M5, consumed predecessors, ready/consumed terminal M5) | MFS exemplar cases; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#3c056106ef68~0` (:1481) | MISCONFIGURED, exit 4 | G2 / lifecycle-view-derived-from-current-ledger (generated marker + source_sha256 of phase_state) | MFS `edited_generated_self_claim` (:1503); branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#73b89baad3f0~0` (:1485) | MISCONFIGURED, exit 4 | G2 / release-gate-and-replay-attest-pass | MFS exemplar cases; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#b9cd517e62e0~0` (:1489) | MISCONFIGURED, exit 4 | G2 / legacy-exemplar-boundary-present (mode legacy + approved migration boundary) | MFS legacy exemplar cases (:1533-:1554); branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#0f4ca024542c~0` (:1494) | MISCONFIGURED, exit 4 | G2 / migration-evidence-binds-boundary (report + approval bind the approved boundary paths/hashes) | MFS `legacy_rejected_report_rehashed` (:1533); branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#563671939259~0` (:1503) | MISCONFIGURED, exit 4 | G2 / boundary-authority-permitted (migration-boundary authority on the permitted ladder) | MFS `legacy_nobody_authority_rehashed` (:1554) | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#396800ba41f4~0` (:1505) | MISCONFIGURED, exit 4 | G2 / migration-report-approved-by-boundary-authority | MFS `legacy_rejected_report_rehashed` (:1533); branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#f837282fcbb2~0` (:1512) | MISCONFIGURED, exit 4 | G2 / migration-approval-attested (explicit APPROVED + boundary authority) | MFS `legacy_rejected_approval_rehashed` (:1541) | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#d04128701e88~0` (:1532) | MISCONFIGURED, exit 4 | G2 / migration-commit-manifest-bound (committed transaction binds current ledger, approved report, manifest) | MFS legacy cases; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#eb5b59e3b4f0~0` (:1535) | MISCONFIGURED, exit 4 | G2 / rollback-verification-attests-pass | MFS legacy cases; branch unverified | MOVE → G2 | none |
| `MF-EXEMPLAR@milestone_framework_validate:_validate_exemplar_registry#f92958b25311~0` (:1539) | MISCONFIGURED, exit 4 | G2 / exemplar-inputs-stable-throughout (verify_all after validation) | MFS race probes (:1591, :1610) | MOVE → G2 | none |

### validate_document() — namespace, chain, override, export, target readiness (29 rows)

Includes 11 of the 12 `MF-PHASE` sites (the 12th is `validate_gate` :193
above). Per **B-35**: MF-PHASE is a SPLIT — 12 sites carrying several
consistency predicates; the consistency predicates (MCR admission recorded,
deep pass complete, proof surface present, ceiling honored, terminal signoff
evidenced, milestone-status readiness) are **preserved**; only the
collinearity artifact — the phase enum cross-checked against the milestone
namespace — is a retirement CANDIDATE, adjudicated here as exactly one site
(:1756). Sites whose predicate content survives but whose *vocabulary input*
is the phase enum carry the input change explicitly.

| Row ID | Old outcome | New predicate | Fixture | Disp | Appr |
|---|---|---|---|---|---|
| `MF-STRUCTURE@milestone_framework_validate:validate_document#97b0b05ab9b3~0` (:1552) | MISCONFIGURED, exit 4 | G2 / document-is-object | MFS MF-STRUCTURE cases (:77, :78); branch unverified | MOVE → G2 | none |
| `MF-STRUCTURE@milestone_framework_validate:validate_document#33b9485b4536~0` (:1559) | MISCONFIGURED, exit 4 | G2 / no-retired-namespace (`milestone_assignment` forbidden in current ledgers) | MFS `retired_milestone_assignment` (:145) | MOVE → G2 | none |
| `MF-STRUCTURE@milestone_framework_validate:validate_document#6394ace2bd67~0` (:1561) | MISCONFIGURED, exit 4 | G2 / sections-is-object | MFS `list_shaped_sections` (:127) | MOVE → G2 | none |
| `MF-STRUCTURE@milestone_framework_validate:validate_document#16cea78cef6f~0` (:1563) | MISCONFIGURED, exit 4 | G2 / framework-namespace-present | MFS `absent_namespace` (:77); PPS :86, :100 (gate path); DNR :262 | MOVE → G2 | none |
| `MF-HANDOFF@milestone_framework_validate:validate_document#899f98b27f4b~0` (:1584) | MISCONFIGURED, exit 4 | G2 / project-identity-consistent (manuscript_id vs policy project_identity) | MFS `project_identity_disagreement` (:101) | MOVE → G2 | none |
| `MF-HANDOFF@milestone_framework_validate:validate_document#ca54db0fdd42~0` (:1599) | MISCONFIGURED, exit 4 | G2 / handoff-identity-present (ledger-bound F9s require an authoritative project identity) | MFS `native_missing_project_identity` (:100), `legacy_handoffs_without_project_identity` (:102) | MOVE → G2 | none |
| `MF-HANDOFF@milestone_framework_validate:validate_document#f32d7c2de639~0` (:1618) | MISCONFIGURED, exit 4 | G1-APPROVAL / approval-authority-permitted | MFS `fabricated_matching_authority` (:94), `list_shaped_approval` (:92); branch unverified | MOVE → G1-APPROVAL | none |
| `MF-HANDOFF@milestone_framework_validate:validate_document#ccf6d1e4bab9~0` (:1625) | MISCONFIGURED, exit 4 | G1-APPROVAL / approval-evidence-exists-in-project | MFS `missing_approval_evidence` (:95) | MOVE → G1-APPROVAL | none |
| `MF-HANDOFF@milestone_framework_validate:validate_document#ca426c2b6b83~0` (:1638) | MISCONFIGURED, exit 4 | G2 / predecessor-chain-ordered (successor work only after predecessor approved + consumed handoff) — conditions on statuses §6 collapses | MFS `successor_without_consumed_handoff` (:85) | CHANGE (input: "started" status set per §6) | covered by adopted §6 |
| `MF-REOPEN@milestone_framework_validate:validate_document#185172546707~0` (:1655) | MISCONFIGURED, exit 4 | G2 / reopen-propagates-staleness (downstream cannot stay dependency-current after upstream reopen; §6 keeps `reopened` distinct) | MFS `reopened_upstream_current_downstream` (:89), `re_m2_reopened_blocks_m5` (:67) | MOVE → G2 | none |
| `MF-OVERRIDE@milestone_framework_validate:validate_document#41ccdd98a528~0` (:1662) | MISCONFIGURED, exit 4 | G2 / migration-boundary-evidence-bound (legacy boundary evidence + report hash-bound) | MFS `legacy_without_migration_boundary` neighborhood; branch unverified | MOVE → G2 | none |
| `MF-OVERRIDE@milestone_framework_validate:validate_document#fe454a4d323b~0` (:1670) | MISCONFIGURED, exit 4 | G1-APPROVAL / override-complete (not_applicable requires a complete authorized override) | MFS `na_without_complete_override` (:86) | MOVE → G1-APPROVAL | none |
| `MF-OVERRIDE@milestone_framework_validate:validate_document#184f33ed5087~0` (:1674) | MISCONFIGURED, exit 4 | G1-APPROVAL / override-authority-permitted | MFS `rejected_generator_override` (:103); branch unverified | MOVE → G1-APPROVAL | none |
| `MF-OVERRIDE@milestone_framework_validate:validate_document#929f13cdbd80~0` (:1679) | MISCONFIGURED, exit 4 | G1-APPROVAL / override-rule-resolves (anchored rule in authority-appropriate reference or contained project-local contract) | MFS `missing_project_local_override` (:123), `outside_...` (:124), `absolute_...` (:125) | MOVE → G1-APPROVAL | none |
| `MF-OVERRIDE@milestone_framework_validate:validate_document#6cd31194f636~0` (:1690) | MISCONFIGURED, exit 4 | G1-APPROVAL / override-substitute-evidence-bound | MFS `stale_override_evidence` (:126) | MOVE → G1-APPROVAL | none |
| `MF-EXPORT@milestone_framework_validate:validate_document#0629589aca0e~0` (:1698) | MISCONFIGURED, exit 4 | G3 / m5-released-export-present (accepted M5 requires an export on the primary lineage) | MFS MF-EXPORT cases; `export_without_source_binding` neighborhood; branch unverified | MOVE → G3 | none |
| `MF-EXPORT@milestone_framework_validate:validate_document#34cbfef11728~0` (:1710) | MISCONFIGURED, exit 4 | G3 / export-source-binding-current (export source hash/path match the accepted manuscript) | MFS `export_source_mismatch` (:120) | MOVE → G3 | none |
| `MF-HANDOFF@milestone_framework_validate:validate_document#9b1f107174f4~0` (:1740) | MISCONFIGURED, exit 4 | G2 / milestone-target-ready (accepted + dependency-current + approved + ready/consumed F9; legacy boundary coverage honored) — consumed by G2 at Ph1→Ph2 and by G3 for M4/M5 targets via the boundary map | MFS `native_m5_not_started_target` (:73), `legacy_m3_boundary_m5_target` (:75) | MOVE → G2 | none |
| `MF-PHASE@milestone_framework_validate:validate_document#5393a66bf3fb~0` (:1756) | MISCONFIGURED, exit 4 | **collinearity artifact** — Ph2 target cross-checked against the section phase enum; its consistency content ("work has actually reached review readiness") is carried in v1.0 by milestone status (:1759 site) + §6 | MFS MF-PHASE cases (:113-:119); branch unverified | SPLIT (B-35) → **RETIRE — APPROVED**; replacement named: `MF-PHASE@milestone_framework_validate:validate_document#cf1fb683fc57~0` (:1759) under the §6 status machine | ✅ **user-approved 2026-07-16** (batch-4 checkpoint, "Approve incl. :1756 RETIRE"; B-35 named this the sole candidate) |
| `MF-PHASE@milestone_framework_validate:validate_document#cf1fb683fc57~0` (:1759) | MISCONFIGURED, exit 4 | G2 / target-milestone-active-or-accepted (Ph2→M4, Ph4→M5) — status set {in_progress, feedback_pending, revision_required, accepted} is exactly the enum §6 remaps (two of the four become derived substates) | MFS MF-PHASE cases; branch unverified | SPLIT (B-35) + CHANGE input (status enum per §6) | covered by adopted §6; B-35 ruled |
| `MF-PHASE@milestone_framework_validate:validate_document#1e6fe1db99de~0` (:1767) | MISCONFIGURED, exit 4 | G3 / ship-proof-surface-nonempty (at least one section with an MCR or ceiling-lock proof surface) | MFS `ph4_empty_sections` (:116) | SPLIT → G3 (B-35) | none (B-35 ruled) |
| `MF-PHASE@milestone_framework_validate:validate_document#3b57bd5f28e9~0` (:1772) | MISCONFIGURED, exit 4 | G3 / ceiling-vocabulary-legal (default_final_phase) — vocabulary input is the phase enum, renamed under the v1.0 milestone vocabulary | MFS MF-PHASE cases; branch unverified | SPLIT → G3 (B-35); vocab input renamed | none (B-35 ruled; re-sign if the ceiling vocabulary mapping changes) |
| `MF-PHASE@milestone_framework_validate:validate_document#61d94473a9c9~0` (:1779) | MISCONFIGURED, exit 4 | G3 / proof-surface-is-object | MFS `ph4_nonobject_section` (:117) | SPLIT → G3 (B-35) | none (B-35 ruled) |
| `MF-PHASE@milestone_framework_validate:validate_document#5deabd8eb895~0` (:1788) | MISCONFIGURED, exit 4 | G3 / section-ceiling-override-legal (null or legal vocabulary) — phase-enum input, renamed per v1.0 | MFS `ph4_list_ceiling_override` (:118), `ph4_dict_ceiling_override` (:119) | SPLIT → G3 (B-35); vocab input renamed | none (B-35 ruled) |
| `MF-PHASE@milestone_framework_validate:validate_document#960740047de8~0` (:1804) | MISCONFIGURED, exit 4 | G3 / unlocked-section-at-terminal-stage (non-ceiling-locked section must be at the terminal stage after MCR admission) — phase-enum input | MFS `inf_unlocked_ph3_sibling_blocks_ph4` (:114); branch unverified | SPLIT → G3 (B-35); vocab input renamed | none (B-35 ruled) |
| `MF-PHASE@milestone_framework_validate:validate_document#cd6febe04bb7~0` (:1820) | MISCONFIGURED, exit 4 | G3 / mcr-admission-recorded (explicit unretracted admission transition row) — trigger/phase vocabulary renamed per v1.0 event vocabulary | MFS `ph4_without_mcr_admission` (:113), `ph4_retracted_mcr_admission` (:115) | SPLIT → G3 (B-35); vocab input renamed | none (B-35 ruled) |
| `MF-PHASE@milestone_framework_validate:validate_document#9441896afef5~0` (:1827) | MISCONFIGURED, exit 4 | G3 / pre-ship-deep-pass-complete (pairs with matrix D-3 hash-binding discipline) | MFS MF-PHASE cases; branch unverified | SPLIT → G3 (B-35) | none (B-35 ruled) |
| `MF-PHASE@milestone_framework_validate:validate_document#8626adb2e046~0` (:1832) | MISCONFIGURED, exit 4 | G3 / valid-proof-surface-exists (no section survived the per-section checks ⇒ block) | MFS `ph4_retracted_mcr_admission` (:115); branch unverified | SPLIT → G3 (B-35) | none (B-35 ruled) |
| `MF-PHASE@milestone_framework_validate:validate_document#3ec99a507598~0` (:1843) | MISCONFIGURED, exit 4 | G3 / terminal-convergence-signoff-evidenced (`is_terminal: true` in the convergence signoff when any section needs terminal signoff) | MFS MF-PHASE cases; PPS :215; branch unverified | SPLIT → G3 (B-35) | none (B-35 ruled) |

### Batch 4 supplementary findings

- **S-1 — O-2 resolution: `MF-POLICY-ATTESTATION-PIN-STALE` and
  `MF-POLICY-EXEMPLAR-PIN-STALE` are LIVE, not mention-only.** Both are
  emitted at :957-:959: `reader_policy_staleness_codes` (:879-:889) returns
  them from its checks table (:882-:884) whenever the stored
  attestation/exemplar view pin differs from current policy and neither the
  epoch-gap nor the v0.29.0 continuing-compatibility carve-out applies; the
  loop maps each code to a field/message (:952-:956) and appends a BLOCKER →
  MISCONFIGURED exit 4. Fixture-asserted: DNR :246 (attestation), :250
  (exemplar), :258 (carve-out suppresses both), RRS :236-:237 (unit table).
  Strike both from the matrix §8 O-2 candidate list at checkpoint.
- **S-2 — rowless dynamic emissions (code-as-variable `_finding` shape).**
  The census generated no rows for the two dynamic emissions at :959
  (codes: `MF-POLICY-PROFILE-STALE` / `MF-POLICY-ATTESTATION-PIN-STALE` /
  `MF-POLICY-EXEMPLAR-PIN-STALE`) and :969 (`MF-POLICY-PIN-EPOCH-STALE`),
  nor for the helper list-return at :896 (`policy_epoch_findings`). It
  attributed the helper literals instead: the :888 row (append inside
  `reader_policy_staleness_codes`) and the :950 literal. Consequence for the
  :888 row above: **inside this emitter the only production call passes
  `opening_new_cycle=False` (:957), so the :888 append is unreachable on this
  file's own validation path**; the live epoch predicate flows through
  `policy_epoch_findings` (:892-:896) into :968-:969. The helper is a public
  API exercised directly by RRS :241 and remains the correct unit to
  preserve. Not adjudicated as dead — adjudicated as the pin-epoch predicate
  with its production emission at :969. Census follow-up owed (post-freeze):
  cover `_finding(<variable>, ...)` and helper-return code shapes.
- **S-3 — rowless default-code `_file_binding` call sites (two live
  predicates with no generated row).** `_validate_artifacts` :756-:760
  (accepted-milestone artifact bytes binding) and `_validate_packet`
  :800-:803 (F9 packet bytes binding) call `_file_binding` without an
  explicit `code=` argument, so they emit the default `MF-BINDING` (plus the
  shared MF-CANON branches) — and the census's `call:_file_binding`
  attribution missed them while catching every explicit-code call. Both are
  live, fixture-asserted predicates: MFS `stale_deliverable_hash` (:87),
  `re_m5_manuscript_changed` (:66) for the artifact binding;
  `stale_f9_packet_hash` (:88) for the packet binding; PPS :156 asserts
  MF-BINDING on the gate path. Adjudicated here without inventing row IDs:
  artifact-bytes-current → **G1-APPROVAL** (fires only on accepted
  milestones; acceptance-evidence integrity), packet-bytes-current → **G2**.
  Both KEEP-equivalent MOVEs, no approval. Census follow-up owed
  (default-argument call shape), post-freeze.
- **S-4 — rowless schema-conformance emission (one site, seven codes).**
  `_schema_findings` :547 emits `_finding(_schema_code(path, msg), ...)` —
  a dynamic code from the `_schema_code` map (:410-:424: MF-OVERRIDE /
  MF-FEEDBACK / MF-EVENT / MF-LINEAGE / MF-HANDOFF / MF-ROLE /
  MF-STRUCTURE). It carries the entire Draft 2020-12 conformance surface for
  `milestone_framework.schema.json` (:1568) and the F9 packet schema (:811),
  and has **no generated row**. Adjudicated in supplement: G2 /
  schema-conformance, one predicate family per schema — and a **§6
  dependency**: the milestone schema's status enum must be regenerated with
  the adopted status machine, so this family is CHANGE-covered-by-§6 at the
  schema level. Fixtures: MFS structure/role/feedback cases (:77-:81) reach
  it; branch attribution unverified. Census follow-up owed.
- **S-5 — non-outcome exits are contract-clean.** Usage errors exit 1
  (`UsageArgumentParser.error`, :62-:64; `parser.error` at :1905) and
  unreadable/unparseable `phase_state.json` exits 2 (:1907-:1911), matching
  MFHP:133's exit categories exactly. Not predicates; no rows; nothing owed.
- **S-6 — MF-CANON fixture gap.** No suite anywhere under `scripts/` asserts
  `MF-CANON` (grep 2026-07-16). The two `_file_binding` MF-CANON rows are
  code-level only. Recorded as a v1.0 corpus requirement alongside B1-N2 and
  B2-N2: cases for a path escaping the project root and a dangling bound
  path.
- **S-7 — outcome-vocabulary coupling in the exemplar registry.** :1369-:1371
  hard-code `READY`/`LEGACY_READY` as the class-expected registry outcomes,
  and registered evidence records the same tokens (:1455). If v1.0 renames
  the MFHP-9 vocabulary, registry entries, this predicate, and MFHP §13 must
  migrate together — a cross-artifact migration dependency not visible from
  any single row.
- **S-8 — QE2026 replay coverage (matrix §7, quoted not reproduced).** The
  replay exercises MF-HANDOFF, MF-EVENT (×2), MF-POLICY,
  MF-POLICY-PROVENANCE, MF-STRUCTURE and two READY outcomes — live-project
  PASS/BLOCK evidence for exactly the MF-HANDOFF/MF-EVENT/MF-POLICY rows
  above whose MFS attribution is branch-unverified. It should be pinned as
  a named fixture set in the v1.0 corpus.
- **S-9 — placement question for the checkpoint: MF-EXEMPLAR family gate.**
  All 37 MF-EXEMPLAR-family sites (here: 4 + 2 + 31 of the 32 registry rows;
  the 32nd is MF-DERIVED) are routed to G2 as credential-consistency
  predicates, preserved as an unmerged named family per §3.1. If the v1.0
  design wants credential checking at a different surface (e.g., only when a
  credential is actually claimed/consumed rather than on every G2 pass),
  that is a MOVE crossing a frequency boundary and needs explicit approval;
  routed to G2 it preserves today's every-validation cardinality.
- **S-10 — v0.29.0 carve-outs must sunset.** `LEGACY_READER_PROFILE_HASHES`
  (:45-:49) and the `continuing_semantic_compatibility` projection-migration
  tolerance (:938-:948) are explicitly bounded to the v0.29.0 migration.
  They soften rows :950(else-branch), :978, :986, :998. The v1.0 rewrite
  should either carry them as an explicit LEGACY_READY-class migration rule
  or retire them with the migration — an approval-bearing decision that is
  **not** taken in this batch; the rows above adjudicate the predicates with
  the carve-out noted as a version-scoped input.
- **S-11 — outcome computation itself has no rows.** `_result` (:1850-:1882)
  decides READY / LEGACY_READY / NOT_APPLICABLE / MISCONFIGURED (including
  the legacy-boundary READY-beyond-coverage rule at :1867-:1873 and the
  NOT_APPLICABLE short-circuit) and emits no findings, so the census
  correctly generated no rows — but its outcome classes are exactly the
  matrix §7 preservation classes (PASS cases, LEGACY_READY, NOT_APPLICABLE
  short-circuit). Preservation of this logic rides on the §7 fixture
  classes, not on any row in this batch; MFS PASS cases (`valid_native_chain`,
  `re_manuscript_bound_chain`, READY/exit-0 rows at :64-:65 and the
  `valid_not_applicable_empty_records` exit-0 case) are the falsifiability
  anchors.

**Batch 4 tally (computed from the tables above):** 153 rows =
**132 MOVE** (no approval; cardinality preserved by design intent) +
**9 CHANGE** (all input-named, all covered by the adopted §6 status machine:
:352, :375, :377, :733, :1050, :1053, :1058, :1067, :1638) +
**12 SPLIT** (the B-35 MF-PHASE sites, incl. :1759 which also carries a §6
input change), of which **1 is the B-35 retirement — APPROVED at the batch-4
user checkpoint 2026-07-16** (:1756, replacement :1759 named; see header
status block and matrix §9.1 addendum, which agree).
**PENDING-D4/D5/D6: 0.** Gate targets: G2 ×117, G3 ×16, G3-SIGNOFF ×1,
G1-FEEDBACK ×5, G1-APPROVAL ×13, plus the one retire-candidate (:1756) whose
replacement is a named existing row rather than a new target
(117+16+1+5+13+1 = 153; per-row assignments above are authoritative).
