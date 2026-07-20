#!/usr/bin/env python3
"""Resolve consumer-relative runtime snippet paths inside a plugin root."""

from __future__ import annotations

from pathlib import Path


RUNTIME_SNIPPET_BINDINGS = {
    "references/_snippets/output-profile.md": {
        "skills/run-iterate/SKILL.md": "../../references/_snippets/output-profile.md",
        "skills/run-phase-1/SKILL.md": "../../references/_snippets/output-profile.md",
        "skills/run-phase-2/SKILL.md": "../../references/_snippets/output-profile.md",
        "skills/run-phase-3/SKILL.md": "../../references/_snippets/output-profile.md",
    },
    "references/_snippets/reflection-grounding.md": {
        "agents/reflector-closeout.md": "../references/_snippets/reflection-grounding.md",
        "agents/reflector-probe.md": "../references/_snippets/reflection-grounding.md",
    },
}


def resolve_runtime_binding(root: Path, consumer_rel: str, binding_rel: str) -> Path:
    root = root.resolve()
    consumer = (root / consumer_rel).resolve()
    if not consumer.is_file() or root not in consumer.parents:
        raise ValueError(f"runtime-binding consumer is missing or outside root: {consumer_rel}")
    target = (consumer.parent / binding_rel).resolve()
    if root not in target.parents or not target.is_file():
        raise ValueError(
            f"runtime binding {binding_rel!r} from {consumer_rel} is missing or escapes root"
        )
    return target


def read_with_runtime_bindings(root: Path, consumer_rel: str) -> str:
    """Read a consumer plus every snippet its declared runtime contract binds."""
    consumer = (root / consumer_rel).resolve()
    text = consumer.read_text(encoding="utf-8")
    bound = [text]
    for consumers in RUNTIME_SNIPPET_BINDINGS.values():
        binding_rel = consumers.get(consumer_rel)
        if binding_rel is None:
            continue
        if binding_rel not in text or "relative to this" not in text:
            raise ValueError(
                f"{consumer_rel}: missing explicit consumer-relative binding {binding_rel}"
            )
        target = resolve_runtime_binding(root, consumer_rel, binding_rel)
        bound.append(target.read_text(encoding="utf-8"))
    return "\n".join(bound)
