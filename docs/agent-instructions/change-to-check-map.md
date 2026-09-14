# Change-to-check map

Use this map for ordinary scoped development in the harness checkout. It identifies the cheapest check that can falsify a local change. It does not convert a focused pass into release qualification, independent review, shipment, installation, catalog, host, consumer, or research authority.

## Validation levels

1. **Focused development check**: run the mapped validator and directly affected smoketest(s). This is the default after a scoped edit.
2. **Structural census**: run the package-root maintainer scripts in `AGENTS.md` when a change crosses several contract surfaces or before handing a candidate to another maintainer.
3. **Authoritative fixture corpus**: run `python scripts/analysis/fixture_runner.py --no-write` before release qualification, after changing the fixture registry/census/cache infrastructure, or when the mapped rows below explicitly require it. The corpus is intentionally complete and may be long-running.

`python scripts/analysis/fixture_runner.py --tier quick --no-write` is a non-authoritative diagnostic sample. It is useful for rapid feedback but never substitutes for the full corpus at a release or qualification gate.

## Subset corpus (`--suite`)

A changed area can run one or more `REGISTRY` keys without paying the full
~111.5-minute corpus:

```bash
python scripts/analysis/fixture_runner.py --list
python scripts/analysis/fixture_runner.py --suite scripts/version_policy_smoketest.py --no-write
python scripts/analysis/fixture_runner.py --suite version_policy_smoketest --suite destination_capability_smoketest --no-write
```

`--suite` accepts an exact registry path from `--list`, a unique basename, or a
unique stem. Repeat the flag to run several keys. The selection is
`NON_AUTHORITATIVE_PARTIAL` and cannot write or void the committed fixture
manifest. The full corpus remains:

```bash
python scripts/analysis/fixture_runner.py --no-write
```

Use that full command at release/qualification gates and after runner, census,
cache, or registry-membership changes. Direct `python scripts/<name>_smoketest.py`
and `--suite <same key>` are both valid focused paths; `--suite` goes through
the runner lock and registry invocation.

## Map

| Changed surface | Focused checks | Direct behavioral check | Full corpus required before ordinary handoff? |
|---|---|---|---|
| `agents/**`, ordinary `skills/*/SKILL.md` | `python scripts/skill-check.py`; `python scripts/command_surface_check.py` when exposure changes | Run the named skill's registered smoketest when one exists | No |
| Phase participation or dispatch routing | `python scripts/phase_engagement_check.py`; `python scripts/version-planes-check.py` | Relevant alias, phase, or routing smoketest | No |
| `references/schemas/**`, role/output, shipment, or lifecycle contracts | `python scripts/schema_runtime_check.py`; `python scripts/contract-kernel-check.py` | `python scripts/contract_kernel_coherence_smoketest.py` plus the schema's named smoketest | No, unless registry/census behavior changed |
| `references/contract_kernel.v1.json` or a kernel-bound component | `python scripts/contract-kernel-check.py`; `python scripts/schema_runtime_check.py` | `python scripts/contract_kernel_coherence_smoketest.py` | No |
| `references/compatibility/shipment-v2/**` | `python scripts/schema_runtime_check.py` | `python scripts/contract_kernel_coherence_smoketest.py`; `python scripts/shipment_manifest_smoketest.py` | No |
| Destination policy, bootstrap, staging, or output routing | `python scripts/destination-coverage-check.py` | `python scripts/destination_capability_smoketest.py`; the changed command's smoketest | No |
| Version or host identity (`version.json`, `plugin.json`, Agent Plugins `$schema`) | `python scripts/version-check.py`; `python scripts/manifest-coherence-check.py`; `python scripts/ssot-check.py` | `python scripts/version_policy_smoketest.py` | No |
| Packaging, release gate, runtime/archive plane | `python scripts/version-check.py`; Bash syntax check for changed shell files | `python scripts/build_plugin_provenance_smoketest.py`; `python scripts/runtime_plane_probe_smoketest.py`; applicable release negative checks | Yes before release qualification; not for a local documentation handoff |
| Command catalog or capability disposition | `python scripts/catalog-check.py`; `python scripts/command_surface_check.py` | Capability- or alias-specific smoketest | No |
| Snippets or runtime snippet consumers | `python scripts/snippet-check.py` | Consumer skill's smoketest | No |
| Documentation and links | `python scripts/path-hygiene-check.py`; `python scripts/manifest_links_check.py`; `python scripts/retirement-sweep-check.py` | None unless the document is a machine-consumed contract | No |
| Ordinary task source support, traces, archives or timing | `python scripts/contract-kernel-check.py`; `python scripts/destination-coverage-check.py` | `piw_acceptance_smoketest.py`, `piw_research_support_smoketest.py`, `piw_trace_io_smoketest.py`, `piw_archive_smoketest.py`, `hermes_host_smoketest.py` under `scripts/` | No, unless registry/census changes |
| Golden or research artifact scoring | `python scripts/contract-kernel-check.py` | `python scripts/golden_eval_smoketest.py`; `python scripts/research_artifact_eval_smoketest.py` | No, unless registry/census changes |
| Distribution inventory or rights | `python scripts/distribution-rights-check.py` | `python scripts/distribution_rights_smoketest.py` | No |
| Output-economy contracts | `python scripts/output_economy_check.py` | `python scripts/output_economy_smoketest.py` | No |
| Commitment interactions | `python scripts/commitment-interactions-check.py` | Relevant interaction smoketest, if registered | No |
| `scripts/analysis/fixture_runner.py`, `fixture_cache.py`, `code_census.py`, or registry membership | `python scripts/analysis/fixture_infrastructure_check.py`; `python scripts/analysis/fixture_runner.py --list` | Targeted runner/cache self-tests | **Yes** |
| A new or removed `*_smoketest.py` / registered suite | `python scripts/analysis/fixture_infrastructure_check.py`; `python scripts/analysis/fixture_runner.py --list` | Run the suite directly first | **Yes** |

## How to find the direct check

1. Search the registry: `python scripts/analysis/fixture_runner.py --list`.
2. Search references to the changed path: `rg -n "<filename-or-contract-id>" scripts references`.
3. Run the matching script directly, for example `python scripts/contract_kernel_coherence_smoketest.py`, or the same key through the runner: `python scripts/analysis/fixture_runner.py --suite scripts/contract_kernel_coherence_smoketest.py --no-write`.
4. Run the mapped focused validators.
5. Escalate to the structural census or full corpus only when the change surface or gate requires it.

When no direct test exists, report that gap. Do not describe a generic linter, type checker, formatter, or repository-root test command as present unless the repository actually provides it.
