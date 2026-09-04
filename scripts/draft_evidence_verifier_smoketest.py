#!/usr/bin/env python3
"""Focused C3 transaction, manifest, replay, and recovery boundary."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

import draft_evidence_verifier as verifier
import draft_governance
import evidence_publication
from c2_evidence_fixture_support import build_activation_fixture
from reader_accessibility_policy import (
    reader_profile_phase_state_binding,
    resolve_reader_profile,
)


ROOT = Path(__file__).resolve().parent.parent
SEMANTICS_MANIFEST = ROOT / "references" / "semantics_manifest.v1.json"
PRODUCT_V2_SCHEMA = ROOT / "references" / "schemas" / "product_assurance.v2.schema.json"
TRANSACTION_SCHEMA = ROOT / "references" / "schemas" / "verifier_transaction.schema.json"
BLOCKER_SCHEMA = ROOT / "references" / "schemas" / "verifier_blocker.schema.json"
PUBLICATION_SCHEMA = ROOT / "references" / "schemas" / "verifier_publication_manifest.schema.json"
MARKER_SCHEMA = ROOT / "references" / "schemas" / "verifier_commit_marker.schema.json"
CLAIM_SCHEMA = ROOT / "references" / "schemas" / "evidence_publication_claim.schema.json"
JOURNAL_SCHEMA = ROOT / "references" / "schemas" / "evidence_publication_journal.schema.json"


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def tree_state(
    root: Path,
    *,
    omit_locks: bool = False,
    include_mtime: bool = True,
) -> list[tuple[str, str, str | None, int | None]]:
    if not root.exists():
        return []
    rows: list[tuple[str, str, str | None, int | None]] = []
    for path in sorted(root.rglob("*")):
        if omit_locks and path.name == "claim.lock":
            continue
        relative = path.relative_to(root).as_posix()
        if path.is_file():
            rows.append((
                relative,
                "file",
                hashlib.sha256(path.read_bytes()).hexdigest(),
                path.stat().st_mtime_ns if include_mtime else None,
            ))
        elif not omit_locks:
            rows.append((relative, "dir", None, None))
    return rows


def require_refusal(call, code: str) -> None:
    try:
        call()
    except verifier.VerifierError as exc:
        assert exc.code == code, (exc.code, exc.message)
    else:
        raise AssertionError(f"expected verifier refusal {code}")


def build_graph_independent_fixture(root: Path):
    activation = build_activation_fixture(root)
    write_json(
        activation.root / "project_manifest.json",
        json.loads(activation.project_manifest.read_text(encoding="utf-8")),
    )
    directives = activation.root / "research_notes" / "directives.md"
    directives.parent.mkdir(parents=True, exist_ok=True)
    directives.write_text(
        "project_id: graph-independent-test\npassage_scope_class: technical\n",
        encoding="utf-8",
    )
    resolved = resolve_reader_profile(activation.root)
    reader_policy = (
        activation.root
        / "reviews"
        / ".harness"
        / "policies"
        / "reader_accessibility.resolved.json"
    )
    write_json(reader_policy, resolved)
    phase_state = activation.root / "reviews" / "phase_state.json"
    write_json(
        phase_state,
        {
            "milestone_framework": {
                "policy_bindings": {
                    "reader_accessibility": reader_profile_phase_state_binding(
                        resolved, reader_policy, activation.root
                    )
                }
            }
        },
    )
    return activation, reader_policy


def main() -> int:
    required_callables = (
        "publish_verifier_transaction",
        "validate_verifier_transaction",
        "recover_verifier_transaction",
    )
    missing_callables = [
        name for name in required_callables
        if not callable(getattr(verifier, name, None))
    ]
    missing_files = [
        str(path.relative_to(ROOT))
        for path in (
            SEMANTICS_MANIFEST,
            PRODUCT_V2_SCHEMA,
            TRANSACTION_SCHEMA,
            BLOCKER_SCHEMA,
            PUBLICATION_SCHEMA,
            MARKER_SCHEMA,
            CLAIM_SCHEMA,
            JOURNAL_SCHEMA,
        )
        if not path.is_file()
    ]
    if missing_callables or missing_files:
        raise AssertionError(
            "C3 interface-activation red (not vulnerability reproduction): "
            f"missing callables={missing_callables}; missing files={missing_files}"
        )

    product_validator = Draft202012Validator(
        json.loads(PRODUCT_V2_SCHEMA.read_text(encoding="utf-8"))
    )
    transaction_validator = Draft202012Validator(
        json.loads(TRANSACTION_SCHEMA.read_text(encoding="utf-8"))
    )
    Draft202012Validator.check_schema(product_validator.schema)
    Draft202012Validator.check_schema(transaction_validator.schema)
    Draft202012Validator.check_schema(
        json.loads(BLOCKER_SCHEMA.read_text(encoding="utf-8"))
    )
    auxiliary_validators = {
        path.name: Draft202012Validator(json.loads(path.read_text(encoding="utf-8")))
        for path in (PUBLICATION_SCHEMA, MARKER_SCHEMA, CLAIM_SCHEMA, JOURNAL_SCHEMA)
    }
    for validator in auxiliary_validators.values():
        Draft202012Validator.check_schema(validator.schema)

    with tempfile.TemporaryDirectory(prefix="draft-evidence-verifier-c3-") as td:
        root = Path(td)
        graph, reader_policy = build_graph_independent_fixture(
            root / "graph-independent" / "project"
        )
        graph_published = verifier.publish_graph_independent_verifier_transaction(
            artifact=graph.artifact,
            reader_policy=reader_policy,
            phase="generation",
            project_root=graph.root,
            harness_root=ROOT,
            semantics_manifest=SEMANTICS_MANIFEST,
            out_dir=graph.root / "verifier" / "graph-independent",
            requested_independence_level="none",
        )
        graph_transaction = verifier.validate_verifier_transaction(
            transaction=graph_published["transaction"],
            publication_manifest=graph_published["publication_manifest"],
            commit_marker=graph_published["commit_marker"],
            artifact=graph.artifact,
            semantic_receipt=None,
            reader_policy=reader_policy,
            project_root=graph.root,
            wiki_root=None,
            harness_root=ROOT,
            semantics_manifest=SEMANTICS_MANIFEST,
        )
        assert graph_transaction["qualification_mode"] == "graph_independent_v2"
        assert graph_transaction["semantic_usage"] == "not_invoked"
        assert "semantic_receipt" not in graph_transaction

        activation = build_activation_fixture(root / "project")
        stronger_before = tree_state(activation.root, omit_locks=True)
        require_refusal(
            lambda: verifier.publish_verifier_transaction(
                artifact=activation.artifact,
                semantic_receipt=activation.receipt,
                phase="generation",
                project_root=activation.root,
                wiki_root=activation.wiki_root,
                harness_root=ROOT,
                semantics_manifest=SEMANTICS_MANIFEST,
                out_dir=activation.root / "verifier" / "unavailable-independence",
                requested_independence_level="host_attested_independence",
            ),
            "INDEPENDENCE_UNVERIFIED",
        )
        assert tree_state(activation.root, omit_locks=True) == stronger_before
        out_dir = activation.root / "verifier" / "control"
        published = verifier.publish_verifier_transaction(
            artifact=activation.artifact,
            semantic_receipt=activation.receipt,
            phase="generation",
            project_root=activation.root,
            wiki_root=activation.wiki_root,
            harness_root=ROOT,
            semantics_manifest=SEMANTICS_MANIFEST,
            out_dir=out_dir,
            requested_independence_level="none",
        )
        assert set(published) == {
            "transaction_id", "product_assurance", "transaction",
            "publication_manifest", "commit_marker",
        }
        product_validator.validate(json.loads(
            published["product_assurance"].read_text(encoding="utf-8")
        ))
        transaction = json.loads(
            published["transaction"].read_text(encoding="utf-8")
        )
        transaction_validator.validate(transaction)
        auxiliary_validators[PUBLICATION_SCHEMA.name].validate(json.loads(
            published["publication_manifest"].read_text(encoding="utf-8")
        ))
        auxiliary_validators[MARKER_SCHEMA.name].validate(json.loads(
            published["commit_marker"].read_text(encoding="utf-8")
        ))
        assert transaction["product_disposition"] == "evaluation_ready"
        assert transaction["qualification_mode"] == "governed_v3"
        validated = verifier.validate_verifier_transaction(
            transaction=published["transaction"],
            publication_manifest=published["publication_manifest"],
            commit_marker=published["commit_marker"],
            artifact=activation.artifact,
            semantic_receipt=activation.receipt,
            project_root=activation.root,
            wiki_root=activation.wiki_root,
            harness_root=ROOT,
            semantics_manifest=SEMANTICS_MANIFEST,
        )
        assert validated["transaction_id"] == published["transaction_id"]

        governance_result = draft_governance._verify_current_semantic_transaction(
            args=argparse.Namespace(
                phase="generation",
                role="generator",
                wiki_root=str(activation.wiki_root),
                verifier_out_dir=str(activation.root / "verifier" / "draft-governance"),
                semantics_manifest=str(SEMANTICS_MANIFEST),
                requested_independence_level="none",
            ),
            semantic_path=activation.receipt,
            semantic=json.loads(activation.receipt.read_text(encoding="utf-8")),
            evidence_paths=[activation.receipt],
            contract={"target": "FINAL", "project_root": str(activation.root)},
            artifact_path=activation.artifact,
            artifact_sha=hashlib.sha256(activation.artifact.read_bytes()).hexdigest(),
        )
        assert governance_result["product_disposition"] == "evaluation_ready"
        assert governance_result["verifier_transaction_id"].startswith("verifier-")

        transaction_lane = (
            activation.root
            / ".harness-evidence-transactions"
            / published["transaction_id"]
        )
        auxiliary_validators[CLAIM_SCHEMA.name].validate(json.loads(
            (transaction_lane / "claim.json").read_text(encoding="utf-8")
        ))
        auxiliary_validators[JOURNAL_SCHEMA.name].validate(json.loads(
            (transaction_lane / "journal.json").read_text(encoding="utf-8")
        ))
        idempotent_before = {
            "outputs": tree_state(out_dir),
            "transaction": tree_state(transaction_lane),
        }
        replay = verifier.publish_verifier_transaction(
            artifact=activation.artifact,
            semantic_receipt=activation.receipt,
            phase="generation",
            project_root=activation.root,
            wiki_root=activation.wiki_root,
            harness_root=ROOT,
            semantics_manifest=SEMANTICS_MANIFEST,
            out_dir=out_dir,
            requested_independence_level="none",
        )
        assert replay["transaction_id"] == published["transaction_id"]
        assert {
            "outputs": tree_state(out_dir),
            "transaction": tree_state(transaction_lane),
        } == idempotent_before

        lookalike = out_dir / "role-authored-verifier-transaction.json"
        shutil.copyfile(published["transaction"], lookalike)
        lookalike_before = tree_state(activation.root)
        require_refusal(
            lambda: verifier.validate_verifier_transaction(
                transaction=lookalike,
                publication_manifest=published["publication_manifest"],
                commit_marker=published["commit_marker"],
                artifact=activation.artifact,
                semantic_receipt=activation.receipt,
                project_root=activation.root,
                wiki_root=activation.wiki_root,
                harness_root=ROOT,
                semantics_manifest=SEMANTICS_MANIFEST,
            ),
            "ASSURANCE-FORGED",
        )
        assert tree_state(activation.root) == lookalike_before
        lookalike.unlink()

        copied_dir = activation.root / "verifier" / "role-authored-copy"
        shutil.copytree(out_dir, copied_dir)
        copied_before = tree_state(activation.root)
        require_refusal(
            lambda: verifier.validate_verifier_transaction(
                transaction=copied_dir / "verifier-transaction.json",
                publication_manifest=copied_dir / "publication-manifest.json",
                commit_marker=copied_dir / "commit-marker.json",
                artifact=activation.artifact,
                semantic_receipt=activation.receipt,
                project_root=activation.root,
                wiki_root=activation.wiki_root,
                harness_root=ROOT,
                semantics_manifest=SEMANTICS_MANIFEST,
            ),
            "ASSURANCE-FORGED",
        )
        assert tree_state(activation.root) == copied_before
        (copied_dir / "commit-marker.json").unlink()
        copied_recovery_before = tree_state(activation.root, omit_locks=True)
        require_refusal(
            lambda: verifier.recover_verifier_transaction(
                transaction=copied_dir / "verifier-transaction.json",
                publication_manifest=copied_dir / "publication-manifest.json",
                commit_marker=copied_dir / "commit-marker.json",
                artifact=activation.artifact,
                semantic_receipt=activation.receipt,
                project_root=activation.root,
                wiki_root=activation.wiki_root,
                harness_root=ROOT,
                semantics_manifest=SEMANTICS_MANIFEST,
                acknowledgement="inspected-evidence-state-and-journal",
            ),
            "ASSURANCE-FORGED",
        )
        assert tree_state(activation.root, omit_locks=True) == copied_recovery_before

        published["commit_marker"].unlink()
        incomplete_before = tree_state(activation.root, omit_locks=True)
        require_refusal(
            lambda: verifier.validate_verifier_transaction(
                transaction=published["transaction"],
                publication_manifest=published["publication_manifest"],
                commit_marker=published["commit_marker"],
                artifact=activation.artifact,
                semantic_receipt=activation.receipt,
                project_root=activation.root,
                wiki_root=activation.wiki_root,
                harness_root=ROOT,
                semantics_manifest=SEMANTICS_MANIFEST,
            ),
            "VERIFIER-TRANSACTION-INCOMPLETE",
        )
        assert tree_state(activation.root, omit_locks=True) == incomplete_before
        assert verifier.recover_verifier_transaction(
            transaction=published["transaction"],
            publication_manifest=published["publication_manifest"],
            commit_marker=published["commit_marker"],
            artifact=activation.artifact,
            semantic_receipt=activation.receipt,
            project_root=activation.root,
            wiki_root=activation.wiki_root,
            harness_root=ROOT,
            semantics_manifest=SEMANTICS_MANIFEST,
            acknowledgement="inspected-evidence-state-and-journal",
        ) == "committed"
        verifier.validate_verifier_transaction(
            transaction=published["transaction"],
            publication_manifest=published["publication_manifest"],
            commit_marker=published["commit_marker"],
            artifact=activation.artifact,
            semantic_receipt=activation.receipt,
            project_root=activation.root,
            wiki_root=activation.wiki_root,
            harness_root=ROOT,
            semantics_manifest=SEMANTICS_MANIFEST,
        )

        semantics_value = json.loads(
            SEMANTICS_MANIFEST.read_text(encoding="utf-8")
        )
        for label, mutate in (
            ("omission", lambda value: value["members"].pop()),
            ("addition", lambda value: value["members"].append(copy.deepcopy(value["members"][0]))),
            ("redirection", lambda value: value["members"][0].update({"path": "scripts/not-the-kernel.py"})),
        ):
            manifest_path = activation.root / f"semantics-{label}.json"
            write_json(manifest_path, semantics_value)
            baseline_dir = activation.root / "verifier" / f"manifest-{label}-control"
            verifier.publish_verifier_transaction(
                artifact=activation.artifact,
                semantic_receipt=activation.receipt,
                phase="generation",
                project_root=activation.root,
                wiki_root=activation.wiki_root,
                harness_root=ROOT,
                semantics_manifest=manifest_path,
                out_dir=baseline_dir,
                requested_independence_level="none",
            )
            changed = copy.deepcopy(semantics_value)
            mutate(changed)
            write_json(manifest_path, changed)
            attack_dir = baseline_dir
            refusal_before = tree_state(activation.root, omit_locks=True)
            require_refusal(
                lambda manifest_path=manifest_path, attack_dir=attack_dir:
                    verifier.publish_verifier_transaction(
                        artifact=activation.artifact,
                        semantic_receipt=activation.receipt,
                        phase="generation",
                        project_root=activation.root,
                        wiki_root=activation.wiki_root,
                        harness_root=ROOT,
                        semantics_manifest=manifest_path,
                        out_dir=attack_dir,
                        requested_independence_level="none",
                    ),
                "SEMANTICS-DIGEST-MISMATCH",
            )
            assert tree_state(activation.root, omit_locks=True) == refusal_before

        race_dir = activation.root / "verifier" / "input-race"
        original_artifact = activation.artifact.read_bytes()

        def mutate_under_claim() -> None:
            activation.artifact.write_bytes(
                activation.artifact.read_bytes() + b"\nchanged under claim\n"
            )

        race_before = tree_state(
            activation.root, omit_locks=True, include_mtime=False
        )
        try:
            require_refusal(
                lambda: verifier.publish_verifier_transaction(
                    artifact=activation.artifact,
                    semantic_receipt=activation.receipt,
                    phase="generation",
                    project_root=activation.root,
                    wiki_root=activation.wiki_root,
                    harness_root=ROOT,
                    semantics_manifest=SEMANTICS_MANIFEST,
                    out_dir=race_dir,
                    requested_independence_level="none",
                    _under_claim_hook=mutate_under_claim,
                ),
                "EVIDENCE-TOCTOU",
            )
        finally:
            activation.artifact.write_bytes(original_artifact)
        assert tree_state(
            activation.root, omit_locks=True, include_mtime=False
        ) == race_before

        interrupted_dir = activation.root / "verifier" / "interrupted"
        original_marker = evidence_publication._exclusive_marker

        def interrupt_marker(_path: Path, _data: bytes) -> None:
            raise OSError("injected verifier marker interruption")

        evidence_publication._exclusive_marker = interrupt_marker
        try:
            require_refusal(
                lambda: verifier.publish_verifier_transaction(
                    artifact=activation.artifact,
                    semantic_receipt=activation.receipt,
                    phase="generation",
                    project_root=activation.root,
                    wiki_root=activation.wiki_root,
                    harness_root=ROOT,
                    semantics_manifest=SEMANTICS_MANIFEST,
                    out_dir=interrupted_dir,
                    requested_independence_level="none",
                ),
                "VERIFIER-TRANSACTION-INCOMPLETE",
            )
        finally:
            evidence_publication._exclusive_marker = original_marker
        assert not (interrupted_dir / "commit-marker.json").exists()
        interrupted_transaction = json.loads(
            (interrupted_dir / "verifier-transaction.json").read_text(
                encoding="utf-8"
            )
        )
        interrupted_id = interrupted_transaction["transaction_id"]
        interrupted_lane = (
            activation.root / ".harness-evidence-transactions" / interrupted_id
        )
        interrupted_journal = json.loads(
            (interrupted_lane / "journal.json").read_text(encoding="utf-8")
        )
        assert interrupted_journal["state"] == "publishing"
        assert verifier.recover_verifier_transaction(
            transaction=interrupted_dir / "verifier-transaction.json",
            publication_manifest=interrupted_dir / "publication-manifest.json",
            commit_marker=interrupted_dir / "commit-marker.json",
            artifact=activation.artifact,
            semantic_receipt=activation.receipt,
            project_root=activation.root,
            wiki_root=activation.wiki_root,
            harness_root=ROOT,
            semantics_manifest=SEMANTICS_MANIFEST,
            acknowledgement="inspected-evidence-state-and-journal",
        ) == "committed"
        verifier.validate_verifier_transaction(
            transaction=interrupted_dir / "verifier-transaction.json",
            publication_manifest=interrupted_dir / "publication-manifest.json",
            commit_marker=interrupted_dir / "commit-marker.json",
            artifact=activation.artifact,
            semantic_receipt=activation.receipt,
            project_root=activation.root,
            wiki_root=activation.wiki_root,
            harness_root=ROOT,
            semantics_manifest=SEMANTICS_MANIFEST,
        )

    print("draft_evidence_verifier_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
