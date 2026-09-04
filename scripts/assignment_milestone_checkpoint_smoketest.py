#!/usr/bin/env python3
"""Public-command M1-M4 checkpoint walk and adversarial regressions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

import assignment_dispatch_claim as dispatch_claims
import assignment_milestone_transaction as milestone_transactions
import draft_governance
from draft_governance_lifecycle import (
    DraftGovernanceLifecycleError,
    validate_lifecycle_draft_governance_binding,
)
import draft_evidence_verifier as verifier
from assignment_fixture_support import write_valid_contract
from c2_evidence_fixture_support import build_activation_fixture
from draft_governance_smoketest import (
    DeterministicFixtureAdapter,
    obligation_receipt,
)
from semantic_graph_fixture_support import semantic_graph_fixture_environment
from scholarly_assurance_fixture_support import (
    build_qualified_scholarly_from_authorities,
)
from assignment_milestone_transaction import (
    MilestoneTransactionError, accept as accept_transaction,
    record as record_transaction,
)
from milestone_framework_validate import validate_document


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "native_project_bootstrap.py"
GATE = ROOT / "scripts" / "assignment_process_gate.py"
PREFLIGHT = ROOT / "scripts" / "assignment_dispatch_preflight.py"
WRITER = ROOT / "scripts" / "assignment_writer_commit.py"
CHECKPOINT = ROOT / "scripts" / "assignment_milestone_checkpoint.py"
VALIDATOR = ROOT / "scripts" / "milestone_framework_validate.py"
PHASE_VALIDATOR = ROOT / "scripts" / "phase_state_validate.py"
FULL_RUN = ROOT / "scripts" / "full_run_contract_check.py"
SEMANTICS = ROOT / "references" / "semantics_manifest.v1.json"
PATHS = {
    "M1": "milestones/M1_project_memo.md",
    "M2": "milestones/M2_annotated_references.md",
    "M3": "milestones/M3_argument_evidence_outline.md",
    "M4": "milestones/M4_complete_paper_draft.md",
    "M5": "milestones/M5_final_paper.md",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: object, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([sys.executable, *(str(arg) for arg in args)], cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True, check=False)
    if result.returncode != expected:
        raise AssertionError(f"expected {expected}, got {result.returncode}: {' '.join(str(arg) for arg in args)}\n{result.stdout}{result.stderr}")
    return result


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def state(project: Path) -> dict:
    return json.loads((project / "reviews" / "phase_state.json").read_text(encoding="utf-8"))


def _root_binding(project: Path, path: Path, root: str) -> dict[str, str]:
    base = project if root == "project" else ROOT
    return {
        "root": root,
        "path": path.resolve().relative_to(base.resolve()).as_posix(),
        "sha256": sha(path),
    }


def _wiki_binding(project: Path, wiki_root: Path) -> dict[str, str]:
    resolved = wiki_root.resolve()
    if resolved.is_relative_to(project.resolve()):
        root, base = "project", project.resolve()
    else:
        root, base = "harness", ROOT.resolve()
    return {
        "root": root,
        "path": resolved.relative_to(base).as_posix(),
        "manifest_sha256": sha(wiki_root / "manifest.json"),
    }


def _lifecycle_locator(
    project: Path, *, milestone: str, label: str, phase: str,
    receipt_id: str, paths: dict, claim: Path, consumption: Path,
    semantic_receipt: Path, wiki_root: Path,
    generation_transaction_id: str | None,
    semantics_manifest: Path = ROOT / "references" / "semantics_manifest.v1.json",
) -> dict[str, str]:
    transaction = paths["transaction"]
    locator = (
        project / "reviews" / ".harness" / "shipments" / "synthetic"
        / f"{milestone.lower()}_{label}_{phase}.lifecycle.json"
    )
    write_json(locator, {
        "schema_version": "1.0.0",
        "binding_type": "lifecycle_verifier_transaction",
        "phase": phase,
        "product_disposition": (
            "evaluation_ready" if phase == "generation" else "product_qualified"
        ),
        "target": PATHS[milestone],
        "receipt_id": receipt_id,
        "transaction": _root_binding(project, transaction, "project"),
        "publication_manifest": _root_binding(
            project, paths["publication_manifest"], "project"
        ),
        "commit_marker": _root_binding(project, paths["commit_marker"], "project"),
        "semantic_receipt": _root_binding(project, semantic_receipt, "project"),
        "wiki_root": _wiki_binding(project, wiki_root),
        "semantics_manifest": _root_binding(
            project, semantics_manifest, "harness"
        ),
        "dispatch_claim": _root_binding(project, claim, "project"),
        "dispatch_consumption": _root_binding(project, consumption, "project"),
        "generation_verifier_transaction_id": generation_transaction_id,
    })
    return {
        "evidence_path": locator.relative_to(project).as_posix(),
        "evidence_sha256": sha(locator),
    }


def _draft_governance_locator(
    project: Path, *, milestone: str, label: str, phase: str,
    receipt_id: str, claim: Path, consumption: Path,
) -> tuple[dict[str, str], Path]:
    """Build real graph-independent draft-governance evidence for lifecycle use."""
    role = {"generation": "generator", "evaluation": "evaluator"}[phase]
    artifact = project / PATHS[milestone]
    lane = (
        project / "reviews" / ".harness" / "draft-governance"
        / f"{milestone.lower()}-{label}-{phase}"
    )
    contract = draft_governance.prepare(SimpleNamespace(
        project_root=str(project), target=milestone, phase=phase,
        role=role, artifact=str(artifact),
    ))
    assert contract["centroid"]["required"] is False
    assert contract["centroid"]["semantic_usage"] == "not_invoked"
    contract_path = lane / "contract.json"
    write_json(contract_path, contract)
    generic = lane / "non-graph-evidence.txt"
    generic.parent.mkdir(parents=True, exist_ok=True)
    generic.write_text("Synthetic current non-graph obligation evidence.\n", encoding="utf-8")
    receipt = obligation_receipt(
        contract, contract_path, artifact, phase, generic, generic,
    )
    receipt_path = lane / "obligation-receipt.json"
    write_json(receipt_path, receipt)
    envelope = draft_governance.verify(
        SimpleNamespace(
            contract=str(contract_path), receipt=str(receipt_path),
            artifact=str(artifact), phase=phase, role=role,
            wiki_root=None, verifier_out_dir=None,
            semantics_manifest=str(SEMANTICS),
            requested_independence_level="none",
        ),
        _test_authority_adapter=DeterministicFixtureAdapter(),
    )
    assert envelope["status"] == "verified"
    assert envelope["semantic_usage"] == "not_invoked"
    envelope_path = lane / "verified-envelope.json"
    write_json(envelope_path, envelope)
    evidence_id = "draft-governance-" + sha(envelope_path)[:16]
    locator = lane / "lifecycle.json"
    write_json(locator, {
        "schema_version": "1.0.0",
        "binding_type": "lifecycle_draft_governance",
        "evidence_id": evidence_id,
        "phase": phase,
        "role": role,
        "target": PATHS[milestone],
        "receipt_id": receipt_id,
        "semantic_usage": "not_invoked",
        "contract": _root_binding(project, contract_path, "project"),
        "obligation_receipt": _root_binding(project, receipt_path, "project"),
        "verified_envelope": _root_binding(project, envelope_path, "project"),
        "dispatch_claim": _root_binding(project, claim, "project"),
        "dispatch_consumption": _root_binding(project, consumption, "project"),
        "lifecycle_inventory": _root_binding(
            project,
            ROOT / "references" / "draft_governance_lifecycle_inventory.v1.json",
            "harness",
        ),
    })
    return ({
        "evidence_path": locator.relative_to(project).as_posix(),
        "evidence_sha256": sha(locator),
    }, locator)


def checkpoint_input(
    project: Path, milestone: str, at: str, *, valid_m4: bool = True,
    label: str = "initial", phase: str = "Ph1", cycle_id: str | None = None,
    policy: dict,
) -> Path:
    suffix = "" if label == "initial" else f"_{label}"
    evidence = project / "reviews" / ".harness" / "milestones" / "checkpoints" / f"{milestone.lower()}_feedback{suffix}.md"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(f"Synthetic adjudicated feedback for {milestone}.\n", encoding="utf-8")
    policy = json.loads(json.dumps(policy))
    if milestone == "M3":
        references = project / "references" / "REFERENCES.md"
        references.parent.mkdir(parents=True, exist_ok=True)
        references.write_text("# Verified synthetic references\n", encoding="utf-8")
        wiki = project / "synthetic-wiki"
        source = wiki / "sources" / "source.md"; source.parent.mkdir(parents=True, exist_ok=True); source.write_text("# Source\n", encoding="utf-8")
        graph = wiki / "graphify-out" / "graph.json"; graph.parent.mkdir(parents=True, exist_ok=True); graph.write_text('{"nodes": []}\n', encoding="utf-8")
        grounding = project / "reviews" / ".harness" / "assignment" / "wiki_grounding_walk.json"
        write_json(grounding, {
            "schema_version": "1.0.0", "lineage_id": "main", "produced_at": at,
            "wiki_path": str(wiki), "wiki_first_resources": True,
            "skills_invoked": ["seed-snowball-discovery"],
            "references_path": "references/REFERENCES.md", "references_sha256": sha(references),
            "graph_path": str(graph), "graph_sha256_provenance": sha(graph),
            "sources_consulted": [{"path": str(source), "sha256": sha(source)}],
            "authority": "planner", "notes": "Synthetic public-command walk evidence."
        })
        policy["wiki_grounding"] = {"evidence_path": grounding.relative_to(project).as_posix(), "evidence_sha256": sha(grounding)}
    elif milestone == "M4":
        policy.update({
            "phase": phase,
            "cycle_id": cycle_id or f"m4-{label}-assembly-001",
        } if valid_m4 else {"phase": phase})
    payload = {
        "schema_version": "1.0.0", "milestone": milestone,
        "feedback_records": [{
            "feedback_id": f"{milestone.lower()}-feedback-{label}",
            "evidence_class": "direct_milestone_feedback",
            "source_path": evidence.relative_to(project).as_posix(), "source_sha256": sha(evidence),
            "source_actor": "user", "source_authority": "user",
            "source_milestone": milestone, "target_milestone": milestone,
            "received_at": at,
            "contemporaneity_evidence_path": evidence.relative_to(project).as_posix(),
            "contemporaneity_evidence_sha256": sha(evidence),
            "lineage_id": "main", "blocking": False, "disposition": "informational",
            "rationale": "Synthetic feedback was reviewed and requires no revision.",
            "successor_effect": "Proceed only after explicit approval."
        }],
        "inputs_consumed": [], "decisions_frozen": [f"Freeze {milestone} synthetic decision."],
        "open_debts": [], "next_milestone_instructions": [f"Use accepted {milestone} evidence."],
        "policy_evidence": policy,
    }
    path = evidence.with_name(f"{milestone.lower()}_checkpoint{suffix}{'_invalid' if not valid_m4 else ''}.json")
    write_json(path, payload)
    return path


def approval_input(project: Path, milestone: str, at: str) -> Path:
    if milestone == "M4":
        record = state(project)["milestone_framework"]["milestones"][milestone]
        artifact = next(row for row in record["artifacts"] if row["role"] == "deliverable")
        deliverable_path = artifact["path"]
    else:
        deliverable_path = PATHS[milestone]
    deliverable = project / deliverable_path
    path = project / "reviews" / ".harness" / "milestones" / "checkpoints" / f"{milestone.lower()}_approval.json"
    write_json(path, {
        "schema_version": "1.0.0", "status": "approved", "milestone": milestone,
        "authority": "user", "approved_at": at,
        "deliverable": {"path": deliverable_path, "sha256": sha(deliverable)},
    })
    return path


def advance_m4_fixture_to_ph2(project: Path) -> None:
    """Prepare a valid Ph2 state so public M4 re-record can bind a revision."""
    document = state(project)
    for section in document["sections"].values():
        section["current_phase"] = "Ph2"
        section["phase_entry_log"].append({
            "prev_phase": "Ph1", "new_phase": "Ph2", "trigger": "user_approval",
            "actor": "user", "notes": "Synthetic Ph2 entry for M4 revision.",
            "timestamp": "2026-07-19T00:00:23.1Z", "model_used": None,
        })
    write_json(project / "reviews" / "phase_state.json", document)


def converge_m4_fixture(project: Path) -> None:
    """Prepare upstream phase-owned state for the separate M4-accept test."""
    document = state(project)
    for section in document["sections"].values():
        if section["current_phase"] == "Ph1":
            section["phase_entry_log"].append(
                {"prev_phase": "Ph1", "new_phase": "Ph2", "trigger": "user_approval", "actor": "user", "notes": "Synthetic Ph2 entry.", "timestamp": "2026-07-19T00:00:23.1Z", "model_used": None}
            )
        section["current_phase"] = "Ph3_converged"
        section["phase_entry_log"].extend([
            {"prev_phase": "Ph2", "new_phase": "Ph3", "trigger": "user_approval", "actor": "user", "notes": "Synthetic Ph3 entry.", "timestamp": "2026-07-19T00:00:23.2Z", "model_used": None},
            {"prev_phase": "Ph3", "new_phase": "Ph3_converged", "trigger": "ph3_convergence_signoff_terminal", "actor": "planner", "notes": "Synthetic terminal convergence signoff.", "timestamp": "2026-07-19T00:00:23.3Z", "model_used": None},
        ])
    write_json(project / "reviews" / "phase_state.json", document)


def m4_acceptance_policy_input(project: Path) -> Path:
    document = state(project)
    framework = document["milestone_framework"]
    binding = framework["policy_bindings"]["reader_accessibility"]
    deliverable = next(
        row for row in framework["milestones"]["M4"]["artifacts"]
        if row.get("role") == "deliverable"
    )
    manuscript_relative = deliverable["path"]
    manuscript = project / manuscript_relative
    transition_snapshot = {key: binding["transitions"][key]["state"] for key in ("G", "H", "VE")}
    check8 = project / "reviews" / "check8_m4_converged.json"
    write_json(check8, {
        "schema_version": "check8_evidence.v2", "cycle_id": "m4-converged-001",
        "profile_path": binding["resolved_path"], "profile_sha256": binding["profile_sha256"],
        "semantic_usage": "not_invoked",
        "manuscript_path": manuscript_relative, "manuscript_sha256": sha(manuscript), "phase": "Ph3",
        "transition_snapshot": transition_snapshot,
        "subchecks": {letter: {"findings": []} for letter in "ABCDEFGH"},
        "subcheck_verdicts": {letter: "CLEAN" for letter in "ABCDEFGH"},
        "ve": {"aggregate_member": False, "gate_contribution": "none", "findings": []},
        "aggregate_verdict": "CLEAN",
    })
    policy = project / "reviews" / ".harness" / "milestones" / "checkpoints" / "m4_acceptance_policy.json"
    write_json(policy, {
        "schema_version": "1.0.0", "milestone": "M4", "manuscript_sha256": sha(manuscript),
        "phase": "Ph3", "cycle_id": "m4-converged-001",
        "check8_path": check8.relative_to(project).as_posix(), "check8_sha256": sha(check8),
        "aggregate_verdict": "CLEAN",
    })
    return policy


def publish(
    project: Path, milestone: str, content: bytes, *, label: str = "initial",
    include_dstyle: bool = False, native_v2: bool = False,
    exercise_v2_adversarial: bool = False,
    ) -> tuple[Path, dict]:
    activation = build_activation_fixture(
        project,
        artifact_relative=PATHS[milestone],
        evidence_relative=f"reviews/.harness/fixtures/{milestone.lower()}-{label}",
    )
    suffix = content.decode("utf-8", errors="strict").strip()
    claim_text = (
        "This paper argues a bounded claim because evidence supports the warrant "
        "and explains the stakes. However, a limitation defines the scope and an "
        "alternative explanation. AI-assisted work is disclosed."
        if include_dstyle or native_v2
        else f"A bounded synthetic {milestone} claim remains qualified."
    )
    activation.mutate_artifact(
        lambda text: (
            f"{text}\n\n{suffix}\n\n# Synthetic analysis\n\n"
            f"{claim_text}\n"
        )
    )
    project_manifest = project / "project_manifest.json"
    if not project_manifest.is_file():
        write_json(project_manifest, {
            "schema_version": "synthetic-nonqualifying-1.0.0",
            "identity": "c5-milestone-lifecycle-fixture",
            "fixture_id": "c5-milestone-lifecycle-fixture",
            "production_authority": False,
        })
    artifact_bytes = activation.artifact.read_bytes()
    ready = project / "reviews" / ".harness" / "assignment" / "ready" / f"gate_receipt_{milestone}_walk_{label}.json"
    run(GATE, "--project-root", project, "--stage", "draft", "--target-milestone", milestone, "--emit-receipt", ready)
    record = json.loads(ready.read_text(encoding="utf-8"))
    run(PREFLIGHT, "--project-root", project, "--receipt", ready, "--consumer", "planner", "--expected-target", milestone, "--write-path", PATHS[milestone])
    reserved = ready.parent.parent / "reserved" / ready.name
    generation_claim, generation_claim_path, _ = dispatch_claims.issue_generation_claim(
        project,
        reserved,
        policy_path=activation.wiki_root / "policy.json",
        bibliography_snapshot=activation.bibliography_snapshot,
        nonce=hashlib.sha256(f"{milestone}:{label}:generation".encode()).hexdigest()[:32],
        issuer_transaction_id=f"assignment-reserve-{milestone}",
        issued_at="2026-07-19T00:00:00Z",
    )
    alternate_generation: tuple[dict, Path] | None = None
    if native_v2 and exercise_v2_adversarial:
        alternate_claim, alternate_path, _ = dispatch_claims.issue_generation_claim(
            project,
            reserved,
            policy_path=activation.wiki_root / "policy.json",
            bibliography_snapshot=activation.bibliography_snapshot,
            nonce=hashlib.sha256(
                f"{milestone}:{label}:alternate-generation".encode()
            ).hexdigest()[:32],
            issuer_transaction_id=f"assignment-reserve-{milestone}",
            issued_at="2026-07-19T00:00:00Z",
        )
        alternate_generation = alternate_claim, alternate_path
    staged = project / "reviews" / ".harness" / "assignment" / "staged" / record["receipt_id"] / f"{milestone.lower()}_{label}.md"
    staged.parent.mkdir(parents=True, exist_ok=True); staged.write_bytes(artifact_bytes)
    plan = staged.with_name("write_plan.json")
    write_json(plan, {
        "schema_version": "1.0.0", "receipt_id": record["receipt_id"],
        "reservation_id": record["reservation_id"], "target_milestone": milestone,
        "role": "generator", "writes": [{
            "staged_path": staged.relative_to(project).as_posix(),
            "target_path": PATHS[milestone], "sha256": hashlib.sha256(artifact_bytes).hexdigest(),
        }]
    })
    run(WRITER, "--project-root", project, "--receipt", reserved, "--plan", plan)
    consumed_receipt = ready.parent.parent / "consumed" / ready.name
    generation_consumption, generation_consumption_path, _ = (
        dispatch_claims.consume_dispatch_claim(
            project,
            generation_claim_path,
            role="generator",
            consumer_transaction_id=f"assignment-write-{milestone}",
            target_paths=[PATHS[milestone]],
            consumed_at="2026-07-19T00:00:01Z",
        )
    )
    alternate_consumption_path: Path | None = None
    if alternate_generation is not None:
        _, alternate_consumption_path, _ = dispatch_claims.consume_dispatch_claim(
            project,
            alternate_generation[1],
            role="generator",
            consumer_transaction_id=f"assignment-write-{milestone}-alternate",
            target_paths=[PATHS[milestone]],
            consumed_at="2026-07-19T00:00:01Z",
        )
    verifier_root = (
        project / "reviews" / ".harness" / "verifier"
        / f"{milestone.lower()}-{label}"
    )
    semantics = SEMANTICS
    if native_v2:
        generation_binding, generation_locator = _draft_governance_locator(
            project, milestone=milestone, label=label, phase="generation",
            receipt_id=record["receipt_id"], claim=generation_claim_path,
            consumption=generation_consumption_path,
        )
        generation_paths = {}
        if alternate_generation is not None and alternate_consumption_path is not None:
            try:
                dispatch_claims.issue_evaluation_claim(
                    project,
                    alternate_generation[1],
                    generation_consumption=alternate_consumption_path,
                    artifact=activation.artifact,
                    generation_draft_governance=generation_locator,
                    nonce=hashlib.sha256(
                        f"{milestone}:{label}:mismatched-evaluation".encode()
                    ).hexdigest()[:32],
                    issuer_transaction_id=f"assignment-evaluation-{milestone}",
                    issued_at="2026-07-19T00:00:02Z",
                    _test_authority_adapter=DeterministicFixtureAdapter(),
                )
            except dispatch_claims.ReceiptTransactionError as exc:
                assert exc.code == "APG-DISPATCH-CLAIM-GENERATION-MISMATCH"
            else:
                raise AssertionError(
                    "evaluation issuance accepted a v2 locator bound to another exact generation claim"
                )
        evaluation_claim, evaluation_claim_path, _ = dispatch_claims.issue_evaluation_claim(
            project,
            generation_claim_path,
            generation_consumption=generation_consumption_path,
            artifact=activation.artifact,
            generation_draft_governance=generation_locator,
            nonce=hashlib.sha256(f"{milestone}:{label}:evaluation".encode()).hexdigest()[:32],
            issuer_transaction_id=f"assignment-evaluation-{milestone}",
            issued_at="2026-07-19T00:00:02Z",
            _test_authority_adapter=DeterministicFixtureAdapter(),
        )
    else:
        generation_paths = verifier.publish_verifier_transaction(
            artifact=activation.artifact,
            semantic_receipt=activation.receipt,
            phase="generation",
            project_root=project,
            wiki_root=activation.wiki_root,
            harness_root=ROOT,
            semantics_manifest=semantics,
            out_dir=verifier_root / "generation",
            requested_independence_level="none",
        )
        evaluation_claim, evaluation_claim_path, _ = dispatch_claims.issue_evaluation_claim(
            project,
            generation_claim_path,
            generation_consumption=generation_consumption_path,
            artifact=activation.artifact,
            generation_transaction=generation_paths["transaction"],
            generation_publication_manifest=generation_paths["publication_manifest"],
            generation_commit_marker=generation_paths["commit_marker"],
            generation_semantic_receipt=activation.receipt,
            wiki_root=activation.wiki_root,
            semantics_manifest=semantics,
            nonce=hashlib.sha256(f"{milestone}:{label}:evaluation".encode()).hexdigest()[:32],
            issuer_transaction_id=f"assignment-evaluation-{milestone}",
            issued_at="2026-07-19T00:00:02Z",
        )
    scholarly = build_qualified_scholarly_from_authorities(
        project,
        authorities={
            "artifact": activation.artifact,
            "artifact_relative": PATHS[milestone],
            "receipt_id": record["receipt_id"],
            "reservation_id": record["reservation_id"],
            "activation": activation,
            "semantics": semantics,
            "generation": generation_claim,
            "generation_path": generation_claim_path,
            "generation_consumption": generation_consumption_path,
            "generation_paths": generation_paths,
            "evaluator": evaluation_claim,
            "evaluator_path": evaluation_claim_path,
        },
        label=f"{milestone.lower()}-{label}",
        claim_text=claim_text,
        include_dstyle=include_dstyle,
        legacy_semantic_evidence=not native_v2,
    )
    evaluation_consumption_path = scholarly.evaluation_consumption
    evaluation_semantic = scholarly.evaluation_semantic_receipt
    evaluation_paths = scholarly.evaluation_verifier
    if native_v2:
        evaluation_binding, _ = _draft_governance_locator(
            project, milestone=milestone, label=label, phase="evaluation",
            receipt_id=record["receipt_id"], claim=evaluation_claim_path,
            consumption=evaluation_consumption_path,
        )
        policy = {
            "draft_generation": generation_binding,
            "draft_evaluation": evaluation_binding,
            "scholarly_evaluation": scholarly.binding,
        }
    else:
        generation_id = json.loads(
            generation_paths["transaction"].read_text(encoding="utf-8")
        )["transaction_id"]
        policy = {
            "draft_generation": _lifecycle_locator(
            project, milestone=milestone, label=label, phase="generation",
            receipt_id=record["receipt_id"], paths=generation_paths,
            claim=generation_claim_path, consumption=generation_consumption_path,
            semantic_receipt=activation.receipt, wiki_root=activation.wiki_root,
            generation_transaction_id=None,
            semantics_manifest=semantics,
        ),
            "draft_evaluation": _lifecycle_locator(
            project, milestone=milestone, label=label, phase="evaluation",
            receipt_id=record["receipt_id"], paths=evaluation_paths,
            claim=evaluation_claim_path, consumption=evaluation_consumption_path,
            semantic_receipt=evaluation_semantic, wiki_root=activation.wiki_root,
            generation_transaction_id=generation_id,
            semantics_manifest=semantics,
        ),
            "scholarly_evaluation": scholarly.binding,
        }
    assert generation_claim["receipt_id"] == record["receipt_id"]
    assert generation_consumption["claim_id"] == generation_claim["claim_id"]
    assert evaluation_claim["receipt_id"] == record["receipt_id"]
    return consumed_receipt, policy


def main() -> int:
    native_v2_only = sys.argv[1:] == ["--native-v2-only"]
    if sys.argv[1:] and not native_v2_only:
        raise SystemExit("usage: assignment_milestone_checkpoint_smoketest.py [--native-v2-only]")
    # Package-local scratch keeps this end-to-end fixture runnable from a
    # distributed plugin cache whose production boundary correctly refuses
    # unrelated OS-temp writes when no workspace manifest is discoverable.
    with tempfile.TemporaryDirectory(
            prefix="assignment-milestone-checkpoint-", dir=ROOT) as raw:
        project = Path(raw) / "walk"
        run(BOOTSTRAP, "--project-root", project, "--project-name", "walk", "--title", "Synthetic Walk", "--intended-reader", "researcher", "--created-at", "2026-07-19T00:00:00Z", "--handoff-policy", "audited")
        write_valid_contract(project)

        # Native reader-profile v2 lifecycle compatibility: synthetic fixture
        # authority is injected only into library calls.  Production CLI paths
        # retain the real authority verifier and this fixture creates no
        # semantic transaction, publication, receipt, or commit marker.
        v2_project = Path(raw) / "native-v2"
        run(BOOTSTRAP, "--project-root", v2_project, "--project-name", "native-v2", "--title", "Synthetic Native V2", "--intended-reader", "researcher", "--created-at", "2026-07-19T00:00:00Z", "--handoff-policy", "audited")
        write_valid_contract(v2_project)
        v2_consumed, v2_policy = publish(
            v2_project, "M1", b"# M1 native v2 synthetic deliverable\n",
            native_v2=True, exercise_v2_adversarial=True,
        )
        v2_checkpoint = checkpoint_input(
            v2_project, "M1", "2026-07-19T00:00:02Z", policy=v2_policy,
        )
        fixture_adapter = DeterministicFixtureAdapter()
        record_transaction(
            v2_project, "M1", v2_consumed, v2_checkpoint,
            "2026-07-19T00:00:03Z",
            _test_authority_adapter=fixture_adapter,
        )
        v2_state = state(v2_project)
        v2_m1 = v2_state["milestone_framework"]["milestones"]["M1"]
        assert v2_m1["status"] == "in_progress" and v2_m1["artifacts"]
        original_draft_validator = milestone_transactions._validate_draft_evidence

        def force_v2_stale(*args, **kwargs):
            raise DraftGovernanceLifecycleError(
                "LIFECYCLE-DRAFT-GOVERNANCE-STALE",
                "forced stale lifecycle evidence",
            )

        milestone_transactions._validate_draft_evidence = force_v2_stale
        try:
            try:
                milestone_transactions._validate_checkpoint(
                    v2_project,
                    v2_checkpoint,
                    "M1",
                    "main",
                    json.loads(v2_consumed.read_text(encoding="utf-8"))["receipt_id"],
                    _test_authority_adapter=fixture_adapter,
                )
            except milestone_transactions.MilestoneTransactionError as exc:
                assert exc.code == "AMC-DRAFT-POLICY-STALE"
            else:
                raise AssertionError(
                    "v2 lifecycle staleness lost its typed milestone diagnostic"
                )
        finally:
            milestone_transactions._validate_draft_evidence = original_draft_validator
        generation_locator = json.loads(
            (v2_project / v2_policy["draft_generation"]["evidence_path"]).read_text(encoding="utf-8")
        )
        evaluation_locator = json.loads(
            (v2_project / v2_policy["draft_evaluation"]["evidence_path"]).read_text(encoding="utf-8")
        )
        evaluation_claim = json.loads(
            (v2_project / evaluation_locator["dispatch_claim"]["path"]).read_text(encoding="utf-8")
        )
        scholarly_value = json.loads(
            (v2_project / v2_policy["scholarly_evaluation"]["evidence_path"]).read_text(encoding="utf-8")
        )
        assert generation_locator["semantic_usage"] == "not_invoked"
        assert evaluation_locator["semantic_usage"] == "not_invoked"
        assert "generation_verifier" not in evaluation_claim
        assert evaluation_claim["generation_draft_governance"]["evidence_id"] == generation_locator["evidence_id"]
        assert scholarly_value["evaluation_dispatch"]["claim"]["path"] == evaluation_locator["dispatch_claim"]["path"]
        assert generation_locator["receipt_id"] == evaluation_locator["receipt_id"] == evaluation_claim["receipt_id"]
        assert not list(v2_project.rglob("evaluation-semantic.json"))
        assert not list(v2_project.rglob("evaluation-product"))
        generation_result = validate_lifecycle_draft_governance_binding(
            locator=v2_project / v2_policy["draft_generation"]["evidence_path"],
            artifact=v2_project / PATHS["M1"],
            project_root=v2_project,
            expected_phase="generation",
            expected_role="generator",
            expected_milestone="M1",
            expected_receipt_id=generation_locator["receipt_id"],
            expected_dispatch_claim=v2_project / generation_locator["dispatch_claim"]["path"],
            expected_dispatch_consumption=v2_project / generation_locator["dispatch_consumption"]["path"],
            _test_authority_adapter=fixture_adapter,
        )
        dependency_paths = {
            Path(row["path"]).as_posix() for row in generation_result["dependencies"]
        }
        assert any(
            path.endswith("/scripts/draft_governance_lifecycle.py")
            for path in dependency_paths
        )
        assert any(
            path.endswith("/references/schemas/lifecycle_draft_governance_binding.schema.json")
            for path in dependency_paths
        )
        alternate_inventory = (
            v2_project / "reviews/.harness/draft-governance/alternate-inventory.json"
        )
        alternate_inventory.write_bytes(
            (ROOT / "references/draft_governance_lifecycle_inventory.v1.json").read_bytes()
        )
        alternate_locator = json.loads(json.dumps(generation_locator))
        alternate_locator["lifecycle_inventory"] = _root_binding(
            v2_project, alternate_inventory, "harness",
        )
        alternate_locator_path = alternate_inventory.with_name(
            "alternate-inventory-lifecycle.json"
        )
        write_json(alternate_locator_path, alternate_locator)
        try:
            validate_lifecycle_draft_governance_binding(
                locator=alternate_locator_path,
                artifact=v2_project / PATHS["M1"],
                project_root=v2_project,
                expected_phase="generation",
                expected_role="generator",
                expected_milestone="M1",
                expected_receipt_id=generation_locator["receipt_id"],
                expected_dispatch_claim=v2_project / generation_locator["dispatch_claim"]["path"],
                expected_dispatch_consumption=v2_project / generation_locator["dispatch_consumption"]["path"],
                _test_authority_adapter=fixture_adapter,
            )
        except DraftGovernanceLifecycleError as exc:
            assert exc.code == "LIFECYCLE-DRAFT-GOVERNANCE-INVENTORY"
        else:
            raise AssertionError("v2 lifecycle accepted a substituted inventory path")
        try:
            validate_lifecycle_draft_governance_binding(
                locator=v2_project / v2_policy["draft_generation"]["evidence_path"],
                artifact=v2_project / PATHS["M1"],
                project_root=v2_project,
                expected_phase="generation",
                expected_role="generator",
                expected_milestone="M1",
                expected_receipt_id="receipt-from-another-authority-chain",
                expected_dispatch_claim=v2_project / generation_locator["dispatch_claim"]["path"],
                expected_dispatch_consumption=v2_project / generation_locator["dispatch_consumption"]["path"],
                _test_authority_adapter=fixture_adapter,
            )
        except DraftGovernanceLifecycleError as exc:
            assert exc.code == "LIFECYCLE-DRAFT-GOVERNANCE-DISPATCH"
        else:
            raise AssertionError("v2 lifecycle replay accepted a cross-receipt authority")
        try:
            validate_lifecycle_draft_governance_binding(
                locator=v2_project / v2_policy["draft_generation"]["evidence_path"],
                artifact=v2_project / PATHS["M1"],
                project_root=v2_project,
                expected_phase="generation",
                expected_role="generator",
                expected_milestone="M2",
                expected_receipt_id=generation_locator["receipt_id"],
                expected_dispatch_claim=v2_project / generation_locator["dispatch_claim"]["path"],
                expected_dispatch_consumption=v2_project / generation_locator["dispatch_consumption"]["path"],
                _test_authority_adapter=fixture_adapter,
            )
        except DraftGovernanceLifecycleError as exc:
            assert exc.code == "LIFECYCLE-DRAFT-GOVERNANCE-DISPOSITION"
        else:
            raise AssertionError("M1 draft governance accepted under the M2 artifact contract")
        malformed_locator = (
            v2_project / "reviews/.harness/draft-governance/malformed-root.json"
        )
        malformed_locator.parent.mkdir(parents=True, exist_ok=True)
        for malformed_root in ([], "scalar", 7):
            malformed_locator.write_text(
                json.dumps(malformed_root) + "\n", encoding="utf-8"
            )
            try:
                milestone_transactions._validate_draft_evidence(
                    v2_project, malformed_locator, v2_project / PATHS["M1"],
                    "generation", "evaluation_ready",
                )
            except DraftGovernanceLifecycleError as exc:
                assert exc.code == "LIFECYCLE-DRAFT-GOVERNANCE-INVALID"
            else:
                raise AssertionError(
                    "milestone transaction accepted a non-object lifecycle locator"
                )
        v2_validation = validate_document(
            v2_project, v2_state, _test_authority_adapter=fixture_adapter,
        )
        assert v2_validation.exit_permitted, v2_validation.findings
        phase_state_path = v2_project / "reviews/phase_state.json"
        phase_state_bytes = phase_state_path.read_bytes()
        malformed_locator.write_text("[]\n", encoding="utf-8")
        malformed_state = json.loads(phase_state_bytes)
        malformed_state["milestone_framework"]["milestones"]["M1"][
            "policy_evidence"
        ]["draft_generation"] = {
            "evidence_path": malformed_locator.relative_to(v2_project).as_posix(),
            "evidence_sha256": sha(malformed_locator),
        }
        malformed_validation = validate_document(
            v2_project, malformed_state, _test_authority_adapter=fixture_adapter,
        )
        assert not malformed_validation.exit_permitted
        assert any(
            row.code == "AMC-SCHOLARLY-EVALUATION-STALE"
            for row in malformed_validation.findings
        )
        write_json(phase_state_path, malformed_state)
        malformed_full_run = run(
            FULL_RUN, "terminal", "--project-root", v2_project, expected=4,
        )
        assert "FRC-DRAFT-POLICY-STALE" in malformed_full_run.stdout
        phase_state_path.write_bytes(phase_state_bytes)
        if native_v2_only:
            print("assignment milestone native-v2 lifecycle smoketest: PASS")
            return 0

        # No state or F9 handoff is edited by this test: every lifecycle change
        # below goes through the public command under test.
        ticks = iter(range(1, 50))
        for milestone in ("M1",):
            print(f"walk/{milestone}", flush=True)
            if milestone != "M1":
                run(CHECKPOINT, "begin", "--project-root", project, "--milestone", milestone, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
            derived = json.loads(run(CHECKPOINT, "derive", "--project-root", project).stdout)
            assert derived == {"status": "READY", "milestone": milestone, "action": "draft", "authority_mode": "direct_local"}, derived
            consumed, draft_policy = publish(
                project, milestone, f"# {milestone} synthetic deliverable\n".encode(),
            )
            checkpoint = checkpoint_input(
                project, milestone, f"2026-07-19T00:00:{next(ticks):02d}Z",
                policy=draft_policy,
            )
            run(CHECKPOINT, "record", "--project-root", project, "--milestone", milestone, "--receipt", consumed, "--checkpoint", checkpoint, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
            approval = approval_input(project, milestone, f"2026-07-19T00:00:{next(ticks):02d}Z")
            run(CHECKPOINT, "accept", "--project-root", project, "--milestone", milestone, "--checkpoint", checkpoint, "--approval-evidence", approval, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
            run(VALIDATOR, "--project-root", project)

        # Reader-profile v2 refresh is round-gated and never consumes semantic
        # re-pin requests. Legacy semantic-v1 request handling is covered by
        # the dedicated re-pin regressions.
        initial = state(project)
        initial_binding = initial["milestone_framework"]["policy_bindings"]["reader_accessibility"]
        assert initial_binding["binding_version"] == "2.0.0"
        before_open_round_refusal = (project / "reviews" / "phase_state.json").read_bytes()
        refused = run(CHECKPOINT, "rebind-reader-policy", "--project-root", project, expected=4)
        assert "AMC-REPIN-ROUND" in refused.stdout
        assert (project / "reviews" / "phase_state.json").read_bytes() == before_open_round_refusal
        # Synthetic phase setup: this lifecycle fixture does not run the
        # section-round closer, so mark its initial dispatch logs closed before
        # testing the authorized no-open-round transaction boundary.
        closed = state(project)
        for section in closed["sections"].values():
            if section.get("phase_entry_log"):
                section["phase_entry_log"].append({
                    "prev_phase": "Ph1", "new_phase": "Ph1",
                    "trigger": "ph1_draft_completion_signed", "actor": "planner",
                    "notes": "Synthetic no-open-round boundary for Planner rebind regression.",
                    "timestamp": "2026-07-19T00:00:00Z", "model_used": None,
                })
        write_json(project / "reviews" / "phase_state.json", closed)
        before_no_delta = (project / "reviews" / "phase_state.json").read_bytes()
        refused = run(CHECKPOINT, "rebind-reader-policy", "--project-root", project, expected=4)
        assert "AMC-REPIN-NO-DELTA" in refused.stdout, refused.stdout
        assert (project / "reviews" / "phase_state.json").read_bytes() == before_no_delta

        # Build a self-consistent stale v2 snapshot without changing live
        # package sources. The refresh must replace both artifacts, carry
        # transitions, publish one distinct receipt, and record source-binding
        # digests without introducing any semantic pin.
        stale_state = state(project)
        stale_binding = stale_state["milestone_framework"]["policy_bindings"]["reader_accessibility"]
        prior_transitions = json.loads(json.dumps(stale_binding["transitions"]))
        resolved_path = project / stale_binding["resolved_path"]
        stale_resolved = json.loads(resolved_path.read_text(encoding="utf-8"))
        stale_resolved["profile_sha256"] = "0" * 64
        stale_resolved["source_bindings"][0]["sha256"] = "0" * 64
        write_json(resolved_path, stale_resolved)
        stale_binding["profile_sha256"] = "0" * 64
        stale_binding["source_bindings"] = json.loads(
            json.dumps(stale_resolved["source_bindings"])
        )
        stale_binding["resolved_sha256"] = sha(resolved_path)
        write_json(project / "reviews" / "phase_state.json", stale_state)

        applied = run(CHECKPOINT, "rebind-reader-policy", "--project-root", project)
        assert applied.stdout.startswith("REBOUND "), applied.stdout
        receipt_path = Path(applied.stdout.strip().removeprefix("REBOUND "))
        assert receipt_path.is_file()
        refreshed = state(project)["milestone_framework"]["policy_bindings"]["reader_accessibility"]
        assert refreshed["binding_version"] == "2.0.0"
        assert refreshed["semantic_usage"] == "not_invoked"
        assert refreshed["profile_sha256"] != "0" * 64
        assert refreshed["transitions"] == prior_transitions
        assert all(key not in refreshed for key in (
            "attestation_view_pin", "exemplar_view_pin", "graph_sha256_provenance", "pin_epoch",
        ))
        assert sha(resolved_path) == refreshed["resolved_sha256"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert receipt["schema_version"] == "2.0.0"
        assert len(receipt["prior"]["source_bindings_digest"]) == 64
        assert len(receipt["current"]["source_bindings_digest"]) == 64
        assert receipt["current"]["semantic_usage"] == "not_invoked"
        assert receipt["current"]["milestone_policy_evidence_refreshed"] == []
        run(VALIDATOR, "--project-root", project)

        # Continue the canonical walk only after the M1-bound refresh.  This
        # is the active Paper2 lifecycle posture and does not rewrite accepted
        # M3+ reader evidence or immutable F9 bytes.
        for milestone in ("M2", "M3"):
            print(f"walk/{milestone}", flush=True)
            run(CHECKPOINT, "begin", "--project-root", project, "--milestone", milestone, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
            derived = json.loads(run(CHECKPOINT, "derive", "--project-root", project).stdout)
            assert derived == {"status": "READY", "milestone": milestone, "action": "draft", "authority_mode": "direct_local"}, derived
            consumed, draft_policy = publish(
                project, milestone, f"# {milestone} synthetic deliverable\n".encode()
            )
            checkpoint = checkpoint_input(
                project, milestone, f"2026-07-19T00:00:{next(ticks):02d}Z",
                policy=draft_policy,
            )
            run(CHECKPOINT, "record", "--project-root", project, "--milestone", milestone, "--receipt", consumed, "--checkpoint", checkpoint, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
            approval = approval_input(project, milestone, f"2026-07-19T00:00:{next(ticks):02d}Z")
            run(CHECKPOINT, "accept", "--project-root", project, "--milestone", milestone, "--checkpoint", checkpoint, "--approval-evidence", approval, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
            run(VALIDATOR, "--project-root", project)

        before_wrong_begin = (project / "reviews" / "phase_state.json").read_bytes()
        refused = run(CHECKPOINT, "begin", "--project-root", project, "--milestone", "M3", "--at", f"2026-07-19T00:00:{next(ticks):02d}Z", expected=4)
        assert "AMC-ORDER" in refused.stdout and (project / "reviews" / "phase_state.json").read_bytes() == before_wrong_begin
        run(CHECKPOINT, "begin", "--project-root", project, "--milestone", "M4", "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
        print("walk/M4-started", flush=True)
        before = state(project)["milestone_framework"]["milestones"]["M4"]
        assert before["status"] == "in_progress" and not before["artifacts"]
        assert set(before["policy_evidence"]) == {"profile_path", "profile_sha256", "resolved_sha256", "semantic_usage"}
        run(VALIDATOR, "--project-root", project)

        consumed, draft_policy = publish(
            project, "M4", b"# M4 complete initial manuscript\n"
        )
        forged_receipt = project / "reviews" / ".harness" / "milestones" / "checkpoints" / "copied_consumed_receipt.json"
        forged_receipt.write_bytes(consumed.read_bytes())
        forged_checkpoint = checkpoint_input(
            project, "M4", f"2026-07-19T00:00:{next(ticks):02d}Z",
            policy=draft_policy,
        )
        phase_before_forgery = (project / "reviews" / "phase_state.json").read_bytes()
        refused = run(CHECKPOINT, "record", "--project-root", project, "--milestone", "M4", "--receipt", forged_receipt, "--checkpoint", forged_checkpoint, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z", expected=4)
        assert "APG-RECEIPT-INVALID" in refused.stdout and (project / "reviews" / "phase_state.json").read_bytes() == phase_before_forgery
        invalid_checkpoint = checkpoint_input(
            project, "M4", f"2026-07-19T00:00:{next(ticks):02d}Z",
            valid_m4=False, policy=draft_policy,
        )
        phase_before_refusal = (project / "reviews" / "phase_state.json").read_bytes()
        refused = run(CHECKPOINT, "record", "--project-root", project, "--milestone", "M4", "--receipt", consumed, "--checkpoint", invalid_checkpoint, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z", expected=4)
        assert "AMC-CHECKPOINT" in refused.stdout and (project / "reviews" / "phase_state.json").read_bytes() == phase_before_refusal

        valid_checkpoint = checkpoint_input(
            project, "M4", f"2026-07-19T00:00:{next(ticks):02d}Z",
            policy=draft_policy,
        )
        checkpoint_bytes = valid_checkpoint.read_bytes()
        phase_before_mutation = (project / "reviews" / "phase_state.json").read_bytes()
        try:
            record_transaction(
                project, "M4", consumed, valid_checkpoint,
                f"2026-07-19T00:00:{next(ticks):02d}Z",
                _before_state_publish=lambda: valid_checkpoint.write_bytes(checkpoint_bytes + b" "),
            )
        except MilestoneTransactionError as exc:
            assert exc.code == "AMC-DEPENDENCY-CHANGED", exc.code
        else:
            raise AssertionError("record accepted a checkpoint mutated after validation")
        assert (project / "reviews" / "phase_state.json").read_bytes() == phase_before_mutation
        failed_snapshot = project / "reviews" / ".harness" / "snapshots" / "M4" / f"{sha(project / PATHS['M4'])}.md"
        assert not failed_snapshot.exists(), "failed record left an unbound M4 snapshot"
        valid_checkpoint.write_bytes(checkpoint_bytes)
        run(CHECKPOINT, "record", "--project-root", project, "--milestone", "M4", "--receipt", consumed, "--checkpoint", valid_checkpoint, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
        after = state(project)["milestone_framework"]["milestones"]["M4"]
        manuscript = after["artifacts"][0]
        assert after["policy_evidence"]["manuscript_sha256"] == manuscript["sha256"]
        assert after["policy_evidence"]["phase"] == "Ph1"
        assert after["policy_evidence"]["cycle_id"] == "m4-initial-assembly-001"
        run(VALIDATOR, "--project-root", project)

        # Initial assembly is not the end of M4. A later, receipt-scoped
        # Generator revision must be re-recordable without rewriting the first
        # deliverable event or its exact-byte evidence.
        initial_digest = manuscript["sha256"]
        initial_event_count = len(state(project)["milestone_framework"]["events"])
        advance_m4_fixture_to_ph2(project)
        run(PHASE_VALIDATOR, "--project-root", project)
        derived = json.loads(run(CHECKPOINT, "derive", "--project-root", project).stdout)
        assert derived == {"status": "READY", "milestone": "M4", "action": "revise", "authority_mode": "direct_local"}, derived
        revised_consumed, revised_policy = publish(
            project, "M4", b"# M4 substantively revised manuscript\n",
            label="ph2-revision",
        )
        revised_checkpoint = checkpoint_input(
            project, "M4", f"2026-07-19T00:00:{next(ticks):02d}Z",
            label="ph2-revision", phase="Ph2", cycle_id="m4-ph2-revision-001",
            policy=revised_policy,
        )
        run(
            CHECKPOINT, "record", "--project-root", project, "--milestone", "M4",
            "--receipt", revised_consumed, "--checkpoint", revised_checkpoint,
            "--at", f"2026-07-19T00:00:{next(ticks):02d}Z",
        )
        revised = state(project)["milestone_framework"]
        revised_m4 = revised["milestones"]["M4"]
        assert revised_m4["artifacts"][0]["sha256"] != initial_digest
        assert revised_m4["policy_evidence"]["phase"] == "Ph2"
        assert revised_m4["policy_evidence"]["cycle_id"] == "m4-ph2-revision-001"
        assert len(revised["events"]) == initial_event_count + 3
        run(VALIDATOR, "--project-root", project)
        valid_checkpoint = revised_checkpoint

        approval = approval_input(project, "M4", f"2026-07-19T00:00:{next(ticks):02d}Z")
        phase_before_accept = (project / "reviews" / "phase_state.json").read_bytes()
        refused = run(CHECKPOINT, "accept", "--project-root", project, "--milestone", "M4", "--checkpoint", valid_checkpoint, "--approval-evidence", approval, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z", expected=4)
        assert "AMC-M4-NOT-CONVERGED" in refused.stdout
        assert (project / "reviews" / "phase_state.json").read_bytes() == phase_before_accept
        assert not (project / "reviews" / ".harness" / "handoffs" / "M4_to_M5.json").exists()

        # A live claim cannot be recovered, and there is no TTL bypass.
        claim = project / "reviews" / ".harness" / "milestones" / "claims" / "transaction.lock"
        write_json(claim, {"schema_version": "1.0.0", "pid": __import__("os").getpid(), "host": __import__("platform").node(), "operation": "test", "started_at": "2026-07-19T00:00:00Z"})
        refused = run(CHECKPOINT, "recover", "--project-root", project, "--acknowledgement", "inspected-milestone-state-and-journal", expected=4)
        assert "AMC-RECOVERY-LIVE" in refused.stdout and claim.exists()
        claim.unlink()

        write_json(claim, {"schema_version": "1.0.0", "pid": 2147483647, "host": "foreign-host", "operation": "accept:M4", "started_at": "2026-07-19T00:00:00Z"})
        refused = run(CHECKPOINT, "recover", "--project-root", project, "--acknowledgement", "inspected-milestone-state-and-journal", expected=4)
        assert "AMC-RECOVERY-FOREIGN" in refused.stdout and claim.exists()
        claim.unlink()

        # Adversarial residue injection is outside the positive public walk:
        # inspected recovery archives both a dead claim and an unbound F9.
        orphan = project / "reviews" / ".harness" / "handoffs" / "M4_to_M5.json"
        write_json(orphan, {"synthetic_orphan": True})
        write_json(claim, {"schema_version": "1.0.0", "pid": 2147483647, "host": __import__("platform").node(), "operation": "accept:M4", "started_at": "2026-07-19T00:00:00Z"})
        run(CHECKPOINT, "recover", "--project-root", project, "--acknowledgement", "inspected-milestone-state-and-journal")
        assert not claim.exists() and not orphan.exists()
        journal = project / "reviews" / ".harness" / "milestones" / "journal"
        assert list(journal.glob("recovered-claim-*.json")) and list(journal.glob("orphan-M4_to_M5-*.json"))

        # Separate acceptance fixture: phase ownership is prepared explicitly,
        # then the milestone acceptance itself remains public-command-only.
        converge_m4_fixture(project)
        run(PHASE_VALIDATOR, "--project-root", project)
        policy = m4_acceptance_policy_input(project)
        approval = approval_input(project, "M4", f"2026-07-19T00:00:{next(ticks):02d}Z")
        approval_bytes = approval.read_bytes()
        phase_before_accept_mutation = (project / "reviews" / "phase_state.json").read_bytes()
        try:
            accept_transaction(
                project, "M4", valid_checkpoint, approval,
                f"2026-07-19T00:00:{next(ticks):02d}Z", policy,
                _before_state_publish=lambda: approval.write_bytes(approval_bytes + b" "),
            )
        except MilestoneTransactionError as exc:
            assert exc.code == "AMC-DEPENDENCY-CHANGED", exc.code
        else:
            raise AssertionError("accept published state after approval evidence mutation")
        assert (project / "reviews" / "phase_state.json").read_bytes() == phase_before_accept_mutation
        assert not (project / "reviews" / ".harness" / "handoffs" / "M4_to_M5.json").exists()
        approval.write_bytes(approval_bytes)
        run(CHECKPOINT, "accept", "--project-root", project, "--milestone", "M4", "--checkpoint", valid_checkpoint, "--approval-evidence", approval, "--policy-evidence", policy, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
        accepted = state(project)["milestone_framework"]["milestones"]["M4"]
        assert accepted["status"] == "accepted" and accepted["policy_evidence"]["phase"] == "Ph3"
        run(VALIDATOR, "--project-root", project)

    print("OK assignment_milestone_checkpoint_smoketest")
    return 0


if __name__ == "__main__":
    with semantic_graph_fixture_environment():
        raise SystemExit(main())
