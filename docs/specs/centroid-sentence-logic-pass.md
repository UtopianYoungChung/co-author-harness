# Centroid sentence-logic pass (spec only)

**Status.** Implemented on the existing `centroid-sentence-logic` skill and script as **centroid-check**. Binder is **centroid-bind**. Policy member is **centroid-source**. Not promoted. SK-32 stays CLOSED.
**Date.** 2026-08-19. Join-cadence retarget the same day (Joseph via Orchestrator). Naming split 2026-08-30 (Joseph): leftover shared word `centroid` repaired without moving the Yu 2011 window.
**Owner.** Harness (instrument). Joseph is the only R-plane actor.
**Does not change.** The live policy centroid-source member or window; SK-32; role files in this pass; manuscripts.

Three names (no glossary hunt):

| Name | Object |
|---|---|
| **centroid-source** | Live policy `references/policies/reader_accessibility.v1.json` member `yu-et-al-2011-social-modeling`, role `centroid`. Yu-authored window book pp. 3-10 and 11-52. Does not move when M4 or a check moves. |
| **centroid-check** | This pass. Consecutive sentences join to admitted Yu/Dennett passages. Requires named manuscript bytes. A check of live M4 is a check, not a redefinition of the source. |
| **centroid-bind** | `scripts/centroid_service.py` packet. Policy + graph eligibility + named bytes. `GRAPH-SEMANTIC-INELIGIBLE` is eligibility, not a pair verdict. Empty `semantic_findings` is not a pass. |

This document specifies a **role-produced** pass that sits on top of a successful centroid-bind packet. The binder stays a binder.

---

## 1. Purpose

Generator and Evaluator must use **attested Yu and Dennett passages** to join ideas and logic from one sentence to the next.

The current centroid skill only binds policy, members, warrants, hashes, and scope. It emits **no semantic verdict**. That is correct and stays. Empty `semantic_findings` from the service is not a pass.

The sentence-logic pass is the missing judgment layer: given a `binding_resolved` packet plus manuscript bytes plus **admitted** passages, the roles decide whether consecutive sentences actually carry Yu-grounded modeling logic (and Dennett-grounded argument warrants) without stealing anyone's voice.

---

## 2. Inputs

All three are required before a verdict. Missing any one is fail-closed (see §8).

1. **centroid-bind packet.** A successful `centroid_service.py` result with `status: binding_resolved` and `instrument: centroid-bind`. The packet is evidence of what was bound, not of prose quality.
2. **Manuscript bytes.** The exact UTF-8 bytes whose `sha256` matches `packet.manuscript.sha256` (and scoped bytes matching `packet.manuscript.scope.sha256`).
3. **Admitted passages.** Verbatim excerpts that the packet's member and warrant views already admit, each with locator (source_key, work, page or section, quote, sha256 of the quote). Passages Joseph admits on the R-plane count. Passages invented by a role, fetched from a structural-only graph, or taken from a Yu/Dennett page outside the admitted retrieval_scope do **not** count.

The service still emits no semantic verdict. Roles produce the sentence-logic judgment **and** a receipt (§7).

---

## 3. Sentence-to-sentence checks

Work one consecutive pair at a time inside the bound scope (then the next pair). Do not score the paragraph as a bag of claims.

For each pair `(S_n, S_{n+1})`:

| Check | Question | Fail if |
|---|---|---|
| Carry | Does `S_{n+1}` take a named idea, relation, or commitment from `S_n` (actor, goal, dependency, intentional stance, etc.) rather than starting a new unlinked topic? | Topic jump with no explicit hinge |
| Hinge | Is the join lexical or logical (therefore, which means, that dependency, the same actor…), not only a stylish connector? | "And" / "also" with no shared referent |
| Attestation | Is the hinge licensed by an admitted Yu or Dennett passage, not by generic RE folklore? | Warrant is "everyone knows i*" or an unlocated paraphrase |
| Scope | Does the pair stay inside the packet's heading/byte scope? | Pair cites or depends on out-of-scope prose |
| Voice | Does the pair stay in the author's C-7 voice? | Pair mimics Yu's or Dennett's identity-layer phrasing |
| Role split | Is Yu used for modeling/join architecture and Dennett only for argument warrant? | Dennett used as surface register; Yu used as personality |
| Join-cadence | Does `S_{n+1}` show how the idea was derived from `S_n`, or only a short unearned verdict? A missing join-cadence is a miss even when an attested hinge is present. | Short unearned verdict; all-short stack (receipt flag); missing backtrack when the argument needs one |

A pair is **CLEAN**, **ADVISORY**, or **BLOCKER**. BLOCKER means the next sentence does not logically continue the last on attested grounds.

Join-cadence is **not** the hinge and is **not** the binder. Attestation can pass and join-cadence still miss. The instrument may emit mechanical signals (`unearned_verdict`, `derivation_shown`, `all_short_stack`, `needed_backtrack_missing`). Roles still fill CLEAN / ADVISORY / BLOCKER. The script does not mint CLEAN.

