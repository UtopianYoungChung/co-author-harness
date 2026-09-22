# `fixture_runner` tree mutation: caused by a concurrent session, not by the corpus

**Status.** Resolved. `fixture_runner` has no defect. Its refusal was correct and
its cause is external: another session writing enumerated files while the run was
in flight. Nothing in the corpus, the registry, or the runner needs changing.

**Date.** 2026-09-22. **Established at.** `aeeb9fe`, by a controlled comparison
between a shared checkout and a frozen detached worktree.

---

## The symptom

`python scripts/analysis/fixture_runner.py --no-write` completes the corpus and
then refuses its own result:

```
tested-inputs canonical pre:  565d3eb0dbb9 (845 files)
tested-inputs canonical post: 2370e52e97df (845 files)
ERROR: code under test changed DURING the run; results describe no single tree
REGISTRY_EXIT=2
```

`compute_tested_inputs()` hashes the enumerated package files before and after,
and a run whose subject moved describes no single tree. The refusal is the runner
working, not failing. The question was only what moves the tree.

## The controlled comparison

Two full runs of all 110 suites, back to back, same day, same corpus, watched by
the same external read-only poller — a process that hashes all 845 enumerated
files in a loop and records every change with a timestamp. It only reads, so it
cannot perturb what it measures.

| | Shared primary checkout | Detached worktree at `aeeb9fe` |
|---|---|---|
| Cases | 114 PASS, 0 failures | 114 PASS, 0 failures |
| tested-inputs pre | `565d3eb0dbb9` | `2370e52e97df` |
| tested-inputs post | `2370e52e97df` | `2370e52e97df` |
| Poller change events | **1** | **0** |
| Runtime | 7595 s | 6247 s |
| Verdict | `REGISTRY_EXIT=2` | **`REGISTRY_EXIT=0`** |

The only variable between them is whether another session could write the tree.

## The cause, named

In the contaminated run the poller recorded exactly one change, about 24 seconds
in, across roughly 1,250 samples:

```
scripts/citation_gate/PROVENANCE.json          0c016a4c66f2 -> 7c5a1daff8bb
scripts/citation_gate/validate_sources.py      b3c7f98335e3 -> 187e3be96ea3
scripts/citation_gate/verify_locators.py       0a3d45787c9d -> f4d1256455c4
scripts/citation_gate/verify_locators_test.py  ad5928fe48a6 -> 39880a8f857b
```

Three independent facts attribute those bytes to another session:

1. **No suite writes them.** The registry only *registers* two test files under
   `scripts/citation_gate/`; nothing in the corpus writes that directory.
2. **`git status` showed them as uncommitted working-tree modifications** while
   the run was still going.
3. **The commit log times it to the second.** The run spanned 13:46:59-15:53:34;
   commit `fd20dcc` landed at **13:47:32**, ~33 s in, exactly where the poller saw
   the bytes move. `aeeb9fe` followed at 13:53:14, touching only the
   non-enumerated `.plugin` / `.zip` snapshots — invisible to the hash, as expected.

The clean-room run recorded **zero** change events over 6,247 seconds and returned
`REGISTRY_EXIT=0` with pre and post identical.

## Why this took three wrong answers first

Every earlier explanation was proposed against evidence that could not decide it.
The pattern is worth more than the bug.

| Proposed cause | Verdict | How it was settled |
|---|---|---|
| Regenerated `.claude-plugin/*.plugin` and `.zip` | disproven | neither binary is in the enumerated set; regenerating them cannot move the hash |
| An LF to CRLF rewrite of 85 tracked files | disproven | a later full run moved the hash with the CRLF count pinned at 2 throughout |
| Parallel execution inside the runner | **disproven** | the loop is `for rel in sorted(registry)` with a blocking `run_owned`; `fixture_process_supervisor` has no pool, no `concurrent.futures`, no thread fan-out |
| A concurrent session writing enumerated files | **CONFIRMED** | the controlled comparison above |

The concurrent-session hypothesis was raised early and **retired in error**, on the
grounds that the mutation "reproduces with no concurrent writer and a clean tree."
That evidence could not support that conclusion. The other session's cycle is
*edit then commit*, and a commit restores a clean `git status` while leaving the
bytes changed. Checking the tree before and after a run is structurally blind to
the one writer pattern that matters. **A clean `git status` is not evidence that
nothing wrote during a run.** Only a watcher sampling *during* the window, or a
tree no one else can reach, can establish that.

