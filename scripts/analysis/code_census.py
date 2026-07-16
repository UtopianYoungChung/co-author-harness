#!/usr/bin/env python3
"""code_census — reproducible per-SITE census of gate predicates, with set parity.

Why this exists
---------------
Two successive failures, one level apart:

  Round 1 (counting).  A census of "63 codes" came from a pipeline ending in
  `| head -20`: the output was truncated at 20 and 20 was reported as the count.
  Four live MF codes were dropped by truncation, not judgment.

  Round 2 (granularity). The fix counted 70 CODE LABELS and called them
  predicates. But MF-POLICY has ~30 emission sites, MF-EXEMPLAR ~37, MF-EVENT
  ~23. One matrix row per label preserves the NAME while deleting most of the
  RULES behind it. A label is not a predicate.

This script therefore emits one row per EMISSION SITE, not per code, and it
discovers its own emitters instead of trusting a hand-maintained list (which
had silently omitted assignment_dispatch_preflight.py, the required dispatch
preflight, and render_lifecycle_state.py).

Contract: completeness, not precision. It reports a superset with evidence and
refuses to classify -- five distinct emission shapes exist in this tree and
three successive heuristics each under-reported, i.e. each would have silently
retired a live rule. A false positive costs one adjudication row; a false
negative deletes a rule.

Usage
-----
    python scripts/analysis/code_census.py                 # human summary
    python scripts/analysis/code_census.py --json          # machine-readable
    python scripts/analysis/code_census.py --emit-matrix   # generate matrix rows
    python scripts/analysis/code_census.py --parity FILE   # set-parity vs matrix

Exit: 0 ok; 1 parity failure; 2 source/scan error.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import re
import sys
from pathlib import Path

# A maintainer gate must run under the DOCUMENTED environment with no
# undeclared override. Every run of this script shown in review was silently
# wrapped in `$env:PYTHONIOENCODING="utf-8"`; without it the parity command
# crashed with UnicodeEncodeError on a cp949 console. A gate that passes only
# under a hidden override does not pass. Establish UTF-8 in-process, and keep
# all emitted text ASCII so the output survives any console codepage.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
else:  # pragma: no cover - very old interpreters
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PLUGIN_ROOT / "scripts"

PREFIXES = ("APG-", "MF-", "E-", "W-", "G0-", "G1-", "G2-", "G3-")
CODE_SHAPED_RE = re.compile(r"[A-Z][A-Z0-9_-]{2,}")
STATIC_RE = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in PREFIXES) + r")[A-Z0-9]+(?:-[A-Z0-9]+)*\b"
)

# Emitters are DISCOVERED, not declared. A hand-maintained SOURCES list is a
# census gap waiting to happen: the previous revision hardcoded three files and
# missed APG-RECEIPT-TARGET-MISMATCH in assignment_dispatch_preflight.py:63.
# Smoketests are scanned too, but classified separately -- they are FIXTURES,
# and the review requires fixture-level preservation, so they must appear in the
# matrix rather than be filtered out.
FIXTURE_MARKERS = ("_smoketest", "_test", "test_")


# TESTED-INPUT SNAPSHOT.
#
# Binding a run to the SUITE file is not binding it to the CODE UNDER TEST.
# Verified hole: record a valid manifest, mutate milestone_framework_validate.py
# (subject sha e65541a4 -> 4279d69d), leave every smoketest untouched -- parity
# still exited 0. The evidence claimed to describe behaviour that no longer
# exists.
#
# A git rev is NOT sufficient: a dirty worktree has uncommitted subject changes
# under a clean-looking commit id, and this repo's whole history is uncommitted
# work. Hash CONTENT.
#
# NO LOCAL POPULATION. The subject is enumerated by the PACKAGING AUTHORITY.
#
# Seven populations were invented in this workstream, each an allowlist, each
# too narrow:
#   emitters        hand-listed          3 of 6
#   suite universe  code-literal filter  11 of 30
#   tested inputs   *.py + schema json   99 files  ("conservative", wasn't)
#   tested inputs   six-root "denylist"  365 files -- STILL an allowlist, and
#                   still wrong: vs. build-plugin.py's 450 tracked files it
#                   omitted 87 SHIPPED files (README.md, CLAUDE.md,
#                   CHANGELOG.md, .github/**, docs/**, reviews/**, root config)
#                   and INCLUDED 2 generated .plugin archives the builder
#                   explicitly excludes. Editing an omitted shipped file left
#                   evidence "valid"; rebuilding an archive invalidated it.
#
# The lesson is not "write a better list". It is: DO NOT AUTHOR A POPULATION
# THAT ALREADY HAS AN OWNER. scripts/package_enumeration.py owns "which files
# ship" for the .plugin bundle; this module and build-plugin.py import the same
# function.
#
# SCOPE (updated 2026-07-16): package_enumeration is now the population
# authority for BOTH bundle paths. release-gate.sh Phase 1 and
# build-release-zip.sh each build by invoking the committed
# scripts/build-plugin.py rather than their former independent
# `zip -r`-with-exclusions populations. One producer, one population rule;
# the former two-population blocker is closed.
#
# CONTENT comes from the WORKING TREE, not HEAD blobs. The enumeration answers
# "which files ship"; the hash answers "what do they say right now". Reading
# HEAD would reintroduce the dirty-worktree hole. (No worktree count is quoted
# here: it changed 8 -> 9 -> 10 across three review rounds, and a count in a
# comment is a fact with no owner. Run `git status --porcelain`.)
# Plain import of the neutral authority. NO try/except fallback: the previous
# revision tried `from build_plugin_shim import ...` first and only fell back to
# the real authority on ImportError -- so creating a file named
# build_plugin_shim.py anywhere on the path would have silently replaced the
# source of truth, with no warning. A checker whose authority can be swapped by
# adding a file is not a checker. If this import fails, the census must die.
sys.path.insert(0, str(SCRIPTS_DIR))
from package_enumeration import enumerate_package_files  # noqa: E402

# The checker cannot vouch for its own observer, so it is bound separately via
# script_sha256 (see parity()). Two subtractions from the packaging authority,
# each a stated exception rather than a filter:
#
#   scripts/analysis/                 the observer zone (bound via script_sha256
#                                     and runner_sha256 instead)
#   docs/.../fixture_manifest.json    THE EVIDENCE ITSELF, exact path. Once the
#                                     manifest is tracked, hashing it makes the
#                                     evidence self-binding: the runner would
#                                     hash the old manifest into pre/post and
#                                     then overwrite it, so every manifest is
#                                     stale the moment it is written and the
#                                     gate only passes while evidence stays
#                                     untracked (2026-07-16). Exact file, not a
#                                     generated-docs prefix -- predicate_rows.md
#                                     IS subject matter and must stay hashed.
#
# Both entries are machine-recorded in every manifest's tested_inputs.exclude
# and reconciled by the consistency check below; widening this tuple silently
# is therefore not possible without invalidating existing evidence.
TESTED_INPUT_EXCLUDE: tuple[str, ...] = (
    "scripts/analysis/",
    "docs/analysis/generated/fixture_manifest.json",
)


def compute_tested_inputs() -> dict:
    """Deterministic content snapshot of the shipped subject.

    Enumeration: scripts/package_enumeration.py (imported, not reimplemented).
    Content: WORKING TREE. Merkle-style -- sort by repo-relative path, hash
    `path\\0sha256` per file, digest the concatenation. Sorted -> stable across
    filesystem order; per-path -> a rename is a change; content -> immune to
    dirty worktrees.

    Self-reference CLOSED at e4a23c7: package_enumeration.py is tracked, so the
    module deciding which files are hashed is itself inside the hash. Before
    that commit it was untracked -- the population definer sat outside the
    population it defined, and the digest bound 450 files while excluding the
    code that picked the 450. build-plugin.py keeps it in REQUIRED_FILES so a
    bundle can never again ship the importer without its import target.

    Raises SystemExit on any enumerated file missing from the worktree: a
    smaller snapshot must never be silently "valid". The previous version
    skipped missing roots and would have produced exactly that.
    """
    files, _excluded_archives = enumerate_package_files()
    entries: list[str] = []
    missing: list[str] = []
    for rel in files:
        if any(rel.startswith(x) for x in TESTED_INPUT_EXCLUDE):
            continue
        p = PLUGIN_ROOT / rel
        if not p.is_file():
            missing.append(rel)
            continue
        entries.append(f"{rel}\0{hashlib.sha256(p.read_bytes()).hexdigest()}")
    if missing:
        raise SystemExit(
            "BLOCKER: files enumerated by the packaging authority are absent from "
            f"the worktree ({len(missing)}): {missing[:5]}\n"
            "  A missing subject file must block, not yield a smaller valid snapshot."
        )
    entries.sort()
    digest = hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest()
    return {
        "mode": "packaging-authority",
        "sha256": digest,
        "file_count": len(entries),
        # Provenance must name the module actually imported. This said
        # "build-plugin.py" after the enumeration moved to the neutral module --
        # a provenance field pointing at the wrong file is worse than none.
        "enumerator": "scripts/package_enumeration.py::enumerate_package_files",
        "exclude": list(TESTED_INPUT_EXCLUDE),
    }


def _assert_injective(rows: list[dict], label: str) -> None:
    """Fail loudly if two sites share a site_id.

    Non-negotiable: parity compares SETS of ids. A collision therefore hides a
    predicate AND reports PASS. Verified failure of the pre-ordinal scheme:
    two identical `_finding("MF-TEST", "same")` calls in one function produced
    2 sites and 1 id.
    """
    seen: dict[str, dict] = {}
    for r in rows:
        prev = seen.get(r["site_id"])
        if prev is not None:
            raise SystemExit(
                f"BLOCKER: site_id not injective in {label} set.\n"
                f"  id:   {r['site_id']}\n"
                f"  site A: {prev['file']}:{prev['line']}\n"
                f"  site B: {r['file']}:{r['line']}\n"
                "  Two predicates would share one adjudication row and parity "
                "would still PASS. Add a discriminator before generating."
            )
        seen[r["site_id"]] = r


# OUTCOME VOCABULARIES ARE COMPONENT-SPECIFIC. THERE IS NO GLOBAL MAP.
#
# Three of my errors, compounding:
#   1. "PASS iff exit 0" -- invented. LEGACY_READY and NOT_APPLICABLE also
#      exit 0, so every valid fixture in those classes would be rejected.
#   2. PASS/BLOCK -- invented. The authority's enum is READY|LEGACY_READY|
#      NOT_APPLICABLE|MISCONFIGURED. I took names from a review summary.
#   3. Worst: I applied ONE contract GLOBALLY to 30 heterogeneous suites, and
#      minted USAGE_ERROR/IO_ERROR as outcome tokens. The authority defines
#      those only as EXIT CATEGORIES, not outcomes -- and it scopes itself in
#      the sentence I skipped: MFHP:124 "Validators and *compatible preflight
#      gates* use:". Not universal law.
#      Consequence, verified: pre_phase_advance_check.py:1367 is
#      `return 1 if errors else 0` -- exit 1 is its GENUINE PREDICATE FAILURE
#      path. A global map would relabel every historical block in that
#      component as USAGE_ERROR, corrupting the corpus it exists to preserve.
#
# The repair: separate UNIVERSAL fixture facts from COMPONENT-SPECIFIC
# vocabulary. Universal and always required: fixture_file, case_id,
# expected_exit (exact), expected_code (exact or null). A native outcome is
# OPTIONAL and only meaningful under a declared contract.
OUTCOME_CONTRACTS: dict[str, tuple[str, ...]] = {
    # references/MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md:124-131. Governs
    # milestone_framework_validate and compatible preflight gates ONLY.
    "MFHP-9": ("READY", "LEGACY_READY", "NOT_APPLICABLE", "MISCONFIGURED"),
    # pre_phase_advance_check.py:1367 `return 1 if errors else 0`.
    # CLEAN -> 0, BLOCKED -> 1. I/O and argument failures (:1267/:1274/:313 ff.
    # return 2) are NOT outcomes of this contract -- record them under
    # EXIT-ONLY. Distinct contract; do not merge with MFHP-9.
    "PRE-PHASE": ("CLEAN", "BLOCKED"),
    # Components emitting only an exit code and finding code: no native
    # outcome vocabulary. expected_outcome MUST be null under this contract.
    "EXIT-ONLY": (),
}

# Exit expectations are NOT derived from the outcome. expected_exit is recorded
# exactly, per case, because it is the one fact every suite shares. Where a
# contract does constrain exit, it is declared here -- narrowly, per contract.
CONTRACT_OUTCOME_EXIT: dict[str, dict[str, int]] = {
    "MFHP-9": {"READY": 0, "LEGACY_READY": 0, "NOT_APPLICABLE": 0, "MISCONFIGURED": 4},
    # An earlier revision left this empty "because exit 2 exists", which let
    # CLEAN/exit-2 and BLOCKED/exit-0 pass -- unconstrained is not the same as
    # unknown. The source DOES fix these two: :1367 `return 1 if errors else 0`.
    # Exit 2 paths are I/O and argument failures, which are not outcomes of this
    # contract at all and belong under EXIT-ONLY.
    "PRE-PHASE": {"CLEAN": 0, "BLOCKED": 1},
}


def _check_suite_bound_manifest_consistency(
        report: dict, manifest_path: Path | None = None) -> tuple[bool, str]:
    """SUITE-BOUND MANIFEST CONSISTENCY. *Not* case completeness.

    The name is the honest property. Five rounds of this check were each named
    for something stronger than they proved:

      presence  -> "case_id" appeared in prose                     (round 4)
      file      -> a 1-case file passed, 10 suites absent          (round 4b)
      suite parity -> only 11 of 30 suites were discoverable       (round 5)
      "case completeness" -> a manifest naming each suite once passed (round 6)
      "case completeness" -> STILL an overclaim: `case_count == len(cases)`
                   compares the manifest to ITSELF. A fabricated one-case-per-
                   suite file with correctly computed hashes and arbitrary run
                   ids passes. Same loophole, more fields.       (round 7)

    WHAT THIS PROVES:
      * every discovered suite is represented (both directions);
      * suite bytes are CURRENT (sha256 vs disk) -- a suite edited since its
        recorded run has not reported on the code being adjudicated;
      * declared counts match the rows supplied;
      * every case path is a discovered suite (no phantom cases);
      * ids are unique, types are right, and each case's outcome is valid
        under ITS declared contract.

    WHAT THIS DOES NOT PROVE:
      * that the supplied rows EXHAUST a suite's cases;
      * that any case ever RAN.
    Both are unprovable from a document that describes itself. They become
    provable only when a central runner is the authoritative writer and its
    case registry drives execution -- i.e. the manifest is a side effect of
    running, not an artifact someone writes. That runner now exists
    (scripts/analysis/fixture_runner.py, 2026-07-16, suite granularity);
    this checker still verifies only the DOCUMENT, so nothing in this
    docstring's epistemics changes: from the manifest alone, completion
    remains ASSERTED EVIDENCE, and the trust upgrade comes from the runner's
    own fail-closed contract, not from this check.

    Returns (ok, detail). Never raises on a malformed manifest.

    `manifest_path` exists for focused negative tests ONLY (they synthesize
    manifests at temp paths); production callers pass nothing and get the
    canonical location.
    """
    path = manifest_path or (
        PLUGIN_ROOT / "docs" / "analysis" / "generated" / "fixture_manifest.json")
    if not path.is_file():
        return False, "absent: docs/analysis/generated/fixture_manifest.json"
    try:
        # utf-8-sig, not utf-8: a manifest written by PowerShell (or most
        # Windows editors) carries a BOM, and a strict utf-8 read rejects a
        # perfectly valid manifest as "unparseable". Discovered when a probe
        # manifest failed for the wrong reason -- the check reported the right
        # verdict via the wrong evidence, which is its own kind of false pass.
        man = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return False, f"unparseable: {exc}"
    except OSError as exc:
        return False, f"unreadable: {exc}"

    # Top-level type guard BEFORE any .get(). `[]`, `null`, `"text"`, and `42`
    # all parse as valid JSON and then raise AttributeError on man.get(...) --
    # contradicting this function's "never raises on a malformed manifest"
    # docstring. A contract the code violates is the defect this file exists to
    # find; it should not ship inside the finder.
    if not isinstance(man, dict):
        return False, f"malformed: top level must be an object, got {type(man).__name__}"

    problems: list[str] = []

    # WRITER BINDING (2026-07-16). Recording an identity is not verifying one
    # -- the same defect as the unenforced script_sha256 stamp, this time on
    # the runner. The manifest must present as the output of the authoritative
    # runner, and the runner file it names must be the file on disk NOW: a
    # runner edited since the evidence was written has not vouched for it.
    RUNNER_REL = "scripts/analysis/fixture_runner.py"
    if man.get("schema") != "coauthor-fixture-manifest/v1":
        problems.append(f"schema {man.get('schema')!r} != coauthor-fixture-manifest/v1")
    if man.get("written_by") != RUNNER_REL:
        problems.append(f"written_by {man.get('written_by')!r} is not the "
                        f"authoritative runner ({RUNNER_REL})")
    runner_file = PLUGIN_ROOT / RUNNER_REL
    if not runner_file.is_file():
        problems.append(f"authoritative runner absent from tree: {RUNNER_REL}")
    elif man.get("runner_sha256") != hashlib.sha256(runner_file.read_bytes()).hexdigest():
        problems.append("runner_sha256 STALE: the runner changed since this "
                        "evidence was written; re-run it")
    top_run_id = man.get("run_id")
    if not isinstance(top_run_id, str) or not top_run_id.strip():
        problems.append("manifest needs a nonempty top-level run_id")
        top_run_id = None
    cases = man.get("cases")
    if not isinstance(cases, list) or not cases:
        return False, "empty or malformed: 'cases' must be a non-empty list"

    seen: set[tuple[str, str]] = set()
    cases_per_suite: dict[str, int] = {}
    for i, c in enumerate(cases):
        if not isinstance(c, dict):
            problems.append(f"case[{i}] is not an object")
            continue
        fx, cid = c.get("fixture_file"), c.get("case_id")
        if not isinstance(fx, str) or not isinstance(cid, str):
            problems.append(f"case[{i}] needs string fixture_file and case_id")
            continue
        cases_per_suite[fx] = cases_per_suite.get(fx, 0) + 1
        if (fx, cid) in seen:
            problems.append(f"duplicate identity: {fx}::{cid}")
        seen.add((fx, cid))
        # PHANTOM CASE GUARD. Case paths were never checked against the
        # universe -- only completion-record paths were -- so a valid 30-suite
        # manifest could carry arbitrary extra cases for undiscovered paths and
        # still pass. Verified: a case for "scripts/TOTALLY_FAKE.py" raised
        # nothing.
        if fx not in report["suite_universe"]:
            problems.append(f"case names an undiscovered suite: {fx}::{cid}")

        # Runner-produced evidence must show the observation, and it must
        # match the declaration: a manifest whose observed_exit disagrees
        # with expected_exit records a run the runner should never have
        # written (it fails closed on mismatch), so its presence here means
        # fabrication or a broken writer -- both block.
        obs_exit = c.get("observed_exit")
        if type(obs_exit) is not int:
            problems.append(f"{fx}::{cid}: observed_exit must be int "
                            f"(got {type(obs_exit).__name__}); runner-produced "
                            "evidence carries the observation")
        # --- UNIVERSAL facts: required of every case in every suite ---
        exp_exit = c.get("expected_exit")
        # `type(x) is int`, NOT isinstance: JSON true/false decode to Python
        # bool, and bool subclasses int -- so isinstance(True, int) passes and
        # `"expected_exit": true` would sail through as a valid exit code.
        if type(exp_exit) is not int:
            problems.append(f"{fx}::{cid}: expected_exit must be int (got {type(exp_exit).__name__})")
        elif type(obs_exit) is int and obs_exit != exp_exit:
            problems.append(f"{fx}::{cid}: observed_exit {obs_exit} != "
                            f"expected_exit {exp_exit}")
        if "expected_code" not in c:
            problems.append(f"{fx}::{cid}: expected_code required (may be null)")
        elif c["expected_code"] is not None and not isinstance(c["expected_code"], str):
            problems.append(f"{fx}::{cid}: expected_code must be string or null")

        # --- COMPONENT-SPECIFIC: outcome only means something under a contract ---
        contract = c.get("outcome_contract")
        exp_out = c.get("expected_outcome")
        if contract not in OUTCOME_CONTRACTS:
            problems.append(
                f"{fx}::{cid}: outcome_contract {contract!r} unknown "
                f"(expected one of {tuple(OUTCOME_CONTRACTS)})"
            )
            continue
        allowed = OUTCOME_CONTRACTS[contract]
        if exp_out is None:
            pass  # legitimate: EXIT-ONLY, or a contract case with no native outcome
        elif not allowed:
            problems.append(
                f"{fx}::{cid}: contract {contract} defines no outcome vocabulary; "
                f"expected_outcome must be null, got {exp_out!r}"
            )
        elif exp_out not in allowed:
            problems.append(f"{fx}::{cid}: outcome {exp_out!r} not valid under {contract} {allowed}")
        # Exit/outcome consistency ONLY where the contract actually constrains
        # it. Never inferred globally: pre_phase_advance_check.py:1367 returns
        # exit 1 for genuine predicate failure, which no global map can express.
        table = CONTRACT_OUTCOME_EXIT.get(contract, {})
        if type(exp_exit) is int and exp_out in table and exp_exit != table[exp_out]:
            problems.append(
                f"{fx}::{cid}: {contract} requires exit {table[exp_out]} for "
                f"{exp_out}, got {exp_exit}"
            )

    # --- SUITE COMPLETION RECORDS: "appears once" is not "ran" ---
    discovered_suites = set(report["suite_universe"])
    suites_block = man.get("suites")
    if not isinstance(suites_block, list):
        problems.append("'suites' must be a list of per-suite completion records")
        suites_block = []
    reported: dict[str, dict] = {}
    for s in suites_block:
        if not isinstance(s, dict) or not isinstance(s.get("fixture_file"), str):
            problems.append("suite record needs a string fixture_file")
            continue
        # Duplicate completion records SILENTLY OVERWROTE each other here --
        # last-write-wins, so a second record could quietly replace the first
        # (verified: a bogus case_count:999 record displaced a valid one). A
        # suite reports completion exactly once.
        if s["fixture_file"] in reported:
            problems.append(f"duplicate completion record: {s['fixture_file']}")
            continue
        reported[s["fixture_file"]] = s

    for m in sorted(discovered_suites - set(reported)):
        problems.append(f"suite has no completion record: {m}")
    for p in sorted(set(reported) - discovered_suites):
        problems.append(f"completion record for undiscovered suite: {p}")

    run_ids: set[str] = set()
    for fx, rec in sorted(reported.items()):
        if fx not in discovered_suites:
            continue
        # Bind the record to the CURRENT source bytes. A suite edited since its
        # last recorded run has not reported on the code being adjudicated.
        want_sha = rec.get("suite_sha256")
        try:
            actual = hashlib.sha256((PLUGIN_ROOT / fx).read_bytes()).hexdigest()
        except OSError as exc:
            problems.append(f"{fx}: unreadable for hash binding ({exc})")
            continue
        if not isinstance(want_sha, str):
            problems.append(f"{fx}: completion record needs suite_sha256")
        elif want_sha != actual:
            problems.append(f"{fx}: suite_sha256 stale (source changed since the recorded run)")
        # run_id must IDENTIFY something. An empty string passed the old
        # isinstance(str) check. Decision taken: a manifest is the evidence of
        # ONE run, so every record shares one nonempty run_id. (The alternative
        # -- independent per-suite runs -- would have to be named suite_run_id
        # and would weaken the artifact to a pile of unrelated receipts.)
        rid = rec.get("run_id")
        if not isinstance(rid, str) or not rid.strip():
            problems.append(f"{fx}: completion record needs a nonempty run_id")
        else:
            run_ids.add(rid)
            if top_run_id is not None and rid != top_run_id:
                problems.append(f"{fx}: suite run_id {rid[:8]}... != top-level "
                                f"run_id {top_run_id[:8]}...")
        declared = rec.get("case_count")
        present = cases_per_suite.get(fx, 0)
        if type(declared) is not int:
            problems.append(f"{fx}: completion record needs int case_count")
        elif declared != present:
            problems.append(f"{fx}: declares {declared} cases, manifest carries {present}")
        elif declared == 0:
            problems.append(f"{fx}: declares 0 cases; a suite with no cases preserves nothing")

    if len(run_ids) > 1:
        problems.append(
            f"manifest mixes {len(run_ids)} run_ids; one manifest is the evidence of one run "
            "(use suite_run_id if independent per-suite runs are intended)"
        )

    # --- TESTED-INPUT BINDING: bind to the CODE UNDER TEST, not just the suite ---
    # Without this, the verified sequence passes wrongly: run a suite, record it,
    # then edit the SUBJECT (milestone_framework_validate.py) leaving the suite
    # untouched -- evidence describing behaviour that no longer exists.
    ti = man.get("tested_inputs")
    current = compute_tested_inputs()
    if not isinstance(ti, dict):
        problems.append(
            "manifest needs a tested_inputs snapshot binding the run to the code "
            "under test (suite_sha256 binds only the test file)"
        )
    else:
        if ti.get("mode") != current["mode"]:
            problems.append(
                f"tested_inputs.mode {ti.get('mode')!r} != {current['mode']!r}; "
                "a different snapshot mode is a different claim"
            )
        if (ti.get("enumerator") != current["enumerator"]
                or ti.get("exclude") != current["exclude"]):
            problems.append(
                "tested_inputs enumerator/exclude differ from this checker's; the "
                "recorded run measured a different input set"
            )
        # file_count was RECORDED AND NEVER CHECKED -- asserted evidence that
        # nothing verified, exactly like the unenforced script_sha256 stamp.
        # Either reconcile it or do not carry it.
        if ti.get("file_count") != current["file_count"]:
            problems.append(
                f"tested_inputs.file_count {ti.get('file_count')} != current "
                f"{current['file_count']}; the recorded run saw a different file set"
            )
        # PRE/POST equality. The runner must digest BEFORE and AFTER execution
        # and record both. A single post-run hash cannot detect code that
        # changed DURING the run -- the results would describe a mixture of two
        # trees, and the manifest would look perfectly bound.
        pre, post = ti.get("pre_sha256"), ti.get("post_sha256")
        if not isinstance(pre, str) or not isinstance(post, str):
            problems.append(
                "tested_inputs needs pre_sha256 and post_sha256 (digest before AND "
                "after execution; a post-run hash alone cannot detect code changing "
                "mid-run)"
            )
        elif pre != post:
            problems.append(
                f"tested_inputs pre/post differ ({pre[:12]} -> {post[:12]}): the code "
                "under test changed DURING the run; results describe no single tree"
            )
        elif post != current["sha256"]:
            problems.append(
                "tested_inputs STALE: code under test changed since the recorded run "
                f"(recorded {post[:12]}, current {current['sha256'][:12]})"
            )

    if problems:
        head = "; ".join(problems[:4])
        more = f" (+{len(problems)-4} more)" if len(problems) > 4 else ""
        return False, f"{len(problems)} problem(s): {head}{more}"
    return True, (
        f"{len(cases)} cases across {len(reported)}/{len(discovered_suites)} suites; "
        f"suites + tested-inputs ({current['file_count']} files, "
        f"{current['sha256'][:12]}) hash-bound"
    )


def _self_sha() -> str:
    """Hash of this script, stamped into generated artifacts.

    Provenance lives in the GENERATED file, never in prose. A hash written into
    a design doc goes stale the moment the script changes -- the same
    snapshot-freeze antipattern as references/schemas/version_planes.json,
    which ratifies drift instead of resolving it. Two review rounds quoted two
    different stale hashes from prose before this was fixed.
    """
    return hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()[:12]


def discover_suite_universe() -> list[str]:
    """EVERY test suite under scripts/, independent of code literals.

    THE SUITE UNIVERSE MUST NOT BE DERIVED FROM CODE LITERALS. The previous
    revision filtered on STATIC_RE *before* fixture classification, so a suite
    became visible only if it happened to mention a finding code. Result: 11 of
    27 suites discovered. A manifest covering "11/11" would have passed while
    16 suites -- migration, bootstrap, end-to-end, phase-notification, parity --
    were silently absent.

    This is the founding error of this whole file, recurring at the suite level:
    a population defined by the thing you are looking for cannot tell you what
    you are missing. PASS-case suites are precisely the ones with no code
    literal, and they are precisely the ones that make a regression corpus
    falsifiable.

    Definition: any file under scripts/ whose name matches a FIXTURE_MARKER.
    No content filter. Ever.
    """
    universe: list[str] = []
    self_path = Path(__file__).resolve()
    for path in sorted(SCRIPTS_DIR.rglob("*.py")):
        if "__pycache__" in path.parts or path.resolve() == self_path:
            continue
        if any(m in path.name for m in FIXTURE_MARKERS):
            universe.append(path.relative_to(PLUGIN_ROOT).as_posix())
    return universe


def discover_emitters() -> tuple[list[str], list[str]]:
    """Production emitters (code-literal filtered) and fixture files WITH literals.

    The literal filter is correct for PRODUCTION emitters -- a production file
    with no code emits no predicate. It is NOT correct for the suite universe;
    see discover_suite_universe(), which is the authority for fixture coverage.

    The second return value is only the subset of suites containing a code
    literal, retained for diagnostics. It is NOT the suite universe and must
    never be used as one.
    """
    emitters: list[str] = []
    fixtures_with_literals: list[str] = []
    self_path = Path(__file__).resolve()
    for path in sorted(SCRIPTS_DIR.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        # Never scan the census itself: its docstring quotes real codes as
        # examples, which would enter the matrix as phantom predicates.
        if path.resolve() == self_path:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not STATIC_RE.search(text):
            continue
        rel = path.relative_to(PLUGIN_ROOT).as_posix()
        if any(m in path.name for m in FIXTURE_MARKERS):
            fixtures_with_literals.append(rel)
        else:
            emitters.append(rel)
    return emitters, fixtures_with_literals


def _enclosing_function(tree: ast.AST) -> dict[int, str]:
    """Map line number -> enclosing function name, for site provenance."""
    owner: dict[int, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", node.lineno)
            for ln in range(node.lineno, end + 1):
                owner.setdefault(ln, node.name)
    return owner


def _string_literals(node: ast.AST) -> list[str]:
    """Every string constant reachable from node, incl. f-string prefixes."""
    out: list[str] = []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        out.append(node.value)
    elif isinstance(node, ast.JoinedStr):
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                out.append(v.value)
                break
    elif isinstance(node, ast.IfExp):
        out.extend(_string_literals(node.body))
        out.extend(_string_literals(node.orelse))
    return out


def collect_sites(rel: str, text: str) -> list[dict]:
    """One row per emission SITE. This is the unit of adjudication.

    Covers every shape observed in this tree:
      Finding(code="E-...")                       keyword
      Finding(code="A" if x else "B")             conditional keyword
      _finding("MF-...", field, msg)              positional
      findings.append(("APG-...", "msg"))         tuple literal
      _load_json(path, "APG-PROFILE-MISSING", f)  threaded through a helper
      codes.append("MF-POLICY-PIN-EPOCH-STALE")   bare list append
      f"APG-SEQUENCE-{target}"                    dynamic family
      "[ADVISORY] APG-EXEMPLAR-DENNETT-PENDING: " embedded in prose
    """
    sites: list[dict] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return sites
    owner = _enclosing_function(tree)
    dup_counter: dict[tuple, int] = {}

    def _expr_hash(node: ast.AST) -> str:
        """Normalized AST hash of the emitting expression.

        Durable row identity must survive an unrelated line insertion above the
        site, so line numbers cannot be the identity -- only a locator. Hash the
        structure with position attributes stripped.
        """
        try:
            clone = ast.parse(ast.unparse(node), mode="eval").body
        except (SyntaxError, ValueError, AttributeError):
            clone = node
        dump = ast.dump(clone, annotate_fields=True, include_attributes=False)
        return hashlib.sha256(dump.encode("utf-8")).hexdigest()[:12]

    def add(line: int, code: str, shape: str, node: ast.AST | None = None,
            bare_ok: bool = False) -> None:
        code = code.strip()
        # Prose-embedded codes: pull the code token out of the sentence.
        #
        # bare_ok (added 2026-07-16): a code-shaped literal WITHOUT a known
        # prefix, vouched by arriving through a finding-shaped call. The
        # previous version matched these in the collector and then DROPPED
        # them here -- the CODE_SHAPED_RE branch below this early return was
        # dead code. Verified live losses: SECTION_MISSING_FIELD (:519),
        # SECTION_FIELD_EMPTY (:531,:540), TRIGGER_UNKNOWN (:1024) in
        # pre_phase_advance_check.py -- four Finding-emitted predicates with
        # no row, no mention-only listing, invisible. TRIGGER_UNKNOWN is even
        # named by matrix ruling A-13. A population defined by a prefix list
        # is the same under-narrow allowlist as every other in this file.
        if not code.startswith(PREFIXES):
            if bare_ok and CODE_SHAPED_RE.fullmatch(code):
                pass  # vouched bare code; keep verbatim
            else:
                m = STATIC_RE.search(code)
                if not m:
                    return
                code = m.group(0)
        code = code.rstrip("-")
        if not (code.startswith(PREFIXES) or CODE_SHAPED_RE.fullmatch(code)):
            return
        fn = owner.get(line, "<module>")
        ehash = _expr_hash(node) if node is not None else "nonode000000"
        module = rel.rsplit("/", 1)[-1][:-3]  # module identity: two files may
                                              # share a function name.
        # DURABLE IDENTITY: code @ module:function # asthash ~ ordinal.
        #
        # The ordinal is REQUIRED, not cosmetic. code@function#asthash is NOT
        # injective: two identical `_finding("MF-TEST", "same")` calls in one
        # function hash identically and collapse to a single id -- and parity
        # sets them, so one predicate silently loses its row while the check
        # still reports PASS. Verified: 2 sites -> 1 unique id.
        #
        # The ordinal counts prior identical (code, module, fn, ehash) tuples in
        # source order within the file. It shifts only if an identical sibling
        # is inserted before it -- which genuinely is a new predicate needing
        # adjudication -- and is stable under unrelated line moves.
        key = (code, module, fn, ehash)
        ordinal = dup_counter.get(key, 0)
        dup_counter[key] = ordinal + 1
        sites.append({
            "site_id": f"{code}@{module}:{fn}#{ehash}~{ordinal}",
            "file": rel,
            "line": line,
            "code": code,
            "shape": shape,
            "module": module,
            "function": fn,
            "expr_hash": ehash,
            "ordinal": ordinal,
            "dynamic": "f-string" in shape,
        })

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fname = (
                node.func.id if isinstance(node.func, ast.Name)
                else node.func.attr if isinstance(node.func, ast.Attribute)
                else ""
            )
            # Any string arg (positional or keyword) that looks like a code.
            candidates: list[ast.AST] = list(node.args)
            for kw in node.keywords:
                candidates.append(kw.value)
            for arg in candidates:
                for lit in _string_literals(arg):
                    if not lit:
                        continue
                    if lit.startswith(PREFIXES) or (
                        CODE_SHAPED_RE.fullmatch(lit) and "finding" in fname.lower()
                    ):
                        shape = "f-string-family" if isinstance(arg, ast.JoinedStr) else f"call:{fname}"
                        # bare_ok: the second disjunct vouches non-prefix codes
                        # (finding-shaped call). Without it add() dropped them.
                        add(getattr(arg, "lineno", node.lineno), lit, shape, node,
                            bare_ok=True)
                    elif STATIC_RE.search(lit) and (
                        "[ADVISORY]" in lit or "[BLOCKER]" in lit
                    ):
                        # [BLOCKER]-prose added 2026-07-16: refusal banners
                        # emitted via bare print() -- e.g. APG-DISPATCH-REFUSED
                        # in assignment_dispatch_preflight.py (:22, :86) -- are
                        # live emissions the [ADVISORY]-only branch missed.
                        shape = ("advisory-prose" if "[ADVISORY]" in lit
                                 else "blocker-prose")
                        add(getattr(arg, "lineno", node.lineno), lit, shape, node)
                # tuple: (code, "msg") -- incl. (f"APG-SEQUENCE-{target}", msg).
                # The f-string must keep its dynamic flag HERE: an earlier
                # revision routed tuple-wrapped f-strings through the plain
                # "tuple" shape and reported 0 dynamic families where there are 2.
                if isinstance(arg, ast.Tuple) and arg.elts:
                    head = arg.elts[0]
                    shape = "tuple-f-string" if isinstance(head, ast.JoinedStr) else "tuple"
                    for lit in _string_literals(head):
                        if lit.startswith(PREFIXES):
                            add(getattr(head, "lineno", node.lineno), lit, shape, node)
        elif isinstance(node, ast.Tuple) and len(node.elts) == 2:
            head = node.elts[0]
            shape = "tuple-f-string" if isinstance(head, ast.JoinedStr) else "tuple-literal"
            for lit in _string_literals(head):
                if lit.startswith(PREFIXES):
                    add(getattr(head, "lineno", node.lineno), lit, shape, node)
    return sites


def collect_mentions(rel: str, text: str, emitted_lines: set[int]) -> list[dict]:
    """Code-shaped tokens on lines with no detected emission.

    Reported for adjudication, NOT auto-classified as dead: e.g.
    W-SNOWBALL-PRECONDITION-UNMET is comment-only here but emitted by
    run-phase-2 Step 0.5.
    """
    out: list[dict] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if i in emitted_lines:
            continue
        for m in STATIC_RE.finditer(line):
            out.append({"file": rel, "line": i, "code": m.group(0)})
    return out


def build_report() -> dict:
    emitters, fixtures = discover_emitters()
    suite_universe = discover_suite_universe()
    if not emitters:
        print("BLOCKER: no emitters discovered under scripts/", file=sys.stderr)
        sys.exit(2)

    all_sites: list[dict] = []
    all_fixture_sites: list[dict] = []
    all_mentions: list[dict] = []

    for rel in emitters + fixtures:
        text = (PLUGIN_ROOT / rel).read_text(encoding="utf-8")
        sites = collect_sites(rel, text)
        mentions = collect_mentions(rel, text, {s["line"] for s in sites})
        if rel in fixtures:
            all_fixture_sites.extend(sites)
        else:
            all_sites.extend(sites)
            all_mentions.extend(mentions)

    # Deduplicate by site identity (file, line, code). One AST node can be
    # reached by more than one collector path (e.g. a literal matched both as a
    # positional arg and via the tuple branch), which produced 17 phantom rows
    # -- an OVER-count. Every prior census error under-counted; this one did
    # not, which is exactly why the parity check (242) and the summary (259)
    # disagreed and caught it. Keep the first shape seen; record the rest.
    def _dedupe(rows: list[dict]) -> list[dict]:
        seen: dict[tuple[str, int, str], dict] = {}
        for r in rows:
            key = (r["file"], r["line"], r["code"])
            if key in seen:
                seen[key].setdefault("also_matched", []).append(r["shape"])
            else:
                seen[key] = r
        return list(seen.values())

    all_sites = _dedupe(all_sites)
    all_fixture_sites = _dedupe(all_fixture_sites)

    # HARD UNIQUENESS ASSERTION. Parity sets the ids, so a non-injective id
    # scheme collapses two predicates into one row and still reports PASS --
    # the exact silent-deletion failure this whole census exists to prevent.
    # Fail loudly at GENERATION time; an id change after adjudication would
    # invalidate every human overlay row.
    _assert_injective(all_sites, "production")
    _assert_injective(all_fixture_sites, "fixture")

    all_sites.sort(key=lambda s: (s["file"], s["line"], s["code"]))
    all_fixture_sites.sort(key=lambda s: (s["file"], s["line"], s["code"]))
    all_mentions.sort(key=lambda s: (s["file"], s["line"], s["code"]))

    codes = sorted({s["code"] for s in all_sites})
    sites_per_code: dict[str, int] = {}
    for s in all_sites:
        sites_per_code[s["code"]] = sites_per_code.get(s["code"], 0) + 1

    mention_only = sorted({m["code"] for m in all_mentions} - set(codes))

    return {
        "emitters": emitters,
        # Code-literal-independent. THE authority for fixture coverage.
        "suite_universe": suite_universe,
        # Diagnostic only: suites that happen to contain a code literal.
        # NEVER use as the suite universe (it found 11 of 27).
        "fixtures": fixtures,
        "sites": all_sites,
        "fixture_sites": all_fixture_sites,
        "mention_only_candidates": mention_only,
        "codes": codes,
        "sites_per_code": dict(sorted(sites_per_code.items(), key=lambda kv: (-kv[1], kv[0]))),
        "totals": {
            "emitters": len(emitters),
            "fixtures": len(fixtures),
            "codes": len(codes),
            # THE unit of adjudication. Not len(codes).
            "emission_sites": len(all_sites),
            "fixture_sites": len(all_fixture_sites),
            "mention_only_candidates": len(mention_only),
            "dynamic_families": sum(1 for s in all_sites if s["dynamic"]),
        },
    }


def emit_matrix(report: dict) -> str:
    """Generate one adjudication row per emission site.

    Hand-written matrices cannot track 30 MF-POLICY branches; that is how a
    label survives while its rules are deleted. Rows are GENERATED; humans
    adjudicate.

    Row identity is code@module:function#asthash~ordinal -- INJECTIVE and
    deterministic, but NOT durable: an identical sibling inserted before an
    existing site renumbers it. Freeze emitters during adjudication.
    """
    man_ok, _man_detail = _check_suite_bound_manifest_consistency(report)
    man_cases: list[dict] = []
    if man_ok:
        man_path = PLUGIN_ROOT / "docs" / "analysis" / "generated" / "fixture_manifest.json"
        man_cases = json.loads(man_path.read_text(encoding="utf-8-sig"))["cases"]
    lines = [
        "<!-- GENERATED by scripts/analysis/code_census.py --emit-matrix. Do not hand-edit rows;",
        "     re-run to regenerate. Adjudicate the TBD columns via the tracked overlay.",
        f"     script_sha256={_self_sha()}",
        f"     production_sites={len(report['sites'])}",
        f"     suite_universe={len(report['suite_universe'])}"
        f"  (code-literal-independent; authority for fixture coverage)",
        (f"     fixture_cases={len(man_cases)} (from fixture_manifest.json, "
         f"suite-granularity)" if man_ok
         else "     fixture_cases=0 (manifest absent or invalid; run "
              "scripts/analysis/fixture_runner.py)"),
        f"     fixture_literal_sites={len(report['fixture_sites'])}"
        f" in {len(report['fixtures'])} suites - NOT cases, diagnostic only",
        "",
        "     Row IDs are code@module:function#asthash~ordinal.",
        "     DETERMINISTIC, not durable: inserting an identical sibling BEFORE",
        "     an existing site renumbers that site's ordinal. Freeze emitters",
        "     during adjudication, or re-key the overlay on regeneration.",
        "     file:line is a LOCATOR, not identity.",
        "",
        "     THESE ARE CANDIDATE PREDICATES, NOT PROVEN ONES. A site may be a",
        "     diagnostic, one branch of a helper whose condition lives elsewhere,",
        "     a code-table entry shared by several conditions, or a wrapper. This",
        "     is the adjudication queue; it is not evidence of preservation. -->",
        "",
        "## Production predicate candidates",
        "",
        "| Row ID | Code | Locator | Function | Shape | Old outcome | New predicate | Fixture | Disp | Appr |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in report["sites"]:
        lines.append(
            f"| `{s['site_id']}` | `{s['code']}` | `{s['file']}:{s['line']}` | `{s['function']}()` "
            f"| {s['shape']} | TBD | TBD | TBD | TBD | [ ] |"
        )

    # FIXTURE COVERAGE IS NOT IMPLEMENTED, AND IS NOT FAKED HERE.
    #
    # A previous revision generated "16 fixture cases" from AST code literals
    # and called that regression coverage. It is not. Those 16 are code-emission
    # CALL SITES -- all MF-EXEMPLAR -- not test cases:
    #   * Passing cases carry NO expected code, so they are invisible to a
    #     literal scan: absent_claim_without_registration, ledger_analytical_scalar.
    #     These are exactly the PASS cases that make the corpus falsifiable --
    #     "every old block still blocks" is satisfiable by a gate that blocks
    #     everything, and only PASS rows catch that.
    #   * A single static site inside a loop executes MANY cases.
    # So AST discovery over-counts loops, under-counts PASS cases, and cannot
    # know an expected outcome at all.
    #
    # Correct repair (built 2026-07-16 at SUITE granularity): the central
    # runner scripts/analysis/fixture_runner.py executes a registered
    # invocation per suite and writes the manifest as a side effect; fixture
    # rows generate FROM THE MANIFEST (see the man_ok branch above). Native
    # per-case emission BY each suite is still future work, per suite.
    # When the manifest is absent/invalid this section declares the gap
    # rather than asserting coverage.
    # Use report["fixtures"] -- EVERY discovered smoketest file -- not
    # report["fixture_sites"], which lists only files containing a code
    # literal. Deriving the awaiting-manifest list from code literals listed
    # 1 file instead of 11: the same defect as the fixture rows themselves,
    # since PASS-case suites carry no code literal and vanish from the scan.
    if man_ok:
        lines += [
            "",
            "## Fixture cases (regression corpus) - from fixture_manifest.json",
            "",
            "Written by scripts/analysis/fixture_runner.py as a SIDE EFFECT of",
            "execution: each row records a suite invocation that actually ran,",
            "with its exit matched against the registry's declared expectation",
            "and the tested-input tree hash-bound pre and post. Granularity is",
            "per registered INVOCATION -- a row does not claim to exhaust the",
            "suite's internal cases (see the runner's docstring).",
            "",
            "| Suite | Case | Expected exit | Expected code | Contract |",
            "|---|---|---|---|---|",
        ]
        for c in man_cases:
            lines.append(
                f"| {c['fixture_file']} | {c['case_id']} | {c['expected_exit']} "
                f"| {c['expected_code'] if c['expected_code'] is not None else 'null'} "
                f"| {c['outcome_contract']} |"
            )
        return "\n".join(lines)

    fixture_files = sorted(report["suite_universe"])
    lines += [
        "",
        "## Fixture cases (regression corpus) - NOT IMPLEMENTED",
        "",
        "**No fixture rows are generated.** AST code-literal discovery cannot",
        "produce a regression corpus: clean-outcome cases carry no expected",
        "code and are invisible to a literal scan, one static site in a loop",
        "runs many cases, and a literal cannot carry an expected outcome.",
        "Generating rows from it would assert coverage that does not exist.",
        "",
        "**Blocked on the manifest contract.** Each suite emits, as a side",
        "effect of EXECUTION, a completion record + its cases:",
        "",
        "```jsonc",
        '  "suites": [ { "fixture_file": "scripts/<suite>.py",',
        '                "suite_sha256": "<current bytes>",',
        '                "case_count": N, "run_id": "<uuid>" } ],',
        '  "cases":  [ { "fixture_file": "scripts/<suite>.py",',
        '                "case_id": "<id>",',
        '                "expected_exit": 0,          // UNIVERSAL, exact',
        '                "expected_code": null,       // UNIVERSAL, exact-or-null',
        '                "outcome_contract": "MFHP-9|PRE-PHASE|EXIT-ONLY",',
        '                "expected_outcome": "READY"  // OPTIONAL, per-contract',
        "              } ]",
        "```",
        "",
        "There is NO global outcome enum. `MFHP-9` (READY|LEGACY_READY|",
        "NOT_APPLICABLE|MISCONFIGURED) governs milestone_framework_validate and",
        "compatible preflight gates ONLY -- MFHP:124 scopes itself. Exit 1 in",
        "pre_phase_advance_check.py:1367 is a genuine predicate failure, not a",
        "usage error; a global map would corrupt those historical blocks.",
        "Universal facts (suite, case_id, exact exit, exact code) are what all",
        "30 heterogeneous suites share.",
        "",
        f"Fixture files awaiting a manifest ({len(fixture_files)}):",
        "",
    ]
    for f in fixture_files:
        lines.append(f"- [ ] `{f}`")
    return "\n".join(lines)


def parity(report: dict, matrix_path: Path) -> int:
    """Set parity, by identity -- never by count.

    A count check is satisfiable by coincidence: retire one predicate, add
    another, total unchanged. Identity parity is not.
    """
    if not matrix_path.is_file():
        print(f"BLOCKER: matrix not found: {matrix_path}", file=sys.stderr)
        return 1
    text = matrix_path.read_text(encoding="utf-8")

    # Identity is site_id = code@module:function#asthash~ordinal -- injective
    # and DETERMINISTIC, not durable (an identical sibling inserted before a
    # site renumbers it; freeze emitters during adjudication). NOT file:line:
    # a conditional emitter puts two predicates on one line, and an unrelated
    # insertion above a site shifts every line below it.
    #
    # Parity scores PRODUCTION only. Fixture coverage is reported as a blocking
    # gap via _check_fixture_manifest() against the code-literal-INDEPENDENT
    # suite universe -- scoring fixture code-literals as coverage was the false
    # claim this replaces.
    discovered = {s["site_id"] for s in report["sites"]}
    covered = set(re.findall(r"`([A-Z][A-Z0-9_-]+@[\w.:<>-]+#[0-9a-f]{12}~\d+)`", text))

    uncovered = sorted(discovered - covered)     # live predicate, no row
    orphaned = sorted(covered - discovered)      # row, predicate gone

    # CHECKER PROVENANCE. The generated header stamps script_sha256, but nothing
    # enforced it -- so a changed checker could evaluate a matrix generated by a
    # previous one and report PASS. The checker is excluded from tested_inputs
    # (a subject cannot vouch for its own observer), so it must be bound HERE.
    stamped = re.search(r"script_sha256=([0-9a-f]{12})", text)
    checker_now = _self_sha()
    checker_problem = None
    if not stamped:
        checker_problem = "matrix carries no script_sha256 stamp; regenerate"
    elif stamped.group(1) != checker_now:
        checker_problem = (
            f"matrix was generated by checker {stamped.group(1)}, current is "
            f"{checker_now}; regenerate before trusting parity"
        )

    # Fixture manifest presence is a FILE check, never a text check.
    # A first attempt tested `"case_id" in text and "expected_outcome" in text`
    # and reported MANIFEST PRESENT -- because the NOT-IMPLEMENTED prose
    # *mentions those words*. A check satisfiable by prose describing the thing,
    # rather than the thing existing, is precisely the presence-not-
    # correspondence defect this redesign exists to remove.
    fixture_manifest_present, fixture_manifest_detail = (
        _check_suite_bound_manifest_consistency(report)
    )

    # Literal presence per discovered code -- NOT a prefix regex. The prior
    # regex `(?:APG|MF|E|W|G[0-3])-...` was the prefix allowlist again, one
    # level down: when the collector learned bare codes (SECTION_MISSING_FIELD,
    # TRIGGER_UNKNOWN, 2026-07-16), the codes appeared in the matrix and this
    # check still reported them absent. The population is report["codes"];
    # test each member directly.
    missing_codes = sorted(c for c in report["codes"] if f"`{c}`" not in text)

    # ASCII only: an em dash here is what crashed this gate on a cp949 console.
    print("SET PARITY - census vs matrix")
    print(f"- Emitters scanned:      {report['totals']['emitters']}")
    print(f"- Production sites:      {len(discovered)}")
    print(f"- Covered:               {len(covered & discovered)}/{len(discovered)}")
    print(f"- UNCOVERED production:  {len(uncovered)}  (live predicate, no row)")
    for u in uncovered[:40]:
        print(f"      {u}")
    if len(uncovered) > 40:
        print(f"      ... and {len(uncovered)-40} more")
    print(f"- ORPHANED rows:         {len(orphaned)}  (row cites a site that no longer exists)")
    for o in orphaned:
        print(f"      {o}")
    print(f"- Codes absent:          {len(missing_codes)}")
    for m in missing_codes:
        print(f"      {m}")

    ok = not uncovered and not orphaned and not missing_codes and not checker_problem
    print()
    print("CHECKER PROVENANCE:             "
          + ("PASS" if not checker_problem else f"FAIL - {checker_problem}"))
    print("PRODUCTION PARITY:              " + ("PASS" if ok else "FAIL"))
    print("SUITE-BOUND MANIFEST CONSISTENCY: "
          + ("PASS" if fixture_manifest_present else "NOT IMPLEMENTED (blocking)"))
    print(f"                   {fixture_manifest_detail}")
    print()
    print("SCOPE OF THIS CHECK - read before quoting it:")
    print("  * Proves every discovered code LITERAL has an adjudication row.")
    print("  * Does NOT prove predicates are preserved: rows are TBD candidates,")
    print("    and a site may be a diagnostic, a shared code-table entry, a")
    print("    wrapper, or one branch of a condition living elsewhere.")
    print("  * The manifest property is SUITE-BOUND CONSISTENCY, not case")
    print("    completeness: it proves every suite is represented, bytes are")
    print("    current, and declared counts match supplied rows. It does NOT")
    print("    prove the rows exhaust a suite's cases, nor that any case RAN --")
    print("    `case_count == len(cases)` compares the manifest to itself.")
    print("    Completion stays ASSERTED EVIDENCE until a central runner is the")
    print("    authoritative writer and its case registry drives execution.")
    # Production parity alone is not a green light; the fixture gap is blocking.
    return 0 if (ok and fixture_manifest_present) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--emit-matrix", action="store_true")
    ap.add_argument("--parity", type=str, default=None, metavar="MATRIX_MD")
    args = ap.parse_args()

    report = build_report()

    if args.parity:
        return parity(report, Path(args.parity) if Path(args.parity).is_absolute()
                      else PLUGIN_ROOT / args.parity)
    if args.emit_matrix:
        print(emit_matrix(report))
        return 0
    if args.json:
        blob = json.dumps(report, indent=2, sort_keys=True)
        print(blob)
        print(f"\n// sha256: {hashlib.sha256(blob.encode()).hexdigest()}", file=sys.stderr)
        return 0

    t = report["totals"]
    print("CODE CENSUS (per-site)")
    print(f"- Plugin root:        {PLUGIN_ROOT}")
    print(f"- Emitters discovered:{t['emitters']}")
    for e in report["emitters"]:
        print(f"      {e}")
    print(f"- Fixtures discovered:{t['fixtures']} (regression corpus; matrix must cover these too)")
    print()
    print(f"- Distinct codes:     {t['codes']}")
    print(f"- EMISSION SITES:     {t['emission_sites']}   <-- the unit of adjudication")
    print(f"- Fixture sites:      {t['fixture_sites']}")
    print(f"- Dynamic families:   {t['dynamic_families']}")
    print(f"- Mention-only cand.: {t['mention_only_candidates']} (adjudicate; NOT auto-dead)")
    for c in report["mention_only_candidates"]:
        print(f"      {c}")
    print()
    print("Sites per code (a label is not a predicate):")
    for code, n in report["sites_per_code"].items():
        if n > 1:
            print(f"      {n:>3}  {code}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
