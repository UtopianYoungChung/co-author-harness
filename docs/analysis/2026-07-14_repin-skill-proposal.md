# `/repin-register` — systematic re-pin skill (spec for Codex)

*2026-07-14. Cowork proposal, revised per external review (12 refinements folded in). Builds on `docs/analysis/2026-07-13_domain-native-register-model.md` (§3 `pin`, §8) and the v0.28.0 implementation (`scripts/reader_accessibility_policy.py`, `references/policies/reader_accessibility.v1.json`). Pin **policy** is closed; this spec operationalizes re-pin **events** so they are deliberate, versioned, race-free, and enforceable by construction. Implementation is Codex's; build against this.*

---

## 1. Purpose and governing invariants

A re-pin event recomputes the two semantic view pins against the current graph/wiki state, records the change as a versioned event, and propagates it to project bindings without ever moving the yardstick mid-cycle. Four invariants are load-bearing and non-negotiable:

1. **One compute path.** `reader_accessibility_policy.py` owns the recipe. The skill orchestrates; it never hashes. A `--repin [--dry-run]` mode is added to the loader — not a second hasher, not prose arithmetic.
2. **Planner is sole writer of `reviews/phase_state.json`.** The skill communicates with it only via a rebind request file (§6).
3. **Single-snapshot compute (TOCTOU-closed).** Graph read once, hashed once, views derived from those same bytes; the snapshot is *materialized as an audit artifact* (§5), not just claimed.
4. **Epoch softening.** Old-cycle evidence stays valid for the cycle it was produced in; a *new* cycle opened without rebinding blocks. This is the settled reading of "never intra-cycle," not a re-open.

## 2. Skill surface

```
/repin-register [--dry-run] [--project-root PATH] [--trigger milestone|snowball|mf-policy-discovery|manual]
                [--allow-unrelated-dirty] [--force-lock]
```

Two surfaces, one skill, two-phase flow:

- **Package phase (default; no project context required):** preflight → single-snapshot compute → diff → no-delta: ledger row only, done → real delta: render delta report → explicit user confirmation → atomic profile write → ledger row → smoketests → propose commit. A package-only re-pin must succeed with no project root (library maintenance).
- **Project phase (requires `--project-root`):** emit `reviews/repin_rebind_request.json` for that project. Never touches `phase_state.json`.

## 3. New structures

### 3.1 Profile / schema (change BEFORE first apply)

`expected_verification` gains `pin_epoch` (monotonic int) and `pinned_at` (ISO-8601 UTC). `reader_accessibility_profile.schema.json` must admit both **before** the first `--repin` apply, or the write fails its own validation.

### 3.2 Ledger — `references/policies/repin_log.jsonl` (+ derived md view)

Machine-append JSONL; one derived human view `repin_log.md` regenerated from it (same pattern as `lifecycle_state.md`). Markdown is never the ledger — hand edits and brittle parsers. Row schema:

```json
{"epoch": 4, "pinned_at": "…Z", "dry_run": false,
 "attestation_view_pin": {"old": "…", "new": "…"},
 "exemplar_view_pin":    {"old": "…", "new": "…"},
 "profile_sha256":       {"old": "…", "new": "…"},
 "graph_sha256_provenance": "…",
 "delta_class": "none|attestation|exemplar|both",
 "delta_summary": {"resolved_seed_count": [3, 12], "primary_communities": [[5,10], [5,10,12]],
                    "degeneracy_warning": ["present", "cleared"],
                    "unresolved_seed_ids": {"added": [], "removed": ["zave-1997-…", "…"]},
                    "membership": {"added_count": 0, "removed_count": 0},
                    "exemplar_tuples_changed": []},
 "snapshot_ref": "reviews/.harness/repin/epoch-4.snapshot.json",
 "trigger": "milestone|snowball|mf-policy-discovery|manual",
 "operator": "…", "commit": null}
```

`delta_class: none` rows carry `null` old/new pins-unchanged fields but always land in the ledger — auto-accept is an event too.

### 3.3 Snapshot artifact — `reviews/.harness/repin/epoch-<N>.snapshot.json`

Written on **both** dry-run and apply: graph sha256 + mtime, both computed view pins, full `seed_resolution_map`, `seed_resolution_ties`, `unresolved_seed_ids`, `primary_communities`, degeneracy warnings, member count. Ledger rows point at it. This is what makes "read once, hash once, derive from those bytes" auditable.

### 3.4 Binding-level epoch

Each project's `phase_state.json.milestone_framework.policy_bindings.reader_accessibility` stores `pin_epoch` (and `pinned_at`) **at bind time**, alongside the existing hashes. The profile carries only the *current* epoch. Without binding-level epoch, "old evidence still valid mid-cycle" is unenforceable mechanically. Distinct MF-POLICY conditions:

| Condition | Code |
|---|---|
| Profile file hash drifted | `MF-POLICY-PROFILE-STALE` |
| View pin drifted vs recompute | `MF-POLICY-ATTESTATION-PIN-STALE` / `MF-POLICY-EXEMPLAR-PIN-STALE` |
| Binding epoch < profile epoch, no rebind, **new cycle** | `MF-POLICY-PIN-EPOCH-STALE` |

Mid-cycle rounds under an old epoch do **not** raise `PIN-EPOCH-STALE`; only opening a new cycle does.

### 3.5 Rebind request — `reviews/repin_rebind_request.json`

```json
{"request_id": "…", "pin_epoch": 4, "profile_sha256": "…",
 "attestation_view_pin": "…", "exemplar_view_pin": "…",
 "delta_class": "…", "repin_log_ref": "references/policies/repin_log.jsonl#epoch-4",
 "status": "pending|applied|cancelled"}
```

