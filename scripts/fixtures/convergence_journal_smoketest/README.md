# convergence_journal migration smoketest (v0.8.0 P2.1d)

`minimal_project/reviews/convergence_journal.jsonl` — two P-4 rows with **scalar** `convergence_metric` (float).

Used by `scripts/release-gate.sh` Phase 0.695: `migrate_convergence_journal_v075.py --dry-run` twice (`cmp` on stdout), then a temp-directory **write + re-run** idempotency check (second migration leaves bytes unchanged).
