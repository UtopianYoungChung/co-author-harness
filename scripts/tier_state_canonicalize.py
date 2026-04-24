#!/usr/bin/env python3
# =============================================================================
# [v0.7.3-READ-ONLY] DEPRECATION NOTICE — v0.7.4 forwarding artefact.
#
# This script is retained under its tier-named filename during the v0.7.4
# minor for back-compatibility. The authoritative canonicalizer is renamed
# `phase_state_canonicalize.py` at v0.7.4 and operates against
# `reviews/phase_state.json` under the Lifecycle-Phase Ladder vocabulary.
# The canonicalization logic itself is unchanged across the rename; only the
# filename, the state-file default, and internal log strings flip to the
# phase vocabulary.
#
# Callers should migrate to `scripts/phase_state_canonicalize.py` before
# upgrading beyond v0.7.4. This tier-named file is **removed at v0.7.5 RC**.
# =============================================================================
"""tier_state_canonicalize.py — three-mode LaTeX canonicalizer for fingerprinting.

Implements the canonicalization contract from references/tier_state_schema.md §§4.1–4.3.
At v0.7.0 the canonicalization logic itself is unchanged from v0.6.0; the
tolerant mode continues to absorb mechanical LaTeX edits while accumulating
line-delta drift into `cumulative_drift_lines_since_approval`.

Consumed by:
  - agents/generator.md T3 drift reporting (Phase 3.5 Self-T1 Verdict retired
    at v0.7.0 — see TIER_PROTOCOL.md §11)
  - agents/evaluator.md local-scope re-read at T2 entry and intra-T3
    iterations (Confirmation Mode retired at v0.7.0 alongside the rest of
    the Generator Self-T1 surface)
  - scripts/migrate_v060_to_v070.py (fingerprint preserved verbatim on
    migration; canonicalization is not re-run)
  - Planner Phase 0 staleness check (fingerprint_staleness_budget, 24 h)

Modes (top-level `fingerprint_mode`):
  strict    whitespace-collapse + line-ending normalization only.
            Every other character difference flips the fingerprint.
  tolerant  (default) seven rules per §4.2. T3-loop exceedance of
            `tolerant_drift_threshold` at v0.7.0 emits
            W-T3-DRIFT-EXCEEDED-TOLERANT (warning, not fingerprint_reset) to
            preserve the T3 unbounded-loop contract.
  off       identity passthrough (hash is over the unchanged bytes;
            used only where LaTeX parsing is unreliable).

Public API:
    canonicalize(body: str, mode: str = "tolerant",
                 opaque_envs: list[str] | None = None) -> str
    fingerprint(body: str, mode: str = "tolerant",
                opaque_envs: list[str] | None = None) -> str

`fingerprint` returns the sha256 hex digest of the canonical form (UTF-8).

CLI:
    python tier_state_canonicalize.py --file manuscript/main.md [--mode tolerant]
                                       [--print-body] [--print-hash]
                                       [--opaque-env ENV]*

Exit codes: 0 = success, 1 = read error, 2 = bad mode.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys

# Six built-in verbatim environments per §4.2 rule 3. The user may extend via
# reviews/classification.md `fingerprint_opaque_envs:`; the Planner passes that
# list through as `opaque_envs` on each invocation.
BUILTIN_OPAQUE_ENVS = (
    "verbatim",
    "lstlisting",
    "minted",
    "Verbatim",
    "BVerbatim",
    "LVerbatim",
)

# Sentinels used to carve out spans that should not be touched by later passes.
_SENTINEL_PREFIX = "\x00CANON_SENTINEL_"
_SENTINEL_SUFFIX = "\x00"

# Unicode em-dash (U+2014) and en-dash (U+2013) per §4.2 rule 5.
EM_DASH = "\u2014"
EN_DASH = "\u2013"


class CanonicalizationError(Exception):
    """Raised when the canonicalizer cannot complete (e.g., unterminated
    verbatim environment). The Generator's Phase 3.5 verdict reports this as
    `drift: uncomputed (<reason>)` rather than estimating."""


# --------------------------------------------------------------- primitives


def _collapse_line_endings(body: str) -> str:
    """Normalize CRLF and lone CR to LF. Pre-pass for every mode."""
    return body.replace("\r\n", "\n").replace("\r", "\n")


def _strip_trailing_whitespace(body: str) -> str:
    """Strip trailing space/tab on each line; applied in strict and tolerant."""
    return "\n".join(line.rstrip(" \t") for line in body.split("\n"))


# --------------------------------------------------------------- tolerant rules

# Rule 1: percent escapes. Replace `\%` with a sentinel before comment-stripping
# so we don't treat escaped percents as comment starts.
_PERCENT_ESCAPE_RE = re.compile(r"\\%")

# Rule 7: comments. `%` starting through end-of-line. We apply this AFTER
# replacing `\%` sentinels.
_COMMENT_RE = re.compile(r"(?<!\\)%.*")


# Rule 2: inline math (single $...$) and display math (\[...\], $$...$$, \(...\)).
# Order matters — $$ ... $$ must be matched before $ ... $ to avoid splitting
# display spans into two inline spans.
_MATH_SPANS = [
    # display math
    re.compile(r"\$\$(?:\\.|[^\\])*?\$\$", re.DOTALL),
    re.compile(r"\\\[(?:\\.|[^\\])*?\\\]", re.DOTALL),
    # inline math
    re.compile(r"\\\((?:\\.|[^\\])*?\\\)", re.DOTALL),
    re.compile(r"(?<!\\)\$(?:\\.|[^$\\])*?(?<!\\)\$", re.DOTALL),
]


# Rule 6: labels and refs. Preserved verbatim.
_LABEL_REF_RE = re.compile(
    r"\\(?:label|ref|eqref|autoref|cref|pageref)\{[^}]*\}"
)


def _opaque_env_pattern(env_names: list[str]) -> re.Pattern[str]:
    """Build a combined pattern for \\begin{env} ... \\end{env} blocks."""
    escaped = [re.escape(name) for name in env_names]
    joined = "|".join(escaped)
    # Non-greedy body; DOTALL so multi-line environments match.
    return re.compile(
        r"\\begin\{(?P<env>" + joined + r")\}.*?\\end\{(?P=env)\}",
        re.DOTALL,
    )


def _carve_spans(
    body: str,
    patterns: list[re.Pattern[str]],
    tag: str,
) -> tuple[str, list[str]]:
    """Replace matches of each pattern with a stable tagged sentinel; return the
    stripped body plus the list of carved-out spans in match order. Each
    carve-category supplies its own tag so uncarve can demultiplex without
    cross-category collisions."""
    spans: list[str] = []

    def _sub(match: re.Match[str]) -> str:
        spans.append(match.group(0))
        return f"{_SENTINEL_PREFIX}{tag}_{len(spans) - 1}{_SENTINEL_SUFFIX}"

    for pat in patterns:
        body = pat.sub(_sub, body)
    return body, spans


def _uncarve_spans(body: str, spans: list[str], tag: str) -> str:
    """Reinsert carved spans at their tagged sentinel positions."""

    def _sub(match: re.Match[str]) -> str:
        idx = int(match.group(1))
        return spans[idx]

    return re.sub(
        re.escape(_SENTINEL_PREFIX) + re.escape(tag) + r"_(\d+)" + re.escape(_SENTINEL_SUFFIX),
        _sub,
        body,
    )


def _normalize_dashes(body: str) -> str:
    """Rule 5: `---` → U+2014, `--` → U+2013. Applied after comment stripping
    so that authored Unicode dashes inside comments do not distort the body.
    Order matters: `---` before `--` to avoid partial match."""
    body = body.replace("---", EM_DASH)
    body = body.replace("--", EN_DASH)
    return body


def _collapse_whitespace(body: str) -> str:
    """Rule 4: collapse runs of whitespace to a single space (outside opaque
    spans, which have already been carved)."""
    return re.sub(r"[ \t\n]+", " ", body).strip()


# --------------------------------------------------------------- top-level API


def canonicalize(
    body: str,
    mode: str = "tolerant",
    opaque_envs: list[str] | None = None,
) -> str:
    """Return the canonical form of the body under the given mode.

    Raises CanonicalizationError on unparsable input (e.g. an unterminated
    verbatim environment under tolerant mode)."""
    if mode not in ("strict", "tolerant", "off"):
        raise ValueError(f"unknown fingerprint mode: {mode!r}")

    if mode == "off":
        return body

    # All modes: line-ending normalization.
    body = _collapse_line_endings(body)

    if mode == "strict":
        # Strict mode: trailing-whitespace strip + line-ending normalization.
        # No LaTeX rules apply. Every other character difference is drift.
        return _strip_trailing_whitespace(body)

    # Tolerant mode: apply the seven rules in order.
    #
    # Step A: carve out opaque spans that must pass through byte-for-byte.
    # Order: verbatim environments first (largest span), then math, then
    # \label/\ref (smallest atoms). This ordering avoids a \label inside a
    # verbatim being double-carved.

    envs = list(BUILTIN_OPAQUE_ENVS)
    if opaque_envs:
        envs.extend(opaque_envs)

    try:
        env_pattern = _opaque_env_pattern(envs)
    except re.error as exc:
        raise CanonicalizationError(f"opaque env pattern compile failed: {exc}") from exc

    # Carve verbatim-family environments first.
    body, carved_envs = _carve_spans(body, [env_pattern], "ENV")

    # Sanity check: no dangling `\begin{env}` without `\end{env}` for our
    # recognised envs. A dangling begin means an unterminated verbatim, which
    # would cause silent drift — we refuse to canonicalize.
    for env in envs:
        if re.search(r"\\begin\{" + re.escape(env) + r"\}", body):
            raise CanonicalizationError(
                f"unterminated \\begin{{{env}}}: opaque environment does not close"
            )

    # Rule 1: percent-escape sentinel. Replace \% with a fixed token that will
    # be restored after comment stripping.
    escape_token = f"{_SENTINEL_PREFIX}PCT{_SENTINEL_SUFFIX}"
    body = _PERCENT_ESCAPE_RE.sub(escape_token, body)

    # Rule 7: strip comments (from unescaped `%` to end-of-line).
    body = _COMMENT_RE.sub("", body)

    # Restore percent escapes. They re-enter the body as `\%` literal.
    body = body.replace(escape_token, r"\%")

    # Carve math spans and label/ref atoms now (after comment strip so commented
    # math does not preserve).
    body, carved_math = _carve_spans(body, _MATH_SPANS, "MATH")
    body, carved_refs = _carve_spans(body, [_LABEL_REF_RE], "REF")

    # Rule 5: normalize dashes.
    body = _normalize_dashes(body)

    # Rule 4: collapse whitespace.
    body = _collapse_whitespace(body)

    # Reinsert carved spans in reverse carve-order (refs last carved, uncarve
    # first; envs were carved first, uncarve last). The tagged sentinels let
    # each pass ignore sentinels of other categories.
    body = _uncarve_spans(body, carved_refs, "REF")
    body = _uncarve_spans(body, carved_math, "MATH")
    body = _uncarve_spans(body, carved_envs, "ENV")

    return body


def fingerprint(
    body: str,
    mode: str = "tolerant",
    opaque_envs: list[str] | None = None,
) -> str:
    """Return the sha256 hex digest of the canonical form."""
    canonical = canonicalize(body, mode=mode, opaque_envs=opaque_envs)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --------------------------------------------------------------- CLI


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--file", required=True, help="Path to the body file (e.g. manuscript/main.md)")
    ap.add_argument(
        "--mode",
        choices=("strict", "tolerant", "off"),
        default="tolerant",
        help="Canonicalization mode (default: tolerant)",
    )
    ap.add_argument(
        "--opaque-env",
        action="append",
        default=[],
        help="Extra opaque environment (repeatable)",
    )
    ap.add_argument("--print-body", action="store_true", help="Print canonical body to stdout")
    ap.add_argument("--print-hash", action="store_true", help="Print sha256 hex digest")
    args = ap.parse_args()

    try:
        with open(args.file, "r", encoding="utf-8") as fh:
            body = fh.read()
    except OSError as exc:
        print(f"tier_state_canonicalize: cannot read {args.file}: {exc}", file=sys.stderr)
        return 1

    try:
        canonical = canonicalize(body, mode=args.mode, opaque_envs=args.opaque_env)
    except CanonicalizationError as exc:
        print(f"tier_state_canonicalize: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"tier_state_canonicalize: {exc}", file=sys.stderr)
        return 2

    # Default: print hash unless overridden.
    if not args.print_body and not args.print_hash:
        args.print_hash = True

    if args.print_body:
        sys.stdout.write(canonical)
        if not canonical.endswith("\n"):
            sys.stdout.write("\n")

    if args.print_hash:
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        print(digest)

    return 0


if __name__ == "__main__":
    sys.exit(main())
