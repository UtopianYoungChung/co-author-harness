#!/usr/bin/env python3
"""phase_notifications_loader.py — render Planner/Reflector notification messages (v0.7.4).

Renamed from `tier_notifications_loader.py` as part of the v0.7.4 Tier → Phase
terminology rename. Reads `references/phase_notifications.yaml` and renders
one of several message classes: a phase-transition announcement, an
escalation-gate firing notice, a Ph3 loop signal, a Ph1/Ph2 signoff notice,
a response-letter (T4R sibling-ladder) notice, an integrity warning, a
Manuscript Convergence Report notice, a fallback message, or a Ph3
stability-sub-mode signal.
Milestone gate outcomes are selected through the ``milestone_gate`` class;
their ``notification_id`` values are notifications, not lifecycle triggers.

Renders inline placeholders of the form ``{{key}}`` from a dict of context
values; unfilled placeholders are rendered as the literal text in braces so
they surface as test-visible regressions rather than silent elisions.

Dual-read contract (v0.7.4 minor only)
--------------------------------------
The loader prefers `references/phase_notifications.yaml`. If that file is
missing, it falls back to the legacy `references/tier_notifications.yaml`
while emitting a `W-DUAL-READ-LEGACY` DEPRECATION_WARNING on stderr. Both
resolutions succeed at v0.7.4; **the legacy fallback is removed at v0.7.5 RC**.

Usage (invoked by the Planner or by a developer testing a rendering):

    python scripts/phase_notifications_loader.py \\
        --class phase_transitions --key ph3_iteration_round_manuscript \\
        --context '{"date": "2026-04-21"}'

    python scripts/phase_notifications_loader.py \\
        --class escalation_gates --key eg1_ph4_downgrade_to_ph3 \\
        --context '{"trigger_detail": "grounding violation in §4.2",
                    "prev_phase": "Ph4"}'

Exit codes:
    0 — rendered successfully
    2 — requested class/key pair not present in the config
    3 — config file missing or unreadable
    4 — config parity mismatch with PHASE_PROTOCOL.md (soft — still renders)

The loader intentionally does not mutate any file. Writing the rendered string
to `reviews/escalation_log.md` or to stdout for the agent to consume is the
caller's responsibility — keeping the loader pure makes it trivially testable.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys


def _resolve_config_path(explicit_path: str | None) -> tuple[pathlib.Path, bool]:
    """Resolve the config path — honour explicit flag, else prefer phase-named file.

    Returns (resolved_path, is_legacy). When is_legacy is True, the caller
    is expected to surface a W-DUAL-READ-LEGACY DEPRECATION_WARNING.
    """
    if explicit_path:
        p = pathlib.Path(explicit_path)
        if not p.is_absolute():
            p = pathlib.Path.cwd() / p
        legacy = p.name == "tier_notifications.yaml"
        return p, legacy
    here = pathlib.Path(__file__).resolve().parent
    phase_path = here.parent / "references" / "phase_notifications.yaml"
    legacy_path = here.parent / "references" / "tier_notifications.yaml"
    if phase_path.exists():
        return phase_path, False
    if legacy_path.exists():
        return legacy_path, True
    return phase_path, False  # phase path wins in the error message


def _emit_dual_read_warning(path: pathlib.Path) -> None:
    """Emit the W-DUAL-READ-LEGACY deprecation warning on stderr."""
    sys.stderr.write(
        f"[phase_notifications_loader] W-DUAL-READ-LEGACY — fell back to legacy "
        f"{path.name} because phase_notifications.yaml is missing. The legacy "
        f"tier_notifications.yaml is parseable but unsupported at v0.11.0; the "
        f"v0.7.3->v0.7.4 migration helper was retired at v0.11.0 c5. Author a "
        f"fresh phase_notifications.yaml from the references/ template to resume "
        f"normal notification rendering.\n"
    )


def _load_yaml(path: pathlib.Path) -> dict:
    """Load YAML without requiring PyYAML if the config is simple enough.

    Falls back to a shallow parser for the documented schema (top-level maps
    with scalar or folded-scalar values) so the loader works in environments
    where PyYAML is not installed. If the config grows beyond this shape, the
    PyYAML path is used.
    """
    try:
        import yaml  # type: ignore

        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        return _shallow_yaml_parse(path.read_text(encoding="utf-8"))


def _shallow_yaml_parse(text: str) -> dict:
    """Minimal YAML reader for the documented two-level schema."""
    root: dict[str, object] = {}
    current_section: str | None = None
    current_key: str | None = None
    folded: list[str] = []

    def _commit_folded():
        nonlocal folded, current_section, current_key
        if current_key is None or current_section is None:
            folded = []
            return
        container = root.setdefault(current_section, {})
        assert isinstance(container, dict)
        existing = container.get(current_key)
        joined = " ".join(s.strip() for s in folded if s.strip())
        if isinstance(existing, dict):
            existing["long"] = joined if "long" not in existing else existing["long"]
        else:
            container[current_key] = joined
        folded = []

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if indent == 0 and stripped.endswith(":"):
            _commit_folded()
            current_section = stripped[:-1]
            current_key = None
            root.setdefault(current_section, {})
        elif indent == 0 and ":" in stripped:
            _commit_folded()
            k, _, v = stripped.partition(":")
            root[k.strip()] = v.strip().strip('"')
            current_section = None
            current_key = None
        elif indent == 2 and stripped.endswith(":") and current_section is not None:
            _commit_folded()
            current_key = stripped[:-1]
        elif indent >= 4 and current_key is not None:
            folded.append(stripped)
        elif indent == 2 and ":" in stripped and current_section is not None:
            _commit_folded()
            k, _, v = stripped.partition(":")
            container = root.setdefault(current_section, {})
            assert isinstance(container, dict)
            container[k.strip()] = v.strip().strip('"')
            current_key = None
    _commit_folded()
    return root


_PLACEHOLDER_RE = re.compile(r"\{\{?\s*([A-Za-z0-9_]+)\s*\}?\}")


def render(template: str, context: dict[str, object]) -> str:
    """Substitute {{key}} or {key} placeholders — leave unknown placeholders literal."""
    def _sub(m: re.Match) -> str:
        key = m.group(1)
        if key in context:
            return str(context[key])
        return m.group(0)
    return _PLACEHOLDER_RE.sub(_sub, template)


# The v0.7.4 phase_notifications.yaml exposes nine sections. The legacy
# v0.7.0 tier_notifications.yaml exposed three (dispatch / gates / calibration).
# The loader accepts both class-vocabularies so existing callers that used
# --class dispatch|gates|calibration continue to resolve (with a one-time
# rename note on stderr) during the v0.7.4 minor.
_LEGACY_CLASS_MAP = {
    "dispatch": "phase_transitions",
    "gates": "escalation_gates",
    "calibration": "integrity",
}

_ALLOWED_CLASSES = {
    "phase_transitions",
    "escalation_gates",
    "ph3_loop",
    "ph1_ph2_signoff",
    "response_letter",
    "integrity",
    "mcr",
    "fallbacks",
    "ph3_stability_sub_mode",
    "milestone_gate",
    # legacy aliases — v0.7.4 minor only
    "dispatch",
    "gates",
    "calibration",
}


def _select(config: dict, cls: str, key: str) -> str | None:
    section_name = _LEGACY_CLASS_MAP.get(cls, cls)
    section = config.get(section_name)
    if not isinstance(section, dict):
        return None
    entry = section.get(key)
    if isinstance(entry, str):
        return entry.strip()
    if isinstance(entry, dict):
        return entry.get("long", entry.get("short", entry.get("message", entry.get("user_template", "")))).strip()
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--class", dest="cls", required=True,
                    choices=sorted(_ALLOWED_CLASSES))
    ap.add_argument("--key", required=True,
                    help="phase/gate/loop key (see phase_notifications.yaml §1–§9)")
    ap.add_argument("--context", default="{}",
                    help="JSON object of placeholder substitutions")
    ap.add_argument("--config", default=None,
                    help="override config path (default: auto-resolve)")
    args = ap.parse_args()

    path, is_legacy = _resolve_config_path(args.config)
    if not path.exists():
        sys.stderr.write(f"[phase_notifications_loader] config not found: {path}\n")
        return 3
    if is_legacy:
        _emit_dual_read_warning(path)

    if args.cls in _LEGACY_CLASS_MAP:
        sys.stderr.write(
            f"[phase_notifications_loader] NOTE: --class {args.cls} is a v0.7.0 "
            f"alias for --class {_LEGACY_CLASS_MAP[args.cls]}; legacy aliases "
            f"are removed at v0.7.5 RC.\n"
        )

    try:
        config = _load_yaml(path)
    except Exception as exc:  # noqa: BLE001 — surface any parse failure
        sys.stderr.write(f"[phase_notifications_loader] could not parse config: {exc}\n")
        return 3

    template = _select(config, args.cls, args.key)
    if template is None:
        sys.stderr.write(f"[phase_notifications_loader] no entry for {args.cls}/{args.key}\n")
        return 2

    try:
        ctx = json.loads(args.context)
        if not isinstance(ctx, dict):
            raise ValueError("context must be a JSON object")
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"[phase_notifications_loader] bad --context: {exc}\n")
        return 3

    rendered = render(template, ctx)
    sys.stdout.write(rendered.rstrip() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
