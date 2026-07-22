# Producer-Boundary Phase A — Baseline Receipt

**Date:** 2026-07-22. **Repo:** `B:\Agents\platform\co-author-harness`,
branch `main`, HEAD `32bf9d4`, working tree clean at run start.
**Scope:** baseline recording only; no behavior change. Companion inventory:
`docs/analysis/2026-07-22_mutation-surface-inventory.md`.

## Battery results (host-side, Windows Python 3)

| Command | Exit |
|---|---|
| `python scripts/skill-check.py` | 0 |
| `python scripts/version-check.py` | 0 |
| `python scripts/distribution-rights-check.py` | 0 |
| `python scripts/catalog-check.py` | 0 |
| `python scripts/command_surface_check.py` | 0 |
| `python scripts/path-hygiene-check.py` | 0 |
| `python scripts/snippet-check.py` | 0 |
| `python scripts/output_economy_check.py` | 0 |
| `python scripts/version-planes-check.py` | 0 |
| `python scripts/commitment-interactions-check.py` | 0 |
| `python scripts/retirement-sweep-check.py` | 0 |
| `python scripts/analysis/fixture_infrastructure_check.py` | 0 |
| `python scripts/analysis/fixture_runner.py --no-write` | **1** (see below) |
| `python scripts/assignment_milestone_checkpoint_smoketest.py` | 0 |
| `python scripts/assignment_terminal_close_smoketest.py` | 0 |
| `python B:\Agents\research\99_System\tools\qe_workspace_guard.py` | 0 (`Errors: 0`, `OK No findings.`) |

## Pre-existing fixture failure (recorded, not fixed)

`fixture_runner.py --no-write` reports exactly one failing case:
`scripts/build_plugin_provenance_smoketest.py::default`. All other registered
fixtures PASS; `--no-write` preserved prior manifest evidence.

Characterization (two runs on identical clean HEAD):

- Root symptom: `git clean -qfdx` returns exit 1 inside the smoketest's
  disposable sandbox clone under `B:\Agents\platform\.coauthor-provenance-sbx\`,
  raising `CalledProcessError` and cascading through subsequent cases.
- The failing-case boundary is **not stable**: via `fixture_runner.py` nine
  cases failed starting at `case_dirty_unstaged_ignored`; run directly, those
  passed and the first failure moved to `case_staged_rename_ignored`.
- Verdict: pre-existing, environment-sensitive (sandbox file lock or
  permission interference during `git clean`), present on clean `main` before
  any producer-boundary work. Not logic drift in the harness.

Baseline rule going forward: this is the accepted baseline state. Any
producer-boundary phase must leave every currently-green surface green;
`build_plugin_provenance_smoketest.py` flakiness is tracked separately and is
not a regression signal for this work unless its failure mode changes.

## Verified command-surface facts

- Public milestone CLI verbs (`scripts/assignment_milestone_checkpoint.py`
  line 19): `derive`, `begin`, `record`, `accept`, `rebind-reader-policy`,
  `recover`. No public `register`/`release`/`ship`/`close`.
- All canonical-Wiki mutation paths already fail-closed
  (`WIKI_WRITE_TRANSACTION_UNAVAILABLE`); only automatic attempt wiring
  remains live (see inventory §D).
