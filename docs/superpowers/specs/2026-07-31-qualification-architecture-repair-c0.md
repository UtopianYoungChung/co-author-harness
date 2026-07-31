# Qualification architecture repair C0 freeze

**Status:** approved package-maintainer implementation boundary; no academic
lifecycle, research mutation, shipment, installation, or host-qualification
claim is authorized by this file.

**Run scope:** `adhoc_review`.

**Baseline:** branch `main`; commit
`759ec278c846bc29696be84df81b0f5e41c8381f`; tree
`2330a37e06f37fcb1fe98c9f2b3a93762593e198`; local `origin/main`
`67be86bc33127cf711084e717403b5e399191ab5`; ahead 33, behind 0; clean source;
one worktree; package version `0.42.0`.

**Preserved state:** stashes
`4cab725415f1aa92482c2568f9dacb54dba1806c` and
`e9fb3df15939faca4c08e8fb65985adbeee38146`; persistent runner lock SHA-256
`e0c6e2a94370231c7851717d0035fb590831082700f6c70ca24067671baad4ae`
with dead PID 89140. The two pre-existing `.coauthor-fic-sbx` sandboxes are
preserved in place as abandoned evidence: their internal PIDs 60044 and 34700
are dead, their owner is the current Windows user, and no live process refers
to them. They are not deleted or reused.

**Observed host anomalies:** this task's startup skill catalog names the absent
`0.41.0` skill root while CLI/cache resolve `0.42.0`; local marketplace metadata
is `0.37.1` (748 bytes, SHA-256
`478389a5f646a0b6e7e2d4210e46450ad6e726e60ffd8e2ade99b91667f2f9cb`).
The installed cache manifest is 674 bytes, SHA-256
`25f801100daecb1539208b78cf550e99c200dadfb1344c083386b5e306d1fa60`;
its provenance is 1,127 bytes, SHA-256
`0defb67ef2f9785ccd4f7696cec8101bf59e9f05013f69cf6b2fe716e4f66cb1`,
and binds the baseline commit. CLI/cache agreement is not startup or loaded-path
qualification.

**Environment:** no ambient `PYTHON*` variables; Git Bash exists at
`C:\Program Files\Git\bin\bash.exe` and is absent from PowerShell `PATH`;
`pytest` command/module is absent. Direct Python smoketests remain authoritative.

**Token baseline:** `cl100k_base`, `tiktoken 0.12.0`; 128 measured files; 120
breaches (115 fail-tier, 5 warn-tier); always-loaded floor 15,274 against the
target of at most 8,000. This is debt to ratchet, not a pass.

## Frozen non-overlapping ledger

Lane A owns only its five rows. Lane B owns only its eleven rows. Lane C owns
only its eight rows. Root owns every integration/version row. The shared
environment helper belongs to Lane A; Lane B imports it. `release-gate.sh` is
Lane A's implementation path but its final integration is Root-reviewed. Any
new path requires a committed C0 addendum before mutation.

