# v0.43 Linux kernel-containment C0 addendum

**Status:** approved package-maintainer boundary for closing the last exact
Linux/WSL process-tree ownership gap. This grants no C2 qualification, version,
package clearance, shipment, cache mutation, consumer re-attestation, host
qualification, activation, research mutation, acceptance, promotion, release,
or canon authority.

**Run scope:** `adhoc_review`.

**Parent authority:**
`docs/superpowers/specs/2026-08-03-v043-exceptional-tree-closure-c0-addendum.md`.

The dedicated child-subreaper anchor now contains inner-worker death, exact
pidfd signaling, owner loss, interruption, and deadline cleanup. Independent
review correctly found one remaining boundary: arbitrary `SIGKILL` of that
anchor is not kernel-cascaded on stock Linux, so its adopted suite descendants
can outlive the supervisor. The parent contract requires complete owned-tree
termination on every failure path; a documented caveat is not sufficient.

This host exposes cgroup v2 and a functioning systemd user manager, while its
cgroup root is not directly writable. A transient systemd user service is the
available governed kernel ownership primitive. Linux/WSL execution must refuse
before suite bytes execute when the required service/cgroup properties cannot
be proved.

## Exact writable ledger

| Action | Path | Preimage bytes | Preimage SHA-256 |
|---|---|---:|---|
| CREATE | `docs/superpowers/specs/2026-08-03-v043-linux-kernel-containment-c0-addendum.md` | 0 | `ABSENT` |
| MODIFY | `scripts/analysis/fixture_process_supervisor.py` | 49,609 | `8e89973849a5430f4f2ac6777a55b66cc7d469c123c53628c7694149e8b2702f` |
| MODIFY | `scripts/analysis/fixture_infrastructure_check.py` | 61,630 | `acf84f125a974163272be06bcaed3a028061d672d74e72636bc35a42994b013b` |
| MODIFY | `references/destination_coverage_registry.json` | 14,556 | `3ca322cd8a88965d21df5aa5f6ec0046c5392449f30b095982e75027718a3996` |
| MODIFY | `references/contract_kernel.v1.json` | 37,588 | `78acc03740c7c67ce1232127253943a3022a9bea8e347d5538afd0c3042b90e8` |
| MODIFY | `references/compatibility/shipment-v2/contract_kernel_projection.json` | 2,907 | `cedaf4aaa1bd11397d97968e360124b34c9b947596087738959f75f7407535a5` |
| MODIFY | `references/compatibility/shipment-v2/compatibility_profile.json` | 4,510 | `80490de9461b02d3d2d444803cacb06af982a61969f2f5249f8d5a8155ed5f56` |

## Exact mechanism boundary

On Linux/WSL, launch the trusted anchor as the main process of one unique,
collected transient systemd **user service** in cgroup v2. The unit must prove
`KillMode=control-group`; anchor exit or death must cause the manager to kill
every remaining unit process. The anchor remains the sole child subreaper and
uses revalidated pidfds plus two empty scans for ordinary cleanup.

The parent must transmit the exact suite specification, including environment,
through an inherited pipe/stdin protocol, never command-line arguments or a
durable file. The same live channel provides owner-loss EOF. Result and byte
capture remain pipe/anonymous-temporary-file data. A unique unit name may be
created only for the current suite and must be collected after terminal state.
No persistent user-manager configuration, global daemon setting, cgroup-root
write, privileged operation, or caller-selected destination is authorized.

Add focused WSL regressions that kill the service main anchor after product
spawn and prove: the cgroup becomes empty, a delayed mutation is impossible,
the result is typed refusal, unrelated processes survive, and the unit is
inactive/collected. Also prove missing systemd user manager, non-cgroup-v2
topology, or unproven `KillMode` refuses before suite bytes. Preserve the single
absolute deadline, environment privacy, cache/evidence gating, and every prior
adversarial case.

After exact focused native/WSL tests pass, refresh only changed destination
pins, bind only changed kernel component hashes, then update the projection and
profile hashes mechanically. Freeze exact postimages and obtain fresh
B0/M0/m0 review before any corpus transaction. Any additional tracked path,
persistent service state, weakened test, warning, skip, or residual failure
path is a stop.
