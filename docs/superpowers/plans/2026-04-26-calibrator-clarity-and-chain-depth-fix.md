# Calibrator Clarity Score and Chain Depth Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two calibrator false positives against the co-author-harness plugin — a 0.25 prompt clarity score caused by vocabulary mismatch, and a chain depth of 21 caused by a missing `PROTOCOL_STAGES` constant — without touching harness prose or restructuring skills.

**Architecture:** Two independent workstreams, one per finding. Workstream A (chain depth) is entirely within the harness and requires only a new `scripts/protocol_constants.py`. Workstream B (clarity) requires extending the calibrator's `efficiency.py` with an `extra_clarity_section_tags` config key and then declaring that key in the harness's `.plugin-efficiency.json`. As an immediate interim (Path C), the clarity false-negative baseline is documented in `.plugin-efficiency.json` so the score is interpretable before the code change lands. Advisor source: `reviews/advisor_consultation_2026-04-26.md`.

**Tech Stack:** Python 3 (AST-safe edits to `plugin_calibrator/efficiency.py`), JSON (`.plugin-efficiency.json`), Markdown; calibrator located at the path noted in each task.

---

## File structure

Files created or modified across all tasks:

| File | Action | Task |
|---|---|---|
| `scripts/protocol_constants.py` | **Create** | Task 1 |
| `.plugin-efficiency.json` | **Modify** (add `clarity_false_negative_baseline` key) | Task 2 |
| `.remote-plugins/plugin_01Q7iXHRyKL2TPd9xCgb4j2p/plugin_calibrator/efficiency.py` | **Modify** (`DEFAULT_CONFIG`, `_prompt_clarity_score`, `audit_quality`) | Task 3 |
| `.plugin-efficiency.json` | **Modify** (add `extra_clarity_section_tags` key) | Task 4 |

