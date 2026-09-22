# `fixture_runner` reports tree mutation that no suite in its registry causes

**Status.** Open. Diagnosed to the point of a precise problem statement; the
cause is not identified and this is not a proposed fix.

**Date.** 2026-09-22. **Observed at.** `fee200d`, and at every earlier commit this
was run against. **Not introduced by** the argument-coherence work that surfaced it.

---

## The symptom

`python scripts/analysis/fixture_runner.py --no-write` completes the corpus and
then refuses its own result:

```
tested-inputs canonical pre:  ccb467b3879e (844 files)
tested-inputs canonical post: 3eb825a5ba4d (844 files)
ERROR: code under test changed DURING the run; results describe no single tree
REGISTRY_EXIT=2
```

The refusal is correct behaviour by the runner: `compute_tested_inputs()` hashes
the enumerated package files before and after, and a run whose subject moved
describes no single tree. The question is what moves it.

It reproduces with a clean working tree, no concurrent writer, and every suite
passing. On the run above: **114 of 114 registered cases, 0 failures**, and
`REGISTRY_EXIT=2` all the same.

## What it is not

Three explanations were proposed and all three are dead. Each was tested, not
argued away.

| Proposed cause | Verdict | How it died |
|---|---|---|
| Regenerated `.claude-plugin/*.plugin` and `.zip` | **disproven** | neither binary is in the enumerated 844; regenerating them cannot move the hash |
| A concurrent session editing the repo | **disproven** | reproduces with no concurrent writer and a clean tree |
| An LF → CRLF rewrite of 85 tracked files | **disproven** | a later full run moved the hash with the CRLF count pinned at 2 throughout |

The CRLF trail is worth one paragraph because it is a trap. After one run, 85
tracked files were genuinely CRLF where `HEAD` had LF, invisible to `git status`
because `.gitattributes` `text=auto` normalises before comparing. That was
investigator contamination, not the bug: `git checkout -- .` rewrites files per
`core.autocrlf=true`, and it had been run while undoing a manual line-ending edit.
**Do not hand-edit line endings in this repo.** Rewriting the 85 files to LF makes
git report all 85 as modified; `git checkout -- .` is the restore.

## What the bisect established

All 110 registry suites, run individually through the runner, hashing all 844
enumerated files before and after each:

```
110/110 suites run     0 nonzero exits     0 suites mutated any enumerated file
tested-inputs before   e3c5341e0b86 / 1a4489aee972
tested-inputs after    e3c5341e0b86 / 1a4489aee972   (identical)
```

**No individual suite touches the tree.** The mutation is a property of the full
run, not of any suite in it.

### Remaining candidates, unseparated

- **Concurrency.** The runner's process supervisor may execute suites in parallel
  where a serial bisect does not. Cheapest next test and the strongest lead:
  compare a parallel run against the serial pass above.
- **The runner's own machinery between suites** — manifest handling, the fixture
  cache, the lock, or `code_census` itself.
- **Accumulated sandbox state** across suites that no single suite reproduces.

## Reproducing the bisect

Not shipped as a script, because it is a diagnostic rather than a gate. It is
~40 lines and perturbs nothing:

```python
# For each REGISTRY key: hash every enumerated file, run the suite through the
# runner exactly as a normal run would, hash again, report the delta.
import hashlib, importlib.util, pathlib, re, subprocess, sys
ROOT = pathlib.Path('.')
spec = importlib.util.spec_from_file_location('cc', ROOT / 'scripts/analysis/code_census.py')
cc = importlib.util.module_from_spec(spec); sys.path.insert(0, str(ROOT / 'scripts'))
spec.loader.exec_module(cc)

files, _ = cc.enumerate_package_files()
paths = sorted(r for r in files if not cc._is_excluded(r))
snap = lambda: {r: hashlib.sha256((ROOT / r).read_bytes()).hexdigest() for r in paths}

body = (ROOT / 'scripts/analysis/fixture_runner.py').read_text(encoding='utf-8')
suites = re.findall(r'^\s+"(scripts/[^"]+)"\s*:', body.split('REGISTRY: dict[str, list[dict]] = {', 1)[1], re.M)

before = snap()
for name in suites:
    subprocess.run([sys.executable, 'scripts/analysis/fixture_runner.py',
                    '--no-write', '--suite', name], cwd=ROOT, capture_output=True)
    after = snap()
    changed = sorted(k for k in before if before[k] != after.get(k))
    if changed:
        print(name, '->', changed)
    before = after
```

Do **not** restore the tree between suites: restoring means `git checkout`, which
rewrites files itself and is what contaminated the earlier attempt. Deltas are
cumulative and each is attributed to the suite that produced it.

## A method note, recorded because it cost two hours

A `sitecustomize` write tracer — hooking `builtins.open` and `subprocess.*` across
every subprocess — was used for one full run before the bisect. It **perturbed the
corpus**: 15 suites failed under it that pass without it (`claude_host_smoketest`,
`centroid_service_smoketest`, `semantic_qualification_consumer_smoketest` each
verified both ways). That run is void as a measurement.

It also reported zero writes to enumerated files, which was a correct answer to the
wrong question, and which the bisect later confirmed.

**Validate a diagnostic against a known-green suite before spending a full run on
it.** The bisect above was self-tested on three green suites first and left them
passing; the tracer was not.

## What this does not affect

The corpus itself is green. On `fee200d`, every registered case passes; the
refusal is about the runner's single-tree guarantee, not about suite outcomes. A
run that ends `REGISTRY_EXIT=2` with `0 failures` and this error is reporting
exactly that distinction, and should be read as such rather than as a red corpus.
