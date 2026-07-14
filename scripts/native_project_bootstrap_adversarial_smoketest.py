#!/usr/bin/env python3
"""Adversarial checks for transactional native-project bootstrap publication."""

from __future__ import annotations

import os
import io
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import native_project_bootstrap as bootstrap_module


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "native_project_bootstrap.py"
VALID_TIMESTAMP = "2026-07-13T20:00:00Z"


def _run(
    project: Path,
    *,
    timestamp: str = VALID_TIMESTAMP,
    project_name: str = "test-project",
    title: str = "Test Project",
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            str(BOOTSTRAP),
            "--project-root",
            str(project),
            "--project-name",
            project_name,
            "--title",
            title,
            "--intended-reader",
            "requirements engineering researchers",
            "--created-at",
            timestamp,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _assert_rejected(result: subprocess.CompletedProcess[str], project: Path) -> None:
    if result.returncode == 0:
        raise AssertionError(f"unsafe bootstrap unexpectedly succeeded: {result.stdout}")
    if "BOOTSTRAPPED" in result.stdout or "BOOTSTRAPPED" in result.stderr:
        raise AssertionError("bootstrap announced success before safe publication")
    if project.exists() and not any(project.iterdir()):
        raise AssertionError("failed bootstrap left an empty published target")


def _make_directory_link(link: Path, target: Path) -> str | None:
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            text=True,
            capture_output=True,
            check=False,
        )
        return None if result.returncode == 0 else result.stderr.strip() or result.stdout.strip()
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        return str(exc)
    return None


def _failed_validation(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["injected-validator"], 4, "MISCONFIGURED\n", "")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="native-bootstrap-adversarial-") as directory:
        root = Path(directory)

        existing = root / "existing-target"
        existing.mkdir()
        marker = existing / "marker.txt"
        marker.write_text("preserve\n", encoding="utf-8")
        result = _run(existing)
        _assert_rejected(result, existing)
        if marker.read_text(encoding="utf-8") != "preserve\n" or set(existing.iterdir()) != {marker}:
            raise AssertionError("existing target was modified")

        f9_target = root / "preexisting-f9"
        f9 = f9_target / "reviews" / ".harness" / "milestones" / "M1_packet.json"
        f9.parent.mkdir(parents=True)
        f9.write_text('{"fabricated": true}\n', encoding="utf-8")
        result = _run(f9_target)
        _assert_rejected(result, f9_target)
        if f9.read_text(encoding="utf-8") != '{"fabricated": true}\n':
            raise AssertionError("pre-existing F9 evidence was changed")

        policy_target = root / "preexisting-policy"
        policy = policy_target / "reviews" / ".harness" / "policies" / "reader_accessibility.resolved.json"
        policy.parent.mkdir(parents=True)
        policy.write_text('{"fabricated": true}\n', encoding="utf-8")
        result = _run(policy_target)
        _assert_rejected(result, policy_target)
        if policy.read_text(encoding="utf-8") != '{"fabricated": true}\n':
            raise AssertionError("pre-existing policy evidence was overwritten")

        invalid_date_target = root / "invalid-date"
        result = _run(invalid_date_target, timestamp="2026-02-31T20:00:00Z")
        _assert_rejected(result, invalid_date_target)
        if invalid_date_target.exists():
            raise AssertionError("invalid timestamp published a target")

        invalid_names = (
            "innocent\nregister_class: non-technical",
            "innocent\rproject_id: forged",
            "two words",
            "name:override",
            "name#comment",
            "name\x00control",
            "_leading-punctuation",
        )
        for index, project_name in enumerate(invalid_names):
            target = root / f"invalid-name-{index}"
            if "\x00" in project_name:
                try:
                    bootstrap_module.bootstrap(
                        target,
                        project_name,
                        "Test Project",
                        ["requirements engineering researchers"],
                        VALID_TIMESTAMP,
                    )
                except ValueError:
                    pass
                else:
                    raise AssertionError("embedded-NUL project identifier was accepted")
            else:
                result = _run(target, project_name=project_name)
                _assert_rejected(result, target)
            if target.exists():
                raise AssertionError(f"invalid project identifier published a target: {project_name!r}")

        invalid_titles = (
            "Innocent\nregister_class: non-technical",
            "Innocent\rproject_id: forged",
            "Title\x00control",
            "\t",
        )
        for index, title in enumerate(invalid_titles):
            target = root / f"invalid-title-{index}"
            if "\x00" in title:
                try:
                    bootstrap_module.bootstrap(
                        target,
                        "test-project",
                        title,
                        ["requirements engineering researchers"],
                        VALID_TIMESTAMP,
                    )
                except ValueError:
                    pass
                else:
                    raise AssertionError("embedded-NUL title was accepted")
            else:
                result = _run(target, title=title)
                _assert_rejected(result, target)
            if target.exists():
                raise AssertionError(f"invalid title published a target: {title!r}")

        rollback_target = root / "validator-failure"
        captured = io.StringIO()
        try:
            with redirect_stdout(captured):
                bootstrap_module.bootstrap(
                    rollback_target,
                    "test-project",
                    "Test Project",
                    ["requirements engineering researchers"],
                    VALID_TIMESTAMP,
                    validator_runner=_failed_validation,
                )
        except ValueError:
            pass
        else:
            raise AssertionError("injected canonical validation failure was ignored")
        if rollback_target.exists():
            raise AssertionError("validation failure published a target")
        if "BOOTSTRAPPED" in captured.getvalue():
            raise AssertionError("bootstrap announced success before canonical validation")
        leftovers = list(root.glob(f".{rollback_target.name}.bootstrap-*"))
        if leftovers:
            raise AssertionError(f"validation failure left staging paths: {leftovers}")

        outside = root / "outside"
        outside.mkdir()
        junction_target = root / "junction-target"
        junction_target.mkdir()
        link_error = _make_directory_link(junction_target / "manuscript", outside)
        if link_error is None:
            result = _run(junction_target)
            _assert_rejected(result, junction_target)
            if list(outside.iterdir()):
                raise AssertionError("bootstrap followed a manuscript junction outside the target")
        else:
            print(f"junction_case: SKIP ({link_error})")

        success = root / "fresh-target"
        result = _run(success)
        if result.returncode != 0 or result.stdout.count("BOOTSTRAPPED") != 1:
            raise AssertionError(f"fresh transactional bootstrap failed: {result.stdout}{result.stderr}")
        milestone_dir = success / "reviews" / ".harness" / "milestones"
        if not milestone_dir.is_dir() or list(milestone_dir.iterdir()):
            raise AssertionError("successful bootstrap fabricated an F9 packet")
        if list(root.glob(f".{success.name}.bootstrap-*")):
            raise AssertionError("successful bootstrap left a staging directory")
        directives = (success / "research_notes" / "directives.md").read_text(encoding="utf-8")
        if directives.count("project_id: test-project") != 1 or directives.count("register_class: technical") != 1:
            raise AssertionError("validated inputs did not produce exactly one canonical directive key each")

    print("native_project_bootstrap_adversarial_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
