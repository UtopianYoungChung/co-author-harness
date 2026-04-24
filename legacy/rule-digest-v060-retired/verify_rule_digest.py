#!/usr/bin/env python3
"""Verify the tier-gated rule digest against the plugin source files.

This script is the release gate for the digest. It is what makes the
digest a *property of the plugin* rather than a property of any agent's
run — and therefore what allows it to serve as a Rule 1 satisfier at
tiers T1 and T2 under ``GROUNDING_PROTOCOL.md Rule 1, Tier-gated digest
exception``.

Verification is narrow and strictly mechanical:

  1. The digest's ``schema_version`` matches the consumer's expected
     version.
  2. The digest's ``plugin_version`` matches ``.claude-plugin/plugin.json``.
  3. The set of files covered by the digest matches ``DIGEST_SOURCES``
     in ``build_rule_digest.py`` — no silent scope expansion or
     contraction.
  4. Every source file's current SHA-256, byte count, and line count
     match the values recorded in the digest.
  5. Every rule entry's ``source_line`` still points at a heading line
     in the source file.

A verifier failure is a release blocker. Agents consuming a digest that
has not passed verification are operating under the unamended Rule 1 —
they must read the source file, not the digest.

Non-goals. This script does not re-extract rules from scratch and diff
against the digest's ``rules`` array. The SHA-256 check guarantees byte
fidelity; re-extraction would be redundant and would mask extraction
bugs behind themselves.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Keep the expected schema in lockstep with ``build_rule_digest.py``.
EXPECTED_SCHEMA_VERSION = "1.0"

EXPECTED_SOURCES: tuple[str, ...] = (
    "references/GROUNDING_PROTOCOL.md",
    "references/DETERMINISTIC_CHECKS.md",
    "references/SAFEGUARD_LAYER.md",
    "references/REVIEW_ORCHESTRATION.md",
    "references/TIER_PROTOCOL.md",
)


@dataclass
class VerificationFinding:
    """One verification finding. ``severity`` is ``"blocker"`` for any
    mismatch that invalidates the digest as a Rule 1 satisfier, or
    ``"warning"`` for cosmetic issues (currently unused — all findings
    are blockers in v0.4.18)."""

    severity: str
    check: str
    detail: str


def _read_manifest_version(plugin_root: Path) -> str:
    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = manifest.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError(
            f"plugin.json at {manifest_path} has no usable 'version' field"
        )
    return version


def _sha256_of(path: Path) -> tuple[str, int, int]:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    line_count = text.count("\n") + (0 if text.endswith("\n") else 1)
    return hashlib.sha256(raw).hexdigest(), len(raw), line_count


def _verify(
    plugin_root: Path,
    digest: dict,
    expected_version: str | None,
) -> list[VerificationFinding]:
    findings: list[VerificationFinding] = []

    # 1. Schema version.
    schema = digest.get("schema_version")
    if schema != EXPECTED_SCHEMA_VERSION:
        findings.append(
            VerificationFinding(
                severity="blocker",
                check="schema_version",
                detail=(
                    f"digest schema_version={schema!r}, "
                    f"verifier expects {EXPECTED_SCHEMA_VERSION!r}"
                ),
            )
        )
        # A schema mismatch invalidates every subsequent structural
        # assumption; return immediately rather than cascade.
        return findings

    # 2. Plugin version.
    digest_version = digest.get("plugin_version")
    if expected_version is not None and digest_version != expected_version:
        findings.append(
            VerificationFinding(
                severity="blocker",
                check="plugin_version",
                detail=(
                    f"digest plugin_version={digest_version!r}, "
                    f"caller expected {expected_version!r}"
                ),
            )
        )
    manifest_version = _read_manifest_version(plugin_root)
    if digest_version != manifest_version:
        findings.append(
            VerificationFinding(
                severity="blocker",
                check="plugin_version_vs_manifest",
                detail=(
                    f"digest plugin_version={digest_version!r} != "
                    f"plugin.json version={manifest_version!r}"
                ),
            )
        )

    # 3. Source-file scope parity.
    digest_files = tuple(s["file"] for s in digest.get("sources", []))
    if digest_files != EXPECTED_SOURCES:
        findings.append(
            VerificationFinding(
                severity="blocker",
                check="source_scope",
                detail=(
                    f"digest covers {digest_files!r}, "
                    f"expected {EXPECTED_SOURCES!r}"
                ),
            )
        )
        # Scope drift means the rest of the per-file checks are not
        # meaningful under the expected contract; stop here.
        return findings

    # 4. Per-file fidelity.
    for src in digest["sources"]:
        rel = src["file"]
        abs_path = plugin_root / rel
        if not abs_path.is_file():
            findings.append(
                VerificationFinding(
                    severity="blocker",
                    check=f"source_missing:{rel}",
                    detail=f"{abs_path} does not exist",
                )
            )
            continue
        actual_sha, actual_bytes, actual_lines = _sha256_of(abs_path)
        if actual_sha != src["sha256"]:
            findings.append(
                VerificationFinding(
                    severity="blocker",
                    check=f"sha256:{rel}",
                    detail=(
                        f"digest sha256={src['sha256']}, "
                        f"actual sha256={actual_sha}"
                    ),
                )
            )
        if actual_bytes != src["byte_count"]:
            findings.append(
                VerificationFinding(
                    severity="blocker",
                    check=f"byte_count:{rel}",
                    detail=(
                        f"digest bytes={src['byte_count']}, "
                        f"actual bytes={actual_bytes}"
                    ),
                )
            )
        if actual_lines != src["line_count"]:
            findings.append(
                VerificationFinding(
                    severity="blocker",
                    check=f"line_count:{rel}",
                    detail=(
                        f"digest lines={src['line_count']}, "
                        f"actual lines={actual_lines}"
                    ),
                )
            )

        # 5. Rule source-line sanity. Hash equality already guarantees
        # the file is byte-identical; this check catches digest-build
        # bugs that slip heading offsets past the hasher (e.g. a
        # pre-hash rewrite that happened to be a no-op on bytes).
        raw_lines = abs_path.read_text(encoding="utf-8").splitlines()
        for rule in src.get("rules", []):
            line_no = rule.get("source_line", 0)
            if not (1 <= line_no <= len(raw_lines)):
                findings.append(
                    VerificationFinding(
                        severity="blocker",
                        check=f"source_line_range:{rel}:{rule['id']}",
                        detail=(
                            f"digest source_line={line_no}, "
                            f"file has {len(raw_lines)} lines"
                        ),
                    )
                )
                continue
            actual_line = raw_lines[line_no - 1]
            expected_heading = rule.get("heading", "")
            if actual_line.strip() != expected_heading.strip():
                findings.append(
                    VerificationFinding(
                        severity="blocker",
                        check=f"heading_drift:{rel}:{rule['id']}",
                        detail=(
                            f"line {line_no} is {actual_line!r}, "
                            f"digest heading is {expected_heading!r}"
                        ),
                    )
                )

    return findings


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="verify_rule_digest",
        description=(
            "Verify the tier-gated rule digest against the plugin source "
            "files. Exit 0 on clean, 1 on findings, 2 on usage/IO errors."
        ),
    )
    parser.add_argument(
        "--plugin-root",
        required=True,
        type=Path,
        help="Path to the plugin root.",
    )
    parser.add_argument(
        "--digest-path",
        required=True,
        type=Path,
        help="Path to the digest JSON to verify.",
    )
    parser.add_argument(
        "--expected-version",
        default=None,
        help=(
            "If given, the verifier additionally asserts the digest's "
            "plugin_version equals this string. Useful in CI when the "
            "release tag is known independently of plugin.json."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON findings instead of text.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(sys.argv[1:] if argv is None else argv))

    plugin_root: Path = args.plugin_root.resolve()
    digest_path: Path = args.digest_path.resolve()

    if not plugin_root.is_dir():
        print(f"error: plugin-root {plugin_root} is not a directory", file=sys.stderr)
        return 2
    if not digest_path.is_file():
        print(f"error: digest-path {digest_path} does not exist", file=sys.stderr)
        return 2

    digest = json.loads(digest_path.read_text(encoding="utf-8"))
    findings = _verify(plugin_root, digest, args.expected_version)

    if args.json:
        payload = {
            "digest_path": str(digest_path),
            "plugin_root": str(plugin_root),
            "findings": [f.__dict__ for f in findings],
            "clean": not findings,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        if not findings:
            print(f"OK — digest at {digest_path} verifies clean")
        else:
            print(
                f"FAIL — {len(findings)} finding(s) against {digest_path}",
                file=sys.stderr,
            )
            for f in findings:
                print(f"  [{f.severity}] {f.check}: {f.detail}", file=sys.stderr)

    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
