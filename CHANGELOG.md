# Changelog — co-author-harness

Package-level changelog tracking substantive architectural changes, lessons learned across release cycles, and proposed-and-approved package improvements. Version-by-version narrative is mirrored in `README.md §Version`; this file adds the meta-learning layer (lessons, proposals, recurrence tracking) that `README.md` does not carry.

Format follows the co-author-harness Reflector convention: each entry records *what*, *why*, and *how to apply*, with severity and agent attribution where applicable.

---

## v0.50.0 — 2026-08-20

### M1→M2→M3→M4 flow repair

**Version identity.** SemVer corrected from 0.5.0 to 0.50.0. The 0.5.0 identifier was semantically older than 0.43.0, preventing proper version ordering. 0.50.0 is monotonically newer than 0.43.0 and aligns with the intended 0.50 kernel identity.

**Evaluation-lane restoration.** The evaluation-lane behavior is restored from dest-safe-only fail-close. Mechanical dest-safe obligations (`d-style-profile`, `deterministic-audit`) run. Scholarly and governance obligations are deferred as `not_run` shells (honest deferral, not CLEAN). Centroid obligations fail-close when `semantic_usage=not_invoked` or receipt absent. Scholarly CLEAN is still not minted; DEST-PROTECTED remains enforced.

**Grounding Protocol Rule 6 enforcement.** Rule 6 (no plausible fabrication) now has documented precedence over named-case pressure and "concrete detail" guidance. Generator must leave marked gaps (`[FACT NEEDED]`) rather than inventing plausible scenes when no vault/plan case exists. This binding is documented in `generator.md` and `run-draft/SKILL.md`.

**Writer contract unification.** Generator stages only; Writer (outside plugin) applies exact path+hash after Joseph accepts. `generator.md` updated to match `run-draft/SKILL.md`: Generator is not the manuscript writer, Generator is the stager. Leftover in-place procedure language (direct M4/revision-log writes) is restaged through `assignment_writer_commit.py`. DEST-PROTECTED maintained. SK-32 `/run-generator-session` is `CLOSED_PUBLIC_BYPASS` with an unconditional refuse: no write path even when Evaluator findings and F6 are on disk.

**General `AGENTS.md` only.** Package-root `CLAUDE.md` and `references/CLAUDE.md` are removed. Invocation rules live in `AGENTS.md` and `references/AGENTS.md`. This package is not a Claude-specific instruction surface.

**Token-budget check removed.** `scripts/token_budget_check.py` and `scripts/token_budget_smoketest.py` are deleted. The package-surface debt ratchet is not a live gate. `TOKEN_BUDGET_PROTOCOL.md` remains advisory for long-manuscript segmentation.

**run-phase-1 invocability.** The `run-phase-1` skill is marked `user-invocable: false` to prevent model invocation. It remains on disk as a parked paper-specific compatibility body per the 0.50 kernel spec.

**Receipt metadata.** Evaluation transactions now bind host identity, prompt-package identity/hash, and input artifact paths+hashes. Evaluate operations refuse to proceed without these receipt fields. This closes the generation/evaluate transaction binding gap.

**Milestone-contract slice (2026-08-21).** Clarified R-plane authority and milestone acceptance contract. Joseph is the only R-plane actor; no agent promotes research artifacts. Milestone accepts are ongoing until M5 is produced; a prior accept is the current working hash, not a freeze. Any iteration may require revision of any of M1–M4. Updated kernel spec, planner, run-draft, and run-iterate to document this contract. DEST-PROTECTED and Writer-stages-only remain unchanged.

**Scholarly-evaluation-lane slice (2026-08-21).** c84b430 stamped scholarly obligations dest-safe as completed/INFO (“fired; requires evaluator dispatch”). That stamp is not scholarly fire. Superseded the same day by the repair below.

**Scholarly-evaluation-lane repair (2026-08-21).** Undo the c84b430 dest-safe completed/INFO scholarly stamp. Evaluation-lane runs mechanical dest-safe preflight only (`d-style-profile`, `deterministic-audit`). Scholarly rows fail closed with a blocking MAJOR finding (`EVALUATOR-FIRE-REQUIRED`: Evaluator must fire the skill on these bytes). Evaluate `verify` refuses dest-safe INFO/ADVISORY impersonation stamps and refuses completion without Evaluator `assignment_dispatch` receipts and `scripts/scholarly_evaluation.py` C6 (claim, derivation, warrant, citation). Generation may still defer scholarly rows as honest `not_run`. Public coordinators stay user-invocable; their fire tables are required, not decorative. This is not a full paper machine, not CLEAN, and not a host-sync claim. DEST-PROTECTED, SK-32 CLOSED, Writer-apply-only, and honest graph fail-closed remain.

**Instrument independence (2026-08-21).** The harness is a tool, not a governing body. A live work-id root stays `DEST-PROTECTED` (manuscript, `phase_state`, acceptance). Tool scratch under `reviews/.harness/` (assignment ready/reserved/consumed, control-plane lock, scholarly-evaluations, shipments) is dest-legal `instrument` per work-id. Assignment gate and receipt transactions no longer require the whole live package to be writable. Two work-ids stay isolated. Package identity does not depend on any one paper. Manuscript publish onto the live workbench still refuses. Writer apply and Joseph R-plane unchanged.

**Gather/circulate milestone split (2026-08-21).** First-start of M1–M4 remains an earning order (`APG-SEQUENCE-*` on a `not_started` target). After materials are in play — Joseph's bound `materials_in_play` declaration, four current accepted hashes, or ledger proof that each of M1–M4 has been accepted at least once — READY/derive/authorize may name any started M1–M4. File presence is never enough. FINAL still requires four current accepted hashes; accepted M5 is the one-way door. DEST-PROTECTED, SK-32 CLOSED, Writer-apply-only, and Joseph R-plane unchanged.

**Dest-safe as C6 guardrail (2026-08-21).** Gather/circulate remains the dispatch/apply/FINAL order. It is not a bar on C6 reading bytes Joseph already staged. `assignment_process_gate.py --stage evaluate` and `derive --purpose evaluate` bind a named M1-M4 for scholarly evaluate even when `phase_state` predecessors are not currently accepted. Sequence, source-hash, and wiki-grounding dest-safe misses no longer exit-4 that path. Planner derive no longer binds M1 when the named target is M4. Evaluate still does not emit a write-authorizing READY receipt. C6 remains required at evaluate verify (claim, derivation, warrant, citation plus Evaluator `assignment_dispatch`). Dest-safe mechanical preflight still runs; dest-safe must not stamp scholarly rows completed/INFO or impersonate C6. FINAL still requires accepted M1-M4. DEST-PROTECTED, SK-32 CLOSED, Writer-apply-only, no scholarly CLEAN, and honest graph fail-closed remain. No paper-specific bars.

## v0.43.1 — 2026-08-14

### Shipment-v2 membership repair and qualification-coverage closure

**Shipment membership.** Shipment-v2 validation now treats `inputs/` as
immutable preimage evidence while requiring operation bijection only across
`work/`, `state/`, and `evidence/`. Supplied recoverable copies must be
inventoried input members whose digest matches the declared preimage.

**Qualification coverage.** The package-completeness controls now route their
declared `RUNTIME-PLANE-MISSING` diagnostics, and the versioned qualification
suite includes the static output-economy guard. The prior two-case carve-out
and candidate-specific output-economy exception do not carry into v0.43.1.

**Versioned boundary.** This slice records package identity, release history,
compatibility bindings, and the ratcheted token-budget baseline. It is not
source qualification, consumer compatibility, package clearance, shipment,
installation, host loading, research acceptance, or activation; those remain
distinct ordered gates.

## v0.43.0 — 2026-08-08

### Graph-independent reader activation and release qualification closure

**Graph-independent reader policy.** Reader-profile v2 now records
`semantic_usage: not_invoked` when no governed semantic binding is available,
so the package can route reader-accessibility obligations without treating a
structural graph as semantic authority. The atomic refresh path preserves the
existing fail-closed project-binding and lifecycle boundaries.

**Qualification evidence.** Release qualification now uses a durable,
receipt-authoritative controller transaction with explicit process ownership,
environment admission, generation/replay continuity, source and manifest
bindings, and stable residue checks. A `finalizing` journal is terminal only
beside its independently validated immutable receipt.

**Versioned boundary.** This history slice makes `0.43.0` the manifest version
and refreshes the shipment-v2 compatibility projection. The slice itself is
not source qualification, consumer compatibility, package clearance,
shipment, installation, host loading, research acceptance, or activation;
those remain distinct ordered gates.

## v0.42.0 — 2026-07-30

### Capability closure and typed shipment v2

**Six-plane capability truth.** Capability claims now bind policy, a versioned
machine contract, producer implementation, independently governed consumer,
packaged runtime, and qualification evidence to the same contract kernel. The
kernel contains 109 components, and compatibility is evaluated against an
immutable shipment-v2 kit rather than mutable checkout imports.

**Typed output and shipment transactions.** Role/output contract 3.0.0 covers
fixed and triggered F1-F9 outputs with explicit occurrence, scope, naming,
deduplication, and diagnostic rules. Shipment schema 2.0.0 binds transaction
state, preimage/postimage evidence, seals, retry identity, refusal diagnostics,
recovery, and concurrency behavior. Producer qualification exercises both
successful transactions and fail-closed adversarial paths.

**Independent consumer boundary.** A separately governed research consumer
vendors exact compatibility-kit bytes and replays the shared frozen 40-fixture
corpus through its own guard, policy, configuration, and tests. Its receipt is
external evidence: receipt presence does not apply a shipment, change research
lifecycle state, authorize F9, promote an artifact, or imply acceptance.

**Qualification boundary.** The source is a versioned candidate only until the
exact final tree passes C10, package/archive/unpacked/installed-cache planes
pass C11, and independent sequence reviews clear C12. This history entry does
not claim `PACKAGE_CLEARED`, `SHIPPED`, `HOST_QUALIFIED`, research activation,
push, tag, or upload.

## v0.41.0 — 2026-07-30

### Laboratory iteration and derived milestone handoff

**Invocation authority.** Added an exact three-scope invocation contract:
`adhoc_review`, `lab_iteration`, and `full_lifecycle`. Laboratory iteration is
transient, private, proposal-only work in a governed staging or shipment lane;
it cannot write lifecycle state, exercise F9 authority, publish a final
deliverable, or claim terminal completion. Ad hoc review remains read-only,
while full lifecycle retains the existing project, assignment, user-gate, and
terminal-proof obligations.

**Derived handoff policy.** Milestone framework 1.1.0 separates native/legacy
mode from explicit `derived|audited` handoff policy. Valid 1.0.0 ledgers resolve
mechanically to implicit audited behavior without byte rewrites. New native
projects default explicitly to derived handoff; audited remains available.
Derived acceptance authorizes the next milestone from accepted current state
without requiring F9, while an explicitly requested optional F9 remains exact,
non-gating, and non-consumed evidence.

**Receipted migration and recovery.** Added the explicit
`lab-iteration-derived-handoff-v1` migration with hash-bound claim, receipt,
journal, verification, rollback, destination protection, concurrent-claim
refusal, tamper detection, and interrupted-transaction recovery. Existing
projects do not acquire derived policy through validation or inference; only
the explicit migration may change their bytes.

**Qualification boundary.** Synthetic source qualification covers legacy and
native compatibility, laboratory non-effects, derived and audited transaction
paths, optional-F9 preservation, migration recovery, protected destinations,
and global orchestration routes. Package clearance, repository shipment,
installed-cache observation, dissemination, and live host qualification remain
separate later decisions and are not implied by this history entry.

## v0.40.0 — 2026-07-28

### Scholarly assurance closure and reader-policy decoupling

**Control-plane authority.** Replaced mutable role and lifecycle assertions
with transaction-issued control-plane transitions, single-use dispatch claims,
typed obligation results, compact receipt indices, and current-byte milestone
and terminal verification. Phase engagement is now a registered structural
gate, and draft governance distinguishes revisable private shipment work from
protected consumer state without treating a harness verdict as acceptance.

**Scholarly assurance.** Added a canonical claim register, schema-bound
scholarly evaluation, exact generation/evaluation binding, authority-chain
checks, and a recorded lifecycle integration fixture. Product-assurance
detectors now carry development, frozen, and held-out corpora with explicit
scoring; heuristic findings remain candidates until independently adjudicated.

**Reader policy and host evidence.** Native projects use reader-profile binding
v2 and Check 8 v2 without inferring semantic authority from a structural graph;
legacy migration is receipted and rollback-safe, while graph-dependent behavior
continues to fail closed. Canonical bootstrap installs the binding, validation
refuses omissions and hand-built substitutes, and the public draft and role
routes derive centroid obligations from that authority. Host qualification is a separate transaction bound to
the cleared archive and installed bytes. Archive qualification propagates the
exact cleared ZIP and source commit into its isolated runtime probe, while a
source-installed cache may qualify only through exact package-member equality
with that externally validated archive. Package clearance, repository shipment,
installed-cache qualification, and live host qualification remain distinct.

## v0.39.0 — 2026-07-25

### Assurance provenance closure and release qualification

**Authority.** Replaced self-asserted workflow identities with kernel-issued,
role-scoped, one-time dispatch authority. Generation and evaluation issuance,
claim consumption, manuscript mutation, milestone acceptance, handoff, and
terminal close now share exact candidate and transaction bindings. Host
attestation and externally authorized legacy mutation remain explicitly
separate trust roots.

**Evidence and lifecycle.** Canonical extraction, citation identity, passage
use, product-assurance adjudication, and verifier transactions are checked as
one current-byte evidence graph. A recorded synthetic M1-to-FINAL fixture
exercises the production lifecycle and targeted tamper paths without claiming
human-quality semantic judgment or host-attested agent separation.

**Runtime and shipment.** Added the governed product gate, source/archive/cache
runtime-plane receipts, safe central-directory-first archive extraction,
canonical read-back SHA-256 publication, immutable hash-bound release evidence
indices, and command-driven plugin/marketplace version parity. Package
clearance, repository shipment, and live Cowork host qualification are recorded
as distinct states.

## v0.38.0 — 2026-07-24

### Product-assurance kernel and mutation authority

**What.** Replaced the process-proxy centroid boundary with a five-stage
contract: binding resolution, canonical source extraction, role-produced
passage execution, exact-byte product assurance, and hash-chained manuscript
mutation authority. The deterministic centroid state is now
`binding_resolved`; it cannot be read as conditioned or acceptable.

**Product gate.** v2 semantic receipts carry the verbatim quote, canonical
extract method, source/title citation identity, locator, warrant, and use.
`product_assurance.py`, invoked through the canonical `run_all.py` surface,
checks quote containment, bibliography same-year title/label mapping,
corpus-relative coinage and register, abstract insider-negation, and uncited
empirical generalization. Quote/citation failures are hard; semantic candidates
remain visible for independent Evaluator adjudication by exact code/locator.
Grounding and register are reported as separate dimensions.

**Lifecycle and operations.** Generation and evaluation envelopes bind the
product report; evaluation remains structurally independent and cannot pass
unresolved candidates. Assignment publication appends preimage/postimage rows
to a project-wide mutation hash-chain, and milestone/terminal gates reject live
bytes that depart from the latest sanctioned postimage. A recoverable stale
policy binding is classified as `PROJECT_BINDING_REBIND_AVAILABLE` with the
exact Planner command. The canonical audit command accepts explicit wiki and
workspace roots, so mechanics and product checks run together without a
host-specific retry sequence. Distributed plugin caches discover governance
from the requested destination's ancestor manifest as well as from the package
checkout; this restores installed operation without using process cwd as an
authority source or weakening `DEST-UNGOVERNED` fail-closed behavior.

**Incident closure.** Synthetic regressions encode the 2026-07-24 failures:
skipped passage use, self-certification, missing/misassigned quotes, 1994a/b
title-label drift, `design-time`, repeated corpus-absent `bounded`, abstract
`not rungs`, uncited `often`, a lossy PDF adapter, and an unlogged direct edit.

## v0.37.5 — 2026-07-23

### Passage-bound centroid execution and independent evaluation

**What.** Replaced generic centroid path/hash evidence with a role-produced
semantic execution receipt. Every passage actually used must bind an admitted
member, warrant scope, original source hash, non-empty extract hash, precise
locator, use statement, exact artifact, and deterministic centroid packet.
Generation now requires the packet's `write` derivation; evaluation requires
`review`, binds the verified generation envelope, and refuses a reused actor or
dispatch identity.

**Lifecycle enforcement.** Evaluation preparation is bound to the exact bytes
subsequently reviewed. Milestone transactions and the terminal full-run gate
require the enriched generation/evaluation envelopes and independently bind the
evaluation envelope to the generation-envelope hash. A ready deterministic
packet or an empty `semantic_findings` array remains policy-resolution evidence,
not proof that passages conditioned prose.

**Verification.** Failing-first regressions cover generic evidence, wrong packet
derivation, post-prepare byte changes, and Generator self-evaluation. The focused
draft-governance, milestone-checkpoint, and semantic-bypass suites pass; release
acceptance still requires the complete 59-suite registry from the committed
clean checkout and installed-cache byte parity.

## v0.37.4 — 2026-07-23

### Project-neutral centroid freeze and shipment boundary

**What.** Installed the 290-page semantic inventory freeze for the universal
centroid, with Yu, Giorgini, and Maiden (2011) as its primary reference. Pin
integrity is fail-closed: a missing pinned page or a pinned-path hash mismatch
blocks use. Later live Wiki additions are reported as enrichment candidates
and do not invalidate an otherwise intact freeze.

**Governance boundary.** The harness remains a project-neutral producer. It
may stage only beneath a governed workspace root and may write private
shipments only into an active research package's exact shipment lane. A path
under this repository's own `outputs/co-author-harness/` is now refused as
`DEST-MISROUTED`, and path hygiene fails if that misleading tree reappears.
No project can become the governing body for the harness.

**Verification.** The semantic inventory, graph eligibility, destination
capability, path hygiene, documentation, and Contract Kernel pins are covered
by the authoritative fixture registry. The final committed release is accepted
only after the complete 59-suite registry passes from a clean detached
checkout.

---

## v0.37.3 — 2026-07-23

### Reader-policy rebind completion and epoch-8 semantic refresh

**What.** Closed the live `PROJECT_BINDING_STALE` failure that prevented the
mandatory centroid write/review derivations from executing after the canonical
Wiki semantic refresh. The producer boundary now admits only the exact
Planner-owned re-pin request, applied archive, resolved sidecar, and hash-bound
stale-request archive surfaces. The Planner can archive an inert request only
when its caller supplies the exact request hash and the request no longer
matches the current profile.

**Windows state transaction.** Atomic Planner state replacement now preserves
an existing target's file mode. A read-only `reviews/phase_state.json` is
temporarily unlocked only for the same-directory atomic replacement and is
read-only again after success; rollback restores the original mode. This closes
the observed `WinError 5` without weakening the protected research-root guard.

**Semantic pin.** Deliberate epoch 8 binds graph SHA-256
`587d07c48c11d86e71005ebda660af5e296c81c98ed1889c34d4795ecf194f03`,
attestation pin
`00133e506e399db25cd8a182a97f0d82e9c6a1140b0cfef115da2331c0aa7f5e`,
and the unchanged exemplar pin
`5b7fcb501ca76e21d92ab187be9a7db7494d2ba4f72bf931516227b12c888344`.
Static accessibility fixtures and contract-kernel hashes were refreshed in
lockstep.

**Verification.** The live project rebind completed while preserving the
read-only state attribute. Centroid `write` on accepted M3 and centroid
`review` on the current M4 both return `ready` with 13 admitted members. This
does not retroactively certify the existing M4 as centroid-generated. All 59
registered fixture suites pass with `--no-write`.

---

## v0.37.2 — 2026-07-22

### Centroid CLI and refusal-code truth repair

**What.** Corrected two defects found by executing the promoted centroid
contract against the live M4 project. `draft_governance.py prepare` now accepts
the documented mandatory `--role` argument and refuses a role that does not
match the requested generation/evaluation phase. `centroid_service.py` now
preserves the stable `GRAPH-SEMANTIC-INELIGIBLE` policy refusal instead of
flattening it into the generic `PROFILE_UNRESOLVED` envelope.

**Verification.** Failing-first regressions cover the exact documented CLI and
the structural-only graph refusal. The authoritative fixture registry passes
59/59 suites with stable source digests, and the live project round trip now
returns a ready 25-obligation generation contract followed by the truthful
graph-eligibility refusal.

---

## v0.37.1 — 2026-07-22

### Universal centroid and all-drafts governance

**What.** Promoted `/centroid-pass` to a public read-only orchestration surface
and installed `draft_governance.v1.json` plus a deterministic resolver/verifier.
Every M1-M4 and FINAL draft now requires centroid-conditioned Generator evidence
and independent Evaluator evidence over the exact current bytes. The obligation
does not depend on whether a milestone artifact already exists. The bundle
includes D-STYLE, retained grammar/style commitments, grounding, deterministic
checks, SAFEGUARD, and every piece-conditional overlay.

**Enforcement.** Assignment receipts always bind centroid conditioning;
milestone `record` refuses missing, stale, self-evaluated, or incomplete policy
envelopes; the terminal full-run gate rechecks all five deliverables. Ph1 now has
a bounded policy Evaluator pass while the full revision-maturity review remains
Ph2+.

### Producer boundary R2: clean refusal exit codes; runbook parity enforced

**What.** Patch corrections found by supervisory review of R1.

- `d_style_profile_check.py` refused protected destinations correctly but
  exited 1 through a `NameError` traceback (missing `import sys`) instead of
  the documented refusal code 4. Fixed; and
  `destination_capability_smoketest.py`'s redirect-refusal cases now require
  **exactly** exit 4 with a clean, traceback-free `[BLOCKER] DEST-PROTECTED`
  diagnostic — an any-nonzero contract had let a crashing refusal pass.
- `destination-coverage-check.py` now also fails unless BOTH root maintainer
  runbooks (`CLAUDE.md` **and** `AGENTS.md`) list the coverage command;
  `AGENTS.md` had been missed, and it is the runbook governing Codex and
  other agents. Its own sha256 pin was refreshed through the `--pin`
  workflow after the inspected change.

**Why.** A refusal that crashes is not a contract, and a battery only some
agents run is a battery that rots.

**How to apply.** Redirectable-writer refusals must exit 4 cleanly; keep the
two runbook battery lists in lockstep — the coverage check now enforces it.

---

## v0.37.0 — 2026-07-22

### Producer boundary R1: machine-enforced writer coverage

**What.** Bounded revision to v0.36.0 after supervisory review found the
guard coverage incomplete: `coupling_health_report.py` demonstrably wrote
into a protected governed root while the corpus was green.

- New maintainer check `scripts/destination-coverage-check.py` +
  `references/destination_coverage_registry.json`: a mechanical census of
  every filesystem writer under `scripts/` must classify each as guarded
  (with a live guard call and a named negative regression), package-confined,
  test-only, or excluded — the last three sha256-pinned so any change forces
  deliberate re-review. An unclassified new writer fails the battery.
- Census result: 34 writers, including seven the prose inventory had missed.
  Newly guarded: `coupling_health_report`, `aggregate_h_calibration`,
  `install_preflight_assets`, `gate_threshold_tuner` (`--output`),
  `audit/run_all` (project root + all output paths),
  `coupling_readiness_check` (output paths), `d_style_profile_check`,
  `token_budget_check` (`--out`). Each observed red against a disposable
  synthetic tree first; refusal cases (including alias spellings) added to
  `destination_capability_smoketest.py`.

**Why.** Coverage that lives only in prose rots; the registry makes writer
coverage a failing check instead of a claim.

**How to apply.** Adding any writer now requires either a guard + regression
or an explicit pinned classification; `--pin` refreshes pins only as a
deliberate re-review act.

---

## v0.36.0 — 2026-07-22

### Producer boundary: destination-capability guard, staging lane, shipment_only mode

**What.** The harness is now structurally a producer, not a decision maker,
for every governed workspace consumer (constitutional basis:
`research/10_Governance/HARNESS_SHIPMENT_BOUNDARY.md`, binding 2026-07-22).

- `scripts/destination_capability.py` — single write-destination chokepoint:
  harness package and the governed staging lane
  (`outputs/co-author-harness/staging/<work-id>/<run-id>/`) are writable;
  any other destination under a governed root refuses `DEST-PROTECTED`; no
  discoverable workspace governance fails closed `DEST-UNGOVERNED` for all
  non-package writes. All 5 milestone transaction verbs, 3 receipt-transaction
  entries, and 13 writer CLIs are wired through it; the additive-only
  `COAUTHOR_EXTRA_GOVERNED_ROOTS` test hook can never un-protect a real root.
- `scripts/staging_run.py` + `references/schemas/shipment_manifest.schema.json`
  — staging-run lifecycle: immutable input snapshots, exclusive byte-verified
  `effect_scope: proposal_only` shipment emission, tamper detection,
  consumer-side application-receipt recognition (absence means NOT applied).
- Authority mode `shipment_only` (orthogonal to assignment profile and run
  scope; operating mode stays reserved-empty): `derive` reports
  `authority_mode`; staging-lane events, genesis bootstrap events, and F9
  handoffs carry `effect_scope: proposal_only` (additive optional schema
  fields; historical evidence remains valid; direct-local output unchanged).
- Staging revisability: post-convergence M4 and recorded M5 (FINAL) candidates
  re-record freely in staging; the superseding `deliverable_recorded` event
  carries a `previous_content` binding, names `candidate_superseded`, and
  discloses the research-master revalidation advisory the harness never
  applies. M5 staging deliverables are content-addressed snapshots so
  historical event bindings stay byte-valid. Direct-local projects keep the
  historical AMC-ORDER refusals.
- Wiki: automatic canonical-Wiki/lessons-promotion attempt wiring removed
  across skills/agents/references; canonical Wiki changes are separately
  adjudicated shipments to Wiki governance; `wiki_writes` is configuration,
  not promotion authority.
- Binding producer-boundary duty declarations landed in the harness root
  `CLAUDE.md`/`AGENTS.md`, `AGENT_ORCHESTRATION.md`, and
  `ASSIGNMENT_MILESTONE_PROCESS.md` §0.

**Why.** The July 22 shipment boundary gives the harness zero direct-write
authority under the research root; code, contracts, and instructions now
enforce what the constitution declares, with the temporary C→E functional gap
(research-rooted direct milestone writes refuse until staging-lane runs are
adopted) accepted as correct boundary enforcement.

**How to apply.** Run research-facing work in a staging-lane project
(`shipment_only` derives automatically); return `shipment/MANIFEST.json` to
research governance for adjudication; never treat any harness verdict, phase
label, terminal PASS, or `accepted` status as research authority.

---

## v0.35.0 — 2026-07-21

### Semantic register stability and closed rebind loop

**What changed.** The domain-native semantic register now accepts provenance-
checked audits from either Codex or Claude Code, including multi-reviewer
artifacts, while retaining exact reviewer counts and row lineage. Graph
projections tolerate NetworkX's valid endpoint orientation and verify derived
normal labels rather than treating serializer details as semantic drift.

**Writer safety.** Governed semantic graph states are protected from legacy
refresh, merge, and normalization writers. Stabilization preserves reviewer-
scoped caches, safely reuses or archives candidate plans, and maintains unique
history artifacts. The live corpus was re-audited and re-pinned at epoch 7 with
zero unsupported sampled relations and no unresolved register seeds.

**Planner transaction.** `assignment_milestone_checkpoint.py` now provides the
missing production path for a pending rebind request. It refuses open rounds,
verifies the current profile, both pins, epoch, timestamp, and append-only log
row, retains G/H/VE transition history, publishes the resolver before state,
checks concurrent changes, then archives the applied request. Regression
coverage proves open-round and malformed-request refusals as well as the
successful state-last path.

**Why a minor release.** This closes a documented workflow capability gap and
widens the supported semantic-audit provider contract without weakening any
gate. The public slash-command surface remains unchanged.

---

## v0.34.0 — 2026-07-20

### One native command surface

**What changed.** Claude Code now loads the plugin through native
`skills/*/SKILL.md` commands only. The obsolete `commands/*.md` redirect layer
was removed after the installed host reported each redirect and its same-named
skill as separate inventory entries. The supported user menu is reduced to the
active manuscript, review, formatting, evidence, advisor, and snowball
workflows. Legacy lifecycle bodies, maintainer operations, and truthful
unavailable capability contracts remain installed but are hidden from the
user's slash menu with `user-invocable: false`.

**Policy and enforcement.** `references/policies/command_surface.v1.json` is
the machine-readable classification authority. `scripts/command_surface_check.py`
refuses duplicate command files, incomplete classification, frontmatter/menu
drift, and hidden catalog rows. Synthetic regressions cover duplicate shims,
visibility drift, and hidden-row leakage. The skill and catalog checks now
compare `/plugin-commands` with user-invocable skills rather than every
installed capability.

**Drift repair.** `/review`, `/ship`, `/review-letter`, `/cancel-climb`,
`/raise-ceiling`, and Ph3 termination/re-engagement tokens had been described
as slash commands without corresponding installed skills. Public behavior now
routes through `/run-draft`, `/run-iterate`, `/run-finalize`, and
`/response-letter-review`; cancellation, ceiling changes, re-engagement, and
terminal signoff are named Planner intents or checkpoint elections rather than
fabricated command surfaces.

**Versioning.** This is a pre-1.0 minor release because it intentionally changes
menu visibility at the user's request. The hidden legacy skills remain present
and model-invocable; only the duplicated and misleading user-facing surface is
removed.

---

## v0.33.2 — 2026-07-20

### Remote-install and release-byte parity

**What changed.** The six live consumers that previously depended on
packaging-time Markdown include expansion now carry explicit consumer-relative
runtime bindings to their canonical plugin-root snippet files. Claude and Codex Git-source
marketplace installs therefore receive the same policy-bearing source bytes as
the audited `.plugin` archive without duplicating the shared policy blocks.

**Enforcement.** A new release source-parity checker compares every packaged
member with its committed `HEAD` byte sequence and permits only the generated
`PROVENANCE.json` member. It refuses missing, unexpected, duplicate, or
rewritten source members. The release gate and full ZIP wrapper both invoke it;
the fixture registry covers exact, tampered, missing, extra, duplicate, and
live build-only-include cases. Snippet checks now bind the exact runtime
consumer sets and reject live include sentinels.

**Why a patch.** v0.33.1 repaired Codex discovery, but post-install cache
comparison found six semantic differences between Git-source caches and the
rendered release archive. The v0.33.1 tag remains immutable; this patch
supersedes it.

---

## v0.33.1 — 2026-07-20

### Dual-loader marketplace compatibility

**What changed.** The single-plugin marketplace now resolves the repository-root
package through a remote HTTPS URL source. Claude accepts the prior local
`"./"` form, but Codex cannot resolve a plugin to the marketplace root. The URL
form preserves the canonical root package, the single `main` branch, and one
copy of the substrate while allowing both loaders to discover and install it.

**Enforcement.** Marketplace identity is now determined by the manifest plugin
name rather than by stringifying the source field. Version, license,
description, and SSOT parity therefore remain active when the source changes
from a local string to an object. A shared marketplace contract and synthetic
regressions refuse root-relative sources, unsupported source objects,
repository mismatches, and parity drift. The archive loader check consumes the
same rule.

**Release boundary.** The URL is intentionally not commit-pinned inside the
self-hosted manifest: a release commit cannot contain its own SHA. Immutable
release identity remains the semantic version plus annotated Git tag; a new
version is required whenever package bytes change.

---

## v0.33.0 — 2026-07-20

### Systematic package repair and canonical lifecycle

**What changed.** The package now binds lifecycle, ownership, recovery, and
capability truth through machine-readable contracts. A versioned Contract
Kernel, canonical lifecycle transition table, role-output contract, and
capability registry replace scattered prose as the operational authority.
Planner-owned M1–M5 checkpoints, single-use scoped-writer receipts, atomic M4
first-deliverable bindings, recovery transactions, and the M5/FINAL close now
share one validated state model. Public entrypoints and reflection modes route
through that model instead of maintaining parallel workflow interpretations.

**Capability truth.** Every catalogued capability now has an explicit
disposition and evidence path. Deferred graph/Wiki authority remains
unavailable with deterministic reason codes. `/centroid-pass` remains publicly
unavailable; its maintainer-only service prepares a read-only, hash-bound
analysis packet but does not claim semantic judgment or write authority.

### Fixture, packaging, and distribution integrity

**One evidence authority.** The fixture registry is the sole behavioral-test
population across local, CI, and release surfaces. It binds its writer,
registered cases, tested-input census, and canonical checkout-portable digest;
failed runs void stale evidence. Windows console encoding, detached-worktree
packaging, and commit-bound provenance are regression tested.

**Distribution rights.** The package license is MIT. Known raw third-party
extracts, the advisor workbook/transcription, and the prior long-passage corpus
and planning copies are absent from the current package and replaced with
package-authored summaries or synthetic examples. `THIRD_PARTY_NOTICES.md` and
`references/distribution_rights.json` state the forward-looking scope and bind
whole-file hashes, normalized passage hashes, historical paths, and replacement
bytes. This remediation governs the current tree and future artifacts; it does
not rewrite Git history or make a legal determination.

**Release acceptance.** Shipment requires the structural checks, the complete
registered fixture corpus, a clean detached-worktree build, exact manifest and
provenance reconciliation, archive-level rights and loader checks, and an
installation receipt bound to the immutable artifact. Capability dispositions
did not change during the rights repair, so H2 was not reopened.

---

## v0.32.0 — 2026-07-19

### Full-run enforcement review follow-up

**What changed.** The scoped hook now intercepts `MultiEdit` alongside
`Write`/`Edit`, and malformed hook JSON fails closed whenever
`FRC_PARENT_SCOPE` is active. The completeness report discovers projects from
either native scaffold marker. Release gating now classifies every non-zero
full-run smoketest and every missing portability smoketest as a BLOCKER; error
substrings can no longer downgrade a genuine regression. Synthetic regressions
pin each boundary.

**Why.** Claude's independent adjudication of CodeRabbit's shipment review
confirmed six correctness gaps. Historical version labels in this changelog and
the README release-history table remain valid under the root version-authority
policy and were intentionally left unchanged.

### Centroid capability-truth repair — `/centroid-pass`

**What changed.** A live-interface audit found that the initial SK-47 prose
promised write/review/revise execution, an apply path, and milestone-fence bypass
without an executable public implementation. The public command, catalog, skill
registry, README, and capability registry now agree: `/centroid-pass` is
unavailable with reason `IMPLEMENTATION_MISSING` and returns a deterministic
read-only envelope without writing an artefact.

**Candidate substrate.** `scripts/centroid_service.py` prepares a maintainer-only
analysis packet. It reads the full UTF-8 manuscript, resolves an exact full-file
or heading scope, binds manuscript and scope hashes, resolves the existing
reader-accessibility profile and semantic pins, preserves surface-versus-argument
membership, and reports deterministic text metrics. It emits no semantic verdict,
retrieved passage, quotation, attestation, or locator and writes only to stdout.
Public activation remains an H2 decision.

**Graph and Wiki boundary.** Graph authority remains unconditionally unavailable.
A behavioral fixture proves that a structurally valid and fresh graph still
returns `GRAPH_GOVERNED_GENERATION_UNAVAILABLE`; the deferred autonomous path
returns `WIKI_WRITE_TRANSACTION_UNAVAILABLE` and creates no Wiki directory.

**Verification.** Capability contracts now require every unavailable skill to
declare its exact reason code in the first 80 lines. Centroid and graph behavioral
smoketests are registered in the authoritative fixture runner.

---

## v0.31.1 — 2026-07-19

### Full-run enforcement surfaces and deliberate register re-pin

**What changed.** The existing full-run contract is now connected to the
Claude Code plugin surface and the release gate. An explicitly scoped driver
activates PreToolUse checks for manuscript Write/Edit operations and subagent
Task/Agent dispatch, plus a Stop check for terminal-completion claims. The
post-hoc completeness report preserves authoritative gate outcomes, including
UNVERIFIABLE for execution errors and explicit expected roots in mixed trees.
The previously orphaned full-run, semantic-bypass, enforcement-surface, and
corpus-portability suites are release-gated with `errexit`-safe exit capture.

**Verification and boundary.** Synthetic regressions cover inactive ordinary
sessions, exact child-scope inheritance, slash-normalized manuscript paths,
terminal claims, exit-code preservation, and mixed-root detection. Claude Code
2.1.214 was exercised directly: its observed `Task` spelling was denied for an
undeclared child scope and then allowed after exact `full_lifecycle`
inheritance; the Stop hook also executed on the host. Shell writes remain
outside the hook surface, driver activation remains explicit, and Cowork
prevention is not claimed without build-specific verification.

**Register and baseline repair.** A confirmed epoch-5 exemplar-view re-pin
updates the three changed Yu-source tuples while retaining the attestation pin,
membership, seed count, and primary communities. Its dry-run, applied snapshot,
commit provenance, and read-back are recorded. The milestone smoke expectation
now matches the intentionally unconditional
`GRAPH_GOVERNED_GENERATION_UNAVAILABLE` authority gate introduced in v0.31.0.

## v0.31.0 — 2026-07-18

### Reproducible release packaging, evidence integrity, and Wiki-write deferral

**What changed.** Two consolidated lines land on top of v0.30.0. (1) The
release-packaging path is a deterministic artifact of a single commit: package
enumeration is extracted into a neutral module, the executing builder is bound
via a clean-worktree re-exec, every release path converges onto the one
committed builder, and fixture/release-manifest evidence is commit-stable,
writer-bound, and concurrency-safe (pass-fixture hashes bind to committed bytes,
digest-exact manifests regenerate deterministically, duplicate-manifest emission
is rejected, and the test harness gains a repo-global sandbox/lock with exact
exclusions and an honest 5/6/7 exit contract). (2) Research Truth Phase 0/1:
canonical Coupling C/D Wiki mutation is unavailable — all entry points return a
structured deferred result (`WIKI_WRITE_TRANSACTION_UNAVAILABLE`, `wiki_page_key:
null`) without blocking Research completion, approval, or release, and
`scripts/graph_authority_gate.py` adds an unconditional
`GRAPH_GOVERNED_GENERATION_UNAVAILABLE` gate on the separate graph-authority
plane.

**Verification and boundary.** Packaging smoketests pin worktree re-exec, exit
codes, provenance key sets, and output handoff; the build voids on
worktree-cleanup failure and fails closed on toolchain drift. Additive to the
packaging/evidence and reflection layers — no four-agent contract or
phase-ledger schema change.

**Severity / attribution.** Minor release consolidating the
`codex/assignment-gate-hardening` cycle. Version intent: v0.31.0.

## v0.30.0 — 2026-07-18

### Milestone auditability and portable register roots

**What.** Milestone deliverables recorded before acceptance now require a
matching append-only `deliverable_recorded` event, bound to the primary-lineage
artifact's exact path and SHA-256. Reader-accessibility register roots accept
`AGENT_WIKI_ROOT`, `AGENT_WORKSPACE_ROOT`, and `AGENT_HARNESS_ROOT` fallbacks
when callers provide no explicit root, and override-mode resolved policy records
the source of every effective root. Assignment-gate diagnostics now state that
`mode:native` is a lifecycle-format selection, not implicit N/A authority.

**Why.** Adding an artifact only to `milestones.Mx.artifacts[]` left its creation
time inferable only from a state diff. The earlier portability proposal also
introduced ambient inputs without recording whether a value came from the
profile, an explicit argument, the environment, or the running package. The
proposed native assignment-gate no-op was rejected because it contradicted the
fail-closed assignment and full-run contracts and would not have passed the
receipt preflight in any event.

**How to apply.** Planner transactions that add or replace a current
primary-lineage deliverable append `deliverable_recorded` with the matching
artifact binding in the same atomic state write. Root precedence is explicit
argument, then environment, then profile/runtime default; `path_roots_mode` and
`resolution_sources` preserve the decision in resolved policy evidence.

## v0.29.1 — 2026-07-17

### Full-run lifecycle contract

**What.** A "Harness full run" request produced a complete essay with no project
root, no assignment contract, no phase state, no milestone acceptance, no
F7/F8/F9 and no G.4, and reported "Ladder complete ... PASS" (audit
2026-07-17, session local_7fe69519, lines 1 / 112 / 342). Every agent file
already forbade this; nothing enforced it.

**Why it was possible.** The fail-closed assignment gates are all
`--project-root` parameterised, so with *no project at all* none can fire.
`run_scope` did not exist, so a parent's whole-lifecycle intent could not bind
a child — the coordinator dispatched the Evaluator with "no project scaffold
... Do NOT attempt to write reviews/ artifacts ... Return findings in your
response only." `references/AGENT_ORCHESTRATION.md` states outright that role
permissions are "not structurally enforced by the filesystem," and no
deterministic check stood between an agent and the words "ladder complete."

**How to apply.** `references/FULL_RUN_CONTRACT.md` is the single normative
surface (run scope; no-project-no-prose; child-dispatch prohibition; the
fifteen terminal requirements; error codes `FRC-*`). Other surfaces route to it
and do not restate it — duplicated policy prose is the drift this repair
exists to close. `scripts/full_run_contract_check.py` is its mechanical
authority (`authorize` / `scope` / `authorship` / `terminal` / `intent`);
where the prose and the script disagree, the script is the contract.
`scripts/full_run_contract_smoketest.py` pins the behaviour against the real
audit strings, and includes a valid native M1→M4→FINAL fixture that must PASS
so the gate cannot be satisfied by refusing everything.

**Lesson (recurrent).** A rule that exists only as prose is a rule the system
does not have. This is the same species as the CRLF fixture hashes and the
`B:/` corpus roots: a claim whose enforcement was assumed rather than
mechanised.

## v0.29.0 — 2026-07-14

### Exemplar ingestion and warrant-scope routing

**What changed.** `/repin-register` now validates one exact-key exemplar add or
drop and carries it through the existing single-snapshot, confirmed, atomic
re-pin transaction. The profile schema admits controlled members and the
`intentional-root` role; singleton locks protect the Yu centroid and Dennett
root. Missing PDFs and graph-coherence distance remain visible advisories.
Resolver output now separates `surface_exemplar_members` (`both` only) from
`argument_exemplar_members` (all admitted), and Check 8 H consumes the former.

**Verification and boundary.** Criterion 9 covers refusal, advisory, add/drop,
dry-run, ledger, epoch, and consumer-routing behavior in fixtures. The pending
Dennett documentation block remains pending: this release neither creates a
wiki page nor performs a live re-pin. Version intent: v0.29.0 minor.

## v0.28.1 — 2026-07-14

### Deliberate domain-register re-pin workflow

**What changed.** `/repin-register` operationalizes the accepted semantic-pin policy without introducing a second hasher. `reader_accessibility_policy.py --repin` now owns preflight, single-snapshot resolution, delta classification, package-scoped audit snapshots, append-only JSONL logging and its derived Markdown view, explicit confirmation, atomic profile patching with read-back, and optional project rebind-request emission. No-delta events use `delta_class: none` and leave profile bytes and version untouched. Real deltas patch-bump the policy profile and advance its binding epoch.

Project bindings now carry `pin_epoch` and `pinned_at`. The milestone validator distinguishes profile hash drift, attestation drift, exemplar drift, and a stale binding epoch. Epoch enforcement is softened exactly at the cycle boundary: an old open round remains valid, while a pending rebind blocks a newly opened cycle. The Planner remains the sole `phase_state.json` writer and alone applies and archives rebind requests.

**Safety and evidence.** Fresh and stale locks refuse by default; force recovery needs explicit confirmation. Pin-affecting dirt always blocks, unrelated dirt needs an explicit flag, and the schema-first gate fails closed before any apply. `repin_register_smoketest.py` covers all eight accepted criteria and is release-gated alongside the existing accessibility and milestone suites. All tests use temporary fixtures; no live INF3130 or RE project tree is written.

**Severity / attribution.** Patch release implementing the accepted 2026-07-14 Joseph/Cowork/Codex architecture. Version intent: v0.28.1.

## v0.28.0 — 2026-07-14

### Milestone feedback and handoff framework

**What changed.** The harness now treats milestones as an evidence-bearing workflow rather than a project-local list of filenames. A machine-readable M1–M5 state records each milestone's deliverable, feedback, adjudication, current-content binding, and handoff; `reviews/lifecycle_state.md` is a deterministic derived view of that authority, never a second ledger. Phase admission consumes the same state, so unresolved feedback, stale hashes, reopened upstream work, and incomplete handoffs block downstream claims instead of being papered over by a green phase check.

Native bootstrap, schema validation, migration preview/apply, and exemplar governance ship together. Clean lifecycle exemplars and legacy migration exemplars are separate classes with external, credentialed evidence. Migration treats filename-derived milestone and feedback labels only as non-authoritative candidate hints. Explicit adjudication must admit, exclude as unrelated, or mark prior-contract evidence unavailable; admitted feedback retains its class, named source actor and authority, source/target milestones, receipt time, and hash-bound contemporaneity evidence. Reports keep admitted, excluded, unavailable, and missing evidence distinct. Project `directives.md` remains above package defaults on the documented precedence ladder. Preflight outcomes are strictly tri-state: READY and explicitly authorized NOT_APPLICABLE may proceed; MISCONFIGURED blocks.

The reader-accessibility contract now carries deterministic cadence semantics and a domain-native register model. The model distinguishes domain fluency from passage-scope accessibility, keeps advisory verdict-edge analysis outside the A–H aggregate, and binds exemplar and graph evidence by semantic content hashes. The banded cadence architecture records the user's acceptance separately from calibration status: paragraph length remains a candidate signal with profile-governed structure requirements, not a universal proxy for prose quality, while the provisional 300-word ceiling remains profile-tunable without code or schema edits.

The release gate adds a blocking Phase 0.59 for the aggregate milestone, accessibility, lifecycle-rendering, and migration suites; standalone adversarial/bootstrap/retirement suites; and syntax compilation of the three runtime tools. Missing runners or compile targets are blockers.

**Why.** The RE essay exposed the live failure that motivated the contract: an M4 deliverable and M5 checklist could exist while the handoff between manuscript content, feedback, adjudication, and approval was not mechanically continuous. INF3130 exposed a different risk: reconstructed milestone history can look direct and coherent after the fact even when archive/live lineages diverge. A reusable harness feature therefore had to encode provenance and handoff predicates, not merely document either project.

**How to apply.** Bootstrap new projects into the clean lifecycle contract. Run legacy projects through dry-run migration, resolve HOLDs, and apply only with project-authorized directives. Render lifecycle prose from the machine state. Use the tri-state preflight result as returned; do not convert MISCONFIGURED to NOT_APPLICABLE or infer approval from file age.

**Pilot boundary.** The RE-essay and INF3130 checks were read-only pilots. They informed temporary, synthetic regression fixtures for current-hash continuity, stale approvals, reopened milestones, divergent lineage, retrospective feedback, array-shaped sections, and unlocked Ph3 siblings. This release does **not** claim either live research project was migrated, normalized, or edited.

**Severity / attribution.** Minor feature release spanning milestone governance, deterministic tooling, reader-accessibility policy, migration, exemplars, and release gating. Architecture incorporates the 2026-07-13 Joseph/Cowork/Codex adjudication; implementation and tests are harness-local.

---

## v0.27.0 — 2026-07-13

### Audit-remediation cycle — green checks are not coherence

**What changed.** A full harness audit (2026-07-13; report at `reviews/harness_audit_2026-07-13.md`) ran the 10-script maintainer suite (all green) and then a three-lane semantic sweep, which surfaced drift the deterministic layer structurally cannot see. Remediation, one commit per theme:

- **Guardrail migration completed.** `scripts/pre_phase_advance_check.py` — the in-flight tier_state → phase_state migration finished: `load_ledger` reads `reviews/phase_state.json` under `SCHEMA_VERSION_EXPECTED = "0.7.4"` (constant restored; inline literals removed) through an in-memory Ph→T translation shim; `VALID_TRIGGERS` completed against `phase_state_schema.md §3.1` (canonical triggers 28 `ph3_accessibility_blocker_surfaced` and 30 `stability_mode_escalated_to_full_ph3` added; trigger 13 stays excluded per its v0.11.0 retirement); header/docstring re-voiced from the stale v0.7.3 deprecation banner; CLI accepts `Ph1–Ph4` (`--target-phase` alias) with `T1–T4` as legacy aliases. New regression smoketest `pre_phase_advance_phase_state_smoketest.py` wired into `release-gate.sh` (Phase 0.58).
- **Dispatch-critical reference re-voiced.** `references/MODEL_ALLOCATION.md` (read by the Planner at every dispatch) was frozen at v0.7.3: tier vocabulary, live writes to the retired `tier_state.json`, and a future-tense promise of the v0.7.4 rename. Now phase-named throughout; the model pins (Opus 4.7 / Sonnet 4.6 / Haiku 4.5) are deliberately unchanged and the v0.25.0 deferral of that plane is recorded in-file (§8).
- **Counterclaim sweep.** Residual 15/16-field and 30-trigger claims (pre-v0.10.0 shapes) corrected to the 18-field/31-trigger canon in `references/CLAUDE.md`, `agents/planner.md`, `AGENT_ORCHESTRATION.md` (§ ledger description now names the two v0.10.0 snowball fields), `docs/agent-instructions/*`, `templates/F3_reflector_lightweight_probe.md`, `phase_notifications.yaml`, `READER_ACCESSIBILITY.md`; `SKILL_REGISTRY.md` SK-25/26/27 live clauses migrated off tier residue (six-field `tier_entry_log` row → 7-field `phase_entry_log` with `model_used`).
- **Ghost and retired citations.** `skills/SKILL_REGISTRY.md` → `references/SKILL_REGISTRY.md` (6 citations across 4 files — the Reflector's actual write target); `classify-manuscript` Step 5 dispatch table re-pointed from retired `run-tier-*` names; `eygp-framework-checker` (SK-28) no longer cited as live; phantom `legacy/` archive claims re-worded; retired migration scripts annotated `[retired from tree]`; `tier_state_canonicalize.py` "retained" contradiction fixed.
- **SAFEGUARD routing re-keyed.** `SAFEGUARD_LAYER.md` "when to run" and the per-rung table migrated from the retired v0.4.x review-depth vocabulary (`quick`/`standard`/`submission-bound`) and T-labels to phase routing.
- **Drift class design-time-blocked.** `retirement-sweep-check.py` + `schemas/retired_surfaces.json` extended with **`retired_phrases`** — negative string assertions ("15-field", "16-field", "17-field", "sixteen canonical fields", "30-trigger", "30 legal values", "six-field row", "Lifecycle-Stage Ladder") that block on live surfaces unless the line carries a historical marker. This complements the snapshot-mode `version-planes-check.py`, which verifies registered assertions are *present* but cannot see stale counterclaims.
- **Housekeeping.** Retired T-labels on live command descriptions → Ph-labels; `harness-architecture.md` prose version pin removed (manifest is the sole version authority) and reflector-split/public-ladder/releases-gitignored corrections; README maintainer list matched to CLAUDE.md/AGENTS.md (10 scripts); `plugin_update_proposals.md` summary table reconciled with its own v0.8.4 close-out; committed v0.13-era validator outputs removed from `outputs/`.

**Why.** The audit's structural lesson: every deterministic check was green while `references/CLAUDE.md` misstated the ledger shape and the Planner's dispatch-time reference instructed writes to a retired surface. Presence-mode checks (assertion still present) cannot catch absence-mode drift (stale counterclaim still present). The `retired_phrases` extension converts this audit's most expensive finding class into a release-gate blocker.

**How to apply.** Nothing changes procedurally. Two audit-report corrections are recorded in-place: `ph3_iteration_round_manuscript` is canonical trigger 29 (the original S2.1(b) finding was wrong — the real gap was the tier-era enum), and `run-evaluator-preflight.ps1` is a per-project seed script (`PROJECT_BOOTSTRAP.md §2.11`), not a ghost.

**Known remaining (deliberate).** The agent-file ladder fork (planner v0.8.0 / evaluator+generator v0.7.4) stays recorded-not-harmonized in `version_planes.json`; the subagent-dispatch model plane stays on Opus 4.7/Sonnet 4.6/Haiku 4.5 pending its own re-validation cycle; classification's T-coded `tier:` field is a live surface by design and was not re-voiced.

**Severity / attribution.** Maintainer increment, doc-plane + one guardrail script. Source: 2026-07-13 audit (Cowork session), fix commits C1–C6.

---

## v0.26.0 — 2026-07-12

### Precision-gate cycle — a definition is not an introduction, and precision outranks vividness

**What changed.** Two mandatory judgment gates were added to the Step-4 sentence-craft layer and threaded across every surface that names it:

- **Concept-introduction priority gate** (`bacon_2009_well_crafted_sentence_guidelines.md §3.7`, new). Before ordinary craft checks, every newly introduced analytical term, category, unit, or field-level generalization must pass the **introduction-provenance**, **derivation-continuity**, **scope-authority**, and **reader-reconstruction** tests: the prose must name the need and the operation that connect the new construct to the concept preceding it. A fluent definition does **not** clear an unintroduced construct; a frame-changing failure is **MAJOR**.
- **Semantic-predication integrity** as `sentence-level-pass` **Check 10** (`bacon_2009_well_crafted_sentence_guidelines.md §3.6`, new). Every definitional, modelling, or ontological sentence is tested with the **bearer**, **contrast-set**, **domain-collocation**, **transformation-continuity**, and **conceptual-debt** tests. A concrete, well-focused subject is not a pass; the predicate must be true of the entity that actually bears it, not of a model, representation, or ascription of it. *Precision and clarification outrank vividness*: an image or analogy whose implication a following clause must retract or repair is a finding even when the repair succeeds.

Wiring: `agents/evaluator.md` (both gates mandatory at every applicable review depth), `references/REVIEW_ORCHESTRATION.md` (Step 4 routing + overlap map), `references/project_writing_style_checklist.md` (Part 3), and `skills/sentence-level-pass/SKILL.md` (→ **v1.4**: priority-gate section + Check 10 in the 10-point checklist; description updated). Two regression smoketests — `scripts/concept_introduction_contract_smoketest.py` and `scripts/semantic_predication_contract_smoketest.py` — assert the gate language stays present across all five surfaces and pin the live QE2026 fixtures (the L21 "the field's working unit is the *actor*" derivation failure and the "a hospital wants patient safety" anthropomorphism). Both are enforced by `scripts/release-gate.sh`.

**Why.** Surfaced during the QE2026 First-Principles RE Essay Ph4 precision pass. Two recurrent defect classes were slipping past the existing clarity and predication checks: (1) an analytical term arriving by fluent definition with no derivation from the preceding problem or entity ("a definition is not an introduction"), and (2) figurative or anthropomorphic phrasing that a neighbouring clause then had to disclaim, leaving conceptual debt. Earlier checks judged focus and grammatical clarity but neither the *provenance* of a construct nor the *truthful bearer* of a predicate, so both failures read as clean prose. Making them named, ordered gates — with the exact failures frozen as fixtures — converts a recurring reviewer miss into a design-time blocker.

**How to apply.** Nothing changes for normal invocation. Evaluators now run the concept-introduction gate first at Step 4 and the semantic-predication check on every definitional/modelling/ontological sentence; both yield MAJOR when the failure changes the frame or the claim. Maintainers gain `python scripts/concept_introduction_contract_smoketest.py` and `python scripts/semantic_predication_contract_smoketest.py` (also run by the release gate).

**Known remaining drift (out of scope, recorded).** The Cowork-installed plugin cache still carries `sentence-level-pass` at **v1.2** and lacks both gates; the canonical checkout is v1.4. Redeploy/reinstall of the installed cache is deferred to its own step and is not resolved by this release.

**Severity / attribution.** Maintainer feature increment, judgment-layer only; additive with no schema, ledger, or four-agent-contract change. All maintainer structural checks and both new smoketests green. Source: QE2026 First-Principles RE Essay precision-pass handoff (2026-07-12).

---

## v0.25.0 — 2026-07-07

### Advisor-surface alignment — Fable 5 baseline inherited from advisor plugin v0.4.0

**What changed.** The peer advisor plugin (`B:\Agents\platform\Advisor`) was audited and updated 2026-07-07 (v0.3.0 → v0.4.0): advisor model `claude-opus-4-7` → `claude-fable-5`, server pricing defaults US$15/US$75 → **US$10/US$50 per MTok** (Fable 5 list pricing, externally verified). This release aligns the harness's consumer surfaces: `skills/advisor-escalation/SKILL.md` (procedural-flow preamble, Step 1 cost-gate block, trigger-table example de-pinned from a model name, closing rule) and `references/SKILL_REGISTRY.md` SK-18 (re-worded "frontier-class advisor output" with a dated model pin rather than a bare model name).

**Why.** The Step 1 cost gate quoted Opus 4.x pricing against a server that now bills Fable 5 — every estimate would disagree with the server's footer telemetry, and the footer's model string (`claude-fable-5`) would look anomalous against skill text naming Opus 4.7. The harness's own drift rule (context contract §10: version stamped in every footer so the bridge skill can warn on drift) is the mechanism this fixes.

**How to apply.** Nothing changes procedurally. Steps 1–7, EXTERNAL-tag re-classification, EP-1/EP-2 entry points, and artifact filing are untouched. Users see updated pricing in the cost gate and `Advisor: claude-fable-5 … contract v1.4.0` in proof-of-life footers.

**Known remaining drift (out of scope, recorded).** (1) `references/MODEL_ALLOCATION.md` and `agents/planner.md` still pin dispatch models `claude-opus-4-7` / `claude-sonnet-4-6` / `claude-haiku-4-5` for the four-agent loop — that is the *subagent dispatch* plane, not the advisor plane; migrating it requires re-validating the capability ordering and `E-MA-DEPRECATED-MODEL` list, deferred to its own cycle. (2) Advisor-plugin audit finding F-4 (contract doc defines through v1.3.0; server stamps v1.4.0; packer implements neither) awaits an owner decision on the advisor side.

**Severity / attribution.** Maintainer increment, doc-plane only. Source: advisor plugin audit `Advisor/advisor-audit-2026-07-07.md` findings F-2/F-6.

---

## v0.24.0 — 2026-07-07

### Deferred-register closure — one ladder, one vocabulary, one authority per fact, every authority checked

**What changed.** The nine open items from the coherence audit (`2026-07-07_full-links-coherence-audit.md §4`), executed as a single linked program (full dispositions: `docs/analysis/2026-07-07_deferred-register-closure.md`):

- **Migration completed (items 1–3).** `REVIEW_ORCHESTRATION.md §3.3` rewritten phase-native with schema-verified spellings (stable tier-era *codes* keep historical spellings, each annotated); `AGENT_CONTRACTS.md §2` Evaluator contract reconciled — phase-gated preconditions, F7-default outputs, depth names mapped to `check_profile` envelopes, I-Refl-3 renumbered to the split reflectors; **T3R settled**: retired as an independent sibling per the newest authority (SKILL_REGISTRY v0.14.0 banner) — response-letter review is a manuscript-class within Ph3, `T3R` a historical label, legacy `tier=T3R` records still routing.
- **Migration enforced (items 4–5).** New `scripts/retirement-sweep-check.py` over `references/schemas/retired_surfaces.json` (15 retired scripts with provenance): no retired or missing script cited as live on live surfaces without a historical marker; unknown danglers always block. First sweep: 24 violations, zero unknown, all annotated in place. Count planes `section_state_field_count` (18) and `trigger_enum_count` (31) added to `version_planes.json` — the audit's dominant drift class is now design-time-blocked. Wired into gate (0.55/0.56), CI, both maintainer blocks, MANIFEST.
- **Contracts made portable (item 6).** Truncated/host-pinned MCP UUID namespaces in `seed-snowball-discovery` and `tool-contract-roundtrip` replaced with symbolic tool identities + resolve-at-runtime instructions.
- **Orphans disposed (items 7–9).** `GROUND_TRUTH.md` routed (binding P-stage vocabulary source, cited from classify-manuscript); planning-phase README marked historical; `protocol_constants.py` pickup failure documented in-file; convergence-journal fixture quarantined; packaging canonicalized to release-gate Phase 1; PHASE_PROTOCOL §2.2 marked reserved (no renumber — citation stability); new `phase_notifications_smoketest.py` (validates 37 entries, the deprecated forwarding stub, and loader import) wired into gate + CI; quick-deterministic coverage seam documented.

**Why.** The nine items were one defect expressed nine ways: the v0.7.4 tier→phase migration was declared complete but never enforced, so its residue kept resurfacing as danglers, forks, and pre-ladder contracts. This closure finishes the migration where it was incomplete and installs the checks that make incompleteness a blocker rather than an audit finding.

**How to apply.** Nothing changes for normal use. Maintainers gain `python scripts/retirement-sweep-check.py` and `python scripts/phase_notifications_smoketest.py`. Sole remaining fork: the recorded agent-file ladder fork (planner v0.8.0 / evaluator+generator v0.7.4) — harmonization still rides with a future dispatch-surface test. Stale `.claude/worktrees/` need a manual prune (host permissions).

**Severity / attribution.** Maintainer increment. One judgment call exercised under delegated authority: the T3R disposition (newest-declaration rule). 23/23 checks green.

---

## v0.23.0 — 2026-07-07

### Full-links coherence audit — healing schema-count drift, retirement residue, and the CI coverage gap

**What changed.** A four-lane parallel audit of the complete dependency graph (references↔MANIFEST, agent contracts, skills/commands/registries, scripts wiring) followed by ~45 anchor-verified mechanical fixes and CI expansion. Full report with finding classes, per-lane evidence, and the open judgment register: `docs/analysis/2026-07-07_full-links-coherence-audit.md`.

Headlines: every agent contract now agrees with `phase_state_schema.md` (18-field SectionStateObject, 31-trigger enum, 7-field `phase_entry_log` row with `model_used`); the planner's stale "Rule 1 digest exception applies at Ph1" leak is retired language everywhere; evaluator/orchestration pointers into the emptied reflector router now target the split files; `/run-iterate` shim, skill, and catalog agree it is the canonical iterate surface; the 0.15.1 stage×profile fork is recorded in `version_planes.json` (registry philosophy: record deliberately, never widen silently); SKILL_REGISTRY current-claim rows are phase-native; MANIFEST no longer overclaims completeness; `references/terminology_register.md` exists (three live files cited it for years while it didn't); four committed check-output dumps left `scripts/`; CI runs 21 checks instead of 9 — including `end_to_end_smoketest.py` and `d_style_profile_smoketest.py`, both formerly orphaned, the former catching two regressions introduced and fixed within this very cycle.

**Why.** Three growth patterns generated nearly all findings: schema-ahead-of-contracts (counts asserted in 10+ files with no registry guard), retirement residue (retired scripts/vocabulary cited as current in live protocol files), and alarm-narrower-than-gate (CI claimed "same check set" at 9/25). Each fix follows the established registry-over-prose direction; the remaining enforcement gap (a retirement-sweep check) heads the deferred register.

**How to apply.** Nothing changes for normal use. Maintainers: the CI honest-scope header names what stays gate-only; report §4 holds the nine open judgment items, led by the `REVIEW_ORCHESTRATION.md` tier-vocabulary rewrite, the pre-ladder `AGENT_CONTRACTS.md §2` evaluator contract, and the T3R retired-vs-sibling ontology decision.

**Severity / attribution.** Maintainer increment; additive/corrective, no behavioral contract redesign (count corrections align contracts to the schema authority they already cite). Audit lanes run as four parallel read-only subagents; every edit anchor-verified; 21/21 checks green post-remediation.

---

## v0.22.0 — 2026-07-06

### Registry-over-prose hardening — version planes, commitment interactions, judgment-layer evals, CI

**What changed.** A structural-integrity cycle driven by an evidence-first audit and an adversarial plan review (13 findings integrated; plan + review trail: `docs/analysis/2026-07-06_systematic-improvement-plan.md`):

- **WS-2 `references/schemas/version_planes.json` + `scripts/version-planes-check.py`** — snapshot-mode registry of every current-value version assertion for the non-package planes (lifecycle ladder, phase-state schema, evaluator envelope, stage × profile vocabulary), including the *known fork* (planner/PHASE_PROTOCOL assert v0.8.0; evaluator/generator assert v0.7.4). The check makes silent assertion drift and fork-widening blockers while tolerating the recorded fork. Harmonization to a single current value per plane is deliberately deferred — it edits agent dispatch descriptions and must ride with a dispatch-surface test.
- **WS-3 `references/schemas/commitment_interactions.json` + `scripts/commitment-interactions-check.py`** — all 28 C-1…C-8 pair classifications explicit (4 declared-tension, 4 protective-overlap, 4 meta-rule, 16 no-known-tension); adding C-9 without its 8 pair entries is a blocker. Moves interaction-collision discovery (cf. the C-6↔C-8/M-1 live-run find at v0.21.0) from live-run to design time. STYLE_COMMITMENTS.md remains authoritative for tension *content*.
- **WS-4 golden-manuscript eval scaffold** — `scripts/fixtures/golden/` (`golden_p2_theory.md`, 6 seeded defects across C-5/C-6/C-8; `golden_p1_brief.md`, false-positive control for the P2-gated moves; `manifest.json` with findings-file schema + code-family-first matching rule) and `scripts/eval/golden_eval_score.py` (deterministic scorer: per-defect recall, P1 false positives, `--baseline` regression exit). The scorer's smoke test caught and fixed a real matcher bug (broad-family steal), validating the schema-first design.
- **WS-5 CI** — `.github/workflows/structural-checks.yml` runs the full nine-check set on push/PR; the two new checks are wired simultaneously into `release-gate.sh` (Phase 0.55), root `CLAUDE.md`, and `AGENTS.md`, so gate and alarm enforce the same set.
- **WS-1 hygiene** — `RELEASE_v0.16.0_runbook.md` → `docs/release-notes/` (not gitignored `releases/`, which would have dropped it from version control); `extract_pdf_comments.py` → `scripts/`; `pdf_comments_dump.txt` → `scratch/` (disclosed untracking); `agents/reflector.md` "retained for one minor" replaced with an explicit retirement condition (host dispatch surface no longer names `reflector`).
- `references/MANIFEST.md` rows for the two new registries.

**Why.** The deterministic layer was regression-tested; the facts the agents must quote (version planes) and the spaces that grow quadratically (commitment pairs) were guarded only by prose, and the judgment layer had no regression measure at all. Each fix applies the package's own established pattern — one machine-readable authority + one check — to a surface that lacked it.

**How to apply.** Run the two new checks standalone or via `release-gate.sh`. After editing any judgment skill: run the pass over both golden fixtures (strip the inline defect markers before dispatch), transcribe findings into the manifest's findings schema, score with `golden_eval_score.py`, and treat recall drop / new P1 false positive as a release blocker once two baselines exist. Deferred register (harmonization sweep, context-economy trim, STYLE_COMMITMENTS §3/§6 demotion, convergence-metric calibration): plan §9.

**Severity / attribution.** Maintainer increment; additive, no agent-contract changes, no skill retirement. Adversarial review by clean-context agent; two of its BLOCKER findings (gitignored relocation target; day-one-blocker registry design) materially changed the implementation.

---

## v0.21.0 — 2026-07-01

### C-8 companion skills + the C-6↔M-1 interaction (from two live-run validations)

**What changed.** Completed the C-8 skill set and folded in two findings the live validation earned:

- New skill **SK-43 `definition-derivation-check`** (`skills/definition-derivation-check/SKILL.md`) — the isolated **M-1** pass: classifies each load-bearing term as derived / imported-motivated / stipulated, with the **C-6 upfront-glossary carve-in** (keys-only glossaries pass; a glossary that pre-states a derived construct's payoff is a `[MINOR — C-6↔C-8/M-1]` note). P2-gated.
- New skill **SK-44 `dissolution-move-check`** (`skills/dissolution-move-check/SKILL.md`) — the isolated **M-2** pass: scores each rival-engagement site on charitable reconstruction / named buried assumption / dissolution-vs-contradiction; strawman → `[MAJOR]`. P2-gated (a P1 piece holding positions open is correct non-convergence, not an M-2 failure).
- Both ship with command shims, `/plugin-commands` catalog rows, and `SKILL_REGISTRY.md` entries.
- **C-6↔C-8/M-1 interaction encoded.** `references/analytic_construction_guidelines.md §2 M-1` gains the reconciliation rule (a terminological glossary is M-1-compatible if keys-only; flag only entries that pre-state a derived construct's payoff); `STYLE_COMMITMENTS.md §1.0a` (C-6) and `§1.0d` (C-8) both carry the interaction note and the `[MINOR — C-6↔C-8/M-1]` finding code.
- **Applicability gate tightened.** `analytic-move-audit` and `analytic_construction_guidelines.md §5` now admit advisor-facing **conceptual briefs and working drafts toward a proposal** explicitly (genre label does not decide scope; the presence of a built conceptual argument does), closing the reviewer-judgment gap the first live-run exposed.
- `STYLE_COMMITMENTS.md §6` open-front updated: the companion-skill set is now complete.

**Why.** Two live-runs against QE2026 advisor artifacts validated the C-8 machinery and surfaced two real gaps. (1) The seven-move `analytic-move-audit` bundled M-1 and M-2, but those are the two highest-value, most-often-botched theory moves and deserve isolated single-purpose passes. (2) The P2 reciprocity draft's upfront "one word, one meaning" glossary sat exactly on a previously-unencoded fault line — the project's **C-6** terminological-consistency discipline pushes toward front-loaded stipulation while **C-8/M-1** pushes toward deferred derivation. Neither commitment's text acknowledged the other. (3) A substantive P1 supervision brief fell through the "memo" exclusion by reviewer judgment rather than by rule. The two-run contrast also confirmed the **P-stage gate** works: the same skill suppressed M-1/M-2/M-7 on the P1 brief (deliberate non-convergence read as appropriate deferral) and fired them on the P2 draft (catching the glossary/derivation tension).

**How to apply.** Run `/definition-derivation-check` for a fast M-1-only "did I stipulate or derive this?" audit, or `/dissolution-move-check` for an M-2-only "am I contradicting or dissolving?" audit; both refuse below P2. Author an upfront glossary as *keys-only* to satisfy C-6 without deflating a C-8/M-1 derivation. Rationale for the whole C-8 line: `docs/analysis/2026-07-01_abbott-system-of-professions-analytic-construction-and-C8-rationale.md §5`.

**Severity / attribution.** Maintainer increment; additive, no breaking change to C-1…C-8 or agent contracts. The two companion skills are P2-gated and orthogonal to SK-42.

---

## v0.20.0 — 2026-07-01

### C-8 analytic-construction discipline — claiming the analytic-move layer between C-2 and C-4

**What changed.** Added an eighth declared style commitment, **C-8 (analytic-construction discipline)**, and the substrate + standalone skill to ground it:

- New `references/analytic_construction_guidelines.md` — absorbs one sustained exemplar, Abbott's *The System of Professions* (1988), under the source-absorption pattern. Encodes seven analytic moves (M-1 definitional deferral; M-2 reconstruct-then-dissolve; M-3 counterexample-as-demolition; M-4 anaphoric demonstration; M-5 cadential verdict; M-6 calibrated confidence; M-7 meta-reflexivity), each with a verified grounding quotation and an operational test; the P-stage gating (M-1/M-2/M-7 are P2-only); the M-4/M-5 protective carve-outs; and a §6 reflexive coda mapping Abbott's *jurisdiction* theory onto the harness's own division of expert labor.
- New skill **SK-42 `analytic-move-audit`** (`skills/analytic-move-audit/SKILL.md`) + `commands/analytic-move-audit.md` shim + `/plugin-commands` catalog row + `SKILL_REGISTRY.md` entry. Standalone Abbott pass; P-stage-gated; carries the M-4/M-5 carve-outs that overturn a `sentence-level-pass` monotony/concision flag on demonstrative anaphora and cadential verdicts.
- `references/STYLE_COMMITMENTS.md` — C-8 row in the §1 table; new §1.0d full text; updates to the summary paragraph (C-8 as convergent, occupying the analytic-move layer), the §3 interaction table (Planner records C-8 applicability + P-stage; new Reflector analytic-move row), the §4 relaxation procedure (per-move suspension; P-stage gating by construction), §5 prohibitions (argument-feature stripping on "concision"; C-4≠C-8 over-claim), and §6 open fronts (M-6↔C-1 tension; the designed-but-unshipped companion skills; the reflexive jurisdiction lens).
- Agent wiring: `generator.md` (draft/revise under the moves; do not flatten M-4/M-5 on concision), `evaluator.md` (`[MAJOR — C-8/M-x]` findings, P-stage gate, carve-out overturn), `planner.md` (records C-8 applicability **and P-stage** at classification).
- `references/MANIFEST.md` — indexes the new C-8 substrate and (retroactively) the C-7 substrate.

**Why.** C-4 (Baird) audits whether a theory *has* the right parts; nothing audited whether those parts were *earned* by the argument. That analytic-move vacancy sat between C-2 (clause craft) and C-4 (static theory anatomy) with no claimant — and, exactly as idiolect did before C-7, an unowned feature got mishandled by the nearest adjacent check (a mechanical monotony flag reading Abbott's demonstrative anaphora as a rhythm defect). C-8 claims the vacancy and supplies the protective carve-outs so the craft skills stop mis-flagging argumentative features. The choice of Abbott is deliberate and non-colliding: the harness already absorbed Abbott-the-methodologist for C-7 (*Methods of Discovery*, *Digital Paper*); C-8 absorbs Abbott-the-theorist (*System of Professions*) — C-7 protects the writer's voice, C-8 governs the writer's argumentative moves.

**How to apply.** C-8 is on by default for any piece that builds or extends a theory or conceptual argument; the Planner also records the P-stage, which gates the move set (P0/P1 → M-3/M-5/M-6; P2 → all seven). Suspend a single move or the whole commitment via `research_notes/directives.md` for venues that expect flat assertion or up-front stipulation. Run the standalone pass with `/analytic-move-audit`. Full rationale + per-move analysis + the reflexive jurisdiction lens: `docs/analysis/2026-07-01_abbott-system-of-professions-analytic-construction-and-C8-rationale.md`.

**Severity / attribution.** Maintainer increment; additive, no agent-contract retirement, no breaking change to C-1…C-7. *Grounding caveat:* all Abbott 1988 quotations verified character-for-character against the uploaded full-text extract; chapter-level locators are used because the digital edition lacks stable pagination.

---

## v0.19.0 — 2026-06-30

### C-7 authorial voice-fingerprint preservation — the first protective style commitment

**What changed.** Added a seventh declared style commitment, **C-7 (authorial voice-fingerprint preservation)**, and the substrate to ground it:

- New `references/voice_preservation_guidelines.md` — absorbs four craft authorities (Moran *First You Write a Sentence*; Zinsser *On Writing Well*; Strunk *Elements of Style*, original edition; Abbott *Methods of Discovery* + *Digital Paper*), corroborated by Turabian ch. 11 and the Penguin "Good style" chapter, under the v0.17.0 source-absorption pattern. Encodes the mechanics/identity split, the idiolect non-target list, the anti-pattern catalogue, and the baseline-before-register operationalization.
- `references/STYLE_COMMITMENTS.md` — C-7 row in the §1 table; new §1.0c full text; updates to the interaction table (Planner/Reflector), the §4 relaxation procedure (C-7 relaxes *inverse* to C-1…C-4 — on by default, suspended when a borrowed/house voice is chosen), §5 prohibitions (idiolect-stripping on taste), and §6 open fronts (C-7↔C-1 tension; baseline source).
- `references/SAFEGUARD_LAYER.md` Check 6 — new Step 0 establishes the author's idiolect baseline *before* register-marker counting; the degraded-voice verdict now distinguishes drift from the author's baseline (a C-7 regression) from drift from a borrowed exemplar (often acceptable).
- Skills tuned with a C-7 carve-out: `sentence-level-pass` (v1.1→1.2; monotony/passive/length flags yield to baseline idiolect; Moran "average not maximum") and `narrative-structure-pass` (v1.0→1.1; Check 7 "Consistent voice" no longer fires on baseline idiolect).
- Agent wiring: `generator.md` (burden-of-proof-on-rewrite), `evaluator.md` (`[MAJOR — C-7]` finding + baseline-first scoring), `planner.md` (records C-7 applicability at classification).
- **Review-hardening (post-review pass).** Two guards added so C-7 cannot be over-claimed: (i) **baseline-confidence tiering** — a baseline from accepted prior prose carries full force, but a baseline from only the least-revised current draft is *provisional* (C-7 findings drop to [MINOR]/ADVISORY; craft flags are noted, not suppressed, pending author confirmation); (ii) **disciplined-idiolect guard** — recurrence alone does not protect a feature, so a recurring mechanical error or surviving LLM tic is still flagged, not shielded. Propagated through `voice_preservation_guidelines.md` §§2,5, `STYLE_COMMITMENTS.md §1.0c`, `SAFEGUARD_LAYER.md` Check 6 Step 0, and both craft skills. Also: `.gitignore` now ignores the stray `scripts/audit/reviews/` auditor-output dir (canonical findings live at project-root `reviews/`).

**Why.** C-1…C-6 were all *convergent* — they say what prose should move toward — so idiolect-bearing features (sentence-length signature, repetition tolerance, point of view, cadence, humor, evaluative stance) had no defender and were silently optimized away. The pre-existing voice audit (Check 6) scored "humanness" only against borrowed exemplars (Suchman/Vidal), so the harness could flatten an author *in the name of* protecting voice. C-7 is the first **protective** commitment: it names what must not be lost and scores voice against the author's own baseline first.

**How to apply.** C-7 is on by default for any piece in the author's own voice; suspend it via `research_notes/directives.md` only when adopting a borrowed/house voice. Style rewrites must now cite a correctness, clutter, or C-5 accessibility warrant before touching an identity-layer feature — taste alone is a C-7 violation. Full rationale + per-book analysis: `docs/analysis/2026-06-30_voice-fingerprint-analysis-and-C7-rationale.md`.

**Severity / attribution.** Maintainer increment; additive, no agent-contract retirement, no breaking change to C-1…C-6. *Grounding caveat:* the absorbed *Elements of Style* is Strunk's original, not Strunk & White; White's "Approach to Style" is not relied on.

---

## v0.18.0 — 2026-06-29

### D-STYLE profile-routing check + canonical pre-flight consolidation + surface-floor validators

**What changed.** Added an executable consumption layer for the workspace-level D-STYLE research-writing architecture (reference/d-style-research-architecture.md):

- New `scripts/d_style_profile_check.py` (schema 1.1.0): validates the optional `research_notes/directives.md` `d_style_profile` block (enum validation, inherit-by-absence defaults), emits active D-STYLE obligations, and runs surface-floor validators for argument (claim/reason/evidence/warrant/limit), visual-evidence (source/scale/method/limit), and assistance-disclosure cues. New `scripts/d_style_profile_smoketest.py` (5 cases).
- Canonical pre-flight consolidation: `scripts/audit/run_all.py` gains `--project-root`, emitting both `reviews/findings.json` and `reviews/d_style_profile_YYYY-MM-DD.json` from one command; legacy positional API preserved.
- Wiring: profile-routing pre-flight documented in `DETERMINISTIC_CHECKS.md` section 0, cited by `agents/evaluator.md` before Step 0a, scheduled by `agents/planner.md`, routed in `MANIFEST.md`, admitted in `ARTEFACT_FRONTMATTER_SCHEMA.md` checks_scheduled, and seeded in `PROJECT_BOOTSTRAP.md`.

**Why.** D-STYLE was documented and routed but had no executable reader for its profile declaration. This consumes the profile at pre-flight time and gives the routed obligations a deterministic floor.

**How to apply.** Run `python scripts/audit/run_all.py "<manuscript>" --project-root "<project-root>" --date YYYY-MM-DD`. Treat surface findings as a floor only: a `*_SURFACE_PRESENT` result means the cues exist, not that warrant exposure, visual honesty, or argument adequacy are sufficient — adequacy remains Evaluator judgment (D-STYLE section 9 keeps an open front for stronger substantive validators).

**Severity / attribution.** Maintainer increment; no agent-contract retirement. Surface validators are advisory floor checks; missing assistance disclosure is MAJOR under project_local and BLOCKER under venue_required or overseer_escalate.

## v0.17.0 — 2026-06-28

### Three external-manual integration (Turabian, Abbott, Blue Book)

**What changed.** Absorbed three writing authorities into the harness under the established source-absorption pattern (`references/<source>_guidelines.md` + optional paired skill + binding hooks), routing each to the layer whose contract it actually extends rather than treating them uniformly:

- **Blue Book of Grammar & Punctuation** (Kaufman & Straus) → mechanical/correctness layer. New `references/blue_book_grammar_guidelines.md`; new skill **SK-40 `grammar-mechanics-pass`**; new `DETERMINISTIC_CHECKS.md §3b` grammar-mechanics work queue; Generator invariant **I-Gen-9** (read-before-copyedit, declared-style precedence, em-dash deferral).
- **Turabian / Chicago** → citation-*form* + mechanical style. New `references/turabian_chicago_guidelines.md`; new skill **SK-41 `citation-format-pass`** (orthogonal to `CITATION_DISCIPLINE.md`'s whether-to-cite judgment, cross-referenced both ways).
- **Abbott, *Digital Paper*** → research-*process* layer (read-surface, **no skill**). New `references/abbott_2014_research_process_guidelines.md`; readiness hooks in `PROJECT_BOOTSTRAP.md` and `seed-snowball-discovery` (preliminary→midphase→endphase model; brute-force-is-midphase rule complements the Wohlin snowball).

**Why.** The harness owned sentence *craft* (Bacon) and em-dash *discipline* but had no correctness/copyedit surface and no citation-*form* surface; Abbott fills the pre-drafting research-process gap upstream of Ph1.

**How to apply.** `/grammar-mechanics-pass` for copyedit/proofread; `/citation-format-pass` for Turabian/Chicago citation conformance; the Planner reads the Abbott guideline at bootstrap and before snowball runs. Shared mechanics conflicts (Blue Book ↔ Turabian Part III) resolve by declared `citation_style`, emitting `[CONFLICT]` rather than silently choosing.

**Provenance.** `docs/superpowers/plans/2026-06-28-three-manuals-integration.md`. Raw source extractions committed under `references/resources/`. Skill count 35 → 37.

---

## v0.16.0 — 2026-06-25

### PR-3b.4 compatibility landing

**What changed.** The public lifecycle surface is now the three-stage ladder
`/run-draft` -> `/run-iterate` -> `/run-finalize`. Former Ph2 review routes to
`/run-iterate --profile refine`, and former Ph3 stability routes to
`/run-iterate --profile stability`.

**Compatibility.** Legacy `/run-phase-2` and `/run-phase-3-stability` commands
remain shipped as compatibility routers so existing project automation,
historical ledgers, and slash-command histories continue to resolve. They should
not be advertised as separate public stages in new guidance.

**Validation.** `scripts/alias_parity_smoketest.py` now pins the compatibility
routing contract instead of pinning the old PR-3b.3 absence/preservation
contract.

### BFO ontology design guideline + C-6 scoped-metaphor commitment

**What changed.** New canonical reference `references/BFO_ONTOLOGY_DESIGN.md` — an operational policy for building,
extending, formalizing, or auditing BFO-aligned domain ontologies (realism, univocity, single-rooted `is_a` structure,
disciplined provenance), paraphrasing Arp, Smith & Spear, *Building Ontologies with Basic Formal Ontology* (MIT Press,
2015), ch. 3–4. New style commitment **C-6 — “rhetorical–analytical separation & scoped metaphor”** in
`STYLE_COMMITMENTS.md §1.0a`: the same term for the same concept; rhetorical force kept clear of any unstated analytical
commitment; every load-bearing metaphor (`layer`, `cube`, `above`, `below`, `control`, `weight`, `machine`, `system`,
`AI`, `human`, `static`) declares what it is used for and which aspect bears load, with the ontology behind
spatial/mechanical metaphors made explicit. Adds a `references/MANIFEST.md` routing entry and binds the Planner,
Evaluator, Generator, and root `AGENTS.md` / `CLAUDE.md` to both surfaces.

**Why.** Both surfaces operationalize directives from the INF3006Y supervisor meetings (C-6 dated 2026-06-18,
reinforced 2026-06-25): separate rhetorical from analytical wording, and make the ontology behind metaphors explicit.
The BFO guideline carries a strict trigger boundary — it governs formal ontology artifacts only (ontology, module,
term/definition set, or an audit of one), never ordinary philosophical or metaphor uses of “ontology,” schemas, or
knowledge graphs.

**How to apply.** The Planner names whether C-6 applies at classification time; the Generator and Evaluator hold the
piece against it. Apply `BFO_ONTOLOGY_DESIGN.md` only when the requested artifact is a formal ontology or an audit of
one; otherwise record BFO alignment as a proposal or question rather than assuming it.

**Provenance.** Landed unversioned at commit `5182c9f` (2026-06-22); formalized into this release 2026-06-25. Also in
0.16.0: wiki-path migration to `knowledge/LLM wiki/` across the affected skills (`f7d4548`).

## v0.15.0 — 2026-05-13

**What.** Strict-Layers architecture — a coordinated nine-commit stack that promotes regex-in-markdown to executable scripts, closes the citation self-attestation loop, lands a backwards-compatible lifecycle bridge with new vocabulary aliases, adds a routing-index progressive-disclosure layer, splits the Reflector by dispatch mode, and ships warn-only token-budget measurement.

**Why.** The v0.15.0 architecture audit found four classes of debt: (1) regex catalogues stored in markdown but executed by the LLM at runtime, (2) circular citation self-verification where the LLM that cited a rule also "verified" it, (3) eager-load orchestration prelude that named ~13 reference files unconditionally, (4) a 20,113-token Reflector agent that was the second-largest agent in the package and routinely loaded for every dispatch regardless of mode. Strict-Layers separates *script* from *judgment*, *truth* (binding `inviolable` severity) from *taste* (`default` severity), and *lifecycle stage* (monotonic) from *review profile* (per-iteration dial).

**How to apply.** Read `references/MANIFEST.md` first to find the file you need; `references/CLAUDE.md` is now ~83 lines of invocation rules + precedence ladder, not a routing list. Run `scripts/audit/run_all.py <manuscript>` for the mechanical pre-flight (the `/quick-deterministic` skill v2 wraps this). Citation grounding is now a script: `scripts/audit/audit_citations.py` resolves `[GP §N]` / `GROUNDING_PROTOCOL.md §Rule N` against the stable HTML anchors in `GROUNDING_PROTOCOL.md`, and the release-gate fails closed on unresolved citations. The new `stage` / `profile` shadow fields on every `SectionStateObject` are additive — existing ledgers continue to validate; `scripts/migrate_v0150pre_add_stage_profile.py` is the idempotent backfill helper. New skill aliases `/run-draft` / `/run-iterate` / `/run-finalize` resolve alongside the canonical `/run-phase-1` / `/run-phase-3` / `/run-phase-4`. Reflector dispatch resolves to `agents/reflector-probe.md` (lightweight Ph1–Ph3) or `agents/reflector-closeout.md` (full Ph4); the legacy `agents/reflector.md` is a one-minor compatibility router. Token-budget measurement is warn-only; check `reviews/token_budget_report.json` to see the top-10 largest files.

**The nine-commit stack (oldest to newest on `main`):**

1. **PR-1 + PR-2 (`68ced21`)** — Snippet includes mechanism under `references/_snippets/` (resolved at packaging time by `scripts/resolve_includes.py`; anti-duplication guard at `scripts/snippet-check.py`). Scripts-first audit suite at `scripts/audit/` with canonical `Finding` / `FindingsReport` schema (two-tier severity: `inviolable` for truth, `default` for taste); 13 check classes spanning absolutes, em-dash, LLM tics, voice, sentence length, passive voice. Replaces the `/quick-deterministic` LLM-prosecuted regex counting with a deterministic Python wrapper.
2. **PR-3a (`43576b3`)** — Stable `<a id="gp-N"></a>` HTML anchors above every rule heading in `references/GROUNDING_PROTOCOL.md` (rules 1–7, 7a). Substrate for the deterministic citation resolver. CI guard at `scripts/grounding_anchors_check.py` fails closed on rename-without-anchor-update regressions.
3. **PR-3b.1 (`8fd4ede`)** — Additive `stage` (`draft`/`iterate`/`finalize`) and `profile` (`refine`/`structural`/`deep`/`stability`) shadow fields. `scripts/phase_state_validate.py` accepts both; `scripts/migrate_v0150pre_add_stage_profile.py` backfills idempotently from `current_phase` and `check_profile`. Zero behaviour change; the bridge exists so PR-3b.2/3 can target a stable schema surface. 11/11 smoketest.
4. **PR-3b.2 (`14c63d7`)** — MCR convergence-evidence advisory `W-MCR-CONVERGENCE-EVIDENCE`. Helper `_compute_mcr_convergence_evidence` reads convergence-log iteration rows; fires iff the last two rows carry a non-refine `profile`, `findings_count_delta: 0`, and the same non-null `convergence_metric`. Explicitly **does not** substitute for the human `TerminalSignoffRow`; the W- prefix routes the advisory to warnings per `pre_phase_advance_check.py`'s exit-code split. Behaviour-identity table pins `_is_mcr_cleared` unchanged. 13/13 smoketest.
5. **PR-3b.3 (`3dd9621`)** — Phase-skill aliases. New skills `/run-draft`, `/run-iterate`, `/run-finalize` with matching command shims and `SKILL_REGISTRY.md` entries SK-37/38/39. Old `/run-phase-N` canonical preserved. Parity smoketest pins `test_ph2_has_no_alias` (Ph2 is the rung the architecture intends to merge later — aliasing it now would lock in a surface we may collapse) and `test_run_phase_3_stability_preserved`. 8/8 smoketest.
6. **PR-4a (`4abf492`)** — Deterministic citation resolver. `scripts/audit/audit_citations.py` parses three canonical citation forms (`GROUNDING_PROTOCOL.md §Rule N`, multi-rule lists, `[GP §N]`) and resolves them against the live anchor set. Findings carry `severity: inviolable` (citation is a truth claim). The release-gate walks `references/`, `agents/`, `skills/`, `commands/` and fails closed on any unresolved citation. 8/8 smoketest.
7. **PR-4b (`3f485f4`)** — `references/MANIFEST.md` (158 lines) routing index. `references/CLAUDE.md` slimmed from 150 → 83 lines while preserving every binding rule and the §4 precedence ladder verbatim. `scripts/manifest_links_check.py` enforces (A) every backticked file in MANIFEST resolves under the appropriate root, and (B) CLAUDE.md continues to name `GROUNDING_PROTOCOL.md` + `MANIFEST.md` and retains all seven precedence-line fragments.
8. **PR-4d (`7e2a813`)** — `scripts/token_budget_check.py` with `tiktoken` cl100k_base; per-class budgets (agents warn>300/fail>700, references warn>600/fail>1000, skills warn>120/fail>250, snippets warn>40/fail>60). Strictly warn-only; release-gate increments `WARNINGS`, never `BLOCKERS`. Captures the top-10 largest files and an always-loaded prelude floor measurement (12,109 tokens; 8k target unreachable without slimming `GROUNDING_PROTOCOL.md`, which is binding).
9. **PR-4c (`e085831`)** — Reflector split. `agents/reflector-probe.md` (3,405 tokens) for Ph1–Ph3 lightweight integrity probes (Phases 1, 2f, 2.5, 2.5.1, 2.6, 3, 5, 6); `agents/reflector-closeout.md` (5,875 tokens) for Ph4 full reflection (all phases including 2/2b/2d/2e/2g/4). Shared `_snippets/reflection-grounding.md` (1,486 tokens) carries binding-constraint, dispatch modes, output contract, invariants, and v0.7.4 vocabulary. `agents/reflector.md` (970 tokens) retained as compatibility router for one minor. Per-mode dispatch cost: lightweight 4,891 tokens (−76%), closeout 7,361 tokens (−63%). 8/8 parity smoketest.

**Files added or modified (high-level):**

- New scripts (10): `scripts/audit/{audit_style.py, audit_citations.py, run_all.py, schema.py, test_audit.py, test_citations.py}`, `scripts/{resolve_includes.py, snippet-check.py, grounding_anchors_check.py, migrate_v0150pre_add_stage_profile.py, migrate_v0150pre_stage_profile_smoketest.py, mcr_convergence_evidence_smoketest.py, alias_parity_smoketest.py, manifest_links_check.py, token_budget_check.py, token_budget_smoketest.py, reflector_split_parity_smoketest.py}`, `scripts/tests/test_resolve_includes.py`.
- New references: `references/MANIFEST.md`, `references/_snippets/{output-profile.md, reflection-grounding.md}`.
- New agents: `agents/{reflector-probe.md, reflector-closeout.md}`.
- New skills: `skills/{run-draft, run-iterate, run-finalize}/SKILL.md` with matching command shims under `commands/`.
- Slimmed: `references/CLAUDE.md`, `agents/reflector.md`.
- Anchored: `references/GROUNDING_PROTOCOL.md` (stable `gp-N` IDs).
- Extended: `references/phase_state_schema.md §2.2`, `scripts/phase_state_validate.py`, `scripts/pre_phase_advance_check.py`, `scripts/release-gate.sh` (eight new phases 0.60a–0.60d5), `.gitignore` (token-budget report), `references/SKILL_REGISTRY.md` (SK-37/38/39), `skills/plugin-commands/SKILL.md` (alias rows), `references/REVIEW_ORCHESTRATION.md`, `references/OPERATING_MANUAL.md`, `skills/quick-deterministic/SKILL.md` (v2.0 scripts-first), `scripts/build-plugin.py` (snippet rendering in bundle).

**Lessons feed-forward (Reflector recurrence-audit candidates):**

1. **Eager-load reduction validation.** PR-4b cut CLAUDE.md from 150 to 83 lines. The recurrence audit should monitor whether agents that route via MANIFEST.md actually load fewer reference files per dispatch versus pre-4b — if MANIFEST gets consulted but agents continue to load the full reference list "just to be safe," the slim is cosmetic.
2. **Citation auditor false-positive surveillance.** PR-4a's auditor errs precision-over-recall (bare `Rule N` prose without the `§` qualifier or `[GP]` short form is deliberately not matched). The reflector should watch for cases where genuine GP citations slip past resolution because authors used a non-canonical form, and propose a citation-style normalization pass if that becomes a real failure mode.
3. **Token-budget threshold calibration.** PR-4d's measurement shows the architecture's aggressive thresholds (e.g., 300/700 for agents) are unreachable for the largest files. A future right-sizing decision should come *after* observing whether the Reflector split's pattern reduces other agents' totals, not from theoretical budgets.
4. **Reflector-router retirement timing.** `agents/reflector.md` is committed as a one-minor compatibility router. The reflector should track when project CLAUDE.md files and slash commands have all migrated to `reflector-probe` / `reflector-closeout` so the router can be retired at v0.16.0 without breakage.
5. **PR-3b.4 deferral re-examination.** The Ph2 → Ph3-refine merge was deferred because deleting a live phase surface is high risk. The reflector should keep this in the proposal queue and revisit after one or two release cycles' worth of `stage`/`profile` field-population data — if every Ph2-tagged section also carries `profile: refine`, the merge becomes empirically grounded rather than speculative.

**Severity / agent attribution.** No BLOCKER findings cleared (this is a structural release, not a defect patch). One major LLM-self-attestation hole (Category 4 grounding) closed by PR-4a. Reflector contract surface formally split (PR-4c) without behaviour change. Generator and Evaluator contracts unchanged. Planner contract gains a new advisory output (`W-MCR-CONVERGENCE-EVIDENCE` at the MCR boundary). Skill count: 32 → 35 (+3 aliases; no canonicals retired). Command count: 16 → 19 (+3 shims).

**Deferred for a later release.** PR-3b.4 — merging Ph2 into `/run-iterate refine` and thinning `run-phase-3-stability` to a delegation wrapper — is intentionally out of scope. The current stack is a coherent compatibility-preserving slice; PR-3b.4 deletes/reroutes a live phase surface and is best handled after one or two release cycles of stability on the v0.15.0 surfaces.

---

## v0.14.0 — 2026-05-04

**What.** Output economy (evidence-first defaults): F7 JSON evidence packets, F8 final round reports, `OUTPUT_ECONOMY_PROTOCOL.md`, schema and template, phase-skill and agent contract updates, `output_economy_check.py` / `output_economy_smoketest.py`, and `artefact_frontmatter_validate.py` F7/F8 lanes wired into `release-gate.sh`.

**Why.** Reduces default Markdown report volume per round while preserving machine-checkable evidence and a single human-facing round report; documents compatibility pointers for legacy paths.

**How to apply.** Read `references/OUTPUT_ECONOMY_PROTOCOL.md`; run `python scripts/output_economy_check.py` and `python scripts/output_economy_smoketest.py` before release; Planner assembles F8 per agent instructions.

---

## v0.13.0 — 2026-04-30

**What.** Voice / register / citation lessons batch from the INF3006Y late-April 2026 sessions. Six lesson clusters surfaced from the 2026-04-29 reverse-engineering handoff, the 2026-04-30 manuscript polish session, and the in-session voice round 2 + lay-term twin-fix. The patch closes operational-specificity gaps on existing C-1 / H surfaces and adds three new surfaces (Sub-check J under SAFEGUARD; new `CITATION_DISCIPLINE.md`; new top-level `EMDASH_BUNDLE_DISCIPLINE.md` with Generator binding). Per the Q5 versioning-policy answer, three new surfaces + one Generator default-behavior change put this batch firmly in MINOR territory.

**Why.** Each lesson surfaced as a recurrent failure pattern. Voice/attribution drift across structurally parallel sites (the §3 hidden-assumption diagnoses; the §4.1/4.2/4.3 questions-framing predications) was C-1-discoverable in principle but not caught operationally because C-1 is a commitment, not a verb-set. Lay-term protocol violations recurred at structurally parallel sites (the §2 / §5 twin-paragraph pattern with identical "stipulating away" / "operational reductions that stabilize" phrases) but H lacked a twin-paragraph detector. Verdict-edge intensifier-stacking ("the very" + "supposed to" + "is eroded") drifted from diagnostic to verdict register without an existing sub-check to flag it. Citation discipline at register-boundary asides was operating implicitly but not codified. The em-dash bundle (humanizer rules 13 + 9 + 11) was partly captured at DETERMINISTIC_CHECKS §3 line 63 but the bundle-treatment discipline was not at top-level binding force, and a single em-dash audit was missing the co-occurrent rules 9 and 11.

**How to apply.** Six clusters land in seven content patches:

- **Cluster 3.1 — Voice / attribution discipline.** `STYLE_COMMITMENTS.md §1.1` (new): canonical first-person verb-set (`I identify`, `I read [X] as`, `I press`, `I find`, `I trace`, `I group`, `I mark`, `I characterize`); parallelism discipline requiring sibling-site audits within the same revision round; Reflector Check 6 treats sibling-site drift as higher severity than isolated drift.
- **Cluster 3.2 — Verdict-edge / intensifier-stack discipline.** `SAFEGUARD_LAYER.md` Sub-check J (new, advisory_until J_two_revision_cycles): three-class intensifier counter (emphatic determiners / deontic-implicit phrasings / verdict verbs); cross-class stack of three or more fires; modal-distribution softening rule per the INF3006Y Fügener-finding precedent (`is eroded by the very X it is supposed to anchor` → `may not remain stable under the X to which it is supposed to anchor`).
- **Cluster 3.3 — Twin-paragraph detection.** `skills/accessibility-overlay/references/sub_checks.md §H` step 1 augmented with `_twin_paragraph` probe; shibboleth phrases extracted from H finding's evidence field automatically; `twin_candidate_<location>` follow-on findings emitted on >0 outside-passage hits.
- **Cluster 3.4 — Citation discipline at register-boundary asides.** `references/CITATION_DISCIPLINE.md` (new file): engagement-cite vs. demarcation-no-cite two-question test; INF3006Y precedent (`tool calls (Schick et al., 2023)` engagement-cite vs. `incentive-incompatibility` / `contract-net protocol` demarcation-no-cite); four edge cases.
- **Cluster 3.5 — Lay-term protocol corpus addition.** `lay_term_lexicons.md §5` (new): seven drift-monitored paraphrase entries from the §2 / §5 twin-fix; mandatory `_corpus_drift` grep-cadence at every H-cycle; "Take X:" worked-example signpost-as-M4-vehicle pattern.
- **Cluster 3.6 — Em-dash bundle elevation (top-level discipline + Generator binding).** `references/EMDASH_BUNDLE_DISCIPLINE.md` (new file, parallel binding force to GROUNDING_PROTOCOL): three co-occurrent rules (B1 em-dash / B2 negative parallelism / B3 triadic-list), mandatory co-audit at every Generator prose action, bundle delta check (post-action counts ≤ pre-action) enforced, multi-rule fixes commit in single revision pass; waiver requires explicit user instruction in current session naming paragraph + rule + rationale; inherited waivers from prior sessions invalid; Generator cannot self-waive. `agents/generator.md` second binding constraint added. `references/CLAUDE.md` row 9c registers the discipline.
- **Cluster 3.6 (procedural) — Cross-file mirror grep discipline.** Memory entry under `feedback_*`: after any cross-file edit touching paired canonical files (.md/.tex), run two verifying greps before declaring sync complete (deprecated phrases must return zero; new phrases must return present in both files).

**Files added or modified.**

- `references/STYLE_COMMITMENTS.md` — new §1.1 (C-1 verb-set + parallelism rules)
- `references/lay_term_lexicons.md` — new §5 (DRIFT-MONITORED corpus); v0.13.0 status header
- `skills/accessibility-overlay/references/sub_checks.md` — new "Twin-paragraph probe (added v0.13.0)" sub-section under H step 1
- `references/SAFEGUARD_LAYER.md` — new Sub-check J — Verdict-Edge Discipline; output-format augmented; aggregation rule line updated
- `references/CITATION_DISCIPLINE.md` — new file (8 sections)
- `references/EMDASH_BUNDLE_DISCIPLINE.md` — new file (6 sections)
- `agents/generator.md` — Second binding constraint (em-dash bundle) at line 27
- `references/CLAUDE.md` — rows 9c (EMDASH_BUNDLE_DISCIPLINE) and 9d (CITATION_DISCIPLINE) added to §3 components table
- `docs/superpowers/plans/2026-04-30-voice-and-h-lessons.md` — source memo
- Memory: `feedback_cross_file_mirror_grep_discipline.md`

**Lessons feed-forward (Reflector recurrence-audit candidates).**

1. **Operational-specificity gap.** Three of the six clusters were "discoverable from C-1 / H principles in place but not operationally caught." The recurrence audit should monitor whether subsequent rounds emit findings against the new operational rules (verb-set, twin-paragraph probe, intensifier-stack floor) at meaningfully higher detection rates than prior rounds. If yes, the operational specificity is closing real gaps; if no, the lessons may have been overfit to INF3006Y.
2. **Drift-monitored corpus path validation.** The `lay_term_lexicons.md §5` entries are anchored to live-manuscript source phrases. The `_corpus_drift` probe must run at every H-cycle on INF3006Y; first drift-detection on a contributing source phrase will validate or falsify the path-(a) approach. If multiple §5 entries flip to RETIRED within two cycles, the immutable `references/examples/` commit path becomes preferred for future corpora.
3. **Bundle-treatment economy claim.** The em-dash bundle treatment claims "single audit pass with three-rule coverage" reduces Generator overhead vs. three separate audits. Reflector Phase 2g should monitor whether bundle-flagged paragraphs in subsequent rounds show co-occurrence of all three rules (validating the cluster-signal premise) or whether the rules fire independently (suggesting the bundle is a discipline-of-convenience rather than an empirical-cluster rule).

**Severity / agent attribution.** No BLOCKER findings cleared; one D-02 / P0 register WARN closed (Edit 7 softening per cluster 3.2). No agent retirements or capability changes. Generator gains a second binding constraint (cluster 3.6, parallel to GROUNDING_PROTOCOL). Reflector Check 6 gains sibling-site drift weighting (cluster 3.1). Evaluator Sub-check H gains twin-paragraph probe (cluster 3.3) and Sub-check J (cluster 3.2). Skill count invariant unchanged. §6.0 coupling-checklist EXEMPT throughout (no schema change, no phase-runner step edit).

---

## v0.12.3 — 2026-04-28

**Marketplace-schema alignment patch.** v0.12.3 restructures
`marketplace.json` to clear the Cowork remote-marketplace upload
validator (`uploadAccountPlugin` endpoint), which rejected v0.12.2
within minutes despite the static `loader-compat-check.py` returning
CLEAR. No agent contract, skill, command, or governance-field
change. Diagnosis and validator scope-limit lessons recorded below.

### What changed

- **`.claude-plugin/marketplace.json`** restructured along four axes:
    * Added `$schema: "https://anthropic.com/claude-code/marketplace.schema.json"`
      at the top of the document — the validator expects a schema
      declaration; absent in v0.12.2 and prior.
    * Removed top-level `description` and re-anchored it under
      `metadata.description`. Per the marketplaces docs, `description`
      is also accepted under `metadata` for backward compatibility;
      the working peer (`token-optimizer` at
      `rpm/plugin_01BueBLWJxwbkpJsWFnyw4nK/.claude-plugin/marketplace.json`)
      places it there, suggesting the remote validator prefers — or
      requires — the metadata anchor.
    * Renamed top-level `name` from `co-author-harness` to
      `joseph-chung-co-author-harness`, namespacing the marketplace
      identifier with the maintainer's name. Token-optimizer uses
      `<github-handle>-<plugin-name>`; the maintainer chose a
      personal-name prefix instead. Either way, the bare
      `co-author-harness` form was unverified against the validator
      and presumed insufficient.
    * Changed `plugins[0].category` from `"research"` to
      `"productivity"`. `"research"` is not corroborated anywhere in
      the marketplaces docs or the only working peer manifest;
      `"productivity"` is the documented example value and a
      confirmed-accepted enum member. Semantic accuracy traded for
      validator acceptance; revisit if/when an enum schema with
      `"research"` is published.

- **`.claude-plugin/plugin.json`** unchanged except for the version
  bump (0.12.2 → 0.12.3). The direct-install schema validated by the
  Cowork plugin loader UI was correct in v0.12.2 and remains correct.

### Architectural posture and rationale

- **Two distribution paths, two schemas.** The Cowork plugin loader
  has at least two install paths: direct local `.plugin` upload
  (validates `plugin.json`) and remote `uploadAccountPlugin` to a
  personal marketplace (validates `marketplace.json`). The schemas
  are different. A bundle that passes one is not guaranteed to pass
  the other. Recorded as a binding constraint in the agent's auto-
  memory (`feedback_cowork_dual_plugin_install_paths.md`); future
  plugin work for this maintainer must default to confirming the
  install path before validating.

- **Static verification scope limit.** The `loader-compat-check.py`
  validator landed in v0.12.2 covers the direct-install schema only.
  Its v0.12.2 CLEAR verdict was correct on its own terms but said
  nothing about marketplace-upload acceptance. Going forward,
  `loader-compat-check.py` should be extended with a
  marketplace-schema axis (deferred from v0.12.3 to keep the diff
  minimal); until extended, its CLEAR verdict must be qualified as
  "structurally valid for direct local install" rather than
  "loader-ready" in the unqualified sense.

- **Diagnosis-before-fix discipline held.** v0.12.2's rejection
  surfaced as a generic "Plugin validation failed for both files"
  banner with no diagnostic detail. Reading the Cowork main.log at
  `%APPDATA%\Claude\logs\main.log` narrowed the failure class to the
  marketplace endpoint and its schema in roughly three turns — far
  cheaper than patch-and-pray iteration. Recorded as
  `reference_cowork_main_log.md` in the agent's auto-memory; future
  plugin-load debugging must start with the log before any other
  diagnostic step.

### Skills, commands, agents, governance fields

- No additions, removals, or renames. Skill count invariant holds;
  no governance-field changes; no migration script required.

### Deferred items (carried into v0.12.4 candidate scope)

- Extend `scripts/loader-compat-check.py` with a marketplace-schema
  validation axis covering `$schema` presence, `metadata.description`
  vs top-level `description` placement, namespacing of top-level
  `name`, and `category` enum membership when published.
- Confirm whether bundling `marketplace.json` AND `plugin.json` in
  the same `.plugin` archive is itself a rejection signal on the
  direct-install path. Orthogonal to v0.12.3's failure; worth
  validating once the marketplace path is unblocked.

---

## v0.12.2 — 2026-04-28

**Pre-shipment quality patch.** v0.12.2 ships a new static
loader-compatibility validator and clears the only quality finding
the validator surfaced — three over-margin SKILL.md descriptions —
before pushing the v0.12.x line to a GitHub Release. No agent
contract, skill, command, or governance-field change.

### What changed

- **`scripts/loader-compat-check.py`** (new) — static loader-
  compatibility validator covering ten axes: ZIP integrity (CRC +
  truncation via `zipfile.testzip()`); file enumeration with
  zero-byte / oversize audit; manifest schema (required fields,
  semver, name shape, 300-char description budget, 12-keyword
  budget); marketplace self-reference parity (plugin.json vs
  marketplace.json version, description, source format); path-
  encoding scan (no backslashes, traversal, non-ASCII bytes,
  oversized components, reserved Windows basenames); required-files
  presence (every `skills/<name>/` has `SKILL.md`; agents and
  commands are `.md`; README and CHANGELOG at root); SKILL.md
  frontmatter validity (CRLF-tolerant; YAML parses; `name` and
  `description` populated; description ≤500 chars); no-nested-
  archives; dry-run extract + rezip-byte-count sanity; peer-plugin
  description-length distribution comparison (auto-discovers peer
  root via Cowork-session sandbox convention). Cannot exercise
  loader runtime (skill discovery, command registration, agent
  dispatch wiring). Exit codes match `release-gate.sh` convention.

- **Three SKILL.md description trims** (each preserves all
  skill-triggering keywords; only metadata bloat, internal stage
  codes, and trigger-field duplication were cut):
    * `skills/claim-coverage-audit/SKILL.md`: 534 → 472 chars (−62).
      Cut: version-stage labels (`v0.10.0-S3`, `S4 onward` — internal
      release history with no triggering value) and the duplicate
      "Manually-invokable" qualifier.
    * `skills/run-phase-2/SKILL.md`: 534 → 327 chars (−207). Cut:
      (a) the embedded `Trigger:` clause that duplicated the separate
      `trigger:` field; (b) internal stage codes (`SK-34`, `SK-35`,
      `BELOW_THRESHOLD`, `AUDIT-FAILED`, `IDEMPOTENT_HIT`) that
      belong in the body, not the description.
    * `skills/extend-snowball-incremental/SKILL.md`: 1029 → 477 chars
      (−552). Cut: verbose tri-context dispatch enumeration (already
      in `trigger:` field), procedural detail (anchor-for-
      `SCHOLAR_GATEWAY` probes, parallel-invocation caps — body
      material). Moved `snowball` earlier in the sentence to lift
      triggering precedence.

### Architectural posture and rationale

- The condition (over-margin descriptions) predates v0.12.0 and was
  present in v0.11.0 and earlier. The 500-char safety margin is
  advisory rather than loader-fatal; `release-gate.sh` Phase 0.2 has
  emitted it as a WARN across multiple releases and the harness has
  shipped anyway. Closing it now is a pre-GitHub-Release polish step,
  not a regression fix.
- The new `loader-compat-check.py` is the validator that surfaced the
  finding. It is a peer to the other `scripts/<purpose>-check.py`
  validators and uses the same argparse + exit-code convention. It is
  not yet wired into `release-gate.sh`; deferred to a future patch.

### Skills, commands, agents, governance fields

- No additions, removals, or renames. Skill count invariant holds; no
  governance-field changes; no migration script required.

---

## v0.12.1 — 2026-04-28

**Reader-accessibility calibration patch.** Two coupled additions to
the calibration substrate, derived from Sub-check H's first live
revision pass on the INF3006Y manuscript (2026-04-27). The patch
extends the Reflector's diagnostic vocabulary without altering any
agent contract, skill, command, or governance field; both surfaces
are advisory-tier and cross-reference each other.

### What changed

- **`references/DETERMINISTIC_CHECKS.md §3`** — names the
  "H-motivated em-dash insertion" false-fix pattern. When the
  Generator applies Sub-check H marker 4 (register-shift signposting),
  its default vehicle is the em-dash, which adds to the §3 count even
  when individual paragraph thresholds remain ≤1 pair. The new
  paragraph documents §3-neutral M4 alternatives (semicolon for
  contrast bridges, colon for specification pivots, explicit cue
  phrases like `consider concretely:`, `in plain terms:`,
  `to put this technically:`) and directs revision passes to flag
  any em-dash count delta as a §3 regression — the *pattern* is the
  tell. Cross-references `lay_term_lexicons.md §4` note 5,
  `sub_checks.md §H marker 4`, and MASTER §E.2 (verbatim citation
  verified against MASTER line 330).

- **`references/lay_term_lexicons.md §4`** (new) — "Verified lay-term
  paraphrase examples (INF3006, 2026-04-27)". A five-row transformation
  table from the INF3006Y survey-framing paragraph, with each entry
  carrying original formulation, accepted paraphrase, marker-gain
  attribution, and a draft-form note (the column documenting the
  Generator's typical em-dash → semicolon revision step). One
  kept-as-is exemplar shows H adjudicating CLEAN without paraphrase
  ("The underlying question… will very likely outlast it.") —
  important calibration data, since transformation corpora often
  show only the failure-to-pass arc. Five generalisation notes type
  the patterns: polemical/methodological opposition; abstract-quality
  adjective + Latinate noun; relativised relative clause; field-as-map
  metaphor; em-dash-as-draft-M4 substitution rule. The corpus is
  framed as an existence proof, not a template; closed extensibility
  is preserved (next entries gated to Reflector Phase 4 cross-project
  recurrence audit). Feeds `aggregate_h_calibration.py` training set.

### Plan amendments recorded

- Three internal-consistency edits applied during pre-commit review:
  (a) §4 generalisation note 1 example shifted from em-dash form to
  semicolon form (was contradicting note 5's substitution rule);
  (b) note 5 made flush with notes 1–4 (continuous numbered list);
  (c) §4 versioning row date and shipped-at-version corrected from
  authoring-time placeholder ("2026-04-27 (post-v0.10.2)") to ship-
  time canonical ("2026-04-28 (v0.12.1)").

### Skills, commands, agents, governance fields

- No additions, removals, or renames. Skill count invariant holds; no
  governance-field changes; no migration script required.

---

## v0.12.0 — 2026-04-28

**Reader-accessibility calibration corpus.** v0.12.0 closes the
zero-example gap in SAFEGUARD Check 8 Sub-checks A–G and the
INF3006Y-only domain-overfit risk in Sub-check H by introducing a
package-tier corpus of pre-verified model passages. The corpus draws
from two scholarly authors who write complex sociotechnical argument
in daily-English register — exactly the register the accessibility
criteria are designed to produce — providing the Evaluator with a
calibration anchor at the exact decision point of every Sub-check
adjudication.

### What changed

- **New file** `references/examples/model_prose_corpus.md`: sixteen
  verbatim passages, two per Sub-check A–H. One passage in each pair
  is drawn from Vidal 2022 (cooperative knowledge work, sociotechnical
  systems analysis), the other from Suchman 2007 (human-machine
  reconfigurations, situated action). Each passage carries marker
  audit, annotation against the relevant Sub-check criteria, and a
  contrastive calibration note distinguishing it from a borderline
  failure case. Frontmatter pins Zotero attachment keys for
  provenance: Vidal full-text `TKH5M6RK` (parent `QH8Y3FE6`); Suchman
  full-text `NT26F6GS` (parent `TJUP6UCB`).
- **`skills/accessibility-overlay/SKILL.md`** — MANDATORY corpus load
  block added (line 81), wiring the corpus into every overlay
  invocation alongside the existing `READER_ACCESSIBILITY.md`
  mandatory load.
- **`skills/accessibility-overlay/references/sub_checks.md`** — eight
  one-line cross-reference pointers added (one at the end of each
  Sub-check A–H section), surfacing the calibration anchor at the
  exact decision point.
- **`references/READER_ACCESSIBILITY.md`** — pointer paragraph added
  at the top of §13.4 worked-examples section, directing human
  protocol readers to the corpus for A–G examples.

### Architectural posture and rationale

- **Package-tier, not project-tier.** The corpus has no per-project
  override mechanism (design spec §7). Per-project override of
  reader-accessibility calibration would invite drift toward the
  same kind of governance-trailer skew v0.11.0 was structured to
  prevent.
- **Closed extensibility.** The corpus is designed to grow only via
  Reflector Phase 4 cross-project recurrence audit. Single-project
  examples must not be appended; the file's extensibility section
  documents this discipline explicitly.
- **Pre-verification.** Every passage was extracted from Zotero
  full-text during the design session and verified against the
  relevant Sub-check criteria before inclusion. They are CLEAN
  examples by construction.

### Plan amendments recorded

- The implementation followed the seven-task subagent-driven plan at
  `docs/superpowers/plans/2026-04-27-model-prose-corpus-implementation.md`
  to spec. Tasks 1–3 ran serially (scaffold → A–D content → E–H
  content); Tasks 4–6 ran in parallel (independent file edits);
  Task 7 (harness integrity verification) ran in the controller. All
  three release-gate scripts passed with zero blockers and zero
  warnings before the release ceremony.

### Deferred to v0.12.1

- Generator-side guidance against Sub-check H marker 4 ("register-shift
  signposting") defaulting to em-dash as the M4 vehicle, which inflates
  the §3 em-dash count. The Sub-check H marker discipline document and
  the lay-term lexicon §4 verified-paraphrase corpus from INF3006Y are
  staged for the next patch.

### Skills, commands, agents, governance fields

- No additions, removals, or renames. Skill count invariant holds; no
  governance-field changes; no migration script required.

---

## v0.11.0 — 2026-04-27

**Architectural cut + structural anti-drift posture.** v0.11.0 responds to
the v0.10.2 audit finding that governance-trailer drift had become the
load-bearing source of the maintainer's "does the plugin deliver what it
promised?" worry. The release deletes machinery that was not delivering,
adds structural validators that hard-fail drift recurrence, and registers
the small set of facts the plugin repeats across files in a single source
of truth.

### What changed

- **c0** — Predecessor audit + definitive architectural plan.
- **c1a / c1b / c1c** — SD/SR machinery cut. Removed across PHASE_PROTOCOL,
  AGENT_ORCHESTRATION, AGENT_CONTRACTS, agents/{evaluator,generator,planner},
  phase_notifications.yaml, pre_phase_advance_check.py, phase_state_schema,
  run-phase-1, run-phase-2, classify-manuscript, plugin-commands, and
  related minor surfaces. The v0.10.0->v0.11.0 migration helper at
  `scripts/migrate_v0100_to_v0110_drop_sd_sr.py` removes the field from
  consumers; idempotent; no rollback; advisory output only.
- **c2 / c2.5 / c2.6** — Manifest hygiene. Description rewritten as
  human-readable copy; keywords trimmed 18 -> 10 with substrate-resolution
  posture; "Ships 32 skills" assertion dropped from both manifests;
  catalog-check inverted (asserted skill count -> BLOCKER; absence ->
  healthy).
- **c3** — README repository-layout fix; skill count derived from
  filesystem at validate-time rather than asserted in prose.
- **c4** — SK-21 phantom roadmap references stripped from references/CLAUDE.md,
  PROJECT_BOOTSTRAP.md, SKILL_REGISTRY.md, graph-grounding-overlay/SKILL.md.
- **c5** — Eight superseded scripts deleted: migrate_convergence_log_v074,
  migrate_v055_to_v060, migrate_v060_to_v070, migrate_v073_to_v074_tier_to_phase,
  migrate_convergence_journal_v075, tier_state_canonicalize, tier_state_validate,
  tier_notifications_loader. Active consumers (release-gate.sh,
  phase_state_validate.py, phase_notifications_loader.py) updated.
- **c6** — Historical audit artefacts relocated to docs/historical/.
- **c7** — Version trailers stripped from 16 prose docs.
- **c8** — Validator extensions:
    * `manifest-coherence-check.py` (new) — description ≤300 chars,
      keywords ≤12, substrate-resolution, asserted-count BLOCKER,
      plugin.json / marketplace.json description parity.
    * `version-check.py` extended with version-trailer detector
      against the c7 invariant.
    * `path-hygiene-check.py` extended with README-orphan rule and
      untracked-files-in-tracked-directories rule (forensic §4 Gap 3).
- **c9** — SSOT registry. `.claude-plugin/ssot.yaml` declares
  authoritative facts (skill_count, command_count, manifest_version,
  manifest_description); `scripts/ssot-check.py` enforces fact-consumer
  parity. Both manifest descriptions registered as `skill_count`
  consumers with `method=none` — closes the forensic §2.2
  SSOT-inconsistency disposition (drop side at c2.5; enforce side at c9).
- **c10** — End-to-end ladder smoketest fixture (skeleton scope per the
  plan §3.5 4-8 hour estimate; full agent-dispatch simulation deferred
  to c10.5). `scripts/end_to_end_smoketest.py` exercises the validator
  chain plus pre_phase_advance_check.py against the fixture.
- **c11** — Operational tightening. `pre_phase_advance_check.py` clause
  (d) extended with classification.md presence check
  (E-CLASSIFICATION-MISSING-AT-T2). README Prerequisites section
  names Zotero MCP and scholarly-search MCP.

### Plan amendments recorded

- The catalog-check inversion (originally scoped at c8) was lifted
  forward to c2.6 to unblock the validator-green invariant during c1a/c1b.
  c8's remaining scope (manifest-coherence + version-trailer +
  path-hygiene rules) shipped as planned.
- c1 was decomposed into c1a + c1b + c1c. Cumulative diff matches plan
  §2.1 spec.
- The forensic §2.2 SSOT inconsistency was resolved with the combined
  disposition: drop "Ships 32 skills" from descriptions (c2.5) AND
  register descriptions as `skill_count` consumers in ssot.yaml (c9).
- The forensic §4 four validator-gap closures land at c8: asserted-count
  BLOCKER on manifest descriptions, description parity, untracked-files
  rule, README-orphan rule.

### Known follow-ups

- c10.5: tighten the end-to-end smoketest to assert exit-0 from
  pre_phase_advance_check.py against a fully-fleshed-out fixture
  (multi-section + populated reference pool + deterministic-check
  artefact + Generator revision_log row).
- TIER_PROTOCOL.md and references/tier_notifications.yaml carry the
  v0.7.4 tier-named state alongside the phase-named state. The tier->phase
  rename completed at v0.7.5 RC; these files are slated for deletion in a
  future cleanup commit but were intentionally left in place at v0.11.0
  to avoid a sprawling rename PR alongside the architectural cut.
- Substrate-doc references to the eight retired scripts (CHANGELOG,
  RELEASE_NOTES_*, PHASE_PROTOCOL.md migration semantics,
  AGENT_ORCHESTRATION.md historical pointers) were intentionally not
  swept in c5; they serve as audit-trail breadcrumbs documenting the
  historical migration paths.

---

## v0.10.2 — 2026-04-27

**Theme.** v0.10.1 deferred-items sweep with mixed substrate / forward-looking-spec strategy per user adjudication 2026-04-27 (Option A scope; single `patch/v0.10.2` branch). Closes the four items declared in v0.10.1's "Deferred to v0.10.2+" list — DETERMINISTIC_CHECKS §9e H pre-filter substrate (slot corrected from "§9b" per the v0.10.1 narrative; §9b was already taken by the v0.7.2 Reader cognitive load pre-filter); Sub-check H telemetry/aggregator + flag-retirement-decision plan doc; quantitative-thresholds plan doc; v0.10.0 pilot integration replay protocol plan doc. Plus a substantial mid-cycle policy tightening (S1.5) per user directive 2026-04-27 to refine the H lay-term policy across five tighten-points (Latinate exemption whitelist; concrete-referent operational definition; signpost orienting/contribution split with Ph2/Ph3 binding refinement; worked examples in §13.4 + new lexicon file; new fourth positive marker for register-shift signposting). Six commits on `patch/v0.10.2` off `9861762` (v0.10.1 merge tip).

### Changes

- **S1 — DETERMINISTIC_CHECKS §9e H pre-filter substrate (commit `d44cbc2`).** New §9e "Register pre-filter (added 2026-04-27, feeds SAFEGUARD_LAYER Check 8 Sub-check H)" specifying three counter probes: nominalisation density (suffix-pattern match -tion / -ment / -ance / -ence / -ity / -ness divided by passage word count, threshold 0.08, 20-term content-bearing exclusion list, -ing intentionally excluded per pilot 30% FP-inflation observation on participial constructions); prepositional-phrase run length (longest consecutive PP chain over 13-preposition cover set, threshold ≥3 per Williams *Style* §6); hedging density (15-marker built-in default, threshold >2 per 100 words; per-project override deferred to v0.10.3 per Q4 2026-04-27 adjudication). Output contract per probe: `(probe_name, raw_count, normalised_value, threshold, fired: bool)`. Reference Python at `scripts/check8_h_prefilter.py`. Overlay version 1.3 → 1.4; H step 1 reads §9e bundle and short-circuits to NULL/CLEAN when all three `fired` flags are false.

- **S1.5 — H lay-term policy tightening (commit `92ead00`).** Five refinements per user adjudication 2026-04-27. **(A) Load-bearing-Latinate whitelist**: six entries (`whereby`, `hence`, `notwithstanding`, `insofar as`, `qua`, `mutatis mutandis`) with semantic-function rationale per entry; replaces v0.10.1's vague "unless the Latinate form is genuinely more precise" exemption with a closed-by-default whitelist (closure rule: function specificity + economy + register-coherence three-part test). **(B) Concrete-referent operational definition**: three explicit classes (physical/material entity; named individual or group; specific scenario or worked vignette); defined constructs (Sub-check C terms; project-glossary entries; italicised tokens) explicitly excluded from the count to close the dilution back-door on referentially-precise-but-abstract terms. **(C) Signpost orienting/contribution clause split with Ph2/Ph3 binding**: orienting clause (where-am-I) binding at Ph2 with BLOCKER-CANDIDATE on zero positive markers; contribution clause (what-this-section-does) binding at Ph3 with technical density permitted. Detection rule via backward-reference grammatical subject for orienting; forward-reference subject + verb-of-action for contribution. **(D1) Worked examples in `READER_ACCESSIBILITY.md §13.4`** anchoring Evaluator adjudication: PASSES H (signpost orienting clause with four positive markers); FAILS H (the user's option-1 case 2026-04-27 — methods-section label dropped into narrative prose; preferred fix "*This is not a speculative argument.*" flowing into the contrastive move); EDGE CASE (referentially-precise-but-abstract paragraph that fails marker 1 under construct exclusion). **(D2) New canonical lexicon file `references/lay_term_lexicons.md`** consolidating hedge list (15 markers with class + rationale per entry; Hyland 2005 + Biber et al. 1999 source attribution), discourse-connective list (plain-English preferred + Latinate-flagged-outside-whitelist + load-bearing-Latinate whitelist), and domain-term-token exclusion list (content-bearing nominals + i\*/GORE/AORE/HCI construct families). Per-project override semantics documented; implementation deferred to v0.10.3. **(F) Register-shift signposting (added v0.10.2)** — fourth positive marker capturing user directive 2026-04-27 *"Being consistent is also important. And, a proper signpost at every tone shift."* Within-passage register shifts must be announced via signposting cue (`consider concretely:`, `in plain terms:`, `to put this technically:`); cross-passage register consistency enforced implicitly. Compliance frame raised from at-least-two-of-three to at-least-two-of-four positive markers. Overlay version 1.4 → 1.5.

- **S2 — H telemetry/aggregator + retirement-decision plan doc (commit `87ead3d`).** New `scripts/aggregate_h_calibration.py` reads `reviews/h_calibration_<cycle_id>.md` per project; computes per-cycle FPR (false_positive_count / eligible_findings, where eligible excludes inherited-from-pre-h findings per the v0.10.1 grace rule — closes R-17 in strategy doc risk register); computes cumulative-eligible aggregate FPR; emits `reviews/h_calibration_aggregate.md` with per-cycle table + cumulative metrics + retirement-criterion comparison + parse diagnostics. Per Q2 adjudication 2026-04-27, per-project only; cross-project deferred to v0.10.3. New `docs/superpowers/plans/2026-04-27-h-flag-retirement-decision.md` captures provisional retirement criterion (cycles >=2 + aggregate_fpr < 0.30 per Q1 default), 5 alternative criteria considered with trade-offs, adjudication template for the future binding decision. SAFEGUARD §H step 7 added naming the aggregator as canonical empirical-input consumer.

- **S3 — H quantitative-thresholds plan doc (part of commit `a8a53ec`).** New `docs/superpowers/plans/2026-04-27-h-quantitative-thresholds.md` enumerates candidate thresholds per marker (concrete-referent: per-50/100/150-words; agent-verb-object: 40/50/60%; discourse-connective: 3/5 per page or ratio>0.5; register-shift signposting: strict/tolerant/hybrid). FPR-vs-FNR trade-offs section anchors the 30% per-marker FPR cap as adjudication anchor. Three binding-preconditions: flag retirement closes; per-marker telemetry available; ≥3 projects observed.

- **S4 — v0.10.0 pilot integration replay protocol (part of commit `a8a53ec`).** New `docs/superpowers/plans/2026-04-27-v0.10.0-pilot-replay-protocol.md` captures the replay protocol for v0.10.0 RC carryover. Pilot manuscript candidate slot left as TBD per Q3 adjudication 2026-04-27 (named at replay-session open). Clean-room workspace setup; Ph1 → Ph2 → Ph3 ladder protocol; metric set; exit criteria; known-deferred surfaces. Replay materialises the first full H advisory cycle on a real project, feeding S2's aggregator.

### Files modified across the patch (15 total)

Spec/contract layer (4): `references/DETERMINISTIC_CHECKS.md` (new §9e); `references/READER_ACCESSIBILITY.md` (§13.3 criterion 8 + §13.4 worked examples + §13.5 Ph2/Ph3 binding); `references/SAFEGUARD_LAYER.md` (§H scope + procedure + severity floor + new step 7); `references/lay_term_lexicons.md` (new). Skill body (1): `skills/accessibility-overlay/SKILL.md` (frontmatter v1.3 → v1.5; source_tag updates; step 4 + Interaction-with-9b/9d/9e + Normative status). Skill references (1): `skills/accessibility-overlay/references/sub_checks.md` (positive markers redefinition; signpost split; new marker 4; compliance frame update; pre-filter integration paragraphs). Scripts (2): `scripts/check8_h_prefilter.py` (new); `scripts/aggregate_h_calibration.py` (new). Plan docs (4): `2026-04-27-v0.10.2-implementation-strategy.md` (new + slot correction commit); `2026-04-27-h-flag-retirement-decision.md` (new); `2026-04-27-h-quantitative-thresholds.md` (new); `2026-04-27-v0.10.0-pilot-replay-protocol.md` (new). RC ceremony surfaces (4): `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md`, `CHANGELOG.md`. Release notes (1): `docs/release-notes/RELEASE_NOTES_v0.10.2.md` (new).

### Deferred to v0.10.3+

- Per-project hedge / connective / Latinate-whitelist override mechanism (per Q4 2026-04-27 adjudication; built-in defaults ship at v0.10.2 with `references/lay_term_lexicons.md` as override target).
- Per-marker FPR telemetry extension (precondition for adopting quantitative thresholds beyond qualitative judgment).
- Cross-project FPR roll-up in `aggregate_h_calibration.py` (per Q2 2026-04-27 adjudication; per-project only at v0.10.2 ship).
- Pilot integration replay execution itself (v0.10.2 ships the protocol; the run is a separate session).
- Sub-check H `advisory_until` flag retirement adjudication (gated on `aggregate.md` showing both criteria met on at least one project).
- Quantitative thresholds adoption (gated on flag retirement + per-marker telemetry).

### Process notes

The §9b → §9e slot correction (commit `f9dc2ee`) caught a v0.10.1 narrative artefact: RELEASE_NOTES_v0.10.1.md and the Sub-check H amendment plan doc both referenced "§9b" for the H pre-filter, but §9b was already occupied by the Reader cognitive load pre-filter (added v0.7.2). The correction landed before any §9b-named substrate was written. Future cross-spec slot allocations should grep DETERMINISTIC_CHECKS.md for the candidate slot label before naming a new pre-filter section.

The S1.5 lay-term policy tightening was triggered mid-stream by a user directive between S1 close and S2 open, demonstrating the patch-level sub-staging precedent from v0.10.0 S1.5 (also a hardening pass). The user-supplied option-1 example ("*This is not a speculative argument.*") became the centerpiece §13.4 worked example; the user's two-principle distillation ("Being consistent is also important. And, a proper signpost at every tone shift.") became the rationale for the new fourth positive marker. The user-directive-to-spec pattern reflects the harness's intended collaboration model — the user's worked-prose intuitions inform spec refinements without being themselves committed as plan-doc text.

The four Open Questions (Q1 §9e thresholds; Q2 aggregator output format; Q3 pilot manuscript candidate; Q4 hedge override) all adjudicated to the Recommended defaults per the v0.10.2 strategy doc §8 surface. The plan-doc pattern (PROPOSAL → user adjudicates §8 → ADOPTED implicit on substrate-commit) carries v0.10.0's precedent forward.

---

## v0.10.1 — 2026-04-27

**Theme.** Hardening patch closing the two work items declared in v0.10.0's "Deferred to v0.10.1+" list: architecture- and strategy-doc mirrors for the four S4 binding decisions anchored at `agents/planner.md §Phase 3.8`; and the accessibility Sub-check H (Register Appropriateness) amendment per `docs/superpowers/plans/2026-04-27-accessibility-subcheck-h-amendment.md`. Plus two `marketplace.json` hot-fixes — the v0.10.0 RC version-skew that was rejecting the `.plugin` loader install (commit `103faf4`), and a post-RC-tag source-format slip that the marketplace loader's schema rejected as `Invalid input` (commit `7a53c02`). The v0.10.1 annotated tag was re-anchored twice within ~30 min of original creation to capture the second hot-fix and this doc backfill, on the consumer-count criterion (zero consumers existed at re-anchor time).

### Changes

- **Hot-fix #1 — version skew (commit `103faf4`).** `.claude-plugin/marketplace.json` plugin-entry version was `0.9.0` while `plugin.json` had been bumped to `0.10.0` at the v0.10.0 RC gate; the `.plugin` ZIP route carries both files, so the loader rejected the install on the disagreement (user-reported symptom). The marketplace.json plugin-entry version is now synced to plugin.json. `scripts/version-check.py` extended with `extract_marketplace_self_referencing_versions` — reads marketplace.json, identifies plugins[] entries whose `source` resolves to plugin_root, and emits BLOCKER for any version disagreement with plugin.json. The check absent-marketplace.json is silent; present-but-no-self-referencing entries is silent; mismatch hard-gates the gate. Closes the RC-gate gap that let this slip ship and prevents recurrence.

- **Hot-fix #2 — source-format slip (commit `7a53c02`, post-RC-tag).** Within ~10 min of v0.10.1's original tag creation, the user attempted `/plugin marketplace add B:\Agents\co-author-harness` and the loader rejected with `Failed to parse marketplace file ... plugins.0.source: Invalid input`. The `marketplace.json` had shipped with `"source": "."` since v0.10.0; the v0.10.1 version-skew hot-fix touched the version field but not the source field, so the format slip survived the RC gate intact. Empirical schema check against two working `marketplace.json` examples (the workspace's parent marketplace and `everything-claude-code/.claude-plugin/marketplace.json`) showed both use the leading-prefix form (`"./"`). Fix: `marketplace.json` `"source": "."` → `"source": "./"` (one character; relative path now valid against the marketplace loader schema; resolves to plugin_root via the `.claude-plugin/` parent traversal). `scripts/version-check.py` `extract_marketplace_self_referencing_versions` now flags bare `"."` and `".."` as `<INVALID_SOURCE_FORMAT>` with a guidance message naming the loader's accepted form (`"./"` or `"../"`); the check fires as BLOCKER via the version-mismatch comparison in `main()` when the placeholder value is recorded. Both classes of marketplace.json slip (version skew + source format) now hard-gate at the validator. Tag `v0.10.1` re-anchored to this commit on the consumer-count criterion (no consumers had fetched the original tag).

- **Arch/strategy doc mirrors for the four S4 binding decisions (commit `f614b34`).** The four binding decisions originated during S4 implementation but had RC-scope deferral on the architecture/strategy mirrors. agents/planner.md §Phase 3.8 has carried the authoritative spec since S4; v0.10.1 amendments add cross-reference paragraphs to the architecture doc (`docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md`) and the strategy doc (`docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md`) without duplicating the contract (single-source-of-truth per architecture §6.0 row 4). Architecture amendments: §5.2 Edit-2 enumerates four outcome classes (CLEAN / BELOW_THRESHOLD / AUDIT_FAILED / IDEMPOTENT_HIT) — IDEMPOTENT_HIT was missing entirely from the architecture doc and its asymmetric notification treatment vs. AUDIT_FAILED is the load-bearing rationale for four outcomes rather than three; §6.0 closing paragraph names the Phase 3.7 (HALT — substrate failure) vs Phase 3.8 (CONTINUE — advisory failure) asymmetry as the canonical example of row-4 partial-failure halt-vs-continue semantics; §7 Risk Register adds R-14 (outcome (ii) BELOW_THRESHOLD on a long-tail uncovered list could blow the verifier budget unboundedly; mitigation `max_parallel_extend_snowball` cap of 8 with Rule-7a-criticality ranking and `W-COVERAGE-FANOUT-CAPPED` deferral). Strategy amendments: §5.5 Stage S4 carries a binding-decisions enumeration with each decision's architecture mirror point named; §5.6 Stage S4.5 carries an S4-carry-overs paragraph naming the two parameters that materialise S4 binding decisions (b) and (c). Terminology corrections vs. handoff: decision (a) is anchored as "four-outcome handler for `claim-coverage-audit`" (not extend-snowball-incremental); decision (d) is anchored as the Phase 3.7-vs-3.8 substrate-vs-advisory asymmetry (not generic "partial snowball failures"). The §6.0 closing paragraph adds a meta-rule for future contributors so the SOT pattern is self-propagating.

- **Sub-check H — Register Appropriateness (commits `0c408dc` + `2d5ea2e` + `edfe0a9`).** SAFEGUARD Check 8 expands from seven Sub-checks (A–G) to eight (A–H). The new Sub-check H operationalises the user's daily-language directive at two scopes: a passage-scoped variant audits register quality within the five non-technical passage roles already named by D, F, G plus section framing and inter-section transitions (functional removability test gates eligibility — "removing every domain-term token and substituting plain-language glosses preserves propositional content"); a manuscript-scoped variant under the new `register_class: technical | mixed | non-technical` field in `research_notes/directives.md` extends scope to abstract / introduction / conclusion (mixed) or manuscript-wide (non-technical). Three positive markers (concrete-referent anchoring, agent-verb-object default, plain-English connectives) and three negative markers (unnecessary nominalisation, stacked prepositional phrases, hedging pile-up) are tracked under a **presence-of-positive-markers** compliance frame — a deliberate inversion of absence-of-negative-markers grammar that closes the dilution back-door (a passage with one negative marker but two positive markers is CLEAN; the rule rewards register craft rather than punishing register lapses). Severity floors: MINOR / MAJOR / BLOCKER mirroring A–G grammar; BLOCKER reserved for `register_class: non-technical` manuscript-wide variant when >50% of non-technical passages emit MAJOR. H ships under `advisory_until: H_two_revision_cycles` (cycle-counting via `h_advisory_cycles_observed` in `reviews/classification.md`, distinct from G's manuscript-scoped `next_manuscript_at_ph3` flag) — H findings are recorded but do not contribute to the §3.3.3 TerminalSignoffRow gate aggregate until two revision cycles clear. Per-finding `false_positive_candidate: true|false` telemetry feeds `reviews/h_calibration_<cycle_id>.md` for the v0.10.2 retirement adjudication. Back-compat grace period: first H run on a previously-non-H manuscript runs MINOR-only for one iteration. Stability sub-mode: H runs advisory-only mirroring G's stability-sub-mode treatment. **Recommended path** per the plan doc (overlay-internal, not a sibling skill, no SKILL_REGISTRY entry) — skill count invariant 32 holds. **All five plan-doc Open Questions adjudicated to plan-doc Default proposed answers** (functional removability test scope mirrors C's construct definition; positive-marker thresholds qualitative for advisory period; register_class:mixed extends to four-section list; false_positive_candidate telemetry yes; back-compat grace period yes).

- **Plan doc adoption.** `docs/superpowers/plans/2026-04-27-accessibility-subcheck-h-amendment.md` Status: PROPOSAL → ADOPTED (implicit — v0.10.1 implementation lands the spec). The plan doc remains in tree as the historical record of the advisor consultation and the dual-scope authoring decision; future v0.10.2 retirement adjudication consumes the plan doc's §10 Open Questions table to validate the empirical false-positive rate against the (provisional) 30% retirement criterion.

- **Files modified across the patch (12 total).** Spec/contract layer (2): `skills/accessibility-overlay/references/sub_checks.md`, `references/READER_ACCESSIBILITY.md`. Skill body + protocol layer (3): `skills/accessibility-overlay/SKILL.md` (frontmatter version 1.2 → 1.3), `references/SAFEGUARD_LAYER.md`, `references/PHASE_PROTOCOL.md` (§3.3.3 only). Phase wiring (3): `skills/run-phase-3/SKILL.md`, `agents/evaluator.md` (§Step 8.5 only), `references/PROJECT_BOOTSTRAP.md` (§2.8 directives template only). Arch/strategy mirrors (2): `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md`, `docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md`. RC ceremony surfaces (4): `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md`, `CHANGELOG.md`. Hot-fix (1): `scripts/version-check.py`.

### Deferred to v0.10.2+

- `references/DETERMINISTIC_CHECKS.md §9b` H pre-filter (cheap counter probes for nominalisation, prepositional-phrase stacking, hedging) — deferred per plan doc "not required for v1" guidance. Optional optimisation; H currently runs without a pre-filter feed (slower path, same findings).
- Sub-check H `advisory_until: H_two_revision_cycles` flag retirement decision — scheduled for v0.10.2 (or v0.11.0 if the calibration log shows persistent false positives requiring threshold tightening before retirement). Retirement criterion provisionally set at false-positive rate <30% across two revision cycles, anchored at the plan doc's §10.4 Default proposed answer.
- Quantitative thresholds for H positive markers (e.g., "≥1 concrete noun per 100 words"; "≥60% agent-subject sentences") — deferred to post-flag-retirement based on observed false-positive patterns per plan doc §10.2 Default proposed answer.

### Process notes

The four S4 binding decisions had been correctly anchored at `agents/planner.md §Phase 3.8` during S4 implementation, but the architecture- and strategy-doc mirrors were deferred to RC-scope and then deferred again to v0.10.1 — the structural-clean precedent set by §6.0 for handling SOT-vs-mirror divergence. v0.10.1's mirror-only amendments (no contract changes) preserved the SOT discipline cleanly. The audit at v0.10.1 open identified two terminology slips in the handoff doc's enumeration of the four decisions; both were corrected at the source rather than propagated into the doc-mirror prose.

The v0.10.0 RC marketplace.json version-skew (declared `0.9.0` while plugin.json shipped `0.10.0`) was a `version-check.py` scope gap, not a typo — the validator did not read marketplace.json plugin-entry versions during v0.10.0 RC. v0.10.1 closes the gap at the validator level so future RC gates hard-fail on the same class of skew.

The v0.10.1 source-format slip (`"source": "."` rejected by the marketplace loader as `Invalid input`) was a sibling failure mode in the same file: data that the harness considered valid (the §2.1a check accepted `"."` as a self-referencing source for version-resolution purposes) but that the loader's schema rejected at install time. The lesson generalises — validator coverage of a JSON file should not assume that "syntactically permissible" maps to "schema-accepted by the consumer." v0.10.1's second hot-fix tightens the validator to mirror the loader's strictness on the `source` field specifically; future contracts where harness validators speak about consumer-bound JSON should similarly track consumer schema rather than just structural correctness. The two slips together also demonstrate that RC-tag immutability is contingent on consumer existence — re-anchoring a tag with zero consumers is reversible at zero cost; re-anchoring once consumers exist would not be.

The Sub-check H amendment is the second package-tier extension of SAFEGUARD Check 8 since v0.7.2 introduction (after v0.8.1's Sub-check G addition for the cumulative scale). The three-scale architecture (local A–F + cumulative G + register H) is now stable; further sub-check additions would need cross-scale justification.

---

## v0.10.0 — 2026-04-27

**Theme.** Snowball-driven reference scaffolding for Phase 1 / Phase 2 of the Lifecycle-Phase Ladder; materialises Coupling E.1 (`graph-read-at-planner`) via SK-NEW-A's graph-substrate iteration. Eight-stage rollout per `docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md`.

### Changes

- **S1 (closed 2026-04-26).** SK-NEW-A `seed-snowball-discovery` skill (SK-33) shipped manually-invokable. New files: `skills/seed-snowball-discovery/SKILL.md` (246 lines), `commands/seed-snowball-discovery.md`. Edited: `references/SKILL_REGISTRY.md` (SK-33 entry), `skills/plugin-commands/SKILL.md` (catalog row), `README.md` (skill count 28 → 29), `.plugin-efficiency.json` (executor registration; cost rebase to $6.0793 — 100% feature-attributed; zero bloat). Calibrator economics gate green. The S1 SKILL.md body absorbed the architecture's §5.5.1, §5.5.2, and §5.5.6 content that the strategy doc §5.2 had nominally allocated to S1.5 — this is documented as a strategy-doc deviation in `docs/release-notes/RELEASE_NOTES_v0.10.0.md §2.S1` and reconciled at S1.5.
- **S1.5 (closed 2026-04-26).** Hardening pass over S1's absorbed content. Eighteen-row audit table mapping every architecture sub-clause in §5.5.1/§5.5.2/§5.5.6 to its SKILL.md realisation (17 covered, 1 partial gap fixed in S1.5). Gap-fix: `skills/seed-snowball-discovery/SKILL.md` §3 Phase 2 — new `**Lookup keying.**` paragraph specifying the `source_file` primary / `(author, year)` secondary resolution contract for `lookup_node_by_doi_or_pdf_path`. Scenario fixtures: `scripts/fixtures/snowball_graph_substrate_smoketest/{basic_graph_traversal,ambiguous_edge_no_admit,dual_path_access_modes}/` — three reference scenarios documenting expected SK-NEW-A behaviour in human-readable form, with mock graph.json and seed_set.json inputs. Python validator deferred to a future hardening pass when SK-NEW-C's S4 ship justifies the second consumer of the same iteration logic. Side-effect fix: `scripts/version-check.py` patched to skip `(unreleased)` headings per strategy §8.2 + §8.4 (otherwise every v0.10.0 stage close would surface a spurious BLOCKER). Calibrator baseline target: maintain S1's $6.0793 per `.plugin-efficiency.json`. See `docs/release-notes/RELEASE_NOTES_v0.10.0.md §2.S1.5`.
- **S3 (closed 2026-04-27).** SK-NEW-B `claim-coverage-audit` skill (SK-34) shipped manually-invokable. New files: `skills/claim-coverage-audit/SKILL.md` (~3933 tokens; manuscript + REFERENCES.md → three-set coverage map (covered / partially-covered / uncovered) + score = covered/total at `reviews/claim_coverage_<date>_<cycle_id>.md`; deterministic claim extraction with five-kind taxonomy from architecture §4.1; conservative source-mapping via three categories (explicit citation, anchored metadata, lexical-match similarity ≥0.6); advisory not gating); `commands/claim-coverage-audit.md` shim. Edited: `references/SKILL_REGISTRY.md` (SK-34 entry between SK-33 and the Orchestration Commands divider); `skills/plugin-commands/SKILL.md` (new routing-table row + catalog-table row, both inserted adjacent to `/seed-snowball-discovery`); `README.md` (skill count 29 → 30; new skill named in the headline list); `.plugin-efficiency.json` (`claim-coverage-audit` registered as executor per architecture §5.1; first-pass cost reading 6.4428 USD with default orchestrator classification, dropped to **6.323805 USD** (+3.02% vs S2's 6.13842 baseline) after the role_override; subagent_dispatch_multiplier dropped from 9.739 to 9.604 — the expected pattern for a manually-invokable skill that does not pull through the auto-dispatch graph). Five-script gate green: zero blocker, zero major, three minor (all known-FP carry-overs from S2: cyclomatic 39, chain depth 22, parallelisable 0.073). Semantic-review not invoked (advisory at S3 per strategy §5.4). Pilot validation (hand-curated coverage maps for two sections within ±5pp) deferred to user-side use of the skill on a real project. Plan-doc-only side deliverable also landed: `docs/superpowers/plans/2026-04-27-accessibility-subcheck-h-amendment.md` capturing an Opus 4.6 advisor-consultation output proposing a new accessibility Sub-check H ("Register Appropriateness") with dual scope (within-manuscript non-technical passages + audience-conditioned `register_class` field); orthogonal to v0.10.0 snowball rollout, suggested staging is v0.10.1 patch. See `docs/release-notes/RELEASE_NOTES_v0.10.0.md §2.S3`.
- **S2 (closed 2026-04-27).** Phase-1 wiring + four orchestration co-mutations + architecture-doc amendment. **Originally three-deliverable scope (Step 4.5 + schema + migration); actual close required seven deliverables across five semantic-review rounds, surfacing an under-specification in the architecture doc itself.** Document-layer (Sub-A/B/C round 1): `skills/run-phase-1/SKILL.md` Step 4.5 dispatch insertion with OR-conjunctive outer guard per architecture §5.2 Edit-1 spec; `references/phase_state_schema.md` schema bump (16 → 17 fields with `references_initialized`; trigger-enum 30 → 31 with `seed_snowball_signed`; new `SECTION_BAD_REFERENCES_INITIALIZED_TYPE` finding code); `scripts/migrate_v090_to_v100_snowball_fields.py` body authoring (S0 237-line skeleton → 938-line implementation; 9 smoketest fixtures populated under `scripts/fixtures/phase_state_smoketest/v090_to_v100/`; `--validate` exit 0). Orchestration co-mutations (Sub-D/E/F round 2 + advisor-recommended Path C round 3): `agents/planner.md` new Phase 3.7 (canonical Planner-side contract for SK-NEW-A dispatch; placed between Phase 3.5 and Phase 4 to mirror run-phase-1 Step 4.5's pre-revision-plan placement); `references/phase_notifications.yaml` declares `W-SNOWBALL-PRECONDITION-UNMET` and `E-SNOWBALL-MID-RUN-FAILURE`; `scripts/pre_phase_advance_check.py` extends `VALID_TRIGGERS` with `seed_snowball_signed` and adds `references_initialized_advisory()` function wired into `main()` (non-blocking stderr emission); `skills/run-phase-2/SKILL.md` Step 0.5 placeholder re-tests the gate at Ph2 entry (full Ph2-side dispatch defers to S3/S4 per strategy §5.4/§5.5). Architecture amendment (advisor-recommended Path C, Opus 4.7 consultation at round-2 inflection): new **§6.0 Coupling Checklist for Phase-Runner Step Edits** (4-row table; applies to S2/S4/S4.5 and any post-v0.10.0 stage editing a phase-runner); §6.3 enumerated to seven deliverables; §5.2 Edit-1 corrected (`classification.md` → `phase_state.json` field placement; `W-CORPUS-BOOTSTRAP-DEFERRED` → `W-SNOWBALL-PRECONDITION-UNMET` operational name; explicit halt-on-partial-failure). Strategy §5.3 mirrored. Calibrator: pass; cost rebase to $6.13842 (+0.83% vs S1.5 baseline; +1.77% multiplier over v0.9.0 ceiling, accepted per noise-tolerance precedent); chain depth dropped 23 → 19 across the rounds as cross-references compressed the graph. Semantic-review verdict CLEAR after 5 rounds. See `docs/release-notes/RELEASE_NOTES_v0.10.0.md §2.S2`.
- **S4 (closed 2026-04-26).** Phase-2 wiring + SK-NEW-C `extend-snowball-incremental` (SK-35; ~5300 tokens; Phase 1 anchor selection / Phase 2 micro-iteration / Phase 2.5 direct-claim probe / Phase 3 atomic-write to REFERENCES.md snowball table) + four orchestration co-mutations. New: `skills/extend-snowball-incremental/SKILL.md`; `commands/extend-snowball-incremental.md` shim; `references/SKILL_REGISTRY.md` SK-35 row. Edited: `skills/run-phase-2/SKILL.md` Step 0.5 placeholder → full body with **four-outcome handler** (CLEAN / BELOW_THRESHOLD with auto SK-NEW-C / AUDIT-FAILED non-blocking-CONTINUES / IDEMPOTENT_HIT clean-exit-equivalent); `references/phase_state_schema.md` schema bump 17 → 18 (new `last_coverage_score: float | null` plus `SECTION_BAD_LAST_COVERAGE_SCORE_TYPE` MINOR finding code); `agents/planner.md` new Phase 3.8 (canonical Planner-side contract for the SK-NEW-B → SK-NEW-C chain); `references/phase_notifications.yaml` declares `W-COVERAGE-BELOW-THRESHOLD` and `E-COVERAGE-AUDIT-FAILED` (round-2 amended `E-COVERAGE-AUDIT-FAILED` template to exclude `IDEMPOTENT_HIT` from failure reason-code enumeration); `README.md` skill count 30 → 31; `skills/plugin-commands/SKILL.md` routing + catalog rows. Round-2 fix surgically addressed all four binding semantic-review MAJORs from round 1: explicit fourth IDEMPOTENT_HIT outcome (resolves four-way confusion across planner.md / phase_notifications.yaml / SK-34 §2); inline parallel SK-NEW-C dispatch fanout cap of 8 with Rule-7a-criticality ranking + `W-COVERAGE-FANOUT-CAPPED` deferral path; coverage regression hook explicitly framed as "S4.5-deferred consumer" with "written but not yet consulted" framing; halt-vs-continue asymmetry rationale (Phase 3.7 outcome (iii) HALTS Ph1; Phase 3.8 outcome (iii) CONTINUES Ph2 — anchored at planner.md, not in consumed SKILL.md). Calibrator pass; cost rebase $6.323805 → **$6.754935** (+6.81% feature-attributed; SK-35 IS on the auto-dispatch graph unlike S3's manually-invokable SK-34). Semantic-review binding (per strategy §4.4): closed in **2 rounds** (target hit; matches §6.0 pre-flight prediction). Promise-reviewer flagged `CHANGELOG.md` + `RELEASE_NOTES_v0.10.0.md §2.S4` as MINOR-deferred-expected at S4 tip — landed at S4.5 R2 catch-up. **Latent gap surfaced at S4.5 R1 grep:** `W-COVERAGE-FANOUT-CAPPED` referenced in `agents/planner.md §Phase 3.8` since S4 round-2 but never declared in `phase_notifications.yaml`; declared at S4.5 R2 (latent-gap catch-up below). See `docs/release-notes/RELEASE_NOTES_v0.10.0.md §2.S4`.
- **S4.5 (closed 2026-04-27).** Two-round close: R1 ships primary deliverables; R2 ships S4 carry-overs + a S4 latent-gap catch-up. **R1 (commit `91f4784`):** `skills/claim-coverage-audit/SKILL.md` new Phase 2.5 synthesis-alignment fast-path (architecture §5.5.3) — four-set output (covered / synthesis-covered / partially-covered / uncovered); score formula `(covered + synthesis-covered) / total` with subscores reported separately; idempotency cache extended with `wiki/syntheses/` content hash; thresholds 0.6 cosine (mcp_fastpath) / 0.3 Jaccard (filesystem) per architecture §5.5.6 `wiki_access_mode` conditioning; backward-compatible — silently no-ops without `wiki/syntheses/`. `skills/retrofit-concept-grounding/SKILL.md` new Phase 4.5 red-link auto-trigger (architecture §5.5.4) — gated on `auto_redlink_snowball + wiki_linked` (default off); capped at `red_link_cap_per_round` (default 5; document-order selection); per-dispatch failure: skip-and-continue (FM-1 in new §Failure modes section with FM-1..FM-6); cap saturation emits `W-REDLINK-CAP-SATURATED` + logs deferred candidates; SK-NEW-C registered as downstream. `references/phase_notifications.yaml` declares `W-REDLINK-CAP-SATURATED` block (non-blocking; mirrors `W-SNOWBALL-PRECONDITION-UNMET` per R-12 mitigation). `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md` §6.0 closing-sentence revised (S4.5 moved to exempt list with empirical-staleness rationale; pre-flight verified rows 1/3 EXEMPT, rows 2/4 NOT-EXEMPT but resolved by baseline contracts not §6.0 coupling — user decisions: `W-REDLINK-CAP-SATURATED` user-visible at cap; skip-and-continue formal partial-failure contract); §6.6 round-split paragraphs. R1 validation gate (4 scripts, all PASS): 31 skills, 15 commands, 0 blockers throughout. **R2:** `scripts/migrate_v090_to_v100_snowball_fields.py` extends `CLASSIFICATION_DEFAULTS` with 4 new entries + new `S4_5_CLASSIFICATION_FIELDS` tuple appending 6 fields at R2 migration (`coverage_regression_floor` 0.05; `max_parallel_extend_snowball` 8; `synthesis_alignment_threshold_cosine` 0.6; `synthesis_alignment_threshold_jaccard` 0.3; `auto_redlink_snowball` false; `red_link_cap_per_round` 5; synthesis thresholds use Option-B flat-scalar shape per the R2 entry decision). 5 pass-case fixtures' `expected/reviews/classification.md` updated with the 6 new fields appended after `claim_coverage_threshold`; `idempotent-rerun/reviews/classification.md` input also updated to reflect post-R2 v0.10.0 state. Migration `--validate` PASS (9/9 fixtures). `agents/planner.md §Phase 3.8` — cross-round regression-detection consumer wiring landed (delivers the S4 round-2 fix's "S4.5-deferred consumer" promise; read-prior-score / read-floor / compare / write-new-score procedure); non-gating; skipped on outcomes (iii)/(iv); single-source-of-truth contract anchored here; `max_parallel_extend_snowball` cap source updated from "inline at S4" to "sourced from classification.md" with default-fallback discipline. `references/phase_notifications.yaml` declares two new W-* codes: `W-COVERAGE-REGRESSION-OBSERVED` (S4.5 R2 — emitted by Planner Phase 3.8 cross-round regression check; non-blocking) and `W-COVERAGE-FANOUT-CAPPED` (S4 latent-gap catch-up — referenced in planner.md §Phase 3.8 since S4 round-2 but never previously declared; non-blocking). `CHANGELOG.md` + `RELEASE_NOTES_v0.10.0.md §§2.S4, 2.S4.5` filled (this entry; promise-reviewer flagged S4 catch-up as MINOR-deferred-expected at S4 close — landed here as planned). Semantic-review advisory at S4.5 (per strategy §4.4); not invoked at R1 or R2. Calibrator binding at S4.5 final-close ceremony; pending at R2 final-commit. See `docs/release-notes/RELEASE_NOTES_v0.10.0.md §2.S4.5`.

- **S5 (closed 2026-04-27).** Documentation-only stage. Three reference files amended (binding semantic-review per strategy §4.4; 2 MAJORs fixed before close; 4 files changed, 35 ins / 11 del): `references/EXTERNAL_VERIFIERS.md §1.5` — Skill-executors paragraph naming SK-33 (Ph1) and SK-35 (Ph2) as wiki-first ladder executors; `references/AGENT_ORCHESTRATION.md §8.6` — restructured to dual-coupling section E.1/E.2; Coupling E.1 registered under SK-33 / `graph-read-at-planner` identifier; SK-20 `graphify-project` SKILL.md updated to name SK-33 as planned successor; `references/SKILL_REGISTRY.md` — SK-NEW-A/B/C/D placeholders resolved to SK-33/34/35/36; SK-36 added as forward-reference stub (Active at S6). See `docs/release-notes/RELEASE_NOTES_v0.10.0.md §2.S5`.
- **S6 (closed 2026-04-27).** SK-NEW-D `inherit-snowball-from-wiki` (SK-36) shipped + SK-33 Phase 0 pre-seed wiring + migration S6 activation. New files: `skills/inherit-snowball-from-wiki/SKILL.md` (SK-36; Ph1 pre-seed via cross-project community-adjacency traversal; Conditions A/B resolution chain; `pre_seed_cap` default 10; no-op reason codes `NOT_WIKI_LINKED`, `INHERIT_SNOWBALL_DISABLED`, `PRE_SEED_CAP_ZERO`, etc.; emits `reviews/pre_seed.json`); `commands/inherit-snowball-from-wiki.md` UI shim. Edited: `skills/seed-snowball-discovery/SKILL.md` (Phase 0 pre-seed block auto-invoking SK-36; Phase 4 Core corpus provenance clause for `[pre-seed: wiki-community-<id>]`; SK-NEW-x → SK-33/34/35/36 across 11 occurrences); `scripts/migrate_v090_to_v100_snowball_fields.py` (S6 activation: `S6_CLASSIFICATION_FIELDS = ("inherit_snowball", "pre_seed_cap")`; `inherit_snowball` default conditional on `wiki_linked`); 6 fixture expected files updated; `references/SKILL_REGISTRY.md` SK-36 Active (v0.10.0+); `references/AGENT_ORCHESTRATION.md §8.6` §6.0-exemption note + stale staging hedge removed; `skills/plugin-commands/SKILL.md` catalog row + dispatch row; `README.md` skill count 31 → 32. Semantic review: 5 MAJORs fixed before close. Validation: 0 blockers / 0 warnings all 4 scripts; 32 skills; skill count 32. **§6.0 coupling-checklist EXEMPT at S6** — Phase 0 is intra-SK-33 and does not alter any Step number in a phase-runner. 14 files changed, 338 ins / 51 del. See `docs/release-notes/RELEASE_NOTES_v0.10.0.md §2.S6`.

### Deferred to v0.10.1+

- Architecture- and strategy-doc amendments mirroring the four S4 binding decisions anchored at `agents/planner.md §Phase 3.8` (four-outcome handler / inline parallel cap of 8 / S4.5-delivered regression hook / halt-vs-continue asymmetry rationale). Planned as v0.10.1 hardening patch.
- Plan-doc accessibility Sub-check H amendment (`docs/superpowers/plans/2026-04-27-accessibility-subcheck-h-amendment.md`) scheduled for v0.10.1 patch after v0.10.0 RC.

### Process notes

A merge anomaly at S1 close (`6ad499d` landed an empty tree where `--no-ff` of `f9411d5` was intended) was recovered via cherry-pick (`5fbc0c7`); the `v0.10.0-S1` annotated tag was force-moved from a pre-S1 location (`dcb6e2e`) to the recovery commit. Both events are preserved in git history rather than rewritten — future archaeology has the full incident trace via the merge commit message and the cherry-pick commit message. Strategy §6.3's deferred-merge fallback was considered and rejected once the recovery completed.

---

## v0.9.0 — 2026-04-26

**Theme.** UI loadability via `.claude-plugin/plugin.json` + `commands/` shim convention; model allocation calibrator pin restored to `references/MODEL_ALLOCATION.md §2`.

### Changes

- **UI loadability** — twelve `commands/<name>.md` shim files for the headline-cut slash commands (six phase-ladder rungs + `/run-generator-session`, `/classify-manuscript`, `/plugin-commands`, `/run-reflection`, `/quick-deterministic`, `/check-contradictions`, `/grounding-audit`). Each shim delegates to its sibling `skills/<name>/SKILL.md` as the binding authority; the SKILL remains the single source of truth.
- **Manifest** — `.claude-plugin/plugin.json` `description` rewritten to point at `/plugin-commands` for the full slash catalog rather than privilege a single slash by name; `version` 0.8.7 → 0.9.0.
- **Root `CLAUDE.md`** — trigger table line 40 flagged "illustrative — full catalog at `/plugin-commands`"; missing v0.8.7 headline `/run-generator-session` added.
- **Catalog parity** — `scripts/catalog-check.py` extended with `parse_plugin_commands_purposes`, `discover_commands`, `check_commands_parity`, and a Unicode-quote normalization helper. The new rule asserts every `commands/<name>.md` frontmatter description is a prefix of the matching catalog Purpose column (markdown bold, inline-code backticks, and curly quotes normalized before comparison).
- **Calibrator pin restored** — `.plugin-efficiency.json` `role_overrides` reconciled to `MODEL_ALLOCATION.md §2`. Seven artefacts downshifted from `orchestrator` to `executor` (`agents/planner.md`, `agents/generator.md`, `skills/run-phase-1/SKILL.md`, `skills/run-reflection/SKILL.md`, `skills/classify-manuscript/SKILL.md`, `skills/advisor-escalation/SKILL.md`, `skills/tool-contract-roundtrip/SKILL.md`); one added (`skills/run-generator-session/SKILL.md` as `executor`); `assumed_invocations_per_run` retuned to `{executor: 5, orchestrator: 2}`. Net orchestrator pool 14 → 7. Bookkeeping correction only — no agent dispatch behavior changes; the Planner resolves runtime dispatch from `MODEL_ALLOCATION.md §2`, not from this file.
- **Release notes** — `docs/release-notes/RELEASE_NOTES_v0.9.0.md`.

### Not changed

- No `phase_state.json` schema or trigger-enum change.
- No `MODEL_ALLOCATION.md` edit (the audit *restores* the existing pin).
- No agent prompt change.

### Open items for next audit

- Empirical calibrator economics re-run on the patched Windows-side `plugin_calibrator/efficiency.py` to confirm the projected cost-per-invocation drop (estimated $10.03 → $5.50–$7.00). Decision 4-α: shipping is justified by bookkeeping correctness; cost reduction is downstream.
- F4 (`agents/reflector.md`) and F8 (`skills/run-phase-3-stability/SKILL.md`) conservative-keeps are revisitable if the calibrator schema later supports a tri-tier `{Haiku 4.5} ≺ {Sonnet 4.6} ≺ {Opus 4.7}` representation.

---

## v0.8.7 — 2026-04-25

**Theme.** Session-sourced Generator skill and catalog wiring.

### Changes

- **New skill** — `run-generator-session` (`/run-generator-session`): apply chat-originated revision instructions under real `phase_state` + `classification` per approved design `docs/superpowers/specs/2026-04-25-generator-session-revision-design.md`.
- **Registry** — `SKILL_REGISTRY` SK-32; `plugin-commands` routing + catalog.
- **Release** — `build-release-zip.sh` + `releases/co-author-harness-claude-v0.8.7.zip`.

### Not changed

- No `phase_state.json` schema or trigger-enum change.

---

## v0.8.6 — 2026-04-25

**Theme.** Advisor MCP entry points, em-dash control on **fix** rounds, release-gate chain-depth without external calibrator, packaging polish.

### Changes

- **Advisor MCP** — `references/ADVISOR_MCP.md`, `PHASE_PROTOCOL.md` cross-ref, `advisor-escalation` / `plugin-commands` / `SKILL_REGISTRY` (EP-1 post-Ph2 pre-Ph3, EP-2 pre-MCR/Ph4).
- **Generator** — `agents/generator.md`: em-dash discipline on **fix application**; `MASTER_research_and_paper_guidelines.md` §E.2, `research_paper_writing_guidelines.md` §7, `sentence-level-pass` (v1.1) mechanical scan.
- **Release** — `scripts/plugin_calibrator_audit.py` in-tree; `release-gate.sh` discovers it before peer stub; `accessibility-overlay` `description` trimmed to pass 500-char skill gate; `build-release-zip.sh` + `releases/co-author-harness-claude-v0.8.6.zip`.

### Not changed

- No `phase_state.json` schema or trigger-enum change.

---

## v0.8.5 — 2026-04-24

**Theme.** **Wiki-first resource order** for wiki-linked projects: consult peer `LLM wiki/` before new Zotero PDFs and external discovery tools when adding literature.

### Changes

- **Protocol** — `references/EXTERNAL_VERIFIERS.md` §1.5 (strict read order + logged **Wiki-first** line); `PROJECT_BOOTSTRAP.md` `wiki_first_resources` flag; `GROUNDING_PROTOCOL.md` discovery vs. Rule 7a resolution; `AGENT_CONTRACTS.md` I-Gen-8; `agents/planner.md` wiki paths and Phase 1 / 3.5; `references/SKILL_REGISTRY.md` protocol surface note; Zotero row in §2 clarified for discovery vs. citation resolution.

### Not changed

- No new scripts; no `phase_state.json` schema or trigger enum change.

---

## v0.8.4 — 2026-04-24

**Theme.** Close documented plugin gaps: §9d executable, package docs, efficiency role map, and lightweight A6–A8 follow-through.

### Changes

- **Scripts** — `scripts/check8_g_prefilter.py` implements `references/DETERMINISTIC_CHECKS.md` §9d and merges output into `reviews/deterministic_<cycle_id>.md` (HTML-comment bounded block). `scripts/provenance_prewrite_check.py` (A8) verifies every `phase_deliverable_path` in `reviews/phase_state.json` resolves before ledger writes. Both are `py_compile` gates in `scripts/release-gate.sh`.
- **Documentation** — `references/CLAUDE.md` component table: authoritative `references/phase_notifications.yaml` (legacy `tier_notifications.yaml` remains a read-only stub). New `references/ADVISORY_UNTIL_SCOPING.md` (A7). `agents/reflector.md` Phase 2g: §9d G-candidate scale signal (A6). `agents/planner.md` pre-write path check (A8).
- **Config** — `.plugin-efficiency.json` `role_overrides` completed for the eight skills that were previously unmapped.
- **Proposals** — `reviews/plugin_update_proposals.md` v0.8.1 session rows for A6–A9 marked **IMPLEMENTED** in this release (user sign-off assumed via this shipping task).

### Not changed

- No new slash-command skills; no `phase_state.json` schema or trigger enum change.

---

## v0.8.3 — 2026-04-24

**Theme.** Repository and plugin **co-author** rebrand only.

### Changes

- **Plugin manifest** — `name` field: `co-author-harness-claude` (replaces `research-writing-harness-claude`). `description` updated to reflect the rebrand; no other manifest fields changed.
- **Release zip** — canonical filename pattern: `co-author-harness-claude-v<version>.zip` via `scripts/build-release-zip.sh`.
- **Documentation** — harness root, architecture, reference index, history, `README`, `CLAUDE.md`, and live agent/skill references updated to use `co-author-harness/` as the checkout folder name and `co-author-harness-claude` where the plugin id is cited. Historical release notes and proposals that refer to older ship artifacts are unchanged.

### Not changed

- No skills added, removed, or renamed. No `phase_state.json` schema, trigger enum, agent contract, or slash-command wiring change.

---

## v0.8.2 — 2026-04-24

**Theme.** Skill-body quality patches. A skill-judge audit of the v0.8.1 plugin (27 skills, judged against the Anthropic skill-design rubric) scored 97/120 (B, 81%) and flagged three systemic issues: (1) a ~500-character "File resolution (plugin context)" boilerplate block duplicated verbatim across 13 SKILL.md bodies, (2) 12 skills carrying descriptions under ~160 chars with weak trigger-keyword coverage, and (3) six skills over 200 lines that never used the per-skill `references/` subdirectory pattern despite having natural split boundaries. v0.8.2 addresses all three without altering capability — no new skills, no new behaviours, no surface renames. The expected score after patches is ~106/120 (A−, 88%).

### Changes

#### Quality — boilerplate removal

- **13 SKILL.md bodies** had the identical `> **File resolution (plugin context).** This plugin replaces the legacy `.paper-package/` deployment...` blockquote removed: `IS-theory-pass`, `advisor-escalation`, `check-abstract-body`, `check-contradictions`, `classify-manuscript`, `narrative-structure-pass`, `p-stage-checker`, `quick-deterministic`, `response-letter-review`, `run-reflection`, `sentence-level-pass`, `suchman-register-audit`, `tool-contract-roundtrip`. The legacy path translation note was obsolete for any session that reaches a skill (the plugin loader already resolves `${CLAUDE_PLUGIN_ROOT}` at runtime); removing it saves ~120 tokens × 13 invocations of context tax. All 13 files pass frontmatter validation post-edit.

#### Quality — description thickening

- **12 SKILL.md descriptions** were rewritten to carry explicit `Use when: "..."` trigger-phrase keywords alongside the capability statement, pushing each from sub-160-char to 275–337 chars (all ≤ 350 cap). Skills affected: `check-contradictions`, `plugin-commands`, `quick-deterministic`, `p-stage-checker`, `check-abstract-body`, `sentence-level-pass`, `IS-theory-pass`, `grounding-audit`, `public-interest-accountability-pass`, `narrative-structure-pass`, `suchman-register-audit`, `promote-lessons-to-wiki`. The `trigger:` field was already rich; the change propagates that richness to the activation surface (`description:`), which is the only pre-load field the Agent sees.

#### Quality — progressive disclosure via per-skill `references/`

- **4 SKILL.md bodies** had their longest detail blocks spilled into per-skill `references/` subdirectories with `MANDATORY — READ ENTIRE FILE` triggers at the workflow point where the detail is needed:
  - `accessibility-overlay`: 214 → 157 lines in SKILL.md + 68-line `references/sub_checks.md` (seven Sub-check A–G threshold specs).
  - `grounding-audit`: 249 → 116 lines in SKILL.md + 147-line `references/audit_categories.md` (eight audit-category rubrics with verification procedures).
  - `advisor-escalation`: 298 → 223 lines in SKILL.md + 89-line `references/external_reclassification.md` (Step 4 EXTERNAL re-classification: four attribution-pattern regexes + 4a–4d procedure).
  - `graph-grounding-overlay`: 232 → 198 lines in SKILL.md + 46-line `references/finding_types.md` (Phase 3 Finding A/B/C specs + three-tier matcher thresholds).
- Combined: **993 → 694 lines in SKILL.md bodies** (30% reduction) with ~350 lines parked behind MANDATORY triggers. Each extracted file opens with a statement of what it owns versus what SKILL.md owns.
- **Deferred:** `tool-contract-roundtrip` (230 lines) and `response-letter-review` (212 lines) sit just above the 200-line threshold but don't have an obvious natural split boundary — marked as future work rather than force-splitting.

#### Build hygiene

- **Zip build verified** against the canonical `scripts/build-release-zip.sh` exclusion list: 0 nested zips, 0 `__pycache__`/`.pyc`, 0 `releases/` entries, 0 boilerplate instances, 27/27 SKILL.md frontmatters valid, 206 files / 983 KB. Fixes the v0.8.1 release-zip defect where `releases/research-writing-harness-claude-v0.7.4.1.zip` and `releases/research-writing-harness-claude-v0.8.0.zip` were accidentally packaged inside the v0.8.1 zip, triggering the loader's "A zip file cannot have a nested zip file" refusal.

### Outstanding — canonical-tree drift

- The workspace-canonical `B:\Agents\co-author-harness\skills\` tree still carries the deprecated `run-tier-1`/`run-tier-2`/`run-tier-3`/`run-tier-4` aliases (v0.7.3-era) while the v0.8.1/v0.8.2 unpacked snapshot carries the `run-phase-*` names. The v0.8.2 patches in this release were applied to the unpacked tree only; the canonical root was not touched. A reconciliation pass is needed before the next release cut: either sync the canonical tree to the v0.8.1/v0.8.2 schema, or establish the `unpacked/<version>/` snapshots as canonical for release cuts and retire `skills/` at the root.

### Not changed

- No skill was added, removed, or renamed. No slash-command behaviour changed. No `phase_state.json` field rename, no trigger-enum change, no severity-floor change, no agent-contract change. Every agent that was valid at v0.8.1 remains valid at v0.8.2; every frontend invocation pattern is unchanged.

---

## v0.8.1 — 2026-04-23

**Theme.** Cumulative accessibility. v0.7.2 introduced SAFEGUARD Check 8 with six Sub-checks A–F operationalising Ph.D.-root CLAUDE.md §13.3 as a local-scale reader-accessibility defence — paragraph cadence, sentence rhythm, first-use definition, section-opening signposting, jargon density per paragraph, worked examples at density spikes. The INF3006Y Co Author Ph4 test variant (2026-04-23) surfaced a case the six local Sub-checks could not catch: the manuscript passed A–F everywhere yet accumulated six framings and three positions across twenty pages without a consolidation summary before Sec. 6's accountability-gap argument depended on them all. The local checks can all pass while the manuscript still imposes a working-memory tax that is visible only at distance. v0.8.1 adds **Sub-check G** (Cumulative Cognitive Load / Consolidation Anchors) as the seventh operational criterion, scoped to full-manuscript dispatch only and wired into the §3.3.3 accessibility convergence gate with the existing A–F aggregation rule extended to A–G.

### Changes

#### New SAFEGUARD sub-check

- **Check 8 Sub-check G — Cumulative Cognitive Load / Consolidation Anchors.** Operationalises Ph.D.-root CLAUDE.md §13.3 criterion 7. Scope = full manuscript only; noop reason code `G_REQUIRES_FULL_MANUSCRIPT` when invoked with a section path. Procedure: enumerate structural boundaries → measure construct accumulation → apply the three-or-more-constructs threshold → flag boundaries lacking a consolidation anchor → apply the word-count envelope (BLOCKER for 5,000+ word manuscripts with no anchors). Severity floors: MINOR on a single missed boundary under 5,000 words; MAJOR on two or more missed boundaries or a single miss at the closing argumentative move; BLOCKER on 5,000+ words with no anchors or a miss directly preceding an abstract-specified argument with three-plus prior-section dependencies. Full specification in `SAFEGUARD_LAYER.md` Check 8 Sub-check G.

#### Policy extension

- **`READER_ACCESSIBILITY.md §13.1–§13.2`** expanded to name the local/cumulative two-scale architecture explicitly: extraneous load is typically local; germane load is inherently cumulative. Consolidation anchors are the minimum-cost corrective at the cumulative scale.
- **`READER_ACCESSIBILITY.md §13.3`** criterion 7 added (Consolidation anchors at structural boundaries) with the construct-accumulation threshold and the canonical one-sentence anchor form.
- **`READER_ACCESSIBILITY.md §13.5`** remapped from six criteria → seven and from Sub-checks A–F → A–G. New `advisory_until: next_manuscript_at_ph3` transitional-scoping paragraph records the two-speed rollout for manuscripts whose Ph1 classification predates 2026-04-23.

#### Gate wiring

- **`TIER_PROTOCOL.md §3.3.3`** — gate trigger enumeration amended from "A–F finding" to "A–G finding" with the Sub-check G transitional exception noted; logging text updated to log G findings and mark advisory-under-flag status. The `PHASE_PROTOCOL.md` surface receives the equivalent update when the v0.8.1 unpacked tree is cut.

#### Skill extension

- **`skills/accessibility-overlay/SKILL.md`** bumped from v1.0 to v1.1 per D-G-2 decision (option A — single skill with a G branch, not a sibling skill). Preconditions extended with scope-resolution check (`G_REQUIRES_FULL_MANUSCRIPT` noop) and stability-sub-mode interaction. Sub-check G section added with procedure, severity floors, Sub-check D interaction note, advisory-until flag, stability-sub-mode advisory rule. Output template adds a G-findings block and `advisory_until_flag_active` / `stability_advisory` output fields. Tier-conditioning table updated to distinguish A–F at T2 from A–G at T3/T4. Closing normative status updated to reflect v0.8.1 extension.

#### Stability sub-mode rule (D-G-3 decision)

- **`SAFEGUARD_LAYER.md` Check 8 Sub-check G "Stability sub-mode interaction"** subsection documents the advisory-only rule under `run-phase-3-stability` (v0.8.0+): G findings under stability mode carry `stability_advisory: true`, do not force full-Ph3 escalation, do not contribute to the §3.3.3 aggregate verdict, and are handed to Reflector Phase 2g for recurrence accounting. The authoritative statement will live in `skills/run-phase-3-stability/SKILL.md §3.2` once the v0.8.1 unpacked tree is cut; the SAFEGUARD_LAYER.md paragraph is canonical until then.

#### Deterministic pre-filter for Sub-check G

- **`DETERMINISTIC_CHECKS.md §9d` — Cumulative cognitive load pre-filter.** New manuscript-scope pre-filter feeding Sub-check G. Emits boundary-gap word counts, paragraph counts since last major heading, and consolidation-cue density in the two-paragraph pre-heading window and the opening paragraph of each new major section. A G-candidate boundary requires both (i) preceding-span word count exceeding the P-stage gap envelope (P0 ≥ 800, P1 ≥ 700, P2 ≥ 600 words) AND (ii) zero consolidation-cue matches in both pre- and post-heading windows. Hint-only — the judgment pass confirms whether the boundary actually crosses the construct-accumulation threshold of §13.3 criterion 7. Orthogonal to §9b (paragraph-scale) and §9a (sentence-pair-scale). Runs at Ph3 and Ph4 only; skipped at Ph2. The pre-existing §9c (INF3001H artifact organization) is unaffected — §9d is the new section. Supersedes the proposal §4.4 "optional" tag: §9d is shipped with v0.8.1 to give Sub-check G a parallel pre-filter architecture rather than a judgment-only path.

#### Ship scope (D-G-1 decision)

- **v0.8.1 chosen over amending v0.8.0 §7 non-goal.** v0.8.0 ships from the frozen unpacked substrate at `unpacked/research-writing-harness-claude-v0.8.0/` without Sub-check G. v0.8.1 rebases on v0.8.0 and adds the changes listed above. This preserves the v0.8.0 non-goal contract on `PHASE_PROTOCOL.md §3.3.3` and keeps Sub-check G on a follow-on release cadence.

#### Consumer-manuscript directive (INF3006Y)

- **INF3006Y D-13** registered in `Ph.D. Research/INF3006Y_AgencyDelegation/research_notes/directives.md` as a Ph4 revision candidate (three consolidation anchors at end of Sec. 3, pivot into Sec. 5, opening of Sec. 6). Paired with Sub-check G under the `advisory_until: next_manuscript_at_ph3` flag, so the current Co Author Ph4 pass receives the anchors without the new Sub-check G gate retroactively reopening Ph3 convergence on the locked P0 manuscript variant.

### Lessons recorded

- **L-v0.8.1-01 — Local checks can be jointly comprehensive and globally insufficient.** Every Sub-check A–F passed on the INF3006Y Co Author manuscript before Sub-check G was authored; the meta-critique that surfaced the gap did so only because an external reviewer read the manuscript end-to-end. Structural audits at the local scale must be paired with a cumulative-scale audit when the manuscript exceeds the length at which a local pass can certify readability in one sitting. (Applies to: any harness adding local-only structural defences.)
- **L-v0.8.1-02 — Advisory-until scoping prevents retroactive gate reopenings.** The `advisory_until: next_manuscript_at_ph3` flag lets Sub-check G ship with binding severity for future manuscripts without forcing a re-convergence pass on manuscripts that closed Ph3 under the prior rule set. The pattern is generalisable: when adding a new BLOCKER-grade gate, scope the binding transition to "next manuscript at the affected rung" rather than "all manuscripts at the affected rung."
- **L-v0.8.1-03 — Judgment-heavy sub-checks need an explicit stability-sub-mode decision.** A–F are hash-inherited under `run-phase-3-stability` because they are judgment findings keyed to deterministic counter snapshots. G has no deterministic pre-filter (by design — the construct-accumulation procedure is read-the-whole-manuscript judgment). The D-G-3 advisory decision preserves the stability sub-mode's economic profile while keeping G's recurrence trail.

---

## v0.8.0 — 2026-04-23

**Theme.** Ph3/Ph4 redesign, token pruning, and verdict caching — composed as a single release from four architectural layers on the v0.7.4.1 substrate. v0.8.0 widens `SectionStateObject` from 15 to 16 fields (`pre_mcr_deep_pass_completed`), reshapes Ph3 iteration around three refinement profiles (refine / structural / deep) with a diff-scoped Evaluator and context halo, replaces the scalar `convergence_metric` with a four-component convergence vector over a three-round window, introduces a paragraph-hash verdict carryover cache for cross-iteration check reuse, and adds a pre-MCR Ph3-deep safety net. Token-surface reductions land through Evaluator pointer-demotion (α-C1), a shared Ph3/Ph4 common envelope (α-C2), and a `sk20_overlay_run.py` refactor that drops cyclomatic complexity from 48 to 15 (α-D). The four-agent contract (Planner / Evaluator / Generator / Reflector), the Grounding Protocol, the Lifecycle-Phase Ladder rung semantics (Ph1→Ph4), the SD/SR opt-in gate (v0.7.1), the Reader-Experience defence (v0.7.2), and the phase-conditioned model allocation (v0.7.3) all carry forward unchanged. The I-SubAgent-1/2/3 invariants (v0.7.4) are preserved throughout; `E-MA-CAPABILITY-INVERSION` extends to the verdict cache layer.

**Evidentiary caveat — structural-plus-hygiene at v0.8.0; empirical backfill deferred.** The ~80% cost overrun that motivated the v0.7.4 P-1 through P-8 package remains a single observation (INF3006Y iter-7, n=1). v0.8.0 adds structural refinements to the Ph3 iteration loop (check profiles, diff scoping, verdict caching) whose value is architectural — they reshape the iteration envelope regardless of the quantitative overrun figure. The v0.7.4 evidentiary caveat carries forward: economic-efficiency claims remain n=1 pending INF3001H's first Ph3 round under v0.8.0 as the independent replication. Threshold retuning for P-12 (convergence-vector stable-window) and P-16 (ceiling-lock budget) is deferred to v0.8.1 post-replication; thresholds ship as `v0.8.0-provisional`.

### Changes — Phase 0 (γ verify-and-cleanup against v0.7.4.1)

v0.7.4.1 shipped six bug-class closures (see v0.7.4.1 entry below). Phase 0 verified those closures on the wip0 substrate and completed two additional cleanup steps.

- **Deprecated-alias retirement.** The four `skills/run-tier-{1,2,3,4}/` deprecated-alias directories, retained at v0.7.4 for back-compatibility, are removed. `skills/plugin-commands/SKILL.md` command-catalog rows flipped from `/run-tier-N` to `/run-phase-N`. Skills count moves 31 → 27 (README heading and table updated).
- **P0.1a — `phase_state_schema.md` content rewrite.** The v0.7.4.1 file-rename left the body in v0.7.0 prose. Clean-rewrite to v0.7.4 shape: `sections` as object (not array), 15-field `SectionStateObject`, 7-field `PhaseEntryLogRow` with absent-means-null `model_used`, 30-trigger enum, exit-code convention `{0 PASS, 1 usage, 2 I/O, 3 MINOR/MAJOR, 4 BLOCKER}`. Smoketest fixtures renamed `tier_state_smoketest/` → `phase_state_smoketest/` with v0.7.4-shape content.
- **P0.3 Classes C/D audit.** Legacy-tree and retired-skill path references confirmed absent in wip0 `README.md`; historical `§Version` narrative preserved under the v0.7.4.1 carve-out.

### Changes — Phase 1 (α instrumentation: Tier A + Tier B)

- **P1.1 (α-A) `.plugin-efficiency.json` measured-throughput amendment.** Replaced the 2,000 tok/s placeholder with measured throughput: `input_tokens_per_second: 16897.1` against a warm Opus 4.7 connection. `role_overrides` table confirmed against the post-Phase-0 skills directory (27 skills).
- **P1.3 (α-B) chain-depth regression gate.** `scripts/release-gate.sh` extended with a chain-depth check against `.plugin-efficiency.json` at `max_chain_depth <= 15`. Phase 0.2 alias retirement dropped measured chain depth from 19 to the 12–15 range.

### Changes — Phase 2 (β core: Ph3/Ph4 redesign)

Fourteen sub-phases (P2.1a through P2.8) compose the architectural core. Eight proposals (P-9 through P-16 from `proposals/v0.7.5_phase3_refinement_loop_proposal.md`) land on the wip0 substrate.

#### P2.1a — `SectionStateObject` 15 → 16 fields

- **`pre_mcr_deep_pass_completed`** (bool, default `false`). The β-P-9a safety-net field: Planner flips to `true` on a Ph3 iteration closed under an approved F6 with `check_profile: deep`. MCR admission refuses sections with `pre_mcr_deep_pass_completed != true` via `E-MCR-PRE-DEEP-PASS-REQUIRED`. Schema, validator, and fixtures updated in sync.

#### P2.1a.1 — F6 `planner_dispatch_plan` validator reconciliation

- Pre-existing substrate gap: the `planner_dispatch_plan` family was documented in `ARTEFACT_FRONTMATTER_SCHEMA.md §7a` but had no `FAMILY_SCHEMAS` entry in the validator. Reconciled with `strict: True`, six required fields per §7a.1, six optional fields per §7a.2, `("list", element_schema)` DSL branch, and two F6-specific must-be-true cross-field rules (`user_approval_required`, `verdict_authoritative_as_read`). Fixture harness created: `artefact_frontmatter_smoketest/` with F6 PASS/BLOCK pair. `release-gate.sh` Phase 0.68 block added.

#### P2.1b — F1/F4/F6 frontmatter extensions

- **F1** (`evaluator_findings`): new required fields `adversarial_register` (enum: `refinement` | `certification`) and `routing_rationale` per P-9 register-audit + P-15 demoted-check routing.
- **F4** (`reflector_full_report`): new optional `demoted_check_advisories` append-only list.
- **F6** (`planner_dispatch_plan`): new optional fields `check_profile` (enum: `refine` | `structural` | `deep`), `structural_delta_flag`, `parallel_dispatch`, `threshold_version` (enum: `v0.7.5-provisional` | `v0.8.0-provisional`).
- Template `F1_evaluator_findings.md` updated to `schema_version: "1.1"`. Three new BLOCK fixtures authored.

#### P2.1c — `paragraph_hash_map.py`

- New script producing a paragraph-level hash map over manuscript files. Deterministic output (paragraph-boundary canonicalization documented in module header). Feeds P-10 diff-scope and the verdict cache key design. `release-gate.sh` Phase 0.69 determinism check added.

#### P2.1d — `migrate_convergence_journal_v075.py`

- Backfills prior scalar `convergence_metric` rows to the four-component shape; marks un-reconstructible rows `[v0.8.0-BACKFILL-N/A]`; idempotent re-runs supported. `release-gate.sh` Phase 0.695 smoketest added.

#### P2.2 — `PHASE_PROTOCOL.md` rewrites

- **§3.3.0** — three `check_profile` values with `halo_scope` enum; normative per-check matrix imported by reference from `DETERMINISTIC_CHECKS.md` and `SAFEGUARD_LAYER.md`.
- **§3.3.1a** — P-12 four-component `convergence_metric` object: `{grounding_clean, check8_aggregate_ok, findings_count_delta, line_delta}`. Three-round `[CONVERGENCE-STABLE]` window for objects (vs two-round for legacy scalars). Thresholds ship as `v0.8.0-provisional`.
- **§3.3.4** — journal extended with optional `paragraph_hash_map`, `convergence_metric` typed `float | null | object`, dual `[CONVERGENCE-STABLE]` rule for legacy vs migrated.
- **§3.4** — pre-MCR Ph3-deep pass: `pre_mcr_deep_pass_completed: true` required; `E-MCR-PRE-DEEP-PASS-REQUIRED` refusal.

#### P2.3 — Ph3/Ph4 SKILL rewrites

- `skills/run-phase-3/SKILL.md`, `skills/run-phase-3-stability/SKILL.md`, `skills/run-phase-4/SKILL.md` aligned to `check_profile` router, P-12 convergence-vector, and MCR `pre_mcr_deep_pass_completed` gate.

#### P2.4 — Evaluator prompt additions

- P-13 parallel subagent dispatch with `parallel_dispatch_cost_multiplier` logging and `parallel_dispatch: false` opt-out.
- P-9 `adversarial_register` (refinement ↔ certification split).
- P-10 diff-scope + `halo_scope` + `paragraph_hash_map` + `containing_section` fallback.
- P-15 `demoted_check_advisories` + `routing_rationale`.
- F6 `check_profile` in Ph3 procedure; sixteen-field read list; YAML frontmatter.

#### P2.5 — Reflector prompt additions

- Phase 2f: `R-Refl-RG-1 register_mismatch` (MAJOR), `R-Refl-RT-1 routing_ambiguity` (new finding class).
- Phase 2g: `§2g.3 Demoted-check recurrence` with `R-Refl-DC-1`.

#### P2.6 — Planner prompt additions

- Phase 0.6 F6 authorship extended with `check_profile`, `structural_delta_flag`, `parallel_dispatch`, `threshold_version`.
- P-16 ceiling-aware iteration budget with `/ph3-terminate` suggestion under ceiling-lock.
- Phase 5.5 `pre_mcr_deep_pass_completed` flip on `deep`-profile close.
- Phase 6 MCR β-P-9a deep-pass list.

#### P2.7 — Agent contracts

- **I-Eval-8** — P-13 F6 `parallel_dispatch` + multiplier logging.
- **I-Planner-11** — P-16 ceiling-aware budget + MCR β-P-9a hook.
- **I-Planner-10** extended with F6 quartet fields.
- **I-Planner-9** scalar + menu.

#### P2.8 — Scope-freeze gate (A-GK-4)

- §3.P-9.1 eleven-row falsification-table disposition column populated under user directive **Default continue** (D-6). Rows 1–10: **retained in Ph4-deep**. Row 11: **retained in Ph4-deep with confessed coverage gap + v0.7.6 lightweight-proxy milestone logged**. The Ph3-refine check surface is NOT widened by P2.8; all deferred checks stay in Ph4-deep.

### Changes — Phase 3 (α token pruning: Tier C1 + Tier C2 + Tier D)

Applied after Phase 2 (β core) so pointer-demotion and envelope factorisation operate on the final post-β surface.

#### P3.1 (α-C1) — Evaluator pointer-demotion

- The long Tier-conditioned / gate-set exposition in `agents/evaluator.md` replaced by a **phase-conditioned pointer table**, four binding call-outs, and a one-line Gate set pointer to `PHASE_PROTOCOL.md §7`. Ph-native adaptation of the hand-authored diff (the diff targets v0.7.0 Tier vocabulary; the wip0 surface is post-β Ph vocabulary). Token reduction: ~1,465 tokens on the evaluator prompt.
- Paired review confirmed all 14 README binding rules accounted for (12 PRESENT, 1 at skill layer, 1 intentionally dropped).
- SAFEGUARD Check 1 (Regression Guard): CLEAN — 16 rules inventoried, all PRESERVED or REACHABLE.

#### P3.2 (α-C2) — Common envelope factorisation

- **New reference `references/PHASE3_PHASE4_COMMON_ENVELOPE.md`** (127 lines, 10 sections). Shared semantic blocks: seven-step judgment-pass structure, SAFEGUARD layer invocation, Check 8 aggregation, convergence-metric contract, Coupling E.2 overlay dispatch, Reflector audit hooks.
- Three SKILL files rewritten to pointer + differentiators: `run-phase-3` (204→180 lines), `run-phase-3-stability` (134→133), `run-phase-4` (214→199).
- **Note on economics.** The factorisation is maintenance deduplication (single source of truth for 10 shared blocks), not per-invocation token savings. Per-invocation load increases slightly because the agent reads the 127-line envelope in addition to the SKILL. The value is structural, not economic.
- Paired review CLEAN — all invariants preserved.

#### P3.3 (α-D) — `sk20_overlay_run.py` refactor

- Cyclomatic complexity: max 56 → 15, average 13.75 → 7.24.
- Maintainability index: 0 → 18.7 (B-grade; MI ≥ 30 not achievable without reducing functionality due to the file's inherent operator/operand volume at ~420 lines).
- New `_GraphCorpus` class + 5 extracted functions. I/O contract preserved.

#### P3.4 — Tier → Phase residual cleanup

- Three remaining `T1`/`T2`-vocabulary substitutions in `agents/evaluator.md` outside the v0.7.0 documentary block boundaries. Zero residuals after sweep.

### Changes — Phase 4 (β P-14 pulled-forward: paragraph-hash verdict carryover cache)

- **New reference `references/VERDICT_CACHE_CONTRACT.md`** (~140 lines, 8 sections). Defines per-check-class cache keys: paragraph-local checks use `(paragraph_hash, check_id)`; cross-paragraph checks add `diff_scope_fingerprint = SHA-256(sorted(changed_paragraph_id_set))`. Check-class tag derived from `halo_scope`.
- **Key design correction.** The architecture spec (§P4.1) placed `model_family` in the cache key. The shipped contract stores `model_family` in the entry but filters at lookup time via capability-inversion ordering. This enables cross-model reuse (an Opus verdict is usable by Sonnet) while preserving the `E-MA-CAPABILITY-INVERSION` refusal (a Haiku verdict is refused by Opus).
- Cache is Evaluator-owned at `reviews/.evaluator_verdict_cache/<project>.json`. Not a ledger artefact; the Planner does not read it.
- **P4.3 threshold retuning.** `v0.8.0-provisional` added to `VALID_F6_THRESHOLD_VERSIONS` in the validator, planner, and schema. Fixtures retain `v0.7.5-provisional` to confirm backward compatibility.

### Plugin manifest

- **`.claude-plugin/plugin.json`.** Version `0.7.4.1 → 0.8.0`. Description rewritten (see P5.2).

### New files (summary)

| File | Phase | Purpose |
|------|-------|---------|
| `references/PHASE3_PHASE4_COMMON_ENVELOPE.md` | P3.2 | Shared Ph3/Ph4 envelope |
| `references/VERDICT_CACHE_CONTRACT.md` | P4.1/P4.2 | Verdict cache contract |
| `scripts/paragraph_hash_map.py` | P2.1c | Paragraph-level hash map |
| `scripts/migrate_convergence_journal_v075.py` | P2.1d | Convergence journal backfill migration |

### Expected release-gate profile

- BLOCKER 0, MAJOR 0.
- `prompt_clarity_score` MINOR remains (structural, declared non-blocking at v0.7.4.1).
- `audit-package-speed` rc=2 in some environments (WARN-degradation, non-blocking).

### Migration

- **From v0.7.4 or v0.7.4.1.** Run `python scripts/migrate_convergence_journal_v075.py --project-root <project>` to backfill the convergence journal to the four-component shape. The 15 → 16 field widening (`pre_mcr_deep_pass_completed`) uses absent-means-false semantics — existing ledgers parse without modification; the Planner writes the field on first `deep`-profile close.
- **From v0.7.3 or earlier.** Run the v0.7.4 two-pass migration first (see v0.7.4 entry below), then the v0.8.0 journal migration.
- **Dual-read surfaces removed.** The four `run-tier-{1,2,3,4}` deprecated-alias directories, the `tier_state.json` fallback in `phase_state_validate.py`, and the `TIER_PROTOCOL.md` forwarding stub are all removed at v0.8.0. Projects must be on the phase-named surface before upgrading.

### Lessons

- **Maintenance deduplication beats per-invocation token savings when the shared surface is ≥10 semantic blocks.** The α-C2 common-envelope extraction increases per-invocation token load slightly (the agent reads the 127-line envelope + the SKILL), but collapses three maintenance surfaces to one. The trade-off is favourable because the 10 shared blocks had already drifted between the three SKILL files during the β Ph3/Ph4 redesign — deduplication closes a real consistency hazard, not a hypothetical one.
- **Cache key design should place model-family at lookup, not in the key.** Placing `model_family` in the key makes capability-inversion protection redundant (key mismatch = automatic miss) and forfeits cross-model reuse (an Opus verdict becomes invisible to Sonnet). Placing it at lookup enables reuse on the capability-ordering `{Haiku} ≺ {Sonnet} ≺ {Opus}` while still refusing capability-inversion at access time.
- **Substrate inconsistencies surface during pre-flight, not during planning.** Twice during Phase 2 (R-P0-SCHEMA-3, R-P2-VALIDATOR-F6), a pre-existing v0.7.4 gap surfaced during a sub-phase pre-flight audit. The remedy was to nest a dedicated reconciliation sub-phase before the additive work touched the same surface. Lesson: budget one reconciliation sub-phase per three planned sub-phases when the substrate has not been recently audited.
- **n=1 carries forward honestly.** The v0.7.4 ship-on-iter-7-only caveat is now at v0.8.0 with no additional replication data. The structural refinements (check profiles, diff scoping, verdict caching) are defensible on architectural grounds independent of the quantitative overrun figure, but the economic claims remain n=1 until INF3001H's first Ph3 round.

---

## v0.7.4.1 — 2026-04-21

**Theme.** Point release — hygiene pass against the plugin-calibrator's release gate. Six bug classes surfaced by the calibrator on the v0.7.4 tree are closed, the authoritative allow-list at `.plugin-calibrator.json` is frozen for v0.7.4.1, and the expected post-fix severity profile is BLOCKER 0 / MAJOR 0 / MINOR 0. No runtime-behavioural changes. Every agent contract, phase gate, ledger invariant, convergence metric, SAFEGUARD aggregation, and model-allocation rule behaves exactly as at v0.7.4. **This is a documentation-and-metadata release; no migration is required from v0.7.4.**

### Changes

- **Class A — `tier_state_schema.md` → `phase_state_schema.md` rename.** Physical file rename landed at v0.7.4.1 closing the Tier → Phase rename that v0.7.4 otherwise declared complete. A file-rename note is added at the head of `references/phase_state_schema.md` flagging that the body is v0.7.0 schema prose pending full-body rewrite at v0.7.5 RC; the key-renames table near the top of the file still holds for machine consumption.
- **Class B — deprecated-alias SKILL.md relative paths.** The four v0.7.4 deprecated aliases under `skills/run-tier-{1,2,3,4}/` referenced the canonical phase-named sibling skill directories and the phase-protocol reference file with relative-path forms that the calibrator's plugin-root-anchored resolver (strip-`..` + suffix-match) could not resolve. The two references in each of the four alias files are rewritten to plugin-root-anchored forms pointing at the phase-named sibling skill directories and at the phase-protocol reference file, which work both as valid relative markdown links from the referring files and as suffix-matches after the resolver's strip-`..` step.
- **Classes C and D — `README.md` legacy-tree and retired-skill references.** The `README.md` sections describing v0.5.5 (Tier Marshal rollout) and v0.6.0 (rule-digest build-verify) linked to files under `legacy/marshal-f1-retired/` and `legacy/rule-digest-v060-retired/` — trees that are development-only and release-excluded. The historical paragraphs are rewritten to describe the retired mechanisms in prose without linking to their retired source paths; the file-path references (10 refs across 11 lines) are removed and the descriptions retain their load-bearing narrative. Retired-skill references to `run-tier-standard` / `run-tier-submission` / `run-tier-reflex` / `run-full-review` in the historical changelog prose stand as-is (narrative reference to the then-live skill name is not a dead-reference claim against the shipped v0.7.4.1 skill catalogue).
- **Class E — `README.md` skills-catalog parity.** The `README.md` skills table advertised **26** skills; the filesystem ships **31** (the v0.7.4 additions: `run-phase-1`, `run-phase-2`, `run-phase-3`, `run-phase-3-stability`, `run-phase-4`, plus the four deprecated-alias directories `run-tier-{1,2,3,4}`). Five net-new rows are added to the skills table for the phase-named canonical rung skills and the stability sub-mode, and the four tier-named rung rows are demoted to `**Deprecated alias** of run-phase-N` entries. The count in the `### Skills (N)` heading moves 26 → 31 and the `readme_catalog_parity:skills` check clears.
- **Class F — agent output-contract heading.** The calibrator's `md_agent_contract_declared` check walks each agent prompt under `agents/` looking for a stable heading declaring the artefact the agent produces. All four v0.7.4 agent prompts missed this heading. A `## Output Contract` section is added near the top of each of the four agent prompts (`planner.md`, `evaluator.md`, `generator.md`, `reflector.md`), cross-referencing `AGENT_CONTRACTS.md §N` with a short summary of what the agent writes and — critically — what it does not write. Severity was MINOR because the contracts *exist* in `AGENT_CONTRACTS.md` and the pipeline honours them; the finding was about discoverability, not integrity.
- **`.plugin-calibrator.json` (authoritative).** The allow-list declaring the user-project-tree prefixes that the plugin's skills legitimately reference at runtime (`manuscript/`, `research_notes/`, `reviews/`, `wiki/`) plus six well-known individual runtime-pointer files (`concepts/humanness.md`, `graphify-out/GRAPH_REPORT.md`, `graphify-out/graph.json`, `references/REFERENCES.md`, `references/terminology_register.md`, `sources/chung-2026-identity-req.md`) is shipped as authoritative for v0.7.4.1 and beyond. The `_comment` field reframes the file from the v0.7.4-era "punch-list pending" framing to a stable v0.7.4.1 reference-configuration contract.

### Expected release-gate profile (post-fix)

- BLOCKER 0, MAJOR 0, MINOR 0 under the curated `.plugin-calibrator.json`.
- All six v0.7.4 residuals clear with zero remaining noise.
- No behavioural regressions — the v0.7.4 contract stands byte-for-byte.

### Migration

None. A project tree that was on v0.7.4 can advance to v0.7.4.1 without running any migration script; the v0.7.4 ledger shape (7-field log row, 30-trigger enum, 15-field `SectionStateObject`) is unchanged. Projects still on v0.7.3 or earlier run the v0.7.4 two-pass migration (`migrate_v073_to_v074_tier_to_phase.py` then `migrate_convergence_log_v074.py`) described in v0.7.4's CHANGELOG entry.

### What carries forward unchanged from v0.7.4

The eight-proposal economic-efficiency package (P-1 through P-8) lands byte-for-byte; the Tier → Phase rename is complete (with the Class A schema file rename closing the last loose end); the I-SubAgent-1 invariant stands; the phase-conditioned model allocation (v0.7.3), the Reader-Experience defence (v0.7.2), the SD/SR opt-in gate (v0.7.1), and the Grounding Protocol (universal) are unchanged. The four-rung ladder, the MCR admission gate, the Check 8 TerminalSignoffRow gate, and the EG-1 / EG-7 monotonicity exemptions behave as at v0.7.4.

---

## v0.7.4 — 2026-04-21

**Theme.** Two tracks behind one scaffold. v0.7.4 bundles (A) an eight-proposal economic-efficiency package **P-1 through P-8** addressing a ~80% cost overrun observed on **one** diagnostic round (INF3006Y iter-7 stability pass; n=1) and (B) a cross-cutting **Tier → Phase terminology rename** retiring a latent clash between the retired *Tier* surface (review depth) and the active *Phase* surface (manuscript lifecycle). The two tracks share a Phase-1 scaffold — migration scripts, validator replacement, protocol rename, agent-prompt surface rewrite, skill-name rename — so each of the eight proposals lands on a fully-migrated ledger and cannot leak tier-named surfaces into the new contracts. The **Lifecycle-Stage Ladder** becomes the **Lifecycle-Phase Ladder**: Ph1 Plan & Draft → Ph2 Review & Revise → Ph3 Iterate & Converge → Ph4 Finalize & Close. The ledger at `reviews/phase_state.json` carries a 15-field `SectionStateObject` and a **7-field** `PhaseEntryLogRow` (widened 6 → 7 fields with absent-means-null `model_used`), and the trigger enum extends **28 → 30** (trigger 29 `ph3_iteration_round_manuscript` for P-7 batching, trigger 30 `stability_mode_escalated_to_full_ph3` for P-2 escalation). The **I-SubAgent-1/2/3** invariants are new at v0.7.4 under P-5: subagent-returned verdicts are authoritative-as-read and the dispatching agent may not re-adjudicate. The four-agent contract (Planner / Evaluator / Generator / Reflector), the Grounding Protocol, the SD/SR opt-in gate (v0.7.1), the Reader-Experience defence (v0.7.2), and the phase-conditioned model allocation (v0.7.3) all carry forward unchanged.

**Evidentiary caveat — ship-on-iter-7-only (n=1).** The ~80% cost overrun that motivates the P-1 through P-8 package is a **single observation** from one diagnostic round (INF3006Y iter-7, stability pass with a byte-stable manuscript re-entering full Ph3 against the prior close). The package corrects a structural failure mode that round surfaced — full Ph3 re-work on a byte-stable manuscript — but the quantitative overrun figure may not generalise. INF3001H's first Ph3 round under v0.7.4 will serve as the independent replication. If the overrun does not reappear, the quantitative framing in this CHANGELOG (see `CHANGELOG.md` §v0.7.4 theme) steps down from "~80% observed" to "~80% observed on a single round"; the structural fixes stand regardless.

### Changes — Track A (P-1 through P-8 economic-efficiency package)

#### P-1 — Planner Phase 0.6 dispatch plan

- **`agents/planner.md` Phase 0.6 (new).** Round-scoped dispatch plan authored before any Ph2/Ph3/Ph4 invocation, naming which agents will engage at which phase, which checks will run, and which model is allocated per slot (feeds v0.7.3's `MODEL_ALLOCATION §2`). Artefact: `reviews/dispatch_plan_<round>.md`.
- **Schema family F6** (`references/ARTEFACT_FRONTMATTER_SCHEMA.md`) — `planner_dispatch_plan` frontmatter contract. F6 is **not inherited** under the P-2 stability sub-mode (stability rounds author a reduced-envelope F6 with the S-0 hash-match stamp).
- **Not a ledger trigger** — per decision 6 of the v0.7.4 gate, the dispatch plan is a round-scoped artefact rather than a new trigger-enum slot. The user-gated checkpoint replaces inferred dispatch.
- **New invariant** I-Planner-10 — Planner must author F6 before any Ph2/Ph3/Ph4 subagent invocation; missing F6 blocks dispatch with `E-PLANNER-MISSING-DISPATCH-PLAN`.

#### P-2 — Ph3 stability sub-mode (`run-phase-3-stability`)

- **New skill `skills/run-phase-3-stability/SKILL.md`** (SK-31). Reduced-envelope Ph3 pass authorised only on a manuscript byte-stable against the prior Ph3 close (SHA-256 of the F1/F2/F3/F5 substrate unchanged). Runs grounding audit (Rule 1 full-file read) and Check 8 deterministic pre-filter counters from `DETERMINISTIC_CHECKS §9b` only; skips Evaluator seven-step judgment pass and full SAFEGUARD.
- **S-0 admission gate** — `PHASE_PROTOCOL.md §3.3.2` names the hash-match precondition; failure drops through to full Ph3 (not a ledger row).
- **Trigger 30** `stability_mode_escalated_to_full_ph3` — on a stability-pass failure, the Planner appends one row back to full Ph3 under trigger 30; `escalation_reason` preserved in `notes`.
- **Evaluator extension** — `agents/evaluator.md` Ph3 scope-budget clause 1 extended with stability-sub-mode cross-reference; explicit skip list; report escalation-reason string without authoring `TerminalSignoffRow`.

#### P-3 — Artefact frontmatter-first contract (F1–F6)

- **`references/ARTEFACT_FRONTMATTER_SCHEMA.md` (new).** Six-family schema: **F1** `evaluator_findings`, **F2** `evaluator_deterministic`, **F3** `reflector_lightweight_probe`, **F4** `reflector_full_report`, **F5** `planner_consolidated_findings`, **F6** `planner_dispatch_plan` (P-1). YAML frontmatter replaces prose re-parsing.
- **`scripts/artefact_frontmatter_validate.py` (new).** Family-aware validator enforcing required fields, type constraints, and count consistency.
- **Finding classes** `R-Refl-FM-1` (missing field), `FM-2` (type mismatch), `FM-3` (unknown field), `FM-4` (count consistency), `FM-5` (Check 8 derivation), `FM-6` (legacy advisory for pre-v0.7.4 artefacts), `FM-7` (unknown document_type). All land under the Reflector Phase 2f contract audit.
- **Evaluator / Reflector templates rewritten** — all Evaluator and Reflector artefact templates now open with YAML frontmatter.

#### P-4 — Convergence-log contract split

- **`reviews/convergence_log.md`** frozen as Trajectory-synthesis prose only (narrative of the round's convergence trajectory).
- **`reviews/convergence_journal.jsonl` (new).** Per-iteration state with fields `{cycle_id, iteration, convergence_metric, check8_aggregate, manuscript_hash, new_findings_count, delta_lines, accessibility_gate_state, timestamp}`.
- **`scripts/migrate_convergence_log_v074.py` (new, Pass 2).** Backfills the journal from the legacy prose log; emits `reviews/migration_report_convergence_log_v074.md`; idempotent re-runs supported.

#### P-5 — Subagent delegation (I-SubAgent-1/2/3)

- **I-SubAgent-1** (authoritative-as-read). Subagent-returned verdicts — e.g., an Evaluator's SAFEGUARD Check 8 aggregation, a grounding audit, a deterministic-counter pass — are authoritative-as-read: the dispatching agent may not re-adjudicate.
- **I-SubAgent-2** (scope preservation). Subagent dispatch may not widen the scope of the dispatched task beyond the Planner-declared envelope recorded in the F6 dispatch plan.
- **I-SubAgent-3** (termination parity). Subagent completion is necessary and sufficient for the dispatching agent's corresponding step; no silent re-run.
- **Reflector Phase 2f audit** gains `R-Refl-SA-1` (invariant violation BLOCKER) for re-adjudication, `R-Refl-SA-2` (scope violation MAJOR), and `R-Refl-SA-3` (termination parity mismatch MAJOR).

#### P-6 — Session-state caching (I-Planner-7)

- **Hash-keyed in-memory cache** for `phase_state.json`, `classification.md`, and `directives.md` reads for the duration of a round; invalidated on any write to the three files.
- **I-Planner-7** invariant — Planner reads these three files through the cache during a round; direct disk reads outside the cache are flagged by Reflector Phase 2f.
- Prevents the re-read storm that iter-7 attributed ~18% of its overrun to (n=1).

#### P-7 — Manuscript-level Ph3 iteration batching (I-Planner-8)

- **Trigger 29** `ph3_iteration_round_manuscript` (new). Licences one ledger row per section in a manuscript-level Ph3 iteration touching N sections, sharing a `cycle_id` in `notes`, instead of N independent rows with N independent cycle_ids.
- **I-Planner-8** invariant — per-section monotonicity preserved; manuscript-level cycle_id shared across the N rows of a single iteration.
- Collapses ledger-write overhead without losing per-section accountability.

#### P-8 — Ceiling-lock termination ranking (I-Planner-9)

- **Distance-to-ceiling metric** — when a Ph3 close is blocked by a single BORDERLINE advisory or a near-stable `convergence_metric`, the Planner ranks termination candidates by distance-to-ceiling and presents a ceiling-lock proposal to the user rather than spending additional budget on diminishing returns.
- **I-Planner-9** invariant — ceiling-lock proposals are user-gated; automatic lock is never permitted.
- **Finding class** `R-Refl-CL-1` (MAJOR) for orphan ceiling-lock actions (locked without user approval on the record).

### Changes — Track B (Tier → Phase rename, cross-cutting)

#### Field renames (ledger and classification)

- `reviews/tier_state.json` → **`reviews/phase_state.json`**
- `current_tier` → **`current_phase`**
- `tier_goal_declared` → **`phase_goal_declared`**
- `tier_deliverable_path` → **`phase_deliverable_path`**
- `tier_entry_log` → **`phase_entry_log`**
- `t1_pstage_declaration` → **`ph1_pstage_declaration`**
- `t3_last_activity_at` → **`ph3_last_activity_at`**
- `default_final_tier` → **`default_final_phase`** (in `classification.md` frontmatter)

#### Value renames

- `T1`, `T2`, `T3`, `T4` → **`Ph1`**, **`Ph2`**, **`Ph3`**, **`Ph4`**
- `T3_converged` → **`Ph3_converged`**
- `[T3-STALE]` → **`[Ph3-STALE]`**
- Trigger prefix `t*_*` → **`ph*_*`** across the enum
- `eg1_t4_downgrade_to_t3` → **`eg1_ph4_downgrade_to_ph3`**

#### Completion-artefact renames

- `reviews/t1_draft_completion.md` → **`reviews/ph1_draft_completion.md`**
- `reviews/t2_review_completion.md` → **`reviews/ph2_review_completion.md`**
- `reviews/t3_convergence_signoff.md` → **`reviews/ph3_convergence_signoff.md`**

#### Log row widened 6 → 7 fields

- New 7th field **`model_used`** (absent-means-null): string naming the Claude model that produced each state transition, feeding the capability-inversion refusal at v0.7.3 §12.9.
- Reflector Phase 2f gains two new findings coupled to the new field: **`R-Refl-MA-4`** (MAJOR) when `model_used` disagrees with `MODEL_ALLOCATION §2` for a phase-actor slot without a corresponding dispatch-override directive; **`R-Refl-MA-5`** (MINOR) when `model_used` is null but `actor` is not `user` (incomplete provenance). R-Refl-MA-5 is suppressed for rows dated before the v0.7.4 release to avoid a retroactive finding cloud.

#### Trigger enum 28 → 30

- **Trigger 29** `ph3_iteration_round_manuscript` (P-7 batching).
- **Trigger 30** `stability_mode_escalated_to_full_ph3` (P-2 escalation).
- Monotonicity exemptions unchanged: `retraction`, `eg1_ph4_downgrade_to_ph3` (renamed), `eg7_mcr_readmission_after_class_change`.

#### Protocol rename

- **`references/TIER_PROTOCOL.md` → `references/PHASE_PROTOCOL.md`**. The tier-named path ships as a symlink (or copy with a one-line deprecation banner) during the v0.7.4 minor; removed at v0.7.5 RC.
- All `§3.3.*`, `§5.*`, and `§6.*` section anchors preserved under the renamed file.

#### Skill renames

- **`skills/run-tier-1` → `skills/run-phase-1`**; **`skills/run-tier-2` → `skills/run-phase-2`**; **`skills/run-tier-3` → `skills/run-phase-3`**; **`skills/run-tier-4` → `skills/run-phase-4`**.
- The four tier-named skills ship as **deprecated aliases** during the v0.7.4 minor (no-op wrappers emitting `DEPRECATION_WARNING` and forwarding to the phase-named skill); removed at v0.7.5 RC.
- `SKILL_REGISTRY.md`: phase-named entries added; SK-31 `run-phase-3-stability` (P-2) brings the active skill count to 25.

#### Sibling-ladder naming (preserved, not renamed)

- The response-letter sibling ladder rung **T4R** (v0.7.0 rename of T3R) **remains T4R** at v0.7.4 — not renamed Ph4R. The sibling ladder does not read or write `phase_state.json` and does not feed the main Ph1 → Ph4 advancement.

#### Agent-prompt surface

- All four `agents/*.md` files rewritten for the phase-named surface: Planner Phase 0.6 + Phase 4.5 (v0.7.3 carryover) + Phase 5.5 (P-2 stability dispatch); Evaluator Ph3 scope-budget clause 1 extended; Generator phase-scoped drafting envelopes; Reflector Phase 2f extended with new FM / SA / MA / CL finding classes.

#### Scripts

- **`scripts/migrate_v073_to_v074_tier_to_phase.py` (new, Pass 1).** Renames ledger file, top-level fields, values, trigger prefix, `eg1_*` trigger, completion-artefact paths, and `default_final_tier` → `default_final_phase`; widens log row 6 → 7 with absent-means-null `model_used`; emits `reviews/migration_report_v073_to_v074.md`; idempotent re-runs supported; backup at `phase_state.json.v073.bak`.
- **`scripts/migrate_convergence_log_v074.py` (new, Pass 2).** See P-4 above.
- **`scripts/phase_state_validate.py` (new).** Replaces `scripts/tier_state_validate.py`; enforces monotonicity with the three documented exemptions. The old script ships as a one-line forwarding shim during the v0.7.4 minor.
- **`scripts/phase_notifications_loader.py` (new, renamed from `scripts/tier_notifications_loader.py`).** Loader rewritten with a dual-read path — prefers `references/phase_notifications.yaml` and falls back to `references/tier_notifications.yaml` with a `W-DUAL-READ-LEGACY` DEPRECATION_WARNING on stderr. Legacy `--class` vocabulary (`dispatch` / `gates` / `calibration`) continues to resolve via an internal alias map with a one-time rename note. The tier-named loader ships as a one-line forwarding shim through the v0.7.4 minor; both the dual-read fallback and the legacy-class aliases are removed at v0.7.5 RC.
- **`scripts/pre_tier_advance_check.py`** and **`scripts/tier_state_canonicalize.py`** — banner comments added at the head of each file under the `[v0.7.3-READ-ONLY]` marker; retained for the v0.7.4 minor; removed at v0.7.5 RC.
- **Dual-read path.** `phase_state_validate.py` accepts legacy `tier_state.json` with a `DEPRECATION_WARNING` finding during the v0.7.4 minor; removed at v0.7.5 RC.

#### Notifications catalogue rename

- **`references/tier_notifications.yaml` → `references/phase_notifications.yaml`** (whole-file Ph-keyed rewrite). `config_version` `3.0 → 4.0`; `schema_version: 0.7.4`. Nine top-level sections (`phase_transitions` / `escalation_gates` / `ph3_loop` / `ph1_ph2_signoff` / `response_letter` / `integrity` / `mcr` / `fallbacks` / `ph3_stability_sub_mode`); all 30 triggers rendered; all `{prev_tier}` / `{new_tier}` placeholders renamed to `{prev_phase}` / `{new_phase}`; T4R response-letter keys preserved verbatim. Net-new template `integrity/dual_read_legacy_warning` (finding key `W-DUAL-READ-LEGACY`) emitted by the loader on legacy-file fallback. The tier-named YAML ships as a ≤50-line forwarding stub with a `[v0.7.3-READ-ONLY]` banner through the v0.7.4 minor; removed at v0.7.5 RC.

#### Reference-file banners

- **`references/TIER_PROTOCOL.md`** (forwarding stub, bannered at Phase-1 scaffold — see *Protocol rename* above).
- **`references/tier_state_schema.md`** — `[v0.7.3-READ-ONLY]` banner added at the head of the file pointing to `phase_state_schema.md` / `PHASE_PROTOCOL.md §5` as authoritative; mental-rename map inlined for the dual-read window; removed at v0.7.5 RC.

### Plugin manifest

- **`.claude-plugin/plugin.json`.** Version `0.7.3 → 0.7.4`. Description rewritten in Ph-named vocabulary at 390 characters (under the ~400-char manifest ceiling). Keyword renames (`lifecycle-stage-ladder → lifecycle-phase-ladder`, `tier-state-ledger → phase-state-ledger`) and additions (`stability-sub-mode`, `dispatch-plan`) for 14 total.

### Portfolio-root CLAUDE.md (Ph.D. Research)

- **§12 rewritten** end-to-end for the phase-named surface. §12.10 added for the v0.7.4 economic-efficiency package (P-1 through P-8) with the ship-on-iter-7-only (n=1) caveat made visible.
- **§13.5 retitled** to track the Ph2/Ph3/Ph4 enforcement surface without changing the aggregation or severity mechanics.
- **§10 Prohibited Moves** final bullet updated: Ph4 admission gated by `Ph3_converged` + no `[Ph3-STALE]` flags.

### Lessons

- **Two tracks behind one scaffold beats two releases.** The P-1 through P-8 economic-efficiency package could have shipped at v0.7.4 alone, with the Tier → Phase rename deferred to v0.7.5. The decision to bundle them was deliberate: every P-proposal touches the ledger surface (new triggers, new log-row field, new invariants), and landing those on the tier-named ledger would have forced a second cycle of agent-prompt edits, validator edits, and migration work at v0.7.5. Bundling absorbs the rename churn once. Lesson: when a rename and a feature set both touch the same schema spine, bundle them behind a Phase-1 scaffold rather than serialising the releases.
- **Ship-on-n=1 is a deliberate user override, not a silent decision.** The ~80% cost overrun motivating P-1 through P-8 is a single observation. Shipping fixes on n=1 is defensible only when the structural failure mode is legible independent of the quantitative figure — which is the case here (full Ph3 on a byte-stable manuscript is a definable structural error). The caveat is recorded in the CHANGELOG theme, in §12.10 of the portfolio-root CLAUDE.md, and in `docs/release-notes/`; INF3001H's first Ph3 round under v0.7.4 is the replication check. Lesson: when shipping fixes on n=1, make the caveat visible at every surface a reader might first encounter the change.
- **Authoritative-as-read beats re-adjudication.** P-5's I-SubAgent-1 invariant closes a latent failure mode: when a dispatching agent re-adjudicates a subagent's verdict, both costs are paid (the subagent ran + the dispatching agent re-ran the judgment), and the pipeline's integrity guarantee degrades to "whichever agent had the last word." Declaring subagent verdicts authoritative-as-read — logged by the dispatcher, not re-judged — preserves the adversarial-load allocation v0.7.3 established and makes subagent delegation economically legible.
- **Absent-means-null migration is the seventh-field equivalent of absent-means-inherit.** v0.7.1 used absent-means-false (SD/SR opt-in), v0.7.2 used absent-means-passes (Check 8 verdict), v0.7.3 used absent-means-inherit (model allocation). v0.7.4 extends the pattern to the new 7th log-row field: `model_used` is null on all pre-v0.7.4 rows, and Reflector Phase 2f suppresses `R-Refl-MA-5` on those rows to avoid a retroactive finding cloud. The family of absent-means-* migration semantics is now a package-level pattern — five consecutive releases have used it.

### Migration

- **Two-pass migration script.** Run in order: `python scripts/migrate_v073_to_v074_tier_to_phase.py --project-root <project>` (Pass 1, structural rename) then `python scripts/migrate_convergence_log_v074.py --project-root <project>` (Pass 2, convergence-log split). Both scripts are idempotent and re-emit their reports on re-run.
- **User sign-off.** After reviewing both `reviews/migration_report_v073_to_v074.md` and `reviews/migration_report_convergence_log_v074.md`, append `user_confirmed_migration_report_at: <ISO timestamp>` to `reviews/classification.md` frontmatter to clear the Planner's Phase-0 hold.
- **Dual-read path through v0.7.4 minor.** `phase_state_validate.py` accepts legacy `tier_state.json` with a `DEPRECATION_WARNING`; `TIER_PROTOCOL.md` remains readable as a symlink or deprecated-banner copy; `run-tier-{1..4}` skills forward to the phase-named skills with a `DEPRECATION_WARNING`. All three deprecated surfaces are **removed at v0.7.5 RC**.
- **Absent-means-null for `model_used`.** Pre-v0.7.4 log rows migrated by Pass 1 carry `model_used: null`. Reflector Phase 2f suppresses `R-Refl-MA-5` (MINOR) for rows dated before the v0.7.4 release to avoid a retroactive finding cloud; `R-Refl-MA-4` (MAJOR) also treats null as "no claim" rather than "mismatch."
- **Forward compatibility.** No v0.7.5 rename is currently planned — the phase surface is stable. The v0.7.5 RC removes the three dual-read deprecations (legacy ledger filename, legacy protocol filename, legacy skill names) but does not introduce new renames.

---

## v0.7.3 — 2026-04-21

**Theme.** Tier-conditioned model allocation. v0.7.2 closed the Reader-Experience defence gap but left one load-bearing decision implicit: *which Claude model each agent runs on at each tier*. Under the four-agent contract the Planner is the dispatcher, the Evaluator is the adversarial reviewer, the Generator is the sole writer, and the Reflector is the cross-round audit — but if all four agents ran on the same model, the pipeline's integrity guarantee degraded from adversarial to cosmetic whenever the model in play was not sized to the adversarial slot. v0.7.3 makes model capability a tier-conditioned dispatch decision resolved by the Planner at every invocation from a new reference file, `references/MODEL_ALLOCATION.md`. The allocation follows the AORE principle that capability must track *adversarial load*, not paragraph volume: the non-negotiable Opus 4.7 floor sits at **Evaluator-T2, Evaluator-T3, Evaluator-T4, and Reflector-full-T4** — the four slots where weak capability is the fatal failure mode. Every other slot downshifts to Sonnet 4.6, with Haiku 4.5 placed at Reflector-lightweight on a 30-day pilot. The Planner refuses any round that would place the Evaluator below the Generator on the family ordering `{Haiku 4.5} ≺ {Sonnet 4.6} ≺ {Opus 4.7}` with `E-MA-CAPABILITY-INVERSION`. Absent-means-inherit migration — existing projects pick up the default allocation at first Planner invocation under v0.7.3; no migration script.

### Changes

#### New reference (one)

- **`references/MODEL_ALLOCATION.md`** (new at v0.7.3). Single source of truth for the per-tier × per-agent Claude-model mapping. §2 holds the allocation table; §3 names the four-slot non-negotiable Opus 4.7 floor; §4 records the three downshifts from the naive role-seniority baseline (Generator-T1, Generator-T4, Planner-T4); §5 names the two live hazards (H-MA-1 capability inversion, H-MA-2 Reflector-floor pilot); §6 documents the absent-means-inherit migration semantics; §7 extends the Reflector Phase 2f audit with three new model-selection invariants (I-MA-1/2/3); §8 records Opus 4.6 deprecation and forward compatibility to the Ph1–Ph4 rename at v0.7.4.

#### Planner dispatch logic

- **`agents/planner.md` §What-you-read.** `MODEL_ALLOCATION.md` added to the package-always-read list.
- **`agents/planner.md` Phase 4.5 (new).** Model-dispatch resolution inserted between the revision-plan phase and the present-and-dispatch phase. Three-step procedure: (a) read `MODEL_ALLOCATION.md`, (b) resolve per dispatched agent with directive-override support, (c) check capability-inversion invariant.
- **`agents/planner.md` Planner-specific rules.** New rule binding the Planner to `MODEL_ALLOCATION.md` as the sole source of truth for model selection; recording the dispatch in `tier_state.json log[].notes` as `model_dispatch:{agent}:={model}`; refusing capability inversion and deprecated-model requests.

#### Contract invariants (four new)

- **`references/AGENT_CONTRACTS.md` §1 Planner.** New invariant **I-Planner-5** — Planner-resolved model dispatch from `MODEL_ALLOCATION.md §2`; capability-inversion refusal; no authority for agent-frontmatter `model:` fields.
- **`references/AGENT_CONTRACTS.md` §2 Evaluator.** New invariant **I-Eval-6** — runs on the Planner-dispatched model; dormant-at-T1 invariant (`E-MA-DORMANT-ACTOR-ENGAGED`).
- **`references/AGENT_CONTRACTS.md` §3 Generator.** New invariant **I-Gen-6** — runs on the Planner-dispatched model; T4 Generator is fix-only-no-new-prose under Sonnet 4.6.
- **`references/AGENT_CONTRACTS.md` §4 Reflector.** New invariant **I-Refl-6** — Haiku 4.5 lightweight (30-day pilot), Opus 4.7 full; Phase 2f extended to audit model-selection consistency; `model_dispatch_audit` telemetry block on every run.

#### Contract-verification extensions

- **`references/AGENT_CONTRACTS.md` §6 table.** Three new audit rows: model-dispatch match against `MODEL_ALLOCATION.md §2`; capability-inversion detection across the round; model-override provenance against `research_notes/directives.md`.

#### Orchestration overlay

- **`references/AGENT_ORCHESTRATION.md` §3.0.** New model-capability overlay table mirroring `MODEL_ALLOCATION.md §2` for orientation. Authoritative source remains `MODEL_ALLOCATION.md`.
- **`references/AGENT_ORCHESTRATION.md` §5 Via the Agent tool.** Agent tool invocation example extended with the `model` parameter; capability-inversion refusal documented; audit-trail contract documented.
- **`references/AGENT_ORCHESTRATION.md` §1 The Four Agents.** New Planner-scope clarification paragraph naming the seven orchestration responsibilities the role has accumulated since v0.5.x (classification; revision planning; dispatch; sole-writer state authority on `tier_state.json`; model-capability arbitration; MCR admission; user-checkpoint gating); documents the deliberate non-split into a fifth "Maestro" agent (orchestration co-locates with state authority on a single dispatcher; Reflector Phase 2f is the cross-cutting harmonization audit a separate orchestrator would otherwise duplicate); flags v0.7.4 rename consideration to `Director` or `Conductor` alongside the Tier → Phase rename.

#### Plugin manifest

- **`.claude-plugin/plugin.json`.** Version bumped `0.7.2 → 0.7.3`. Description extended to mention tier-conditioned Planner-dispatched model allocation. Keywords gain `model-allocation` and `tier-conditioned-dispatch`.

#### Portfolio-root CLAUDE.md (Ph.D. Research)

- **§12.9 (new).** Three-paragraph subsection documenting the tier-conditioned model allocation, the capability-inversion invariant, and the absent-means-inherit migration semantics. No change to Hard Constraints; no change to §13 accessibility gate.

### Lessons

- **Capability inversion is the silent failure mode of a multi-agent pipeline.** A pipeline in which every agent runs on the same model can still feel "done" at round close even when the Evaluator is too weak to catch a class of findings the Generator could produce under a stronger model. The fix is not "run everything on the strongest model" (which discards the cost-efficiency that makes Sonnet the right choice at Generator-T1 drafting) but *tie capability to adversarial load at every dispatch*. The v0.7.3 four-slot floor is the smallest set that preserves the integrity guarantee; downshifting any one of those four would put the pipeline back in the failure mode.
- **Dispatch policy belongs to the dispatcher, not to the dispatched.** The first draft of v0.7.3 considered per-agent frontmatter `model:` fields — each `agents/*.md` naming its own default. That approach looks local but fails the tier-dimension: the Evaluator at T2/T3/T4 should be Opus, the Evaluator at T1 is dormant, and frontmatter cannot vary per tier without duplicate agent definitions. Putting the policy in the Planner's dispatch logic, read from `MODEL_ALLOCATION.md`, lets the same agent file serve all tiers. Lesson: when a dispatch decision has a free dimension the dispatched agent does not know about, the decision belongs to the dispatcher.
- **Absent-means-inherit beats mandatory migration.** v0.7.1 (SD/SR opt-in) and v0.7.2 (Check 8 verdict) both used absent-means-default migration semantics and shipped without a script. v0.7.3 continues the pattern: projects with no `model_dispatch` notes inherit §2 unconditionally. The principle is working — incremental v0.7.x upgrades that add orthogonal capability do not force migration pain on projects that did not ask for the new feature.
- **The dispatcher is already the conductor — naming is not architecture.** v0.7.3's explicit capability-arbitration authority (Planner reads `MODEL_ALLOCATION.md` at every dispatch) surfaced a latent question: should the package add a fifth "Maestro" agent to orchestrate the other four? On inspection, the Planner had, over v0.5.x → v0.7.3, absorbed seven orchestration responsibilities no single label captures — classification, revision planning, dispatch, sole-writer state authority, capability arbitration, MCR admission, and user-checkpoint gating. The right fix was documentation, not decomposition: a fifth agent would duplicate state authority (the Planner's sole-writer invariant on `tier_state.json`), add a round-trip hop with no added judgment, and cannibalize the Reflector's Phase 2f cross-cutting audit. The Planner-as-Conductor paragraph in `AGENT_ORCHESTRATION.md §1` is the documentation fix; a rename to `Director` (or `Conductor`) is queued for v0.7.4 alongside the Tier → Phase rename. Lesson: when an orchestration concern surfaces as a "should we add an agent" question, check whether the existing role already carries the responsibility under an outgrown name before reaching for decomposition.

### Migration

- **Absent-means-inherit migration semantics.** Projects that predate v0.7.3 have no `model_dispatch` marker in `reviews/tier_state.json` and no model-selection directives in `research_notes/directives.md`. At first Planner invocation under v0.7.3, the allocation in `MODEL_ALLOCATION.md §2` is inherited unconditionally; no migration script is required.
- **Directive opt-out preserved.** Projects may declare per-slot overrides in `research_notes/directives.md` via `D-NN: Model dispatch override — {agent}-{tier} := {model}` entries. Overrides are validated against the capability-inversion invariant at dispatch; orphan overrides (no active directive) are flagged by the Reflector Phase 2f audit with `R-Refl-MA-3`.
- **Deprecated Opus 4.6.** Any directive that hard-codes `claude-opus-4-6` fails the resolution with `E-MA-DEPRECATED-MODEL`; the Planner prompts the user to choose Opus 4.7 (capability-equivalent forward) or Sonnet 4.6 (cost-efficient alternative).
- **Forward compatibility to v0.7.4.** The tier identifiers in `MODEL_ALLOCATION.md §2` will rename T1 → Ph1, T2 → Ph2, T3 → Ph3, T4 → Ph4 as part of the v0.7.4 Tier → Phase rename. Model assignments carry forward unchanged; the v0.7.4 migration script will rewrite identifiers only.

---

## v0.7.2 — 2026-04-20

**Theme.** The Reader-Experience defence. v0.7.1 preserved the four-agent contract and the lifecycle-stage ladder but left the `SAFEGUARD_LAYER.md` layer at six Checks, while `agents/evaluator.md` and `skills/run-tier-3/SKILL.md` referenced *eight* — a load-bearing contract bug where the referenced Checks 7 and 8 did not exist, and `DETERMINISTIC_CHECKS §9b` pre-filter fed a "Check 8 work queue" that had no judgment layer. v0.7.2 closes the gap. Check 7 (Inter-Sentential Logical Connective Audit) and Check 8 (Reader-Experience / Prose Architecture Audit) are now authored in `SAFEGUARD_LAYER.md`; Check 8 operationalises the six reader-accessibility criteria of Ph.D.-root CLAUDE.md §13.3 (paragraph cadence, sentence-length distribution, first-use definition, section-transition signposting, jargon discipline, worked examples at density spikes) and is wired into the T3 Iterate & Converge convergence gate as the **Reader-Experience defence** (`TIER_PROTOCOL.md §3.3.3`). A Check 8 BLOCKER at T3 terminal signoff refuses the TerminalSignoffRow write with `E-T3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF` (trigger 28, `t3_accessibility_blocker_surfaced`); a BORDERLINE verdict permits signoff with the `[CONVERGENCE-BORDERLINE-ACCESSIBILITY]` advisory recorded for Reflector Phase 2g recurrence accounting. The new skill `accessibility-overlay` is the judgment layer that produces Check 8 findings; `DETERMINISTIC_CHECKS §9b` is extended with three new pre-filter patterns feeding Sub-checks A, D, and E. The Reflector gains **Phase 2g** (accessibility recurrence audit) at Reflector-full close-out, executing the §13.4 mandate of the Ph.D.-root CLAUDE.md. STYLE_COMMITMENTS.md gains commitment **C-5** — the one commitment that cannot be suspended via the §4 relaxation procedure.

### Changes

#### New SAFEGUARD checks (two)

- **Check 7 — Inter-Sentential Logical Connective Audit.** Consumes the `DETERMINISTIC_CHECKS §9a` pre-filter. Judges attributional inversion, template invocation, descriptive-to-normative jumps, and Following-X pivots. Severity floors vary per pattern; highest-severity pattern is BLOCKER (attributional inversion on a load-bearing claim). Full specification in `SAFEGUARD_LAYER.md`.
- **Check 8 — Reader-Experience / Prose Architecture Audit.** Six Sub-checks A–F operationalising Ph.D.-root CLAUDE.md §13.3. Aggregation rule: single MAJOR = BORDERLINE; two MAJORs = MAJOR aggregate; any BLOCKER = BLOCKER aggregate. Runs at T2 (subset with T2 severity floor), T3 (full severity, gates TerminalSignoffRow via §3.3.3), and T4 (full severity). Full specification in `SAFEGUARD_LAYER.md` and `skills/accessibility-overlay/SKILL.md`.

#### Convergence-gate wiring

- **`TIER_PROTOCOL.md §3.3.3` (new subsection).** The Check 8 accessibility convergence gate: gate trigger, gate scope (BLOCKER blocks, MAJOR produces BORDERLINE advisory, MINOR no effect), clearance mechanism, iteration accounting (refused write does not consume budget), logging (trigger `t3_accessibility_blocker_surfaced`), independence from line-diff stability.
- **`tier_state_schema.md` trigger enum.** Extended from 27 to 28. New trigger 28 `t3_accessibility_blocker_surfaced` records each Planner refusal.
- **`tier_state_schema.md §6.1` failure codes.** New code `E-T3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF` with recovery procedure.
- **`tier_state_schema.md §6.2` pre-advance check.** Extended from seven-clause to eight-clause guardrail; clause (h) is the Check 8 accessibility gate, binding only on TerminalSignoffRow writes at T3.
- **`agents/planner.md` terminal-row handling.** Planner now reads the Check 8 aggregate verdict from `reviews/safeguard_layer_results.md` before accepting a TerminalSignoffRow write; refuses on BLOCKER; logs the refused write; permits on CLEAN or BORDERLINE with advisory recorded.
- **`tier_notifications.yaml`.** New advisory surfaces `[CONVERGENCE-BLOCKED-ACCESSIBILITY]` and `[CONVERGENCE-BORDERLINE-ACCESSIBILITY]`; 28-trigger enum reflected; trigger 28 notification rendered under `t3_loop`.

#### Pre-filter extensions

- **`DETERMINISTIC_CHECKS §9b`.** Three new pre-filter patterns feed Check 8 Sub-checks A, D, and E: paragraph cadence (turn-point absence in paragraphs >150 words), section-transition preamble absence (missing orienting or contribution clauses), jargon density per paragraph (P-stage-scaled cap).

#### New skill (one)

- **`skills/accessibility-overlay/`** (new at v0.7.2). Reusable overlay that converts a section's prose into a structured Check 8 findings report consumable by the Evaluator at T2, T3, and T4. Six finding classes (Cadence-Flag, Rhythm-Flag, First-Use-Flag, Signpost-Flag, Jargon-Density-Flag, Worked-Example-Flag) with severity floors matched to the SAFEGUARD_LAYER Check 8 aggregation rule. Mirrors the structural precedent of `skills/graph-grounding-overlay` (Coupling E.2).

#### T2 SAFEGUARD subset extension

- **`agents/evaluator.md §Step 8.5` + `agents/evaluator.md §T2` + `skills/run-tier-2/SKILL.md` §4.** T2 SAFEGUARD subset extended from checks 1, 4, 5 to checks 1, 4, 5, and 8. Check 8 at T2 is advisory on T2 admission but carries forward to T3 where it binds the §3.3.3 gate; BLOCKER-CANDIDATE tags on Sub-checks A, D, F at T2 avoid terminal emission while still surfacing the candidate.

#### Reflector Phase 2g (net-new)

- **`agents/reflector.md §Phase 2g` (Reflector-full only).** Accessibility recurrence audit: within-project consecutive-round recurrence becomes a project-scoped lesson candidate; cross-project recurrence becomes a package-tier plugin-update proposal (`A5-accessibility-recurrence`, routed through the Planner's three-filter gatekeeper); BORDERLINE-permitted signoff audit and BLOCKER clearance-cost distribution surface accumulated accessibility debt. Fulfils Ph.D.-root CLAUDE.md §13.4. Reflection report template gains a new §10e subsection.

#### Style-commitment extension (one)

- **`STYLE_COMMITMENTS.md` commitment C-5.** Reader-accessibility meta-rule operationalising C-1…C-4. The one commitment that cannot be suspended via the §4 relaxation procedure — inherits the binding force of Ph.D.-root CLAUDE.md §9. Project-scoped severity-floor overrides permitted via `directives.md`; wholesale disable not permitted.
- **`MASTER_research_and_paper_guidelines.md §A.1`.** New bullet point: the Reader-accessibility constraint, binding at all P-stages, cross-referenced to C-5 / Check 8 / accessibility-overlay / Ph.D.-root Hard Constraint #8.
- **`research_paper_writing_guidelines.md §1`.** New bullet point stating C-5 succinctly with the six Sub-checks and the §3.3.3 gate behaviour.

### Lessons

- **A contract referenced in three places must exist at the third place.** v0.7.1 shipped `agents/evaluator.md §Step 8.5` and `skills/run-tier-3/SKILL.md §5` both saying "all eight checks," but `SAFEGUARD_LAYER.md` contained only six. The `DETERMINISTIC_CHECKS §9b` pre-filter fed a "Check 8 work queue" that had no consumer. Lesson: when extending a referenced count ("all N checks"), grep for every use of the count string and the referenced item across the whole package before shipping. The Reflector's Phase 2f tier-row contract audit is the template; apply it to cross-file contracts, not only to ledger rows.
- **Accessibility is extraneous-load reduction, not intrinsic-load collapse.** The six Sub-checks A–F enforce prose surface properties (cadence, rhythm, definition, signposting, jargon density, worked examples); they do not enforce a reading-level ceiling or a grade-level proxy. Ph.D.-register argument in sentences averaging 28 words with high variance and clean first-use definitions is compliant; the same argument in 240-word paragraphs with nested parentheticals and undefined neologisms is not. The distinction is binding and is recorded in commitment C-5, Hard Constraint #8, and this CHANGELOG so future rounds do not re-open it.
- **Gate wiring costs more than check authoring.** Writing Check 7 and Check 8 in SAFEGUARD_LAYER.md was a single file edit. Wiring Check 8 into the T3 convergence gate required edits to TIER_PROTOCOL.md §3.3.3, tier_state_schema.md trigger enum + §6.1 + §6.2, tier_notifications.yaml, agents/planner.md, skills/run-tier-3/SKILL.md, and agents/evaluator.md — six files for one gate. Lesson: treat any gate that couples to the TerminalSignoffRow or MCR as a cross-cutting change; plan the wiring sequence before the first edit.

### Migration

- **Absent-means-passes migration semantics.** v0.7.1 projects with no `reviews/safeguard_check8_*.md` artefacts will see the Planner's §3.3.3 gate treat the Check 8 verdict as CLEAN (absent-means-passes). This is the conservative default: the gate does not refuse signoff on projects that never ran Check 8. The first time the Evaluator runs Check 8 (via the accessibility-overlay skill or directly under Step 8.5), the gate becomes binding on subsequent signoff attempts. No migration script required.
- **27→28 trigger enum.** Existing `tier_state.json` files remain valid; the new trigger 28 appears only on newly written rows. Trigger enum validators accept both the v0.7.1 27-value set and the v0.7.2 28-value set.
- **Evaluator contract change at T2.** Projects mid-round at T2 when v0.7.2 lands will see Check 8 enter the T2 SAFEGUARD subset on the next Evaluator dispatch; no ledger action required.

---

## v0.7.1 — 2026-04-20

**Theme.** Scope-respecting SD/SR. v0.7.0 treated the Strategic Dependency / Strategic Rationale (i\*) artefacts as an unconditional T1 authoring obligation and a T2 read-prerequisite, which made sense for GORE/AORE-native projects but silently imposed goal-modelling work on every manuscript — including ones where the user never asked for i\* modelling. v0.7.1 makes SD/SR authoring **opt-in at the package level** via a new `sd_sr_required` field in `reviews/classification.md` (default `false`). The field is read by the Planner, Evaluator, Generator, and the `pre_tier_advance_check.py` Cold-Start defence; when absent or `false`, SD/SR authoring is out of scope at T1, SD/SR read-prerequisites are skipped at T2 entry, and the `E-T2-SD-UNGROUNDABLE` and `E-IMODEL-STRUCTURALLY-INCOMPLETE` failure codes do not emit. Absent-means-false migration semantics — existing v0.7.0 projects continue to work unchanged without a migration script.

### Changes

#### Scope gate (one)

- **`sd_sr_required` flag in `reviews/classification.md`.** Canonical specification at `references/TIER_PROTOCOL.md §3.1.2`. Default `false`; set `true` only when the user explicitly requests i\* Strategic Dependency / Strategic Rationale modelling within the assigned project scope. Resolved by the Planner at T1 dispatch and by `pre_tier_advance_check.check_clause_e` at T2 admission via `_resolve_sd_sr_required(project_root)`.

#### Conditionalized surfaces

- **T1 SD/SR authoring** (`skills/run-tier-1/SKILL.md`, `agents/planner.md`, `references/TIER_PROTOCOL.md §2.2 + §3.1 + §3.1.1`, `references/AGENT_ORCHESTRATION.md §3.0 + §10.1 + §10.2`). When `sd_sr_required: false`, the Planner does not author `reviews/sd_model.md` or `reviews/sr_model.md`, does not run the §3.1.1 structural-completeness validator, and does not emit the `imodel_structural_validation_signed` trigger.
- **T2 SD/SR read-prerequisite** (`skills/run-tier-2/SKILL.md`, `agents/evaluator.md`, `references/TIER_PROTOCOL.md §3.2 + §5.3`, `references/REVIEW_ORCHESTRATION.md §3.3`, `references/SKILL_REGISTRY.md SK-29`, `references/TIER_PROTOCOL_SR.mermaid`). When `sd_sr_required: false`, the Evaluator does not open the SD/SR models before prose reads, `E-T2-SD-UNGROUNDABLE` does not emit, and the T2 scope budget excludes the SD/SR read.
- **Generator goal-model reads** (`agents/generator.md`). When `sd_sr_required: false`, goal-model-artefact reads are out of scope for the Generator at T1 and T2.
- **Cold-Start defence** (`scripts/pre_tier_advance_check.py check_clause_e`). Opens a new helper `_resolve_sd_sr_required(project_root)` that parses `reviews/classification.md` and returns `False` when the flag is absent. `check_clause_e` early-returns when the helper returns `False`, so `E-IMODEL-STRUCTURALLY-INCOMPLETE` no longer fires on opt-out projects.
- **Canonical T1 tier goal** (`references/tier_state_schema.md`, `scripts/migrate_v060_to_v070.py TIER_GOAL_TABLE["T1"]`). v0.7.1 canonical T1 goal is `"produce a complete first draft with classification and an advisory Evaluator note"`; projects that set `sd_sr_required: true` may append `" and i* SD/SR"` downstream.
- **Notifications catalogue** (`references/tier_notifications.yaml`). `imodel_validation_signed`, `imodel_structurally_incomplete`, and `t2_sd_ungroundable` now carry YAML comments annotating the opt-in gate and `log_detail` strings carry `(sd_sr_required=true)` markers.

#### Documentation

- **`references/TIER_PROTOCOL.md §3.1.2`** — net-new subsection "SD/SR opt-in gate (v0.7.1 — `sd_sr_required`)" documenting motivation, flag location, absent-means-false migration, all downstream gates affected, what remains unconditional, and change-of-mind semantics.
- **`skills/classify-manuscript/SKILL.md`** — classification template row for the new flag with a default-false recommendation; default-classification fallback now includes `sd_sr_required: false`.

### Lessons

- **Default assumptions about modelling scope bleed into every surface.** The v0.7.0 assumption that SD/SR authoring was universal was encoded in ~18 files. Moving from unconditional to opt-in required edits across `references/`, `agents/`, `skills/`, and `scripts/`. Lesson: when adding a new cross-cutting obligation, author the opt-in/opt-out gate in the same release — do not assume the default will stay correct.
- **Absent-means-false migration semantics are cheaper than a migration script.** Rather than requiring existing v0.7.0 projects to write `sd_sr_required: false` into their classification files, the Planner and pre-flight check treat *absent* as *false*. This makes the v0.7.0 → v0.7.1 upgrade zero-cost for the vast majority of projects.

---

## v0.7.0 — 2026-04-20

**Theme.** The Lifecycle-Stage Ladder. v0.6.0's Progressive Approval Staircase gave us a per-section ledger, monotonic advancement, and explicit rung semantics, but it framed T1–T4 as review *depth settings* rather than *project lifecycle stages*. In practice this produced three problems: drafting work was forced through a review-shaped dispatch, T3 "Verify" presupposed a single correct pass rather than the iterative convergence that the underlying work actually required, and the Evaluator's involvement at T1 Draft was either nominal or actively in the way of generative work. v0.7.0 reframes the ladder from **Progressive Approval Staircase** → **Lifecycle-Stage Ladder**: T1 Plan & Draft (M1 + M2 + M3 absorbed, Evaluator dormant, Generator-led), T2 Review & Revise (M4a absorbed, Evaluator joins with SD/SR read-prerequisites), T3 Iterate & Converge (M4b absorbed, unbounded iteration feeding `reviews/convergence_log.md`), T4 Finalize & Close (M5 absorbed, terminal with required G.4 sign-off). T3 is the center of gravity — it stays open until a terminal sign-off row flips `current_tier` to `T3_converged`. T4 admission is gated by the **Manuscript Convergence Report (MCR)**, the renamed-and-reframed successor to the Laggard Clearance Report. The Evaluator's Confirmation Mode, the Generator's Self-T1 Verdict (Phase 3.5), the EG-2 mismatch gate, the T3R sibling ladder, and Grounding Rule 1's tier-gated digest exception are retired. The Reflector gains a **lightweight/full dispatch split** and the Planner gains a **three-filter gatekeeper role** on plugin-update proposals.

### Changes

#### Architectural replacement (one)

- **The Lifecycle-Stage Ladder.** Four rungs corresponding to project lifecycle stages, not review-depth settings: T1 Plan & Draft (M1+M2+M3) → T2 Review & Revise (M4a) → T3 Iterate & Converge (M4b, unbounded) → T4 Finalize & Close (M5, terminal). Per-section ledger at `reviews/tier_state.json` with a **15-field `SectionStateObject`** (10 v0.6.0 fields + 5 new: `tier_goal_declared`, `tier_deliverable_path`, `convergence_metric`, `t1_pstage_declaration`, `t3_last_activity_at`). 27-trigger enum with `confirmation_failed` migrated read-only. Row-shape migrates from v0.6.0's `{from_tier, to_tier, scope, cycle_id, detail}` to v0.7.0's **six-field row** `{prev_tier, new_tier, trigger, actor, notes (≤280 chars), timestamp}` — `actor` is new and required; `notes` is the single free-form field replacing scope/cycle_id/detail. Canonical diagram at `references/TIER_PROTOCOL_SR.mermaid`.

#### Tier-conditioned agent engagement

- **Evaluator dormant at T1.** Drafting is Generator-led; no Evaluator review occurs until T2 entry. The retired v0.6.0 pattern of running the Evaluator at T1 with a narrow digest-based read is replaced by a clean hand-off: the Generator drafts and declares a P-stage; the Planner advances to T2 on user approval; the Evaluator starts reading at T2 with full-file floor.
- **Evaluator at T2 with SD/SR read-prerequisites.** The Evaluator's pre-entry reading list at T2 now includes the Strategic Dependency / Strategic Rationale (i\*) artefacts declared in `reviews/classification.md`. Missing artefacts fire the net-new `E-T2-SD-UNGROUNDABLE` finding class.
- **T3 unbounded iteration.** Each Evaluator–Generator cycle at T3 appends a `T3 Iteration <N>` block to `reviews/convergence_log.md` with the convergence metric target, BLOCKER/MAJOR/MINOR counts, top unresolved finding, advisory warnings, and Generator handoff. T3 stays open until a **terminal sign-off row** (`is_terminal: true`) flips `current_tier` → `T3_converged`. A **re-engagement sign-off row** refreshes `t3_last_activity_at` without flipping `current_tier`, clearing `[T3-STALE]` advisories.
- **T4 terminal with G.4 sign-off required.** Strict superset of T3. MCR admission required (§6), G.4 sign-off artefact required (§9), Reflector full-mode dispatch at close-out required (including new audit phases 2d/2e/2f).

#### Net-new audit phases in the Reflector

- **Phase 2d — T3 convergence trajectory audit.** Classifies each section's T3 history as Converged / Converged-with-reserve / Thrashed / Abandoned / No T3 history using iteration counts, BLOCKER trajectories, and advisory-warning frequency.
- **Phase 2e — `[T3-STALE]` catalog and MCR volatility count.** Computed purely from `t3_last_activity_at` vs. wall-clock now against a default `t3_staleness_budget=14 days`; advisory within T3, gating at MCR.
- **Phase 2f — tier-row contract audit.** Schema version check, six-field row shape check, 27-trigger enum check, monotonicity check with the three exemptions (retraction, EG-1 `eg1_t4_downgrade_to_t3`, EG-7 `eg7_mcr_readmission_after_class_change`), and ownership-transfer rationale check. The only phase that runs in both dispatch modes.

#### Reflector dispatch split

- **Lightweight mode** — T1/T2/T3 ad-hoc integrity probe. Phases 1, 2.5, 2.6, 2f, 3 (memory-only). No skill proposals, no plugin-update filings. Catches ledger-integrity drift mid-iteration without forcing a full close-out cycle.
- **Full mode** — T4 close-out only. All five phases plus the new audit phases 2d/2e/2f. Skill proposals and plugin-update proposals routed through the Planner's three-filter gate.

#### Planner gatekeeper role (net-new at v0.7.0)

- **Three-filter review** on `reviews/plugin_update_proposals.md` (net-new full-mode Reflector write artefact): (1) evidence-adequacy — does the proposal carry enough round-level evidence to justify a package change? (2) non-duplication — does it duplicate an existing skill or section? (3) tier-appropriateness — is the proposed tier (package / project / global) consistent with the observed pattern scope? The Reflector proposes raw; the Planner filters; the user decides.

#### Retired surfaces (v0.7.0 removals)

- **Evaluator Confirmation Mode** — retired at every rung. Full-file reads are the universal floor; diff-backed shortcut is no longer recognized.
- **Generator Self-T1 Verdict (Phase 3.5)** — retired. Drift measurement migrates into Phase 4 structured completion signal.
- **EG-2 (Self-T1 verdict mismatch gate)** — retired. No Verdict artefact to mismatch.
- **T3R sibling ladder** — retired. Response-letter review folds into T2 (mid-iteration) or T3 (resubmission-paired) as a manuscript-class on the main ladder.
- **Rule 1 tier-gated digest exception** — retired entirely. Single-code-path full-file grounding at every rung. `scripts/verify_rule_digest.py` archived.
- **Phase 3a digest integrity** — retired in lockstep with the digest exception.

#### Repurposed surfaces

- **EG-1** — now the T4→T3 grounding-demotion gate (monotonicity-exempt: `prev_tier: T4`, `new_tier: T3`, `trigger: eg1_t4_downgrade_to_t3`).
- **EG-6** — degraded to a non-blocking advisory warning (was: T2 promotion-ceiling gate).

#### Net-new gates

- **EG-7** — `eg7_mcr_readmission_after_class_change`. Fires when a classification change after MCR admission requires re-admission. Monotonicity-exempt.

#### Renames

- **Laggard Clearance Report (LCR)** → **Manuscript Convergence Report (MCR)**. Artefact path, schema fields, and Planner phase references renamed consistently across TIER_PROTOCOL.md, AGENT_ORCHESTRATION.md, REVIEW_ORCHESTRATION.md, tier_state_schema.md, SKILL_REGISTRY.md, and the four run-tier-N skills.
- **`T4_ready`** (staircase approval state) → **`T3_converged`** (ladder convergence state).
- **`laggard_clearance_approved`** flag → **`mcr_admission`**.
- **Row fields:** `from_tier` → `prev_tier`; `to_tier` → `new_tier`; `{scope, cycle_id, detail}` → `notes` (≤280 chars); new required `actor` field (`planner|evaluator|generator|reflector|user`).

#### Agent contract updates

- **`agents/planner.md`** — three-filter gatekeeper role on `reviews/plugin_update_proposals.md`; MCR authoring at T4 entry (renamed from LCR); sole-writer responsibility for `tier_state.json` retained; six-field row contract at `§8.2a`.
- **`agents/evaluator.md`** — T1 dormant, T2 SD/SR read-prerequisites, T3 unbounded iteration feeding `convergence_log.md`, T4 terminal with G.4 required. Confirmation Mode removed entirely. New `E-T2-SD-UNGROUNDABLE` finding class. New `reviews/findings/eg7_readmission_<date>.md` write artefact. v0.7.0 gate-set table (EG-1 repurposed, EG-2 retired, EG-6 warn-only, EG-7 net-new).
- **`agents/generator.md`** — Phase 3.5 retired; drift measurement migrates into Phase 4 structured completion signal. Tier-conditioned execution: T1 full drafting, T2/T3 fix-plus-targeted-prose, T4 fix-only-no-new-prose. EG-1 demotion cost note for T4 fabrications.
- **`agents/reflector.md`** — largest rewrite (~450 lines). Dispatch modes table at top; Phases 2d/2e/2f net-new; Phase 2b degraded to historical-only audit using new v0.7.0 row shape; Phase 3a retired in lockstep with digest exception; Phase 4 writes `reviews/plugin_update_proposals.md` (full-mode only) routed through Planner gatekeeper; Phase 5 template adds §10a/10b/10c/10d subsections with mode-conditioned sections.

#### Notification + orchestration

- **`references/tier_notifications.yaml`** `config_version` 2.0 → 3.0. MCR-renamed notifications; new `t3_staleness_warning` (advisory at 14 days). Retired: `laggard_clearance_report_pending` (renamed), `confirmation_failed_prompt` (Confirmation Mode retired).
- **`references/AGENT_ORCHESTRATION.md §§3, 8.2a, 8.2b, 10`** — tier-conditioned engagement tables; six-field row contract at §8.2a; MCR references throughout.
- **`references/REVIEW_ORCHESTRATION.md`** — tier-table rewritten for the Lifecycle-Stage Ladder; T3 unbounded iteration rules; MCR admission flow; T3R sibling ladder retirement notice.
- **`references/SKILL_REGISTRY.md`** — v0.7.0 retirement banner added; SK-11, SK-23, SK-25, SK-26, SK-27, SK-29 rewritten in place; SK-06 updated for Reflector lightweight/full split; SK-28 `eygp-framework-checker` retired per release-gate WARN (R5); Orchestration Commands section updated for MCR / Lifecycle-Stage Ladder vocabulary.
- **`references/GROUNDING_PROTOCOL.md`** — digest-exception subsection replaced with v0.7.0 retirement notice; migration guidance for citations valid under contemporaneous protocol; forward-compatibility clause requiring explicit protocol amendment to re-introduce any digest path.

#### Release-gate wiring

- **`scripts/release-gate.sh` Phase 0.67** now runs `scripts/tier_state_validate.py` against v0.7.0 smoketest fixtures (15-field SectionStateObject, six-field row, 27-trigger enum, `T3_converged` state). v0.6.0 Phase 0.67 fixtures migrated under the one-way migrator; v0.6.0 fixtures retained as regression baseline.
- **`scripts/migrate_v060_to_v070.py`** — one-way migrator. Reads v0.6.0 `tier_state.json` (10-field rows, 12-trigger enum); writes v0.7.0 `tier_state.json` atomically (lockfile + `.tmp → rename`) and `reviews/migration_report_v060_to_v070.md`. `T4_ready` rows coerce to `T3_converged` with a `T4_READY_COERCED` warning; `laggard_clearance_approved` fields rename to `mcr_admission`; historical row shapes fold into `notes` preserving scope/cycle_id/detail in a canonical serialization.

### Breaking changes

- `plugin.json.version` → `0.7.0`; `description` rewritten.
- `references/tier_notifications.yaml` `config_version` 3.0 is not readable by v0.6.x loaders.
- `SectionStateObject` widens from 10 fields to 15 fields; consumers must read all 15.
- Row shape changes from five free-form fields to six structured fields; `actor` is required.
- `T4_ready` and `laggard_clearance_approved` are not legal values at v0.7.0; migrator coerces with warning.
- `verify_rule_digest.py` archived; any tooling that invoked it must stop. Full-file reads are the universal floor.
- `/review-letter` no longer dispatches the T3R sibling ladder; it classifies the letter into T2 or T3 on the main ladder.

### Migration

One-way. Rollback requires the preserved `research-writing-harness-claude-v0.6.0/` tree.

```bash
# 1. Dry-run (no writes); inspect warnings and coerced rows.
python3 scripts/migrate_v060_to_v070.py --project-root <project> --dry-run

# 2. Real run.
python3 scripts/migrate_v060_to_v070.py --project-root <project>

# 3. Validator must exit 0 before the Planner will dispatch.
python3 scripts/tier_state_validate.py <project>/reviews/tier_state.json
```

The Planner refuses `/review` until the user appends `user_confirmed_migration_report_at: <ISO-8601>` to `reviews/classification.md`.

### Lessons recorded

- **Lifecycle stages beat review depths.** The v0.6.0 Staircase framed T1–T4 as depth settings; projects read them as lifecycle stages anyway. The v0.7.0 rename resolves the framing mismatch at source.
- **T3 is the center of gravity, not T4.** Convergence is the hard problem; sign-off is the ceremony. v0.7.0 makes T3 the unbounded iteration rung and T4 the thin terminal rung.
- **Single code path beats tiered exceptions.** The Rule 1 tier-gated digest exception produced more audit surface than it saved. Full-file reads at every rung is simpler, cheaper to audit, and harder to degrade.
- **Reflector needs two modes.** Mid-iteration integrity probes and close-out five-phase runs have different cadence and different outputs; collapsing them into one mode forced either-too-heavy or too-light behavior.
- **Proposals need a gatekeeper.** Reflector-proposed package changes bypassing the Planner produced duplicate and scope-mismatched skills. The three-filter gate restores editorial discipline.

---

## v0.6.0 — 2026-04-19

**Theme.** The Progressive Approval Staircase. v0.5.5's Phase F.1 Tier Marshal shipped an orchestrator-over-the-tier-ladder because the v0.5.x Incremental Tier Protocol's invariants were enforced distributively across four agents and kept drifting apart in practice. v0.6.0 removes the drift at the source: replace the six-mode ladder and whole-manuscript `tier:` field with a **four-rung Progressive Approval Staircase** (T1 Draft → T2 Review → T3 Verify → T4 Ship) and a **per-section ledger** (`reviews/tier_state.json`). Monotonicity becomes an invariant at the data layer; retraction is the sole documented downward transition. Most of the Marshal's 24 predicates become architecturally impossible to violate. The Marshal is retired to `legacy/marshal-f1-retired/`; its residual obligations (classification exists, rule digest is in parity, override enum is legal) absorb into **Planner Phase 0 bootstrap** + **Evaluator entry/closeout checks**. Grounding Rule 1's tier-gated digest exception narrows from `{T1, T2}` to `{T1}` only: the Evaluator joins at T2, and full-file reads are mandatory the moment it does.

### Changes

#### Architectural replacement (one)

- **The Progressive Approval Staircase.** Four rungs (T1 Draft, T2 Review, T3 Verify, T4 Ship) + `T4_ready` marker tier + T3R response-letter sibling. Each rung runs review → plan → generate → human approval. Advancement is per-section; T4 admission requires every section at `T4_ready` with the **Laggard Clearance Report** (LCR, `references/TIER_PROTOCOL.md §7`) clear. The LCR includes a +50% iteration reserve per tier (NEW-H-7) and caps its climb target at `default_final_tier` (R-02). Canonical diagram at `references/TIER_PROTOCOL_SR.mermaid`.

#### Net-new artefacts (seven)

- **`reviews/tier_state.json`** — per-section ledger. Ten `SectionStateObject` fields + `tier_entry_log` array (12-trigger enum). Single writer = Planner. Canonical schema at `references/tier_state_schema.md §§2–4`; 17 failure codes at §6; migration contract at §7.
- **`scripts/tier_state_validate.py`** — read-only validator for all 17 failure codes. Exit codes map: 0 valid, 1 schema error, 2 consistency error, 3 version/migration gate, 4 bad invocation.
- **`scripts/tier_state_canonicalize.py`** — three-mode LaTeX canonicalizer (`strict` / `tolerant` / `off`) with sentinel-tagged carve/uncarve for `verbatim`, `lstlisting`, `minted`, and related opaque environments. Public API: `canonicalize()` and `fingerprint()`. Raises `CanonicalizationError` on unterminated verbatim spans.
- **`scripts/migrate_v055_to_v060.py`** — one-way migrator. Reads `reviews/classification.md`, `reviews/escalation_log.md`, and `reviews/tier_decisions_log.md` (v0.5.5); writes `reviews/tier_state.json` atomically (lockfile + `.tmp → rename`) and `reviews/migration_report_v055_to_v060.md` (three sections: Mapped rows / Warnings / User hold-point per `tier_state_schema.md §7.3`). Invokes `tier_state_validate.py` post-write and propagates exit 2 on failure. The Planner refuses `/review` until the user appends `user_confirmed_migration_report_at: <ISO-8601>` to the classification record.
- **`scripts/fixtures/tier_state_smoketest/{pass,block}/reviews/tier_state.json`** — release-gate smoketest fixtures. PASS asserts exit 0; BLOCK asserts exit 2 (`MONOTONICITY_VIOLATION`).
- **Four rung-explicit skills:** `run-tier-1` (renamed from `run-tier-reflex`, body rewritten), `run-tier-2` (net-new), `run-tier-3` (renamed from `run-tier-standard`, body rewritten), `run-tier-4` (renamed from `run-tier-submission`, body rewritten).
- **`references/TIER_PROTOCOL_SR.mermaid`** — i\*-style Strategic Rationale diagram of the staircase and the LCR admission gate.

#### Retirements (six categories)

- **T0 state-probe** — merged into Planner Phase 0 bootstrap. T0 seeds in `default_final_tier` are coerced to T3 at migration time with a `T0_DEFAULT_COERCED` warning.
- **Phase 5.5 Tier Close-Out** (Down / Stay / Up / Done election) — advancement is now binary user Approve/Reject per section.
- **The asymmetric-Down ratchet** (`ascent_observed` array) — monotonicity removes its referent.
- **`reviews/tier_decisions_log.md`** with the `choice` column — superseded by `tier_state.json`'s `tier_entry_log`, which widens from user-election-only to every state transition.
- **`reviews/tier_closeout_<round>_<date>.md`** benefit-delta artefact — no referent under the staircase.
- **The fifth agent — Tier Marshal** — retired whole. Archived intact at `legacy/marshal-f1-retired/` (design doc, contract, predicates, preflight/postflight scripts, smoketest fixtures, migration helper `migrate_classification_to_tier.py`). `run-tier-reflex`, `run-tier-standard`, `run-tier-submission` slash commands removed.

#### Gate-semantics deltas

- **EG-2 (Self-T1 verdict mismatch)** relocates to **T2 entry** — T1 has no Evaluator. Prior-cycle `CLEAN` Self-T1 Verdicts shortcut into Evaluator Confirmation Mode at T2; otherwise T2 runs a full Evaluator local-scope pass.
- **EG-3 (Cross-scope reference mismatch)** redefined to fire when a T2 finding cites a `location:` outside the containing section.
- **Grounding Rule 1 tier-gated digest exception** narrows from `{T1, T2}` to `{T1}` only (`references/GROUNDING_PROTOCOL.md §Rule 1`).

#### Agent contract updates

- **`agents/planner.md`** — Phase 0 bootstrap expanded to absorb the retired Marshal's norm-compliance checks (classification exists, rule digest in parity, ledger parses); LCR authoring at T4 entry; sole-writer responsibility for `tier_state.json`.
- **`agents/evaluator.md`** — Confirmation Mode relocated to T2 entry; Step 8.5 tier-gated depth table refreshed; ledger reads at every dispatch.
- **`agents/reflector.md`** — Phase 2b (confirmation-failure rate) retained and widened to absorb Phase 2c's intent; Phase 2c (tier-decision drift audit) retired whole with inline retirement paragraph.

#### Notification + orchestration

- **`references/tier_notifications.yaml`** `config_version` 1.2 → 2.0. New integrity hold `migration_report_hold` (fires when the migration report exists but the user has not appended the confirmation line). Retired Marshal notifications removed.
- **`references/AGENT_ORCHESTRATION.md §§8.2a, 8.2b, 8.3`** — escalation log section revised; ledger section (§8.2b) net-new; Marshal retirement recorded at §8.3.
- **`references/REVIEW_ORCHESTRATION.md §3`** — tier-table rewritten for the four rungs and T3R sibling.
- **`references/SKILL_REGISTRY.md`** — swept for v0.6.0; SK-05 `run-full-review` alias retirement preserved as historical record.

#### Release-gate wiring

- **`scripts/release-gate.sh` Phase 0.67** now runs `scripts/tier_state_validate.py` against the v0.6.0 smoketest fixtures (PASS asserts exit 0; BLOCK asserts exit 2 for `MONOTONICITY_VIOLATION`). The v0.5.5 Phase 0.65 Marshal smoketest is removed wholesale. Phase 0.7 `py_compile` list updated: the three v0.6.0 scripts added, the four retired Marshal scripts removed.
- **`skills/plugin-commands/SKILL.md`** command table refreshed — the three retired commands removed, the four rung-explicit commands added with v0.6.0-accurate one-liners.

### Breaking changes

- `plugin.json.version` → `0.6.0`; `description` rewritten.
- `references/tier_notifications.yaml` `config_version` 2.0 is not readable by v0.5.x loaders.
- `classify-manuscript` frontmatter: `tier:` → `default_final_tier:`, legal values `{T1, T2, T3, T4}` (plus T3R sibling). T0 seeds coerced at migration with warning.
- The per-section ledger replaces the whole-manuscript `tier:` field. Any external tooling that consumed `classification.md:tier` must now read `tier_state.json:sections[i].current_tier` (or `default_final_tier` at the top level for the manuscript-wide aspiration).
- Monotonicity invariant enforced at the validator: consumers must treat `trigger: retraction` as the sole legal downward transition.
- `run-tier-reflex`, `run-tier-standard`, `run-tier-submission` removed. Use `run-tier-1/2/3/4`.

### Migration

One-way. Rollback requires the preserved `research-writing-harness-claude-v0.5.4/` tree.

```bash
# 1. Dry-run (no writes); inspect warnings and mapped rows.
python3 scripts/migrate_v055_to_v060.py --project-root <project> --dry-run

# 2. Real run.
python3 scripts/migrate_v055_to_v060.py --project-root <project>

# 3. Review reviews/migration_report_v055_to_v060.md.

# 4. Append the confirmation line to reviews/classification.md frontmatter:
#      user_confirmed_migration_report_at: 2026-04-19T00:00:00Z

# 5. Invoke /review; Planner Phase 0 clears the integrity hold.
```

Seven warning categories the migrator may raise: `T0_DEFAULT_COERCED`, `HEADING_PATH_DUPLICATE`, `MISSING_ARTEFACT`, `T4_REQUIRES_LCR`, `RETRACTION_LOSSY`, `CURRENT_TIER_FROM_LOG`, and `TRIGGER_MAPPING_HEURISTIC`. All are documented in `tier_state_schema.md §7.2` and in §2 of the generated migration report.

### Lessons

- **L-2026-04-19-30 — description-colon trap.** The skill-check gate parses SKILL.md frontmatter strictly; a `description:` string containing `current_tier: T4_ready` breaks the YAML load even when the inner colon is inside backticks. Prefer prose phrasing in descriptions, and move backticked literals to the body. *How to apply:* run `scripts/skill-check.py` locally after any frontmatter edit.
- **L-2026-04-19-31 — cross-reference probe.** Two stale forward-references (`TIER_PROTOCOL_ARCHITECTURAL_PLAN.md §8`, `PROJECT_BOOTSTRAP.md §2.10a`) persisted across four minor versions before being caught by `/tmp/xref_check.py`. *How to apply:* the probe is small enough to promote into `scripts/` as a release-gate phase in a follow-up; meanwhile, treat any doc rename as a reference-sweep trigger.
- **L-2026-04-19-32 — validator exit-code discipline.** `MONOTONICITY_VIOLATION` maps to exit 2 (consistency error), not exit 1 (schema error). Smoketests must assert the exact code the validator emits, not a generic non-zero. *How to apply:* when adding a new failure code, record its exit-code class in `references/tier_state_schema.md §6` *and* in any test fixture's README.
- **L-2026-04-19-33 — retraction-lossy is load-bearing.** v0.5.5 preserved approval history across retraction; v0.6.0's validator rejects `last_approved_tier > current_tier`. The migrator resolves by resetting `last_approved_tier` to match the new running tier and emits `RETRACTION_LOSSY` so the user sees the history loss. *How to apply:* do not attempt to preserve v0.5.5-style approval provenance in the v0.6.0 ledger — the validator will reject the round-trip.

### Architectural notes

- **Why retire the Marshal wholesale rather than port it.** The Marshal's authority lived in twenty-four predicates. Sixteen of them were invariants that the staircase + ledger now enforce at the data layer (monotonicity, per-section independence, single-writer ledger, T4_ready admission, `choice`-enum legality). Five of the remaining eight had no referent under the retired Phase 5.5 machinery (`ascent_observed`, `tier_closeout`, `Down`-legality, ratchet-header parse, `tier_entered_via` consistency). The final three (classification exists, rule digest in parity, override enum legal) are load-bearing but architecturally belong to Planner Phase 0 and Evaluator entry checks, not to a standalone fifth agent. A one-to-one port would have reintroduced the orchestrator layer that the data-layer invariants make redundant.
- **Why `T4_ready` is a tier-enum value rather than a section-level flag.** Modelling it as a flag would allow `current_tier: T4` + `ready_for_ship: false` — two fields that can drift. Modelling `T4_ready` as the enum value reachable via `user_approval` from T3, and `T4` as reachable only via the Planner's LCR-clearance transition, makes the state machine single-source. The validator enforces the transition (`T4_ready → T4` only under `trigger: laggard_clearance_approved`).
- **Why three fingerprint modes.** `strict` is for final-submission rounds where every character matters; `tolerant` is the default and handles the common LaTeX stability cases (`\%` variants, `$…$` vs `\(…\)`, whitespace inside displayed equations); `off` is for projects that are still being edited in prose form and where the fingerprint check would produce noise. The canonicalizer is co-located with the migration script so fingerprint calculation is identical between migration-time seeding and session-time validation.

---

## v0.5.5 — 2026-04-19

**Theme.** Phase F.1 Tier Marshal advisory rollout. v0.5.4's Tier Close-Out Protocol supplied the dual exit step the Incremental Tier Protocol had been missing, but an architectural asymmetry remained: the protocol's invariants — classification exists, rule digest is in parity, revision log is readable, the asymmetric-Down ratchet is respected, the tier-scoped artefact actually lands, the close-out carries a user election — were enforced distributively across the four agents with no single surface refusing to open or close a round when the invariants were violated. The user-facing evaluator review framed it as "the workflow needs an orchestrator who owns the tier ladder." v0.5.5 introduces the package's fifth agent — the **Tier Marshal** — as a hard-gate norm-compliance check bracketing every round. At F.1 the Marshal ships in advisory-only mode: predicates run, findings are recorded, BLOCK severities are downgraded to WARN so no active project is interrupted. At F.2 (v0.5.6) the BLOCK gate activates.

### Changes

#### Architectural additions (three)

- **New fifth agent — Tier Marshal.** Defined in `references/TIER_MARSHAL_CONTRACT.md` (declared §8.3 of the agent-orchestration spec, scoped as a standalone reference pending the F.2 paste into `AGENT_ORCHESTRATION.md`). The Marshal reads project state — classification record, rule digest, escalation log, decisions log, revision log, tier-closeout artefacts — and emits preflight/postflight reports with three-valued verdicts (PASS/WARN/BLOCK, exit codes 0/1/2). It writes only its own reports; it never edits the manuscript, never writes to the escalation log, never writes to the decisions log. Its authority is the predicates and a closed-enum override vocabulary: `[MARSHAL-OVERRIDE-{DIGEST-UNAVAILABLE|CLASSIFICATION-PENDING|USER-TIME-CRITICAL|EXPERIMENTAL-SKIP}]`. Operates under PARALLEL_CONDUCTOR §7 as a hard-gate norm-compliance check (no filesystem locks; correctness is the predicate, not the arbitration).
- **Preflight predicate battery P-1…P-13.** Thirteen predicates, each with severity and remediation, exercised against project state *before* the Planner opens a round: P-1 (classification exists), P-2 (`tier:` field present, not legacy `review_depth:`), P-3 (tier matches Planner request), P-4/P-5 (rule digest in parity, required at T1/T2), P-6 (revision log readable), P-7 (tier-decisions log readable, ratchet header parsable), P-8 (Down-legality via `ascent_observed`), P-9 (T2 scope envelope declared), P-10 (`manuscript/response_letter.md` present at T3R), P-11 (Class-1 verifier present at T4), P-12 (no prior round's postflight is BLOCK), P-13 (override enum legal). Full table at `research_notes/tier_marshal_design_v1.md §10.1`.
- **Postflight predicate battery Q-1…Q-11.** Eleven predicates exercised *after* Phase 5.5 and *before* Reflector dispatch: Q-1 (state-probe at T0), Q-2 (tier_closeout emitted), Q-3 (tier_closeout schema-valid per `references/tier_closeout_schema.md §3-4`), Q-4 (escalation log rows present for any gate the round fired), Q-5 (decisions-log row appended, with first-round exemption), Q-6 (tier-scoped artefact emitted — T1→patch_report, T2→local_findings, T3/T4→consolidated_findings_report, T3R→letter_findings), Q-7 (`tier_entered_via` consistent with the prior round's election), Q-8 (`ascent_observed` consistent with the election sequence), Q-9 (orphan findings WARN-only), Q-10 (G.4 sign-off at T4), Q-11 (manuscript-diff evidence present when the revision log claims edits). Full table at `research_notes/tier_marshal_design_v1.md §10.2`.

#### New artefacts (six)

- **`scripts/marshal_preflight.py`** — stdlib-only runner implementing P-1…P-13. CLI: `--project-root`, `--tier`, `--round`, `--date`, `--plugin-root`, `--advisory-only`. Emits `reviews/marshal_preflight_<round>.md` (human-readable) and `reviews/marshal_preflight_<round>.json` (machine-readable; schema-stable, `schema_version: 1`). Exit codes 0/1/2 = PASS/WARN/BLOCK; `--advisory-only` downgrades exit code 2 → 1 for F.1.
- **`scripts/marshal_postflight.py`** — mirrored runner for Q-1…Q-11. Same CLI and sidecar layout; reads tier-closeout schema to validate Q-3; reads escalation log and decisions log under the pipe-row format `scripts/gate_threshold_tuner.py` already parses (GAP-B2 at v0.5.3 aligned this for both producers and consumers).
- **`scripts/_marshal_common.py`** — shared helpers (`CheckResult`, `MarshalReport`, stdlib YAML-lite frontmatter parser, plugin-root resolver, rule-digest locator, override-tag classifier). No runtime dependencies; pure-stdlib.
- **`references/TIER_MARSHAL_CONTRACT.md`** — §8.3-scoped reference file. Carries the agent's I/O contract, the verdict grammar, the override protocol, the integration checklist, and the F.1/F.2 rollout phases. `AGENT_ORCHESTRATION.md §8.3` gets a one-paragraph forward-reference at v0.5.5; the full §8.3 paste lands at v0.5.6.
- **`references/tier_closeout_schema.md` — already shipped at v0.5.4**, now bound as the normative schema for Q-3 validation. No edits at v0.5.5; the dependency is codified in the postflight runner.
- **`research_notes/tier_marshal_design_v1.md`** — fourteen-section design spec. §1 requirements frame (GORE softgoals + i* SD/SR sketch), §2 agent taxonomy, §3 hard-gate vs coordinator analysis, §4 architectural placement, §5 I/O surface, §6 invariants as predicates, §7 verdict grammar, §8 override protocol, §9 artefact layout, §10 predicate tables (P-* / Q-*), §11 rollout phases F.0/F.1/F.2/F.3, §12 AORE per-agent contract, §13 integration checklist, §14 open questions.

#### New helper script (one)

- **`scripts/migrate_classification_to_tier.py`** — stdlib-only migration helper for active projects whose `reviews/classification.md` still carries the legacy `review_depth:` field (retired as a read-path at v0.5.1, retired fully in runtime prose at v0.5.3). Reads the project root, migrates `quick→T1`, `standard→T3`, `submission-bound→T4` into a new `tier:` field, preserves the original line as a commented reference under the new field, and writes a `.bak` backup. Idempotent (a second invocation is a no-op once `tier:` is present). The user runs this against local project roots outside the package — at F.1 a legacy `review_depth:` record triggers WARN in preflight (P-2); at F.2 it triggers BLOCK, so migration is the documented remediation path before v0.5.6.
- **Table-cell fallback (v0.5.5 late-add).** Some active classification records predate both the `tier:` field *and* the YAML-lite frontmatter convention — they carry the inputs in a prose markdown table of the form `| **Review depth** | \`standard\` | <reason> |`. The helper now detects this row form as a secondary source and prepends a minimal frontmatter block carrying the derived `tier:` without mutating the original table row. Defensive posture: the fallback fires only when exactly one such row is present; two or more rows trigger WARN ("refusing to guess which is authoritative") rather than a silent rewrite. Regex handles emphasis (`**`), backticks, case-insensitivity, and both `submission-bound` / `submission_bound` spellings. Discovered during the F.1 live-project smoketest against INF3006Y_AgencyDelegation (see `research_notes/marshal_f1_live_smoketest_2026-04-19.md`).

#### Notification additions (three keys)

- `references/tier_notifications.yaml` bumps `config_version` 1.1 → 1.2. A new top-level `marshal:` section carries three keys: `preflight_block` (fired at F.2 when preflight returns exit 2; at F.1 the message is suppressed by the advisory flag), `postflight_block` (same, for postflight), and `override_recorded` (fired on every `[MARSHAL-OVERRIDE-*]` tag read, in both F.1 and F.2). Placeholders `{{reason}}` and `{{remediation}}` render from the `CheckResult.remediation` field.

#### Release-gate wiring

- `scripts/release-gate.sh` Phase 0.65 now runs the Marshal smoketest against `scripts/fixtures/marshal_smoketest/` — two tiny fixtures (PASS and BLOCK) exercised through both preflight and postflight runners with `--advisory-only`. The gate asserts: (a) the PASS fixture returns exit 0; (b) the BLOCK fixture under `--advisory-only` returns exit 1 and the JSON sidecar carries at least one `severity: "block"` CheckResult; (c) both JSON sidecars parse and carry `schema_version: 1`. At F.2 the gate will re-run the BLOCK fixture without `--advisory-only` and assert exit 2. Phase 0.7 `py_compile` list grows to include the four new runners.

#### Integration surfaces (one)

- `references/AGENT_ORCHESTRATION.md §8.3` carries a forward-reference paragraph pointing to `TIER_MARSHAL_CONTRACT.md` as the authoritative §8.3 source until v0.5.6 pastes the contract inline. The forward reference keeps the orchestration spec's section numbering continuous (§8.1 Escalation Log, §8.2a Escalation Log Schema, §8.2b Tier Decisions Log, §8.3 Tier Marshal) without importing the full agent contract at F.1.

### Architectural notes

- **Hard-gate norm-compliance is the right shape for this agent.** The Marshal does not need filesystem locks or cross-project serialization to do its job — PARALLEL_CONDUCTOR §7 is explicit that correctness for norm-compliance agents lives in the predicates, not in arbitration. The Marshal's authority is that its predicates are deterministic, its verdict vocabulary is three-valued, and its override enum is closed. When a predicate fails at F.2, the round does not proceed; when the same predicate is overridden with a valid tag, the round proceeds and the override is recorded. The shape is simpler than a coordinator and more principled than an advisory-only hook.
- **Advisory-only F.1 is a deliberate deferred cost.** Shipping the Marshal directly with BLOCK active at v0.5.5 would surface preflight failures on every active project simultaneously (INF3006Y and INF3001H, at least, still carry legacy `review_depth:` classification records). F.1 ships the instrument in read-only mode so its verdicts are visible in Planner Phase 0 artefacts for at least one release cycle before they gate anything. Phase F.2 at v0.5.6 flips BLOCK active once the user has run the migration helper against active projects and confirmed no false-positive preflight BLOCKs remain. The two-phase rollout is itself a lesson from v0.5.0/v0.5.1 (Phase C turned gates on, Phase D tuned them — Phase F is the same pattern applied to an agent).
- **The Marshal complements SAFEGUARD Check 5 rather than duplicating it.** Check 5 (Edit Traceability) verifies that every manuscript edit traces to a finding; it operates on the revision log and the findings set. Marshal Q-2 verifies that every round closes on a tier_closeout artefact the user has signed; it operates on the tier-closeout and decisions-log surfaces. The two checks cover disjoint failure modes — Check 5 catches an edit not grounded in a finding, Q-2 catches a round that never reached a close-out election — and they execute at different phases (Evaluator Step 3 vs Marshal postflight). v0.5.5 documents the complementarity in `TIER_MARSHAL_CONTRACT.md §8.3.4` and in `SAFEGUARD_LAYER.md §Check 5 cross-refs`.
- **The Marshal is an agent, not a skill.** An earlier design proposed a `/run-marshal` slash command that a user would invoke explicitly. The proposal was rejected: the Marshal's job is to bracket every round, not to be invocable on demand. Its user-visible surface is (a) the Planner's Phase 0 dispatch of preflight, (b) the Planner's post-Phase-5.5 dispatch of postflight, and (c) the `marshal_preflight_<round>.md` / `marshal_postflight_<round>.md` artefacts that land under `reviews/`. No slash command ships at v0.5.5 or v0.5.6. The skill ledger remains unchanged at 24 live + 1 retired.

### Lessons learned

- **L-2026-04-19-20 — A protocol with seven gates and two user-facing phase checkpoints still needs a norm-compliance agent.** The Incremental Tier Protocol has well-specified entry (Phase 2.5 dispatch), well-specified exit (Phase 5.5 close-out), seven escalation gates, and four agents that each carry a piece of the invariant. But the invariants are distributively enforced: the classification record's presence is validated by the Planner, the rule digest's parity is validated by the Evaluator, the revision log's readability is validated by the Generator, the decisions log's consistency is validated by the Reflector at Phase 2c. No single surface refuses to open or close a round when an invariant is violated. A user-facing evaluator review framed this as "the workflow needs an orchestrator," and the correct response was a fifth hard-gate agent, not a coordinator that reorders the existing four. Filed against the Phase F plan. Severity: BLOCKER (closed at v0.5.5 in advisory mode; fully closed at v0.5.6).
- **L-2026-04-19-21 — Two-phase rollouts (advisory, then active) are the right shape for instrument additions with BLOCK semantics.** Phase C (v0.5.0) turned the six-tier ladder on with all seven gates active and the Reflector divergence audit at live severity; the release shipped with calibration signals firing on every reviewed manuscript because thresholds were set from design-time intuition, not from production evidence. Phase D (v0.5.1) added the `gate_threshold_tuner.py` harness to retune from accumulated logs. The Marshal follows the same shape but inverts the order: F.1 ships the instrument in advisory mode so the calibration evidence accumulates *before* BLOCK is active, and F.2 flips BLOCK with the benefit of one release of evidence. Filed against Phase F+ plan. Severity: MAJOR.
- **L-2026-04-19-22 — A helper script that rewrites user project files must be idempotent, stdlib-only, and backup-emitting.** `scripts/migrate_classification_to_tier.py` operates against the user's live project roots (INF3006Y, INF3001H), not against the package. The three disciplines the script enforces — idempotence (second run is a no-op), stdlib-only (no `pip install` for a migration), backup-emission (a `.bak` file the user can roll back from) — are the minimum shape for any harness script that touches user state. Filed as a reusable pattern for future helpers. Severity: MINOR.

---

## v0.5.4 — 2026-04-19

**Theme.** Phase E.1 user-gated completion release. v0.5.3 closed the internal-consistency gaps the v0.5.2 audit surfaced but left one architectural asymmetry untouched: every round in the Incremental Tier Protocol terminated by producing findings and dispatching the Reflector, with *no user checkpoint between the round's output and the decision of whether to continue, escalate, de-escalate, or stop*. The Planner's Phase 2.5 dispatch handled entry into a tier but the protocol had no dual exit step, so completion was either implicit ("we stopped because we ran out of findings") or user-driven outside the harness ("I just stopped asking"). v0.5.4 introduces a mandatory terminal phase — Planner Phase 5.5, the Tier Close-Out Protocol — that every T1-or-above round must pass through before the Reflector runs, emits a machine-readable benefit-delta artifact, and elicits a user election from **Down / Stay / Up / Done**. Completion becomes an explicit user speech-act rather than a silent runtime fallthrough, and the project's overall trajectory across rounds becomes a first-class auditable signal.

### Changes

#### Architectural additions (two)

- **New Planner Phase 5.5 — Tier Close-Out.** `agents/planner.md` gains a Phase 5.5 subsection placed *inside the round* (after Generator + Evaluator return, before Reflector dispatch), so the invariant "one round emits exactly one close-out" holds without the Reflector needing to observe its own input artefact. The phase has three steps: (a) Compute the deterministic benefit delta — BLOCKER/MAJOR/MINOR count changes, paragraphs touched, escalation gates fired this round, wall-clock — from the consolidated findings report and round-scoped revision log; (b) Emit `reviews/tier_closeout_<round>_<YYYY-MM-DD>.md` per the `references/tier_closeout_schema.md` template (frontmatter, delta block, ≤ 120-word Evaluator-authored narrative, close-out choice block) and present it to the user; (c) Route on the user's election — `Down` / `Stay` / `Up` / `Done` — appending the decision to `reviews/tier_decisions_log.md`. The phase is user-gating; the Planner never auto-elects.
- **New Reflector Phase 2c — Tier-decision drift audit.** `agents/reflector.md` gains Phase 2c between Phase 2b (Planner/Reflector divergence) and Phase 2.5 (grounding audit). It reads the session window of `reviews/tier_decisions_log.md` and computes three drift metrics: *systematic down-drift* (Down elections > 60% across ≥ 3 rounds with non-zero residual MAJORs), *premature completion* (3 consecutive `Done` elections carrying the `[DECLARED-COMPLETION-BELOW-TIER]` advisory), and *ratchet-suppression frequency* (Down offered / Down taken ratio ≥ 40%). Findings land in `reviews/reflection_report.md §10b` and, when thresholds breach, emit drift signals that `gate_threshold_tuner.py` will consume in a later phase. The audit is metrics-only; it does not rewrite a user's historical choices.

#### New artefacts (three)

- **`reviews/tier_closeout_<round>_<YYYY-MM-DD>.md`** — per-round Planner-written close-out file. Canonical template lives in `references/tier_closeout_schema.md`; the frontmatter carries `round`, `tier_entered`, `tier_entered_via` (enum: `initial-dispatch` / `user-up` / `user-stay` / `user-down` / `auto-escalation-EG-<n>`), `ascent_observed` (the session's ratchet state at round-close), `classification_tier` (copied from `reviews/classification.md`), and `advisories` (legal values: `[DECLARED-COMPLETION-BELOW-TIER]`, `[USER-OVERRIDE]`, `[RATCHET-VIOLATION-ATTEMPTED]`, `[NARRATIVE-TRUNCATED]`).
- **`reviews/tier_decisions_log.md`** — append-only session-scoped ledger written by the Planner at Phase 5.5 step (c). Schema at `AGENT_ORCHESTRATION.md §8.2b` (parallel to the §8.2a Escalation Log): `| round | from_tier | choice | to_tier | ratchet_respected | advisories |`. The session header carries the `ascent_observed: [...]` ratchet array that Down-election suppression reads at Phase 2.5. Writer-exclusive to the Planner; readers are Reflector Phase 2c and Planner Phase 2.5.
- **`references/tier_closeout_schema.md`** — normative schema for the close-out artifact, binding on both the Planner's emission and the Reflector's read-path. Documents field-level validation surface for a future `scripts/tier-closeout-schema-check.py`.

#### Protocol additions (three)

- **Asymmetric-Down ratchet.** The close-out choice set offered to the user is a subset of `{Down, Stay, Up, Done}`, not the full set. `Down` is only offered when `ascent_observed` contains at least one tier strictly greater than the present tier — i.e. the session must have ascended at some point before a descent is reachable. Suppression is presentation-time: the ratchet does not block a `Down` choice from being recorded if the user explicitly overrides, but the default choice set respects the asymmetry. This implements the "don't drop below a tier you needed to ascend to" invariant without hard-blocking user agency.
- **Soft-floor completion semantics.** A user may elect `Done` at any tier, including below the manuscript's classification tier. When `tier_entered < classification_tier` at the moment of a `Done` election, the Planner appends `[DECLARED-COMPLETION-BELOW-TIER]` to the close-out's `advisories` field and to the decision-log row. The round still terminates; Reflector Phase 2c tracks the advisory across the session but does not block completion. Completion remains a user speech-act; the harness records, rather than adjudicates, the gap.
- **Tier-decision log writer discipline.** `AGENT_ORCHESTRATION.md §8.2b` declares the tier-decisions log writer-exclusive to the Planner, parallel to the §8.2a Escalation Log's Planner exclusivity. No other agent — Evaluator, Generator, Reflector — may write to this file. Reflector Phase 2c reads the log but does not amend historical rows; its output lands in `reflection_report.md`.

#### Notification additions (eight keys)

`references/tier_notifications.yaml` bumps `config_version` 1.0 → 1.1 and `paired_with_tier_protocol` 1.1 → 1.2. A new top-level `closeout:` section adds five keys (one per tier T1, T2, T3, T3R, T4) carrying the standard close-out notification payload (present tier, delta summary, offered choices); a new top-level `advisories:` section adds three keys (`declared_completion_below_tier`, `ratchet_violation_attempted`, `narrative_truncated`) for the Planner to surface close-out-specific advisory text when the corresponding frontmatter flag is set.

#### Strategic Rationale update

`references/TIER_PROTOCOL_SR.mermaid` — updated header version comment from v0.5.1 to v0.5.4 and extended to model the close-out protocol: the Planner agent gains `P_T_phase55` (task) with three decomposed sub-tasks (`P_T_compute_delta`, `P_T_present_closeout`, `P_T_route`) plus resources `P_R_ratchet` (the `ascent_observed[]` resource read from the tier-decisions log header) and `P_R_decisions` (the tier-decisions log itself); the Reflector agent gains `R_T_phase2c` depending on `P_R_decisions`; the User agent gains a softgoal `U_SG_declare` (completion is user-declared) with four decomposed tasks `U_T_down` / `U_T_stay` / `U_T_up` / `U_T_done`; a Phase 5.5 sub-graph wires the three Planner sub-tasks and the four user elections together, with `U_T_down` constrained by `P_R_ratchet` to express the asymmetric-Down invariant at the diagram level.

### Architectural notes

- **Completion is a speech-act, not a runtime fallthrough.** Prior to v0.5.4, a project's completion was an implicit event — the session simply stopped. The harness had no way to distinguish "the user is satisfied and this manuscript is done" from "the user ran out of time and tabled it." The Tier Close-Out Protocol makes the distinction explicit: every round that executes T1 or above terminates at a checkpoint where the user must say something. `Done` is now a recordable choice with frontmatter advisories and a ledger row, not an absence of evidence.
- **The asymmetric-Down ratchet is a kindness, not a rule.** The ratchet's job is to keep a user from reflexively answering "Down" at every checkpoint without having earned the descent through an ascent. It is a presentation-layer default, not a hard invariant. A user who means to descend anyway can still do so by explicit override (advisory `[USER-OVERRIDE]` fires). The ratchet distinguishes between the user's considered choice to descend and the path-of-least-resistance drift toward the cheapest tier — and makes the latter measurable at Reflector Phase 2c.
- **Phase 5.5 placed inside the round preserves the one-round-one-closeout invariant.** An earlier design placed Phase 5.5 after the Reflector phase, which would have required the Reflector to observe its own input. By dispatching Phase 5.5 before Reflector dispatch, the Planner writes the close-out artifact and the decision-log row, the Reflector's Phase 2c then reads the session window — which may include the round that just completed — and the invariant holds: the round that the Reflector is reflecting on is the most recent row in the decisions log it reads.
- **No new tier, no new gate, no new skill.** The close-out protocol is a mandatory phase of the existing Planner agent. Adding a `/run-tier-closeout` skill was considered and rejected: close-out is not a dispatchable entry point (there is no state from which a user would explicitly say "run a close-out on its own"), it is a terminal phase. The skill ledger is therefore unchanged; `README.md` gains a callout explaining why close-out is not a skill. Escalation gates EG-1..EG-7 are unchanged.

### Lessons learned

- **L-2026-04-19-17 — Every protocol needs a dual exit step, not just a dual entry step.** The Incremental Tier Protocol had a well-specified Phase 2.5 entry (classify + dispatch + escalation-gate sweep) but no counterpart exit step until v0.5.4. The asymmetry was invisible until completion was examined as its own object: once a user's completion election is the unit of analysis, the absence of a checkpoint at which that election is made becomes obvious. Filed against the Phase E plan. Severity: BLOCKER (closed).
- **L-2026-04-19-18 — User election events are valuable audit signal, not just control flow.** The tier-decisions log is primarily a routing artefact — the Planner reads the previous row to know where the next round enters. But the log is also a project-trajectory signal: a sequence of Down/Stay/Up/Done elections across rounds characterises the manuscript's journey in a way no single round's artefacts can. Reflector Phase 2c is the first consumer; later phases could mine the log for cross-project patterns (e.g. "projects that took three or more T4 rounds before Done cluster around a particular gap class"). Filed against Phase E+ plan. Severity: MAJOR.
- **L-2026-04-19-19 — Soft-floor completion is more honest than hard-floor completion.** An earlier design required the user to reach `classification_tier` before `Done` was offered. The hard-floor design would have forced a user who had run T3 on a T4-classified manuscript to either run T4 or lie about being done. The soft-floor design lets the user declare completion below classification while preserving the signal as an advisory the Reflector reads. The lesson: the harness should record disagreement with its own recommendations, not suppress them. Filed against Phase E+ plan. Severity: MINOR.

---

## v0.5.3 — 2026-04-19

**Theme.** Phase D.2 internal-consistency release for the v0.5.2 Phase D.1 ship cycle. The v0.5.2 post-ship audit surfaced that while v0.5.2 closed the `run-full-review` rename-cycle gaps, the package still did not follow its own stated logic in a number of places: two contracts had divergent definitions across documents (the escalation-gate table between `TIER_PROTOCOL.md §4` and `AGENT_ORCHESTRATION.md §8.2a`; the escalation-log schema between the orchestration-spec markdown-block format and the pipe-row format `scripts/gate_threshold_tuner.py` actually parses), several agent procedures under-specified what they wrote or read, and the self-T1 verdict vocabulary in the tier protocol did not match the Generator's runtime emission. v0.5.3 does not introduce new runtime behaviour; it brings every document describing a contract into parity with every other document describing the same contract, and aligns every enforcement script with the format the docs prescribe.

### Changes

#### BLOCKER-class (two)

- **GAP-B1 — Canonical escalation-gate register consolidated in `TIER_PROTOCOL.md §4`.** `AGENT_ORCHESTRATION.md §8.2a` previously carried its own EG-1…EG-7 table, whose rows did not fully match `TIER_PROTOCOL.md §4`'s rows (divergent "target tier" values for EG-3, divergent firing-semantics notes for EG-4). v0.5.3 rewrites `TIER_PROTOCOL.md §4` to be the canonical register — a full table with condition, target tier, phase-of-activation, and firing-semantics notes — and replaces `AGENT_ORCHESTRATION.md §8.2a`'s gate table with a one-paragraph cross-reference. Each of the four agent files gains a one-line pointer near its first EG-reference, stating that the agent names gates and records observations but does not redefine firing logic. This eliminates the three-way divergence the v0.5.2 audit flagged.
- **GAP-B2 — Escalation-log schema aligned with `scripts/gate_threshold_tuner.py`.** `AGENT_ORCHESTRATION.md §8.2a` previously specified the `reviews/escalation_log.md` entry format as a multi-line markdown block (`- timestamp: …`, `- from_tier: …`, `- gate: …`, etc.). The tuner script has always parsed a pipe-delimited row format via `GATE_ROW_RE` at lines 62–65: `| timestamp | from_tier -> to_tier | gate | reason | round_id |`. No existing round's logs could have been parsed by the tuner as specified. v0.5.3 rewrites the schema section to specify the pipe-row format as canonical (with an ASCII `->` arrow, not `→`, per the regex), documents field semantics, the required header, and an optional human-readable context block.

#### MAJOR-class (nine)

- **GAP-B4 — Evaluator Confirmation Mode now reads the escalation log.** `agents/evaluator.md §Confirmation Mode` Step 2 now reads `reviews/escalation_log.md` for the current round before running the deterministic subset: if the Generator's self-T1 claims `CLEAN` but the log already carries a gate firing whose `to_tier` exceeds T1, the verdict is stale and the Evaluator returns `CONFIRMATION-FAILED` without the deterministic subset. This is the audit surface `AGENT_ORCHESTRATION.md §8.2a` has been promising — a `CLEAN` verdict in the revision log is not a sufficient basis for Confirmation Mode when the escalation log already shows a higher tier was reached.
- **GAP-E1 — Coupling E.2 pre-flight ordering corrected in `PROJECT_BOOTSTRAP.md`.** The bootstrap file previously described the SK-20 overlay as firing "at every Evaluator pre-flight, before Step 1." `agents/evaluator.md` and `skills/run-tier-standard/SKILL.md` have always documented Step 0 (SK-20 overlay) as running before Step 0a (deterministic checks), because Step 0a's deterministic checks consume the overlay's source-tag output when grading citations. v0.5.3 updates `PROJECT_BOOTSTRAP.md` to state the ordering as "Step 0 — the first Evaluator action, before Step 0a (deterministic checks) and before Step 1 (classification gating)."
- **GAP-F2 — Rule-digest build-and-verify at release time.** `scripts/release-gate.sh` now runs Phase 0.65: it invokes `scripts/build_rule_digest.py` into a temp directory and re-verifies the freshly-built digest with `scripts/verify_rule_digest.py --expected-version <current>`. Any parity failure is a BLOCKER. This closes the contract `GROUNDING_PROTOCOL.md` Rule 1 and `TIER_PROTOCOL.md §3.2` declare release-gated: the tier-gated digest exception is only available to T1/T2 agents if the digest is demonstrably in parity with the source rules of the shipping version. Prior releases relied on a runtime build step that could drift between ship and first use.
- **GAP-H1 — `SKILL_REGISTRY.md` file-path hygiene.** SK-01 (`check-contradictions`), SK-02 (`check-abstract-body`), SK-03 (`quick-deterministic`), SK-13 (`suchman-register-audit`), and SK-20 (`graph-grounding-overlay`) previously declared `File: skills/<name>.md`. All five skills actually ship at `skills/<name>/SKILL.md`. v0.5.3 corrects the registry entries to match the shipped paths. The `path-hygiene-check.py` structural check does not audit registry entries, so these were invisible to the release gate — a lesson for a follow-up check.
- **GAP-H3 — Corrected: SK-04 file reference is valid.** The v0.5.2 post-ship audit initially flagged SK-04 `classify-manuscript` as pointing to a missing packaged file. Re-audit of the v0.5.2 tree confirmed `skills/packaged/classify-manuscript.skill` is in fact shipped. No registry edit is required; the audit finding is withdrawn.
- **GAP-I1 — Planner "What you write" contract completed.** `agents/planner.md §What you write` previously listed three artefacts and closed with "Nothing else." The Planner-specific rules elsewhere in the file required writing `reviews/escalation_log.md`, `reviews/round_program.md`, `reviews/state_probe_YYYY-MM-DD.md` (at T0), and a `reviews/local_findings_<date>.md` header (at T2). v0.5.3 expands the summary section to enumerate every artefact, organized into *every round*, *tier-specific*, *round-close archive*, and *conditional* groups; also spells out the round-close `reviews/escalation_log.md.<round-id>` archival copy per the `AGENT_ORCHESTRATION.md §8.2a` contract.
- **GAP-J2 — Deprecated `review_depth` migration prose retired.** The transitional read-path `quick↔T1, standard↔T3, submission-bound↔T4` was retired at v0.5.1; `TIER_PROTOCOL.md` §1 and §10 already reflected this at v0.5.1. v0.5.3 sweeps the last pockets in `agents/planner.md §Phase 2.5` and `skills/classify-manuscript/SKILL.md` Step 5 that still described the Planner as silently migrating `review_depth`-only classification records. The operational replacement: the Planner returns the user to `classify-manuscript` to produce a fresh `tier:` field.
- **GAP-J3 — Self-T1 verdict vocabulary reconciled.** `TIER_PROTOCOL.md §5.3` specified `Self-T1 verdict: CLEAN | FLAGS` with `MINOR / MAJOR / BLOCKER` sub-bullets; `agents/generator.md §Phase 3.5` has emitted `CLEAN | SUSPECT | DIRTY` since v0.4.19. The two enums are not reducible to each other. v0.5.3 rewrites `TIER_PROTOCOL.md §5.3` and §5.4 to use the three-valued runtime vocabulary, with §5.4 dispatch rules restated accordingly: `CLEAN` → Confirmation Mode; `SUSPECT` → full T1 reflex; `DIRTY` → T3 under EG-1. The block format is reproduced from `agents/generator.md §Phase 3.5` to keep the tier protocol readable on its own.
- **GAP-D2 — Reflector phase ordering fixed.** `agents/reflector.md` Phase 3a previously appeared *before* Phase 2.5 in the file, contradicting Phase 3a's own prose ("immediately before writing the final reflection report") and the fact that Phase 2.5's grounding-audit output is embedded in that report. v0.5.3 moves Phase 3a to sit between Phase 4 (Skill Development) and Phase 5 (Produce Reflection Report), so the document order now matches the runtime order: Phase 1 → 2 → 2b → 2.5 → 2.5.1 → 2.6 → 3 → 4 → 3a → 5 → 6. The duplicate "Phase 5 — Present to the User" is renamed Phase 6.

#### MINOR-class (eight)

- **GAP-B3 — Gate-ownership cross-references.** Each of the four agent files (`planner.md`, `evaluator.md`, `generator.md`, `reflector.md`) now carries a one-line pointer to `TIER_PROTOCOL.md §4` near its first EG-reference, stating that the agent names gates and records observations but does not redefine firing logic. Removes the partial, per-agent gate-mapping pattern the v0.5.2 audit flagged.
- **GAP-C1 — Stale EG-4 phase note in `run-tier-reflex`.** `skills/run-tier-reflex/SKILL.md` Step 4 previously described EG-4 as "deferred to v0.5.0, inactive at v0.4.19." EG-4 has been active at v0.5.0+. v0.5.3 rewrites the line to describe EG-4 as "Contradiction surface — active at v0.5.0+" and adds the note that a Generator self-T1 verdict of `DIRTY` is itself an EG-1 escalation that bypasses T1 reflex directly to T3.
- **GAP-D1 — Reflector output filename unified.** `agents/reflector.md §Phase 2b` step 4 previously wrote to `reviews/reflection_<date>.md`; the rest of the package (including the same file's §Phase 5) uses `reviews/reflection_report.md`. v0.5.3 unifies on `reviews/reflection_report.md`.
- **GAP-D3 — Reflector cross-reference corrected.** `agents/reflector.md §Phase 2.5 item 8a.ii` previously cited `agents/evaluator.md §Step 0.2` for the `Independent reasoning:` line contract. Step 0.2 lives at `skills/run-tier-standard/SKILL.md §Step 0.2` (the Coupling E.2 graph-grounding overlay step), not in `agents/evaluator.md`. v0.5.3 fixes the cross-reference.
- **GAP-E2 — Graph-grounding-overlay file-path corrected.** `AGENT_ORCHESTRATION.md §8.6` previously referred to the skill as `skills/graph-grounding-overlay.md`. The shipped layout is `skills/graph-grounding-overlay/SKILL.md`. v0.5.3 updates the path.
- **GAP-E3 — Coupling-script release-gate scope note.** `scripts/release-gate.sh` Phase 0.7 header now carries a note explaining that the coupling automation scripts (`coupling_readiness_check.py`, `coupling_health_report.py`, the three `sk20_*.py` scripts) are invoked by the Evaluator at runtime against live project state and cannot be meaningfully executed against an empty plugin tree at release time; the phase's guarantee is therefore narrower than the structural checks above ("no script has a syntax error that would crash on import"). Full-invocation coverage lives in the round-level regression harness the Reflector runs per-project.
- **GAP-F1 — Deferred-sweep checks documented in `release-gate.sh`.** The script's header now lists the three deferred follow-up sweeps the v0.5.2 CHANGELOG proposed (retirement-sweep check, tier-table sweep audit, description-length gate sourcing from README.md) as "Known gaps" so the script's documented scope matches what the CHANGELOG says is pending.
- **GAP-H2 — `eygp-framework-checker` registered as SK-28.** The file `skills/packaged/eygp-framework-checker.md` has been shipped since 2026-04-17 with no corresponding `SKILL_REGISTRY.md` entry, making it invisible to the registry-based audit surface. v0.5.3 adds SK-28 as the package's one packaged-only skill (no canonical `skills/<name>/SKILL.md` counterpart); the entry declares that status explicitly so the Reflector can audit the distribution as a registration-only change rather than a new runtime skill.

### Architectural notes

- **Runtime is the source of truth.** The pattern behind most v0.5.3 fixes is the same: a specification document and an enforcement script (or agent procedure) drifted apart. The resolution is always to make the spec describe what the script or procedure actually does, not the reverse. GAP-B2 is the cleanest example: the orchestration spec described a markdown-block schema that no tuner script could parse; v0.5.3 aligns the spec with the regex. GAP-J3 is the same pattern at the vocabulary level: the tier protocol described a verdict enum the Generator had never emitted. In both cases, the runtime has been in production for one or more releases; the spec is the moving part.
- **Canonical-source discipline is additive.** Establishing `TIER_PROTOCOL.md §4` as the single EG register and having every other document cross-reference it is a principle the package has stated but not uniformly applied. v0.5.3 applies the principle consistently without removing content; downstream readers of `AGENT_ORCHESTRATION.md §8.2a` still find gate names and orchestration wiring at the point of use, but the firing-condition text lives in exactly one place.
- **Release-gate coverage gaps are themselves reviewable.** GAP-H1 (SKILL_REGISTRY file paths) and GAP-H2 (unregistered shipped skill) both slipped past v0.5.2's release gate because no structural check audits the registry-to-filesystem correspondence. The v0.5.2 CHANGELOG filed a lesson about the absence of a `retirement-sweep-check.py`; v0.5.3 files parallel lessons for a registry-path auditor and a registry-completeness auditor.

### Lessons learned

- **L-2026-04-19-14 — Enforcement-script parsers are load-bearing contracts.** When a script parses a machine-readable format from an agent artefact, the parser regex *is* the canonical schema, whether or not the schema document acknowledges it. Three releases shipped with `gate_threshold_tuner.py`'s pipe-row format unmatched by the orchestration spec's markdown-block format; the tuner would have failed on any production log. Future specification updates for agent-written artefacts must be co-audited against the scripts that consume them. Filed against the Phase D release-gate plan. Severity: MAJOR.
- **L-2026-04-19-15 — Cross-document gate-definition drift is invisible unless a structural check audits it.** `TIER_PROTOCOL.md §4` and `AGENT_ORCHESTRATION.md §8.2a` both shipped gate tables for three releases; no check compared them. A future `scripts/cross-reference-check.py` could hash the normative definition in one canonical file and verify cross-references match. Filed against Phase D+ plan. Severity: MAJOR.
- **L-2026-04-19-16 — Registry-to-filesystem and registry-completeness audits are missing structural checks.** GAP-H1 and GAP-H2 both describe v0.5.2-era state that `skill-check.py`, `catalog-check.py`, and `path-hygiene-check.py` could not detect: a declared skill pointing to a missing file, or a shipped skill absent from the registry. Candidate follow-ups: `scripts/registry-path-check.py` to verify every `File:` line in `SKILL_REGISTRY.md` resolves, and `scripts/registry-completeness-check.py` to verify every `skills/<name>/SKILL.md` and every `skills/packaged/*.md` has a registry entry. Severity: MINOR.

---

## v0.5.2 — 2026-04-19

**Theme.** Phase D.1 correction release for the v0.5.1 Phase D ship cycle. v0.5.1 declared the `run-full-review` transitional alias removed and framed `/run-full-review` as returning a skill-not-found error, but the shipped tree carried seven surfaces where the alias was still described as active or recommended to users — including the frontmatter `description` of the migration-target skill `run-tier-standard` itself. v0.5.2 finishes the sweep, trims the plugin description to the documented `≤ 350 char` operating target, and removes the last file in the bundle carrying the retired skill's name. No new runtime behaviour: every agent contract, tier, gate, and rule reads exactly as at v0.5.1.

### Changes

- **Sweep of `/run-full-review` references across live skill and reference files.**
  - `skills/run-tier-standard/SKILL.md` — frontmatter `description` and Naming-and-aliasing paragraph now describe the alias as "retained at v0.5.0 and removed at v0.5.1" rather than "retained for one release." Description measures 691 chars after the edit (up from 673 at v0.5.1), still well below the 747-char peer ceiling.
  - `skills/classify-manuscript/SKILL.md` Step 5 — handoff bullet list rewritten to enumerate the tier-bound dispatch targets (`run-tier-standard` / `run-tier-submission` / `run-tier-reflex` / `response-letter-review`) with the T0 and T2 cases called out explicitly. The legacy `run-full-review` bullet and the `quick-depth`-specific instruction bullet are replaced. Closes the gap where classification would still send users to a retired command.
  - `skills/response-letter-review/SKILL.md` — body "Do not run a full review of the revised manuscript" bullet now points to the tier-bound siblings and flags the `/run-full-review` retirement inline.
  - `skills/grounding-audit/SKILL.md` and `skills/sentence-level-pass/SKILL.md` — cross-skill recommendations ("if you find 5+ MAJORs…", "for manuscript content review…") point to the tier-bound siblings instead of the retired command. Parallel sweep applied to `skills/packaged/{grounding-audit,response-letter-review,sentence-level-pass}.md`.
  - `references/RESEARCH_ROOT_CLAUDE.md` line 33 trigger-example list updated from `/run-full-review` to `/run-tier-standard`.
  - `references/TIER_PROTOCOL.md` — top-of-file Phase-status paragraph advances from a Phase-C/v0.5.0 self-description to a Phase-D-plus-Phase-D.1 self-description. §1 Legacy-compatibility paragraph and §10 Release-Scope Phase-D paragraph describe the alias as removed at v0.5.1 rather than pending removal. A Phase D.1 (v0.5.2) scope paragraph is appended to §10.
  - `references/SKILL_REGISTRY.md` — SK-18 sibling pointer now lists SK-26 and SK-27 (the live entry points) instead of the retired SK-05. SK-23 sibling pointer does the same. SK-26 and SK-27 sibling lists no longer describe SK-05 as a live transitional alias; SK-05 is cross-referenced as "(retired at v0.5.1; see Retired Skills)" and the authoritative retirement block at the end of the file stands unchanged.
- **`skills/packaged/run-full-review.skill` — removed.** The 3.9 kB stub file carrying the retired skill's exact name is deleted. The rest of `skills/packaged/` is preserved because `SKILL_REGISTRY.md` (SK-02/SK-03/SK-06 through SK-13 `File:` fields), `references/GROUND_TRUTH.md` (EYgp framework-checker load path), and `references/DETERMINISTIC_CHECKS.md` (pre-filter pointer into the checker) reference those files.
- **`.claude-plugin/plugin.json.description` trimmed from 356 → 335 chars.** The v0.5.1 manifest description cleared the 365-char peer max but exceeded the `≤ 350 char` conservative operating target the package's own README documents. v0.5.2 reshapes the sentence without dropping any capability claim: the "with" / "and" linkage is compressed and the SR-diagram / notifications / gate-tuner phrase is collapsed to "SR diagram, and gate tuner." The 365-char peer max is preserved as slack; 350 chars is the operating envelope.
- **No manifest-contract or structural-check changes.** `plugin.json` manifest contract (name, version, description, author, license, keywords) is unchanged in shape. The four structural checks (`skill-check.py`, `version-check.py`, `catalog-check.py`, `path-hygiene-check.py`) pass at 0 blockers / 0 warnings. No skill added, no skill retired, skill count remains 24.

### Architectural notes

- **The rename cycle revealed a missing release-gate check.** v0.5.1 declared a skill retirement and documented the contract in README and CHANGELOG, but the release gate had no check for whether live skill files and reference docs actually honoured the retirement. `skill-check.py` verifies frontmatter parseability and command/registry parity; `catalog-check.py` verifies README skill-count parity; neither greps the shipped text for retired skill names appearing outside a retirement block. The v0.5.2 sweep is a manual backstop; a follow-up candidate (see Notes) is a `retirement-sweep-check.py` that reads the `SKILL_REGISTRY.md` retired-skills list and fails the gate on any live reference to a retired skill's exact name outside declared historical contexts (README §Version, CHANGELOG entries, retirement blocks).
- **"Visible deprecation on every invocation" is insufficient without a source-of-truth contract in the rest of the tree.** v0.5.0 made the alias visible-on-dispatch so users would see the migration note on every call. But five live skill files and two reference docs at v0.5.1 still *instructed* users to use the retired command, undoing the dispatch-time warning at read-time. The lesson generalises: a deprecation is only as effective as the weakest pointer the user still has in front of them. Updating dispatch-time text without sweeping read-time text is half a rename.
- **`skills/packaged/` is a secondary distribution channel, not a legacy mirror.** The v0.5.1 review assumed `skills/packaged/` was legacy and could be dropped. The registry and `GROUND_TRUTH.md` / `DETERMINISTIC_CHECKS.md` show it is actually referenced as the load path for SK-02/SK-03/SK-06 through SK-13 (`.skill` / `.md` format) and the EYgp framework-checker skill. Dropping the directory wholesale would have broken those pointers. The v0.5.2 fix is surgical: remove the stub for the retired skill, sweep the stale `/run-full-review` call-outs inside the surviving `.md` files, and leave the rest of the directory intact.

### Lessons filed

- **L-2026-04-19-11 — A skill-retirement contract must be swept across the tree, not just declared.** A retirement noted in README and CHANGELOG but not reflected in the frontmatter `description` of the migration-target skill and in every cross-skill call-out is a half-retirement. The user-visible "skill-not-found" error the release notes promised only lands if no other shipped surface is still telling the user to run the retired command. The sweep is deterministic and can be mechanised; a follow-up release-gate check is the appropriate closure.
- **L-2026-04-19-12 — Secondary distribution channels inherit the primary surface's rename obligations.** `skills/packaged/*.md` duplicates the executable-prompt body of several canonical `skills/<name>/SKILL.md` files but drifts independently. A rename that sweeps the canonical copies must also sweep the `packaged/` copies, because both are reachable from `SKILL_REGISTRY.md`. Treat paired surfaces as a single unit when renaming.
- **L-2026-04-19-13 — Operating envelopes in the package's own docs are the binding target when they are tighter than the external validator.** The v0.5.1 description sat at 356 chars: below the 365-char peer max but above the 350-char README target. When the package's own docs declare a conservative envelope tighter than the validator enforces, the tighter envelope is the contract the package has written for itself. Slipping above it because "the validator still accepts it" treats the envelope as advisory when the README words it as binding. Fix: respect the documented envelope, or widen the envelope in the docs and cite the evidence for the wider value.

### Notes

- v0.5.2 is the second release in the Phase D cycle and the first patch release in the research-writing-harness-claude tree. v0.5.1 remains in `releases/` as the authoritative Phase-D ship artefact for historical reference; v0.5.2 supersedes it for install and is built from the v0.5.1 tree with the sweep applied in place.
- Follow-up candidates deferred beyond v0.5.2: `scripts/retirement-sweep-check.py` to make retired-skill references a release-gate BLOCKER outside declared historical contexts; a tier-table sweep audit that catches `review_depth`-vocabulary residue in the same way this sweep caught `run-full-review` residue; a description-length gate that reads the target from `README.md §Packaging constraints` instead of a hard-coded constant, closing the gap between "what the docs say" and "what the gate enforces."

---

## v0.5.1 — 2026-04-19

**Theme.** Phase D polish of the Incremental Tier Protocol — the ship-ready release. Phase C (v0.5.0) turned on every tier and every gate but left three gaps: a visual Strategic Rationale diagram, a user-tunable notifications config, and a multi-project calibration harness. Phase D fills all three. It also closes the skill-rename cycle begun at v0.5.0 by removing the `run-full-review` transitional alias.

### Changes

- **`run-full-review` alias retired.** At v0.5.0 the old skill name was a deprecated alias that dispatched to `run-tier-standard` or `run-tier-submission` based on classification. Every invocation surfaced a visible deprecation note so the migration path stayed in view. At v0.5.1 the alias is removed. SK-05 moves to the Retired Skills section of `SKILL_REGISTRY.md` under criterion R1 (superseded). Invocations of `/run-full-review` after v0.5.1 return a skill-not-found error.
- **`references/TIER_PROTOCOL_SR.mermaid` — new.** A Strategic Rationale diagram of the tier protocol, rendered in Mermaid using i*-style conventions (Yu 1995, 2011). Each agent carries its own decomposition; each tier is a task on the Evaluator side; the seven escalation gates are decomposition tasks on the Planner that contribute to the safety softgoal and (for EG-1 and EG-4) negatively contribute to cost. Strategic dependencies between agents are dotted edges. The diagram is the AORE companion to `TIER_PROTOCOL.md` — a promise the spec has carried since Phase A and that Phase D finally pays off.
- **`references/tier_notifications.yaml` — new.** All user-visible dispatch announcements, gate-firing notices, and Reflector calibration signals live in a single YAML config with `{{placeholder}}` substitution. Version-pinned (`config_version: "1.0"`), paired with `TIER_PROTOCOL.md` version 1.1, organised into three top-level maps (`dispatch`, `gates`, `calibration`). Unknown placeholders render as literal `{{key}}` so unfilled substitutions surface in testing rather than at runtime.
- **`scripts/tier_notifications_loader.py` — new.** Renders messages from the config with placeholder substitution. Includes a shallow fallback YAML parser so the loader works in environments without PyYAML; uses the PyYAML fast path when available. Exit codes distinguish missing config (3), unknown class/key (2), successful render (0). The loader is intentionally pure — writing the rendered string to `reviews/escalation_log.md` or to the agent's stdout is the caller's responsibility.
- **`scripts/gate_threshold_tuner.py` — new.** Reads accumulated Planner escalation logs across one or more project roots, parses per-gate firing rows against a documented regex, approximates round counts from `reviews/step_findings/` dated stems, and emits a markdown calibration report with per-gate firing rates, expected ranges (from `TIER_PROTOCOL.md §7`), and calibration signals for gates whose observed rate falls outside the documented range. Never mutates any config. Exit codes: 0 (no signals), 1 (signals raised), 2 (no logs found), 3 (read error).
- **Skill count 25 → 24.** One skill retired (`run-full-review`); two tier-bound siblings (`run-tier-standard`, `run-tier-submission`) remain active. Migration path documented in the SKILL_REGISTRY retirement entry with explicit pointers to SK-26 and SK-27.
- **README and `plugin.json` bumped to 0.5.1.** Plugin description trimmed to 356 chars (below the 365 peer max). README opener updated to reference the three Phase D artefacts; `### Skills (25)` → `### Skills (24)`; alias row removed from the skill table; quickstart prose points to the tier-bound sibling names; v0.5.1 `## Version` entry prepended.

### Architectural notes

- **The SR diagram formalises the agent-oriented reading of the tier protocol.** `TIER_PROTOCOL.md §2` describes tiers as dispatch alternatives in Planner Phase 2.5; the SR diagram makes explicit that each tier is a task belonging to the Evaluator agent, selected via means-end reasoning over the Planner's dispatch goal, and that the seven gates are themselves Planner-side tasks that contribute to the safety softgoal while negatively contributing to cost (for EG-1 and EG-4 specifically, where the cost hit is material). The diagram is not decorative — it is the paired AORE artefact that the spec has been referencing since v0.4.18. Shipping it here closes the "spec without diagram" gap that has been open since Phase A.
- **The notifications config separates agent behaviour from agent rhetoric.** Previously the exact wording of "Tier T3 selected (standard full review)" lived inside the Planner's prompt. Any phrasing change — for tone, localisation, or venue convention — required editing agent source and re-running regression suites. With the config externalised, phrasing changes are YAML edits reviewable in isolation. In AORE terms: the agent's behaviour is separated from its surface rhetoric. The config carries `config_version` and a paired `TIER_PROTOCOL.md` version so drift is detectable without being pinned.
- **The gate tuner closes the calibration loop started by Phase 2b.** Reflector Phase 2b emits `[GATE CALIBRATION SIGNAL: EG-N under/over-firing]` when a gate's rolling 3-round firing rate crosses the expected bounds documented in `TIER_PROTOCOL.md §7`. But 3 rounds in one project is a weak evidence base for a threshold change. The tuner aggregates across projects and across longer windows, producing a report the maintainer can act on with confidence. Critically, the tuner is report-only — threshold edits remain a maintainer decision with a visible diff against the spec.
- **Removing the alias at one release is the right horizon.** Holding the alias longer would make the rename open-ended; removing it at the next release after deprecation is the tightest horizon that still gives users time to migrate. The visible-on-every-invocation deprecation at v0.5.0 made sure the migration was not silent. A user who ignored the deprecation for one full release cycle is now expected to fix forward, not to have the package carry the ambiguity indefinitely.

### Lessons filed

- **L-2026-04-19-08 — Specs paired with diagrams should ship with both parts.** `TIER_PROTOCOL.md` referenced the SR model as the AORE pair since Phase A, but the diagram did not ship until Phase D. In the interim, readers had to reconstruct the agent-oriented reading from prose. The lesson generalises: if a specification declares a paired visual artefact, the visual artefact should ship in the same release as the spec, not as a later polish item. When this is impractical, the spec should explicitly mark the diagram as forthcoming with a target release.
- **L-2026-04-19-09 — Phrasing in agent source is surprisingly load-bearing.** Externalising notification text from the Planner prompt to a YAML config revealed how many minor phrasing choices had been folded into the prompt as if they were behavioural. When reviewing agent source going forward, ask whether any natural-language passage could in principle be swapped for a different one without changing agent behaviour. If the answer is yes, that text is a config concern, not a behaviour concern — and it should live outside the prompt so it can be tuned without a regression run.
- **L-2026-04-19-10 — Calibration tools that modify config should be mutation-free.** The gate tuner was initially sketched with an `--apply` flag that would edit threshold bounds directly. Removing that flag and making the tuner report-only forced the threshold-change decision back to the maintainer with a visible diff. The lesson generalises to any tool that sits between a reflection signal and a spec change: stay report-only; keep the edit decision visible and human-authored.

### Notes

- v0.5.1 is the first release to ship to the `releases/` folder since v0.4.18. The Phases B (v0.4.19) and C (v0.5.0) trees were built and gate-validated but intentionally not shipped, per the "ship only the final zip after all phases complete" directive from the user.
- Follow-up candidates deferred beyond v0.5.1: user-specified expected firing-rate overrides for the gate tuner so project-specific norms can override the package defaults; a small render harness that converts `TIER_PROTOCOL_SR.mermaid` to a static SVG for venue submissions where Mermaid is not supported; a Phase D+ pass over the T3R artefact templates so response-letter-review outputs can be checked structurally rather than only semantically; a corresponding `concept_notifications.yaml` for grounding-protocol and graphify messages, applying the same rhetoric-versus-behaviour separation to the other agent surfaces.

---

## v0.5.0 — 2026-08-20 (history appendix — superseded by 0.50.0; do not use)

### 0.5.0 kernel cut after the 0.43.1 snapshot (SUPERSEDED)

**Status.** This version identifier was superseded by 0.50.0 on 2026-08-20 due to SemVer ordering issues. Do not reference this version.

**Identity.** This heading is the 2026-08-20 kernel initially recorded in `version.json` as 0.5.0. It is not the April 2026 Incremental Tier Protocol release that historically used the same identifier (that record is below in the v0.5.1 historical subsection).

**Evaluation lane.** `evaluation-lane` ran dest-safe obligations (`d-style-profile`, `deterministic-audit`) only and fail-closed prompt-mediated scholarly rows with an explicit reason_code. This was corrected in 0.50.0. Centroid/graph fail-closes when `semantic_usage=not_invoked`. The lane does not mint scholarly CLEAN. DEST-PROTECTED stays. SK-32 stays CLOSED. Grok-only host lock stays.

---

### Historical record — April 2026 Incremental Tier Protocol (then labeled v0.5.0; not the 2026-08-20 kernel)

**Theme.** Phase C completion of the Incremental Tier Protocol. The v0.4.19 dispatch activation turns on four of the six tiers and five of the seven escalation gates; v0.5.0 completes the ladder. All six tiers (T0, T1, T2, T3, T3R, T4) dispatch, all seven gates (EG-1 through EG-7) are active, Reflector Phase 2b moves from stub to active precision/recall computation, Reflector Phase 3a (digest integrity) becomes a session-close requirement, and the legacy `review_depth` vocabulary retires in favour of an authoritative `tier:` field. Backward compatibility for one release is preserved via a transitional read-path that migrates `review_depth: quick|standard|submission-bound` in place. The v0.4.x single skill `run-full-review` is split into two tier-bound siblings — `run-tier-standard` (T3) and `run-tier-submission` (T4) — with the old name retained as a transitional alias that removes at v0.5.1.

### Changes

- **TIER_PROTOCOL.md — Phase C status.** Replaced the Phase B activation paragraph with a Phase C completion paragraph: all six tiers dispatch, all seven gates active, Reflector Phase 2b/3a active, `review_depth` retired with transitional read-path. Rewrote §4 to carry the full seven-gate semantic table, added the EG-3 cross-scope paragraph and the EG-4 same-diff contradiction paragraph. §7 expanded with the full Phase 2b procedure (trajectory collection, self-T1 pairing, P/R computation, calibration signals) and the new Phase 3a (`verify_rule_digest` invocation and SAFEGUARD consequence on mismatch). §9 file-relationships table updated; §10 Phase C release-scope paragraph replaces the v0.4.19 cut-point.
- **T2 (local-scope) dispatch — active.** Planner Phase 2.5 accepts `tier: T2` with a declared scope envelope (a specific subsection, a single paragraph range, or a single citation claim). The Evaluator runs the scoped subset of Step 2 or Step 3 plus a local SAFEGUARD Check 1. Scope definition is a Planner contract artefact; an undefined or ambiguous scope trips EG-3 and escalates to T3. T2 is the tier the architectural plan reserved for small-footprint edits that must still be audited without paying the full T3 cost.
- **T3R (response-letter mini-tier) — active.** `response-letter-review` declares `tier_binding: T3R (v0.5.0+)` in its frontmatter and becomes the authoritative dispatch target for response-letter manuscripts. `classify-manuscript` auto-recommends T3R for `paper_type: response-letter`. T3R runs the seven response-letter checks plus SAFEGUARD Checks 1/4/5, emits the three-artifact bundle (`reviews/response_letter_findings_<date>.md`, `reviews/response_letter_reframe_brief_<date>.md`, `manuscript/response_letter.md`), and escalates out to T3 or T4 on the three named escalation-out triggers.
- **EG-3 and EG-4 — now active; all seven gates live.** EG-3 fires on any cross-scope reference: a T2 finding whose location falls outside the declared envelope, or a compound-claim citation reusing the L-P4 pattern. EG-4 fires whenever SAFEGUARD Check 4 surfaces a contradiction between co-invoked sources on the **same diff** — the same-diff qualifier is the key design choice, preventing stale contradictions from over-firing. `AGENT_ORCHESTRATION.md §8.2a` carries the full seven-gate table and a calibration paragraph referencing the Phase D `gate_threshold_tuner.py`.
- **Reflector Phase 2b — divergence audit, active.** The Reflector reads `reviews/escalation_log.md` plus the round's Generator self-T1 verdicts, cross-tabulates CLEAN × CONFIRMED-CLEAN / CONFIRMATION-FAILED / [SELF-T1-DIVERGENCE], computes precision and recall for the Generator's self-assessment, and emits §10a of the reflection report. Rolling 3-round windows surface `[SELF-T1 TRUSTWORTHINESS]` (fires if precision < 0.80) and `[GATE CALIBRATION SIGNAL: EG-N under-firing/over-firing]` signals. A missing escalation log remains a Planner-contract MAJOR.
- **Reflector Phase 3a — digest integrity check, active.** At session close, the Reflector invokes `scripts/verify_rule_digest.py`. A parity mismatch is a SAFEGUARD-LAYER violation that blocks the reflection report from claiming `grounding_clean` and forces a `[DIGEST-DRIFT]` marker. This closes the tier-gated digest exception at Rule 1: the exception is only honoured if the digest is demonstrably in parity with the source rules — a drifted digest is contract violation, not a low-severity warning.
- **Skill rename — `run-full-review` → `run-tier-standard`, with `run-tier-submission` added.** Two new skills registered (SK-26 `run-tier-standard` for T3; SK-27 `run-tier-submission` for T4). `run-full-review` survives at v0.5.0 as a transitional alias that dispatches to the appropriate sibling based on the classification record's `tier:` field. Every invocation of the alias surfaces a deprecation note to the user. The alias is removed at v0.5.1.
- **`classify-manuscript` — tier field authoritative; `review_depth` retired.** The classification prompt now asks for `tier: T0 · T1 · T2 · T3 · T3R · T4` (default T3), auto-recommends T3R for response-letter inputs, and auto-recommends T4 on the five submission-bound triggers. The Step 2 input table retires the `review_depth` row to a parenthetical footnote explaining the transitional read-path. Legacy records parse under `quick↔T1, standard↔T3, submission-bound↔T4` and are migrated in place on first read.
- **`REVIEW_ORCHESTRATION.md §3.3` — rewritten as the tier table.** The three-row depth table replaced by a six-row tier table (T0 · T1 · T2 · T3 · T3R · T4) with explicit required-step vectors and G.4 sign-off columns. Transitional read-path paragraph documents the migration semantics.
- **`plugin-commands` and `SKILL_REGISTRY.md`.** Added `/run-tier-standard` and `/run-tier-submission` rows to the command catalog with tier-bound purposes; retained `/run-full-review` row with explicit alias annotation. Registered SK-26 and SK-27 in the registry with full dependency-and-sibling metadata; updated SK-05 status to *Deprecated alias (v0.5.0) — removed at v0.5.1* with the dispatch-target pointer.
- **Description and header updates.** Bumped `plugin.json` version to 0.5.0; rewrote the description to retire the Phase-B language and declare Phase C completion (final length 357 chars, below the 365 peer max). Updated the README opening paragraph to reflect full-ladder dispatch, the skill table header from `(23)` to `(25)`, and added three skill rows. Prepended the v0.5.0 `## Version` entry with 10 bullets covering the changes above.

### Architectural notes

- **Additive-only discipline is selectively broken in Phase C — deliberately.** Phase A and Phase B held to an additive-only rule: no existing contract text was narrowed. Phase C explicitly retires the `review_depth` vocabulary, which is a contracting change. The mitigation is the transitional read-path: a classification record that still writes `review_depth: standard` parses successfully and migrates silently to `tier: T3` on first read. At v0.5.1 the read-path is removed. The lesson for future phases: *one release of silent migration is the cost of contracting a vocabulary; publish the cost up-front.*
- **Same-diff qualifier on EG-4 is the load-bearing design choice.** The naïve design of EG-4 (fire whenever SAFEGUARD Check 4 surfaces any contradiction) would cause the gate to fire on every round that touches a section where two contradictory sources have long coexisted. Scoping the trigger to *co-invocation on the same diff* means EG-4 only fires when a new contradiction is introduced by the current round's edits — exactly the thing a reviewer should catch before the edit ships. Stale contradictions are still surfaced by the standalone `/check-contradictions` skill, where they belong.
- **The `run-full-review` alias is surfaced to the user on every invocation.** Silent aliasing hides the rename from users whose saved prompts and scripts need to migrate before v0.5.1. A visible deprecation note on every dispatch forces the migration path into view. The alias file's body is written around this principle — it dispatches but also *tells the user it dispatched*.
- **Reflector Phase 3a closes the tier-gated digest exception properly.** The Rule 1 exception was written in Phase A as *"at T1/T2 only, a release-verified digest may satisfy the read-before-cite requirement for a narrow enumerated scope."* The exception only holds if the digest is demonstrably in parity with the source rules. Phase 3a makes the parity check a session-close requirement, not a release-time one — which means a drifted digest surfaces in the reflection report of the round that used it, not three releases later when someone happens to re-run the verifier.

### Lessons filed

- **L-2026-04-19-05 — Silent aliasing hides renames from users who most need to migrate.** When renaming a user-facing skill, make the alias visible to the user on every dispatch rather than transparent. Silent aliasing optimizes for "nothing breaks today" but guarantees breakage at alias-removal time because no user migrated. Visible aliasing forces the migration into view on every invocation.
- **L-2026-04-19-06 — Contradiction detection needs a same-diff qualifier to avoid over-firing.** A contradiction-audit gate that fires on every co-invocation regardless of recency will flag every round touching a mature section. The actionable signal is *new* contradictions introduced by the current diff. Standalone contradiction audits handle stale contradictions where they belong; gate triggers should scope to same-diff. This pattern generalises to any SAFEGUARD check that could fire on long-standing state.
- **L-2026-04-19-07 — Digest parity is a session-close concern, not a release-time one.** A digest that drifts between the release build and session execution is invisible to release-gate verification but visible to the Reflector at session close. Making the parity check a session-close requirement surfaces drift in the round that used the digest, which is the round that still has context to act on it.

### Notes

- Release-gate at v0.5.0 is expected to clear CLEARED-WITH-WARNINGS. The four warnings inherited from v0.4.19 persist; the skill rename to `run-tier-standard` and the new `run-tier-submission` both inherit descriptions near the 747-char peer ceiling (still below ceiling) and will surface as informational warnings. Final zip is not shipped at v0.5.0 per the ship-only-v0.5.1 release plan; the v0.5.0 tree exists to gate Phase D.
- The Phase D (v0.5.1) polish phase ships `TIER_PROTOCOL_SR.mermaid` (Strategic Rationale diagram of the tier ladder), `tier_notifications.yaml` + loader, `scripts/gate_threshold_tuner.py`, and removes the `run-full-review` alias.

---

## v0.4.19 — 2026-04-19

**Theme.** Phase B activation of the Incremental Tier Protocol. The v0.4.18 foundation ships spec-only infrastructure; v0.4.19 turns on tier-aware dispatch for four of the six tiers (T0, T1, T3, T4) and wires five of the seven escalation gates (EG-1, EG-2, EG-5, EG-6, EG-7). T2, T3R, EG-3, EG-4, and the Reflector divergence-audit precision/recall block remain parked for v0.5.0. Additive-only discipline is preserved: every change is a new file, a new section, or an additive insertion.

### Changes

- **TIER_PROTOCOL.md status update.** Replaced the "Phase A spec-only" status paragraph with a Phase B activation paragraph declaring which tiers and gates are live at v0.4.19 and which remain deferred to v0.5.0. Updated the §9 file-relationships table to reflect live integration points across `REVIEW_ORCHESTRATION.md`, `AGENT_ORCHESTRATION.md`, `planner.md`, `evaluator.md`, and `generator.md`. Rewrote §10 as "Release Scope (current and forthcoming)" with four phase descriptions in prose, so readers of v0.4.19 can locate the current cut-point without consulting the architectural plan separately.
- **Planner Phase 0 — T0 state-probe (new).** Added a read-only survey phase that emits `reviews/state_probe_<date>.md` containing plugin version, classification tier, last revision-log date, and digest-presence flag. Informational queries ("what stage is this project at?") terminate at Phase 0 without touching the manuscript.
- **Planner Phase 2.5 — Tier Dispatch (new).** Consumes the classification record's `tier:` field (falling back to `review_depth` when absent), enforces the tier→dispatch-sequence table, writes every tier-up or tier-down transition to `reviews/escalation_log.md` per the §8.2a contract, and lists the five active gates (EG-1, EG-2, EG-5, EG-6, EG-7). The Planner is the single writer of the escalation log; Evaluator and Generator read-only.
- **Evaluator Confirmation Mode (new, T1 only).** When the Generator emits a self-T1 verdict of CLEAN, the Evaluator performs a ≤20-second reduced-scope verification: re-runs `DETERMINISTIC_CHECKS` mandatory subset (em-dashes, absolutes, LLM tics, >60-word sentences), spot-checks the top changed passage under `SAFEGUARD_LAYER` Check 1, and records CONFIRMED-CLEAN or CONFIRMATION-FAILED in `reviews/step_findings/confirmation_<date>.md`. CONFIRMATION-FAILED escalates via Planner under EG-2. T3 and T4 continue to use the full re-check path; Confirmation Mode is tier-gated to T1.
- **Generator Phase 3.5 — self-T1 verdict block (new).** After applying edits, the Generator self-checks five items (deterministic parity, rule-citation integrity, grounding footprint, DO_NOT_DISTURB compliance, scope fidelity) and appends a structured verdict block to `manuscript/revision_log.md` carrying one of CLEAN · SUSPECT · DIRTY, plus changed-paragraph list, judgment-call edit count, and off-plan addition count. The verdict is advisory: a falsified CLEAN verdict caught at Confirmation Mode or in Reflector Phase 2b is a BLOCKER under SAFEGUARD Check 1.
- **Reflector Phase 2b — divergence-audit stub (v0.4.19 stub; activates v0.5.0).** Reads `reviews/escalation_log.md` and the round's self-T1 verdicts; emits raw tuples to a new §10a of the reflection report. No precision/recall computation, no pattern extraction — those require the Phase C tier-set completion. A missing escalation log at v0.4.19 is a Planner-contract violation (MAJOR, Planner-attributed), not a Reflector failure.
- **`skills/run-tier-reflex/` (new, SK-25).** Diff-scoped T1 reflex pass with a ≤60-second median wall-clock budget. Reads tier preconditions, scopes to the Generator diff, loads `DETERMINISTIC_CHECKS` mandatory subset plus Grounding Rules 1/5/7a, routes on the Generator's self-T1 verdict (CLEAN → Confirmation Mode; SUSPECT/DIRTY → full T1 reflex), emits `reviews/patch_report_<date>.md`. Escalates to T3 on any EG-1 trigger, EG-5 violation, or explicit user override.
- **`skills/plugin-commands/SKILL.md` — `/run-tier-reflex` row.** Added a catalog row exposing the new slash command with its v0.4.19 version floor and the "use instead of /run-full-review when the diff is small and a Generator self-T1 verdict is present" usage guidance.
- **`references/SKILL_REGISTRY.md` — SK-25 entry.** Added the SK-25 registry row for `run-tier-reflex` at tier Package, with dependency chain (TIER_PROTOCOL.md §2 T1, Rule 1 tier-gated exception, rule-digest, escalation-log contract) and sibling skills SK-03 / SK-04 / SK-05.
- **`AGENT_ORCHESTRATION.md §8.2a` — active-gates table.** Replaced the "Phase A status" note with the seven-gate table showing condition, target tier, and status at v0.4.19 (EG-1/2/5/6/7 active; EG-3/4 deferred to v0.5.0), plus deferral rationale.
- **`REVIEW_ORCHESTRATION.md §3.3` — tier column.** Added a `Tier (v0.4.19+)` column to the depth table mapping `quick↔T1`, `standard↔T3`, `submission-bound↔T4`, and a new paragraph documenting the Planner's tier-first-then-depth precedence, the one-release compatibility shim, and the fact that T0 (state probe) and T3R (ships v0.5.0) are reached only by explicit request.
- **`classify-manuscript/SKILL.md` — tier field unpinned.** The Step-2 input table row for `Tier` now declares `T0 · T1 · T3 · T4` legal at v0.4.19 (default `T3`), explicitly notes that `T2` and `T3R` arrive at v0.5.0 per `TIER_PROTOCOL.md §2`, and documents the legacy `review_depth` fallback mapping. The Step-4 classification-record template Inputs line is updated in parallel.
- **Manifest, README, and CHANGELOG.** Bumped `plugin.json` to `0.4.19`, revised the description to replace "Phase A foundation" with "Phase B tier dispatch (T0/T1/T3/T4)" while staying under the peer-max envelope (342 chars, peer max 365). Updated the README opening paragraph and added a `v0.4.19` section under `## Version`. Bumped the `### Skills` count from 22 to 23 (catalog-check contract). This entry.

### Architectural notes

- **Additive-only discipline preserved at Phase B.** Every change in this release is a new file, a new section, or an additive insertion into an existing section. No existing contract text is narrowed, no existing skill behaviour is altered, and no existing rule is rewritten. A v0.4.19 project that does not set an explicit `tier:` field and does not consume `run-tier-reflex` runs bit-compatibly with v0.4.18 at review-depth `standard`.
- **Three-layer discipline.** The `run-tier-reflex` skill and the Generator self-T1 verdict logic are Experimental-layer additions (agent-visible, observable at runtime). The escalation-log artifact is an Experimental-layer artifact, Planner-owned under a single-writer invariant. The tier parameter exposed in `classify-manuscript` is a Control-layer input — user-facing, now parameterised rather than hard-pinned.
- **Forward compatibility with Phase C (v0.5.0).** The following v0.4.19 stubs activate on schedule in v0.5.0: Reflector Phase 2b divergence-audit precision/recall computation, EG-3 grounding-violation-count threshold, EG-4 cross-section contradiction via SAFEGUARD Check 4, T2 local-scope dispatch, T3R response-letter mini-tier, and the `run-full-review` → `run-tier-standard` rename with `run-tier-submission` as a new skill. The v0.4.19 compatibility shim mapping `review_depth → tier` retires at v0.5.0; classification records written against v0.4.19 will carry both fields and remain parseable.
- **Gate-activation ordering rationale.** EG-1/5/6/7 are wired first because they are per-finding (not per-round), and have independent trigger semantics that do not require round-level accounting. EG-2 is wired first because it rides on the self-T1 verdict which ships in this release. EG-3 and EG-4 require the Phase C round-level violation tally and SAFEGUARD Check 4 scope computation, respectively, and are deferred rather than partially wired — partial activation of a gate inverts its safety profile relative to no activation at all.

### Lessons filed

- **L-2026-04-19-03 — Advisory self-verdicts must be paired with an independent confirmation mode.** The Generator self-T1 verdict block, ungated by an independent confirmation, would constitute self-grading — a violation of the four-agent separation invariant documented in `AGENT_ORCHESTRATION §1`. The Confirmation Mode (Evaluator) + EG-2 gate (Planner) + Phase 2b divergence audit (Reflector) triangulation preserves the invariant: the Generator declares, the Evaluator confirms under a bounded rubric, the Planner routes on mismatch, the Reflector audits the declaration-confirmation-routing triple across rounds. Filed as a package-level design pattern for future self-attestation additions.
- **L-2026-04-19-04 — Additive gate activation ordering.** When a release ships a gate register with N gates but only M<N of them are runtime-wired, the gate table itself must carry explicit active/deferred status per gate and a deferral rationale, not a footnote. Readers of the gate list at v0.4.19 otherwise incorrectly assume all seven gates fire, which silently over-promises runtime behaviour. Filed against `AGENT_ORCHESTRATION.md §8.2a` as a general principle for incremental activation documentation.

### Notes

- **Behavioural parity for untouched projects.** A v0.4.18 project opened under v0.4.19 and reviewed at `review_depth: standard` dispatches to T3 via the compatibility shim and runs the full pipeline — outputs are byte-compatible with v0.4.18 outputs at the same review depth. Tier-aware behaviour surfaces only when the user sets an explicit `tier:` in the classification record, invokes `/run-tier-reflex`, or receives an EG-1/2/5/6/7 escalation.
- **Release-gate expectations.** The v0.4.19 release gate clears with four warnings under the SKILL.md frontmatter `description` peer-distribution check: three are inherited from v0.4.18 (`classify-manuscript` 622 chars, `run-full-review` 748 chars, `run-reflection` 613 chars), and one is introduced in this release (`run-tier-reflex` 716 chars). All four are warnings at the 500-char operating-envelope level; all four remain below the 747-char peer-max observed in the installed baseline (`run-full-review` sits at the ceiling). The `run-tier-reflex` description carries the tier-gated exception reference, digest contract, escalation-log contract, and version floor inline because the skill's novelty warrants the guidance; it will be reviewed for compression when the skill stabilises in Phase C.
- **Not released publicly.** v0.4.19 is built and gated in the internal staging tree. Per the project directive "get the ship-ready pack only after all the phases have completed successfully," the v0.4.19 zip remains in `/sessions/festive-lucid-darwin/plugin-build-v0.4.19/` and is not copied to the releases folder. The ship artifact is the v0.5.1 zip produced at the end of Phase D.

---

## v0.4.18 — 2026-04-19

**Theme.** Phase A foundation of the Incremental Tier Protocol — rule-digest infrastructure, escalation-log artifact contract, and additive classification vocabulary. Foundation-only: no agent dispatch behaviour changes at this version; every project classified under v0.4.18 runs at tier T3, identical to the pre-tier default.

### Changes

- **TIER_PROTOCOL.md (new).** Added `references/TIER_PROTOCOL.md`, the normative specification of the Incremental Tier Protocol (tiers T0–T4 including T3R, escalation gates EG-1 through EG-7, Generator self-T1 verdict contract, Evaluator confirmation mode, digest contract). The file explicitly marks its status as "spec now, dispatch in Phase B" so downstream consumers can reference the vocabulary without implying runtime activation.
- **GROUNDING_PROTOCOL.md Rule 1 amendment.** Added the "Tier-gated digest exception (v0.4.18+)" subsection to Rule 1. The exception admits a package-versioned, release-verified rule-digest as a Rule 1 satisfier at tiers T1 and T2 only, subject to five narrow conditions (scope, version-binding, release-verification, contestation-trigger, tier-down-on-miss). Full-read semantics at T3/T4 are unchanged. No existing Rule 1 language is modified.
- **scripts/build_rule_digest.py (new).** Compiles the version-bound rule digest from the enumerated source set (`GROUNDING_PROTOCOL.md`, `DETERMINISTIC_CHECKS.md`, `SAFEGUARD_LAYER.md`, `REVIEW_ORCHESTRATION.md`, `TIER_PROTOCOL.md`) into `reviews/_rule_digest_<version>.json`. Extraction is conservative: rule headings matched against an explicit pattern set, one-liners extracted only from the project's bolded-statement convention, no semantic compression.
- **scripts/verify_rule_digest.py (new).** Release-gate verifier. Checks schema parity, plugin-version parity against `plugin.json`, source-scope parity, per-file SHA-256/byte/line fidelity, and per-rule source-line sanity. A verifier failure invalidates the digest as a Rule 1 satisfier — agents consuming an unverified digest operate under the unamended Rule 1.
- **AGENT_ORCHESTRATION.md §8.2a (new).** Declared the `reviews/escalation_log.md` artifact contract: Planner-written, append-only, schema-fixed, one-entry-per-escalation. Phase A ships the contract; no agent writes to the log at v0.4.18.
- **classify-manuscript/SKILL.md — additive `tier` field.** Added one row to the Step 2 input table and one line to the Step 4 classification-record Inputs section. At v0.4.18 the value is hard-coded to `T3` and is not prompted for; the field pins the schema forward so Phase B can parameterise it without migrating legacy classifications.
- **Manifest, README, keyword surface.** Bumped `plugin.json` to `0.4.18`; surfaced Phase A foundation in the README opening paragraph and added a v0.4.18 entry to `README.md §Version`; added `"tier-protocol"` to the keyword list.

### Architectural notes

- **Additive-only discipline.** Every change in this release is a file addition or an additive insertion into an existing file. No existing section content is rewritten, no existing contracts are narrowed, no existing skill behaviour is altered. A project running at v0.4.17 semantics at v0.4.18 is bit-compatible with pre-Phase-A behaviour; the difference surfaces only once Phase B (v0.4.19) activates tier dispatch.
- **Three-layer discipline.** The digest scripts are Immutable-layer infrastructure (agents do not modify them). The escalation log is an Experimental-layer artifact (Planner writes, Reflector reads). The `tier` field in classification is a Control-layer input (user-facing, but hard-pinned at v0.4.18).
- **Forward compatibility.** Plan reference: `reviews/TIER_PROTOCOL_ARCHITECTURAL_PLAN.md §7 Phase A items 1–5`. Phase B items parked for v0.4.19 include: probe-state skill, reflex-review skill, Planner tier-dispatch patch, Generator self-T1 verdict block, Evaluator confirmation-mode patch, REVIEW_ORCHESTRATION tier ladder wiring, PROJECT_BOOTSTRAP §2.10a seed, and parameterised `tier` prompt in `classify-manuscript`.

### Lessons filed

- **L-2026-04-19-01 — Additive schema pinning across phased releases.** Inserting the `tier: T3` line into the classification record at v0.4.18, despite no consumer reading it until v0.4.19, eliminates the per-project migration that would otherwise be needed when Phase B lands. This is the second time (after the Rule 7a external-verification migration in v0.4.12) that a Phase-0 schema-pin has prevented a Phase-1 rewrite; filed as a package-level pattern.
- **L-2026-04-19-02 — Release-gate verifier owns fidelity, not re-extraction.** `verify_rule_digest.py` checks hash/byte/line parity and source-line sanity, but deliberately does *not* re-extract rules and diff the extraction. The SHA-256 check already guarantees byte fidelity; re-extraction would mask extraction bugs behind themselves. Filed as a general principle for any future content-derived artifact verifier.

### Notes

- **Behavioural parity at v0.4.18.** The nine-step review pipeline, the four-agent dispatch, the release-gate set, the SK-20/SK-22 orchestration, and the coupling readiness checks are all unchanged in runtime behaviour. A project that does not consult `TIER_PROTOCOL.md`, `build_rule_digest.py`, or the `tier` field in its classification record runs identically to v0.4.17.
- **Digest generation is opt-in in Phase A.** Running `build_rule_digest.py` at release time is encouraged but not required at v0.4.18; the digest has no consumers until Phase B. Release CI should add the build + verify steps in the same release cycle that adds the Phase B dispatchers.

---

## v0.4.17 — 2026-04-17

**Theme.** Portability and graph-path contract hardening, aligned to graphify integration guidance.

### Changes

- **Cross-platform wrapper root resolution.** Updated `scripts/install_preflight_assets.py` and `references/PROJECT_BOOTSTRAP.md` seed wrapper/checklist templates to resolve plugin root in this order: `AGENT_PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT`, `CURSOR_PLUGIN_ROOT`, then local fallback.
- **Graph-path contract alignment.** Updated SK-20 and grounding-audit instructions to resolve graph artifacts via project `wiki_path` (`${wiki_path}/graphify-out/`) rather than fixed literal workspace paths.
- **No-op reason parity.** Added `GRAPH_SCHEMA_INVALID` to SK-20 machine-readable no-op reason codes so skill contract matches deterministic gate output.
- **Reference-path hygiene.** Updated Coupling references in `PROJECT_BOOTSTRAP.md` to point to shipped directory-based skill paths (`skills/<name>/SKILL.md`) instead of legacy `.paper-package/` file paths.
- **Version synchronization.** Bumped package metadata/docs to `0.4.17`.

### Lessons filed

None. This release tightens portability and contract clarity without changing review semantics or coupling logic.

---

## v0.4.16 — 2026-04-17

**Theme.** Governance surface sync with the live `.paper-package` project vault and introduction of the four wiki-coupling skills (SK-14/15/16/17) that close the Research↔Wiki loop.

### Changes

- **Governance imports (new files in `references/`).** Added `ROUTING_SPINE.md` (intent-to-phase dispatch), `AGENT_CONTRACTS.md` (per-agent I/O contracts), `PARALLEL_CONDUCTOR.md` (L0–L3 concurrency + session handoff), `GROUND_TRUTH.md` (EYgp workbook registration), `STYLE_COMMITMENTS.md` (C-1…C-4 binding commitments), `OPERATING_MANUAL.md`, `EVAL_METHODOLOGY.md`, `REFLEXIVITY_CHECK.md`, `DRIFT_CHECK.md`, `DRIFT_LOG.md`, dated drift reports (`DRIFT_CHECK_REPORT_2026-04-13.md`, `DRIFT_CHECK_REPORT_2026-04-13-synergy.md`, `DRIFT_CHECK_REPORT_2026-04-16-v0.3.1.md`), `QUICKSTART.md`, `M1_M2_M3_PLANNING_PHASE_README.md`, `M1_M2_M3_ARGUMENTATIVE_RIGOR_CHECKLIST.md`, and `PACKAGE_INTEGRATION_SUMMARY_2026_04_13.md`.
- **Reference refresh.** Replaced `CLAUDE.md` (adds row 9b registering `GROUND_TRUTH.md`), `DETERMINISTIC_CHECKS.md`, `project_writing_style_checklist.md`, `bacon_2009_well_crafted_sentence_guidelines.md`, `baird_2021_writing_guidelines.md`, and both `examples/*_walkthrough.md` files with newer `.paper-package` content.
- **Four new skills (SK-14/15/16/17).** Ported `backfill-source-stubs-from-references`, `retrofit-concept-grounding`, `promote-lessons-to-wiki`, and `ingest-m5-to-wiki` from `.paper-package/skills/` into `skills/<name>/SKILL.md` directory form. Registered all four in `/plugin-commands` catalog and updated `references/SKILL_REGISTRY.md` file-path entries to the new `SKILL.md` locations. Skill count rises from 18 to 22.
- **Ground-truth payload.** Added `references/EYgp_Research_process_and_artifacts.md` + `.xlsx` (EYgp *Research Process and Artifacts* workbook, canonical definitions per `GROUND_TRUTH.md`) and `skills/packaged/eygp-framework-checker.{md,skill}` as the axis-stage framework checker.
- **Project-style example payload.** Included `tier{1,2,3}-skills-eval-review.html`, `reviews/`, `research_notes/`, `.obsidian/`, and `.claudian/` from `.paper-package` so the harness distribution carries a full worked project sample for onboarding and inspection. The harness's own agents/, scripts/, and directory-based skill structure are untouched.
- **Version synchronization.** Bumped package manifest, `README.md §Version`, and `CHANGELOG.md` to `0.4.16`.

### Lessons filed

None filed in this release. The changes are content-sync and skill additions; no architectural decisions or recurrence patterns surfaced that require a new lesson.

### Notes

- **Scripts unchanged.** The harness already shipped newer versions of `coupling_readiness_check.py`, `coupling_health_report.py`, `install_preflight_assets.py`, and `sk20_preflight_gate.py` than `.paper-package/scripts/`; those were preserved to avoid regression.
- **Behavioral parity.** No changes to the four-agent architecture, the nine-step review pipeline, the release-gate set (`skill-check.py`, `version-check.py`, `catalog-check.py`, `path-hygiene-check.py`), or the SK-20/SK-22 orchestration.

---

## v0.4.15 — 2026-04-17

**Theme.** Claude-branded package naming for clearer distribution targeting.

### Changes

- **Manifest/package rename.** Updated plugin identity to `research-writing-harness-claude`.
- **Version synchronization.** Bumped package metadata/docs to `0.4.15`.
- **Behavioral parity.** No runtime, skill, or orchestration behavior changes from `v0.4.14`.

### Lessons filed

None. This release is a naming/packaging identity update only.

---

## v0.4.14 — 2026-04-17

**Theme.** Agent metadata completeness and parser contract consistency.

### Changes

- **Evaluator frontmatter completion.** Added missing YAML frontmatter to `agents/evaluator.md` with `name`, `description`, and usage examples, aligning it with planner/generator/reflector agent files and strict metadata parsers.
- **Version synchronization.** Bumped package manifest and docs to `0.4.14`.

### Lessons filed

None. This release closes a structural metadata gap in the agent surface.

---

## v0.4.13 — 2026-04-17

**Theme.** Advisor contract alignment with current Advisor runtime.

### Changes

- **SK-18 metadata sync.** Updated `references/SKILL_REGISTRY.md` to align advisor-escalation with current Advisor runtime contract (Opus 4.7 wording, canonical runtime entrypoint reference, `project_root` canonical context-packing expectation).
- **Advisor skill wording update.** Updated `skills/advisor-escalation/SKILL.md` phrasing to match current advisor invocation and response footer fields.
- **Version synchronization.** Bumped package manifest and docs to `0.4.13`.

### Lessons filed

None. This release resolves advisor contract/documentation drift in shipped metadata and operator guidance.

---

## v0.4.12 — 2026-04-17

**Theme.** Full autonomous Coupling E.2 cycle: feed bibliography into wiki, rebuild graph artifacts, then run SK-20 overlay.

### Changes

- **New autonomous loop script.** Added `scripts/sk20_autonomous_loop.py` to run feed + rebuild + overlay as one deterministic command.
- **Wiki source ingestion layer.** The script parses manuscript bibliography and writes citation-keyed source pages into `wiki/sources/` for stable graph/source alignment.
- **Graph rebuild integration.** The script augments `graphify-out/graph.json` with bibliography-grounded nodes/edges, reclusters communities, regenerates `GRAPH_REPORT.md`, and then invokes `sk20_overlay_run.py`.
- **Loop audit artifact.** The script emits `reviews/sk20_autonomous_<date>.json` with ingest totals, graph rebuild stats, and overlay invocation payload.
- **Release-gate integration.** Added `scripts/sk20_autonomous_loop.py` to Coupling automation syntax checks in `scripts/release-gate.sh`.
- **Version synchronization.** Bumped package manifest and docs to `0.4.12`.

### Lessons filed

None. This release operationalizes autonomous graph-feeding and graph-rebuild behavior so Coupling E.2 can run without manual staging between steps.

---

## v0.4.11 — 2026-04-17

**Theme.** Deterministic end-to-end SK-20 loop execution with actionable overlay output under sparse graph coverage.

### Changes

- **New overlay runner.** Added `scripts/sk20_overlay_run.py` to execute readiness gating and overlay generation in one script, writing:
  - `reviews/coupling_readiness_<date>.json`
  - `reviews/graph_overlay_<date>.md`
  - `manuscript/revision_log.md` append entry
- **Bibliography-aware mapping.** Implemented citation-key resolution using bib metadata signals (key/year/author/title tokens) and source-node label hints to improve citation-to-graph matching.
- **Actionability under partial coverage.** Unresolved citation keys now emit explicit Type-A graph-stub findings, preventing zero-finding overlays when graph corpus linkage is incomplete.
- **Version synchronization.** Bumped package manifest and docs to `0.4.11`.

### Lessons filed

None. This release operationalizes the full Coupling E.2 loop for local Cursor/Codex execution and makes sparse-corpus outcomes explicit in findings.

---

## v0.4.10 — 2026-04-17

**Theme.** Environment compatibility variant for local Cursor/Codex loop testing.

### Changes

- **CLI override support for SK-20 preflight.** Added metadata/path override flags to `scripts/sk20_preflight_gate.py` and `scripts/coupling_readiness_check.py`:
  - `--wiki-linked`, `--coupling-e-on-review`, `--wiki-path`
  - `--manuscript-path`, `--references-path`, `--classification-path`
- **CLAUDE resolution flexibility.** Added `--allow-ancestor-claude`, `--project-claude-path`, and `--allow-missing-project-claude` to support project layouts that do not carry a local root `CLAUDE.md`.
- **TeX citation recognition.** Extended readiness citation detection to include LaTeX `\\cite...{}` forms, enabling SK-20 gating on `.tex` manuscripts.
- **Version synchronization.** Bumped package metadata and docs to `0.4.10`.

### Lessons filed

None. This release adds runtime compatibility controls for non-Claude-native workspace layouts while preserving deterministic SK-20 gating.

---

## v0.4.9 — 2026-04-17

**Theme.** Graphify contract hardening for Coupling E.2 deterministic readiness and health telemetry.

### Changes

- **New graph contract module.** Added `scripts/graphify_contract.py` to centralize graphify-aligned validation logic (schema checks, confidence taxonomy checks, and timestamp parsing for freshness evaluation).
- **Readiness gate hardening.** Updated `scripts/coupling_readiness_check.py` to enforce graph schema validity before SK-20 execution, reject non-graphify confidence labels, and emit graph metrics in readiness metadata.
- **Freshness parsing fix.** Replaced date-only graph timestamp parsing with mixed date/ISO parsing, preventing stale-check failures when `captured_at` uses ISO 8601.
- **Health report expansion.** Updated `scripts/coupling_health_report.py` to aggregate graph confidence totals, schema-error frequency, and latest graph snapshot metrics from readiness artifacts.
- **Version synchronization.** Bumped package manifest and documentation to `0.4.9`.

### Lessons filed

None. This release ports graphify validation and confidence-discipline patterns into Coupling E.2 preflight/telemetry scripts.

---

## v0.4.8 — 2026-04-17

**Theme.** Coupling E.2 operational hardening for distributed plugin installs.

### Changes

- **Portable preflight installer assets.** Updated `scripts/install_preflight_assets.py` so generated project wrappers no longer assume a fixed `.paper-package/` path; wrappers now support `CLAUDE_PLUGIN_ROOT`, explicit `-PluginRoot`, and a local fallback for legacy deployments.
- **Bootstrap template alignment.** Updated `references/PROJECT_BOOTSTRAP.md` templates (`round_checklist.md`, `run-evaluator-preflight.ps1`) to document plugin-root resolution and explicit operator override.
- **Release-gate expansion.** `scripts/release-gate.sh` now performs a dedicated Coupling E.2 automation syntax phase (`py_compile`) for `coupling_readiness_check.py`, `sk20_preflight_gate.py`, `coupling_health_report.py`, and `install_preflight_assets.py`.
- **Version bump.** Synchronized package metadata to `0.4.8` in manifest, changelog, and README.

### Lessons filed

None. This release removes deployment-path assumptions and improves pre-release determinism for Coupling E.2 automation.

---

## v0.4.7 — 2026-04-16

**Theme.** Optional policy-critical style overlay added without replacing Baird/Sexton/Bacon core controls.

### Changes

- **New style-reference distillation.** Added `references/eubanks_2018_automating_inequality_style_guidelines.md` capturing additive narration/voice patterns for policy-critical writing: human-impact anchoring, mechanism traceability, evidence pairing, normative-term clarity, and methods transparency.
- **New optional skill.** Added `skills/public-interest-accountability-pass/SKILL.md` (`/public-interest-accountability-pass`) as a conditional overlay pass for inequality/public-service accountability manuscripts.
- **Runbook integration with strict gating.** Updated `references/REVIEW_ORCHESTRATION.md` to add optional Step 5a and paper-type gating row for the new Eubanks reference, plus overlap-map guidance to avoid duplicate checks.
- **Checklist integration with strict gating.** Updated `references/project_writing_style_checklist.md` with subsection `5A` (optional public-interest accountability overlay), explicitly scoped so non-policy manuscripts can mark it N/A.
- **Discoverability updates.** Added the new slash command to `skills/plugin-commands/SKILL.md`, added SK-24 entry to `references/SKILL_REGISTRY.md`, and updated `README.md` skill inventory and style-library list.

### Lessons filed

None. This release adds a scoped overlay profile rather than replacing foundational style controls.

---

## v0.4.6 — 2026-04-16

**Theme.** Release-governance parity checks inspired by deep repository comparison, implemented with markdown + bash/python only.

### Changes

- **New `scripts/version-check.py`.** Adds a release-version sync gate across `.claude-plugin/plugin.json`, the latest `README.md` version entry, and the top `CHANGELOG.md` version heading.
- **New `scripts/catalog-check.py`.** Adds a catalog/documentation parity gate for:
  - README skill-count (`### Skills (N)`) vs discovered `skills/*/SKILL.md`,
  - `/plugin-commands` command table vs discovered shipped skill names,
  - `references/SKILL_REGISTRY.md` coverage for shipped skills.
- **New `scripts/path-hygiene-check.py`.** Adds maintainer-local absolute-path blocking for install-facing files (`README`, `CHANGELOG`, `.claude-plugin`, `skills`, `agents`, `scripts`).
- **Manifest contract checks in `scripts/skill-check.py`.** Adds required-key and field checks for `.claude-plugin/plugin.json` and blocks top-level `hooks` declarations.
- **Release-gate expansion.** `scripts/release-gate.sh` now runs `skill-check.py`, `version-check.py`, `catalog-check.py`, and `path-hygiene-check.py` as mandatory pre-bundle checks.

### Lessons filed

None. This release operationalizes deterministic governance checks from cross-repository audit findings.

---

## v0.4.5 — 2026-04-16

**Theme.** High-confidence skill integrity gating with markdown + bash/python only.

### Changes

- **New `scripts/skill-check.py`.** Added a static skill integrity checker that:
  - validates YAML frontmatter parseability for every `skills/*/SKILL.md`,
  - enforces required frontmatter keys (`name`, `description`, `trigger`, `version`),
  - verifies `/plugin-commands` command table parity against discovered shipped skills,
  - verifies every shipped skill name is present in `references/SKILL_REGISTRY.md`,
  - reports registry-only historical/external entries as warnings.
- **Release-gate hardening.** `scripts/release-gate.sh` now runs the new integrity checker as Phase 0.3 and blocks release when checker blockers are present.
- **Constraint compliance.** Implementation is markdown + bash/python only (no Node/Bun dependency introduced).

### Lessons filed

None. This release codifies verification discipline and command/registry consistency.

---

## v0.4.4 — 2026-04-16

**Theme.** Slash-command discoverability and command-catalog usability.

### Changes

- **New command-catalog skill.** Added `skills/plugin-commands/SKILL.md`, providing a single slash command (`/plugin-commands`) that lists every shipped command, purpose, and best-use moment.
- **README command discoverability update.** Updated `README.md` skill inventory (16 → 17) and usage guidance to explicitly direct users to `/plugin-commands` after installation.
- **Skill registry update.** Added SK-23 `plugin-commands` entry in `references/SKILL_REGISTRY.md` so command-list maintenance is tracked as a first-class package capability.

### Lessons filed

None. This is a usability-focused packaging enhancement.

---

## v0.4.3 — 2026-04-16

**Theme.** Wiki-guided synthesis and reconciliation integrated into the full four-agent loop.

### Changes

- **Planner synthesis briefing protocol.** `agents/planner.md` now requires Planner to produce `reviews/wiki_synthesis_brief.md` for wiki-linked rounds with synthesis-writing scope, using `LLM wiki/wiki/sources/*.md`, `GRAPH_REPORT.md`, and latest graph-overlay artifacts as inputs.
- **Generator reconciliation-writing protocol.** `agents/generator.md` now requires Generator to reconcile convergence/divergence clusters from the synthesis brief before drafting synthesis-heavy prose and to log reconciliation stance in `manuscript/revision_log.md`.
- **Evaluator pre-flight + synthesis audit extension.** `agents/evaluator.md` and `references/REVIEW_ORCHESTRATION.md` now include Step 0.3 for synthesis-brief checks in wiki-linked rounds and require Step 8 reporting on forced-consensus and unresolved-cluster handling.
- **Reflector Category 8b extension.** `agents/reflector.md` now adds a synthesis-reconciliation audit path (Category 8b) and depth-gated enforcement criteria for wiki-linked synthesis rounds.
- **Architecture/bootstrap wiring.** `references/AGENT_ORCHESTRATION.md` adds a dedicated wiki synthesis-and-reconciliation loop section, and `references/PROJECT_BOOTSTRAP.md` now includes `reviews/wiki_synthesis_brief.md` in standard runtime artifacts with a seed template.

### Lessons filed

None in this release entry; this round is a workflow integration change extending existing Coupling E usage from evaluation-only signals to full-agent synthesis behavior.

---

## v0.4.2 — 2026-04-16

**Theme.** Metadata contract cleanup and release-gate dependency hardening for the packaged plugin surface.

### Changes

- **Frontmatter consistency for core entry skills.** Added explicit `trigger` and `version` fields to `skills/classify-manuscript/SKILL.md`, `skills/run-full-review/SKILL.md`, and `skills/run-reflection/SKILL.md` so all distributed skills expose the same metadata keys under strict parsers.
- **YAML parse repair for `graph-grounding-overlay`.** Converted long frontmatter values (`created_from`, `pattern_source`) to folded YAML scalars, resolving `mapping values are not allowed here` parse failures in strict YAML loaders.
- **`scripts/release-gate.sh` dependency hardening.** The script now declares PyYAML as a runtime dependency, emits a BLOCKER when `python3 -c "import yaml"` fails, and reports skip-state explicitly for SKILL frontmatter length checks when YAML support is unavailable.
- **Packaging guidance alignment.** Updated `README.md §Packaging constraints` to set the conservative `plugin.json.description` target to `<= 350 chars`, consistent with the current validated 322-char manifest description.

### Lessons filed

None in this patch release; this round applies previously identified packaging and metadata quality controls.

---

## v0.4.1 — 2026-04-16

**Theme.** Packaging self-probe. Three user-approved improvements from the v0.4.0 release reflection, closing the packaging-layer defect class that cost three validator round-trips on the v0.4.0 release.

### Changes

- **SK-22 Phase 0 — manifest self-probe.** `skills/tool-contract-roundtrip/SKILL.md` now opens with a reflexive check against the plugin's own length-bounded manifest fields before any external verifier is probed. Peer distribution computed across installed plugins; current values bucketed as OK / WARN / BLOCKER against peer p75 and peer max. (P-plugin-01, approved.)
- **`scripts/release-gate.sh`.** New shell helper that implements SK-22 Phase 0 as a standalone command. One invocation measures manifest fields against peer distribution, builds the bundle, verifies the in-archive manifest matches the source, and scans the outputs directory for stale deliverables under superseded filenames. (P-plugin-03, approved.)
- **`README.md §Packaging constraints`.** New section documenting the empirical length caps on `plugin.json.description` and SKILL.md frontmatter descriptions, the `/mnt/outputs/` append-only constraint, and the `cp -f` / `allow_cowork_file_delete` workarounds. Makes previously-implicit validator behaviour explicit for every future release. (P-plugin-02, approved.)

### Lessons filed

**L-plugin-01 — Cowork `plugin.json.description` has an empirical length cap.**
- *What:* The Cowork plugin validator rejects manifests whose `description` field exceeds an undocumented length threshold. Empirical population across seven installed plugins on a reference host ranges 164–492 chars (median ≈ 185). Failure envelope sits above 492 and below 772 chars; 1,609 and 772 both failed; 322 cleared.
- *Why:* The component-schemas reference doc is silent on plugin.json length constraints. The constraint is enforced by the host at save-time, not declared in any schema the plugin can read.
- *How to apply:* Keep `plugin.json.description` ≤ 300 chars. Route changelog prose, version enumeration, and detailed narrative to `README.md`, which has no cap. Run `scripts/release-gate.sh` before every release — it measures the current length against the peer p75.
- *Recurrence status:* First observation in v0.4.0. Not yet confirmed as recurring across rounds.

**L-plugin-02 — `/mnt/outputs/` is append-only; stale deliverables under superseded filenames cannot be deleted from the sandbox.**
- *What:* `rm -f` against `/mnt/outputs/` returns `Operation not permitted`. `cp -f` can overwrite an existing file at a given path but cannot remove one under a different filename. A user who installs from a superseded deliverable sees every fix as ineffective.
- *Why:* Sandbox permissions on Cowork output directories disallow unlink. Multiple-file deliverables (e.g. simultaneously publishing `.plugin` and `.zip`) diverge silently after the first rename.
- *How to apply:* Generate deliverables under a single stable filename per release cycle, or overwrite every superseded filename with the current content via `cp -f` at the end of each fix. When unlink is required, request `mcp__cowork__allow_cowork_file_delete` with the target path. Confirm via `ls -la` timestamps before declaring the round closed. `scripts/release-gate.sh --outputs-dir` scans for violations.
- *Recurrence status:* First observation in v0.4.0. The sandbox constraint is permanent, so the operational rule applies to every future release.

**L-plugin-03 — When a validator fails without a field-level error, compute the empirical distribution across peer artifacts before hypothesizing a threshold.**
- *What:* Guessing a cap from a single baseline (the prior version of the same plugin) costs round-trips. Measuring the population (every installed plugin's manifest) collapses the hypothesis space in one pass.
- *Why:* Undocumented constraints are empirical. The fastest way to discover an empirical constraint is to sample the artifacts the host has already accepted.
- *How to apply:* On any first-pass validator failure, run a one-liner that measures the suspect field across the directory of installed plugins. Use the resulting distribution to choose a trim target. `scripts/release-gate.sh` automates this for description fields.
- *Recurrence status:* First observation in v0.4.0.

**L-plugin-04 — The "measure-before-assume" rule is the packaging analogue of Rule 4 (verify-before-reference).**
- *What:* Rule 4 says: do not cite what you have not verified. The packaging-layer analogue: do not assume a constraint is absent merely because it is undocumented. If the host accepts artifacts, measure them. If it rejects yours, measure them against the accepted ones.
- *Why:* Silence in documentation is not evidence of absence in enforcement. The harness already enforces this discipline on manuscripts; the v0.4.0 round demonstrated that the same discipline applies to the harness's own release artifacts.
- *How to apply:* Extend every existing Rule 4 audit (in SK-22, in Reflector Phase 2.5 item 4, in the GROUNDING_PROTOCOL rule-citation audit) to include packaging-layer claims about host behaviour, not just citation-level claims about sources.
- *Recurrence status:* First observation in v0.4.0. Candidate for promotion to a GROUNDING_PROTOCOL rule (Rule 4b?) if a second instance occurs in a future release cycle.

### Proposed improvements from v0.4.0 reflection — disposition

| Proposal | Description | Disposition |
|---|---|---|
| P-plugin-01 | Extend SK-22 to cover plugin's own manifest (empirical cap check) | APPROVED — landed as SK-22 Phase 0 |
| P-plugin-02 | Document empirical description cap in package README | APPROVED — landed as `README.md §Packaging constraints` |
| P-plugin-03 | Release-gate bash helper | APPROVED — landed as `scripts/release-gate.sh` |

---

## v0.4.0 — 2026-04-16

**Theme.** Audit-surface hardening. Five tracks closing reflexive and coverage gaps in the harness's audit surface.

### Changes

- **SK-22 `tool-contract-roundtrip`.** New skill. Reflexive release-gate probe of every external-verifier MCP. Applies Rule 1 and Rule 4 to the plugin's own tool surface.
- **Reflector Phase 2.6 — self-audit.** New meta-audit. Applies Rule 7a to the Reflector's own claims, closing the one previously-unaudited agent.
- **Depth-tiered Phase 2.5 gating table.** Explicit quick / standard / submission-bound audit-item subsets with severity floors. Silent omission is a Category 6 violation.
- **Response-letter Check 7 — render-contract rebuttal-surface audit.** Extends Category 9.a into `response-letter-review` for Scholar Gateway, Consensus, and HuggingFace Papers evidence cited in rebuttals.
- **Category 8a — graphify confidence-echo detector.** Catches mechanical severity-from-confidence mapping without independent reasoning. Round-level ECHO+SHALLOW rate ≥ 30% triggers `[COUPLING-E.2 DEGRADED]` flag.

### Lessons filed

(See v0.4.1 entry above — all four lessons were filed during the v0.4.0 post-release reflection and are documented against v0.4.1 because that is the release where the remediations landed.)

### Packaging history

Shipping v0.4.0 required four validator round-trips before the `.zip` cleared. Root cause: `plugin.json.description` at 1,609 chars — 3× the peer max. L-plugin-01 through L-plugin-04 document the diagnostic progression and the corrective actions.

---

## v0.3.3 — prior

Scholar Gateway render-contract enforcement and runtime MCP namespace pinning. See `README.md §Version` for full notes.

## v0.3.2 — prior

External verifier tier integration (Zotero, Scholar Gateway, Consensus, HuggingFace Papers, Scite) and Graphify Coupling E.2 wiring. Grounding Audit extended from six to nine categories. See `README.md §Version`.

## v0.3.1 — prior

Graphify SK-20 pilot. See `README.md §Version`.

## v0.1.0 — prior

Initial packaged release. Port from the legacy `.paper-package/` project-level deployment.

---

## How to use this file

- **When a new release ships,** prepend a new entry at the top. Include theme, changes, lessons filed, and disposition of any proposed-and-approved improvements from the prior round's Reflector report.
- **When filing a new lesson,** number it `L-plugin-NN` continuing from the highest existing number in this file. Include *what / why / how to apply / recurrence status*.
- **When a lesson recurs in a second release,** update its recurrence status to `Confirmed recurring (v0.N and v0.M)` and consider promoting its *how to apply* rule to a formal `GROUNDING_PROTOCOL.md` entry or a dedicated skill via the SK-NN SKILL_REGISTRY process.
- **Proposed improvements from a Reflector report** are listed with disposition (APPROVED / DEFERRED / REJECTED). Approved proposals are implemented in the release that files them.