## 4. Refuse gates and lock semantics

Preflight refuses when, in order:

1. **Lock held.** `reviews/.repin.lock` at **harness root** for the profile rewrite; an optional project-root lock only during rebind-request write. Lock contents: `pid`, `host`, `started_at`, `stale_after` (default 30 min). Stale lock → refuse with recovery instructions; never silently steal; `--force-lock` requires explicit user confirmation.
2. **Uncommitted prior re-pin.** A previous re-pin diff sitting uncommitted on pin-affecting paths blocks a second re-pin regardless of `--allow-unrelated-dirty`.
3. **Dirty tree — scoped.** Refuse only on dirt in pin-affecting paths: `references/policies/reader_accessibility.v1.json`, `repin_log.jsonl` + derived md, the lock file, and the graph path if tracked. Dirt elsewhere: list the unmatched paths and proceed only with `--allow-unrelated-dirty`. A whole-repo dirty refuse would fire constantly in this workspace.
4. **Open round** in any section of the target project (project phase only — a package-only re-pin doesn't consult phase state; the epoch model protects mid-cycle projects by construction).
5. **Graph/wiki unreachable** (all three path roots resolve; graph parses; link contract holds).

## 5. Atomic write and versioning rules

- Write recipe: temp file in the same directory → `fsync` → `os.replace` → **read-back** of pins, epoch, and recomputed `profile_sha256`, asserted against intent. Never Edit-tool the policy JSON.
- **No `profile_version` bump and no profile rewrite on `delta_class: none`.** Auto-accept is a ledger row only. Otherwise every no-op re-pin flips `profile_sha256` and storms `MF-POLICY-PROFILE-STALE` across the portfolio.
- Real delta: patch-bump `profile_version`, update pins + `pin_epoch` + `pinned_at` + `graph_sha256_provenance`, one atomic replace.
- Known coupling, accepted: a real re-pin necessarily flips `profile_sha256` (pins live in the profile). Reason codes keep the failure modes distinguishable; a re-pin *is* a versioned policy change.

## 6. Planner contract additions (write into `agents/planner.md` "What you read / What you write")

- **Reads:** `reviews/repin_rebind_request.json` at dispatch and at phase-advance preflight.
- **Writes:** refreshes `policy_bindings.reader_accessibility` **only** (hashes, pins, `pin_epoch`, `pinned_at`); archives the request to `reviews/repin_rebind_request.<epoch>.applied.json`.
- **Refuses:** opening a *new* cycle while a request is `pending`. Continuing an already-open round under the old epoch is permitted (that is the epoch softening).

## 7. Delta report (human confirmation surface)

First-class fields, always shown — not buried in JSON: `resolved_seed_count` and `primary_communities` before→after; whether `RA-DNR-DEGENERATE` appeared or cleared; `unresolved_seed_ids` adds/drops; membership added/removed counts (with samples); changed exemplar tuples including newly staged `pdf_sha256`. Rationale: a graphify backfill that only shrinks `unresolved_seed_ids` **is** a real membership delta even when no exemplar PDF changed — today's most likely first re-pin looks exactly like that (9 seeds pending backfill).

## 8. Commit semantics (host-safe)

The skill **proposes** a single-purpose commit (message drafted, scope = pin-affecting paths + snapshot + ledger) and requires explicit user approval — it never auto-commits. In sandboxes that cannot write `.git`, success = "working tree ready + commit message drafted," not a failed skill. Lock release does **not** depend on commit success when the user defers — but gate 2 in §4 refuses the *next* re-pin until the diff lands. `commit` field in the ledger row is back-filled once known.

## 9. Acceptance criteria

1. **No-delta path:** `--repin` against an unchanged graph writes exactly one ledger row (`delta_class: none`), zero profile bytes changed, no version bump, exit 0.
2. **Delta path:** mutated fixture graph → delta report rendered with all §7 fields → apply produces atomic profile rewrite, epoch increment, patch bump, snapshot artifact, ledger row referencing it; read-back assertion exercised.
3. **Epoch enforcement (Planner smoketest fixture):** pending rebind request + attempt to open a new cycle → blocked with `MF-POLICY-PIN-EPOCH-STALE`; continuing an open round under the old epoch → passes; after Planner applies and archives the request → new cycle passes. This locks the "by construction" claim.
4. **Reason-code matrix:** four distinct codes (§3.4 table) each triggered by exactly its condition in fixtures; no cross-firing.
5. **Scoped dirty:** dirt on an unrelated path + no flag → proceed refused with path list; with `--allow-unrelated-dirty` → proceeds; dirt on `reader_accessibility.v1.json` → refused regardless.
6. **Lock:** fresh lock → refuse; stale lock (> `stale_after`) → refuse with recovery text; `--force-lock` without confirmation → refuse; uncommitted prior re-pin diff → refuse second re-pin.
7. **Schema-first:** applying `--repin` against a schema lacking `pin_epoch`/`pinned_at` fails closed with a message naming the schema migration (guards ordering of the rollout).
8. **Package-only:** `--repin` with no `--project-root` succeeds end-to-end without reading any `phase_state.json`.

## 10. Out of scope

- Changing the pin recipe, deny-list, or the D-4/view-pin separation (all settled; see 2026-07-13 spec §3/§8).
- Automatic graphify re-runs — backfilling the 9 unresolved seeds is a separate, user-triggered event; when it lands it flows through this skill as an ordinary delta.
- Multi-project batch rebind — one request file per project root; batch orchestration can layer on later without schema change.
