# Assignment dispatch preflight fixtures

These fixtures encode blocker shapes only. They are synthetic, deliberately non-authoritative, and must never be treated as assignment contracts, gate acceptance, or milestone acceptance evidence.

- `fresh_skip_gate/` mirrors the incident class: Ph1 manuscript bytes exist, M1-M3 are reopened, M4 requires revision, and both the assignment contract and READY receipt are absent.
- `wrong_target_m4/` has a deliberately unresolved fixture contract, non-accepted M1 state, and a deliberately invalid fixture receipt that claims M4. Calling preflight for the derived M1 target must fail with `APG-RECEIPT-TARGET-MISMATCH` before any write.

The smoketest reads these directories in place and verifies byte-for-byte that preflight does not mutate them.
