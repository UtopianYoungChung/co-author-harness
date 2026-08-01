#!/usr/bin/env python3
"""Measure package prompt surfaces and enforce the owned debt ratchet.

The pinned policy measures `agents/`, `references/`, `skills/*/SKILL.md`,
and `references/_snippets/` with tiktoken 0.12.0/cl100k_base.

Per-class budgets (from the v0.15.0 architecture):

    File class                  Warn      Fail
    --------------------------  --------  -----------------
    agents/*.md                 > 300     > 700  tokens
    references/*.md             > 600     > 1000 tokens
    skills/*/SKILL.md           > 120     > 250  tokens
    references/_snippets/*.md   > 40      > 60   tokens

Output
------
Prints per-class debt, the ten largest files, and ratchet blockers. `--out`
writes JSON. Exit 0 means no debt growth, 1 means ratchet refusal, and 2 means
the policy, baseline, encoder, load graph, exception, or environment failed.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, List, Tuple

HARNESS = Path(__file__).resolve().parent.parent
POLICY_PATH = HARNESS / "references" / "policies" / "token_budget.v1.json"
POLICY_SCHEMA_PATH = HARNESS / "references" / "schemas" / "token_budget_policy.schema.json"
PINNED_TIKTOKEN_VERSION = "0.12.0"
PINNED_ENCODING = "cl100k_base"
EXPECTED_LOAD_GRAPH = (
    "references/GROUNDING_PROTOCOL.md",
    "references/CLAUDE.md",
    "references/MANIFEST.md",
)
EXPECTED_OWNERSHIP_PREFIXES = {
    "references/_snippets/",
    "references/",
    "agents/",
    "skills/",
    "__always_loaded_floor__",
}
RATCHET_CONTRACT = (
    "immutable_baseline",
    "new_breach_refused",
    "existing_breach_growth_refused",
    "always_loaded_floor_growth_refused",
    "unknown_policy_refused",
    "encoder_load_graph_mismatch_refused",
    "expired_exception_refused",
    "ownerless_exception_refused",
)


class TokenBudgetError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Class definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FileClass:
    name: str
    glob_pattern: str       # rglob pattern relative to HARNESS
    warn_tokens: int
    fail_tokens: int
    base: str               # root directory under HARNESS

    def iter_paths(self) -> Iterable[Path]:
        base_dir = HARNESS / self.base
        if not base_dir.is_dir():
            return
        for p in sorted(base_dir.rglob(self.glob_pattern)):
            yield p


FILE_CLASSES: List[FileClass] = [
    FileClass(
        name="agents",
        base="agents",
        glob_pattern="*.md",
        warn_tokens=300,
        fail_tokens=700,
    ),
    FileClass(
        name="references (non-snippet)",
        base="references",
        glob_pattern="*.md",
        warn_tokens=600,
        fail_tokens=1000,
    ),
    FileClass(
        name="skills",
        base="skills",
        glob_pattern="SKILL.md",
        warn_tokens=120,
        fail_tokens=250,
    ),
    FileClass(
        name="snippets",
        base="references/_snippets",
        glob_pattern="*.md",
        warn_tokens=40,
        fail_tokens=60,
    ),
]


@dataclass
class FileReport:
    path: str
    cls: str
    tokens: int
    warn_threshold: int
    fail_threshold: int
    status: str             # "ok" | "warn" | "fail"


@dataclass
class BudgetReport:
    schema_version: str = "0.15.0-pre"
    total_files: int = 0
    by_class: dict = field(default_factory=dict)
    breaches: List[FileReport] = field(default_factory=list)
    top10_largest: List[FileReport] = field(default_factory=list)
    always_loaded_floor_tokens: int = 0
    files: List[FileReport] = field(default_factory=list)
    ratchet_blockers: List[dict] = field(default_factory=list)
    policy: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Counting
# ---------------------------------------------------------------------------


def _get_encoder():
    try:
        import tiktoken
    except ImportError as exc:
        raise SystemExit(
            f"[BLOCKER] tiktoken is required for the token-budget check; "
            f"install via `pip install tiktoken`. ({exc})"
        )
    installed = importlib.metadata.version("tiktoken")
    if installed != PINNED_TIKTOKEN_VERSION:
        raise SystemExit(
            f"[BLOCKER] TOKEN-BUDGET-ENCODER-MISMATCH: tiktoken {installed} "
            f"!= pinned {PINNED_TIKTOKEN_VERSION}"
        )
    return tiktoken.get_encoding(PINNED_ENCODING)


def count_tokens(path: Path, encoder) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"[BLOCKER] cannot read {path}: {exc}")
    return len(encoder.encode(text))


def classify(tokens: int, warn: int, fail: int) -> str:
    if tokens > fail:
        return "fail"
    if tokens > warn:
        return "warn"
    return "ok"


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


# References that PR-4b designated as "always-loaded floor."
ALWAYS_LOADED_FILES = [
    Path("references/GROUNDING_PROTOCOL.md"),
    Path("references/CLAUDE.md"),
    Path("references/MANIFEST.md"),
]


def _exclude_snippets_from_references(path: Path) -> bool:
    """References class measures non-snippet refs only; snippets have their
    own class with a tighter budget."""
    rel = path.relative_to(HARNESS)
    return "_snippets" in rel.parts


def _load_policy() -> dict:
    try:
        from jsonschema import Draft202012Validator
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        schema = json.loads(POLICY_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (ImportError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TokenBudgetError(f"TOKEN-BUDGET-POLICY-UNKNOWN: {exc}") from exc
    return _validate_policy_value(policy, schema, Draft202012Validator)


def _validate_policy_value(policy: dict, schema: dict, validator_class=None) -> dict:
    if policy.get("schema_version") != "token-budget-policy/1.0.0":
        raise TokenBudgetError("TOKEN-BUDGET-POLICY-UNKNOWN: unsupported schema_version")
    if validator_class is None:
        from jsonschema import Draft202012Validator as validator_class
    errors = sorted(validator_class(schema).iter_errors(policy), key=lambda e: list(e.path))
    if errors:
        raise TokenBudgetError(
            "TOKEN-BUDGET-POLICY-UNKNOWN: "
            + "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
        )
    encoder = policy["encoder"]
    if (
        encoder["package"] != "tiktoken"
        or encoder["version"] != PINNED_TIKTOKEN_VERSION
        or encoder["encoding"] != PINNED_ENCODING
    ):
        raise TokenBudgetError("TOKEN-BUDGET-ENCODER-MISMATCH: policy encoder is not pinned")
    if tuple(policy["load_graph"]["always_loaded"]) != EXPECTED_LOAD_GRAPH:
        raise TokenBudgetError("TOKEN-BUDGET-LOAD-GRAPH-MISMATCH: always-loaded graph differs")
    declared_classes = policy["classes"]
    expected_classes = {cls.name for cls in FILE_CLASSES}
    if set(declared_classes) != expected_classes:
        raise TokenBudgetError("TOKEN-BUDGET-POLICY-UNKNOWN: class set differs")
    for cls in FILE_CLASSES:
        declared = declared_classes.get(cls.name)
        if declared != {"warn_tokens": cls.warn_tokens, "fail_tokens": cls.fail_tokens}:
            raise TokenBudgetError(f"TOKEN-BUDGET-POLICY-UNKNOWN: class drift for {cls.name}")
    ownership_prefixes = [str(row["prefix"]) for row in policy["ownership"]]
    if (
        len(ownership_prefixes) != len(set(ownership_prefixes))
        or set(ownership_prefixes) != EXPECTED_OWNERSHIP_PREFIXES
    ):
        raise TokenBudgetError("TOKEN-BUDGET-POLICY-UNKNOWN: ownership prefix set differs")
    _validated_exceptions(policy)
    return policy


def _owner_for(path: str, policy: dict) -> str:
    rows = sorted(policy["ownership"], key=lambda row: len(row["prefix"]), reverse=True)
    for row in rows:
        if path.startswith(row["prefix"]):
            return str(row["owner"])
    raise TokenBudgetError(f"TOKEN-BUDGET-OWNER-MISSING: no owner for {path}")


def _validated_exceptions(policy: dict) -> dict[str, dict]:
    now = datetime.now(timezone.utc)
    result: dict[str, dict] = {}
    for row in policy["exceptions"]:
        path = str(row.get("path", ""))
        owner = str(row.get("owner", "")).strip()
        if not owner:
            raise TokenBudgetError(f"TOKEN-BUDGET-EXCEPTION-OWNER-MISSING: {path}")
        if owner != _owner_for(path, policy):
            raise TokenBudgetError(f"TOKEN-BUDGET-EXCEPTION-OWNER-MISMATCH: {path}")
        try:
            expiry = datetime.fromisoformat(str(row["expires_at"]).replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError) as exc:
            raise TokenBudgetError(f"TOKEN-BUDGET-EXCEPTION-EXPIRED: invalid expiry for {path}") from exc
        if expiry.tzinfo is None or expiry <= now:
            raise TokenBudgetError(f"TOKEN-BUDGET-EXCEPTION-EXPIRED: {path}")
        if path in result:
            raise TokenBudgetError(f"TOKEN-BUDGET-POLICY-UNKNOWN: duplicate exception for {path}")
        result[path] = row
    return result


def _class_for_rel(path: str) -> FileClass | None:
    if path.startswith("references/_snippets/") and path.endswith(".md"):
        return FILE_CLASSES[3]
    if path.startswith("references/") and path.endswith(".md"):
        return FILE_CLASSES[1]
    if path.startswith("agents/") and path.endswith(".md"):
        return FILE_CLASSES[0]
    if path.startswith("skills/") and path.endswith("/SKILL.md"):
        return FILE_CLASSES[2]
    return None


def _git(*args: str) -> bytes:
    proc = subprocess.run(
        ["git", *args], cwd=HARNESS, capture_output=True, check=False
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()
        raise TokenBudgetError(f"TOKEN-BUDGET-BASELINE-UNAVAILABLE: {detail}")
    return proc.stdout


def _baseline_reports(policy: dict, encoder) -> tuple[dict[str, FileReport], int]:
    baseline = policy["baseline"]
    commit = str(baseline["commit"])
    tree = _git("rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    if tree != baseline["tree"]:
        raise TokenBudgetError("TOKEN-BUDGET-BASELINE-DRIFT: pinned commit tree differs")
    paths = _git("ls-tree", "-r", "--name-only", commit).decode(
        "utf-8", errors="strict"
    ).splitlines()
    reports: dict[str, FileReport] = {}
    for rel in paths:
        cls = _class_for_rel(rel)
        if cls is None:
            continue
        raw = _git("show", f"{commit}:{rel}")
        try:
            tokens = len(encoder.encode(raw.decode("utf-8", errors="strict")))
        except UnicodeDecodeError as exc:
            raise TokenBudgetError(f"TOKEN-BUDGET-BASELINE-UNAVAILABLE: {rel}: {exc}") from exc
        reports[rel] = FileReport(
            path=rel, cls=cls.name, tokens=tokens,
            warn_threshold=cls.warn_tokens, fail_threshold=cls.fail_tokens,
            status=classify(tokens, cls.warn_tokens, cls.fail_tokens),
        )
    floor = sum(
        len(encoder.encode(
            _git("show", f"{commit}:{rel}").decode("utf-8", errors="strict")
        ))
        for rel in EXPECTED_LOAD_GRAPH
    )
    breaches = sum(row.status != "ok" for row in reports.values())
    if (
        len(reports) != baseline["total_files"]
        or breaches != baseline["breaches"]
        or floor != baseline["always_loaded_floor_tokens"]
    ):
        raise TokenBudgetError("TOKEN-BUDGET-BASELINE-DRIFT: pinned metrics do not reproduce")
    return reports, floor


def _ratchet_blockers(report: BudgetReport, policy: dict, encoder) -> list[dict]:
    baseline, baseline_floor = _baseline_reports(policy, encoder)
    exceptions = _validated_exceptions(policy)
    blockers: list[dict] = []
    for observed in report.files:
        _owner_for(observed.path, policy)
        prior = baseline.get(observed.path)
        code = None
        if observed.status != "ok" and (prior is None or prior.status == "ok"):
            code = "TOKEN-BUDGET-NEW-BREACH"
        elif prior is not None and prior.status != "ok" and observed.tokens > prior.tokens:
            code = "TOKEN-BUDGET-DEBT-GROWTH"
        if code:
            exception = exceptions.get(observed.path)
            if exception is None or observed.tokens > int(exception["max_tokens"]):
                blockers.append({
                    "code": code, "path": observed.path,
                    "owner": _owner_for(observed.path, policy),
                    "baseline_tokens": prior.tokens if prior else None,
                    "observed_tokens": observed.tokens,
                })
    if report.always_loaded_floor_tokens > baseline_floor:
        path = "__always_loaded_floor__"
        exception = exceptions.get(path)
        if exception is None or report.always_loaded_floor_tokens > int(exception["max_tokens"]):
            blockers.append({
                "code": "TOKEN-BUDGET-FLOOR-GROWTH", "path": path,
                "owner": _owner_for(path, policy),
                "baseline_tokens": baseline_floor,
                "observed_tokens": report.always_loaded_floor_tokens,
            })
    return blockers


def build_report() -> BudgetReport:
    policy = _load_policy()
    encoder = _get_encoder()
    report = BudgetReport()

    all_files: List[FileReport] = []
    for cls in FILE_CLASSES:
        per_class_ok = 0
        per_class_warn = 0
        per_class_fail = 0
        for p in cls.iter_paths():
            # The references class must skip the _snippets/ subtree.
            if cls.name.startswith("references") and _exclude_snippets_from_references(p):
                continue
            tokens = count_tokens(p, encoder)
            status = classify(tokens, cls.warn_tokens, cls.fail_tokens)
            fr = FileReport(
                path=p.relative_to(HARNESS).as_posix(),
                cls=cls.name,
                tokens=tokens,
                warn_threshold=cls.warn_tokens,
                fail_threshold=cls.fail_tokens,
                status=status,
            )
            all_files.append(fr)
            report.total_files += 1
            if status == "ok":
                per_class_ok += 1
            elif status == "warn":
                per_class_warn += 1
                report.breaches.append(fr)
            else:
                per_class_fail += 1
                report.breaches.append(fr)
        report.by_class[cls.name] = {
            "warn_threshold": cls.warn_tokens,
            "fail_threshold": cls.fail_tokens,
            "ok": per_class_ok,
            "warn": per_class_warn,
            "fail": per_class_fail,
            "total": per_class_ok + per_class_warn + per_class_fail,
        }

    report.top10_largest = sorted(
        all_files, key=lambda f: f.tokens, reverse=True
    )[:10]
    report.files = all_files

    floor_total = 0
    for rel in ALWAYS_LOADED_FILES:
        p = HARNESS / rel
        if p.is_file():
            floor_total += count_tokens(p, encoder)
    report.always_loaded_floor_tokens = floor_total
    report.policy = {
        "schema_version": policy["schema_version"],
        "owner": policy["owner"],
        "baseline_commit": policy["baseline"]["commit"],
        "encoder": policy["encoder"],
        "load_graph": policy["load_graph"],
    }
    report.ratchet_blockers = _ratchet_blockers(report, policy, encoder)

    return report


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def _emit(report: BudgetReport, *, verbose: bool) -> None:
    print("token_budget_check (debt ratchet, tiktoken 0.12.0/cl100k_base)")
    print(f"  total files measured: {report.total_files}")
    print(f"  always-loaded prelude floor: "
          f"{report.always_loaded_floor_tokens} tokens "
          f"(target: <= 8000 per v0.15.0 architecture)")
    print()
    print("Per-class summary:")
    for cls_name, summary in report.by_class.items():
        print(
            f"  {cls_name:30s}  ok={summary['ok']:>3}  "
            f"warn={summary['warn']:>3}  fail={summary['fail']:>3}  "
            f"(warn>{summary['warn_threshold']}, "
            f"fail>{summary['fail_threshold']} tokens)"
        )
    print()
    print(f"Threshold breaches ({len(report.breaches)} files):")
    if not report.breaches:
        print("  (none — every measured file is within its warn threshold)")
    else:
        # Sort breaches by severity then size descending
        order = {"fail": 0, "warn": 1}
        for fr in sorted(report.breaches,
                          key=lambda f: (order.get(f.status, 9), -f.tokens)):
            tag = "FAIL" if fr.status == "fail" else "WARN"
            print(
                f"  [{tag}] {fr.tokens:>5} tok ({fr.cls})  {fr.path}  "
                f"(warn>{fr.warn_threshold}, fail>{fr.fail_threshold})"
            )
    print()
    print("Top-10 largest files across the package "
          "(PR-4c target list):")
    for fr in report.top10_largest:
        tag = fr.status.upper() if fr.status != "ok" else "ok  "
        print(f"  [{tag}] {fr.tokens:>5} tok  {fr.path}")
    print()
    if report.ratchet_blockers:
        print(f"Ratchet blockers ({len(report.ratchet_blockers)}):")
        for finding in report.ratchet_blockers:
            print(f"  [BLOCKER] {finding['code']} {finding['path']} "
                  f"{finding['baseline_tokens']} -> {finding['observed_tokens']} "
                  f"owner={finding['owner']}")
    else:
        print("Ratchet: PASS (no new debt, debt growth, or always-loaded-floor growth)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: List[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=None,
                        help="Optional: write reviews/token_budget_report.json")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress per-file output (still writes --out)")
    args = parser.parse_args(argv)

    if args.out:
        from destination_capability import DestinationRefused, assert_writable
        try:
            assert_writable(args.out.resolve(), purpose="token-budget report output")
        except DestinationRefused as exc:
            print(f"[BLOCKER] {exc}", file=sys.stderr)
            return 4

    try:
        report = build_report()
    except TokenBudgetError as exc:
        print(f"[BLOCKER] {exc}", file=sys.stderr)
        return 2

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(
                {
                    "schema_version": report.schema_version,
                    "total_files": report.total_files,
                    "always_loaded_floor_tokens": report.always_loaded_floor_tokens,
                    "by_class": report.by_class,
                    "breaches": [asdict(f) for f in report.breaches],
                    "top10_largest": [asdict(f) for f in report.top10_largest],
                    "ratchet_blockers": report.ratchet_blockers,
                    "policy": report.policy,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    if not args.quiet:
        _emit(report, verbose=False)

    return 1 if report.ratchet_blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
