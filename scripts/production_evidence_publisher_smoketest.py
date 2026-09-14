#!/usr/bin/env python3
"""Behavioral smoke test for the graph-independent production publisher rail."""

from __future__ import annotations

import copy
from contextlib import contextmanager
import os
import tempfile
import subprocess
import sys
import hashlib
import json
from pathlib import Path
from assignment_fixture_support import package_scratch

import draft_governance_publish as draft_publish
import scholarly_evaluation_publish as scholarly_publish
import assignment_dispatch_claim as dispatch
import evidence_publication
from destination_capability import DEST_PROTECTED, DestinationRefused
from assignment_milestone_transaction import record as record_transaction
from c2_evidence_fixture_support import build_activation_fixture
from assignment_milestone_checkpoint_smoketest import (
    checkpoint_input,
    write_valid_contract,
)
from milestone_framework_validate import validate_document
from reader_accessibility_policy import (
    reader_profile_phase_state_binding,
    resolve_reader_profile,
)
from scholarly_assurance_fixture_support import _profile, _span


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "native_project_bootstrap.py"
GATE = ROOT / "scripts" / "assignment_process_gate.py"
PREFLIGHT = ROOT / "scripts" / "assignment_dispatch_preflight.py"
WRITER = ROOT / "scripts" / "assignment_writer_commit.py"
FULL_RUN = ROOT / "scripts" / "full_run_contract_check.py"


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(value))


def _directory_link(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link, target_is_directory=True)
        return
    except OSError:
        if os.name != "nt":
            raise
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False, encoding="utf-8", errors="replace"
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"cannot create the junction attack fixture: {completed.stderr}"
        )


