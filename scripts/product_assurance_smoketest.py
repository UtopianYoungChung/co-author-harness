#!/usr/bin/env python3
"""Hermetic regressions for the product-assurance kernel."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

from c2_evidence_fixture_support import build_activation_fixture


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "product_assurance.py"
RUN_ALL = ROOT / "scripts" / "audit" / "run_all.py"
SOURCE_EXTRACT = ROOT / "scripts" / "source_extract.py"
PRODUCT_SCHEMA = json.loads(
    (ROOT / "references" / "schemas" / "product_assurance.schema.json").read_text(
        encoding="utf-8"
    )
)
V3_SCHEMA = json.loads(
    (ROOT / "references" / "schemas" / "centroid_semantic_execution.v3.schema.json").read_text(
        encoding="utf-8"
    )
)
EXTRACT_SCHEMA = json.loads(
    (ROOT / "references" / "schemas" / "canonical_extract_receipt.schema.json").read_text(
        encoding="utf-8"
    )
)
BIBLIOGRAPHY_SCHEMA = json.loads(
    (ROOT / "references" / "schemas" / "canonical_bibliography_snapshot.schema.json").read_text(
        encoding="utf-8"
    )
)
PRODUCT_VALIDATOR = Draft202012Validator(PRODUCT_SCHEMA)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding(path: Path) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": sha(path)}


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"


def run(
    manuscript: Path,
    receipt: Path,
    output: Path,
    *,
    project_root: Path | None = None,
    wiki_root: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable, str(SCRIPT), "build", "--artifact", str(manuscript),
        "--semantic-receipt", str(receipt), "--out", str(output),
    ]
    if project_root is not None:
        command.extend(["--project-root", str(project_root)])
    if wiki_root is not None:
        command.extend(["--wiki-root", str(wiki_root)])
    return subprocess.run(
        command,
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def refusal_codes(output: Path) -> set[str]:
    if not output.is_file():
        return set()
    try:
        payload = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return set()
    PRODUCT_VALIDATOR.validate(payload)
    codes: set[str] = set()
    reason = payload.get("reason_code") if isinstance(payload, dict) else None
    if isinstance(reason, str):
        codes.add(reason)
    findings = payload.get("findings") if isinstance(payload, dict) else None
    if isinstance(findings, list):
        for row in findings:
            code = row.get("code") if isinstance(row, dict) else None
            if isinstance(code, str):
                codes.add(code)
    return codes


def expect_intended_refusal(
    failures: list[str],
    *,
    label: str,
    result: subprocess.CompletedProcess[str],
    output: Path,
    expected_code: str,
) -> None:
    """Collect C1 intended-red misses so every adversarial case executes."""
    actual_codes = refusal_codes(output)
    if result.returncode == 0 or expected_code not in actual_codes:
        failures.append(
            f"{label}: expected nonzero/{expected_code}, "
            f"actual rc={result.returncode} codes={sorted(actual_codes)}"
        )


def write_receipt(path: Path, manuscript: Path, source_a: Path, extract_a: Path,
                  source_b: Path, extract_b: Path, *, quote: str,
                  label: str = "1994a") -> None:
    payload = {
        "schema_version": "2.0.0",
        "receipt_type": "centroid_semantic_execution",
        "target": "M4",
        "phase": "evaluation",
        "role": "evaluator",
        "actor_id": "eval-1",
        "dispatch_id": "dispatch-eval-1",
        "artifact": binding(manuscript),
        "centroid_packet": {"path": str(path.resolve()), "sha256": "0" * 64},
        "generation_envelope": {"path": str(path.resolve()), "sha256": "0" * 64},
        "adjudications": [],
        "passages": [
            {
                "source_key": "yu-mylopoulos-1994-understanding-why",
                "use_scope": "surface",
                "source": binding(source_a),
                "locator": "p. 3",
                "extract": binding(extract_a),
                "extraction": {"method": "text-direct", "tool": "utf-8", "canonical": True},
                "quote": quote,
                "citation": {
                    "authors": ["Yu, E.", "Mylopoulos, J."], "year": 1994,
                    "title": "Understanding why in software process modelling",
                    "label": label,
                },
                "use": "Register and quotation evidence.",
            },
            {
                "source_key": "yu-mylopoulos-1994-modelling-strategic-actors",
                "use_scope": "surface",
                "source": binding(source_b),
                "locator": "p. 1",
                "extract": binding(extract_b),
                "extraction": {"method": "text-direct", "tool": "utf-8", "canonical": True},
                "quote": "social actors depend on each other",
                "citation": {
                    "authors": ["Yu, E.", "Mylopoulos, J."], "year": 1994,
                    "title": "Modelling strategic actor relationships",
                    "label": "1994b",
                },
                "use": "Register evidence.",
            },
        ],
        "semantic_assessment": {
            "summary": "independent semantic review", "strengths": [],
            "deviations": [], "warrant_limits": [], "actionable_findings": [],
        },
    }
    path.write_text(canonical_json(payload), encoding="utf-8", newline="\n")
    # Self-bindings above are deliberately ignored by this kernel; draft
    # governance owns cross-envelope identity and exact packet verification.


def main() -> int:
    assert SCRIPT.is_file(), "product assurance kernel has not been implemented"
    # Keep the hermetic fixture inside the plugin package.  A distributed
    # install intentionally has no discoverable workspace governance, so an OS
    # temp directory is correctly classified DEST-UNGOVERNED by the production
    # extractor.  Package-local scratch remains authorized and exercises the
    # same extraction path from both a source checkout and an installed cache.
    with tempfile.TemporaryDirectory(prefix="product-assurance-", dir=ROOT) as td:
        root = Path(td)
        source_a = root / "why.txt"; extract_a = root / "why.extract.txt"
        source_b = root / "actors.txt"; extract_b = root / "actors.extract.txt"
        text_a = "requirements models reveal the whys behind the whats and hows"
        text_b = "processes involve social actors depend on each other for goals"
        for path, text in ((source_a, text_a), (extract_a, text_a),
                           (source_b, text_b), (extract_b, text_b)):
            path.write_text(text + "\n", encoding="utf-8")
        adapter_text = root / "adapter.extract.txt"
        adapter_receipt = root / "adapter.extract.json"
        adapter = subprocess.run(
            [sys.executable, str(SOURCE_EXTRACT), "--source", str(source_a),
             "--text-out", str(adapter_text), "--receipt-out", str(adapter_receipt)],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert adapter.returncode == 0, adapter.stdout + adapter.stderr
        adapter_payload = json.loads(adapter_receipt.read_text(encoding="utf-8"))
        assert adapter_payload["extraction"] == {
            "method": "text-direct", "tool": "utf-8", "canonical": True,
        }

        good = root / "good.md"
        good.write_text(
            "# Abstract\n\nThe model reveals \"the whys behind the whats and hows\" "
            "(Yu & Mylopoulos, 1994a).\n\n# Body\n\nSocial actors depend on each other "
            "(Yu & Mylopoulos, 1994b).\n\n# References\n\n"
            "Yu, E., & Mylopoulos, J. (1994a). Understanding why in software process modelling.\n"
            "Yu, E., & Mylopoulos, J. (1994b). Modelling strategic actor relationships.\n",
            encoding="utf-8")
        receipt = root / "receipt.json"; report = root / "report.json"
        write_receipt(receipt, good, source_a, extract_a, source_b, extract_b,
                      quote="the whys behind the whats and hows")
        result = run(good, receipt, report)
        assert result.returncode == 0, result.stdout + result.stderr
        payload = json.loads(report.read_text(encoding="utf-8"))
        PRODUCT_VALIDATOR.validate(payload)
        assert payload["status"] == "passed"
        assert payload["dimensions"]["grounding"] == "passed"
        assert payload["dimensions"]["register"] == "passed"

        intended_red: list[str] = []

        # C1 canonical JSON parser attacks. Each malicious document has a
        # semantically benign twin that v0.38 already accepts.
        duplicate_receipt = root / "duplicate-key-receipt.json"
        duplicate_text = receipt.read_text(encoding="utf-8").replace(
            '"schema_version":"2.0.0"',
            '"schema_version":"9.9.9","schema_version":"2.0.0"',
            1,
        )
        duplicate_receipt.write_text(
            duplicate_text, encoding="utf-8", newline="\n"
        )
        duplicate_report = root / "duplicate-key-report.json"
        duplicate_result = run(good, duplicate_receipt, duplicate_report)
        expect_intended_refusal(
            intended_red,
            label="duplicate JSON key",
            result=duplicate_result,
            output=duplicate_report,
            expected_code="EVIDENCE-SCHEMA-INVALID",
        )

        unknown_receipt = root / "unknown-field-receipt.json"
        unknown_payload = json.loads(receipt.read_text(encoding="utf-8"))
        unknown_payload["unknown_trust_claim"] = True
        unknown_receipt.write_text(
            json.dumps(unknown_payload, indent=2) + "\n", encoding="utf-8",
        )
        unknown_report = root / "unknown-field-report.json"
        unknown_result = run(good, unknown_receipt, unknown_report)
        expect_intended_refusal(
            intended_red,
            label="unknown semantic-receipt field",
            result=unknown_result,
            output=unknown_report,
            expected_code="EVIDENCE-SCHEMA-INVALID",
        )

        nonfinite_receipt = root / "nonfinite-receipt.json"
        nonfinite_payload = json.loads(receipt.read_text(encoding="utf-8"))
        nonfinite_payload["semantic_assessment"]["summary"] = float("nan")
        nonfinite_receipt.write_text(
            json.dumps(nonfinite_payload, indent=2) + "\n", encoding="utf-8",
        )
        nonfinite_report = root / "nonfinite-report.json"
        nonfinite_result = run(good, nonfinite_receipt, nonfinite_report)
        expect_intended_refusal(
            intended_red,
            label="non-finite JSON value",
            result=nonfinite_result,
            output=nonfinite_report,
            expected_code="EVIDENCE-SCHEMA-INVALID",
        )

        canonical_receipt = root / "canonical-json-benign.json"
        canonical_payload = json.loads(receipt.read_text(encoding="utf-8"))
        canonical_receipt.write_text(
            json.dumps(
                canonical_payload, sort_keys=True, separators=(",", ":"),
                ensure_ascii=False,
            ) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        canonical_report = root / "canonical-json-benign-report.json"
        canonical_result = run(good, canonical_receipt, canonical_report)
        assert canonical_result.returncode == 0, canonical_result.stdout + canonical_result.stderr
        noncanonical_receipt = root / "noncanonical-json-receipt.json"
        noncanonical_receipt.write_text(
            json.dumps(canonical_payload, indent=4, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        noncanonical_report = root / "noncanonical-json-report.json"
        noncanonical_result = run(good, noncanonical_receipt, noncanonical_report)
        expect_intended_refusal(
            intended_red,
            label="non-canonical JSON serialization",
            result=noncanonical_result,
            output=noncanonical_report,
            expected_code="EVIDENCE-CANONICALIZATION-INVALID",
        )

        # Authorized C2 activation seam.  The complete v3 future evidence is
        # carried through the real FINAL product boundary, but production maps
        # only the explicitly supplied diagnostic legacy view.  Every future
        # trust fact remains synthetic, nonqualifying, and intentionally
        # unchecked until its independently reviewed red is confirmed.
        activation = build_activation_fixture(root / "c2-activation")
        Draft202012Validator(V3_SCHEMA).validate(
            json.loads(activation.receipt.read_text(encoding="utf-8"))
        )
        Draft202012Validator(EXTRACT_SCHEMA).validate(
            json.loads(activation.extract_receipt.read_text(encoding="utf-8"))
        )
        Draft202012Validator(BIBLIOGRAPHY_SCHEMA).validate(
            json.loads(activation.bibliography_snapshot.read_text(encoding="utf-8"))
        )
        activation_report = root / "c2-activation-benign-report.json"
        activation_result = run(
            activation.artifact,
            activation.receipt,
            activation_report,
            project_root=activation.root,
            wiki_root=activation.wiki_root,
        )
        assert activation_result.returncode == 0, (
            activation_result.stdout + activation_result.stderr
        )
        activation_payload = json.loads(activation_report.read_text(encoding="utf-8"))
        assert activation_payload["status"] == "passed", activation_payload
        assert activation_payload["semantic_receipt"] == binding(activation.receipt)
        activation_receipt_sha = sha(activation.receipt)
        stable_activation_result = {
            key: activation_payload[key]
            for key in (
                "status",
                "artifact",
                "corpus_extract_sha256",
                "dimensions",
                "findings",
                "adjudications",
            )
        }

        authority_claim = json.loads(activation.receipt.read_text(encoding="utf-8"))
        authority_claim["qualifying_authority"] = True
        authority_path = root / "c2-authority-claim.json"
        authority_path.write_text(
            json.dumps(authority_claim, indent=2) + "\n", encoding="utf-8",
        )
        authority_output = root / "c2-authority-claim-report.json"
        authority_result = run(
            activation.artifact,
            authority_path,
            authority_output,
            project_root=activation.root,
            wiki_root=activation.wiki_root,
        )
        assert (
            authority_result.returncode == 2
            and "SEMANTIC-RECEIPT-VERSION" in refusal_codes(authority_output)
        ), authority_result.stdout + authority_result.stderr

        def activation_attack(
            label: str,
            expected_code: str,
            *,
            receipt_change=None,
            extract_change=None,
            page_map_change=None,
            fixture_change=None,
        ) -> None:
            activation.reset()
            if receipt_change is not None:
                activation.mutate_receipt(receipt_change)
            if extract_change is not None:
                activation.mutate_extract(extract_change)
            if page_map_change is not None:
                activation.mutate_page_map(page_map_change)
            if fixture_change is not None:
                fixture_change()
            attacked_receipt_sha = sha(activation.receipt)
            assert attacked_receipt_sha != activation_receipt_sha, (
                f"{label}: one-fact twin did not change the supplied v3 bytes"
            )
            output = root / (
                "c2-" + "-".join(label.casefold().replace("/", " ").split()) + ".json"
            )
            result = run(
                activation.artifact,
                activation.receipt,
                output,
                project_root=activation.root,
                wiki_root=activation.wiki_root,
            )
            if result.returncode == 0:
                attacked_payload = json.loads(output.read_text(encoding="utf-8"))
                assert {
                    key: attacked_payload[key]
                    for key in stable_activation_result
                } == stable_activation_result, (
                    f"{label}: ignored future fact changed legacy diagnostic behavior"
                )
                assert attacked_payload["semantic_receipt"] == {
                    "path": str(activation.receipt.resolve()),
                    "sha256": attacked_receipt_sha,
                }, f"{label}: report did not bind the exact attacked v3 bytes"
            expect_intended_refusal(
                intended_red,
                label=f"C2 {label}",
                result=result,
                output=output,
                expected_code=expected_code,
            )

        activation_attack(
            "missing extraction receipt",
            "EXTRACT-RECEIPT-MISSING",
            receipt_change=lambda value: value["passages"][0].pop(
                "canonical_extract_receipt"
            ),
        )
        activation_attack(
            "uncommitted extraction receipt",
            "EXTRACT-RECEIPT-INVALID",
            fixture_change=activation.remove_extract_commit_marker,
        )
        activation_attack(
            "malformed extraction receipt",
            "EXTRACT-RECEIPT-INVALID",
            extract_change=lambda value: value.update({"extraction": []}),
        )
        activation_attack(
            "unsupported extractor version",
            "EXTRACTOR-UNSUPPORTED",
            extract_change=lambda value: value["extraction"]["executable"].update(
                {"version": "99.0.0"}
            ),
        )
        activation_attack(
            "extractor executable hash mismatch",
            "EXTRACTOR-IDENTITY-MISMATCH",
            extract_change=lambda value: value["extraction"]["executable"].update(
                {"sha256": "f" * 64}
            ),
        )
        activation_attack(
            "extractor argv mismatch",
            "EXTRACT-BINDING-STALE",
            extract_change=lambda value: value["extraction"].update(
                {"argv": ["-layout", "-enc", "UTF-8"]}
            ),
        )
        activation_attack(
            "extractor layout mismatch",
            "EXTRACT-BINDING-STALE",
            extract_change=lambda value: value["extraction"].update(
                {"layout_mode": "layout-v1"}
            ),
        )
        activation_attack(
            "extractor normalization mismatch",
            "EXTRACT-BINDING-STALE",
            extract_change=lambda value: value["extraction"].update(
                {"normalization_version": "unknown-v9"}
            ),
        )
        activation_attack(
            "extract binding mismatch",
            "EXTRACT-BINDING-STALE",
            extract_change=lambda value: value["normalized_output"].update(
                {"sha256": "0" * 64}
            ),
        )
        activation_attack(
            "source binding mismatch",
            "EXTRACT-BINDING-STALE",
            extract_change=lambda value: value["source"].update(
                {"sha256": "0" * 64}
            ),
        )
        activation_attack(
            "coordinated source and extract substitution",
            "EXTRACT-BINDING-STALE",
            fixture_change=activation.substitute_extract_objects,
        )
        activation_attack(
            "locator page mismatch",
            "EXTRACT-LOCATOR-MISMATCH",
            receipt_change=lambda value: value["passages"][0]["locator"].update(
                {"page_start": 3, "page_end": 3}
            ),
        )
        activation_attack(
            "locator occurrence mismatch",
            "EXTRACT-LOCATOR-MISMATCH",
            receipt_change=lambda value: value["passages"][0]["locator"].update(
                {"occurrence": 2}
            ),
        )
        activation_attack(
            "locator span mismatch",
            "EXTRACT-LOCATOR-MISMATCH",
            receipt_change=lambda value: value["passages"][0]["locator"].update(
                {"normalized_start_utf8": 0}
            ),
        )
        activation_attack(
            "repeated locator map occurrence mismatch",
            "EXTRACT-LOCATOR-MISMATCH",
            page_map_change=lambda value: value["named_spans"][
                "repeated_locator"
            ][1].update({"occurrence": 1}),
        )
        activation_attack(
            "cross-page map boundary mismatch",
            "EXTRACT-LOCATOR-MISMATCH",
            page_map_change=lambda value: value["pages"][0].update({
                "normalized_end_utf8": value["pages"][0][
                    "normalized_end_utf8"
                ] + 1,
            }),
        )
        activation_attack(
            "ligature map span mismatch",
            "EXTRACT-LOCATOR-MISMATCH",
            page_map_change=lambda value: value["named_spans"][
                "ligature_probe"
            ][0].update({"text_sha256": "0" * 64}),
        )
        activation_attack(
            "extraction path escape",
            "EXTRACT-PATH-ESCAPE",
            extract_change=lambda value: value["source"].update(
                {"path": "../../outside/miniature.pdf"}
            ),
        )
        activation_attack(
            "extraction path alias",
            "EXTRACT-PATH-ESCAPE",
            extract_change=lambda value: value["source"].update(
                {"path": "alias/../miniature.pdf"}
            ),
        )
        activation_attack(
            "quotation relabelled as conditioning",
            "PASSAGE-CLASSIFICATION-MISMATCH",
            receipt_change=lambda value: value["passages"][0].update(
                {"passage_use": "conditioning_passage"}
            ),
        )
        activation_attack(
            "manuscript span mismatch",
            "MANUSCRIPT-SPAN-MISMATCH",
            receipt_change=lambda value: value["passages"][0]["manuscript_span"].update(
                {"start_utf8": 0, "end_utf8": 1}
            ),
        )
        activation_attack(
            "conditioning evaluator review mismatch",
            "PASSAGE-CLASSIFICATION-MISMATCH",
            receipt_change=lambda value: value["passages"][1][
                "evaluator_review"
            ].update({"artifact_sha256": "0" * 64}),
        )
        activation_attack(
            "centroid surface passage missing",
            "CENTROID-COVERAGE-INCOMPLETE",
            receipt_change=lambda value: value["passages"][0].update(
                {"use_scope": "argument"}
            ),
        )
        activation_attack(
            "argument-member rationale missing",
            "CENTROID-COVERAGE-INCOMPLETE",
            receipt_change=lambda value: value["member_coverage"][1].pop("rationale"),
        )

        wrong_quote = root / "wrong-quote.json"
        write_receipt(wrong_quote, good, source_a, extract_a, source_b, extract_b,
                      quote="words absent from the canonical extract")
        result = run(good, wrong_quote, root / "wrong-quote-report.json")
        assert result.returncode == 2 and "QUOTE-NOT-IN-EXTRACT" in result.stdout

        wrong_label = root / "wrong-label.json"
        write_receipt(wrong_label, good, source_a, extract_a, source_b, extract_b,
                      quote="the whys behind the whats and hows", label="1994b")
        result = run(good, wrong_label, root / "wrong-label-report.json")
        assert result.returncode == 2 and "CITATION-SAME-YEAR" in result.stdout

        candidate = root / "candidate.md"
        candidate.write_text(
            good.read_text(encoding="utf-8").replace(
                "# References", "The bounded contribution is bounded and bounded.\n\n# References"
            ), encoding="utf-8",
        )
        candidate_receipt = root / "candidate-receipt.json"
        write_receipt(candidate_receipt, candidate, source_a, extract_a, source_b, extract_b,
                      quote="the whys behind the whats and hows")
        candidate_report = root / "candidate-report.json"
        first_candidate = run(candidate, candidate_receipt, candidate_report)
        assert first_candidate.returncode == 2
        candidate_payload = json.loads(candidate_report.read_text(encoding="utf-8"))
        semantic_candidates = [row for row in candidate_payload["findings"]
                               if row["severity"] == "candidate"]
        assert semantic_candidates
        receipt_payload = json.loads(candidate_receipt.read_text(encoding="utf-8"))
        receipt_payload["adjudications"] = [{
            "code": row["code"], "locator": row["locator"],
            "disposition": "accepted_synthesis",
            "rationale": "Independent Evaluator accepts this explicit synthesis for the fixture.",
        } for row in semantic_candidates]
        candidate_receipt.write_text(
            canonical_json(receipt_payload), encoding="utf-8", newline="\n"
        )
        adjudicated = run(candidate, candidate_receipt, root / "candidate-adjudicated.json")
        assert adjudicated.returncode == 0, adjudicated.stdout + adjudicated.stderr

        bad = root / "bad.md"
        bad.write_text(
            "# Abstract\n\nRequirements engineering is often reached for after failure. "
            "These are not rungs of a ladder.\n\n# Body\n\nThe design-time bounded contribution "
            "is bounded, bounded, and bounded.\n", encoding="utf-8")
        bad_receipt = root / "bad-receipt.json"
        write_receipt(bad_receipt, bad, source_a, extract_a, source_b, extract_b,
                      quote="the whys behind the whats and hows")
        result = run(bad, bad_receipt, root / "bad-report.json")
        assert result.returncode == 2
        codes = {row["code"] for row in json.loads((root / "bad-report.json").read_text(encoding="utf-8"))["findings"]}
        assert {"TERM-COINAGE", "REGISTER-ABSENT", "INSIDER-NEGATION",
                "EMPIRICAL-UNSUPPORTED"} <= codes, codes
        suite_out = root / "suite-findings.json"
        suite = subprocess.run(
            [sys.executable, str(RUN_ALL), str(bad), "--out", str(suite_out),
             "--semantic-receipt", str(bad_receipt), "--skip-accessibility",
             "--skip-d-style-profile"], cwd=ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        assert suite.returncode == 2, suite.stdout + suite.stderr
        suite_payload = json.loads(suite_out.read_text(encoding="utf-8"))
        suite_codes = {row["check_id"] for row in suite_payload["findings"]}
        assert {"TERM-COINAGE", "REGISTER-ABSENT", "INSIDER-NEGATION",
                "EMPIRICAL-UNSUPPORTED"} <= suite_codes

        if intended_red:
            raise AssertionError(
                "C1/C2 intended-red product-assurance regressions:\n- "
                + "\n- ".join(intended_red)
            )

    print("product_assurance_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