> **Path shorthand used in Tasks 3–4:**
> Calibrator root = `C:\Users\young\AppData\Roaming\Claude\local-agent-mode-sessions\4becaaed-1261-4c40-9b52-9f7f0c00ae1c\c7567f6a-ee6a-432c-8c64-add10a1a6282\rpm\plugin_01Q7iXHRyKL2TPd9xCgb4j2p\`
> Calibrator `efficiency.py` = `<calibrator_root>\plugin_calibrator\efficiency.py`
> Harness root = `B:\Agents\co-author-harness\`

---

## Task 1 — Create `scripts/protocol_constants.py` (chain-depth fix)

**Why:** `_declared_protocol_stage_count` in `efficiency.py` (lines 524–548) scans Python source files for any AST variable whose name contains `"STAGES"` and is assigned a `list` or `tuple`. The harness has no such variable, so the function returns 0 and the speed audit falls back to graph-traversal depth — which resolves to 21 via the `plugin-commands/SKILL.md` manifest hub. Declaring a `PROTOCOL_STAGES` list in any Python file under `scripts/` gives the scanner exactly what it needs: a list of length 5 (Ph1 → Ph2 → Ph3/stability → Ph4), making `max_subagent_chain_depth = max(graph_depth, 5) = 21` only if graph is still used — but with this constant present the declared count overrides the graph result.

**Files:**
- Create: `B:\Agents\co-author-harness\scripts\protocol_constants.py`

- [ ] **Step 1: Confirm the scanner will find this file**

  The detection logic in `orchestrator_detect.py` walks the plugin root for `.py` files to discover orchestrator candidates; `scripts/` is on that path. Verify:

  ```bash
  find /sessions/youthful-admiring-goldberg/mnt/co-author-harness/scripts -name "*.py" | head -10
  ```

  Expected: one or more `.py` files listed, confirming the scanner reaches `scripts/`.

- [ ] **Step 2: Write `scripts/protocol_constants.py`**

  ```python
  """Protocol stage constants for the co-author-harness lifecycle ladder.

  This module exists so that the plugin-calibrator's
  ``_declared_protocol_stage_count`` scanner can locate the authoritative
  phase count via AST inspection rather than falling back to graph-traversal
  depth.  The list below mirrors the Ph1–Ph4 ladder defined in
  ``references/PHASE_PROTOCOL.md``; update it if new phases are added.
  """

  # Each entry is one rung on the Lifecycle-Phase Ladder (Ph1 → Ph4).
  # ``run-phase-3-stability`` is an intra-Ph3 stability pass, not a new phase,
  # so the operational pipeline remains 5 distinct stages.
  PROTOCOL_STAGES = [
      "ph1_plan_draft",
      "ph2_review_revise",
      "ph3_iterate_converge",
      "ph3_stability_pass",
      "ph4_finalize_close",
  ]
  ```

  Save to `B:\Agents\co-author-harness\scripts\protocol_constants.py`.

- [ ] **Step 3: Verify the file parses cleanly**

  ```bash
  python3 -c "import ast; ast.parse(open('/sessions/youthful-admiring-goldberg/mnt/co-author-harness/scripts/protocol_constants.py').read()); print('PARSE OK')"
  ```

  Expected: `PARSE OK`

- [ ] **Step 4: Smoke-test that the scanner will find it**

  ```bash
  python3 - <<'EOF'
  import ast
  from pathlib import Path
  src = Path('/sessions/youthful-admiring-goldberg/mnt/co-author-harness/scripts/protocol_constants.py').read_text()
  tree = ast.parse(src)
  for node in ast.walk(tree):
      if isinstance(node, ast.Assign):
          for target in node.targets:
              if isinstance(target, ast.Name) and "STAGES" in target.id.upper():
                  if isinstance(node.value, (ast.List, ast.Tuple)):
                      print(f"FOUND: {target.id} len={len(node.value.elts)}")
  EOF
  ```

  Expected: `FOUND: PROTOCOL_STAGES len=5`

- [ ] **Step 5: Commit**

  ```bash
  cd /sessions/youthful-admiring-goldberg/mnt/co-author-harness && \
  git add scripts/protocol_constants.py && \
  git commit -m "fix: add PROTOCOL_STAGES constant so calibrator speed audit reports correct chain depth

  Without this constant, _declared_protocol_stage_count returns 0 and the
  speed auditor falls back to graph-traversal depth (21), driven by the
  plugin-commands manifest hub.  With len(PROTOCOL_STAGES)=5 the declared
  count overrides graph depth for the harness operational pipeline.

  Ref: reviews/advisor_consultation_2026-04-26.md (Finding 3 / Path A analogue)"
  ```

---

## Task 2 — Document clarity false-negative baseline in `.plugin-efficiency.json` (interim Path C)

**Why:** Until the calibrator's `_CLARITY_SECTION_TAGS` vocabulary is extended (Task 3), the 0.25 clarity score is a known false negative. The `"baseline"` key in `.plugin-efficiency.json` is currently `null`. Adding a structured comment field makes the score interpretable to anyone running the calibrator and prevents future real regressions from being invisible against unexplained noise.

**Files:**
- Modify: `B:\Agents\co-author-harness\.plugin-efficiency.json`

- [ ] **Step 1: Read current `.plugin-efficiency.json`**

  Open `B:\Agents\co-author-harness\.plugin-efficiency.json`. Confirm `"baseline": null` is on the last line before the closing `}`.

- [ ] **Step 2: Replace the `baseline` key with a structured record**

  Change:
  ```json
  "baseline": null
  ```

  To:
  ```json
  "baseline": {
    "prompt_clarity_score": {
      "known_false_negative": true,
      "recorded_score": 0.25,
      "recorded_date": "2026-04-26",
      "failing_artefacts": 24,
      "total_artefacts": 32,
      "root_cause": "calibrator _CLARITY_SECTION_TAGS vocabulary mismatch — harness uses '## What you do', '## Step N —', '## Phase N —' which are not in the hardcoded tuple at efficiency.py lines 694-701",
      "resolution": "Path A: add extra_clarity_section_tags config support to efficiency.py (Task 3) and declare harness-specific tags in this file (Task 4)",
      "advisor_reference": "reviews/advisor_consultation_2026-04-26.md — Path C as interim, Path A as fix"
    }
  }
  ```

- [ ] **Step 3: Verify the file is valid JSON**

  ```bash
  python3 -c "import json; json.load(open('/sessions/youthful-admiring-goldberg/mnt/co-author-harness/.plugin-efficiency.json')); print('JSON OK')"
  ```

  Expected: `JSON OK`

- [ ] **Step 4: Commit**

  ```bash
  cd /sessions/youthful-admiring-goldberg/mnt/co-author-harness && \
  git add .plugin-efficiency.json && \
  git commit -m "fix: document clarity false-negative baseline in .plugin-efficiency.json (Path C)

  The calibrator's _CLARITY_SECTION_TAGS tuple does not include harness-specific
  section headers ('## What you do', '## Step N —', '## Phase N —'), causing
  24/32 artefacts to fail the clarity check at a score of 0.25.  This is a
  calibrator vocabulary gap, not a structural deficiency in the harness.

  Documents the known false-negative baseline per advisor recommendation
  (interim Path C) while the upstream fix (Path A, Task 3+4) is prepared.

  Ref: reviews/advisor_consultation_2026-04-26.md"
  ```

---

## Task 3 — Add `extra_clarity_section_tags` support to `efficiency.py` (Path A, calibrator change)

**Why:** `_prompt_clarity_score` (line 705) hardcodes `_CLARITY_SECTION_TAGS` as the only vocabulary for recognising structured sections. It receives no config argument, so there is currently no way for a plugin to declare supplementary section headers. Three surgical changes are required: (1) add `"extra_clarity_section_tags": []` to `DEFAULT_CONFIG`, (2) add an `extra_tags` parameter to `_prompt_clarity_score` and merge it with `_CLARITY_SECTION_TAGS`, (3) pass `cfg.get("extra_clarity_section_tags", [])` from `audit_quality`.

**Files:**
- Modify: `<calibrator_root>\plugin_calibrator\efficiency.py`

  (Absolute: `C:\Users\young\AppData\Roaming\Claude\local-agent-mode-sessions\4becaaed-1261-4c40-9b52-9f7f0c00ae1c\c7567f6a-ee6a-432c-8c64-add10a1a6282\rpm\plugin_01Q7iXHRyKL2TPd9xCgb4j2p\plugin_calibrator\efficiency.py`)

- [ ] **Step 1: Write a failing test before touching the code**

  Add this test to `<calibrator_root>\tests\test_efficiency_clarity.py` (create the file if absent, otherwise append):

  ```python
  import pytest
  from pathlib import Path
  from plugin_calibrator.efficiency import _prompt_clarity_score, Artefact

  def _make_art(body: str, kind: str = "skill") -> "Artefact":
      """Minimal Artefact stub for clarity testing."""
      from plugin_calibrator.efficiency import Artefact
      return Artefact(
          relpath="skills/test/SKILL.md",
          kind=kind,
          frontmatter={"description": "test", "trigger": "test"},
          body=body,
          tokens_body=len(body) // 4,
      )

  def test_extra_tags_extends_vocabulary():
      """extra_tags=['what you do'] should make a skill with '## What you do' pass."""
      body = "## What you do\n\nDo stuff.\n\n```bash\necho hi\n```\n"
      art = _make_art(body)
      # Without extra_tags: should FAIL (no standard section tag matches)
      score_without, details_without = _prompt_clarity_score([art])
      assert score_without == 0.0, f"Expected 0.0 without extra_tags, got {score_without}"
      # With extra_tags: should PASS
      score_with, details_with = _prompt_clarity_score([art], extra_tags=["what you do"])
      assert score_with == 1.0, f"Expected 1.0 with extra_tags, got {score_with}"

  def test_extra_tags_empty_list_is_noop():
      """Passing extra_tags=[] must be identical to calling without extra_tags."""
      body = "## Output Contract\n\nReturns a dict.\n"
      art = _make_art(body, kind="agent")
      score_default, _ = _prompt_clarity_score([art])
      score_empty, _ = _prompt_clarity_score([art], extra_tags=[])
      assert score_default == score_empty
  ```

  Run and confirm both tests **fail** (function signature doesn't accept `extra_tags` yet):

  ```bash
  cd <calibrator_root> && python -m pytest tests/test_efficiency_clarity.py -v 2>&1 | tail -20
  ```

  Expected: `TypeError: _prompt_clarity_score() got an unexpected keyword argument 'extra_tags'`

- [ ] **Step 2: Add `extra_clarity_section_tags` to `DEFAULT_CONFIG`**

  In `efficiency.py`, find `DEFAULT_CONFIG` (starts around line 106). After the `"role_overrides": {},` line and before `"baseline": None,`, insert:

  ```python
      "extra_clarity_section_tags": [],
  ```

  The relevant block becomes:

  ```python
  DEFAULT_CONFIG: Dict[str, object] = {
      "model_tiers": { ... },
      "input_tokens_per_second": 500,
      "assumed_output_tokens_per_invocation": 400,
      "assumed_invocations_per_run": {"executor": 1, "orchestrator": 1},
      "thresholds": { ... },
      "role_overrides": {},
      "extra_clarity_section_tags": [],   # <-- ADD THIS LINE
      "baseline": None,
  }
  ```

- [ ] **Step 3: Add `extra_tags` parameter to `_prompt_clarity_score`**

  Current signature (line 705):
  ```python
  def _prompt_clarity_score(artefacts: Sequence[Artefact]) -> Tuple[float, List[Dict]]:
  ```

  New signature:
  ```python
  def _prompt_clarity_score(
      artefacts: Sequence[Artefact],
      extra_tags: Sequence[str] = (),
  ) -> Tuple[float, List[Dict]]:
  ```

  Inside the function, find the `section_hits` computation (around line 722):
  ```python
  section_hits = [
      heading
      for _, heading, _ in extract_sections(art.body)
      if any(tag in heading.lower() for tag in _CLARITY_SECTION_TAGS)
  ]
  ```

  Replace with:
  ```python
  _effective_tags = _CLARITY_SECTION_TAGS + tuple(extra_tags)
  section_hits = [
      heading
      for _, heading, _ in extract_sections(art.body)
      if any(tag in heading.lower() for tag in _effective_tags)
  ]
  ```

  Also update the docstring to note the new parameter:
  ```python
  """Fraction of artefacts that meet simple legibility requirements.

  An artefact is "clear" when it satisfies all of:
    (1) required frontmatter keys for its kind,
    (2) at least one named section from ``_CLARITY_SECTION_TAGS`` union
        ``extra_tags`` (plugin-specific section vocabulary from config),
    (3) at least one fenced code block - required only for skills.
  """
  ```

- [ ] **Step 4: Thread `extra_tags` through `audit_quality`**

  In `audit_quality` (line 761), find:
  ```python
  clarity_score, clarity_per_artefact = _prompt_clarity_score(artefacts)
  ```

  Replace with:
  ```python
  extra_clarity_tags = cfg.get("extra_clarity_section_tags") or []
  clarity_score, clarity_per_artefact = _prompt_clarity_score(
      artefacts, extra_tags=extra_clarity_tags
  )
  ```

- [ ] **Step 5: Run the tests — both should now pass**

  ```bash
  cd <calibrator_root> && python -m pytest tests/test_efficiency_clarity.py -v
  ```

  Expected:
  ```
  PASSED tests/test_efficiency_clarity.py::test_extra_tags_extends_vocabulary
  PASSED tests/test_efficiency_clarity.py::test_extra_tags_empty_list_is_noop
  ```

- [ ] **Step 6: Run full calibrator test suite to check for regressions**

  ```bash
  cd <calibrator_root> && python -m pytest -v 2>&1 | tail -30
  ```

  Expected: all previously-passing tests still pass; no new failures.

- [ ] **Step 7: Commit the calibrator change**

  ```bash
  cd <calibrator_root> && \
  git add plugin_calibrator/efficiency.py tests/test_efficiency_clarity.py && \
  git commit -m "feat: add extra_clarity_section_tags config support to _prompt_clarity_score

  Plugins that use domain-specific section headers (e.g. '## What you do',
  '## Step N —') were scored 0 on clarity despite being well-structured, because
  _CLARITY_SECTION_TAGS only contained generic vocabulary.

  - DEFAULT_CONFIG gains 'extra_clarity_section_tags': [] (backward-compatible)
  - _prompt_clarity_score accepts extra_tags parameter (defaults to ())
  - audit_quality threads cfg['extra_clarity_section_tags'] through

  Tested by: tests/test_efficiency_clarity.py (two new cases)"
  ```

---

## Task 4 — Declare harness-specific tags in `.plugin-efficiency.json`

**Why:** With `extra_clarity_section_tags` now supported by the calibrator (Task 3), the harness's `.plugin-efficiency.json` can declare the four section-header patterns that account for all 24 previously-failing artefacts: `"what you do"` (covers `## What you do`), `"step "` (covers `## Step N —`), `"phase "` (covers `## Phase N —`), and `"output"` (covers `## Output`). These are substring matches (same as the existing tags), so `"step "` with the trailing space avoids false matches on unrelated words.