def _remove_directory_link(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
    elif path.exists():
        os.rmdir(path)


def _committed_consumptions(project: Path, claim_id: str) -> list[Path]:
    root = project / "reviews/.harness/assignment/dispatch/consumptions"
    matches: list[Path] = []
    for path in root.glob("*/consumption.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("claim_id") == claim_id and (
            path.parent / "commit_marker.json"
        ).is_file():
            matches.append(path)
    return matches


def _hermetic_governed_root(base: Path) -> Path:
    fake = base / "fake-ws"
    (fake / "research" / "60_Workbench").mkdir(parents=True)
    (fake / "outputs" / "co-author-harness" / "staging").mkdir(parents=True)
    (fake / "knowledge").mkdir(parents=True)
    manifest = fake / "governance" / "output-routing" / "output_routing.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("schema_version: 1\nroutes: []\n", encoding="utf-8")
    return fake


def _protected_refusal(exc: BaseException) -> bool:
    current: BaseException | None = exc
    while current is not None:
        if isinstance(current, DestinationRefused) and current.code == DEST_PROTECTED:
            return True
        if "DEST-PROTECTED" in str(current):
            return True
        current = current.__cause__
    return False


def _relative_entries(root: Path) -> set[Path]:
    return {p.relative_to(root) for p in root.rglob("*")}


def _run_protected_transaction_id_probe(*, action: str) -> None:
    """Refuse ../../../forbidden with no new files or directories.

    Codex WP2h probe (guards unmocked, hermetic Temp only): post-006
    publish_committed created forbidden/, forbidden/prepared, and
    reviews/.harness/evidence-transactions then raised DEST-PROTECTED.
    Pre-006 refused with new_paths=[]. Preserve that preflight: validate
    every intended control/output destination before mkdir/ensure_directory.
    """
    previous = os.environ.get("COAUTHOR_EXTRA_GOVERNED_ROOTS")
    with tempfile.TemporaryDirectory(
        prefix="research-assurance-wp2i-protected-"
    ) as raw:
        fake = _hermetic_governed_root(Path(raw))
        root = fake / "research" / "60_Workbench" / "probe"
        root.mkdir()
        out = root / "reviews" / ".harness" / "evidence" / "probe"
        out.mkdir(parents=True)
        os.environ["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = str(fake)
        try:
            before = _relative_entries(root)
            refused: BaseException | None = None
            try:
                if action == "publish":
                    evidence_publication.publish_committed(
                        project_root=root,
                        transaction_id="../../../forbidden",
                        preconditions=[],
                        inventory_preconditions=[],
                        outputs=[(out / "product.json", b"{}\n")],
                        marker=(out / "marker.json", b"{}\n"),
                    )
                elif action == "recover":
                    evidence_publication.recover_committed(
                        project_root=root,
                        transaction_id="../../../forbidden",
                        acknowledgement="inspected-evidence-state-and-journal",
                        preconditions=[],
                        inventory_preconditions=[],
                        outputs=[(out / "product.json", b"{}\n")],
                        marker=(out / "marker.json", b"{}\n"),
                        destination_validator=lambda _path: None,
                    )
                else:
                    raise AssertionError(f"unknown protected probe action: {action}")
            except BaseException as exc:
                refused = exc
            after = _relative_entries(root)
            new_paths = after - before
            assert refused is not None, (
                f"protected transaction_id {action} succeeded"
            )
            assert _protected_refusal(refused), refused
            assert new_paths == set(), (
                f"protected transaction_id {action} mutated the filesystem "
                f"including directories before DEST-PROTECTED refusal: "
                + str(sorted(str(p) for p in new_paths))
            )
            assert not (root / "forbidden").exists()
            assert not (root / "forbidden" / "prepared").exists()
            assert not (root / "forbidden" / "recovery").exists()
        finally:
            if previous is None:
                os.environ.pop("COAUTHOR_EXTRA_GOVERNED_ROOTS", None)
            else:
                os.environ["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = previous


def case_protected_transaction_id_publish_creates_no_directories() -> None:
    _run_protected_transaction_id_probe(action="publish")


def case_protected_transaction_id_recover_creates_no_directories() -> None:
    _run_protected_transaction_id_probe(action="recover")


def _attempt_directory_substitution(
    source: Path, saved: Path, outside: Path
) -> str:
    """Try to replace source with a link to outside. Return completed|prevented."""
    try:
        source.rename(saved)
    except OSError:
        return "prevented"
    try:
        _directory_link(source, outside)
    except BaseException:
        if saved.exists():
            saved.rename(source)
        raise
    return "completed"


def case_late_open_marker_parent_substitution_is_contained() -> None:
    """Late-open substitution at actual exclusive-create backends.

    NT exclusive marker creation uses Path.open('xb'). POSIX exclusive
    marker creation uses os.open(..., O_EXCL, dir_fd=parent) via
    _exclusive_create_posix, so a Path.open('xb')-only hook never runs on
    that backend. Hook both mutation points. Do not fake os.name and do
    not mock destination_capability guards. A prevented OS rename is a
    valid negative. Escape is a new file or directory outside the admitted
    root. attempted / prevented / completed are recorded separately.
    Handle-relative create may succeed in-root after a completed swap;
    path-based create after a completed swap must not write outside.
    """
    from unittest.mock import patch

    with tempfile.TemporaryDirectory(
        prefix="research-assurance-wp2i-late-open-"
    ) as raw:
        base = Path(raw).resolve()
        root = base / "project"
        root.mkdir()
        parent = root / "artifacts"
        parent.mkdir()
        saved = root / "artifacts-original"
        outside = base / "outside"
        outside.mkdir()
        marker = parent / "commit-marker.json"
        original_open = Path.open
        original_os_open = evidence_publication.os.open
        attempted: list[str] = []
        substitution = "not_attempted"

        def _try_substitute(backend: str) -> None:
            nonlocal substitution
            if attempted:
                return
            attempted.append(backend)
            assert parent.resolve().is_relative_to(base)
            assert outside.resolve().is_relative_to(base)
            substitution = _attempt_directory_substitution(parent, saved, outside)

        def injected_open(self: Path, mode: str = "r", *args: object, **kwargs: object):
            if self == marker and mode == "xb" and not attempted:
                _try_substitute("path.open.xb")
                if substitution == "prevented":
                    return original_open(self, mode, *args, **kwargs)
            return original_open(self, mode, *args, **kwargs)

        def injected_os_open(path: str | bytes | os.PathLike[str], flags: int = 0, *args: object, **kwargs: object):
            name = os.fspath(path)
            excl = bool(flags & getattr(os, "O_EXCL", 0))
            if (
                excl
                and os.path.basename(name) == marker.name
                and not attempted
            ):
                _try_substitute("os.open.excl")
                if substitution == "prevented":
                    return original_os_open(path, flags, *args, **kwargs)
            return original_os_open(path, flags, *args, **kwargs)

        publisher_returned: str
        try:
            with (
                patch.object(Path, "open", injected_open),
                patch.object(evidence_publication.os, "open", injected_os_open),
            ):
                try:
                    evidence_publication.publish_committed(
                        project_root=root,
                        transaction_id="codex-final-open-probe",
                        preconditions=[],
                        inventory_preconditions=[],
                        outputs=[(parent / "product.json", b"{}\n")],
                        marker=(marker, b'{"committed":true}\n'),
                    )
                    publisher_returned = "success"
                except Exception as exc:
                    publisher_returned = f"{type(exc).__name__}: {exc}"
            outside_files = sorted(
                p.name for p in outside.iterdir() if p.is_file()
            )
            outside_dirs = sorted(
                p.name for p in outside.iterdir() if p.is_dir()
            )
            outside_marker = (
                (outside / "commit-marker.json").read_bytes()
                if (outside / "commit-marker.json").is_file()
                else None
            )
        finally:
            if substitution == "completed":
                _remove_directory_link(parent)
                if saved.exists():
                    saved.rename(parent)

        if outside_files or outside_dirs or outside_marker is not None:
            raise AssertionError(
                "late-open exclusive-create marker-parent substitution wrote "
                f"outside the admitted root: files={outside_files} "
                f"dirs={outside_dirs} marker={outside_marker!r} "
                f"publisher_returned={publisher_returned} "
                f"substitution={substitution} attempted={attempted} "
                f"os.name={os.name!r}"
            )
        if not attempted:
            raise AssertionError(
                "late-open exclusive-create probe did not run; reproducer is "
                f"incomplete publisher_returned={publisher_returned} "
                f"substitution={substitution} os.name={os.name!r}"
            )
        if publisher_returned == "success":
            assert (parent / "commit-marker.json").read_bytes() == b'{"committed":true}\n'
            assert (parent / "product.json").read_bytes() == b"{}\n"


def case_direct_publish_and_recover_roundtrip() -> None:
    """Normal permitted publish/validate/recover still succeed in-root."""
    with tempfile.TemporaryDirectory(
        prefix="research-assurance-wp2h-positive-"
    ) as raw:
        base = Path(raw).resolve()
        root = base / "project"
        root.mkdir()
        parent = root / "artifacts"
        parent.mkdir()
        product = parent / "product.json"
        marker = parent / "commit-marker.json"
        product_bytes = b"{}\n"
        marker_bytes = b'{"committed":true}\n'
        evidence_publication.publish_committed(
            project_root=root,
            transaction_id="wp2h-positive-roundtrip",
            preconditions=[],
            inventory_preconditions=[],
            outputs=[(product, product_bytes)],
            marker=(marker, marker_bytes),
        )
        assert product.read_bytes() == product_bytes
        assert marker.read_bytes() == marker_bytes
        evidence_publication.validate_committed(
            project_root=root,
            transaction_id="wp2h-positive-roundtrip",
            preconditions=[],
            inventory_preconditions=[],
            outputs=[(product, product_bytes)],
            marker=(marker, marker_bytes),
        )
        recovered = evidence_publication.recover_committed(
            project_root=root,
            transaction_id="wp2h-positive-roundtrip",
            acknowledgement="inspected-evidence-state-and-journal",
            preconditions=[],
            inventory_preconditions=[],
            outputs=[(product, product_bytes)],
            marker=(marker, marker_bytes),
            destination_validator=lambda _path: None,
        )
        assert recovered == "committed"
        assert product.read_bytes() == product_bytes
        assert marker.read_bytes() == marker_bytes


def case_admitted_root_rename_is_prevented_or_refused() -> None:
    """Root rename between validation and use must not write outside."""
    with tempfile.TemporaryDirectory(
        prefix="research-assurance-wp2h-root-sub-"
    ) as raw:
        base = Path(raw).resolve()
        holder = base / "holder"
        holder.mkdir()
        root = holder / "project"
        root.mkdir()
        parent = root / "artifacts"
        parent.mkdir()
        saved = holder / "project-original"
        outside = base / "outside"
        outside.mkdir()
        marker = parent / "commit-marker.json"
        substitution = "not_attempted"

        def inject_root_swap() -> None:
            nonlocal substitution
            substitution = _attempt_directory_substitution(root, saved, outside)

        try:
            try:
                evidence_publication.publish_committed(
                    project_root=root,
                    transaction_id="wp2h-root-substitution",
                    preconditions=[],
                    inventory_preconditions=[],
                    outputs=[(parent / "product.json", b"{}\n")],
                    marker=(marker, b'{"committed":true}\n'),
                    under_claim_validator=inject_root_swap,
                )
                publisher_returned = "success"
            except Exception as exc:
                publisher_returned = f"{type(exc).__name__}: {exc}"
            outside_files = sorted(
                p.name for p in outside.iterdir() if p.is_file()
            )
        finally:
            if substitution == "completed":
                _remove_directory_link(root)
                if saved.exists():
                    saved.rename(root)

        if substitution == "not_attempted":
            raise AssertionError(
                "admitted-root substitution did not trigger under claim "
                f"publisher_returned={publisher_returned}"
            )
        if outside_files:
            raise AssertionError(
                "admitted-root substitution wrote outside the admitted root: "
                f"{outside_files} substitution={substitution} "
                f"publisher_returned={publisher_returned}"
            )
        if substitution == "completed" and publisher_returned == "success":
            raise AssertionError(
                "admitted-root substitution completed and publisher returned success"
            )


def case_publishers_refuse_protected_and_escaping_destinations() -> None:
    with tempfile.TemporaryDirectory(prefix="publisher-dest-refuse-") as raw:
        fake = _hermetic_governed_root(Path(raw))
        project = fake / "research" / "protected-not-workbench" / "probe"
        project.mkdir(parents=True)
        artifact = project / "artifact.md"
        artifact.write_text("# probe\n", encoding="utf-8")
        claim = project / "claim.json"
        claim.write_text("{}\n", encoding="utf-8")
        previous = os.environ.get("COAUTHOR_EXTRA_GOVERNED_ROOTS")
        os.environ["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = str(fake)
        try:
            before = {p.relative_to(project) for p in project.rglob("*")}
            refused = None
            try:
                draft_publish.prepare_contract(
                    project_root=project,
                    artifact=artifact,
                    milestone="M1",
                    phase="generation",
                    role="generator",
                    evidence_label="dest-probe",
                )
            except (
                DestinationRefused,
                draft_publish.DraftGovernancePublicationError,
            ) as exc:
                refused = exc
            assert refused is not None, "draft publisher accepted a protected destination"
            assert _protected_refusal(refused), refused
            after = {p.relative_to(project) for p in project.rglob("*")}
            assert after == before, (
                "draft publisher wrote partial output on a protected destination: "
                + str(sorted(str(p) for p in (after - before))[:8])
            )

            before = {p.relative_to(project) for p in project.rglob("*")}
            refused = None
            try:
                scholarly_publish.publish_evaluation(
                    project_root=project,
                    artifact=artifact,
                    evaluation_claim=claim,
                    evaluation_id="SET-DEST-PROBE",
                    milestone="M1",
                    criteria=["c1"],
                    scholarly_profile={},
                    claim_register={},
                    judgment={},
                    created_at="2026-09-05T00:00:00Z",
                )
            except (
                DestinationRefused,
                scholarly_publish.ScholarlyPublicationError,
            ) as exc:
                refused = exc
            assert refused is not None, (
                "scholarly publisher accepted a protected destination"
            )
            assert _protected_refusal(refused), refused
            after = {p.relative_to(project) for p in project.rglob("*")}
            assert after == before, (
                "scholarly publisher wrote partial output on a protected destination: "
                + str(sorted(str(p) for p in (after - before))[:8])
            )

            for invalid in ("", "../escape", "bad\\name", "bad/name", "bad:name"):
                try:
                    draft_publish.publication_lane(
                        project,
                        milestone="M1",
                        phase="generation",
                        evidence_label=invalid,
                    )
                except draft_publish.DraftGovernancePublicationError:
                    pass
                else:
                    raise AssertionError(
                        f"unsafe evidence label was accepted: {invalid!r}"
                    )
        finally:
            if previous is None:
                os.environ.pop("COAUTHOR_EXTRA_GOVERNED_ROOTS", None)
            else:
                os.environ["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = previous


def case_committed_dependencies_are_replayed() -> None:
    with tempfile.TemporaryDirectory(prefix="publication-dependency-replay-") as raw:
        root = Path(raw).resolve()
        source = root / "input.txt"
        source.write_bytes(b"before\n")
        inventory = root / "inventory"
        inventory.mkdir()
        member = inventory / "one.md"
        member.write_bytes(b"one\n")
        product, marker = root / "product.json", root / "marker.json"
        kwargs = dict(
            project_root=root, transaction_id="dependency-replay",
            preconditions=[(source, hashlib.sha256(source.read_bytes()).hexdigest())],
            inventory_preconditions=[(inventory, {"one.md": hashlib.sha256(member.read_bytes()).hexdigest()})],
            outputs=[(product, b"{}\n")], marker=(marker, b"{}\n"),
        )
        evidence_publication.publish_committed(**kwargs)
        evidence_publication.validate_committed(**kwargs)
        try:
            evidence_publication.validate_recorded_committed(
                project_root=root, transaction_id="dependency-replay",
                expected_products=[product], expected_marker=marker,
            )
        except evidence_publication.EvidencePublicationError:
            pass
        else:
            raise AssertionError("recorded replay invented the missing inventory map")
        assert evidence_publication.recover_committed(
            **kwargs, acknowledgement="inspected-evidence-state-and-journal",
            destination_validator=lambda _path: None,
        ) == "committed"
        lane = evidence_publication._transaction_lane(root, "dependency-replay")
        observed = [product, marker, lane / "claim.json", lane / "journal.json"]
        before = {path: path.read_bytes() for path in observed}
        for dependency in (source, member):
            original = dependency.read_bytes()
            dependency.write_bytes(b"x" * len(original))
            try:
                try:
                    evidence_publication.validate_committed(**kwargs)
                except evidence_publication.EvidencePublicationError as exc:
                    assert "changed" in str(exc), str(exc)
                else:
                    raise AssertionError(f"committed replay accepted changed dependency: {dependency.name}")
                assert {path: path.read_bytes() for path in observed} == before
            finally:
                dependency.write_bytes(original)
        evidence_publication.validate_committed(**kwargs)


def case_recovery_rechecks_after_both_claims() -> None:
    for drift in ("file", "inventory", "destination"):
        with tempfile.TemporaryDirectory(prefix="publication-recovery-recheck-") as raw:
            root = Path(raw).resolve()
            source = root / "input.txt"
            source.write_bytes(b"before\n")
            inventory = root / "inventory"
            inventory.mkdir()
            member = inventory / "one.md"
            member.write_bytes(b"one\n")
            product, marker = root / "product.json", root / "marker.json"
            kwargs = dict(
                project_root=root, transaction_id="recovery-recheck",
                preconditions=[(source, hashlib.sha256(source.read_bytes()).hexdigest())],
                inventory_preconditions=[(inventory, {"one.md": hashlib.sha256(member.read_bytes()).hexdigest()})],
                outputs=[(product, b"{}\n")], marker=(marker, b"{}\n"),
            )
            evidence_publication.publish_committed(**kwargs)
            lane = evidence_publication._transaction_lane(root, "recovery-recheck")
            observed = [product, marker, lane / "claim.json", lane / "journal.json"]
            before = {path: path.read_bytes() for path in observed}
            original_lock = evidence_publication._claim_lock
            acquired = 0
            mutated = False
            validations = []

            @contextmanager
            def mutate_after_claim(path, **lock_kwargs):
                nonlocal acquired, mutated
                with original_lock(path, **lock_kwargs):
                    acquired += 1
                    if acquired == 2:
                        if drift == "file":
                            source.write_bytes(b"change\n")
                        elif drift == "inventory":
                            member.write_bytes(b"two\n")
                        mutated = True
                    yield

            def validate_destination(path):
                validations.append(mutated)
                if drift == "destination" and mutated:
                    raise evidence_publication.EvidencePublicationError("destination changed under claims")

            evidence_publication._claim_lock = mutate_after_claim
            try:
                try:
                    evidence_publication.recover_committed(
                        **kwargs, acknowledgement="inspected-evidence-state-and-journal",
                        destination_validator=validate_destination,
                    )
                except evidence_publication.EvidencePublicationError as exc:
                    assert "changed" in str(exc), str(exc)
                else:
                    raise AssertionError(f"recovery accepted {drift} drift after precheck")
            finally:
                evidence_publication._claim_lock = original_lock
            assert acquired == 2 and mutated
            assert validations[:2] == [False, False], validations
            if drift == "destination":
                assert validations[-1] is True, validations
            assert {path: path.read_bytes() for path in observed} == before


def case_recorded_publication_replays_exact_intent() -> None:
    with tempfile.TemporaryDirectory(prefix="recorded-publication-replay-") as raw:
        root = Path(raw).resolve()
        dependency = root / "input.txt"
        dependency.write_bytes(b"before\n")
        product, marker = root / "product.json", root / "marker.json"
        evidence_publication.publish_committed(
            project_root=root, transaction_id="recorded-replay",
            preconditions=[(dependency, hashlib.sha256(dependency.read_bytes()).hexdigest())],
            inventory_preconditions=[], outputs=[(product, b"{}\n")],
            marker=(marker, b'{"committed":true}\n'),
        )
        kwargs = dict(
            project_root=root, transaction_id="recorded-replay",
            expected_products=[product], expected_marker=marker,
        )
        evidence_publication.validate_recorded_committed(**kwargs)
        lane = evidence_publication._transaction_lane(root, "recorded-replay")
        state_files = [lane / "claim.json", lane / "journal.json"]
        state = {path: path.read_bytes() for path in state_files}
        for target in (dependency, product):
            original = target.read_bytes()
            target.write_bytes(b"x" * len(original))
            try:
                try:
                    evidence_publication.validate_recorded_committed(**kwargs)
                except evidence_publication.EvidencePublicationError:
                    pass
                else:
                    raise AssertionError(f"recorded replay accepted stale {target.name}")
                assert {path: path.read_bytes() for path in state_files} == state
            finally:
                target.write_bytes(original)
        try:
            evidence_publication.validate_recorded_committed(
                **{**kwargs, "expected_marker": product},
            )
        except evidence_publication.EvidencePublicationError:
            pass
        else:
            raise AssertionError("recorded replay accepted another marker")
        evidence_publication.validate_recorded_committed(**kwargs)


def main() -> int:
    case_recorded_publication_replays_exact_intent()
    case_committed_dependencies_are_replayed()
    case_recovery_rechecks_after_both_claims()
    case_publishers_refuse_protected_and_escaping_destinations()
    case_protected_transaction_id_publish_creates_no_directories()
    case_protected_transaction_id_recover_creates_no_directories()
    case_late_open_marker_parent_substitution_is_contained()
    case_direct_publish_and_recover_roundtrip()
    case_admitted_root_rename_is_prevented_or_refused()
    with tempfile.TemporaryDirectory(
        prefix="production-evidence-publisher-", dir=package_scratch(ROOT)
    ) as raw:
        project = (Path(raw) / "project").resolve()

        generation_lane = draft_publish.publication_lane(
            project,
            milestone="M1",
            phase="generation",
            evidence_label="producer-smoke",
        )
        expected_generation = (
            project
            / "reviews/.harness/evidence/draft-governance/m1/"
            / "generation/producer-smoke"
        ).resolve()
        assert generation_lane == expected_generation
        assert generation_lane.is_relative_to(project)

        evaluation_path = scholarly_publish.evaluation_output_path(
            project,
            evaluation_id="SET-PRODUCER-SMOKE",
        )
        expected_evaluation = (
            project
            / "reviews/.harness/evidence/scholarly-evaluation/"
            / "SET-PRODUCER-SMOKE/evaluation.json"
        ).resolve()
        assert evaluation_path == expected_evaluation
        assert evaluation_path.is_relative_to(project)

        for invalid in ("", "../escape", "bad\\name", "bad/name", "bad:name"):
            try:
                scholarly_publish.evaluation_output_path(
                    project,
                    evaluation_id=invalid,
                )
            except scholarly_publish.ScholarlyPublicationError:
                pass
            else:
                raise AssertionError(
                    f"unsafe evaluation identity was accepted: {invalid!r}"
                )

        subprocess.run(
            [
                sys.executable,
                str(BOOTSTRAP),
                "--project-root",
                str(project),
                "--project-name",
                "production-evidence-publisher",
                "--title",
                "Production Evidence Publisher",
                "--intended-reader",
                "researcher",
                "--created-at",
                "2026-08-11T00:00:00Z",
                "--handoff-policy",
                "audited",
            ],
            check=True,
            text=True, encoding="utf-8", errors="replace"
        )
        escape_parent = project / "reviews/.harness/evidence/junction-attack"
        escape_parent.mkdir(parents=True, exist_ok=True)
        safe_parent = escape_parent.with_name("junction-attack-safe")
        outside = Path(raw) / "outside-publication"
        outside.mkdir()

        publication_swap = "not_attempted"

        def swap_publication_parent() -> None:
            nonlocal publication_swap
            try:
                escape_parent.replace(safe_parent)
                _directory_link(escape_parent, outside)
                publication_swap = "completed"
            except OSError:
                publication_swap = "prevented"

        original_durable_write = evidence_publication._durable_write

        def inject_junction_after_prepare(
            path: Path, data: bytes, **kwargs: object
        ) -> None:
            original_durable_write(path, data, **kwargs)
            if (
                publication_swap == "not_attempted"
                and path.name == "journal.json"
                and b'"state":"publishing"' in data
            ):
                swap_publication_parent()

        evidence_publication._durable_write = inject_junction_after_prepare
        try:
            publication_result = "success"
            try:
                evidence_publication.publish_committed(
                    project_root=project,
                    transaction_id="junction-escape-regression",
                    preconditions=[],
                    inventory_preconditions=[],
                    outputs=[(escape_parent / "product.json", b"{}\n")],
                    marker=(escape_parent / "commit-marker.json", b"{}\n"),
                )
            except (evidence_publication.EvidencePublicationError, OSError):
                publication_result = "refused"
            if publication_swap == "not_attempted":
                raise AssertionError(
                    "ancestor junction swap did not trigger during publication"
                )
            if publication_swap == "completed" and publication_result == "success":
                raise AssertionError(
                    "evidence publication accepted an ancestor junction swap"
                )
            assert not (outside / "product.json").exists(), (
                "junction substitution redirected publication outside the project"
            )
            assert list(outside.iterdir()) == [], (
                "outside content changed during publication ancestor substitution"
            )
        finally:
            evidence_publication._durable_write = original_durable_write
            if publication_swap == "completed":
                _remove_directory_link(escape_parent)
                if safe_parent.exists():
                    safe_parent.replace(escape_parent)
        publication_lock = (
            project / ".harness-evidence-transactions/publication.lock"
        )
        with evidence_publication._claim_lock(publication_lock, root=project):
            try:
                evidence_publication.recover_committed(
                    project_root=project,
                    transaction_id="junction-escape-regression",
                    acknowledgement="inspected-evidence-state-and-journal",
                    preconditions=[],
                    inventory_preconditions=[],
                    outputs=[(escape_parent / "product.json", b"{}\n")],
                    marker=(escape_parent / "commit-marker.json", b"{}\n"),
                    destination_validator=lambda _path: None,
                )
            except evidence_publication.EvidencePublicationError:
                pass
            else:
                raise AssertionError(
                    "evidence recovery bypassed the project publication lock"
                )
        (escape_parent / "product.json").write_bytes(b"{}\n")
        recovery_parent = project / "reviews/.harness/evidence/junction-recovery"
        recovery_parent.mkdir(parents=True, exist_ok=True)
        recovery_safe = recovery_parent.with_name("junction-recovery-safe")
        recovery_product = recovery_parent / "product.json"
        recovery_marker = recovery_parent / "commit-marker.json"
        original_exclusive_marker = evidence_publication._exclusive_marker

        def interrupt_before_marker(
            path: Path, data: bytes, **kwargs: object
        ) -> None:
            if path.name == "commit-marker.json":
                raise OSError("injected interrupt before marker")
            original_exclusive_marker(path, data, **kwargs)

        evidence_publication._exclusive_marker = interrupt_before_marker
        try:
            try:
                evidence_publication.publish_committed(
                    project_root=project,
                    transaction_id="junction-escape-recovery",
                    preconditions=[],
                    inventory_preconditions=[],
                    outputs=[(recovery_product, b"{}\n")],
                    marker=(recovery_marker, b"{}\n"),
                )
            except evidence_publication.EvidencePublicationError:
                pass
            else:
                raise AssertionError(
                    "setup publish did not interrupt before the recovery marker"
                )
        finally:
            evidence_publication._exclusive_marker = original_exclusive_marker
        recovery_product.write_bytes(b"{}\n")
        recovery_swap = "not_attempted"

        def inject_recovery_junction(
            path: Path, data: bytes, **kwargs: object
        ) -> None:
            nonlocal recovery_swap
            if recovery_swap == "not_attempted" and path.name == "commit-marker.json":
                try:
                    recovery_parent.replace(recovery_safe)
                    _directory_link(recovery_parent, outside)
                    recovery_swap = "completed"
                except OSError:
                    recovery_swap = "prevented"
            original_exclusive_marker(path, data, **kwargs)

        evidence_publication._exclusive_marker = inject_recovery_junction
        try:
            recovery_result = "success"
            try:
                evidence_publication.recover_committed(
                    project_root=project,
                    transaction_id="junction-escape-recovery",
                    acknowledgement="inspected-evidence-state-and-journal",
                    preconditions=[],
                    inventory_preconditions=[],
                    outputs=[(recovery_product, b"{}\n")],
                    marker=(recovery_marker, b"{}\n"),
                    destination_validator=lambda _path: None,
                )
            except (evidence_publication.EvidencePublicationError, OSError):
                recovery_result = "refused"
            if recovery_swap == "not_attempted":
                raise AssertionError(
                    "ancestor junction swap did not trigger during recovery"
                )
            if recovery_swap == "completed" and recovery_result == "success":
                raise AssertionError(
                    "evidence recovery accepted an ancestor junction swap"
                )
            assert not (outside / "commit-marker.json").exists(), (
                "junction substitution redirected recovery outside the project"
            )
            assert list(outside.iterdir()) == [], (
                "outside content changed during recovery ancestor substitution"
            )
        finally:
            evidence_publication._exclusive_marker = original_exclusive_marker
            if recovery_swap == "completed":
                _remove_directory_link(recovery_parent)
                if recovery_safe.exists():
                    recovery_safe.replace(recovery_parent)
        write_valid_contract(project)
        _write_json(
            project / "project_manifest.json",
            {
                "schema_version": "synthetic-nonqualifying-1.0.0",
                "identity": "production-evidence-publisher-smoketest",
                "fixture_id": "production-evidence-publisher-smoketest",
                "production_authority": False,
            },
        )
        artifact = project / "milestones/M1_project_memo.md"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(
            "# M1\n\n"
            "This paper argues a bounded claim because evidence supports the "
            "warrant and explains the stakes. However, a limitation defines "
            "the scope and an alternative explanation. AI-assisted work is "
            "disclosed.\n",
            encoding="utf-8",
        )
        directives = project / "research_notes/directives.md"
        directives.parent.mkdir(parents=True, exist_ok=True)
        directives.write_text(
            directives.read_text(encoding="utf-8")
            + "\nd_style_profile:\n"
            "  question_type: conceptual\n"
            "  citation_style: venue_template\n"
            "  source_role_policy: strict_role_classification\n"
            "  evidence_display_policy: standard\n"
            "  assistance_disclosure_policy: project_local\n"
            "  harness_profile: standard_research_review\n",
            encoding="utf-8",
        )
        reader_profile_path = (
            project
            / "reviews"
            / ".harness"
            / "policies"
            / "reader_accessibility.resolved.json"
        )
        reader_profile = resolve_reader_profile(project)
        reader_profile_path.write_text(
            json.dumps(reader_profile, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        initial_state_path = project / "reviews" / "phase_state.json"
        initial_state = json.loads(initial_state_path.read_text(encoding="utf-8"))
        initial_state["milestone_framework"]["policy_bindings"][
            "reader_accessibility"
        ] = reader_profile_phase_state_binding(
            reader_profile, reader_profile_path, project
        )
        initial_state_path.write_text(
            json.dumps(initial_state, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        prepared = draft_publish.prepare_contract(
            project_root=project,
            artifact=artifact,
            milestone="M1",
            phase="generation",
            role="generator",
            evidence_label="producer-smoke",
        )
        assert prepared["contract_path"].is_file()
        assert prepared["commit_marker"].is_file()
        assert prepared["contract"]["status"] == "binding_resolved"
        assert prepared["contract"]["centroid"]["semantic_usage"] == "not_invoked"
        draft_publish.validate_prepared_contract(**prepared["validation"])
        if not callable(getattr(dispatch, "issue_obligation_evaluation_claim", None)):
            raise AssertionError(
                "production obligation-evaluation dispatch issuer is absent"
            )

        activation = build_activation_fixture(
            project,
            artifact_relative="milestones/M1_project_memo.md",
            evidence_relative="reviews/.harness/fixtures/producer-smoke",
        )
        activation.mutate_artifact(
            lambda _text: (
                "# M1\n\n"
                "This paper argues a bounded claim because evidence supports "
                "the warrant and explains the stakes. However, a limitation "
                "defines the scope and an alternative explanation. AI-assisted "
                "work is disclosed.\n"
            )
        )
        ready = (
            project
            / "reviews/.harness/assignment/ready/"
            / "gate_receipt_M1_producer_smoke.json"
        )
        subprocess.run(
            [
                sys.executable,
                str(GATE),
                "--project-root",
                str(project),
                "--stage",
                "draft",
                "--target-milestone",
                "M1",
                "--emit-receipt",
                str(ready),
            ],
            check=True,
            text=True, encoding="utf-8", errors="replace"
        )
        record = json.loads(ready.read_text(encoding="utf-8"))
        subprocess.run(
            [
                sys.executable,
                str(PREFLIGHT),
                "--project-root",
                str(project),
                "--receipt",
                str(ready),
                "--consumer",
                "planner",
                "--expected-target",
                "M1",
                "--write-path",
                "milestones/M1_project_memo.md",
            ],
            check=True,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace"
        )
        reserved = ready.parent.parent / "reserved" / ready.name
        generation, generation_path, _ = dispatch.issue_generation_claim(
            project,
            reserved,
            policy_path=activation.wiki_root / "policy.json",
            bibliography_snapshot=activation.bibliography_snapshot,
            nonce=hashlib.sha256(b"producer-smoke:generation").hexdigest()[:32],
            issuer_transaction_id="assignment-reserve-M1",
            issued_at="2026-08-11T00:00:01Z",
        )
        artifact_bytes = artifact.read_bytes()
        staged = (
            project
            / "reviews/.harness/assignment/staged"
            / record["receipt_id"]
            / "m1.md"
        )
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(artifact_bytes)
        plan = staged.with_name("write_plan.json")
        _write_json(
            plan,
            {
                "schema_version": "1.0.0",
                "receipt_id": record["receipt_id"],
                "reservation_id": record["reservation_id"],
                "target_milestone": "M1",
                "role": "generator",
                "writes": [
                    {
                        "staged_path": staged.relative_to(project).as_posix(),
                        "target_path": "milestones/M1_project_memo.md",
                        "sha256": hashlib.sha256(artifact_bytes).hexdigest(),
                    }
                ],
            },
        )
        subprocess.run(
            [
                sys.executable,
                str(WRITER),
                "--project-root",
                str(project),
                "--receipt",
                str(reserved),
                "--plan",
                str(plan),
            ],
            check=True,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace"
        )
        _, generation_consumption, _ = dispatch.consume_dispatch_claim(
            project,
            generation_path,
            role="generator",
            consumer_transaction_id="assignment-write-M1",
            target_paths=["milestones/M1_project_memo.md"],
            consumed_at="2026-08-11T00:00:02Z",
        )
        prepared_live = draft_publish.prepare_contract(
            project_root=project,
            artifact=artifact,
            milestone="M1",
            phase="generation",
            role="generator",
            evidence_label="typed-producer-smoke",
        )
        obligation_claim, obligation_claim_path, _ = (
            dispatch.issue_obligation_evaluation_claim(
                project,
                generation_path,
                generation_consumption=generation_consumption,
                artifact=artifact,
                nonce=hashlib.sha256(
                    b"producer-smoke:obligation-evaluation"
                ).hexdigest()[:32],
                issuer_transaction_id="assignment-obligation-evaluation-M1",
                issued_at="2026-08-11T00:00:03Z",
            )
        )
        assert obligation_claim["claim_kind"] == "obligation_evaluation"
        assert obligation_claim["authority_scope"] == "obligation_results"
        assert obligation_claim_path.is_file()
        if not callable(getattr(dispatch, "consume_evidence_dispatch_claim", None)):
            raise AssertionError(
                "production evidence-backed dispatch consumption is absent"
            )
        report_path = (
            project
            / "reviews/.harness/evidence/obligation-results/producer-smoke/"
            / "grounding-protocol-report.json"
        )
        report_data = _json_bytes(
            {
                "schema_version": "1.0.0",
                "report_type": "producer_smoke_subject",
                "artifact_sha256": hashlib.sha256(artifact_bytes).hexdigest(),
            }
        )
        report_marker = report_path.with_name("commit-marker.json")
        report_marker_data = _json_bytes(
            {
                "schema_version": "1.0.0",
                "publication_type": "obligation_report_batch",
                "state": "committed",
                "transaction_id": "obligation-report-producer-smoke",
            }
        )
        evidence_publication.publish_committed(
            project_root=project,
            transaction_id="obligation-report-producer-smoke",
            preconditions=[
                (artifact, hashlib.sha256(artifact_bytes).hexdigest())
            ],
            inventory_preconditions=[],
            outputs=[(report_path, report_data)],
            marker=(report_marker, report_marker_data),
        )
        _, obligation_consumption, _ = dispatch.consume_evidence_dispatch_claim(
            project,
            obligation_claim_path,
            role="evaluator",
            consumer_transaction_id="obligation-results:producer-smoke",
            artifact=artifact,
            publication_transaction_id="obligation-report-producer-smoke",
            product_paths=[report_path],
            commit_marker=report_marker,
            consumed_at="2026-08-11T00:00:04Z",
        )
        dispatch.validate_consumed_claim_for_context(
            project,
            obligation_claim_path,
            obligation_consumption,
            expected_role="evaluator",
            expected_target="milestones/M1_project_memo.md",
            expected_receipt_id=generation["receipt_id"],
            expected_artifact_sha256=hashlib.sha256(artifact_bytes).hexdigest(),
        )
        exact_report = report_path.read_bytes()
        report_path.write_bytes(exact_report + b" ")
        try:
            dispatch.validate_consumed_claim_for_context(
                project,
                obligation_claim_path,
                obligation_consumption,
                expected_role="evaluator",
                expected_target="milestones/M1_project_memo.md",
                expected_receipt_id=generation["receipt_id"],
                expected_artifact_sha256=hashlib.sha256(
                    artifact_bytes
                ).hexdigest(),
            )
        except dispatch.ReceiptTransactionError as exc:
            assert exc.code == "APG-DISPATCH-CLAIM-INVALID"
        else:
            raise AssertionError(
                "evidence-backed consumption accepted a tampered product"
            )
        report_path.write_bytes(exact_report)
        if not callable(getattr(draft_publish, "publish_obligation_results", None)):
            raise AssertionError("production typed-obligation publisher is absent")
        typed_claim, typed_claim_path, _ = (
            dispatch.issue_obligation_evaluation_claim(
                project,
                generation_path,
                generation_consumption=generation_consumption,
                artifact=artifact,
                nonce=hashlib.sha256(
                    b"producer-smoke:typed-obligation-evaluation"
                ).hexdigest()[:32],
                issuer_transaction_id="assignment-obligation-evaluation-M1",
                issued_at="2026-08-11T00:00:05Z",
            )
        )
        registry = json.loads(
            (
                ROOT
                / "references/policies/obligation_result_registry.v1.json"
            ).read_text(encoding="utf-8")
        )
        artifact_binding = {
            "path": artifact.relative_to(project).as_posix(),
            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            "byte_length": artifact.stat().st_size,
        }
        contract_binding = {
            "path": prepared_live["contract_path"].relative_to(project).as_posix(),
            "sha256": hashlib.sha256(
                prepared_live["contract_path"].read_bytes()
            ).hexdigest(),
            "byte_length": prepared_live["contract_path"].stat().st_size,
        }
        adapter_reports: dict[str, Path] = {}
        for row in prepared_live["contract"]["obligations"]:
            if (
                "generation" not in row["phases"]
                or row.get("typed_result_required") is not True
                or row["id"] == "d-style-profile"
            ):
                continue
            obligation_id = row["id"]
            adapter = registry["obligations"][obligation_id]
            report_path = (
                project
                / "reviews/.harness/external-evaluator/producer-smoke"
                / f"{obligation_id}.json"
            )
            _write_json(
                report_path,
                {
                    "schema_version": "1.0.0",
                    "report_type": "obligation_adapter_report",
                    "adapter_id": adapter["adapter_id"],
                    "adapter_version": adapter["adapter_version"],
                    "obligation_id": obligation_id,
                    "artifact": artifact_binding,
                    "policy": contract_binding,
                    "activation": adapter["activation"],
                    "execution_status": "completed",
                    "outcome": "clean",
                    "findings": [],
                    "diagnostic_only": adapter["diagnostic_only"],
                    "created_at": "2026-08-11T00:00:06Z",
                },
            )
            adapter_reports[obligation_id] = report_path
        original_publish_committed = draft_publish.publish_committed
        injected_result_failure = False

        def fail_once_after_obligation_consumption(**kwargs: object) -> None:
            nonlocal injected_result_failure
            transaction_id = str(kwargs.get("transaction_id", ""))
            if (
                not injected_result_failure
                and transaction_id.startswith("obligation-results-")
            ):
                injected_result_failure = True
                raise evidence_publication.EvidencePublicationError(
                    "forced post-consumption publication interruption"
                )
            original_publish_committed(**kwargs)

        draft_publish.publish_committed = fail_once_after_obligation_consumption
        try:
            try:
                draft_publish.publish_obligation_results(
                    project_root=project,
                    artifact=artifact,
                    contract_path=prepared_live["contract_path"],
                    phase="generation",
                    role="generator",
                    milestone="M1",
                    evidence_label="typed-producer-smoke",
                    obligation_claim=typed_claim_path,
                    adapter_reports=adapter_reports,
                    created_at="2026-08-11T00:00:07Z",
                )
            except evidence_publication.EvidencePublicationError:
                pass
            else:
                raise AssertionError(
                    "obligation publication fault injection did not interrupt"
                )
        finally:
            draft_publish.publish_committed = original_publish_committed
        assert len(_committed_consumptions(project, typed_claim["claim_id"])) == 1
        published_results = draft_publish.publish_obligation_results(
            project_root=project,
            artifact=artifact,
            contract_path=prepared_live["contract_path"],
            phase="generation",
            role="generator",
            milestone="M1",
            evidence_label="typed-producer-smoke",
            obligation_claim=typed_claim_path,
            adapter_reports=adapter_reports,
            created_at="2026-08-11T00:00:07Z",
        )
        assert set(published_results["result_paths"]) == {
            row["id"]
            for row in prepared_live["contract"]["obligations"]
            if "generation" in row["phases"]
            and row.get("typed_result_required") is True
        }
        authority_modes = []
        for obligation_id, result_path in published_results["result_paths"].items():
            if obligation_id == "d-style-profile":
                continue
            assert "dispatch-separated-evaluator" in registry["obligations"][
                obligation_id
            ]["authorized_adjudicators"], (
                "the registry does not explicitly authorize the producer's "
                f"dispatch-separated evaluator mode for {obligation_id}"
            )
            result_value = json.loads(result_path.read_text(encoding="utf-8"))
            receipt_path = project / result_value["verifier_receipt"]["path"]
            authority_modes.append(
                json.loads(receipt_path.read_text(encoding="utf-8"))["authority"]
            )
        assert authority_modes and set(authority_modes) == {
            "dispatch-separated-evaluator"
        }, "typed results overstated evaluator independence"
        report_paths = [
            published_results["report_commit_marker"].parent / f"{row['id']}.json"
            for row in prepared_live["contract"]["obligations"]
            if "generation" in row["phases"]
            and row.get("typed_result_required") is True
        ]
        try:
            dispatch.consume_evidence_dispatch_claim(
                project,
                obligation_claim_path,
                role="evaluator",
                consumer_transaction_id="obligation-results:replay-attack",
                artifact=artifact,
                publication_transaction_id=published_results[
                    "report_transaction_id"
                ],
                product_paths=report_paths,
                commit_marker=published_results["report_commit_marker"],
                consumed_at="2026-08-11T00:00:07Z",
            )
        except dispatch.ReceiptTransactionError as exc:
            assert exc.code == "APG-DISPATCH-CLAIM-REPLAY"
        else:
            raise AssertionError(
                "one obligation Evaluator claim acquired multiple consumptions"
            )
        assert typed_claim["claim_id"] != obligation_claim["claim_id"]
        if not callable(getattr(draft_publish, "finalize_evidence", None)):
            raise AssertionError("production draft-governance finalizer is absent")
        finalized = draft_publish.finalize_evidence(
            project_root=project,
            artifact=artifact,
            contract_path=prepared_live["contract_path"],
            obligation_publication=published_results,
            phase="generation",
            role="generator",
            milestone="M1",
            evidence_label="typed-producer-smoke",
            receipt_id=generation["receipt_id"],
            dispatch_claim=generation_path,
            dispatch_consumption=generation_consumption,
        )
        assert finalized["locator"].is_file()
        assert finalized["validated"]["envelope"]["status"] == "verified"
        assert finalized["validated"]["envelope"]["semantic_usage"] == "not_invoked"
        if not callable(getattr(scholarly_publish, "publish_evaluation", None)):
            raise AssertionError("production C6 publisher is absent")
        evaluation_claim, evaluation_claim_path, _ = dispatch.issue_evaluation_claim(
            project,
            generation_path,
            generation_consumption=generation_consumption,
            artifact=artifact,
            generation_draft_governance=finalized["locator"],
            nonce=hashlib.sha256(
                b"producer-smoke:full-evaluation"
            ).hexdigest()[:32],
            issuer_transaction_id="assignment-evaluation-M1",
            issued_at="2026-08-11T00:00:08Z",
        )
        evaluation_prepared = draft_publish.prepare_contract(
            project_root=project,
            artifact=artifact,
            milestone="M1",
            phase="evaluation",
            role="evaluator",
            evidence_label="evaluation-producer-smoke",
        )
        evaluation_obligation_claim, evaluation_obligation_claim_path, _ = (
            dispatch.issue_obligation_evaluation_claim(
                project,
                generation_path,
                generation_consumption=generation_consumption,
                artifact=artifact,
                nonce=hashlib.sha256(
                    b"producer-smoke:evaluation-obligations"
                ).hexdigest()[:32],
                issuer_transaction_id="assignment-obligation-evaluation-M1",
                issued_at="2026-08-11T00:00:09Z",
            )
        )
        evaluation_contract_binding = {
            "path": evaluation_prepared["contract_path"].relative_to(
                project
            ).as_posix(),
            "sha256": hashlib.sha256(
                evaluation_prepared["contract_path"].read_bytes()
            ).hexdigest(),
            "byte_length": evaluation_prepared["contract_path"].stat().st_size,
        }
        evaluation_reports: dict[str, Path] = {}
        for row in evaluation_prepared["contract"]["obligations"]:
            if (
                "evaluation" not in row["phases"]
                or row.get("typed_result_required") is not True
                or row["id"] == "d-style-profile"
            ):
                continue
            obligation_id = row["id"]
            adapter = registry["obligations"][obligation_id]
            report_path = (
                project
                / "reviews/.harness/external-evaluator/evaluation-producer-smoke"
                / f"{obligation_id}.json"
            )
            _write_json(
                report_path,
                {
                    "schema_version": "1.0.0",
                    "report_type": "obligation_adapter_report",
                    "adapter_id": adapter["adapter_id"],
                    "adapter_version": adapter["adapter_version"],
                    "obligation_id": obligation_id,
                    "artifact": artifact_binding,
                    "policy": evaluation_contract_binding,
                    "activation": adapter["activation"],
                    "execution_status": "completed",
                    "outcome": "clean",
                    "findings": [],
                    "diagnostic_only": adapter["diagnostic_only"],
                    "created_at": "2026-08-11T00:00:09Z",
                },
            )
            evaluation_reports[obligation_id] = report_path
        evaluation_results = draft_publish.publish_obligation_results(
            project_root=project,
            artifact=artifact,
            contract_path=evaluation_prepared["contract_path"],
            phase="evaluation",
            role="evaluator",
            milestone="M1",
            evidence_label="evaluation-producer-smoke",
            obligation_claim=evaluation_obligation_claim_path,
            adapter_reports=evaluation_reports,
            created_at="2026-08-11T00:00:09Z",
        )
        claim_text = "This paper argues a bounded claim"
        span = _span(artifact, claim_text)
        profile = _profile(
            {
                "path": "publisher-overwrites-this-binding",
                "sha256": "0" * 64,
                "byte_length": 0,
            }
        )
        register = {
            "schema_version": "1.0.0",
            "register_id": "SCR-PRODUCER-SMOKE",
            "artifact": artifact_binding,
            "review_dispatch": {
                "dispatch_id": evaluation_claim["claim_id"],
                "role": "evaluator",
            },
            "claims": [
                {
                    "claim_id": "C-001",
                    "text": claim_text,
                    "span_sha256": span["sha256"],
                    "locator": {
                        "section": span["section"],
                        "line": span["line"],
                        "byte_start": span["byte_start"],
                        "byte_end": span["byte_end"],
                    },
                    "load_bearing": True,
                    "viewpoint": "project_position",
                    "provenance": "author_derivation",
                    "admission_use": "working_position",
                    "argument_leg": "composition",
                    "modal_force": "qualified",
                    "warrant_relation": "candidate",
                }
            ],
            "generator_inventory": ["C-001"],
            "evaluator_additions": [],
            "evaluator_omissions": [],
            "coverage_disposition": "complete",
            "created_at": "2026-08-11T00:00:09Z",
        }
        judgment = {
            "findings": [],
            "omitted_checks": [],
            "obligation_results": [],
            "independence_level": "dispatch_separation",
            "verdict": {
                "status": "qualified",
                "check_results": [
                    {
                        "check_id": row["check_id"],
                        "status": "pass",
                        "evidence": [artifact_binding],
                        "reasoning": (
                            "The synthetic independent Evaluator supplied this "
                            "bounded pass judgment."
                        ),
                    }
                    for row in profile["checks"]
                ],
            },
        }
        invalid_judgment = copy.deepcopy(judgment)
        invalid_judgment["verdict"]["check_results"] = []
        try:
            scholarly_publish.publish_evaluation(
                project_root=project,
                artifact=artifact,
                evaluation_claim=evaluation_claim_path,
                evaluation_id="SET-PRODUCER-SMOKE-INVALID",
                milestone="M1",
                criteria=[
                    "The bounded M1 claim remains within the stated scope."
                ],
                scholarly_profile=profile,
                claim_register=register,
                judgment=invalid_judgment,
                created_at="2026-08-11T00:00:10Z",
            )
        except scholarly_publish.ScholarlyPublicationError:
            pass
        else:
            raise AssertionError("invalid C6 evidence passed publisher preflight")
        assert _committed_consumptions(project, evaluation_claim["claim_id"]) == [], (
            "invalid C6 evidence consumed the full Evaluator claim"
        )
        stale_binding_judgment = copy.deepcopy(judgment)
        stale_binding_judgment["verdict"]["check_results"][0]["evidence"][0][
            "sha256"
        ] = "0" * 64
        try:
            scholarly_publish.publish_evaluation(
                project_root=project,
                artifact=artifact,
                evaluation_claim=evaluation_claim_path,
                evaluation_id="SET-PRODUCER-SMOKE-STALE-PASS",
                milestone="M1",
                criteria=[
                    "The bounded M1 claim remains within the stated scope."
                ],
                scholarly_profile=profile,
                claim_register=register,
                judgment=stale_binding_judgment,
                created_at="2026-08-11T00:00:10Z",
            )
        except scholarly_publish.ScholarlyPublicationError:
            pass
        else:
            raise AssertionError("stale pass evidence passed substantive C6 preflight")
        assert _committed_consumptions(project, evaluation_claim["claim_id"]) == [], (
            "substantively invalid C6 evidence consumed the Evaluator claim"
        )
        original_consume_evidence = dispatch.consume_evidence_dispatch_claim
        injected_dependency_swap = False

        def swap_profile_during_consumption(*args, **kwargs):
            nonlocal injected_dependency_swap
            evaluation_product = Path(kwargs["product_paths"][0])
            profile_dependency = evaluation_product.parent / "scholarly-profile.json"
            profile_payload = profile_dependency.read_bytes()
            if not injected_dependency_swap:
                injected_dependency_swap = True
                profile_dependency.write_bytes(profile_payload + b" ")
            try:
                return original_consume_evidence(*args, **kwargs)
            finally:
                profile_dependency.write_bytes(profile_payload)

        dispatch.consume_evidence_dispatch_claim = swap_profile_during_consumption
        try:
            try:
                scholarly_publish.publish_evaluation(
                    project_root=project,
                    artifact=artifact,
                    evaluation_claim=evaluation_claim_path,
                    evaluation_id="SET-PRODUCER-SMOKE-DEPENDENCY-SWAP",
                    milestone="M1",
                    criteria=[
                        "The bounded M1 claim remains within the stated scope."
                    ],
                    scholarly_profile=profile,
                    claim_register=register,
                    judgment=judgment,
                    created_at="2026-08-11T00:00:10Z",
                )
            except dispatch.ReceiptTransactionError as exc:
                assert exc.code == "APG-DISPATCH-CLAIM-STALE"
            else:
                raise AssertionError(
                    "C6 consumption accepted a dependency changed after preflight"
                )
        finally:
            dispatch.consume_evidence_dispatch_claim = original_consume_evidence
        assert _committed_consumptions(project, evaluation_claim["claim_id"]) == [], (
            "a post-preflight dependency swap consumed the Evaluator claim"
        )
        original_verify_evaluation = scholarly_publish.scholarly_evaluation.verify_evaluation
        injected_verifier_failure = False

        def fail_once_after_evaluation_consumption(*args, **kwargs):
            nonlocal injected_verifier_failure
            if not injected_verifier_failure:
                injected_verifier_failure = True
                raise RuntimeError("forced post-consumption verifier interruption")
            return original_verify_evaluation(*args, **kwargs)

        scholarly_publish.scholarly_evaluation.verify_evaluation = (
            fail_once_after_evaluation_consumption
        )
        verifier_fault_detail = ""
        try:
            try:
                scholarly_publish.publish_evaluation(
                    project_root=project,
                    artifact=artifact,
                    evaluation_claim=evaluation_claim_path,
                    evaluation_id="SET-PRODUCER-SMOKE",
                    milestone="M1",
                    criteria=[
                        "The bounded M1 claim remains within the stated scope."
                    ],
                    scholarly_profile=profile,
                    claim_register=register,
                    judgment=judgment,
                    created_at="2026-08-11T00:00:10Z",
                )
            except scholarly_publish.ScholarlyPublicationError as exc:
                verifier_fault_detail = str(exc)
            else:
                raise AssertionError("C6 verifier fault injection did not interrupt")
        finally:
            scholarly_publish.scholarly_evaluation.verify_evaluation = (
                original_verify_evaluation
            )
        assert len(_committed_consumptions(project, evaluation_claim["claim_id"])) == 1, verifier_fault_detail
        scholarly = scholarly_publish.publish_evaluation(
            project_root=project,
            artifact=artifact,
            evaluation_claim=evaluation_claim_path,
            evaluation_id="SET-PRODUCER-SMOKE",
            milestone="M1",
            criteria=["The bounded M1 claim remains within the stated scope."],
            scholarly_profile=profile,
            claim_register=register,
            judgment=judgment,
            created_at="2026-08-11T00:00:10Z",
        )
        assert scholarly["verified"]["status"] == "qualified"
        assert scholarly["judgment_truth_certified"] is False
        evaluation_finalized = draft_publish.finalize_evidence(
            project_root=project,
            artifact=artifact,
            contract_path=evaluation_prepared["contract_path"],
            obligation_publication=evaluation_results,
            phase="evaluation",
            role="evaluator",
            milestone="M1",
            evidence_label="evaluation-producer-smoke",
            receipt_id=evaluation_claim["receipt_id"],
            dispatch_claim=evaluation_claim_path,
            dispatch_consumption=scholarly["consumption"],
            expected_generation_result=finalized["validated"],
        )
        assert evaluation_finalized["validated"]["envelope"]["status"] == "verified"
        assert evaluation_obligation_claim["claim_id"] != evaluation_claim["claim_id"]
        generation_locator_binding = {
            "evidence_path": finalized["locator"].relative_to(project).as_posix(),
            "evidence_sha256": hashlib.sha256(
                finalized["locator"].read_bytes()
            ).hexdigest(),
        }
        evaluation_locator_binding = {
            "evidence_path": evaluation_finalized["locator"].relative_to(
                project
            ).as_posix(),
            "evidence_sha256": hashlib.sha256(
                evaluation_finalized["locator"].read_bytes()
            ).hexdigest(),
        }
        checkpoint = checkpoint_input(
            project,
            "M1",
            "2026-08-11T00:00:14Z",
            policy={
                "draft_generation": generation_locator_binding,
                "draft_evaluation": evaluation_locator_binding,
                "scholarly_evaluation": scholarly["binding"],
            },
        )
        record_transaction(
            project,
            "M1",
            ready.parent.parent / "consumed" / ready.name,
            checkpoint,
            "2026-08-11T00:00:15Z",
        )
        phase_state_path = project / "reviews" / "phase_state.json"
        phase_state = json.loads(phase_state_path.read_text(encoding="utf-8"))
        validation = validate_document(project, phase_state)
        assert validation.exit_permitted, validation.findings
        framework = phase_state["milestone_framework"]
        assert any(
            row.get("event_type") == "deliverable_recorded"
            and row.get("milestone") == "M1"
            for row in framework["events"]
        ), "native reader-profile-v2 evidence did not admit a genuine M1 record"
        assert set(framework["milestones"]["M1"]["policy_evidence"]) >= {
            "draft_generation",
            "draft_evaluation",
            "scholarly_evaluation",
            "assignment_receipt",
        }
        terminal = subprocess.run(
            [
                sys.executable,
                str(FULL_RUN),
                "terminal",
                "--project-root",
                str(project),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=180, encoding="utf-8", errors="replace"
        )
        assert terminal.returncode == 4, terminal.stdout + terminal.stderr
        terminal_diagnostics = terminal.stdout + terminal.stderr
        assert "FRC-TERMINAL-UNPROVEN" in terminal_diagnostics, (
            "the incomplete M2-M5 ladder, not M1 evidence admission, must explain "
            "the expected terminal refusal"
        )
        for forbidden in (
            "FRC-DRAFT-POLICY-MISSING",
            "FRC-DRAFT-POLICY-STALE",
            "AMC-SCHOLARLY-EVALUATION-MISSING",
            "AMC-SCHOLARLY-EVALUATION-STALE",
        ):
            assert forbidden not in terminal_diagnostics, terminal_diagnostics

    print("production evidence publisher smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