### 3.1 Join-cadence (Joseph, 2026-08-19)

- **Derivation.** `S_{n+1}` must show the step from `S_n` (named carry plus how it was obtained). Naming a Yu hinge is not enough.
- **Unearned verdict.** A short `S_{n+1}` that only announces a conclusion (`thus` / `therefore` / `so` / `hence` / `in short`) without derivation is a join-cadence miss.
- **All-short stack.** If every sentence in the bound scope is short (instrument: ≤12 words) and there are at least three sentences, flag `all_short_stack` on the receipt. That is a miss pattern for the stack. It is not an automatic BLOCKER on every pair.
- **Backtrack.** Do not require a backtrack on every pair. A clean forward derivation does not need one. Flag `needed_backtrack_missing` only when `S_{n+1}` retracts, qualifies, or abandons an open commitment from `S_n` without returning to it.

Keep: no Yu/Dennett voice imitation; Dennett argument-only; Yu 2011 window (pp. 3–10 and 11–52); C-7 author voice; no CLEAN mint; SK-32 CLOSED. Do not collapse this check into `centroid_service.py`.

The pass does **not** replace Bacon sentence-craft, em-dash discipline, or grounding-audit. Those stay adjacent skills.

---

## 4. Yu vs Dennett split

### Yu 2011 *Social Modeling* — primary centroid

- Source key (live policy): `yu-et-al-2011-social-modeling`.
- Retrieve **only** the verified Yu-authored volume introduction (book pp. 3–10) and Yu's i* core chapter (book pp. 11–52).
- Use: argument architecture and **domain-native surface register** (how strategic actors, goals, and dependencies are named and joined).
- Other Yu members (`yu-1995-istar`, 1994/1997/2001 papers, 2024–2025 recent-yu) may **condition** that domain-native surface register. They are not a second primary centroid and do not expand the 2011 page window.
- Yu is never a voice-emulation target. Register ≠ identity.

### Dennett 1987 *The Intentional Stance* — argument-only warrant

- Source key (live policy): `dennett-1987-intentional-stance`.
- `warrant_scope: argument-only`.
- Use: to warrant **why** a sentence may treat an actor as having beliefs/goals/intentions (intentional-stance argument).
- **Never** a surface-register model. **Never** a voice-emulation target.
- A sentence that "sounds like Dennett" is a C-7 violation even if the argument is right.

### C-7 fence (already in the tree)

Generator must not imitate a source's identity-layer voice. C-7 stays the **author's** voice, not Yu's or Dennett's. The sentence-logic pass may praise a Yu-licensed join and still BLOCKER the same pair for voice theft.

---

## 5. write / review / revise

The binder's `--mode` stays. This pass consumes that mode; it does not add a fourth.

| Mode | Who judges | What they do | What they must not do |
|---|---|---|---|
| `write` | Generator, after the binder packet, before or while drafting the next sentence | Use admitted Yu joins to decide what `S_{n+1}` may say; use Dennett only to warrant intentional ascription | Chat-apply (SK-32 stays CLOSED). No `/run-generator-session`. No manuscript write from a chat summary. No invented Yu/Dennett quotes |
| `review` | Evaluator, independent, on the exact bound bytes | Mark each pair CLEAN / ADVISORY / BLOCKER; record warrant limits | Do not rewrite prose. Do not treat empty service `semantic_findings` as CLEAN |
| `revise` | Generator, only on Evaluator-authorized pairs plus F6-listed items | Repair the hinge or the attestation; keep propositional content and C-7 identity features | Do not add argument beyond those findings. Do not "smooth" voice toward Yu/Dennett |

Planner may schedule the pass. Planner does not judge pairs and does not write manuscript.

---

## 6. Live wiki graph is GRAPH-SEMANTIC-INELIGIBLE

The workspace graph is structural-only (`semantic_status` pending; required semantic provenance missing). **Do not pretend retrieval works.**

What Generator and Evaluator do in that state:

| Need | Disposition |
|---|---|
| Binder packet itself | Allowed. `binding_resolved` + `reason_code: GRAPH-SEMANTIC-INELIGIBLE` is a general binding, not a scholarly pass. |
| Graph-retrieved Yu/Dennett passages | **Fail closed.** Structural nodes are not admitted passages. |
| Sentence-logic verdict that depends on those passages | **Fail closed** unless Joseph (R-plane) has already admitted exact excerpts with locators, or the hash-bound PDF pages in the live policy `retrieval_scope` are read as files (not via the graph). |
| "We couldn't retrieve, but the join feels right" | Forbidden. That is folklore. |
| Graph later becomes semantic-complete | **Deferred** until a new binder packet shows eligible semantic provenance. Old ineligible packets do not get upgraded in place. |

Advisory is allowed only for **packet limitations** (tell Joseph the graph cannot retrieve). It is not an advisory pass on the prose.

---

## 7. Receipt shape

Roles write the receipt. The service does not. Suggested path (not created here):

`reviews/.harness/shipments/<id>/centroid-check_<mode>.md` (or a JSON sibling under the same stem)

