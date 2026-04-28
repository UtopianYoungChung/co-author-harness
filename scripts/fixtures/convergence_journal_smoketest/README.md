# convergence_journal smoketest fixture

`minimal_project/reviews/convergence_journal.jsonl` — two P-4 rows with **scalar** `convergence_metric` (float). Representative of v0.7.5+ project state.

Originally authored as the input fixture for the v0.8.0 P2.1d
`migrate_convergence_journal_v075.py` determinism gate; the migration script
was retired at v0.11.0 c5 (the convergence-journal schema has been stable
since v0.7.5 and no fresh project requires migration). The fixture is
preserved as representative project state for other potential smoketests
(c10 end-to-end ladder smoketest re-uses similar layouts).
