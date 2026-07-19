---
name: centroid-pass
description: 'On-demand single-centroid Eric-Yu domain-native register pass (write/review/revise) run against a manuscript scope outside the automatic phase/milestone path. Advisory dry-run by default; --apply commits write/revise through the Generator. Overrides the M1–M3 assignment-scope fence with an explicit APG-EXEMPLAR-M4-FENCE-BYPASSED advisory. Falls back to the package-pinned centroid when the project is unbound; never re-pins and never writes phase_state.json.'
trigger: when the user runs /centroid-pass <mode> [scope] on a manuscript to exercise the Yu centroid on demand — i.e. outside the automatic Ph1 Generator / Ph2–Ph4 Check-8 path — for a write-conditioning, review-warrant, or revise-substitution pass; never auto-dispatched.
version: 1.0
---

# centroid-pass — On-Demand Single-Centroid (Eric-Yu) Register Pass

**Grounding basis:** `references/policies/reader_accessibility.v1.json` → `domain_native_register` (`reader_model`, `corpus_binding`, `exemplar_members`, `warrant_layers`, `c7_fence`, `derivations`); `docs/analysis/2026-07-13_domain-native-register-model.md` §§1–9 (the register spec: two-sided plainness, two warrant layers, C-7 fence, write/review/revise derivations); `agents/generator.md` (assignment-exemplar scope refusal; retrieval-conditions-not-determines discipline; voice-register matching; DO_NOT_DISTURB); `skills/accessibility-overlay/SKILL.md` (Sub-check H surface-warrant handling; advisory-only absence); `skills/repin-register/SKILL.md` and `scripts/reader_accessibility_policy.py` (the only sanctioned pin/resolve path — this skill *reads* a resolved profile and never re-pins); `references/GROUNDING_PROTOCOL.md` (no fabrication, quote-before-attribute, no gap-filling).

---

## 1. What this skill does

`centroid-pass` exercises the single-centroid **Eric-Yu domain-native register** on demand against a manuscript scope, decoupled from the automatic activation path. In the normal flow the centroid only fires (a) inside the Ph1 Generator draft or in-plan Ph2/Ph3 new prose and (b) inside SAFEGUARD Check 8 Sub-check H at Ph2–Ph4 — and only **from milestone M4 onward** (`agents/generator.md`: exemplar conditioning is refused at M1–M3). This skill lets the user run the same three derivations — `write`, `review`, `revise` — at any time, at any milestone, on a bound project or an ad-hoc manuscript.

It changes **when** and **on demand whether** the centroid runs. It does **not** change the register model, the pins, or the governance meaning of the three warrant layers. It is a thin, auditable front door onto `domain_native_register.derivations`, not a new register.

Three deliberate posture decisions (recorded 2026-07-19, user-authorized) distinguish it from the automatic path:

1. **Milestone: override-with-warning.** The pass runs at any milestone, including the M1–M3 assignment/course-essay scope that the Generator otherwise refuses. Whenever it runs below M4 — or when the milestone cannot be determined (unbound project) — it emits the advisory `APG-EXEMPLAR-M4-FENCE-BYPASSED` at the head of its output. The fence is bypassed *visibly*, never silently.
2. **Output: advisory dry-run by default, `--apply` opt-in.** By default every mode is read-only and writes proposals to `reviews/`. `--apply` lets `write` and `revise` commit through the Generator contract with a logged revision diff. `review` is **always** read-only regardless of `--apply`.
3. **Binding: package-default fallback.** If the project binds `milestone_framework.policy_bindings.reader_accessibility`, resolve that. If it does not, resolve the package-pinned profile (`references/policies/reader_accessibility.v1.json`) directly so the pass works on any manuscript. The output records which provenance was used (`project` vs `package-default`).

## 2. Invocation

```
/centroid-pass <mode> [scope] [--apply] [--exemplar-warrant surface|argument|both]
```

- `<mode>` (required): `write` | `review` | `revise` | `all`. `all` runs review → write → revise in that order.
- `[scope]` (optional): a `section_heading_path` into `manuscript/main.md`, or `full_manuscript`. Default: the section the user names, else `full_manuscript`.
- `--apply` (optional): commit `write`/`revise` edits through the Generator with a revision-log diff. Absent ⇒ dry-run proposals only.
- `--exemplar-warrant` (optional): restrict which warrant layer conditions the pass — `surface` (register only), `argument` (derivation only), `both` (default). `argument-only` exemplar members (e.g. Dennett) are honoured regardless: they never feed the surface layer.

## 3. Preconditions (graceful no-op, never error)

Abort with `centroid-pass: no-op (<reason_code>)` and write a machine-readable no-op record to `reviews/centroid_pass_noop_<YYYY-MM-DD>.json` if any of the following fails:

1. **Profile resolves.** Resolve the domain-native profile with `scripts/reader_accessibility_policy.py` — with `--project-root <root>` if the project is bound, else against the default package profile. Bind the returned `exemplar_view_pin` and `attestation_view_pin`; record `binding_provenance`. Reason code `PROFILE_UNRESOLVED`.
2. **Exemplar corpus present.** At least the centroid PDF (`yu-1995-istar.pdf`) must be stageable/readable for the surface layer; if absent, `write`/`revise` surface conditioning degrades to argument-layer-only and records `SURFACE_CORPUS_ABSENT` as a warning (not a no-op).
3. **Scope resolves to prose.** An empty or all-table/all-figure scope ⇒ `NO_PROSE`. A heading path that does not resolve ⇒ `HEADING_NOT_RESOLVED`.
4. **Manuscript readable.** `manuscript/main.md` (or the ad-hoc target the user names) must be readable in full — full-file read is the grounding floor. Reason code `MANUSCRIPT_UNREADABLE`.