Minimum fields:

```text
pass: centroid-check
instrument: centroid-check
centroid_source: yu-et-al-2011-social-modeling
naming: this is a centroid-check of manuscript <sha256>/<bytes> against centroid-source yu-et-al-2011-social-modeling
mode: write | review | revise
packet_sha256: <sha256 of the binder JSON>
manuscript_sha256: <must match packet.manuscript.sha256>
scope_sha256: <must match packet.manuscript.scope.sha256>
graph_state: ineligible | eligible
admitted_passages:
  - source_key, locator, quote_sha256, warrant_layer (surface|argument)
pairs:
  - n, s_n_locator, s_n1_locator, check results (including join-cadence), verdict (CLEAN|ADVISORY|BLOCKER), attesting_passage
summary: counts by verdict; all_short_stack; join_cadence_misses; needed_backtrack_missing
c7: any voice-theft BLOCKERs
actor: Generator | Evaluator
r_plane: Joseph only (no role self-admits a new passage)
```

A receipt without matching packet/manuscript hashes is void. A receipt that lists `semantic_findings: []` copied from the service is void as a pass.

---

## 8. Fail-closed cases

- No `binding_resolved` packet, or packet `status` is `unavailable`.
- Manuscript or scope hash mismatch.
- GRAPH-SEMANTIC-INELIGIBLE **and** no Joseph-admitted excerpts **and** no in-scope PDF page read.
- Yu quote from outside book pp. 3–10 or 11–52 (for the 2011 primary).
- Dennett used as surface register or voice model.
- Role invents or paraphrases an unlocated "Yu says / Dennett says".
- `/run-generator-session` or any chat-to-manuscript apply (SK-32 CLOSED).
- Anyone other than Joseph admits a new passage onto the R-plane.

Fail closed means: no CLEAN verdict, no manuscript write, no promotion.

---

## 9. Out of scope

- Changing `centroid_service.py` or the live binder schema.
- Restoring the Claude pack, marketplace, or slash-only wiring.
- Reopening SK-32.
- Graph repair / making the wiki semantic-complete (Wiki's lane).
- Research writes, P1, or knowledge/ edits.
- Promoting this spec to a skill, capability row, or command_surface entry.
- Bacon craft, em-dash, grounding-audit, classify-manuscript.
- Treating other Yu members as a second primary centroid.

---

## 10. Decided (2026-08-19, Joseph via Orchestrator)

Held. These defaults replace the open questions. The rest of this spec is unchanged.

1. When the graph is ineligible, hash-bound PDFs in the live policy `retrieval_scope` count as admitted passages. Joseph-pasted excerpts also count. A paste is not required every time.
2. One BLOCKER pair fails the whole bound scope for qualification. The receipt still counts every pair.
3. `write` mode: Generator must name the Yu hinge (and the Dennett warrant if the pair makes an intentional ascription). It does not lock emitting `S_{n+1}`.
4. Receipt: JSON is the machine contract; a markdown sibling is for humans.
5. Invoke-only while the binder packet is `GRAPH-SEMANTIC-INELIGIBLE`. Auto-run after the binder only once a later packet is semantically eligible.
6. Extra Yu members may condition domain-native register only. Join vocabulary stays the 2011 window (pp. 3–10 and 11–52). Not a second centroid.
7. Missing join-cadence is a miss, not only a missing attested hinge. Flag all-short stacks and missing backtrack when the argument needs one. Do not require a backtrack on every pair. Do not collapse this into the binder.

---

## 11. Contradictions already in the tree (flag, do not "fix" here)

- `skills/centroid-pass/SKILL.md` already tells roles to retrieve admitted passages and perform a semantic judgment, then says empty service `semantic_findings` is not a pass. This spec **agrees** on the second point and **tightens** the first: retrieval is not the binder, and graph retrieval currently cannot work.
- `scripts/centroid_service.py` now emits a general `binding_resolved` packet with `reason_code: GRAPH-SEMANTIC-INELIGIBLE` on this workspace. That can be misread as "centroid ran, so sentence logic may run." Under this spec it only means the binder ran. Sentence logic still fail-closes without admitted passages.
- `agents/generator.md` binds centroid through draft-governance / capability scope and teaches **Bacon** sentence craft and project voice (Suchman / Vidal / CLAUDE.md). It does **not** currently require Yu-to-next-sentence joins or a Dennett argument-only warrant. Implementing this spec would add a duty Generator.md does not yet state.
- `agents/generator.md` still has Claude plugin-root / `CLAUDE.md` file-resolution language. This spec uses general skill names only and does not reintroduce that host.
- `references/capabilities.yaml` marks `centroid-pass` active again. This spec does **not** add a second capability row. If Joseph later implements, the new pass needs its own general name (proposed: `centroid-sentence-logic`) so it is not collapsed into the binder.

---

## 12. Proposed later name (not created)

General skill name if Joseph approves implementation: `centroid-sentence-logic`.
Not a Claude command. Not a marketplace plugin. Not `/run-generator-session`.
