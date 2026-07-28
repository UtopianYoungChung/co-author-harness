#!/usr/bin/env python3
"""Synthetic public-command M1-to-M2 scholarly recovery sequence."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import assignment_dispatch_claim as dispatch_claims
import assignment_milestone_checkpoint_smoketest as checkpoint_fixture
import control_plane_transition as control_transition
from assignment_fixture_support import write_valid_contract
from c2_evidence_fixture_support import build_activation_fixture
from assignment_milestone_checkpoint_smoketest import (
    BOOTSTRAP,
    CHECKPOINT,
    _lifecycle_locator,
    approval_input,
    checkpoint_input,
    run,
    state,
)
from scholarly_assurance_fixture_support import (
    build_qualified_scholarly_from_authorities,
)
from scholarly_evaluation_binding import (
    ScholarlyBindingError,
    validate_scholarly_binding,
)
from semantic_graph_fixture_support import semantic_graph_fixture_environment


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_RELATIVE = "milestones/M1_project_memo.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_rebind(project: Path) -> tuple[dict[str, object], dict[str, bytes]]:
    """Publish eight exact synthetic controls and invalidate one old receipt."""

    preview = build_activation_fixture(
        project,
        artifact_relative=ARTIFACT_RELATIVE,
        evidence_relative="reviews/.harness/fixtures/m1-scholarly-recovery",
    )
    preview.mutate_artifact(
        lambda text: (
            f"{text}\n\n# M1 synthetic deliverable\n\n# Synthetic analysis\n\n"
            "A bounded synthetic M1 claim remains qualified.\n"
        )
    )
    rebound_artifact = preview.artifact.read_bytes()
    old = (
        project
        / "reviews/.harness/assignment/ready/gate_receipt_M1_20260726T000010Z.json"
    )
    phase_before_authority = (project / "reviews/phase_state.json").read_bytes()
    run(
        checkpoint_fixture.GATE,
        "--project-root",
        project,
        "--stage",
        "draft",
        "--target-milestone",
        "M1",
        "--emit-receipt",
        old,
    )
    authorized = run(
        checkpoint_fixture.GATE,
        "--project-root",
        project,
        "--verify-receipt",
        old,
    )
    if "VERIFIED assignment-process receipt" not in authorized.stdout:
        raise AssertionError("production READY receipt did not authorize before rebind")
    if (project / "reviews/phase_state.json").read_bytes() != phase_before_authority:
        raise AssertionError("READY receipt verification changed milestone state")
    old_value = json.loads(old.read_text(encoding="utf-8"))
    old_bytes = old.read_bytes()
    old_hash = hashlib.sha256(old_bytes).hexdigest()
    plan: dict[str, list[dict[str, str]]] = {
        "members": [],
        "superseded_authority": [
            {
                "receipt_id": old_value["receipt_id"],
                "authority_kind": "receipt",
                "pre_state": "ready",
                "path": old.relative_to(project).as_posix(),
            }
        ],
    }
    expected: dict[str, bytes] = {}
    for name in control_transition.MEMBERS:
        target_relative = (
            ARTIFACT_RELATIVE
            if name == "active_target"
            else f"controls/rebound/{name}.json"
        )
        candidate_relative = f"controls/candidate/{name}.json"
        target = project / target_relative
        candidate = project / candidate_relative
        target.parent.mkdir(parents=True, exist_ok=True)
        candidate.parent.mkdir(parents=True, exist_ok=True)
        if name == "active_target":
            target.write_text(
                "# Superseded synthetic M1 target\n",
                encoding="utf-8",
                newline="\n",
            )
            candidate.write_bytes(rebound_artifact)
        else:
            target.write_text(
                json.dumps({"revision": "old", "member": name}) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            candidate.write_text(
                json.dumps(
                    {"revision": "rebound", "member": name}, sort_keys=True
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
        expected[target_relative] = candidate.read_bytes()
        plan["members"].append(
            {
                "member": name,
                "control_revision": "C7-rebound",
                "path": target_relative,
                "candidate_path": candidate_relative,
                "publication_mode": "replace",
            }
        )
    transition_id = "c7-integrated-rebind"
    prepared = control_transition.prepare(project, plan, transition_id)
    superseded = prepared["superseded_authority"]
    invalidations = prepared["publication_manifest"]["invalidations"]
    if superseded != [
        {
            "receipt_id": old_value["receipt_id"],
            "authority_kind": "receipt",
            "pre_state": "ready",
            "post_state": "invalidated",
        }
    ]:
        raise AssertionError("transition does not name the exact READY identity")
    if not (
        len(invalidations) == 1
        and invalidations[0]["receipt_id"] == old_value["receipt_id"]
        and invalidations[0]["source"]["path"]
        == old.relative_to(project).as_posix()
        and invalidations[0]["source"]["preimage"]
        == {
            "exists": True,
            "sha256": old_hash,
            "byte_length": len(old_bytes),
        }
    ):
        raise AssertionError("transition does not bind exact READY path/hash/identity")
    control_transition.publish(project, transition_id)
    committed = control_transition.verify_committed(project, transition_id)
    if committed.get("findings") != []:
        raise AssertionError(f"atomic rebind did not verify: {committed!r}")
    for relative, payload in expected.items():
        if (project / relative).read_bytes() != payload:
            raise AssertionError(f"atomic rebind postimage differs: {relative}")
    marker = (
        project
        / "reviews/.harness/control-plane/transitions"
        / transition_id
        / "commit_marker.json"
    )
    invalidated = (
        project / "reviews/.harness/assignment/invalidated" / old.name
    )
    if (
        not marker.is_file()
        or old.exists()
        or not invalidated.is_file()
        or invalidated.read_bytes() != old_bytes
    ):
        raise AssertionError("atomic rebind did not publish marker-last invalidation")
    return (
        {
            "path": invalidated,
            "receipt_id": old_value["receipt_id"],
            "sha256": old_hash,
            "bytes": old_bytes,
        },
        expected,
    )


def rebound_authorities(
    project: Path,
    policy: dict,
    *,
    label: str,
) -> dict:
    """Issue another Evaluator dispatch over the rebound Generator bytes."""

    locator = json.loads(
        (project / policy["draft_generation"]["evidence_path"]).read_text(
            encoding="utf-8"
        )
    )
    claim_path = project / locator["dispatch_claim"]["path"]
    consumption_path = project / locator["dispatch_consumption"]["path"]
    generation = json.loads(claim_path.read_text(encoding="utf-8"))
    transaction = project / locator["transaction"]["path"]
    publication = project / locator["publication_manifest"]["path"]
    marker = project / locator["commit_marker"]["path"]
    semantic = project / locator["semantic_receipt"]["path"]
    wiki_root = ROOT / locator["wiki_root"]["path"]
    semantics = ROOT / locator["semantics_manifest"]["path"]
    artifact = project / ARTIFACT_RELATIVE
    evaluator, evaluator_path, _ = dispatch_claims.issue_evaluation_claim(
        project,
        claim_path,
        generation_consumption=consumption_path,
        artifact=artifact,
        generation_transaction=transaction,
        generation_publication_manifest=publication,
        generation_commit_marker=marker,
        generation_semantic_receipt=semantic,
        wiki_root=wiki_root,
        semantics_manifest=semantics,
        nonce=hashlib.sha256(f"{label}:evaluation".encode()).hexdigest()[:32],
        issuer_transaction_id="assignment-evaluation-M1",
        issued_at="2026-07-26T00:02:00Z",
    )
    return {
        "artifact": artifact,
        "artifact_relative": ARTIFACT_RELATIVE,
        "receipt_id": generation["receipt_id"],
        "reservation_id": generation["reservation_id"],
        "activation": SimpleNamespace(
            artifact=artifact,
            receipt=semantic,
            wiki_root=wiki_root,
        ),
        "semantics": semantics,
        "generation": generation,
        "generation_path": claim_path,
        "generation_consumption": consumption_path,
        "generation_paths": {
            "transaction": transaction,
            "publication_manifest": publication,
            "commit_marker": marker,
        },
        "evaluator": evaluator,
        "evaluator_path": evaluator_path,
    }


def evaluation_policy(
    project: Path,
    base: dict,
    fixture: object,
    authorities: dict,
    *,
    label: str,
) -> dict:
    policy = copy.deepcopy(base)
    transaction_id = json.loads(
        authorities["generation_paths"]["transaction"].read_text(encoding="utf-8")
    )["transaction_id"]
    policy["draft_evaluation"] = _lifecycle_locator(
        project,
        milestone="M1",
        label=label,
        phase="evaluation",
        receipt_id=authorities["receipt_id"],
        paths=fixture.evaluation_verifier,
        claim=authorities["evaluator_path"],
        consumption=fixture.evaluation_consumption,
        semantic_receipt=fixture.evaluation_semantic_receipt,
        wiki_root=authorities["activation"].wiki_root,
        generation_transaction_id=transaction_id,
        semantics_manifest=authorities["semantics"],
    )
    policy["scholarly_evaluation"] = fixture.binding
    return policy


def publish_rebound(project: Path) -> tuple[Path, dict]:
    """Run the shared public publisher with the committed rebind identity."""

    original = checkpoint_fixture.run

    def rebound_run(*arguments: object, expected: int = 0):
        values = list(arguments)
        if values and Path(values[0]) == checkpoint_fixture.GATE:
            values.extend(["--control-transition-id", "c7-integrated-rebind"])
        return original(*values, expected=expected)

    checkpoint_fixture.run = rebound_run
    try:
        return checkpoint_fixture.publish(
            project,
            "M1",
            b"# M1 synthetic deliverable\n",
            label="scholarly-recovery",
        )
    finally:
        checkpoint_fixture.run = original


def public_checkpoint(
    project: Path,
    command: str,
    *arguments: object,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECKPOINT),
            command,
            "--project-root",
            str(project),
            *(str(value) for value in arguments),
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def expect_refusal(
    result: subprocess.CompletedProcess[str], code: str, label: str
) -> None:
    output = result.stdout + result.stderr
    if result.returncode != 4 or code not in output:
        raise AssertionError(
            f"{label}: expected rc=4 {code}, got rc={result.returncode}: {output!r}"
        )


def main() -> int:
    cases = 0
    with semantic_graph_fixture_environment():
        with tempfile.TemporaryDirectory(
            prefix="scholarly-lifecycle-c7-", dir=ROOT
        ) as raw:
            project = Path(raw) / "recovery"
            run(
                BOOTSTRAP,
                "--project-root",
                project,
                "--project-name",
                "scholarly-recovery",
                "--title",
                "Synthetic Scholarly Recovery",
                "--intended-reader",
                "researcher",
                "--created-at",
                "2026-07-26T00:00:00Z",
            )
            write_valid_contract(project)
            old_authority, rebound_postimages = atomic_rebind(project)
            phase_after_rebind = (project / "reviews/phase_state.json").read_bytes()
            old_refusal = subprocess.run(
                [
                    sys.executable,
                    str(checkpoint_fixture.GATE),
                    "--project-root",
                    str(project),
                    "--verify-receipt",
                    str(old_authority["path"]),
                ],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
            expect_refusal(
                old_refusal, "APG-RECEIPT-INVALID", "old authority"
            )
            assert (project / "reviews/phase_state.json").read_bytes() == phase_after_rebind
            assert Path(old_authority["path"]).read_bytes() == old_authority["bytes"]
            assert sha(Path(old_authority["path"])) == old_authority["sha256"]
            for relative, payload in rebound_postimages.items():
                assert (project / relative).read_bytes() == payload
            cases += 1

            consumed, clean_policy = publish_rebound(project)

            receipt = json.loads(consumed.read_text(encoding="utf-8"))
            artifact = project / ARTIFACT_RELATIVE
            scholarly = validate_scholarly_binding(
                project_root=project,
                artifact=artifact,
                binding=clean_policy["scholarly_evaluation"],
            )
            generation_locator = json.loads(
                (project / clean_policy["draft_generation"]["evidence_path"]).read_text(
                    encoding="utf-8"
                )
            )
            evaluation_locator = json.loads(
                (project / clean_policy["draft_evaluation"]["evidence_path"]).read_text(
                    encoding="utf-8"
                )
            )
            if not (
                generation_locator["receipt_id"]
                == evaluation_locator["receipt_id"]
                == receipt["receipt_id"]
            ):
                raise AssertionError("draft and scholarly authorities split receipt identity")
            dependency_paths = {str(path) for path in scholarly["dependency_paths"]}
            for key in ("dispatch_claim", "dispatch_consumption"):
                expected = str(
                    (project / evaluation_locator[key]["path"]).resolve()
                )
                if expected not in dependency_paths:
                    raise AssertionError(
                        f"C6 dependency inventory omits same-chain {key}: {expected}"
                    )
            generation_claim = json.loads(
                (project / generation_locator["dispatch_claim"]["path"]).read_text(
                    encoding="utf-8"
                )
            )
            if generation_claim["target_path"] != ARTIFACT_RELATIVE:
                raise AssertionError("rebound Generator dispatch names another target")
            generation_transaction = json.loads(
                (project / generation_locator["transaction"]["path"]).read_text(
                    encoding="utf-8"
                )
            )
            if generation_transaction["artifact"]["sha256"] != sha(artifact):
                raise AssertionError("rebound Generator publication does not bind current bytes")
            cases += 1

            missing_policy = copy.deepcopy(clean_policy)
            del missing_policy["scholarly_evaluation"]
            missing_checkpoint = checkpoint_input(
                project,
                "M1",
                "2026-07-26T00:01:00Z",
                label="missing-scholarly",
                policy=missing_policy,
            )
            before_missing = (project / "reviews/phase_state.json").read_bytes()
            expect_refusal(
                public_checkpoint(
                    project,
                    "record",
                    "--milestone",
                    "M1",
                    "--receipt",
                    consumed,
                    "--checkpoint",
                    missing_checkpoint,
                    "--at",
                    "2026-07-26T00:01:01Z",
                ),
                "AMC-SCHOLARLY-EVALUATION-MISSING",
                "missing scholarly evaluation",
            )
            assert (project / "reviews/phase_state.json").read_bytes() == before_missing
            cases += 1

            stale_policy = copy.deepcopy(clean_policy)
            stale_policy["scholarly_evaluation"]["evidence_sha256"] = "0" * 64
            stale_checkpoint = checkpoint_input(
                project,
                "M1",
                "2026-07-26T00:02:00Z",
                label="stale-scholarly",
                policy=stale_policy,
            )
            before_stale = (project / "reviews/phase_state.json").read_bytes()
            expect_refusal(
                public_checkpoint(
                    project,
                    "record",
                    "--milestone",
                    "M1",
                    "--receipt",
                    consumed,
                    "--checkpoint",
                    stale_checkpoint,
                    "--at",
                    "2026-07-26T00:02:01Z",
                ),
                "AMC-SCHOLARLY-EVALUATION-STALE",
                "stale scholarly evaluation",
            )
            assert (project / "reviews/phase_state.json").read_bytes() == before_stale
            cases += 1

            claim_text = "A bounded synthetic M1 claim remains qualified."
            blocked_authorities = rebound_authorities(
                project, clean_policy, label="c7-unresolved-major"
            )
            blocked_fixture = build_qualified_scholarly_from_authorities(
                project,
                authorities=blocked_authorities,
                label="c7-unresolved-major",
                claim_text=claim_text,
                include_dstyle=True,
                allow_blocked=True,
            )
            if blocked_fixture.verified.get("status") != "blocked":
                raise AssertionError("synthetic Evaluator did not retain unresolved MAJOR")
            try:
                validate_scholarly_binding(
                    project_root=project,
                    artifact=artifact,
                    binding=blocked_fixture.binding,
                )
            except ScholarlyBindingError as exc:
                if exc.cause_code != "SET-FINDING-UNRESOLVED":
                    raise AssertionError(f"unexpected unresolved-MAJOR mapping: {exc.cause_code}")
            else:
                raise AssertionError("unresolved obligation MAJOR qualified")
            blocked_policy = evaluation_policy(
                project,
                clean_policy,
                blocked_fixture,
                blocked_authorities,
                label="c7-unresolved-major",
            )
            blocked_checkpoint = checkpoint_input(
                project,
                "M1",
                "2026-07-26T00:02:30Z",
                label="unresolved-major",
                policy=blocked_policy,
            )
            before_blocked = (project / "reviews/phase_state.json").read_bytes()
            expect_refusal(
                public_checkpoint(
                    project,
                    "record",
                    "--milestone",
                    "M1",
                    "--receipt",
                    consumed,
                    "--checkpoint",
                    blocked_checkpoint,
                    "--at",
                    "2026-07-26T00:02:31Z",
                ),
                "AMC-SCHOLARLY-EVALUATION-STALE",
                "unresolved obligation MAJOR",
            )
            assert (project / "reviews/phase_state.json").read_bytes() == before_blocked
            assert state(project)["milestone_framework"]["milestones"]["M1"]["handoff"]["status"] == "not_ready"
            cases += 1

            resolved_authorities = rebound_authorities(
                project, clean_policy, label="c7-resolved-major"
            )
            resolved_fixture = build_qualified_scholarly_from_authorities(
                project,
                authorities=resolved_authorities,
                label="c7-resolved-major",
                claim_text=claim_text,
                include_dstyle=True,
                adjudicate_dstyle=True,
            )
            if resolved_fixture.artifact.read_bytes() != artifact.read_bytes():
                raise AssertionError("resolved evaluation changed the rebound artifact")
            resolved_value = json.loads(
                resolved_fixture.evaluation.read_text(encoding="utf-8")
            )
            obligation_entry = resolved_value["obligation_results"][0]
            result_value = json.loads(
                (project / obligation_entry["result"]["path"]).read_text(
                    encoding="utf-8"
                )
            )
            if not (
                any(row["severity"] == "MAJOR" for row in result_value["findings"])
                and result_value["adjudications"]
                and all(
                    row["disposition"] == "resolved"
                    for row in result_value["adjudications"]
                )
            ):
                raise AssertionError("Evaluator finding/adjudication chain is incomplete")
            resolved_policy = evaluation_policy(
                project,
                clean_policy,
                resolved_fixture,
                resolved_authorities,
                label="c7-resolved-major",
            )
            cases += 1

            plausible = project / "reviews/.harness/status-complete.md"
            plausible.parent.mkdir(parents=True, exist_ok=True)
            plausible.write_text(
                "# Scholarly evaluation\n\nstatus: complete\n",
                encoding="utf-8",
                newline="\n",
            )
            before_markdown = (project / "reviews/phase_state.json").read_bytes()
            expect_refusal(
                public_checkpoint(
                    project,
                    "record",
                    "--milestone",
                    "M1",
                    "--receipt",
                    consumed,
                    "--checkpoint",
                    plausible,
                    "--at",
                    "2026-07-26T00:02:40Z",
                ),
                "AMC-CHECKPOINT",
                "plausible complete Markdown",
            )
            assert (project / "reviews/phase_state.json").read_bytes() == before_markdown
            cases += 1

            hostile_policy = copy.deepcopy(resolved_policy)
            hostile_policy["draft_evaluation"] = clean_policy["draft_evaluation"]
            hostile_checkpoint = checkpoint_input(
                project,
                "M1",
                "2026-07-26T00:02:50Z",
                label="same-artifact-second-chain",
                policy=hostile_policy,
            )
            before_hostile = (project / "reviews/phase_state.json").read_bytes()
            expect_refusal(
                public_checkpoint(
                    project,
                    "record",
                    "--milestone",
                    "M1",
                    "--receipt",
                    consumed,
                    "--checkpoint",
                    hostile_checkpoint,
                    "--at",
                    "2026-07-26T00:02:51Z",
                ),
                "AMC-SCHOLARLY-EVALUATION-STALE",
                "same-artifact second-chain substitution",
            )
            assert (project / "reviews/phase_state.json").read_bytes() == before_hostile
            cases += 1

            clean_checkpoint = checkpoint_input(
                project,
                "M1",
                "2026-07-26T00:03:00Z",
                label="recovered",
                policy=resolved_policy,
            )
            recorded = public_checkpoint(
                project,
                "record",
                "--milestone",
                "M1",
                "--receipt",
                consumed,
                "--checkpoint",
                clean_checkpoint,
                "--at",
                "2026-07-26T00:03:01Z",
            )
            if recorded.returncode != 0:
                raise AssertionError(recorded.stdout + recorded.stderr)
            retained = state(project)["milestone_framework"]["milestones"]["M1"]
            if retained.get("policy_evidence", {}).get("scholarly_evaluation") != (
                resolved_policy["scholarly_evaluation"]
            ):
                raise AssertionError("M1 record did not retain exact scholarly binding")
            cases += 1

            before_missing_approval = (
                project / "reviews/phase_state.json"
            ).read_bytes()
            expect_refusal(
                public_checkpoint(
                    project,
                    "accept",
                    "--milestone",
                    "M1",
                    "--checkpoint",
                    clean_checkpoint,
                    "--approval-evidence",
                    project / "missing-user-approval.json",
                    "--at",
                    "2026-07-26T00:04:00Z",
                ),
                "AMC-APPROVAL",
                "user approval separation",
            )
            assert (
                project / "reviews/phase_state.json"
            ).read_bytes() == before_missing_approval
            cases += 1

            evaluation_bytes = resolved_fixture.evaluation.read_bytes()
            resolved_fixture.evaluation.write_bytes(evaluation_bytes + b" ")
            before_stale_accept = (project / "reviews/phase_state.json").read_bytes()
            try:
                stale_approval = approval_input(
                    project, "M1", "2026-07-26T00:04:00Z"
                )
                expect_refusal(
                    public_checkpoint(
                        project,
                        "accept",
                        "--milestone",
                        "M1",
                        "--checkpoint",
                        clean_checkpoint,
                        "--approval-evidence",
                        stale_approval,
                        "--at",
                        "2026-07-26T00:04:00Z",
                    ),
                    "AMC-SCHOLARLY-EVALUATION-STALE",
                    "F9 current-evidence replay",
                )
            finally:
                resolved_fixture.evaluation.write_bytes(evaluation_bytes)
            assert (project / "reviews/phase_state.json").read_bytes() == before_stale_accept
            assert state(project)["milestone_framework"]["milestones"]["M1"]["handoff"]["status"] == "not_ready"
            cases += 1

            approval = approval_input(project, "M1", "2026-07-26T00:04:01Z")
            accepted = public_checkpoint(
                project,
                "accept",
                "--milestone",
                "M1",
                "--checkpoint",
                clean_checkpoint,
                "--approval-evidence",
                approval,
                "--at",
                "2026-07-26T00:04:02Z",
            )
            if accepted.returncode != 0:
                raise AssertionError(accepted.stdout + accepted.stderr)
            accepted_state = state(project)["milestone_framework"]["milestones"]["M1"]
            if (
                accepted_state.get("status") != "accepted"
                or accepted_state.get("handoff", {}).get("status") != "ready"
            ):
                raise AssertionError("M1 acceptance did not publish a ready F9 handoff")
            cases += 1

            begun = public_checkpoint(
                project,
                "begin",
                "--milestone",
                "M2",
                "--at",
                "2026-07-26T00:05:00Z",
            )
            if begun.returncode != 0:
                raise AssertionError(begun.stdout + begun.stderr)
            final_state = state(project)["milestone_framework"]["milestones"]
            if (
                final_state["M1"]["handoff"]["status"] != "consumed"
                or final_state["M2"]["status"] != "in_progress"
            ):
                raise AssertionError("public M2 begin did not consume the exact M1 F9")
            cases += 1

    print(
        "scholarly_lifecycle_integration_smoketest: PASS "
        f"({cases} same-chain M1-to-M2 cases)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