Determining milestone: read `milestone_framework` from `phase_state.json` if bound; else `milestone = unknown`. `milestone < M4` or `unknown` ⇒ set `m4_fence_bypassed = true`.

## 4. The three modes (each a derivation from the one policy object)

Each mode reads only the profile keys its derivation declares (`domain_native_register.derivations.<mode>.profile_keys`) and obeys that derivation's `discipline` string verbatim.

### 4a. `write` — conditioning (keys: `exemplar_members`, `warrant_layers`)
Retrieve near-neighbor exemplar passages relevant to the target scope's argument moves and surface register. **Retrieval conditions, it does not determine, generation** — never paste exemplar prose; never let a retrieved passage dictate propositional content. Dry-run: emit a *conditioning brief* — the retrieved anchors, the register features they attest (connectives, sentence shapes, construct-introduction patterns), and where the current draft diverges. `--apply`: hand the brief to the Generator as drafting conditioning for the scope, under the project's declared voice register and the C-7 fence (§5).

### 4b. `review` — warrant check (keys: `corpus_binding`, `warrant_layers`) — ALWAYS read-only
Flag surface constructions with no attestation warrant and argument moves with no exemplar warrant. **Absence of warrant is advisory only** (`derivations.review.discipline`) — never an automatic finding, never a BLOCKER. This mode mirrors Check 8 Sub-check H but is dispatched directly here; it reuses the same advisory-only semantics and never contributes to any TerminalSignoffRow gate. Output is a warrant map: `attested` / `advisory-foreign-surface` / `advisory-unwarranted-argument`, each with a corpus locator or an explicit "no attestation in current views" note (never invent an attestation).

### 4c. `revise` — attested substitution (keys: `warrant_layers.surface`, `c7_fence`)
For each `advisory-foreign-surface` item, propose a substitution drawn from an **attested** corpus construction (never a fresh invention), preserving propositional content (dilution guard) and the identity layer (C-7 fence). Dry-run: emit substitution proposals as a diff the user can accept. `--apply`: the Generator applies accepted substitutions and logs the revision diff; DO_NOT_DISTURB-registered passages require the usual justification in the revision log.

## 5. Non-negotiable invariants (inherited, not re-litigated here)

- **C-7 identity fence.** The centroid informs the *discipline layer* (domain conventions, argument derivation) and must never overwrite the author's *identity layer* (sentence-length signature, cadence, repetition tolerance, point of view, humor, evaluative stance, characteristic metaphor). On conflict, surface for adjudication; never default to Yu-pastiche.
- **Voice register is separate.** The project's declared voice (Vidal-cartographer / Suchman-interlocutor / blend, per project `CLAUDE.md`) governs identity; this pass never changes it.
- **Argument-only members stay off the surface.** `warrant_scope: argument-only` exemplars (e.g. `dennett-1987-intentional-stance`) feed argument architecture and attestation membership only — never the surface-register emulation target.
- **No pin motion.** This skill never re-pins, never writes `phase_state.json`, and never moves a yardstick inside an open cycle. Re-pinning is `/repin-register` only.
- **Grounding Protocol is absolute.** No fabricated corpus locators, no uncited attestations, quote-before-attribute for any exemplar phrase surfaced.

## 6. Output artefact

Write to `reviews/centroid_pass_<mode>_<YYYY-MM-DD>_<cycle_id>.md`:

```markdown
# centroid-pass — <mode>
Scope: <heading_path | full_manuscript>
Cycle: <cycle_id>
Binding provenance: <project | package-default>
Resolved exemplar_view_pin: <sha256>   attestation_view_pin: <sha256>
Milestone: <M1..M5 | unknown>
m4_fence_bypassed: <true|false>
Apply mode: <dry-run | applied>
Exemplar-warrant scope: <surface | argument | both>

> ADVISORY APG-EXEMPLAR-M4-FENCE-BYPASSED — centroid conditioning run below M4
> (or on an unbound project). The automatic path refuses this; the manual pass
> bypasses the assignment-scope fence deliberately.   [emit only when true]

## Result
<mode-specific body: conditioning brief | warrant map | substitution diff>

## Invariants honoured
- C-7 fence: <held | surfaced-for-adjudication at …>
- Argument-only members kept off surface: <yes>
- Pins unchanged / phase_state untouched: <yes>
```

For `--apply` runs, additionally append the Generator revision-log entry reference and the drift measurement, exactly as an ordinary Generator fix pass would.

## 7. What this skill is NOT

- **Not a re-pin.** It reads a resolved profile; it never recomputes or moves pins. Use `/repin-register` to change the yardstick.
- **Not a Check-8 replacement.** `review` mode is a direct, advisory warrant check; it does not emit the canonical Check 8 aggregate and never gates a TerminalSignoffRow. The automatic Sub-check H remains the gating surface at Ph2–Ph4.
- **Not a gate.** No mode of this skill can BLOCK. Its strongest output is an advisory.
- **Not a milestone override for the automatic path.** It overrides the fence only for *this manual invocation*; the Generator's M1–M3 refusal on the automatic path is unchanged.
- **Not a voice/identity editor.** It cannot rewrite the author's fingerprint; the C-7 fence forbids it.
- **Not domain-agnostic.** The centroid is IS/SE/RE-specific (i\*/conceptual-modeling prose). On an off-domain manuscript the conditioning is miscalibrated by construction; the pass runs but the output should be read as such.

---

*Normative status.* This skill operationalizes `domain_native_register.derivations` as an on-demand front door. The policy object at `references/policies/reader_accessibility.v1.json` remains the sole authority for exemplar membership, warrant layers, the C-7 fence, and the pins. This prose supplies invocation and rationale only; it creates no membership, severity, or pin semantics of its own.
