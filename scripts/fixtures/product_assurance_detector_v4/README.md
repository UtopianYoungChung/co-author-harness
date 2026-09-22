# `product_assurance_detector_v4/` — what these splits bind, and what they do not

These fixtures are exercised by `scripts/product_assurance_detector_evaluation.py`
(`score` / `validate`) and by `scripts/product_assurance_detector_evaluation_smoketest.py`.
They are candidate-detector test evidence only: `candidate_only: true` and
`judgment_truth_certified: false` in `freeze.json` are load-bearing, and no number
produced here certifies scholarly truth, promotes a finding, or moves research state.

## Scope — these scores describe one function

`score()` calls **`product_assurance._semantic_findings(artifact, text, corpus)`**
and nothing else. An item in `development.json` / `held_out.json` carries an
artifact text, a corpus text, and labels; that is the whole input surface.

**The scorer never enters `product_assurance.build()`.** This is structural, not
incidental: `build()` takes `(artifact: Path, receipt_path: Path)` and needs a
schema-validated canonical receipt with passages and extract receipts on disk,
which a corpus item cannot carry. No item added here will ever reach it.

So a `precision 1.0 / recall 1.0` line from this corpus means *`_semantic_findings`
scored 1.0 on these 16 items*. It does not mean the detector as a whole was
measured. Read it that way and cite it that way.

## Where `build()` is covered instead

`scripts/product_assurance_smoketest.py` drives `build` through its CLI
(`product_assurance.py build --artifact … --semantic-receipt … --out …`) with
fixtures that carry a `# References` heading and receipts assembled via
`bibliography_fixture_support.from_passages`. That is the suite to extend when
`build()` changes — not this corpus.

## Why the distinction has teeth

Worked example, the 2026-09-22 re-freeze. Commit `ca9c784` changed
`product_assurance.py` in three ways: it widened year matching from
`(?:19|20)\d{2}` to `[1-9]\d{3}`, changed `_citation_groups` to count distinct
source identities rather than inspected passages, and added a hard finding in
`build()` that calls `bibliography.validate`.

Re-scored before and after on the same 16 items, both splits returned
`precision 1.0, recall 1.0, tp 4, fp 0, fn 0, tn 28` — identical per item and per
code, not merely in aggregate. Two of the three changes could not register here:

- no item in either split carries a year outside 1900–2099, so the widened regex
  had nothing to match differently;
- the new `bibliography.validate` call lives in `build()`, which this evaluation
  never enters.

**A change confined to `build()` moves no number in this corpus.** The only signal
that the detector moved at all was `DETECTOR-EVAL-FREEZE-STALE` — the hash refusal,
not the scores. Keep that refusal loud; treating it as noise removes the one control
that saw the change.

## Held-out discipline

`held_out.json` is `tuning_use: prohibited`. It may be **scored** — that is what it
is for — but never tuned against, and `score()` refuses `purpose="tuning"` on it
outright. `held_out_freeze_sha256` seals the held-out labels and bytes *together
with the detector binding*, so rebinding the detector necessarily reissues that
seal; that is the freeze's declared sequence
(`development_frozen → detector_candidate_frozen → held_out_labels_and_bytes_frozen
→ scoring_authorized`), not a weakening of it.

Adding items to either split changes its bytes, its hash, and the seal. Items
authored after seeing the detector are precisely what a held-out set exists to
exclude, so extend `development.json` if you extend anything, and treat any change
to `held_out.json` as minting a new held-out set rather than editing this one.

## Layout

```
development.json   8 items, tuning_use: permitted
held_out.json      8 items, tuning_use: prohibited
freeze.json        binds the detector (sha256, byte_length) and both splits
README.md          this file
```
