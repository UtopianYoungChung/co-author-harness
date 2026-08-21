# Harness 0.50 kernel (spec only)

**Status.** Accepted 2026-08-20 by Joseph as written. Implementation ordered 2026-08-20; landed as 0.50.0 (corrected from initial 0.5.0 SemVer error). Host-after-pack locked Grok-only 2026-08-20. Not a ready mint.
**Accepted.** 2026-08-20. Lock as given in this file. Do not retarget.
**Accepted-as.** sha256 `a31d3e5505e8d28197a073f29859e686e0ee9531a1e184cf03a93708d326d430` (bytes before this accept stamp).
**Date.** 2026-08-20.
**Owner.** Harness (instrument). Joseph is the only R-plane actor.
**Lane.** New docs lane. Do not treat this file as a rewrite of the live 0.43.1 tree.

**Does not change until Joseph orders implementation.** `version.json`, live skills, DEST-PROTECTED, SK-32, role files, the dirty 0.43.1 audit tree, or any manuscript under `research/`. Closed until he orders them: Evaluator fold, `/run-reflection` coordinator. Host-after-pack locked Grok-only 2026-08-20.

This is a **kernel cut of what already works**, not a from-zero rewrite.

---

## 1. Purpose

Freeze what the plugin is allowed to be after the Claude-pack wipe and the 0.43.1 quality-audit dirt.

0.50 is the next instrument kernel: four hands inside the plugin, real public coordinators on **staging**, dest-safe receipts, Writer as the only apply step onto a governed workbench. It is not a scholarly CLEAN mint and not a chat-to-manuscript bypass.

---

## 2. Historical 0.43.1 freeze (snapshot lane — superseded by 0.50.0)

**Status.** This section was accurate at the time the 0.50 kernel spec was accepted (2026-08-20). The 0.50 kernel has since been implemented and shipped as version 0.50.0 on 2026-08-20. Live package identity is now **0.50.0** at HEAD `d3b93b3` on origin/main.

Original freeze note (historical): Live package identity at spec acceptance was **0.43.1** at HEAD `e8ed23b` (dirty, origin/main +9). That tree was a **snapshot lane**. The packaging retarget off `.claude-plugin` to `version.json` + root `plugin.json` was part of the 0.43.1 snapshot cleanup, not 0.50 implementation.

---

## 3. Intended loop

Four hands **inside** the plugin:

| Hand | Does | Does not |
|---|---|---|
| Planner | One active target, assignment/phase bind, READY reserve | Edit manuscript |
| Generator | Rewrite/fix-apply **on staging** via `assignment_writer_commit.py` | Publish to `research/60_Workbench`; chat-apply (SK-32) |
| Evaluator | Certify **shipment / staging bytes** (exact hash) | Edit prose; mint scholarly CLEAN |
| Reflector | Probe / closeout after a certified shipment | Accept milestones; promote research artifacts |

**Outside** the plugin (not 0.50 kernel members): Grok Writer, Reviewer, Wiki, Orchestrator, Overseer. They package, draft, critique, and steward research. They do not become plugin roles.

**R-plane authority.** Joseph is the only R-plane actor. Milestone accepts are ongoing until M5 is produced; a prior accept is the current working hash, not a freeze. Any iteration may require revision of any of M1–M4. No agent promotes research artifacts.

Loop on a live package:

1. Public coordinator (`/run-draft` / `/run-iterate` / `/run-finalize` / `/run-reflection`) runs **on staging**.
2. Generator publishes staging bytes through `assignment_writer_commit.py` only.
3. Evaluator certifies those exact shipment bytes.
4. Harness writes dest-safe receipts under `reviews/.harness/shipments/<id>/` and/or `outputs/co-author-harness/staging/<work-id>/<run-id>/`.
5. **Writer** (the research agent, outside the plugin) is the apply step onto `research/60_Workbench/<work-id>/`: exact path, exact hash. If Writer edits on apply, that is a **new draft**, not the certified shipment.

Derived handoff remains valid. No F9 invention. No CLEAN mint.

---

## 4. Write law (Joseph-locked)

DEST-PROTECTED **stays**.

Harness may write:

- this package root (instrument)
- `<workspace-root>/outputs/co-author-harness/staging/<work-id>/<run-id>/`
- `research/60_Workbench/<work-id>/reviews/.harness/shipments/<shipment-id>/` (scratch receipts only; never acceptance)

Harness must refuse a direct write of manuscript bytes onto `research/60_Workbench/<work-id>/` (`DEST-PROTECTED`). Tool scratch under that work-id's `reviews/.harness/` (assignment control-plane, shipments, control-plane lock) is dest-legal instrument space. The live package is a consumer, not a kill switch for the tool, and not a governing body for other work-ids.

Writer is the apply step (exact path, exact hash). Evaluator certifies shipment bytes. If Writer edits on apply, that is a new draft.

---

## 5. Public surface (Joseph-locked)

**Real coordinators** (not degraded ads). They coordinate the four hands **on staging**:

- `/run-draft`
- `/run-iterate`
- `/run-finalize`
- `/run-reflection`