**Files:**
- Modify: `B:\Agents\co-author-harness\.plugin-efficiency.json`

- [ ] **Step 1: Verify the 4 tag patterns cover the failing artefacts**

  Run a quick grep to confirm the patterns appear in harness skill files:

  ```bash
  grep -rhi "^## \(what you do\|step [0-9]\|phase [0-9]\|output\)" \
    /sessions/youthful-admiring-goldberg/mnt/co-author-harness/skills/ \
    | sort | uniq -c | sort -rn | head -20
  ```

  Expected: results for all four pattern types with counts summing to ≥24.

- [ ] **Step 2: Add `extra_clarity_section_tags` to `.plugin-efficiency.json`**

  Open `B:\Agents\co-author-harness\.plugin-efficiency.json`. After the `"assumed_invocations_per_run"` block and before `"thresholds"`, add:

  ```json
  "extra_clarity_section_tags": [
    "what you do",
    "step ",
    "phase ",
    "output"
  ],
  ```

  The file section should look like:

  ```json
  "assumed_invocations_per_run": {
    "executor": 3,
    "orchestrator": 4
  },

  "extra_clarity_section_tags": [
    "what you do",
    "step ",
    "phase ",
    "output"
  ],

  "thresholds": {
  ```

- [ ] **Step 3: Verify the file is valid JSON**

  ```bash
  python3 -c "import json; json.load(open('/sessions/youthful-admiring-goldberg/mnt/co-author-harness/.plugin-efficiency.json')); print('JSON OK')"
  ```

  Expected: `JSON OK`

