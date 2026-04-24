#!/usr/bin/env python3
"""Build the tier-gated rule digest for the research-writing-harness plugin.

Phase A (v0.4.18) of the Incremental Tier Protocol introduces a bounded
exception to GROUNDING_PROTOCOL Rule 1: at tiers T1 and T2, an agent may
satisfy "Read Before Cite" for package rule-files by consulting a
package-versioned, release-verified digest rather than the source file.
This script produces that digest.

The digest is a property of the plugin release, not of any agent run.
It is generated once per plugin version at release time (or at development
time for forward testing), verified by ``verify_rule_digest.py``, and
consumed by agents operating at T1/T2 only.

Scope. The digest covers exactly the files enumerated in ``DIGEST_SOURCES``
below, in the order given. Extending scope requires an amendment to
``TIER_PROTOCOL.md §3`` and ``GROUNDING_PROTOCOL.md Rule 1, Tier-gated
digest exception``. This script does not extend scope silently.

Output. A single JSON file at ``<reviews_dir>/_rule_digest_<version>.json``.
The filename is version-bound so that agents can assert the digest matches
their running plugin. A stale digest is treated as absent; it is not a
Rule 1 satisfier.

Non-goals. This script does not interpret rules, rank them, or attempt to
summarize their meaning beyond extracting their declared one-line
statement. Semantic compression of rule content would reintroduce the
very hallucination surface the tier protocol is trying to eliminate.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Digest contract
# ---------------------------------------------------------------------------

#: Schema version for the digest JSON format. Bump on structural changes.
#: Consumers MUST verify schema_version before relying on a digest.
DIGEST_SCHEMA_VERSION = "1.0"

#: The enumerated set of rule-files covered by the digest. This list is the
#: authoritative scope of the Rule 1 tier-gated exception. Adding a file
#: here is a plugin-level decision, not a per-session one.
DIGEST_SOURCES: tuple[str, ...] = (
    "references/GROUNDING_PROTOCOL.md",
    "references/DETERMINISTIC_CHECKS.md",
    "references/SAFEGUARD_LAYER.md",
    "references/REVIEW_ORCHESTRATION.md",
    "references/TIER_PROTOCOL.md",
)

#: Heading patterns from which rule entries are extracted. Each matched
#: heading becomes one digest entry. The patterns are intentionally
#: conservative — headings that do not match are not guessed at.
#:
#: Pattern coverage across the enumerated sources:
#:   - GROUNDING_PROTOCOL.md: ``## Rule N — Title`` (Rule blocks).
#:   - SAFEGUARD_LAYER.md:    ``## Check N — Title`` (Check blocks).
#:   - DETERMINISTIC_CHECKS.md, REVIEW_ORCHESTRATION.md, TIER_PROTOCOL.md:
#:     ``## N. Title`` and ``## N<letter>. Title`` (numbered sections),
#:     plus ``### N.M Subtitle`` (numbered subsections in REVIEW_*).
#:   - TIER_PROTOCOL.md:      ``### Tx — Title`` (tier specs) and
#:                            ``## EG-N — Title`` (escalation gates, when
#:                            they appear as top-level headings).
_RULE_HEADING_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Rule blocks (GROUNDING_PROTOCOL).
    re.compile(r"^##\s+Rule\s+(?P<id>\d+[a-z]?)\s+[—\-–]\s+(?P<title>.+)$"),
    # Check blocks (SAFEGUARD_LAYER).
    re.compile(r"^##\s+Check\s+(?P<id>\d+[a-z]?)\s+[—\-–]\s+(?P<title>.+)$"),
    # Explicit §-prefixed sections (if any file adopts them).
    re.compile(r"^##\s+§(?P<id>[\d.]+)\s+(?P<title>.+)$"),
    # Escalation-gate headings (TIER_PROTOCOL, future).
    re.compile(r"^##\s+(?P<id>EG-\d+)\s+[—\-–]\s+(?P<title>.+)$"),
    # Tier headings at H3 (TIER_PROTOCOL §2.x).
    re.compile(r"^###\s+(?P<id>T[0-4]R?)\s+[—\-–]\s+(?P<title>.+)$"),
    # Numbered top-level sections.
    re.compile(r"^##\s+(?P<id>\d+[a-z]?)\.\s+(?P<title>.+)$"),
    # Numbered second-level sections (e.g. "### 3.1 By paper type").
    re.compile(r"^###\s+(?P<id>\d+\.\d+[a-z]?)\s+(?P<title>.+)$"),
)


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------


@dataclass
class RuleEntry:
    """One digested rule.

    ``id`` is the rule's stable identifier as written in the source heading
    (e.g. "1", "2", "EG-3", "T1", "§3.2"). ``heading`` is the full heading
    text. ``one_liner`` is the first **bolded** sentence beneath the
    heading, if one exists — that is the project's convention for the
    normative statement of a rule. If no bolded first sentence is found,
    ``one_liner`` is left empty rather than guessed at.
    """

    id: str
    heading: str
    one_liner: str = ""
    source_line: int = 0


@dataclass
class SourceDigest:
    """One digested source file."""

    file: str
    sha256: str
    byte_count: int
    line_count: int
    rules: list[RuleEntry] = field(default_factory=list)


@dataclass
class Digest:
    """The full digest payload written to disk."""

    schema_version: str
    plugin_version: str
    generated_at: str
    plugin_root: str
    sources: list[SourceDigest] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


_BOLD_FIRST_SENTENCE = re.compile(r"\*\*(?P<text>[^*]+?)\*\*")


def _extract_one_liner(body_lines: list[str]) -> str:
    """Return the first **bolded** sentence in ``body_lines``, or ``""``.

    The convention in this package is that every normative rule opens with
    a bolded one-sentence statement immediately under its heading.
    Deviations from that convention are preserved as empty one-liners
    rather than silently filled with a best guess.
    """
    for line in body_lines:
        line = line.strip()
        if not line:
            continue
        m = _BOLD_FIRST_SENTENCE.search(line)
        if m:
            return m.group("text").strip()
        # First non-empty, non-bolded line breaks the scan; the rule does
        # not follow the bolded-one-liner convention.
        return ""
    return ""


def _extract_rules(text: str) -> list[RuleEntry]:
    """Walk the file line by line, matching rule headings against the
    enumerated patterns. Between a matched heading and the next heading
    (of any level), collect the body lines used for one-liner extraction.
    """
    rules: list[RuleEntry] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        match = None
        for pattern in _RULE_HEADING_PATTERNS:
            match = pattern.match(line)
            if match:
                break
        if match is None:
            i += 1
            continue

        heading = line.strip()
        rule_id = match.group("id")
        body: list[str] = []
        j = i + 1
        while j < len(lines):
            if lines[j].startswith("## ") or lines[j].startswith("### "):
                break
            body.append(lines[j])
            j += 1

        rules.append(
            RuleEntry(
                id=rule_id,
                heading=heading,
                one_liner=_extract_one_liner(body),
                source_line=i + 1,
            )
        )
        i = j
    return rules


def _digest_source(plugin_root: Path, rel_path: str) -> SourceDigest:
    """Read one source file and produce its ``SourceDigest``.

    Raises ``FileNotFoundError`` if the file is missing — a missing source
    is a release blocker, not a soft condition.
    """
    abs_path = plugin_root / rel_path
    raw = abs_path.read_bytes()
    text = raw.decode("utf-8")
    return SourceDigest(
        file=rel_path,
        sha256=hashlib.sha256(raw).hexdigest(),
        byte_count=len(raw),
        line_count=text.count("\n") + (0 if text.endswith("\n") else 1),
        rules=_extract_rules(text),
    )


# ---------------------------------------------------------------------------
# Version discovery
# ---------------------------------------------------------------------------


def _read_plugin_version(plugin_root: Path) -> str:
    """Read the ``version`` field from ``.claude-plugin/plugin.json``.

    The digest filename and the ``plugin_version`` field in the payload
    are both bound to this value. Agents use this binding to confirm the
    digest matches the running plugin.
    """
    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = manifest.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError(
            f"plugin.json at {manifest_path} has no usable 'version' field"
        )
    return version


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="build_rule_digest",
        description=(
            "Build the tier-gated rule digest for the research-writing-harness "
            "plugin. Output is a version-bound JSON file at "
            "<reviews-dir>/_rule_digest_<version>.json."
        ),
    )
    parser.add_argument(
        "--plugin-root",
        required=True,
        type=Path,
        help="Path to the plugin root (contains .claude-plugin/ and references/).",
    )
    parser.add_argument(
        "--reviews-dir",
        required=True,
        type=Path,
        help="Directory where the digest will be written (typically <project>/reviews/).",
    )
    parser.add_argument(
        "--version",
        default=None,
        help=(
            "Explicit plugin version override. If omitted, the version is "
            "read from .claude-plugin/plugin.json. Use the override only for "
            "forward-testing a digest before bumping the manifest."
        ),
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Also print the digest JSON to stdout after writing.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(sys.argv[1:] if argv is None else argv))

    plugin_root: Path = args.plugin_root.resolve()
    reviews_dir: Path = args.reviews_dir.resolve()

    if not plugin_root.is_dir():
        print(f"error: plugin-root {plugin_root} is not a directory", file=sys.stderr)
        return 2
    if not reviews_dir.is_dir():
        # Fail fast rather than create silently. The reviews dir is a
        # project-level artifact; this script does not own its lifecycle.
        print(f"error: reviews-dir {reviews_dir} is not a directory", file=sys.stderr)
        return 2

    version = args.version or _read_plugin_version(plugin_root)

    sources: list[SourceDigest] = []
    for rel_path in DIGEST_SOURCES:
        sources.append(_digest_source(plugin_root, rel_path))

    digest = Digest(
        schema_version=DIGEST_SCHEMA_VERSION,
        plugin_version=version,
        generated_at=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        plugin_root=str(plugin_root),
        sources=sources,
    )

    out_path = reviews_dir / f"_rule_digest_{version}.json"
    payload = json.dumps(asdict(digest), indent=2, ensure_ascii=False)
    out_path.write_text(payload + "\n", encoding="utf-8")

    if args.stdout:
        print(payload)

    rule_count = sum(len(s.rules) for s in sources)
    print(
        f"wrote {out_path} — {len(sources)} sources, {rule_count} rules, "
        f"plugin v{version}, schema v{DIGEST_SCHEMA_VERSION}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
