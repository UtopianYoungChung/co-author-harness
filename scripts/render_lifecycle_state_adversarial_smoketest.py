#!/usr/bin/env python3
"""Adversarial coverage for lifecycle rendering boundaries and publication safety."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from semantic_graph_fixture_support import semantic_graph_fixture_environment


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "native_project_bootstrap.py"
RENDERER = ROOT / "scripts" / "render_lifecycle_state.py"
FIXED_TIME = "2026-07-13T18:00:00Z"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "-S", str(script), *args],
        cwd=ROOT,
        text=True, encoding="utf-8", errors="replace",
        capture_output=True,
        check=False,
    )


def _bootstrap(parent: Path, name: str) -> Path:
    project = parent / name
    result = _run(
        BOOTSTRAP,
        "--project-root", str(project),
        "--project-name", name,
        "--title", "Lifecycle Test",
        "--intended-reader", "requirements engineering researchers",
        "--created-at", "2026-07-13T17:00:00Z",
    )
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return project


def _render(project: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return _run(RENDERER, "--project-root", str(project), "--generated-at", FIXED_TIME, *extra)


def _must_fail_without_change(project: Path, mutate: object, label: str) -> None:
    view = project / "reviews" / "lifecycle_state.md"
    sentinel = b"do not replace\n"
    view.write_bytes(sentinel)
    mutate()
    result = _render(project)
    if result.returncode != 4 or "MF-DERIVED" not in result.stdout + result.stderr:
        raise AssertionError(f"{label} was not a controlled MF-DERIVED failure: {result!r}")
    if view.read_bytes() != sentinel:
        raise AssertionError(f"{label} caused a partial/unsafe lifecycle publication")
    if list(view.parent.glob(".lifecycle_state.*.tmp")):
        raise AssertionError(f"{label} leaked a publication temporary file")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="lifecycle-adversarial-") as directory:
        parent = Path(directory)

        invalid_time = _bootstrap(parent, "invalid-time")
        view = invalid_time / "reviews" / "lifecycle_state.md"
        result = _run(
            RENDERER, "--project-root", str(invalid_time),
            "--generated-at", "2026-02-30T18:00:00Z",
        )
        if result.returncode != 2 or view.exists():
            raise AssertionError(f"invalid timestamp was accepted or wrote output: {result!r}")

        malformed = _bootstrap(parent, "malformed-json")
        source = malformed / "reviews" / "phase_state.json"
        _must_fail_without_change(malformed, lambda: source.write_bytes(b"\xff\xfe"), "non-UTF-8 ledger")

        invalid = _bootstrap(parent, "invalid-ledger")
        invalid_source = invalid / "reviews" / "phase_state.json"
        def break_authority() -> None:
            document = json.loads(invalid_source.read_text(encoding="utf-8"))
            document["milestone_framework"]["milestones"]["M1"]["status"] = "accepted"
            invalid_source.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        _must_fail_without_change(invalid, break_authority, "canonically invalid ledger")

        invalid_phase = _bootstrap(parent, "invalid-phase")
        phase_source = invalid_phase / "reviews" / "phase_state.json"
        def break_phase() -> None:
            document = json.loads(phase_source.read_text(encoding="utf-8"))
            document["sections"]["manuscript/main.md"]["current_phase"] = "Ph99"
            phase_source.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        _must_fail_without_change(invalid_phase, break_phase, "canonically invalid phase state")

        # Reuse the real accepted-chain fixture builder to prove the renderer reads
        # accepted/current packets only after the ledger validator binds them.
        sys.path.insert(0, str(ROOT / "scripts"))
        import milestone_framework_smoketest as mf  # type: ignore
        accepted = parent / "accepted-chain"
        accepted.mkdir()
        ledger = mf._materialize_native_project(accepted)
        phase_document = mf._phase_document(ledger)
        accepted_source = accepted / "reviews" / "phase_state.json"
        accepted_source.parent.mkdir(parents=True, exist_ok=True)
        accepted_source.write_text(json.dumps(phase_document, indent=2) + "\n", encoding="utf-8")
        before = accepted_source.read_bytes()
        accepted_result = _render(accepted)
        if accepted_result.returncode != 0:
            raise AssertionError(accepted_result.stdout + accepted_result.stderr)
        accepted_view = (accepted / "reviews" / "lifecycle_state.md").read_text(encoding="utf-8")
        if "| M1 | M2 | `reviews/.harness/milestones/M1_packet.json`" not in accepted_view:
            raise AssertionError("accepted/current F9 evidence was not rendered")
        if accepted_source.read_bytes() != before:
            raise AssertionError("renderer mutated the authoritative ledger")

        import render_lifecycle_state as renderer  # type: ignore
        raced_payload = renderer.render_bytes(accepted.resolve(), FIXED_TIME)
        raced_view = accepted / "reviews" / "lifecycle_state.md"
        raced_sentinel = b"preserve old lifecycle view\n"
        raced_view.write_bytes(raced_sentinel)
        packet = accepted / ledger["milestones"]["M1"]["handoff"]["packet_path"]
        packet.write_text("{}\n", encoding="utf-8")
        try:
            renderer._publish(accepted.resolve(), raced_payload)
        except renderer.RenderError:
            pass
        else:
            raise AssertionError("F9 mutation between render and publish was accepted")
        if raced_view.read_bytes() != raced_sentinel:
            raise AssertionError("F9 race replaced the prior lifecycle view")

        preserved = (accepted / "reviews" / "lifecycle_state.md").read_bytes()
        stale = _render(accepted)
        if stale.returncode != 4 or (accepted / "reviews" / "lifecycle_state.md").read_bytes() != preserved:
            raise AssertionError("stale F9 binding was published or not rejected")

        for case in (
            "forged_f9_project_identity",
            "forged_f9_from_milestone",
            "forged_f9_to_milestone",
            "legacy_handoffs_without_project_identity",
        ):
            forged = parent / case
            forged.mkdir()
            mf._write_real_case(case, forged)
            forged_view = forged / "reviews" / "lifecycle_state.md"
            forged_view.write_bytes(b"preserve forged-case sentinel\n")
            forged_result = _render(forged)
            if forged_result.returncode != 4 or "MF-DERIVED" not in forged_result.stdout + forged_result.stderr:
                raise AssertionError(f"renderer did not reject {case}: {forged_result!r}")
            if forged_view.read_bytes() != b"preserve forged-case sentinel\n":
                raise AssertionError(f"renderer published over {case}")

        # Symlink/reparse tests are conditional because Windows may deny creation.
        linked = _bootstrap(parent, "linked-source")
        real_source = linked / "reviews" / "phase_state.real.json"
        source_link = linked / "reviews" / "phase_state.json"
        source_link.rename(real_source)
        try:
            os.symlink(real_source, source_link)
        except OSError:
            real_source.rename(source_link)
        else:
            link_result = _render(linked)
            if link_result.returncode != 4 or "MF-DERIVED" not in link_result.stdout + link_result.stderr:
                raise AssertionError("symlinked authority was not rejected")

        target_linked = _bootstrap(parent, "linked-target")
        outside = parent / "outside.md"
        outside.write_bytes(b"outside sentinel\n")
        target = target_linked / "reviews" / "lifecycle_state.md"
        try:
            os.symlink(outside, target)
        except OSError:
            pass
        else:
            target_result = _render(target_linked)
            if target_result.returncode != 4 or outside.read_bytes() != b"outside sentinel\n":
                raise AssertionError("symlinked target was followed or overwritten")

    print("render_lifecycle_state_adversarial_smoketest: PASS")
    return 0


if __name__ == "__main__":
    with semantic_graph_fixture_environment():
        raise SystemExit(main())