- [ ] **Step 4: Commit**

  ```bash
  cd /sessions/youthful-admiring-goldberg/mnt/co-author-harness && \
  git add .plugin-efficiency.json && \
  git commit -m "fix: declare extra_clarity_section_tags for harness-specific section headers

  Adds the four harness section-header patterns that were invisible to the
  calibrator's hardcoded _CLARITY_SECTION_TAGS vocabulary:
    - 'what you do'  -> ## What you do
    - 'step '        -> ## Step N —
    - 'phase '       -> ## Phase N —
    - 'output'       -> ## Output

  With extra_clarity_section_tags support in efficiency.py (Task 3), this
  should lift the clarity score from 0.25 to ~1.0 for the 24 previously-
  failing artefacts.

  Ref: reviews/advisor_consultation_2026-04-26.md (Path A recommendation)"
  ```

---

## Task 5 — Re-run calibration loop and verify fixes

**Why:** Validates that both findings are resolved — chain depth should now report ≤15 (declared stage count = 5), and the clarity score should be ≥0.5 (ideally ~1.0).

**Files:** No files modified.

- [ ] **Step 1: Re-run the speed audit**

  ```bash
  python3 - <<'EOF'
  import sys, json
  sys.path.insert(0, 'C:/Users/young/AppData/Roaming/Claude/local-agent-mode-sessions/4becaaed-1261-4c40-9b52-9f7f0c00ae1c/c7567f6a-ee6a-432c-8c64-add10a1a6282/rpm/plugin_01Q7iXHRyKL2TPd9xCgb4j2p')
  from pathlib import Path
  from plugin_calibrator.efficiency import audit_speed
  result = audit_speed(Path('B:/Agents/co-author-harness'))
  print(f"max_subagent_chain_depth: {result['max_subagent_chain_depth']}")
  print(f"declared_protocol_stage_count: {result['declared_protocol_stage_count']}")
  EOF
  ```

  Expected: `declared_protocol_stage_count: 5`, `max_subagent_chain_depth: 5` (or ≤15).

