# v0.43 C2 ambient bytecode invocation retry C0 addendum

**Status:** approved package-maintainer boundary for replacing the
pretransaction-refused attempt 013/unused attempt 014 labels with one fresh
source transaction and one fresh detached transaction. This addendum grants no
package clearance, shipment, cache mutation, consumer re-attestation, host
qualification, activation, research mutation, acceptance, promotion, release,
or canon authority.

**Run scope:** `adhoc_review`.

**Parent authority:**
`docs/superpowers/specs/2026-08-03-v043-c2-final-postimage-freeze-c0-addendum.md`.
All parent gates and exact committed repair bytes remain binding.

## Frozen pretransaction refusal

- Repository HEAD: `fba689c7c5a693f1a30d39c47697feae888773f0`;
  tree: `30e23837b396b9e70e3bffbe6fb10a449a885d0e`.
- The source worktree is clean. Its governed bytecode baseline remains exactly
  180 files and four `__pycache__` directories.
- The attempt-013 command supplied
  `--env PYTHONDONTWRITEBYTECODE=1`. The controller refused it with
  `QUALIFICATION-ENV-DELTA: caller may not inject Python controls` before
  creating the run directory or launching any corpus process.
- The exact attempt-013 path remains absent. Its label will not be reused.
  Attempt 014 was reserved for a detached replay contingent on successful 013;
  it remains absent and will not be repurposed.

The correct contract is to place `PYTHONDONTWRITEBYTECODE=1` in the ambient
frontend environment, omit the forbidden `--env` delta, and retain explicit
`-B` on both controller and fixture-runner interpreter command lines. The
controller then sanitizes and records the controlled child environment itself.

## Fresh exact paths and gates

Only these new paths are authorized:

- source-root attempt 015:
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260803-attempt-015`;
- detached replay attempt 016:
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260803-attempt-016`;
- detached worktree:
  `B:\Agents\.coauthor-v043-c2-detached-retry-4`.

All three paths were verified absent before this addendum. Attempt 015 must use
the exact committed repair tree, `--tier full --cache-mode off`, the source root
as its sole watch root, the manifest as its sole allowed output, and only the
exact shared runner lock as ignored output. Require 93 suites / 97 direct cases,
zero failures, zero cache hits/misses, stable canonical/raw inputs, exact
180-file bytecode postflight, empty stderr, zero live identities, and terminal
success before committing only the resulting manifest.

Only after that exact manifest commit may retry-4 be created at the exact
committed tree. Attempt 016 must use `--tier full --no-write --cache-mode off`,
watch both retry-4 and the primary root, allow no package output, and ignore
only the exact shared runner lock. Require primary 180/four and detached
zero/zero before and after, stable Git administration, no external Git/cache
activity, 93/97 direct green execution, stable inputs, empty stderr, zero live
identities, and terminal success. Any warning, residue, refusal, incomplete
evidence, failed case, cache activity, or review finding is a stop.

C2 and every later version, package, cache, clearance, remote, shipment,
fresh-host, startup-catalog, loaded-path, consumer, activation, research,
acceptance, promotion, release, and canon claim remain closed.
