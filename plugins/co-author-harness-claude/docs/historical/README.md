# Historical audit artifacts

This directory archives point-in-time audit reports and integration summaries that were once siblings of the live rule files in `references/`. They are preserved as history; they are **not** load-bearing under the current substrate.

If a current rule cites one of these files, the citation is itself a drift signal — the rule should be re-anchored against a live rule file (e.g., `references/DRIFT_CHECK.md` for drift discipline, `references/CHANGELOG.md`-equivalent for version archaeology).

## Contents

| File | Original location | Date archived | Reason |
| --- | --- | --- | --- |
| `DRIFT_CHECK_REPORT_2026-04-13.md` | `references/` | 2026-04-27 (v0.11.0) | Point-in-time drift report; not a rule. |
| `DRIFT_CHECK_REPORT_2026-04-13-synergy.md` | `references/` | 2026-04-27 (v0.11.0) | Same. |
| `DRIFT_CHECK_REPORT_2026-04-16-v0.3.1.md` | `references/` | 2026-04-27 (v0.11.0) | Same. |
| `PACKAGE_INTEGRATION_SUMMARY_2026_04_13.md` | `references/` | 2026-04-27 (v0.11.0) | One-shot integration summary; superseded by `CHANGELOG.md`. |

The active drift-check rule remains at `references/DRIFT_CHECK.md` and is invoked by the Reflector's Phase 2.6 gate.
