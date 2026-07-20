#!/usr/bin/env python3
"""Smoketest for the v0.15.0-pre PR-3b.1 stage/profile migration.

Signoff criteria (from review):
    (1) Existing fixtures with only current_phase still validate.
    (2) Migrated fixtures contain both old and new fields.
    (3) Migration is idempotent.
    (4) No command/skill routing changes yet (out of scope here).
    (5) release-gate.sh keeps passing with old-schema projects.

This test exercises (1), (2), (3), and adds two negative cases that pin
down validator behaviour: a bad `stage` value is BLOCKER; a bad `profile`
value is BLOCKER.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from migrate_v0150pre_add_stage_profile import migrate_doc, derive  # noqa: E402
from phase_state_validate import _validate_doc, Severity, Finding  # noqa: E402

CANONICAL_FIXTURE = HERE / "fixtures" / "phase_state_smoketest" / "pass" / "reviews" / "phase_state.json"


def _validate(doc: dict) -> list[Finding]:
    findings: list[Finding] = []
    _validate_doc(doc, findings)
    return findings


def _blockers(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity == Severity.BLOCKER]


def test_pre_migration_fixture_still_validates() -> None:
    doc = json.loads(CANONICAL_FIXTURE.read_text(encoding="utf-8"))
    blockers = _blockers(_validate(doc))
    assert not blockers, f"pre-migration fixture should validate, got: {blockers}"


def test_migration_adds_both_fields() -> None:
    doc = json.loads(CANONICAL_FIXTURE.read_text(encoding="utf-8"))
    migrated, updated, skipped = migrate_doc(doc)
    assert updated == 1, f"expected 1 section updated, got {updated}"
    assert skipped == 0
    for _name, section in migrated["sections"].items():
        assert "stage" in section, f"stage missing after migration: {section}"
        assert "profile" in section
        # Canonical fixture sits at current_phase=Ph2 → iterate/refine
        assert section["stage"] == "iterate"
        assert section["profile"] == "refine"
        # current_phase must be untouched
        assert section["current_phase"] == "Ph2"


def test_migration_is_idempotent() -> None:
    doc = json.loads(CANONICAL_FIXTURE.read_text(encoding="utf-8"))
    migrate_doc(doc)
    after_once = copy.deepcopy(doc)
    _, updated_again, skipped_again = migrate_doc(doc)
    assert updated_again == 0, f"second pass should update 0, got {updated_again}"
    assert skipped_again == 1
    assert doc == after_once, "doc mutated on idempotent re-run"


def test_migration_repairs_partial_shadow_fields() -> None:
    doc = json.loads(CANONICAL_FIXTURE.read_text(encoding="utf-8"))
    for _, section in doc["sections"].items():
        section["stage"] = "iterate"
        section.pop("profile", None)
    _, updated, skipped = migrate_doc(doc)
    assert updated == 1, f"partial shadow fields should be repaired, got updated={updated}"
    assert skipped == 0
    for _, section in doc["sections"].items():
        assert section["stage"] == "iterate"
        assert section["profile"] == "refine"


def test_migrated_doc_still_validates() -> None:
    doc = json.loads(CANONICAL_FIXTURE.read_text(encoding="utf-8"))
    migrate_doc(doc)
    blockers = _blockers(_validate(doc))
    assert not blockers, f"migrated doc must validate, got blockers: {blockers}"


def test_derivation_covers_all_phases() -> None:
    cases = {
        "Ph1": ("draft", None),
        "Ph2": ("iterate", "refine"),
        "Ph3": ("iterate", "refine"),
        "Ph3_converged": ("iterate", "refine"),
        "Ph4": ("finalize", None),
    }
    for phase, expected in cases.items():
        got = derive({"current_phase": phase})
        assert got == expected, f"{phase}: expected {expected}, got {got}"


def test_ph3_with_check_profile_override() -> None:
    section = {"current_phase": "Ph3", "check_profile": "deep"}
    assert derive(section) == ("iterate", "deep")
    section_bad = {"current_phase": "Ph3", "check_profile": "garbage"}
    assert derive(section_bad) == ("iterate", "refine")


def test_unknown_phase_is_left_alone() -> None:
    section = {"current_phase": "Ph99"}
    assert derive(section) == (None, None)
    doc = {"sections": {"x": {"current_phase": "Ph99", "phase_entry_log": []}}}
    migrate_doc(doc)
    assert "stage" not in doc["sections"]["x"]


def test_bad_stage_is_blocker() -> None:
    doc = json.loads(CANONICAL_FIXTURE.read_text(encoding="utf-8"))
    for _, section in doc["sections"].items():
        section["stage"] = "garbage"
    blockers = _blockers(_validate(doc))
    codes = [b.code for b in blockers]
    assert "SECTION_BAD_STAGE" in codes, f"expected SECTION_BAD_STAGE, got {codes}"


def test_bad_profile_is_blocker() -> None:
    doc = json.loads(CANONICAL_FIXTURE.read_text(encoding="utf-8"))
    for _, section in doc["sections"].items():
        section["stage"] = "iterate"
        section["profile"] = "garbage"
    blockers = _blockers(_validate(doc))
    codes = [b.code for b in blockers]
    assert "SECTION_BAD_PROFILE" in codes, f"expected SECTION_BAD_PROFILE, got {codes}"


def test_dry_run_does_not_mutate_disk() -> None:
    """End-to-end: invoke the migration CLI in --dry-run mode on a temp copy
    of the canonical fixture and confirm the on-disk file is unchanged."""
    import subprocess
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "phase_state.json"
        target.write_text(CANONICAL_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        before = target.read_bytes()
        result = subprocess.run(
            [sys.executable, str(HERE / "migrate_v0150pre_add_stage_profile.py"),
             "--path", str(target), "--dry-run"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0, result.stderr
        after = target.read_bytes()
        assert before == after, "--dry-run mutated the file"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tests = [
        test_pre_migration_fixture_still_validates,
        test_migration_adds_both_fields,
        test_migration_is_idempotent,
        test_migration_repairs_partial_shadow_fields,
        test_migrated_doc_still_validates,
        test_derivation_covers_all_phases,
        test_ph3_with_check_profile_override,
        test_unknown_phase_is_left_alone,
        test_bad_stage_is_blocker,
        test_bad_profile_is_blocker,
        test_dry_run_does_not_mutate_disk,
    ]
    failures = []
    for t in tests:
        try:
            t()
            print(f"  OK  {t.__name__}")
        except AssertionError as exc:
            failures.append(f"{t.__name__}: {exc}")
            print(f"  FAIL {t.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(f"[BLOCKER] {len(failures)} test(s) failed", file=sys.stderr)
        return 1
    print(f"OK migrate_v0150pre_stage_profile_smoketest — {len(tests)}/{len(tests)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