**Invoke-only** (fail-closed; no auto-dispatch as scholarly CLEAN):

- `centroid-pass` (bind only)
- `centroid-sentence-logic`
- `quick-deterministic`
- `classify-manuscript`

Graph / centroid remain invoke-only / fail-closed (`GRAPH-SEMANTIC-INELIGIBLE` stays a fail-closed, not a fabricated retrieval).

**Keep (instrument):**

- `assignment_writer_commit.py` — publish to **staging** only
- dest-safe `draft_governance` (`evaluation-lane`, `attach-verifier-receipt`; no CLEAN bind)
- existing centroid instruments (`centroid_service.py` binder; `centroid_sentence_logic.py`)

**Park as first-class, paper-specific skills** (not public coordinators; Claude/Cursor marketplace leftovers):

- `run-phase-1`
- `run-phase-2`
- `run-phase-3`
- `run-phase-4`

Do **not** park citation / claim / derivation / similar checks unless they are folded into Evaluator so they still fire. Default in this spec: those checks stay invoke-able and Evaluator still fires them. Folding into Evaluator is a later Joseph order, not a silent park.

**Closed:**

- `run-generator-session` (SK-32) stays `CLOSED_PUBLIC_BYPASS` / unavailable

---

## 6. Identity and test bind (Joseph-locked)

- `version.json` owns current package name, version, license.
- Root `plugin.json` is published host metadata and mechanically mirrors those identity fields.
- `.claude-plugin/plugin.json` is retired. Do not restore the Claude pack.
- Tests **fail** if they mention `.claude-plugin` as a required path, identity source, or HEAD-clone fixture.

---

## 7. Keep / park list (kernel cut)

### Keep (already works; 0.50 continues them)

- DEST-PROTECTED write chokepoint (`destination_capability.py`)
- `assignment_writer_commit.py` (staging publish)
- `draft_governance.py` dest-safe evaluation-lane + attach-verifier-receipt
- `centroid_service.py` bind-only
- `centroid_sentence_logic.py` (including join-cadence)
- `version.json` + root `plugin.json`
- Four role files under `agents/` (planner, generator, evaluator, reflector*)
- Public coordinator skill names in §5
- Invoke-only skills in §5
- Citation / claim / derivation / similar checks (stay firing; see §5)

### Park (not public 0.50 coordinators)

- `run-phase-1` .. `run-phase-4` (paper-specific / marketplace leftovers)
- Claude pack manifests and marketplace install of `co-author-harness-claude`
- Any check that still requires `.claude-plugin/plugin.json`

### Closed (do not reopen in 0.50)

- SK-32 `run-generator-session`
- Scholarly CLEAN mint
- Harness apply onto `research/60_Workbench/<work-id>/` manuscript paths

---

## 8. What 0.50 is not (non-goals)

- Not a from-zero rewrite of 0.43.1.
- Not a Claude pack restore.
- Not a generic linter / type / formatter / repo-root product (compatibility-scan plane).
- Not a mechanical generate+evaluate that lands M4 bytes on the live workbench.
- Not a scholarly CLEAN mint.
- Not a reopening of SK-32.
- Not Grok Writer / Reviewer / Wiki becoming plugin roles.
- Not an implementation order. Joseph reviews this spec first.

---

## 9. Joseph-only decisions still open

These are recorded, not assumed:

1. Accept or retarget this spec.
2. When (if) to order 0.50 implementation, and whether `version.json` then becomes `0.50.0`.
3. Commit / push of the 0.43.1 snapshot (dirty audit tree).
4. Host after the pack: **accepted 2026-08-20 Grok-only.** Identity stays `version.json` + root `plugin.json`. Do not install a Cursor or Claude marketplace pack. Coordinators stay Harness skill files + python CLI. Do not add a new host manifest. Do not implement `executor_claim.json`. Do not restore `.claude-plugin`. Do not reopen SK-32. Do not lift DEST-PROTECTED.
5. Whether citation / claim / derivation checks are later **folded into** Evaluator (they fire either way; fold is optional).
6. Whether `/run-reflection` stays a coordinator or becomes invoke-only after first implementation review.

---

## 10. Assumed defaults (called out)

These were not in the lock text; Harness assumed them so the spec is implementable later. Joseph may override.

- `/run-reflection` is the existing `skills/run-reflection` public name, promoted from degraded-ad to real coordinator **on staging** only.
- `classify-manuscript` stays the existing skill, invoke-only.
- 0.50 does not bump `version.json` in this spec file.
- Parked `run-phase-*` remain on disk as compatibility bodies until an implementation order deletes or hides them.
- In-flight 0.43.1 packaging retarget (`release_manifest_negative_check`, `build_plugin_provenance_smoketest`) is snapshot cleanup, not 0.50 work.

---

## 11. Implementation hold

Joseph accepted this spec as written on 2026-08-20. Do not implement 0.50 from this document until he orders it. Orchestrator packages; Harness implements only that package.

DEST-PROTECTED stays. SK-32 stays CLOSED. No Claude restore. No CLEAN mint. No ready mint.