- [ ] **Step 2: Re-run the quality audit**

  ```bash
  python3 - <<'EOF'
  import sys, json
  sys.path.insert(0, 'C:/Users/young/AppData/Roaming/Claude/local-agent-mode-sessions/4becaaed-1261-4c40-9b52-9f7f0c00ae1c/c7567f6a-ee6a-432c-8c64-add10a1a6282/rpm/plugin_01Q7iXHRyKL2TPd9xCgb4j2p')
  from pathlib import Path
  from plugin_calibrator.efficiency import audit_quality
  result = audit_quality(Path('B:/Agents/co-author-harness'))
  score = result['prompt_clarity_score']
  failing = [a for a in result['prompt_clarity_per_artefact'] if not a['ok']]
  print(f"prompt_clarity_score: {score}")
  print(f"failing artefacts: {len(failing)}")
  if failing:
      for a in failing:
          print(f"  FAIL: {a['relpath']} — recognised_sections={a['recognised_sections']}")
  EOF
  ```

  Expected: `prompt_clarity_score: 1.0` (or close), `failing artefacts: 0`.

- [ ] **Step 3: If any artefacts still fail, inspect them**

  For each entry in the failing list, open the SKILL.md, identify the actual section header, and add the missing substring to `extra_clarity_section_tags` in `.plugin-efficiency.json`. Re-run Step 2 to confirm.