| Owner | Action | Path | Bytes | SHA-256 / preimage |
|---|---:|---|---:|---|
| A | MODIFY | `scripts/release-gate.sh` | 40,981 | `d4a8def74d4dd0efaa6c4cf33e433f060df977e6632883cb74ab021110c4253e` |
| A | CREATE | `scripts/qualification_environment.py` | 0 | `ABSENT` |
| A | CREATE | `scripts/release_qualification_controller.py` | 0 | `ABSENT` |
| A | CREATE | `scripts/release_qualification_controller_smoketest.py` | 0 | `ABSENT` |
| A | CREATE | `references/schemas/release_qualification_controller.schema.json` | 0 | `ABSENT` |
| B | MODIFY | `scripts/runtime_plane_probe.py` | 46,955 | `de053a9aeebc358e40a805cc22099c7ff1c258c500f72e5d4c0d9cda95a2c296` |
| B | MODIFY | `scripts/runtime_plane_probe_smoketest.py` | 23,018 | `921c0807557c0eb3403b53c11ec06a9d61a65ec3d39e1b00b25e8c227d04f301` |
| B | MODIFY | `references/schemas/runtime_plane_receipt.schema.json` | 10,217 | `c18a5817e6466ed876a52a65ff8e70bbdfd18f727a14df72ee53c106721ec5fb` |
| B | MODIFY | `scripts/archive_runtime_probe.py` | 33,266 | `d0ab9b184bded3115b40b9944f71c6ad4f349ed2f740c6ab3ebcbd68da429498` |
| B | MODIFY | `scripts/archive_runtime_probe_smoketest.py` | 23,229 | `c1f77bf695f04997cb5eb74ffa677abf7a76a6ac972b39055b123dea0de9bd49` |
| B | MODIFY | `references/schemas/archive_runtime_receipt.schema.json` | 9,544 | `30c26dd081af0735b5f969eaaea9af3e4faea35513183022324bcc7418313ae9` |
| B | MODIFY | `scripts/build-plugin.py` | 31,421 | `7c0471cb7d51301359cd0fce4cefbf5d5afe18598afc8cb6bff2fe348137cd85` |
| B | MODIFY | `scripts/build_plugin_provenance_smoketest.py` | 39,181 | `a07d9b534c28b7f9fba67f264e6a884ce37fe9eac4318a48a6be901bdac42f60` |
| B | CREATE | `scripts/qualification_plane_topology.py` | 0 | `ABSENT` |
| B | CREATE | `scripts/qualification_plane_topology_smoketest.py` | 0 | `ABSENT` |
| B | CREATE | `references/schemas/qualification_plane_topology_receipt.schema.json` | 0 | `ABSENT` |
| C | MODIFY | `scripts/token_budget_check.py` | 10,766 | `105de5f6f314fb0c23349b7f6aed91f0661ad06f2e1d19ed39f905c6fe16eec5` |
| C | MODIFY | `scripts/token_budget_smoketest.py` | 4,554 | `f43db1e487efca3107d99381cc0dcb3bd79dd399502e40972fe8955d07780599` |
| C | MODIFY | `references/TOKEN_BUDGET_PROTOCOL.md` | 8,120 | `2e95c049223b92b1d42803af65428a3168a19a8b4db2857b4af30abf9745630f` |
| C | CREATE | `references/policies/token_budget.v1.json` | 0 | `ABSENT` |
| C | CREATE | `references/schemas/token_budget_policy.schema.json` | 0 | `ABSENT` |
| C | MODIFY | `scripts/host_qualification_transaction.py` | 30,723 | `450ef89bec0aa3ef59403917275013f8634101e465728111e2e6e1d34ff7dba3` |
| C | MODIFY | `scripts/host_qualification_transaction_smoketest.py` | 31,398 | `172a574798e7dc8056ef58d43997939bfea1a03c60084b39976a19fe42568afa` |
| C | MODIFY | `references/schemas/host_qualification_transaction.schema.json` | 9,352 | `a0f50b81749593105593b36eef9d5ac05f9fd03a25afaf4cf4a856ee40316b1c` |
| Root | CREATE | `docs/superpowers/specs/2026-07-31-qualification-architecture-repair-c0.md` | 0 | `ABSENT` |
| Root | MODIFY | `scripts/analysis/fixture_runner.py` | 39,261 | `da4b4edef987653be9118f1ea249f257ee47bf9e00ea2c57386896bfabf02d0c` |
| Root | MODIFY | `docs/analysis/generated/fixture_manifest.json` | 53,094 | `0cab9ae3f88b51f74fbb4f3d3e24a06ee31559cdef73e8201cc5ffcc4e892c9b` |
| Root | MODIFY | `references/destination_coverage_registry.json` | 14,317 | `cd99cd8a7000c92494ec2656c7a05eef986edc2d6fe6a0fd9e2c012f6aa24a75` |
| Root | MODIFY | `references/MANIFEST.md` | 28,859 | `d999e66a6222a2f5d93f60ede89ea27bf56da4fa9400b05272de5ba185fcfb39` |
| Root | MODIFY | `references/DETERMINISTIC_CHECKS.md` | 46,681 | `edb3beba6214a9d33c04b12e7d2303e165a510d13537c108d81d2263237e9798` |
| Root | MODIFY | `references/contract_kernel.v1.json` | 33,281 | `14a4c052239c137dc0f2cfe7dd887e65aba2de59c7b7a2b38f755cfcf44002ad` |
| Root | MODIFY | `references/compatibility/shipment-v2/contract_kernel_projection.json` | 2,907 | `ea5143e3cfa66bac760d2fea0cdbacb8429543461346e723c482bace1aae877d` |
| Root | MODIFY | `references/compatibility/shipment-v2/compatibility_profile.json` | 4,510 | `8b48f33b15e89063aa77772f54d9c5b8bb33752c94a63dc0afb2ce54d6e1badc` |
| Root | MODIFY | `scripts/schema_runtime_check.py` | 9,709 | `31e139b3d630b485e48eda2a4212379855c7a6da58abd89ca26cb76275584f83` |
| Root | MODIFY | `.github/workflows/structural-checks.yml` | 2,570 | `e42df94389504340c8fee3e185d1a753c8042e48ac80cf5d0f9aca111e8feed5` |
| Root | MODIFY | `references/schemas/release_evidence_index.schema.json` | 4,608 | `583de8f7f959538f90cd4e96ac3711754f3ee92d5c00fd288a97b3ddca8d363c` |
| Root | MODIFY | `scripts/release_evidence_index.py` | 8,292 | `18d9bc000a737070547720d987ebe4d9b41edc429841d6984f1179636a045f23` |
| Root | MODIFY | `scripts/release_evidence_index_smoketest.py` | 5,064 | `91fed2efd704d16d6596fdca73eb2c6e063df3f87196a3eb8fc4b9571e2207c9` |
| Root | MODIFY | `CHANGELOG.md` | 390,689 | `eee78a4eb0edb693f44350e71052e3c40ca44fbf299b8c73e10cbeb8552a478c` |
| Root | MODIFY | `README.md` | 39,512 | `8f6b62302dae0303db8964d5c47d9b92aee0212ac76719a230ab14a3b5adda23` |
| Root | MODIFY | `.claude-plugin/plugin.json` | 674 | `25f801100daecb1539208b78cf550e99c200dadfb1344c083386b5e306d1fa60` |
| Root | MODIFY | `.claude-plugin/marketplace.json` | 1,425 | `69a330f66b9561b98f55b08d81999a777a3a13430d888d33de31cfd21d1a3055` |
| Root | CREATE | `docs/release-notes/RELEASE_NOTES_v0.43.0.md` | 0 | `ABSENT` |

All existing paths have Git mode `100644`. Both pre-edit rechecks observed 43
candidate paths, zero candidate-key collisions, zero CREATE collisions, zero
ancestor reparse points, zero related competing processes, the same clean
commit/tree/worktree/stash/lock state, and zero ambient `PYTHON*` variables.

## Stop gates

Stop on dirty or concurrent state, path overlap, any unledgered path, protected
destination, schema/runtime divergence not repaired by this ledger, ambiguous
sandbox ownership, or broadened authority. Red regressions land before their
repairs. A green suite is not package clearance; package clearance is not
shipment, installation, startup-catalog agreement, loaded-path agreement,
fresh-host qualification, research acceptance, or activation.