The CRLF trail is worth one paragraph because it is a trap. After one run, 85
tracked files were genuinely CRLF where `HEAD` had LF, invisible to `git status`
because `.gitattributes` `text=auto` normalises before comparing. That was
investigator contamination, not the bug: `git checkout -- .` rewrites files per
`core.autocrlf=true`, and it had been run while undoing a manual line-ending edit.
**Do not hand-edit line endings in this repo.** Rewriting the 85 files to LF makes
git report all 85 as modified; `git checkout -- .` is the restore.

## Corroboration: the per-suite bisect

Before the cause was known, all 110 registry suites were run individually through
the runner, hashing all enumerated files before and after each:

```
110/110 suites run     0 nonzero exits     0 suites mutated any enumerated file
tested-inputs before   e3c5341e0b86 / 1a4489aee972
tested-inputs after    e3c5341e0b86 / 1a4489aee972   (identical)
```

Read at the time as "the mutation is a property of the full run." It was not: the
bisect simply ran while the other session happened to be idle. It stands as
independent confirmation that **no suite touches the tree**, which is what the
clean-room run then showed across a full run as well.

## How to run the corpus so this does not recur

Run it where no one else can write:

```bash
git worktree add --detach B:/Agents/.scratch/treecheck-<sha> <sha>
```

Then run `python scripts/analysis/fixture_runner.py --no-write` from inside that
worktree.

This is safe alongside another session: the shared sandbox resolves to a sibling of
the primary worktree root, outside every worktree, and the runner's lock is
repo-global, so a second concurrent runner fails loudly with exit 2 rather than
corrupting a verdict.

**Reading the exit code.** `REGISTRY_EXIT=2` together with `0 failures` and this
error means the tree moved under the run. It is not a red corpus, and it is not a
runner bug. Re-run in a detached worktree; if it returns `0`, the corpus was green
and something outside the run wrote the tree.

## The instrument

Not shipped as a script: it is a diagnostic, not a gate, and nothing should run it
routinely. Roughly 40 lines, read-only, no hooking.

```python
# Hash every enumerated file in a loop; print each change with its timestamp.
import hashlib, importlib.util, pathlib, sys, time
ROOT = pathlib.Path('.')
spec = importlib.util.spec_from_file_location('cc', ROOT / 'scripts/analysis/code_census.py')
cc = importlib.util.module_from_spec(spec); sys.path.insert(0, str(ROOT / 'scripts'))
spec.loader.exec_module(cc)

files, _ = cc.enumerate_package_files()
paths = sorted(r for r in files if not cc._is_excluded(r))
snap = lambda: {r: hashlib.sha256((ROOT / r).read_bytes()).hexdigest() for r in paths}

before, start = snap(), time.time()
while not pathlib.Path('STOP').exists():
    after = snap()
    for k in (k for k in before if before[k] != after.get(k)):
        print(f'{time.time() - start:9.2f}  {k}  {before[k][:12]} -> {after.get(k, "GONE")[:12]}')
    before = after
    time.sleep(0.25)
```

One snapshot costs about 5.5 s over 845 files, so it samples roughly every 6 s.
That is coarse in time and exact in identity — the right trade, because the
question was always *which* files move, not precisely when.

## A method note, recorded because it cost two hours

Before the poller, a `sitecustomize` write tracer — hooking `builtins.open` and
`subprocess.*` across every subprocess — was used for one full run. It **perturbed
the corpus**: 15 suites failed under it that pass without it (`claude_host_smoketest`,
`centroid_service_smoketest`, `semantic_qualification_consumer_smoketest` each
verified both ways). That run is void as a measurement. It also reported zero writes
to enumerated files, a correct answer to the wrong question.

Both failures in this investigation were instrument failures, in opposite
directions: the tracer changed what it measured, and the `git status` check could
not see what it claimed to rule out. **Validate a diagnostic against a known-green
suite before spending a full run on it, and state what a negative result would
actually exclude.** The poller was validated first on three green suites
(`piw_trace_io`, `golden_eval`, `argument_coherence`), which stayed green under it.

## What this does not affect

The corpus is green and always was. Both runs above are 114 of 114 cases with 0
failures. No suite, and no part of the runner, mutates the tree.