- [ ] **Step 4: Run the full calibration loop via the orchestrator**

  In Cowork, invoke:
  ```
  /unified-superkit:run-plugin-calibration-loop on the co-author-harness
  ```

  Expected final summary:
  - `md_dead_references`: PASS (0 findings — already confirmed in this session)
  - `prompt_clarity_score`: ≥ 0.5 (target 1.0), no MAJOR
  - `max_subagent_chain_depth`: ≤ 15, no MAJOR

---

## Self-review

**Spec coverage check:**
- Finding 1 (dead references) — already fixed this session; no task needed. ✓
- Finding 2 (clarity 0.25, calibrator vocabulary gap) — covered by Tasks 2, 3, 4. ✓
- Finding 3 (chain depth 21, missing PROTOCOL_STAGES) — covered by Task 1. ✓
- Advisor path C (interim documentation) — Task 2. ✓
- Advisor path A (root-cause fix) — Tasks 3 and 4. ✓
- Advisor path B (alias headers in 24 skills) — **explicitly excluded** per advisor recommendation. ✓
- Verification — Task 5. ✓

**Placeholder scan:** No TBD, TODO, or "similar to Task N" references. All code blocks contain actual implementations.

**Type consistency:** `_prompt_clarity_score` uses `Sequence[str]` for `extra_tags` (same type as the existing `_CLARITY_SECTION_TAGS` tuple elements); `cfg.get("extra_clarity_section_tags") or []` always returns a list; `tuple(extra_tags)` in the implementation handles both lists and tuples safely.
