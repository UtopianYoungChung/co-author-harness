# v0.43 C2 isolated-Python closure and retry C0 addendum

**Status:** approved package-maintainer boundary for closing the remaining
isolated-Python bytecode-emission class exposed by refused C2 attempt 002 and
for one new controller-owned retry. This addendum grants no package clearance,
shipment, cache mutation, consumer re-attestation, host qualification,
activation, research mutation, acceptance, promotion, release, or canon
authority.

**Run scope:** `adhoc_review`.

**Parent authority:**
`docs/superpowers/specs/2026-08-02-v043-c2-repair-retry-c0-addendum.md`.
All parent prohibitions and later gates remain binding. Any path not enumerated
here or in the parent ledgers requires another committed addendum before it is
created or changed.

## Frozen refused state

- Repository: `B:\Agents\platform\co-author-harness`.
- Branch: `main`, the only permitted branch.
- Commit: `cda7cdd26bb1efd6c5a1074d9d4e6726f56af48e`.
- Tree: `c7ec33e57d89145ea1efd80f1149d85b515a5885`.
- Refused attempt, frozen and never reusable:
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260802-attempt-002`.
- Attempt 002 ran all 93 suites / 97 cases cache-off. Every case returned its
  expected result, cache hits were zero, and tested-input canonical and raw
  digests were stable, but the controller refused
  `RELEASE-CONTROLLER-OUTPUT-SCOPE`. Corpus success is not C2 qualification.
- The attempt-002 product manifest is present at
  `docs/analysis/generated/fixture_manifest.json`, 54,252 bytes, SHA-256
  `74b978da52643fdf0cbd22f3a7e4a5e32cddfb4f7125ad34632e636e05c34fa7`.
  It is failed-transaction output: it may not be committed or treated as
  qualified evidence and must be voided by the next authoritative run.

Attempt-002 controller evidence is:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `receipt.json` | 3,320 | `ac10ed610988a7620de1fd2e0f860eced2b9036c5c14cf4c34b2860081508772` |
| `exit.json` | 755 | `6e40af8d2d6f1940eafc8a5f03b177ad57aa3c931465c878a63b4aee61762cf2` |
| `journal.json` | 765 | `d05b640bcde8e7fb2ccfcf76b245df059c47d08968030710acd9da48ffdc0fa8` |
| `owner.json` | 114 | `e68cd680725302f7f903679b03248b53a96cf6354dbcb66ca5b2f17422424451` |
| `intent.json` | 639,573 | `902117d6592de2b7a417845e3db45a7defa13047a0e3ee9e7994dd77cfd42c71` |
| `stdout.bin` | 9,744 | `05fd2ebfe703f0f0e8741d06661d084acf07e14b052492e4a635d1963c9973a2` |
| `stderr.bin` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

The unauthorized delta is
`scripts/__pycache__/milestone_framework_smoketest.cpython-314.pyc`.
Its controller-frozen preimage was 174,111 bytes, SHA-256
`2770ee1309e1fe17509e5ff519ab562fd5446936ede3353eb29bee9ca2cf7b55`;
its refused postimage is 174,207 bytes, SHA-256
`057add644f960be03a9d09f7bba000f43f1981531e64b1cf947e4c8a013896fb`.
The postimage is hash-bound evidence, not package state. After this addendum is
committed it may be removed only by an exact resolved-path, size, and hash
guard, leaving all other pre-existing ignored bytecode untouched.

## Architectural cause and required scope

Attempt 001 proved that `python -I` ignores inherited
`PYTHONDONTWRITEBYTECODE`; attempt 002 proved that repairing only the first
observed emitter is insufficient when pre-existing ignored bytecode masks
other isolated launchers. The direct attempt-002 emitter was the isolated
`domain_native_register_smoketest.py` child launched by
`reader_accessibility_contract_smoketest.py`; that child imports
`milestone_framework_smoketest.py`.

A repository-wide AST audit found 17 executable isolated-Python command
expressions across ten files that contain `sys.executable` plus `-I` or `-S`
without `-B`. This addendum closes that entire syntactic class and adds a
static regression to the existing subprocess policy test before another full
corpus is permitted.

## Authorized tracked paths

Only these tracked paths may change in this repair slice:

| Action | Path | Bytes | SHA-256 / preimage |
|---|---|---:|---|
| CREATE | `docs/superpowers/specs/2026-08-02-v043-c2-isolated-python-retry-c0-addendum.md` | 0 | `ABSENT` |
| MODIFY | `scripts/derived_handoff_policy_smoketest.py` | 34,020 | `1d5b7f6ffd7d1fa288b11f5989d470159badbe26b66395fa5be4eff1eba52cdd` |
| MODIFY | `scripts/migrate_legacy_milestones.py` | 61,012 | `09d4271dc38c47779178df33ec66689e7e7774a94ca028199a5e986884fc88f3` |
| MODIFY | `scripts/migrate_legacy_milestones_adversarial_smoketest.py` | 18,100 | `821996f1c9be50c59bf82919c8fe95e5280d794d9039ff0fbcf917f33f73c13c` |
| MODIFY | `scripts/migrate_legacy_milestones_smoketest.py` | 32,780 | `d87036ae2e3a1abaee36fe76ea75139267f7513402bfeb07d6b7f4591e968a33` |
| MODIFY | `scripts/native_project_bootstrap.py` | 17,123 | `021dbd34cf5420a711f0a22271af2c3762f95fe79e503397af214cd649d6f33c` |
| MODIFY | `scripts/native_project_bootstrap_adversarial_smoketest.py` | 9,563 | `e7c41254283544579ccb302c07b6d883f9e50afb3a70661b4ee6eb78032c7fb0` |
| MODIFY | `scripts/native_project_bootstrap_smoketest.py` | 12,784 | `352345548760db6df04367f43e44ac4a0a6f4fd986cac1f4415cfff7dd1948e5` |
| MODIFY | `scripts/reader_accessibility_adversarial_smoketest.py` | 12,123 | `9f38fc2366ce7e9e83ba7f59731d64fa03d48957bb1c2e76b3a1023c242f5480` |
| MODIFY | `scripts/reader_accessibility_contract_smoketest.py` | 17,957 | `37bc81a1bc9ccb7099139b8b82a28ff9032590a36452c54e1d3f3b4fa8ad6a54` |
| MODIFY | `scripts/render_lifecycle_state_smoketest.py` | 4,141 | `6258b9cd6b1bb513b2d9162f973c1667179e5d628dcf7b22506be2593df7927a` |
| MODIFY | `scripts/subprocess_text_policy_smoketest.py` | 4,636 | `526599a5ab0f315a45ed01ea99481852baeb027629f02de546ad9d063f463229` |
| MODIFY | `docs/analysis/generated/fixture_manifest.json` | 54,252 | `FAILED_ATTEMPT_002_OUTPUT` |

The pre-existing ignored C2 evidence files authorized by the parent may be
updated to bind the second refusal, repair, and retry results. No new evidence
filename is authorized here.

## Required red-to-green repair

1. Preserve attempt 002 and its output-scope refusal. Do not convert its green
   case exits or manifest into source qualification.
2. Extend `subprocess_text_policy_smoketest.py` so an executable Python command
   expression containing `sys.executable` and `-I` or `-S` must also contain
   `-B`. It must cover direct list/tuple commands and composed expressions such
   as the reader-accessibility contract command.
3. Add `-B` to all 17 audited isolated command expressions. Preserve argument
   semantics, including any code that indexes the script path after inserting
   the interpreter flag.
4. After the exact failed `.pyc` postimage is removed by guard, run the static
   policy red-to-green check, all directly affected smoketests, and the two
   affected production-path checks. Require zero created, changed, or removed
   `.pyc` across a repository-wide before/after census.
5. Obtain independent B0/M0/m0 review and commit the exact repair before any
   new full corpus.

## Authorized retry path and gates

The only new transient qualification path is:

`C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260802-attempt-003`

It must be absent before creation, receive a controller owner marker, and use
the same cache-off full-registry request as attempt 002 on the committed repair
bytes. Attempts 001 and 002 remain immutable. Attempt 003 may publish the
fixture manifest only if all suites and cases pass, cache hits are zero, tested
inputs are stable, process closure is complete, and the controller observes no
unauthorized output. All terminal artifacts and pre/post censuses must be
hash-bound before cleanup or a pass claim.

After a green source-root transaction, run the parent-authorized detached
read-only replay and obtain independent B0/M0/m0 review. Any ambiguity,
additional output, new failing case, incomplete process evidence, source drift,
or unledgered path is a stop. Version, package, cache, clearance, remote, and
fresh-host gates remain closed until C2 is green and committed.
