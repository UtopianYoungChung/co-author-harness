---
name: repin-register
user-invocable: false
description: Deliberately recompute and version the domain-native register semantic pins, record the package-scoped snapshot and re-pin ledger, and optionally request a Planner-owned project rebind. Use at milestone transitions, after grounded-source admission, after MF-POLICY pin discovery, or for an explicit maintenance re-pin; never use intra-cycle to move an active round's yardstick.
trigger: when the user asks to repin the reader-accessibility register, a milestone or snowball event changes the register corpus, MF-POLICY reports stale semantic pins, or package maintenance requires a pin audit
created_by: Codex from accepted Joseph/Cowork/Codex architecture
created_from: docs/analysis/2026-07-14_repin-skill-proposal.md
version: 1.0
---
# Re-pin Domain-Native Register

Run the accepted, deterministic re-pin workflow. The Python loader is the only
compute authority. This skill orchestrates it; never calculate, edit, or infer
either semantic hash in prose.

## Invocation

`/repin-register [--dry-run] [--project-root PATH] [--trigger milestone|snowball|mf-policy-discovery|manual] [--allow-unrelated-dirty] [--force-lock] [--add-exemplar KEY --role ROLE [--warrant-scope both|argument-only] | --drop-exemplar KEY [--confirm-drop-locked-role]]`

Package phase is the default and requires no project. `--project-root` adds the
project phase, whose only direct project write is
`reviews/repin_rebind_request.json`. Never write a live project's
`reviews/phase_state.json`; the Planner is its sole writer.

## Before running

1. Read `references/policies/reader_accessibility.v1.json` and confirm its
   schema admits `expected_verification.pin_epoch` and `pinned_at`.
2. Run from the package root. Preserve the package lock at
   `reviews/.repin.lock`; never remove or steal it manually.
   The loader also holds the Wiki's shared `.graph-write.lock` from semantic
   resolution through final read-back, so graph publication and re-pin cannot
   overlap.
3. If `--project-root` is supplied, confirm the path is the intended project.
   The loader refuses an open round. Do not work around that refusal.
4. Explain that old-cycle evidence remains valid; only a new cycle is held for
   a pending rebind. A re-pin is not permission to reopen an active round.

## Exemplar ingestion

`--add-exemplar` and `--drop-exemplar` stage one register-definition change
inside the same compute/confirmation/epoch transaction; they never perform a
metadata-only edit. Addition uses the exact `wiki/sources/KEY.md` page (no
alias resolution), requires a live grounding tier outside `stub`/`unresolved`,
and requires `--role`. `centroid` is locked to
`yu-et-al-2011-social-modeling`;
`intentional-root` is locked to `dennett-1987-intentional-stance` and defaults
to `argument-only`. Explicitly assigning that role `both` is a refusal.

The centroid's retrieval scope is limited to the
verified Yu-authored volume introduction and i* core chapter recorded in the
profile; the rest of the edited volume is not a Yu-style warrant.

Missing PDFs and membership/one-hop coherence are advisories for human
judgment, not admission gates. Dropping a locked-role member additionally
requires the typed `--confirm-drop-locked-role` flag. Never create or ground a
wiki page, and never promote a pending exemplar, on the user's behalf.

## Procedure

1. Invoke the single compute path:

   `python scripts/reader_accessibility_policy.py --repin --trigger <trigger> [--dry-run] [--project-root "<path>"] [--allow-unrelated-dirty] [--force-lock]`

2. On `delta_class: none`, report the ledger event and snapshot. Confirm that
   the profile bytes and `profile_version` did not change. Stop.
3. On a real delta, present every `delta_report` field before approval:
   resolved seed count, primary communities, degeneracy transition, unresolved
   seed additions/removals, membership counts and samples, and changed exemplar
   tuples including staged PDF hashes.
   For ingestion, also present `exemplar_members_added` or
   `exemplar_members_dropped`, its effective `warrant_scope`, and every
   PDF/coherence advisory.
4. Ask the user explicitly whether to apply. Only an affirmative answer may be
   passed to the loader's confirmation prompt. A refusal leaves the dry-run
   snapshot/ledger evidence and does not rewrite the profile.
5. After apply, report the patch-bumped profile version, new pin epoch,
   package-scoped snapshot, ledger row, atomic read-back result, and optional
   project request path. Do not claim the project is rebound until the Planner
   applies and archives the request.
   If the loader returns `COMMITTED_CLEANUP_REQUIRED`, report every
   `cleanup_errors` entry and stop for lock-owner recovery. The package writes
   are committed, but this is not clean `READY`: do not run another re-pin,
   proceed to tests, or propose/perform a commit until the named lock state has
   been inspected and recovered.
6. Only after clean `READY`, run:

   `python scripts/repin_register_smoketest.py`

   Then run the reader-accessibility contract and milestone-framework suites.
7. Draft the single-purpose commit message emitted by the loader and list the
   pin-affecting files, snapshot, and ledger. Ask for approval before committing.
   Never auto-commit. If the host cannot write `.git`, hand back the cleanly
   prepared working tree and message. After the approved commit exists, record
   its immutable object ID without recomputing either pin:

   `python scripts/reader_accessibility_policy.py --backfill-repin-commit <40-or-64-character-object-id> --repin-epoch <N>`

   The loader requires that object to exist as a commit and be reachable from
   `main`. Commit or amend that ledger-only backfill according to the
   repository's release procedure. Never predict a commit ID or record a
   pre-commit value. If backfill returns `COMMITTED_CLEANUP_REQUIRED`, the
   pointer is already recorded: report `cleanup_errors` and stop for lock-owner
   recovery rather than retrying or claiming clean completion.

## Refusals are authoritative

- Existing fresh or stale lock: stop. Stale recovery needs `--force-lock` and
  separate explicit confirmation.
- Uncommitted earlier re-pin paths: commit or deliberately discard that work
  before a second re-pin.
- Pin-affecting dirt: stop regardless of `--allow-unrelated-dirty`.
- Unrelated dirt: list it; proceed only when the user supplied
  `--allow-unrelated-dirty`.
- Schema migration missing, graph/wiki/root unreachable, malformed graph/link
  contract, graph semantic eligibility missing or provisional
  (`GRAPH-SEMANTIC-INELIGIBLE`), stale research-page inventory, incomplete
  semantic output chain, non-conforming audit sample, or project open round:
  stop with the loader's exact reason. Never repin a `structural-only` or
  `pending` graph.
- A post-publication freshness refusal may preserve an inert project rebind
  request while rolling package files back. Report its exact path and have the
  Planner inspect and archive it before retrying; never delete or overwrite it
  as part of re-pin recovery. Bind the recovery to the request's exact bytes:

  `python scripts/assignment_milestone_checkpoint.py rebind-reader-policy --project-root <project-root> --archive-stale-request --expected-request-sha256 <sha256>`

  The Planner command refuses an open round, a wrong hash, or a request that
  matches the current profile (which must be applied rather than archived).

## Ownership boundary

Package writes are confined to the package profile, `repin_log.jsonl`, its
derived Markdown view, the package lock, and
`reviews/.harness/repin/epoch-<N>.snapshot.json`. With a project root, the only
skill-owned project artifact is the pending rebind request. The Planner alone
updates the binding fields and archives the applied request.
